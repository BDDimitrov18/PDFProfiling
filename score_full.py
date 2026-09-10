#!/usr/bin/env python3
"""Score complete cached predictions against CURRENT labels, with strata and gap masks.

Usage: python score_full.py eval_full logs/fulltests_stage2.log [--json report.json]
Accepts detection logs or eval_results.json. Page 1 is not a scored cut.
Exact-document recovery requires both endpoints and no spurious interior cut;
documents touching unresolved masked seams are excluded from that metric.
"""
import argparse
import json
import re
from pathlib import Path
from pypdf import PdfReader
from production_state import atomic_json, file_hash


def load_preds(logpath):
    path = Path(logpath)
    if path.suffix.lower() == '.json':
        data = json.loads(path.read_text(encoding='utf-8'))
        rows = next(iter(data['by_tolerance'].values()))['per_file']
        if len({r['file'] for r in rows}) != len(rows):
            raise ValueError('Duplicate predictions in results JSON')
        return {r['file']: set(r['pred']) for r in rows}
    preds, cur = {}, None
    for line in path.read_text(errors='replace').splitlines():
        s = line.strip()
        if s.endswith('.pdf'):
            cur = s
        else:
            m = re.search(r'pred=\[([^\]]*)\]', line)
            if m and cur:
                if cur in preds:
                    raise ValueError(f'Duplicate prediction block: {cur}; use one complete run')
                preds[cur] = {int(x) for x in m.group(1).split(',') if x.strip()}
    return preds


def masked_pages(ranges):
    return {p for lo, hi in ranges for p in range(lo, hi + 1)}


def score_stratum(files, gt, preds, masked, strata, stratum):
    TP = FP = FN = 0
    rows = []
    for f in sorted(files):
        if strata.get(f) != stratum:
            continue
        mp = masked_pages(masked.get(f, []))
        true = set(gt[f]) - {1} - mp
        pred = set(preds[f]) - {1} - mp
        fp, fn = sorted(pred - true), sorted(true - pred)
        TP += len(true & pred); FP += len(fp); FN += len(fn)
        rows.append((f, fp, fn))
    P = TP / (TP + FP) if TP + FP else 0.0
    R = TP / (TP + FN) if TP + FN else 0.0
    F1 = 2 * P * R / (P + R) if P + R else 0.0
    return TP, FP, FN, P, R, F1, rows


def document_intervals(starts, total):
    pages = sorted(set(starts) | {1})
    return set(zip(pages, pages[1:] + [total + 1]))


def evaluate(gt, preds, masked, strata, totals):
    missing, extra = set(gt) - set(preds), set(preds) - set(gt)
    if missing or extra:
        raise ValueError(f'Prediction coverage mismatch: missing={sorted(missing)}, extra={sorted(extra)}')
    if not gt or set(strata) != set(gt) or set(totals) != set(gt):
        raise ValueError('Labels, strata and source page counts must cover the same nonempty dataset')
    rows = []
    for name, true in gt.items():
        total = totals[name]
        pred = preds[name]
        if (total < 1 or not true or true != sorted(set(true)) or true[0] != 1
                or any(type(p) is not int or not 1 <= p <= total for p in list(true) + list(pred))):
            raise ValueError(f'Invalid start page or source page count: {name}')
        mp = masked_pages(masked.get(name, []))
        docs = document_intervals(true, total)
        eligible = {(a, b) for a, b in docs if not any(a <= p <= b for p in mp)}
        exact = len(eligible & document_intervals(pred, total))
        rows.append({'file': name, 'stratum': strata[name], 'docs_exact': exact,
                     'docs_total': len(eligible), 'docs_excluded': len(docs) - len(eligible),
                     'source_exact': set(true) == (set(pred) | {1})})
    groups = {}
    for group in sorted(set(strata.values())) + ['aggregate']:
        membership = strata if group != 'aggregate' else {n: group for n in gt}
        TP, FP, FN, P, R, F1, errors = score_stratum(gt, gt, preds, masked, membership, group)
        selected = [r for r in rows if group == 'aggregate' or r['stratum'] == group]
        groups[group] = {'files': len(selected), 'TP': TP, 'FP': FP, 'FN': FN,
                         'precision': P, 'recall': R, 'f1': F1,
                         **{k: sum(r[k] for r in selected) for k in ('docs_exact', 'docs_total', 'docs_excluded', 'source_exact')},
                         'errors': [{'file': n, 'fp': fp, 'fn': fn} for n, fp, fn in errors]}
    return {'by_stratum': groups, 'per_file': rows}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('folder', type=Path)
    ap.add_argument('predictions', type=Path)
    ap.add_argument('--json', type=Path, dest='output')
    args = ap.parse_args(argv)
    folder = args.folder
    gt = json.loads((folder / 'ground_truth.json').read_text(encoding='utf-8'))
    masked = json.loads((folder / 'masked.json').read_text()) if (folder / 'masked.json').exists() else {}
    strata = json.loads((folder / 'strata.json').read_text()) if (folder / 'strata.json').exists() else {n: 'all' for n in gt}
    try:
        totals = {n: len(PdfReader(str(folder / n)).pages) for n in gt}
        report = evaluate(gt, load_preds(args.predictions), masked, strata, totals)
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    report['inputs'] = {'predictions_sha256': file_hash(args.predictions),
                        'ground_truth_sha256': file_hash(folder / 'ground_truth.json')}
    for name, result in report['by_stratum'].items():
        print(f"\n{name}: {result['files']} files; TP={result['TP']} FP={result['FP']} FN={result['FN']} "
              f"P={result['precision']:.2%} R={result['recall']:.2%} F1={result['f1']:.2%}")
        print(f"Exact documents: {result['docs_exact']}/{result['docs_total']} "
              f"({result['docs_excluded']} excluded at unresolved gaps)")
        if name != 'aggregate':
            for row in result['errors']:
                if row['fp'] or row['fn']:
                    print(f"  {row['file']}: FP={row['fp']} FN={row['fn']}")
    if args.output:
        atomic_json(args.output, report)
        print(f'Written: {args.output}')


if __name__ == '__main__':
    main()
