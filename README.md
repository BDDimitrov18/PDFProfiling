# PDF document splitting

**Best validated variant: V15**, labeled by the Git tag **`best-v15`** and
[BEST_VARIANT.json](BEST_VARIANT.json). The exact saved runtime, commands and
validation results are in [releases/v15](releases/v15/README.md).
V15 recovered **1,221/1,377 exact documents on the original 94 PDFs** and
**708/845 on the additional 82 PDFs**, improving on V14 by five and three
documents respectively. The newer set's boundary F1 is **93.21%**; it is a
different metric from exact-document recovery. These are development/regression
results, not a sealed holdout estimate.

Use the explicit V15 command below; compatibility defaults still select the
legacy backend:

```bash
python run_production.py /path/to/input --backend qwen38 --thinking off \
  --boundary-method archive-context --request-timeout 600
```

The sections below retain the setup and historical evaluation context.

Splits scanned Bulgarian construction archives into document PDFs using Qwen2.5-VL-32B-Instruct, CUDA and 4-bit NF4. The production driver detects document boundaries only. Classification is a separate path in `split.py`.

The Qwen2.5 reference is commit `9fee964`: **89.10% strict boundary F1 and 252/335 exact documents** on GT v3, 20 PDFs / 733 pages. Qwen3.8 thinking off with the original detector measured **88.69% F1 and 264/335 exact documents**. See [the improvement record](docs/IMPROVEMENTS.md) and [the project review](docs/PROJECT_REVIEW.md).

Qwen3.8-27B is available through a pinned local-server backend. The new thinking-off `archive-context` pipeline combines explicit image order, typed evidence and narrowly scoped filing rules. Its historical stage replay reaches **97.32% strict F1 and 314/335 exact documents**. On the separately selected final 50-page check, both `archive-context` and the faster `archive-fast` method measured **97.96% F1 and 25/26 exact documents**, versus 92.00% and 24/26 for the original detector. The full fast run scored 96.42% F1 and 311/335 exact documents and failed the accuracy gate. A final receipt-heading reconciliation improves its recorded outputs to 96.57%, 312/335; `archive-context` remains recommended. Production defaults remain compatible with Qwen2.5. See [the results and their scope](docs/QWEN38_RESULTS.md), [the experiment log](docs/QWEN38_IMPROVEMENT_LOG.md), and [the Qwen3.8 runbook](docs/QWEN38.md).

## Installation

Inference needs a Linux CUDA machine. Previous measured runs used an RTX 5090; use the same GPU architecture and software stack for comparisons. The model uses roughly 18 GB VRAM with the existing quantization configuration and downloads about 64 GB of weights. Allow at least 80 GB for the model cache, plus corpus, outputs, staging and retained history. Store these on persistent storage.

On the GPU machine, inside a dedicated environment:

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-osd
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export HF_HOME=/workspace/hf_cache
export HF_HUB_DISABLE_XET=1
```

`requirements-lock.txt` preserves the recorded June package versions. `requirements.txt` adds the CUDA package index and explicitly pins Pillow, the Tesseract Python wrapper and the matching torchvision release, which were missing from that record. This does not recreate an unrecorded historical environment exactly. Record a new baseline before comparing model changes. Python, package versions, code hashes, source hashes, and requested model revision are recorded by the drivers; the evaluator also records the resolved model commit and GPU/CUDA details.

## Production

```bash
python run_production.py /workspace/GIS_Pv
# Retry failures; the exit status determines success.
bash supervisor.sh /workspace/GIS_Pv >> /workspace/prod.log 2>&1
```

With the pinned Qwen3.8 server running, the optional archive method uses
thinking off, positional image labels, greedy decoding and typed evidence checks:

```bash
python run_production.py /workspace/GIS_Pv --backend qwen38 --thinking off --boundary-method archive-context --request-timeout 600
```

This method checkpoints each seam. Restarting reuses validated completed seams,
including their rotations and usage records. Changed source bytes or settings use
a separate cache namespace. `archive-fast` removes the general second pass; its
complete validation results and measured tradeoffs are in the results report.

Originals can be flat or nested. Generated `split/` and hidden directories are excluded. Outputs retain the existing names: `<source>_NNN_00000_.pdf`. Exported pages retain their original orientation; rotation correction is for inference images.

Each source has a completion record under its `split/.state/` directory. It contains contiguous source page ranges, confidence, `needs_review`, inference rotations, source/output hashes, and run settings. A low-confidence flag is a review aid, not a calibrated probability of error.

Resume checks the entire output set, hashes and page counts. Partial, missing, corrupt, legacy outputs without a completion record, or outputs from different settings/code are reprocessed. Completed originals are skipped before loading the model. Replaced files are retained under `split/.history/`; allow space for these copies. A failed staging write leaves the old set intact. A failure during publication leaves the source incomplete and forces repair on retry. A flat output directory is not an atomic multi-file transaction: consumers should use validated completion records.

Exit codes: `0` all selected originals complete, `1` failures, `2` invalid input. The supervisor retries ordinary failures and stops on invalid input or signal-style exit codes. `PRODUCTION_ATTEMPTS`, `PRODUCTION_RETRY_SECONDS`, and `PRODUCTION_PYTHON` override its defaults.

For multiple workers, give each an exact shard list, one root-relative or absolute PDF path per line:

```bash
python run_production.py /workspace/GIS_Pv --files /workspace/shard-1.txt
```

Overlapping workers are protected by per-source OS locks. Unknown shard entries fail validation. Use `--revision <commit-sha>` to pin model and processor weights in either driver.

## Evaluation

With the pinned Qwen3.8 server running and advertising `qwen3.8-27b-009632fe-compact-v3`, evaluate methods in separate result directories:

```bash
python eval_boundaries.py eval_full --backend qwen38 --thinking off --boundary-method archive-context --request-timeout 600 --run-dir experiments/qwen38-archive-context
python eval_boundaries.py eval_full --backend qwen38 --thinking off --boundary-method archive-fast --request-timeout 600 --run-dir experiments/qwen38-archive-fast
python eval_boundaries.py eval_full --backend qwen38 --thinking off --boundary-method legacy --request-timeout 600 --run-dir experiments/qwen38-original-off
```

The older `scripts/run_qwen38_pilot.py` reproduces the original OFF/medium comparison and checks both smoke modes. Medium was stopped for this investigation; it is not required for the new OFF methods. Its `--check` validates the original pilot plan without starting inference.

The same model options are supported by `run_production.py` and `split.py`. Use evaluation first. The model server has its own pinned CUDA 13 runtime; the lightweight client uses `requirements-qwen38-client.txt`. Changing thinking, completion cap, endpoint or deployment configuration invalidates existing checkpoints. No labels or historical model outputs are sent in inference requests.

Qwen3.8 has one shared recovery budget. A completed answer with invalid JSON/field types gets a format reminder. An OFF answer ending at the token limit gets one retry with bounded string fields (160 characters for headings, 256 for other strings) and whole-percent confidence. The completion cap stays unchanged. There are at most two calls total; transport failures and medium truncations propagate. Both attempts and all tokens are counted, and the recovery policy is part of checkpoint identity. See the runbook for details.

The isolated EVN section rule remains a separate follow-up experiment after the model comparison. Its frozen 12-page extraction probe, GPU package and comparison gates are documented in [EVN_EXPERIMENT.md](docs/EVN_EXPERIMENT.md). It is not enabled in production.

The large source corpora are local and excluded from Git. Builders link originals and preserve reviewed corrections in `data/boundary_corrections.json`, tied to source hashes.

```bash
python build_eval_set.py                 # dev + holdout; rotation truth includes upright files
python build_full_eval.py                # fixed historical 20-source GT v3 benchmark
python build_full_eval.py --include-all  # separate eval_expanded: 21 sources / 798 pages
python build_full_eval.py --corpus tests2 --include-all
```

The five-source Gergana review is now available separately: 84 pages / 35 human-confirmed documents. Rebuild it with `python build_review_eval.py --corpus /path/to/Gergana-2.07.2026`; it uses `data/gergana_review_v1.json` and writes `eval_gergana/`. See [the Gergana validation record](docs/GERGANA_VALIDATION.md). Unreviewed `obraboteni` outputs are not labels.

`tests2` currently provides 51 labelled sources / 1,496 pages. One 11-page source has no reference splits and is recorded as unlabelled in `dataset.json`. Six sources have unresolved reference gaps; their masks exclude those seams from scoring. Neither the historical “fresh” stratum nor `tests2` should be described as a pristine unseen test set.

```bash
python eval_boundaries.py eval_full --run-dir experiments/baseline --revision <commit-sha>
python score_full.py eval_full experiments/baseline/eval_results.json --json experiments/baseline/score.json
```

Repeat the evaluation command to resume completed PDFs. Checkpoints are written after each source. Changing source bytes, code or settings requires a new run directory. A model/GPU change during a partial run is rejected. Updated labels can rescore the same cached predictions without a GPU. Custom run directories keep logs and results separate; without `--run-dir`, checkpoints go under the dataset's `eval_run/` and the legacy `eval_results.json` location is also updated.

The scorer accepts saved logs and JSON results, requires exact file coverage, and uses current labels instead of trusting historical summary scores. It reports strict boundary precision/recall/F1, exact-document recovery, and errors by stratum. Documents touching masked seams are excluded from exact-document scoring. Tolerance-1 scores from the evaluator are diagnostic and unmasked; use strict masked scores for acceptance.

To reproduce the recorded reference without inference:

```bash
python score_full.py eval_full logs/fulltests_stage2.log
python audit_confirmation.py logs/fulltests_stage2.log
```

`--align-confirmation` is an experimental option on both inference drivers. It confirms the proposed seam after relocation. It is off by default and has no demonstrated accuracy gain; see the audit and acceptance criteria in the improvement record.

## Local checks

These checks need no model or GPU. In a local virtual environment, install `pypdf`, `pdf2image`, `Pillow`, `pytesseract` and `xlrd` if absent, then run:

```bash
python -m unittest discover -s unit_tests -v
python -m unittest test_nomenclature_match -v
bash -n supervisor.sh
```

Use the explicit test directory: several historical root-level `test_*.py` files are GPU/corpus evaluation programs, not unit tests.
