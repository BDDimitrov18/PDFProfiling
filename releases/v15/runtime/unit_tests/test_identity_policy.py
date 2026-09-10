import unittest
from identity_policy import proposal

def facts(kind, **values):
    return dict(kind=kind, confidence=95, fresh_start=False, **values)

class IdentityPolicyTests(unittest.TestCase):
    def test_certification_requires_two_literal_identifiers_without_conflict(self):
        a=facts('notarial_signature_certificate',principal_birth_date='11.08.1969',principal_company_id='175198935')
        l=facts('apostille');r=facts('power_of_attorney',principal_birth_date='11.08.1969',principal_company_id='175198935')
        self.assertEqual(proposal(a,l,r)[0],False)
        self.assertIsNone(proposal(a,l,{**r,'principal_company_id':'175198936'}))
        self.assertIsNone(proposal(a,l,{**r,'principal_company_id':''}))
        self.assertIsNone(proposal(a,facts('other'),r))

    def test_report_cover_requires_same_literal_project_and_body(self):
        a=facts('assessment_report_cover',project_id='56784.123.45')
        r=facts('assessment_report_body',project_id='56784.123.45')
        self.assertFalse(proposal(a,a,r)[0])
        self.assertIsNone(proposal(a,a,{**r,'project_id':'56784.123.46'}))
        self.assertIsNone(proposal(a,a,facts('assessment_report_body')))
        self.assertIsNone(proposal(a,a,{**r,'kind':'assessment_report_cover'}))

    def test_seasonal_outputs_preserve_different_projects_or_new_reports(self):
        a=facts('cooling_output',project_name='Магазин за хранителни стоки')
        l=facts('cooling_output');r=facts('heating_output',project_name='Магазин за хранителни стоки')
        self.assertFalse(proposal(a,l,r)[0])
        self.assertIsNone(proposal(a,l,{**r,'project_name':'Жилищна сграда'}))
        self.assertIsNone(proposal(a,l,{**r,'kind':'assessment_report_cover'}))
        self.assertIsNone(proposal(a,{**l,'project_id':'123.45'}, {**r,'project_id':'123.46'}))

    def test_backward_regulatory_requires_waste_transition_and_total(self):
        a=facts('waste_plan',printed_page='17',printed_total='18')
        r=facts('regulatory_list',printed_page='7',printed_total='18');r['fresh_start']=True
        self.assertTrue(proposal(a,a,r)[0])
        for update in ({'printed_total':'20'},{'printed_page':'18'},{'printed_page':''},{'fresh_start':False}):
            self.assertIsNone(proposal(a,a,{**r,**update}))
        self.assertIsNone(proposal(a,{**a,'kind':'other'},r))

    def test_review_bridge_does_not_join_different_projects(self):
        a=facts('review_sheet',project_id='56784.123.45');l=facts('signature_note')
        self.assertFalse(proposal(a,l,a,a)[0])
        self.assertIsNone(proposal(a,l,{**a,'project_id':'56784.123.46'},a))
        self.assertIsNone(proposal(a,l,a,None))
        self.assertIsNone(proposal(a,facts('other'),a,a))

if __name__=='__main__':unittest.main()
