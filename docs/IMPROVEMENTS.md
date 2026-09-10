# Reliability and evaluation improvements — 2026-09-05

This pass reduces lost work and makes subsequent accuracy experiments reproducible. No new GPU accuracy result is claimed. Changes are on `codex/reliable-splitting`; the historical measured detector remains the default routing.

## Delivered

- Production stages every source's splits, validates page counts and page-range coverage, publishes the files, and writes a completion manifest last. Resume verifies source/settings identity and every output's hash and page count. Legacy partial outputs are retained in history when replaced, rather than treated as success. OS locks prevent concurrent publication for one source.
- Batch failures return a nonzero exit code. The supervisor uses that process status, not an old `PRODUCTION_DONE` log entry. A bad source does not prevent later valid sources from completing. Model exceptions propagate to retry instead of silently becoming negative boundary predictions.
- Evaluation checkpoints completed PDFs, records source/code/runtime identity, refuses incompatible cache reuse, and keeps experiments in separate run directories. A completed cache can be rescored without loading the model. `--revision` pins model and processor to the same requested Hugging Face commit; resumed inference checks resolved model/GPU details.
- Dataset regeneration preserves the four existing human correction records and rejects changed source bytes for those rulings. Default full evaluation retains historical 20-file membership and verifies its GT v3 digest. Expanded discovery includes flat folders and records unlabelled sources explicitly. Rotation evaluation data includes wholly upright files.
- Scoring accepts historical logs or result JSON, requires complete matching file coverage, applies current labels/masks, and reports exact-document recovery alongside boundary scores. Historical JSON's old label snapshots cannot silently become current scores.
- The CUDA requirements entry point replaces the obsolete MLX dependency. The June version record remains unchanged; added Pillow/Tesseract wrapper and matching torchvision pins require a new GPU baseline.

## Verification

- 39 new CPU tests and 17 existing nomenclature tests pass. They exercise interrupted staging/publication, retry, archive retention, corrupt outputs, changed sources/settings, shard discovery, locks, inference exceptions, evaluation resume, incomplete predictions, correction hash checks, gap masking, actual confirmation page pairs, and historical log reconstruction.
- Default routing matches `9fee964` across 500 deterministic mocked eight-page scenarios: identical model-query sequence, rotations, starts and confidence. This checks control flow; it does not replace real GPU inference.
- Rebuilt dev (9 files), holdout (3), and full (20) labels exactly match the current reviewed labels. Full masks remain empty. Expanded `tests` contains 21 files / 798 pages. Expanded `tests2` contains 51 labelled files / 1,496 pages, with one unlabelled 11-page source recorded separately and six sources masked around unresolved gaps.
- Rescoring both `logs/fulltests_stage2.log` and `logs/fulltests_stage2_results.json` gives the same GT v3 result:

| Partition | TP | FP | FN | Strict F1 | Exact documents |
|---|---:|---:|---:|---:|---:|
| Dev | 76 | 6 | 7 | 92.12% | 76/92 |
| Holdout | 11 | 1 | 4 | 81.48% | 10/18 |
| Fresh | 199 | 34 | 18 | 88.44% | 166/225 |
| All | 286 | 41 | 29 | 89.10% | 252/335 |

The aggregate exact-document rate is 75.22%. These are rescored historical predictions, not new inference results. Machine-readable scores and audit counts are saved in [verification_2026-09-05.json](verification_2026-09-05.json).

## Confirmation candidate and GPU decision

The detector may relocate a proposed end from iteration `n` to another page. Historically, low-confidence confirmation still used pages `n,n+1`. The opt-in `--align-confirmation` candidate instead confirms `effective_end,effective_end+1` after final-page projection is resolved. A forward projection can briefly require a fourth page image, which receives normal rotation handling. Strong title/header exemptions remain in place.

Unit expectations, fixed before GPU evaluation:

| Scenario at iteration 2 | Legacy pair | Candidate pair / action |
|---|---|---|
| End relocated to page 1 | 2,3 | 1,2 |
| End stays on page 2 | 2,3 | 2,3 |
| End relocated to page 3 of a longer source | 2,3 | 3,4, with page 4 rotated for inference |
| Page 3 is self-contained | 2,3 | 2,3 after correction |
| Projected end is the final continuation page | 2,3 before projection check | no out-of-range confirmation |
| Confirmation rejects proposed seam | suppress | suppress; no confidence or start recorded |

The historical audit found **zero mismatched pairs** among **228 confirmation calls** across six saved full-benchmark runs:

| Log stem | Confirmation calls | Same pair |
|---|---:|---:|
| round1_candidate | 33 | 33 |
| run8_stage3 | 44 | 44 |
| fulltests_stage2 | 33 | 33 |
| round3_ad_fulltests | 34 | 34 |
| round3_abd_fulltests | 50 | 50 |
| round4_aprime_fulltests | 34 | 34 |

`audit_confirmation.py` reconstructs proposed seams from the detector's logged signal and projection decisions. It is independently tested on backward and forward relocation examples. This is a latent control-flow defect, with no evidence that it caused the measured errors in these runs. **Do not rent a GPU just to rerun this candidate on the existing 20 files.** Given the same model responses, the expected historical result is unchanged.

For a future comparison with examples that actually exercise relocation, freeze the PDF list, labels, expected keep/reject decisions, source hashes, model revision, GPU architecture and runtime before running. Run baseline and aligned mode separately in the same environment:

```bash
python eval_boundaries.py <probe-folder> --run-dir experiments/probe-baseline --revision <commit-sha>
python eval_boundaries.py <probe-folder> --run-dir experiments/probe-aligned --revision <commit-sha> --align-confirmation
python score_full.py <probe-folder> experiments/probe-baseline/eval_results.json
python score_full.py <probe-folder> experiments/probe-aligned/eval_results.json
```

Inspect changed seams and query logs first. Reject a candidate that loses expected true cuts or adds unjustified cuts on the fixed probe. Any promotion still requires better aggregate F1 and exact-document recovery, no fresh-partition precision/recall regression against a freshly run same-environment baseline, and a separate masked `tests2` comparison. Keep runtime and call counts alongside accuracy. A gain only on already-inspected examples is insufficient.

## EVN experiment preparation

The next isolated candidate transcribes title and issuer on proposed starts, then suppresses only the exact EVN “Търговски условия” section heading covered by historical human rule 7. Missing evidence keeps the split. It is separate from `split.py` and production remains unchanged. The source-hashed 12-page probe has two expected suppressions, nine keep controls, and one observation. A passed extraction probe is not an accuracy result.

`run_evn_experiment.py` checkpoints every successful page, rejects incompatible code/runtime/source/model caches, reuses recorded baseline rotations for paired evaluation, and requires complete baseline-cut coverage. Reports include strict boundary and exact-document scores, every changed cut, and successful processing time. They exclude loading and failed attempts from time, so are not pod billing estimates. The runner never marks a candidate ready for promotion.

The current CPU suite passes **73 unit tests plus 17 nomenclature tests (90 total)**. The 28 EVN tests cover conservative parsing/matching, checkpoint corruption and crash/resume, pinned model identity, source mutation, rotation reuse, frozen probe failure gates, full paired coverage, first-page preservation, and measured regression when a true start is removed. All four real probe source hashes and page counts were validated. There is still no new CUDA result. See [the GPU runbook](EVN_EXPERIMENT.md) for the frozen revision, package and validation gates.

## Qwen3.8 adaptation

The experimental Qwen3.8 backend uses a local SGLang server with a pinned NVFP4 checkpoint, BF16 vision/output heads, FP32 GDN state and a container image pinned by digest. The client transports original rendered page images in order and reuses the detector's prompts and boundary routing. The current HF Qwen2.5 loader remains the default.

Shared model options expose thinking off/low/medium/xhigh and a completion cap covering reasoning plus final answer. The client requests independent contexts, uses a fixed seed, checks the advertised model ID, separates reasoning from the final answer, and rejects incomplete/empty/malformed responses. Qwen3.8 query fields are validated before the detector's legacy conversions; string booleans and missing fields fail the source. These parser and sampling choices are recorded comparison settings, not an assertion that changing only weights explains every difference.

Per-source evaluation checkpoints include available call/token usage. Failed attempts retain usage separately; unknown usage stays unknown. Source/code/runtime/thinking changes invalidate caches. A two-window smoke runner validates ordinary and large page images without consulting labels. The transfer package contains the fixed 20-source benchmark and five reviewed Gergana sources, with dereferenced PDFs and verified hashes. See [QWEN38.md](QWEN38.md) for supported commands and the remaining GPU checks.

Local verification passes **106 unit tests plus 17 nomenclature tests (123 total)**. The 33 added tests exercise real loopback HTTP requests, image order, completion failures, reasoning separation, strict field validation, deployment options, full detector/evaluator integration, rotation, token accounting, cache resume, smoke selection and package integrity. All 11 existing prompt constructions match `HEAD` exactly at the Python AST level. Neither these checks nor the packaged sources establish GPU performance or accuracy.

## Remaining limits

The completion manifest proves successful publication and byte/page consistency, not semantic correctness. Flat outputs are visible during publication; consumers must validate the manifest. Abrupt process death can leave staging directories, and history is retained rather than automatically deleted. Persistent storage is still required.

Model-generated confidence is not calibrated. The parser's historical defaults for malformed JSON remain unchanged (three such warnings occur in the measured full log); correcting structured-output handling is a separate accuracy experiment. Per-source evaluation checkpoints lose the unfinished source's inference work on a crash, not the already completed PDFs. Source and code fingerprints do not fully capture system binaries or GPU nondeterminism; compare on one fixed environment.

The larger accuracy opportunities remain distinguishing genuine starts inside visually similar drawing/table runs, and document closure at signature/section transitions. These need specific labelled examples and clear filing rules. The historical 92.52% human-reviewed figure remains an alternative-label estimate, not an achieved model score.
