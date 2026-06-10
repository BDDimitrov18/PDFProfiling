# PDF Document Splitter — Project Spec

## What This Does
Automatically classifies and splits a multi-document scanned PDF into separate PDFs, one per document. The user receives batches of combined scanned PDFs (e.g. 100 pages = multiple different documents scanned together) and needs them split apart automatically.

## Business Context
- User is paid per document processed
- Per-document API costs must stay below per-document income
- Solution must be economically viable → **local AI only, zero per-run cost**
- Volume: **6–7 combined PDFs per day**
- Runs as a **background job** (not real-time, results needed by next working session)

## Key Technical Constraints
- Documents are **scanned images** — OCR/text extraction is unreliable, must use **vision AI**
- AI needs **full document context** across all pages to detect boundaries accurately
- Must run **100% locally** — no cloud API calls during processing
- Must support **multiple images per prompt** — required for rolling window approach

## Hardware
- MacBook with **Apple M3 chip, 32GB unified RAM**
- Apple Silicon — MLX framework runs natively, no CUDA/drivers needed

## Chosen Tech Stack
| Component | Choice | Reason |
|---|---|---|
| Vision AI runtime | **mlx-vlm** (direct Python) | Native Apple Silicon, multi-image support, built-in vision feature cache |
| Vision model | **Qwen3-VL 8B 4-bit** from mlx-community | Best local document understanding, fits 32GB, multi-image confirmed working in mlx-vlm |
| PDF → images | **pdf2image** + poppler | Standard, reliable |
| PDF splitting | **pypdf** | Lightweight, pure Python |
| Image handling | **Pillow** | Required by pdf2image |
| Language | **Python** | Simple, cross-platform |

### Why mlx-vlm over Ollama
Ollama has a confirmed bug where Qwen3-VL returns no response when multiple images are sent
in a single prompt — making the rolling window approach impossible. mlx-vlm:
- Natively supports multiple images per prompt (Qwen3-VL multi-image confirmed working,
  with a dedicated bug fix shipped in a recent mlx-vlm release)
- Built specifically for Apple Silicon (MLX framework)
- Includes VisionFeatureCache: pages N-2 and N-1 are already cached when the next
  window starts, so only the new page N is fully encoded each time — significant speedup
- Direct Python API, no separate server process needed

### Model: mlx-community/Qwen3-VL-8B-Instruct-4bit
- Downloaded once from HuggingFace at first run (~5GB)
- 4-bit quantized for memory efficiency on 32GB
- DocVQA score: **96.1%** (beats Qwen2.5-VL 7B at 95.7%, ahead of Claude 3.5 Sonnet at 95.2%)
- Wins on 9 out of 12 benchmarks vs Qwen2.5-VL 7B
- Multi-image support fully working via mlx-vlm

## How It Works (Architecture)
1. Watch a folder for incoming combined PDFs
2. Convert each PDF page to an image
3. Load mlx-vlm model (Qwen3-VL 8B 4-bit) once at startup (stays in memory for all PDFs)
4. For each page N, send [page N-2, page N-1, page N] as a multi-image prompt
5. AI returns boundary decision + document type code from nomenclature table
6. Confidence voting across overlapping windows confirms or rejects each boundary
7. Split original PDF into separate files using pypdf
8. Output split PDFs to a `/split` subfolder, named by document code

## Context Strategy — Rolling Window (chosen)
For each page N, send pages **N-2, N-1, N** (3-page rolling window) to the model and ask:
- Does page N start a NEW document?
- If yes, which document type from the nomenclature table does it match?

Since each page appears in 3 consecutive windows, a **confidence voting** mechanism
cross-checks boundary decisions — if 2 out of 3 windows agree a boundary exists at
page N, the split is made there.

### Vision feature caching advantage
With mlx-vlm's VisionFeatureCache, pages already seen in a previous window are not
re-encoded. For a 3-page window sliding one page at a time, 2 out of 3 images are
cache hits on every call — roughly 3x faster than re-encoding all images each time.

Additional accuracy mechanisms:
- **Confidence threshold:** If model confidence < 80%, flag page for manual review
- **Overlap voting:** Cross-check boundary decisions across windows
- **Fallback code:** Unrecognized documents default to the catch-all `X999` "Друг вид документ" code

## Performance Expectations
- First page of each window: full vision encoding (~5–10 sec)
- Pages 2–3 of each window: cache hits (~under 1 sec each)
- 100-page PDF ≈ 8–18 minutes total
- Acceptable since it runs as a background/overnight job

## Setup Steps (One Time)
```bash
# 1. Install Homebrew from brew.sh (if not already installed)
brew install poppler

# 2. Install Python dependencies
pip install mlx-vlm pdf2image pypdf pillow
# Note: pandas/xlrd NOT needed — nomenclature table is hardcoded in the script
# Note: ollama package NOT needed — mlx-vlm replaces it entirely

# 3. Model downloads automatically from HuggingFace on first run (~5GB)
# Model: mlx-community/Qwen3-VL-8B-Instruct-4bit
```

## Nomenclature Table
**Hardcoded as a constant in the script** — no file loading at runtime.
Format: numeric code (e.g. `1001`) mapped to Bulgarian name (e.g. `Обяснителна записка`)
Total entries: **382 document types** across 19 top-level categories:

| Code range | Category |
|---|---|
| 1000–1999 | Архитектура |
| 2000–2999 | Конструкции |
| 3000–3999 | Водоснабдяване и канализация |
| 4000–4999 | Електричество |
| 5000–5999 | Топлоснабдяване, отопление, вентилация и климатизация |
| 6000–6999 | Енергийна ефективност |
| 7000–7999 | Газоснабдяване |
| 8000–8999 | Геодезия |
| 9000–9999 | Паркоустрояване и благоустрояване |
| 10000–10999 | Технологична |
| 11000–11999 | Пожарна безопасност |
| 12000–12999 | ПБЗ (безопасност и здраве) |
| 13000–13999 | Организация и безопасност на движението |
| 14000–14999 | Консервация, реставрация |
| 15000–15999 | Инженерно-геоложко проучване |
| 16000–16999 | Преработка по чл. 154 |
| 17000–17999 | Генерален план |
| 18000–18999 | Сметна документация |
| 19000–19999 | Документи (legal/admin documents) |

The full table is injected into the AI system prompt at runtime so the model classifies
against exact codes and names rather than guessing freely.

Output PDFs are named using the code and name: e.g. `1001_Обяснителна_записка.pdf`

## Open Questions (Decide Before Building)
1. **Script interface:** Command line (`python split.py /folder`) or GUI (drag-and-drop)?
2. **Multi-page documents:** Are documents expected to span multiple pages, or mostly single-page?
3. **Error handling:** What should happen if AI confidence < 80% on a boundary? (flag for manual review, or best guess?)

## What To Build
A Python script that:
- Accepts a folder path as input
- Processes all PDFs in that folder
- Loads mlx-vlm model once at startup (not per PDF)
- For each PDF: converts to images → rolling window classification → splits into separate PDFs
- Saves output to a `/split` subfolder next to the originals
- Logs progress so the user can see what happened after the fact
- Handles errors gracefully (bad scans, uncertain boundaries, etc.)