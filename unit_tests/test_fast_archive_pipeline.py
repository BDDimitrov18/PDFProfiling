import json,logging,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from pypdf import PdfWriter
import split
from feature_pipeline import configure,detect,cache_directory
from model_options import DEFAULT_DEPLOYMENT
from production_state import source_identity
from qwen38_client import Qwen38Client


class FastArchiveTests(unittest.TestCase):
    def test_receipt_reconciliation_changes_output_without_extra_queries(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);pdf=root/'unseen-name.pdf';writer=PdfWriter()
            for _ in range(4):writer.add_blank_page(width=72,height=72)
            writer.write(pdf);source=source_identity(pdf)
            settings=configure({'inference':{'backend':'qwen38','thinking':'off'},'code':{}},'archive-fast')
            deployment=json.loads(DEFAULT_DEPLOYMENT.read_text());client=Qwen38Client('http://127.0.0.1:8000/v1',deployment['served_model'],deployment)
            def infer(prompt,*args,**kwargs):
                client._model_calls+=1;client._successful_calls+=1
                cut=client._model_calls==2
                heading='ИЗВЕСТИЕ ЗА ПОСТАВЯНЕ' if cut else 'ИЗВЕСТИЕ ЗА ДОСТАВЯНЕ'
                return json.dumps({'left_heading':heading,'right_heading':heading,'left_kind':'other','right_kind':'other',
                    'left_columns':'','right_columns':'','right_first_row_label':'','page_type_confidence':100,
                    'relationship':'independent' if cut else 'form_series','evidence':'Postal receipts','new_document':cut,'confidence':100})
            kwargs=dict(pipeline=split,checkpoint_dir=root/'cache',source=source,settings=settings)
            params=(pdf,4,client,None,{'backend':'qwen38'},150,logging.getLogger('receipt-consistency'))
            with patch('split._load_page',return_value=Image.new('RGB',(10,10))),patch('split._query_rotation',return_value=0),patch.object(client,'infer',side_effect=infer) as query:
                for _ in range(2):
                    boundaries,_=detect(*params,**kwargs);self.assertEqual([b.page for b in boundaries],[1])
                self.assertEqual(query.call_count,3)
            directory=cache_directory(root/'cache',source,settings);summary=json.loads((directory/'summary.json').read_text())
            self.assertEqual(summary['receipt_consistency_changes'][0]['right_page'],3)
            self.assertEqual(summary['model_usage']['model_calls'],3)
            self.assertIn('same_page_receipt_heading_disagreement',summary['review_candidates'][0]['reasons'])
            raw=json.loads((directory/'0003.json').read_text())
            self.assertTrue(raw['decision']['new_document'])
            self.assertEqual(raw['decision']['right_heading'],'ИЗВЕСТИЕ ЗА ПОСТАВЯНЕ')

    def test_one_pass_then_receipt_policy_resumes_without_a_refinement_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);pdf=root/'arbitrary.pdf';writer=PdfWriter()
            for _ in range(3):writer.add_blank_page(width=72,height=72)
            writer.write(pdf);source=source_identity(pdf)
            settings=configure({'inference':{'backend':'qwen38','thinking':'off'},'code':{}},'archive-fast')
            deployment=json.loads(DEFAULT_DEPLOYMENT.read_text());client=Qwen38Client('http://127.0.0.1:8000/v1',deployment['served_model'],deployment)
            def infer(prompt,*args,**kwargs):
                self.assertIn('Apply these more specific archive-unit conventions',prompt)
                client._model_calls+=1;client._successful_calls+=1
                left,right=(('СЪОБЩЕНИЕ','ИЗВЕСТИЕ ЗА ДОСТАВЯНЕ') if client._model_calls==1
                            else ('ИЗВЕСТИЕ ЗА ДОСТАВЯНЕ','УДОСТОВЕРЕНИЕ'))
                return json.dumps({'left_heading':left,'right_heading':right,'left_kind':'other','right_kind':'other',
                   'left_columns':'','right_columns':'','right_first_row_label':'','page_type_confidence':95,
                   'relationship':'independent','evidence':'Distinct named documents','new_document':True,'confidence':95})
            kwargs=dict(pipeline=split,checkpoint_dir=root/'cache',source=source,settings=settings)
            params=(pdf,3,client,None,{'backend':'qwen38'},150,logging.getLogger('fast-test'))
            with patch('split._load_page',return_value=Image.new('RGB',(10,10))),patch('split._query_rotation',return_value=0),patch.object(client,'infer',side_effect=infer) as query:
                for _ in range(2):
                    boundaries,_=detect(*params,**kwargs);self.assertEqual([b.page for b in boundaries],[1,3])
                self.assertEqual(query.call_count,2)
            directory=cache_directory(root/'cache',source,settings);summary=json.loads((directory/'summary.json').read_text())
            self.assertFalse((directory/'refinements').exists())
            self.assertEqual(summary['model_usage']['model_calls'],2)
            self.assertEqual(summary['context_queries'],0)
            self.assertEqual(summary['review_candidates'][0]['context_rule'],'single_receipt_supports_notice')


if __name__=='__main__':unittest.main()
