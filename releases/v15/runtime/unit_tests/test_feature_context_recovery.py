import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from pypdf import PdfWriter
import split
from feature_context_recovery import recover
from model_options import DEFAULT_DEPLOYMENT, usage_snapshot
from production_state import atomic_json, source_identity
from qwen38_client import Qwen38Client, Qwen38Error

BASE = {'page_type_confidence':95,'new_document': False, 'relationship': 'continuation', 'confidence': 95,
        'left_heading': 'Energy tables', 'right_heading': 'Thermal calculation'}
THERMAL = {'left_role': 'thermal_output', 'right_role': 'thermal_output',
           'right_first_page': True, 'left_evidence': 'Tables',
           'right_evidence': 'First-looking table', 'confidence': 95}


class ContextRecoveryTests(unittest.TestCase):
    def setup_case(self, root, count):
        pdf = root / 'arbitrary-name.pdf'
        writer = PdfWriter()
        for _ in range(count):
            writer.add_blank_page(width=72, height=72)
        writer.write(pdf)
        source = source_identity(pdf)
        deployment = json.loads(DEFAULT_DEPLOYMENT.read_text())
        client = Qwen38Client('http://127.0.0.1:8000/v1', deployment['served_model'], deployment)
        directory = root / 'cache'
        atomic_json(directory / 'summary.json', {'seam_processing_seconds': 0, 'model_usage': usage_snapshot(client)})
        params = (pdf, count, (client, None, {'backend': 'qwen38'}), 150, logging.getLogger('context-test'))
        kwargs = dict(pipeline=split, directory=directory, source=source, settings={}, rotations={})
        return directory, client, params, kwargs

    def test_interrupted_thermal_check_resumes_and_can_remove_earlier_false_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            directory, client, params, kwargs = self.setup_case(Path(temp), 2)
            atomic_json(directory / 'facts/0002.json', {
                'status': 'complete', 'identity': {'base_decision': BASE,
                'source': kwargs['source'], 'settings': kwargs['settings']}, 'facts': THERMAL})
            decisions = {2: {**BASE, 'new_document': True, 'relationship': 'independent',
                             'fact_recovery': 'thermal_output_restart'}}
            def infer(*args, **kw):
                client._model_calls += 1
                if client._model_calls == 1:
                    client._failed_calls += 1
                    raise Qwen38Error('connection interrupted during context verification')
                client._successful_calls += 1
                return json.dumps({'left_heading': 'Interior table', 'right_heading': 'Interior calculation',
                                   'left_closing_summary': False, 'right_output': 'continuation',
                                   'evidence': 'Neither side completes the report', 'confidence': 95})
            with patch('split._load_page', return_value=Image.new('RGB', (10, 10))), \
                 patch.object(client, 'infer', side_effect=infer) as request:
                with self.assertRaises(Qwen38Error):
                    recover(*params, **kwargs, decisions=decisions)
                result = recover(*params, **kwargs, decisions=decisions)
                self.assertFalse(result[2]['new_document'])
                self.assertIsNone(result[2]['fact_recovery'])
                # The outer detector resets the preceding-stage summary on resume.
                atomic_json(directory / 'summary.json',
                            json.loads((directory / 'summary.json').read_text())['pre_context_summary'])
                cached = recover(*params, **kwargs, decisions=decisions)
                self.assertEqual(cached, result)
                self.assertEqual(request.call_count, 2)
            summary = json.loads((directory / 'summary.json').read_text())
            self.assertEqual(summary['model_usage']['model_calls'], 2)
            self.assertEqual(summary['model_usage']['failed_calls'], 1)
            self.assertEqual(summary['cached_context'], 1)
            self.assertFalse(summary['review_candidates'][0]['final_cut'])
            self.assertTrue(decisions[2]['new_document'])

    def test_anchor_is_predicted_start_not_previous_page_or_new_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            directory, client, params, kwargs = self.setup_case(Path(temp), 5)
            decisions = {p: {**BASE, 'right_heading': ''} for p in range(2, 6)}
            decisions[2].update(new_document=True, relationship='independent')
            for p in (4, 5):
                decisions[p]['right_heading'] = 'ДЕНДРОЛОГИЧНА ВЕДОМОСТ'
            def infer(prompt, *args, **kw):
                self.assertIn('source page 2,', prompt)
                client._model_calls += 1
                client._successful_calls += 1
                return json.dumps({'anchor_heading': 'КОЛИЧЕСТВЕНА СМЕТКА',
                                   'right_heading': 'ДЕНДРОЛОГИЧНА ВЕДОМОСТ',
                                   'anchor_kind': 'quantity_schedule', 'right_kind': 'tree_inventory',
                                   'right_fresh_start': True, 'evidence': 'Different named table types',
                                   'confidence': 95})
            with patch('split._load_page', return_value=Image.new('RGB', (10, 10))) as load, \
                 patch.object(client, 'infer', side_effect=infer):
                result = recover(*params, **kwargs, decisions=decisions)
                self.assertEqual([call.args[1] for call in load.call_args_list], [2, 4, 2, 5])
            self.assertTrue(result[4]['new_document'])
            self.assertTrue(result[5]['new_document'])
            self.assertFalse(decisions[4]['new_document'])
            row = json.loads((directory / 'context/anchor/0005.json').read_text())
            self.assertEqual(row['identity']['context_page'], 2)


if __name__ == '__main__':
    unittest.main()
