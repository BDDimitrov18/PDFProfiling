import json
from pathlib import Path
import tempfile
import unittest

from model_options import DEFAULT_DEPLOYMENT
from scripts.run_qwen38_pilot import plan_stages


class PilotBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('smoke_qwen38.py', 'eval_boundaries.py', 'score_full.py'):
            (self.root / name).touch()
        for name in ('eval_full', 'eval_gergana'):
            folder = self.root / name
            folder.mkdir()
            (folder / 'source.pdf').touch()
            (folder / 'ground_truth.json').write_text(json.dumps({'source.pdf': [1]}))

    def plan(self, **kwargs):
        return plan_stages(self.root, self.root / 'run', 'http://127.0.0.1:8000/v1',
                           DEFAULT_DEPLOYMENT, 150, 600, **kwargs)

    def test_medium_only_applies_larger_budget_to_smoke_and_both_datasets(self):
        stages = self.plan(thinking='medium')
        self.assertEqual([s['id'] for s in stages], [
            'smoke-medium', 'eval_full-medium', 'eval_full-medium-score',
            'eval_gergana-medium', 'eval_gergana-medium-score'])
        for stage in stages:
            if stage['kind'] != 'score':
                command = stage['command']
                self.assertEqual(command[command.index('--max-completion-tokens') + 1], '16384')
                self.assertEqual(command[command.index('--thinking') + 1], 'medium')
        self.assertFalse((self.root / 'run').exists())

    def test_off_budget_is_unchanged_and_old_medium_budget_can_be_reproduced(self):
        for selection, cap in [('off', '4096'), ('medium', '8192')]:
            stages = self.plan(thinking=selection, medium_max_completion_tokens=8192)
            command = stages[0]['command']
            self.assertEqual(command[command.index('--max-completion-tokens') + 1], cap)
        self.assertEqual(len(self.plan()), 10)

    def test_budget_cannot_reach_server_context_and_invalid_selection_is_rejected(self):
        for cap in (0, -1, True, 32768, 65536):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                self.plan(thinking='medium', medium_max_completion_tokens=cap)
        with self.assertRaises(ValueError):
            self.plan(thinking='invalid')


if __name__ == '__main__':
    unittest.main()
