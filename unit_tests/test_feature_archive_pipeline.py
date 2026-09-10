import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from pypdf import PdfWriter
import split
from feature_pipeline import detect,cache_directory,configure
from model_options import DEFAULT_DEPLOYMENT
from production_state import source_identity
from qwen38_client import Qwen38Client,Qwen38Error
from filing_unit_policy import apply


BASE={'left_heading':'Slab Surface Loading','right_heading':'Slab Resultant M22',
      'left_kind':'other','right_kind':'other','left_columns':'','right_columns':'','right_first_row_label':'',
      'page_type_confidence':95,'relationship':'independent','evidence':'Different software outputs',
      'new_document':True,'confidence':95}


class ArchivePipelineTests(unittest.TestCase):
    def fixture(self,mode):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);pdf=root/'source.pdf';w=PdfWriter()
            for _ in range(2):w.add_blank_page(width=72,height=72)
            w.write(pdf);source=source_identity(pdf);settings={'boundary_method':'features_v11' if mode=='thermal_context' else 'features_v9'}
            d=json.loads(DEFAULT_DEPLOYMENT.read_text());client=Qwen38Client('http://127.0.0.1:8000/v1',d['served_model'],d)
            def infer(*args,**kwargs):
                client._model_calls+=1;i=client._model_calls
                if mode=='plot' and i==3:
                    client._failed_calls+=1;raise Qwen38Error('plot request interrupted')
                client._successful_calls+=1
                if i<=2:
                    answer=BASE if mode=='plot' else {**BASE,'left_heading':'Thermal summary','right_heading':'Thermal calculation',
                          'evidence':'Thermal tables','new_document':False,'relationship':'continuation'}
                elif mode=='thermal_context' and i==4:answer={'left_heading':'Interior thermal table','right_heading':'Thermal calculation',
                     'left_closing_summary':False,'right_output':'continuation','evidence':'No completed report','confidence':95}
                elif mode=='plot':answer={'left_kind':'structural_software_plot','right_kind':'structural_software_plot',
                     'same_structure':True,'right_independent_titleblock':False,'evidence':'Same grid and geometry','confidence':95}
                else:answer={'left_role':'thermal_output','right_role':'thermal_output','right_first_page':True,
                     'left_evidence':'Summary','right_evidence':'New output, initial parameters','confidence':95}
                return json.dumps(answer)
            kwargs=dict(pipeline=split,checkpoint_dir=root/'cache',source=source,settings=settings)
            params=(pdf,2,client,None,{'backend':'qwen38'},150,logging.getLogger('archive-test'))
            with patch('split._load_page',return_value=Image.new('RGB',(10,10))),patch('split._query_rotation',return_value=0), \
                 patch.object(client,'infer',side_effect=infer) as request:
                if mode=='plot':
                    with self.assertRaises(Qwen38Error):detect(*params,**kwargs)
                boundaries,_=detect(*params,**kwargs)
                self.assertEqual([b.page for b in boundaries],[1] if mode in ('plot','thermal_context') else [1,2])
                calls=4 if mode in ('plot','thermal_context') else 3;self.assertEqual(request.call_count,calls)
                detect(*params,**kwargs);self.assertEqual(request.call_count,calls)
                summary=json.loads((cache_directory(root/'cache',source,settings)/'summary.json').read_text())
                self.assertEqual(summary['model_usage']['model_calls'],calls)
                self.assertEqual(summary['model_usage']['failed_calls'],1 if mode=='plot' else 0)
                self.assertEqual(summary['plot_queries'],1 if mode=='plot' else 0)
                self.assertEqual(summary['fact_queries'],0 if mode=='plot' else 1)

    def test_plot_verification_resumes_without_repeating_other_passes(self):self.fixture('plot')
    def test_fresh_thermal_output_is_recovered_without_plot_call(self):self.fixture('thermal')

    def test_context_verifies_and_removes_false_thermal_restart(self):self.fixture('thermal_context')

    def test_postal_batch_keeps_singleton_attachment_and_separates_batch(self):
        receipt='ИЗВЕСТИЕ ЗА ДОСТАВЯНЕ'
        first={**BASE,'left_heading':'СЪОБЩЕНИЕ','right_heading':receipt,'new_document':False,'relationship':'continuation'}
        second={**BASE,'left_heading':receipt,'right_heading':receipt}
        self.assertFalse(apply({2:first})[2]['new_document'])
        result=apply({2:first,3:second});self.assertTrue(result[2]['new_document']);self.assertFalse(result[3]['new_document'])
        self.assertFalse(first['new_document']);self.assertTrue(second['new_document'])
        setting=configure({'inference':{'backend':'qwen38','thinking':'off'},'code':{}},'archive')
        self.assertEqual(setting['boundary_method'],'features_v9');self.assertIn('plot_facts.py',setting['code'])


if __name__=='__main__':unittest.main()
