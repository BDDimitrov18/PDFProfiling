#!/usr/bin/env python3
"""Diagnostic repeated order/sampling tests. Only source pages, no labels, enter inference."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import archive_boundary
from labeled_qwen38 import LabeledQwen38Client
from model_options import DEFAULT_DEPLOYMENT
from production_state import atomic_json,file_hash,source_identity
import split


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('--cases',type=Path,required=True);p.add_argument('--run-dir',type=Path,required=True)
    a=p.parse_args();a.run_dir.mkdir(parents=True,exist_ok=True)
    d=json.loads(DEFAULT_DEPLOYMENT.read_text());cases=json.loads(a.cases.read_text())
    log=split.setup_logging(a.run_dir/'logs');results=[]
    identity={'cases_sha256':file_hash(a.cases),'code':{n:file_hash(ROOT/n) for n in ['archive_boundary.py','labeled_qwen38.py','scripts/check_image_order.py']},'deployment':d,'sources':{c['file']:source_identity(a.folder/c['file']) for c in cases}}
    for c in cases:
        right=c['right'];images=[]
        for page in [right-1,right]:
            img=split._load_page(a.folder/c['file'],page,150)
            angle=split._query_rotation(img,page,None,None,None,log)
            images.append(img.rotate(angle,expand=True) if angle else img)
        for labels,greedy in [(False,False),(True,False),(False,True),(True,True)]:
            client=LabeledQwen38Client('http://127.0.0.1:8000/v1',d['served_model'],d,thinking='off',timeout_seconds=600,image_labels=labels,greedy=greedy);client.verify()
            for repeat in range(2):
                started=time.monotonic();r={'file':c['file'],'right':right,'image_labels':labels,'greedy':greedy,'repeat':repeat,'model':client.model_details()}
                try:
                    raw=split._infer(archive_boundary.prompt('typed_v3',right-1,right),images,client,None,{'backend':'qwen38'},log,response_schema=archive_boundary.SCHEMA)
                    r.update(status='complete',raw_final=raw,decision=archive_boundary.decision(json.loads(raw)))
                except Exception as exc:r.update(status='failed',error=repr(exc))
                r['seconds']=time.monotonic()-started;results.append(r)
                atomic_json(a.run_dir/'results.json',{'identity':identity,'results':results})
                print(c['file'],right,'labels',labels,'greedy',greedy,'repeat',repeat,r.get('decision',{}).get('correction'),r['status'],flush=True)
    atomic_json(a.run_dir/'status.json',{'status':'complete','queries':len(results),'failures':sum(r['status']!='complete' for r in results)})


if __name__=='__main__':main()
