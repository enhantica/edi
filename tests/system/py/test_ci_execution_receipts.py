"""The shipped suite drivers preserve selection and propagate actual process results.

The superseded JSON execution-report interface is not part of the reshaped task.
These controls execute the shipped Bash drivers; only the expensive suite process
is replaced with an independently observed exit/argument transport.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SHIPPED = json.loads((ROOT / 'tests/fixtures/ci_cadence/shipped-policy.json').read_text())
REPO = SHIPPED['repo']
MODES = ['all', 'nightly'] if REPO == 'crysta' else ['1', '2', '3']
NIGHTLY_GROUP = 'nightly' if REPO == 'crysta' else 'nightly-only'


def execute(tmp_path, mode, skip, result, *, empty=False):
    tools = tmp_path / 'tools/ci'
    tools.mkdir(parents=True)
    tests = tmp_path / 'tests'
    tests.mkdir()
    policy = json.loads((ROOT / 'tests/test-groups.json').read_text())
    if empty:
        policy['groups'][NIGHTLY_GROUP]['paths'] = []
    (tests / 'test-groups.json').write_text(json.dumps(policy))
    name = 'python-tiers.sh' if REPO == 'crysta' else 'system-tests-part.sh'
    driver = tools / name
    shutil.copyfile(ROOT / 'tools/ci' / name, driver)
    binary = tmp_path / 'bin'
    binary.mkdir()
    output = tmp_path / 'calls.json'
    endpoint = binary / ('coverage' if REPO == 'crysta' else 'python')
    endpoint.write_text(
        '#!' + sys.executable + '\n'
        'import json, os, sys\n'
        'if sys.argv[1:2] == ["-c"]:\n'
        ' os.execv(sys.executable, [sys.executable, *sys.argv[1:]])\n'
        'with open(os.environ["CADENCE_ARGUMENTS"], "w") as f:\n'
        ' json.dump(sys.argv[1:],f)\n'
        'sys.exit(int(os.environ["CADENCE_RESULT"]))\n'
    )
    endpoint.chmod(0o755)
    if REPO == 'crysta':
        (binary / 'python').symlink_to(sys.executable)
    selection_env = (
        {'CRYSTA_SKIP_NIGHTLY_GROUP': str(skip).lower()}
        if REPO == 'crysta'
        else {'EDI_RUN_NIGHTLY_ONLY': str(not skip).lower()}
    )
    child = subprocess.run(
        ['/bin/bash', str(driver), mode, *(['3'] if REPO == 'edi' else [])],
        cwd=tmp_path,
        env={
            **os.environ,
            'PATH': str(binary) + ':/usr/bin:/bin',
            **selection_env,
            'CADENCE_ARGUMENTS': str(output),
            'CADENCE_RESULT': str(result),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )
    return child.returncode, json.loads(output.read_text()) if output.exists() else None


@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize('skip', [False, True], ids=['full-cohort', 'pr-deferral'])
@pytest.mark.parametrize('result', [0, 23], ids=['passed', 'failed'])
def test_shipped_driver_executes_exact_selection_and_preserves_exit(tmp_path, mode, skip, result):
    code, args = execute(tmp_path, mode, skip, result)
    assert code == result, 'shipped suite driver propagates the actual executed process result'
    assert args is not None, 'a declared cohort reaches the actual suite process boundary'
    frozen = json.loads(SHIPPED['files']['tests/test-groups.json'])['groups'][NIGHTLY_GROUP][
        'paths'
    ]
    ignored = [arg for arg in args if arg.startswith('--ignore=')]
    expected_ignored = (
        ['--ignore=' + path for path in frozen] if skip and mode != 'nightly' else []
    )
    assert ignored == expected_ignored, (
        'only the independently shipped nightly paths can leave the declared PR cohort'
    )
    selected = [arg for arg in args if arg.startswith('tests/')]
    if REPO == 'crysta':
        expected = (
            frozen
            if mode == 'nightly'
            else ['tests/unit/py', 'tests/integration/py', 'tests/system/py', 'tests/fitting']
        )
        assert args[:4] == ['run', '-m', 'pytest', '-q'], (
            'the Crysta driver executes its pytest process under coverage'
        )
    else:
        expected = ['tests/system']
        assert args[:2] == ['-m', 'pytest'], 'the Edi driver executes pytest'
        assert args[args.index('--splits') + 1] == '3', (
            'the Edi driver preserves the declared total number of system parts'
        )
        assert args[args.index('--group') + 1] == mode, (
            'each Edi system part addresses its own partition, not another part'
        )
    assert selected == expected, 'shipped full and deferred selections retain their exact roots'
    assert not {'--collect-only', '-m', '-k'} & set(args[args.index('pytest') + 1 :]), (
        'a suite executes its whole cohort without marker or keyword pruning'
    )


def test_empty_deferred_cohort_refuses_before_execution(tmp_path):
    code, args = execute(tmp_path, MODES[0], skip=True, result=0, empty=True)
    assert code != 0, 'an empty configured deferred cohort cannot silently pass'
    assert args is None, 'invalid cohort configuration refuses before invoking the suite'


def test_invalid_driver_selection_refuses_before_execution(tmp_path):
    code, args = execute(tmp_path, 'invalid', skip=False, result=0)
    assert code != 0, 'invalid suite mode or partition refuses explicitly'
    assert args is None, 'invalid driver selection cannot execute an invented cohort'
