"""Changed WebAssembly build inputs reach the required compile and exclusion check."""

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.fixtures.e09_t75_workflow import STORE_ACTION, active, require_reporting_step

ROOT = Path(__file__).resolve().parents[3]
INPUTS = {
    'app/**',
    'tests/system/manual/*.mjs',
    'tests/fixtures/e04_t11_wasm/**',
    'tests/fixtures/survey/**',
    'tests/system/py/test_survey_events.py',
    'tests/integration/py/test_preferences_and_survey.py',
    'website/surfaces/docs/assets/survey/**',
    'website/surfaces/docs/about/survey.md',
    'website/surfaces/mkdocs.yml',
    'website/build.py',
    'pixi.toml',
    'pixi.lock',
    'tools/ci/crysta*',
    'tools/ci/compiler_cache.py',
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
    trace_program = tmp_path / 'trace.py'
    trace_program.write_text(
        'import json,os,sys\nfrom pathlib import Path\n'
        'with Path(os.environ["WASM_COMMAND_TRACE"]).open("a") as stream:\n'
        ' stream.write(json.dumps([Path(sys.argv[1]).name,*sys.argv[2:]])+"\\n")\n',
        encoding='utf-8',
    )
    for name in ('pixi', 'bash'):
        command = binaries / name
        command.write_bytes(
            b'#!/bin/sh\nexec "$WASM_TRACE_PYTHON" "$WASM_TRACE_PROGRAM" "$0" "$@"\n'
        )
        command.chmod(0o755)
    real_bash = shutil.which('bash')
    assert real_bash, 'The same Bash entry used by CI must be installed'
    result = subprocess.run(
        [real_bash, '-e', '-c', program],
        cwd=tmp_path,
        env={
            **os.environ,
            'PATH': str(binaries) + os.pathsep + os.environ['PATH'],
            'EDI_WASM_OWED': owed,
            'WASM_COMMAND_TRACE': str(trace),
            'WASM_TRACE_PYTHON': Path(sys.executable).as_posix(),
            'WASM_TRACE_PROGRAM': trace_program.as_posix(),
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
    job = workflow()['app-wasm']
    assert job['runs-on'] == 'ubuntu-24.04', (
        'Required linux wasm compile routes through sdk build and exclusion check.'
    )
    assert set(job['needs']) == {'changes', 'native', 'crysta-sdk'}, (
        'Required linux wasm compile routes through sdk build and exclusion check.'
    )
    resolved = {**job, 'if': job['if'].replace('needs.changes.outputs.wasm_build', repr(owed))}
    selected = active(
        resolved,
        'pull_request',
        states={'changes': 'success', 'native': 'success', 'crysta-sdk': 'success'},
    )
    assert selected == (owed == 'true'), (
        'The dedicated browser job consumes the real changed-input decision on PRs'
    )
    steps = job['steps']
    sdk = next(s for s in steps if s.get('uses') == './.github/actions/crysta-sdk')
    native = next(s for s in steps if s.get('uses') == './.github/actions/edi-native')
    source = next(s for s in steps if s.get('uses') == './.github/actions/crysta-source')
    toolchain = next(s for s in steps if s.get('id') == 'toolchain')
    core = next(s for s in steps if s.get('run') == 'pixi run core-build')
    build = next(s for s in steps if s.get('id') == 'site')
    ordered = [toolchain, sdk, native, source, core, build]
    assert [steps.index(step) for step in ordered] == sorted(
        steps.index(step) for step in ordered
    ), 'Install the public toolchain before fetching source and building the browser kit'
    assert source['with']['sha'] == '${{ env.CRYSTA_SOURCE_SHA }}', (
        'The WebAssembly compiler receives exactly the workflow-resolved source pin'
    )
    assert toolchain.get('shell') == 'bash' and job['defaults']['run']['shell'] == (
        'python3 tools/ci/public_log.py {0}'
    ), 'Only commands before the private fetch run under the plain Bash setup shell'
    assert not any(s.get('if') or s.get('continue-on-error') for s in ordered[:-1]), (
        'Toolchain, SDK, native restore, exact source and core remain required predecessors'
    )
    require_reporting_step(build, 'toolchain')
    build = (ROOT / 'tools/ci/wasm-build.sh').read_text()
    assert 'bash "$ROOT/tools/ci/wasm-assistant-check.sh" "$out/app"' in build, (
        'The common multithread builder retains the mandatory assistant-exclusion check'
    )
    expected = (
        [
            ['pixi', 'run', '-e', 'app', 'wasm-toolchain'],
            ['pixi', 'run', 'core-build'],
            ['pixi', 'run', '-e', 'app', '--skip-deps', 'wasm-build'],
        ]
        if selected
        else []
    )
    program = '\n'.join(step['run'] for step in (toolchain, core, ordered[-1]))
    assert dispatch(tmp_path, program if selected else ':', owed) == expected, (
        'The real selected workflow commands execute the early toolchain and late browser build'
    )


def cache_workflows():
    pages = yaml.safe_load((ROOT / '.github/workflows/pages.yml').read_text())['jobs']
    return workflow(), pages


def save_for(steps, path):
    saves = [
        step
        for step in steps
        if step.get('uses') in {'actions/cache/save@v4', STORE_ACTION}
        and step.get('with', {}).get('path') == path
    ]
    assert len(saves) == 1, f'Exactly one explicit publisher owns the {path} cache'
    return saves[0]


def verify_wasm_cache_route(job):
    steps = job['steps']
    calls = [step for step in steps if step.get('uses') == './.github/actions/wasm-cache']
    assert len(calls) == 1 and not calls[0].get('with'), (
        'Every builder uses the one shared restore action without any operation selector'
    )
    restore = calls[0]
    assert restore.get('id') == 'wasm-cache' and not (
        restore.get('if') or restore.get('continue-on-error')
    ), 'The shared restore always runs and a restore error remains a job failure'
    toolchain = next(step for step in steps if step.get('id') == 'toolchain')
    source = next(step for step in steps if step.get('uses') == './.github/actions/crysta-source')
    build = next(step for step in steps if 'wasm-build' in step.get('run', ''))
    tool_save = save_for(steps, '~/.cache/edi-wasm')
    object_save = save_for(steps, '~/.cache/edi-ccache')
    assert (
        tool_save['uses'] == 'actions/cache/save@v4'
        and tool_save['with']['key'] == '${{ steps.wasm-cache.outputs.toolchain }}'
        and object_save['uses'] == STORE_ACTION
        and object_save['with']['key'] == '${{ steps.wasm-cache.outputs.objects }}'
        and object_save['with'].get('ccache') == 'pixi run --skip-deps python'
        and not any(step.get('continue-on-error') for step in (tool_save, object_save))
    ), 'Toolchain and checked objects are saved under the exact restore action outputs'
    assert (
        steps.index(restore)
        < steps.index(toolchain)
        < steps.index(tool_save)
        < (steps.index(source))
        < steps.index(build)
        < steps.index(object_save)
    ), 'Public tooling is cached before source admission and compiled objects after the build'
    for hit in ('true', 'false'):
        for install in ('success', 'failure'):
            assert active(
                tool_save,
                'push',
                outputs={('wasm-cache', 'toolchain-hit'): hit},
                states={'toolchain': install},
            ) == (hit == 'false' and install == 'success'), (
                'A toolchain save requires a cold restore and a successful install'
            )
    for outcome in ('success', 'failure', 'skipped'):
        for cancelled in (False, True):
            assert active(
                object_save,
                'push',
                outputs={('wasm-cache', 'outcome'): outcome},
                states={'build': 'failure'},
                cancelled=cancelled,
            ) == (outcome == 'success' and not cancelled), (
                'Only successful restores save checked objects after a noncancelled build failure'
            )


def shared_cache_routes(ci, pages):
    assert not any(
        step.get('uses') == './.github/actions/wasm-cache' or 'wasm-build' in step.get('run', '')
        for step in ci['app']['steps']
    ), 'Desktop jobs cannot duplicate the dedicated browser build/cache route'
    verify_wasm_cache_route(ci['app-wasm'])
    verify_wasm_cache_route(pages['wasm'])


def cache_action_boundary(action):
    steps = action['runs']['steps']
    restores = [step for step in steps if step.get('uses') == 'actions/cache/restore@v4']
    assert not action.get('inputs') and len(restores) == 2, (
        'The restore-only composite accepts no mode and restores exactly two cache families'
    )
    assert not any(
        step.get('uses', '').startswith(('actions/cache/save@', 'actions/cache@'))
        or step.get('uses') == STORE_ACTION
        for step in steps
    ), 'Cache publication is available only to the two explicit workflow stages'
    compiler = next(step for step in steps if step.get('id') == 'compiler')
    key_step = next(step for step in steps if step.get('id') == 'keys')
    assert compiler.get('uses') == './.github/actions/ccache' and not (
        compiler.get('if') or compiler.get('continue-on-error')
    ), 'The common action still configures the declared compiler wrapper'
    expected = {'~/.cache/edi-ccache': 'objects', '~/.cache/edi-wasm': 'toolchain'}
    assert {step['with']['path'] for step in restores} == expected.keys(), (
        'No restore may use a partial or foreign cache directory'
    )
    for restore in restores:
        output = expected[restore['with']['path']]
        key = '${{ steps.keys.outputs.' + output + ' }}'
        assert (
            restore['with']['key'] == action['outputs'][output]['value'] == key
            and not restore.get('if')
            and not restore.get('continue-on-error')
            and steps.index(compiler) < steps.index(key_step) < steps.index(restore)
        ), 'Each required restore and its public output use the same computed cache identity'
    toolchain = next(step for step in restores if step.get('id') == 'toolchain')
    assert toolchain['with']['path'] == '~/.cache/edi-wasm' and (
        action['outputs']['toolchain-hit']['value'] == '${{ steps.toolchain.outputs.cache-hit }}'
    ), 'The warmth flag comes from the actual toolchain restore'
    keys = key_step['run']
    for dimension in (
        'steps.compiler.outputs.key-prefix',
        'github.run_id',
        'github.run_attempt',
        'github.job',
        'runner.os',
        'runner.arch',
        "hashFiles('tools/ci/wasm-env.sh')",
        "hashFiles('tools/ci/wasm-env.sh', 'tests/fixtures/web_parallel/package-lock.json')",
    ):
        assert '${{ ' + dimension + ' }}' in keys, (
            'Cache keys retain platform, lock/tool inputs, run/attempt and job ownership'
        )


def test_every_wasm_route_uses_shared_toolchain_and_compiler_caches_and_rejects_partial_restore():
    ci, pages = cache_workflows()
    shared_cache_routes(ci, pages)
    cache_action_boundary(
        yaml.safe_load((ROOT / '.github/actions/wasm-cache/action.yml').read_text())
    )
    for area in ('app-wasm', 'pages'):
        changed_ci, changed_pages = copy.deepcopy(ci), copy.deepcopy(pages)
        job = changed_pages['wasm'] if area == 'pages' else changed_ci[area]
        step = next(
            step for step in job['steps'] if step.get('uses') == './.github/actions/wasm-cache'
        )
        step['uses'] = 'actions/cache@v4'
        step['with'] = {'path': '~/.cache/edi-wasm', 'key': 'partial-toolchain-only'}
        with pytest.raises(AssertionError):
            shared_cache_routes(changed_ci, changed_pages)


@pytest.mark.parametrize('operation', ['restore', 'save', '', 'RESTORE', 'upload', 'restore save'])
def test_shared_cache_route_cannot_select_any_retired_operation(operation):
    ci, pages = cache_workflows()
    shared_cache_routes(ci, pages)
    for job in (ci['app-wasm'], pages['wasm']):
        damaged = copy.deepcopy(job)
        action = next(step for step in damaged['steps'] if step.get('id') == 'wasm-cache')
        action['with'] = {'operation': operation}
        with pytest.raises(AssertionError, match='without any operation'):
            verify_wasm_cache_route(damaged)


def test_shared_cache_rejects_missing_save_wrong_identity_and_bypassed_validation():
    ci, pages = cache_workflows()
    shared_cache_routes(ci, pages)
    for job in (ci['app-wasm'], pages['wasm']):
        for damage in ('missing-save', 'wrong-key', 'wrong-phase', 'optional-restore', 'no-check'):
            damaged = copy.deepcopy(job)
            steps = damaged['steps']
            save = save_for(steps, '~/.cache/edi-ccache')
            if damage == 'missing-save':
                steps.remove(save)
            elif damage == 'wrong-key':
                save['with']['key'] = 'foreign-objects'
            elif damage == 'wrong-phase':
                steps.insert(0, steps.pop(steps.index(save)))
            elif damage == 'optional-restore':
                next(step for step in steps if step.get('id') == 'wasm-cache')[
                    'continue-on-error'
                ] = True
            else:
                save['with'].pop('ccache')
            with pytest.raises(AssertionError):
                verify_wasm_cache_route(damaged)
    action = yaml.safe_load((ROOT / '.github/actions/wasm-cache/action.yml').read_text())
    cache_action_boundary(action)
    key = next(step for step in action['runs']['steps'] if step.get('id') == 'keys')
    key['run'] = key['run'].replace('${{ github.job }}', 'shared-job')
    with pytest.raises(AssertionError, match='run/attempt and job ownership'):
        cache_action_boundary(action)


def test_survey_browser_checks_run_after_the_shared_chrome_toolchain_is_installed():
    steps = workflow()['app-wasm']['steps']
    toolchain = next(step for step in steps if step.get('run') == 'pixi run -e app wasm-toolchain')
    surveys = [step for step in steps if 'test_survey_events.py' in step.get('run', '')]
    assert len(surveys) == 1 and steps.index(toolchain) < steps.index(surveys[0]), (
        'Survey browser checks run after the shared chrome toolchain is installed.'
    )
    require_reporting_step(surveys[0], 'toolchain')
    core = workflow()['core']
    assert not any('test_survey_events.py' in step.get('run', '') for step in core['steps']), (
        'Survey browser checks run after the shared chrome toolchain is installed.'
    )
