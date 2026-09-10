#!/usr/bin/env python3
"""Offline measurement of recovery from independent single-page profiles."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from page_profile import decision, additions
from production_state import atomic_json, file_hash, state_key
from score_full import load_preds, evaluate


def score(folder,run_dir,baseline_path,archive_results=None,allow_partial=False,policy='v4',direct_run=None):
    if policy not in ('v4','v4b'):raise ValueError('Unknown profile policy')
    recovery=additions
    if policy=='v4b':
        from profile_policy_v4b import additions as recovery
    state=json.loads((run_dir/'run.json').read_text())
    gt_all=json.loads((folder/'ground_truth.json').read_text())
    strata_all=json.loads((folder/'strata.json').read_text()) if (folder/'strata.json').exists() else {n:'all' for n in gt_all}
    masked=json.loads((folder/'masked.json').read_text()) if (folder/'masked.json').exists() else {}
    baseline=load_preds(baseline_path)
    if direct_run:
        if archive_results:raise ValueError('Choose either a direct run or archive refinement results')
        baseline={}
        for name in state['identity']['sources']:
            path=direct_run/'predictions'/(state_key(Path(name))+'.json')
            if not path.exists() or json.loads(path.read_text())['status']!='complete':
                if allow_partial:continue
                raise ValueError('Incomplete direct source: '+name)
            baseline[name]=set(json.loads(path.read_text())['starts'])
    if archive_results:
        baseline.update({n:set(p) for n,p in json.loads(archive_results.read_text())['predictions'].items()})
    gt,strata,totals,base,corrected,changes={},{},{},{},{},[]
    for name in state['identity']['sources']:
        if name not in baseline:
            if allow_partial:continue
            raise ValueError('Missing predictions: '+name)
        pp=run_dir/'predictions'/(state_key(Path(name))+'.json')
        if not pp.exists() or json.loads(pp.read_text())['status']!='complete':
            if allow_partial:continue
            raise ValueError('Incomplete source: '+name)
        total=json.loads(pp.read_text())['total_pages']
        gt[name],strata[name],totals[name]=gt_all[name],strata_all[name],total
        base[name]=set(baseline[name])|{1};corrected[name]=set(base[name])
        profiles={}
        for page in range(1,total+1):
            row=json.loads((run_dir/'seams'/state_key(Path(name))/f'{page:04}.json').read_text())
            if row['status']!='complete':raise ValueError('Unresolved page')
            profiles[page]=decision(row['decision'])
        for right in range(2,total+1):
            reason=recovery(profiles[right-1],profiles[right])
            if reason and right not in base[name]:
                corrected[name].add(right)
                changes.append({'file':name,'page':right,'reason':reason,'is_true_boundary':right in gt[name],
                                'left':profiles[right-1],'right':profiles[right]})
    if not gt:raise ValueError('No complete sources')
    return {'partial':len(gt)!=len(state['identity']['sources']),'files':len(gt),'pages':sum(totals.values()),
            'policy':policy,'policy_sha256':file_hash(ROOT/('page_profile.py' if policy=='v4' else 'profile_policy_v4b.py')),
            'direct_run_sha256':file_hash(direct_run/'run.json') if direct_run else None,
            'baseline_sha256':file_hash(baseline_path),'archive_results_sha256':file_hash(archive_results) if archive_results else None,
            'ground_truth_sha256':file_hash(folder/'ground_truth.json'),
            'baseline':evaluate(gt,base,masked,strata,totals),'corrected':evaluate(gt,corrected,masked,strata,totals),
            'changes':changes,'predictions':{n:sorted(p) for n,p in corrected.items()}}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder',type=Path);p.add_argument('run_dir',type=Path)
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--archive-results',type=Path);p.add_argument('--allow-partial',action='store_true')
    p.add_argument('--policy',choices=('v4','v4b'),default='v4')
    p.add_argument('--direct-run',type=Path,help='Use completed direct seam predictions as the starting result')
    a=p.parse_args();r=score(a.folder,a.run_dir,a.baseline,a.archive_results,a.allow_partial,a.policy,a.direct_run);atomic_json(a.output,r)
    print('partial',r['partial'],'files',r['files'],'pages',r['pages'])
    for key in ('baseline','corrected'):
        m=r[key]['by_stratum']['aggregate'];print(key,'F1',round(m['f1']*100,4),'TP',m['TP'],'FP',m['FP'],'FN',m['FN'],'exact',m['docs_exact'],'/',m['docs_total'])
    print('additions',len(r['changes']),'harmful',sum(not c['is_true_boundary'] for c in r['changes']))


if __name__=='__main__':main()
