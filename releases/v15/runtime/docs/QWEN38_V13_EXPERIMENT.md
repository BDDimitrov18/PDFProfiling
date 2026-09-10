# Qwen3.8 V13 identity candidate

Status: development replay complete; fresh full evaluation pending. The frozen V11
release remains the confirmed baseline (97.3228% F1, 314/335 exact historical documents).
The active V12 validation and the root V11 runtime have not been edited.

The current candidate is V13b. V13 passed its20-page cold accuracy preflight, but
a subsequent audit found that CPU OCR records erased aggregate model-usage totals.
V13b keeps OCR timing while excluding CPU-only records from model-call accounting;
unknown usage from actual model calls remains unknown. Segmentation logic is unchanged.
The queued V13 controller was replaced before its full run began, with no active
evaluator interrupted. V13b repeats the cold preflight and checks accounting explicitly.

All four sets have been exposed during development. These results measure regression
fit and are not an estimate on a new unseen collection. Reference labels are unchanged.
The user confirmed the repository PDFsam-derived reference is authoritative; Gergana
uses the existing user page-start lists, not unreviewed `obraboteni` outputs.

| Set | V11 exact documents | V13 recorded-fact runtime replay | V13 boundary F1 |
|---|---:|---:|---:|
| Historical, 20 PDFs / 733 pages | 314/335 | 334/335 | 99.8415% |
| Gergana, 5 PDFs / 84 pages | 31/35 | 32/35 | 96.6667% |
| Former final set, 2 PDFs / 50 pages | 25/26 | 25/26 | 97.9592% |
| Pilot, 5 PDFs / 223 pages, with existing masks | 60/62 | 61/62 | 99.1453% |

V11 historical/Gergana/former-final baselines are fresh runs. The V11 pilot baseline
is a documented stage replay. V13 above executes the actual candidate terminal code
on frozen model/OCR answers and V12 recorded-run overlays; it is NOT fresh end-to-end
inference. All32 source stage resumes were verified to preserve decisions and timing
without repeated model queries. The added terminal stage uses172 model calls and2 OCR
pages in this replay, in addition to earlier pipeline stages.

## Changes after V12

- Group a cover with a short contents page immediately followed by a separately
  starting qualification certificate. Preserve contents that continues into contents
  or report text. This uses existing confident stage evidence.
- Start an explicitly titled materials schedule after a technical assignment;
  ordinary work-quantity schedules do not receive this rule.
- Detect a reordered regulatory section after a waste-plan section only when both
  printed page counters agree on the total and the page counter moves backward.
- Recognize the same literal regulated plot despite optional UPI/Roman-label prefixes
  and longer descriptive names. Seasonal temperature tables can remain in the same
  project's HVAC calculations; different explicit identifiers are preserved.
- Read legal principal identities independently per page. A certificate/apostille/POA
  bundle requires explicit attached-POA wording plus matching full principal name,
  birth date and company name. A sparse lower-page crop can recover a wrapped company
  name only when its principal identity corroborates the full page and its complete
  company name matches the POA. Printed conflicting company numbers remain recorded;
  no identifiers are silently corrected.
- For a report cover/body with matching numeric regulated plot, quarter and subproject,
  corroborate a disputed Roman numeral using two Tesseract modes and independent
  model crops. Every required read must agree. Handwritten identifiers that remain
  inconsistent do not trigger a merge.

These nine additional changes across the four sets caused zero observed regressions
in the recorded-fact runtime replay. Seven affect historical boundaries. No policy
uses source filenames, fixed page positions, or ground-truth labels as model inputs.

## Evidence and rejected experiments

The first identity probe completed97 single-page reads. A dataset-path error after78
was fixed using aliases to the existing unchanged extra-set directories; hashes of
all97 page sources were verified and only the remaining19 reads ran on resume.
Its final status usage counts the resumed19 only; complete usage must be summed from
all page records. The main V12 benchmark continued throughout.

Focused legal probes completed15 reads each. The revised prompt corrected a wrapped
company name on one source; four independent crops established the second correction.
The actual company number differs between the certificate and POA, so number-only
matching was rejected. Focused filing extraction completed57 reads. Eight additional
model crops alone still disagreed and were rejected as sufficient evidence. Tesseract
5.3.4 on the pod corroborated the regulated-plot reference in two modes on both report
pages (6.44 seconds total); that evidence also matched the wider model crops.

Broad safety, quantity-table and thermal merges had already harmed control boundaries
and remain rejected. Removing receipt copy suffixes would also merge a true historical
boundary and remains rejected. The remaining historical structural-calculation cut has
a visibly different property identifier (657 versus658); no filename exception or
fuzzy identifier merge has been added. The remaining insurance/credential conventions
and unreadable review-form identifiers keep their existing reference labels.

## Validation and preservation

177 candidate unit tests passed, including transport restoration after failure,
source/settings cache validation, bounded failed-record recovery, exact-identifier
counterexamples, OCR disagreement, and repeatable resumes. A separate runtime replay
exercised all32 sources and verified every selected probe window matches the runtime
selector. Package allowlist validation and the final frozen manifest are recorded
alongside the candidate release.

Fresh validation will process all32 PDFs /1090 pages, plus a small cold preflight,
from empty run directories. Each set must meet or exceed the saved baseline's F1 and
exact-document score; historical exact documents must improve. Runtime and dataset
hashes are checked before and after. Bounded automatic evaluator restarts resume only
the new run's own checkpoints. No automatic pod shutdown is authorized.

V12 elapsed timing overlaps the V13 development probes and is not an isolated speed
measurement. The final V13 full run is queued after V12 validation to obtain its own
uncontended timing. Do not promote this candidate based solely on replay scores.
