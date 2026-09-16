# SPDX-License-Identifier: AGPL-3.0-or-later
"""Real local file reads; false claim is explicitly a controlled test case."""
import json
import tempfile
import uuid
from pathlib import Path
from tool_evidence_guard import check


def main():
    contract = {'call_id': str(uuid.uuid4()), 'fields': [
        {'path': '/data/bytes', 'type': 'integer', 'minimum': 0}]}
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'sample.txt'
        path.write_bytes(b'local tool evidence\n')
        captured = {'call_id': contract['call_id'], 'status': 'ok',
                    'data': {'bytes': len(path.read_bytes())}}
        observed = captured['data']['bytes']
        document = {'contract': contract, 'result': captured,
                    'claims': [{'path': '/data/bytes', 'value': observed}]}
        reports = {'real_file_read': check(document)}
        document['claims'][0]['value'] = observed + 100  # Intentional test mismatch.
        reports['controlled_false_claim'] = check(document)
        failed_contract = dict(contract, call_id=str(uuid.uuid4()))
        try:
            (Path(directory) / 'absent.txt').read_bytes()
        except FileNotFoundError:
            reports['real_missing_file'] = check({
                'contract': failed_contract,
                'result': {'call_id': failed_contract['call_id'], 'status': 'error',
                           'error': 'FileNotFoundError'},
            })
    print(json.dumps(reports, indent=2))


if __name__ == '__main__':
    main()
