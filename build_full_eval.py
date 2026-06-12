#!/usr/bin/env python3
"""Build eval_full/ — ALL tests/ originals (that have PDFsam splits) with the fixed
coverage-based GT, gap MASKING (±1 page) for unattested gap files, and dev/holdout/fresh
strata. Overnight: gaps are masked (scored neither way), NOT attested.

Writes under --out/eval_full/: symlinks to originals, ground_truth.json, masked.json
({file: [[lo,hi],...]} inclusive page ranges to exclude from scoring), strata.json
({file: dev|holdout|fresh}).
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from pypdf import PdfReader
from build_eval_set import parse_boundary_starts, originals_in_case, DEV_CASES, HOLDOUT_CASES

# dev gap files are human-attested FINAL (boundary 10 / 4) — do NOT mask them.
ATTESTED = {"Image_00112022025163444215.pdf", "Image_00112032025084303475.pdf"}


def detect_gap_runs(case_dir: Path, original_name: str):
    """Return list of (lo,hi) inclusive runs of uncovered internal pages (excl page 1)."""
    stem = Path(original_name).stem
    tag = f"_PDFsam_{stem}"
    total = len(PdfReader(str(case_dir / original_name)).pages)
    covered: set[int] = set()
    for f in case_dir.iterdir():
        if f.suffix.lower() != ".pdf" or tag not in f.stem:
            continue
        m = re.search(r"(\d+)$", f.stem.split(tag)[0])
        if not m:
            continue
        s = int(m.group(1)); n = len(PdfReader(str(f)).pages)
        covered.update(range(s, s + n))
    gaps = sorted(p for p in range(1, total + 1) if p not in covered and p != 1)
    runs = []
    for p in gaps:
        if runs and p == runs[-1][1] + 1:
            runs[-1][1] = p
        else:
            runs.append([p, p])
    return [(lo, hi) for lo, hi in runs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=".")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()
    base = Path(args.base).resolve(); tests = base / "tests"
    out = Path(args.out).resolve() / "eval_full"
    out.mkdir(parents=True, exist_ok=True)

    dev_files, holdout_files = set(), set()
    for c in DEV_CASES:
        for o in originals_in_case(tests / c):
            dev_files.add(o.name)
    for c in HOLDOUT_CASES:
        for o in originals_in_case(tests / c):
            holdout_files.add(o.name)

    gt, masked, strata = {}, {}, {}
    total_pages = 0
    for proj in sorted(d for d in tests.iterdir() if d.is_dir()):
        for case in sorted(d for d in proj.iterdir() if d.is_dir()):
            for orig in originals_in_case(case):
                starts = parse_boundary_starts(case, orig.name)
                if len(starts) <= 1:
                    continue
                gt[orig.name] = starts
                strata[orig.name] = ("dev" if orig.name in dev_files
                                     else "holdout" if orig.name in holdout_files else "fresh")
                runs = detect_gap_runs(case, orig.name)
                if runs and orig.name not in ATTESTED:
                    masked[orig.name] = [[lo - 1, hi + 1] for lo, hi in runs]  # ±1, inclusive
                link = out / orig.name
                if link.exists() or link.is_symlink():
                    link.unlink()
                link.symlink_to(orig.resolve())
                total_pages += len(PdfReader(str(orig)).pages)

    (out / "ground_truth.json").write_text(json.dumps(gt, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "masked.json").write_text(json.dumps(masked, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "strata.json").write_text(json.dumps(strata, indent=2, ensure_ascii=False), encoding="utf-8")

    from collections import Counter
    cnt = Counter(strata.values())
    print(f"eval_full: {len(gt)} files (~{total_pages} pages) -> {out}")
    print(f"  strata: dev={cnt['dev']} holdout={cnt['holdout']} fresh={cnt['fresh']}")
    print(f"  masked (unattested gaps, ±1): {masked}")


if __name__ == "__main__":
    main()
