import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from pypdf import PdfWriter
import split
from feature_pipeline import configure,detect,cache_directory
from model_options import DEFAULT_DEPLOYMENT
from production_state import source_identity
from qwen38_client import Qwen38Client,Qwen38Error


class FeaturePipelineTests(unittest.TestCase):
    def test_interrupted_source_reuses_seams_and_retains_usage(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);pdf=root/'source.pdf';cache=root/'cache'
            writer=PdfWriter()
            for _ in range(3):writer.add_blank_page(width=72,height=72)
            writer.write(pdf);source=source_identity(pdf)
            (root/'ground_truth.json').write_text('MUST NOT BE READ')
            settings={'boundary_method':'features_v6','revision':'test'}
            d=json.loads(DEFAULT_DEPLOYMENT.read_text());client=Qwen38Client('http://127.0.0.1:8000/v1',d['served_model'],d)
            answer={'left_heading':'','right_heading':'','left_kind':'other','right_kind':'other',
                    'left_columns':'','right_columns':'','right_first_row_label':'','page_type_confidence':95,
                    'relationship':'continuation','evidence':'Continued text','new_document':False,'confidence':95}
            def infer(*args,**kwargs):
                client._model_calls+=1
                if client._model_calls==2:
                    client._failed_calls+=1
                    raise Qwen38Error('temporary outage')
                client._successful_calls+=1
                return json.dumps(answer if client._model_calls==1 else {**answer,'relationship':'independent','new_document':True})
            kwargs=dict(pipeline=split,checkpoint_dir=cache,source=source,settings=settings)
            params=(pdf,3,client,None,{'backend':'qwen38'},150,logging.getLogger('feature-test'))
            with patch('split._load_page',return_value=Image.new('RGB',(10,20))), \
                 patch('split._query_rotation',side_effect=lambda img,page,*_:270 if page==2 else 0), \
                 patch.object(client,'infer',side_effect=infer) as request:
                with self.assertRaises(Qwen38Error):detect(*params,**kwargs)
                boundaries,rotations=detect(*params,**kwargs)
                self.assertEqual([b.page for b in boundaries],[1,3]);self.assertEqual(rotations,{2:270})
                self.assertEqual(request.call_count,3)
                directory=cache_directory(cache,source,settings)
                summary=json.loads((directory/'summary.json').read_text())
                self.assertEqual(summary['cached_seams'],1)
                self.assertEqual(summary['model_usage']['model_calls'],3)
                self.assertEqual(summary['model_usage']['failed_calls'],1)
                detect(*params,**kwargs);self.assertEqual(request.call_count,3)
                self.assertNotEqual(directory,cache_directory(cache,source,{**settings,'revision':'new'}))

    def test_feature_mode_rejects_incompatible_configuration(self):
        legacy={'inference':{'backend':'hf'},'code':{}}
        self.assertIs(configure(legacy,'legacy'),legacy)
        with self.assertRaises(ValueError):configure(legacy,'features')
        qwen={'inference':{'backend':'qwen38','thinking':'off'},'code':{},'align_confirmation':False}
        configured=configure(qwen,'features')
        self.assertNotIn('experimental_greedy',qwen['inference'])
        self.assertTrue(configured['inference']['experimental_greedy'])
        self.assertIn('feature_pipeline.py',configured['code'])
        with self.assertRaises(ValueError):configure({**qwen,'align_confirmation':True},'features')


if __name__=='__main__':unittest.main()
