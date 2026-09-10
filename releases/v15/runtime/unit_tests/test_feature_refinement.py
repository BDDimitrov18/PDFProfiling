import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from pypdf import PdfWriter
from model_options import DEFAULT_DEPLOYMENT
from production_state import atomic_json,source_identity,state_key
from qwen38_client import Qwen38Client
from scripts import run_feature_refinement as runner


class RefinementTests(unittest.TestCase):
    def test_candidates_reuse_base_and_resume_without_labels(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);pdf=root/'source.pdf';base=root/'base';run=root/'run'
            writer=PdfWriter()
            for _ in range(4):writer.add_blank_page(width=72,height=72)
            writer.write(pdf);source=source_identity(pdf);key=state_key(pdf)
            (root/'sources.json').write_text(json.dumps([pdf.name]))
            (root/'ground_truth.json').write_text('Not valid JSON. Inference must never read this.')
            settings={'variant':'features_v6'}
            atomic_json(base/'run.json',{'identity':{'settings':settings,'sources':{pdf.name:source}}})
            atomic_json(base/'predictions'/(key+'.json'),{'status':'complete','identity':{'source':source},'starts':[1,3]})
            answer={'left_heading':'','right_heading':'','left_kind':'other','right_kind':'other',
                    'left_columns':'','right_columns':'','right_first_row_label':'','page_type_confidence':95,
                    'relationship':'continuation','evidence':'Continuing text','new_document':False,'confidence':95}
            for right in (2,3,4):
                d={**answer,'relationship':'independent','new_document':True} if right==3 else answer
                atomic_json(base/'seams'/key/f'{right:04}.json',{'status':'complete','identity':{'source':source},
                            'decision':d,'rotations':{'1':0,'2':0,'3':0,'4':0}})
            deployment=json.loads(DEFAULT_DEPLOYMENT.read_text())
            client=Qwen38Client('http://127.0.0.1:8000/v1',deployment['served_model'],deployment)
            args=[str(root),'--sources',str(root/'sources.json'),'--run-dir',str(run),
                  '--base-run',str(base),'--variant','features_v7','--greedy']
            with patch.object(runner,'preflight'),patch.object(runner,'load_labeled_model',return_value=(client,None,{'backend':'qwen38'})), \
                 patch('split._load_page',return_value=Image.new('RGB',(10,10))),patch('split._query_rotation',return_value=0), \
                 patch.object(client,'infer',return_value=json.dumps(answer)) as infer,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.main(args),0);self.assertEqual(infer.call_count,1)
                pred=json.loads((run/'predictions'/(key+'.json')).read_text());self.assertEqual(pred['starts'],[1])
                reused=json.loads((run/'seams'/key/'0002.json').read_text());self.assertEqual(reused['origin'],'reused_features_v6')
                self.assertEqual(runner.main(args),0);self.assertEqual(infer.call_count,1)
                changed=json.loads((base/'predictions'/(key+'.json')).read_text());changed['starts']=[1]
                atomic_json(base/'predictions'/(key+'.json'),changed)
                with self.assertRaisesRegex(ValueError,'Inputs or settings changed'):runner.main(args)


if __name__=='__main__':unittest.main()
