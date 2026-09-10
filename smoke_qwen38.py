#!/usr/bin/env python3
"""Check real three-page image inference before evaluation; never an accuracy score.

Select windows from PDF geometry only, without reading ground-truth labels.
The first eligible PDF and the largest page's window exercise ordinary and large
images. --check validates selection without contacting a server or rendering.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

from pypdf import PdfReader
from model_options import add_model_arguments, resolve_model_arguments, load_kwargs, usage_snapshot
from production_state import atomic_json, file_hash, source_identity, source_lock
from run_production import preflight, runtime_settings


def select_windows(folder):
    first = largest = None
    for pdf in sorted(folder.glob('*.pdf')):
        reader = PdfReader(pdf)
        if len(reader.pages) < 3:
            continue
        if first is None:
            first = {'file': pdf.name, 'pages': [1, 2, 3], 'current_page': 2, 'purpose': 'first_three_page_window'}
        for number, page in enumerate(reader.pages, 1):
            area = float(page.mediabox.width) * float(page.mediabox.height)
            if not math.isfinite(area) or area <= 0:
                raise ValueError(f'Invalid PDF page geometry: {pdf.name} p{number}')
            if largest is None or area > largest[0]:
                center = max(2, min(number, len(reader.pages) - 1))
                largest = (area, {'file': pdf.name, 'pages': [center - 1, center, center + 1],
                    'current_page': center, 'largest_page': number, 'purpose': 'largest_page_window'})
    if first is None:
        raise ValueError('Smoke check needs at least one original PDF with three pages')
    return [first, largest[1]]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, help='Old benchmark originals, normally eval_full')
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--dpi', type=int, default=150)
    parser.add_argument('--check', action='store_true', help='Offline input/manifest check; no rendering or inference')
    add_model_arguments(parser)
    parser.set_defaults(backend='qwen38')
    args = parser.parse_args(argv)
    try:
        if args.dpi <= 0 or args.backend != 'qwen38':
            raise ValueError('This smoke runner requires the Qwen3.8 backend and positive DPI')
        model, revision, inference = resolve_model_arguments(args)
        folder, run_dir = args.folder.resolve(), args.run_dir.resolve()
        windows = select_windows(folder)
        sources = {w['file']: source_identity(folder / w['file']) for w in windows}
        settings = runtime_settings(model, args.dpi, False, revision, inference)
        settings['code']['smoke_qwen38.py'] = file_hash(Path(__file__))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.check:
        print(json.dumps({'offline_check': 'passed', 'windows': windows, 'sources': sources,
                          'thinking': inference['thinking'], 'inference_calls': 0}, indent=2))
        return 0
    import split
    logger = split.setup_logging(run_dir / 'logs')
    identity = {'settings': settings, 'sources': sources, 'windows': windows}
    result = {'version': 1, 'status': 'running', 'identity': identity, 'records': [],
              'meaning': 'Transport, image-memory and final-JSON smoke check only. No accuracy score.'}
    bundle = None
    with source_lock(Path('qwen38_smoke'), run_dir):
        marker = run_dir / 'smoke_results.json'
        if marker.exists():
            prior = json.loads(marker.read_text())
            if prior['identity'] != identity:
                raise ValueError('Smoke settings/sources changed; choose a new --run-dir')
            if prior['status'] == 'complete':
                print(f'Completed smoke check already exists: {marker}')
                return 0
            # Preserve the failed attempt before restarting the two-call check.
            history = run_dir / '.history'
            history.mkdir(exist_ok=True)
            atomic_json(history / (file_hash(marker) + '.json'), prior)
        atomic_json(marker, result)
        try:
            preflight()
            bundle = split.load_model(model, logger, **load_kwargs(settings))
            result['model_details'] = bundle[0].model_details()
            for window in windows:
                images, rotations = [], []
                for page in window['pages']:
                    image = split._load_page(folder / window['file'], page, args.dpi)
                    angle = split._query_rotation(image, page, *bundle, logger)
                    images.append(image.rotate(angle, expand=True) if angle else image)
                    rotations.append(angle)
                decision = split._query_document_end(images, window['pages'], window['current_page'], *bundle, logger)
                raw = bundle[0].last_final_text
                text = split.clean_response(raw)
                data = json.loads(text)
                if (type(data.get('end')) is not bool
                        or type(data.get('confidence')) not in (int, float)
                        or not math.isfinite(data['confidence'])
                        or not isinstance(data.get('signal'), str)
                        or type(data.get('signal_on_page')) is not int
                        or data['signal_on_page'] not in window['pages']):
                    raise ValueError('Smoke response did not follow the document-end schema/window')
                if source_identity(folder / window['file']) != sources[window['file']]:
                    raise ValueError('Source changed during smoke inference')
                result['records'].append({**window, 'rotations': rotations, 'raw_final': raw,
                    'decision': decision, 'image_sizes': [list(image.size) for image in images]})
                result['model_usage'] = usage_snapshot(bundle[0])
                atomic_json(marker, result)
            result['status'] = 'complete'
            atomic_json(marker, result)
        except BaseException:
            result['status'] = 'failed'
            result['model_usage'] = usage_snapshot(bundle[0]) if bundle else None
            atomic_json(marker, result)
            logger.exception('Qwen3.8 smoke check failed; inspect results before evaluation')
            return 1
    print(f'Smoke PASS: {len(result["records"])} three-page queries. See {marker}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
