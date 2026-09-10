import unittest
from artifact_policy import abstention_reason

def facts(**kw):
    return dict(dict(anchor_heading='ОБЯСНИТЕЛНА ЗАПИСКА',left_heading='',right_heading='',left_kind='explanatory_note'),**kw)

class GuardTests(unittest.TestCase):
    def test_arabic_safety_section_abstains(self):
        self.assertIsNotNone(abstention_reason(facts(right_heading='3. ПЛАН ЗА БЕЗОПАСНОСТ'),(True,'separate_safety_note')))
    def test_roman_safety_section_abstains(self):
        self.assertIsNotNone(abstention_reason(facts(right_heading='VII. ТЕХНИКА ПО БЕЗОПАСНОСТ'),(True,'separate_safety_note')))
    def test_standalone_safety_note_still_allowed(self):
        self.assertIsNone(abstention_reason(facts(right_heading='ОБЯСНИТЕЛНА ЗАПИСКА ПО БХТБП'),(True,'separate_safety_note')))
    def test_continuing_waste_plan_abstains(self):
        self.assertIsNotNone(abstention_reason(facts(left_kind='waste_plan',right_heading='МЕРКИ'),(True,'separate_waste_plan')))
    def test_decimal_subsection_abstains(self):
        self.assertIsNotNone(abstention_reason(facts(right_heading='5.2. СЪБИРАНЕ НА ОТПАДЪЦИ'),(True,'separate_waste_plan')))
    def test_new_waste_plan_after_safety_still_allowed(self):
        self.assertIsNone(abstention_reason(facts(left_kind='safety_note',right_heading='9. ПЛАН ЗА УПРАВЛЕНИЕ НА ОТПАДЪЦИТЕ'),(True,'separate_waste_plan')))
    def test_insurance_policy_does_not_establish_contract_parent(self):
        self.assertIsNotNone(abstention_reason(facts(anchor_heading='ЗАСТРАХОВАТЕЛНА ПОЛИЦА',right_heading='ПРИЛОЖЕНИЕ КЪМ ДОГОВОР'),(False,'explicit_contract_attachment')))
    def test_explicit_contract_with_unnumbered_annex_allowed(self):
        self.assertIsNone(abstention_reason(facts(anchor_heading='ДОГОВОР № 820',right_heading='ПРИЛОЖЕНИЕ КЪМ ДОГОВОР'),(False,'explicit_contract_attachment')))
    def test_different_contract_ids_abstain(self):
        self.assertIsNotNone(abstention_reason(facts(anchor_heading='ДОГОВОР № 820',right_heading='ПРИЛОЖЕНИЕ №1 КЪМ ДОГОВОР № 821'),(False,'explicit_contract_attachment')))
    def test_matching_contract_ids_allowed(self):
        self.assertIsNone(abstention_reason(facts(anchor_heading='ДОГОВОР № 820',right_heading='ПРИЛОЖЕНИЕ №1 КЪМ ДОГОВОР № 820'),(False,'explicit_contract_attachment')))

if __name__=='__main__':unittest.main()
