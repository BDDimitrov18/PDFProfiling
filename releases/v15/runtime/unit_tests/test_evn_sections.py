import json
import unittest

from evn_sections import parse_evidence, should_suppress, transcription_prompt


class EvidenceTests(unittest.TestCase):
    def parse(self, title="Търговски условия", issuer="EVN България ЕАД"):
        return parse_evidence(json.dumps({"title": title, "issuer": issuer}, ensure_ascii=False))

    def test_literal_transcription_is_retained_for_audit(self):
        title, issuer = " II. ТЪРГОВСКИ\nУСЛОВИЯ: ", "„ЕВН България“ ЕАД"
        evidence = self.parse(title, issuer)
        self.assertEqual(evidence["status"], "ok")
        self.assertEqual(evidence["title"], title)
        self.assertEqual(evidence["issuer"], issuer)
        self.assertTrue(evidence["reason"])

    def test_missing_or_empty_fields_abstain(self):
        for raw in ('{}', '{"title":"Търговски условия"}', '{"issuer":"EVN"}'):
            with self.subTest(raw=raw):
                self.assertEqual(parse_evidence(raw)["status"], "abstain")
                self.assertFalse(should_suppress(parse_evidence(raw)))
        for title, issuer in [("", "EVN"), ("Търговски условия", ""), (" \n", "EVN"),
                              ("Търговски условия", "\t"), ("", "")]:
            with self.subTest(title=title, issuer=issuer):
                evidence = self.parse(title, issuer)
                self.assertEqual(evidence["status"], "abstain")
                self.assertFalse(should_suppress(evidence))

    def test_non_string_and_boolean_fields_abstain(self):
        for invalid in (None, True, False, 1, 3.5, [], {}, ["EVN"]):
            for title, issuer in [(invalid, "EVN"), ("Търговски условия", invalid)]:
                with self.subTest(title=title, issuer=issuer):
                    evidence = self.parse(title, issuer)
                    self.assertEqual(evidence["status"], "abstain")
                    self.assertFalse(should_suppress(evidence))

    def test_malformed_ambiguous_and_unrequested_json_is_not_repaired(self):
        valid = json.dumps({"title": "Търговски условия", "issuer": "EVN"}, ensure_ascii=False)
        raws = [None, {}, True, b'{}', "", "not JSON", "```json\n" + valid + "\n```",
                "Evidence: " + valid, valid + " commentary", valid + valid,
                '["Търговски условия", "EVN"]', '"EVN"', "null", "true",
                '{"title":"Търговски условия","issuer":"EVN","issuer":"Other"}',
                '{"title":"Търговски условия","issuer":"Other","issuer":"EVN"}',
                '{"title":"Търговски условия","issuer":"EVN","suppress":true}',
                '{"Title":"Търговски условия","issuer":"EVN"}']
        for raw in raws:
            with self.subTest(raw=raw):
                evidence = parse_evidence(raw)
                self.assertEqual(set(evidence), {"status", "title", "issuer", "reason"})
                self.assertEqual(evidence["status"], "abstain")
                self.assertFalse(should_suppress(evidence))

    def test_absence_placeholder_is_not_positive_evidence(self):
        for title, issuer in [("NONE", "EVN"), ("Търговски условия", "unreadable"),
                              ("Търговски условия", "NONE")]:
            self.assertFalse(should_suppress(self.parse(title, issuer)))


class RuleTests(unittest.TestCase):
    def suppress(self, title="Търговски условия", issuer="EVN България ЕАД"):
        return should_suppress(parse_evidence(json.dumps({"title": title, "issuer": issuer})))

    def test_exact_heading_and_issuer_gate(self):
        self.assertTrue(self.suppress())
        self.assertTrue(self.suppress(issuer="EVN"))
        self.assertTrue(self.suppress(issuer="ЕВН"))

    def test_case_and_interword_whitespace_are_ignored(self):
        for title in [" ТЪРГОВСКИ УСЛОВИЯ ", "Търговски\nусловия", "Търговски\t  условия",
                      "търговски\u00a0условия"]:
            for issuer in [" evn ", " ЕВН   България\nЕАД", "евН България", "„EVN България“ ЕАД"]:
                with self.subTest(title=title, issuer=issuer):
                    self.assertTrue(self.suppress(title, issuer))

    def test_numbered_section_heading_and_terminal_punctuation(self):
        for title in ["2. Търговски условия", "2) Търговски условия", "(2) Търговски условия",
                      "II. Търговски условия", "IV) Търговски условия", "2.1. Търговски условия",
                      "Търговски условия:", "Търговски условия."]:
            with self.subTest(title=title):
                self.assertTrue(self.suppress(title))

    def test_other_issuers_keep_their_trade_terms(self):
        for issuer in ["Електрохолд България ЕООД", "ЕНЕРГО-ПРО", "Община Пловдив", "ВиК ЕООД"]:
            with self.subTest(issuer=issuer):
                self.assertFalse(self.suppress(issuer=issuer))

    def test_evn_different_heading_is_preserved(self):
        for title in ["ДОГОВОР", "УДОСТОВЕРЕНИЕ", "Общи условия", "Становище", "Приложение № 1"]:
            with self.subTest(title=title):
                self.assertFalse(self.suppress(title))

    def test_body_mentions_and_longer_headings_do_not_match(self):
        for title in ["Договор за търговски условия", "Нови търговски условия",
                      "Търговски условия за присъединяване", "Приложение: Търговски условия",
                      "ДОГОВОР\nТърговски условия", "Търговски условия\n1. Настоящият договор",
                      "Съгласно Търговски условия, приложени към договора."]:
            with self.subTest(title=title):
                self.assertFalse(self.suppress(title))

    def test_issuer_token_collisions_and_mixed_scripts_do_not_match(self):
        for issuer in ["DEVN", "EVNEX", "EVN2", "2EVN", "EVN_България", "prefix_EVN",
                       "ЕВНЕТ", "ЕВН2", "НЕВН", "EВN", "ЕVN", "E V N", "Е В Н"]:
            with self.subTest(issuer=issuer):
                self.assertFalse(self.suppress(issuer=issuer))

    def test_heading_typos_and_letter_spacing_are_not_fuzzily_repaired(self):
        for title in ["Търговcки условия", "Търговски условя", "Т ъ р г о в с к и условия",
                      "2 Търговски условия", "Раздел II Търговски условия"]:
            with self.subTest(title=title):
                self.assertFalse(self.suppress(title))

    def test_invalid_direct_evidence_never_suppresses(self):
        for evidence in [None, True, [], "EVN", {},
                         {"status": "abstain", "title": "Търговски условия", "issuer": "EVN"},
                         {"status": True, "title": "Търговски условия", "issuer": "EVN"},
                         {"status": "ok", "title": True, "issuer": "EVN"},
                         {"status": "ok", "title": "Търговски условия", "issuer": ["EVN"]},
                         {"status": "ok", "title": "Търговски условия"}]:
            with self.subTest(evidence=evidence):
                self.assertFalse(should_suppress(evidence))


class PromptTests(unittest.TestCase):
    def test_prompt_requests_literal_evidence_without_revealing_candidate(self):
        prompt = transcription_prompt(17)
        self.assertIn("page 17", prompt)
        self.assertIn('"title"', prompt)
        self.assertIn('"issuer"', prompt)
        self.assertIn("empty string", prompt)
        for leak in ("EVN", "ЕВН", "Търговски", "boundary", "suppress", "document start"):
            self.assertNotIn(leak.casefold(), prompt.casefold())

    def test_page_number_must_be_a_positive_integer(self):
        for page in (0, -1, True, None, "2", 2.5):
            with self.subTest(page=page), self.assertRaises(ValueError):
                transcription_prompt(page)


if __name__ == "__main__":
    unittest.main()
