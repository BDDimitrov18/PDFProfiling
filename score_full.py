#!/usr/bin/env python3
"""Stratified + masked scorer for the full-tests CANDIDATE run.

Reads eval_full/{ground_truth,masked,strata}.json + a detection log containing per-file
'pred=[...]' lines (produced by eval_boundaries.py). Masked page ranges are excluded from
BOTH pred and true (scored neither way — unattested overnight gaps). Reports each stratum
(dev / holdout / fresh) separately, then the aggregate, and flags the dev-vs-unseen F1 gap.

Usage: python score_full.py eval_full <detection_log>
"""
import argparse, json, re
from pathlib import Path


def load_preds(logpath):
    preds, cur = {}, None
    for line in Path(logpath).read_text(errors="replace").splitlines():
        s = line.strip()
        if s.endswith(".pdf"):
            cur = s
        else:
            m = re.search(r"pred=\[([^\]]*)\]", line)
            if m and cur:
                preds[cur] = set(int(x) for x in m.group(1).split(",") if x.strip())
    return preds


def masked_pages(ranges):
    s = set()
    for lo, hi in ranges:
        s.update(range(lo, hi + 1))
    return s


def score_stratum(files, gt, preds, masked, strata, stratum):
    TP = FP = FN = 0
    rows = []
    for f in sorted(files):
        if strata.get(f) != stratum:
            continue
        mp = masked_pages(masked.get(f, []))
        true = (set(gt[f]) - {1}) - mp
        pred = (preds.get(f, set()) - {1}) - mp
        fp, fn = sorted(pred - true), sorted(true - pred)
        TP += len(true & pred); FP += len(fp); FN += len(fn)
        rows.append((f, fp, fn))
    P = TP / (TP + FP) if TP + FP else 0.0
    R = TP / (TP + FN) if TP + FN else 0.0
    F1 = 2 * P * R / (P + R) if P + R else 0.0
    return TP, FP, FN, P, R, F1, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("log")
    args = ap.parse_args()
    folder = Path(args.folder)
    gt = json.loads((folder / "ground_truth.json").read_text(encoding="utf-8"))
    masked = json.loads((folder / "masked.json").read_text(encoding="utf-8"))
    strata = json.loads((folder / "strata.json").read_text(encoding="utf-8"))
    preds = load_preds(args.log)
    files = list(gt)

    agg = {}
    for stratum in ("dev", "holdout", "fresh"):
        TP, FP, FN, P, R, F1, rows = score_stratum(files, gt, preds, masked, strata, stratum)
        agg[stratum] = F1
        print(f"\n=== STRATUM: {stratum} ({sum(1 for f in files if strata.get(f)==stratum)} files) ===")
        print(f"TP={TP} FP={FP} FN={FN}   P={P:.2%}  R={R:.2%}  F1={F1:.2%}")
        for f, fp, fn in rows:
            if fp or fn:
                print(f"  {f}: FP={fp} FN={fn}")

    # aggregate over all strata
    aTP = aFP = aFN = 0
    for stratum in ("dev", "holdout", "fresh"):
        TP, FP, FN, *_ = score_stratum(files, gt, preds, masked, strata, stratum)
        aTP += TP; aFP += FP; aFN += FN
    P = aTP / (aTP + aFP) if aTP + aFP else 0.0
    R = aTP / (aTP + aFN) if aTP + aFN else 0.0
    F1 = 2 * P * R / (P + R) if P + R else 0.0
    print(f"\n=== AGGREGATE (all 20, masked excluded) ===")
    print(f"TP={aTP} FP={aFP} FN={aFN}   P={P:.2%}  R={R:.2%}  F1={F1:.2%}")
    unseen = (agg["holdout"] + agg["fresh"]) / 2 if (agg["holdout"] or agg["fresh"]) else 0.0
    print(f"\n>>> OVERFITTING MEASURE: dev F1={agg['dev']:.2%}  vs  unseen(holdout+fresh) "
          f"holdout={agg['holdout']:.2%} fresh={agg['fresh']:.2%}  (gap dev−fresh = {agg['dev']-agg['fresh']:+.2%})")


if __name__ == "__main__":
    main()
