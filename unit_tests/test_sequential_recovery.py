import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from sequential_recovery import recover

class SequenceRecoveryTests(unittest.TestCase):
    def test_validates_anchor_provenance_and_preserves_timing(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);(d/'context/anchor').mkdir(parents=True)
            source={'sha256':'source'};settings={'code':'frozen'}
            summary={'seam_processing_seconds':123,'model_usage':{'requests':7}}
            (d/'summary.json').write_text(json.dumps(summary))
            record={'identity':{'source':source,'settings':settings},'status':'complete','facts':{
                'confidence':95,'right_fresh_start':True,'anchor_kind':'technical_assignment',
                'right_kind':'quantity_schedule','right_heading':'Количествена сметка на материалите'}}
            path=d/'context/anchor/0002.json';path.write_text(json.dumps(record))
            decisions={2:{'new_document':False}}
            first=recover(decisions,d,source,settings)
            self.assertTrue(first[2]['new_document'])
            recorded=json.loads((d/'summary.json').read_text())
            self.assertEqual(recorded['seam_processing_seconds'],123)
            self.assertEqual(recorded['model_usage'],summary['model_usage'])
            self.assertEqual(first,recover(decisions,d,source,settings))
            self.assertEqual(recorded,json.loads((d/'summary.json').read_text()))
            with self.assertRaisesRegex(ValueError,'mismatch'):recover(decisions,d,{'sha256':'changed'},settings)
            with self.assertRaisesRegex(ValueError,'mismatch'):recover(decisions,d,source,{'code':'changed'})
            record['status']='failed';path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'complete'):recover(decisions,d,source,settings)

if __name__=='__main__':unittest.main()
