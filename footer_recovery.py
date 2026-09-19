"""Conditional footer OCR with source, rotation, engine and code-bound checkpoints."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from footer_guard import POLICY_VERSION, apply, eligible
from production_state import atomic_json, source_identity


def query(image):
    rows = []
    with tempfile.TemporaryDirectory(prefix='folio-footer-') as temporary:
        path = Path(temporary) / 'footer.png'
        # Same fixed crop as the development study; no case-specific coordinates.
        image.crop((0, int(image.height * .82), image.width, image.height)).save(path)
        for mode in (6, 11):
            try:
                result = subprocess.run(['tesseract', str(path), 'stdout', '-l', 'eng', '--psm', str(mode)],
                                        capture_output=True, text=True, timeout=30,
                                        env=dict(os.environ, OMP_THREAD_LIMIT='1'))
                rows.append(dict(mode=mode, text=result.stdout,
                                 error=(result.stderr or f'exit {result.returncode}') if result.returncode else None))
            except (OSError, subprocess.TimeoutExpired) as exc:
                rows.append(dict(mode=mode, text='', error=str(exc)))
    return rows


def engine_version():
    try:
        return subprocess.check_output(['tesseract', '--version'], text=True, timeout=10).splitlines()[0]
    except (OSError, subprocess.SubprocessError) as exc:
        return 'unavailable: ' + str(exc)


def read_page(pdf, page, *, pipeline, directory, source, settings, rotations, dpi, engine):
    if page not in rotations:
        raise ValueError('Footer OCR requires the actual inferred page rotation')
    identity = dict(source=source, settings=settings, page=page, rotation_ccw=rotations[page], dpi=dpi,
                    engine=engine, language='eng', modes=[6, 11], crop='bottom18percent_fullwidth')
    path = directory / 'footer_ocr' / f'{page:04}.json'
    old = json.loads(path.read_text()) if path.exists() else None
    if old and old['identity'] != identity:
        raise ValueError('Footer OCR checkpoint identity mismatch')
    if old and old['status'] == 'complete':
        return old, True
    record = dict(identity=identity, attempts=(old or {}).get('attempts', 0) + 1,
                  history=[*(old or {}).get('history', []),
                           *([{k: v for k, v in old.items() if k not in ('identity', 'history')}] if old else [])],
                  model_usage=None)
    started = time.monotonic()
    try:
        image = pipeline._load_page(pdf, page, dpi)
        if rotations[page]:
            image = image.rotate(rotations[page], expand=True)
        readings = query(image)
        record.update(readings=readings, status='failed' if any(r['error'] for r in readings) else 'complete')
    except BaseException as exc:
        record.update(status='failed', error=type(exc).__name__ + ': ' + str(exc))
        raise
    finally:
        record['seconds'] = time.monotonic() - started
        atomic_json(path, record)
    return record, False


def recover(pdf, *, decisions, pipeline, directory, source, settings, rotations, dpi):
    pages = sorted({n for p, d in decisions.items() if eligible(d) for n in (int(p) - 1, int(p))})
    if settings.get('footer_evidence_policy') != POLICY_VERSION:
        raise ValueError('Footer policy must be explicit in settings')
    if source_identity(pdf) != source:
        raise ValueError('Source changed before footer OCR')
    started = time.monotonic()
    engine = engine_version() if pages else None
    records, cache_hits = {}, 0
    for page in pages:
        records[page], cached = read_page(pdf, page, pipeline=pipeline, directory=directory,
                                         source=source, settings=settings, rotations=rotations, dpi=dpi, engine=engine)
        cache_hits += cached
    if source_identity(pdf) != source:
        raise ValueError('Source changed during footer OCR')
    result, changes = apply(decisions, records)
    summary = dict(policy=POLICY_VERSION, pages=pages, cache_hits=cache_hits,
                   failed_pages=[p for p, r in records.items() if r['status'] != 'complete'],
                   seconds=time.monotonic() - started, changes=changes,
                   note='Two layouts of the same OCR engine; agreement is not independent evidence.')
    return result, changes, summary
