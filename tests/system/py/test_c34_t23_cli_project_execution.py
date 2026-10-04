""": execute the public runner and corrupt a crysta REGRESSION PIN.

The child-process audit observes real `python -m edi` invocations; it never replaces them.
CI/verify wiring is checked separately against this same entry point.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

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


def test_real_cli_matches_the_independent_crysta_regression_pin(tmp_path):
    result, _, _ = run_registry(tmp_path)
    assert result.returncode == 0, (
        ' real CLI execution must agree with its copied regression pins: '
        + result.stdout
        + result.stderr
    )


@pytest.mark.parametrize('count', [1, 2])
def test_corrupt_expected_value_makes_the_real_cli_gate_red(tmp_path, count):
    result, rows, _ = run_registry(tmp_path, corrupt=True, count=count)
    output = result.stdout + result.stderr
    assert result.returncode != 0, ' corrupted expected values must fail the executing CLI gate'
    assert rows[-1]['id'] in output and 'rwp' in output.lower(), (
        ' refusal must identify the corrupted quantity even in a later registry entry'
    )
