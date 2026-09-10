#!/usr/bin/env python3
"""Offline scoring of named archive vetoes against a fixed baseline."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import archive_boundary
from production_state import atomic_json, file_hash, state_key
from score_full import load_preds, evaluate


def score(folder, run_dir, baseline_path, rules, allow_partial=False):
    state = json.loads((run_dir/'run.json').read_text())
    gt_all = json.loads((folder/'ground_truth.json').read_text())
    strata_all = json.loads((folder/'strata.json').read_text()) if (folder/'strata.json').exists() else {n:'all' for n in gt_all}
    masked = json.loads((folder/'masked.json').read_text()) if (folder/'masked.json').exists() else {}
    baseline = load_preds(baseline_path)
    gt, strata, totals, base, corrected, changes = {}, {}, {}, {}, {}, []
    for name in state['identity']['sources']:
        pp = run_dir/'predictions'/(state_key(Path(name))+'.json')
        if not pp.exists() or json.loads(pp.read_text())['status'] != 'complete':
            if allow_partial: continue
            raise ValueError('Incomplete source: '+name)
        total = json.loads(pp.read_text())['total_pages']
        gt[name], strata[name], totals[name] = gt_all[name], strata_all[name], total
        base[name] = set(baseline[name]) | {1}
        corrected[name] = set(base[name])
        for right in sorted(base[name]-{1}):
            row = json.loads((run_dir/'seams'/state_key(Path(name))/f'{right:04}.json').read_text())
            if row['status'] != 'complete': raise ValueError('Unresolved seam')
            d = archive_boundary.decision(row['decision'])
            if not d['new_document'] and d['correction'] in rules:
                corrected[name].remove(right)
                changes.append({'file':name,'page':right,'rule':d['correction'],
                                'was_true_boundary':right in gt[name], 'evidence':d['link_evidence']})
    if not gt: raise ValueError('No complete sources')
    return {'partial':len(gt)!=len(state['identity']['sources']), 'files':len(gt), 'pages':sum(totals.values()),
            'rules':sorted(rules),'baseline_sha256':file_hash(baseline_path),
            'ground_truth_sha256':file_hash(folder/'ground_truth.json'),
            'baseline':evaluate(gt,base,masked,strata,totals),
            'corrected':evaluate(gt,corrected,masked,strata,totals),
            'changes':changes, 'predictions':{n:sorted(p) for n,p in corrected.items()}}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder',type=Path);p.add_argument('run_dir',type=Path)
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--rules',nargs='+',choices=sorted(archive_boundary.RULES-{'none'}),required=True)
    p.add_argument('--allow-partial',action='store_true')
    a=p.parse_args();r=score(a.folder,a.run_dir,a.baseline,set(a.rules),a.allow_partial)
    atomic_json(a.output,r)
    print('partial',r['partial'],'files',r['files'],'pages',r['pages'])
    for key in ('baseline','corrected'):
        m=r[key]['by_stratum']['aggregate']
        print(key, 'F1',round(m['f1']*100,4),'TP',m['TP'],'FP',m['FP'],'FN',m['FN'],'exact',m['docs_exact'],'/',m['docs_total'])
    print('vetoes',len(r['changes']),'harmful',sum(c['was_true_boundary'] for c in r['changes']))


if __name__=='__main__':main()
