import contextlib
import io
import json
import logging
import os
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch, Mock

from pypdf import PdfReader, PdfWriter
import production_state as state
import run_production as production
import split

LOG = logging.getLogger('unit-reliability')
LOG.addHandler(logging.NullHandler())
SETTINGS = {'model': 'fake', 'dpi': 150, 'align_confirmation': False}


def pdf_file(path, pages=5):
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for n in range(pages):
        writer.add_blank_page(width=100 + n, height=200)
    with path.open('wb') as stream:
        writer.write(stream)
    return path


def boundary(page, confidence=.9):
    return split.DocumentBoundary(page, 0, '', confidence)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf = pdf_file(self.root / 'scan[1].pdf')
        self.output = self.root / 'split'
        self.source = state.source_identity(self.pdf)
        self.boundaries = [boundary(1, 1), boundary(3, .6)]

    def publish(self, split_fn=split.split_pdf, boundaries=None):
        with state.source_lock(self.pdf, self.output):
            return state.publish(self.pdf, self.output, self.source, SETTINGS, 5,
                                 boundaries or self.boundaries, {2: 90}, split_fn, LOG)

    def complete(self):
        return state.is_complete(self.pdf, self.output, self.source, SETTINGS)

    def test_publication_conserves_page_order_and_records_review(self):
        record = self.publish()
        self.assertTrue(self.complete())
        self.assertEqual([(s['start_page'], s['end_page']) for s in record['segments']], [(1, 2), (3, 5)])
        self.assertEqual([s['needs_review'] for s in record['segments']], [False, True])
        widths = [int(p.mediabox.width) for s in record['segments'] for p in PdfReader(self.output / s['file']).pages]
        self.assertEqual(widths, [100, 101, 102, 103, 104])
        self.assertEqual(record['segments'][0]['file'], 'scan[1]_001_00000_.pdf')
        self.assertEqual(record['rotations_ccw_for_inference'], {2: 90})

    def test_legacy_partial_output_is_not_completion_and_is_preserved(self):
        self.output.mkdir()
        old = pdf_file(self.output / 'scan[1]_001_00000_.pdf', 1)
        old_hash = state.file_hash(old)
        self.assertFalse(self.complete())
        self.publish()
        self.assertTrue(self.complete())
        archived = [p for p in (self.output / '.history').rglob('*.pdf') if p.name == old.name]
        self.assertEqual([state.file_hash(p) for p in archived], [old_hash])

    def test_staging_failure_keeps_previous_complete_set(self):
        self.publish()
        marker = state.manifest_path(self.pdf, self.output).read_bytes()
        def fail(pdf, boundaries, staging, logger):
            split.split_pdf(pdf, boundaries, staging, logger)
            raise OSError('disk full')
        with self.assertRaises(OSError):
            self.publish(fail)
        self.assertTrue(self.complete())
        self.assertEqual(state.manifest_path(self.pdf, self.output).read_bytes(), marker)

    def test_mid_publication_failure_cannot_be_skipped_and_recovers(self):
        self.publish()
        replace = os.replace
        writes = []
        def interrupted(src, dst):
            if Path(dst).parent == self.output and Path(dst).suffix == '.pdf':
                writes.append(dst)
                if len(writes) == 2:
                    raise OSError('interrupted publication')
            return replace(src, dst)
        with patch.object(state.os, 'replace', side_effect=interrupted), self.assertRaises(OSError):
            self.publish()
        self.assertFalse(self.complete())
        self.publish()
        self.assertTrue(self.complete())
        self.assertTrue(list((self.output / '.history').rglob('completion.json')))

    def test_corruption_extra_files_and_settings_invalidate_resume(self):
        record = self.publish()
        self.assertFalse(state.is_complete(self.pdf, self.output, self.source, {**SETTINGS, 'dpi': 120}))
        extra = pdf_file(self.output / 'scan[1]_003_00000_.pdf', 1)
        self.assertFalse(self.complete())
        extra.unlink()
        (self.output / record['segments'][0]['file']).write_bytes(b'broken')
        self.assertFalse(self.complete())

    def test_source_change_invalidates_resume_and_publication(self):
        self.publish()
        pdf_file(self.pdf, 6)
        self.assertFalse(state.is_complete(self.pdf, self.output, state.source_identity(self.pdf), SETTINGS))
        with self.assertRaises(ValueError):
            self.publish()

    def test_incomplete_split_or_invalid_boundaries_never_commit(self):
        def short(pdf, boundaries, staging, logger):
            return [pdf_file(staging / 'scan[1]_001_00000_.pdf', 1)]
        with self.assertRaises(ValueError):
            self.publish(short)
        for starts in ([2], [1, 1], [1, 6], [1, 4, 3]):
            with self.subTest(starts=starts), self.assertRaises(ValueError):
                self.publish(boundaries=[boundary(p) for p in starts])
        self.assertFalse(self.complete())

    def test_os_lock_prevents_overlapping_workers_and_releases(self):
        with state.source_lock(self.pdf, self.output):
            with self.assertRaises(RuntimeError):
                with state.source_lock(self.pdf, self.output):
                    self.fail('lock allowed overlapping worker')
        with state.source_lock(self.pdf, self.output):
            pass

    def test_batch_failure_then_retry_and_cached_run_without_model(self):
        pipeline = types.SimpleNamespace(PdfReader=PdfReader, CONFIDENCE_THRESHOLD=.8,
            load_model=Mock(return_value=(None, None, None)),
            detect_boundaries=Mock(return_value=(self.boundaries, {})),
            split_pdf=Mock(side_effect=OSError('disk full')))
        output = io.StringIO()
        with patch.object(production, 'preflight'), contextlib.redirect_stdout(output):
            self.assertEqual(production.run([self.pdf], self.root, pipeline, LOG, SETTINGS), 1)
            self.assertNotIn('PRODUCTION_DONE', output.getvalue())
            pipeline.split_pdf = split.split_pdf
            self.assertEqual(production.run([self.pdf], self.root, pipeline, LOG, SETTINGS), 0)
            pipeline.load_model.reset_mock()
            pipeline.detect_boundaries.reset_mock()
            self.assertEqual(production.run([self.pdf], self.root, pipeline, LOG, SETTINGS), 0)
            pipeline.load_model.assert_not_called()
            pipeline.detect_boundaries.assert_not_called()

    def test_bad_source_does_not_prevent_later_sources_from_completing(self):
        bad = self.root / 'bad.pdf'
        bad.write_bytes(b'%PDF-1.4 invalid')
        pipeline = types.SimpleNamespace(PdfReader=PdfReader, CONFIDENCE_THRESHOLD=.8,
            load_model=Mock(return_value=(None, None, None)),
            detect_boundaries=Mock(return_value=(self.boundaries, {})), split_pdf=split.split_pdf)
        with patch.object(production, 'preflight'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(production.run([bad, self.pdf], self.root, pipeline, LOG, SETTINGS), 1)
        self.assertTrue(self.complete())
        pipeline.load_model.assert_called_once()

    def test_discovery_nested_flat_and_exact_shards(self):
        second = pdf_file(self.root / 'nested' / 'second.PDF', 1)
        pdf_file(self.output / 'skip.pdf', 1)
        pdf_file(self.root / '.history' / 'skip.pdf', 1)
        self.assertEqual(set(production.discover(self.root)), {self.pdf, second})
        shard = self.root / 'shard.txt'
        shard.write_text('nested/second.PDF\n')
        self.assertEqual(production.discover(self.root, shard), [second])
        shard.write_text('typo.pdf\n')
        with self.assertRaises(ValueError):
            production.discover(self.root, shard)


class SupervisorTests(unittest.TestCase):
    def test_uses_exit_status_even_when_stdout_claims_done(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = root / 'fake-python'
            counter = root / 'attempts'
            fake.write_text('#!/bin/bash\necho attempt >> "$COUNTER"\necho PRODUCTION_DONE 1/1\nexit "$FAKE_EXIT"\n')
            fake.chmod(0o755)
            env = {**os.environ, 'PRODUCTION_ATTEMPTS': '2', 'PRODUCTION_RETRY_SECONDS': '0',
                   'PRODUCTION_PYTHON': str(fake), 'COUNTER': str(counter)}
            for status, attempts in [('1', 2), ('0', 1), ('2', 1), ('130', 1)]:
                counter.write_text('')
                run = subprocess.run(['bash', 'supervisor.sh', str(root)], env={**env, 'FAKE_EXIT': status}, capture_output=True)
                self.assertEqual(run.returncode, int(status))
                self.assertEqual(len(counter.read_text().splitlines()), attempts)

    def test_inference_exception_propagates_instead_of_becoming_a_negative_prediction(self):
        torch = types.SimpleNamespace()
        vision = types.SimpleNamespace(process_vision_info=Mock())
        processor = Mock()
        processor.apply_chat_template.side_effect = RuntimeError('CUDA out of memory')
        with patch.dict('sys.modules', {'torch': torch, 'qwen_vl_utils': vision}):
            with self.assertRaisesRegex(RuntimeError, 'must be retried'):
                split._infer('prompt', [], None, processor, None, LOG)
