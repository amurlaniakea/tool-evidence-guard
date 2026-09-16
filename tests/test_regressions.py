# SPDX-License-Identifier: AGPL-3.0-or-later
import unittest
from datetime import datetime, timezone
from test_guard import document
from tool_evidence_guard import check


class RegressionTests(unittest.TestCase):
    def test_no_claims_means_zero_supported_claims(self):
        doc = document()
        doc.pop('claims')
        self.assertEqual(check(doc)['supported_claims'], 0)

    def test_numeric_enum_enforced(self):
        doc = document(2)
        doc['contract']['fields'][0]['enum'] = [1]
        self.assertIn('VALUE_NOT_ALLOWED', check(doc)['reasons'])

    def test_boolean_enum_allowed(self):
        doc = document(False)
        doc['contract']['fields'][0].update(type='boolean', enum=[False])
        self.assertEqual(check(doc)['retrieval_status'], 'OK')

    def test_flag_must_be_boolean_not_integer(self):
        for flag in [0, 1, None]:
            doc = document()
            doc['result']['truncated'] = flag
            self.assertIn('INVALID_RESULT', check(doc)['reasons'])

    def test_numeric_call_id_not_allowed(self):
        doc = document()
        doc['contract']['call_id'] = doc['result']['call_id'] = 1
        self.assertIn('INVALID_CONTRACT', check(doc)['reasons'])

    def test_contract_limits_must_be_finite_and_applicable(self):
        for field in [dict(minimum=float('nan')), dict(maximum=float('inf')),
                      dict(type='string', minimum=1), dict(enum=[{}]), dict(minimum=None)]:
            doc = document()
            doc['contract']['fields'][0].update(field)
            self.assertIn('INVALID_CONTRACT', check(doc)['reasons'])
        for age in [None, float('nan'), float('inf'), True]:
            doc = document()
            doc['contract']['max_age_seconds'] = age
            self.assertIn('INVALID_CONTRACT', check(doc)['reasons'])

    def test_noncanonical_array_indices_rejected(self):
        for index in ['-1', '00', '+0', ' 0']:
            doc = document()
            path = '/data/values/' + index
            doc['result']['data'] = {'values': [42]}
            doc['contract']['fields'][0]['path'] = path
            doc['claims'][0]['path'] = path
            self.assertIn('MISSING_FIELD', check(doc)['reasons'])

    def test_fresh_timestamp(self):
        doc = document()
        doc['contract']['max_age_seconds'] = 60
        doc['result']['observed_at'] = datetime.now(timezone.utc).isoformat()
        self.assertEqual(check(doc)['retrieval_status'], 'OK')

    def test_mixed_case_and_embedded_redaction(self):
        for value in [' [redacted] ', 'Value: [REDACTED]', 'bad\ufffdtext']:
            doc = document(value)
            doc['contract']['fields'][0]['type'] = 'string'
            self.assertEqual(check(doc)['retrieval_status'], 'FAILED')

    def test_unknown_document_key_rejected(self):
        doc = document()
        doc['claim'] = [{'value': 1234}]
        self.assertIn('INVALID_DOCUMENT', check(doc)['reasons'])

    def test_large_tree_rejected(self):
        doc = document()
        doc['result']['extra'] = list(range(20000))
        self.assertIn('INPUT_LIMIT', check(doc)['reasons'])

    def test_bool_cannot_match_numeric_claim(self):
        doc = document(1)
        doc['claims'][0]['value'] = True
        self.assertIn('CLAIM_MISMATCH', check(doc)['reasons'])

    def test_huge_integer_valid(self):
        self.assertEqual(check(document(10**400))['retrieval_status'], 'OK')
