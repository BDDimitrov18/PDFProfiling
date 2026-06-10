#!/usr/bin/env python3
"""Build flat eval folders (dev + holdout) from the nested tests/ tree.

Boundary truth  : derived from the N_PDFsam_<stem>.pdf split files in each case.
Rotation truth  : derived from groundTruthHuman (page lists; tests/ pages are all 90 deg).

Produces, under --out:
    eval_dev/      <symlinks to originals> + ground_truth.json + rotation_truth.json
    eval_holdout/  <symlinks to originals> + ground_truth.json + rotation_truth.json

Usage:
    python build_eval_set.py --base . --out .
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

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
    """Start pages from <page>_PDFsam_<stem>.pdf (handles PDFsam_<page>_PDFsam_ too)."""
    stem = Path(original_name).stem
    tag = f"_PDFsam_{stem}"
    starts = set()
    for f in case_dir.iterdir():
        if f.suffix.lower() != ".pdf" or tag not in f.stem:
            continue
        prefix = f.stem.split(tag)[0]
        m = re.search(r"(\d+)$", prefix)
        if m:
            starts.add(int(m.group(1)))
    starts.add(1)
    return sorted(starts)


def load_rotation_truth(gt_human: Path) -> dict[str, dict[str, int]]:
    """Parse groundTruthHuman -> {filename: {page: 90}}. tests/ rotations are all 90 deg."""
    def expand(spec: str) -> set[int]:
        pages = set()
        for part in spec.replace("[", "").replace("]", "").split(","):
            part = part.strip()
            if not part:
                continue
            m = re.match(r"(\d+)\s*[-–]\s*(\d+)", part)
            if m:
                pages.update(range(int(m.group(1)), int(m.group(2)) + 1))
            else:
                m2 = re.match(r"(\d+)", part)
                if m2:
                    pages.add(int(m2.group(1)))
        return pages

    result: dict[str, dict[str, int]] = {}
    for line in gt_human.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"(.+\.pdf)\s+(.*)", line, re.IGNORECASE)
        if not m:
            continue
        fname = Path(m.group(1).strip()).name
        pages = expand(m.group(2).strip())
        if pages:
            result.setdefault(fname, {}).update({str(p): 90 for p in pages})
    return result


def originals_in_case(case_dir: Path) -> list[Path]:
    return sorted(f for f in case_dir.iterdir()
                  if f.suffix.lower() == ".pdf" and f.stem.upper().startswith("IMAGE_"))


def build_split(name: str, cases: list[str], tests_dir: Path, out_root: Path,
                rot_truth: dict[str, dict[str, int]]) -> None:
    out_dir = out_root / name
    out_dir.mkdir(parents=True, exist_ok=True)
    ground_truth: dict[str, list[int]] = {}
    rotation_truth: dict[str, dict[str, int]] = {}

    total_pages = 0
    for case_rel in cases:
        case_dir = tests_dir / case_rel
        if not case_dir.is_dir():
            print(f"  WARN: missing case {case_rel}")
            continue
        for orig in originals_in_case(case_dir):
            starts = parse_boundary_starts(case_dir, orig.name)
            if len(starts) <= 1:
                print(f"  WARN: no boundary splits for {case_rel}/{orig.name} — skipping")
                continue
            ground_truth[orig.name] = starts
            if orig.name in rot_truth:
                rotation_truth[orig.name] = rot_truth[orig.name]
            link = out_dir / orig.name
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(orig.resolve())
            from pypdf import PdfReader
            total_pages += len(PdfReader(str(orig)).pages)

    (out_dir / "ground_truth.json").write_text(
        json.dumps(ground_truth, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "rotation_truth.json").write_text(
        json.dumps(rotation_truth, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{name}: {len(ground_truth)} files, ~{total_pages} pages, "
          f"{len(rotation_truth)} files with rotation truth -> {out_dir}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=".", help="repo root containing tests/ and groundTruthHuman")
    ap.add_argument("--out", default=".", help="where to create eval_dev/ and eval_holdout/")
    args = ap.parse_args()

    base = Path(args.base).resolve()
    tests_dir = base / "tests"
    gt_human = base / "groundTruthHuman"
    out_root = Path(args.out).resolve()

    rot_truth = load_rotation_truth(gt_human)
    build_split("eval_dev", DEV_CASES, tests_dir, out_root, rot_truth)
    build_split("eval_holdout", HOLDOUT_CASES, tests_dir, out_root, rot_truth)


if __name__ == "__main__":
    main()
