"""Run each wasm engine's fit against the committed native CLI oracle.

This proves numerical backend parity. The browser driver separately clicks Start
fitting in the GUI and requires completion, a results popup and save/reopen.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.e04_t11_wasm.compare import compare

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/e04_t11_wasm'


@pytest.mark.parametrize('mode', ['singlethread', 'multithread'])
def test_wasm_cli_fit_matches_the_native_cli(tmp_path, mode):
    explicit = os.environ.get('EDI_WASM_CLI_' + mode.upper())
    if not explicit:
        pytest.skip('real wasm numerical parity runs in app · WebAssembly via wasm-check')
    cli = Path(explicit)
    assert cli.is_file(), 'each wasm kit requires its compiled CLI numerical acceptance vehicle'
    oracle = json.loads((FIXTURE / 'native.json').read_text())
    project = tmp_path / 'project'
    shutil.copytree(ROOT / oracle['project'], project)
    run = subprocess.run(
        ['node', str(cli.resolve()), 'fit', str(project), '--verbosity', 'full'],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert run.returncode == 0, (
        'wasm fit must complete successfully before numeric parity is claimed: '
        + run.stdout
        + run.stderr
    )
    compare(run.stdout, oracle)


def test_numeric_gate_accepts_native_reference_and_rejects_every_perturbed_operand():
    oracle = json.loads((FIXTURE / 'native.json').read_text())
    record = (FIXTURE / 'native-report.txt').read_text()
    compare(record, oracle)
    fields = dict(line.split('=', 1) for line in record.splitlines())
    for key in [*oracle['parameters'], 'reduced_chi_square']:
        for value in ['nan', 'inf', str(float(fields[key]) * 1.000001)]:
            planted = {**fields, key: value}
            with pytest.raises(ValueError, match='wasm fit'):
                compare('\n'.join(f'{name}={number}' for name, number in planted.items()), oracle)
    for key in ['status', 'converged', *oracle['parameters'], 'reduced_chi_square']:
        planted = {name: number for name, number in fields.items() if name != key}
        with pytest.raises(ValueError, match='wasm fit'):
            compare('\n'.join(f'{name}={number}' for name, number in planted.items()), oracle)
