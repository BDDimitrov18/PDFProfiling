import unittest
from page_profile import additions


class PageProfileTests(unittest.TestCase):
    def test_repeated_table_header_is_not_a_new_output(self):
        left={'kind':'coordinate_table','confidence':95,'columns':'N X Y','first_row_label':'1'}
        self.assertIsNone(additions(left,{**left,'first_row_label':'18'}))
        self.assertIsNone(additions(left,{**left,'columns':'N Х У'}))
        self.assertIsNone(additions(left,{**left,'columns':'N X Y Z','first_row_label':'18'}))
        self.assertEqual(additions(left,{**left,'columns':'N X Y Z'}),'new_coordinate_output')

    def test_register_type_change_and_first_review(self):
        left={'kind':'family_register','confidence':95}
        self.assertIsNone(additions(left,left))
        self.assertEqual(additions(left,{**left,'kind':'person_register'}),'distinct_register')
        self.assertIsNone(additions(left,{**left,'kind':'person_register','confidence':80}))
        self.assertEqual(additions(left,{**left,'kind':'review_sheet'}),'first_review')

    def test_height_column_aliases_preserve_continuations(self):
        from profile_policy_v4b import additions as refined
        left={'kind':'coordinate_table','confidence':95,'columns':'N X Y','first_row_label':'1'}
        self.assertEqual(refined(left,{**left,'columns':'N X Y H'}),'new_coordinate_output')
        self.assertIsNone(refined({**left,'columns':'N X Y Z'},{**left,'columns':'N X Y Н'}))


if __name__=='__main__':unittest.main()
