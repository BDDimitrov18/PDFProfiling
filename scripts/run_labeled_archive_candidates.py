#!/usr/bin/env python3
"""Narrow archive verification only at fixed baseline candidate cuts.

Source lists contain only basenames. This runner never reads ground-truth labels.
Failed seams are recorded and retried once after other seams; unresolved failures
make the run incomplete. Interrupted runs reuse only identity-matched checkpoints.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pypdf import PdfReader
from labeled_qwen38 import load_model as load_labeled_model
import archive_boundary as pair_boundary
from model_options import add_model_arguments, resolve_model_arguments, load_kwargs, usage_snapshot, usage_delta
from production_state import atomic_json, file_hash, source_identity, source_lock, state_key
from run_production import runtime_settings, preflight


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder', type=Path)
    p.add_argument('--sources', type=Path, required=True)
    p.add_argument('--variant', choices=('typed_v3',), required=True)
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--dpi', type=int, default=150)
    p.add_argument('--greedy', action='store_true', help='Experimental: temperature 0, top-k 1, no presence penalty')
    p.add_argument('--baseline', type=Path, required=True, help='Saved predictions, never ground-truth labels')
    add_model_arguments(p)
    p.set_defaults(backend='qwen38', thinking='off', request_timeout=600)
    args = p.parse_args(argv)
    folder, run_dir = args.folder.resolve(), args.run_dir.resolve()
    names = json.loads(args.sources.read_text())
    if not isinstance(names,list) or not names or len(set(names)) != len(names) or any(
            type(n) is not str or Path(n).name != n or not n.endswith('.pdf') for n in names):
        raise ValueError('Expected a nonempty unique PDF basename list')
    model, revision, inference = resolve_model_arguments(args)
    inference['experimental_greedy'] = args.greedy
    if inference['backend'] != 'qwen38' or inference['thinking'] != 'off':
        raise ValueError('Pair experiment uses the Qwen3.8 thinking-off backend')
    settings = runtime_settings(model,args.dpi,False,revision,inference)
    settings['variant'] = args.variant
    settings['input_image_labels'] = 'positional_v1'
    from score_full import load_preds
    candidate_starts = load_preds(args.baseline)
    if any(n not in candidate_starts for n in names): raise ValueError('Missing baseline source')
    settings['candidate_predictions_sha256'] = file_hash(args.baseline)
    settings['code'].update({name:file_hash(ROOT/name) for name in ('archive_boundary.py','labeled_qwen38.py','scripts/run_labeled_archive_candidates.py')})
    sources = {n:source_identity(folder/n) for n in names}
    identity = {'settings':settings,'sources':sources}
    with source_lock(Path('archive_experiment'),run_dir):
        marker = run_dir/'run.json'
        prior = json.loads(marker.read_text()) if marker.exists() else None
        if prior and prior['identity'] != identity:
            raise ValueError('Inputs or settings changed; use a new run directory')
        state = {'status':'running','identity':identity,'started_at':datetime.now(timezone.utc).isoformat(),
                 'files':{},'failures':[]}
        atomic_json(marker,state)
        import split
        logger = split.setup_logging(run_dir/'logs')
        bundle = None
        try:
            preflight()
            bundle = load_labeled_model(model,logger,**load_kwargs(settings))
            for name in names:
                pdf = folder/name
                total = len(PdfReader(pdf).pages)
                pages, rotations, records = {}, {}, {}
                def ensure(page):
                    if page not in pages:
                        image = split._load_page(pdf,page,args.dpi)
                        angle = split._query_rotation(image,page,*bundle,logger)
                        rotations[page] = angle
                        pages[page] = image.rotate(angle,expand=True) if angle else image
                    return pages[page]
                def run_seam(right):
                    key = {'source':sources[name],'settings':settings,'right_page':right}
                    path = run_dir/'seams'/state_key(pdf)/f'{right:04}.json'
                    if path.exists():
                        old = json.loads(path.read_text())
                        if old['identity'] != key:
                            raise ValueError('Seam checkpoint identity mismatch')
                        if old['status'] == 'complete':
                            pair_boundary.decision(old['decision'])
                            records[right] = old
                            return True
                    images = [ensure(right-1),ensure(right)]
                    started = time.monotonic(); before = usage_snapshot(bundle[0])
                    history = []
                    if path.exists():
                        history = [*old.get('history',[]),{k:v for k,v in old.items() if k not in ('identity','history')}]
                    record = {'identity':key,'rotations':{str(i):rotations[i] for i in (right-1,right)},'history':history,
                              'status':'running','attempts':(old.get('attempts',0) if path.exists() else 0)+1}
                    try:
                        raw = split._infer(pair_boundary.prompt(args.variant,right-1,right),images,*bundle,logger,
                                           max_tokens=300,response_schema=pair_boundary.SCHEMA)
                        data = pair_boundary.decision(json.loads(split.clean_response(raw)))
                        record.update(status='complete',decision=data,raw_final=raw)
                    except Exception as exc:
                        record.update(status='failed',error=type(exc).__name__+': '+str(exc))
                        logger.warning('PAIR FAILED %s p%d: %s',name,right,record['error'])
                    record.update(seconds=time.monotonic()-started,model_usage=usage_delta(before,usage_snapshot(bundle[0])))
                    atomic_json(path,record)
                    records[right] = record
                    for page in list(pages):
                        if page < right-1: del pages[page]
                    return record['status']=='complete'
                failed = []
                if any(type(p) is not int or not 1 <= p <= total for p in candidate_starts[name]):
                    raise ValueError('Invalid candidate page')
                for right in sorted(set(candidate_starts[name])-{1}):
                    if not run_seam(right): failed.append(right)
                    if right%10 == 0 or right == total:
                        print(f'PROGRESS {name} {right}/{total} failed={len(failed)}',flush=True)
                        state['files'][name]={'pages':total,'seams_done':len(records),'failed':failed}
                        atomic_json(marker,state)
                for right in failed: run_seam(right)
                unresolved = [p for p,r in records.items() if r['status']!='complete']
                if source_identity(pdf)!=sources[name]: raise ValueError('Source changed during inference')
                state['files'][name]={'pages':total,'seams_done':len(records),'failed':unresolved}
                state['failures'].extend({'file':name,'page':p} for p in unresolved)
                starts = [1]+[p for p,r in sorted(records.items()) if r['status']=='complete' and r['decision']['new_document']]
                atomic_json(run_dir/'predictions'/(state_key(pdf)+'.json'),{
                    'status':'incomplete' if unresolved else 'complete','identity':{'source':sources[name],'settings':settings},
                    'starts':starts,'total_pages':total,'seconds':sum(r.get('seconds',0) for r in records.values()),
                    'unresolved_pages':unresolved})
                atomic_json(marker,state)
            state['status'] = 'incomplete' if state['failures'] else 'complete'
        except BaseException as exc:
            state.update(status='interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed',error=type(exc).__name__+': '+str(exc))
            raise
        finally:
            state['finished_at']=datetime.now(timezone.utc).isoformat()
            state['model_usage']=usage_snapshot(bundle[0]) if bundle else None
            atomic_json(marker,state)
        return 0 if state['status']=='complete' else 1


if __name__=='__main__':
    raise SystemExit(main())
