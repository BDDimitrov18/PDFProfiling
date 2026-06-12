# Boundary / Rotation Eval Results

## ☀ MORNING SUMMARY (overnight round 1 complete, 2026-06-12)

**CANDIDATE = Fix9-only, `git tag round1-candidate` (88f58dc).** Boundary detection, RTX 5090, corrected GT.

**5090 fix chain (dev eval, tol=0 F1):**
| stage | F1 | verdict |
|---|---|---|
| Baseline (anchor) | 85.88% | — |
| Fix 8 (titled→confirm) | 88.48% | superseded |
| Fix 8+9 | 89.02% | superseded |
| **Fix9-only** | **89.94%** | **KEPT = CANDIDATE (+4.06 vs baseline)** |
| Fix 11 (table-confirm) | 89.14% | REVERTED (< 89.44 keep-threshold) |

**Full-`tests/` CANDIDATE run (20 files / 733 pages, masked gaps excluded), STRATIFIED:**
| stratum | files | P | R | **F1** |
|---|---|---|---|---|
| dev (tuned) | 9 | 87.36% | 92.68% | **89.94%** |
| holdout (unseen) | 3 | 91.67% | 73.33% | **81.48%** |
| fresh (unseen) | 8 | 77.31% | 93.49% | **84.63%** |
| **aggregate** | 20 | 80.22% | 92.31% | **85.84%** |

docs exactly recovered (aggregate): 231/336.

**⚠ OVERFITTING MEASURE: dev 89.94% vs unseen — fresh 84.63% (gap +5.31), holdout 81.48% (gap +8.46).**
Round 1 tuned on the 9 dev files; unseen files score 5–8 F1 lower. Pattern: **fresh precision 77% vs dev 87%**
— the pipeline OVER-SPLITS on unseen files (e.g. 145428614 = 24 FP, 142438096 = 11 FP). Recall generalizes
fine (92–93% everywhere); precision does not. So round-1's gains are partly dev-specific.

### Open questions for human (morning)
1. **Masked ranges to attest** (scored neither way overnight): `143041245[63-65]` and `145428614[147-149]`
   (same gap pattern as the attested dev cases — likely real СКИЦА/section boundaries; inspect & attest).
2. **Fix 11 table-confirm is too permissive** — fired 12× and answered different=true every time; recovered 2
   real table boundaries but added 4 FP → reverted. Needs a stricter "continues numbering" branch before re-try.
3. **Generalization gap (+5–8 F1)** — fresh-file over-splitting (precision 77%) is the round-2 target; the
   titled_id_header drawing-block / page-counter exclusions tuned on dev don't fully transfer.

### Overnight deviations: NONE
All steps verifier-gated PASS (Fable 5). No improvisation, no extra edits; every keep/revert followed the
rule arithmetic. Final-report gate: checks 1–4 PASS (numbers re-verified on pod = exact, masking applied,
strata 9/3/8, CANDIDATE md5 ca8aea3); check 5 flagged an untracked `eval_full/` → gitignored (generated
symlink dir), tree clean. (Cosmetic verifier notes only: a note block splitting a markdown table; "3 commits
not 2" where the 3rd was the reverted Fix 11 impl — neither a deviation.)

**QUEUE COMPLETE. Loop stopped.** Round-1 candidate = Fix9-only (tag round1-candidate). Awaiting human:
attest masked ranges, decide round-2 target (fresh-file over-splitting / table-confirm v2).

## 🗂 ROUND 2 BACKLOG (local-only, strict order, one commit + targeted probe each)

Sorted by certainty-of-gain ÷ risk. **Probe set = 163444215, 164505881, 165204533, 082511233** (~100 pages,
~30 min on 5090). **Named test cases:** FP31, FN12+FP13, FN3, FN20, FP11, FP19, FP27. Revert rule unchanged
(revert if dev tol=0 F1 drops). Stratified full-tests run is the real verdict — fresh-precision is the target.

**TIER 1 — pure logic bugs (no model-behavior change, no overfitting risk). Each its own commit.**
1. **Direction-aware `signal_on_page`.** Current logic treats ALL signals as start-markers. Correct only for
   `titled_id_header`/`plain_title` (header on n+1 → cut BEFORE n+1, current behavior). INVERTED for end-markers:
   `signature_block`/`table_end` on n+1 means the doc extends THROUGH n+1 → cut AFTER it. Add signature POSITION:
   bottom-of-page = closing; top-of-page = title-page countersignature (start context). Fixes severed deed
   signature (FP31@163444215) + the FN12/FP13 spillover pair (164505881) in one change. **Highest-confidence fix.**
2. **Window-range validation.** Model returned `signal_on_page=4` from context [1,2,3]; code silently substituted
   page 2 and planted a boundary (FN3@165204533). Validate returned page ∈ window; on violation, ONE re-query with
   explicit page labels ("you are looking at pages 1, 2, 3"); NEVER silently substitute.
3. **Rotation everywhere.** OSD rotation applies in Phase 1 only; confirm/one-page-check/start-detect see RAW
   orientations and judged a rotated 'Проектант'+signature page as mid-document (FN20@082511233). Route every image
   through the same rotation path, log per-page angle, pass "orientation differs between n and n+1" as a context
   line to the confirm prompt (orientation flips correlate with boundaries here).

**TIER 2 — local anti-hallucination gate (replaces a Fable arbiter).**
4. **Transcribe-then-judge for `titled_id_header`.** Signal JSON must carry the verbatim identifier string +
   location; then ONE follow-up: "Transcribe all text in the top quarter of page N" — accept the signal only if the
   quoted identifier appears in the transcription. Kills invented-РС№ class (FP11, FP19, FP27) by separating reading
   from concluding (32B confabulates when judging, far less when reading). Cost: +1 query per titled firing (~15–20/file).

**TIER 3 — BLOCKED until the fresh-FP attribution table is delivered (don't build before the data).**
5. **Repeated-form suppression.** Consecutive pages sharing a printed template = one doc. Likely kills the ЕСУТ-stack
   class + maybe the fresh collapse (24 FP on 145428614). Implement ONLY after fresh-FP attribution confirms form
   stacks are the bulk. Local impl: structural similarity on binarized page skeleton (downsample + perceptual hash /
   line-grid correlation), VLM consulted only when the score is ambiguous — NOT pairwise VLM "is this the same form".
6. **Fix 11 v2 (table confirm).** v1 answered different=true 12/12 (prompt primed it). v2: force evidence before
   verdict — JSON must report `last_row_number(n)` and `first_row_number(n+1)`; continuous numbering = same document
   MECHANICALLY, no judgment question asked. Targets table FN cluster (20@082511233, 19–20@142044854, 15–16@084303475).

**PROCESS:** Tier 1 = 3 commits → probe (4 files only) → check 7 named cases pass → full dev eval. Then Tier 2 →
probe → full dev eval. Stratified full-tests run only after both tiers settle. Expected: Tier 1+2 ≈ +2–4 dev F1
toward low-90s AND should transfer to fresh (none is dev-tuned prompt wording); Tier 3 attacks fresh 77% precision.

### ROUND 2 LOG

#### ⛓ OVERNIGHT CHAIN — BINDING AMENDMENTS (Fable 5 audit of 6015f0b, 2026-06-12)
Verifier audited 6015f0b from repo: diff surgical (one functional clause `and signal not in
("signature_block","table_end")`, NO prompt strings, project_signoff path intact), md5 7985f70 confirmed.
Chain proceeds under these BINDING rules (rule arithmetic wins on conflict; any uncovered decision STOPS that
branch → morning question; never self-attest GT):
1. **Probe verdict gate — byte-level, not eyeball.** Expected sets: 163444215 FP=[6,13] FN=[] (FP31 dead AND
   none of full-#1's failure modes: no +FP2, no 34→33, no +FN4); 164505881 FP=[9,13] FN=[12]; 165204533 FP=[]
   FN=[3,4]; 082511233 FP=[] FN=[20]. ANY deviation beyond FP31's death → **revert 6015f0b immediately**, run
   rest of chain on #2+#4 only (#1-lite retried later as its own probe; chain must NOT stall). Record full
   per-file FP/FN sets in the RESULTS probe row either way; the "31/32 cut exists at conf 92" claim MUST be
   evidenced by the quoted probe-log line.
2. **Stage-1 dev revert order (binding — stack confounds attribution).** If dev tol=0 F1 < 89.94, revert
   newest-first, ONE A/B re-run per revert, never >1 commit between evals: (a) 6015f0b #1-lite → re-run; (b)
   9fee964 #4-upgrade → re-run; (c) 559b8d7 #4-base; (d) cf9f88a #2 last (least suspect — byte-identical on
   probe). Record every A/B row.
3. **Terminology — FN3/FN4/FN20 are NOT waivers; they are STRICT FNs.** A waiver = human-attested
   filer-convention GT issue in waivers.json (which does NOT exist — do not create it; never put model failures
   in it). Record mislocalization-class misses as "known strict FNs, deferred to backlog (requery-aware
   relocation spec / Tier-3 class)." ALL overnight metrics are STRICT only.
4. **Stage 2 (full-tests stratified) additions.** Beyond per-stratum [TITLE-GATE] SUPPRESSED / one-of-two
   accept / [WINDOW-REQUERY] counts, ALSO count per stratum how often #1-lite changed behavior = end-events
   where signal∈{signature_block,table_end} landed on n+1 (old code would have one-page-checked). Derive
   POST-HOC from existing log lines — NO code edits after the probed md5. Masked 143041245[62-66],
   145428614[146-150] excluded + listed. Strata 9/3/8 + aggregate, per-file FP/FN, overfitting gap flagged.
   Baseline row = round1-candidate full-tests (85.84 aggregate / fresh P 77.31).
5. **Stage 3 run8.py full-tests stratified runs REGARDLESS of Stage-2** (settles historical-88.5; same
   masking/strata).
6. **Stage 4 pod DOWN per REDEPLOY PROTOCOL.** Before shutdown: git status clean, all pushed, morning summary
   written (final tables, event counts, open questions). Morning questions for USER (never self-attest): masked
   ranges + the FP13@163444215 seam. Push + verifier-gate after EVERY stage (numbers match artifacts, git show
   matches claims, no improvisation).

#### 📎 LOG-ARTIFACTS AMENDMENT (human, 2026-06-12) — tracked `logs/` for independent audit
Raw run logs are repo-tracked, append-only evidence. After each stage, copy its log to `logs/` BEFORE the gate
and push immediately: `logs/probe_1lite2.log` (done), `logs/dev_stage1.log`, `logs/fulltests_stage2.log`,
`logs/run8_stage3.log`, plus each eval's `eval_results.json` → `logs/<stage>_results.json` (these embed per-file
`pred`/`true`/`fp`/`fn` arrays = the primary predictions artifact; audit recomputes FP/FN independently). NEVER
edit/trim/regenerate a committed log; a re-run commits under a NEW name (e.g. `dev_stage1_ab_revert4.log`), old
kept. Gzip (`.log.gz`) if >50 MB, never truncate. `eval_dev/ eval_holdout/ eval_full/ eval_probe/` stay gitignored
(symlink dirs) — this tracks logs + predictions only.
**Item-4 log-retention check (CONFIRMED, no code edit):** `[TITLE-GATE]` lines preserve full `title=`/`identifier=`
verbatim at INFO with NO truncation — code logs `{t_title!r}` (repr, no slice); inspected `logs/probe_1lite2.log`:
longest title 'РАЙОНЕН ЕКСПЕРТЕН СЪВЕТ ПО УСТРОЙСТВО…РАЙОН "ЗАПАДЕН"' (90 chars) printed complete, 0 ellipsis
truncations, 16/16 verdict lines at INFO. Sole length bound is `_query_transcribe_title` `max_tokens=120` on the
MODEL's transcription (inherent to build 63da033, not a logging defect) → nomenclature experiment has full strings.

#### 🌅 MORNING QUESTIONS (human attestation only — never self-attest, never touch GT)
- **082511233 p20 vs p21:** is the true `НАКЛОНЕН ПОКРИВ` boundary on p20 or p21? (GT currently p20; #1-lite's FP21
  and the OOB self-contained verdict both touched this seam — human call, GT untouched.)
- **FP13@163444215 seam** (pending human attestation).
- **Masked ranges** to inspect/attest: 143041245[62-66], 145428614[146-150] (+ exported to `attestations/`).

#### 📋 BACKLOG
- **#1-lite v2:** gate BOTH one-page-check call sites (normal n+1 branch AND OOB-PROJECTION branch) for
  signature_block/table_end; one commit + full 4-file probe with exact expected sets. NOT tonight.
- **Requery-aware relocation** (FN3-class): relocation trigger = not-BOTH-grounded + suspect provenance (via
  #2-requery OR reason-title/page mismatch); search = match reason-cited title against window transcriptions.
  Pod-less dev batch, gated on tonight's fresh-stratum event counts.
- **Tier 3 #5 repeated-form suppression:** pod-less, CPU structural similarity on binarized page skeletons.
- **FN3 / FN4 / FN20:** known STRICT FNs, mislocalization-class, deferred here. NOT waivers (no waivers.json).


**Tier 1 #1 — direction+position-aware `signal_on_page` — REVERTED (commit 3b06dff → revert 6917329).**
Added a `signal_position` field (bottom=closing / top=countersignature) to `_query_document_end`, position-aware
`effective_end`, and gated the n+1 one-page-check to `position=='none'`. Probe (5090, Tier1#1 md5 37340f8,
`probe_t1_1.log`) vs round-1 Fix9-only on the 4 probe files, scored against corrected GT:

| File | Round-1 (Fix9-only) tol0 | Tier1#1 tol0 | Δ |
|---|---|---|---|
| 163444215 | FP[6,11,13,19,27,**31**] FN[] | FP[**2**,6,11,13,19,27,**33**] FN[**4**,**34**] | FP31 fixed; **+FP2, 34→33 displ., +FN4** |
| 164505881 | FP[9,**13**] FN[**12**] | FP[9,13] FN[] | **FN12 fixed**; FP13 persists |
| 165204533 | FP[] FN[3,4] | FP[**7**] FN[3,4] | **+FP7** |
| 082511233 | FP[] FN[**20**] | FP[**21**] FN[20] | 20→21 displ., still misses 20 |
| **total** | **8 FP / 4 FN (12 err)** | **11 FP / 5 FN (16 err)** | **net −4 tol0** |

Both named targets fixed (**FP31 gone, FN12 recovered**) but net-negative: −4 errors tol=0. **Root cause:** Edit 1
added the position instruction to the `_query_document_end` *prompt itself* — a global perturbation, not a surgical
placement change. For the front pages (p2/p3/p4 of 163444215) the placement logic is byte-identical to round-1, yet
boundaries still shifted **3,4→2,3** — only the changed prompt text can move the model's own end-detection on
unrelated pages. The feature cannot be isolated from collateral detection drift. Per the brief's "no new regressions"
bar + established revert discipline (Fix 8 flagged, Fix 11 reverted) → reverted; `split.py` restored to Fix9-only
(md5 ca8aea3). **Finding for Tier 3 redesign:** the severed-deed / countersignature geometry needs a mechanism that
does NOT alter the shared end-detection prompt (e.g. a dedicated post-hoc position query only on the candidate page,
or fold into #5/#6). Proceeding to **Tier 1 #2** (window-range validation — touches substitution logic, not the
end-detection prompt → no bleed risk).

**Tier 1 #2 — window-range validation (no silent substitution) — KEPT (commit cf9f88a).** `_requery_signal_page`
replaces the silent `signal_page = current_page` substitution. Probe (Tier1#2 md5 21945c2, `probe_t1_2.log`):
**predictions byte-identical to round-1 on all 4 files** — tol=0 unchanged (FP[6,11,13,19,27,31]/FN[]; FP[9,13]/FN[12];
FN[3,4]; FN[20]). The re-query fired once (165204533 p2: `signal_on_page=4` outside [1,2,3] → re-placed on page 1) but
**FN3 NOT recovered** — when forced in-window the model picks page 1, i.e. it mislocalizes the boundary in this rapid
single-page-stack; silent substitution was never the cause. **No bleed, no regressions** (validates the isolated-change
thesis vs #1's prompt-level perturbation). Kept as a real correctness fix (kills the silent-misplacement FP class that
the probe's 4 files just don't exercise); the full dev eval is its real test — A/B-revert if it regresses there. FN3
reclassified as a model-localization failure for #5/#6 (single-page-doc stacks), not a substitution bug. → **Tier 1 #3**.

**Tier 1 #3 — rotation everywhere — SKIPPED (premise stale; no code change).** Audit of split.py:899-914 shows
`detect_rotation(p)` already rotates `page_buffer[p]` IN PLACE for n-1/n/n+1 at the top of every Phase-1 iteration,
and EVERY gate (style-continuity 924, one-page-check 959/1066, start-detect 1001/1101, confirm 1028/1046) reads from
`page_buffer` — so the gates already see UPRIGHT pages. The backlog's premise ("confirm/one-page-check/start-detect
see RAW orientations") is false in the current code; #3 is already implemented. **FN20@082511233 is NOT a rotation
case:** pages 18-21 carry no rotation (the file's only OSD hit was p15→270°, correctly detected + applied, then
smoothed to 0). Real FN20 mechanism (`probe_t1_2.log`): on p20 (ctx [19,20,21]) the model reads the `НАКЛОНЕН ПОКРИВ`
title + signature and localizes the new-doc start at **p21 (one page late; truth=p20)**; the one-page-check confirms
p21 self-contained and the boundary is then dropped downstream → neither 20 nor 21 survives. This is the same
off-by-one signature-localization family as #1 (un-fixable without prompt bleed) — reclassified to **Tier 3 #6**
(table/numbering branch + signature-position). → no probe needed.

**Tier 2 #4 — transcribe-then-judge titled gate — PROBE PASS, KEPT pending dev eval (commit 559b8d7).**
Probe (Tier2#4 md5 7f67d16, `probe_t2_4.log`) vs round-1 reference on the 4 files, tol=0:
| File | Round-1 | Tier2#4 | Δ |
|---|---|---|---|
| 163444215 | FP[6,**11**,13,**19**,**27**,31] FN[] | FP[6,13,31] FN[] | **−3 FP (FP11/19/27 killed)** |
| 164505881 | FP[9,13] FN[12] | FP[9,13] FN[12] | identical (p4 suppressed but co-detected → no FN) |
| 165204533 | FP[] FN[3,4] | FP[] FN[3,4] | identical |
| 082511233 | FP[] FN[20] | FP[] FN[20] | identical |
| **F1 tol0** | **83.3%** | **86.96%** | **+3.66 (all precision)** |
KILL-direction: all 3 named targets dead (`[TITLE-GATE] p19/p27/p15 → none/none → SUPPRESS`).
SURVIVE-direction: every grounded titled TP kept — p10 (СКИЦА № 15-158202), p12 (протокол №5),
p25, p26 (НОТАРИАЛЕН АКТ №30705), p2 (УДОСТОВЕРЕНИЕ №02944), p5 (договор №4279762), p6 (полица).
No true boundary lost; recall unchanged. **FLAG (both-directions watch):** p4@164505881 is a TRUE
start with a real identifier (`изх. № 6480458`) but model read `title='none'` → BOTH-grounded rule
SUPPRESSED it; it survived only via co-detection (no FN here, but the rule could FN an изх-№-only
start with no redundancy — also p1@082511233 ЧЕЛЕН ЛИСТ suppressed, but p1 is excluded from scoring).
Dev/full eval must watch for titled-suppressions that become FNs. → stacked #2+#4 dev eval next.

**Tier 2 #4 UPGRADE — localizer + one-of-two — KEPT (commit 9fee964), FN3 BLOCKED by #2 interaction.**
Probe5 (md5 63da033, `probe_t2_4b.log`): score IDENTICAL to filter-only #4 (tol=0 F1 86.96 TP30/FP5/FN4;
tol=1 89.86). 163444215 FP[6,13,31] FN[]; 164505881 FP[9,13] FN[12]; 165204533 FN[3,4]; 082511233 FN[20].
Audit: (b) FP11/19/27 STAY DEAD ✓ — p11/p27 SUPPRESSED ("2 grounded-title pages ambiguous"), p19/p15
SUPPRESSED ("no grounded-title page"; p15 is a TRUE bndry but survived via signature_block co-detection,
FN[] holds). (c) p10 (2/2) KEEP, **p4@164505881 (1/2, изх.№-only) now accepted-capped 0.60 by one-of-two
EXPLICITLY** (was luck-of-redundancy before) ✓; all 2/2 titles kept. (d) capped boundaries: confirmation
pass correctly rejects genuine low-conf non-boundaries (p18/p19@082511233), capped true starts survive.
(a) **FN3 NOT resolved.** Mechanism (165204533, a stack with p1=ЧЕЛЕН ЛИСТ cover, p3=ИЗХОДНИ ТОЧКИ title):
p2 end-detect hallucinated `signal_on_page=4` (true p3) → #2 requery forced in-window picked **p1** → gate
on p1 read `title='ЧЕЛЕН ЛИСТ' id=none` grounded=1/2 → **one-of-two accepted p1 (capped), skipping
relocation** (relocation fires only on NEITHER) → degenerate boundary at p1, p3 never reached. Relocation
WOULD have worked (search [1,2,3]−p1 → only p3 grounds a title → exactly one → relocate to p3); it was
pre-empted by the cover-sheet title on the mis-claimed page. **Proposed in-spirit fix (beyond written spec,
NOT yet implemented):** make relocation requery-aware — when #2 requeried the claim (out-of-window original →
unreliable claimed page) AND it is not BOTH-grounded, run the relocation search even on a 1/2 claim. Cleanly
separates FN3 (requeried→relocate→p3) from p4 (in-window→trust capped accept). KEPT the upgrade (net-neutral,
strictly more robust, no regression); FN3 fork surfaced to user before the stacked dev eval.

**#1-lite (skip n+1 one-page-check for signature_block/table_end) — PROBED, REVERTED per byte-gate (commit
6015f0b → revert ba9aab1).** Re-probe (`probe_1lite2.log`, md5 7985f70) byte-level vs Amendment-1 expected sets:
| File | Expected (tol0) | Got | Verdict |
|---|---|---|---|
| 163444215 | FP=[6,13] FN=[] | FP=[6,13] FN=[] | ✓ **FP31 DEAD** |
| 164505881 | FP=[9,13] FN=[12] | FP=[9,13] FN=[12] | ✓ |
| 165204533 | FP=[] FN=[3,4] | FP=[] FN=[3,4] | ✓ |
| 082511233 | FP=[] FN=[20] | **FP=[21]** FN=[20] | ✗ NEW FP21 |
tol0 F1 86.96 (TP30/FP5/FN4, unchanged — traded FP31 for FP21); tol1 F1 92.75. **FP31-death claim EVIDENCED:**
probe log `End at page 31 → doc starts at page 32 (conf=92%, signal=signature_block)` (p31 own window) — the
override is pure noise. **But** 082511233 gained FP21 (deviation beyond FP31's death) → Amendment-1 byte-gate →
**reverted immediately**, chain continues on #2+#4 (logic md5 == 63da033). ROOT CAUSE: there are TWO one-page-check
call sites — the n+1 site (gated by #1-lite) AND the OOB-projection site (NOT gated); skipping the n+1 site
rerouted p20's signature_block (signal_on_page=21, new_start=22 OOB) through the OOB-projection one-page-check,
which fired self_contained on p21 ('НАКЛОНЕН ПОКРИВ') → boundary at 21. **A correct #1-lite must gate BOTH sites
together** — deferred to its own probe cycle (backlog #1-lite v2). FP31 stays a STRICT FP on #2+#4 for now.
**Verbatim [OOB-PROJECTION] evidence (`probe_1lite2.log` lines 395–398):**
```
[OOB-PROJECTION] new_start=22 > total_pages=21 — re-evaluating
[ONE-PAGE-CHECK] p21 self_contained=True (conf=95%): The page has a clear document title ('НАКЛОНЕН ПОКРИВ' and 'ПОД НАД ЗЕМЯ') at the very top, indicating it is a self-contained document.
[OOB-PROJECTION] p21 self-contained — boundary corrected to p20
End at page 20 → doc starts at page 21 (conf=80%, signal=signature_block)
```
FP31-death evidence (`probe_1lite2.log` line 166, p31 own window): `End at page 31 → doc starts at page 32 (conf=92%, signal=signature_block)`.
**Provenance note:** `git show 9fee964:split.py | md5sum` returns a different hash than the checked-out file (a
macOS stdin-pipe artifact); the authoritative check is `git checkout 9fee964 -- split.py` → `md5sum` = **63da033**
(matches the pod + Fable's probe5 reference). split.py restored to exactly 63da033; Stage 1 relaunched on it
(`dev_stage1.log`) after a transient working-tree state (`fab0d5a`, a duplicated-comment block, logic-identical).

### FREE TP-SIDE ATTRIBUTION (no GPU) — titled_id_header: ABLATE vs GATE decision
From the saved candidate (Fix9-only) full-tests log + GT/strata/masked, each TP boundary
classified by the full set of signals that resolved to it (per-event `End at page X → doc
starts at Y (...signal=S)` lines + `[START-DETECT]`). Script `titled_tp_attribution.py`.

| stratum | titled TPs | **unique-titled** | co-detected | titled FPs |
|---|--:|--:|--:|--:|
| dev | 28 | **22** | 6 | 5 |
| holdout | 2 | **2** | 0 | 0 |
| fresh | 83 | **74** | 9 | 34 |

Co-detected (survive ablation) = 15 total, ~all signature_block/project_signoff/table_end on
the prior page. **DECISION: do NOT ablate — proceed with #4's grounding gate.** Rule was
"unique ≤~2 dev AND low fresh ⇒ ablate"; reality is 22 dev / 74 fresh unique → titled is the
single largest recall mechanism (this archive identifies docs by top title/ID, not closing
signature, so most boundaries have NO prior-page end-signal and titled is the sole catcher).
Ablation would cost ~98 unique TPs to save ~39 FPs. titled-FP=34 fresh reconciles with the
prior fresh-FP attribution (59 FPs × 58% ≈ 34) → parser validated. #4 was already built
(`559b8d7`) + probing when this ran → attribution confirms the path, no rework. run8 full-tests
still launches after the #4 experiment (answers the historical 88.5 question; ablation would not).

### TIER 1 VERDICT
Of 3 Tier-1 fixes, only **#2 (window-range validation)** is a viable kept change, and it is **net-zero on the probe**
(real value untested — kills a silent-misplacement FP class the 4 probe files don't exercise). #1 reverted (shared-prompt
bleed), #3 skipped (already implemented; target mis-attributed). **Tier 1's named FN targets (FN3, FN20) are model
localization/hallucination failures, not the logic bugs the backlog assumed** — they belong to Tier 2/3, not Tier 1.
The real lever remains **Tier 2 #4** (transcribe-then-judge anti-hallucination on `titled_id_header`) which attacks the
invented-РС№ class = 58% of fresh FPs per the attribution table. CHECKPOINT: surfaced to user (Tier 1 thinner than the
backlog predicted; cost-conscious — confirm whether to spend pod-hours on Tier 2 #4 next or pause).

---

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
> **C-tracking — one-page-check (`_query_is_self_contained`) structural-symmetry fallacy:** it asks a
> COMPLETENESS question ("is this page self-contained?") that EVERY closing page of a multi-page document
> satisfies — a top label/heading + a bottom seal/signature (FP31 proof: p31 'СЪДЕЛИТЕЛИ' heading + notary
> seal → self_contained=True → wrongly overrode the correct n+1 extension back to n). **Third instance of a
> corrective query whose FRAMING predetermines its failure**, after (1) `_query_confirm_boundary` inverted
> bias for titled signals and (2) Fix 11 v1 "yes-machine" (different=true 12/12). Pattern: a yes/no question
> whose "yes" surface-pattern is present on BOTH the boundary and non-boundary case can only rubber-stamp.
> Interim fix shipped: skip the n+1 one-page-check for signature_block/table_end (the real 31/32 cut already
> exists from p31's own window at conf 92). **One-page-check v2 (future, post-#5):** reframe from completeness
> to DIRECTION — "does the TOP of this page begin a NEW document given the previous page?" — or require a
> TITLE-GATE-grounded fresh title before any one-page self-contained verdict is allowed to move a boundary.
> **C-tracking — OOB-PROJECTION one-page-check = 4th framing-predetermined corrective query** (after (1)
> `_query_confirm_boundary` inverted bias, (2) Fix 11 v1 yes-machine, (3) n+1 one-page-check structural-symmetry
> fallacy). The OOB-projection branch runs its OWN `_query_is_self_contained` call site (never gated by #1-lite).
> Its "title at top of page?" question is satisfied by closing drawing sheets too (082511233 p21 'НАКЛОНЕН ПОКРИВ'
> is a sheet, not a doc start) → cannot discriminate boundary from non-boundary → moved truth-20 boundary to 21
> (FP21). Same root family as the n+1 site; #1-lite v2 must gate BOTH. One-page-check v2 (post-#5) reframe applies
> to BOTH call sites.
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
| **Fix9-only (A/B WINNER)** | RTX 5090 | 87.36% | 92.68% | **89.94%** | 72/91 | **+0.92 vs Fix8+9; −0.23 vs Fix 4** | — |
| Fix 11 (REVERTED) | RTX 5090 | 83.87% | 95.12% | 89.14% | 73/91 | **−0.80 vs Fix9-only → REVERT** | — |

**Fix 11 (table-confirm, commit e719049, RTX 5090) — step 4 → REVERTED.** TP=78 FP=15 FN=4. Keep rule
`tol0_F1 ≥ 89.44 (=89.94−0.5) AND FN_reduced ≥ 2`: **FN_reduced = 6→4 = 2 ✓** (recovered table boundaries
`20@082511233`, `20@142044854`; recall 92.68→95.12) but **F1 89.14 < 89.44 ✗** → AND fails → **REVERT**.
Cause: the table-confirm fired 12× and answered different=True EVERY time (too permissive) — recovered 2 real
boundaries but added 4 FPs (`35,37@163444215`, `19@082511233`, `5@085108460`). Per-[TABLE-CONFIRM]: 2 TP
(20@082511233, 20@142044854) + the 4 FPs above + 6 fires on already-detected/correct boundaries. main reverted
to Fix9-only. **Open question (morning): table-confirm needs a stricter "continues numbering" branch to cut FPs
without losing the 2 recovered boundaries.**

**A/B verdict (step 3): WINNER = Fix9-only.** Rule `argmax tol0_F1 {Fix8+9=89.02, Fix9-only=89.94}` → Fix9-only
(89.94 > 89.02, not a tie). Recall 92.68% vs Fix8+9 89.02% confirms Fix 8's confirmation routing was costing
recall (inverted titled bias). Reconcile: 9181a66 (Fix 8) reverted on main → main = Fix9-only. Fix9-only
163444215 FP=[6,11,13,19,27,31] (drawing-block removed 20,21; 11,19,27 survived exclusions); p4 preserved.
Fix9-only still −0.23 vs Fix 4 — cumulative-best (step 5) decided after Fix 11.

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

## EXPERIMENTAL — Fable 5 single-file boundary benchmark (NOT comparable to GPU rows)

> **⚠ NOT a fix-chain row.** Different model (claude-fable-5 via Agent-tool subagents, no
> greedy-decoding determinism guarantee), n=1 file, single run. Informs the cascade decision only.
> Full report: `fable5_run/diff_report.md`; raw responses: `fable5_run/163444215_raw.log`.

| Stage | model | file | P | R | F1 (tol0=tol1) | TP/FP/FN | notes |
|-------|-------|------|---|---|----------------|----------|-------|
| Fable 5 replay (EXPERIMENTAL) | claude-fable-5 | 163444215 (37p) | 66.67% | **100%** | **80.00** | 16 / 8 / 0 | FP=[6,13,16,17,18,19,20,21]. Same file, candidate 32B: P=72.73 R=100 F1=84.21 (FP=[6,11,13,19,27,31]). |

- **Strict parity replay** of `split.py` @ `round1-candidate` (Fix9-only): pipeline's own 150-DPI
  rendering + OSD rotation (all 37 pages → 0°), verbatim prompts, same window/routing/threshold logic
  executed by the candidate's own code; only `_infer` redirected to fable subagents (81 queries:
  72 base + 9 corrective). No GT leakage to subagents.
- **Confabulated-identifier FPs 11, 27, 31 all FIXED** — Fable 5 returns grounded `end=false` citing
  text that actually exists (p11 `стр. 2 от 2` + Скица № 15-158202; p27 deed body mid-list; p31
  СЪДЕЛИТЕЛИ/НОТАРИУС signature page of the deed). p10 and p4-class boundaries HOLD; FN=0 (recall 100%).
- **New failure mode: form-instance over-split** — the ЕСУТ review-slip stack (GT: one doc, 15–21)
  splits at every slip (FPs 16,17,18,20,21 + shared FP 19) via `header_block_reset`, which Fix9-only
  exempts from the confirmation pass at any confidence. Shared GT-convention FPs 6 and 13 reproduce
  in both models. Without the slip cluster Fable 5 would be FP=[6,13] → F1 94.1 on this file.
- **Cost/latency (subagent path):** 981k subagent tokens ≈ $10–16 total ≈ **$0.30–0.45/page**;
  avg 21.4 s/query, 47 s summed query time/page (base queries parallelizable). 1/81 responses
  malformed JSON (absorbed by the pipeline's parse-failure path, but no determinism across runs).
- **Cascade implication:** Fable 5 as arbiter looks strongest exactly where the 32B hallucinates
  (identifier-grounding seams), not as a wholesale replacement — its slip-stack granularity would
  need either a GT-convention decision or a repeated-form suppression rule before any cascade gains
  show up in F1.
