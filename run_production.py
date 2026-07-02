#!/usr/bin/env python3
"""run_production.py — batch PRODUCTION split over a nested folder tree, ONE model load.

Recursively finds PDFs under <root>, splits each into documents by BOUNDARY DETECTION ONLY
(classify=False — NO Phase-2 classification), output to <pdf.parent>/split/ as
<stem>_NNN_00000_.pdf (code 00000 / no class name, since classification is skipped).
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
    ap.add_argument("--files", default=None,
                    help="path to a text file of PDF paths (relative to root, or absolute); "
                         "process ONLY these. Used to shard the workload across pods.")
    a = ap.parse_args()
    root = Path(a.root).resolve()

    import split  # heavy; pod-only
    logger = split.setup_logging(root / "_prod_logs")
    model, processor, config = split.load_model(split.MODEL_PATH, logger)
    dpi = a.dpi or split.DEFAULT_DPI

    pdfs = sorted(p for p in root.rglob("*.pdf") if "split" not in p.parts)
    if a.files:
        wanted = {ln.strip() for ln in Path(a.files).read_text().splitlines() if ln.strip()}
        before = len(pdfs)
        pdfs = [p for p in pdfs if str(p.relative_to(root)) in wanted or str(p) in wanted]
        logger.info(f"--files {a.files}: sharded to {len(pdfs)} of {before} PDFs")
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
            total = len(split.PdfReader(str(pdf)).pages)
            # BOUNDARY-ONLY: classify=False (no Phase-2 classification)
            boundaries, _rot = split.detect_boundaries(pdf, total, model, processor, config, dpi, logger, classify=False)
            split.split_pdf(pdf, boundaries, out, logger)
            done += 1
        except Exception as e:
            logger.error(f"FAILED {pdf}: {e}", exc_info=True)
        print(f"PROGRESS {done}/{len(pdfs)}", flush=True)
    print(f"PRODUCTION_DONE {done}/{len(pdfs)}", flush=True)


if __name__ == "__main__":
    main()
