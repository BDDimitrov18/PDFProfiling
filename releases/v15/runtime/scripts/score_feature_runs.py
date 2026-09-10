#!/usr/bin/env python3
"""Compare disjoint feature-run predictions with baselines on identical sources."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from production_state import atomic_json,file_hash,state_key
from score_full import evaluate,load_preds


def score(folder,runs,baselines,allow_partial=False,base_runs=None,fact_policy=False,postal_policy=False,plot_runs=None):
    all_gt=json.loads((folder/'ground_truth.json').read_text())
    all_strata=json.loads((folder/'strata.json').read_text()) if (folder/'strata.json').exists() else {n:'all' for n in all_gt}
    masked=json.loads((folder/'masked.json').read_text()) if (folder/'masked.json').exists() else {}
    preds,totals,selected,run_info={},{},set(),[]
    if base_runs and len(base_runs)!=len(runs):raise ValueError('One guard base per run is required')
    guard_changes=[];fact_changes=[];postal_changes=[];identities={};plot_changes=[]
    for run_index,root in enumerate(runs):
        state=json.loads((root/'run.json').read_text());names=state['identity']['sources']
        if selected&set(names):raise ValueError('Duplicate source coverage across runs')
        selected.update(names)
        for n,source in names.items():
            p=root/'predictions'/(state_key(Path(n))+'.json')
            row=json.loads(p.read_text()) if p.exists() else None
            if not row or row['status']!='complete':
                if allow_partial:continue
                raise ValueError('Incomplete predictions: '+n)
            if row['identity']['source']!=source:raise ValueError('Source identity mismatch')
            preds[n]=set(row['starts']);totals[n]=row['total_pages'];identities[n]=source
            if base_runs:
                from refinement_policy import choose
                starts={1}
                for page in range(2,row['total_pages']+1):
                    relative=Path('seams')/state_key(Path(n))/f'{page:04}.json'
                    base=json.loads((base_runs[run_index]/relative).read_text())
                    proposed=json.loads((root/relative).read_text())
                    if any(d['status']!='complete' or d['identity']['source']!=source for d in (base,proposed)):
                        raise ValueError('Incomplete/mismatched guard seam')
                    final=choose(base['decision'],proposed['decision'])
                    if final['new_document']:starts.add(page)
                    if final['new_document']!=proposed['decision']['new_document']:
                        guard_changes.append({'file':n,'page':page,'policy':final['refinement_policy']})
                preds[n]=starts
            if fact_policy:
                from boundary_fact_policy import recover_decision
                starts={1}
                for page in range(2,row['total_pages']+1):
                    cached=json.loads((root/'seams'/state_key(Path(n))/f'{page:04}.json').read_text())
                    if cached['status']!='complete':raise ValueError('Incomplete facts seam')
                    final=recover_decision(cached['decision'],cached['facts']) if cached.get('facts') else cached['decision']
                    if final['new_document']:starts.add(page)
                    if final['new_document']!=cached['decision']['new_document']:
                        fact_changes.append({'file':n,'page':page,'rule':final['fact_recovery']})
                preds[n]=starts
            if postal_policy:
                from filing_unit_policy import apply
                decisions={page:json.loads((root/'seams'/state_key(Path(n))/f'{page:04}.json').read_text())['decision']
                           for page in range(2,row['total_pages']+1)}
                # Retain earlier selected fact-policy cuts before applying postal rules.
                for page,d in decisions.items():d['new_document']=page in preds[n]
                final=apply(decisions)
                for page,d in final.items():
                    if d['new_document']!=decisions[page]['new_document']:
                        postal_changes.append({'file':n,'page':page,'rule':d['filing_unit_rule']})
                preds[n]={1}|{p for p,d in final.items() if d['new_document']}
        elapsed=None
        if state.get('finished_at'):elapsed=(datetime.fromisoformat(state['finished_at'])-datetime.fromisoformat(state['started_at'])).total_seconds()
        run_info.append({'path':str(root),'status':state['status'],'identity_sha256':file_hash(root/'run.json'),
                         'wall_seconds':elapsed,'model_usage':state.get('model_usage'),
                         'note':'Wall/client times may include other concurrent experiment requests.'})
    if plot_runs:
        covered=set()
        for plot_root in plot_runs:
            plot_state=json.loads((plot_root/'run.json').read_text())
            for n,source in plot_state['identity']['sources'].items():
                if n not in preds:continue
                if source!=identities[n]:raise ValueError('Plot source identity mismatch')
                p=plot_root/'predictions'/(state_key(Path(n))+'.json')
                if not p.exists() or json.loads(p.read_text())['status']!='complete':continue
                if n in covered:raise ValueError('Duplicate plot coverage')
                covered.add(n)
                for page in range(2,totals[n]+1):
                    row=json.loads((plot_root/'seams'/state_key(Path(n))/f'{page:04}.json').read_text())
                    if row['status']!='complete':raise ValueError('Incomplete plot seam')
                    if row.get('facts'):
                        from plot_facts import recovery
                        rule=recovery(row['facts'])
                        if rule and page in preds[n]:
                            preds[n].remove(page);plot_changes.append({'file':n,'page':page,'rule':rule})
        if set(preds)-covered:
            if not allow_partial:raise ValueError('Incomplete plot coverage')
            preds={n:p for n,p in preds.items() if n in covered};totals={n:totals[n] for n in preds}
    gt={n:all_gt[n] for n in preds};strata={n:all_strata[n] for n in gt}
    reports={'candidate':evaluate(gt,preds,masked,strata,totals)}
    for name,path in baselines.items():
        base=load_preds(path);reports[name]=evaluate(gt,{n:base[n] for n in gt},masked,strata,totals)
    return {'partial':len(gt)!=len(selected),'files':len(gt),'pages':sum(totals.values()),
            'ground_truth_sha256':file_hash(folder/'ground_truth.json'),'reports':reports,
            'predictions':{n:sorted(p) for n,p in preds.items()},'totals':totals,'runs':run_info,
            'plot_overlay':{'runs':[str(p) for p in plot_runs],'changes':plot_changes} if plot_runs else None,
            'postal_policy':{'code_sha256':file_hash(Path(__file__).resolve().parent.parent/'filing_unit_policy.py'),'changes':postal_changes} if postal_policy else None,
            'fact_policy':{'code_sha256':file_hash(Path(__file__).resolve().parent.parent/'boundary_fact_policy.py'),'changes':fact_changes} if fact_policy else None,
            'baseline_hashes':{n:file_hash(p) for n,p in baselines.items()},
            'guard':{'code_sha256':file_hash(Path(__file__).resolve().parent.parent/'refinement_policy.py'),
                     'base_runs':[str(p) for p in base_runs],'changes':guard_changes} if base_runs else None}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path)
    p.add_argument('--runs',type=Path,nargs='+',required=True)
    p.add_argument('--baseline',action='append',default=[],help='NAME=JSON_PATH')
    p.add_argument('--guard-base-runs',type=Path,nargs='+',help='Apply frozen v7b scope guard using these v6 base runs')
    p.add_argument('--plot-runs',type=Path,nargs='+',help='Overlay completed narrow plot verifications')
    p.add_argument('--postal-policy',action='store_true',help='Apply declared receipt-batch grouping')
    p.add_argument('--fact-policy',action='store_true',help='Apply v8b recovery to saved page facts')
    p.add_argument('--allow-partial',action='store_true');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();baseline={k:Path(v) for k,v in (x.split('=',1) for x in a.baseline)}
    report=score(a.folder,a.runs,baseline,a.allow_partial,a.guard_base_runs,a.fact_policy,a.postal_policy,a.plot_runs);atomic_json(a.output,report)
    print('partial',report['partial'],'files',report['files'],'pages',report['pages'])
    for label,data in report['reports'].items():
        r=data['by_stratum']['aggregate'];print(f"{label}: F1 {r['f1']:.4%}, TP {r['TP']}, FP {r['FP']}, FN {r['FN']}, exact {r['docs_exact']}/{r['docs_total']}, sources {r['source_exact']}/{r['files']}")


if __name__=='__main__':main()
