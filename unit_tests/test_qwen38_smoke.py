import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from pypdf import PdfWriter
import smoke_qwen38
import model_options


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        writer = PdfWriter()
        for width in (100, 100, 100, 300, 100):
            writer.add_blank_page(width=width, height=100)
        writer.write(self.root / 'a.pdf')
        self.run_dir = self.root / 'run'
        # A deliberately unusable label file proves smoke selection never reads it.
        (self.root / 'ground_truth.json').write_text('not ground truth')

    def test_offline_check_selects_large_window_without_reading_labels_or_loading_model(self):
        with patch('split.load_model') as load, contextlib.redirect_stdout(io.StringIO()):
            code = smoke_qwen38.main([str(self.root), '--run-dir', str(self.run_dir), '--check'])
        self.assertEqual(code, 0)
        self.assertFalse(self.run_dir.exists())
        load.assert_not_called()
        windows = smoke_qwen38.select_windows(self.root)
        self.assertEqual([w['pages'] for w in windows], [[1, 2, 3], [3, 4, 5]])

    def test_actual_end_schema_round_trip_and_completed_check_needs_no_server(self):
        from qwen38_client import Qwen38Client
        deployment = json.loads(model_options.DEFAULT_DEPLOYMENT.read_text())
        client = Qwen38Client('http://127.0.0.1:8000/v1', deployment['served_model'], deployment)
        def infer(prompt, images, logger, max_tokens, response_schema):
            self.assertEqual(response_schema['signal_on_page'], int)
            center = 2 if 'Does page 2 END' in prompt else 4
            client._last_final_text = json.dumps({'end': False, 'signal': 'none',
                'signal_on_page': center, 'confidence': 90, 'reason': 'Continues.'})
            return client.last_final_text
        with patch('smoke_qwen38.preflight'), patch('split.load_model', return_value=(client, None, {'backend': 'qwen38'})), \
                patch('split._load_page', return_value=Image.new('RGB', (10, 10))), \
                patch('split._query_rotation', return_value=0), patch.object(client, 'infer', side_effect=infer), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(smoke_qwen38.main([str(self.root), '--run-dir', str(self.run_dir)]), 0)
        report = json.loads((self.run_dir / 'smoke_results.json').read_text())
        self.assertEqual(report['status'], 'complete')
        self.assertEqual(len(report['records']), 2)
        self.assertEqual(json.loads(report['records'][0]['raw_final'])['end'], False)
        with patch('split.load_model') as load, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(smoke_qwen38.main([str(self.root), '--run-dir', str(self.run_dir)]), 0)
        load.assert_not_called()


if __name__ == '__main__':
    unittest.main()
