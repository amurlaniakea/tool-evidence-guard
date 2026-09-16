# SPDX-License-Identifier: AGPL-3.0-or-later
import copy
import importlib.util
import unittest


def document(value=42):
    return {
        "contract": {
            "call_id": "call-1",
            "fields": [{"path": "/data/value", "type": "integer"}],
        },
        "result": {"status": "ok", "call_id": "call-1", "data": {"value": value}},
        "claims": [{"path": "/data/value", "value": value}],
    }


class GuardTests(unittest.TestCase):
    def check(self, doc):
        self.assertIsNotNone(importlib.util.find_spec("tool_evidence_guard"),
                             "Missing tool-output verifier implementation")
        from tool_evidence_guard import check
        return check(doc)

    def test_ok_without_contract_is_rejected(self):
        out = self.check({"result": {"status": "ok"}})
        self.assertEqual(out["retrieval_status"], "FAILED")
        self.assertIn("INVALID_CONTRACT", out["reasons"])

    def test_ok_without_call_id_is_rejected(self):
        doc = document()
        del doc["result"]["call_id"]
        self.assertIn("CALL_ID_MISMATCH", self.check(doc)["reasons"])

    def test_valid_value_supports_claim(self):
        out = self.check(document())
        self.assertEqual(out["retrieval_status"], "OK")
        self.assertEqual(out["supported_claims"], 1)

    def test_missing_field_is_not_zero(self):
        doc = document(0)
        doc["result"]["data"] = {}
        self.assertIn("MISSING_FIELD", self.check(doc)["reasons"])

    def test_wrong_call_cannot_support_claim(self):
        doc = document()
        doc["result"]["call_id"] = "old-call"
        self.assertIn("CALL_ID_MISMATCH", self.check(doc)["reasons"])

    def test_explicit_error_overrides_data(self):
        doc = document()
        doc["result"]["status"] = "error"
        self.assertIn("TOOL_ERROR", self.check(doc)["reasons"])

    def test_null_and_wrong_type_rejected(self):
        for value in [None, "42", True, {}, []]:
            with self.subTest(value=value):
                self.assertEqual(self.check(document(value))["retrieval_status"], "FAILED")

    def test_zero_is_valid(self):
        self.assertEqual(self.check(document(0))["retrieval_status"], "OK")

    def test_fabricated_value_rejected(self):
        doc = document()
        doc["claims"][0]["value"] = 123
        out = self.check(doc)
        self.assertIn("CLAIM_MISMATCH", out["reasons"])
        self.assertEqual(out["supported_claims"], 0)

    def test_claim_outside_contract_rejected(self):
        doc = document()
        doc["claims"][0]["path"] = "/status"
        doc["claims"][0]["value"] = "ok"
        self.assertIn("UNDECLARED_CLAIM", self.check(doc)["reasons"])

    def test_no_input_mutation(self):
        doc = document()
        original = copy.deepcopy(doc)
        self.check(doc)
        self.assertEqual(doc, original)


if __name__ == "__main__":
    unittest.main()
