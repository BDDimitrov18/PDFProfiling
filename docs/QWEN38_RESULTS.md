# Qwen3.8 improvement results — 6 September 2026

The final recommended `archive-context` release has now completed a fresh run on
all 20 historical ground-truth PDFs (733 pages): **97.32% strict boundary F1,
314/335 exact documents**, with 11 extra cuts and 6 missed cuts. It took
5,606.28 seconds (93m26s), or **7.65 seconds/page** including evaluator overhead.
All 1,225 model requests succeeded, with zero process restarts. Runtime and
reference hashes stayed unchanged. This confirms the prior stage-replay score.
The historical set remains development-exposed.

The complete run is saved under
`experiments/qwen38_improvement_20260906/historical_integrated_final_context`.
The separately preserved release is under
`experiments/releases/qwen38-archive-context-v11-receipts-20260906`;
its original package remains unchanged, with the fresh benchmark result alongside it.

The model swap alone did not improve strict boundary F1. The improvement comes from
explicit image order, typed page evidence, narrower filing rules and resumable
inference. Qwen3.8 thinking remains off. The original Qwen2.5 defaults remain
available; the new methods are explicit options.

The completed integrated comparison used the frozen snapshot recorded in
`experiments/qwen38_improvement_20260906/final_snapshot.json`. The tables below
identify which results are complete stage replays and which are cold integrated
runs. Reference labels have not been edited to improve a score.

## Historical reference: 20 PDFs, 733 pages

| Method | Strict boundary F1 | Extra cuts | Missed cuts | Exact documents |
|---|---:|---:|---:|---:|
| Original Qwen2.5 | 89.10% | 41 | 29 | 252/335 |
| Original Qwen3.8 OFF | 88.69% | 49 | 25 | 264/335 |
| Conservative archive-context, V11 stage replay | 97.32% | 11 | 6 | 314/335 |
| Final archive-context release, fresh integrated run | 97.32% | 11 | 6 | 314/335 |
| archive-fast V11, fresh integrated run | 96.42% | 18 | 5 | 311/335 |
| archive-fast plus final receipt reconciliation, recorded-run replay | 96.57% | 17 | 5 | 312/335 |

The historical set is development-exposed. The V11 stage-replay row uses validated
model stages and deterministic guards; the final-release row is a separate fresh
integrated run of every historical source. Full replay source arrays, changes and current-label hashes are in
`features_v11_scores.json` under the improvement experiment directory.

The full fast run finished in 58m20s (4.78 seconds/page), with 805 requests,
including one failed completion recovered within the same process. It missed
one fewer boundary than conservative, but made seven more extra cuts and
recovered three fewer exact documents. It failed the predeclared accuracy gate;
the frozen controller selected `archive-context` for its production smoke check.
The final receipt reconciliation repairs one OCR-driven extra cut, without
changing any model prompt, query selection or context anchor. It is applied only
after every model stage. Its 96.57% replay also fails the gate; `archive-context`
remains recommended. The conservative predictions are unchanged by this rule.

## Gergana review: 5 PDFs, 84 pages

| Method | Strict boundary F1 | Extra cuts | Missed cuts | Exact documents |
|---|---:|---:|---:|---:|
| Original Qwen3.8 OFF | 88.52% | 4 | 3 | 26/35 |
| Conservative V11 stage replay | 95.08% | 2 | 1 | 31/35 |
| Conservative V11, fresh integrated run | 95.08% | 2 | 1 | 31/35 |
| archive-fast, fresh integrated run | 95.08% | 2 | 1 | 31/35 |

The conservative run took 655.15 seconds and 143 calls; fast took 442.74 seconds
and 107 calls, a 32.4% time reduction. Neither had a failed request.

Gergana now contributes development evidence. Its labels remain review v1. Two
apparent label issues are pending human clarification, and one cover/body filing
choice differs from the implemented convention. See [the label questions](QWEN38_LABEL_QUESTIONS.md).

## Separate 223-page pilot

The original detector and frozen V9 ran on the same server, sequentially, before
pilot accuracy was used for later structural refinements. Existing masks exclude
five documents from exact scoring; 62 remain eligible.

| Method | Strict boundary F1 | Extra cuts | Missed cuts | Exact eligible documents |
|---|---:|---:|---:|---:|
| Original OFF, integrated | 88.52% | 10 | 4 | 52/62 |
| V9, integrated before pilot error analysis | 93.55% | 8 | 0 | 59/62 |
| V11 stage replay after pilot development | 98.31% | 2 | 0 | 60/62 |

The last row is not an unseen result. A final 50-page comparison uses the two
remaining unused permit case groups, selected by metadata and fixed seed. These
are older archive references, not newly reviewed human labels. The faster variant
must match the conservative variant's F1 and exact-document counts on both that
check and Gergana before a full historical fast run is allowed.

## Reserved final case check: 2 PDFs, 50 pages

Both implementations were frozen before inspecting accuracy or pages in this
subset. No final-case error was used to change their policies.

| Method, fresh integrated run | Strict boundary F1 | Extra cuts | Missed cuts | Exact documents | Elapsed |
|---|---:|---:|---:|---:|---:|
| Original Qwen3.8 OFF | 92.00% | 3 | 1 | 24/26 | 5m46s |
| Conservative archive-context | 97.96% | 1 | 0 | 25/26 | 5m47s |
| archive-fast | 97.96% | 1 | 0 | 25/26 | 3m40s |

The fast method matched conservative accuracy while taking 36.5% less time:
4.41 versus 6.94 seconds/page. The runs made 50 and 77 calls respectively,
with no failed calls. The original detector made 146 calls. This small case check
does not establish the speed or accuracy of the whole original collection.
The later receipt-reconciliation replay leaves both this check and Gergana
unchanged. That later replay is posthoc, not a new unseen validation result.

## Measured time and reliability

The 223-page original OFF run took 24m20s (6.55 seconds/page). V9 took 29m05s
(7.83 seconds/page), including a rejected completion and checkpoint resume but
excluding manual idle time. V9 made fewer requests but generated more tokens, so
fewer requests did not translate into a speed win on this pilot.

The 34-page V9 production sample took 4m35s (8.10 seconds/page). Its repeat took
1.18 seconds, reusing completed outputs. Every exported page matched the original
rendered pixels at 72 dpi; page order, counts, geometry, rotation and output hashes
also passed verification. This is a small sample, not a whole-corpus time guarantee.

The final packaged runtime was then checked on two complete original PDFs:

| Final-code production check | Pages | Correct documents | First run | Cached repeat | Model calls |
|---|---:|---:|---:|---:|---:|
| Recommended archive-context, Gergana thermal report | 26 | 5/5 | 219.31s | 0.97s | 53 |
| Experimental archive-fast, receipt regression | 48 | 21/21 | 198.18s | 1.33s | 48 |

Both first runs had zero failed model calls. Every one of the 74 exported pages
matched the original rendered pixels at 72 dpi. Source bytes, current-reference
start pages, order, counts, geometry, rotations and output hashes also passed.
The fast regression reproduced the raw p10 mistake, then the final rule removed
that cut. The conservative result did not change. These samples validate output
behavior and resume; they do not override the full historical accuracy gate.

Local outputs: [the recommended-method report](../experiments/qwen38_improvement_20260906/receipt_release_context/input/split/Image_00102112026095941278_004_00000_.pdf)
and [the repaired receipt batch](../experiments/qwen38_improvement_20260906/receipt_release_fast/input/split/Image_00112032025083553577_005_00000_.pdf).
The portable package contains source/reference PDFs, not these local output copies.

For the original Gergana collection (133 originals, 4,100 pages), the measured
conservative range of 6.94–8.44 seconds/page extrapolates to about **8–10 hours**
with the model already loaded on the tested RTX 5090. This is a planning estimate
from smaller runs, not a measured full-collection production time. No new run of
all 133 originals was started during this investigation.

One OFF failure repeatedly emitted escaped non-breaking spaces inside a heading.
External JSON whitespace constraints cannot bound text inside a string. The new
recovery gives an OFF truncation one retry with hard string-length constraints
(160 characters for heading fields, 256 for other strings) and whole-percent
confidence. The unchanged token cap remains 4,096. A live bounded probe returned
valid JSON in 5.21 seconds on the previously looping window. Automatic recovery
and its call/token accounting are tested through the local HTTP integration tests.
The later isolated client replay succeeded on its first request, so it did not
itself exercise the failure branch. During the final integrated historical fast
run, the original looping window did trigger automatic recovery: its first
4,096-token completion truncated, then bounded recovery returned valid JSON in
3.40 seconds and the run continued. Its checkpoint records two calls, one failed,
4,281 output tokens total and the correct invoice-to-cadastral-sketch cut.

Format repair and OFF truncation recovery share a maximum of two calls. Repeated
failure remains an error, never an assumed continuation. Completed source and seam
checkpoints survive interruptions and include source/settings identity and usage.
Greedy decoding and a fixed seed do not guarantee bitwise-identical GPU results.

## Final receipt decision

The retained rule repairs an isolated heading disagreement inside an established
receipt batch. It requires high-confidence receipt readings in both neighbouring
comparisons and similar headings for the same physical pages. It does not create
new batch starts or infer an attachment from a shared project. The complete
55-source-run development audit changed only one false cut. Raw model answers
remain intact, and the correction enters the review record. The local suite passes
148 tests, including no-extra-query and checkpoint-resume checks for this rule.

An additional receipt-to-notice reference matcher was rejected. The two-image
probe misread a copy suffix and date; a close-up variant still read the wrong
suffix with 95% confidence and would have removed a true boundary. Normalizing
apparently matching model-generated IDs was therefore insufficient. Neither that
matcher nor the extra crop is enabled in production.

## Run the new methods

With the pinned server running:

```bash
python eval_boundaries.py eval_full --backend qwen38 --thinking off \
  --boundary-method archive-context --request-timeout 600 \
  --run-dir experiments/my-archive-context-check

python run_production.py /path/to/originals --backend qwen38 --thinking off \
  --boundary-method archive-context --request-timeout 600
```

`archive-fast` uses the refined prompt directly before the same typed checks and
filing policies. Its full integrated run failed the accuracy gate; the perfect
development replay did not predict whole-corpus accuracy. `archive` retains the earlier V9
method for comparisons. `legacy` retains the original routing.

The portable package contains the historical 20 and Gergana 5 sources. The local
`tests2` subsets are separate, with their selection and source hashes retained in
the experiment artifacts. See [the runbook](QWEN38.md) for environment setup and
[the experiment log](QWEN38_IMPROVEMENT_LOG.md) for accepted and rejected variants.

Remaining disagreements concern covers, attachments, report identity and some
standalone sections. A high model confidence is not a calibrated guarantee that
such filing decisions are correct. Exact-document counts should stay alongside
boundary F1 when judging improvements.
