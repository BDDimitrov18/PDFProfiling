"""Round-3 Commit A' — unit tests for the TITLE-GATE duplicate-guard (SUPPRESS-WITH-FLAG).
Pure-logic tests of split._titled_gate_decision; no GPU/model. Fixtures reconstruct real
dup-reloc traces from logs/dev_stage1.log + logs/fulltests_stage2.log.
A' fork reversal (2026-06-13): keep-original-capped was REVERTED on full-tests evidence
(+15 fresh FP / −1 TP — resurrected ungrounded claims). On a consumed relocation target the
gate now SUPPRESSES the claim (is_end=False, [DUP-GUARD-SUPPRESS]), never keeps the original.
Run: python3 -m unittest test_dup_guard -v"""
import unittest
from split import _titled_gate_decision as D


class TestDupGuardSuppress(unittest.TestCase):
    # --- the dev FN19 trigger: 142044854 n=18, claimed p19, unique grounded target p18 (already
    #     opened at n=17). A' SUPPRESSES the claim (does NOT keep the ungrounded p19). ---
    def test_dev_142044854_consumed_target_suppressed(self):
        sp, ee, conf, is_end, action = D(0, 19, 18, 0.90, 18,
                                         [(18, "УДОСТОВЕРЕНИЕ", "№ 000193", 1)], {2, 18})
        self.assertFalse(is_end)                       # claim SUPPRESSED, not kept
        self.assertEqual(action[0], "DUP-GUARD-SUPPRESS")
        self.assertEqual(action[1], 19)                # the suppressed claimed page
        self.assertEqual(action[2], 18)                # target that was already a boundary

    def test_fresh_083553577_consumed_target_suppressed(self):
        _, _, _, is_end, action = D(0, 38, 37, 0.92, 37, [(37, "x", "y", 1)], {36, 37})
        self.assertFalse(is_end)
        self.assertEqual(action[0], "DUP-GUARD-SUPPRESS")

    def test_fresh_142438096_consumed_target_suppressed(self):
        _, _, _, is_end, action = D(0, 39, 38, 0.90, 38, [(38, "x", "y", 1)], {37, 38})
        self.assertFalse(is_end)
        self.assertEqual(action[0], "DUP-GUARD-SUPPRESS")

    def test_dup_guard_suppresses_never_resurrects(self):
        # invariant (A'): a consumed grounded target => SUPPRESS, never keep an ungrounded claim
        for claimed, target in [(19, 18), (38, 37), (76, 75), (86, 85)]:
            _, _, _, is_end, action = D(0, claimed, claimed - 1, 0.9, claimed - 1,
                                        [(target, "t", "i", 1)], {target})
            self.assertFalse(is_end, f"dup-guard wrongly kept claim {claimed}")
            self.assertEqual(action[0], "DUP-GUARD-SUPPRESS")


class TestRelocationPreserved(unittest.TestCase):
    """Behaviour that must NOT change vs the pre-Round-3 gate."""

    def test_normal_reloc_when_target_free(self):
        # unique grounded target NOT already a boundary -> relocate there (FN3-style recovery)
        sp, ee, conf, is_end, action = D(0, 1, 0, 0.9, 2, [(3, "ИЗХОДНИ ТОЧКИ", "none", 0)], {1})
        self.assertEqual((sp, ee), (3, 2))   # boundary moves to p3
        self.assertTrue(is_end)
        self.assertEqual(action[0], "RELOC")
        self.assertAlmostEqual(conf, 0.60)   # title-only -> capped

    def test_reloc_both_grounded_full_conf(self):
        sp, ee, conf, is_end, action = D(0, 1, 0, 0.9, 2, [(3, "СКИЦА", "№ 15-1", 1)], {1})
        self.assertEqual(action[0], "RELOC")
        self.assertAlmostEqual(conf, 0.9)    # both grounded -> not capped

    def test_keep_both(self):
        sp, ee, conf, is_end, action = D(2, 10, 9, 0.9, 9, [], {1})
        self.assertEqual((sp, ee, is_end), (10, 9, True))
        self.assertAlmostEqual(conf, 0.9)
        self.assertEqual(action[0], "KEEP-BOTH")

    def test_one_of_two_cap(self):
        sp, ee, conf, is_end, action = D(1, 10, 9, 0.9, 9, [], {1})
        self.assertAlmostEqual(conf, 0.60)
        self.assertTrue(is_end)
        self.assertEqual(action[0], "KEEP-ONE-OF-TWO")

    def test_suppress_none(self):
        sp, ee, conf, is_end, action = D(0, 10, 9, 0.9, 9, [], {1})
        self.assertFalse(is_end)
        self.assertEqual((sp, ee), (10, 9))      # effective_end -> n on suppress
        self.assertEqual(action[0], "SUPPRESS")

    def test_suppress_ambiguous_multiple(self):
        _, _, _, is_end, action = D(0, 10, 9, 0.9, 9, [(8, "a", "b", 0), (11, "c", "d", 0)], {1})
        self.assertFalse(is_end)
        self.assertEqual(action[0], "SUPPRESS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
