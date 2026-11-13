""": execute the public runner and corrupt a crysta REGRESSION PIN.

The child-process audit observes real `python -m edi` invocations; it never replaces them.
CI/verify wiring is checked separately against this same entry point.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / 'tools/checks/cli_projects.py'
AUDITED_RUN = """
import json, pathlib, runpy, sys
log = pathlib.Path(sys.argv[1])
runner = sys.argv[2]
sys.argv = [runner, '--root', sys.argv[3]]
def audit(event, arguments):
    if event == 'subprocess.Popen':
        with log.open('a') as stream:
            stream.write(json.dumps(arguments[1]) + '\\n')
sys.addaudithook(audit)
runpy.run_path(runner, run_name='__main__')
"""


def run_registry(tmp_path, *, corrupt=False, count=1):
    assert RUNNER.is_file(), ' requires an executable CLI-project expected-result checker'
    source = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2'
    assert source.is_dir(), (
        ' real execution probe needs the independently copied executable LBCO seed'
    )
    rows = []
    for index in range(count):
        name = f'pd-neut-cwl_lbco-hrpt_probe-{index}'
        target = tmp_path / 'docs/user/cli' / name
        shutil.copytree(source, target)
        if corrupt and index == count - 1:
            expected = target / 'expected.json'
            values = json.loads(expected.read_text())
            # This is a deliberately impossible drift pin, never a correctness oracle.
            for variant in values['variants'].values():
                variant['quantities']['rwp']['value'] = 1e50
            expected.write_text(json.dumps(values))
        rows.append({'id': name, 'executing': True})
    (tmp_path / 'docs/user/cli/projects.yml').write_text(
        yaml.safe_dump({'schema': 1, 'projects': rows})
    )
    audit = tmp_path / 'processes.jsonl'
    env = {**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}
    result = subprocess.run(
        [sys.executable, '-c', AUDITED_RUN, str(audit), str(RUNNER), str(tmp_path)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert audit.is_file(), (
        ' project execution must launch real CLI child processes: ' + result.stdout + result.stderr
    )
    commands = [json.loads(line) for line in audit.read_text().splitlines()]
    cli_calls = [
        command
        for command in commands
        if isinstance(command, list)
        and any(command[index : index + 2] == ['-m', 'edi'] for index in range(len(command) - 1))
    ]
    assert cli_calls, ' runner must execute python -m edi, not return canned pin values'
    return result, rows, cli_calls


def scan_registry(tmp_path, *, reporting_corruption=False, raw_corruption=False):
    rows = []
    for name in ('pd-neut-cwl_cosio-d20_scan-3f', 'pd-xray-cwl_latp_scan-4f'):
        target = tmp_path / 'docs/user/cli' / name
        shutil.copytree(ROOT / 'docs/user/cli' / name, target)
        rows.append({'id': name, 'executing': True})
        if raw_corruption:
            expected = target / 'expected.json'
            document = json.loads(expected.read_text())
            quantity = next(key for key in document['quantities'] if key.startswith('results['))
            document['quantities'][quantity]['value'] = 1e50
            expected.write_text(json.dumps(document))
    (tmp_path / 'docs/user/cli/projects.yml').write_text(
        yaml.safe_dump({'schema': 1, 'projects': rows})
    )
    program = """
import csv, pathlib, runpy, subprocess, sys
runner, root, corrupt = sys.argv[1:]
original = subprocess.run
def observed(argv, **kwargs):
    result = original(argv, **kwargs)
    if (corrupt == 'yes' and list(argv[:3]) == [sys.executable, '-m', 'edi']
            and argv[3] == 'fit' and result.returncode == 0):
        path = pathlib.Path(argv[4]) / 'analysis/results.csv'
        with path.open(newline='') as handle:
            reader=csv.DictReader(handle); fields=reader.fieldnames; rows=list(reader)
        rows[0]['fit_result.reduced_chi_square'] = '0'
        with path.open('w', newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    return result
subprocess.run=observed
sys.argv=[runner,'--root',root]
runpy.run_path(runner,run_name='__main__')
"""
    return subprocess.run(
        [
            sys.executable,
            '-c',
            program,
            str(RUNNER),
            str(tmp_path),
            'yes' if reporting_corruption else 'no',
        ],
        cwd=ROOT,
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def reporting_controls(tmp_path):
    spec = importlib.util.spec_from_file_location('cli_reporting_checker', RUNNER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    # Independently authored edge: the raw value passes its original scientific bound,
    # whereas its correctly reported projection lies outside it. No bound is widened.
    raw = {
        'phase.cell.length_c': 20.83147355523315,
        'phase.cell.length_c.uncertainty': 0.0008751,
        'fit_result.reduced_chi_square': 142228766.76932976,
    }
    pin = {'value': 20.831573, 'tol_abs': 0.0001, 'tol_rel': None}
    assert checker._deviations('c', pin, raw['phase.cell.length_c']) == []
    assert checker._reported('phase.cell.length_c', raw) == Decimal('20.83147')
    assert checker._reported('phase.cell.length_c.uncertainty', raw) == Decimal('0.00088')
    assert checker._reported('fit_result.reduced_chi_square', raw) == Decimal(140000000)
    assert checker._deviations('c', pin, 20.83147), (
        'Reported rounding must never replace the unrounded scientific assertion'
    )
    assert checker._deviations('c', pin, 20.83146), 'A true raw breach remains a failure'
    for column in ('phase.cell.length_c', 'fit_result.reduced_chi_square'):
        for value in (float('nan'), float('inf'), -float('inf')):
            with pytest.raises(ValueError, match='not finite'):
                checker._reported(column, {**raw, column: value})
    for su in (-1, float('nan'), float('inf')):
        with pytest.raises(ValueError, match='uncertainty is invalid'):
            checker._reported(
                'phase.cell.length_c', {**raw, 'phase.cell.length_c.uncertainty': su}
            )
    with pytest.raises(KeyError):
        checker._reported('missing', raw)

    # Exercise every boundary independently of solver output and of the expected.json pins.
    rows = [dict(file_path='input/a.dat', **{'phase.cell.length_c': '20.83147'})]
    checker._check_prefix_rows(rows, [dict(rows[0], file_path='other/a.dat')])
    for changed in (
        [],
        [dict(rows[0], file_path='other/b.dat')],
        [dict(file_path='input/a.dat', **{'phase.cell.length_c': '20.83146'})],
    ):
        with pytest.raises(ValueError, match='raw scan prefix'):
            checker._check_prefix_rows(rows, changed)
    project = SimpleNamespace(structures=[SimpleNamespace(name='phase')], experiments=[])
    outcome = SimpleNamespace(
        reduced_chi_square=142228766.76932976,
        iterations=4,
        success=True,
        values={'structures[phase].cell.length_c': 20.83147355523315},
        uncertainty={'structures[phase].cell.length_c': 0.0008751},
    )
    assert checker._raw_outcome_columns(project, outcome) == {
        **raw,
        'fit_result.iterations': 4,
        'fit_result.success': 1.0,
    }
    outcome.values = {'unidentified.cell.length_c': 20.83147355523315}
    with pytest.raises(ValueError, match='not uniquely labelled'):
        checker._raw_outcome_columns(project, outcome)
    outcome.values = {
        'structure.cell.length_c': 20.83147355523315,
        'structures[phase].cell.length_c': 20.83147355523315,
    }
    with pytest.raises(ValueError, match='duplicate raw result'):
        checker._raw_outcome_columns(project, outcome)
    directory = tmp_path / 'analysis'
    directory.mkdir(parents=True)
    table = directory / 'results.csv'
    name = 'results[a.dat].phase.cell.length_c'
    for written, valid in [('20.83147', True), ('20.83146', False), ('NaN', False)]:
        with table.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['file_path', 'phase.cell.length_c'])
            writer.writeheader()
            writer.writerow({'file_path': 'input/a.dat', 'phase.cell.length_c': written})
        measured, findings = checker._measurement(name, {}, tmp_path, {'a.dat': raw})
        assert measured == raw['phase.cell.length_c'], (
            'The raw scientific quantity never comes from the written CSV'
        )
        assert bool(findings) is not valid, 'Any wrong reporting projection must be refused'
    with pytest.raises(KeyError):
        checker._measurement(name, {}, tmp_path, {})


def test_real_cli_matches_the_independent_crysta_regression_pin(tmp_path):
    result, _, _ = run_registry(tmp_path)
    assert result.returncode == 0, (
        ' real CLI execution must agree with its copied regression pins: '
        + result.stdout
        + result.stderr
    )
    reporting_controls(tmp_path / 'projection')
    scan = scan_registry(tmp_path / 'scans')
    assert scan.returncode == 0, (
        'The real CLI scan gate preserves raw pins and exact reporting projections: '
        + scan.stdout
        + scan.stderr
    )


@pytest.mark.parametrize('count', [1, 2])
def test_corrupt_expected_value_makes_the_real_cli_gate_red(tmp_path, count):
    result, rows, _ = run_registry(tmp_path, corrupt=True, count=count)
    output = result.stdout + result.stderr
    assert result.returncode != 0, ' corrupted expected values must fail the executing CLI gate'
    assert rows[-1]['id'] in output and 'rwp' in output.lower(), (
        ' refusal must identify the corrupted quantity even in a later registry entry'
    )

    scan = scan_registry(
        tmp_path / 'scans', reporting_corruption=count == 1, raw_corruption=count == 2
    )
    assert scan.returncode != 0, 'Both raw numerical and reported CSV corruptions fail closed'
    diagnostic = scan.stdout + scan.stderr
    assert 'fit_result.reduced_chi_square' in diagnostic, (
        'A scan refusal identifies its corrupted raw or reported quantity'
    )
