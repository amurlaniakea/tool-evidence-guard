# Tool Evidence Guard

<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](LICENSE)

Deterministic, contract-based verification of tool results and exact scalar claims for LLM agents. Pure Python, zero runtime dependencies, runs fully local.

LLM agents keep answering after a tool fails: they assert values the tool never returned, read `null` as zero, or relay `[REDACTED]` as a real answer ([arXiv:2609.14758](https://arxiv.org/abs/2609.14758) measured up to 45.3% dishonest answers when the failure is not signalled). This library checks the evidence **before** the answer: a pre-registered contract states what a usable result must contain, and every claim the agent wants to make must match the captured data exactly.

**`retrieval_status: OK` means contract conformance — not truth.** The contract and the captured result must come from your trusted harness, never from the model. What this checks is deterministic and auditable; what the model says remains unverified unless a claim proves it.

## Features

- Typed fields at JSON Pointer paths (`integer`, `number`, `string`, `boolean`) with optional `minimum`, `maximum`, `enum`
- Detects: declared errors, missing fields, wrong types, `null`, empty strings, redaction placeholders (`[REDACTED]`, `\ufffd`, `n/a`), truncation/corruption/staleness flags, mismatched or fabricated claims
- Freshness opt-in: `max_age_seconds` + timezone-aware `observed_at`, future timestamps rejected
- Exact scalar claim checking (no bool/int confusion, no NaN, no dict comparison) — `0` and `false` are valid values, not absences
- Hard input limits: 1 MiB CLI / 10,000-node API, depth 64, strict JSON (no duplicate keys, no NaN/Infinity)
- Value-free report: reasons are codes, never echoed content; exit codes 0/1/2 for CI gates

## Install

```sh
git clone https://github.com/amurlaniakea/tool-evidence-guard.git
cd tool-evidence-guard
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

Requires Python >= 3.10. No third-party dependencies.

## Usage

```sh
.venv/bin/tool-evidence-guard examples/valid.json     # exit 0: {"retrieval_status": "OK", ...}
.venv/bin/tool-evidence-guard examples/unusable.json  # exit 1: FAILED + reasons
echo '< json >' | .venv/bin/tool-evidence-guard       # stdin also accepted
```

Or as a module: `python3 -m tool_evidence_guard examples/valid.json`

Exit codes: `0` conformant · `1` rejection · `2` unreadable input (invalid JSON, too large, I/O). Use exit 1 as a CI/pre-commit gate.

## Input contract

A JSON document with `contract`, `result`, optional `claims` (unknown root keys rejected):

- `contract.call_id` — non-empty string, assigned by your trusted harness before execution; must equal `result.call_id`
- `contract.fields` — list of rules: `path` (JSON Pointer under `/data/`) + `type`; optional `minimum`/`maximum`/`enum`
- `result.status` must be exactly `ok`; `error` key present means failure even if null; optional boolean flags `truncated`, `stale`, `corrupted`, `redacted` reject when `true`
- `result.observed_at` — ISO 8601 with timezone; required when freshness is enforced
- `claims` — list of exactly `{"path": ..., "value": ...}`; only exact scalar equality with the captured value counts. Zero claims verified → `supported_claims: 0` approves nothing

Each rule must state what the task needs **before** seeing the response. For "did the operation complete" claims, require a final state plus postcondition evidence — not just the submission's `status:ok`.

Full details: [README.es.md](README.es.md) (Spanish, complete contract reference).

## Honest limits

- `OK` = this contract held. It does not certify truth, authorship, permissions, or real execution
- A forged contract + captured payload passes: trust must be established outside the model
- Prose is not analyzed; unmarked corruption in an ordinary string can pass
- Call IDs are correlation, not authentication or signatures
- Not an automatic Hermes/Tars plugin (yet) — use the CLI/library where you decide it matters

## Testing

```sh
.venv/bin/python -m unittest discover -s tests -q   # 51 tests
.venv/bin/python examples/local_demo.py             # real file read + controlled mismatch
```

## Origin

Design informed by *"Fabrication After Tool Failure: Tool-Augmented Agents Assert Values Their Tools Did Not Return"* ([arXiv:2609.14758](https://arxiv.org/abs/2609.14758)). Independent implementation: this is a deterministic contract checker, **not** a reproduction of that paper's model-emitted flag, and none of its measured percentages apply here.

## License

[AGPL-3.0-or-later](LICENSE) — Copyright (C) 2026 Pedro Sordo Martínez <amurlaniakea@gmail.com>.
