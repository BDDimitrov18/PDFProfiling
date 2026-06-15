"""Unit tests for domain_rules.py — one synthetic page-sequence per rule. No GPU, no eval.
Each CLOSURE rule is tested BOTH with the marker present (boundary after it stands) AND with a
pre-marker section heading (that boundary is suppressed) AND with the marker absent (abstain).
Run: python3 -m unittest test_domain_rules -v"""
import unittest
from domain_rules import (
    PageInfo, Boundary, apply_domain_rules,
    rule1_closure_notarial, rule2_closure_naslednici, rule4_closure_obyasnitelna,
    rule3_normalize_types, rule6_merge_izvestie, rule7_evn_trade_terms,
    rule8_invest_sadarzhanie, rule5_rs_twopage_prior,
    MARKER_NOTARY, MARKER_OFFICIAL, MARKER_PROEKTANT, MARKER_SASTAVIL,
)


def pg(n, title=None, issuer=None, markers=()):
    return PageInfo(n, title=title, issuer=issuer, markers=frozenset(markers))


def run(rule, pages, starts):
    pmap = {p.page: p for p in pages}
    bnds = [Boundary(s) for s in starts]
    audit = []
    out = rule(pmap, bnds, audit)
    return sorted(b.page for b in out), out, audit


class TestClosureRule1Notarial(unittest.TestCase):
    def test_pre_marker_section_suppressed_and_post_marker_stands(self):
        pages = [pg(1, "НОТАРИАЛЕН АКТ за покупко-продажба"), pg(2, "СКИЦА"),
                 pg(3, "продължение", markers=[MARKER_NOTARY]), pg(4, "ДОГОВОР")]
        starts, _, audit = run(rule1_closure_notarial, pages, [1, 2, 4])
        self.assertEqual(starts, [1, 4])                 # p2 (pre-signature) suppressed; p4 (post) stands
        self.assertTrue(any(a.action == "suppress" and a.page == 2 for a in audit))

    def test_abstain_when_signature_never_read(self):
        # dropped scan: no notary_signature anywhere -> suppress NOTHING (never manufacture a merge)
        pages = [pg(1, "НОТАРИАЛЕН АКТ"), pg(2, "СКИЦА"), pg(3, "още")]
        starts, _, audit = run(rule1_closure_notarial, pages, [1, 2])
        self.assertEqual(starts, [1, 2])
        self.assertTrue(any(a.action == "abstain" for a in audit))


class TestClosureRule2Naslednici(unittest.TestCase):
    def test_official_signoff_closes(self):
        pages = [pg(1, "УДОСТОВЕРЕНИЕ ЗА НАСЛЕДНИЦИ"), pg(2, "списък наследници"),
                 pg(3, "длъжностно лице", markers=[MARKER_OFFICIAL]), pg(4, "ПОЛИЦА")]
        starts, _, audit = run(rule2_closure_naslednici, pages, [1, 2, 4])
        self.assertEqual(starts, [1, 4])
        self.assertTrue(any(a.action == "suppress" and a.page == 2 for a in audit))

    def test_abstain_when_official_absent(self):
        pages = [pg(1, "УДОСТОВЕРЕНИЕ ЗА НАСЛЕДНИЦИ"), pg(2, "списък")]
        starts, _, _ = run(rule2_closure_naslednici, pages, [1, 2])
        self.assertEqual(starts, [1, 2])


class TestClosureRule4Obyasnitelna(unittest.TestCase):
    def test_proektant_closes(self):
        pages = [pg(1, "ОБЯСНИТЕЛНА ЗАПИСКА"), pg(2, "КОЛИЧЕСТВЕНА СМЕТКА"),
                 pg(3, "Проектант", markers=[MARKER_PROEKTANT]), pg(4, "СКИЦА")]
        starts, _, _ = run(rule4_closure_obyasnitelna, pages, [1, 2, 4])
        self.assertEqual(starts, [1, 4])

    def test_sastavil_also_closes(self):
        pages = [pg(1, "Обяснителна записка"), pg(2, "раздел"),
                 pg(3, "Съставил", markers=[MARKER_SASTAVIL])]
        starts, _, _ = run(rule4_closure_obyasnitelna, pages, [1, 2])
        self.assertEqual(starts, [1])


class TestRule3Normalize(unittest.TestCase):
    def test_synonyms_collapse_to_koordinaten(self):
        for title in ("изходни точки", "списък с подробни точки", "Координатен регистър"):
            pages = [pg(1, title)]
            _, out, _ = run(rule3_normalize_types, pages, [1])
            self.assertEqual(out[0].doc_type, "Координатен регистър", f"{title!r} should normalize")


class TestRule6Merge(unittest.TestCase):
    def test_consecutive_izvestie_merge(self):
        pages = [pg(1, "Известие за доставяне"), pg(2, "Известие за доставяне"),
                 pg(3, "Известие за доставяне")]
        starts, out, audit = run(rule6_merge_izvestie, pages, [1, 2, 3])
        self.assertEqual(starts, [1])
        self.assertEqual(out[0].doc_type, "Обратна разписка")
        self.assertEqual(sum(1 for a in audit if a.action == "merge"), 2)

    def test_non_consecutive_not_merged(self):
        pages = [pg(1, "Известие за доставяне"), pg(2, "ДОГОВОР"), pg(3, "Известие за доставяне")]
        starts, _, _ = run(rule6_merge_izvestie, pages, [1, 2, 3])
        self.assertEqual(starts, [1, 2, 3])


class TestRule7EvnSection(unittest.TestCase):
    def test_evn_trade_terms_suppressed(self):
        pages = [pg(1, "Търговски условия", issuer="EVN България ЕАД")]
        starts, _, _ = run(rule7_evn_trade_terms, pages, [1])
        self.assertEqual(starts, [])

    def test_non_evn_trade_terms_kept(self):
        # ISSUER-SPECIFIC: same title, different issuer -> NOT suppressed
        pages = [pg(1, "Търговски условия", issuer="Община Пловдив")]
        starts, _, _ = run(rule7_evn_trade_terms, pages, [1])
        self.assertEqual(starts, [1])


class TestRule8Adjacency(unittest.TestCase):
    def test_invest_then_sadarzhanie_not_split(self):
        pages = [pg(1, "Заглавна страница — Инвестиционен проект"), pg(2, "съдържание")]
        starts, _, _ = run(rule8_invest_sadarzhanie, pages, [1, 2])
        self.assertEqual(starts, [1])

    def test_invest_then_other_kept(self):
        pages = [pg(1, "Инвестиционен проект"), pg(2, "ДОГОВОР")]
        starts, _, _ = run(rule8_invest_sadarzhanie, pages, [1, 2])
        self.assertEqual(starts, [1, 2])


class TestRule5SoftPrior(unittest.TestCase):
    def test_never_changes_boundary_set_twopage(self):
        pages = [pg(1, "Разрешение за строеж"), pg(3, "ДОГОВОР")]
        starts, out, audit = run(rule5_rs_twopage_prior, pages, [1, 3])
        self.assertEqual(starts, [1, 3])                       # no add/remove
        nudged = next(b for b in out if b.page == 3)
        self.assertGreater(nudged.conf, 0.90)                  # weak prior toward 2-page span
        self.assertTrue(any(a.action == "prior" for a in audit))

    def test_tolerates_one_page_scan_no_force(self):
        # 1-page scan: РС then a real next-doc at p2 -> rule must NOT merge/split/penalise
        pages = [pg(1, "Разрешение за строеж"), pg(2, "ПОЛИЦА")]
        starts, out, _ = run(rule5_rs_twopage_prior, pages, [1, 2])
        self.assertEqual(starts, [1, 2])
        self.assertEqual([b.conf for b in out], [0.90, 0.90])  # nothing forced/changed


class TestOrchestrator(unittest.TestCase):
    def test_end_to_end_combines_rules_with_audit(self):
        pages = [
            pg(1, "ОБЯСНИТЕЛНА ЗАПИСКА"),
            pg(2, "КОЛИЧЕСТВЕНА СМЕТКА"),                       # intra-doc section (pre-closure)
            pg(3, "Проектант", markers=[MARKER_PROEKTANT]),     # closes the Обяснителна записка
            pg(4, "Известие за доставяне"),
            pg(5, "Известие за доставяне"),                     # merges with p4
        ]
        bnds = [Boundary(1), Boundary(2), Boundary(4), Boundary(5)]
        out, audit = apply_domain_rules(pages, bnds)
        self.assertEqual([b.page for b in out], [1, 4])        # p2 suppressed (R4), p5 merged (R6)
        self.assertEqual(next(b for b in out if b.page == 4).doc_type, "Обратна разписка")
        self.assertTrue(audit)                                  # audit trail populated


if __name__ == "__main__":
    unittest.main(verbosity=2)
