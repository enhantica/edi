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
    routes = [('app', ci['app']), ('app-wasm', ci['app-wasm']), ('pages', pages['wasm'])]
    for name, job in routes:
        calls = [
            step for step in job['steps'] if step.get('uses') == './.github/actions/wasm-cache'
        ]
        assert len(calls) == 1, (
            'Every PR, dedicated CI and Pages wasm build inherits the complete shared cache action'
        )
        if name == 'app':
            assert calls[0].get('if') == (
                "${{ !cancelled() && matrix.platform == 'Linux' "
                "&& needs.changes.outputs.wasm_build == 'true' }}"
            ), 'The PR cache retains its original Linux and actual owed-input guard'
        else:
            assert not calls[0].get('if'), (
                'Dedicated wasm builders always restore their shared caches'
            )


def test_every_wasm_route_uses_shared_toolchain_and_compiler_caches_and_rejects_partial_restore():
    import copy  # noqa: PLC0415 - independent source mutation controls

    ci = workflow()
    pages = yaml.safe_load((ROOT / '.github/workflows/pages.yml').read_text())['jobs']
    shared_cache_routes(ci, pages)
    action = yaml.safe_load((ROOT / '.github/actions/wasm-cache/action.yml').read_text())
    caches = [step for step in action['runs']['steps'] if step.get('uses') == 'actions/cache@v4']
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
