"""The shared native environment transports the Unicode catalogue unchanged."""

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_declared_utf8_mode_reads_and_emits_the_real_catalogue_in_a_legacy_locale():
    mode = tomllib.loads((ROOT / 'pixi.toml').read_text(encoding='utf-8'))['activation']['env'][
        'PYTHONUTF8'
    ]
    assert mode == '1'
    env = {**os.environ, 'LC_ALL': 'C', 'PYTHONCOERCECLOCALE': '0', 'PYTHONUTF8': mode}
    probe = subprocess.run(
        [sys.executable, '-c', 'import sys; assert sys.flags.utf8_mode == 1'],
        env=env,
        capture_output=True,
        check=False,
    )
    assert probe.returncode == 0, probe.stderr
    run = subprocess.run(
        [sys.executable, str(ROOT / 'tools/checks/case_records.py'), '--json'],
        cwd=ROOT,
        env=env,
        capture_output=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    rows = json.loads(run.stdout.decode('utf-8'))
    registry = json.loads((ROOT / 'app/examples/metadata.json').read_text(encoding='utf-8'))
    assert {row['id'] for row in rows} == set(registry['examples'])
    assert any('₂' in row['title'] for row in rows)
