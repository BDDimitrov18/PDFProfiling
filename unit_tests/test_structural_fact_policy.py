import unittest
from structural_fact_policy import candidate_reason,recover_decision

FACTS={'left_kind':'structural_calculation_body','right_kind':'structural_calculation_body',
       'different_project_reference':False,'evidence':'Tables with the same stamp','confidence':100}
BASE={'new_document':True,'confidence':95,'relationship':'independent','page_type_confidence':95,
      'left_kind':'other','right_kind':'other','left_heading':'Рамка X7','right_heading':'Рамка X9',
      'evidence':'Structural calculations for different frames'}


class StructuralFactPolicyTests(unittest.TestCase):
    def test_wrong_broad_type_cannot_erase_coordinates_quantities_or_new_report_title(self):
        cases=[{**BASE,'left_kind':'coordinate_table','right_kind':'coordinate_table'},
               {**BASE,'left_heading':'КОЛИЧЕСТВЕНА СМЕТКА','right_heading':'НАТОВАРВАНЕ'},
               {**BASE,'right_heading':'СТАТИЧЕСКО ОБСЛЕДВАНЕ НА ОБЕКТ: ЖИЛИЩНА СГРАДА'}]
        for base in cases:
            with self.subTest(base=base):
                self.assertIsNone(candidate_reason(base))
                self.assertTrue(recover_decision(base,FACTS)['new_document'])
                self.assertTrue(base['new_document'])

    def test_internal_frame_changes_merge_but_explicit_project_change_is_preserved(self):
        self.assertFalse(recover_decision(BASE,FACTS)['new_document'])
        self.assertTrue(recover_decision(BASE,{**FACTS,'different_project_reference':True})['new_document'])


if __name__=='__main__':unittest.main()
