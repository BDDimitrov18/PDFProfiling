import unittest
import identity_policy as policy

def page(identifier,report=''):
    return dict(project_id=identifier,project_name='Residential building',report_id=report)

class RomanPlotIdentityTests(unittest.TestCase):
    def test_different_explicit_roman_plots_do_not_merge(self):
        self.assertFalse(policy.shared_project(page('УПИ I-5100001'),page('УПИ II-5100001')))
    def test_missing_optional_roman_prefix_can_still_match(self):
        self.assertTrue(policy.shared_project(page('УПИ II-5100001'),page('5100001')))
    def test_same_roman_prefix_different_formatting_matches(self):
        self.assertTrue(policy.shared_project(page('UPI XXI - 5100001'),page('УПИ XXI–5100001')))
    def test_cyrillic_roman_lookalikes_match(self):
        self.assertTrue(policy.shared_project(page('УПИ ХХІІ-5100001'),page('UPI XXII-5100001')))
    def test_unicode_roman_numerals_match(self):
        self.assertTrue(policy.shared_project(page('УПИ Ⅻ-5100001'),page('UPI XII-5100001')))
    def test_different_numeric_property_ids_remain_different(self):
        self.assertFalse(policy.shared_project(page('УПИ I-5100001'),page('УПИ I-5100002')))
    def test_report_number_conflict_remains_protected(self):
        self.assertFalse(policy.shared_project(page('5100001','R001'),page('5100001','R002')))
    def test_multiple_explicit_plot_labels_are_not_collapsed(self):
        self.assertFalse(policy.shared_project(page('I-5100001; II-5100001'),page('I-5100001')))
    def test_cover_body_proposal_respects_explicit_conflict(self):
        a=dict(page('I-5100001'),kind='assessment_report_cover',confidence=95)
        b=dict(page('II-5100001'),kind='assessment_report_body',confidence=95)
        self.assertIsNone(policy.proposal(a,a,b))

if __name__=='__main__':unittest.main()
