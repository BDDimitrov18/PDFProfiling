import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from pypdf import PdfWriter
from qwen38_client import Qwen38Client
from model_options import DEFAULT_DEPLOYMENT
from scripts import run_archive_candidates, run_profile_experiment


class ArchiveRunnerTests(unittest.TestCase):
    def run_fixture(self, module, variant, answer, candidate_mode):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source.pdf';run=root/'run'
            writer=PdfWriter()
            for _ in range(4):writer.add_blank_page(width=72,height=72)
            writer.write(source)
            (root/'sources.json').write_text(json.dumps([source.name]))
            (root/'ground_truth.json').write_text('Ground truth must never be read by this runner')
            (root/'base.json').write_text(json.dumps({'by_tolerance':{'0':{'per_file':[{'file':source.name,'pred':[1,3]}]}}}))
            deployment=json.loads(DEFAULT_DEPLOYMENT.read_text())
            client=Qwen38Client('http://127.0.0.1:8000/v1',deployment['served_model'],deployment)
            args=[str(root),'--sources',str(root/'sources.json'),'--run-dir',str(run),'--variant',variant]
            if candidate_mode:args+=['--baseline',str(root/'base.json')]
            with patch.object(module,'preflight'),patch('split.load_model',return_value=(client,None,{'backend':'qwen38'})), \
                 patch('split._load_page',return_value=Image.new('RGB',(10,10))),patch('split._query_rotation',return_value=0), \
                 patch.object(client,'infer',return_value=json.dumps(answer)) as infer,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(args),0)
                self.assertEqual(infer.call_count,1 if candidate_mode else 4)
                self.assertEqual(len(infer.call_args.args[1]),2 if candidate_mode else 1)
                names=sorted(p.name for p in (run/'seams').glob('*/*.json'))
                self.assertEqual(names,['0003.json'] if candidate_mode else ['0001.json','0002.json','0003.json','0004.json'])
                infer.reset_mock();self.assertEqual(module.main(args),0);infer.assert_not_called()

    def test_candidate_verifier_only_queries_saved_cuts(self):
        self.run_fixture(run_archive_candidates,'typed_v3',{
            'left_heading':'','right_heading':'','left_kind':'other','right_kind':'other',
            'link_evidence':'No narrow continuation evidence.','correction':'none','confidence':95},True)

    def test_profile_runner_includes_first_page_and_one_image_only(self):
        self.run_fixture(run_profile_experiment,'profile_v4',{
            'heading':'','kind':'other','columns':'','first_row_label':'','last_row_label':'',
            'evidence':'Blank page.','confidence':95},False)


if __name__=='__main__':unittest.main()
