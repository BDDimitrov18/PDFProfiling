# V12 candidate: independent page facts

V12 has completed all four fresh validation sets: **32 PDFs / 1,090 pages**.
The independent local rescore, source/reference/runtime hashes and raw model-call
accounting all passed. Historical accuracy improved from V11's 97.3228% boundary
F1 and 314/335 exact documents to **98.7382% and 325/335**. All nine changed
historical boundaries were correct. The other three sets retained their scores.
Neither source PDFs nor ground-truth labels have changed.

| Fresh set | Boundary F1 | Exact documents | Seconds/page |
|---|---:|---:|---:|
| Historical, 20 PDFs / 733 pages | 98.7382% | 325/335 | 8.773 |
| Gergana, 5 PDFs / 84 pages | 95.0820% | 31/35 | 7.846 |
| Former final, 2 PDFs / 50 pages | 97.9592% | 25/26 | 7.071 |
| Pilot, 5 PDFs / 223 pages | 98.3051% | 60/62 eligible | 7.987 |

Historical timing shared the GPU with development probes. The other sets ran
without competing model probes. All four evaluator processes completed on their
first attempt. There were 1,911 model calls: 1,910 successful and one truncated
pilot answer recovered by the existing bounded retry. All token counters are
available and reconcile with the individual checkpoint records.

The complete validated runtime is preserved under
`experiments/releases/qwen38-artifact-v12-validated-20260906`. The saved V11 release
and root runtime remain intact while the next candidate undergoes fresh validation.

## Evidence before integration

Seven simple policy ablations were checked against the full recorded decisions.
Broad thermal-output merging introduced two missed boundaries. Broad safety-note
and quantity-schedule recoveries each fixed one boundary but broke another.
Those broad policies were rejected.

A semantic selector then chose all 40 matching windows across four existing
sets, without using their labels in selection or prompts. These include correctly
handled boundaries as controls. There are 37 historical windows and one each
from Gergana, the earlier pilot, and the former final-case check.

The first three-image probe was stopped after 22 requests because its transport
annotation defined “right” as image 2, conflicting with a task using image 3.
Its outputs are retained as diagnostics, not valid accuracy evidence. A corrected
transport probe completed 40 requests in 285.52 seconds with no request failures.
It recovered six boundaries, reaching 98.26% F1 and 321/335 exact documents in a
recorded-run overlay, but some facts still confused page roles.

The selected approach reads one image at a time, with no pair-role annotation.
The same 40 windows required 87 unique page reads, including opening-page context.
All 87 requests succeeded in 299.01 seconds. This removes cross-image attribution
from each fact-extraction request. The original frozen transition policy then
recovered seven boundaries: 98.42% F1 and 322/335 exact historical documents.

Two additional narrow policies were tested against those facts: a named equipment
schedule following a safety note need not begin with row 1; an interior software
plot without an issued drawing title block can continue its calculation body.
They recover two more boundaries. Regression controls and tests preserve continuing
equipment tables, fresh report starts and independently issued drawing sheets.

| Set | V11 baseline F1 / exact documents | V12 recorded-run overlay |
|---|---|---|
| Historical: 20 PDFs / 733 pages | 97.32% / 314 of 335 | 98.74% / 325 of 335 |
| Gergana: 5 PDFs / 84 pages | 95.08% / 31 of 35 | unchanged |
| Former final check: 2 PDFs / 50 pages | 97.96% / 25 of 26 | unchanged |
| Earlier pilot: 5 PDFs / 223 pages | 98.31% / 60 of 62 eligible | unchanged |

The historical overlay has six extra cuts and two missed cuts, compared with
eleven and six respectively in V11. All nine changed boundaries agree with the
unchanged references. The pilot baseline itself is a V11 stage replay; the other
baseline predictions are from fresh integrated runs.

These are development results, not a new unseen accuracy estimate. Every set is
now development or regression evidence. The original final50 result retains its
historical pre-inspection status for V11, but it is not an unseen V12 test.

## Candidate behavior

The new stage runs after all existing V11 model stages and receipt reconciliation.
It freezes the predicted opening pages before making any new decisions. It reads
each selected page once per source, checks its type and literal heading, and
compares those facts in code. No label, filename rule or expected split is passed
to inference. Existing raw decisions remain intact in the logs.

The retained changes concern explicit contract annexes, coordinate-register title
sheets, separately introduced waste/safety notes, graphic-part covers, matching
heating/cooling outputs, named equipment schedules and interior software plots.
Uncertain types and insufficient confidence preserve the existing decision.
Heating/cooling merging requires an explicit matching named subject on both pages.

Page checkpoints include source and settings identity. Single-page transport
settings are restored even when a request fails. Completed work is reused only
within the same frozen run identity. Summary timing and review metadata remain
idempotent on resume.

## Validation procedure and evidence

The candidate runtime passed 157 automated tests. The first isolated test attempt
revealed a missing supervisor shell script in the copied test environment; adding
that existing script resolved the harness failure. The completed snapshot contains
122 verified files. The main working runtime and the preserved V11 archive are
unchanged.

The remote controller first evaluates one complete affected PDF from scratch and
requires its predictions to match the frozen probe result. It then runs all four
sets from empty result directories: 32 PDFs and 1,090 pages. The promotion gate
requires no decrease in F1 or exact documents on any set, and an increase in exact
historical documents. Bounded evaluator retries may resume only the new run's own
checkpoints. Failed runs remain explicitly failed.

The initial cold check has passed: the complete nine-page source
`Image_00112032025085002901.pdf` finished in 95.69 seconds and recovered its safety
note and equipment-schedule starts at pages 8 and 9. Its predicted starts match
the frozen probe exactly. The known cover-to-contents extra cut remains: the
sample scores 90.91% F1 and 5/6 exact documents, so this is not a perfect sample.
All four full evaluations have now completed; final scores are reported above.

Candidate archive: `experiments/releases/qwen38-artifact-v12-candidate/runtime.tar.gz`.
SHA256: `2e35ddb2a5cea428ca512a6e569c2948af3985583ef5053725e556324f02d13c`.

Results and diagnostics live under
`experiments/qwen38_improvement_20260906/iteration12`, `iteration12b`, and
`iteration12c`. The live full-run status is `iteration12c/validation_status.json`
on the pod. Independent verification is recorded in
`iteration12c/independent_full_verification.json`.

The user confirmed the repository PDFsam-derived reference is authoritative.
The two previously queried conventions retain their existing labels; tentative
visual impressions did not override them. Gergana retains the existing user page
lists. Unreviewed `obraboteni` outputs are not ground truth.
