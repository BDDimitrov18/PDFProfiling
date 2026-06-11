# Boundary / Rotation Eval Results

> **RESUME POINT (2026-06-11):** Working on a migrated **RTX 5090** pod (the original run-8 pod;
> env reproduces run-8 exactly, so the **84.57% baseline is reused as the 5090 anchor**, no
> baseline re-run). Model cached at `/hf_cache`; deps per `requirements-lock.txt`; `HF_HOME=/hf_cache`,
> `HF_HUB_DISABLE_XET=1`. Speed ~16.5 s/page.
> **Queue (one commit + eval + Stage D row each):** (1) run8.py head-to-head on 5090 — RUNNING
> (`run8_5090.log`); (2) re-run **Fix 4** on 5090 (diff ref for Fix 8; sanity-compare per-file to
> 6000 Ada Fix 4 = F1 88.10%); (3) **Fix 8** (force `titled_id_header` through confirmation — edits
> the `conf<0.75` confirm block at ~split.py:993); (4) **Fix 9 — TWO exclusions in ONE commit** in
> the `titled_id_header` prompt (~split.py:472-474): (i) drawing-title-block (ОБЕКТ/ЧАСТ/ФАЗА/МАЩАБ/
> ЧЕРТЕЖ №/sheet#) → targets FPs {19,20,21,27}; (ii) page-counter exclusion — **X-of-Y FORM ONLY**
> ('стр. 2 от 2', '2/2' with X>1) = continuation NOT new doc even when the agency letterhead banner
> repeats → targets FP {11} (p11 = 'стр. 2 от 2' of p10's скица; model confabulated 'РС №' from the
> repeated AGKK banner). **BARE numerals (a lone corner '2') MUST NOT trigger it** — canonical
> counter-case: **084303475 p4** is a TRUE doc start carrying a bare corner '2' because its leading
> pages (incl. Челен лист) are absent from the scan; X-of-Y wording keeps it catchable. The exclusion
> is a `titled_id_header` SUPPRESSOR ONLY — missing-leading-page starts remain catchable via the Fix 8
> confirmation path. Stage D row reports per-FP attribution ({19,20,21,27} vs {11}) AND confirms p4 stays a boundary;
> (5) **Fix 11** (table-specialized `_query_confirm_table_boundary`, route `signal=="table_end"` in
> the confirm block; table-path None→reject; targets 5 table FNs 20@082511233 / 19,20@142044854 /
> 15,16@084303475; success FN −3+ with ≤+2 leaked table FPs). Fix 6 cancelled; Fix 3 lowest-priority.
> **Queue update (post-Fix-9):** after Fix 9 row records (Fix 8+9 combined = HEAD aea8297), run ONE extra
> eval: **Fix 9 WITHOUT Fix 8** (revert 9181a66 on a branch, keep aea8297). Keep whichever of {Fix8+9,
> Fix9-only} scores higher (predicted: Fix9-only — Fix 9 prompt-excludes most of what Fix 8 routing
> caught, Fix 8's FN cost remains). Fix 9 Stage D row: per-exclusion attribution + list every
> confirm-pass veto with TP/FP. Verify 084303475 p4 stays a detected boundary. Fix 11 on the winner.
> Revert any fix that drops tol=0 F1 >2 pts. pod ssh details are in the conversation, not committed.
> **C-tracking caution:** Reason fields are POST-HOC rationalizations — never treat text cited in a
> Reason as actually on the page without checking the image (p11's confabulated 'РС №' is the proof).
> **C-tracking — `_query_confirm_boundary` has TWO confirmed weaknesses:** (1) 0-for-5 on consecutive
> table-documents (rejects real table boundaries → Fix 11 replaces it for table_end). (2) **INVERTED
> bias for titled signals** (Fix 8 evidence): it kills real same-issuer titled_id_header transitions
> (lost 5 true starts) while passing fresh-looking drawing sheets — so routing titled_id_header through
> it (Fix 8) costs recall without removing the drawing-sheet FPs. Implication: prompt-level exclusion
> (Fix 9) is the right tool for titled FPs; the generic confirm is the wrong tool to *validate* titled starts.
> **C-tracking truth notes (closed):** GT boundaries 163444215:p10 and 084303475:p4 are human-attested
> FINAL (p4: rest of ЧАСТ ЕЛЕКТРОТЕХНИЧЕСКА incl. its Челен лист is not in the combined PDF at all;
> p3 = previous document). The 'convention-mismatch' category DISSOLVES for FP 10 (human did split the
> receipt). **084303475 p4 = canonical test case for Fix 9's page-counter exclusion** (true start with a
> bare corner '2' from missing leading pages — must survive the exclusion).
> **Full coverage audit (closed):** 4 of 20 `tests/` files have internal gap pages — 163444215[10,11]
> + 084303475[4] (both in dev, corrected) and 143041245[63-65] + 145428614[147-149] (not in eval set;
> fixed derivation covers them if added). **Historical-truth (closed):** run8.py = run-8 code (matches
> historical run-8 byte-identically on all 9 dev files; matches run-8 not run-9 on the 2 discriminating
> files). GT regen + free re-score of all rows DONE. Truth layer CLOSED → Fix 8 (running) → 9 → 11.

> ## OVERNIGHT BRIEF (verbatim — the ONLY plan; verifier gates against this)
> Overnight autonomous queue — run unattended, commit+push after EVERY step, all jobs in tmux. No human
> available until morning: any decision not covered by these rules → stop that branch, record the question
> in RESULTS.md, continue with the rest.
>
> 1. Record Fix 8+9 combined row (if not already done).
> 2. Run Fix 9-only A/B (revert 9181a66 on a branch, keep aea8297). Record row.
> 3. Winner rule: higher tol=0 F1 of {Fix8+9, Fix9-only} wins; tie → Fix9-only (fewer model calls). Record
>    verdict; the loser's commit is reverted/kept accordingly on main.
> 4. Implement Fix 11 on the winner (spec already in RESULTS.md resume notes). Run eval. Keep/revert rule:
>    keep if tol=0 F1 ≥ winner − 0.5 AND FN reduced by ≥2; revert otherwise. Record row + per-table-boundary
>    [TABLE-CONFIRM] attribution.
> 5. The cumulative best after step 4 = CANDIDATE. Tag it in git (round1-candidate).
> 6. Derive GT for ALL tests/ files with the fixed coverage-based derivation. For the two known gap files
>    (143041245[63-65], 145428614[147-149]) and any new gaps found: MASK the gap range ±1 page — no
>    attestation overnight; list every masked range in RESULTS.md for morning human inspection. Annotate
>    sources (pdfsam-derived/masked) as in dev GT.
> 7. Run CANDIDATE on the full tests set (classify=False, boundary scoring only). Report stratified, never
>    aggregated alone: (a) dev 9 files, (b) holdout files, (c) fresh never-evaluated files — P/R/F1 +
>    per-file FP/FN lists each, plus the aggregate. Explicitly flag the dev-vs-unseen gap as the
>    overfitting measure.
> 8. Push everything; end with a RESULTS.md summary block: final table, open questions for morning (masked
>    ranges to inspect, any stopped branches).
>
> Budget note: full tests is several hundred pages (~3-5+ h) — start it only after steps 1-5 are committed,
> so a pod death never costs decided results.
>
> **VERIFIER GATE:** after each numbered step and BEFORE the next, an independent verifier subagent
> (model claude-fable-5, fallback inherit) checks: (1) every RESULTS.md number matches eval_results.json /
> saved predictions; (2) decision verdicts match the rule arithmetic (arithmetic wins on conflict);
> (3) git show confirms each commit's diff touches exactly what's claimed (A/B branch reverts ONLY 9181a66);
> (4) committed+pushed before next step; (5) NO improvisation — any extra edit/threshold/prompt tweak →
> FAIL, revert it, log under "overnight deviations". Ambiguity is a morning question, never verifier-resolved.
> Step 7 (long run): gate only the final report. Verifier output = PASS/FAIL checklist per step with evidence.

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
| **Baseline (5090 anchor, reused)** | **RTX 5090** | 77.89% | 92.50% | 84.57% | 77.89% | 92.50% | 84.57% | 65/89 | Env-match CONFIRMED (run8.py reproduced historical run-8 exactly on this migrated pod) → original 84.57% is the valid same-GPU anchor for the 5090 deltas below. |
| **run8.py (reference)** | **RTX 5090** | 85.71% | 90.00% | 87.80% | 85.71% | 90.00% | 87.80% | 67/89 | Genuine run-8 code. **+3.2 F1 vs current baseline (84.57%) on same arch → quantifies the run8→current regression.** TP=72 FP=12 FN=8. 163444215 matches historical run-8 exactly (FP=[6,10,11,13,31] FN=[7,9]). |
| Fix 4 | RTX 5090 | 83.52% | 95.00% | 88.89% | 83.52% | 95.00% | 88.89% | 70/89 | Buggy-GT score. re-run on 5090; per-file ≈ 6000 Ada Fix 4 (3 single-page GPU flips). |

> **⚠ GROUND-TRUTH CORRECTION (2026-06-11, authorized): all F1 above are on the BUGGY GT — superseded by the table below.**
> `build_eval_set.py` derived boundaries only from PDFsam start prefixes and ignored piece page-counts,
> so pages covered by NO split file (gaps) were absorbed into the preceding doc, dropping 2 real boundaries:
> **163444215 +p10** (СКИЦА after isolated p9 invoice) and **084303475 +p4** (electrical-part cover). Fixed
> (coverage-based derivation); diff across all 9 dev + 3 holdout files = exactly these 2, nothing else.
> All rows re-scored from saved predictions (free). FP 10/4 → TP; **FP 11 stays a real error** (skица cut).

### Boundary detection — CORRECTED GT (authoritative)

| Stage | gpu | P | R | **F1** | docs | Δ F1 (same GPU) | was (buggy GT) |
|-------|-----|---|---|--------|------|-----------------|----------------|
| Baseline (anchor) | RTX 5090 | 80.0% | 92.7% | **85.88%** | — | — | ~~84.57%~~ |
| run8.py (reference) | RTX 5090 | 88.1% | 90.2% | **89.16%** | — | +3.28 vs baseline | ~~87.80%~~ |
| **Fix 4** | RTX 5090 | 85.7% | 95.1% | **90.17%** | — | **+4.29 vs baseline** | ~~88.89%~~ |
| Fix 8 (KEPT, flagged) | RTX 5090 | 87.95% | 89.02% | 88.48% | 68/91 | **−1.69 vs Fix 4** | — |
| Fix 9 (Fix 8+9) | RTX 5090 | 89.02% | 89.02% | 89.02% | 69/91 | **+0.54 vs Fix 8; −1.15 vs Fix 4** | — |

**Fix 9 (Fix 8+9 combined, commit aea8297, RTX 5090, corrected GT) — step 1 row.**
tol0=tol1: P=89.02 R=89.02 **F1=89.02**. TP=73 FP=9 FN=9. vs Fix 8 (88.48): +0.54 (FP 10→9).
- Per-exclusion attribution (163444215, vs Fix 8 FP=[6,13,19,20,21,31]): **drawing-block exclusion removed
  20,21**; 27 & 11 were already gone via Fix 8 (page-counter's isolated effect measured by the A/B);
  **19 SURVIVED** the exclusion (not recognized as a drawing title block). New FP `13`@164505881 appeared.
- **084303475 p4 PRESERVED as a boundary** (pred=[2,4,5,6,7,12,14]) — X-of-Y exclusion spared the bare-'2'. ✓
- 17 confirm-pass vetoes (Fix 8's titled routing); recall held at 89.0% (FN=9: 12@164505881, 3,4@165204533,
  20@082511233, 19,20,37@142044854, 15,16@084303475). Per-veto TP/FP not cleanly attributable (page numbers
  repeat across files); the Fix9-only A/B isolates Fix 8's net contribution. Still −1.15 below Fix 4.
| Baseline (anchor) | RTX 6000 Ada | 78.9% | 91.5% | 84.74% | — | — | ~~83.43%~~ |
| Fix 4 | RTX 6000 Ada | 86.4% | 92.7% | 89.36% | — | +4.62 | ~~88.10%~~ |

Primary anchor = **RTX 5090** (env-matched to original run-8 pod). Fix 4 = **90.17%**, +4.29 over the 85.88%
baseline. Fix 8/9/11 measured against this corrected 5090 GT.

**Fix 8 Stage D (RTX 5090, corrected GT) — KEPT (drop 1.69 ≤ 2), FLAGGED net-negative.**
TP=73 FP=10 FN=9; P=87.95 R=89.02 F1=88.48 (tol0=tol1). Removed FPs `11,27`@163444215, `7`@165204533;
but generic confirm wrongly REJECTED 5 true titled_id_header starts → new FN `4`@163444215, `12`@164505881,
`19,37`@142044854, `15`@084303475 (recall 95.1→89.0). Note titled FPs `13,19,20,21`@163444215 SURVIVED
confirm (drawing title blocks — Fix 9 targets them at the prompt). `19`@142044854 + `15`@084303475 are Fix 11
recovery targets. **Reconsider Fix 8 if Fix 9+11 cumulative stays < Fix 4 90.17.**

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

- **run8.py provenance: RESOLVED — it IS genuine run-8 code.** The migrated run-8 pod's
  `test_run8.log` (the actual historical run 8) predicted `163444215` =
  `[1,3,4,5,6,8,10,11,12,13,15,22,23,24,25,26,31,32,34]` → F1 **80.0%**, FP=`[6,10,11,13,31]`,
  FN=`[7,9]` (matches stats.py historical run8=80 exactly). run8.py predicted the **identical
  FP set** `[6,10,11,13,31]`; the ONLY difference is page 7 (run8.py caught it, raising F1 to
  83.3%) — symmetric diff = `[7]`, a single boundary flip explained by GPU-arch
  non-determinism (6000 Ada vs the original run-8 5090). Style modifiers present = consistent
  with pristine run-8 (demoted to log-only later, not added). [Earlier "probably not pristine"
  was WRONG.] **CONFIRMED on 5090: run8.py reproduces historical run-8 byte-identically on ALL
  9 dev files** (the 6000 Ada's page-7 diff was pure GPU non-determinism). **Discriminating test
  (it's run-8 NOT run-9):** historical run-8 vs run-9 differ on 2 of 9 files — `163444215` (run9
  adds 7,9,16) and `084303475` (run9 drops 15); run8.py matches run-8 and NOT run-9 on BOTH.
  Definitive: run8.py = run-8 code, and the migrated 5090 reproduces the original run-8 env exactly.
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
