# Label questions found during the Qwen3.8 error audit

Reference labels remain unchanged. These are questions for human review, not
model-generated ground truth. All reported validation scores continue to use the
versioned user-supplied labels in `data/gergana_review_v1.json`.

| Reference | Stored decision | Visible evidence | Question |
|---|---|---|---|
| Gergana Review 01, source 135512148, before page 6 | Keep pages 5–8 together | Page 5 is a complete professional qualification certificate; page 6 opens a technical energy-efficiency verification report | Should page 6 start a document? |
| Gergana Review 02, source 105903855, before page 11 | Split before page 11 | Pages 10–11 contain the same Lev Ins insurance policy; page 11 continues premium/indemnity clauses and closes with signatures | Should page 11 continue page 10? |

A four-page local review copy preserves those original pages, in the table order:
[`output/pdfs/qwen38-label-review.pdf`](../output/pdfs/qwen38-label-review.pdf).
This convenience copy is outside the portable package; its original source PDFs
and page numbers are included there.

The exact pages were rendered and inspected under `tmp/pdfs/qwen38-audit`:
`gergana-cert-5.png`, `gergana-cert-6.png`, `gergana-policy-10.png`,
`gergana-policy-11.png`. The user was asked to clarify both choices while the
unchanged-label benchmarks continued.

On 6 September, the user clarified that they are the developer, not the person
who labeled the ground truth. They tentatively see the certificate and report as
separate, and the insurance pages as one document, but explicitly instructed us
to trust the existing ground truth over those impressions. This is not approval
to change either label. Both reference decisions remain unchanged; any correction
would require a definitive ruling from the label owner.

Two other filing distinctions deserve attention before broader deployment:

- Historical source 164052657 separates the static-calculation title page (17)
  from its first body page (18), while Gergana Review 02 keeps a report title page
  (2) with its body (3). A blanket rule splitting every title-only report cover
  does not reproduce both choices.
- Historical source 164052657 keeps page 25 inside the ongoing structural report,
  despite a prominently printed project identifier ending in 658 rather than 657
  on its earlier cover. This may be a source typo or an intentional filing choice;
  the model's separate-document interpretation is not obviously unreasonable.

Neither uncertainty justifies relabeling examples automatically or inserting
source-specific exceptions into the detector.

## Remaining historical convention questions

These are audit findings, not proposed automatic label edits. The historical
references remain unchanged. Page numbers below are one-based source pages.

| Source suffix | Page(s) | Current discrepancy | Why a general model rule is risky |
|---|---:|---|---|
| `142438096` | 48, 53 | Model separates titled technical assignments that the reference retains as contract appendices. | Other attached plans/registers are separate filing units in these references; “appendix” alone is insufficient. |
| `145428614` | 71, 128, 151 | Cover-to-contents/data cuts disagree with the reference. | Some other project covers are explicitly separate. A universal cover policy needs a consistent decision. |
| `085002901` | 2 | Cover-to-contents cut disagrees with the reference. | Same cover-policy conflict. |
| `164052657` | 25 | Model separates a structural subsection showing a different printed project identifier. | The reference groups it, but distinct identifiers can be real evidence elsewhere. |
| `143041245` | 66 versus 68 | Reference keeps one quantity schedule in the existing document but starts another later schedule. | A generic “titled quantity table starts” recovery would repair one seam and break another. |

Other residual errors, such as apostille/translation chains and graphic-part
separators, also need a declared filing policy and controls before broad merging
or splitting rules are enabled. The fact probes target narrower visible
transitions first. Predicted document boundaries never substitute for human labels.
