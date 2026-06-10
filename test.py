#!/usr/bin/env python3
"""
Test harness for split.py boundary detection.

Folder structure expected under --tests-dir:
  tests/
    <project>/
      <case>/
        Image_<id>.pdf                   ← original PDF to split
        1_PdfSam_Image_<id>.pdf          ← ground truth: doc starting at page 1
        5_PdfSam_Image_<id>.pdf          ← ground truth: doc starting at page 5
        ...

Ground truth start pages are parsed from the numeric prefix before _PdfSam_.
Rotation ground truth is read from the /Rotate metadata of each page in the
split PDFs and compared against the original page rotations.

Results are appended to test_results.jsonl for longitudinal tracking.

Usage:
    python test.py tests/
    python test.py tests/ --dpi 120 --model Qwen/Qwen2.5-VL-7B-Instruct
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from split import load_model, detect_boundaries, DEFAULT_DPI, MODEL_PATH
from pypdf import PdfReader


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("split_test")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


# ---------------------------------------------------------------------------
# Ground truth: boundaries
# ---------------------------------------------------------------------------

def parse_ground_truth_boundaries(folder: Path, original_name: str) -> list[int]:
    """
    Find all  <page>_PDFsam_<original_stem>.pdf  files and return their
    start pages sorted ascending.

    Handles both simple  10_PDFsam_Image_*.pdf  and PDFsam's own re-export
    pattern  PDFsam_10_PDFsam_Image_*.pdf  by extracting the last integer
    before _PDFsam_<stem>.
    """
    stem = Path(original_name).stem
    tag = f"_PDFsam_{stem}"
    starts = []
    for f in folder.iterdir():
        if f.suffix.lower() != ".pdf":
            continue
        if tag not in f.stem:
            continue
        prefix = f.stem.split(f"_PDFsam_{stem}")[0]
        # extract trailing integer (handles plain "10" and "PDFsam_10")
        m = re.search(r"(\d+)$", prefix)
        if m:
            starts.append(int(m.group(1)))
    return sorted(starts)


# ---------------------------------------------------------------------------
# Ground truth: rotations
# ---------------------------------------------------------------------------

def get_pdf_page_rotations(pdf_path: Path) -> dict[int, int]:
    """Return {1-indexed page number: /Rotate degrees} for every page."""
    reader = PdfReader(str(pdf_path))
    result = {}
    for i, page in enumerate(reader.pages):
        rotate = page.get("/Rotate", 0)
        result[i + 1] = int(rotate) if rotate else 0
    return result


def parse_ground_truth_rotations(
    folder: Path, original_name: str, original_pdf: Path
) -> dict[int, int]:
    """
    For each *_PDFsam_* split file, compare the /Rotate of its pages to the
    corresponding pages in the original PDF.
    Returns {original_1indexed_page: degrees} for pages the human rotated.
    """
    orig_rotations = get_pdf_page_rotations(original_pdf)
    stem = Path(original_name).stem
    tag = f"_PDFsam_{stem}"
    human_rotations: dict[int, int] = {}

    for f in sorted(folder.iterdir()):
        if f.suffix.lower() != ".pdf" or tag not in f.stem:
            continue
        prefix = f.stem.split(f"_PDFsam_{stem}")[0]
        m = re.search(r"(\d+)$", prefix)
        if not m:
            continue
        start_page = int(m.group(1))

        split_rotations = get_pdf_page_rotations(f)
        for split_idx, split_rot in split_rotations.items():
            orig_page = start_page + split_idx - 1
            orig_rot  = orig_rotations.get(orig_page, 0)
            # Effective rotation = split rotation minus original rotation
            delta = (split_rot - orig_rot) % 360
            if delta != 0:
                human_rotations[orig_page] = delta

    return human_rotations


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def compare_boundaries(predicted: list[int], ground_truth: list[int]) -> dict:
    pred_set = set(predicted)
    gt_set   = set(ground_truth)
    tp = sorted(pred_set & gt_set)
    fp = sorted(pred_set - gt_set)
    fn = sorted(gt_set  - pred_set)
    return {"true_positives": tp, "false_positives": fp, "false_negatives": fn,
            "tp": len(tp), "fp": len(fp), "fn": len(fn)}


def compare_rotations(
    algo_rotations: dict[int, int],   # page → degrees our algo rotated
    human_rotations: dict[int, int],  # page → degrees human rotated
) -> dict:
    algo_pages  = set(algo_rotations)
    human_pages = set(human_rotations)
    tp = sorted(algo_pages & human_pages)
    fp = sorted(algo_pages - human_pages)   # we rotated, human didn't
    fn = sorted(human_pages - algo_pages)   # human rotated, we missed
    return {"true_positives": tp, "false_positives": fp, "false_negatives": fn,
            "tp": len(tp), "fp": len(fp), "fn": len(fn)}


def metrics(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return p, r, f


# ---------------------------------------------------------------------------
# Main test runner
# ---------------------------------------------------------------------------

def run_tests(tests_dir: Path, model_path: str, dpi: int, logger: logging.Logger) -> dict:
    model, processor, config = load_model(model_path, logger)

    # Re-enable logging after transformers/accelerate may have disabled it
    logging.disable(logging.NOTSET)
    logger.setLevel(logging.DEBUG)

    file_results = []
    b_tp = b_fp = b_fn = 0   # boundary totals
    r_tp = r_fp = r_fn = 0   # rotation totals

    def _has_originals(d: Path) -> list[Path]:
        return sorted(f for f in d.iterdir()
                      if f.suffix.lower() == ".pdf" and f.stem.upper().startswith("IMAGE_"))

    # Collect (project_name, case_dir) pairs; handles both nested and flat layouts
    cases: list[tuple[str, Path]] = []
    for project_dir in sorted(d for d in tests_dir.iterdir() if d.is_dir()):
        flat = _has_originals(project_dir)
        if flat:
            cases.append((project_dir.name, project_dir))
        else:
            for case_dir in sorted(d for d in project_dir.iterdir() if d.is_dir()):
                if _has_originals(case_dir):
                    cases.append((f"{project_dir.name}/{case_dir.name}", case_dir))

    for _label, case_dir in cases:
            originals = _has_originals(case_dir)
            if not originals:
                logger.warning(f"No Image_*.pdf in {case_dir.relative_to(tests_dir)}")
                continue

            for original in originals:
                gt_starts = parse_ground_truth_boundaries(case_dir, original.name)
                if not gt_starts:
                    logger.warning(f"No ground truth splits for {original.name} — skipping")
                    continue

                gt_rotations = parse_ground_truth_rotations(case_dir, original.name, original)

                logger.info("=" * 60)
                logger.info(f"File  : {original.relative_to(tests_dir)}")
                logger.info(f"Truth boundaries : {gt_starts}")
                logger.info(f"Truth rotations  : {gt_rotations}")

                try:
                    total_pages = len(PdfReader(str(original)).pages)
                    boundaries, algo_rotations = detect_boundaries(
                        original, total_pages, model, processor, config, dpi, logger,
                        classify=False,
                    )
                    pred_starts = [b.page for b in boundaries]
                except Exception as e:
                    logger.error(f"Detection failed: {e}", exc_info=True)
                    continue

                logger.info(f"Pred  boundaries : {pred_starts}")
                logger.info(f"Pred  rotations  : {algo_rotations}")

                # Boundary comparison
                bcmp = compare_boundaries(pred_starts, gt_starts)
                bp, br, bf = metrics(bcmp["tp"], bcmp["fp"], bcmp["fn"])
                b_tp += bcmp["tp"]; b_fp += bcmp["fp"]; b_fn += bcmp["fn"]

                # Rotation comparison
                rcmp = compare_rotations(algo_rotations, gt_rotations)
                rp, rr, rf = metrics(rcmp["tp"], rcmp["fp"], rcmp["fn"])
                r_tp += rcmp["tp"]; r_fp += rcmp["fp"]; r_fn += rcmp["fn"]

                logger.info(
                    f"Boundaries — TP={bcmp['tp']} FP={bcmp['fp']} FN={bcmp['fn']} | "
                    f"P={bp:.0%} R={br:.0%} F1={bf:.0%}"
                )
                if bcmp["false_positives"]:
                    logger.info(f"  ✗ Extra splits at   : {bcmp['false_positives']}")
                if bcmp["false_negatives"]:
                    logger.info(f"  ✗ Missed splits at  : {bcmp['false_negatives']}")

                logger.info(
                    f"Rotations  — TP={rcmp['tp']} FP={rcmp['fp']} FN={rcmp['fn']} | "
                    f"P={rp:.0%} R={rr:.0%} F1={rf:.0%}"
                )
                if rcmp["false_positives"]:
                    logger.info(f"  ✗ Over-rotated pages  : {rcmp['false_positives']}")
                if rcmp["false_negatives"]:
                    logger.info(f"  ✗ Missed rotations at : {rcmp['false_negatives']}")

                file_results.append({
                    "case":    _label,
                    "file":    original.name,
                    "boundaries": {
                        "ground_truth": gt_starts,
                        "predicted":    pred_starts,
                        **bcmp,
                        "precision": round(bp, 4),
                        "recall":    round(br, 4),
                        "f1":        round(bf, 4),
                    },
                    "rotations": {
                        "ground_truth": gt_rotations,
                        "predicted":    algo_rotations,
                        **rcmp,
                        "precision": round(rp, 4),
                        "recall":    round(rr, 4),
                        "f1":        round(rf, 4),
                    },
                })

    b_prec, b_rec, b_f1 = metrics(b_tp, b_fp, b_fn)
    r_prec, r_rec, r_f1 = metrics(r_tp, r_fp, r_fn)

    return {
        "timestamp":    datetime.now().isoformat(),
        "model":        model_path,
        "dpi":          dpi,
        "files_tested": len(file_results),
        "boundaries": {
            "total_tp": b_tp, "total_fp": b_fp, "total_fn": b_fn,
            "overall_precision": round(b_prec, 4),
            "overall_recall":    round(b_rec,  4),
            "overall_f1":        round(b_f1,   4),
        },
        "rotations": {
            "total_tp": r_tp, "total_fp": r_fp, "total_fn": r_fn,
            "overall_precision": round(r_prec, 4),
            "overall_recall":    round(r_rec,  4),
            "overall_f1":        round(r_f1,   4),
        },
        "files": file_results,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test split.py boundary detection against ground truth PdfSam splits",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("tests_dir", help="Root folder containing test cases")
    parser.add_argument("--dpi",    type=int, default=DEFAULT_DPI)
    parser.add_argument("--model",  default=MODEL_PATH)
    parser.add_argument("--output", default="test_results.jsonl",
                        help="File to append results to (one JSON object per run)")
    args = parser.parse_args()

    tests_dir = Path(args.tests_dir).resolve()
    if not tests_dir.is_dir():
        print(f"Error: '{tests_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    logger = setup_logger()
    logger.info("Split.py Test Harness")
    logger.info(f"Tests dir : {tests_dir}")
    logger.info(f"Model     : {args.model}")
    logger.info(f"DPI       : {args.dpi}")

    results = run_tests(tests_dir, args.model, args.dpi, logger)

    b = results["boundaries"]
    r = results["rotations"]

    logger.info("")
    logger.info("=" * 60)
    logger.info("OVERALL RESULTS")
    logger.info(f"  Files tested : {results['files_tested']}")
    logger.info("")
    logger.info("  BOUNDARY DETECTION")
    logger.info(f"    True  positives : {b['total_tp']}")
    logger.info(f"    False positives : {b['total_fp']}  (extra splits)")
    logger.info(f"    False negatives : {b['total_fn']}  (missed splits)")
    logger.info(f"    Precision : {b['overall_precision']:.1%}")
    logger.info(f"    Recall    : {b['overall_recall']:.1%}")
    logger.info(f"    F1 score  : {b['overall_f1']:.1%}")
    logger.info("")
    logger.info("  PAGE ROTATION")
    logger.info(f"    True  positives : {r['total_tp']}")
    logger.info(f"    False positives : {r['total_fp']}  (rotated when not needed)")
    logger.info(f"    False negatives : {r['total_fn']}  (missed rotations)")
    logger.info(f"    Precision : {r['overall_precision']:.1%}")
    logger.info(f"    Recall    : {r['overall_recall']:.1%}")
    logger.info(f"    F1 score  : {r['overall_f1']:.1%}")
    logger.info("=" * 60)

    output_path = Path(args.output)
    with open(output_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(results, ensure_ascii=False) + "\n")
    logger.info(f"Results appended to {output_path}")


if __name__ == "__main__":
    main()
