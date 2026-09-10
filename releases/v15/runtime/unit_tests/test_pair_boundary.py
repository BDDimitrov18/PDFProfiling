import contextlib
import io
import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from pypdf import PdfWriter
import model_options
import pair_boundary
from qwen38_client import Qwen38Client, Qwen38Error
from scripts import run_pair_experiment


class PairBoundaryTests(unittest.TestCase):
    def test_decisions_reject_missing_fields_and_contradictions(self):
        data={'left_heading':'','right_heading':'','relationship':'continuation',
              'evidence':'The sentence continues.','new_document':False,'confidence':90}
        self.assertEqual(pair_boundary.decision(data),data)
        for bad in ({**data,'new_document':True},{**data,'relationship':'invented'},
                    {**data,'confidence':101},{**data,'new_document':'false'}):
            with self.assertRaises((ValueError,RuntimeError)): pair_boundary.decision(bad)
        with self.assertRaises(ValueError): pair_boundary.prompt('archive_v2',2,4)

    def test_failed_seam_does_not_block_next_seam_and_retry_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/'source.pdf'; run=root/'run'
            writer=PdfWriter()
            for _ in range(3): writer.add_blank_page(width=72,height=72)
            writer.write(source)
            (root/'ground_truth.json').write_text('NOT LABELS: this file must never be read')
            (root/'sources.json').write_text(json.dumps([source.name]))
            d=json.loads(model_options.DEFAULT_DEPLOYMENT.read_text())
            client=Qwen38Client('http://127.0.0.1:8000/v1',d['served_model'],d)
            answer={'left_heading':'','right_heading':'','relationship':'independent',
                    'evidence':'A new letter.','new_document':True,'confidence':90}
            negative={**answer,'relationship':'continuation','new_document':False}
            args=[str(root),'--sources',str(root/'sources.json'),'--variant','archive_v2','--run-dir',str(run)]
            with patch('scripts.run_pair_experiment.preflight'), \
                 patch('split.load_model',return_value=(client,None,{'backend':'qwen38'})), \
                 patch('split._load_page',return_value=Image.new('RGB',(10,10))), \
                 patch('split._query_rotation',return_value=0), \
                 patch.object(client,'infer',side_effect=[Qwen38Error('transient'),json.dumps(answer),json.dumps(negative)]) as infer, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_pair_experiment.main(args),0)
                self.assertEqual(infer.call_count,3)
                result=json.loads(next((run/'predictions').glob('*.json')).read_text())
                self.assertEqual(result['starts'],[1,3])
                seam=json.loads(next((run/'seams').glob('*/0002.json')).read_text())
                self.assertEqual(seam['attempts'],2)
                self.assertEqual(seam['history'][0]['status'],'failed')
                infer.reset_mock()
                self.assertEqual(run_pair_experiment.main(args),0)
                infer.assert_not_called()


if __name__=='__main__': unittest.main()
