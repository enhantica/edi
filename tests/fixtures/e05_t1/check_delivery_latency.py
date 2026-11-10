"""Feed actual app delivery measurements into 's existing median ratchet.

Run after the focused manual Qt Quick test. First measurements on an unbanked hand
host are reported; runner measurements require a bank, using the same ten-table
writer and improvement/re-bank rule as the chart. No absolute speed is a limit.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
paths = sorted((ROOT / 'build/delivery-latency').glob('*.json'))
if not paths:
    raise SystemExit(' gate 7 no actual owner-delivery measurement was produced')
with tempfile.TemporaryDirectory(prefix='delivery-hand-bank-') as temporary:
    bank = ROOT / 'tests/latency-bank.json'
    if not bank.exists():
        if any(
            not json.loads(path.read_text()).get('machine', '').startswith('hand:')
            for path in paths
        ):
            raise SystemExit(' runner delivery measurements require a committed machine bank')
        bank = Path(temporary) / 'unbanked-hand.json'
        bank.write_text('{"schema":1,"machines":{}}')
    for path in paths:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / 'tools/ci/latency_bank.py'),
                '--check',
                '--table',
                str(path),
                '--bank',
                str(bank),
            ],
            check=False,
        )
        if result.returncode:
            raise SystemExit(result.returncode)
