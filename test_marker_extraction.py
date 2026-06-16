"""Unit tests for marker_extraction.py — code-side matchers on SYNTHETIC transcriptions.
These test the (b) string-matching half (pure, pod-less). The (a) transcribe-first half is a model
query and is tested on the pod via replay. NEGATIVE CONTROLS are first-class here: a transcription
with no marker string must yield NO marker (the code-side anti-confabulation guarantee).
Run: python3 -m unittest test_marker_extraction -v"""
import unittest
from marker_extraction import (
    match_closure_signoff, match_issuer, match_title, match_titleblock_fields,
    extract_from_transcriptions,
)
from domain_rules import MARKER_NOTARY, MARKER_OFFICIAL, MARKER_PROEKTANT, MARKER_SASTAVIL


class TestClosureMatcher(unittest.TestCase):
    def test_proektant(self):
        r = match_closure_signoff("обяснителна записка ... Проектант: инж. А. Иванова, печат")
        self.assertIn(MARKER_PROEKTANT, r["markers"])

    def test_sastavil(self):
        self.assertIn(MARKER_SASTAVIL, match_closure_signoff("Съставил: техн. Г. Петров")["markers"])

    def test_notary(self):
        r = match_closure_signoff("НОТАРИУС рег. № 123, район на действие РС Пловдив, печат")
        self.assertIn(MARKER_NOTARY, r["markers"])

    def test_official_dlazhnostno_lice(self):
        # squashes 'длъжностно лице' -> 'длъжностнолице'; also tolerant of letter-spacing
        self.assertIn(MARKER_OFFICIAL, match_closure_signoff("подпис на длъжностно лице")["markers"])
        self.assertIn(MARKER_OFFICIAL, match_closure_signoff("Д Л Ъ Ж Н О С Т Н О  Л И Ц Е")["markers"])

    # ---- NEGATIVE CONTROLS (anti-confabulation, code side) ----
    def test_negative_drawing_page_no_marker(self):
        r = match_closure_signoff("Чертеж покрив. Мащаб 1:50. Лист 3 от 8.")
        self.assertEqual(r["markers"], set(), "a drawing page must yield NO closure marker")

    def test_negative_none_token(self):
        self.assertEqual(match_closure_signoff("NONE")["markers"], set())
        self.assertEqual(match_closure_signoff("")["markers"], set())

    def test_negative_table_page(self):
        self.assertEqual(match_closure_signoff("Количествена сметка, общо 39.59 м2")["markers"], set())


class TestIssuerMatcher(unittest.TestCase):
    def test_evn_variants(self):
        # normaliser folds EVN -> 'еvn'; must still match through normalization
        self.assertEqual(match_issuer("EVN България Електроразпределение ЕАД")["issuer"], "EVN")
        self.assertEqual(match_issuer("ЕВН Електроразпределение")["issuer"], "EVN")

    def test_non_evn(self):
        self.assertIsNone(match_issuer("Община Пловдив Район Западен")["issuer"])
        self.assertIsNone(match_issuer("NONE")["issuer"])


class TestTitleMatcher(unittest.TestCase):
    def test_passthrough(self):
        self.assertEqual(match_title("ОБЯСНИТЕЛНА ЗАПИСКА")["heading"], "ОБЯСНИТЕЛНА ЗАПИСКА")

    def test_none(self):
        self.assertIsNone(match_title("NONE")["heading"])
        self.assertIsNone(match_title("   ")["heading"])


class TestTitleblockFields(unittest.TestCase):
    def test_issue_number(self):
        f = match_titleblock_fields("изх. № 2-7000-218 (1)/30.03.2017 г.")
        self.assertEqual(f["issue_kind"].lower().replace(" ", "")[:4], "изх.")
        self.assertIn("2-7000-218", f["issue_number"])

    def test_sheet_marker(self):
        f = match_titleblock_fields("Координатен регистър, лист 2 от 5")
        self.assertEqual((f["sheet_x"], f["sheet_of"]), (2, 5))

    def test_empty(self):
        self.assertEqual(match_titleblock_fields("просто текст без номера"), {})


class TestAggregator(unittest.TestCase):
    def test_plugs_into_pageinfo_shape(self):
        rec = extract_from_transcriptions({
            "closure_signoff": "Проектант: инж. Иванов",
            "issuer": "EVN България",
            "title": "ОБЯСНИТЕЛНА ЗАПИСКА",
            "titleblock_fields": "изх. № 4086 / 14.02.2017",
        })
        self.assertEqual(rec["markers"], {MARKER_PROEKTANT})
        self.assertEqual(rec["issuer"], "EVN")
        self.assertEqual(rec["title"], "ОБЯСНИТЕЛНА ЗАПИСКА")
        self.assertIn("issue_number", rec["titleblock_fields"])

    def test_negative_aggregate_no_confabulation(self):
        # a cue-less drawing page: NO markers, NO issuer, NO title
        rec = extract_from_transcriptions({
            "closure_signoff": "NONE", "issuer": "NONE", "title": "NONE", "titleblock_fields": "NONE"})
        self.assertEqual(rec["markers"], set())
        self.assertIsNone(rec["issuer"])
        self.assertIsNone(rec["title"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
