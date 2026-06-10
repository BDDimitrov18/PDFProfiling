# Boundary / Rotation Eval Results

Eval set: `eval_dev/` (9 files, ~181 pages, derived from `tests/` only).
Boundary truth from PDFsam split files; rotation truth from `groundTruthHuman` (all 90°).
Model: Qwen2.5-VL-32B-Instruct, greedy decoding (deterministic — one run per config).

## Boundary detection

| Stage | tol=0 P | tol=0 R | tol=0 F1 | tol=1 P | tol=1 R | tol=1 F1 | docs exact | notes |
|-------|---------|---------|----------|---------|---------|----------|------------|-------|
| Baseline | — | — | — | — | — | — | — | pending pod |

## Rotation detection (degrees-exact, OSD arm)

| Stage | TP | FP | FN | wrong-deg | Precision | Recall | notes |
|-------|----|----|----|-----------|-----------|--------|-------|
| Baseline (legacy VLM) | — | — | — | — | — | — | pending pod |
| OSD arm | — | — | — | — | — | — | Gate 1 target P>=90% |

## Stage log

- **Stage 0** — harness built (`eval_boundaries.py`, `eval_rotation.py`, `test_osd_mapping.py`,
  `build_eval_set.py`). All compile clean. Edit targets for Stages 1-2 confirmed verbatim.
  eval_dev/ + eval_holdout/ generated.
