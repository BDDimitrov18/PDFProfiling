#!/usr/bin/env python3
"""Run a frozen, label-free anchor-context probe on explicit image windows."""
import argparse,json,logging,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from model_options import add_model_arguments,resolve_model_arguments,load_kwargs,usage_snapshot,usage_delta
from run_production import runtime_settings,preflight
from labeled_qwen38 import load_model
from production_state import atomic_json,file_hash,source_identity
import split,anchor_facts


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--cases',type=Path,required=True);parser.add_argument('--run-dir',type=Path,required=True)
    add_model_arguments(parser);parser.set_defaults(backend='qwen38',thinking='off',request_timeout=600)
    args=parser.parse_args();model,revision,inference=resolve_model_arguments(args);inference['experimental_greedy']=True
    settings=runtime_settings(model,150,False,revision,inference)
    settings['code'].update({n:file_hash(Path(__file__).resolve().parent.parent/n) for n in ['anchor_facts.py','scripts/check_anchor_context.py','labeled_qwen38.py']})
    cases=json.loads(args.cases.read_text());logger=split.setup_logging(args.run_dir/'logs');preflight()
    bundle=load_model(model,logger,**load_kwargs(settings));results=[]
    try:
        for case in cases:
            pdf=args.root/case['folder']/case['file'];right=case['right_page'];source=source_identity(pdf)
            identity={'source':source,'right_page':right,'anchor_page':case['anchor_page'],'settings':settings};path=args.run_dir/(case['id']+'.json')
            if path.exists():
                cached=json.loads(path.read_text())
                if cached['identity']!=identity:raise ValueError('Probe identity changed')
                if cached['status']=='complete':results.append(cached);continue
            images=[]
            for page in (case['anchor_page'],right):
                image=split._load_page(pdf,page,150);angle=split._query_rotation(image,page,*bundle,logger)
                images.append(image.rotate(angle,expand=True) if angle else image)
            before=usage_snapshot(bundle[0]);started=time.monotonic()
            record={'id':case['id'],'identity':identity,'status':'running'}
            try:
                raw=split._infer(anchor_facts.prompt(case['anchor_page'],right),images,*bundle,logger,max_tokens=300,response_schema=anchor_facts.SCHEMA)
                facts=json.loads(split.clean_response(raw))
                rule=anchor_facts.recovery(facts)
                record.update(status='complete',facts=facts,raw_final=raw,recovery=rule)
            except BaseException as exc:record.update(status='failed',error=str(exc));raise
            finally:
                record.update(seconds=time.monotonic()-started,model_usage=usage_delta(before,usage_snapshot(bundle[0])))
                atomic_json(path,record);results.append(record)
            print(case['id'],record['facts'],flush=True)
    finally:atomic_json(args.run_dir/'run.json',{'settings':settings,'cases':cases,'results':results,'model_usage':usage_snapshot(bundle[0]),'status':'complete' if len(results)==len(cases) and all(r['status']=='complete' for r in results) else 'failed'})


if __name__=='__main__':main()
