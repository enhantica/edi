"""Cadence separation and authenticated readonly preparation escape controls."""

import copy
import fnmatch
import json
import os
import runpy
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from tests.fixtures.joint_series import prepare_seeded

ROOT = Path(__file__).resolve().parents[3]
SLOW = 'tests/system/slow/seeded_series.py'
GROUP = 'nightly-only'


def require_isolation(policy, patterns):
    group = policy['groups'][GROUP]
    assert group['slow_paths'] == [SLOW], (
        'Only the owner-authorized slow witness belongs to slow cadence'
    )
    assert SLOW in group['paths'], 'The slow witness must retain its declared cadence authority'
    assert not any(fnmatch.fnmatch(Path(SLOW).name, p) for p in patterns), (
        'The slow filename must stay outside ordinary PR collection'
    )


def test_slow_shape_and_pr_discovery_are_separate(monkeypatch, tmp_path):
    policy = json.loads((ROOT / 'tests/test-groups.json').read_text())
    options = tomllib.loads((ROOT / 'pyproject.toml').read_text())['tool']['pytest']['ini_options']
    patterns = options.get('python_files', ['test_*.py', '*_test.py'])
    if isinstance(patterns, str):
        patterns = patterns.split()
    require_isolation(policy, patterns)
    bad = copy.deepcopy(policy)
    bad['groups'][GROUP]['slow_paths'] = ['tests/system/py/test_joint_series_seeded_nightly.py']
    with pytest.raises(AssertionError):
        require_isolation(bad, patterns)
    with pytest.raises(AssertionError):
        require_isolation(policy, ['*.py'])
    module = runpy.run_path(str(ROOT / SLOW))
    calls = []
    gate = module['test_slow_fullprof_seeded_points']
    monkeypatch.setitem(
        gate.__globals__, 'check_seeded_fit', lambda *a, **kw: calls.append((a, kw))
    )
    for descent in ('fast_descent', 'ladder'):
        gate(tmp_path, descent)
    assert calls == [((tmp_path, 100, d), {'small': False}) for d in ('fast_descent', 'ladder')], (
        'Both slow descents must keep the complete one-hundred-point five-bank fixture'
    )
    assert prepare_seeded.POINTS == 1, (
        'PR preparation must retain one joint point with two independently routed banks'
    )


@pytest.mark.parametrize(
    'defect', ['none', 'duplicate', 'undeclared', 'discoverable', 'wrong_root']
)
def test_actual_slow_driver_refuses_pr_leaks(tmp_path, defect):
    work = tmp_path / 'repo'
    (work / 'tools/ci').mkdir(parents=True)
    shutil.copyfile(
        ROOT / 'tools/ci/slow-seeded-series.sh', work / 'tools/ci/slow-seeded-series.sh'
    )
    shutil.copyfile(ROOT / 'pyproject.toml', work / 'pyproject.toml')
    policy = json.loads((ROOT / 'tests/test-groups.json').read_text())
    group = policy['groups'][GROUP]
    selected = SLOW
    if defect == 'duplicate':
        group['slow_paths'].append(SLOW)
    elif defect == 'undeclared':
        group['paths'].remove(SLOW)
    elif defect in {'discoverable', 'wrong_root'}:
        selected = 'tests/system/' + (
            'slow/test_leak.py' if defect == 'discoverable' else 'py/leak.py'
        )
        group['slow_paths'] = [selected]
        group['paths'].append(selected)
    path = work / selected
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('')
    (work / 'tests/test-groups.json').write_text(json.dumps(policy))
    executable = tmp_path / 'bin'
    executable.mkdir()
    recorder = tmp_path / 'boundary.json'
    fake = executable / 'python'
    fake.write_text(
        '#!' + sys.executable + '\nimport os,sys,json\n'
        'if sys.argv[1] != "-m": os.execv(sys.executable,[sys.executable,*sys.argv[1:]])\n'
        'open(os.environ["BOUNDARY"],"w").write(json.dumps(sys.argv[1:]))\nsys.exit(23)\n'
    )
    fake.chmod(0o755)
    run = subprocess.run(
        ['/bin/bash', str(work / 'tools/ci/slow-seeded-series.sh'), GROUP],
        env={
            **os.environ,
            'PATH': str(executable) + os.pathsep + os.environ['PATH'],
            'BOUNDARY': str(recorder),
        },
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    if defect == 'none':
        assert run.returncode == 23, 'The real slow driver must propagate pytest failure'
        assert json.loads(recorder.read_text()) == ['-m', 'pytest', SLOW, '-q'], (
            'The slow driver must execute exactly its declared scientific file without deselection'
        )
    else:
        assert run.returncode != 0, (
            'A leaking or undeclared slow entry must refuse before reaching pytest'
        )
        assert not recorder.exists(), 'Invalid slow entries must never reach pytest'


@pytest.mark.parametrize('defect', ['missing', 'spec', 'input', 'profile'])
def test_prepared_seeded_input_cannot_repair_or_trust_changed_bytes(tmp_path, defect):
    source = tmp_path / 'input'
    source.mkdir()
    data = source / 'observation.xy'
    data.write_text('1 2 3\n')
    profile = tmp_path / 'profiles.npz'
    profile.write_bytes(b'fixed basis')
    spec = {'authored': 'engine-and-reference-identity'}
    receipt = tmp_path / 'prepared.json'
    receipt.write_text(
        json.dumps({
            'spec': spec,
            'input': prepare_seeded.tree(source),
            'profiles': prepare_seeded.digest(profile),
        })
    )
    prepare_seeded.validate(tmp_path, spec)
    if defect == 'missing':
        receipt.unlink()
    elif defect == 'spec':
        spec = {'authored': 'another-engine'}
    elif defect == 'input':
        data.write_text('1 999 3\n')
    else:
        profile.write_bytes(b'changed basis')
    with pytest.raises(AssertionError):
        prepare_seeded.validate(tmp_path, spec)


def test_slow_ci_steps_are_schedule_or_manual_only():
    jobs = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']
    actual = {}
    for name, job in jobs.items():
        for step in job.get('steps', []):
            if 'slow-seeded-series' in step.get('run', ''):
                actual[name] = (step['run'], step.get('if'))
    expected = {
        'system': (
            'pixi run slow-seeded-series',
            (
                '${{ !cancelled() && matrix.part == 1 && ('
                "github.event_name == 'schedule' || ("
                "github.event_name == 'workflow_dispatch' && inputs.core_only != true)) }}"
            ),
        )
    }
    assert actual == expected, (
        'Slow seeded fits must execute only in the declared schedule/manual CI steps'
    )
    bad = copy.deepcopy(actual)
    key = next(iter(bad))
    bad[key] = (bad[key][0], '${{ true }}')
    assert bad != expected, (
        'An unconditional slow step must fail the independently authored cadence expectation'
    )


def test_ordinary_pytest_collection_cannot_find_slow_fits():
    run = subprocess.run(
        [
            sys.executable,
            '-m',
            'pytest',
            'tests/system/slow',
            '--collect-only',
            '-q',
            '-o',
            'addopts=',
            '-p',
            'no:cacheprovider',
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=4,
        check=False,
    )
    assert run.returncode == 5, 'Actual default discovery must exclude every slow scientific fit'
    assert 'no tests collected' in run.stdout, (
        'Ordinary collection must prove the slow set is empty'
    )


def test_pr_task_graph_requires_shared_seed_preparation():
    tasks = tomllib.loads((ROOT / 'pixi.toml').read_text())['tasks']

    def reaches(name, seen=None):
        seen = set() if seen is None else seen
        if name == 'joint-series-seeded-prepare':
            return True
        if name in seen or name not in tasks:
            return False
        seen.add(name)
        return any(
            reaches(d if isinstance(d, str) else d['task'], seen)
            for d in tasks[name].get('depends-on', [])
        )

    for name in ['test', 'system-tests-part', 'per-pr-measure']:
        assert reaches(name), (
            'Every PR fit entry point must declare shared bounded seed preparation'
        )
    original = tasks['joint-series-prepare']['depends-on']
    tasks['joint-series-prepare']['depends-on'] = [
        d for d in original if d != 'joint-series-seeded-prepare'
    ]
    assert not reaches('joint-series-prepare'), (
        'Removing the preparation dependency must fail the independent task-graph requirement'
    )
