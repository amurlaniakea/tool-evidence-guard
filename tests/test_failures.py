# SPDX-License-Identifier: AGPL-3.0-or-later
import unittest
from test_guard import document
from tool_evidence_guard import check


class FailureTests(unittest.TestCase):
    def test_redacted_string_rejected(self):
        for value in ['[REDACTED]', '***', 'n/a', '\ufffd']:
            doc = document(value)
            doc['contract']['fields'][0]['type'] = 'string'
            self.assertEqual(check(doc)['retrieval_status'], 'FAILED')

    def test_empty_string_rejected(self):
        doc = document('   ')
        doc['contract']['fields'][0]['type'] = 'string'
        self.assertIn('EMPTY_VALUE', check(doc)['reasons'])

    def test_false_is_valid_boolean(self):
        doc = document(False)
        doc['contract']['fields'][0]['type'] = 'boolean'
        self.assertEqual(check(doc)['retrieval_status'], 'OK')

    def test_truncation_flags_reject(self):
        for flag in ['truncated', 'stale', 'corrupted', 'redacted']:
            doc = document()
            doc['result'][flag] = True
            self.assertEqual(check(doc)['retrieval_status'], 'FAILED')

    def test_malformed_flag_is_not_ignored(self):
        doc = document()
        doc['result']['truncated'] = 'false'
        self.assertIn('INVALID_RESULT', check(doc)['reasons'])

    def test_explicit_error_overrides_ok(self):
        doc = document()
        doc['result']['error'] = 'network unavailable'
        self.assertIn('TOOL_ERROR', check(doc)['reasons'])

    def test_number_nonfinite_rejected(self):
        for value in [float('nan'), float('inf')]:
            doc = document(value)
            doc['contract']['fields'][0]['type'] = 'number'
            self.assertIn('NONFINITE_VALUE', check(doc)['reasons'])

    def test_number_constraints(self):
        for value in [-1, 101]:
            doc = document(value)
            doc['contract']['fields'][0].update(minimum=0, maximum=100)
            self.assertIn('OUT_OF_RANGE', check(doc)['reasons'])

    def test_string_enum_checks_completion_not_just_success(self):
        doc = document('pending')
        doc['contract']['fields'][0].update(type='string', enum=['completed'])
        self.assertIn('VALUE_NOT_ALLOWED', check(doc)['reasons'])

    def test_age_requires_timestamp(self):
        doc = document()
        doc['contract']['max_age_seconds'] = 60
        self.assertIn('INVALID_TIMESTAMP', check(doc)['reasons'])

    def test_stale_timestamp(self):
        doc = document()
        doc['contract']['max_age_seconds'] = 60
        doc['result']['observed_at'] = '2000-01-01T00:00:00Z'
        self.assertIn('STALE_RESULT', check(doc)['reasons'])

    def test_future_timestamp(self):
        doc = document()
        doc['contract']['max_age_seconds'] = 60
        doc['result']['observed_at'] = '2999-01-01T00:00:00Z'
        self.assertIn('FUTURE_TIMESTAMP', check(doc)['reasons'])

    def test_timestamp_needs_timezone(self):
        doc = document()
        doc['contract']['max_age_seconds'] = 60
        doc['result']['observed_at'] = '2026-09-17T12:00:00'
        self.assertIn('INVALID_TIMESTAMP', check(doc)['reasons'])

    def test_json_pointer_escapes_and_array_index(self):
        doc = document()
        path = '/data/a~1b/0/~0value'
        doc['contract']['fields'][0]['path'] = path
        doc['claims'][0]['path'] = path
        doc['result']['data'] = {'a/b': [{'~value': 42}]}
        self.assertEqual(check(doc)['retrieval_status'], 'OK')

    def test_invalid_contracts_fail_cleanly(self):
        changes = [ {'call_id': []}, {'typo': True}, {'max_age_seconds': -1},
                    {'fields': [{'path': '/data/x', 'type': []}]},
                    {'fields': [{'path': '/data/x', 'type': 'integer', 'minimun': 5}]},
                    {'fields': [{'path': '/data/x', 'type': 'integer', 'minimum': True}]},
                    {'fields': [{'path': '/data/x', 'type': 'integer', 'minimum': 9, 'maximum': 1}]},
                    {'fields': [{'path': '/data/x~2', 'type': 'integer'}]} ]
        for change in changes:
            with self.subTest(change=change):
                doc = document()
                doc['contract'].update(change)
                self.assertIn('INVALID_CONTRACT', check(doc)['reasons'])

    def test_invalid_claim_path_fails_cleanly(self):
        doc = document()
        doc['claims'][0]['path'] = []
        self.assertIn('INVALID_CLAIMS', check(doc)['reasons'])

    def test_prose_cannot_be_silently_approved(self):
        doc = document()
        doc['claims'][0]['text'] = 'Additionally, the deployment succeeded.'
        self.assertIn('INVALID_CLAIMS', check(doc)['reasons'])

    def test_values_not_echoed_to_report(self):
        doc = document('private-test-value')
        out = check(doc)
        self.assertNotIn('private-test-value', str(out))

    def test_deep_input_fails_cleanly(self):
        doc = document()
        value = {}
        doc['result']['irrelevant'] = value
        for _ in range(100):
            value['next'] = {}
            value = value['next']
        self.assertIn('INPUT_LIMIT', check(doc)['reasons'])


if __name__ == '__main__':
    unittest.main()
