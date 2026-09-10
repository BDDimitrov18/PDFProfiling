# NewTests reference provenance and scoring

On 2026-09-06 the user explicitly designated the split PDFs in each `newTests` source folder as ground truth for the original PDF in that folder. This resolves the earlier provenance question for this batch. It does not change the earlier warning about unrelated automatic `obraboteni` outputs.

The batch contains 18 original scans, 802 pages and 374 reference documents across ten permit folders. All originals were absent by SHA256 from the 77 existing/reserved sources checked. No exact 72 DPI grayscale page matches were found against the existing 2,313-page fingerprint set. This does not establish independence from shared templates or rescans.

Each reference page was aligned by content to its original. Most matches used identical raster output or exact PDF content streams, image-resource data/properties and page boxes. Rotation metadata differs on some split pages, so `/Rotate` was ignored when the underlying content and geometry matched exactly. Every original page occurs exactly once across its reference documents. Filenames were used to associate a split with its same-folder source, not to infer page indices.

Two reference documents contain nonadjacent source pages:

- `РС-62-2007/5/Image_00104202026152909552.pdf`: pages 3, 5, 6, 7 form one document; page 4 belongs to another.
- `РС-69-2007/1/Image_00104202026104849968.pdf`: pages 105 and 107 form one document; page 106 belongs to another.

Those labels are preserved. `ground_truth_page_groups.json` is the complete 374-document reference. `ground_truth.json` records changes of document ownership between adjacent source pages, producing 376 contiguous segments. Its interval-exact score must not be presented as recovery of the 374 reference documents. The separate page-group scorer checks exact ordered page membership and once-only source coverage. Even perfect adjacent boundary decisions can recover at most 372 of the 374 reference documents with the current contiguous-output architecture. This is an architectural ceiling established from the references, not a model accuracy result.

Four scorer tests pass, including interrupted-document recovery, correct regrouping, invalid page conservation and internal page order. A self-check across all actual references confirms 372/374 for ideal contiguous outputs and 374/374 for ideal regrouped outputs. Neither self-check uses model predictions.

The V14 runtime was frozen before the user supplied this batch. The first complete production run is queued after the existing V14 validation gates, and a separate scoring controller waits for all 18 outputs. It will report adjacent-boundary precision/recall/F1, exact reference documents out of 374, completely correct source files, measured runtime and model usage. Earlier-stage comparison is a recorded-stage ablation from the same V14 inference, not a separate fresh V11 run. The first full result must be preserved before tuning on these errors.

Evidence is under `experiments/qwen38_improvement_20260906/newtests_unseen`: `reference_provenance.json`, `reference_page_groups.json`, `reference_v1/`, `score_manifest.json` and the scorer tests. The original source-only archive and its historical “unverified” metadata remain unchanged; the later reference manifest and scoring status supersede that label-status field.
