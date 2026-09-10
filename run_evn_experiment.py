#!/usr/bin/env python3
"""Frozen EVN probe and paired post-processing evaluation; never changes production.

Run 'probe' first. 'apply' reads a completed current-environment baseline from
 eval_boundaries.py and transcribes only its proposed starts, excluding page 1.
Every page is checkpointed; inference errors fail the run, uncertain text keeps cuts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time

from pypdf import PdfReader
from eval_boundaries import model_details
from evn_sections import parse_evidence, should_suppress, transcription_prompt
from production_state import atomic_json, file_hash, source_identity, source_lock, state_key
from run_production import runtime_settings, preflight
from score_full import evaluate


def valid_seconds(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def experiment_settings(model, dpi, revision):
    settings = runtime_settings(model, dpi, False, revision)
    for name in ('eval_boundaries.py', 'evn_sections.py', 'run_evn_experiment.py'):
        settings['code'][name] = file_hash(Path(__file__).parent / name)
    return settings


def probe_requests(folder, spec):
    if spec.get('version') != 1 or not spec.get('cases'):
        raise ValueError('Expected a nonempty versioned probe specification')
    sources = {}
    for name, row in spec['sources'].items():
        if Path(name).name != name:
            raise ValueError('Probe source must be a basename')
        pdf = folder / name
        identity = source_identity(pdf)
        if identity['sha256'] != row['sha256'] or len(PdfReader(pdf).pages) != row['total_pages']:
            raise ValueError(f'Probe source changed: {name}')
        sources[name] = identity
    requests = []
    for case in spec['cases']:
        name, page = case['file'], case['page']
        if (name not in sources or type(page) is not int or not 1 <= page <= spec['sources'][name]['total_pages']
                or case['expected_action'] not in ('keep', 'suppress', 'observe')):
            raise ValueError('Invalid frozen probe request')
        requests.append({'file': name, 'page': page, 'rotation': None})
    if len({(r['file'], r['page']) for r in requests}) != len(requests):
        raise ValueError('Probe repeats a page')
    return requests, sources


def load_baseline(folder, directory, settings):
    manifest = json.loads((directory / 'run.json').read_text())
    expected = {**settings, 'code': {k: v for k, v in settings['code'].items()
                                   if k not in ('evn_sections.py', 'run_evn_experiment.py')}}
    if manifest['status'] != 'complete' or manifest['identity']['settings'] != expected:
        raise ValueError('Baseline is incomplete or has different code/runtime/model/DPI; rerun it first')
    gt = json.loads((folder / 'ground_truth.json').read_text())
    if not gt or any(Path(n).name != n for n in gt):
        raise ValueError('Ground truth must list source basenames')
    sources = {n: source_identity(folder / n) for n in gt}
    if sources != manifest['identity']['sources']:
        raise ValueError('Baseline source bytes or coverage differ from this dataset')
    predictions, totals, requests, seconds = {}, {}, [], 0.0
    for name in gt:
        pdf = folder / name
        cached = json.loads((directory / 'predictions' / (state_key(pdf) + '.json')).read_text())
        if cached['identity'] != {'source': sources[name], 'settings': expected}:
            raise ValueError(f'Baseline checkpoint identity mismatch: {name}')
        total = len(PdfReader(pdf).pages)
        starts = cached['starts']
        if (total != cached['total_pages'] or not starts or starts[0] != 1
                or any(type(p) is not int or not 1 <= p <= total for p in starts)
                or starts != sorted(set(starts))):
            raise ValueError(f'Invalid baseline checkpoint: {name}')
        predictions[name] = set(starts) - {1}
        totals[name] = total
        if not valid_seconds(cached['seconds']):
            raise ValueError(f'Invalid baseline timing: {name}')
        seconds += cached['seconds']
        rotations = cached['rotations_ccw_for_inference']
        if not isinstance(rotations, dict) or any(type(v) is not int or v not in (0, 90, 180, 270)
                                                 for v in rotations.values()):
            raise ValueError(f'Invalid baseline rotations: {name}')
        requests.extend({'file': name, 'page': p, 'rotation': rotations.get(str(p), 0)}
                        for p in starts if p != 1)
    return predictions, totals, requests, sources, manifest, seconds


def extract_pages(folder, requests, sources, settings, run_dir, provenance, pipeline, logger,
                  required_model_details=None):
    """One writer, source-hashed page checkpoints, no GPU load for completed caches."""
    identity = {'settings': settings, 'sources': sources, 'requests': requests, 'provenance': provenance}
    marker = run_dir / 'run.json'
    with source_lock(Path('evn_extraction'), run_dir):
        previous = json.loads(marker.read_text()) if marker.exists() else None
        if previous and previous['identity'] != identity:
            raise ValueError('Experiment inputs/code changed; use a new --run-dir')
        if (previous and required_model_details is not None
                and previous.get('model_details') not in (None, required_model_details)):
            raise ValueError('Cached model/GPU differs from the required baseline')
        manifest = {'version': 1, 'status': 'running', 'identity': identity,
                    'model_details': (previous.get('model_details') if previous else None) or required_model_details}
        atomic_json(marker, manifest)
        bundle, records = None, []
        try:
            for request in requests:
                name, page = request['file'], request['page']
                key = hashlib.sha256(f'{name}:{page}'.encode()).hexdigest()[:24]
                path = run_dir / 'pages' / (key + '.json')
                cache_id = {'settings': settings, 'source': sources[name], 'request': request}
                if path.exists():
                    record = json.loads(path.read_text())
                    if (record.get('version') != 1 or record['identity'] != cache_id or type(record['raw']) is not str
                            or record.get('file') != name or record.get('page') != page
                            or type(record.get('page')) is not int
                            or type(record.get('rotation')) is not int or record['rotation'] not in (0, 90, 180, 270)
                            or (request['rotation'] is not None and record['rotation'] != request['rotation'])
                            or not valid_seconds(record.get('seconds')) or type(record.get('model_calls')) is not int
                            or record['model_calls'] != 1 or manifest['model_details'] is None):
                        raise ValueError(f'Invalid or stale extraction checkpoint: {name} p{page}')
                else:
                    if bundle is None:
                        preflight()
                        bundle = pipeline.load_model(settings['model'], logger, revision=settings['model_revision'])
                        details = model_details(bundle[0])
                        if manifest['model_details'] is not None and manifest['model_details'] != details:
                            raise ValueError('Model revision/GPU differs from the baseline or prior extraction')
                        manifest['model_details'] = details
                        atomic_json(marker, manifest)
                    started = time.monotonic()
                    img = pipeline._load_page(folder / name, page, settings['dpi'])
                    rotation = request['rotation']
                    if rotation is None:
                        rotation = pipeline._query_rotation(img, page, *bundle, logger)
                    if type(rotation) is not int or rotation not in (0, 90, 180, 270):
                        raise ValueError('Invalid rotation angle')
                    if rotation:
                        img = img.rotate(rotation, expand=True)
                    raw = pipeline._infer(transcription_prompt(page), [img], *bundle, logger, max_tokens=220)
                    if type(raw) is not str:
                        raise RuntimeError('Inference returned no transcription')
                    if source_identity(folder / name) != sources[name]:
                        raise ValueError(f'Source changed during extraction: {name}')
                    record = {'version': 1, 'identity': cache_id, 'file': name, 'page': page,
                              'rotation': rotation, 'raw': raw, 'seconds': time.monotonic() - started,
                              'model_calls': 1}
                    atomic_json(path, record)
                evidence = parse_evidence(record['raw'])
                record = {**record, 'evidence': evidence, 'action': 'suppress' if should_suppress(evidence) else 'keep'}
                records.append(record)
                logger.info('EVN %s p%s: %s (%s)', name, page, record['action'], evidence['reason'])
            manifest['status'] = 'complete'
            manifest['page_count'] = len(records)
            atomic_json(marker, manifest)
        except BaseException:
            manifest['status'] = 'failed'
            atomic_json(marker, manifest)
            raise
    return records


def summarize_probe(spec, records):
    lookup = {(r['file'], r['page']): r for r in records}
    expected_keys = {(c['file'], c['page']) for c in spec['cases']}
    if set(lookup) != expected_keys or len(records) != len(expected_keys):
        raise ValueError('Probe results do not cover the frozen requests exactly')
    checks = []
    for case in spec['cases']:
        record = lookup[(case['file'], case['page'])]
        checks.append({'file': case['file'], 'page': case['page'], 'expected': case['expected_action'],
                       'actual': record['action'], 'passed': case['expected_action'] == 'observe' or record['action'] == case['expected_action'],
                       'evidence': record['evidence']})
    invalid = [r for r in records if r['evidence']['status'] == 'abstain'
               and r['evidence']['reason'] != 'title or issuer is absent or unreadable']
    return {'probe_id': spec['id'], 'passed': all(c['passed'] for c in checks) and not invalid,
            'checks': checks, 'invalid_transcriptions': len(invalid),
            'model_calls': sum(r['model_calls'] for r in records),
            'seconds': sum(r['seconds'] for r in records),
            'meaning': 'Extraction/decision probe only; passing does not establish improved document accuracy.'}


def compare_predictions(gt, baseline, totals, masked, strata, records, baseline_seconds):
    candidate = {n: set(pages) for n, pages in baseline.items()}
    expected = {(n, p) for n, pages in baseline.items() for p in pages}
    if {(r['file'], r['page']) for r in records} != expected or len(records) != len(expected):
        raise ValueError('Extraction must cover every proposed cut exactly once')
    changes = []
    for record in records:
        n, p = record['file'], record['page']
        if p == 1:
            raise ValueError('Mandatory page 1 may never be removed')
        if record['action'] not in ('keep', 'suppress'):
            raise ValueError('Unknown extraction action')
        if record['action'] == 'suppress':
            candidate[n].remove(p)
            changes.append({'file': n, 'page': p, 'true_start': p in gt[n], 'evidence': record['evidence']})
    base = evaluate(gt, baseline, masked, strata, totals)
    result = evaluate(gt, candidate, masked, strata, totals)
    a, b = base['by_stratum']['aggregate'], result['by_stratum']['aggregate']
    extra_seconds = sum(r['seconds'] for r in records)
    report = {'baseline': base, 'candidate': result, 'changed_starts': changes,
              'f1_delta': b['f1'] - a['f1'], 'exact_documents_delta': b['docs_exact'] - a['docs_exact'],
              'baseline_seconds': baseline_seconds, 'extra_seconds': extra_seconds,
              'overhead_fraction': extra_seconds / baseline_seconds if baseline_seconds else None,
              'extra_model_calls': len(records), 'promotion_ready': False,
              'timing_scope': 'Successful page/PDF processing, including rendering and source verification; excludes model loading and failed attempts. Cached work retains original durations. Not total pod billing time.',
              'meaning': 'Paired predictions on one dataset; adoption still requires all frozen validation and cost gates.'}
    return candidate, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('probe', 'apply'))
    parser.add_argument('folder', type=Path)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--spec', type=Path, default=Path('data/evn_probe_v1.json'))
    parser.add_argument('--baseline-dir', type=Path)
    parser.add_argument('--model', default='Qwen/Qwen2.5-VL-32B-Instruct')
    parser.add_argument('--revision', required=True, help='Exact 40-character model/processor commit SHA')
    parser.add_argument('--dpi', type=int, default=150)
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[0-9a-f]{40}', args.revision) or args.dpi <= 0:
        parser.error('Use an exact lowercase commit SHA and positive DPI')
    folder, run_dir = args.folder.resolve(), args.run_dir.resolve()
    settings = experiment_settings(args.model, args.dpi, args.revision)
    import split
    logger = split.setup_logging(run_dir / 'logs')
    try:
        required_details = None
        if args.mode == 'probe':
            spec = json.loads(args.spec.read_text())
            requests, sources = probe_requests(folder, spec)
            provenance = {'probe_sha256': file_hash(args.spec)}
        else:
            if args.baseline_dir is None:
                parser.error('apply requires --baseline-dir from a complete eval_boundaries.py run')
            baseline, totals, requests, sources, prior, seconds = load_baseline(folder, args.baseline_dir, settings)
            required_details = prior['model_details']
            if required_details is None:
                raise ValueError('Baseline must record its model/GPU details')
            provenance = {'baseline_run_sha256': file_hash(args.baseline_dir / 'run.json')}
            gt = json.loads((folder / 'ground_truth.json').read_text())
            masked = json.loads((folder / 'masked.json').read_text()) if (folder / 'masked.json').exists() else {}
            strata = json.loads((folder / 'strata.json').read_text()) if (folder / 'strata.json').exists() else {n: 'all' for n in gt}
            evaluate(gt, baseline, masked, strata, totals)  # Validate labels/masks before spending GPU time.
        records = extract_pages(folder, requests, sources, settings, run_dir, provenance, split, logger, required_details)
        if args.mode == 'probe':
            result = summarize_probe(spec, records)
            atomic_json(run_dir / 'probe_results.json', result)
            print(f"Probe {'PASS' if result['passed'] else 'FAIL'}: {len(result['checks'])} checks, "
                  f"{result['invalid_transcriptions']} invalid transcriptions. See {run_dir / 'probe_results.json'}")
            return 0 if result['passed'] else 1
        candidate, report = compare_predictions(gt, baseline, totals, masked, strata, records, seconds)
        atomic_json(run_dir / 'comparison.json', report)
        atomic_json(run_dir / 'eval_results.json', {
            'by_tolerance': {'0': {'per_file': [{'file': n, 'pred': sorted(p)} for n, p in candidate.items()]}},
            'strict_report': report['candidate'], 'baseline_run': str(args.baseline_dir),
            'experiment': 'evn_sections', 'production_default': False})
        print(f"Changed cuts: {len(report['changed_starts'])}; F1 delta={report['f1_delta']:+.2%}; "
              f"exact documents delta={report['exact_documents_delta']:+d}. See {run_dir / 'comparison.json'}")
        return 0
    except Exception:
        logger.exception('EVN experiment incomplete; completed page checkpoints are retained')
        return 1


if __name__ == '__main__':
    sys.exit(main())
