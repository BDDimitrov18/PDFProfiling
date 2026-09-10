#!/usr/bin/env python3
"""Audit the page pair used by low-confidence confirmation in historical detector logs.

This reconstructs the proposed seam at confirmation time; it does not predict how
an alternative model call would answer. A final-page projection is reported as
out of range, since the candidate resolves that projection before confirmation.
"""
import argparse
import re
from pathlib import Path
from production_state import atomic_json, file_hash

START_SIGNALS = {'titled_id_header', 'fresh_letterhead', 'header_block_reset',
                 'appendix_heading', 'blank_form', 'page_number_reset', 'stamp_change'}


def audit(path):
    events, pending = [], []
    current = None
    total = None
    files = []
    for number, line in enumerate(Path(path).read_text(errors='replace').splitlines(), 1):
        phase = re.search(r'Phase 1: end-of-document detection \((\d+) pages\)', line)
        if phase:
            if pending:
                raise ValueError('Unattributed confirmations before next PDF; log format is incomplete')
            total, current = int(phase[1]), None
        result = re.search(r'p(\d+): end=True, signal=(\w+), signal_on_page=(\d+)', line)
        if result:
            n, signal, page = int(result[1]), result[2], int(result[3])
            current = {'iteration': n, 'signal': signal, 'effective_end': page - int(signal in START_SIGNALS)}
        corrected = re.search(r'boundary corrected to p(\d+)', line)
        if corrected and current:
            current['effective_end'] = int(corrected[1])
        confirm = re.search(r'Low-conf boundary at p(\d+)', line)
        if confirm:
            if not current or current['iteration'] != int(confirm[1]) or total is None:
                raise ValueError(f'Cannot reconstruct confirmation at line {number}')
            end, n = current['effective_end'], current['iteration']
            pending.append({**current, 'log_line': number, 'legacy_pair': [n, n + 1],
                            'actual_pair': [end, end + 1] if 1 <= end < total else None,
                            'same_pair': end == n, 'legacy_confirmed': 'confirmed —' in line})
        if re.fullmatch(r'Image_.*\.pdf', line.strip()):
            name = line.strip()
            if name in files:
                raise ValueError(f'Duplicate source in log: {name}')
            files.append(name)
            events.extend({'file': name, **e} for e in pending)
            pending, current = [], None
    if pending:
        raise ValueError('Trailing confirmations have no source filename; log may be interrupted')
    return {'log': str(path), 'log_sha256': file_hash(Path(path)), 'files': len(files),
            'confirmations': len(events), 'same_pair': sum(e['same_pair'] for e in events),
            'relocated_in_range': sum(not e['same_pair'] and e['actual_pair'] is not None for e in events),
            'out_of_range': sum(e['actual_pair'] is None for e in events), 'events': events}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('log', type=Path)
    ap.add_argument('--json', type=Path, dest='output')
    args = ap.parse_args()
    result = audit(args.log)
    print({k: v for k, v in result.items() if k != 'events'})
    for event in result['events']:
        if not event['same_pair']:
            print(event)
    if args.output:
        atomic_json(args.output, result)


if __name__ == '__main__':
    main()
