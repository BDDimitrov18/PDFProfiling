"""Round-3 Commit B — unit tests for the evidence-first next-page gate decision.
Pure tests of split._next_page_decision using the SIX attested sig-triage dossier scenarios
as fixtures (human attestation 2026-06-13). No GPU/model.
Run: python3 -m unittest test_next_page_gate -v"""
import unittest
from split import _next_page_decision as DEC


class TestDossierScenarios(unittest.TestCase):
    # signature(_, heading, continuation, verso, nom_band, model_sn, model_conf) -> (starts_new, conf, reason)

    def test_162710373_p2_verso(self):
        # p2 = handwritten verso of p1's sheet -> NOT a new doc (verso veto, beats any model 'true')
        sn, conf, _ = DEC("", continuation=False, verso=True, nom_band="NONE",
                          model_starts_new=True, model_conf=0.92)
        self.assertFalse(sn)

    def test_142438096_p69_verso(self):
        # p69 = verso of p68's sheet -> NOT new
        sn, *_ = DEC("", continuation=False, verso=True, nom_band="NONE",
                     model_starts_new=True, model_conf=0.9)
        self.assertFalse(sn)

    def test_145428614_p65_no_heading_continuation(self):
        # p65 mid-doc signature block, no heading -> continuation veto
        sn, *_ = DEC("", continuation=True, verso=False, nom_band="NONE",
                     model_starts_new=True, model_conf=0.9)
        self.assertFalse(sn)

    def test_145428614_p66_section_heading_no_match(self):
        # p66 section heading, no nomenclature match, continues -> veto
        sn, *_ = DEC("Раздел 4", continuation=True, verso=False, nom_band="NONE",
                     model_starts_new=True, model_conf=0.92)
        self.assertFalse(sn)

    def test_143041245_p51_section_header(self):
        # p51 section header (would NOT nomenclature-match), 52 continues -> veto
        sn, *_ = DEC("Технически показатели", continuation=True, verso=False, nom_band="NONE",
                     model_starts_new=True, model_conf=0.85)
        self.assertFalse(sn)

    def test_084031203_p46_start_page_grid_must_not_regress(self):
        # p45 is the real start carrying a grid; p46 CONTINUES it. The gate judges p46 only
        # (never re-judges p45's grid) -> p46 is continuation -> not new.
        sn, *_ = DEC("", continuation=True, verso=False, nom_band="NONE",
                     model_starts_new=True, model_conf=0.92)
        self.assertFalse(sn)

    def test_083553577_p9_real_new_doc(self):
        # p9 'ИЗВЕСТИЕ ЗА ДОСТАВЯНЕ' is a separately-filable doc (waiver handles the metric);
        # the gate should still see it as a new doc — no verso, no continuation.
        sn, *_ = DEC("ИЗВЕСТИЕ ЗА ДОСТАВЯНЕ", continuation=False, verso=False, nom_band="NONE",
                     model_starts_new=True, model_conf=0.95)
        self.assertTrue(sn)


class TestDecisionPriority(unittest.TestCase):
    def test_nomenclature_match_makes_new_doc(self):
        # a real document-type heading -> new doc, even if the model hedged false
        sn, conf, _ = DEC("РАЗРЕШЕНИЕ ЗА СТРОЕЖ", continuation=False, verso=False,
                          nom_band="MATCH", model_starts_new=False, model_conf=0.5)
        self.assertTrue(sn)
        self.assertGreaterEqual(conf, 0.85)

    def test_match_beats_continuation(self):
        # MATCH outranks a continuation cue (priority order)
        sn, *_ = DEC("СКИЦА", continuation=True, verso=False, nom_band="MATCH",
                     model_starts_new=True, model_conf=0.8)
        self.assertTrue(sn)

    def test_verso_beats_match(self):
        # verso veto is highest priority
        sn, *_ = DEC("СКИЦА", continuation=False, verso=True, nom_band="MATCH",
                     model_starts_new=True, model_conf=0.9)
        self.assertFalse(sn)

    def test_falls_back_to_model_when_no_cue(self):
        sn_t, *_ = DEC("Някакво заглавие", continuation=False, verso=False, nom_band="NONE",
                       model_starts_new=True, model_conf=0.7)
        sn_f, *_ = DEC("Някакво заглавие", continuation=False, verso=False, nom_band="NONE",
                       model_starts_new=False, model_conf=0.7)
        self.assertTrue(sn_t)
        self.assertFalse(sn_f)

    def test_ambiguous_band_not_treated_as_match(self):
        # AMBIGUOUS must behave like NONE (neutral-default) — continuation veto still applies
        sn, *_ = DEC("Заглавие", continuation=True, verso=False, nom_band="AMBIGUOUS",
                     model_starts_new=True, model_conf=0.9)
        self.assertFalse(sn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
