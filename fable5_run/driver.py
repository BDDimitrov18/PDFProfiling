#!/usr/bin/env python3
"""
Fable 5 boundary benchmark driver — strict parity replay of split.py (round1-candidate)
on tests/РС-31-2017/2/Image_00112022025163444215.pdf.

Reuses the pipeline's own code: split.detect_boundaries runs UNMODIFIED. The only
patch is split._infer, which is replaced by a response cache keyed by
sha256(prompt_text). A cache miss means a model query that has not yet been
answered by a claude-fable-5 subagent:
  - collect mode: misses return None (parse → no-signal defaults), so the run
    completes and enumerates every routing-independent base query (style + end).
  - strict mode: the run STOPS at the first miss (exit 3) so corrective-pass
    routing never proceeds on a placeholder.

split._load_page is wrapped with a lossless PNG disk cache (the first render of
each page goes through the pipeline's own pdf2image call at 150 DPI; reloads are
pixel-identical). split._query_rotation is wrapped with a JSON cache around the
pipeline's own query_rotation_osd_first (tesseract OSD), so rotation is computed
once by the production code path and replayed identically on every rerun.

Usage: python3 driver.py collect|strict
Exit codes: 0 = completed (predictions written), 3 = stopped at pending query.
"""
import hashlib
import json
import logging
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import split  # noqa: E402
from pypdf import PdfReader  # noqa: E402

RUN = REPO / "fable5_run"
PAGES = RUN / "pages_cache"
QUERIES = RUN / "queries"
RESP = RUN / "responses"
PDF = REPO / "tests/РС-31-2017/2/Image_00112022025163444215.pdf"
DPI = 150

MODE = sys.argv[1] if len(sys.argv) > 1 else "strict"
assert MODE in ("collect", "strict"), MODE

# ---------------------------------------------------------------------------
# Page render cache — first render uses the pipeline's own _load_page
# ---------------------------------------------------------------------------
_orig_load_page = split._load_page


def _cached_load_page(pdf_path, page_num, dpi):
    p = PAGES / f"page_{page_num:02d}_dpi{dpi}.png"
    if p.exists():
        from PIL import Image
        return Image.open(p).convert("RGB")
    img = _orig_load_page(pdf_path, page_num, dpi)
    img.save(p)
    return img


split._load_page = _cached_load_page

# ---------------------------------------------------------------------------
# Rotation cache — pipeline's own OSD-first detector, computed once
# ---------------------------------------------------------------------------
ROT_CACHE_PATH = RUN / "rotation_log.json"
_rot_cache = json.loads(ROT_CACHE_PATH.read_text()) if ROT_CACHE_PATH.exists() else {}
_orig_query_rotation = split._query_rotation


def _cached_query_rotation(img, page_num, model, processor, config, logger):
    k = str(page_num)
    if k not in _rot_cache:
        _rot_cache[k] = _orig_query_rotation(img, page_num, model, processor, config, logger)
        ROT_CACHE_PATH.write_text(json.dumps(_rot_cache, indent=1, sort_keys=True))
    return _rot_cache[k]


split._query_rotation = _cached_query_rotation

# ---------------------------------------------------------------------------
# _infer fake — cache-backed; misses become pending Fable 5 queries
# ---------------------------------------------------------------------------
KIND_PATTERNS = [
    ("end_of_doc", r"END a document"),
    ("style_continuity", r"Compare these two scanned document pages visually"),
    ("self_contained", r"SELF-CONTAINED one-page document"),
    ("next_page_starts_new", r"ends with a signature or approval block"),
    ("starts_new_document", r"BEGIN a new, separate document distinct"),
    ("confirm_boundary", r"DIFFERENT documents that should be filed separately"),
    ("appendix_standalone", r"an appendix heading"),
    ("classify", r"FIRST page of a document"),
    ("doc_identifier", r"most prominent document"),
]


def _guess_kind(prompt: str) -> str:
    for kind, pat in KIND_PATTERNS:
        if re.search(pat, prompt):
            return kind
    return "unknown"


def _guess_pages(kind: str, prompt: str):
    if kind == "end_of_doc":
        m = re.search(r"consecutive scanned pages \(([\d, ]+)\)", prompt)
        cur = re.search(r"Does page (\d+) END", prompt)
        return {"window": [int(x) for x in m.group(1).split(",")] if m else [],
                "current": int(cur.group(1)) if cur else None}
    if kind == "style_continuity":
        m = re.search(r"second page \(page (\d+)\)", prompt)
        return {"pages": [int(m.group(1)) - 1, int(m.group(1))] if m else []}
    if kind == "self_contained":
        m = re.search(r"Look at page (\d+)", prompt)
        return {"pages": [int(m.group(1))] if m else []}
    if kind == "next_page_starts_new":
        a = re.search(r"Page (\d+) ends with", prompt)
        b = re.search(r"page \(page (\d+)\)", prompt)
        return {"pages": [int(a.group(1)) if a else None, int(b.group(1)) if b else None]}
    if kind == "starts_new_document":
        m = re.search(r"\(page (\d+) and page (\d+)\)", prompt)
        return {"pages": [int(m.group(1)), int(m.group(2))] if m else []}
    if kind == "confirm_boundary":
        m = re.search(r"Do page (\d+) and page (\d+)", prompt)
        return {"pages": [int(m.group(1)), int(m.group(2))] if m else []}
    if kind == "appendix_standalone":
        m = re.search(r"examining pages ([\d, ]+) from", prompt)
        c = re.search(r"Page (\d+) starts with", prompt)
        return {"window": [int(x) for x in m.group(1).split(",")] if m else [],
                "candidate": int(c.group(1)) if c else None}
    return {}


_call_seq = 0
_pending = []


def _fake_infer(prompt_text, images, model, processor, config, logger, max_tokens=200):
    global _call_seq
    _call_seq += 1
    key = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:16]
    kind = _guess_kind(prompt_text)
    qdir = QUERIES / f"{kind}_{key}"
    if not qdir.exists():
        qdir.mkdir(parents=True)
        for i, im in enumerate(images):
            im.save(qdir / f"img{i}.png")
        (qdir / "prompt.txt").write_text(prompt_text, encoding="utf-8")
        (qdir / "meta.json").write_text(json.dumps({
            "key": key, "kind": kind, "pages": _guess_pages(kind, prompt_text),
            "n_images": len(images), "max_tokens": max_tokens,
            "first_seen_call_seq": _call_seq,
        }, ensure_ascii=False, indent=1))
    resp_file = RESP / f"{key}.txt"
    if resp_file.exists():
        return resp_file.read_text(encoding="utf-8")
    _pending.append({
        "key": key, "kind": kind, "pages": _guess_pages(kind, prompt_text),
        "qdir": str(qdir),
        "images": [str(qdir / f"img{i}.png") for i in range(len(images))],
        "prompt_file": str(qdir / "prompt.txt"),
        "response_file": str(resp_file),
    })
    if MODE == "strict":
        (RUN / "pending.json").write_text(json.dumps(_pending, ensure_ascii=False, indent=1))
        print(f"PENDING_QUERY {kind} {key} pages={_guess_pages(kind, prompt_text)}")
        sys.exit(3)
    return None


split._infer = _fake_infer

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def main():
    logger = logging.getLogger("fable5_driver")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    fh = logging.FileHandler(RUN / "driver_log.txt", mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(ch)
    logger.addHandler(fh)

    total_pages = len(PdfReader(str(PDF)).pages)
    logger.info(f"[driver mode={MODE}] {PDF.name}: {total_pages} pages @ {DPI} DPI")

    boundaries, pages_rotated = split.detect_boundaries(
        PDF, total_pages, None, None, None, DPI, logger, classify=False
    )

    (RUN / "pending.json").write_text(json.dumps(_pending, ensure_ascii=False, indent=1))
    if _pending:
        logger.info(f"[driver] run completed with {len(_pending)} PENDING (placeholder) queries — predictions NOT valid")
        sys.exit(3)

    pred = sorted({b.page for b in boundaries})
    out = {
        "file": "Image_00112022025163444215.pdf",
        "model": "claude-fable-5 (Agent-tool subagents)",
        "pipeline": "split.py @ round1-candidate (Fix9-only), detect_boundaries classify=False",
        "dpi": DPI,
        "total_pages": total_pages,
        "predicted_starts": pred,
        "pages_rotated": pages_rotated,
        "boundaries": [
            {"page": b.page, "confidence": round(b.confidence, 4)} for b in boundaries
        ],
    }
    (RUN / "predictions.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    logger.info(f"[driver] COMPLETE — predicted starts: {pred}")
    logger.info(f"[driver] rotated pages: {pages_rotated}")


if __name__ == "__main__":
    main()
