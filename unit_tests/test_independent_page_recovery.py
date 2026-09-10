import json,logging,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from independent_page_recovery import read
from production_state import source_identity

class IndependentPageRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name);self.pdf=self.directory/'source.pdf';self.pdf.write_bytes(b'fixed PDF bytes')
        self.source=source_identity(self.pdf);self.client=SimpleNamespace(image_labels=True);self.calls=[]
        def infer(prompt,images,*args,**kw):
            self.assertFalse(self.client.image_labels);self.assertEqual(len(images),1)
            self.calls.append(images[0]);return json.dumps({'kind':'other'})
        self.pipeline=SimpleNamespace(_load_page=lambda pdf,p,dpi:p,_infer=infer,clean_response=lambda x:x)
        self.module=SimpleNamespace(SCHEMA={'kind':str},prompt=lambda p:'Read one page',validate=lambda f:f)
    def run_stage(self,settings=None):
        return read(self.pdf,[(2,''),(1,''),(2,'')],self.module,'facts',(self.client,None,{}),150,logging.getLogger('test'),
                    pipeline=self.pipeline,directory=self.directory,source=self.source,settings=settings or {'version':13},rotations={})
    def test_deduplicates_and_resumes_without_requery(self):
        facts,records,hits=self.run_stage();self.assertEqual(self.calls,[1,2]);self.assertEqual(hits,0)
        self.assertTrue(self.client.image_labels);self.assertEqual(len(records),2)
        self.assertEqual(records[0]['raw_final'],'{"kind": "other"}')
        second=self.run_stage();self.assertEqual(facts,second[0]);self.assertEqual(second[2],2);self.assertEqual(self.calls,[1,2])
        with self.assertRaisesRegex(ValueError,'identity'):self.run_stage({'version':14})
    def test_failure_restores_transport_and_is_restartable(self):
        original=self.pipeline._infer
        def fail(*a,**kw):raise RuntimeError('temporary request error')
        self.pipeline._infer=fail
        with self.assertRaises(RuntimeError):self.run_stage()
        self.assertTrue(self.client.image_labels)
        record=json.loads((self.directory/'facts/0001.json').read_text());self.assertEqual(record['status'],'failed')
        self.pipeline._infer=original
        _,records,_=self.run_stage();self.assertEqual(records[0]['attempts'],2);self.assertEqual(records[0]['history'][0]['status'],'failed')
    def test_source_mutation_aborts_even_on_cached_resume(self):
        self.run_stage();self.pdf.write_bytes(b'changed PDF bytes')
        with self.assertRaisesRegex(ValueError,'Source changed'):self.run_stage()

if __name__=='__main__':unittest.main()
