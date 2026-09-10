import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from production_state import source_identity
import report_ocr_recovery

class ReportOCRRecoveryTests(unittest.TestCase):
    def test_checkpoint_reuse_failure_recovery_and_source_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);pdf=d/'source.pdf';pdf.write_bytes(b'fixed source')
            source=source_identity(pdf);settings={'version':13};pipeline=SimpleNamespace(_load_page=lambda *args:object())
            def run(s=settings):return report_ocr_recovery.read(pdf,1,pipeline=pipeline,directory=d,source=source,settings=s,rotations={},dpi=150)
            with patch('report_ocr_recovery.report_ocr_policy.query',return_value=[dict(mode=6,text='',error='temporary OCR failure')]):
                with self.assertRaises(RuntimeError):run()
            rows=[dict(mode=m,text='XXII 7654321',error=None) for m in (6,11)]
            with patch('report_ocr_recovery.report_ocr_policy.query',return_value=rows) as query:
                record,hit=run();self.assertFalse(hit);self.assertEqual(record['attempts'],2)
                cached,hit=run();self.assertTrue(hit);self.assertEqual(record,cached);self.assertEqual(query.call_count,1)
            with self.assertRaisesRegex(ValueError,'identity'):run({'version':14})
            pdf.write_bytes(b'changed source')
            with self.assertRaisesRegex(ValueError,'Source changed'):run()

if __name__=='__main__':unittest.main()
