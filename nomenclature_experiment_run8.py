"""nomenclature_experiment_run8.py — DATA REPORT ONLY, CPU-only, pod-less.

Cross-architecture counterpart of nomenclature_experiment.py, run over the run8 referee log
(run8.py is BYTE-FROZEN — referee + fingerprint roles; any mechanism this motivates is a
forward-port into split.py, NEVER a run8 edit). run8 uses a different signal vocabulary: it
logs `[next_page_heading='<heading of the next page>']` on confirmed boundaries (the analog of
split's titled title), plus header_block_reset / appendix_heading start-signals.

Parses every next_page_heading string + every header_block_reset / appendix_heading event
(file, page, verdict), labels each vs current GT (TP / FP, plus run8-FNs whose page carries a
logged heading), runs nomenclature_match over the headings, and reports per stratum in the same
format as nomenclature_experiment_stage2.txt.

Usage: python3 nomenclature_experiment_run8.py logs/run8_stage3.log
        [--gt eval_full/ground_truth.json --strata ... --masked ... --xls ...]
"""
import argparse
import json
import re
import statistics
from collections import defaultdict

import nomenclature_match as nm

FNAME = re.compile(r"^(Image_\w+\.pdf)$")
NPH = re.compile(r"next_page_heading='(.*)'\]")
DOCSTART = re.compile(r"doc starts at page (\d+) \(conf=\d+%, signal=(\w+)\)")
STARTSIG = re.compile(r"p(\d+): end=True, signal=(header_block_reset|appendix_heading)")
PRED = re.compile(r"pred=\[([^\]]*)\]")


def masked_pages(ranges):
    out = set()
    for lo, hi in ranges or []:
        out.update(range(lo, hi + 1))
    return out


def parse(logpath):
    """Per file: list of boundary events {page, heading, signal} + the file's pred set.
    A next_page_heading is stashed and attached to the doc-start line that follows it (same
    confirmed boundary). header_block_reset/appendix_heading start-signals are captured too."""
    files, preds = {}, {}
    ev, pending, startsig = [], None, None
    lines = open(logpath, encoding="utf-8", errors="replace").read().splitlines()
    for i, line in enumerate(lines):
        m = NPH.search(line)
        if m:
            pending = m.group(1)
        m = STARTSIG.search(line)
        if m:
            startsig = (int(m.group(1)), m.group(2))
        m = DOCSTART.search(line)
        if m:
            page, signal = int(m.group(1)), m.group(2)
            ev.append({"page": page, "heading": pending, "signal": signal})
            pending = None
            startsig = None
        fm = FNAME.match(line.strip())
        if fm:
            files[fm.group(1)] = ev
            for j in range(i, min(i + 4, len(lines))):
                pm = PRED.search(lines[j])
                if pm:
                    preds[fm.group(1)] = set(int(x) for x in pm.group(1).split(",") if x.strip())
                    break
            ev, pending, startsig = [], None, None
    return files, preds


def dist(vals):
    if not vals:
        return "n=0"
    return (f"n={len(vals)} mean={statistics.mean(vals):.3f} median={statistics.median(vals):.3f} "
            f"min={min(vals):.3f} max={max(vals):.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--gt", default="eval_full/ground_truth.json")
    ap.add_argument("--strata", default="eval_full/strata.json")
    ap.add_argument("--masked", default="eval_full/masked.json")
    ap.add_argument("--xls", default=nm.XLS_DEFAULT)
    args = ap.parse_args()
    gt = json.load(open(args.gt, encoding="utf-8"))
    strata = json.load(open(args.strata, encoding="utf-8"))
    masked = json.load(open(args.masked, encoding="utf-8"))
    entries = nm.load_nomenclature(args.xls)
    files, preds = parse(args.log)

    print("=" * 90)
    print("NOMENCLATURE EXPERIMENT — RUN8 REFEREE LOG (cross-architecture) — DATA REPORT ONLY")
    print("run8.py is byte-frozen; any motivated mechanism is a forward-port into split.py, never a run8 edit.")
    print(f"log={args.log}  nomenclature={len(entries)} entries")
    print("=" * 90)

    for stratum in ("dev", "holdout", "fresh"):
        sfiles = [f for f in gt if strata.get(f) == stratum]
        rows = []  # (file, page, heading, signal, label, best, scores, band)
        fn_with_heading = []
        for f in sfiles:
            mp = masked_pages(masked.get(f))
            true = set(gt[f]) - {1} - mp
            pred = preds.get(f, set()) - {1} - mp
            evs = files.get(f, [])
            heading_at = {e["page"]: e["heading"] for e in evs if e["heading"]}
            for e in evs:
                page = e["page"]
                if page in mp or page == 1:
                    continue
                lbl = "TP" if page in true else "FP"
                if e["heading"]:
                    best, scores, band = nm.match_title(e["heading"], entries)
                else:
                    best, scores, band = None, {"exact": 0, "containment": 0, "trigram": 0.0, "token_set": 0.0}, "NONE"
                rows.append((f, page, e["heading"], e["signal"], lbl, best, scores, band))
            # run8-FNs whose page carries a logged heading
            for p in sorted(true - pred):
                if p in heading_at:
                    h = heading_at[p]
                    best, scores, band = nm.match_title(h, entries)
                    fn_with_heading.append((f, p, h, best, scores, band))
        if not rows and not fn_with_heading:
            continue
        print(f"\n{'#'*28} STRATUM: {stratum} ({len(rows)} heading/start events) {'#'*28}")

        for lbl in ("TP", "FP"):
            # score distributions over heading-bearing events only
            tri = [s["trigram"] for (_, _, h, _, l, _, s, _) in rows if l == lbl and h]
            tok = [s["token_set"] for (_, _, h, _, l, _, s, _) in rows if l == lbl and h]
            bands = defaultdict(int)
            for (_, _, h, _, l, _, _, b) in rows:
                if l == lbl and h:
                    bands[b] += 1
            print(f"\n[{stratum}/{lbl}] (heading-bearing) trigram {dist(tri)}")
            print(f"[{stratum}/{lbl}] (heading-bearing) token_set {dist(tok)}")
            print(f"[{stratum}/{lbl}] bands {dict(bands)}")
            sigs = defaultdict(int)
            for (_, _, _, sig, l, _, _, _) in rows:
                if l == lbl:
                    sigs[sig] += 1
            print(f"[{stratum}/{lbl}] signal mix (all events incl. headingless) {dict(sigs)}")

        hits = defaultdict(lambda: {"TP": 0, "FP": 0, "sheet": False})
        for (_, _, h, _, l, best, _, band) in rows:
            if best and h and l in ("TP", "FP") and band != "NONE":
                hh = hits[best["name"]]
                hh[l] += 1
                hh["sheet"] = best["is_sheet_type"]
        sheets = sorted(((n, h) for n, h in hits.items() if h["sheet"]), key=lambda x: -(x[1]["TP"] + x[1]["FP"]))
        admins = sorted(((n, h) for n, h in hits.items() if not h["sheet"]), key=lambda x: -(x[1]["TP"] + x[1]["FP"]))
        print(f"\n[{stratum}] SHEET-TYPE entry hits (TP/FP):")
        for n, h in sheets:
            print(f"    {n:30} TP={h['TP']} FP={h['FP']}")
        if not sheets:
            print("    (none)")
        print(f"[{stratum}] ADMIN-document entry hits (TP/FP):")
        for n, h in admins:
            print(f"    {n:42} TP={h['TP']} FP={h['FP']}")

        print(f"\n[{stratum}] run8-FN pages carrying a logged heading (rescue-analog):")
        if not fn_with_heading:
            print("    (none)")
        for f, p, h, best, s, band in fn_with_heading:
            print(f"    {f[-10:-4]} p{p} heading={h!r} -> {band} {best['name'] if best else None!r} {s}")


def _is_heading(rows, lbl):  # placeholder kept for clarity; unused
    return True


if __name__ == "__main__":
    main()
