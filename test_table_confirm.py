"""Round-3 Commit C / Fix 11 v2 + Round-5 Fix 11 v3 — unit tests for the table-boundary decisions.
Pure tests of split._table_boundary_decision (v2) and _table_boundary_decision_v3 (guarded); no GPU.
Run: python3 -m unittest test_table_confirm -v"""
import unittest
from split import _table_boundary_decision as T
from split import _table_boundary_decision_v3 as V3


class TestTableBoundary(unittest.TestCase):
    def test_continuous_suppresses(self):
        confirmed, _ = T(5, 6)
        self.assertFalse(confirmed)          # 5->6 continuous = same table, NOT a boundary

    def test_reset_stands(self):
        confirmed, _ = T(12, 1)              # new table resets to 1 (FN20-class)
        self.assertTrue(confirmed)

    def test_jump_stands(self):
        self.assertTrue(T(5, 10)[0])

    def test_not_plus_one_stands(self):
        self.assertTrue(T(5, 5)[0])          # repeat, not continuous
        self.assertTrue(T(5, 4)[0])          # decrease

    def test_unreadable_stands(self):
        # the whole point of v2: never reject a real table boundary on missing evidence
        self.assertTrue(T(None, None)[0])
        self.assertTrue(T(5, None)[0])
        self.assertTrue(T(None, 1)[0])

    def test_only_suppresses_on_proven_continuity(self):
        # exhaustive: the ONLY suppress case is both-present-and-consecutive
        suppress_cases = [(n, n + 1) for n in range(1, 30)]
        for last, first in suppress_cases:
            self.assertFalse(T(last, first)[0], f"{last}->{first} should suppress")
        stand_cases = [(12, 1), (5, 10), (5, 5), (None, None), (3, None), (None, 4), (7, 6)]
        for last, first in stand_cases:
            self.assertTrue(T(last, first)[0], f"{last}->{first} should stand")


class TestTableBoundaryV3(unittest.TestCase):
    """Fix 11 v3 GUARD: a non-continuous/unreadable numbering break STANDS only with a start-side
    cue on n+1; bare gaps inside a doc (FP35/37@163444215) suppress. Continuous always suppresses."""

    def test_continuous_suppresses_regardless_of_cue(self):
        self.assertFalse(V3(5, 6, True)[0])      # same table even if a cue is present
        self.assertFalse(V3(5, 6, False)[0])

    def test_bare_numbering_gap_no_cue_suppresses(self):
        # THE GUARD — the FP35 (8->5) and FP37 (10->1) intra-doc gaps @163444215 must NOT cut
        self.assertFalse(V3(8, 5, False)[0])     # FP35-class
        self.assertFalse(V3(10, 1, False)[0])    # FP37-class (reset, but bare)
        self.assertFalse(V3(5, 10, False)[0])    # jump, bare

    def test_numbering_gap_with_cue_stands(self):
        # real new table doc carrying a corroborating start-side cue (TP20-class)
        self.assertTrue(V3(6, 1, True)[0])       # TP20: reset + fresh start cue
        self.assertTrue(V3(8, 5, True)[0])
        self.assertTrue(V3(31, 2, True)[0])

    def test_unreadable_requires_cue(self):
        # v3 reverses v2 here: no proof of continuity AND no start cue -> do NOT cut
        self.assertFalse(V3(None, None, False)[0])
        self.assertFalse(V3(5, None, False)[0])
        self.assertTrue(V3(None, None, True)[0])  # unreadable but corroborated -> stand

    def test_guard_kills_overfire_keeps_recovery(self):
        # exhaustive contrast: every non-continuous case suppresses without a cue, stands with one;
        # continuous always suppresses (cue irrelevant)
        for last, first in [(8, 5), (10, 1), (5, 10), (5, 5), (None, None), (3, None), (None, 4)]:
            self.assertFalse(V3(last, first, False)[0], f"{last}->{first} no-cue should suppress")
            self.assertTrue(V3(last, first, True)[0],  f"{last}->{first} +cue should stand")
        for n in range(1, 20):
            self.assertFalse(V3(n, n + 1, True)[0], f"{n}->{n+1} continuous must suppress")
            self.assertFalse(V3(n, n + 1, False)[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
