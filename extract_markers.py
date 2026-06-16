#!/usr/bin/env python3
"""extract_markers.py — POD-ONLY driver: emit-and-log the 4 transcribe-first marker channels per
page, WITHOUT touching split.py's live boundary decisions (staged, same discipline as Fix-11).

For each page it runs the 4 TRANSCRIPTION prompts (marker_extraction.PROMPTS) through the model —
verbatim transcription, never yes/no — then the PURE matchers render the markers. Writes a JSON
log {file: {page: {channels..., markers, issuer, title, titleblock_fields}}} for replay scoring.

Usage (on the pod):  python3 extract_markers.py eval_full  -> logs/markers_<folder>.json
Pod-only: imports split.py (model load) lazily in main(); NOT importable pod-less without weights.
"""
import json, sys
from pathlib import Path
from marker_extraction import PROMPTS, CHANNELS, extract_from_transcriptions


def main():
    folder = Path(sys.argv[1])
    import split  # lazy: heavy (transformers + weights) — pod-only
    model, processor = split.load_model(split.MODEL_PATH)
    logger = split.setup_logging() if hasattr(split, "setup_logging") else None
    out = {}
    for pdf in sorted(folder.glob("*.pdf")):
        from pypdf import PdfReader
        n_pages = len(PdfReader(str(pdf)).pages)
        out[pdf.name] = {}
        for p in range(1, n_pages + 1):
            img = split._load_page(pdf, p, getattr(split, "DEFAULT_DPI", 150))
            trans = {}
            for ch in CHANNELS:
                raw = split._infer(PROMPTS[ch], [img], model, processor, {}, logger, max_tokens=160)
                trans[ch] = (raw or "").strip()
            rec = extract_from_transcriptions(trans)
            rec["markers"] = sorted(rec["markers"])           # JSON-serialisable
            rec["transcriptions"] = trans                     # keep raw for audit
            out[pdf.name][p] = rec
            print(f"{pdf.name} p{p}: markers={rec['markers']} issuer={rec['issuer']} title={rec['title']!r}")
    dest = Path("logs") / f"markers_{folder.name}.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
