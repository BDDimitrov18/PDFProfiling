"""nomenclature_experiment.py — DATA REPORT ONLY (no thresholds tuned, no pipeline change).

Parses every [TITLE-GATE] event from a full-tests detection log, labels each against GT, matches
the transcribed title via nomenclature_match, and reports per stratum:
  (1) match-score distributions for TP vs FP populations;
  (2) per-table-entry hit counts split TP/FP, with SHEET-TYPE entries reported SEPARATELY from
      administrative-document entries (hypothesis under test: sheet-types concentrate on FPs);
  (3) suppressed-was-true cases whose titles match the table (RESCUE candidates);
  (4) the full AMBIGUOUS-band list with top-3 candidate entries + scores (measures whether an
      AI-adjudication tier is needed at all).

The integration decision (one-of-two cap modulation / relocation preference / sheet-type negative
list / shelve) is a MORNING HUMAN CALL — this script proposes nothing and changes nothing.

Per Fable amendment 6: RECORD tonight, EXECUTE only after the Stage-2 full-tests log exists.
Usage: python3 nomenclature_experiment.py <fulltests_log> [--gt eval_full/ground_truth.json
        --strata eval_full/strata.json --masked eval_full/masked.json --xls номенклатура_цяла.xls]
"""
import argparse
import json
import re
import statistics
from collections import defaultdict

import nomenclature_match as nm

VERDICT_LINE = re.compile(r"\[TITLE-GATE\] p(\d+): title=(.*) identifier=(.*) -> grounded=(\d)/2")
CAPPED = re.compile(r"\[TITLE-GATE\] p(\d+) one-of-two")
SUPPRESSED = re.compile(r"\[TITLE-GATE\] titled_id_header at p(\d+) SUPPRESSED")
RELOC = re.compile(r"\[TITLE-GATE-RELOC\] grounded title on p(\d+) \(title=(.*) id=(.*), grounded=(\d)/2\)")
FNAME = re.compile(r"^(Image_\w+\.pdf)$")


def _unrepr(s):
    s = s.strip()
    if len(s) >= 2 and s[0] in "'\"" and s[-1] == s[0]:
        s = s[1:-1]
    return s


def masked_pages(ranges):
    out = set()
    for lo, hi in ranges or []:
        out.update(range(lo, hi + 1))
    return out


def parse_events(logpath):
    """Return {file: [event,...]}. Each event: dict(page,title,identifier,grounded,verdict,
    reloc_page). Events accumulate until a filename marker closes the file section."""
    files = {}
    buf, by_page = [], {}
    for line in open(logpath, encoding="utf-8", errors="replace"):
        m = VERDICT_LINE.search(line)
        if m:
            ev = {"page": int(m.group(1)), "title": _unrepr(m.group(2)),
                  "identifier": _unrepr(m.group(3)), "grounded": int(m.group(4)),
                  "verdict": "KEEP" if m.group(4) == "2" else "PENDING", "reloc_page": None}
            buf.append(ev)
            by_page[ev["page"]] = ev
            continue
        m = CAPPED.search(line)
        if m and int(m.group(1)) in by_page:
            by_page[int(m.group(1))]["verdict"] = "CAPPED"
            continue
        m = SUPPRESSED.search(line)
        if m and int(m.group(1)) in by_page:
            by_page[int(m.group(1))]["verdict"] = "SUPPRESSED"
            continue
        m = RELOC.search(line)
        if m:
            # relocation: the most recent PENDING/SUPPRESSED event gets moved
            ev = {"page": int(m.group(1)), "title": _unrepr(m.group(2)),
                  "identifier": _unrepr(m.group(3)), "grounded": int(m.group(4)),
                  "verdict": "RELOC", "reloc_page": int(m.group(1))}
            buf.append(ev)
            by_page[ev["page"]] = ev
            continue
        fm = FNAME.match(line.strip())
        if fm:
            files[fm.group(1)] = buf
            buf, by_page = [], {}
    return files


def label(ev, true_set):
    """Label a TITLE-GATE event against GT. Boundary page = reloc_page if relocated else page."""
    page = ev["reloc_page"] if ev["verdict"] == "RELOC" else ev["page"]
    kept = ev["verdict"] in ("KEEP", "CAPPED", "RELOC")
    in_true = page in true_set
    if kept:
        return "TP" if in_true else "FP"
    # SUPPRESSED (or PENDING with no follow-up = treated as suppressed)
    return "suppressed-was-true" if in_true else "suppressed-was-false"


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
    events = parse_events(args.log)

    print("=" * 90)
    print("NOMENCLATURE EXPERIMENT — DATA REPORT ONLY (no thresholds tuned, no pipeline change proposed)")
    print(f"log={args.log}  nomenclature={len(entries)} entries")
    print("=" * 90)

    for stratum in ("dev", "holdout", "fresh"):
        files = [f for f in gt if strata.get(f) == stratum]
        rows = []  # (file, ev, lbl, best, scores, band)
        for f in files:
            mp = masked_pages(masked.get(f))
            true_set = set(gt[f]) - {1} - mp
            for ev in events.get(f, []):
                page = ev["reloc_page"] if ev["verdict"] == "RELOC" else ev["page"]
                if page in mp:
                    continue  # masked: excluded from scoring
                best, scores, band = nm.match_title(ev["title"], entries)
                rows.append((f, ev, label(ev, true_set), best, scores, band))
        if not rows:
            continue
        print(f"\n{'#'*30} STRATUM: {stratum} ({len(rows)} TITLE-GATE events) {'#'*30}")

        # (1) score distributions TP vs FP (kept boundaries only)
        for lbl in ("TP", "FP"):
            tri = [s["trigram"] for _, _, l, _, s, _ in rows if l == lbl]
            tok = [s["token_set"] for _, _, l, _, s, _ in rows if l == lbl]
            bands = defaultdict(int)
            for _, _, l, _, _, b in rows:
                if l == lbl:
                    bands[b] += 1
            print(f"\n[{stratum}/{lbl}] trigram {dist(tri)}")
            print(f"[{stratum}/{lbl}] token_set {dist(tok)}")
            print(f"[{stratum}/{lbl}] bands {dict(bands)}")

        # (2) per-table-entry hit counts TP/FP, sheet-types separate
        hits = defaultdict(lambda: {"TP": 0, "FP": 0, "sheet": False})
        for _, _, l, best, _, band in rows:
            if best and l in ("TP", "FP") and band != "NONE":
                h = hits[best["name"]]
                h[l] += 1
                h["sheet"] = best["is_sheet_type"]
        sheet_rows = sorted(((n, h) for n, h in hits.items() if h["sheet"]),
                            key=lambda x: -(x[1]["TP"] + x[1]["FP"]))
        admin_rows = sorted(((n, h) for n, h in hits.items() if not h["sheet"]),
                            key=lambda x: -(x[1]["TP"] + x[1]["FP"]))
        print(f"\n[{stratum}] SHEET-TYPE entry hits (TP/FP) — hypothesis: concentrate on FP:")
        for n, h in sheet_rows:
            print(f"    {n:30} TP={h['TP']} FP={h['FP']}")
        if not sheet_rows:
            print("    (none)")
        print(f"[{stratum}] ADMIN-document entry hits (TP/FP):")
        for n, h in admin_rows:
            print(f"    {n:42} TP={h['TP']} FP={h['FP']}")

        # (3) suppressed-was-true whose title MATCHes table = rescue candidates
        print(f"\n[{stratum}] RESCUE candidates (suppressed-was-true with table MATCH):")
        any_r = False
        for f, ev, l, best, s, band in rows:
            if l == "suppressed-was-true" and band == "MATCH":
                any_r = True
                print(f"    {f[-10:-4]} p{ev['page']} title={ev['title']!r} -> {best['name']!r} {s}")
        if not any_r:
            print("    (none)")

        # (4) AMBIGUOUS-band list with top-3 candidates
        print(f"\n[{stratum}] AMBIGUOUS-band events (top-3 candidates — measures AI-adjudication need):")
        any_a = False
        for f, ev, l, best, s, band in rows:
            if band == "AMBIGUOUS":
                any_a = True
                top = nm.top_matches(ev["title"], entries, 3)
                cand = "; ".join(f"{e['name']}({sc['trigram']},{sc['token_set']})" for e, sc in top)
                print(f"    {f[-10:-4]} p{ev['page']} [{l}] title={ev['title']!r} -> {cand}")
        if not any_a:
            print("    (none)")


if __name__ == "__main__":
    main()
