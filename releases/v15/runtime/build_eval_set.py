#!/usr/bin/env python3
"""Build flat eval folders (dev + holdout) from the nested tests/ tree.

Boundary truth  : derived from the N_PDFsam_<stem>.pdf split files in each case.
Rotation truth  : derived from per-page /Rotate deltas in the PDFsam reference files.

Produces, under --out:
    eval_dev/      <symlinks to originals> + ground_truth.json + rotation_truth.json
    eval_holdout/  <symlinks to originals> + ground_truth.json + rotation_truth.json

Usage:
    python build_eval_set.py --base . --out .
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from eval_data import derive_starts, corrected_reference, link_original
from production_state import atomic_json

# Case paths (relative to tests/) selected for each split. Both PDFs in a case
# are included if the case holds more than one original.
DEV_CASES = [
    "РС-31-2017/2",   # many single-page docs, same-issuer consecutive
    "РС-31-2017/4",   # short same-issuer consecutive run
    "РС-31-2017/6",   # tiny, dense boundaries
    "РС-31-2017/7",   # rotation runs (both PDFs: pages 10-19 and 6-7)
    "РС-32-2017/1",   # heaviest single-page runs (21) + rotation (9, 37)
    "РС-33-2017/3",   # one long doc (13 pages) + rotation (14)
    "РС-33-2017/4",   # tiny
    "РС-33-2017/7",   # one long doc (13 pages)
]
HOLDOUT_CASES = [
    "РС-31-2017/8",
    "РС-33-2017/5",
    "РС-33-2017/6",
]


def parse_boundary_starts(case_dir: Path, original_name: str) -> list[int]:
    """Coverage-derived starts. Human corrections are applied by the builders."""
    return derive_starts(case_dir / original_name)


def derive_rotation_truth(case_dir: Path, original_name: str) -> dict[str, int]:
    """Rotation truth from the split PDFs' /Rotate metadata (the human's actual
    per-page correction), mapped to original 1-indexed pages.

    A split page's /Rotate is a CLOCKWISE display value; this codebase's rotation
    convention is COUNTER-CLOCKWISE to correct, so ccw = (360 - rotate) % 360.
    Pages with /Rotate == original /Rotate (delta 0) are upright and omitted.
    This carries the degree directly and is self-consistent (an upright page that
    the human left at /Rotate=0 is correctly NOT marked rotated).
    """
    from pypdf import PdfReader
    orig = PdfReader(str(case_dir / original_name))
    orig_rot = {i + 1: int(p.get("/Rotate") or 0) for i, p in enumerate(orig.pages)}

    stem = Path(original_name).stem
    tag = f"_PDFsam_{stem}"
    truth: dict[str, int] = {}
    for f in sorted(case_dir.iterdir()):
        if f.suffix.lower() != ".pdf" or tag not in f.stem:
            continue
        m = re.search(r"(\d+)$", f.stem.split(tag)[0])
        if not m:
            continue
        start = int(m.group(1))
        split = PdfReader(str(f))
        for i, page in enumerate(split.pages):
            orig_page = start + i
            split_rot = int(page.get("/Rotate") or 0)
            delta = (split_rot - orig_rot.get(orig_page, 0)) % 360
            if delta != 0:
                truth[str(orig_page)] = (360 - delta) % 360  # CW delta -> CCW-to-correct
    return truth


def originals_in_case(case_dir: Path) -> list[Path]:
    return sorted(f for f in case_dir.iterdir()
                  if f.suffix.lower() == ".pdf" and f.stem.upper().startswith("IMAGE_"))


def build_split(name: str, cases: list[str], tests_dir: Path, out_root: Path) -> None:
    out_dir = out_root / name
    out_dir.mkdir(parents=True, exist_ok=True)
    ground_truth: dict[str, list[int]] = {}
    rotation_truth: dict[str, dict[str, int]] = {}

    total_pages = 0
    for case_rel in cases:
        case_dir = tests_dir / case_rel
        if not case_dir.is_dir():
            raise ValueError(f"Missing required evaluation case: {case_rel}")
        for orig in originals_in_case(case_dir):
            starts = parse_boundary_starts(case_dir, orig.name)
            if not starts:
                print(f"  WARN: no boundary splits for {case_rel}/{orig.name} — skipping")
                continue
            starts, _ = corrected_reference(orig, starts)
            ground_truth[orig.name] = starts
            rot = derive_rotation_truth(case_dir, orig.name)
            rotation_truth[orig.name] = rot
            link_original(orig, out_dir)
            from pypdf import PdfReader
            total_pages += len(PdfReader(str(orig)).pages)

    atomic_json(out_dir / "ground_truth.json", ground_truth)
    atomic_json(out_dir / "rotation_truth.json", rotation_truth)

    print(f"{name}: {len(ground_truth)} files, ~{total_pages} pages, "
          f"{len(rotation_truth)} files with rotation truth -> {out_dir}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=".", help="repo root containing tests/ and groundTruthHuman")
    ap.add_argument("--out", default=".", help="where to create eval_dev/ and eval_holdout/")
    args = ap.parse_args()

    base = Path(args.base).resolve()
    tests_dir = base / "tests"
    out_root = Path(args.out).resolve()

    build_split("eval_dev", DEV_CASES, tests_dir, out_root)
    build_split("eval_holdout", HOLDOUT_CASES, tests_dir, out_root)


if __name__ == "__main__":
    main()
