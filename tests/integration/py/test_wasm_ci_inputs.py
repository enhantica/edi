"""Changed WebAssembly build inputs reach the required compile and exclusion check."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
INPUTS = {
    'app/src/assistant*',
    '.github/actions/wasm-cache/**',
    '.github/workflows/ci.yml',
    '.github/workflows/pages.yml',
    'tools/ci/wasm*',
}


def workflow():
    return yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']


def declared_inputs(patterns):
    assert set(patterns) == INPUTS, (
        'Every assistant, shared cache, CI/Pages workflow and wasm-tool change owes a web compile'
    )


def test_wasm_change_filter_covers_every_shared_build_input_and_rejects_omissions():
    jobs = workflow()
    filter_step = next(
        step for step in jobs['changes']['steps'] if step.get('uses') == 'dorny/paths-filter@v3'
    )
    patterns = yaml.safe_load(filter_step['with']['filters'])['wasm_build']
    declared_inputs(patterns)
    assert (
        jobs['changes']['outputs']['wasm_build']
        == "${{ steps.filter.outputs.wasm_build == 'true' }}"
    ), 'The real paths-filter boolean, rather than a constant, reaches the downstream compile'
    for pattern in INPUTS:
        with pytest.raises(AssertionError):
            declared_inputs([candidate for candidate in patterns if candidate != pattern])


def dispatch(tmp_path, program, owed):
    binaries = tmp_path / 'commands'
    binaries.mkdir()
    trace = tmp_path / 'commands.jsonl'
    for name in ('pixi', 'bash'):
        command = binaries / name
        command.write_text(
            '#!' + sys.executable + '\nimport json,os,sys\n'
            'from pathlib import Path\n'
            'with Path(os.environ["WASM_COMMAND_TRACE"]).open("a") as stream:\n'
            ' stream.write(json.dumps([Path(sys.argv[0]).name,*sys.argv[1:]])+"\\n")\n',
            encoding='utf-8',
        )
        command.chmod(0o755)
    result = subprocess.run(
        ['/bin/bash', '-e', '-c', program],
        cwd=tmp_path,
        env={
            **os.environ,
            'PATH': str(binaries) + os.pathsep + os.environ['PATH'],
            'EDI_WASM_OWED': owed,
            'WASM_COMMAND_TRACE': str(trace),
        },
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, (
        'The actual host dispatch program must execute its selected route'
    )
    return [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []


@pytest.mark.parametrize('owed', ['true', 'false'])
def test_required_linux_wasm_compile_routes_through_sdk_build_and_exclusion_check(tmp_path, owed):
    step = next(
        step
        for step in workflow()['app']['steps']
        if step.get('name') == 'Compile the app for WebAssembly'
    )
    assert step['env']['EDI_WASM_OWED'] == '${{ needs.changes.outputs.wasm_build }}', (
        'The app compile consumes the actual changed-input decision from the common source job'
    )
    assert step['if'] == "${{ !cancelled() && matrix.platform == 'Linux' }}" and not step.get(
        'continue-on-error'
    ), 'The Linux compile boundary remains mandatory and propagates failures'
    expected = (
        [
            ['pixi', 'run', 'crysta-sdk'],
            ['pixi', 'run', '-e', 'app', 'wasm-toolchain'],
            ['pixi', 'run', '-e', 'app', '--skip-deps', 'wasm-build', 'multithread'],
            ['bash', 'tools/ci/wasm-assistant-check.sh', 'build/wasm/multithread/app'],
        ]
        if owed == 'true'
        else []
    )
    assert dispatch(tmp_path, step['run'], owed) == expected, (
        'Changed wasm inputs acquire the SDK, build the kit and check assistant exclusion in order'
    )


def shared_cache_routes(ci, pages):
    from tests.fixtures.e09_t75_workflow import active  # noqa: PLC0415

    routes = [('app', ci['app']), ('app-wasm', ci['app-wasm']), ('pages', pages['wasm'])]
    for name, job in routes:
        calls = [
            step for step in job['steps'] if step.get('uses') == './.github/actions/wasm-cache'
        ]
        restores = [
            step for step in calls if step.get('with', {}).get('operation', 'restore') == 'restore'
        ]
        saves = [step for step in calls if step.get('with', {}).get('operation') == 'save']
        assert len(calls) == 2 and len(restores) == len(saves) == 1, (
            'Each wasm host restores and saves through the same shared cache owner'
        )
        restore, save = restores[0], saves[0]
        assert restore.get('id') == 'wasm-cache', (
            'The save guard binds the actual shared restore result'
        )
        if name == 'app':
            assert restore.get('if') == (
                "${{ !cancelled() && matrix.platform == 'Linux' "
                "&& needs.changes.outputs.wasm_build == 'true' }}"
            ), 'The PR cache retains its original Linux and actual owed-input guard'
        else:
            assert not restore.get('if'), (
                'Dedicated wasm builders always restore their shared caches'
            )
        builds = [i for i, step in enumerate(job['steps']) if 'wasm-build' in step.get('run', '')]
        assert len(builds) == 1 and job['steps'].index(restore) < builds[0] < job['steps'].index(
            save
        ), 'Each wasm route restores before its actual build and saves after that build attempt'
        for outcome in ['success', 'failure', 'skipped']:
            for cancelled in [False, True]:
                assert active(
                    save,
                    'push',
                    outputs={('wasm-cache', 'outcome'): outcome},
                    states={'build': 'failure'},
                    cancelled=cancelled,
                ) == (outcome == 'success' and not cancelled), (
                    'Only successful restores save after a noncancelled build failure'
                )


def test_every_wasm_route_uses_shared_toolchain_and_compiler_caches_and_rejects_partial_restore():
    import copy  # noqa: PLC0415 - independent source mutation controls

    ci = workflow()
    pages = yaml.safe_load((ROOT / '.github/workflows/pages.yml').read_text())['jobs']
    shared_cache_routes(ci, pages)
    action = yaml.safe_load((ROOT / '.github/actions/wasm-cache/action.yml').read_text())
    caches = [
        step for step in action['runs']['steps'] if step.get('uses') == 'actions/cache/restore@v4'
    ]
    assert {step['with']['path'] for step in caches} == {
        '~/.cache/edi-wasm',
        '~/.cache/edi-ccache',
    }, 'The one shared action restores both the pinned toolchain and validated compiler outputs'
    assert any(
        step.get('uses') == './.github/actions/ccache' for step in action['runs']['steps']
    ), 'The shared action activates the original compiler-wrapper configuration owner'
    for area in ['app', 'app-wasm', 'pages']:
        changed_ci, changed_pages = copy.deepcopy(ci), copy.deepcopy(pages)
        job = changed_pages['wasm'] if area == 'pages' else changed_ci[area]
        step = next(
            step for step in job['steps'] if step.get('uses') == './.github/actions/wasm-cache'
        )
        step['uses'] = 'actions/cache@v4'
        step['with'] = {'path': '~/.cache/edi-wasm', 'key': 'partial-toolchain-only'}
        with pytest.raises(AssertionError):
            shared_cache_routes(changed_ci, changed_pages)


def cache_action_boundary(action):
    steps = action['runs']['steps']
    assert action['inputs']['operation']['default'] == 'restore', (
        'The existing restore caller keeps its declared default'
    )
    assert steps[0].get('env', {}).get('OPERATION') == '${{ inputs.operation }}', (
        'Operation validation receives the actual caller input before any cache side effect'
    )
    assert not steps[0].get('if') and not steps[0].get('continue-on-error'), (
        'Unknown operation refusal cannot be conditional or optional'
    )
    restores = [step for step in steps if step.get('uses') == 'actions/cache/restore@v4']
    saves = [step for step in steps if step.get('uses') == 'actions/cache/save@v4']
    assert len(restores) == len(saves) == 2, (
        'Both toolchain and object caches have explicit restore/save phases'
    )
    for restore in restores:
        paired = [step for step in saves if step['with']['path'] == restore['with']['path']]
        assert len(paired) == 1 and paired[0]['with']['key'] == restore['with']['key'], (
            'Each explicit save names exactly the cache identity its own restore selected'
        )
        assert (
            restore['if'] == "inputs.operation == 'restore'"
            and paired[0]['if'] == "inputs.operation == 'save'"
        ), 'An operation cannot execute the opposite cache phase'
    keys = next(step['run'] for step in steps if step.get('id') == 'keys')
    for dimension in [
        'steps.compiler.outputs.key-prefix',
        'github.run_id',
        'github.run_attempt',
        'github.job',
        'runner.os',
        'runner.arch',
        "hashFiles('tools/ci/wasm-env.sh')",
        "hashFiles('tools/ci/wasm-env.sh', 'tests/fixtures/web_parallel/package-lock.json')",
    ]:
        assert '${{ ' + dimension + ' }}' in keys, (
            'Cache keys retain platform, lock/tool inputs, run/attempt and job ownership'
        )
    return steps[0]['run']


@pytest.mark.parametrize('operation', ['restore', 'save', '', 'RESTORE', 'upload', 'restore save'])
def test_shared_cache_action_refuses_unknown_operations_before_any_cache_side_effect(operation):
    action = yaml.safe_load((ROOT / '.github/actions/wasm-cache/action.yml').read_text())
    guard = cache_action_boundary(action)
    result = subprocess.run(
        ['/bin/bash', '-e', '-c', guard],
        env={**os.environ, 'OPERATION': operation},
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert (result.returncode == 0) == (operation in {'restore', 'save'}), (
        'Only the two declared exact cache operations may reach restore or save'
    )


def test_shared_cache_rejects_missing_save_wrong_identity_and_bypassed_validation():
    import copy  # noqa: PLC0415 - exercise the source boundary rather than cached availability

    action = yaml.safe_load((ROOT / '.github/actions/wasm-cache/action.yml').read_text())
    cache_action_boundary(action)
    for damage in ['missing-save', 'wrong-key', 'wrong-phase', 'optional-guard', 'missing-job']:
        changed = copy.deepcopy(action)
        steps = changed['runs']['steps']
        save = next(step for step in steps if step.get('uses') == 'actions/cache/save@v4')
        if damage == 'missing-save':
            steps.remove(save)
        elif damage == 'wrong-key':
            save['with']['key'] = 'foreign-objects'
        elif damage == 'wrong-phase':
            save['if'] = "inputs.operation == 'restore'"
        elif damage == 'optional-guard':
            steps[0]['continue-on-error'] = True
        else:
            key = next(step for step in steps if step.get('id') == 'keys')
            key['run'] = key['run'].replace('${{ github.job }}', 'shared-job')
        with pytest.raises(AssertionError):
            cache_action_boundary(changed)
