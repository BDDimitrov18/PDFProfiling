import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import identity_recovery

class IdentityUsageAccountingTests(unittest.TestCase):
    def run_case(self,unknown_model=False):
        base_usage={'model_calls':10,'successful_calls':10,'failed_calls':0,'input_tokens':1000,'output_tokens':100,'reasoning_tokens':0}
        model_usage={'model_calls':1,'successful_calls':1,'failed_calls':0,'input_tokens':100,'output_tokens':10,'reasoning_tokens':0}
        common=dict(confidence=95,regulated_plot='XII 7654321',quarter='86',subproject='Сграда 1',cadastral_id='',subject='',heading='',object_field=False,part_field=False,return_date_field=False)
        left={**common,'kind':'assessment_report_cover'};right={**common,'kind':'assessment_report_body','regulated_plot':'XXII 7654321'}
        def read(pdf,requests,module,stage,*args,**kw):
            facts={};records=[]
            for page,crop in sorted(set(requests)):
                if stage=='identity_pages':
                    f=dict(kind='assessment_report_cover' if page==1 else 'assessment_report_body',confidence=95,
                           project_id='7654321' if page==1 else '7654322',project_name='',report_id='')
                else:
                    f=dict(left if page==1 else right)
                    if crop:f['regulated_plot']='XXII 7654321'
                facts[(page,crop)]=f
                usage=None if unknown_model and stage=='identity_pages' and page==1 else model_usage
                records.append({'seconds':1,'model_usage':usage})
            return facts,records,0
        def ocr(*args,**kw):
            return {'seconds':0.5,'model_usage':None,'results':[{'text':'XXII 7654321','error':None} for _ in range(2)]},False
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);(directory/'summary.json').write_text(json.dumps({'seam_processing_seconds':10,'model_usage':base_usage,'review_candidates':[]}))
            ds={2:dict(new_document=True,left_heading='Доклад',right_heading='Оценка за съответствие',right_kind='other')}
            with patch('identity_recovery.read',side_effect=read),patch('identity_recovery.report_ocr_recovery.read',side_effect=ocr):
                final=identity_recovery.recover(directory/'source.pdf',2,(SimpleNamespace(),None,{}),150,None,pipeline=None,
                                                directory=directory,source={},settings={},decisions=ds,rotations={})
            self.assertFalse(final[2]['new_document'])
            return json.loads((directory/'summary.json').read_text())
    def test_cpu_ocr_does_not_erase_model_usage_or_count_as_model_calls(self):
        summary=self.run_case()
        self.assertEqual(summary['model_usage']['model_calls'],16)
        self.assertEqual(summary['model_usage']['input_tokens'],1600)
        self.assertEqual(summary['model_usage']['reasoning_tokens'],0)
        self.assertEqual(summary['identity_page_queries'],6)
        self.assertEqual(summary['identity_ocr_pages'],2)
        self.assertEqual(summary['seam_processing_seconds'],17)
    def test_unknown_actual_model_usage_remains_unknown(self):
        self.assertIsNone(self.run_case(unknown_model=True)['model_usage'])

if __name__=='__main__':unittest.main()
