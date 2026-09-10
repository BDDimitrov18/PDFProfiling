import unittest
import identity_policy
import legal_crop_policy,report_ocr_policy

def legal(kind,company='ТЕСТКОМ 123'):
    return dict(kind=kind,confidence=95,principal_name='Иван Петров Иванов',principal_birth_date='01.02.1980',
                principal_company_name=company,principal_company_id='123456789',certifies_attached_power_of_attorney=True,
                attachment_quote='на прибавеното тук пълномощно')

class IdentityExtensionsTests(unittest.TestCase):
    def test_literal_identifier_prefixes_and_descriptive_extensions(self):
        a=dict(project_id='360020',project_name='Жилищна сграда в УПИ XI',report_id='')
        b=dict(project_id='УПИ XI - 360020',project_name='Жилищна сграда в УПИ XI - 360020, квартал 91',report_id='')
        self.assertTrue(identity_policy.shared_project(a,b))
        self.assertFalse(identity_policy.shared_project(a,{**b,'project_id':'360021'}))
        self.assertFalse(identity_policy.shared_project(a,{**b,'project_name':'Друг обект на същия имот'}))
    def test_company_crop_requires_independent_exact_principal_and_full_name(self):
        full=legal('notarial_signature_certificate','ТЕСТКОМ');left=legal('apostille');right=legal('power_of_attorney');crop=legal('notarial_signature_certificate')
        self.assertTrue(legal_crop_policy.needed(full,left,right))
        self.assertFalse(legal_crop_policy.proposal(full,left,right,crop)[0])
        for update in ({'principal_name':'Друг човек'}, {'principal_birth_date':'02.02.1980'},
                       {'principal_company_name':'ТЕСТКОМ 124'}, {'certifies_attached_power_of_attorney':False}):
            self.assertIsNone(legal_crop_policy.proposal(full,left,right,{**crop,**update}))
        self.assertFalse(legal_crop_policy.needed({**full,'principal_company_name':'ТЕСТКОМ 12'},left,right))
        self.assertFalse(legal_crop_policy.needed({**full,'certifies_attached_power_of_attorney':False},left,right))
    def test_report_ocr_requires_agreement_of_both_modes_and_crop(self):
        a=dict(kind='assessment_report_cover',confidence=95,regulated_plot='XII 7654321',quarter='86',subproject='Сграда 1')
        b={**a,'kind':'assessment_report_body','regulated_plot':'XXII 7654321'}
        crop={**a,'regulated_plot':'XXII 7654321'};texts=['Обект XXII 7654321 за строеж','XXII 7654321']
        self.assertFalse(report_ocr_policy.proposal(a,b,crop,crop,texts,texts)[0])
        self.assertIsNone(report_ocr_policy.proposal(a,b,crop,crop,['XII 7654321',texts[1]],texts))
        self.assertIsNone(report_ocr_policy.proposal(a,b,a,crop,texts,texts))
        self.assertIsNone(report_ocr_policy.proposal(a,b,crop,{**crop,'subproject':'Сграда 2'},texts,texts))
        self.assertIsNone(report_ocr_policy.proposal(a,{**b,'regulated_plot':'XXII 7654322'},crop,crop,texts,texts))
        self.assertIsNone(report_ocr_policy.consensus(['XXII 7654321 XII 7654321',texts[1]],'7654321'))
        self.assertEqual(report_ocr_policy.norm('ХХІІ 7654321'),report_ocr_policy.norm('XXII 7654321'))

if __name__=='__main__':unittest.main()
