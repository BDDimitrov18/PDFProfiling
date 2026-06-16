# Domain-rule scoring over REAL markers (pod-less)

## Stratified F1 — candidate (baseline) vs domain-rules-adjusted (STRICT, tol0, GT v3)
| stratum | base TP/FP/FN | base F1 | rules TP/FP/FN | rules F1 | ΔF1 |
|---|---|--:|---|--:|--:|
| dev | 76/6/7 | 92.12 | 76/4/7 | 93.25 | +1.13 |
| holdout | 11/1/4 | 81.48 | 10/1/5 | 76.92 | -4.56 |
| fresh | 199/34/18 | 88.44 | 195/31/22 | 88.04 | -0.41 |
| AGG | 286/41/29 | 89.10 | 281/36/34 | 88.92 | -0.17 |

## Per-rule firings (TP-fix vs FP-harm vs no-op)
| rule | TP-fix | FP-harm | normalize | prior | abstain | flag |
|---|--:|--:|--:|--:|--:|---|
| R1 | 1 | 0 | 0 | 0 | 0 | — |
| R2 | 0 | 0 | 0 | 0 | 0 | never-acted |
| R3 | 0 | 0 | 0 | 0 | 0 | never-acted |
| R4 | 0 | 4 | 0 | 0 | 0 | NET-NEGATIVE |
| R5 | 0 | 0 | 0 | 4 | 0 | — |
| R6 | 0 | 0 | 0 | 0 | 0 | never-acted |
| R7 | 2 | 0 | 0 | 0 | 0 | — |
| R8 | 2 | 1 | 0 | 0 | 0 | — |

## PRE-REGISTERED expectation checks
- **Rule-1 guard (must stay TP, NOT suppressed):** 142044854 p38=True p39=True; 083553577 p20=True p21=True (all must be True).
- **Rule-4 probe trigger (164505881 p9):** candidate had p9=True; after rules p9 present=False (pre-registered: should be SUPPRESSED → present=False, a TP-fix).
- **Probe firings (expect ~inert except rule-4):** [('R1', '163444215', 31, 'TP-fix'), ('R7', '164505881', 9, 'TP-fix')]

## All firings (rule, file, stratum, page, action, class)
| rule | file | stratum | page | action | class |
|---|---|---|--:|---|---|
| R1 | 163444215 | dev | 31 | suppress | TP-fix |
| R4 | 085002901 | holdout | 8 | suppress | FP-harm |
| R4 | 145428614 | fresh | 138 | suppress | FP-harm |
| R4 | 145428614 | fresh | 139 | suppress | FP-harm |
| R4 | 164959043 | fresh | 8 | suppress | FP-harm |
| R7 | 145428614 | fresh | 66 | suppress | TP-fix |
| R7 | 164505881 | dev | 9 | suppress | TP-fix |
| R8 | 145428614 | fresh | 13 | suppress | FP-harm |
| R8 | 145428614 | fresh | 71 | suppress | TP-fix |
| R8 | 145428614 | fresh | 151 | suppress | TP-fix |
