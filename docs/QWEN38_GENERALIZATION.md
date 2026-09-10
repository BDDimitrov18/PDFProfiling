# What the accuracy results establish

The current scores establish fit to the repository references. They do not yet
establish expected accuracy on arbitrary production documents.

The model weights have not been fine-tuned in these iterations, but prompts,
selectors and policies have been adjusted repeatedly after inspecting benchmark
errors. This is development against labels and can overfit. Avoiding filename
exceptions and fixed page numbers is necessary, but does not remove that risk.

## Different kinds of change

Correct image-role assignment, bounded answer recovery, source-bound checkpoints,
complete token accounting and faithful PDF export address implementation problems.
Their intended behavior is independent of a particular reference split.

Rules about covers, certificates, legal attachments, materials schedules,
calculation sections and document identities are domain assumptions. These use
visible facts and include counterexamples, but many were motivated by errors on
the current benchmark. A narrow rule may behave well on its observed controls and
still fail on another archive or on a different labeling convention.

The model's reported confidence is not a calibrated probability of correctness.
A numerical confidence guard does not constitute an independent accuracy estimate.

## Current evaluation scope

- The historical 20 sources, five Gergana sources, five pilot sources and two
  former-final sources are now development/regression-exposed: 32 PDFs, 1,090 pages.
- The V13b runtime was frozen before its evaluation on the 44 additional labeled
  `tests2` sources: 1,223 pages, selected by excluding the 32 known source hashes.
  No source was selected according to its error count.
- Those 44 sources share permit groups and document styles with development data.
  Different source hashes do not establish page-content independence. A local
  raster-overlap audit is recorded separately under the expanded validation folder.
- Existing reference labels and gap masks remain unchanged. Historical/tests2
  references derive from repository PDFsam files and documented corrections;
  Gergana uses the existing user page-start lists. Unreviewed `obraboteni` outputs
  are not used as independent ground truth.

The first frozen V13b result on the additional collection must be retained as its
first-pass broader validation result. If its errors are used to create another
candidate, that collection becomes development data for the new candidate. A later
improved score must not replace or be presented as the untouched first result.

## Evidence needed for a production accuracy claim

Use a representative batch from new projects or time periods, labeled by the actual
label owner before model evaluation. Include difficult scans and ordinary files,
not only interesting failures. Keep entire related projects together when
partitioning development and evaluation data, and check duplicated pages/templates.
Freeze the candidate before exposing its held-out predictions or error analysis.
Report strict boundary precision/recall, exact recovered documents, whole-source
success, exclusions and failures. Measure speed on that same complete run.

If further tuning uses those errors, another untouched batch is required to assess
the tuned candidate independently. Until this evidence exists, saved releases can
be described as the best validated benchmark version, without promising the same
percentage on new production archives.

## Page-overlap audit, 2026-09-06

A local 72-DPI grayscale raster audit covered all 2,313 pages across the 76 source
PDFs. None of the 1,223 additional pages had an exact raster hash match among the
1,090 development/regression pages. All 44 additional source-file hashes are also
distinct. This rules out exact matches at the audited raster representation, but
not rescans, shared templates or semantic overlap. The common permit-group/style
limitation remains. Perceptual similarity candidates were recorded separately;
they are not treated as confirmed duplicate content or proof of independence.

Evidence: `experiments/qwen38_improvement_20260906/expanded_validation/page_overlap_audit.json`
and `near_page_overlap.json`.
