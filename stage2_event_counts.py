"""stage2_event_counts.py — post-hoc per-stratum gate-event counts from a detection log.
NO pipeline interaction (pure log analysis). Counts, per stratum (masked pages excluded):
  titled_suppressed   — [TITLE-GATE] ... SUPPRESSED
  titled_capped       — [TITLE-GATE] ... one-of-two (1/2 accept, conf capped 0.60)
  titled_reloc        — [TITLE-GATE-RELOC] fires
  titled_reloc_dup    — RELOC whose target page already carries a boundary (≥2 'doc starts at
                        page wp' in the file) → silently drops the claim (FN19@142044854 class)
  window_requery      — [WINDOW-REQUERY] (#2 out-of-window re-query)
  onelite_would_fire  — end-events with signal∈{signature_block,table_end} landing on n+1
                        (the cases the reverted #1-lite would have gated)

Usage: python3 stage2_event_counts.py <log> [--gt ... --strata ... --masked ...]
"""
import argparse
import json
import re
from collections import defaultdict

FNAME = re.compile(r"^(Image_\w+\.pdf)$")
CHECKING = re.compile(r"Checking page (\d+)")
SUPPRESSED = re.compile(r"\[TITLE-GATE\] titled_id_header at p(\d+) SUPPRESSED")
CAPPED = re.compile(r"\[TITLE-GATE\] p(\d+) one-of-two")
RELOC = re.compile(r"\[TITLE-GATE-RELOC\] grounded title on p(\d+)")
REQUERY = re.compile(r"\[WINDOW-REQUERY\]")
DOCSTART = re.compile(r"doc starts at page (\d+)")
ENDEV = re.compile(r"p(\d+): end=True, signal=(signature_block|table_end), signal_on_page=(\d+)")


def masked_pages(ranges):
    out = set()
    for lo, hi in ranges or []:
        out.update(range(lo, hi + 1))
    return out


def parse(logpath):
    """Return {file: {events...}} accumulating until a filename marker closes the section.
    Iteration-aware: tracks the current 'Checking page N' iteration so a duplicate-relocation
    is defined as a RELOC to wp where wp was first emitted as a doc-start in an EARLIER iteration
    (the active doc's start) — NOT merely re-derived within the same iteration (e.g. the trivial
    page-1/page-2 boundary)."""
    files = {}
    cur = _fresh()
    it = 0
    for line in open(logpath, encoding="utf-8", errors="replace"):
        m = CHECKING.search(line)
        if m:
            it = int(m.group(1))
        m = DOCSTART.search(line)
        if m:
            p = int(m.group(1))
            if p not in cur["docstart_first_iter"]:
                cur["docstart_first_iter"][p] = it
        m = SUPPRESSED.search(line)
        if m:
            cur["suppressed"].append(int(m.group(1)))
        m = CAPPED.search(line)
        if m:
            cur["capped"].append(int(m.group(1)))
        m = RELOC.search(line)
        if m:
            wp = int(m.group(1))
            prior = cur["docstart_first_iter"].get(wp)
            # DUPLICATE-RELOCATION (operational def, documented for verifier): the target page was
            # first opened as a doc-start by the IMMEDIATELY PRECEDING iteration (prior == it-1) —
            # i.e. relocating backward onto the freshly-opened adjacent document, abandoning the
            # forward true start (the FN19@142044854 pattern). This EXCLUDES the benign case where
            # the target is a persistent boundary re-derived across non-adjacent iterations (e.g.
            # the trivial page-1/page-2 boundary). Calibrated: dev Stage 1 → exactly 1 (p18).
            cur["reloc"].append((wp, it, prior is not None and prior == it - 1))
        if REQUERY.search(line):
            cur["requery"] += 1
        m = ENDEV.search(line)
        if m and int(m.group(3)) == int(m.group(1)) + 1:
            cur["onelite"].append(int(m.group(1)))
        fm = FNAME.match(line.strip())
        if fm:
            files[fm.group(1)] = cur
            cur = _fresh()
            it = 0
    return files


def _fresh():
    return {"docstart_first_iter": {}, "suppressed": [], "capped": [],
            "reloc": [], "requery": 0, "onelite": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--gt", default="eval_full/ground_truth.json")
    ap.add_argument("--strata", default="eval_full/strata.json")
    ap.add_argument("--masked", default="eval_full/masked.json")
    args = ap.parse_args()
    strata = json.load(open(args.strata, encoding="utf-8"))
    masked = json.load(open(args.masked, encoding="utf-8"))
    files = parse(args.log)

    agg = defaultdict(lambda: defaultdict(int))
    for f, d in files.items():
        s = strata.get(f, "?")
        mp = masked_pages(masked.get(f))
        agg[s]["titled_suppressed"] += sum(1 for p in d["suppressed"] if p not in mp)
        agg[s]["titled_capped"] += sum(1 for p in d["capped"] if p not in mp)
        agg[s]["titled_reloc"] += sum(1 for wp, _, _ in d["reloc"] if wp not in mp)
        agg[s]["titled_reloc_dup"] += sum(1 for wp, _, dup in d["reloc"] if wp not in mp and dup)
        agg[s]["window_requery"] += d["requery"]
        agg[s]["onelite_would_fire"] += sum(1 for p in d["onelite"] if p not in mp)

    cols = ["titled_suppressed", "titled_capped", "titled_reloc", "titled_reloc_dup",
            "window_requery", "onelite_would_fire"]
    print(f"{'stratum':9} " + " ".join(f"{c:18}" for c in cols))
    total = defaultdict(int)
    for s in ("dev", "holdout", "fresh"):
        row = agg.get(s, {})
        print(f"{s:9} " + " ".join(f"{row.get(c,0):<18}" for c in cols))
        for c in cols:
            total[c] += row.get(c, 0)
    print(f"{'ALL':9} " + " ".join(f"{total[c]:<18}" for c in cols))


if __name__ == "__main__":
    main()
