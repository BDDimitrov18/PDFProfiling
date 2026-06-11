# Boundary / Rotation Eval Results

Eval set: `eval_dev/` (9 files, ~181 pages, derived from `tests/` only) — unchanged across all
boundary runs (boundary truth from PDFsam split files; identical `ground_truth.json`).
Rotation truth from split PDFs' `/Rotate` metadata (CW→CCW); see Stage 1 log.
Model: Qwen2.5-VL-32B-Instruct, greedy decoding (deterministic per GPU model, NOT across GPU
architectures — only compare rows with the same `gpu`).

## Boundary detection

| Stage | gpu | tol=0 P | tol=0 R | tol=0 F1 | tol=1 P | tol=1 R | tol=1 F1 | docs exact | notes |
|-------|-----|---------|---------|----------|---------|---------|----------|------------|-------|
| ~~Baseline~~ | ~~RTX 5090~~ | ~~77.89%~~ | ~~92.50%~~ | ~~84.57%~~ | ~~77.89%~~ | ~~92.50%~~ | ~~84.57%~~ | ~~65/89~~ | SUPERSEDED by 6000 Ada anchor (different GPU). TP=74 FP=21 FN=6. |
| ~~Fix 1 (REVERTED)~~ | ~~RTX 5090~~ | ~~74.00%~~ | ~~92.50%~~ | ~~82.22%~~ | ~~75.00%~~ | ~~93.75%~~ | ~~83.33%~~ | ~~63/89~~ | REVERTED (placement errors absent from data; Fix 1-REV also dropped per brief 2). |
| ~~Fix R (kept)~~ | ~~RTX 5090~~ | ~~77.89%~~ | ~~92.50%~~ | ~~84.57%~~ | ~~77.89%~~ | ~~92.50%~~ | ~~84.57%~~ | ~~65/89~~ | SUPERSEDED. Neutral on 5090; rotation no-op rules it out of run-9 regression. |
| **Baseline (anchor)** | **RTX 6000 Ada** | 76.84% | 91.25% | 83.43% | 76.84% | 91.25% | 83.43% | 64/89 | f51a810 code re-run on this GPU. TP=73 FP=22 FN=7. Conf histogram: 3×85, 131×90 (anchored prompt). **Same-GPU anchor for all deltas below.** |
| Fix 4 | RTX 6000 Ada | 84.09% | 92.50% | 88.10% | 84.09% | 92.50% | 88.10% | 69/89 | **Δ F1 +4.67 vs 6000 Ada anchor.** TP=74 FP=14 FN=6. De-anchor + cap noisy signals. Conf histogram: 17×80, 101×90 (4b removed 100s, added 80s; recall up not down). 163444215 FP 22→9. |

**GPU comparability (per brief 2 / A4):** baseline, Fix 1, Fix R were measured on **RTX 5090**;
Fix 4 onward run on **RTX 6000 Ada** (pods cycled due to disk/OOM). Greedy decoding is
deterministic per GPU but not across architectures, so 5090 rows are NOT directly comparable
to 6000 Ada rows. Plan: after Fix 4 records, re-run the baseline on RTX 6000 Ada as a
same-hardware anchor; 5090 rows will then be struck through (kept for history).

## Rotation detection (degrees-exact, OSD arm)

| Stage | TP | FP | FN | wrong-deg | Precision | Recall | notes |
|-------|----|----|----|-----------|-----------|--------|-------|
| Baseline (legacy VLM) | — | — | — | — | — | — | not run (optional; GPU). OSD arm chosen for Fix R. |
| OSD arm (truth=90 BUG) | 0 | 4 | 15 | 3 | 0% | 0% | truth used PDF /Rotate (CW) as CCW — wrong. |
| OSD arm (truth=270 fixed) | 3 | 1 | 12 | 0 | 75% | 20% | degree bug fixed; 1 FP = landscape low-text 180°. |
| OSD arm (thr 2.0→3.0) | 2 | 0 | 13 | 0 | 100% | 13.3% | FP abstained (truth still had bogus p7). |
| **OSD arm (truth from /Rotate)** | **2** | **0** | **12** | **0** | **100%** | **14.3%** | **GATE 1 PASS.** Rotation truth now from split /Rotate metadata (CW→CCW); p7 false positive removed. Fix R enabled. |

## run8.py head-to-head (regression diagnostic)

- **run8.py provenance: UNRESOLVED.** run8.py has load-bearing style modifiers (current
  `split.py` demoted these to log-only), but that is **consistent with pristine run-8** —
  they may have been demoted in a later run, not added. On `163444215` (6000 Ada) run8.py
  scored F1 **83.3%** historical-style (TP=15, FP=5 `{6,10,11,13,31}`, FN=1 `{9}`) vs
  historical run8=80% / run9=84%. The 83.3-vs-80 gap is **GPU-confounded** (historical was
  5090, this was 6000 Ada) and possibly scorer-confounded — so this does **NOT** establish
  run8.py as non-pristine. Clean test pending: re-run run8.py on the 5090.
- **Hard cases:** FPs **11 and 13** on `163444215` are produced by BOTH run8.py and the
  current pipeline, via *different mechanisms* — genuinely hard pages, expected to **survive
  Fix 9**. (run8 unique-misses are only the `titled_id_header` cluster `{19,20,21,27}`, which
  run8 lacks because it predates `titled_id_header` — this is what Fix 8/9 target.)

## Stage log

- **Stage 0** — harness built (`eval_boundaries.py`, `eval_rotation.py`, `test_osd_mapping.py`,
  `build_eval_set.py`). All compile clean. Edit targets for Stages 1-2 confirmed verbatim.
  eval_dev/ + eval_holdout/ generated. Baseline boundary F1=84.57%.
- **Stage 1** — 1a: `_OSD_TO_CCW` corrected to identity (synthetic test 12/12 pass).
  1b: `query_rotation_osd_first` added. 1c: `corroborate_aspect` quarantined (no call sites).
  Found+fixed a ground-truth bug (PDF /Rotate CW vs codebase CCW → 90 should be 270;
  visually confirmed). Raised abstention 2.0→3.0. **GATE 1 PASS (OSD precision 100%).**
