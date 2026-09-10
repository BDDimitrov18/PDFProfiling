**Project review — 5 September 2026**

This is the pre-change review at `f56c0e9`. Subsequent implementation and verification are recorded in [IMPROVEMENTS.md](IMPROVEMENTS.md). Statements about the working tree below describe that reviewed snapshot.

Reviewed at `f56c0e9` on `main`. This report consolidates the current implementation, recorded iterations, saved predictions, evaluation data, representative page images, and production economics. It separates reproduced findings from historical reports and proposed experiments. No inference, production, or ground-truth code was changed, and no GPU or external model was used for this review.

**The current baseline is the restored #2+#4 candidate.** Both `split.py` and `rotation.py` are byte-identical to commit `9fee964`. The full MD5 of `split.py` is `63da033b48f25929e732672d9d03b925`. Commit `9629ed4` removed the unadopted table-confirmation and domain-rule experiments. The warning at RESULTS.md:40 claiming HEAD still contains experimental Fix-11 wiring is stale.

The intended business outcome is faster human processing of Bulgarian construction archives. Documents include permits, reports, letters, invoices, policies, drawings, quantity tables, cover sheets, and attachments. A heading, signature, repeated form, or new sheet can occur inside a document. Some filing decisions also accept more than one segmentation. This makes the task a combination of visual perception, document-instance identity, and filing policy.

**What runs today.** The original `docs/SPEC.md` describes an earlier M3/MLX/Qwen3-VL-8B design with overlapping votes, vision-feature caching, folder watching, and classification. The live implementation uses Hugging Face Transformers, Qwen2.5-VL-32B-Instruct, CUDA, and bitsandbytes NF4 quantization. These are materially different architectures. The model is self-hosted; rented GPU time is a real processing cost.

The production path is `run_production.py` → `split.detect_boundaries(..., classify=False)` → `split.split_pdf`. It loads the model once, recursively discovers PDFs, optionally filters a shard file, and writes each source's documents under its adjacent `split/` directory. Production filenames contain code `00000`; classification is deliberately disabled.

Boundary detection works as follows:

1. Render pages at 150 DPI with Poppler/pdf2image. Retain a small rolling image buffer.
2. Run Tesseract OSD once per loaded page and rotate the images used for inference when OSD is sufficiently confident. Rotation smoothing is diagnostic only.
3. For each page n before the last page, ask a style question about n/n+1 and an end-of-document question about n−1/n/n+1. There are two base model calls per seam, plus conditional checks. Buffered images do not constitute a reusable model vision-embedding cache.
4. Interpret `signal_on_page` differently for end signals and start signals. End signals place the new start after the signal page; start signals place it on the signal page.
5. Apply title transcription/localization, one-page disambiguation, appendix state, a signature/next-page gate, and low-confidence confirmation. An additional start detector can add a boundary at n when an end signal or style break enables it.
6. Deduplicate identical start indices and split original PDF pages. Optional classification examines the first page of each segment, with a second-page peek for cover pages.

There is no majority vote over three windows and no full-document semantic memory. The model sees local windows; Python retains the decisions and appendix state. Rotation corrections affect inference images, while exported PDFs preserve source-page orientation. In production mode every boundary has `flagged=False`, even when confidence is low.

**Repository map.**

| Area | Role |
|---|---|
| `split.py`, `rotation.py` | Live model prompts, routing, orientation, segmentation, optional classification |
| `run_production.py`, `supervisor.sh` | Batch discovery, sharding, restart behavior |
| `eval_boundaries.py`, `score_full.py`, `reroll_scores.py` | Detection evaluation and rescoring saved predictions |
| `build_eval_set.py`, `build_full_eval.py` | Derive reference boundaries from PDFsam splits and build evaluation folders |
| `test.py`, `stats.py`, `reports/stats_run*.txt` | Older evaluation and historical summary machinery with different metric conventions |
| `nomenclature_match.py`, associated tests/experiments | Standalone CPU title matching; not integrated into production |
| `archive/`, Git history | Run-8/run-9 snapshots and recoverable rejected experiments |
| `logs/`, `attestations/`, `data/`, `eval_*/` | Predictions, decision traces, page evidence, nomenclature, labels and waivers |
| `RESULTS.md`, `docs/candidate_mistakes.md` | Detailed experimental record; some statements and totals have been superseded |
| `Calculations.numbers` | Six recorded manual-work/cost comparisons |

**How the iterations developed.** The pre-Git runs survive mainly as reports and selected logs; the initial Git commit is 10 June, after several of those runs. Their precise implementations and environments cannot all be reconstructed from the available evidence.

| Period / change | Evidence and lesson |
|---|---|
| Runs 2–5 | Historical average F1 rose from 56.8% to 73.7%, but file counts changed from 10 to 17. These are not controlled deltas. Early signature-ownership questions confused starts, closing pages, and one-page documents. |
| Run 6: next-page gate | Historical average F1 80.7% over 21 case labels. Checking the next page reduced signature-driven overcuts. |
| Run 7: one-page handling | Historical average F1 83.8%. Better handling of short documents, with closing-page ambiguities remaining. |
| Run 8: independent starts | Historical average F1 88.5%. Start detection recovered boundaries that end detection missed. A genuine run-8 snapshot was subsequently fingerprinted against historical predictions. |
| Runs 9–14 | Changes to confirmation, style modifiers, and rotation did not establish a clear improvement over run 8. Run 13 reports 89.4% average on 49 tests2 case labels; run 14 is a partial 19-label report. |
| Fix R | OSD rotation was integrated into Phase 1. Recorded rotation evaluation: 2 TP, 0 FP, 12 FN. This was a conservative precision result with low recall. |
| Fix 4 | Removed signal-category confidence anchoring and capped noisy signals. Corrected-GT dev F1 improved from 85.88% to 90.17% on the historical 5090 comparison. |
| Fix 8 | Forced titled starts through generic confirmation. It removed some false positives but rejected genuine starts; eventually reverted. |
| Fix 9 | Excluded drawing titleblocks and explicit continuation counters from titled starts. Fix9-only beat Fix8+9 and became the round-1 candidate. |
| Round 2 #2 | Requeried out-of-window signal positions instead of silently substituting a page. Kept, but its isolated probe score was neutral. |
| Round 2 #4 | Read the claimed title/identifier before accepting a titled start. Both present: retain confidence. One present: accept capped at 0.60. Neither: seek a unique title elsewhere in the window or suppress. This produced the principal measured improvement over round 1. |
| A / B / D and A′ | Duplicate-relocation handling, next-page-gate rebuilding, and one-page-check bypasses improved selected dev cases but regressed aggregate performance. Even an apparently inert suppression changed downstream start-detector behavior. |
| Fix 11 v1/v2 | Table confirmation recovered some missed starts but added overcuts. Numbering-based v2 failed both stacked and isolated probes. Visual review showed misread row numbers as well as faulty assumptions about numbering resets. The completion-based v3 design was not validated. |
| Domain rules | All rules together regressed. Dropping the explanatory-note closure rule produced a small gain, but the extra extraction cost was judged unjustified and the code was removed. |

The old “average F1” rows use rounded per-case values, can collapse multiple source PDFs into a case label, and use the older evaluator that includes the automatic start at page 1. Current scores are pooled boundary counts excluding page 1. Ground truth and GPU environments also changed. Old headline percentages must not be placed on one continuous performance curve.

**Reproduced comparison on the same current ground truth.** The following values were recomputed from all 20 saved prediction arrays using committed GT v3, with no masked ranges. Each log contains predictions for all 20 files.

| Build | Dev F1 | Holdout F1 | Fresh F1 | Aggregate F1 | TP / FP / FN | Exact reference documents |
|---|---:|---:|---:|---:|---|---:|
| Round-1 Fix9-only | 90.59% | 81.48% | 84.41% | 85.84% | 291 / 72 / 24 | 233 / 335 |
| Run-8 referee | 89.82% | 76.92% | 87.15% | 87.42% | 285 / 52 / 30 | 243 / 335 |
| **Current #2+#4** | **92.12%** | **81.48%** | **88.44%** | **89.10%** | **286 / 41 / 29** | **252 / 335** |
| A+B+D | 93.33% | 76.92% | 86.92% | 88.16% | 283 / 44 / 32 | 245 / 335 |
| A+D | 93.33% | 81.48% | 87.07% | 88.41% | 290 / 51 / 25 | 249 / 335 |
| A′ suppression | 92.12% | 81.48% | 88.14% | 88.89% | 284 / 40 / 31 | 250 / 335 |

Current precision is 87.46%, recall 90.79%. Versus round 1, the candidate eliminates 31 extra cuts while missing five additional true starts. Its gain is 3.26 percentage points under current GT, rather than the 3.15-point gain quoted for an older label/mask configuration. Only four complete source PDFs have an entirely exact segmentation. Exact-document recovery is 75.22%, where a document counts only if both endpoints match. This is a stricter operational measure, still subject to the chosen filing convention.

The committed one-page waiver changes candidate F1 to 89.24%. The separately reported 92.52% human-reviewed figure credits 17 alternative splits and removes four disputed misses. It is a different labeling interpretation, not a measured algorithm improvement. The mistake document now contains the remaining 49 rows (24 FP, 25 FN), while its introduction still quotes all 70 strict errors. Accepted alternatives should be captured in structured, versioned annotations before using them as a reproducible metric.

The original Fable-5 replay was one file, a different model, and the round-1 routing. Its historical 80.00% versus 84.21% comparison used older labels. Rescoring that file on GT v3 gives 82.93% for the saved Fable replay, 87.18% for round 1, and 94.44% for current #2+#4. These are saved-output comparisons, not a new model benchmark. Better transcription in the replay coexisted with excessive splitting of repeated forms; a more capable model alone did not resolve filing granularity.

I also recovered the pure domain-rule implementation from `6bc669b` in memory and rescored the retained 733-page marker cache. All rules reproduce 88.92%; excluding R4 reproduces 89.62%. R1 and R7 alone yield 89.51% in this retrospective diagnostic, removing three false positives without losing a true boundary. This is a small, already-exposed-sample result, not a validated new candidate. R4's unbounded search for a later signoff swallowed true starts. Marker text is useful evidence, but a printed role label alone does not prove that a document has closed.

**The evaluation data needs attention before another optimization round.**

- `eval_full` contains 20 PDFs / 733 pages: 9 dev, 3 holdout, 8 fresh. Current dev/probe/holdout labels agree with their full-set subsets.
- `tests/` actually contains 21 originals / 798 pages. The full-eval builder misses the flat `РС-37-2017/Image_00112022025144119764.pdf` because it only walks two nested directory levels.
- `tests2/` contains 52 originals / 1,507 pages across 50 case folders, with reference PDFsam splits. Historical run-13 summaries exist, but there is no committed modern candidate evaluation over this corpus. It is useful for a new validation partition after coverage and labeling checks, though it is not historically untouched data.
- Read-only re-derivation proved that rebuilding labels would remove the attested p13 start from `163444215`, reintroduce p63/p66 in `143041245`, and reinstate masks around the previously settled ranges in `143041245` and `145428614`. The builders do not preserve later human corrections.
- Saved result JSONs embed the ground truth from their run. For example, current-candidate JSON reports 250/336 exact documents under old labels; rescoring gives 252/335. Predictions are reusable; stored summary numbers are not timeless.
- Repeated examination of “holdout” and “fresh” errors has exposed both partitions to tuning. The labels describe historical roles, not a pristine current test set. Domain rules were explicitly derived from these same errors.
- Older rotation scoring tests only page membership, while the newer evaluator checks exact degrees. The newer rotation evaluator visits only files present in its sparse rotation-truth map, leaving wholly upright files out of the precision denominator.

**What the errors actually suggest.** Recomputing adjacency gives 28 extra cuts adjacent to an also-predicted true start, 12 isolated extra cuts, and one pure one-page localization error. The earlier 29/11/1 statement is off by one under the current labels: `143041245@66` is isolated after the GT correction. Adjacency is an observable pattern, not proof that every such cut has the same cause.

There are 196 one-page reference documents out of 335. Predicted adjacent-start pairs include 159 pairs where both starts are correct, counting page 1. In a diagnostic, greedy adjacent-cut suppression yielded F1 68.74% when retaining earlier starts and 70.36% when retaining later starts. A useful resolver must distinguish a closing page from a complete one-page document using evidence. A distance-only rule is unsuitable.

Representative retained page images support distinct failure mechanisms:

- `084837699` p7 is a closing/signoff page; p8 has the explanatory-note opening. The prediction cuts both. This is a concrete extra-cut example.
- `143041245` p19 is an ИСКАНЕ with a signature; p20 opens a ДОКЛАД from the same issuer. The logged merge is a judgment failure despite visible content.
- `142438096` p8 is a sideways invoice. Perception/orientation needs to be separated from document-policy reasoning.
- `163444215` p37 visibly contains numbered rows 11/12, a subtotal, and signoff material. This supports the recorded correction to v2's claimed `10→1` reset. Totals, repeated headers, and section numbering need interpretation in context.

The “NO-SIGNAL” label therefore conflates a skipped start check, failure to read the page, and a mistaken continuation judgment. They require different experiments. Current start detection is conditional on another end signal or a style break, so visually similar document transitions can be missed without a direct start question. It also never runs with the final page as n.

**Concrete engineering findings.** These are distinct from hypotheses about model accuracy.

| Finding | Evidence / consequence | Suggested change |
|---|---|---|
| Partial output is treated as completed | `run_production.py:41` skips if any matching split PDF exists. A temporary-directory failure simulation wrote one partial segment; restart skipped the source and printed `PRODUCTION_DONE 1/1`. | Stage a complete per-source output set, validate page coverage/readability, and atomically publish a completion manifest. Resume against source/config identity. |
| Supervisor can stop after failures | Driver prints `PRODUCTION_DONE 0/1` after a failed file and returns normally. `supervisor.sh:9` treats any `PRODUCTION_DONE` text as completion, including an old log entry. | Distinguish completion from failure with a current-run status/exit code and explicit expected/completed/failed counts. |
| Confirmation can inspect a different seam | `split.py:1130` confirms n/n+1 after `effective_end` may have moved. A mocked n=2 case with an end signal on p1 confirmed p2/p3 while committing a start at p2. | Carry the candidate's actual left/right page indices through every check. Measure score effects rather than assuming all old mistakes are explained by this. |
| Production discards review flags | `split.py:1221` forces `flagged=False` for boundary-only mode. The diagnostic returned a 0.75-confidence boundary without a review flag. | Preserve uncertainty/evidence independently of classification; rank review work rather than trust raw model confidence as calibrated probability. |
| Inference/JSON errors can become ordinary decisions | `_infer` returns None on failure. Query-specific parsers substitute no-signal or permissive defaults. The candidate log contains three `No JSON` warnings. | Record explicit error/abstention states, bounded retries, and source completion health. A page-count conservation check cannot detect a whole source mistakenly merged into one document. |
| Reproducibility setup is incomplete | `requirements.txt` still installs the old MLX stack. The CUDA lock omits the Python `pytesseract` dependency used by live rotation; missing it silently causes abstention. Historical scripts can import current root modules. | Document one supported runtime and pin model/processor revision, dependencies, render/OSD settings, prompts, code, source hashes and GT version per run. Keep a real baseline rerun when the environment changes. |

Additional classification issue, outside current production scope: runtime nomenclature contains 360 codes / 198 unique names. The XLS contains 382 rows / 381 distinct codes / 220 names, including duplicate code `19105`. Twenty-two rows (21 distinct codes) are absent from runtime. The “382 entries” runtime comment is inaccurate. Classification needs a canonical table and separate label evaluation before it is enabled as a deliverable.

**Production and economics.** RESULTS.md records 134 PDFs / 4,138 pages processed for GIS_Pv, about 1,500 output documents, with source/split page counts reconciled. It reports roughly 15 GPU hours for useful work at the then-confirmed $1/hour rate; an earlier ephemeral-disk crash added about 12–13 hours. This is historical operational evidence, not a current price or a labeled accuracy test. The record also says only 129/134 sources' outputs were pulled locally at that time. The production corpus/output mirror is absent from this checkout, so current delivery completeness could not be independently checked.

`Calculations.numbers` has six populated case rows and static stored values, with no formula cells. Interpreting its clock fields as elapsed hours/minutes, as its hourly calculations do, total handling time is 47h43 before and 27h26 after preliminary splitting: 20h17 saved, or 42.51%. Its mean of individual percentage reductions is 48.3%, a different aggregation. Recorded revenue sums to 97.65 and machine expense to 2.052 in the sheet's unstated currency. The six-case observation supports optimizing human effort, but it is not a controlled estimate for all future work.

**Proposed order for meaningful improvements.**

1. **Protect output and establish a reproducible evaluation.** Fix restart/completion behavior, encode existing human rulings separately from generated labels, make case discovery complete, and persist structured inference results. These changes make later experiments safe to assess.
2. **Make boundary location consistent.** Represent a candidate as a seam with immutable page/evidence references. Correct confirmation routing and trace which checks add, relocate, suppress, or corroborate it. Keep this narrow at first; A′ proved that early-state changes can affect later decisions.
3. **Reduce human review work with selective evidence checks.** Target competing adjacent starts and weak evidence. Reuse cached observations and ask additional questions only where needed. Compare correction minutes and exact-document recovery alongside F1. Do not apply global adjacent-boundary collapse.
4. **Address missed starts in separate cohorts.** Distinguish unreadable/rotated pages, drawing/table transitions, and same-issuer new instances. Test additional start evidence at quiet seams and the final page, with negative controls from continuous documents. Domain granularity for drawing sets remains a policy input, not something an image-similarity threshold can establish.
5. **Measure inference cost before expanding prompts.** Start from two base calls per seam and identify avoidable or reusable work. The all-page four-channel marker pass cost about 2.4 hours over 733 pages historically. Selective extraction is worth investigating; reinstating the whole rejected rule layer is not supported by its small measured gain.
6. **Treat classification as a separate future objective.** Fix nomenclature coverage/duplicate-code handling and obtain classification labels before measuring it. Boundary F1 provides no classification accuracy evidence.

For the next behavior experiment, specify the target failure mechanism and expected changed cases in advance, retain negative controls with legitimate one-page documents, and compare against the exact current candidate on identical inputs/environment. Use source/case-level validation partitions. Report strict and explicitly versioned alternative-label metrics, document recovery, errors, elapsed GPU time, and human correction effort. A dev-only win or a convincing model explanation is insufficient evidence of improvement.

**Verification performed for this review.** Read current routing and supporting modules, traced all reachable Git history and the major retained/reverted versions, compared code bytes, rescored six complete historical runs, recomputed exact document recovery and adjacency, reconciled corpus/subset coverage, checked label-builder drift without writing labels, replayed archived pure domain rules against saved markers, inspected six representative page images, reconciled the six cost-sheet cases, and ran the 17 existing nomenclature unit tests successfully. Completion and shifted-seam findings were reproduced with mocked inference and temporary files. GPU accuracy/performance was not rerun.

To reproduce the main historical baseline table, run `python3 reroll_scores.py` from the repository root. `python3 score_full.py eval_full logs/round3_ad_fulltests.log` similarly rescores an individual full run. Exact-document figures above additionally pair consecutive starts, include the final endpoint at source page count + 1, and intersect predicted/reference intervals using current GT.
