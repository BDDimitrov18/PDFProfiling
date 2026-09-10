# Gergana corpus intake — 2026-09-05

Source supplied by the user: `/Users/bozhidardimitrov/Documents/Razdelqne/Gergana-2.07.2026`.

At intake, the user confirmed that the `obraboteni*` PDFs were automatic outputs, not yet reviewed. The user has since supplied exact document start pages for the selected five-source review batch and confirmed Review 01 as correct. Only those five sources now have human-confirmed labels; the remaining corpus is unreviewed. No model inference had been run at intake. Later Qwen3.8 evaluations and open label questions are recorded in [the improvement log](QWEN38_IMPROVEMENT_LOG.md) and [the label audit](QWEN38_LABEL_QUESTIONS.md).

## Inventory and checks

- 133 original PDFs / 4,100 pages: 102 files named as scans (4,011 pages), and 31 digital/other attachment candidates (89 pages). This classification uses filenames and location, not visual content.
- 1,277 automatic split PDFs associated with 127 originals. Every associated set has consecutive output sequence numbers and the same total page count as its source. This does not prove correct document boundaries or, by itself, page identity/order.
- Six originals have no automatic outputs (listed below).
- No repeated original basename or SHA256 within the corpus. No basename or SHA256 overlap with the inspected originals in local `tests`, `tests2`, and `data`. Byte comparisons do not detect rescans/recompression and cannot establish whether the files were used elsewhere.
- The source folder was read only. Unrelated images, CAD, Office, archive and metadata files were not imported as PDF references.

## First human review batch

[Open the review instructions](/Users/bozhidardimitrov/Documents/PdfCategorization/review_batches/gergana_2026_07_02/START_HERE.md).

Five originals / 84 pages from five different numeric permit groups were selected using a fixed hash seed, one per source-length band: 6–10, 11–15, 16–20, 21–25 and 26–35 pages. Selection used metadata and complete output availability, not document contents, labels or suspected model errors. It covers manageable sources for initial review; it does not represent the corpus's longest sources or its digital attachments.

| Review | Source relative to supplied folder | Pages | Automatic segments |
|---|---|---:|---:|
| 01 | `РС-75-1-2021/9/Image_00102102026135512148.pdf` | 8 | 5 |
| 02 | `РС-70-1-2021/6/Image_00102102026105903855.pdf` | 11 | 5 |
| 03 | `РС-83-2021/4/Image_00102112026090126620.pdf` | 16 | 10 |
| 04 | `РС-79-2021/5/Image_00102102026145806506.pdf` | 23 | 12 |
| 05 | `РС-84-1-2021/3/Image_00102112026095941278.pdf` | 26 | 5 |

At intake, five original copies and 37 automatic split copies were verified by SHA256 and page fingerprints. After the user review, `corrected/` contains **35 reference PDFs**, preserving all 84 source pages. The 27 prior split copies for Reviews 02–04 were archived under `.history/` before 25 corrected documents were published; Reviews 01 and 05 remained as confirmed. Poppler rendering of every reference page matches the corresponding original page exactly at 900px scale. A representative original/reference image pair was visually checked for artifact fidelity; page content was not used to devise a prompt rule.

The batch manifest now stores `review_status: human_confirmed`, the supplied start pages, current reference-file hashes, and locations of the preserved automatic copies. `data/gergana_review_v1.json` records the original user message, the exact mapping to review IDs, source SHA256 values, and the frozen reference starts. Keep this set separate from prompt tuning and retain case-group membership for later validation.

Detailed local artifacts are `batch.json`, `corpus_inventory.json`, and `overlap_audit.json` beside the review instructions. The batch is Git-ignored. The historical evaluation datasets were not changed. The new `eval_gergana` dataset was built from the explicit reviewed-label record, with source hashes verified before publication. No GPU was needed.

## Confirmed review labels and existing-output score

| Review | Source pages | Confirmed starts | Documents | Extra automatic starts | Missed automatic starts |
|---|---:|---|---:|---|---|
| 01 | 8 | 1, 2, 3, 4, 5 | 5 | none | none |
| 02 | 11 | 1, 2, 8, 9, 10, 11 | 6 | [7] | [9, 11] |
| 03 | 16 | 1, 2, 3, 5, 8, 9, 10, 11, 15 | 9 | [14] | none |
| 04 | 23 | 1, 2, 3, 4, 6, 11, 15, 16, 17, 22 | 10 | [13, 14] | none |
| 05 | 26 | 1, 2, 3, 4, 25 | 5 | none | none |

Existing supplied outputs: **TP 28 / FP 4 / FN 2**, precision **87.50%**, recall **93.33%**, strict boundary **F1 90.32%**. Exact document recovery: **28/35 (80.00%)**; fully correct originals: **2/5**. Required starts at page 1 are excluded from boundary counts. These metrics were independently checked using sets of cut pages and document intervals.

The output-generating model/code/runtime is unknown. This result is a reference score for the supplied files, not a verified current-code GPU baseline and not evidence of an accuracy improvement over a different dataset. These five short-to-medium sources do not establish performance on all 4,100 pages. Full machine-readable results are in [gergana_existing_outputs_score.json](gergana_existing_outputs_score.json).

Rebuild and rescore locally:

```bash
python build_review_eval.py --corpus /Users/bozhidardimitrov/Documents/Razdelqne/Gergana-2.07.2026
python score_full.py eval_gergana eval_gergana/existing_automatic_predictions.json
```

The builder accepts only a nonempty, explicitly human-confirmed versioned label record with review evidence, valid page starts, matching source hashes and page counts. Six import tests pass; with the previously passing CPU suite, `unit_tests` now contains 45 tests. The source PDFs are linked, not modified. `eval_gergana` is Git-ignored; the versioned human labels are retained under `data/`.

## Originals without automatic splits

- `2017/РС-141-1-2017/1/Image_00112102025135819775.pdf` (5 pages)
- `2017/РС-141-1-2017/2/Image_00112102025141108633.pdf` (60 pages)
- `2017/РС-141-1-2017/3/Image_00112102025143300812.pdf` (87 pages)
- `2017/РС-142-2-2017/1/Image_00112112025084119377.pdf` (50 pages)
- `2017/РС-142-2-2017/2/Image_00112112025084822057.pdf` (110 pages)
- `2017/РС-142-2-2017/3/Image_00112112025085139823.pdf` (21 pages)
