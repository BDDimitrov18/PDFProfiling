#!/usr/bin/env python3
"""FREE TP-side attribution for titled_id_header (no GPU). Parses the saved candidate
detection log + GT/strata/masked. For each TP boundary, collects the full set of signals
that resolved to it (via the per-event 'End at page X -> doc starts at page Y (...signal=S)'
lines + [START-DETECT] lines). Reports, per stratum: titled-attributed TPs, of which
unique-titled (only titled resolves there) vs co-detected (another mechanism also did)."""
import json, re
from pathlib import Path
from collections import defaultdict

gt = json.load(open("/tmp/ef_ground_truth.json"))
strata = json.load(open("/tmp/ef_strata.json"))
masked = json.load(open("/tmp/ef_masked.json"))

START_ON_NEXT = {"titled_id_header", "fresh_letterhead", "header_block_reset",
                 "appendix_heading", "blank_form", "page_number_reset", "stamp_change"}

def masked_pages(f):
    s = set()
    for lo, hi in masked.get(f, []):
        s.update(range(lo, hi + 1))
    return s

DOC_START = re.compile(r"doc starts at page (\d+) \(conf=\d+%, signal=(\w+)\)")
STARTDET = re.compile(r"\[START-DETECT\] p(\d+)")
PRED = re.compile(r"pred=\[([^\]]*)\]")
FNAME = re.compile(r"^(Image_\w+\.pdf)$")

# Segment: detection events accumulate until a filename marker closes a file section.
events = defaultdict(list)   # file -> list of (boundary_page, signal)
preds = {}
buf = []
lines = Path("/tmp/cand.log").read_text(errors="replace").splitlines()
for i, line in enumerate(lines):
    m = DOC_START.search(line)
    if m:
        buf.append((int(m.group(1)), m.group(2))); continue
    m = STARTDET.search(line)
    if m:
        buf.append((int(m.group(1)), "start_only_heading")); continue
    fm = FNAME.match(line.strip())
    if fm:
        fname = fm.group(1)
        events[fname] = buf
        buf = []
        # pred is on a following line
        for j in range(i, min(i + 4, len(lines))):
            pm = PRED.search(lines[j])
            if pm:
                preds[fname] = set(int(x) for x in pm.group(1).split(",") if x.strip())
                break

# Per-file: classify each TP boundary by its signal set.
stat = {s: {"titled_tp": 0, "unique": 0, "codet": 0, "titled_fp": 0,
            "unique_list": [], "codet_list": []} for s in ("dev", "holdout", "fresh")}
for f in gt:
    s = strata[f]
    mp = masked_pages(f)
    true = (set(gt[f]) - {1}) - mp
    pred = (preds.get(f, set()) - {1}) - mp
    sig_at = defaultdict(set)
    for B, sig in events.get(f, []):
        sig_at[B].add(sig)
    # TP boundaries attributed (partly) to titled
    for B in sorted(pred & true):
        sigs = sig_at.get(B, set())
        if "titled_id_header" in sigs:
            stat[s]["titled_tp"] += 1
            others = sigs - {"titled_id_header"}
            if others:
                stat[s]["codet"] += 1
                stat[s]["codet_list"].append(f"{f[-10:-4]}:p{B}({'+'.join(sorted(others))})")
            else:
                stat[s]["unique"] += 1
                stat[s]["unique_list"].append(f"{f[-10:-4]}:p{B}")
    # titled-attributed FPs
    for B in sorted(pred - true):
        if "titled_id_header" in sig_at.get(B, set()):
            stat[s]["titled_fp"] += 1

print("=" * 78)
print("TITLED_ID_HEADER TP-SIDE ATTRIBUTION (candidate / Fix9-only, full-tests log)")
print("=" * 78)
print(f"{'stratum':9} {'titledTP':9} {'unique':7} {'codet':6} {'titledFP':9}")
for s in ("dev", "holdout", "fresh"):
    d = stat[s]
    print(f"{s:9} {d['titled_tp']:<9} {d['unique']:<7} {d['codet']:<6} {d['titled_fp']:<9}")
print()
for s in ("dev", "holdout", "fresh"):
    d = stat[s]
    print(f"[{s}] UNIQUE-titled TPs ({d['unique']}): {', '.join(d['unique_list']) or 'none'}")
    print(f"[{s}] co-detected TPs ({d['codet']}): {', '.join(d['codet_list']) or 'none'}")
