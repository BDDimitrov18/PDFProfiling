#!/usr/bin/env python3
"""Score boundary detection against ground truth.
Usage: python eval_boundaries.py <folder> [--dpi 150] [--tolerance 0|1|both]
ground_truth.json format: {"file.pdf": [1, 14, 15, 31], ...}  (1-indexed true start pages)

Detection is the expensive part; tolerance is only a scoring parameter, so a single
detection pass is scored at BOTH tolerance 0 and tolerance 1 (default). This halves
GPU wall-time vs. running the script twice.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time
from pypdf import PdfReader
from production_state import atomic_json, file_hash, source_identity, source_lock, state_key
from run_production import runtime_settings, preflight,load_model_for_settings,detect_for_settings
from score_full import evaluate
from model_options import (add_model_arguments, resolve_model_arguments, load_kwargs,
                           usage_snapshot, usage_delta, summarize_usage)

def match_sets(pred: set, true: set, tol: int):
    """Greedy matching within +/- tol pages. Returns (tp, fp_set, fn_set)."""
    if tol == 0:
        return len(pred & true), pred - true, true - pred
    pred_left, true_left, tp = set(pred), set(true), 0
    for t in sorted(true):
        cands = [p for p in pred_left if abs(p - t) <= tol]
        if cands:
            pred_left.discard(min(cands, key=lambda p: abs(p - t)))
            true_left.discard(t)
            tp += 1
    return tp, pred_left, true_left

def score(per_file: list, tol: int):
    """Aggregate P/R/F1 over cached per-file predictions at a given tolerance."""
    TP = FP = FN = 0
    rows = []
    for name, pred, true, _total in per_file:
        tp, fp_set, fn_set = match_sets(pred, true, tol)
        TP += tp; FP += len(fp_set); FN += len(fn_set)
        rows.append((name, sorted(pred), sorted(true), sorted(fp_set), sorted(fn_set)))
    P = TP / (TP + FP) if TP + FP else 0.0
    R = TP / (TP + FN) if TP + FN else 0.0
    F1 = 2 * P * R / (P + R) if P + R else 0.0
    return TP, FP, FN, P, R, F1, rows

def model_details(model):
    from qwen38_client import Qwen38Client
    if isinstance(model, Qwen38Client):
        return model.model_details()
    details = {"model_commit": getattr(getattr(model, "config", None), "_commit_hash", None)}
    torch = sys.modules.get("torch")
    if torch is not None and torch.cuda.is_available():
        details.update(gpu=torch.cuda.get_device_name(), cuda=torch.version.cuda)
    return details


def run_predictions(folder, gt, run_dir, settings, pipeline, logger):
    """Resume completed PDFs only when source bytes, settings and code agree."""
    sources = {name: source_identity(folder / name) for name in gt}
    identity = {"settings": settings, "sources": sources}
    manifest_path = run_dir / "run.json"
    # A single evaluation writer owns the directory for its whole run.
    with source_lock(Path("evaluation"), run_dir):
        previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
        if previous and previous["identity"] != identity:
            raise ValueError("Run directory belongs to different inputs/code/settings; choose a new --run-dir")
        manifest = {"version": 1, "status": "running", "identity": identity,
                    "ground_truth_sha256": file_hash(folder / "ground_truth.json"),
                    "failed_attempts": previous.get('failed_attempts', []) if previous else [],
                    "model_details": previous.get("model_details") if previous else None}
        atomic_json(manifest_path, manifest)
        bundle, predictions, totals = None, {}, {}
        try:
            for name in gt:
                pdf = folder / name
                total = len(PdfReader(str(pdf)).pages)
                totals[name] = total
                cache_path = run_dir / "predictions" / (state_key(pdf) + ".json")
                cache_id = {"source": sources[name], "settings": settings}
                cached = json.loads(cache_path.read_text()) if cache_path.exists() else None
                if cached is not None:
                    if cached["identity"] != cache_id or cached["total_pages"] != total:
                        raise ValueError(f"Stale prediction checkpoint for {name}; choose a new --run-dir")
                    starts = cached["starts"]
                    if (not starts or starts[0] != 1 or starts != sorted(set(starts))
                            or any(type(p) is not int or not 1 <= p <= total for p in starts)):
                        raise ValueError(f"Invalid prediction checkpoint: {name}")
                    logger.info("CACHE (validated): %s", name)
                else:
                    if bundle is None:
                        preflight()
                        bundle = load_model_for_settings(pipeline,settings,logger)
                        details = model_details(bundle[0])
                        if manifest["model_details"] is not None and manifest["model_details"] != details:
                            raise ValueError("Model revision or GPU changed during this run; choose a new --run-dir")
                        manifest["model_details"] = details
                        atomic_json(manifest_path, manifest)
                    started = time.monotonic()
                    usage_before = usage_snapshot(bundle[0])
                    boundaries, rotations = detect_for_settings(pipeline,pdf,total,bundle,settings,logger,
                        run_dir/'seams'/state_key(pdf),sources[name])
                    starts = [b.page for b in boundaries]
                    if (not starts or starts[0] != 1 or starts != sorted(set(starts))
                            or any(type(p) is not int or not 1 <= p <= total for p in starts)):
                        raise ValueError(f"Invalid model boundaries: {name}")
                    if source_identity(pdf) != sources[name]:
                        raise ValueError(f"Source changed during evaluation: {name}")
                    feature_summary={}
                    measured_usage=usage_delta(usage_before,usage_snapshot(bundle[0]))
                    if settings.get('boundary_method') in ('features_v6','features_v7b','features_v8b','features_v9','features_v11','features_v11_fast'):
                        from feature_pipeline import cache_directory
                        directory=cache_directory(run_dir/'seams'/state_key(pdf),sources[name],settings)
                        feature_summary=json.loads((directory/'summary.json').read_text())
                        measured_usage=feature_summary['model_usage']
                    atomic_json(cache_path, {"version": 1, "identity": cache_id, "starts": starts,
                        "total_pages": total, "boundaries": [asdict(b) for b in boundaries],
                        "rotations_ccw_for_inference": rotations, "seconds": time.monotonic() - started,
                        "model_usage": measured_usage,**({'feature_summary':feature_summary} if feature_summary else {})})
                predictions[name] = set(starts) - {1}
                print(f"\n{name}\n  pred={sorted(predictions[name])}\n  true={sorted(set(gt[name]) - {1})}", flush=True)
            manifest["status"] = "complete"
            atomic_json(manifest_path, manifest)
        except BaseException:
            manifest["status"] = "failed"
            manifest['failed_attempts'].append({'ended_at_unix': time.time(),
                'model_usage': usage_snapshot(bundle[0]) if bundle else None})
            atomic_json(manifest_path, manifest)
            raise
        return predictions, totals


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--tolerance", choices=("0", "1", "both"), default="both")
    add_model_arguments(ap)
    ap.add_argument("--run-dir", type=Path, help="Separate cache/log/results directory for this experiment")
    ap.add_argument("--align-confirmation", action="store_true", help="Experimental: confirm the actual candidate seam")
    ap.add_argument('--boundary-method',choices=('legacy','features','features-refined','features-facts','archive','archive-context','archive-fast'),default='legacy')
    args = ap.parse_args(argv)
    folder = args.folder.resolve()
    run_dir = args.run_dir.resolve() if args.run_dir else folder / "eval_run"
    tols = [0, 1] if args.tolerance == "both" else [int(args.tolerance)]
    try:
        selected_model, revision, inference = resolve_model_arguments(args)
        if args.dpi <= 0:
            raise ValueError("DPI must be positive")
        gt = json.loads((folder / "ground_truth.json").read_text(encoding="utf-8"))
        if not gt or any(Path(n).name != n for n in gt):
            raise ValueError("Ground truth must list source basenames")
        missing = [n for n in gt if not (folder / n).is_file()]
        if missing:
            raise ValueError(f"Missing sources listed in ground truth: {missing}")
        masked = json.loads((folder / "masked.json").read_text()) if (folder / "masked.json").exists() else {}
        strata = json.loads((folder / "strata.json").read_text()) if (folder / "strata.json").exists() else {n: "all" for n in gt}
        totals = {n: len(PdfReader(str(folder / n)).pages) for n in gt}
        evaluate(gt, {n: set() for n in gt}, masked, strata, totals)  # Validate before loading the GPU.
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    import split
    logger = split.setup_logging(run_dir / "logs")
    settings = runtime_settings(selected_model, args.dpi, args.align_confirmation, revision, inference)
    if args.boundary_method!='legacy':
        from feature_pipeline import configure
        try:settings=configure(settings,args.boundary_method)
        except ValueError as exc:ap.error(str(exc))
    settings["code"]["eval_boundaries.py"] = file_hash(Path(__file__))
    try:
        preds, totals = run_predictions(folder, gt, run_dir, settings, split, logger)
    except Exception:
        logger.exception("Evaluation incomplete; completed PDF checkpoints are retained")
        return 1
    strict = evaluate(gt, preds, masked, strata, totals)
    aggregate = strict["by_stratum"]["aggregate"]
    # Preserve the historical result shape. These tolerance scores are unmasked;
    # strict_report applies the dataset's masks and reports each stratum separately.
    per_file = [(n, preds[n], set(gt[n]) - {1}, totals[n]) for n in gt]
    results = {"docs_exact": aggregate["docs_exact"], "docs_total": aggregate["docs_total"],
               "by_tolerance": {}, "strict_report": strict,
               "run_manifest": str(run_dir / "run.json")}
    checkpoints = [json.loads((run_dir / 'predictions' / (state_key(folder / n) + '.json')).read_text()) for n in gt]
    results['model_usage'] = summarize_usage(row.get('model_usage') for row in checkpoints)
    results['processing_seconds'] = sum(row['seconds'] for row in checkpoints)
    results['timing_scope'] = 'Successful PDF processing only; excludes model/server loading and failed attempts. Cached work retains original durations.'
    if settings.get('boundary_method') in ('features_v6','features_v7b','features_v8b','features_v9','features_v11','features_v11_fast'):
        results['seam_processing_seconds']=sum(row['feature_summary']['seam_processing_seconds'] for row in checkpoints)
        results['timing_scope']='Successful PDF attempts only. Original seam processing, including resumed work and failed seam attempts, is recorded separately in seam_processing_seconds; model/server startup is excluded.'
        results['model_usage_scope']='All recorded seam attempts, including retries and work reused after an interrupted PDF.'
    for tol in tols:
        TP, FP, FN, P, R, F1, rows = score(per_file, tol)
        print(f"\nBoundary score (unmasked, tolerance={tol}): TP={TP} FP={FP} FN={FN} P={P:.2%} R={R:.2%} F1={F1:.2%}")
        results["by_tolerance"][str(tol)] = {
            "TP": TP, "FP": FP, "FN": FN, "precision": P, "recall": R, "f1": F1,
            "per_file": [{"file": n, "pred": p, "true": t, "fp": f, "fn": fnn} for n, p, t, f, fnn in rows]}
    print(f"Strict masked F1={aggregate['f1']:.2%}; exact documents={aggregate['docs_exact']}/{aggregate['docs_total']}")
    out = run_dir / "eval_results.json"
    atomic_json(out, results)
    # Old callers expect this file; custom experiment directories stay isolated.
    if args.run_dir is None:
        atomic_json(folder / "eval_results.json", results)
    print(f"Written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
