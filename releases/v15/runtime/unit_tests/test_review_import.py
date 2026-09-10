import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from build_review_eval import build
from production_state import atomic_json, file_hash
from test_reliability import pdf_file


class HumanReviewImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.corpus = self.root / 'corpus'
        self.pdf = pdf_file(self.corpus / 'case' / 'Image_scan.pdf', 5)
        self.labels = self.root / 'labels.json'
        self.output = self.root / 'eval'
        self.reference = {'version': 1, 'id': 'review-v1', 'label_status': 'human_confirmed',
                          'purpose': 'validation', 'review_evidence': {'message': 'Starts 1, 3'},
                          'files': {self.pdf.name: {'source': 'case/Image_scan.pdf',
                              'source_sha256': file_hash(self.pdf), 'total_pages': 5,
                              'starts': [1, 3], 'review_id': '01', 'case_group': 'case'}}}

    def run_build(self):
        atomic_json(self.labels, self.reference)
        with contextlib.redirect_stdout(io.StringIO()):
            return build(self.labels, self.corpus, self.output)

    def test_confirmed_reference_builds_and_can_be_rebuilt_without_inference(self):
        expected = {self.pdf.name: [1, 3]}
        self.assertEqual(self.run_build(), expected)
        self.assertEqual(self.run_build(), expected)
        self.assertEqual(json.loads((self.output / 'ground_truth.json').read_text()), expected)
        self.assertEqual((self.output / self.pdf.name).resolve(), self.pdf.resolve())
        self.assertEqual(file_hash(self.pdf), self.reference['files'][self.pdf.name]['source_sha256'])

    def test_unreviewed_automatic_outputs_cannot_become_labels(self):
        self.reference['label_status'] = 'unreviewed_automatic_outputs'
        with self.assertRaisesRegex(ValueError, 'human-confirmed'):
            self.run_build()
        self.assertFalse(self.output.exists())

    def test_existing_predictions_are_preserved_separately_from_reviewed_starts(self):
        self.reference['files'][self.pdf.name]['existing_automatic_starts'] = [1, 2, 3]
        self.run_build()
        self.assertEqual(json.loads((self.output / 'ground_truth.json').read_text()), {self.pdf.name: [1, 3]})
        predictions = json.loads((self.output / 'existing_automatic_predictions.json').read_text())
        self.assertEqual(predictions['by_tolerance']['0']['per_file'], [{'file': self.pdf.name, 'pred': [2, 3]}])
        self.assertFalse(predictions['provenance']['new_inference'])

    def test_changed_source_rejects_previously_attested_labels(self):
        pdf_file(self.pdf, 6)
        with self.assertRaisesRegex(ValueError, 'has changed'):
            self.run_build()
        self.assertFalse(self.output.exists())

    def test_invalid_start_lists_are_rejected_before_publication(self):
        for starts in ([2, 3], [1, 6], [1, 3, 3], [1, 4, 2], [1, True]):
            with self.subTest(starts=starts):
                self.reference['files'][self.pdf.name]['starts'] = starts
                with self.assertRaises(ValueError):
                    self.run_build()
                self.assertFalse(self.output.exists())

    def test_existing_regular_file_is_preserved(self):
        self.output.mkdir()
        target = self.output / self.pdf.name
        target.write_text('keep this file')
        with self.assertRaisesRegex(ValueError, 'regular file'):
            self.run_build()
        self.assertEqual(target.read_text(), 'keep this file')
