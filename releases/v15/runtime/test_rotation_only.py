#!/usr/bin/env python3
"""Rotation-only test — skips boundary detection, just checks per-page rotation."""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from split import load_model, DEFAULT_DPI, MODEL_PATH, _infer, _parse_json
from rotation import query_rotation, smooth_rotation_log
from pypdf import PdfReader
from pdf2image import convert_from_path

SSH_CMD = None  # running locally on pod


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("rot_test")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


def get_pdf_rotations(pdf_path: Path) -> dict[int, int]:
    reader = PdfReader(str(pdf_path))
    return {i + 1: int(p.get("/Rotate") or 0) for i, p in enumerate(reader.pages)}


def parse_ground_truth_rotations(folder: Path, original_name: str, original_pdf: Path) -> dict[int, int]:
    orig_rotations = get_pdf_rotations(original_pdf)
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
        for i, (_, split_rot) in enumerate(get_pdf_rotations(f).items()):
            orig_page = start_page + i
            orig_rot = orig_rotations.get(orig_page, 0)
            delta = (split_rot - orig_rot) % 360
            if delta != 0:
                human_rotations[orig_page] = delta
    return human_rotations


def metrics(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return p, r, f


def run(tests_dirs: list[Path], model_path: str, dpi: int, logger: logging.Logger):
    model, processor, config = load_model(model_path, logger)
    logging.disable(logging.NOTSET)
    logger.setLevel(logging.DEBUG)

    r_tp = r_fp = r_fn = 0

    def _has_originals(d: Path):
        return sorted(f for f in d.iterdir()
                      if f.suffix.lower() == ".pdf" and f.stem.upper().startswith("IMAGE_"))

    cases: list[tuple[str, Path]] = []
    for tests_dir in tests_dirs:
        for project_dir in sorted(d for d in tests_dir.iterdir() if d.is_dir()):
            flat = _has_originals(project_dir)
            if flat:
                cases.append((project_dir.name, project_dir))
            else:
                for case_dir in sorted(d for d in project_dir.iterdir() if d.is_dir()):
                    if _has_originals(case_dir):
                        cases.append((f"{project_dir.name}/{case_dir.name}", case_dir))

    for label, case_dir in cases:
        for original in _has_originals(case_dir):
            gt_rotations = parse_ground_truth_rotations(case_dir, original.name, original)

            logger.info("=" * 60)
            logger.info(f"File : {label}/{original.name}")
            logger.info(f"Truth rotations: {gt_rotations}")

            try:
                total_pages = len(PdfReader(str(original)).pages)
                images = convert_from_path(str(original), dpi=dpi)
            except Exception as e:
                logger.error(f"Failed to load {original.name}: {e}")
                continue

            algo_rotations: dict[int, int] = {}
            for page_num, img in enumerate(images, start=1):
                deg = query_rotation(
                    img, page_num, model, processor, config, logger,
                    infer_fn=_infer, parse_fn=_parse_json,
                )
                if deg != 0:
                    algo_rotations[page_num] = deg

            algo_rotations = smooth_rotation_log(algo_rotations, logger)
            logger.info(f"Pred  rotations: {algo_rotations}")

            algo_pages  = set(algo_rotations)
            human_pages = set(gt_rotations)
            tp = sorted(algo_pages & human_pages)
            fp = sorted(algo_pages - human_pages)
            fn = sorted(human_pages - algo_pages)
            rp, rr, rf = metrics(len(tp), len(fp), len(fn))
            r_tp += len(tp); r_fp += len(fp); r_fn += len(fn)

            logger.info(f"Rotations — TP={len(tp)} FP={len(fp)} FN={len(fn)} | P={rp:.0%} R={rr:.0%} F1={rf:.0%}")
            if fp: logger.info(f"  Over-rotated : {fp}")
            if fn: logger.info(f"  Missed       : {fn}")

    rp, rr, rf = metrics(r_tp, r_fp, r_fn)
    logger.info("=" * 60)
    logger.info("OVERALL ROTATION RESULTS")
    logger.info(f"  TP={r_tp}  FP={r_fp}  FN={r_fn}")
    logger.info(f"  Precision : {rp:.1%}")
    logger.info(f"  Recall    : {rr:.1%}")
    logger.info(f"  F1        : {rf:.1%}")
    logger.info("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("tests_dirs", nargs="+")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    parser.add_argument("--model", default=MODEL_PATH)
    args = parser.parse_args()

    logger = setup_logger()
    run([Path(d) for d in args.tests_dirs], args.model, args.dpi, logger)
