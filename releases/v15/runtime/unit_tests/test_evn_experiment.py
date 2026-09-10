import contextlib
import copy
import io
import json
import logging
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

import eval_boundaries
import run_evn_experiment as runner
from evn_sections import parse_evidence, should_suppress
from production_state import atomic_json, source_identity
from test_reliability import pdf_file, boundary

LOG = logging.getLogger('unit-evn-experiment')
LOG.addHandler(logging.NullHandler())
KEEP = '{"title":"Договор","issuer":"EVN"}'
SUPPRESS = '{"title":"Търговски условия","issuer":"EVN"}'
SETTINGS = {'model': 'mock', 'model_revision': 'a' * 40, 'dpi': 150,
            'align_confirmation': False, 'code': {'eval_boundaries.py': 'base',
            'evn_sections.py': 'rule', 'run_evn_experiment.py': 'runner'}}


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        pdf_file(self.root / 'a.pdf', 4)
        self.sources = {'a.pdf': source_identity(self.root / 'a.pdf')}
        self.requests = [{'file': 'a.pdf', 'page': 2, 'rotation': 90},
                         {'file': 'a.pdf', 'page': 3, 'rotation': None}]
        self.image = Mock()
        self.pipeline = types.SimpleNamespace(load_model=Mock(return_value=(None, None, None)),
            _load_page=Mock(return_value=self.image), _query_rotation=Mock(return_value=0),
            _infer=Mock(side_effect=[KEEP, SUPPRESS]))

    def extract(self, settings=None, required=None):
        with patch.object(runner, 'preflight'):
            return runner.extract_pages(self.root, self.requests, self.sources,
                settings or SETTINGS, self.root / 'run', {'test': 'frozen'}, self.pipeline, LOG, required)

    def test_resume_retains_completed_page_and_needs_no_gpu_when_complete(self):
        self.pipeline._infer.side_effect = [KEEP, RuntimeError('CUDA out of memory')]
        with self.assertRaisesRegex(RuntimeError, 'CUDA'):
            self.extract()
        self.assertEqual(json.loads((self.root / 'run/run.json').read_text())['status'], 'failed')
        self.assertEqual(len(list((self.root / 'run/pages').glob('*.json'))), 1)
        self.pipeline._infer.reset_mock(side_effect=True)
        self.pipeline._infer.return_value = SUPPRESS
        records = self.extract()
        self.assertEqual([r['action'] for r in records], ['keep', 'suppress'])
        self.pipeline._infer.assert_called_once()
        self.pipeline.load_model.reset_mock()
        self.pipeline._infer.reset_mock()
        self.assertEqual(self.extract(), records)
        self.pipeline.load_model.assert_not_called()
        self.pipeline._infer.assert_not_called()

    def test_reuses_baseline_rotation_and_queries_osd_only_when_unspecified(self):
        self.extract()
        self.image.rotate.assert_called_once_with(90, expand=True)
        self.pipeline._query_rotation.assert_called_once()
        first_images = self.pipeline._infer.call_args_list[0].args[1]
        self.assertEqual(first_images, [self.image.rotate.return_value])
        self.pipeline.load_model.assert_called_once_with('mock', LOG, revision='a' * 40)

    def test_changed_code_refuses_cache(self):
        self.extract()
        changed = copy.deepcopy(SETTINGS)
        changed['code']['evn_sections.py'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'inputs/code changed'):
            self.extract(changed)

    def test_invalid_json_keeps_boundary_but_does_not_hide_transport_errors(self):
        self.pipeline._infer.side_effect = ['not json', KEEP]
        records = self.extract()
        self.assertEqual(records[0]['action'], 'keep')
        self.assertEqual(records[0]['evidence']['status'], 'abstain')

    def test_cached_metadata_cannot_reassign_evidence_or_corrupt_cost(self):
        self.extract()
        path = next((self.root / 'run/pages').glob('*.json'))
        original = json.loads(path.read_text())
        for key, value in [('page', 99), ('file', 'other.pdf'), ('rotation', 90.5),
                           ('seconds', float('nan')), ('seconds', -1), ('model_calls', 0), ('version', 2)]:
            with self.subTest(key=key, value=value):
                # Simulate an externally damaged cache, including nonstandard NaN JSON.
                path.write_text(json.dumps({**original, key: value}))
                with self.assertRaisesRegex(ValueError, 'checkpoint'):
                    self.extract()
                atomic_json(path, original)

    def test_required_baseline_model_identity_applies_to_fresh_and_cached_work(self):
        with self.assertRaisesRegex(ValueError, 'Model revision/GPU'):
            self.extract(required={'model_commit': 'other'})
        # Use a new run directory after the deliberately incompatible model attempt.
        self.root = self.root / 'second'
        self.root.mkdir()
        pdf_file(self.root / 'a.pdf', 4)
        self.sources = {'a.pdf': source_identity(self.root / 'a.pdf')}
        self.extract()
        with self.assertRaisesRegex(ValueError, 'Cached model/GPU'):
            self.extract(required={'model_commit': 'other'})

    def test_source_changes_during_inference_are_not_checkpointed(self):
        def change_source(*args, **kwargs):
            pdf_file(self.root / 'a.pdf', 5)
            return KEEP
        self.pipeline._infer.side_effect = change_source
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            self.extract()
        self.assertFalse(list((self.root / 'run/pages').glob('*.json')))


class PairedTests(unittest.TestCase):
    def test_current_evaluator_checkpoint_is_accepted_without_using_labels_to_select_cuts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_file(root / 'a.pdf', 4)
            gt = {'a.pdf': [1, 4]}
            atomic_json(root / 'ground_truth.json', gt)
            base_settings = copy.deepcopy(SETTINGS)
            base_settings['code'] = {'eval_boundaries.py': 'base'}
            pipeline = types.SimpleNamespace(load_model=Mock(return_value=(None, None, None)),
                detect_boundaries=Mock(return_value=([boundary(1), boundary(2), boundary(3)], {2: 90})))
            with patch.object(eval_boundaries, 'preflight'), contextlib.redirect_stdout(io.StringIO()):
                eval_boundaries.run_predictions(root, gt, root / 'baseline', base_settings, pipeline, LOG)
            result = runner.load_baseline(root, root / 'baseline', SETTINGS)
            self.assertEqual(result[0], {'a.pdf': {2, 3}})
            self.assertEqual(result[2], [{'file': 'a.pdf', 'page': 2, 'rotation': 90},
                                         {'file': 'a.pdf', 'page': 3, 'rotation': 0}])
            changed = copy.deepcopy(SETTINGS)
            changed['dpi'] = 200
            with self.assertRaisesRegex(ValueError, 'different code/runtime'):
                runner.load_baseline(root, root / 'baseline', changed)
            path = next((root / 'baseline/predictions').glob('*.json'))
            cached = json.loads(path.read_text())
            cached['rotations_ccw_for_inference']['2'] = 90.9
            atomic_json(path, cached)
            with self.assertRaisesRegex(ValueError, 'Invalid baseline rotations'):
                runner.load_baseline(root, root / 'baseline', SETTINGS)

    def test_only_existing_cuts_are_removed_and_scores_show_true_cut_regressions(self):
        records = [{'file': 'a.pdf', 'page': p, 'action': a, 'seconds': 1, 'evidence': {}}
                   for p, a in [(2, 'suppress'), (3, 'keep')]]
        args = ({'a.pdf': [1, 3]}, {'a.pdf': {2, 3}}, {'a.pdf': 4}, {}, {'a.pdf': 'held'})
        candidate, report = runner.compare_predictions(*args, records, 10)
        self.assertEqual(candidate, {'a.pdf': {3}})
        self.assertGreater(report['f1_delta'], 0)
        self.assertEqual(report['exact_documents_delta'], 1)
        self.assertEqual(report['overhead_fraction'], .2)
        self.assertFalse(report['promotion_ready'])
        records[0]['action'], records[1]['action'] = 'keep', 'suppress'
        _, regression = runner.compare_predictions(*args, records, 10)
        self.assertLess(regression['f1_delta'], 0)
        self.assertTrue(regression['changed_starts'][0]['true_start'])
        with self.assertRaisesRegex(ValueError, 'every proposed cut'):
            runner.compare_predictions(*args, records[:1], 10)

    def test_page_one_cannot_be_removed(self):
        with self.assertRaisesRegex(ValueError, 'Mandatory page 1'):
            runner.compare_predictions({'a.pdf': [1]}, {'a.pdf': {1}}, {'a.pdf': 4}, {},
                {'a.pdf': 'held'}, [{'file': 'a.pdf', 'page': 1, 'action': 'suppress'}], 1)


class ProbeTests(unittest.TestCase):
    def test_frozen_evidence_replay_and_gate_failures(self):
        spec = json.loads((Path(__file__).parents[1] / 'data/evn_probe_v1.json').read_text())
        records = []
        for case in spec['cases']:
            cached = case['cached_marker']
            evidence = parse_evidence(json.dumps({k: cached[k] or '' for k in ('title', 'issuer')}))
            records.append({'file': case['file'], 'page': case['page'], 'evidence': evidence,
                'action': 'suppress' if should_suppress(evidence) else 'keep', 'seconds': 1, 'model_calls': 1})
        result = runner.summarize_probe(spec, records)
        self.assertTrue(result['passed'])
        self.assertEqual(result['model_calls'], 12)
        self.assertEqual(sum(r['action'] == 'suppress' for r in records), 2)
        records[0]['action'] = 'suppress'
        self.assertFalse(runner.summarize_probe(spec, records)['passed'])
        records[0]['action'] = 'keep'
        records[0]['evidence'] = parse_evidence('malformed')
        self.assertFalse(runner.summarize_probe(spec, records)['passed'])
        with self.assertRaisesRegex(ValueError, 'cover the frozen'):
            runner.summarize_probe(spec, records[:-1])

    def test_probe_sources_are_hash_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_file(root / 'a.pdf', 3)
            spec = {'version': 1, 'sources': {'a.pdf': {**source_identity(root / 'a.pdf'), 'total_pages': 3}},
                    'cases': [{'file': 'a.pdf', 'page': 2, 'expected_action': 'keep'}]}
            requests, _ = runner.probe_requests(root, spec)
            self.assertEqual(requests, [{'file': 'a.pdf', 'page': 2, 'rotation': None}])
            pdf_file(root / 'a.pdf', 4)
            with self.assertRaisesRegex(ValueError, 'source changed'):
                runner.probe_requests(root, spec)
