#!/usr/bin/env python3
"""Build an evaluation set from explicit, source-hashed human review labels.

Unlike PDFsam discovery, this accepts reviewed starts directly. Automatic split
filenames and predictions are never treated as reference labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader
from eval_data import link_original
from production_state import atomic_json, file_hash


def build(labels: Path, corpus: Path, output: Path):
    reference = json.loads(labels.read_text(encoding='utf-8'))
    if reference.get('version') != 1 or reference.get('label_status') != 'human_confirmed':
        raise ValueError('Only versioned, human-confirmed review labels may be imported')
    if not reference.get('review_evidence') or not reference.get('files'):
        raise ValueError('Review evidence and a nonempty source list are required')
    gt, metadata = {}, {}
    corpus = corpus.resolve()
    for name, row in reference['files'].items():
        original = (corpus / row['source']).resolve()
        if Path(name).name != name or original.name != name or corpus not in original.parents:
            raise ValueError(f'Invalid source path: {name}')
        if file_hash(original) != row['source_sha256']:
            raise ValueError(f'Reviewed source has changed: {name}')
        total = len(PdfReader(str(original)).pages)
        starts = row['starts']
        if (total < 1 or total != row['total_pages'] or not starts or starts[0] != 1
                or any(type(p) is not int or not 1 <= p <= total for p in starts)
                or starts != sorted(set(starts))):
            raise ValueError(f'Invalid reviewed page boundaries: {name}')
        link = output / name
        if link.exists() and not link.is_symlink():
            raise ValueError(f'Refusing to replace an existing regular file: {link}')
        gt[name] = starts
        metadata[name] = {'source': row['source'], 'sha256': row['source_sha256'],
                          'total_pages': total, 'review_id': row['review_id'], 'case_group': row['case_group']}
    output.mkdir(parents=True, exist_ok=True)
    for name, row in reference['files'].items():
        link_original(corpus / row['source'], output)
    for name, value in [('ground_truth', gt), ('masked', {}),
                        ('strata', {n: 'external_review' for n in gt})]:
        atomic_json(output / (name + '.json'), value)
    if all('existing_automatic_starts' in row for row in reference['files'].values()):
        atomic_json(output / 'existing_automatic_predictions.json', {
            'by_tolerance': {'0': {'per_file': [
                {'file': name, 'pred': sorted(set(row['existing_automatic_starts']) - {1})}
                for name, row in reference['files'].items()]}},
            'provenance': {'kind': 'rescore_existing_user_supplied_automatic_outputs',
                           'model_code_runtime': 'unknown', 'new_inference': False,
                           'human_reference_id': reference['id'],
                           'human_reference_sha256': file_hash(labels)}})
    atomic_json(output / 'dataset.json', {
        'version': 1, 'reference': reference['id'], 'label_status': 'human_confirmed',
        'purpose': reference['purpose'], 'reference_labels_sha256': file_hash(labels),
        'ground_truth_sha256': hashlib.sha256(json.dumps(gt, sort_keys=True).encode()).hexdigest(),
        'files': metadata})
    print(f'{output}: {len(gt)} sources / {sum(r["total_pages"] for r in metadata.values())} pages / '
          f'{sum(len(v) for v in gt.values())} reference documents')
    return gt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels', type=Path, default=Path('data/gergana_review_v1.json'))
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path('eval_gergana'))
    args = parser.parse_args()
    try:
        build(args.labels, args.corpus, args.out)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
