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
    logger = split.setup_logging(Path("logs"))
    model, processor, config = split.load_model(split.MODEL_PATH, logger)
    dest = Path("logs") / f"markers_{folder.name}.json"
    # RESUME: reload any existing checkpoint so a re-launch after an SSH drop skips done pages.
    out = {}
    if dest.exists():
        try:
            out = json.loads(dest.read_text(encoding="utf-8"))
            print(f"resume: loaded checkpoint with {sum(len(v) for v in out.values())} pages")
        except Exception:
            out = {}
    from pypdf import PdfReader
    for pdf in sorted(folder.glob("*.pdf")):
        n_pages = len(PdfReader(str(pdf)).pages)
        out.setdefault(pdf.name, {})
        for p in range(1, n_pages + 1):
            if str(p) in out[pdf.name]:        # already extracted (resume)
                continue
            img = split._load_page(pdf, p, getattr(split, "DEFAULT_DPI", 150))
            trans = {}
            for ch in CHANNELS:
                raw = split._infer(PROMPTS[ch], [img], model, processor, config, logger, max_tokens=160)
                trans[ch] = (raw or "").strip()
            rec = extract_from_transcriptions(trans)
            rec["markers"] = sorted(rec["markers"])           # JSON-serialisable
            rec["transcriptions"] = trans                     # keep raw for audit
            out[pdf.name][str(p)] = rec
            dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")  # per-page checkpoint
            print(f"{pdf.name} p{p}: markers={rec['markers']} issuer={rec['issuer']} title={rec['title']!r}")
    print(f"MARKERS_DONE wrote {dest}")


if __name__ == "__main__":
    main()
