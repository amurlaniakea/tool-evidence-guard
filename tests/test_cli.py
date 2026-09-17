# SPDX-FileCopyrightText: 2026 Pedro Sordo Martínez <amurlaniakea@gmail.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_guard import document


class CLITests(unittest.TestCase):
    def run_cli(self, payload, *args):
        return subprocess.run([sys.executable, '-m', 'tool_evidence_guard', *args],
                              input=payload, text=True, capture_output=True, timeout=10,
                              check=False)

    def test_stdin_valid(self):
        result = self.run_cli(json.dumps(document()))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['supported_claims'], 1)

    def test_reject_returns_one(self):
        result = self.run_cli(json.dumps(document(None)))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['retrieval_status'], 'FAILED')

    def test_malformed_returns_two_without_echo(self):
        for payload in ['SECRET: invalid', '{"x":NaN}', '{"x":1,"x":2}', '[' * 2000]:
            result = self.run_cli(payload)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['reasons'], ['INVALID_JSON'])
            self.assertNotIn('SECRET', result.stdout + result.stderr)

    def test_file_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_text(json.dumps(document()))
            result = self.run_cli('', str(path))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_file(self):
        result = self.run_cli('', '/does-not-exist/input.json')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['reasons'], ['INPUT_ERROR'])

    def test_input_size_limit(self):
        result = self.run_cli(' ' * 1_048_577)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['reasons'], ['INPUT_LIMIT'])

    def test_help(self):
        result = self.run_cli('', '--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('tool-evidence-guard', result.stdout)


if __name__ == '__main__':
    unittest.main()
