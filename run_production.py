#!/usr/bin/env python3
"""run_production.py — batch PRODUCTION split over a nested folder tree, ONE model load.

Recursively finds PDFs under <root>, runs split.process_pdf on each (full pipeline: boundary
detection + Phase-2 classification + writes named split PDFs), output to <pdf.parent>/split/.
No ground truth — production output only. Per-PDF RESUME: skips a PDF whose split output already
exists, so a re-launch after an SSH/pod drop continues where it left off.

Usage (pod): python3 run_production.py /root/GIS_Pv [--dpi 150]
"""
import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--dpi", type=int, default=None)
    a = ap.parse_args()
    root = Path(a.root).resolve()

    import split  # heavy; pod-only
    logger = split.setup_logging(root / "_prod_logs")
    model, processor, config = split.load_model(split.MODEL_PATH, logger)
    dpi = a.dpi or split.DEFAULT_DPI

    pdfs = sorted(p for p in root.rglob("*.pdf") if "split" not in p.parts)
    logger.info(f"PRODUCTION: {len(pdfs)} PDFs under {root} @ {dpi} DPI")
    done = 0
    for i, pdf in enumerate(pdfs, 1):
        out = pdf.parent / "split"
        if out.exists() and any(out.glob(f"{pdf.stem}_*.pdf")):   # resume: already produced
            done += 1
            print(f"[{i}/{len(pdfs)}] SKIP (done): {pdf.relative_to(root)}", flush=True)
            continue
        print(f"[{i}/{len(pdfs)}] {pdf.relative_to(root)}", flush=True)
        try:
            split.process_pdf(pdf, out, model, processor, config, dpi, logger)
            done += 1
        except Exception as e:
            logger.error(f"FAILED {pdf}: {e}", exc_info=True)
        print(f"PROGRESS {done}/{len(pdfs)}", flush=True)
    print(f"PRODUCTION_DONE {done}/{len(pdfs)}", flush=True)


if __name__ == "__main__":
    main()
