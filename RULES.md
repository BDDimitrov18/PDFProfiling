# Domain Rules — hand-extracted ground-truth splitting rules

Hand-extracted by **human + colleague** by manually splitting **this 20-file dataset**.
Implemented as a **staged, post-processing layer** in `domain_rules.py` (PURE logic, **NOT wired**
into `split.py`'s live path — same staging as the Fix-11 functions). Design + unit tests only
(`test_domain_rules.py`, 16 tests). **No eval until each rule has pre-registered probe expectations.**

## Verbatim rules (preserved exactly)
1. Нотариален акт ends ONLY at the notary's signature.
2. Удостоверение за наследници: starts with that title → lists heirs → ALWAYS ends with a длъжностно лице (official).
3. Titles "изходни точки", "списък с подробни точки", "Координатен регистър" all normalize to type = Координатен регистър.
4. Обяснителна записка ALWAYS ends with "Проектант" or "Съставил".
5. Разрешение за строеж is always 2 pages — but sometimes only 1 page is scanned.
6. Consecutive "Известие за доставяне" merge into one document, categorized as "обратна разписка".
7. EVN documents carry "Търговски условия" as SECTION headings (not boundaries).
8. After a Заглавна страница titled "Инвестиционен проект", a doc titled "съдържание" may follow — DO NOT split between them.

## Rule kinds (implemented distinctly in `domain_rules.py`)
| # | Kind | Function | Mechanism |
|---|---|---|---|
| 1 | **(A) CLOSURE** | `rule1_closure_notarial` | No boundary after a Нотариален акт until `notary_signature` is read; pre-marker candidates suppressed; **abstain** if marker never read. |
| 2 | **(A) CLOSURE** | `rule2_closure_naslednici` | Same engine, marker = `official_signoff` (длъжностно лице). |
| 4 | **(A) CLOSURE** | `rule4_closure_obyasnitelna` | Same engine, marker = `proektant` OR `sastavil`. |
| 3 | **(B) NORMALISE** | `rule3_normalize_types` | Title synonyms → type "Координатен регистър". |
| 6 | **(B) MERGE** | `rule6_merge_izvestie` | Consecutive "Известие за доставяне" → one doc, type "Обратна разписка". |
| 7 | **(B) SECTION** | `rule7_evn_trade_terms` | EVN "Търговски условия" boundary → suppressed (section, not start). |
| 8 | **(B) ADJACENCY** | `rule8_invest_sadarzhanie` | "съдържание" right after Заглавна страница "Инвестиционен проект" → not split. |
| 5 | **SOFT PRIOR** | `rule5_rs_twopage_prior` | РС usually 2 pages → weak conf nudge only. **Never** adds/removes a boundary; **never** forces split/merge on page-count; tolerates a 1-page scan. |

**CLOSURE rules READ a marker string (reliable channel); they do NOT judge content.** If the
marker is missing (dropped scan page) the rule **abstains** — it never manufactures a merge.

**⚠ Structural-expectation logic (rule 5 + any page-count rule) is SOFT PRIOR ONLY.** Rigid
page-count rules MANUFACTURE errors when scans drop pages — so rule 5 only annotates / weakly
nudges confidence and can never force a boundary decision.

## GENERAL vs ISSUER / TYPE-SPECIFIC (over-fit guard when the dataset expands)
| # | Scope | Notes |
|---|---|---|
| 1 | **GENERAL** | Notarial acts close at the notary signature — general Bulgarian convention. |
| 2 | **GENERAL** | Удостоверение за наследници closing with an official — general convention. |
| 3 | **GENERAL** | Title-synonym normalisation; broadly applicable. |
| 4 | **GENERAL** | Обяснителна записка closing with Проектант/Съставил — general design-doc convention. |
| 5 | **TYPE-SPECIFIC (soft)** | РС 2-page span — a structural prior, kept soft precisely because page counts vary by scan. |
| 6 | **GENERAL** | Известие→обратна разписка merge — general postal/delivery-receipt convention. |
| 7 | **ISSUER-SPECIFIC (EVN)** | "Търговски условия" as section is an **EVN** convention; gated on issuer=="EVN". Other issuers untouched. |
| 8 | **GENERAL-ish / DATASET-WATCH** | Инвестиционен-проект→съдържание adjacency is a common filing order, but the exact title pairing may be specific to docs in this set — re-verify when the dataset expands. |

## Nomenclature wiring (`номенклатура_цяла.xls`)
Rule-referenced types that **HAVE** a nomenclature entry (wired in `NOMENCLATURE_CODES`):
| Type | Code |
|---|---|
| Обяснителна записка | 1001 |
| Координатен регистър | 8014 |
| Удостоверение за наследници | 19061 |
| Разрешение за строеж (РС) | 19019 |
| Обратна разписка | 19005 |
| Заглавна страница | 1010 |

Rule-referenced types **ABSENT** from the nomenclature table — **this is the knowledge the rules ADD**
(`RULE_ADDED_TYPES`): **Нотариален акт** (rule 1), **Известие за доставяне** (rule 6, merges into the
listed 19005), **съдържание** (rule 8), **Търговски условия** (rule 7). Also absent: the rule-3
synonyms "изходни точки" / "списък с подробни точки" (they normalise INTO 8014).

## OVERFIT GUARD (record explicitly)
These rules were extracted **from this 20-file test set's own mistakes**, so a rule that "fixes"
a case risks **relabelling that specific case** rather than generalising. Therefore:
- When this layer eventually evals, it gets the **full probe + STRATIFIED full-tests** (dev / holdout / fresh).
- **Any rule that helps dev/probe but not held-out (holdout+fresh) structure is a candidate over-fit
  and is FLAGGED, not kept silently.**
- Issuer/type-specific rules (esp. rule 7 EVN, and rule 8) are the highest over-fit risk on dataset
  expansion — re-verify scope before generalising.

## Status
- `domain_rules.py` + `test_domain_rules.py` (16 tests pass) + this file. **NOT wired into split.py.**
- **Pod stays DOWN.** Next step is to **pre-register per-rule probe expectations** (which exact
  candidate boundaries each rule should flip on the probe files) BEFORE any pod eval.
