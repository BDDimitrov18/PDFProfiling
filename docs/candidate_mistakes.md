# Candidate (#2+#4) Full-Tests Mistake Table

Source: `logs/fulltests_stage2.log` (the #2+#4 production candidate), scored under **GT v3**
(`score_full.py eval_full`). Totals: **41 FP + 29 FN across 16 files**. Aggregate STRICT
dev 92.12 / holdout 81.48 / fresh 88.44 (P 85.41) / **agg 89.10**. Reasons are derived from the
log's signal/decision lines.

## Failure-class legend
- **[TABLE-VETO]** — a real table-document start killed by the low-conf "rejected by confirmation pass" rubber-stamp (the Fix 11 target).
- **[SECTION-FP]** — a section heading / running header (e.g. КОЛИЧЕСТВЕНА СМЕТКА = nomenclature 1002) cut as a new document.
- **[WEAK-TITLE]** — `titled_id_header` one-of-two (title XOR identifier) accepted at conf 0.60 on a continuation page.
- **[SIG-OVERCUT]** — `signature_block` / `project_signoff` + "new heading on next page" fired inside one document.
- **[NO-SIGNAL]** — model saw no cue (end=False) and missed a real start (typically scanned table/drawing runs without a header).
- **[LOCALIZE]** — boundary placed ±1 page off (rotation/displacement class; see rotation-aware-localization backlog).
- **[DOUBLE-FIRE]** — a single document transition cut TWICE (boundary smeared onto the previous doc's signoff/last page AND the real start), leaving a spurious extra start adjacent to a true boundary. NOT a page-index/alignment artifact.

## DEV stratum (9 files)
| Filepath | Page | Type | Reason (from log) |
|---|---|---|---|
| tests/РС-32-2017/1/Image_00112022025142044854.pdf | 6 | FP | [WEAK-TITLE] `titled_id_header` p6, identifier-only `изх.№ 2-9400-375(3)`, one-of-two → accepted @0.60; p6 is a continuation letter |
| tests/РС-32-2017/1/Image_00112022025142044854.pdf | 17 | FP | [SIG-OVERCUT] `signature_block` p17 → cut to p18; p18 continues the same doc |
| tests/РС-32-2017/1/Image_00112022025142044854.pdf | 19 | FN | `titled_id_header` claim at p19 relocated onto already-open p18 (dup collision) → claim lost, real p19 start dropped |
| tests/РС-32-2017/1/Image_00112022025142044854.pdf | 20 | FN | [LOCALIZE] `table_end` cut placed at p21 (TP) but the p20 start went unmarked — consecutive starts collapsed |
| tests/РС-31-2017/2/Image_00112022025163444215.pdf | 6 | FP | [SIG-OVERCUT] boundary opened at p6 inside a continuing doc |
| tests/РС-31-2017/2/Image_00112022025163444215.pdf | 31 | FP | [SECTION-FP] mid-dossier section cut as new doc |
| tests/РС-31-2017/4/Image_00112022025164505881.pdf | 9 | FP | [LOCALIZE/SIG] `signature_block` mislocalized cut near p9 |
| tests/РС-31-2017/4/Image_00112022025164505881.pdf | 13 | FP | [SECTION-FP] КОЛИЧЕСТВЕНА СМЕТКА / table section cut as new doc |
| tests/РС-31-2017/4/Image_00112022025164505881.pdf | 12 | FN | [TABLE-VETO] `table_end` boundaries at p8 & p10 "rejected by confirmation pass" → real p12 table-doc start missed |
| tests/РС-31-2017/6/Image_00112022025165204533.pdf | 3 | FN | [NO-SIGNAL] p3 letterhead start seen by START-DETECT but no end-signal on p2 → not cut |
| tests/РС-31-2017/6/Image_00112022025165204533.pdf | 4 | FN | [NO-SIGNAL] p4 start, end=False, no cue |
| tests/РС-31-2017/7/Image_00112032025082511233.pdf | 20 | FN | [TABLE-VETO] `table_end` p19 "rejected by confirmation pass" → real p20 start missed (Fix-11 target case) |
| tests/РС-33-2017/3/Image_00112032025084303475.pdf | 16 | FN | [NO-SIGNAL] real p16 start, no signal fired |

## HOLDOUT stratum (3 files)
| Filepath | Page | Type | Reason |
|---|---|---|---|
| tests/РС-31-2017/8/Image_00112032025082646183.pdf | 4 | FN | [NO-SIGNAL] p4 start in a run of signature pages, not cut |
| tests/РС-33-2017/5/Image_00112032025084837699.pdf | 7 | FP | [DOUBLE-FIRE] p7 is the previous doc's signoff page (closing clauses + инж. А. Харизанова signature/stamp); the real boundary is p8 (ОБЯСНИТЕЛНА ЗАПИСКА, caught = TP). The signoff seam fired twice → spurious extra start at p7. NOT a page-index artifact (verified by render p7/p8). |
| tests/РС-33-2017/5/Image_00112032025084837699.pdf | 11 | FN | [NO-SIGNAL] p11 start, end=False (drawing/table page, no header) |
| tests/РС-33-2017/5/Image_00112032025084837699.pdf | 12 | FN | [NO-SIGNAL] p12 start, end=False |
| tests/РС-33-2017/6/Image_00112032025085002901.pdf | 9 | FN | [NO-SIGNAL] p9 start in a long table/drawing run (pp6–17 all end=False) |

## FRESH stratum (8 files)
| Filepath | Page | Type | Reason |
|---|---|---|---|
| tests/РС-31-2017/1/Image_00112022025162710373.pdf | 4 | FP | [SECTION-FP] `signature_block` p3→4, "РАЗПИСЕН ЛИСТ" section cut |
| tests/РС-31-2017/3/Image_00112022025164052657.pdf | 14 | FP | [SIG-OVERCUT] `signature_block` p14 → "ОБЯСНИТЕЛНА ЗАПИСКА" section cut as new doc |!!!!!!!!!!!!
| tests/РС-33-2017/1/Image_00112032025083553577.pdf | 9 | FP | [SIG-OVERCUT] `signature_block` p9 inside same doc |
| tests/РС-33-2017/1/Image_00112032025083553577.pdf | 33 | FP | [START-DETECT] p34 letterhead change bled to a p33 cut | !!! VERY IMPORTANT

| tests/РС-34-2017/1/Image_00112022025142438096.pdf | 69 | FP | [SIG-OVERCUT] `signature_block` p69 over-cut |
| tests/РС-34-2017/1/Image_00112022025142438096.pdf | 88 | FP | [SECTION-FP] КОЛИЧЕСТВЕНА СМЕТКА-class section heading | !!!

| tests/РС-34-2017/1/Image_00112022025142438096.pdf | 8 | FN | [NO-SIGNAL] p8 start, end=False |

| tests/РС-34-2017/1/Image_00112022025142438096.pdf | 26 | FN | [NO-SIGNAL] real start in a drawing/table run | Modify the draw criteria
| tests/РС-34-2017/1/Image_00112022025142438096.pdf | 61 | FN | [NO-SIGNAL] real start, end=False |
| tests/РС-34-2017/1/Image_00112022025142438096.pdf | 64 | FN | [NO-SIGNAL/SECTION] КОЛИЧЕСТВЕНА СМЕТКА section-vs-doc confusion |
| tests/РС-34-2017/1/Image_00112022025142438096.pdf | 65 | FN | [NO-SIGNAL] real start missed |

| tests/РС-35-2017/1/Image_00112022025143041245.pdf | 37 | FP | [SECTION-FP] mid-doc section (numbering gap) | !!! Investigate

| tests/РС-35-2017/1/Image_00112022025143041245.pdf | 43 | FP | [WEAK-TITLE] ЗАЯВЛЕНИЕ + START-DETECT EIK-change on a section |

| tests/РС-35-2017/1/Image_00112022025143041245.pdf | 51 | FP | [SIG-OVERCUT] "Търговски условия" section cut |
| tests/РС-35-2017/1/Image_00112022025143041245.pdf | 66 | FP | [SIG-OVERCUT] section cut | !!!!!!!!! Did it see a heading. The number next to the heading could be checked as a continuation of the document as a section.

| tests/РС-35-2017/1/Image_00112022025143041245.pdf | 10 | FN | [LOCALIZE] LETTER OF ATTORNEY localized to p10 area, real start mismatch | !!!!!!!

| tests/РС-35-2017/1/Image_00112022025143041245.pdf | 20 | FN | [NO-SIGNAL] real start, end=False | !!!!!!!!!!

| tests/РС-35-2017/1/Image_00112022025143041245.pdf | 26 | FN | [NO-SIGNAL] real start, end=False | !!!!!





| tests/РС-36-2017/1/Image_00112022025145428614.pdf | 65 | FP | [SECTION-FP]/[SIG-OVERCUT] over-segmentation | !!!!

| tests/РС-36-2017/1/Image_00112022025145428614.pdf | 66 | FP | [SECTION-FP] section heading (КОЛИЧЕСТВЕНА СМЕТКА @66 was a human-attested section) |

| tests/РС-36-2017/1/Image_00112022025145428614.pdf | 71 | FP | [SIG-OVERCUT] over-cut |
| tests/РС-36-2017/1/Image_00112022025145428614.pdf | 102 | FP | [SECTION-FP]/[SIG-OVERCUT] over-segmentation |  !!!!!!!
| tests/РС-36-2017/1/Image_00112022025145428614.pdf | 151 | FP | [SECTION-FP]/[SIG-OVERCUT] over-segmentation |

| tests/РС-36-2017/1/Image_00112022025145428614.pdf | 45 | FN | [NO-SIGNAL]/[TABLE-VETO] real start in a table/drawing run missed |

| tests/РС-36-2017/1/Image_00112022025145428614.pdf | 56 | FN | [NO-SIGNAL] real start missed |!!!!!


| tests/РС-36-2017/1/Image_00112022025145428614.pdf | 104 | FN | [NO-SIGNAL] real start missed |!!!!!

| tests/РС-36-2017/1/Image_00112022025145428614.pdf | 159 | FN | [NO-SIGNAL] real start missed | !!!!!!

| tests/РС-33-2017/2/Image_00112032025084031203.pdf | 6 | FP | [WEAK-TITLE] `titled_id_header` p6 ЗАСТРАХОВАТЕЛНА ПОЛИЦА over-cut region |!!!!!!!!!!!!!!

| tests/РС-33-2017/2/Image_00112032025084031203.pdf | 46 | FP | [SIG-OVERCUT] section over-cut | !!!!!

| tests/РС-33-2017/2/Image_00112032025084031203.pdf | 12 | FN | [LOCALIZE] `project_signoff` p10→11→12, real p12 start localization | !!!!!

| tests/РС-33-2017/2/Image_00112032025084031203.pdf | 30 | FN | [NO-SIGNAL] real start in a long table run (pp16–27 end=False) | !!!!!!!!!

## Dominant patterns

### FP breakdown (programmatic adjacency analysis — AUTHORITATIVE; supersedes the per-row [SECTION-FP]/[SIG-OVERCUT] labels above, which were inferred from log lines)
Classifying each of the 41 FPs by whether it sits ±1 from a true start:
- **29 = DOUBLE-FIRE / extra adjacent cut** (a real start at p±1 was ALSO predicted). The spurious cut is
  wedged next to a real boundary — either a signoff-seam smear (e.g. 084837699 p7: prev doc's signature page
  cut as a start on top of the correct p8) or an extra cut between closely-spaced short docs (certificates/
  policies). **This is the dominant FP mode (~71%).**
- **11 = isolated phantom over-cut** (no true start adjacent) — the genuine [SECTION-FP]/[SIG-OVERCUT] class:
  `164052657@35`, `164505881@9`, `084031203@6`, `142438096@88`, `143041245@{7,8,51}`, `145428614@{7,35,65,66}`.
- **1 = pure LOCALIZATION** (`142438096@7`, real start missed; would be TP at tol=1).

**Implication:** the largest precision lever is **deduping adjacent boundaries** (collapse two cuts within 1 page),
NOT better section-heading detection — only 11 of 41 FPs are true phantom section cuts.

### FN patterns
- **[NO-SIGNAL]** — real starts buried in scanned table/drawing runs with no header cue (the majority of FNs).
- **[TABLE-VETO]** — the rubber-stamp confirm killing genuine table-doc starts (the Fix 11 target; e.g. 082511233 p20, 164505881 p12).

### Per-row caveat
The `Type`/reason labels in the stratum tables above were inferred from the log's signal/decision lines BEFORE the
adjacency analysis. For FP *classification*, trust this programmatic breakdown. One row was render-verified and
corrected: 084837699 p7 = DOUBLE-FIRE (not "[SIG-OVERCUT] inside same doc").

## Caveats
- `145428614`'s 11 FPs are characterized by **class**, not per-line — that file's per-page decision lines
  are not in the committed log slice (only its final prediction array is).
- Built from the committed candidate log (`logs/fulltests_stage2.log`); no pod required.
