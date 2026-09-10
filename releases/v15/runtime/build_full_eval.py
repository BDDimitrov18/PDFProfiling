#!/usr/bin/env python3
"""Rebuild GT v3 without losing human rulings; optionally build expanded corpora.

Default: historical 20-file membership -> eval_full.
--include-all: all reference-labelled tests/ sources, including flat folders -> eval_expanded.
--corpus tests2 --include-all: separate evaluation -> eval_tests2.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader
from eval_data import DATA, corrected_reference, discover_originals, derive_starts, gap_runs, link_original
from production_state import atomic_json, file_hash


def detect_gap_runs(case_dir: Path, original_name: str):
    return gap_runs(case_dir / original_name)


def build(corpus: Path, output: Path, include_all=False):
    reference = json.loads((DATA / "eval_reference.json").read_text(encoding="utf-8"))
    files = discover_originals(corpus)
    if not include_all:
        files = [p for p in files if p.name in reference["strata"]]
        missing = set(reference["strata"]) - {p.name for p in files}
        if missing:
            raise ValueError(f"Missing baseline sources: {sorted(missing)}")
    names = [p.name for p in files]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate source basenames would collide in the flat evaluation folder")
    gt, masked, strata, metadata = {}, {}, {}, {}
    originals, unlabelled = [], []
    for original in files:
        starts = derive_starts(original)
        if not starts:
            if not include_all:
                raise ValueError(f"Missing reference splits: {original}")
            print(f"Skipping unlabelled source: {original}")
            unlabelled.append({"source": str(original.relative_to(corpus)), "sha256": file_hash(original),
                               "total_pages": len(PdfReader(str(original)).pages)})
            continue
        starts, unmask = corrected_reference(original, starts)
        name = original.name
        gt[name] = starts
        strata[name] = reference["strata"].get(name, "fresh")
        gaps = gap_runs(original)
        if gaps and not unmask:
            total = len(PdfReader(str(original)).pages)
            masked[name] = [[max(1, lo - 1), min(total, hi + 1)] for lo, hi in gaps]
        metadata[name] = {"source": str(original.relative_to(corpus)), "sha256": file_hash(original),
                          "total_pages": len(PdfReader(str(original)).pages)}
        originals.append(original)
    if not gt:
        raise ValueError("No reference-labelled PDFs found")
    gt_hash = hashlib.sha256(json.dumps(gt, sort_keys=True).encode()).hexdigest()
    if not include_all and gt_hash != reference["ground_truth_sha256"]:
        raise ValueError("Rebuilt labels differ from GT v3; review source splits/corrections before publishing")
    output.mkdir(parents=True, exist_ok=True)
    # Finish label validation before changing any existing generated data.
    for original in originals:
        link_original(original, output)
    for name, value in [("ground_truth", gt), ("masked", masked), ("strata", strata)]:
        atomic_json(output / (name + ".json"), value)
    atomic_json(output / "dataset.json", {"version": 1, "reference": reference["id"] if not include_all else "expanded",
                "ground_truth_sha256": gt_hash, "files": metadata, "unlabelled_sources": unlabelled,
                "corrections_sha256": file_hash(DATA / "boundary_corrections.json")})
    counts = Counter(strata.values())
    print(f"{output.name}: {len(gt)} files / {sum(x['total_pages'] for x in metadata.values())} pages; {dict(counts)}")
    print(f"Masked unresolved gaps: {masked}")
    return gt, masked, strata


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=".")
    ap.add_argument("--out", default=".", help="Parent of the generated evaluation folder")
    ap.add_argument("--corpus", default="tests", help="Corpus path relative to --base, or absolute")
    ap.add_argument("--include-all", action="store_true")
    args = ap.parse_args(argv)
    corpus = Path(args.base).resolve() / args.corpus
    if not args.include_all and args.corpus != "tests":
        ap.error("Use --include-all when evaluating another corpus")
    name = ("eval_expanded" if Path(args.corpus).name == "tests" else "eval_" + Path(args.corpus).name) if args.include_all else "eval_full"
    build(corpus, Path(args.out).resolve() / name, args.include_all)


if __name__ == "__main__":
    main()
