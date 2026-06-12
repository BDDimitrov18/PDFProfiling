# Fable 5 boundary benchmark — Image_00112022025163444215.pdf (strict pipeline parity)

**Setup.** Target: `tests/РС-31-2017/2/Image_00112022025163444215.pdf` — **37 pages** (the brief said 31;
the actual page count is 37, consistent with corrected GT whose last start is p34 and with Fix-11 notes
referencing FPs 35/37 on this file). Rendering: the pipeline's own `_load_page` (pdf2image @ 150 DPI)
and the pipeline's own `query_rotation_osd_first` (tesseract OSD) — **OSD returned 0° for all 37 pages**,
so no rotation was applied (matches production behavior on upright pages). `split.py` at tag
`round1-candidate` ran **unmodified** (`detect_boundaries`, `classify=False`); the only patch was
`split._infer`, redirected to claude-fable-5 subagents (Agent tool, model=fable). Each subagent got the
verbatim prompt text + the exact PIL images (saved losslessly as PNG), fresh per window, and returned
only the JSON. No ground truth, no candidate predictions, no FP/FN discussion was visible to any
subagent. All routing — sliding window [n−1, n, n+1], signal_on_page adjustment, START_ON_NEXT vs
END_ON_PAGE placement, confidence caps, signature gate, one-page check, appendix chain, low-conf
confirmation, start-detector — executed by the candidate's own code (driver: `fable5_run/driver.py`).

**Queries.** 81 total: 72 base (36 `style_continuity` + 36 `end_of_doc`) + 9 corrective
(7 `starts_new_document`, 2 `next_page_starts_new`). Raw responses: `fable5_run/163444215_raw.log`.
One artifact: the n=15 end-of-doc response came back with the closing `}` missing (truncated
generation); per parity, `_parse_json` treated it as no-signal (end=False), exactly as the pipeline
treats a truncated 32B generation at max_tokens=150. (Its content said `end=true, signal_on_page=16`;
the start-detector independently re-derived the p16 boundary anyway, so the final boundary set is
unaffected by the artifact.)

## Score (eval_boundaries.match_sets, corrected GT, tol 0 = tol 1)

| model | TP | FP | FN | P | R | F1 |
|---|---|---|---|---|---|---|
| candidate 32B (Fix9-only, RTX 5090) | 16 | 6 — [6, 11, 13, 19, 27, 31] | 0 | 72.73% | 100% | **84.21%** |
| **Fable 5 (this run)** | 16 | 8 — [6, 13, 16, 17, 18, 19, 20, 21] | 0 | 66.67% | 100% | **80.00%** |

Fable 5 predicted starts: [1, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 32, 34]
(`fable5_run/predictions.json`).

## Three-way per-boundary diff (✓ = boundary present; page = first page of new doc)

| page | GT | 32B | Fable 5 | seam |
|---|---|---|---|---|
| 3 | ✓ | ✓ | ✓ | СЪОБЩЕНИЕ after permit conditions |
| 4 | ✓ | ✓ | ✓ | **p4-class: HOLDS** (РАЗНОСЕН ЛИСТ; F5 conf 65, titled_id_header skips confirm) |
| 5 | ✓ | ✓ | ✓ | municipal letter (Изх. №) |
| 6 | — | **FP** | **FP** | both split известие за доставяне off the signed letter |
| 7 | ✓ | ✓ | ✓ | ЗАПОВЕД |
| 8 | ✓ | ✓ | ✓ | invoice after signed order |
| 9 | ✓ | ✓ | ✓ | second invoice |
| 10 | ✓ | ✓ | ✓ | **GT-correction boundary: HOLDS** (СКИЦА after invoice; F5 conf 92) |
| 11 | — | **FP** | — | **DISAGREE** — 32B confabulated "РС №" on p11; F5 reads `стр. 2 от 2` → continuation |
| 12 | ✓ | ✓ | ✓ | ПРОТОКОЛ № 5 (12/13 spillover: boundary correctly at 12) |
| 13 | — | **FP** | **FP** | both split the ЗАЯВЛЕНИЕ (вх. № at top); GT keeps 12–14 together |
| 15 | ✓ | ✓ | ✓ | first ЕСУТ review slip |
| 16 | — | — | **FP** | **DISAGREE** — F5 start-detector: slip restart (conf 75) |
| 17 | — | — | **FP** | **DISAGREE** — F5 header_block_reset (conf 70) |
| 18 | — | — | **FP** | **DISAGREE** — F5 header_block_reset (conf 70) |
| 19 | — | **FP** | **FP** | both split; different mechanisms (32B "РС №" confabulation vs F5 slip-header restart) |
| 20 | — | — | **FP** | **DISAGREE** — F5 header_block_reset (conf 75) |
| 21 | — | — | **FP** | **DISAGREE** — F5 header_block_reset (conf 72→75) |
| 22 | ✓ | ✓ | ✓ | АТРИЯ-АРХ cover sheet (fresh_letterhead) |
| 23 | ✓ | ✓ | ✓ | КАБ УДОСТОВЕРЕНИЕ |
| 24 | ✓ | ✓ | ✓ | Армеец policy |
| 25 | ✓ | ✓ | ✓ | СКИЦА № 15-525676 |
| 26 | ✓ | ✓ | ✓ | НОТАРИАЛЕН АКТ |
| 27 | — | **FP** | — | **DISAGREE** — 32B confabulated "numbered identifier"; F5: deed body continues mid-list |
| 31 | — | **FP** | — | **DISAGREE** — deed signature page; F5 keeps it attached to the deed |
| 32 | ✓ | ✓ | ✓ | ОБЯСНИТЕЛНА ЗАПИСКА |
| 34 | ✓ | ✓ | ✓ | КОЛИЧЕСТВЕНА СМЕТКА |

**8 seams where the models disagree: 11, 16, 17, 18, 20, 21, 27, 31.** Fable 5 fixes the 32B's three
"phantom identifier" FPs (11, 27, 31) and adds five new FPs in the ЕСУТ review-slip stack (16–18, 20–21).

## Named test cases (verbatim Fable 5 reasons)

**p11 (32B confabulated "РС №") — FP AVOIDED.** end_of_doc n=10 → `end=false, signal=same_letterhead, conf=90`:
> "Page 11 carries the same Служба по геодезия letterhead with a 'стр. 2 от 2' counter and its footer repeats the same Скица № 15-158202-06.04.2017 as page 10, so it continues the same cadastral sketch document."

The cited text is corroborated by three other independent subagents (end n=9 read the p10 title
"СКИЦА НА ПОЗЕМЛЕН ИМОТ № 15-158202-06.04.2017 г."; start-detect p10→p11 read the same number and the
`стр. 2 от 2` counter; the style query read the shared agency letterhead) — i.e., the reason cites text
that actually exists, unlike the 32B's "РС №".

**p19 (32B confabulated "РС №") — FP REPRODUCED, but for a real visual reason.** end_of_doc n=18 →
`end=true, signal=header_block_reset, conf=75`:
> "Page 19 is a fresh self-contained ЕСУТ review slip repeating the Обект / Част / становище header block with its own date (13.07.2017) and different handwritten content, making page 18 a complete single-page slip."

No invented identifier — Fable 5 splits because each routing slip genuinely restarts the same printed
form. The error is a GT-convention disagreement (GT files the whole slip stack 15–21 as one document),
not a perception failure.

**p27 (32B confabulated "numbered identifier") — FP AVOIDED.** end_of_doc n=26 → `end=false, signal=none, conf=90`:
> "Page 27 continues the notarial act's body text mid-list (numbered ПОЗЕМЛЕН ИМОТ items with cadastral identifiers) with no new title, letterhead, or signature block, so page 26 does not end the document."

(The start-detector p26→p27 corrective independently agreed: "continues the numbered list of ПОЗЕМЛЕН
ИМОТ entries (items 2-7 with the same cadastral identifiers 56784.265.x …)".)

**p31 (deed signature page) — FP AVOIDED.** end_of_doc n=30 → `end=false, signal=none, conf=80`:
> "Page 30 ends mid-notarial-text and page 31 carries the handwritten signatures of the СЪДЕЛИТЕЛИ and НОТАРИУС with stamp, which is the signature page concluding the same notarial deed, not a new document start."

This is precisely the page where the 32B's one-page-check declared p31 "self-contained" off the
СЪДЕЛИТЕЛИ heading. Fable 5's start-detector p30→p31 also said `starts_new=false, conf=95` ("signature/stamp
closing block … of the notarial deed text running on page 30").

**pages 12/13 spillover — boundary 12 CORRECT, FP 13 reproduced.** Boundary at 12 placed exactly
(end n=11 → titled_id_header on p12: "centered issuer header 'РАЙОНЕН ЕКСПЕРТЕН СЪВЕТ…' and the standalone
title 'ПРОТОКОЛ № 5' … while page 11 is the closing 'стр. 2 от 2' continuation of the cadastral sketch").
At n=12 Fable 5 splits p13 like the 32B did, citing real text:
> "Page 12 is a self-contained ПРОТОКОЛ № 5 ending with certification signatures, and page 13 opens a new document — a ЗАЯВЛЕНИЕ to the chief architect with an incoming registration stamp (вх. № with 2017 date) at the very top."

The 32B read the same stamp ('Вх. № 2-94 00-304/27.02.2017'). Both models treat the application as a new
document; GT attaches 13–14 to the doc starting at 12. Conf 88 ≥ 0.75 and titled_id_header skips the
confirmation pass, so the candidate's routing offers no brake here for either model.

**p10 — HOLDS.** end_of_doc n=9 → `end=true, signal=titled_id_header, signal_on_page=10, conf=92`:
> "Page 10 opens with the geodesy/cadastre agency letterhead and the title 'СКИЦА НА ПОЗЕМЛЕН ИМОТ № 15-158202-06.04.2017 г.' at the very top, a fresh document title with its own document-level number, while page 9 is an invoice (ФАКТУРА) unrelated to the cadastral sketch."

**p4-class — HOLDS.** end_of_doc n=3 → `end=true, signal=titled_id_header, signal_on_page=4, conf=65`:
> "Page 3 is a complete СЪОБЩЕНИЕ ending with signed Съобщил/Изготвил fields, and page 4 opens with a new form title (РАЗНОСЕН ЛИСТ) at the very top referencing a '№' identifier, starting a separate tabular delivery-list document."

(conf 65 < 0.75 would normally trigger the confirmation pass, but titled_id_header is exempted — the
boundary survives on the same routing rule that preserved p4 for the 32B.)

## Headline observations

1. **The confabulation failure mode is gone.** All three 32B FPs whose `reason` invented identifiers
   that don't exist (11, 27, 31) flip to confident, correctly-grounded `end=false` — and every Fable 5
   reason that cites specific text is cross-corroborated by other independent subagents seeing the same
   pages. Recall stays 100% (FN=0, including the two corrected-GT boundaries p10 and the p4 class).
2. **A different, honest failure mode appears: form-instance granularity.** Fable 5 splits each ЕСУТ
   routing slip (15–21 → 6 predicted docs; GT says 1). The candidate's `header_block_reset` signal is
   exempt from the confirmation pass at any confidence, so nothing in the Fix9-only routing can stop
   it. This is a labeling-convention question (are 7 filled instances of the same slip one document?),
   the same class as FP 13 and FP 6 — which both models share.
3. **Net F1 on this one file is lower (80.00 vs 84.21)** despite better perception, entirely due to the
   slip cluster. If the slip stack were scored as separate documents (or a cluster-suppression rule for
   repeated identical forms were added), Fable 5 would be at FP=[6,13] → P=88.9, F1=94.1 on this file.
4. **Reliability artifact:** 1 of 81 responses (1.2%) was malformed JSON (truncated). The pipeline's
   parse-failure path absorbed it; with no greedy-decoding determinism, n=1 runs are not exactly
   reproducible.

## Cost & wall-clock

- 81 subagent queries; **981,141 total subagent tokens** (includes each subagent's harness system
  prompt and tool-result framing, so this overstates a pure-API replay); avg 12.1k tokens / 21.4 s per
  query; **26.5k tokens / 47 s of summed query time per page** (37 pages). Elapsed experiment time was
  lower (base queries ran in parallel batches of 8); corrective passes are inherently sequential.
- At claude-fable-5 pricing ($10 in / $50 out per MTok): ≈ $9.8 if all tokens were input, ≈ $14–16 at a
  realistic 10–15% output share (thinking is always on and bills as output) → **≈ $0.30–0.45 per page**.
  For comparison the 32B candidate's marginal cost is GPU-rental time only.

## Files

- `fable5_run/predictions.json` — predicted starts + per-boundary confidences
- `fable5_run/163444215_raw.log` — every raw subagent response, window order, with wall/tokens
- `fable5_run/driver.py` — parity driver (patches only `split._infer`; render/rotation cached)
- `fable5_run/rotation_log.json` — OSD result per page (all 0)
- `fable5_run/queries/` + `fable5_run/responses/` — exact images+prompt per query, and raw replies
