import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from pypdf import PdfWriter
import split
from feature_pipeline import detect,cache_directory
from model_options import DEFAULT_DEPLOYMENT
from production_state import source_identity
from qwen38_client import Qwen38Client,Qwen38Error
from refinement_policy import choose


ANSWER={'left_heading':'','right_heading':'','left_kind':'other','right_kind':'other',
        'left_columns':'','right_columns':'','right_first_row_label':'','page_type_confidence':95,
        'relationship':'independent','evidence':'Separately issued document','new_document':True,'confidence':95}


class RefinedPipelineTests(unittest.TestCase):
    def test_resume_retains_both_passes_and_failed_usage(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);pdf=root/'source.pdf'
            w=PdfWriter()
            for _ in range(3):w.add_blank_page(width=72,height=72)
            w.write(pdf);source=source_identity(pdf);settings={'boundary_method':'features_v7b'}
            d=json.loads(DEFAULT_DEPLOYMENT.read_text());client=Qwen38Client('http://127.0.0.1:8000/v1',d['served_model'],d)
            def infer(*args,**kwargs):
                client._model_calls+=1
                if client._model_calls==4:
                    client._failed_calls+=1;raise Qwen38Error('interrupted refinement')
                client._successful_calls+=1
                return json.dumps({**ANSWER,'new_document':False,'relationship':'continuation'} if client._model_calls==3 else ANSWER)
            kwargs=dict(pipeline=split,checkpoint_dir=root/'cache',source=source,settings=settings)
            params=(pdf,3,client,None,{'backend':'qwen38'},150,logging.getLogger('refined-test'))
            with patch('split._load_page',return_value=Image.new('RGB',(10,10))),patch('split._query_rotation',return_value=0), \
                 patch.object(client,'infer',side_effect=infer) as request:
                with self.assertRaises(Qwen38Error):detect(*params,**kwargs)
                boundaries,_=detect(*params,**kwargs)
                self.assertEqual([b.page for b in boundaries],[1,3]);self.assertEqual(request.call_count,5)
                summary=json.loads((cache_directory(root/'cache',source,settings)/'summary.json').read_text())
                self.assertEqual(summary['cached_seams'],2);self.assertEqual(summary['cached_refinements'],1)
                self.assertEqual(summary['model_usage']['model_calls'],5);self.assertEqual(summary['model_usage']['failed_calls'],1)
                self.assertEqual(summary['review_candidates'][0]['right_page'],2)
                self.assertIn('passes_disagree',summary['review_candidates'][0]['reasons'])
                detect(*params,**kwargs);self.assertEqual(request.call_count,5)
                summary=json.loads((cache_directory(root/'cache',source,settings)/'summary.json').read_text())
                self.assertEqual(summary['model_usage']['model_calls'],5)

    def test_structural_scope_does_not_merge_thermal_outputs(self):
        base={**ANSWER,'right_heading':'Energy consumption indicators'}
        proposed={**ANSWER,'new_document':False,'relationship':'continuation','evidence':'Same project'}
        self.assertTrue(choose(base,proposed)['new_document'])
        self.assertFalse(choose(ANSWER,proposed)['new_document'])


if __name__=='__main__':unittest.main()
