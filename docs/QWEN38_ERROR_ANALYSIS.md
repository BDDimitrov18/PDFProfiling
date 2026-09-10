# Qwen3.8 thinking-off error analysis

The model replacement alone did not improve boundary F1. With the original
routing, Qwen3.8 OFF scored 88.69% on the historical 20-source benchmark versus
89.10% for Qwen2.5. The strongest gains came from changing how page evidence is
requested and how archive filing conventions are applied.

This investigation uses the pinned NVFP4 Qwen3.8-27B derivative and the recorded
SGLang deployment, not an unspecified full-precision Qwen model. Thinking remains
off throughout the improvement experiments. Labels are used only in the scorer.

## What the logs and scans showed

The original OFF run made 49 extra cuts and missed 25 boundaries. Compared with
the Qwen2.5 reference, 29 extra cuts were new, 20 were shared, and 21 previous
extra cuts disappeared: a net increase of eight. Of those 49 extra cuts, 22 were
attributed to `titled_id_header`, 13 to `start_only_heading`, seven to a header
reset, five to a signature, one to page numbering and one to project signoff.
These are the detector's recorded trigger categories, not independent proof of
the visual cause. Twenty-five of the 49 had reported 95% confidence, illustrating
why a confidence threshold alone was a poor repair.

| Failure | Observed example | Response tested |
|---|---|---|
| Evidence assigned to the wrong image | A two-image verifier explained a certificate transition with the source roles reversed. | Interleaved positional image labels and greedy decoding. All eight labeled greedy diagnostic trials were consistent; unlabeled conditions each got six of eight correct. |
| Generic “same project” reasoning merges separate records | Family/person/service registers and coordinate outputs disappear into a preceding form or note. | Ask for visible page types, coordinate columns and initial row labels before the relationship verdict; apply narrow typed recovery. |
| A visible heading becomes an unnecessary cut | Structural calculations split at individual load cases, element checks and software plots. | Refine archive-unit conventions; require typed plot evidence of the same structure and no independent drawing title block before merging. |
| A broad merge rule destroys real boundaries | Generic pair/archive prompts removed true starts, including signed duplicate instruments. | Reject broad rules. Two complete instruments remain separate even when text is identical; use narrowly defined series rules. |
| A rule leaks into an adjacent document family | Structural-report grouping also merged distinct thermal outputs. | Preserve the first-pass cut when the proposed merge concerns thermal/energy content. |
| “Fresh output” is mistaken for “new document” | An interior thermal calculation page was split; a later new detail appendix was missed. | Probe an explicit completed-summary → fresh-output condition, including a separate continuation control. |
| A table tail lacks the context needed to identify its kind | Quantity-schedule tail merged into a newly titled tree inventory. | Probe the predicted document's opening page as a fixed context anchor. |
| The reference convention is inconsistent or unclear | Some covers are separate while others stay with contents; two Gergana label choices appear to conflict with the scans. | Keep labels unchanged, document the ambiguity, and request human clarification rather than optimize to apparent mistakes. |
| OCR noise bypasses an otherwise correct filing rule | A receipt heading was read as `ПОСТАВЯНЕ` rather than `ДОСТАВЯНЕ`. | Reconcile only isolated disagreements inside an established batch using neighbouring readings of the same physical pages; preserve raw answers. |
| High-confidence identifiers are misread | A receipt-reference probe read the wrong copy suffix, even with a close-up. | Reject automatic reference-based merging after it removed a true boundary in a control; do not treat matching model-generated IDs as verified identity. |

The image-order diagnostic is small; it supports a concrete fix, not a universal
claim that labels eliminate every visual error. Greedy decoding likewise reduces
sampling variation but does not establish cross-runtime bitwise determinism.

## Why more reasoning tokens were not the answer

The medium run had a generation/runtime failure: after finite reasoning it emitted
an extremely long whitespace-heavy JSON continuation. Raising the completion cap
from 8K to 16K did not fix that behavior. Compact constrained JSON resolved the
reproduced failure, but the user then stopped the medium experiment. Its interrupted
results are not a completed model-quality comparison and must not be mixed with
thinking-off benchmark scores.

The OFF errors inspected here are mainly incorrect visual facts, overly broad
filing assumptions and insufficient context. A longer reasoning budget would not
by itself establish the correct filing convention or repair a wrong page reading.

## Changes retained

The optional `archive-context` path combines labeled adjacent images, typed facts, selective
filing refinement, scoped recovery and receipt/plot rules. It preserves original
PDF pages when exporting. Each request has an identity-bound checkpoint, and raw
answers, rotations, usage, disagreements and review candidates remain inspectable.
The legacy path and Qwen2.5 defaults remain available for comparison.

The earlier V9 scored 96.69% historical F1 and 91.80% on Gergana, with a thermal
regression. V11's thermal, document-opening context and guarded structural checks
improve the historical stage replay to 97.32%, 314/335 exact documents, with 11
extra and six missed cuts. Its fresh integrated Gergana run reaches 95.08%,
31/35 exact. These sets are development-exposed and their labels remain unchanged.
The reserved 50-page check reaches 97.96%, 25/26 exact, for both conservative and
fast V11, versus 92.00%, 24/26 for the original detector. See
[the current results](QWEN38_RESULTS.md) for timings, validation scope and the
fast-method selection, and [the experiment log](QWEN38_IMPROVEMENT_LOG.md) for
accepted and rejected variants.

The observed OFF generation loop was escaped non-breaking spaces inside a heading.
An OFF truncation now receives one recovery attempt with hard string-length
constraints; simply raising the completion limit would allow the loop to run
longer. Both requests are counted, and repeated failure remains explicit.

## What not to infer from these results

A boundary F1 is not the percentage of complete files that are perfect. V11 replay has
13/20 entirely correct historical sources. Exact-document recovery is stricter
than counting boundaries and should remain alongside F1. The nine-source perfect
development result is not a whole-corpus accuracy estimate.

The Gergana reference is the user's reviewed start-page list, not the automatic
`obraboteni` outputs. Pending corrections remain documented separately in
[the label questions](QWEN38_LABEL_QUESTIONS.md). The `tests2` pilot uses existing
archive references and preserved masks, rather than newly reviewed ground truth.

New filing policies require consistent examples and independent checks. Do not
introduce source-name exceptions, use ground-truth starts as context anchors,
or call a development-tuned result an unseen validation score.
