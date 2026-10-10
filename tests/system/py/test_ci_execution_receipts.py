"""Executed identities and provenance are required, even beside a green summary."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from operator import itemgetter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HEAD = '73' * 20


def verify(tmp_path, report, expected=None, platform='osx-arm64'):
    policy = json.loads((ROOT / 'tests/test-groups.json').read_text())
    command = policy.get('execution_report', {}).get('command')
    assert isinstance(command, list), (
        'CI policy: declare execution_report.command as documented in the visible cadence fixture'
    )
    assert command, (
        'CI policy: declare execution_report.command as documented in the visible cadence fixture'
    )
    command = [sys.executable if word in {'python', 'python3'} else word for word in command]
    want = tmp_path / 'expected.json'
    seen = tmp_path / 'report.json'
    want.write_text(
        json.dumps(expected if expected is not None else ['unit::arm64-pin', 'system::scan'])
    )
    seen.write_text(json.dumps(report))
    return subprocess.run(
        [
            *command,
            '--expected',
            str(want),
            '--report',
            str(seen),
            '--head',
            HEAD,
            '--run-id',
            '790',
            '--attempt',
            '2',
            '--platform',
            platform,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=2,
        check=False,
    )


def receipt():
    return {
        'head': HEAD,
        'run_id': 790,
        'attempt': 2,
        'platform': 'osx-arm64',
        'tests': [
            {'nodeid': 'unit::arm64-pin', 'outcome': 'passed'},
            {'nodeid': 'system::scan', 'outcome': 'passed'},
        ],
    }


@pytest.mark.parametrize(
    'damage',
    [
        'omit',
        'duplicate',
        'empty',
        'skip',
        'xfail',
        'fail',
        'unknown',
        'head',
        'platform',
        'attempt',
        'run',
        'malformed',
    ],
)
def test_executed_identity_receipt_requires_full_results_and_current_provenance(tmp_path, damage):
    good = receipt()
    admitted = verify(tmp_path, good)
    assert admitted.returncode == 0, (
        'CI policy: the exact complete successful result receipt must be '
        'accepted before each refusal control'
    )
    bad = copy.deepcopy(good)
    if damage == 'omit':
        bad['tests'].pop()
    elif damage == 'duplicate':
        bad['tests'].append(copy.deepcopy(bad['tests'][0]))
    elif damage == 'empty':
        bad['tests'] = []
    elif damage in {'skip', 'xfail', 'fail'}:
        bad['tests'][0]['outcome'] = {'skip': 'skipped', 'xfail': 'xfailed', 'fail': 'failed'}[
            damage
        ]
    elif damage == 'unknown':
        bad['tests'][0]['nodeid'] = 'same-count::wrong-identity'
    elif damage == 'head':
        bad['head'] = '42' * 20
    elif damage == 'platform':
        bad['platform'] = 'linux-64'
    elif damage == 'attempt':
        bad['attempt'] = 1
    elif damage == 'run':
        bad['run_id'] = 789
    else:
        bad = {'tests': None}
    result = verify(tmp_path, bad)
    assert result.returncode != 0, (
        'CI policy: omitted, unexecuted or foreign-provenance identities '
        'cannot pass on counts or summary alone'
    )


def test_empty_expected_selection_is_rejected_even_with_empty_green_report(tmp_path):
    report = receipt()
    report['tests'] = []
    result = verify(tmp_path, report, [])
    assert result.returncode != 0, (
        'CI policy: neither an empty smoke nor an empty nightly selection '
        'is valid execution evidence'
    )


def test_only_frozen_platform_nonexecution_is_admitted(tmp_path):
    baseline = json.loads((ROOT / 'tests/fixtures/ci_cadence/baseline.json').read_text())
    for node in baseline['platform_nonexecution']['osx-arm64']:
        report = receipt()
        report['tests'] = [{'nodeid': node, 'outcome': 'skipped'}]
        assert verify(tmp_path, report, [node]).returncode == 0, (
            'CI policy: an exact pre-existing macOS skip retains its frozen platform scope'
        )
        report['platform'] = 'linux-64'
        assert verify(tmp_path, report, [node], platform='linux-64').returncode != 0, (
            'CI policy: the old macOS exception cannot waive required Linux execution'
        )


@pytest.mark.parametrize(
    ('group', 'platform'),
    [
        ('quick', 'linux-64'),
        ('full', 'linux-64'),
        ('macos-smoke', 'osx-arm64'),
        ('nightly-full', 'osx-arm64'),
        ('nightly-full', 'linux-64'),
    ],
)
@pytest.mark.parametrize('outcome', ['passed', 'failed', 'skipped', 'xfailed'])
def test_real_group_collector_retains_the_execution_that_the_workflow_uploads(  # noqa: PLR0914
    tmp_path, outcome, group, platform
):
    policy = json.loads((ROOT / 'tests/test-groups.json').read_text())
    runner = policy.get('execution_report', {}).get('run', {}).get('command')
    assert isinstance(runner, list), 'CI policy: collector argv is a declared list'
    assert runner, (
        'CI policy: the visible group authority names its actual execution collector command'
    )
    workspace = tmp_path / 'checkout'
    workspace.mkdir()
    shutil.copytree(
        ROOT / 'tools', workspace / 'tools', ignore=shutil.ignore_patterns('__pycache__')
    )
    shutil.copyfile(ROOT / 'pixi.toml', workspace / 'pixi.toml')
    baseline = json.loads((ROOT / 'tests/fixtures/ci_cadence/baseline.json').read_text())
    tiers = ['unit/py', 'integration/py', 'system/py', 'fitting']
    if baseline['repo'] == 'edi':
        tiers.append('integration/app')
    markers = []
    planned = []
    actions = {
        'passed': 'pass',
        'failed': 'assert False',
        'skipped': 'pytest.skip("planted nonexecution")',
        'xfailed': 'pytest.xfail("planted nonexecution")',
    }
    for index, tier in enumerate(tiers):
        tests = workspace / 'tests' / tier
        tests.mkdir(parents=True, exist_ok=True)
        marker = tmp_path / ('executed-' + str(index))
        markers.append(marker)
        relative = 'tests/' + tier + '/test_planted_' + str(index) + '.py'
        (workspace / relative).write_text(
            'import pytest\nfrom pathlib import Path\n'
            'def test_actual_execution():\n    Path('
            + repr(str(marker))
            + ').write_text("executed")\n    '
            + actions[outcome]
            + '\n'
        )
        planned.append(relative + '::test_actual_execution')
    for declaration in policy['groups'].values():
        declaration.update(tiers=[], nodes=planned)
    workspace.joinpath('tests/test-groups.json').write_text(json.dumps(policy))
    workspace.joinpath('tests/per-pr-runtimes.tsv').write_text(
        ''.join('0.001\t' + n + '\n' for n in planned)
    )
    out = tmp_path / 'uploaded-directory'
    command = [sys.executable if word in {'python', 'python3'} else word for word in runner]
    env = {
        **os.environ,
        'PYTHONPATH': str(workspace),
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
        'GITHUB_SHA': HEAD,
        'GITHUB_RUN_ID': '790',
        'GITHUB_RUN_ATTEMPT': '2',
    }
    run = subprocess.run(
        [*command, '--group', group, '--platform', platform, '--output-dir', str(out)],
        cwd=workspace,
        env=env,
        text=True,
        capture_output=True,
        timeout=3,
        check=False,
    )
    assert all(marker.is_file() for marker in markers), (
        'CI policy: the real collector executes every planted tier rather than '
        'synthesizing or reducing its receipt'
    )
    assert out.joinpath('expected.json').is_file(), 'CI policy: collected group plan is retained'
    assert out.joinpath('results.json').is_file(), (
        'CI policy: collected execution results are retained'
    )
    assert set(json.loads(out.joinpath('expected.json').read_text())) == set(planned), (
        'CI policy: the actual collector plan retains every independently planted tier identity'
    )
    report = json.loads(out.joinpath('results.json').read_text())
    assert sorted(report['tests'], key=itemgetter('nodeid')) == sorted(
        [{'nodeid': node, 'outcome': outcome} for node in planned], key=itemgetter('nodeid')
    ), 'CI policy: every retained identity has the outcome produced by its actual test process'
    assert (report['head'], report['run_id'], report['attempt'], report['platform']) == (
        HEAD,
        790,
        2,
        platform,
    ), 'CI policy: actual execution is bound to the workflow head, run, attempt and platform'
    assert (run.returncode == 0) == (outcome == 'passed'), (
        'CI policy: real failing or unexecuted tests fail the collector path used by the workflow'
    )
    validation = verify(tmp_path, report, planned, platform=platform)
    assert (validation.returncode == 0) == (outcome == 'passed'), (
        'CI policy: the same production validator consumes actual retained collector results'
    )


@pytest.mark.parametrize('outcome', ['passed', 'failed', 'skipped'])
def test_real_native_collector_reports_the_executed_binary_not_only_its_plan(tmp_path, outcome):
    policy = json.loads((ROOT / 'tests/test-groups.json').read_text())
    command = policy.get('execution_report', {}).get('run', {}).get('command')
    assert command, (
        'CI policy: native selection has the same actual production collector as the workflow'
    )
    workspace = tmp_path / 'checkout'
    workspace.mkdir()
    shutil.copytree(
        ROOT / 'tools', workspace / 'tools', ignore=shutil.ignore_patterns('__pycache__')
    )
    nodes = [
        f'tests/{tier}/cpp/test_planted.cpp::planted native {tier} calculation'
        for tier in ('unit', 'integration', 'system')
    ]
    for node in nodes:
        source = workspace / node.split('::')[0]
        source.parent.mkdir(parents=True)
        source.write_text(
            '/* Independent native process transport fixture, no product numerical oracle. */\n'
        )
    for group in policy['groups'].values():
        group.update(tiers=[], nodes=nodes)
    workspace.joinpath('tests/test-groups.json').write_text(json.dumps(policy))
    workspace.joinpath('tests/per-pr-runtimes.tsv').write_text(
        ''.join('0.001\t' + node + '\n' for node in nodes)
    )
    binary = tmp_path / 'native-planted'
    binary.write_text(
        '#!'
        + sys.executable
        + '\n'
        + (ROOT / 'tests/fixtures/ci_cadence/native_executor.py').read_text()
    )
    binary.chmod(0o755)
    marker = tmp_path / 'native-executed'
    env = {
        **os.environ,
        'CI_CADENCE_MARKER': str(marker),
        'CI_CADENCE_OUTCOME': outcome,
        'GITHUB_SHA': HEAD,
        'GITHUB_RUN_ID': '790',
        'GITHUB_RUN_ATTEMPT': '2',
    }
    out = tmp_path / 'retained'
    command = [sys.executable if word in {'python', 'python3'} else word for word in command]
    admitted = subprocess.run(
        [
            *command,
            '--group',
            'nightly-full',
            '--platform',
            'osx-arm64',
            '--output-dir',
            str(out),
            '--native-binary',
            str(binary),
        ],
        cwd=workspace,
        env={**env, 'CI_CADENCE_OUTCOME': 'passed'},
        text=True,
        capture_output=True,
        timeout=2,
        check=False,
    )
    assert admitted.returncode == 0, (
        'CI policy: actual native passing execution admits before damaged outcomes'
    )
    result = subprocess.run(
        [
            *command,
            '--group',
            'nightly-full',
            '--platform',
            'osx-arm64',
            '--output-dir',
            str(out),
            '--native-binary',
            str(binary),
        ],
        cwd=workspace,
        env=env,
        text=True,
        capture_output=True,
        timeout=2,
        check=False,
    )
    assert marker.is_file(), 'CI policy: the collector executes the actual native process boundary'
    assert out.joinpath('results.json').is_file(), (
        'CI policy: native process results reach the retained report'
    )
    assert sorted(json.loads(out.joinpath('expected.json').read_text())) == sorted(nodes), (
        'CI policy: the native plan retains the independently planted exact test identity'
    )
    report = json.loads(out.joinpath('results.json').read_text())
    assert sorted(report['tests'], key=itemgetter('nodeid')) == sorted(
        [{'nodeid': node, 'outcome': outcome} for node in nodes], key=itemgetter('nodeid')
    ), (
        'CI policy: native report outcomes come from the real binary invocation '
        'and its result stream'
    )
    assert (result.returncode == 0) == (outcome == 'passed'), (
        'CI policy: failed or skipped native cases fail the same collector used '
        'by normal workflows'
    )
    assert (verify(tmp_path, report, nodes).returncode == 0) == (outcome == 'passed'), (
        'CI policy: the workflow validator consumes and refuses actual unexecuted native results'
    )
