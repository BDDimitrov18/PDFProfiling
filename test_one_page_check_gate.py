"""Round-3 Commit D (#1-lite v2) — unit tests for the one-page-check gating predicate.
split._one_page_check_applies must be False for the closing-page signals (signature_block,
table_end) at BOTH call sites, True otherwise. Run: python3 -m unittest test_one_page_check_gate -v"""
import unittest
from split import _one_page_check_applies as A


class TestOnePageCheckGate(unittest.TestCase):
    def test_closing_signals_gated(self):
        self.assertFalse(A("signature_block"))   # structural-symmetry fallacy -> FP31
        self.assertFalse(A("table_end"))

    def test_project_signoff_not_gated(self):
        # spec: only signature_block/table_end gated; project_signoff still runs the check
        self.assertTrue(A("project_signoff"))

    def test_start_and_other_signals_not_gated(self):
        for s in ("titled_id_header", "fresh_letterhead", "header_block_reset",
                  "appendix_heading", "blank_form", "page_number_reset", "stamp_change", "none"):
            self.assertTrue(A(s), f"{s} must not be gated")

    def test_both_sites_use_same_predicate(self):
        # contract: both call sites gate on this single predicate -> v1's reroute (FP21) impossible
        import inspect, split
        src = inspect.getsource(split.detect_boundaries)
        self.assertEqual(src.count("_one_page_check_applies(signal)"), 2,
                         "both one-page-check sites (n+1 AND OOB-projection) must gate on the predicate")


if __name__ == "__main__":
    unittest.main(verbosity=2)
