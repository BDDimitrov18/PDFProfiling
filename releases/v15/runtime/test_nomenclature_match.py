"""Unit tests for nomenclature_match.py — corruption-robustness, negatives, neutral-default.
Run: python3 -m unittest test_nomenclature_match -v   (stdlib only, no pytest dependency)."""
import unittest
import nomenclature_match as nm

ENTRIES = nm.load_nomenclature()


def _band(title):
    return nm.match_title(title, ENTRIES)[2]


def _best_name(title):
    e = nm.match_title(title, ENTRIES)[0]
    return e["name"] if e else None


class TestParse(unittest.TestCase):
    def test_counts(self):
        # Fable spec: 382 rows, 220 unique names, 19 part-categories.
        self.assertEqual(len(ENTRIES), 382)
        self.assertEqual(len({e["name"] for e in ENTRIES}), 220)
        self.assertEqual(len({e["category"] for e in ENTRIES}), 19)

    def test_category_assigned(self):
        # Every entry carries a category (the X000 section heading it falls under).
        self.assertTrue(all(e["category"] for e in ENTRIES))
        # First section is Архитектура.
        self.assertEqual(ENTRIES[0]["category"], "Архитектура")

    def test_sheet_types_flagged(self):
        sheets = {e["name"] for e in ENTRIES if e["is_sheet_type"]}
        for s in ["Разрез", "Фасада", "План", "Ситуация", "План покрив", "Кофражен план", "Детайли"]:
            self.assertIn(s, sheets, f"{s} should be flagged is_sheet_type")


class TestPositiveCorruptions(unittest.TestCase):
    """Synthetic corruptions of REAL table entries must still MATCH."""

    def test_exact_clean(self):
        self.assertEqual(_band("Скица"), "MATCH")
        self.assertEqual(_band("Обяснителна записка"), "MATCH")

    def test_inter_letter_spacing(self):
        # squashed form must defeat letter-spaced scans
        self.assertEqual(_band("С К И Ц А"), "MATCH")
        self.assertEqual(_band("Р А З Р Е З"), "MATCH")
        self.assertEqual(_band("О б я с н и т е л н а   з а п и с к а"), "MATCH")

    def test_single_char_drop(self):
        self.assertEqual(_band("Скца"), "MATCH")              # dropped 'и' from Скица
        self.assertEqual(_band("Обяснителна запска"), "MATCH")  # dropped 'и'

    def test_single_char_substitution(self):
        self.assertEqual(_band("Скнца"), "MATCH")             # и->н in Скица
        self.assertEqual(_band("Ситуацоя"), "MATCH")          # и->о in Ситуация

    def test_homoglyph_mixing(self):
        # Latin homoglyphs for Cyrillic: C,к,и,ц,a etc.
        self.assertEqual(_band("Cкицa"), "MATCH")             # Latin C and a
        self.assertEqual(_band("Pазрез"), "MATCH")            # Latin P -> р

    def test_case_chaos(self):
        self.assertEqual(_band("сКиЦа"), "MATCH")
        self.assertEqual(_band("РАЗРЕЗ"), "MATCH")

    def test_appended_identifier(self):
        self.assertEqual(_band("Скица № 1234 / 12.03.2017"), "MATCH")
        self.assertEqual(_best_name("Скица № 1234 / 12.03.2017"), "Скица")
        self.assertEqual(_band("Становище № 4279762"), "MATCH")

    def test_truncation_two_tokens(self):
        # a long entry truncated to its first 2 tokens should still be recoverable
        long = [e["name"] for e in ENTRIES if len(e["tokens"]) >= 3]
        self.assertTrue(long, "need a 3+ token entry for truncation test")
        sample = long[0]
        first2 = " ".join(sample.split()[:2])
        b = _band(first2)
        self.assertIn(b, ("MATCH", "AMBIGUOUS"), f"{first2!r} truncation -> {b}")


class TestNegatives(unittest.TestCase):
    """Titles genuinely ABSENT from the table must NOT produce a confident MATCH.
    (If any scores MATCH, the matcher is too loose.)"""

    def test_absent_titles_not_match(self):
        for t in ["НАКЛОНЕН ПОКРИВ", "ЧЕЛЕН ЛИСТ", "НОТАРИАЛЕН АКТ"]:
            self.assertNotEqual(_band(t), "MATCH", f"{t!r} must not MATCH")

    def test_absent_titles_are_none(self):
        # stronger: with provisional bounds these currently land NONE
        for t in ["НАКЛОНЕН ПОКРИВ", "ЧЕЛЕН ЛИСТ", "НОТАРИАЛЕН АКТ"]:
            self.assertEqual(_band(t), "NONE", f"{t!r} -> {_band(t)} (expected NONE)")

    def test_empty_and_garbage(self):
        self.assertEqual(_band(""), "NONE")
        self.assertEqual(_band("№ 12345 / 01.02.2003"), "NONE")  # pure identifier, no type word


class TestNeutralDefault(unittest.TestCase):
    """NEUTRAL-DEFAULT hard rule: only MATCH is actionable; AMBIGUOUS and NONE are both
    treated as 'no nomenclature signal'. This is what makes a wrong match harmless."""

    def test_only_match_is_actionable(self):
        self.assertTrue(nm.is_confidence_signal("MATCH"))
        self.assertFalse(nm.is_confidence_signal("AMBIGUOUS"))
        self.assertFalse(nm.is_confidence_signal("NONE"))

    def test_bands_partition(self):
        self.assertEqual(nm.ACTIONABLE_BANDS | nm.NEUTRAL_BANDS, {"MATCH", "AMBIGUOUS", "NONE"})
        self.assertEqual(nm.ACTIONABLE_BANDS & nm.NEUTRAL_BANDS, set())

    def test_band_values_only(self):
        # match_title may only ever emit one of the three bands
        for t in ["Скица", "С К И Ц А", "НАКЛОНЕН ПОКРИВ", "", "xyzzy"]:
            self.assertIn(nm.match_title(t, ENTRIES)[2], {"MATCH", "AMBIGUOUS", "NONE"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
