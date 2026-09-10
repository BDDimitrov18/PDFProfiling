"""Source discovery, reference coverage and persistent human label corrections."""
from __future__ import annotations

import json
from pathlib import Path
import re
from pypdf import PdfReader
from production_state import file_hash

DATA = Path(__file__).parent / "data"


def discover_originals(root: Path) -> list[Path]:
    if not root.is_dir():
        raise ValueError(f"Missing corpus: {root}")
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"
                  and p.stem.upper().startswith("IMAGE_")
                  and not any(x == "split" or x.startswith(".") for x in p.relative_to(root).parts))


def reference_coverage(original: Path):
    total = len(PdfReader(str(original)).pages)
    if total == 0:
        raise ValueError(f"Empty source: {original}")
    tag = f"_PDFsam_{original.stem}"
    starts, covered = set(), set()
    for piece in sorted(original.parent.iterdir()):
        if piece.suffix.lower() != ".pdf" or tag not in piece.stem:
            continue
        match = re.search(r"(\d+)$", piece.stem.split(tag)[0])
        if not match:
            continue
        start = int(match.group(1))
        length = len(PdfReader(str(piece)).pages)
        if length < 1 or start < 1 or start + length - 1 > total:
            raise ValueError(f"Reference split lies outside its source: {piece}")
        starts.add(start)
        covered.update(range(start, start + length))
    return total, starts, covered


def derive_starts(original: Path) -> list[int]:
    total, starts, covered = reference_coverage(original)
    if not starts:
        return []  # An unlabelled source is not a one-document reference.
    for p in range(1, total + 1):
        if p not in covered and (p == 1 or p - 1 in covered):
            starts.add(p)
    return sorted(starts | {1})


def gap_runs(original: Path):
    total, _, covered = reference_coverage(original)
    runs = []
    for p in range(2, total + 1):
        if p in covered:
            continue
        if runs and p == runs[-1][1] + 1:
            runs[-1][1] = p
        else:
            runs.append([p, p])
    return runs


def corrected_reference(original: Path, starts: list[int], corrections=None):
    if corrections is None:
        corrections = json.loads((DATA / "boundary_corrections.json").read_text(encoding="utf-8"))["files"]
    rule = corrections.get(original.name)
    if not rule:
        return starts, False
    if file_hash(original) != rule["source_sha256"]:
        raise ValueError(f"Source changed; existing human ruling needs review: {original.name}")
    starts = sorted((set(starts) | set(rule["add"])) - set(rule["remove"]))
    total = len(PdfReader(str(original)).pages)
    if not starts or starts[0] != 1 or any(type(p) is not int or not 1 <= p <= total for p in starts):
        raise ValueError(f"Invalid corrected boundaries: {original.name}")
    return starts, rule.get("unmask_gaps", False)


def link_original(original: Path, output: Path):
    link = output / original.name
    if link.is_symlink():
        link.unlink()
    elif link.exists():
        raise ValueError(f"Refusing to replace a regular file with an evaluation symlink: {link}")
    link.symlink_to(original.resolve())
