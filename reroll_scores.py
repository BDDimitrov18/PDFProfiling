#!/usr/bin/env python3
"""Re-score the three committed prediction logs under the corrected GT + lifted masks.
STRICT = all FPs counted. WAIVED = waivers.json (file,fp_page) excluded from FP count only.
No pipeline interaction; reads committed logs + eval_full GT/strata + waivers.json."""
import json, re, sys
from pathlib import Path

gt = json.load(open("eval_full/ground_truth.json", encoding="utf-8"))
strata = json.load(open("eval_full/strata.json", encoding="utf-8"))
masked = json.load(open("eval_full/masked.json", encoding="utf-8"))  # now {}
waiv = {(w["file"], w["fp_page"]) for w in json.load(open("waivers.json"))["waivers"]}

def load_preds(log):
    preds, cur = {}, None
    for line in Path(log).read_text(errors="replace").splitlines():
        s = line.strip()
        if s.endswith(".pdf") and not s.startswith("Image_") is False and re.match(r"^Image_\w+\.pdf$", s):
            cur = s
        else:
            m = re.search(r"pred=\[([^\]]*)\]", line)
            if m and cur:
                preds[cur] = set(int(x) for x in m.group(1).split(",") if x.strip())
    return preds

def mp(f):
    s = set()
    for lo, hi in masked.get(f, []): s.update(range(lo, hi+1))
    return s

def score(preds, waived):
    agg = {}
    out = {}
    for stratum in ("dev", "holdout", "fresh"):
        TP=FP=FN=0; rows=[]
        for f in sorted(gt):
            if strata.get(f) != stratum: continue
            m=mp(f)
            true=(set(gt[f])-{1})-m
            pred=(preds.get(f,set())-{1})-m
            fp=pred-true
            if waived:
                fp={p for p in fp if (f,p) not in waiv}
            fn=true-pred
            TP+=len(true&pred); FP+=len(fp); FN+=len(fn)
            if fp or fn: rows.append((f,sorted(fp),sorted(fn)))
        P=TP/(TP+FP) if TP+FP else 0; R=TP/(TP+FN) if TP+FN else 0
        F1=2*P*R/(P+R) if P+R else 0
        out[stratum]=(TP,FP,FN,P,R,F1,rows)
    return out

def agg_of(out):
    TP=sum(out[s][0] for s in out); FP=sum(out[s][1] for s in out); FN=sum(out[s][2] for s in out)
    P=TP/(TP+FP); R=TP/(TP+FN); F1=2*P*R/(P+R)
    return TP,FP,FN,P,R,F1

builds = [("round-1 candidate","logs/round1_candidate.log"),
          ("#2+#4 (Stage 2)","logs/fulltests_stage2.log"),
          ("run8 referee","logs/run8_stage3.log")]

for metric, waived in [("STRICT", False), ("WAIVED", True)]:
    print("="*80); print(f"{metric} METRIC (corrected GT, masks lifted)"); print("="*80)
    for name, log in builds:
        out = score(load_preds(log), waived)
        ta,fa,na,Pa,Ra,F1a = agg_of(out)
        line = f"{name:20}"
        for s in ("dev","holdout","fresh"):
            line += f"  {s}={out[s][5]*100:.2f}"
        line += f"  | AGG F1={F1a*100:.2f} (TP{ta}/FP{fa}/FN{na}, P={Pa*100:.2f} R={Ra*100:.2f}) freshP={out['fresh'][3]*100:.2f}"
        print(line)
    print()

# per-file deltas on the corrected files
print("="*80); print("PER-FILE (corrected files, STRICT)"); print("="*80)
for name, log in builds:
    out=score(load_preds(log), False)
    for s in out:
        for f,fp,fn in out[s][6]:
            if '143041245' in f or '145428614' in f:
                print(f"{name:20} {f[-10:-4]} FP={fp} FN={fn}")
