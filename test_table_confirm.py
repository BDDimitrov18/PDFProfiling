"""Round-3 Commit C / Fix 11 v2 — unit tests for the mechanical table-boundary decision.
Pure tests of split._table_boundary_decision; no GPU. Run: python3 -m unittest test_table_confirm -v"""
import unittest
from split import _table_boundary_decision as T


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
