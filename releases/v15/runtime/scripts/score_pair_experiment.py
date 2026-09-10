#!/usr/bin/env python3
"""Score direct, conservative-veto and hybrid policies on cached pair decisions.

Only this offline scorer reads labels. Policy sweeps are development analyses;
freeze a selected policy before evaluating another source partition.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from score_full import evaluate,load_preds
from production_state import atomic_json,file_hash,state_key
from pair_boundary import decision


def policies(base,seams):
    yield 'baseline',set(base)|{1}
    for threshold in (0,75,85,95):
        yield f'direct_{threshold}',{1}|{p for p,d in seams.items() if d['new_document'] and d['confidence']>=threshold}
    for categories,label in [({'continuation','attachment','section','form_series'},'all'),
                             ({'attachment','section','form_series'},'structural')]:
        for threshold in (75,85,95):
            removed={p for p,d in seams.items() if not d['new_document'] and d['relationship'] in categories and d['confidence']>=threshold}
            kept=(set(base)|{1})-removed
            yield f'veto_{label}_{threshold}',kept
            for add_threshold in (85,95):
                added={p for p,d in seams.items() if d['new_document'] and d['confidence']>=add_threshold}
                yield f'hybrid_{label}_{threshold}_add{add_threshold}',kept|added


def score(folder,run_dir,baseline_path,allow_partial=False):
    state=json.loads((run_dir/'run.json').read_text())
    selected=list(state['identity']['sources'])
    gt_all=json.loads((folder/'ground_truth.json').read_text())
    strata_all=json.loads((folder/'strata.json').read_text()) if (folder/'strata.json').exists() else {n:'all' for n in gt_all}
    masked=json.loads((folder/'masked.json').read_text()) if (folder/'masked.json').exists() else {}
    base=load_preds(baseline_path)
    gt,strata,totals,outputs={},{},{},{}
    for name in selected:
        path=run_dir/'predictions'/(state_key(Path(name))+'.json')
        if not path.exists() or json.loads(path.read_text())['status']!='complete':
            if allow_partial: continue
            raise ValueError('Incomplete source predictions: '+name)
        row=json.loads(path.read_text()); total=row['total_pages']
        seams={}
        for right in range(2,total+1):
            cached=json.loads((run_dir/'seams'/state_key(Path(name))/f'{right:04}.json').read_text())
            if cached['status']!='complete': raise ValueError('Unresolved seam')
            seams[right]=decision(cached['decision'])
        gt[name]=gt_all[name]; strata[name]=strata_all[name]; totals[name]=total
        for label,pred in policies(base[name],seams): outputs.setdefault(label,{})[name]=pred
    if not gt: raise ValueError('No complete sources')
    report={'partial':len(gt)!=len(selected),'files':len(gt),'pages':sum(totals.values()),
            'variant':state['identity']['settings']['variant'],
            'baseline_sha256':file_hash(baseline_path),'ground_truth_sha256':file_hash(folder/'ground_truth.json'),
            'policies':{label:evaluate(gt,preds,masked,strata,totals) for label,preds in outputs.items()}}
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder',type=Path); p.add_argument('run_dir',type=Path)
    p.add_argument('--baseline',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allow-partial',action='store_true')
    a=p.parse_args(); report=score(a.folder,a.run_dir,a.baseline,a.allow_partial)
    atomic_json(a.output,report)
    print('partial',report['partial'],'files',report['files'],'pages',report['pages'])
    for label,data in sorted(report['policies'].items(),key=lambda item:item[1]['by_stratum']['aggregate']['f1'],reverse=True):
        r=data['by_stratum']['aggregate']
        print(f"{label:32} F1={r['f1']:.4%} TP={r['TP']} FP={r['FP']} FN={r['FN']} exact={r['docs_exact']}/{r['docs_total']}")


if __name__=='__main__': main()
