import contextlib
import io
import json
import logging
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from eval_data import corrected_reference, derive_starts, discover_originals, gap_runs, link_original
import eval_boundaries
from production_state import atomic_json, file_hash
from score_full import evaluate, load_preds
from test_reliability import pdf_file, boundary, SETTINGS

LOG = logging.getLogger('unit-evaluation')
LOG.addHandler(logging.NullHandler())


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf = pdf_file(self.root / 'Image_scan.pdf', 6)

    def test_gap_starts_and_gap_masks_are_distinct(self):
        pdf_file(self.root / '1_PDFsam_Image_scan.pdf', 2)
        pdf_file(self.root / '5_PDFsam_Image_scan.pdf', 2)
        self.assertEqual(derive_starts(self.pdf), [1, 3, 5])
        self.assertEqual(gap_runs(self.pdf), [[3, 4]])

    def test_unlabelled_is_excluded_but_one_document_is_included(self):
        self.assertEqual(derive_starts(self.pdf), [])
        pdf_file(self.root / '1_PDFsam_Image_scan.pdf', 6)
        self.assertEqual(derive_starts(self.pdf), [1])

    def test_human_correction_is_bound_to_exact_source_bytes(self):
        rule = {self.pdf.name: {'source_sha256': file_hash(self.pdf), 'add': [3], 'remove': [5], 'unmask_gaps': True}}
        self.assertEqual(corrected_reference(self.pdf, [1, 5], rule), ([1, 3], True))
        pdf_file(self.pdf, 7)
        with self.assertRaisesRegex(ValueError, 'needs review'):
            corrected_reference(self.pdf, [1, 5], rule)

    def test_reference_cannot_extend_beyond_source(self):
        pdf_file(self.root / '5_PDFsam_Image_scan.pdf', 3)
        with self.assertRaises(ValueError):
            derive_starts(self.pdf)

    def test_original_discovery_includes_flat_case_and_excludes_derived(self):
        nested = pdf_file(self.root / 'case' / '1' / 'Image_other.pdf', 1)
        pdf_file(self.root / 'split' / 'Image_output.pdf', 1)
        pdf_file(self.root / '.hidden' / 'Image_output.pdf', 1)
        pdf_file(self.root / '1_PDFsam_Image_scan.pdf', 6)
        self.assertEqual(set(discover_originals(self.root)), {self.pdf, nested})

    def test_symlink_builder_does_not_replace_regular_files(self):
        out = self.root / 'eval'
        out.mkdir()
        link_original(self.pdf, out)
        link_original(self.pdf, out)
        self.assertEqual((out / self.pdf.name).resolve(), self.pdf.resolve())
        (out / self.pdf.name).unlink()
        (out / self.pdf.name).write_text('keep me')
        with self.assertRaises(ValueError):
            link_original(self.pdf, out)


class ScoringTests(unittest.TestCase):
    def report(self, gt, preds, masks=None):
        return evaluate(gt, preds, masks or {}, {n: 'dev' for n in gt}, {n: 6 for n in gt})['by_stratum']['aggregate']

    def test_missing_and_extra_predictions_are_errors(self):
        with self.assertRaisesRegex(ValueError, 'coverage'):
            self.report({'a.pdf': [1, 3]}, {})
        with self.assertRaisesRegex(ValueError, 'coverage'):
            self.report({'a.pdf': [1, 3]}, {'a.pdf': {3}, 'extra.pdf': {2}})

    def test_exact_documents_require_no_interior_cut(self):
        result = self.report({'a.pdf': [1, 3, 5]}, {'a.pdf': {2, 3, 5}})
        self.assertEqual((result['TP'], result['FP'], result['FN']), (2, 1, 0))
        self.assertEqual((result['docs_exact'], result['docs_total']), (2, 3))
        self.assertEqual(result['source_exact'], 0)

    def test_masks_exclude_unknown_seams_from_both_sides(self):
        result = self.report({'a.pdf': [1, 3, 5]}, {'a.pdf': {4, 5}}, {'a.pdf': [[3, 4]]})
        self.assertEqual((result['TP'], result['FP'], result['FN']), (1, 0, 0))
        self.assertEqual((result['docs_exact'], result['docs_total'], result['docs_excluded']), (1, 1, 2))

    def test_page_one_is_not_a_cut_and_one_document_can_be_exact(self):
        result = self.report({'a.pdf': [1]}, {'a.pdf': {1}})
        self.assertEqual((result['TP'], result['FP'], result['FN']), (0, 0, 0))
        self.assertEqual((result['docs_exact'], result['docs_total']), (1, 1))

    def test_out_of_range_predictions_fail_before_scoring(self):
        with self.assertRaises(ValueError):
            self.report({'a.pdf': [1]}, {'a.pdf': {7}})

    def test_old_json_is_rescored_without_trusting_its_embedded_truth(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'results.json'
            atomic_json(path, {'by_tolerance': {'0': {'per_file': [
                {'file': 'a.pdf', 'pred': [3], 'true': [2], 'fp': [3], 'fn': [2]}]}}})
            result = self.report({'a.pdf': [1, 3]}, load_preds(path))
            self.assertEqual(result['f1'], 1)

    def test_duplicate_log_blocks_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'run.log'
            path.write_text('a.pdf\n pred=[3]\na.pdf\n pred=[4]\n')
            with self.assertRaises(ValueError):
                load_preds(path)


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run_dir = self.root / 'run'
        self.gt = {'a.pdf': [1, 3], 'b.pdf': [1, 3]}
        for n in self.gt:
            pdf_file(self.root / n, 5)
        atomic_json(self.root / 'ground_truth.json', self.gt)
        self.pipeline = types.SimpleNamespace(load_model=Mock(return_value=(None, None, None)),
            detect_boundaries=Mock(return_value=([boundary(1), boundary(3)], {})))

    def run_predictions(self, settings=SETTINGS):
        with patch.object(eval_boundaries, 'preflight'), contextlib.redirect_stdout(io.StringIO()):
            return eval_boundaries.run_predictions(self.root, self.gt, self.run_dir, settings, self.pipeline, LOG)

    def test_resume_runs_only_unfinished_pdf_and_final_cache_needs_no_gpu(self):
        self.pipeline.detect_boundaries.side_effect = [([boundary(1), boundary(3)], {}), RuntimeError('GPU failed')]
        with self.assertRaises(RuntimeError):
            self.run_predictions()
        self.assertEqual(json.loads((self.run_dir / 'run.json').read_text())['status'], 'failed')
        self.assertEqual(len(list((self.run_dir / 'predictions').glob('*.json'))), 1)
        self.pipeline.detect_boundaries.reset_mock(side_effect=True)
        preds, totals = self.run_predictions()
        self.assertEqual(preds, {'a.pdf': {3}, 'b.pdf': {3}})
        self.assertEqual(totals, {'a.pdf': 5, 'b.pdf': 5})
        self.pipeline.detect_boundaries.assert_called_once()
        self.pipeline.load_model.reset_mock()
        self.pipeline.detect_boundaries.reset_mock()
        self.run_predictions()
        self.pipeline.load_model.assert_not_called()
        self.pipeline.detect_boundaries.assert_not_called()

    def test_changed_code_settings_or_source_cannot_mix_experiments(self):
        self.run_predictions()
        with self.assertRaisesRegex(ValueError, 'different inputs'):
            self.run_predictions({**SETTINGS, 'align_confirmation': True})
        pdf_file(self.root / 'b.pdf', 6)
        with self.assertRaisesRegex(ValueError, 'different inputs'):
            self.run_predictions()

    def test_new_labels_can_rescore_same_predictions_without_gpu(self):
        self.run_predictions()
        self.gt['a.pdf'] = [1, 2, 3]
        atomic_json(self.root / 'ground_truth.json', self.gt)
        self.pipeline.load_model.reset_mock()
        self.run_predictions()
        self.pipeline.load_model.assert_not_called()

    def test_invalid_checkpoint_is_not_silently_used(self):
        self.run_predictions()
        path = next((self.run_dir / 'predictions').glob('*.json'))
        record = json.loads(path.read_text())
        record['starts'] = [1, 99]
        atomic_json(path, record)
        with self.assertRaisesRegex(ValueError, 'Invalid prediction'):
            self.run_predictions()


class ConfirmationAuditTests(unittest.TestCase):
    def test_reconstructs_backward_and_forward_pairs_from_actual_log_format(self):
        from audit_confirmation import audit
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / 'run.log'
            log.write_text('''12:00:00 [INFO]   Phase 1: end-of-document detection (5 pages)…
12:00:00 [INFO]   p2: end=True, signal=table_end, signal_on_page=1, conf=60%
12:00:00 [INFO]   Low-conf boundary at p2 confirmed — averaged conf=80%
12:00:00 [INFO]   p3: end=True, signal=table_end, signal_on_page=4, conf=60%
12:00:00 [INFO]   Low-conf boundary at p3 (60%) rejected by confirmation pass
Image_test.pdf
  pred=[2]
''')
            report = audit(log)
            self.assertEqual(report['confirmations'], 2)
            self.assertEqual(report['relocated_in_range'], 2)
            self.assertEqual([e['actual_pair'] for e in report['events']], [[1, 2], [4, 5]])

    def test_interrupted_log_cannot_hide_unattributed_confirmations(self):
        from audit_confirmation import audit
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / 'run.log'
            log.write_text('''Phase 1: end-of-document detection (3 pages)
p1: end=True, signal=table_end, signal_on_page=1, conf=60%
Low-conf boundary at p1 confirmed — averaged conf=80%
''')
            with self.assertRaisesRegex(ValueError, 'Trailing confirmations'):
                audit(log)
