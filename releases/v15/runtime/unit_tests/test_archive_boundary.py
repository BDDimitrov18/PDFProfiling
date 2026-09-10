import unittest
from archive_boundary import decision


class ArchiveBoundaryTests(unittest.TestCase):
    def test_veto_needs_consistent_visible_evidence(self):
        d={'left_heading':'СЪОБЩЕНИЕ','right_heading':'ИЗВЕСТИЕ ЗА ДОСТАВЯНЕ',
           'left_kind':'letter','right_kind':'postal_receipt','link_evidence':'Both show reference 123.',
           'correction':'postal_attachment','confidence':95}
        self.assertFalse(decision(d)['new_document'])
        for changed in ({'left_kind':'other'},{'right_kind':'other'},{'link_evidence':''},
                        {'confidence':89},{'correction':'none'}):
            self.assertTrue(decision({**d,**changed})['new_document'])
        with self.assertRaises(ValueError):decision({**d,'correction':'generic_attachment'})

    def test_review_sequence_does_not_remove_first_review_sheet(self):
        d={'left_heading':'','right_heading':'','left_kind':'other','right_kind':'review_sheet',
           'link_evidence':'Review form fields','correction':'review_series','confidence':95}
        self.assertTrue(decision(d)['new_document'])
        self.assertFalse(decision({**d,'left_kind':'review_sheet'})['new_document'])


if __name__=='__main__':unittest.main()
