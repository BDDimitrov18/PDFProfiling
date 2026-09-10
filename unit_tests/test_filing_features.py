import unittest
from filing_features import decision


class FilingFeatureTests(unittest.TestCase):
    def test_first_review_recovery_is_idempotent(self):
        d={'left_heading':'','right_heading':'','left_kind':'other','right_kind':'review_sheet',
           'left_columns':'','right_columns':'','right_first_row_label':'','page_type_confidence':95,
           'relationship':'attachment','evidence':'Review fields follow an application.','new_document':False,'confidence':95}
        result=decision(d)
        self.assertTrue(result['new_document']);self.assertFalse(result['model_new_document'])
        self.assertEqual(decision(result),result)
        self.assertFalse(decision({**d,'left_kind':'review_sheet'})['new_document'])
        self.assertFalse(decision({**d,'page_type_confidence':80})['new_document'])


if __name__=='__main__':unittest.main()
