import copy,json,logging,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
import artifact_policy,artifact_recovery
from production_state import source_identity

def fact(kind='other',**kw):
    return dict(kind=kind,heading='Title',fresh_start=True,explicit_contract_annex=False,
                drawing_titleblock=False,named_subject='',evidence='Visible facts',confidence=95,**kw)

class PolicyTests(unittest.TestCase):
    def test_table_rows_need_not_restart_after_distinct_safety_note(self):
        r=fact('equipment_schedule');r.update(heading='СПЕЦИФИКАЦИЯ НА ОБЗАВЕЖДАНЕТО',fresh_start=False)
        a=fact('explanatory_note')
        self.assertTrue(artifact_policy.proposal(artifact_policy.combine(a,fact('safety_note'),r))[0])
        self.assertIsNone(artifact_policy.proposal(artifact_policy.combine(a,fact('equipment_schedule'),r)))
    def test_fresh_or_issued_software_drawing_is_preserved(self):
        a=fact('structural_calculation');r=fact('software_plot')
        self.assertIsNone(artifact_policy.proposal(artifact_policy.combine(a,a,r)))
        r['fresh_start']=False;r['drawing_titleblock']=True
        self.assertIsNone(artifact_policy.proposal(artifact_policy.combine(a,a,r)))
        r['drawing_titleblock']=False
        self.assertFalse(artifact_policy.proposal(artifact_policy.combine(a,a,r))[0])
    def test_thermal_subject_must_be_explicit_on_both_pages(self):
        a=fact();l=fact('heating_load');r=fact('cooling_load')
        self.assertIsNone(artifact_policy.proposal(artifact_policy.combine(a,l,r)))
        l['named_subject']=r['named_subject']='Магазин хранителни стоки'
        self.assertEqual(artifact_policy.proposal(artifact_policy.combine(a,l,r))[0],False)
        r['named_subject']='Different building'
        self.assertIsNone(artifact_policy.proposal(artifact_policy.combine(a,l,r)))
    def test_safety_cover_and_continuation_are_preserved(self):
        for anchor in ('project_cover','safety_note','contents'):
            self.assertIsNone(artifact_policy.proposal(artifact_policy.combine(fact(anchor),fact('safety_note'),fact('safety_note'))))
        r=fact('safety_note');r['fresh_start']=False
        self.assertIsNone(artifact_policy.proposal(artifact_policy.combine(fact('explanatory_note'),fact(),r)))
    def test_annex_requires_contract_body_and_explicit_reference(self):
        a=fact();l=fact('contract_body');r=fact('contract_annex')
        self.assertIsNone(artifact_policy.proposal(artifact_policy.combine(a,l,r)))
        r['explicit_contract_annex']=True
        self.assertIsNone(artifact_policy.proposal(artifact_policy.combine(a,l,r)))
        l['heading']='ДОГОВОР № 820'
        self.assertEqual(artifact_policy.proposal(artifact_policy.combine(a,l,r))[0],False)
        self.assertIsNone(artifact_policy.proposal(artifact_policy.combine(a,fact('explanatory_note'),r)))
    def test_invalid_or_low_confidence_facts_do_not_create_cuts(self):
        with self.assertRaises(ValueError):artifact_policy.combine(fact('invented'),fact(),fact())
        low=fact('safety_note');low['confidence']=70
        self.assertIsNone(artifact_policy.proposal(artifact_policy.combine(fact('explanatory_note'),fact(),low)))

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name);self.pdf=self.directory/'original.pdf';self.pdf.write_bytes(b'fixed source bytes')
        self.source=source_identity(self.pdf);self.client=SimpleNamespace(image_labels=True);self.calls=[]
        self.rows={1:fact('contract_body'),2:fact('contract_annex'),3:fact('contract_annex')}
        self.rows[1]['heading']='ДОГОВОР № 820'
        self.rows[2]['explicit_contract_annex']=True
        def infer(prompt,images,*args,**kwargs):
            self.assertFalse(self.client.image_labels);self.assertEqual(len(images),1)
            page=images[0];self.calls.append(page);return json.dumps(self.rows[page])
        self.pipeline=SimpleNamespace(_load_page=lambda pdf,p,dpi:p,_infer=infer,clean_response=lambda raw:raw)
        self.decisions={p:{'new_document':p==2,'left_heading':'Contract','right_heading':'ПРИЛОЖЕНИЕ','confidence':95} for p in (2,3)}
        (self.directory/'summary.json').write_text(json.dumps({'seam_processing_seconds':12,'model_usage':None,'review_candidates':[]}))
    def run_stage(self,settings=None):
        return artifact_recovery.recover(self.pdf,3,(self.client,None,{}),150,logging.getLogger('test'),
            pipeline=self.pipeline,directory=self.directory,source=self.source,settings=settings or {'version':12},
            decisions=self.decisions,rotations={})
    def test_unique_page_queries_raw_preservation_and_idempotent_resume(self):
        before=copy.deepcopy(self.decisions);first=self.run_stage();self.assertEqual(self.calls,[1,2,3])
        self.assertFalse(first[2]['new_document']);self.assertEqual(self.decisions,before);self.assertTrue(self.client.image_labels)
        summary=json.loads((self.directory/'summary.json').read_text());second=self.run_stage()
        self.assertEqual(first,second);self.assertEqual(self.calls,[1,2,3])
        resumed=json.loads((self.directory/'summary.json').read_text())
        self.assertEqual(summary['seam_processing_seconds'],resumed['seam_processing_seconds']);self.assertEqual(resumed['artifact_cached_pages'],3)
        self.assertEqual(resumed['review_candidates'][0]['reasons'],['independent_page_artifact_verification'])
    def test_changed_settings_cannot_reuse_cached_page(self):
        self.run_stage()
        with self.assertRaisesRegex(ValueError,'identity'):self.run_stage({'version':13})
    def test_failed_query_restores_transport_and_does_not_guess_a_cut(self):
        def fail(*args,**kw):raise RuntimeError('temporary server failure')
        self.pipeline._infer=fail
        with self.assertRaises(RuntimeError):self.run_stage()
        self.assertTrue(self.client.image_labels)
        self.assertEqual(json.loads((self.directory/'artifact_pages/0001.json').read_text())['status'],'failed')

if __name__=='__main__':unittest.main()
