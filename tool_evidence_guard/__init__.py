# SPDX-FileCopyrightText: 2026 Pedro Sordo Martínez <amurlaniakea@gmail.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Contract-based validation of tool evidence, not a truth detector."""
import math
import re
from datetime import datetime, timezone

__version__ = "0.1.0"
_FLAGS = ("truncated", "stale", "corrupted", "redacted")
_TYPES = {"integer", "number", "string", "boolean"}


def _finite(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _matches(value, kind):
    return {
        "integer": type(value) is int,
        "number": type(value) in (int, float),
        "boolean": type(value) is bool,
        "string": type(value) is str,
    }[kind]


def _same(left, right):
    return type(left) is type(right) and left == right


def _bounded(document):
    """Bound traversal of Python API inputs, including cycles and wide trees."""
    stack, nodes, size = [(document, 1)], 0, 0
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if nodes > 10000 or depth > 64:
            return False
        if isinstance(node, dict):
            if len(node) + nodes + len(stack) > 10000:
                return False
            if not all(isinstance(key, str) for key in node):
                return False
            size += sum(len(key) for key in node)
            stack.extend((child, depth + 1) for child in node.values())
        elif isinstance(node, list):
            if len(node) + nodes + len(stack) > 10000:
                return False
            stack.extend((child, depth + 1) for child in node)
        elif isinstance(node, str):
            size += len(node)
        elif node is not None and type(node) not in (int, float, bool):
            return False
        if size > 1_048_576:
            return False
    return True


def _contract_fields(contract):
    """Return validated rules, or None. This is a small DSL, not JSON Schema."""
    if not isinstance(contract, dict) or set(contract) - {"call_id", "fields", "max_age_seconds"}:
        return None
    if not isinstance(contract.get("call_id"), str) or not contract["call_id"].strip():
        return None
    if "max_age_seconds" in contract:
        age = contract["max_age_seconds"]
        if not _finite(age) or age <= 0:
            return None
    fields = contract.get("fields")
    if not isinstance(fields, list) or not fields:
        return None
    declared = {}
    for field in fields:
        if not isinstance(field, dict) or set(field) - {"path", "type", "minimum", "maximum", "enum"}:
            return None
        path, kind = field.get("path"), field.get("type")
        if not isinstance(path, str) or not path.startswith("/data/") or re.search(r"~(?![01])", path):
            return None
        if not isinstance(kind, str) or kind not in _TYPES or path in declared:
            return None
        for key in ("minimum", "maximum"):
            if key in field and (kind not in ("integer", "number") or not _finite(field[key])):
                return None
        if "minimum" in field and "maximum" in field and field["minimum"] > field["maximum"]:
            return None
        if "enum" in field:
            choices = field["enum"]
            if not isinstance(choices, list) or not choices:
                return None
            if any(not _matches(item, kind) or (type(item) in (int, float) and not _finite(item)) for item in choices):
                return None
        declared[path] = field
    return declared


def _resolve(result, path):
    value = result
    for token in path[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise KeyError(token)
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise KeyError(token)
    return value


def _freshness(result, contract):
    if "max_age_seconds" not in contract and "observed_at" not in result:
        return []
    timestamp = result.get("observed_at")
    try:
        if not isinstance(timestamp, str):
            raise ValueError
        observed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError
        age = (datetime.now(timezone.utc) - observed).total_seconds()
    except (ValueError, OverflowError):
        return ["INVALID_TIMESTAMP"]
    if age < 0:
        return ["FUTURE_TIMESTAMP"]
    if "max_age_seconds" in contract and age > contract["max_age_seconds"]:
        return ["STALE_RESULT"]
    return []


def check(document):
    """Validate a trusted contract against captured data and exact scalar claims.

    OK means contract conformance only. Caller must capture results and establish
    the contract independently of untrusted model output. No claims are inferred.
    """
    supported = 0

    def report(reasons):
        return {"retrieval_status": "FAILED" if reasons else "OK",
                "reasons": list(dict.fromkeys(reasons)),
                "supported_claims": 0 if reasons else supported}

    if not _bounded(document):
        return report(["INPUT_LIMIT"])
    if not isinstance(document, dict):
        return report(["INVALID_CONTRACT"])
    if set(document) - {"contract", "result", "claims"}:
        return report(["INVALID_DOCUMENT"])
    contract = document.get("contract")
    declared = _contract_fields(contract)
    if declared is None:
        return report(["INVALID_CONTRACT"])
    result = document.get("result")
    if not isinstance(result, dict):
        return report(["INVALID_RESULT"])
    reasons = []
    for flag in _FLAGS:
        if flag in result and type(result[flag]) is not bool:
            reasons.append("INVALID_RESULT")
        elif result.get(flag) is True:
            reasons.append(flag.upper() + "_RESULT")
    if result.get("status") != "ok" or "error" in result:
        reasons.append("TOOL_ERROR")
    if not _same(result.get("call_id"), contract["call_id"]):
        reasons.append("CALL_ID_MISMATCH")
    reasons.extend(_freshness(result, contract))
    values = {}
    for path, field in declared.items():
        try:
            value = _resolve(result, path)
        except (KeyError, IndexError, ValueError):
            reasons.append("MISSING_FIELD")
            continue
        if not _matches(value, field["type"]):
            reasons.append("TYPE_MISMATCH")
            continue
        if type(value) in (int, float):
            if not _finite(value):
                reasons.append("NONFINITE_VALUE")
                continue
            if ("minimum" in field and value < field["minimum"]) or ("maximum" in field and value > field["maximum"]):
                reasons.append("OUT_OF_RANGE")
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if not normalized:
                reasons.append("EMPTY_VALUE")
            elif "[redacted]" in normalized or normalized in {"***", "n/a", "null", "undefined"} or "\ufffd" in value:
                reasons.append("UNUSABLE_PLACEHOLDER")
        if "enum" in field and not any(_same(value, allowed) for allowed in field["enum"]):
            reasons.append("VALUE_NOT_ALLOWED")
        values[path] = value
    claims = document.get("claims", [])
    if not isinstance(claims, list):
        reasons.append("INVALID_CLAIMS")
        return report(reasons)
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {"path", "value"} or not isinstance(claim["path"], str):
            reasons.append("INVALID_CLAIMS")
            continue
        path = claim["path"]
        if path not in declared:
            reasons.append("UNDECLARED_CLAIM")
        elif path not in values or not _same(claim["value"], values[path]):
            reasons.append("CLAIM_MISMATCH")
        else:
            supported += 1
    return report(reasons)
