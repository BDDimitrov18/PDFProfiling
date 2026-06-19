#!/usr/bin/env python3
"""Score boundary detection against ground truth.
Usage: python eval_boundaries.py <folder> [--dpi 150] [--tolerance 0|1|both]
ground_truth.json format: {"file.pdf": [1, 14, 15, 31], ...}  (1-indexed true start pages)

Detection is the expensive part; tolerance is only a scoring parameter, so a single
detection pass is scored at BOTH tolerance 0 and tolerance 1 (default). This halves
GPU wall-time vs. running the script twice.
"""
import argparse, json, sys
from pathlib import Path
from pypdf import PdfReader
from run8 import detect_boundaries, load_model, setup_logging, MODEL_PATH, DEFAULT_DPI

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    ap.add_argument("--tolerance", default="both", help="0, 1, or both (default)")
    ap.add_argument("--model", default=MODEL_PATH)
    args = ap.parse_args()

    tols = [0, 1] if args.tolerance == "both" else [int(args.tolerance)]

    folder = Path(args.folder).resolve()
    gt_path = folder / "ground_truth.json"
    if not gt_path.exists():
        sys.exit(f"Missing {gt_path}")
    gt = json.loads(gt_path.read_text(encoding="utf-8"))

    logger = setup_logging(folder / "eval_logs")
    model, processor, config = load_model(args.model, logger)

    # --- single detection pass; cache predictions ---
    per_file = []        # (name, pred_set_excl_1, true_set_excl_1, total)
    docs_exact = docs_total = 0
    for name, true_starts in gt.items():
        pdf = folder / name
        if not pdf.exists():
            logger.error(f"Missing file listed in ground truth: {name}")
            continue
        total = len(PdfReader(str(pdf)).pages)
        boundaries, _ = detect_boundaries(
            pdf, total, model, processor, config, args.dpi, logger, classify=False
        )
        pred = {b.page for b in boundaries} - {1}
        true = set(true_starts) - {1}
        per_file.append((name, pred, true, total))

        # documents exactly recovered (both endpoints correct) — tolerance-independent
        true_sorted = sorted(set(true_starts) | {1})
        pred_sorted = sorted({b.page for b in boundaries} | {1})
        true_docs = set(zip(true_sorted, true_sorted[1:] + [total + 1]))
        pred_docs = set(zip(pred_sorted, pred_sorted[1:] + [total + 1]))
        docs_exact += len(true_docs & pred_docs)
        docs_total += len(true_docs)
        print(f"\n{name}\n  pred={sorted(pred)}\n  true={sorted(true)}")

    # --- score at each tolerance from the cached predictions ---
    results = {"docs_exact": docs_exact, "docs_total": docs_total, "by_tolerance": {}}
    for tol in tols:
        TP, FP, FN, P, R, F1, rows = score(per_file, tol)
        print(f"\n=== Boundary score (tolerance={tol}) ===")
        print(f"TP={TP} FP={FP} FN={FN}")
        print(f"Precision={P:.2%}  Recall={R:.2%}  F1={F1:.2%}")
        if tol == tols[0]:
            for name, pred, true, fp, fn in rows:
                if fp or fn:
                    print(f"  {name}: FP={fp} FN={fn}")
        results["by_tolerance"][str(tol)] = {
            "TP": TP, "FP": FP, "FN": FN,
            "precision": P, "recall": R, "f1": F1,
            "per_file": [{"file": n, "pred": p, "true": t, "fp": f, "fn": fnn}
                         for n, p, t, f, fnn in rows],
        }
    print(f"\nDocuments exactly recovered: {docs_exact}/{docs_total}")

    out = folder / "eval_results.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written: {out}")

if __name__ == "__main__":
    main()
