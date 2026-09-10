import unittest
from boundary_facts import recovery,candidate_reason


class FactRecoveryTests(unittest.TestCase):
    def test_narrow_facts_require_the_correct_roles_and_first_page(self):
        facts={'left_role':'project_cover','right_role':'calculation_output','right_first_page':True,
               'left_evidence':'Title only','right_evidence':'Initial data, page 1','confidence':95}
        self.assertEqual(recovery(facts),'cover_to_body')
        self.assertIsNone(recovery({**facts,'right_role':'cover_continuation'}))
        self.assertIsNone(recovery({**facts,'right_first_page':False}))
        self.assertEqual(recovery({**facts,'left_role':'narrative','right_role':'thermal_output'}),'narrative_to_thermal_output')
        self.assertIsNone(recovery({**facts,'left_role':'thermal_output','right_role':'thermal_output'}))
        self.assertIsNone(recovery({**facts,'confidence':85}))
        self.assertIsNone(candidate_reason({'new_document':True,'evidence':'Thermal output'}))


if __name__=='__main__':unittest.main()
