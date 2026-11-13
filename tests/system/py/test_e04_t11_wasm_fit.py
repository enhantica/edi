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

from tests.fixtures.e04_t11_wasm import iteration_domains, solver_vehicles, written
from tests.fixtures.e04_t11_wasm.cli_domains import compare_current, vehicle
from tests.fixtures.e04_t11_wasm.compare import compare

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/e04_t11_wasm'


@pytest.mark.parametrize('mode', ['multithread'])
def test_wasm_cli_fit_matches_the_native_cli(tmp_path, mode):
    explicit = os.environ.get('EDI_WASM_CLI_' + mode.upper())
    if not explicit:
        pytest.skip('real wasm numerical parity runs in app · WebAssembly via wasm-check')
    cli = Path(explicit)
    assert cli.is_file(), 'each wasm kit requires its compiled CLI numerical acceptance vehicle'
    project = tmp_path / 'project'
    oracle = vehicle(project)
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
    compare_current(run.stdout, oracle)


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


def historical_wasm(cli, fixture, old, source, project, evidence):
    """Exercise every frozen vector operand under the source-backed old conditions."""
    solver_vehicles.vehicle(source, project)
    before = written.files(project)
    run = subprocess.run(
        ['node', str(Path(cli).resolve()), 'fit', str(project), '--dry', '--verbosity', 'full'],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    evidence.with_suffix('.txt').write_text(run.stdout)
    evidence.with_suffix('.stderr').write_text(run.stderr)
    assert run.returncode == 0, 'Historical WASM fit must complete: ' + run.stdout + run.stderr
    assert written.files(project) == before, (
        'Historical WASM fit must preserve its declared input bytes'
    )
    solver_vehicles.qualify_historical_report(fixture, old, run.stdout)


@pytest.mark.parametrize('case', ['lbco', 'ncaf'])
def test_catalogue_wasm_continuation_matches_current_native_work(tmp_path, case):
    cli_path = os.environ.get('EDI_WASM_CLI_MULTITHREAD')
    reference = os.environ.get('EDI_WASM_WRITTEN_REFERENCE')
    if not cli_path:
        pytest.skip('real catalogue backend parity belongs to app WebAssembly qualification')
    assert reference, 'Catalogue WASM count parity requires the explicitly captured native work'
    fixture = written.admit(ROOT, case, Path(reference) / case)
    _, old, source, _, _ = written.inputs(ROOT, case)
    historical_wasm(
        cli_path,
        fixture,
        old,
        source,
        tmp_path / 'historical',
        Path(reference) / (case + '-historical-wasm-machine'),
    )
    project = tmp_path / 'project'
    shutil.copytree(source, project)
    before = written.files(project)
    run = subprocess.run(
        [
            'node',
            str(Path(cli_path).resolve()),
            'fit',
            str(project),
            '--dry',
            '--verbosity',
            'full',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    (Path(reference) / (case + '-wasm-machine.txt')).write_text(run.stdout)
    (Path(reference) / (case + '-wasm-stderr.txt')).write_text(run.stderr)
    assert run.returncode == 0, (
        'The real catalogue WASM fit must complete before any current work parity claim: '
        + run.stdout
        + run.stderr
    )
    assert written.files(project) == before, 'Dry catalogue parity retains every input byte'
    iteration_domains.compare_runtime(
        run.stdout, (Path(reference) / case / 'machine.txt').read_text(), fixture
    )
