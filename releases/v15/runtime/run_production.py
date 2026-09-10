#!/usr/bin/env python3
"""Boundary-only production splitting with validated resume and per-source manifests.

Usage: python3 run_production.py ROOT [--files shard.txt] [--dpi 150]
Exit 0 means every selected source is complete; failures return 1, input errors 2.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import logging
from pathlib import Path
import shutil
import subprocess
import sys

from production_state import file_hash, is_complete, publish, source_identity, source_lock, state_key
from model_options import add_model_arguments, resolve_model_arguments, load_kwargs


def discover(root: Path, files: Path | None = None) -> list[Path]:
    if not root.is_dir():
        raise ValueError(f"Input directory does not exist: {root}")
    pdfs = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"
                  and "split" not in p.relative_to(root).parts
                  and not any(part.startswith(".") for part in p.relative_to(root).parts))
    if files is None:
        return pdfs
    wanted = {line.strip() for line in files.read_text(encoding="utf-8").splitlines() if line.strip()}
    available = {str(p): p for p in pdfs}
    available.update({str(p.relative_to(root)): p for p in pdfs})
    missing = wanted - available.keys()
    if missing:
        raise ValueError(f"Shard contains unknown PDF paths: {sorted(missing)}")
    return sorted({available[name] for name in wanted})


def runtime_settings(model_path: str, dpi: int, align_confirmation: bool, revision: str | None = None,
                     inference: dict | None = None) -> dict:
    versions = {}
    for package in ("torch", "transformers", "bitsandbytes", "accelerate", "qwen-vl-utils",
                    "tokenizers", "pypdf", "pdf2image", "Pillow", "pytesseract",
                    "torchvision", "huggingface-hub", "safetensors", "numpy", "av", "jinja2"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    root = Path(__file__).parent
    return {"model": model_path, "model_revision": revision, "dpi": dpi, "classify": False,
            "inference": inference or {"backend": "hf"},
            "align_confirmation": align_confirmation, "python": sys.version.split()[0],
            "packages": versions,
            "code": {p: file_hash(root / p) for p in ("split.py", "rotation.py", "production_state.py", "run_production.py",
                                                     "model_options.py", "qwen38_client.py")}}


def preflight() -> None:
    import pytesseract  # Required: otherwise the rotation helper silently abstains.
    for program in ("tesseract", "pdftoppm", "pdfinfo"):
        if shutil.which(program) is None:
            raise RuntimeError(f"Required executable is missing: {program}")
    languages = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, check=True)
    if "osd" not in languages.stdout.split():
        raise RuntimeError("Tesseract's osd language data is missing")


def load_model_for_settings(pipeline,settings,logger):
    if settings.get('boundary_method') in ('features_v6','features_v7b','features_v8b','features_v9','features_v11','features_v11_fast'):
        from labeled_qwen38 import load_model
        return load_model(settings['model'],logger,**load_kwargs(settings))
    return pipeline.load_model(settings['model'],logger,**load_kwargs(settings))


def detect_for_settings(pipeline,pdf,total,bundle,settings,logger,checkpoint_dir,source):
    if settings.get('boundary_method') in ('features_v6','features_v7b','features_v8b','features_v9','features_v11','features_v11_fast'):
        from feature_pipeline import detect
        return detect(pdf,total,*bundle,settings['dpi'],logger,pipeline=pipeline,
                      checkpoint_dir=checkpoint_dir,source=source,settings=settings)
    return pipeline.detect_boundaries(pdf,total,*bundle,settings['dpi'],logger,
                                      classify=False,align_confirmation=settings['align_confirmation'])


def run(pdfs: list[Path], root: Path, pipeline, logger, settings: dict) -> int:
    model_bundle = None
    failed = []
    done = 0
    for i, pdf in enumerate(pdfs, 1):
        output = pdf.parent / "split"
        initialization_failed = False
        try:
            with source_lock(pdf, output):
                source = source_identity(pdf)
                if is_complete(pdf, output, source, settings):
                    done += 1
                    print(f"[{i}/{len(pdfs)}] SKIP (validated): {pdf.relative_to(root)}", flush=True)
                    continue
                total = len(pipeline.PdfReader(str(pdf)).pages)
                if total < 1:
                    raise ValueError(f"Empty source PDF: {pdf}")
                if model_bundle is None:
                    try:
                        preflight()
                        model_bundle = load_model_for_settings(pipeline,settings,logger)
                    except Exception:
                        initialization_failed = True
                        raise
                    logging.disable(logging.NOTSET)
                print(f"[{i}/{len(pdfs)}] {pdf.relative_to(root)}", flush=True)
                boundaries, rotations = detect_for_settings(pipeline,pdf,total,model_bundle,settings,logger,
                    output/'.state'/'feature_seams'/state_key(pdf),source)
                publish(pdf, output, source, settings, total, boundaries, rotations,
                        pipeline.split_pdf, logger, pipeline.CONFIDENCE_THRESHOLD)
                done += 1
        except Exception:
            failed.append(str(pdf.relative_to(root)))
            logger.exception("FAILED %s", pdf)
            if initialization_failed:
                break
        print(f"PROGRESS {done}/{len(pdfs)}", flush=True)
    if done != len(pdfs):
        print(f"PRODUCTION_FAILED {done}/{len(pdfs)}; failed={failed}", flush=True)
        return 1
    print(f"PRODUCTION_DONE {done}/{len(pdfs)}", flush=True)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--dpi", type=int, default=150)
    add_model_arguments(parser)
    parser.add_argument("--files", type=Path, help="Exact relative or absolute paths for this worker")
    parser.add_argument("--align-confirmation", action="store_true",
                        help="Experimental: confirm the relocated seam (requires accuracy comparison)")
    parser.add_argument('--boundary-method',choices=('legacy','features','features-refined','features-facts','archive','archive-context','archive-fast'),default='legacy',
                        help='features: experimental single-request Qwen3.8 detector')
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        selected_model, revision, inference = resolve_model_arguments(args)
        if args.dpi <= 0:
            raise ValueError("DPI must be positive")
        pdfs = discover(root, args.files)
        if not pdfs:
            raise ValueError("No PDFs selected")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    import split
    logger = split.setup_logging(root / "_prod_logs")
    settings = runtime_settings(selected_model, args.dpi, args.align_confirmation, revision, inference)
    if args.boundary_method!='legacy':
        from feature_pipeline import configure
        try:settings=configure(settings,args.boundary_method)
        except ValueError as exc:parser.error(str(exc))
    logger.info("PRODUCTION: %s PDFs under %s @ %s DPI", len(pdfs), root, args.dpi)
    return run(pdfs, root, split, logger, settings)


if __name__ == "__main__":
    sys.exit(main())
