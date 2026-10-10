"""Execution-path and concurrency mutations reach the independent gate boundaries."""

# These paths are in intercepted shell argv and are never created by the controls.

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tests.system.py.ci_execution_contract import (
    concurrency_errors,
    execution_errors,
    smoke_errors,
)

ROOT = Path(__file__).resolve().parents[3]


def control(tmp_path):
    tmp_path.joinpath('pixi.toml').write_text("""[tasks]
group-nightly-full = { cmd = ['python', 'tools/ci/run-selection.py', '--group', 'nightly-full',
 '--platform', 'osx-arm64', '--output-dir', '/tmp/ci-selection-probe/result'] }
""")
    policy = {
        'groups': {'nightly-full': {'task': 'group-nightly-full'}},
        'execution_report': {
            'run': {'command': ['python', 'tools/ci/run-selection.py']},
            'command': ['python', 'tools/ci/validate-selection.py'],
        },
    }
    expected = {
        'job': 'nightly full (macOS)',
        'steps': [
            'Execute nightly-full selection',
            'Validate executed selection',
            'Upload executed selection',
        ],
    }
    workflow = {
        'name': 'nightly',
        'on': {
            'pull_request': None,
            'push': {'branches': ['main', 'slot-*']},
            'schedule': [{'cron': '0 3 * * *'}],
            'workflow_dispatch': None,
        },
        'jobs': {
            'full': {
                'name': expected['job'],
                'runs-on': ['self-hosted', 'macOS', 'ARM64'],
                'steps': [
                    {'name': expected['steps'][0], 'run': 'pixi run group-nightly-full'},
                    {
                        'name': expected['steps'][1],
                        'run': (
                            'python tools/ci/validate-selection.py '
                            '--expected /tmp/ci-selection-probe/result/expected.json '
                            '--report /tmp/ci-selection-probe/result/results.json '
                            '--platform osx-arm64'
                        ),
                    },
                    {
                        'name': expected['steps'][2],
                        'uses': 'actions/upload-artifact@v5',
                        'with': {
                            'name': 'ci-selection-osx-arm64',
                            'path': '/tmp/ci-selection-probe/result',
                            'if-no-files-found': 'error',
                        },
                    },
                ],
            }
        },
    }
    return workflow, policy, expected


def execution_control(tmp_path, platform, group):
    workflow, policy, expected = control(tmp_path)
    manifest = tmp_path / 'pixi.toml'
    manifest.write_text(
        manifest.read_text().replace('nightly-full', group).replace('osx-arm64', platform)
    )
    policy['groups'] = {group: {'task': 'group-' + group}}
    job = workflow['jobs']['full']
    job['runs-on'] = (
        'ubuntu-latest' if platform == 'linux-64' else ['self-hosted', 'macOS', 'ARM64']
    )
    for step in job['steps']:
        if 'run' in step:
            step['run'] = step['run'].replace('nightly-full', group).replace('osx-arm64', platform)
        if 'with' in step:
            step['with']['name'] = 'ci-selection-' + platform
    return workflow, policy, expected


@pytest.mark.parametrize(
    'damage',
    [
        'disabled-job',
        'disabled-prerequisite',
        'unselected-environment',
        'disabled-step',
        'wrong-runner',
        'wrong-architecture',
        'wrong-platform',
        'advisory-job',
        'advisory-run',
        'advisory-validation',
        'swallow-run',
        'swallow-validation',
        'disconnected-report',
        'other-job-upload',
        'missing-retention',
        'changed-task',
        'matrix-cancel',
    ],
)
def test_execution_path_auditor_reaches_every_disconnected_or_advisory_boundary(tmp_path, damage):  # noqa: PLR0912
    workflow, policy, expected = control(tmp_path)
    assert not execution_errors(
        tmp_path, workflow, policy, 'schedule', 'osx-arm64', 'nightly-full', expected
    ), (
        'CI policy: an independently planted connected collector, validator and '
        'retention path admits'
    )
    bad = copy.deepcopy(workflow)
    job = bad['jobs']['full']
    steps = job['steps']
    if damage == 'disabled-job':
        job['if'] = False
    elif damage == 'disabled-prerequisite':
        job['needs'] = 'disabled'
        bad['jobs']['disabled'] = {'runs-on': 'ubuntu-latest', 'if': False}
    elif damage == 'unselected-environment':
        path = tmp_path / 'pixi.toml'
        path.write_text(path.read_text().replace('[tasks]', '[feature.unselected.tasks]'))
    elif damage == 'disabled-step':
        steps[0]['if'] = False
    elif damage == 'wrong-runner':
        job['runs-on'] = ['self-hosted', 'Linux', 'X64']
    elif damage == 'wrong-architecture':
        job['runs-on'] = ['self-hosted', 'macOS', 'X64']
    elif damage == 'wrong-platform':
        path = tmp_path / 'pixi.toml'
        path.write_text(path.read_text().replace('osx-arm64', 'linux-64'))
    elif damage == 'advisory-job':
        job['continue-on-error'] = True
    elif damage in {'advisory-run', 'advisory-validation'}:
        steps[0 if damage == 'advisory-run' else 1]['continue-on-error'] = True
    elif damage in {'swallow-run', 'swallow-validation'}:
        steps[0 if damage == 'swallow-run' else 1]['run'] += ' || true'
    elif damage == 'disconnected-report':
        steps[1]['run'] = steps[1]['run'].replace(
            '/result/results.json', '/unrelated/results.json'
        )
    elif damage == 'other-job-upload':
        bad['jobs']['decoration'] = {
            'runs-on': ['self-hosted', 'macOS', 'ARM64'],
            'steps': [steps.pop()],
        }
    elif damage == 'missing-retention':
        steps[2]['with']['if-no-files-found'] = 'warn'
    elif damage == 'changed-task':
        tmp_path.joinpath('pixi.toml').write_text('[tasks]\ngroup-nightly-full = "true"\n')
    else:
        job['strategy'] = {'fail-fast': True}
    assert execution_errors(
        tmp_path, bad, policy, 'schedule', 'osx-arm64', 'nightly-full', expected
    ), 'CI policy: every disconnected, reduced or advisory execution-path mutation reaches refusal'


@pytest.mark.parametrize(
    'damage', ['whitespace-collision', 'job-cancels', 'queued-replacement', 'branch-collision']
)
def test_effective_concurrency_controls_cover_workflows_jobs_slots_and_queued_work(damage):
    first = {
        'name': 'regular',
        'on': ['pull_request', 'push', 'schedule', 'workflow_dispatch'],
        'concurrency': {
            'group': 'regular-${{ github.ref }}-${{ github.run_id }}',
            'cancel-in-progress': False,
        },
        'jobs': {'full': {'runs-on': 'ubuntu-latest'}},
    }
    second = copy.deepcopy(first)
    second['name'] = 'nightly'
    second['concurrency']['group'] = 'nightly-${{github.ref}}-${{github.run_id}}'
    assert not concurrency_errors([first, second]), (
        'CI policy: distinct concrete run identities retain queued and active work '
        'across both slots'
    )
    if damage == 'whitespace-collision':
        second['concurrency']['group'] = 'regular-${{github.ref}}-${{github.run_id}}'
    elif damage == 'job-cancels':
        first['jobs']['full']['concurrency'] = {
            'group': 'job-${{github.ref}}-${{github.run_id}}',
            'cancel-in-progress': '${{ true }}',
        }
    elif damage == 'queued-replacement':
        first['concurrency']['group'] = 'regular-${{github.ref}}'
    else:
        first['concurrency']['group'] = 'regular-${{github.run_id}}'
    assert concurrency_errors([first, second]), (
        'CI policy: whitespace, nested cancellation, queued replacement and slot '
        'collisions are effective refusals'
    )


@pytest.mark.parametrize('category', ['thread', 'scalar', 'simd', 'import', 'cli'])
def test_smoke_auditor_rejects_same_keyword_non_witnesses(category):
    witnesses = json.loads((ROOT / 'tests/fixtures/ci_cadence/policy.json').read_text())[
        'smoke_witnesses'
    ]
    good = [node for cohort in witnesses.values() for node in cohort]
    assert not smoke_errors(good, witnesses), (
        'CI policy: reviewed behavioral witness identities admit'
    )
    decoys = {
        'thread': 'test_thread_policy.py::test_entrypoint_inventory',
        'scalar': 'test_dictionary.py::test_refuses_null_scalar',
        'simd': 'test_build.py::test_simd_flag_string',
        'import': 'test_constraint.py::test_refuses[__import____os__]',
        'cli': 'test_adp.py::test_tensor[monoclinic]',
    }
    bad = [node for node in good if node not in witnesses[category]] + [decoys[category]]
    assert category in smoke_errors(bad, witnesses), (
        'CI policy: a same-keyword declaration, refusal or parameter cannot replace '
        'behavioral execution'
    )


@pytest.mark.parametrize('cleanup', ['rm -rf build', '/bin/rm -rf build', 'command rm -rf build'])
def test_execution_path_probe_cannot_clean_the_product_build(tmp_path, cleanup):
    workflow, policy, expected = control(tmp_path)
    build = tmp_path / 'build'
    build.mkdir()
    sentinel = build / 'native-build-preserved'
    sentinel.write_text('independent preexisting build')
    tmp_path.joinpath('pixi.toml').write_text(
        '[tasks]\ngroup-nightly-full = "' + cleanup + ' && python tools/ci/run-selection.py '
        '--group nightly-full --platform osx-arm64 '
        '--output-dir /tmp/ci-selection-probe/result"\n'
    )
    assert not execution_errors(
        tmp_path, workflow, policy, 'schedule', 'osx-arm64', 'nightly-full', expected
    ), 'CI policy: a connected task remains traceable when it contains inline cleanup'
    assert sentinel.is_file(), (
        'CI policy: dry-run task tracing retains the preexisting build directory'
    )
    assert sentinel.read_text() == 'independent preexisting build', (
        'CI policy: dry-run task tracing cannot delete the product checkout build directory'
    )


@pytest.mark.parametrize('scope', ['workflow', 'job', 'step'])
@pytest.mark.parametrize('damage', ['shell', 'directory', 'environment'])
@pytest.mark.parametrize(
    ('group', 'event', 'platform'),
    [
        ('quick', 'pull_request', 'linux-64'),
        ('full', 'push', 'linux-64'),
        ('macos-smoke', 'pull_request', 'osx-arm64'),
        ('macos-smoke', 'push', 'osx-arm64'),
        ('nightly-full', 'schedule', 'osx-arm64'),
        ('nightly-full', 'workflow_dispatch', 'osx-arm64'),
        ('nightly-full', 'schedule', 'linux-64'),
        ('nightly-full', 'workflow_dispatch', 'linux-64'),
    ],
)
@pytest.mark.parametrize('boundary', ['collector', 'validator'])
def test_run_overrides_cannot_change_the_proved_execution(
    tmp_path, scope, damage, event, platform, group, boundary
):
    workflow, policy, expected = execution_control(tmp_path, platform, group)
    assert not execution_errors(tmp_path, workflow, policy, event, platform, group, expected), (
        'CI policy: the supported default Bash/root-directory execution admits on each event'
    )
    bad = copy.deepcopy(workflow)
    job = bad['jobs']['full']
    owner = (
        bad
        if scope == 'workflow'
        else job
        if scope == 'job'
        else job['steps'][0 if boundary == 'collector' else 1]
    )
    if damage == 'environment':
        owner['env'] = {'BASH_ENV': 'foreign-shell-setup'}
    else:
        settings = (
            owner if scope == 'step' else owner.setdefault('defaults', {}).setdefault('run', {})
        )
        settings['shell' if damage == 'shell' else 'working-directory'] = (
            'bash {0}' if damage == 'shell' else 'different-checkout'
        )
    assert execution_errors(tmp_path, bad, policy, event, platform, group, expected), (
        'CI policy: unsupported execution overrides refuse at every scope and event'
    )


@pytest.mark.parametrize('damage', ['skip-dependencies', 'override-group', 'override-output'])
@pytest.mark.parametrize(
    ('group', 'event', 'platform'),
    [
        ('quick', 'pull_request', 'linux-64'),
        ('full', 'push', 'linux-64'),
        ('macos-smoke', 'pull_request', 'osx-arm64'),
        ('macos-smoke', 'push', 'osx-arm64'),
        ('nightly-full', 'schedule', 'osx-arm64'),
        ('nightly-full', 'workflow_dispatch', 'osx-arm64'),
        ('nightly-full', 'schedule', 'linux-64'),
        ('nightly-full', 'workflow_dispatch', 'linux-64'),
    ],
)
def test_pixi_invocation_cannot_invent_skipped_dependencies_or_hide_arguments(
    tmp_path, damage, event, platform, group
):
    workflow, policy, expected = execution_control(tmp_path, platform, group)
    path = tmp_path / 'pixi.toml'
    original = path.read_text().replace('group-' + group + ' =', 'execute-full =')
    path.write_text(original + 'group-' + group + ' = { depends-on = ["execute-full"] }\n')
    assert not execution_errors(tmp_path, workflow, policy, event, platform, group, expected), (
        'CI policy: a collector reached through an actual task dependency admits'
    )
    step = workflow['jobs']['full']['steps'][0]
    step['run'] = (
        'pixi run --skip-deps group-' + group
        if damage == 'skip-dependencies'
        else step['run']
        + (' --group reduced' if damage == 'override-group' else ' --output-dir different-report')
    )
    assert execution_errors(tmp_path, workflow, policy, event, platform, group, expected), (
        'CI policy: task argument overrides and dependency skipping cannot credit full execution'
    )


@pytest.mark.parametrize('scope', ['workflow', 'job'])
@pytest.mark.parametrize('event', ['pull_request', 'push', 'schedule', 'workflow_dispatch'])
@pytest.mark.parametrize('damage', ['main-cancellation', 'event-queue-replacement'])
def test_concurrency_controls_include_main_and_every_triggered_successor(scope, event, damage):
    workflow = {
        'name': 'independent control',
        'on': [event],
        'concurrency': {
            'group': 'workflow-${{ github.ref }}-${{ github.run_id }}',
            'cancel-in-progress': False,
        },
        'jobs': {
            'full': {
                'runs-on': 'ubuntu-latest',
                'concurrency': {
                    'group': 'job-${{ github.ref }}-${{ github.run_id }}',
                    'cancel-in-progress': False,
                },
            }
        },
    }
    assert not concurrency_errors([workflow]), (
        'CI policy: unique non-cancelling workflow/job run identities admit for each trigger'
    )
    owner = workflow if scope == 'workflow' else workflow['jobs']['full']
    if damage == 'main-cancellation':
        # PRs have merge refs; exercise the real main ref via push/schedule/manual triggers.
        workflow['on'] = [event, 'push']
        owner['concurrency']['cancel-in-progress'] = "${{ github.ref == 'refs/heads/main' }}"
    else:
        owner['concurrency']['group'] = (
            "group-${{ github.ref }}-${{ github.event_name != '"
            + event
            + "' && github.run_id || 0 }}"
        )
    assert concurrency_errors([workflow]), (
        'CI policy: main cancellation and event-specific queue replacement refuse at both scopes'
    )


@pytest.mark.parametrize('scope', ['workflow', 'job'])
def test_concurrency_includes_the_configured_literal_push_branch(scope):
    workflow = {
        'name': 'literal branch control',
        'on': {'push': {'branches': ['repair-other']}},
        'concurrency': {
            'group': 'workflow-${{ github.ref }}-${{ github.run_id }}',
            'cancel-in-progress': False,
        },
        'jobs': {
            'full': {
                'runs-on': 'ubuntu-latest',
                'concurrency': {
                    'group': 'job-${{ github.ref }}-${{ github.run_id }}',
                    'cancel-in-progress': False,
                },
            }
        },
    }
    assert not concurrency_errors([workflow]), (
        'CI policy: configured literal branch admits with independent concurrency identities'
    )
    owner = workflow if scope == 'workflow' else workflow['jobs']['full']
    owner['concurrency']['cancel-in-progress'] = "${{ github.ref == 'refs/heads/repair-other' }}"
    assert concurrency_errors([workflow]), (
        'CI policy: configured literal branch cancellation cannot escape concurrency proof'
    )


@pytest.mark.parametrize('boundary', ['collector', 'validator'])
@pytest.mark.parametrize('damage', ['identity', 'output'])
@pytest.mark.parametrize(
    ('group', 'event', 'platform'),
    [
        ('quick', 'pull_request', 'linux-64'),
        ('full', 'push', 'linux-64'),
        ('macos-smoke', 'pull_request', 'osx-arm64'),
        ('macos-smoke', 'push', 'osx-arm64'),
        ('nightly-full', 'schedule', 'osx-arm64'),
        ('nightly-full', 'workflow_dispatch', 'osx-arm64'),
        ('nightly-full', 'schedule', 'linux-64'),
        ('nightly-full', 'workflow_dispatch', 'linux-64'),
    ],
)
def test_direct_duplicate_options_cannot_hide_execution_overrides(
    tmp_path, boundary, damage, group, event, platform
):
    workflow, policy, expected = execution_control(tmp_path, platform, group)
    assert not execution_errors(tmp_path, workflow, policy, event, platform, group, expected), (
        'CI policy: unique direct collector and validator options admit before argument damage'
    )
    if boundary == 'collector':
        manifest = tmp_path / 'pixi.toml'
        extra = '--group reduced' if damage == 'identity' else '--output-dir other-report'
        manifest.write_text(
            '[tasks]\ngroup-' + group + ' = { cmd = "python tools/ci/run-selection.py '
            '--group '
            + group
            + ' --platform '
            + platform
            + ' --output-dir /tmp/ci-selection-probe/result '
            + extra
            + '" }\n'
        )
    else:
        extra = '--platform wrong-platform' if damage == 'identity' else '--report other-report'
        workflow['jobs']['full']['steps'][1]['run'] += ' ' + extra
    assert execution_errors(tmp_path, workflow, policy, event, platform, group, expected), (
        'CI policy: duplicate direct options cannot conceal group, platform or report overrides'
    )
