import contextlib
import logging
from pathlib import Path
import unittest
from unittest.mock import patch
import split

LOG = logging.getLogger('unit-confirmation')
LOG.addHandler(logging.NullHandler())


class Page:
    def __init__(self, number, rotation=0):
        self.number, self.rotation = number, rotation

    def rotate(self, angle, expand=True):
        return Page(self.number, angle)


class ConfirmationTests(unittest.TestCase):
    def detect(self, signal_page, align, confirmed=True, total=5, self_contained=False, signal='table_end'):
        confirms, loaded, rotations = [], [], []
        def load(pdf, page, dpi):
            self.assertTrue(1 <= page <= total)
            loaded.append(page)
            return Page(page)
        def rotate(image, page, *args):
            rotations.append(page)
            return 90 if page == 4 else 0
        def end(images, pages, n, *args):
            return (True, .6, signal, signal_page) if n == 2 else (False, .9, 'none', n)
        def confirm(left, right, a, b, *args):
            self.assertEqual((left.number, right.number), (a, b))
            if b == 4:
                self.assertEqual(right.rotation, 90)
            confirms.append((a, b))
            return confirmed, .9
        mocks = {'_load_page': load, '_query_rotation': rotate, '_query_document_end': end,
                 '_query_style_continuity': lambda *a: {'letterhead_match': True, 'layout_type_prev': 'text', 'layout_type_curr': 'text'},
                 '_query_confirm_boundary': confirm, '_query_starts_new_document': lambda *a: (False, .9, ''),
                 '_query_is_self_contained': lambda *a: (self_contained, .9),
                 'smooth_rotation_log': lambda rotations, logger: rotations}
        with contextlib.ExitStack() as stack:
            for name, function in mocks.items():
                stack.enter_context(patch.object(split, name, function))
            result, _ = split.detect_boundaries(Path('fake.pdf'), total, None, None, None, 150, LOG,
                                                classify=False, align_confirmation=align)
        return [b.page for b in result], confirms, loaded, rotations

    def test_backward_relocation_confirms_actual_adjacent_pages(self):
        starts, confirms, *_ = self.detect(1, True)
        self.assertEqual(starts, [1, 2])
        self.assertEqual(confirms, [(1, 2)])

    def test_forward_relocation_loads_and_rotates_fourth_page_once(self):
        starts, confirms, loaded, rotations = self.detect(3, True)
        self.assertEqual(starts, [1, 4])
        self.assertEqual(confirms, [(3, 4)])
        self.assertEqual(loaded.count(4), 1)
        self.assertEqual(rotations.count(4), 1)

    def test_default_retains_historical_confirmation_pair(self):
        for signal_page, starts in [(1, [1, 2]), (2, [1, 3]), (3, [1, 4])]:
            result, confirms, *_ = self.detect(signal_page, False)
            self.assertEqual(result, starts)
            self.assertEqual(confirms, [(2, 3)])

    def test_same_seam_and_self_contained_projection_keep_pair(self):
        for page, self_contained in [(2, False), (3, True)]:
            starts, confirms, *_ = self.detect(page, True, self_contained=self_contained)
            self.assertEqual(starts, [1, 3])
            self.assertEqual(confirms, [(2, 3)])

    def test_rejected_confirmation_cannot_record_relocated_cut(self):
        starts, confirms, *_ = self.detect(3, True, confirmed=False)
        self.assertEqual(starts, [1])
        self.assertEqual(confirms, [(3, 4)])

    def test_last_page_continuation_cannot_request_page_beyond_source(self):
        starts, confirms, *_ = self.detect(3, True, total=3)
        self.assertEqual(starts, [1])
        self.assertEqual(confirms, [])

    def test_strong_header_stays_exempt(self):
        starts, confirms, *_ = self.detect(3, True, signal='fresh_letterhead')
        self.assertEqual(starts, [1, 3])
        self.assertEqual(confirms, [])
