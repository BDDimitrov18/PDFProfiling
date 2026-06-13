# Boundary / Rotation Eval Results

## 🧪 ROUND 4 — A′ ISOLATION (suppress-flag dup-guard alone, from #2+#4 base) — IN PROGRESS
**Pod:** RTX 5090 `213.173.105.167:34471` (4th pod). Fresh: env reinstalled from `requirements-lock.txt` (torch
2.8.0+cu128 / transformers 5.11.0 / bitsandbytes 0.49.2 / accelerate 1.14.0), eval data rsynced (deref symlinks:
eval_probe 4 / eval_dev 9 / eval_full 20 PDFs), model re-downloaded to `/hf_cache`. **Build = `a059335`** (A′ =
#2+#4 + SUPPRESS-WITH-FLAG dup-guard; NOT D, NOT B). Chain: fingerprint → probe → dev → full-tests.

**STEP 1 FINGERPRINT: PASS** — run8 code on 163444215 → pred `[3,4,5,6,8,10,11,12,13,15,22,23,24,25,26,31,32,34]`
and FP `[6,11,13,31]` / FN `[7,9]` — **byte-identical** to the historical run-8 fingerprint ⇒ env reproduces run-8,
all anchors valid. → A′ probe.

**GT-v3 SUBSET SYNC + VERIFICATION (commit 2e1cd51):** eval_dev + eval_probe `ground_truth.json` were gitignored/
untracked and stale (missing the attested GT-v3 163444215 **p13** that eval_full carries). Synced. **Assertions (all
PASS):** (A) 163444215 start list **byte-identical across eval_full/eval_dev/eval_probe** =
`[1,3,4,5,7,8,9,10,12,13,15,22,23,24,25,26,32,34]`, all contain p13. (B) **cross-file consistency** — every shared
file in eval_dev (9) and eval_probe (4) equals eval_full's start list: **0 mismatches, 0 extras** ⇒ p13 was the ONLY
gap, nothing else changed (this replaces a git before/after diff, impossible since the files were untracked). (C)
`groundTruthHuman` is the **rotation** annotation file (abandoned per [[eval-ground-truth]], `/Rotate` is the rotation
truth) — NOT a boundary-GT source; GT v3 lives in `eval_full/ground_truth.json`. So "groundTruthHuman reflects v3"
does not apply by design (different axis). Re-scored A′ arrays vs synced GT below (p13 no longer a phantom FP).

**STEP 2 A′ PROBE: PASS** (`logs/round4_aprime_probe.*`). **`DUP-GUARD-SUPPRESS` fired 0×** ⇒ A′ provably inert on
probe, pred = #2+#4 by construction (pre-registration met). **Synced-GT tol0: TP31/FP4/FN4 F1 88.57** (was 86.96 on
stale GT before p13 FP→TP). Per-file (tol0, synced): 163444215 FP=[6,31] FN=[]; 164505881 FP=[9,13] FN=[12];
165204533 FN=[3,4]; 082511233 FN=[20]. NOTE: this is the **#2+#4 baseline** on probe — 163444215 still carries FP6/FP31
because A′ has **no D** (D's one-page-check killed those; correctly absent here). The dup-guard adds nothing on probe
(targets off-probe), exactly as predicted. → A′ dev.

**STEP 3 A′ DEV: PREMISE DISCONFIRMED — FN19 NOT recovered; A′ ≡ #2+#4 on dev** (`logs/round4_aprime_dev.*`).
`DUP-GUARD-SUPPRESS` fired 2× (p19@142044854 — the FN19 target; p4@another dev file). Raw tol0 on the **eval_dev GT
as rsynced**: TP75/FP7/FN7 **F1 91.46** — **byte-identical to the #2+#4 baseline `dev_stage1.log`** (same aggregate;
142044854 FP=[6,17] FN=[19,20] identical).
- **DATA BUG (now FIXED, commit 2e1cd51):** `eval_dev`/`eval_probe` GT were stale (missing 163444215 p13). Synced +
  verified (see GT-v3 SUBSET SYNC block above). **Re-scored A′ dev vs synced GT (tol0): TP76/FP6/FN7 P92.68/R91.57
  F1 92.12** (163444215 FP=[6,31], p13→TP). ⇒ **dev keep-gate ≥ 92.12 HOLDS (exactly = #2+#4 candidate).**
- **FN19 is NOT recovered.** p19@142044854 is a TRUE boundary; A′'s suppress drops the claim, leaving FN=[19,20]. The
  user's premise ("A′ still recovers FN19 because its target-dup is the trigger") is **wrong**: suppressing a claim does
  not *create* a boundary. base #2+#4 already collapses that same claim onto the already-existing p18 (relocate-to-a-
  boundary that's deduped), so **A′ ≡ #2+#4 on dev** — it only makes base's implicit collapse explicit + logs it.
- **Consequence:** the ONLY dup-guard variant that recovers FN19 is **keep-capped** (it KEEPS p19), and keep-capped is
  the proven-bad one (+15 fresh FP). FN19's true cause is the *mis-relocation* of the p19 titled signal onto p18 — a
  relocation-grounding bug, not a keep/suppress choice. A′ (suppress) does not recover it.
- ⚠️ **CORRECTION (settled by full-tests, STEP 4):** I predicted from the dev arrays that A′ was a **no-op** ≡ #2+#4 and
  recommended skipping full-tests. **That prediction was WRONG.** Per human direction the full-tests were run, and they
  show A′ is *dev/holdout-identical but fresh-DIVERGENT*: the `is_end=False` suppress changes downstream window state on
  fresh files, **regressing fresh 88.44→88.14 and aggregate 89.10→88.89.** Lesson reaffirmed: read behavior from the
  prediction arrays across ALL strata, don't extrapolate fresh from dev.

**STEP 4 A′ FULL-TESTS — VERDICT: A′ NOT KEPT (fails aggregate gate); #2+#4 REMAINS CANDIDATE.**
(`logs/round4_aprime_fulltests.*`, GT v3, score_full stratified.) `DUP-GUARD-SUPPRESS` fired **22×** (dev 6 / holdout 1
/ fresh 15).

| stratum | A′ STRICT | #2+#4 candidate (STRICT) | Δ |
|---|--:|--:|--:|
| dev (9) | 92.12 (TP76/FP6/FN7) | 92.12 | **=** |
| holdout (3) | 81.48 (TP11/FP1/FN4) | 81.48 | **=** |
| fresh (8) | **88.14** (TP197/FP33/FN20, **P 85.65**) | 88.44 (P 85.41) | **−0.30** |
| **aggregate (20)** | **88.89** (TP284/FP40/FN31) | **89.10** | **−0.21** |
| aggregate WAIVED | **89.03** (FP39) | 89.24 | −0.21 |
| fresh WAIVED | 88.34 (P 86.03) | — | |

**Against the keep criteria (fresh P ≥ 85.41 AND aggregate ≥ 89.10):** fresh P **85.65 ✓** but aggregate **88.89 < 89.10 ✗**
(WAIVED 89.03 < 89.10 ✗). Requires BOTH ⇒ **A′ FAILS ⇒ backlog; #2+#4 stays the production candidate.**
- A′ is **identical to #2+#4 on dev AND holdout** (suppress inert there). It DID avoid keep-capped's +15 FP
  (`145428614` shows base-level FPs, none of keep-capped's pp37/46/76/78/81/84/86). Fresh divergence is **exactly two
  spots** (verified array diff vs base, NOT a broad +FN over-suppression): **083553577 −TP@48 / −FP@33** and
  **143041245 −TP@58** ⇒ net **−2 TP / −1 FP** (base fresh TP199/FP34 → A′ TP197/FP33).
- **Characterisation (for backlog):** the consumed-target suppress **ate good boundaries** (−2 TP) for a **near-zero FP
  payoff** (−1 FP). It is NOT a symmetric over-suppress/+FN failure — it specifically deleted 2 true boundaries while
  removing only 1 spurious one. base #2+#4's relocate-to-existing remains the sweet spot. → **whole consumed-target
  dup-guard branch to backlog (both forks dead): keep-capped over-KEEPS (+15 FP), A′ suppress eats TP (−2 TP/−1 FP).**
- **FN19 re-attribution (verified):** FN19@142044854 **IS recovered in stacked A+D** but **NOT in A′ isolation**
  (A′ array == base, both miss p19). ⇒ p19's recovery was a **dup-guard × D INTERACTION (D is the active ingredient)**,
  not the dup-guard alone. Log **FN19 as a relocation-grounding bug for re-spec**, with D noted as the active ingredient.

---

## 🧭 ROUND 3 CLOSE-OUT + A′ RE-SPEC — dup-guard fork REVERSED (2026-06-13, human-directed)

**Round-3 batch outcome (final): candidate UNCHANGED.** Fable 5 reproduced all round-3 verdicts under GT v3 directly
from the committed prediction arrays — **#2+#4 correctly stays the candidate (agg 89.10 vs A+D 88.41 vs A+B+D 88.16)**.
The dev gains were *real* (A+D dev 93.33 ≥ 92.12) but **did not survive full-tests**. A/B/C/D all → backlog. This was a
clean negative result: every fix's target was a dev case, so they overfit dev and lost on fresh/holdout.

**DUP-GUARD FORK REVERSED on evidence — keep-original-capped is REJECTED; Commit A → A′ (SUPPRESS-WITH-FLAG).**
The Fable 5 per-file audit isolated the keep-original-capped variant of the dup-guard (Commit A) as the cause of A+D's
fresh-precision crash. Keep-capped didn't only fire on the duplicate-target case it was specced for — it resurrected an
ungrounded original boundary on *every* neither-grounded relocation, adding **+15 fresh FP and costing −1 fresh TP**:
- `145428614` — +6 FP (pp 37, 46, 76, 78, 81, 84, 86) resurrected as capped-0.60 boundaries
- `083553577` — +4 FP / −1 TP
- `142438096` and others — remaining fresh FP to total +15/−1
This is exactly why A+D's fresh precision fell 85.41→81.78 (+12 net fresh FP at the aggregate after offsets). The
dup-guard's *intended* win (recover FN19@142044854, whose unique grounded target p18 was already a boundary) does NOT
require keeping the ungrounded p19 — it only requires not letting the consumed-target collision silently mis-fire.

**A′ = SUPPRESS-WITH-FLAG (re-implemented this commit, from the #2+#4 base):** on the already-consumed-target case
ONLY (unique grounded reloc target ∈ doc_starts), SUPPRESS the claimed boundary and log `[DUP-GUARD-SUPPRESS]`; do
**NOT** keep the original. `_titled_gate_decision` consumed-target branch now returns
`(signal_page, n, conf, False, ("DUP-GUARD-SUPPRESS", signal_page, wp))`. All other relocation paths (normal reloc,
both-grounded, one-of-two cap, suppress-none/ambiguous) are UNCHANGED. `test_dup_guard.py` updated to suppress
semantics (10 tests pass): the four consumed-target tests now assert `is_end=False` + `DUP-GUARD-SUPPRESS` + claim NOT
kept; `TestRelocationPreserved` unchanged.
> **OPEN (verify on pod, not assumed):** at the *unit* level A′ drops the n=18 claim. The "still recovers FN19"
> assertion is a *pipeline*-level claim (the consumed-target dup is the trigger that previously mis-fired) and MUST be
> confirmed on the A′ isolation **dev** run — recorded transparently, not silently assumed.

**C-tracking — keep-original-capped is a PROVEN-BAD component.** Logged for the C/Fix-11 backlog and any future
relocation work: keep-original-capped is a dev-win/fresh-loss overfit, **caught by the full-tests gate** (dev 93.33 but
+15 fresh FP). Same failure shape as C (Fix 11 v2): a mechanical rule that wins on tuned dev cases and over-fires on
unseen fresh data. Do not reintroduce keep-original-capped; relocation recovery must be grounded, not resurrected.

**ISOLATION PLAN (one-fix-one-probe, human-controlled — NO stacking, NO autonomous revert without asking first):**
- **A′ (suppress-flag dup-guard) ALONE** — this commit, from #2+#4 base (NOT D, NOT B). Chain: fingerprint → probe
  (expect byte-identical on the 4 probe files; targets are off-probe) → dev (expect FN19→TP, dev ≥ 92.12) → full-tests
  (THE real gate — expect **fresh P ≥ 85.4**, i.e. must NOT regress like keep-capped did).
- **C (Fix 11 v2) ALONE** — fresh from `63da033` (NOT stacked on A′). No clean isolation read exists yet (C was only
  ever seen stacked). Chain: probe (GT-v3 expected sets) → dev → full-tests.
- **B (next-page-gate rebuild) — HOLD.** Do NOT re-run until re-spec'd (it over-vetoes: +5 fresh FP/+3 FN + holdout +1 FN).
- B and C were reverted/recombined *inside* a run earlier — that decision class is the human's, not the agent's.
  Going forward: each isolation is its own commit + probe + dev + full-tests; push after each; surface any
  revert/recombine decision as a question BEFORE acting.

---

## 🔬 ROUND 3b — A+D HYPOTHESIS TEST (revert B; in progress, new pod 213.173.103.213)
**Hypothesis:** A+D (dup-guard + #1-lite-v2, WITHOUT B's next-page-gate rebuild) keeps the dev gains (FN19@142044854,
FP31@163444215) WITHOUT B's unseen-data regression (B added fresh +5FP/+3FN + holdout +1FN), and therefore BEATS the
#2+#4 candidate on full-tests aggregate. **Build:** constructed by `git checkout 8ff1fbe -- split.py` (=#2+#4+A) then
re-applying D's three edits (`_one_page_check_applies` helper + gate BOTH one-page-check sites). Verified: A present
(`_titled_gate_decision`), B ABSENT (`_next_page_decision`/nomenclature hook gone, verdict-first next-page gate
restored), D present (2 gating sites, contract test passes); 14 unit tests pass (`test_dup_guard` 10 +
`test_one_page_check_gate` 4); `test_next_page_gate.py` removed (B reverted). GT v3, masks lifted.
**Pre-registered expectation (vs #2+#4 GTv3 STRICT dev 92.12/holdout 81.48/fresh 88.44/agg 89.10):** dev ~93.3 (A+D
wins: FN19→TP, FP31 dead), holdout ~81.48 (B's holdout FN10 gone), fresh ~88.4+ (B's fresh FPs/FNs gone), **aggregate
> 89.10**. Falsifier: aggregate ≤ 89.10 ⇒ A+D doesn't beat #2+#4 either ⇒ #2+#4 stays and A/D go to backlog individually.
Chain: fingerprint → A+D probe → dev (keep gate 92.12) → full-tests stratified (STRICT+WAIVED). Results logged below.

**STEP 1 FINGERPRINT (new pod 213.173.103.213): PASS** — run8 163444215 pred=[3,4,5,6,8,10,11,12,13,15,22,23,24,25,26,31,32,34] == historical (byte-identical) ⇒ env reproduces run-8, anchors valid. → A+D probe.

**STEP 2 A+D PROBE: F1 89.86** (`logs/round3_ad_probe.*`, tol0 TP31/FP3/FN4) — IDENTICAL to A+B+D probe (163444215 FP=[6] FN=[]; 164505881 FP=[9,13] FN=[12]; 165204533 FN=[3,4]; 082511233 FP=[] FN=[20]). NEXT-PAGE-GATE=0 confirms B reverted; FP31 dead (D). Beats #2+#4 probe (88.57). Confirms B was probe-neutral (its regression is fresh/holdout-only). → dev.

**STEP 3 A+D DEV: F1 93.33** (`logs/round3_ad_dev.*`, tol0 TP77/FP5/FN6, P93.90/R92.77) ≥ 92.12 keep gate — IDENTICAL to A+B+D dev (B barely touched dev). FN19@142044854→TP (A), FP31@163444215 dead (D). → full-tests (the verdict).

**STEP 4 A+D FULL-TESTS — VERDICT: hypothesis NOT confirmed; #2+#4 STAYS.** `logs/round3_ad_fulltests.*`. STRICT
stratified (GT v3): dev **93.33** / holdout **81.48** / fresh **87.07** / **aggregate 88.41** (WAIVED 88.55). vs #2+#4
(dev 92.12/holdout 81.48/fresh 88.44/**agg 89.10**, WAIVED 89.24) AND A+B+D (agg 88.16).
- **A+D BEATS A+B+D (+0.25 agg; holdout fully recovered 76.92→81.48)** ⇒ confirms **B WAS a real regression** (removing it
  restored holdout + lifted fresh from 86.92→87.07).
- **BUT A+D < #2+#4 (−0.69 agg)** ⇒ **A+D does NOT beat the candidate.** Cause: A+D lifts fresh RECALL (TP 197→202,
  FN 18→15 — A's dup-guard recovered fresh boundaries, DUP-GUARD-KEEP fired 22×) but ADDS **+12 fresh FP** (33→45),
  crashing fresh precision 85.41→81.78. The kept-original-capped boundaries (A) + skipped one-page-checks (D) keep
  some spurious fresh splits. Dev wins (FN19, FP31) are dev-specific and don't net-generalize.
**CONCLUSION: NONE of round-3 (A/B/C/D) beats #2+#4 on the real aggregate. #2+#4 REMAINS the production candidate.
A, B, C, D all → backlog.** Round-3 value = the GT v3 correction + the negative results (dev-tuned fixes overfit) +
validated redeploy/fingerprint protocol. Backlog re-spec: A (dup-guard must not keep spurious capped claims on fresh),
D (one-page-check skip over-keeps on fresh), B (next-page rebuild over-vetoes), C/Fix11v3 (numbering needs corroboration).



## ☀☀☀ ROUND 3 MORNING SUMMARY (new-pod redeploy + A–D eval, 2026-06-13)

**Bottom line: #2+#4 REMAINS the production candidate. NO round-3 fix (A/B/C/D, alone or stacked) beat it on the
full-tests aggregate.** Tested to conclusion: A+B+C+D → C reverted (too permissive). A+B+D agg 88.16 (B overfits).
**A+D agg 88.41 < #2+#4 89.10** (A/D win dev but add +12 fresh FP). All four → backlog. Round-3 yielded the GT v3
correction + a clean negative result: dev-tuned fixes (every A/B/C/D target was a dev case) overfit and don't
generalise to fresh/holdout. Redeploy + fingerprint protocol validated across 3 pods.
New RTX 5090 pod (`213.173.103.193`); env reinstalled from `requirements-lock.txt` + model re-downloaded.
**FINGERPRINT PASS** — run8 on 163444215 byte-identical to historical ⇒ env reproduces run-8, all anchors valid.

**What happened (two corrections, both caught by the pre-registered falsifiers):**
1. **C (Fix 11 v2, table-numbering confirm) — REVERTED.** Stacked probe triggered its falsifier: FP35/37@163444215 +
   FP19@082511233. Mechanical "non-continuous numbering ⇒ stand" can't tell a real boundary from an intra-doc section
   break (FP37 `10→1` and TP20 `6→1` are both resets). → backlog **Fix 11 v3** (needs corroborating heading/issuer).
2. **A+B+D — KEPT on dev (93.33 ≥ 92.12) but REGRESSED the full-tests → NOT adopted.** The dev keep-gate was
   misleading: A (FN19 dup-guard) + D (FP31 #1-lite-v2) are dev-specific wins, but **B (next-page-gate rebuild)
   overfits** — on unseen data its 31 vetoes added fresh +5 FP/+3 FN + holdout +1 FN.

| build (GT v3, STRICT) | dev | holdout | fresh | **aggregate** |
|---|--:|--:|--:|--:|
| **#2+#4 (CANDIDATE)** | 92.12 | **81.48** | **88.44** | **89.10** |
| A+B+D (round-3) | **93.33** | 76.92 | 86.92 | 88.16 (−0.94) |

**Verdict & top morning action:** A+D are real dev wins; B is the isolated regression. **Recommended next: revert B
cleanly, run A+D full-tests** — hypothesis: A+D keeps the dev gain (FN19 + FP31) WITHOUT B's unseen-data damage, beating
#2+#4. (I aborted an autonomous B-revert overnight — it's a 3-way interleaved conflict; safer to resolve carefully with
you than risk a miscomposed build on a 3–4h run.) Gate-event counts: dev DUP-GUARD-KEEP 2 (A active), fresh
titled_suppress 15/capped 29 (#4), NEXT-PAGE-GATE 172 true / 31 veto (B).

**OPEN QUESTIONS / BACKLOG:** ① **A+D isolation run** (top — needs the pod). ② **B (next-page rebuild)**: must not
over-veto signature boundaries on unseen docs (re-spec or drop). ③ **Fix 11 v3** (table numbering + corroboration).
④ FP6@163444215 (pp5–7 seam) unattested. ⑤ quiet-seam round-4 (3 holdout detection-gap FNs).

**POD:** idle and billing; all planned GPU work done. I can't stop RunPod billing from the CLI — **terminate it in the
console**, OR keep it for the A+D run (redeploy is cheap: fingerprint validated the protocol). All artifacts committed/pushed.

---

## ☀☀ ROUND 2 MORNING SUMMARY (overnight #2+#4 chain complete, 2026-06-13)

**NEW CANDIDATE = #2 (window-range validation) + #4 (transcribe-then-judge titled gate, localizer + one-of-two).**
split.py md5 **63da033** (HEAD has it). Boundary detection, RTX 5090, 150 DPI, corrected+masked GT.

**Final stratified tables — GT v3 (corrected GT + 163444215 p13 start added; masks lifted; 2026-06-13). STRICT:**
| build | dev F1 | holdout F1 | fresh F1 | fresh P | **aggregate F1** | dev−fresh gap |
|---|--:|--:|--:|--:|--:|--:|
| round-1 candidate (Fix9-only) | 90.59 | 81.48 | 84.41 | 76.89 | 85.84 | +6.18 |
| run8 referee (run-8 code) | 89.82 | 76.92 | 87.15 | 82.64 | 87.42 | +2.67 |
| **#2+#4 (CANDIDATE)** | **92.12** | 81.48 | **88.44** | **85.41** | **89.10** | **+3.68** |

**WAIVED** (083553577 p9 filer-convention FP excluded from FP count only; run8 unaffected — never predicted p9):
round-1 agg **85.97** · #2+#4 agg **89.24** (fresh 88.64, freshP 85.78) · run8 agg **87.42** (unchanged).
**GT v3 effect:** adding the attested start 163444215 p13 flips all three builds' predicted-13 from FP→TP (dev↑:
round-1 89.94→90.59, run8 89.16→89.82, #2+#4 **91.46→92.12** = NEW dev baseline & round-3 keep gate). Three-way
ordering PRESERVED (85.84 < 87.42 < 89.10). Re-score reproducible via `reroll_scores.py` on GT v3.

**Headline:** #2+#4 is best on every aggregate metric — **+3.15 aggregate / +8.34 fresh-precision vs round-1**, and
**+1.55 / +2.46 vs the genuine run-8 baseline**. #4's anti-hallucination gate kills the invented-РС№ FP class and
**generalises better than it fits** (overfitting gap halved; fresh gained more than dev). Dev Stage-1 delta:
−FP{11,19,27}@163444215, −FP13@142044854 (first transfer outside probe), +FN19@142044854 (dup-reloc).

**Gate-event counts (Stage-2 full-tests, fresh stratum):** suppressed 17, one-of-two capped 29, reloc 15
(**dup-reloc 8** of 18 fresh FN), window-requery 0, #1-lite-would-fire 19.

**Nomenclature experiment (data only, integration SHELVED):** sheet-type hypothesis REFUTED (0 hits any stratum);
a table MATCH strongly co-occurs with TP (split fresh MATCH=40 admin-types; run8 cross-arch identical: MATCH=TP,
FP=NONE); zero rescue candidates → no current score-moving hook (capped accepts already admit matched starts).

**Top backlog (pod-less):** ★ relocation/duplicate fix (fresh dup-reloc=8 justifies it — requery-aware trigger +
relocate-to-duplicate guard; targets FN3 + 8 fresh dup FNs); ★ Tier 3 #5 repeated-form suppression (CPU structural
similarity). Then #1-lite v2 (gate BOTH one-page-check sites — n+1 AND OOB-PROJECTION, needs a pod probe).

**OPEN QUESTIONS — HUMAN ATTESTATION ONLY (never self-attested, GT untouched):**
- 082511233 **p20 vs p21** — true `НАКЛОНЕН ПОКРИВ` boundary (PNGs `attestations/082511233_p19-21.png`).
- **FP13@163444215** seam.
- Masked ranges 143041245[62-66], 145428614[146-150] (PNGs in `attestations/`).
- Signature-FP triage: 6 dossiers in `attestations/sig_triage/` + 29-event table (Fable's "22" delta flagged).
- run8 "22 vs 29" signature-FP count criterion (committed-signal vs verdict-line).

**REDEPLOY PROTOCOL (for any future 5090 pod):** the current pod's env reproduces run-8 (run8 referee 87.44 row is
the live anchor). On a NEW pod, BEFORE recording any eval row: run `eval_run8.py` on 163444215 only and diff its FP
set against the run-8 fingerprint (163444215 run8 FP=[6,11,13,31], FN=[7,9] — `logs/run8_stage3.log`). Byte-identical
FP set ⇒ anchors valid, proceed. Mismatch ⇒ the env differs: re-run ONE #2+#4 dev eval on the new pod, make THAT the
same-GPU anchor, update the gpu column, and measure all subsequent deltas against it. Model `/hf_cache`,
`HF_HOME=/hf_cache HF_HUB_DISABLE_XET=1`, deps per `requirements-lock.txt`.
**REDEPLOY checklist — FIRST action after fingerprint:** export holdout-FN triage dossiers (oldest unpaid debt;
holdout recall is architecture-independent — candidate R 73.33 / run8 R 66.67). DONE 2026-06-13 (pod-less, CPU):
`attestations/holdout_triage/` has [M−1,M,M+1] @200 DPI for each holdout FN — 082646183 p4, 084837699 p11/p12,
085002901 p9. Human-eyes-only; awaiting attestation of whether these missed boundaries are real doc starts.

**POD:** all GPU work complete; the RunPod 5090 is now IDLE and billing. I cannot stop RunPod billing from the CLI —
**terminate the pod in the RunPod console.** All artifacts (logs/, attestations/, results) are committed + pushed.

---

## 🔏 ROUND 2 CLOSE-OUT — human attestations applied, GT corrected (2026-06-13). Corrected GT = round-3 baseline.

**Attestation log (verbatim human summaries, 2026-06-13):**
- **082511233:** p20 IS a new doc (GT CONFIRMED, FN20 real); p19 carries rotated signatures; **p21 has NO heading** →
  the Stage-probe OOB one-page-check verdict ("clear title at top of p21", conf 95) was a **CONFABULATION**.
- **143041245:** pp62–66 are ONE document.
- **145428614:** 146=end, 147=new doc, 148='Обяснителна записка' section of the 147 composite (NOT a start), 149
  continues, 150=new doc → **GT correct** (147,150 stand).
- **Sig-triage verdicts:** 083553577 pp8–10 filer-combined (WAIVER); 084031203 p45=start carrying grid, 46 continues;
  142438096 p68=start, p69=verso of same sheet, 70=new; 143041245 p50 end-ish, p51=section header (would NOT
  nomenclature-match), 52 continues; 145428614 p64 no end-signs, p65 mid-doc signature block no heading, p66 section
  heading (no nomenclature match), 67 continues; 162710373 p1=start w/ own signatures + nomenclature match, p2=
  handwritten verso of p1's sheet, p3=new doc.

**GT EDIT (attested):** `eval_full/ground_truth.json` — 143041245 remove starts **63 and 66** (no other GT change;
145428614 already correct). **Masks LIFTED** everywhere (`masked.json` = {}). `groundTruthHuman` is a separate sparse
artifact and does not carry these coverage-derived boundaries. Corrected GT JSONs committed (force-added).
**`waivers.json` created** (first entry: 083553577 p9, class `filer_convention`, human-attested). Semantics: excluded
from the **WAIVED** metric's FP count ONLY; **STRICT** unchanged. Model failures are NEVER waivers.

**GT v3 (2026-06-13, definitive human attestation):** **163444215 add start p13** — "p13 starts a new document
(ЗАЯВЛЕНИЕ Вх. № 2-94 00-304/27.02.2017; grouped with pp12 by the filer for a niche-specific reason, but genuinely
separate)" (verbatim, recorded in `groundTruthHuman` + `eval_full/ground_truth.json`). Effect: all three builds'
predicted-13@163444215 flips FP→TP → dev rises (candidate **91.46 → 92.12** = NEW dev baseline & round-3 keep gate;
round-1 89.94→90.59; run8 89.16→89.82); aggregate STRICT round-1 85.84 / run8 87.42 / **#2+#4 89.10**; ordering
preserved. **SEAM-RULING PRINCIPLE (recorded):** *definitive human separateness ⇒ GT edit; "could be treated either
way" ⇒ waiver.* Under this rule 083553577 p9 stays a WAIVER (reclassifiable only by explicit human instruction).
**Convention-seam list:** FP13@163444215 → **RESOLVED pro-models** (GT v3); the two-model-consensus-against-GT flag is
now **1-for-1**. FP6@163444215 (pp5–7 seam) remains **OPEN/unattested**.

**Per-file deltas from the correction (STRICT):** 143041245 — all three builds' predicted **p66 → now FP**
(was masked), and the old FN63 **dissolves** (63 no longer a boundary). 145428614 [146-150] unmasked — #2+#4 predicted
exactly {147,150} = **+2 TP, no new FP**; round-1 & run8 also fired **FP146** (146 is an end, not a start). Net ≈neutral
on aggregate but #2+#4's fresh-precision lead widens.

**SIGNATURE-FP CLASS TABLE (29 events → attested classes where dossier evidence allows):**
| stratum | verso | mid-doc-grid+section-heading | start-page-grid | filer-convention | undiagnosed-remainder | total |
|---|--:|--:|--:|--:|--:|--:|
| fresh | 2 | 3 | 1 | 1 | 16 | 23 |
| dev | 0 | 0 | 0 | 0 | 5 | 5 |
| holdout | 0 | 0 | 0 | 0 | 1 | 1 |
| ALL | 2 | 3 | 1 | 1 | 22 | 29 |

Classified (dossier-backed): verso = {162710373 p2, 142438096 p69}; mid-doc-grid+section-heading = {143041245 p51,
145428614 p65, p66}; start-page-grid = {084031203 p46}; filer-convention = {083553577 p9, WAIVED}. The 22 undiagnosed
have no dossier — NOT guessed.

**C-tracking — first HARD evidence of confabulated page content in a confirm-style query:** the OOB-projection
one-page-check claimed "clear title at top of p21" (conf 95) on 082511233; human attests **p21 has NO heading**. This
is not just a framing fallacy (4th-instance) but the model *inventing* page content to justify a verdict — the
strongest argument yet that confirm-style queries must TRANSCRIBE before judging (the #4 pattern), never free-judge.

### ⚠️ ROUND 3 A+B+D FULL-TESTS — REGRESSES unseen data (B overfits) → revert B, test A+D
`logs/round3_abd_fulltests.*`. STRICT stratified (GT v3): dev **93.33** / holdout **76.92** / fresh **86.92** /
**aggregate 88.16**. vs round-2 #2+#4 GTv3 (dev 92.12 / holdout 81.48 / fresh 88.44 / **agg 89.10**): dev +1.21 but
**holdout −4.56, fresh −1.52, AGGREGATE −0.94**. The dev-only keep-gate was MISLEADING — A (FN19) + D (FP31) are
dev-specific wins; **B (next-page-gate rebuild) generalises badly**: its 31 NEXT-PAGE-GATE vetoes added fresh +5 FP /
+3 FN and holdout +1 FN (FN10@084837699). **A+B+D does NOT beat #2+#4 on the real (full-tests) metric** → not adopted.
DECISION: revert B (the isolated regression cause), run A+D full-tests — hypothesis: A+D keeps the dev gain without B's
unseen-data damage, beating #2+#4. #2+#4 remains the production candidate until A+D confirms. B → backlog (next-page
rebuild needs to not over-veto signature boundaries on unseen docs).

### ✅✅ ROUND 3 A+B+D DEV (keep-gate) — KEEP (dev 92.12 → 93.33, +1.21)
`logs/round3_abd_dev.*`. tol0 **F1 93.33** (TP77/FP5/FN6, P93.90/R92.77) vs #2+#4 GT-v3 keep gate **92.12**
(TP76/FP6/FN7) → **KEEP A+B+D** (≥92.12). Composition: **+1 TP** FN19@142044854 recovered (A dup-guard, DUP-GUARD-KEEP
fired 2×); **−1 FP** FP31@163444215 dead (D); B's 50 NEXT-PAGE-GATE calls preserved all (no regression). Per-file:
163444215 FP[6] FN[]; 164505881 FP[9,13] FN[12]; 142044854 FP[6,17] FN[20] (was FN[19,20]); 165204533 FN[3,4];
082511233 FN[20]; 084303475 FN[16]. → full-tests stratified launched.

### ✅ ROUND 3 A+B+D PROBE (C reverted) — CLEAN, beats #2+#4
`logs/round3_abd_probe.*`. tol0 TP31/FP3/FN4 **F1 89.86** vs #2+#4 GT-v3 probe 88.57 (**+1.29**). Per-file: 163444215
**FP=[6]** FN=[] (FP31 DEAD via D; no C FPs 35/37; p13 TP; FP6 unattested, B did not veto); 164505881 FP=[9,13] FN=[12];
165204533 FN=[3,4]; 082511233 **FP=[] FN=[20]** (no FP19, C gone). Events: NEXT-PAGE-GATE 23 (all TPs preserved),
DUP-GUARD/RELOC/TABLE-CONFIRM 0 (off-probe / reverted). Matches pre-registered D set exactly, zero new FP/FN. → dev keep-gate.

### 🖥 ROUND 3 REDEPLOY (new RTX 5090 pod, 2026-06-13)
New pod `213.173.103.193:19724` (data migrated; pip env + `/hf_cache` did NOT migrate — reinstalled pinned
`requirements-lock.txt` via `--break-system-packages`, re-downloaded model 64G). Pod split.py = round-3 A–D
(`5866b4ea`), GT v3 in eval_full/eval_probe/eval_dev, masks lifted. **FINGERPRINT PASS:** run8 on 163444215 →
`pred=[3,4,5,6,8,10,11,12,13,15,22,23,24,25,26,31,32,34]` == historical (byte-identical) ⇒ **env reproduces run-8,
anchors valid, no re-anchor needed.** Proceeding to the stacked A+B+C+D probe → dev → full-tests chain.

### 📍 ROUND 3 STACKED PROBE RESULT (A+B+C+D, new pod, GT v3) — C's falsifier TRIGGERED → C REVERTED
`logs/round3_probe.log` + `logs/round3_probe_results.json`. tol0 TP32/FP6/FN3 (F1 87.67) vs #2+#4 GT-v3 probe
~88.57 = slight regression, **isolated to C**. Per-file: 163444215 FP=[6,**35,37**] FN=[] (FP31 DEAD ✓ via D, 13 is
TP ✓ GT v3); 082511233 FP=[**19**] FN=[] (**FN20→TP ✓** via C); 164505881 FP=[9,13] FN=[12]; 165204533 FN=[3,4].
Gate events: DUP-GUARD-KEEP 0 (targets off-probe), TITLE-GATE-RELOC 0, NEXT-PAGE-GATE 23 (all TPs preserved, FP6 not
vetoed), TABLE-CONFIRM 5. **C (Fix 11 v2) failed its pre-registered falsifier ("any new table FP"):** TABLE-CONFIRM
verdicts `p34→35 (8→5) stands`=FP35, `p36→37 (10→1) stands`=FP37, `p18→19 (31→2) stands`=FP19 — vs `p19→20 (6→1)
stands`=TP20. **Root flaw:** a table reset-to-1/jump occurs at BOTH real boundaries AND intra-document section breaks
(FP37 `10→1` and TP20 `6→1` are BOTH resets) → numbering ALONE cannot discriminate; the mechanical rule is too
permissive (inverse of v1's too-strict). **DECISION: revert C** (per its falsifier), keep A+B+D. C → backlog with a
refined spec: table-numbering discontinuity must be CORROBORATED (heading/issuer/letterhead change on n+1) to stand —
it cannot be a standalone confirm. A+B+D re-probe follows.

### 🧪 ROUND 3 — PRE-REGISTERED PROBE EXPECTATIONS (falsifiable, derived from tonight's logs)
Probe set = 163444215, 164505881, 165204533, 082511233. Redeploy order: fingerprint → probe A → dev A → probe B →
dev → probe C → dev → probe D → dev → round-3 stratified full-tests (STRICT+WAIVED). Same revert discipline as round 2.

**Commit A — duplicate-guard (keep-original-capped).** PROBE expectation = **BYTE-IDENTICAL on all 4 probe files**
(its targets — FN19@142044854 + the 8 fresh dup FNs — live OUTSIDE the probe set): **163444215 FP=[6,31] FN=[]
(GT v3: p13 now TP)**; 164505881 FP=[9,13] FN=[12]; 165204533 FP=[] FN=[3,4]; 082511233 FP=[] FN=[20]. **Real gate =
DEV EVAL**: expect FN19@142044854 → TP (142044854 FN=[19,20] → [20]) IF the kept p19 boundary (capped 0.60) survives
the low-conf confirmation pass; dev tol0 F1 **≥ 92.12** (GT v3 baseline; → ~92.7 if FN19 recovers; ≥92.12 / neutral-safe
if the capped boundary is rejected — dup-guard never silently drops). Falsifier: any probe-file delta, or dev < 92.12.

**Commit B — next-page-gate rebuild (evidence-first).** B touches signature-gate boundaries. Per-file signature-gate
starts on the probe set (from Stage-2 attribution): 163444215 — TPs {3,4,7,8,15,22,23,24,32,34} MUST be PRESERVED,
FP **kill-candidates {6, 31}**; 164505881 — TPs {2,15} preserve, FP candidate **{9}**; 165204533 TPs {2,6} (no
sig-FP); 082511233 TPs {2,7} (no sig-FP). **Expectation:** all 16 signature-TPs preserved; the gate may VETO the
3 FP candidates if page n+1 shows continuation/verso/section-no-match; NO new FP/FN (the rebuild only ADDS veto
paths + a MATCH⇒new-doc path that fires solely on real document-types). Predicted per-file **(GT v3: p13 is TP, not
FP)**: 163444215 FP=[6,31]→[31] (best case, 6&31 vetoed→just 31 or fewer) … [6,31]; 164505881 FP=[9,13]→[13]…[9,13]
FN=[12]; 165204533/082511233 unchanged. **Falsifier:** ANY signature-TP lost (over-veto regression), any new FP/FN, or
dev F1 < 92.12. FP13@163444215 is now a TP (GT v3); FP13@164505881 is titled-not-signature-attributed → unaffected by B.

**Commit C — Fix 11 v2 (table confirm, evidence-first numbering).** C routes `table_end` through
`_query_confirm_table_boundary` (mechanical: suppress ONLY on proven-continuous numbering, else stand). PROBE: **082511233
FN=[20] → []** expected (table_end@p19 → p20 was capped→confirm-vetoed under the generic confirm; v2 stands it unless
p19→p20 row numbering is continuous). RISK on 163444215: table_end signals on p34/p36 were correctly rejected before;
v2 could ADD FP35/FP37 if their numbering reads non-continuous — falsifier = any new table FP. **DEV:** FN19/20@142044854
→ TP. **HOLDOUT (log forensics):** FN12@084837699 = `p11: end=True, signal=table_end, conf=90%` → capped 0.60 →
`rejected by confirmation pass` — same veto class; v2 flips it → **holdout R 73.33 → 80.00** expected. Falsifier: 082511233
FN20 not recovered, OR a new table FP, OR any signature/titled boundary changes (C touches table_end ONLY).

**Commit D — #1-lite v2 (gate BOTH one-page-check sites for signature_block/table_end).** PROBE **(GT v3: p13 is TP)**:
**163444215 FP=[6,31] → [6]** (FP31 dies — the site-1 self-contained override that created it is skipped; p31 is not
the last page so no OOB path). **082511233 UNCHANGED** = FP[] FN[20]: both sites gated, so the v1 OOB reroute that
produced FP21 CANNOT happen (current commits [1,2,3,4,7,10] — the p21 correction never committed anyway). 164505881
FP[9,13] FN[12], 165204533 FN[3,4] unchanged. **Critical contract (v1's failure):** FP31 dead AND NO FP21 — verified
by the contract test (both sites gate on `_one_page_check_applies`). Falsifier: FP31 not dead, FP21 (re)appears, or
any other probe delta. Net of A+B+C+D stacked is the round-3 full-tests run (STRICT+WAIVED) — the real verdict.

### 🔭 ROUND 3 SPEC STUBS (spec only — no code this round)
- **(a) Duplicate-guard** (relocate-to-duplicate, fresh dup-reloc=8): FORK **CLOSED 2026-06-13 → keep-original-capped**
  (human decision). Implemented Commit A (`_titled_gate_decision`): when the unique grounded relocation target is a page
  already opened by a prior boundary, KEEP the original claimed page as the boundary, conf capped 0.60, log
  `[DUP-GUARD-KEEP]` — never silently drop. Tests `test_dup_guard.py` (10, pass; fixtures = real traces).
- **(b) Next-page-gate REBUILD (transcribe-then-judge shape).** IMPLEMENTED Commit B (`_query_next_page_starts_new`
  evidence-first + pure `_next_page_decision`): evidence JSON {transcription, heading, continuation, verso, starts_new}
  produced BEFORE the verdict; CPU post-processor priority = **verso veto > nomenclature MATCH⇒new-doc > continuation
  veto > model**. Nomenclature hook justified by P(TP|MATCH) across architectures — **Stage-2 95.2%** (40/42), **run8
  97.9%** (47/48). HARD: judges page n+1's freshness ONLY, never re-judges page n ⇒ **start-page-grid class
  (p45/46@084031203) cannot regress**. Tests `test_next_page_gate.py` (12, pass — the 6 dossier scenarios as fixtures
  + priority/neutral-default checks).
- **(c) Fix 11 v2** — TRIED (Commit C) then **REVERTED 2026-06-13** (probe falsifier: FP35/37@163444215 + FP19@082511233).
  Mechanical "non-continuous numbering ⇒ stand" is too permissive — a reset-to-1/jump occurs at BOTH real boundaries AND
  intra-doc section breaks (FP37 `10→1` vs TP20 `6→1` both reset). **Fix 11 v3 (backlog):** numbering discontinuity must be
  CORROBORATED by a heading/issuer/letterhead change on n+1; not a standalone confirm. FN20@082511233 / FN12@084837699 /
  FN19,20@142044854 stay STRICT FNs until v3.

#### 🩺 HOLDOUT-FN MECHANISM DIAGNOSIS (human attest 2026-06-13 + Stage-2 log forensics) — backlog item 3 CLOSED
All 5 holdout FNs confirmed REAL model misses (holdout GT fully confirmed, NO GT change): 082646183 p4 (heading not in
nomenclature, no signature on p4); 084837699 p11 (p10 carries the signature), p12 (p11 carries it, different style);
085002901 p9. **p13@084837699 = AMBIGUOUS** (different inventory tables, usually printed separately — human could not
decide) → **convention-seam list** alongside FP13@163444215, **GT untouched** (a lean does not move GT here).
**Mechanism map (verbatim Stage-2 lines):** two classes —
- **Fix 11 v2 class (1):** FN12@084837699 — `p11: end=True, signal=table_end, conf=90%` → capped 0.60 → `rejected by
  confirmation pass`. Same veto that ate FN20@082511233 + the 142044854 pair → **flips with Commit C** (pre-registered).
- **QUIET-SEAM class (3), never-named:** FN4@082646183 (`p3/p4: end=False, signal=none`), FN9@085002901 (`p8: end=False,
  signal=none, conf=100%`), FN11@084837699 (`p10: end=False, signal=none, conf=100%` — model reported NONE despite a
  human-attested signature = flat missed read; possible verso/rotation/unusual-grid — note for the dossier). Nothing
  fired, nothing was vetoed, no gate ever saw the seam. **NOT a judgment failure** (unlike everything round 2 fixed) —
  a detection gap. Cross-architecture: run8 holdout R=66.67 → structurally hard for BOTH architectures. **None of
  Commits A–D touches these.** Backlog item 3 → **CLOSED as DIAGNOSED** (1× Fix11v2 + 3× quiet-seam + GT confirmed).

#### 🔭 ROUND 4 SPEC STUB (direction only — no design, gated on round-3 results)
- **Quiet-seam start detection.** A start-SIDE mechanism (round 2/3 are all end-side gates): a dedicated post-hoc
  style/letterhead-change READ at seams where NO end-signal fired AND the following page opens a candidate fresh block.
  TRANSCRIBE-first per the C-tracking law (never free-judge). Gated on round-3 results + a quiet-seam dossier count
  derived from the round-3 full-tests log. Targets the 3 quiet-seam holdout FNs + any same-class fresh misses.

**ROUND 2 BOOKS CLOSED.** Corrected GT (committed) is the round-3 baseline; #2+#4 (md5 63da033) is the candidate.

---

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

#### 📋 BACKLOG (re-prioritised post Stage-2, per pre-registered decision rule)
- **★ TOP — Relocation/duplicate fix** (PROMOTED: fresh `titled_reloc_dup`=8 of 18 fresh FN = material, meets the
  pre-registered "fresh dup-reloc is non-trivial → promote" rule). Two coupled parts: (i) requery-aware relocation
  trigger = not-BOTH-grounded + suspect provenance (#2-requery OR reason-title/page mismatch), search = match
  reason-cited title against window transcriptions; (ii) relocate-to-duplicate guard = when the unique grounded
  window page is already opened by the immediately-preceding iteration, do NOT silently drop the claim (suppress-
  with-flag vs keep-original-capped — design choice in the spec). Targets FN3@165204533 + the 8 fresh dup-reloc FNs.
- **★ TOP — Tier 3 #5 repeated-form suppression:** pod-less, CPU structural similarity on binarized page skeletons.
- **SHELVED — nomenclature integration:** experiment shows NO current score-moving hook — capped one-of-two accepts
  already admit the matched admin-type starts, and there are ZERO rescue candidates (no suppressed-was-true that a
  MATCH would recover). Re-evaluate ONLY after the relocation fix changes which events exist. (Module + tests kept.)
- **#1-lite v2:** IMPLEMENTED Commit D (`_one_page_check_applies` predicate). Gates BOTH one-page-check sites (n+1
  branch AND OOB-PROJECTION) for signature_block/table_end — v1 gated only the first, rerouting the override to the OOB
  site → FP21. Tests `test_one_page_check_gate.py` (4, pass; incl. a contract test that BOTH sites gate on the
  predicate). Targets FP31@163444215 with no FP21 reroute.
- **FN3 / FN4 / FN20:** known STRICT FNs, mislocalization-class. NOT waivers (no waivers.json).

#### 🔬 ADDENDUM — RUN8 CROSS-ARCHITECTURE NOMENCLATURE EXPERIMENT (`nomenclature_experiment_run8.py`, CPU/pod-less)
After Stage 3 lands, run (does NOT block pod-down): `python3 nomenclature_experiment_run8.py logs/run8_stage3.log
--gt eval_full/ground_truth.json --strata eval_full/strata.json --masked eval_full/masked.json >
logs/nomenclature_experiment_run8.txt` → commit. run8 logs `[next_page_heading='…']` on confirmed boundaries (its
analog of split's titled title) + header_block_reset/appendix_heading; the script labels each vs current GT (TP/FP +
run8-FNs whose page carries a heading) and matches headings via `nomenclature_match`, same report format. **run8.py
stays BYTE-FROZEN** (referee + fingerprint roles) — any mechanism this motivates is a forward-port into split.py,
never a run8 edit. Crash-tested on the partial log: works; notable early signal — **run8 uses `fresh_letterhead`,
NOT `titled_id_header`**, as its start signal (different vocabulary). This cross-architecture comparison (how a
heading-grounded vs title-grounded start-detector distributes nomenclature MATCHes across TP/FP) **feeds the
relocation-fix design** — it shows whether grounding on the next-page heading (run8) vs the claimed-page title
(split) changes which true starts are recoverable.

#### 🔤 ITEM 5 — NOMENCLATURE MATCHER (`nomenclature_match.py` + `test_nomenclature_match.py`, pod-less CPU)
STANDALONE module (zero split.py integration) matching VLM-transcribed titles against
`номенклатура_цяла.xls`. Parse VALIDATED to Fable spec: **382 entries / 220 unique names / 19 categories**
(category = the X000-code section heading each row falls under; codes %1000==0 are headings). Normalization
(both table + titles): NFC→lower→Latin/Cyrillic homoglyph fold→strip punct/№/dashes→squashed (whitespace
removed, defeats 'С К И Ц А') + tokens; transcribed titles also drop identifier tokens (digits/№). Matching
levels: (1) exact-squashed (2) guarded containment (3) char-trigram Jaccard (4) token-set difflib ratio →
returns (best_entry, level_scores, band). **NEUTRAL-DEFAULT hard rule** (docstring + `test_neutral_default` +
`is_confidence_signal()`): only MATCH is actionable; AMBIGUOUS≡NONE≡"no signal" — table can only ADD
confidence, never block. Bands PROVISIONAL/reporting-only (real thresholds tuned later from TP/FP on dev).
Tests: **17/17 pass** — corruption-robust positives (letter-spacing, single drop/sub, homoglyph, case chaos,
appended identifiers, truncation) MATCH; negatives (НАКЛОНЕН ПОКРИВ, ЧЕЛЕН ЛИСТ, НОТАРИАЛЕН АКТ) all NONE.

#### 🔬 ITEM 6 — NOMENCLATURE EXPERIMENT (`nomenclature_experiment.py`, RECORDED; EXECUTE after Stage-2 log)
DATA-REPORT-ONLY analyzer: parses every `[TITLE-GATE]`/`[TITLE-GATE-RELOC]` event from the full-tests log,
labels each vs GT (TP / FP / suppressed-was-true / suppressed-was-false), matches the title via
`nomenclature_match`, and reports per stratum: (1) TP-vs-FP match-score distributions; (2) per-table-entry
hit counts split TP/FP with SHEET-TYPES separated from admin docs (tests "sheet-types concentrate on FPs");
(3) suppressed-was-true ∩ table-MATCH = RESCUE candidates; (4) full AMBIGUOUS list + top-3 candidates (gauges
AI-adjudication need). Proposes/changes NOTHING — integration is a morning human call. Parser crash-tested on
`logs/probe_1lite2.log` (14 events, all 4 sections render). Run after Stage 2:
`python3 nomenclature_experiment.py logs/fulltests_stage2.log` (defaults to `eval_full/` GT/strata/masked).


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

#### 🏁 STAGE 3 — RUN8 REFEREE (historical-88.5 reference, run-8 code, 5090, same 150 DPI + corrected/masked GT)
`logs/run8_stage3.log` + `logs/run8_stage3_results.json` (via `eval_run8.py`, import-swapped to run8; run8.py byte-frozen).
| stratum | TP/FP/FN | P | R | F1 |
|---|---|---|---|---|
| dev (9) | 74/10/8 | 88.10 | 90.24 | 89.16 |
| holdout (3) | 10/1/5 | 90.91 | 66.67 | 76.92 |
| fresh (8) | 198/40/17 | 83.19 | 92.09 | 87.42 |
| **AGGREGATE** | 282/51/30 | 84.68 | 90.38 | **87.44** |
**Three-way ordering (corrected+masked GT): round-1 candidate 85.84 < run8 referee 87.44 < #2+#4 88.99.** #2+#4
beats the genuine run-8 baseline by **+1.55 aggregate / +2.46 fresh-P (85.65 vs 83.19)** → the #2+#4 gains are real
improvements over run-8, not artifacts of a weak round-1 anchor. **Historical-88.5 reconciliation:** run8 cited ~88.5
historically; scores **87.44** here on the CORRECTED+masked GT — the ~1pt delta is the GT correction (added
163444215:p10, 084303475:p4 + coverage-based derivation) + masking, not a regression (run8 reproduces run-8
behaviour; fingerprint check in Stage 4). Notable: run8 still emits FP11@163444215 (the invented-РС№ #4's gate kills)
and misses 163444215 p7/p9 that #2+#4 catches.

#### ✅✅ STAGE 2 — FULL-TESTS STRATIFIED (#2+#4 on 63da033) — STRONG GENERALIZATION
`logs/fulltests_stage2.log` + `logs/fulltests_stage2_results.json` (250/336 docs exact). Masked excluded:
143041245[62-66], 145428614[146-150].
| stratum | TP/FP/FN | P | R | **F1** | round-1 candidate |
|---|---|---|---|---|---|
| dev (9) | 75/7/7 | 91.46 | 91.46 | **91.46** | 89.94 |
| holdout (3) | 11/1/4 | 91.67 | 73.33 | **81.48** | — |
| fresh (8) | 197/33/18 | **85.65** | 91.63 | **88.54** | 84.63 (P 77.31) |
| **AGGREGATE (20)** | 283/41/29 | 87.35 | 90.71 | **88.99** | **85.84** |
**MASKING RECONCILIATION (Fable flagged round-1 row as possibly unmasked — evidence says it is ALREADY masked):**
Both rows scored through the SAME masked `score_full.py` (masks 143041245[62-66], 145428614[146-150]). Round-1
candidate (`logs/round1_candidate.log`) recomputed directly: fresh UNMASKED TP204/FP60/**P77.27**/F1 84.47 →
fresh MASKED TP201/FP59/**P77.31**/F1 84.63. The table's `77.31` IS the masked value (masking removes 3 masked TP +
1 masked FP, nudging fresh P slightly UP, not down to ~77.04). Table is apples-to-apples; deltas stand. #2+#4 fresh
(TP197/FP33/85.65) likewise masked. Aggregate round-1 masked = 85.84 (TP288/FP71, P80.22) — matches the baseline row.
**Headline:** aggregate **85.84 → 88.99 (+3.15)**; **fresh precision 77.31 → 85.65 (+8.34)** = #4 killing the
invented-РС№ FP class exactly as designed. **Overfitting gap dev−fresh NARROWED +5.31 → +2.92** (fresh +3.91 vs
dev +1.52) — #4 transfers to unseen data BETTER than the dev-tuned baseline; it is a real generalization win, not
overfitting. Holdout R low (73%) on tiny n=15 (3 files: 4 FN, mostly missed table/signature starts — not titled).
**Per-stratum gate-event table** (`stage2_event_counts.py`, masked excluded):
| stratum | suppressed | capped | reloc | reloc_dup | requery | onelite_would_fire |
|---|--:|--:|--:|--:|--:|--:|
| dev | 6 | 6 | 2 | 1 | 1 | 9 |
| holdout | 1 | 0 | 0 | 0 | 0 | 1 |
| fresh | 17 | 29 | 15 | **8** | 0 | 19 |
| ALL | 24 | 35 | 17 | 9 | 1 | 29 |
**FRESH `titled_reloc_dup`=8** (of 18 fresh FN) → relocate-to-duplicate is MATERIAL on unseen data → the
requery-aware relocation-trigger fix is worth implementing (decided by this count, per the C-tracking note).
`onelite_would_fire`=29 = end-events a correct (both-sites) #1-lite v2 would gate. Next: nomenclature experiment
on this log, then Stage 3 run8 referee.

#### 🔬 ITEM 6 — NOMENCLATURE EXPERIMENT RESULTS (`logs/nomenclature_experiment_stage2.txt`, DATA ONLY)
TITLE-GATE events: dev 35, holdout 2, fresh 136. **Findings (no thresholds tuned, no pipeline change — integration
is a morning human call):** (1) **Sheet-type hypothesis REFUTED** — 0 sheet-type entry hits in ANY stratum; the
titled gate's titles do not transcribe to drawing-sheet types, so a "sheet-type negative list" integration option
is moot. (2) **A nomenclature MATCH strongly co-occurs with TP**: fresh TP bands MATCH=40/NONE=53; fresh FP bands
NONE=9/MATCH=2 — i.e. MATCHes are overwhelmingly admin-doc TYPES on true starts (Удостоверение 16/0, РС 7/0, Молба
3/0…), titled-FPs are mostly NONE. Only 2 fresh-FP MATCHes (Пълномощно). Consistent with using MATCH as a
confidence-ADD under neutral-default (never a block) — but DECISION DEFERRED to human. (3) **No RESCUE candidates**
(no suppressed-was-true with a table MATCH → the gate didn't wrongly suppress any real nomenclature doc). (4) **No
fresh AMBIGUOUS-band events** → an AI-adjudication tier is not obviously needed at current provisional bounds.

#### ✅ STAGE 1 — DEV EVAL (#2+#4 on authoritative 63da033) — KEEP (+1.52 vs baseline)
*(as-run under pre-v3 GT; under GT v3 this re-scores to dev tol0 **92.12** TP76/FP6/FN7 — the NEW round-3 keep gate; see top table.)*
`logs/dev_stage1.log` + `logs/dev_stage1_results.json`. Dev tol=0 **F1 91.46%** (TP=75 FP=7 FN=7, P=R=91.46%),
tol=1 F1 92.68%, 74/91 docs exact. Baseline round-1 candidate dev tol=0 **89.94** → **+1.52 → KEEP** (≥89.94 rule).
Mechanism: #4 killed FP11/19/27@163444215 (FP 6→3) + FP13@142044854 → precision 87.36→91.46; cost one new
FN19@142044854 → recall 92.68→91.46; net +1.52. FP31 retained (#1-lite reverted). Per-file: 163444215 FP[6,13,31]
FN[]; 164505881 FP[9,13] FN[12]; 165204533 FN[3,4]; 082511233 FN[20]; 142044854 FP[6,17] FN[19,20]; 084303475
FN[16]; (084552444/085108460/082544031 clean).
**Full per-file DELTA vs round-1 candidate (composition, not just aggregate):**
`−FP{11,19,27}@163444215` (titled invented-РС№, killed by #4 gate) ; `−FP13@142044854` (**first #4 transfer
evidence OUTSIDE the probe set** — the gate generalises) ; `+FN19@142044854` (new, from a duplicate-relocation:
the n=18 titled relocated backward onto p18 — already opened at n=17 — abandoning true start p19) ; ALL other
dev per-file sets UNCHANGED. Net: −4 FP, +1 FN.
Dev event counts: SUPPRESSED=6, one-of-two-capped=6, TITLE-GATE-RELOC=2 (**of which duplicate-reloc=1** = p18@142044854,
the FN19 cause), WINDOW-REQUERY=1. → Stage 2 full-tests launched. (Counts via `stage2_event_counts.py`.)

#### 🖼 SIGNATURE-FP TRIAGE — all signature-gate FP events (Stage-2 log, #2+#4)
Criterion: an FP start page P (tol=0) preceded by a `Signature on p(P-1) confirmed as end — next page starts new doc` verdict. **29 events** (23 fresh / 5 dev / 1 holdout); of these **25 commit as signal=signature_block, 4 as project_signoff** (over-determined). NOTE: Fable cited 22 — delta is criterion-dependent (committed-signal filter / masked-page exclusion); full set listed for reconciliation. ★ = page rendered in `attestations/sig_triage/`. Dossiers + this table are for HUMAN eyes (no model commentary on page content).

| ★ | stratum | file | sig page | claimed start | conf | committed signal | verbatim next_page_starts_new verdict |
|---|---|---|--:|--:|--:|---|---|
| ★ | fresh | 083553577 | 8 | 9 | 95 | signature_block | Signature on p8 confirmed as end — next page starts new doc (conf=95%) [next_page_heading='ИЗВЕСТИЕ ЗА ДОСТАВЯНЕ'] |
|  | fresh | 083553577 | 18 | 19 | 95 | signature_block | Signature on p18 confirmed as end — next page starts new doc (conf=95%) [next_page_heading='ИЗВЕЩЕНИЕ ЗА ДОСТАВЯНЕ'] |
|  | fresh | 083553577 | 32 | 33 | 92 | signature_block | Signature on p32 confirmed as end — next page starts new doc (conf=92%) [next_page_heading='CTAHAPT GNC TEMC OOA'] |
|  | fresh | 084031203 | 38 | 39 | 92 | signature_block | Signature on p38 confirmed as end — next page starts new doc (conf=92%) [next_page_heading='Приложение №2'] |
| ★ | fresh | 084031203 | 45 | 46 | 92 | signature_block | Signature on p45 confirmed as end — next page starts new doc (conf=92%) [next_page_heading='ПРОЕКТАНТИ'] |
|  | fresh | 142438096 | 47 | 48 | 92 | signature_block | Signature on p47 confirmed as end — next page starts new doc (conf=92%) [next_page_heading='ПРИЛОЖЕНИЕ №1 ТЕХНИЧЕСКО ЗАДАНИЕ - ИЗХОДНИ ДАННИ И ТЕХНИЧЕСКИ ПАРАМЕТРИ НА ПРИСЪЕДИНЯВАНЕТО КЪМ ПРЕДВАРИТЕЛЕН ДОГОВОР'] |
|  | fresh | 142438096 | 52 | 53 | 92 | signature_block | Signature on p52 confirmed as end — next page starts new doc (conf=92%) [next_page_heading='ПРИЛОЖЕНИЕ №1 ТЕХНИЧЕСКО ЗАДАНИЕ - ИЗХОДНИ ДАННИ И ТЕХНИЧЕСКИ ПАРАМЕТРИ НА ПРИСЪЕДИНЯВАНЕТО КЪМ ПРЕДВАРИТЕЛЕН ДОГОВОР'] |
| ★ | fresh | 142438096 | 68 | 69 | 92 | signature_block | Signature on p68 confirmed as end — next page starts new doc (conf=92%) [next_page_heading='Основни задължения на собственика след получаване на разрешението за строеж'] |
|  | fresh | 142438096 | 87 | 88 | 92 | signature_block | Signature on p87 confirmed as end — next page starts new doc (conf=92%) [next_page_heading='ОБЕКТ: ПЛОЩАДКОВИ ВК МРЕЖИ В ПИ С ИДЕНТИФИКАТОР 56784.510.387'] |
|  | fresh | 143041245 | 36 | 37 | 92 | signature_block | Signature on p36 confirmed as end — next page starts new doc (conf=92%) |
|  | fresh | 143041245 | 42 | 43 | 92 | signature_block | Signature on p42 confirmed as end — next page starts new doc (conf=92%) [next_page_heading='РЕШИ: ПРИЕМА СТРОЕЖА:'] |
| ★ | fresh | 143041245 | 50 | 51 | 85 | signature_block | Signature on p50 confirmed as end — next page starts new doc (conf=85%) [next_page_heading='Търговски условия'] |
|  | fresh | 145428614 | 1 | 2 | 88 | signature_block | Signature on p1 confirmed as end — next page starts new doc (conf=88%) |
|  | fresh | 145428614 | 29 | 30 | 95 | signature_block | Signature on p29 confirmed as end — next page starts new doc (conf=95%) [next_page_heading='ИЗВЕЩЕНИЕ ЗА ДОСТАВЯНЕ'] |
| ★ | fresh | 145428614 | 64 | 65 | 90 | signature_block | Signature on p64 confirmed as end — next page starts new doc (conf=90%) [next_page_heading='Член 9. Общи текстове'] |
| ★ | fresh | 145428614 | 65 | 66 | 90 | signature_block | Signature on p65 confirmed as end — next page starts new doc (conf=90%) [next_page_heading='Търговски условия'] |
|  | fresh | 145428614 | 70 | 71 | 88 | project_signoff | Signature on p70 confirmed as end — next page starts new doc (conf=88%) [next_page_heading='СЪДЪРЖАНИЕ'] |
|  | fresh | 145428614 | 101 | 102 | 92 | signature_block | Signature on p101 confirmed as end — next page starts new doc (conf=92%) |
|  | fresh | 145428614 | 150 | 151 | 88 | project_signoff | Signature on p150 confirmed as end — next page starts new doc (conf=88%) [next_page_heading='СЪДЪРЖАНИЕ'] |
| ★ | fresh | 162710373 | 1 | 2 | 92 | signature_block | Signature on p1 confirmed as end — next page starts new doc (conf=92%) [next_page_heading='Понуки за пазари 1763'] |
|  | fresh | 162710373 | 3 | 4 | 92 | signature_block | Signature on p3 confirmed as end — next page starts new doc (conf=92%) [next_page_heading='Основни задължения на собственика след получаване на разрешението за строеж:'] |
|  | fresh | 164052657 | 13 | 14 | 92 | signature_block | Signature on p13 confirmed as end — next page starts new doc (conf=92%) |
|  | fresh | 164052657 | 34 | 35 | 90 | signature_block | Signature on p34 confirmed as end — next page starts new doc (conf=90%) [next_page_heading='Етаж 2. Надлъжна армировка в греди, cm2'] |
|  | dev | 142044854 | 5 | 6 | 92 | signature_block | Signature on p5 confirmed as end — next page starts new doc (conf=92%) [next_page_heading='ИЗВЕЩЕНИЕ ЗА ДОСТАВЯНЕ'] |
|  | dev | 142044854 | 16 | 17 | 88 | project_signoff | Signature on p16 confirmed as end — next page starts new doc (conf=88%) [next_page_heading='No. 27.02.2014'] |
|  | dev | 163444215 | 5 | 6 | 92 | signature_block | Signature on p5 confirmed as end — next page starts new doc (conf=92%) [next_page_heading='ИЗВЕЩЕНИЕ ЗА ДОСТАВАНЕ'] |
|  | dev | 163444215 | 30 | 31 | 88 | signature_block | Signature on p30 confirmed as end — next page starts new doc (conf=88%) [next_page_heading='СЪДЕЛИТЕЛИ'] |
|  | dev | 164505881 | 8 | 9 | 92 | signature_block | Signature on p8 confirmed as end — next page starts new doc (conf=92%) [next_page_heading='Търговски условия на предварителните договори за присъединяване на обект на Клиент към електроразпределителната мрежа на "ЕВН България Електроразпределение" ЕАД'] |
|  | holdout | 084837699 | 6 | 7 | 92 | project_signoff | Signature on p6 confirmed as end — next page starts new doc (conf=92%) |

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
> **C-tracking — #4 "relocate-to-duplicate" sub-case (dev Stage 1, FN19@142044854):** when the claimed page is
> NEITHER-grounded and the UNIQUE grounded window page is ALREADY consumed by an existing boundary (opened by the
> immediately preceding iteration), the relocation moves the boundary backward onto that existing start and SILENTLY
> DROPS the claim → the forward true start is lost (p19 here). First #4 cost outside its targets. Candidate behaviours
> (suppress-with-flag vs keep-original-capped vs no-op-and-keep-forward) are DEFERRED to the requery-aware
> relocation-trigger spec, to be decided on the FRESH-stratum duplicate-reloc count (Stage 2 `stage2_event_counts.py`
> column `titled_reloc_dup`). Operational def of duplicate-reloc (verifier-checkable): reloc target first opened as a
> doc-start by iteration `reloc_iter − 1`. Counterpart positive: `−FP13@142044854` = first #4 FP-kill transferring
> beyond the probe set.
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
