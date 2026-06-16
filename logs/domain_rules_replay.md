# Domain-rule REPLAY sanity check (POD-LESS) — plumbing + direction ONLY

> ⚠ **VERDICT IS NARROW: this is a PLUMBING + DIRECTION check, NOT a rule-correctness check.**
> Closure markers (rules 1/2/4) are **GENERIC STAND-INS** — `signature_block`/`project_signoff` signals from the SAME log the rules were written against, standing in for the real markers (Проектант/Съставил, notary signature, длъжностно лице). **A green replay does NOT validate the closure rules; only real per-page marker extraction can.** This checks only that the layer fires on the intended candidates and routes correctly. The run is circular by construction.

**Net direction:** TP-fix firings = **0**, FP-harm firings = **4** (normalize 0, prior 4, abstain 0).

## Per-rule fire summary (TP-fix vs FP-harm)
| Rule | TP-fix | FP-harm | normalize | prior | abstain | flag |
|---|--:|--:|--:|--:|--:|---|
| 1 notarial-closure | 0 | 4 | 0 | 0 | 0 | NET-NEGATIVE |
| 2 naslednici-closure | 0 | 0 | 0 | 0 | 0 | ZERO-LEGIBLE-MARKER NEVER-ACTED |
| 3 normalize-coord | 0 | 0 | 0 | 0 | 0 | NEVER-ACTED |
| 4 obyasnitelna-closure | 0 | 0 | 0 | 0 | 0 | ZERO-LEGIBLE-MARKER NEVER-ACTED |
| 5 RS-2page-softprior | 0 | 0 | 0 | 4 | 0 | — |
| 6 merge-izvestie | 0 | 0 | 0 | 0 | 0 | NEVER-ACTED |
| 7 EVN-trade-terms | 0 | 0 | 0 | 0 | 0 | NEVER-ACTED |
| 8 invest-sadarzhanie | 0 | 0 | 0 | 0 | 0 | NEVER-ACTED |

## Rules with NO legible REAL marker in the approximate channel (value UNKNOWN until extraction)
- Closure rules **1/2/4** fired (if at all) only via the **generic signature/signoff stand-in**, NOT the real Проектант/Съставил/notary/длъжностно лице strings → their real value is UNKNOWN here.
  - 2 naslednici-closure: stand-in firings=0, abstains=0 → NO firing at all (zero legible)
  - 4 obyasnitelna-closure: stand-in firings=0, abstains=0 → NO firing at all (zero legible)
  - 1 notarial-closure: stand-in firings=4, abstains=0 → fired on stand-in marker ONLY
  - 7 EVN-trade-terms: no page titled 'Търговски условия' + issuer=EVN found in the log → ZERO legible input (the EVN issuer channel does not exist in the log).

## Full per-rule × per-file firings (every firing, labelled)
| Rule | File | Stratum | Page | Action | Class |
|---|---|---|--:|---|---|
| 1 notarial-closure | 142044854 | dev | 38 | suppress | FP-harm |
| 1 notarial-closure | 142044854 | dev | 39 | suppress | FP-harm |
| 1 notarial-closure | 083553577 | fresh | 20 | suppress | FP-harm |
| 1 notarial-closure | 083553577 | fresh | 21 | suppress | FP-harm |
| 5 RS-2page-softprior | 142438096 | fresh | 15 | prior | no-op(conf) |
| 5 RS-2page-softprior | 143041245 | fresh | 5 | prior | no-op(conf) |
| 5 RS-2page-softprior | 143041245 | fresh | 25 | prior | no-op(conf) |
| 5 RS-2page-softprior | 083553577 | fresh | 25 | prior | no-op(conf) |

## Reading (what this does and does NOT show)
- **Plumbing CONFIRMED:** orchestrator runs on all 20 files, audit trail + per-rule×per-file classification work; rules **1** and **5** demonstrably fire and route.
- **Rule 1's FP-harm firings are STAND-IN ARTIFACTS, not a rule defect.** With the GENERIC signature/signoff marker, the Нотариален акт 'closure' lands on the wrong (far) page, so the rule over-suppresses the adjacent REAL doc-starts (142044854 p38/39, 083553577 p20/21). The REAL notary-signature marker would close the act at its own signature and never touch those. ⇒ this is NOT validation AND NOT condemnation — it is exactly the marker-extraction gap.
- **Rules 2,3,4,6,7,8 were NEVER EXERCISED.** The committed log's title channel only tags `titled_id_header` (TITLE-GATE) pages, so the candidates these rules target (Обяснителна записка via signoff, Известие, coord-register drawings, EVN Търговски условия, invest→съдържание) were not title-tagged; the EVN issuer channel does not exist in the log. Their value is UNKNOWN.
- **BOTTOM LINE:** the replay validates the LAYER's plumbing/routing but validates **NO rule's correctness.** Every rule here is never-exercised, stand-in-only, or a no-op. Do NOT infer rule quality from this run → next step is real per-page **title + closure-marker + issuer extraction**, then pre-registered probe expectations, then pod.
