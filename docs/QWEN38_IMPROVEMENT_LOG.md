# Qwen3.8 thinking-off improvement experiments — 6 September 2026

The user authorized autonomous experiments and requested stopping medium thinking.
The medium-16k process was interrupted; the compact-v3 GPU server remains available
for thinking-off experiments. Ground-truth files are unchanged. Production still
defaults to the measured Qwen2.5 detector.

## Fixed reference

`qwen38-pilot-schema-v1-20260905/eval_full-off`: 20 sources, 733 pages,
TP 290 / FP 49 / FN 25, boundary F1 88.6850%, exact documents 264/335.
The historical Qwen2.5 predictions rescored on these labels have TP 286 / FP 41 /
FN 29, F1 89.0966%, exact documents 252/335. Gergana off: 26/35 exact documents,
FP 4 / FN 3, F1 88.5246%.

Pair experiments use the same model weights and off sampling, but compact-v3 JSON
formatting. Postprocessing a saved baseline is a paired replay experiment, not a
new full end-to-end run of the old detector. That distinction remains in results.

## Audit

All 339 non-initial predicted cuts were traced to their actual log events. Of the
49 false cuts, first-origin counts are: titled_id_header 22, start_only_heading
13, header_block_reset 7, signature_block 5, page_number_reset 1, project_signoff 1.
There are 29 false cuts absent from Qwen2.5 and 20 shared false cuts; Qwen3.8 also
removed 21 of the previous model's false cuts. The net increase is eight, not 29.

Visual inspection of development examples shows delivery receipts attached to
letters, repeated municipal review sheets for different disciplines of the same
project, and contents-to-explanatory-note transitions within a project volume.
Several confident log explanations misread handwriting or treated an entry as a
new instrument. 25/49 false cuts carry 95% reported confidence, so a confidence
threshold alone does not separate these errors reliably.

## Experiment sequence

1. `relation_v1`: classify each adjacent page pair directly, distinguishing an
   independent document from continuation/attachment/section/uncertain evidence.
2. `archive_v2`: the same direct question plus explicit filing conventions for
   review-sheet sequences, delivery receipts, project-volume sections and terms.
3. Offline policy comparisons: use pair decisions directly, veto original cuts
   only with explicit contrary evidence, or also add high-confidence new starts.
   This separates false-cut correction from recovering missed starts.

The two initial prompts are frozen before GPU evaluation on the nine existing dev
sources (181 pages, 172 seams). Variant selection uses dev results. Other historical
strata and the separately reviewed Gergana set are reported separately. These
corpora have previously been inspected; they are not a newly blind test set.
No ground-truth labels, expected boundaries or old model decisions enter a prompt.

Every seam records raw final JSON, source/code/settings identity, rotation,
runtime and token usage. Failed seams do not silently become negative decisions;
they are retried once after the other seams, and unresolved failures mark the
source incomplete. The offline scorer refuses incomplete sources by default.

Live experiment artifacts: `experiments/qwen38_improvement_20260906/` locally and
`/workspace/qwen38_pilot/experiments/qwen38_improvement_20260906/` on the GPU host.

### CPU ablations rejected

On the nine dev sources, the off baseline is 90.5882% F1, 76/92 exact documents.
Keeping only confidence >=75 drops F1 to 79.22%; >=95 drops it to 73.38%.
Disabling start-only detection drops F1 to 88.05% and exact recovery to 64/92;
disabling title starts drops F1 to 52.03%; disabling header resets yields 88.89%.
These interventions remove genuine boundaries along with false cuts, so none is
promoted. Detailed counts are in `cpu_ablations_dev.json`.

### Direct relationship classifier: rejected

Completed relation_v1 on all nine development PDFs: TP 58 / FP 0 / FN 25,
F1 82.2695%, exact 52/92. It removes all ten baseline false cuts but loses nineteen
true boundaries and recovers no baseline misses. Broad veto policies also regress.
Separately filed credentials, quantity sheets, explanatory notes and data reports
were called attachments merely because they support the same project.

An exploratory lexical restriction to municipal form_series, literal postal
receipt headings and trade-conditions headings removes eight false cuts and no
true cut on dev: F1 95.0617%, exact 80/92. This is a development analysis, not a
validated deployment result. A new typed_v3 verifier tests those relationships
explicitly, plus contents-to-note and closing-only continuations. Its type guards
keep the first review sheet and reject contradictory evidence.

### Separate recovery experiment prepared

Single-page profile_v4 reads document kinds without neighboring-page priming.
It tests recovery of the first review sheet, distinct population/service-register
reports, and independently introduced coordinate outputs. Changed coordinate
columns require an explicit row restart; Latin/Cyrillic lookalike labels are
normalized. No filenames or expected page numbers occur in these rules.

Visual inspection found substantial misdescription: the dev service-register page
was called an explanatory note in the three-page baseline; distinct family and
personal-register reports were called one continuing family table. The strict title
gate then rejected several hypothesized starts because their claimed titles were
absent. Ground truth remains unchanged.

Local verification at this point: 121 unit tests passed. GPU variants are isolated
from production and record separate source-code hashes.

### Broad archive prompt: rejected

archive_v2 completed all 172 seams after retrying two contradictory category/boolean
answers. Direct F1 fell to 77.9412% (TP 53 / FP 0 / FN 30), exact 45/92. Its best
hybrid still reached only 83.9161%. This confirms that describing entire project
volumes as a unit is too broad for the existing filing convention.

A fifth variant, filing_v5, explicitly defines independently filed outputs, keeps
the narrow continuation exceptions, and directly decides each seam. It tests
whether those lessons can replace the expensive detector rather than merely add
queries. It is queued after typed_v3 and profile_v4; all use thinking OFF.

### Typed verifier completed on dev

All five corrections: TP 76 / FP 1 / FN 7, F1 95.0000%, exact 80/92.
Excluding closing_continuation: TP 77 / FP 2 / FN 6, F1 95.0617%, exact 80/92.
The latter makes eight useful removals and no harmful removal. The explicit
contents rule did not detect the remaining contents-to-note false cut.

The harmful closing veto reverses image roles: the first image is a notarial
closing stamp and the second is a complete heirs certificate; the answer assigns
the certificate to the left and the stamp to the right. A queued diagnostic repeats
four development seams with/without interleaved positional image labels and with
standard versus greedy sampling (two repetitions per condition, 32 calls total).
Sampling and image annotations are recorded in each diagnostic result.

The profile test began before queue reordering, so it was left running. Only the
still-waiting filing controller was requeued; the image-order diagnostic follows
profiles. The filing experiment has not run yet.

The profile reader correctly transcribed the second coordinate output's columns
as X/Y/H, but the original schema comparison recognized only X/Y/Z. A separate
offline policy v4b normalizes the H/Н height label to Z without changing prompts or
active GPU code. On the first five completed development sources, it recovers
both missed coordinate starts and adds no false cut. This is still partial.

### Combined development result

profile_v4 completed all 181 single-page reads. Policy v4b recovers all six baseline
misses with zero false additions. Combined with typed_v3 excluding closing-only
vetoes, the nine-PDF result is TP 83 / FP 2 / FN 0, F1 98.8095%, exact 90/92
(vs baseline 76/92). The remaining false cuts are the notarial closing page and
contents-to-note transition. This is development selection, not external accuracy.

### Image-order diagnostic

All 32 diagnostic calls completed. Original sampling/no labels and greedy/no labels
each got 6/8 boundary decisions right, repeating the certificate merge twice.
Positional labels with standard sampling got 8/8 after the consistency guard rejected
two contradictory closing requests. Labels with greedy sampling got 8/8 with
consistent decisions. Greedy means temperature 0, top-p 1, top-k 1 and presence
penalty 0; thinking remains off. These four selected seams are diagnostic controls,
not a general accuracy benchmark.

The labeled+greedy verifier now runs on all baseline cuts in the nine development
PDFs. The direct filing_v5 prompt with the same client settings is queued after it.
The unlabeled filing_v5 prompt was prepared but never executed; do not report an
accuracy result for that unrun condition.

### Labeled greedy verifier completed

All 87 original development cuts were checked. With all five rules enabled, it
removes nine false cuts and no true cut: TP 77 / FP 1 / FN 6, F1 95.6522%,
exact 81/92. Combining with profile_v4b gives TP 83 / FP 1 / FN 0, F1 99.4012%,
exact 91/92. The model's closing-page reversal no longer causes a merge.

A typed_v3b prompt refinement defines continued contents sheets by their layout
(numbered short section/drawing titles without explanatory prose), including
sheets lacking the word СЪДЪРЖАНИЕ. The same fixed development cuts will be
checked after the direct-filing run; no non-development result selects this change.

Direct filing plus cached single-page recovery can also be scored without new
GPU calls. The offline scorer now accepts --direct-run; it refuses incomplete
input sources unless --allow-partial is explicitly requested.

### Direct filing completed on dev

filing_v5 with labels/greedy: TP 80 / FP 5 / FN 3, F1 95.2381%, exact 84/92.
Adding cached profile_v4b recovery gives TP 83 / FP 5 / FN 0, F1 97.0760%,
exact 90/92. Four false cuts are consecutive numbered product entries in one
equipment catalog; one is the continued-contents-to-note seam. It is less accurate
than refining the original detector, despite the promising first six files.

The queued features_v6 single-request trial uses filing_v5b, which explicitly keeps
consecutive catalog entries and continued contents with their documents. It also
extracts page kinds and coordinate fields in the same answer and applies the
already tested typed-recovery rules. This tests replacing the extra profile pass.
The original features_v6 draft based on unmodified filing_v5 was never run; its
controller was confirmed waiting before updating the prompt and code hashes.

### Contents-only refinement: no measured gain

The typed_v3b run completed all 87 development cuts with the same result as v3:
TP 77 / FP 1 / FN 6; with profile recovery, F1 99.4012%, exact 91/92. Its remaining
answer calls the relationship toc_section but labels the left page explanatory_note
and reports confidence 85, so the consistency/type/confidence guard correctly
abstains. It is not promoted over the earlier, equally accurate prompt.

features_v6 is now running. After this development comparison, proceed to the
remaining PDFs; do not keep tuning the one remaining dev seam indefinitely.

### Frozen candidate and broader validation

features_v6 completed 172 development requests: TP 82 / FP 0 / FN 1, F1 99.3939%,
exact 90/92. The only miss is a standalone thermal-calculation sheet at dev source
082511233 page 7. It fixed the numbered catalog and contents false cuts.
The slower refinement reference remains 99.4012% F1 and 91/92 exact documents.

features_v6_frozen.json records the selected direct policy, all prompt/client
hashes, off/greedy generation and the 11 remaining historical sources (552 pages).
Those sources are now running with the frozen experimental driver. The first
validation source has three false cuts vs two originally, all inside one safety
plan: contents, responsible-person list, equipment list and explanatory note were
treated as separate units. Exact recovery on that source remains 5/6. Keep the
full validation unchanged; do not report development F1 as full-corpus accuracy.

Local production/evaluation drivers now offer --boundary-method features, still
optional. They use the same prompt/decisions with per-seam validated caches and
a separate settings/source namespace. An interruption test verifies completed
seams are reused and previous failed/successful call usage stays counted. These
integration files have not been uploaded over the active frozen validation runtime.
Local tests: 128 passed; updated portable inputs validate (66 payload files).

### Broader error audit and a selective v7 trial

The first six broader sources expose repeated over-splitting inside structural
calculation reports (load cases, reinforcement plots and element checks), safety
plan sections and recipient copies. Other misses involve title-only covers,
complete duplicate instruments and a separate staff-list output. Inspection
confirms the model frequently reads the content but selects the wrong filing
unit. One structural subsection also shows a differing project identifier; this
is retained as an annotation-ambiguity observation, not relabeled for the model.

features_v7 revises those filing conventions and rechecks all v6 proposed cuts
plus a small, content-selected set of negatives. Selection uses extracted headings
and model evidence, never error locations or human boundaries. The 9 dev sources
need 102 extra requests, with 70 seams reused. This is a two-pass candidate, so its
cost must include the original v6 pass. The 6 inspected historical validation
sources now count as development exposure for v7; the remaining 5 are recorded
before their error results are inspected. Gergana is still reserved for the final
selected implementation. No v7 code overwrites the live frozen v6 modules.

Visual checks on source 084031203 confirm that pages 29 and 30 are two fully
signed copies of the same contract, with different signature/stamp placement;
merging them as a continuation loses a filing unit. Its final designers page is
plain biographical text on the back of the cover, not an issued qualification
certificate. The v7 prompt distinguishes both cases without filenames/page labels.

A possible later speed experiment is a single-pass v7 prompt with conditional
postal lookahead, rather than rechecking all proposed cuts. This has NOT been
implemented or measured; first establish whether the present grouping revision
survives the full comparison. Concurrent GPU experiments make raw wall-time
comparisons misleading; final speed measurements must identify their scope.

### Scope guard and production integration prepared locally

On dev source 082511233, v7 applied grouping to thermal/energy outputs despite the
rule being intended for structural reports, losing two correct starts. v7b keeps
the v6 cut when a proposed merge concerns model-read thermal/energy content. This
content guard has no source-name or page-index conditions. It recovers both losses;
the original thermal appendix miss remains. Raw v7 outputs are retained and scored
separately; the guard is recorded in features_v7b_frozen.json.

An optional features-refined production/evaluation mode is prepared locally. It
runs v6 once, rechecks content-selected candidates, and applies the v7b guard.
Its interruption test fails during the second pass, resumes both sets of caches,
and verifies only the outstanding call is repeated and all five attempts remain
counted. The three targeted test modules pass. No integrated files were uploaded
over either active frozen experimental driver. Broader GPU validation is pending.

### V7b development result and typed-facts follow-up

V7 raw: TP80/FP0/FN3, F1 98.1595%, exact88/92. The frozen thermal scope guard
restores TP82/FP0/FN1, F1 99.3939%, exact90/92 across all 9 dev PDFs. On the first
completed broader files, the safety plan becomes exact and the structural report
loses 8 of its 9 false cuts; its cover-start miss and differing-project subsection
remain. Local integration suite: 131 tests passed before the facts follow-up.

V8 asks only for page roles and visible first-page evidence on selected negatives.
Its 19 dev requests initially leave the same single miss: both adjacent pages are
correctly classified as thermal outputs, and the right page is correctly read as
a first page. V8b permits a fresh thermal output after an earlier thermal output,
using that explicit first-page evidence. This changes only the remaining dev seam:
TP83/FP0/FN0, F1 100%, exact92/92. All other tested thermal interior pages report
right_first_page=false. The same frozen fact policy is queued on the broader
sources; no claim of full-corpus perfection is justified.

### Integrated Gergana run and reference-label audit

The isolated code snapshot /workspace/qwen38_integrated_20260906 runs the actual
features-refined production implementation through eval_boundaries.py. It does
not overwrite the active historical experiment code. Its first two sources expose
2 FP and 1 FN against the stored labels; source 3 is exact. Visual inspection finds
apparent reference issues at Review01 p6 (certificate to technical report) and
Review02 p11 (continuing insurance policy). The user was asked to clarify these;
labels remain unchanged. See QWEN38_LABEL_QUESTIONS.md. A report-cover grouping
conflict also limits the portability of the blanket cover rule. Do not tune the
model to merge a certificate into a report or split a policy merely to raise F1.

### Completed historical V9 comparison (20 sources, 733 pages)

The frozen sequence is V6 page facts, selective V7b filing refinement, V8b typed
recovery, narrow structural-plot verification, then contiguous postal-batch rules.
The historical comparison uses the same current GT v3 and strict scorer for every
model. Page 1 is not counted as a predicted cut.

| Detector | TP | Extra cuts | Missed cuts | Boundary F1 | Exact documents |
|---|---:|---:|---:|---:|---:|
| Qwen2.5 original | 286 | 41 | 29 | 89.10% | 252/335 |
| Qwen3.8 OFF original | 290 | 49 | 25 | 88.69% | 264/335 |
| Qwen3.8 OFF V6 | 297 | 41 | 18 | 90.96% | 288/335 |
| Qwen3.8 OFF V9 | 307 | 13 | 8 | 96.69% | 309/335 |

V9's 21 boundary errors compare with 74 in the original OFF run. Its nine-source
development subset is exact, but the full historical set is not. These scores are
computed by replaying the recorded frozen stages and deterministic policies, not
by claiming a fresh integrated rerun of all 20 sources. All historical errors have
now been inspected; the whole set is development-exposed for further changes.
The legacy `fresh` stratum name does not imply an unseen test here.

Evidence: `experiments/qwen38_improvement_20260906/features_v9_full_scores.json`,
`features_v6_full_scores.json`, and the stage runs referenced inside them. The V9
recipe required 1,179 successful model requests across its recorded stages, versus
2,144 for the original OFF detector. Historical stage wall times overlap with other
GPU experiments and are unsuitable for a speed comparison.

### Integrated Gergana results and thermal regression

Against unchanged review v1 (5 sources, 84 pages, 35 documents):

| Detector | TP | Extra cuts | Missed cuts | Boundary F1 | Exact documents |
|---|---:|---:|---:|---:|---:|
| Qwen3.8 OFF original | 27 | 4 | 3 | 88.52% | 26/35 |
| Integrated V7b | 28 | 2 | 2 | 93.33% | 29/35 |
| Integrated V9 | 28 | 3 | 2 | 91.80% | 29/35 |

V9 adds an incorrect cut at Review05 p10: the right thermal page looks like a
fresh calculation but is actually an interior report page. It still misses the
new detail appendix at p25. A three-window thermal probe was frozen using these
errors and the historical thermal restart before reading the separate pilot's
accuracy. It asks for a completed concluding summary on the left and a genuinely
fresh calculation/detail set on the right. This proposal is not yet a validated
fix. Gergana is now development-exposed for this follow-up.

The apparent reference questions at Review01 p6 and Review02 p11 remain pending;
no labels have been changed. The separate cover/body disagreement is a filing
convention issue, not evidence that every visual transition should be a cut.

### Production output integrity and separate speed check

An isolated V9 production checkout processed two Gergana originals (34 pages)
in 275.26 seconds, or 8.10 seconds/page. A repeat completed in 1.18 seconds by
reusing completed outputs. This is a small sample, not a whole-corpus ETA.
All 34 output pages were rendered at 72 dpi and matched the original page pixels
exactly. The check also verified one-time coverage in original order, page counts,
media boxes, rotations and manifest output hashes. No originals were modified.
Evidence: `production_smoke_status.json`, `production_smoke_fidelity.json` and
`production_smoke/input/split/` under the improvement experiment directory.

### Separate paired pilot, frozen before accuracy inspection

Five `tests2` sources were chosen deterministically, one per length band, with
separate permit case groups and no basename/SHA overlap with the historical 20.
The pilot has 223 pages. Selection used metadata and a fixed hash seed, not
model errors or document content. Existing reference splits and gap masks are
preserved. They are older archive references, not newly human-reviewed truth;
`tests2` was also used in older project iterations.

The original detector and frozen V9 run sequentially on the same GPU, server and
isolated checkout. This preserves meaningful paired timing. Thermal and anchor
probes wait until both jobs finish. See `tests2_pilot_selection.json`,
`tests2_pilot_status.json` and `integration_archive_snapshot.json`.

### Bounded anchor-context probe

The adjacent-page model sometimes reads the tail of one table as belonging to a
new table on the following page. A frozen probe instead supplies the current
predicted document's opening page and the candidate page. It extracts artifact
kinds and allows only technical-assignment → explanatory-note and quantity-schedule
→ tree-inventory recoveries. It does not introduce generic quantity-table,
waste-plan or page-number-reset rules. Candidate selection uses all matching
negative headings in historical V9: 20 windows, including 15 true continuations.
Anchors come from predictions, not reference labels, and are fixed for the pass.
The proposal is experimental until the actual probe and controls finish.

Provenance qualification: V9 was frozen before the paired pilot began. During
operational progress checks, legacy log tails incidentally exposed pilot document
headings. Later thermal/anchor/single-pass proposals use historical/Gergana errors
and were not selected using pilot accuracy, but should not be described as a
pristine blind experiment. The separate pilot itself also has older references
and prior project history, as noted above.

### Completed separate 223-page paired pilot

The same server and frozen checkout ran the original detector, then V9. References
were unchanged, with five of 67 documents excluded from exact scoring by existing
gap masks. All boundaries below use the strict masked scorer.

| Method | TP | FP | FN | F1 | Exact eligible documents |
|---|---:|---:|---:|---:|---:|
| Original OFF | 54 | 10 | 4 | 88.52% | 52/62 |
| V9 OFF | 58 | 8 | 0 | 93.55% | 59/62 |

Original elapsed: 1,459.83 seconds (6.55 seconds/page). V9 elapsed: 1,745.05 seconds
(7.83 seconds/page), about 19.5% slower. V9 includes its failed request and an
unchanged checkpoint resume, excluding the manual idle gap. This is a accuracy
improvement with a measured time cost, not a speed win over original OFF.
The 34-page production sample's 8.10 seconds/page is consistent with this range.

V9 required 366 calls (365 successful, one failed), versus 573 successful original
calls. V9 generated more output tokens: 69,512 including the failed completion,
versus 39,161. Fewer requests alone therefore does not establish faster inference.
The saved V9 `processing_seconds` sum excludes work done before the failed source
resumed; use the controller's combined elapsed and full seam accounting instead.

### One OFF truncation and bounded recovery

The V9 first pass on pilot source `Image_00112032025103907268.pdf`, p30→31,
ended with `finish_reason=length` at 4,096 output tokens, zero reasoning tokens,
after 63.28 seconds. The evaluator failed closed. Its original client did not
retain the incomplete text, so the exact contents of that failed generation are
unknown; do not assume it was the earlier medium whitespace failure.

The unchanged request succeeded on the first checkpoint resume, returning 519
characters of complete JSON. An observational wrapper saved resumed HTTP responses
without changing prompts, schemas, sampling or weights. Completed seams were
reused. The full paired pilot then finished.

The local client now distinguishes `Qwen38TruncatedError` and the splitter gives
an OFF truncation one identical retry. Format repair and OFF-length recovery share
one budget: at most two calls total. HTTP/transport errors, malformed/missing
finals, refusals and medium truncations still propagate; repeated OFF truncation
also fails closed. Both attempts and failed tokens remain counted. The recovery
policy is recorded as `format_or_off_length_once_v2` in runtime identity. The full
suite passed 139 tests before context-mode integration. Frozen pilot files were
not overwritten with this change.

### Thermal and anchor probes completed; V10 replay

All three thermal windows passed the intended discrimination: retain the true
historical p7 start, remove Gergana Review05 p10's false restart, and recover its
p25 detail appendix. The 20-window anchor probe added exactly two correct starts:
historical technical assignment→note p59 and quantity schedule→tree inventory
p159. It changed none of the 15 continuation controls. No additional anchor
candidates exist in the V9 Gergana or pilot outputs; their thermal candidates are
exactly the two Gergana windows already tested.

Replaying these validated facts over V9 yields:

| Dataset | F1 | FP | FN | Exact documents |
|---|---:|---:|---:|---:|
| Historical 20 / 733 pages | 97.02% | 13 | 6 | 312/335 |
| Gergana 5 / 84 pages | 95.08% | 2 | 1 | 31/35 |
| Earlier pilot 5 / 223 pages | 93.55% | 8 | 0 | 59/62 eligible |

These are a stage replay, not a new full integrated inference run. The new optional
`archive-context` implementation has tests for interrupted verification, cached
attempt accounting, removing a false earlier recovery, and fixed predicted anchors.
Labels remain unchanged. Evidence: `features_v10_scores.json`,
`thermal_transition_probe/`, `anchor_context_probe/`, `thermal_external_selection.json`.

### Remaining structural error and a final untouched-case check

The pilot has six extra cuts between structural frames, walls and calculation
subsections. The V7 instruction already said to group these, but the model's
relationship verdict still called each a separate instrument. A typed verifier
now tests whether both pages are substantive structural calculation body, while
preserving thermal reports, title sheets, narrative notes, independent drawings
and visibly different project/report references. The 51 selected positive windows
span all historical/Gergana/pilot outputs and include 37 true boundaries as controls.
No filename or reference-boundary condition enters the rule. This proposal is not
promoted before its complete results are inspected.

Because this rule uses pilot errors, that pilot is now development-exposed for the
structural follow-up. A final 50-page pair from the two remaining unused permit
case groups was selected by fixed seed and metadata only. Three distinct unused
groups were infeasible; exactly two remain after excluding the historical and
pilot groups. Existing references/masks are preserved. No final-case accuracy or
page content is used to select the final rule. See `tests2_final_selection.json`.

### Bounded OFF recovery supersedes the identical retry

The direct V7 development run failed twice on historical source
`Image_00112022025163444215.pdf`, p9→10. A diagnostic response exposed repeated
escaped non-breaking spaces inside `right_heading`. Compact external JSON
whitespace constraints cannot stop this in-string generation loop. The frozen
SGLang/XGrammar runtime accepts string `maxLength` constraints. A bounded probe
using the same images and prompt completed in 5.21 seconds and 185 tokens.

Recovery policy `format_or_bounded_off_length_once_v3` now supersedes v2 above.
An OFF length failure receives one retry with heading strings limited to 160
characters, other strings to 256, and confidence represented by integer enum
0–100. Prompt, token cap and sampling stay unchanged. Format repair and length
recovery share one extra-call budget; repeated failure remains an error. Local
HTTP integration tests verify the conditional schema, unchanged prompt/cap and
accounting for failed tokens. The later live runtime replay succeeded on its
first ordinary request, so it did not exercise automatic recovery itself.

The incomplete direct V7 development run remains recorded as incomplete. A
posthoc replay supplying its missing response from the bounded probe scores
99.40% F1, 91/92 exact documents. A separately audited single-receipt rule removes
its remaining false cut. This development replay is not a fresh complete fast run.

### Guarded structural facts and supporting receipts: V11

The broad structural verifier proposed ten merges: eight correct, two harmful.
Typed guards preserve coordinates, quantity schedules, fresh thermal recoveries,
full report titles and visibly different project references. The guarded policy
keeps seven safe merges across the tested sets. A single high-confidence postal
receipt can attach to the preceding explicit municipal notice when it is not the
start of a receipt batch. Its audit changes only two false cuts across the
conservative and direct-V7 development outputs. No filename or label is an
inference condition.

V11 stage replay scores 97.32% F1, 314/335 exact historical documents; 95.08%,
31/35 on Gergana; and 98.31%, 60/62 eligible on the earlier pilot. All three sets
have contributed development evidence by this point. Original reference labels
and masks remain unchanged.

Both integrated implementations were frozen in `final_snapshot.json` after 143
local tests passed. `archive-context` uses V6 plus selective V7 refinement;
`archive-fast` uses V7 directly, followed by the same typed checks and filing
policies. Fast must match conservative F1 and exact documents on both the reserved
50-page check and Gergana before a full 733-page fast run. That full run must then
match conservative V11's historical replay before fast is selected for production.

### Frozen final case check

The original detector scored 92.00% F1, 24/26 exact documents in 345.65 seconds.
Conservative and fast both scored 97.96%, 25/26 exact, in 347.19 and 220.41 seconds
respectively. Fast took 36.5% less time. Neither new method had a failed request.
No error in these two reserved case groups was used to tune the frozen policies.

The fresh conservative Gergana run also completed: 95.08% F1, 31/35 exact, matching
its replay. It took 655.15 seconds. The broader fast comparison remains in progress;
its completion and production smoke verification belong in the final results report.

At 06:50 UTC the final integrated historical fast run exercised automatic bounded
recovery on the previously looping p9→10 window. Its checkpoint completed without
process restart: two calls, one failed, 4,281 total output tokens, zero reasoning
tokens. The successful retry took 3.40 seconds; the entire seam took 66.73 seconds
including the initial truncated generation and page loading. The returned invoice
→ cadastral-sketch cut is correct. This is actual integrated recovery evidence,
distinct from the earlier isolated client replay that succeeded on its first call.

### Additional receipt errors exposed by the full fast run

The fast run introduces an extra cut inside an established receipt batch at
historical source `083553577`, p10. Both model headings read `ПОСТАВЯНЕ` instead
of `ДОСТАВЯНЕ`; its own evidence identifies postal receipts. Neighbouring pair
comparisons read the same physical pages correctly. An isolated OCR bridge
requires high-confidence receipt readings on both neighbouring comparisons,
matching same-page headings at >=0.90 normalized string similarity, and no known
non-receipt page type. It changes only that false cut in the first 54-source-run
development audit. Four tests cover conflicting titles, typed instruments,
missing/low-confidence neighbours, batch starts, immutability and idempotence.
It remains separate from the frozen benchmark while testing continues.

Two other fast errors split a receipt from a following municipal notice. A broad
receipt→notice merge is rejected: the saved references contain both true and false
cuts there. A four-window identity probe is queued after the frozen controller
finishes. It reads outgoing correspondence references independently, including
recipient/copy suffixes and dates, and refuses barcode/permit/project substitutions.
The true-cut control visibly uses a different copy suffix. Complete reference
matching is a proposed fact check, not yet an accepted filing rule. Reference
labels are absent from probe cases and prompts; the final50 set is excluded from
candidate selection. Evidence: `reverse_receipt_probe_frozen.json`,
`reverse_receipt_candidates.json`, `receipt_consistency_audit.json`.

### Frozen full fast run completed; accuracy gate failed

All 20/733 historical pages completed in 3,500.27 seconds (58m20s, 4.78s/page),
with no process restart. There were 805 model calls, 804 successful and one
truncated call recovered automatically, 121,200 output tokens and zero reasoning
tokens. Strict score: TP310/FP18/FN5, F1 96.42%, 311/335 exact documents,
13/20 entirely correct sources. Conservative V11 replay is TP309/FP11/FN6,
97.32%, 314/335 exact. The full accuracy gate therefore rejected fast and selected
conservative for the original 26-page production smoke check.

Fast's extra disagreements relative to conservative include receipt/notice joins,
a misspelled receipt heading, a contract appendix, a quantity schedule, two
apostille/translation joins and a cover/body join. It also repairs a missed safety
note and a false project-identifier cut. The smaller final50 and Gergana comparisons
alone were insufficient to establish its full-set accuracy. Later receipt repairs
must be reported as separate postprocessing/probe results, not silently folded
into this completed frozen benchmark.

### Receipt proposals resolved

The complete 55-source-run OCR-consistency audit changes only the known receipt
batch false cut. Replaying it over the complete fast run yields TP310/FP17/FN5,
96.57% F1 and 312/335 exact documents; Gergana and the final50 outputs do not
change. This still fails the historical accuracy gate. The rule is retained as a
terminal postprocessor after all model/context stages. Raw answers stay intact,
review metadata records the correction, and no additional model query is made.
A new code/settings fingerprint prevents stale cache reuse. The full local suite
passes 148 tests. `archive-context` remains the recommendation.

The reference matcher is rejected. Its first adapter attempt passed a raw JSON
schema to an API expecting the project's field-type mapping and failed before
HTTP. The fixed two-image probe completed four windows in 16.66 seconds. It
proposed two correct merges, but its negative control misread both copy suffix
and date, preserving the boundary for the wrong reason. Adding a top-left receipt
close-up completed in 16.70 seconds and still misread that suffix at 95% confidence;
it now proposed a harmful merge. Both variants and the factual error are preserved
in `reverse_receipt_decision_audit.json`. No reference-number merger or crop was
deployed. The additional 89-page prefix input set prepared for that proposal was
not run and is not a validation result.

The frozen V11 conservative production check completed 26 pages in 219.41 seconds,
with a cached repeat in 0.85 seconds. Every exported page matched original pixels
at 72 dpi, with counts, order, geometry, rotation and hashes verified. A separate
final-code check uses 26 conservative pages and the 48-page fast receipt regression;
its final timings and fidelity are recorded in the results report after completion.

### Final release checks completed

The final code completed the 26-page conservative sample in 219.31 seconds
(53 calls) and the 48-page fast receipt regression in 198.18 seconds (48 calls),
with no failed calls. Cached repeats took 0.97 and 1.33 seconds. Both source start
lists exactly match current references: 5/5 and 21/21 documents. The regression
again generated the erroneous raw p10 cut, then terminal reconciliation corrected
it. All 74 exported pages passed rendered-pixel equality at 72 dpi, coverage/order,
page counts, media boxes, rotation, source-byte and output-hash checks. Representative
exported pages were visually inspected. Evidence: `receipt_release_status.json`,
`receipt_release_fidelity.json`, `receipt_release_snapshot.json` and the two local
`receipt_release_*` output directories. No automatic receipt-reference merge was
included. `archive-context` remains the selected method.
