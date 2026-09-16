# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path
import subprocess
import sys
import unittest


class DemoTests(unittest.TestCase):
    def test_real_local_read_then_controlled_mismatch(self):
        script = Path(__file__).resolve().parents[1] / 'examples' / 'local_demo.py'
        project = Path(__file__).resolve().parents[1]
        result = subprocess.run([str(project / '.venv' / 'bin' / 'python'), str(script)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        cases = json.loads(result.stdout)
        self.assertEqual(cases['real_file_read']['retrieval_status'], 'OK')
        self.assertEqual(cases['controlled_false_claim']['retrieval_status'], 'FAILED')
        self.assertEqual(cases['real_missing_file']['retrieval_status'], 'FAILED')
