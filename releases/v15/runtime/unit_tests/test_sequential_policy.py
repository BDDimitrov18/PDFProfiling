import copy
import unittest
from sequential_policy import apply


class SequentialPolicyTests(unittest.TestCase):
    def cover_case(self):
        return {
            4: dict(new_document=True, fact_recovery='cover_to_contents',
                    confidence=95, right_heading='СЪДЪРЖАНИЕ'),
            5: dict(new_document=True, confidence=95, page_type_confidence=95,
                    right_heading='УДОСТОВЕРЕНИЕ за проектантска правоспособност'),
        }

    def test_short_contents_with_credential_groups_and_preserves_input(self):
        source = self.cover_case(); before = copy.deepcopy(source)
        result = apply(source, {})
        self.assertFalse(result[4]['new_document'])
        self.assertTrue(result[5]['new_document'])
        self.assertEqual(source, before)
        self.assertEqual(result, apply(result, {}))

    def test_ordinary_contents_and_uncertain_credential_are_preserved(self):
        for replacement in [None, dict(new_document=False),
                            dict(right_heading='ОБЯСНИТЕЛНА ЗАПИСКА'),
                            dict(right_heading='УДОСТОВЕРЕНИЕ за собственост'),
                            dict(confidence=89), dict(page_type_confidence=89)]:
            with self.subTest(replacement=replacement):
                source = self.cover_case()
                if replacement is None: del source[5]
                else: source[5].update(replacement)
                self.assertTrue(apply(source, {})[4]['new_document'])

    def test_requires_verified_cover_transition(self):
        for update in [dict(fact_recovery=None), dict(confidence=89),
                       dict(right_heading='Списък на чертежи')]:
            source = self.cover_case(); source[4].update(update)
            self.assertTrue(apply(source, {})[4]['new_document'])

    def materials_case(self):
        return dict(confidence=95, right_fresh_start=True,
                    anchor_kind='technical_assignment', right_kind='quantity_schedule',
                    right_heading='КОЛИЧЕСТВЕНА СМЕТКА НА МАТЕРИАЛИТЕ')

    def test_explicit_materials_schedule_starts_and_is_idempotent(self):
        source = {4: dict(new_document=False)}; facts = {4: self.materials_case()}
        result = apply(source, facts)
        self.assertTrue(result[4]['new_document'])
        self.assertEqual(result, apply(result, facts))
        self.assertFalse(source[4]['new_document'])

    def test_work_quantities_and_weak_materials_evidence_do_not_split(self):
        for update in [dict(right_heading='КОЛИЧЕСТВЕНА СМЕТКА НА СМР'),
                       dict(right_fresh_start=False), dict(confidence=89),
                       dict(anchor_kind='explanatory_note'), dict(right_kind='other')]:
            facts = self.materials_case(); facts.update(update)
            self.assertFalse(apply({4: dict(new_document=False)}, {4: facts})[4]['new_document'])


if __name__ == '__main__': unittest.main()
