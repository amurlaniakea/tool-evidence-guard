# SPDX-FileCopyrightText: 2026 Pedro Sordo Martínez <amurlaniakea@gmail.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read one bounded JSON document, emit a value-free verification report."""
import argparse
import json
import sys

from . import check

LIMIT = 1_048_576


def reject_constant(value):
    raise ValueError("Nonstandard JSON constant")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tool-evidence-guard")
    parser.add_argument("input", nargs="?", default="-", help="JSON file or - for stdin")
    args = parser.parse_args(argv)
    reason = None
    try:
        if args.input == "-":
            raw = sys.stdin.buffer.read(LIMIT + 1)
        else:
            with open(args.input, "rb") as stream:
                raw = stream.read(LIMIT + 1)
        if len(raw) > LIMIT:
            reason = "INPUT_LIMIT"
        else:
            try:
                doc = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                                 parse_constant=reject_constant)
            except (ValueError, RecursionError):
                reason = "INVALID_JSON"
    except OSError:
        reason = "INPUT_ERROR"
    if reason:
        out = {"retrieval_status": "FAILED", "reasons": [reason], "supported_claims": 0}
        code = 2
    else:
        out = check(doc)
        code = 0 if out["retrieval_status"] == "OK" else 1
    print(json.dumps(out, ensure_ascii=True, allow_nan=False))
    return code
