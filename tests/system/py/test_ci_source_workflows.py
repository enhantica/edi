# SPDX-License-Identifier: BSD-3-Clause
"""Exercise checked cache saves and publication policy through the committed workflow graph."""

import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.fixtures.e09_t75_workflow import active
from tests.integration.py import test_ci_source_runtime as runtime

ROOT = Path(__file__).resolve().parents[3]
ci_runner = runtime.runner


def compile_warning(scratch, cache, runner, name, *, reveal):
    compiler = shutil.which('cc')
    ccache = shutil.which('ccache')
    assert compiler and ccache, 'The cache test requires cc and ccache on the runner'
    source = scratch / f'{name}.c'
    source.write_bytes(
        b'int f(void) {\n'
        + (runtime.SOURCE_LINE if reveal else b'int publicValue = 31;')
        + b'\nreturn 0;\n}\n'
    )
    disable_caret = (
        '-fno-caret-diagnostics' if sys.platform == 'darwin' else '-fno-diagnostics-show-caret'
    )
    flags = [] if reveal else [disable_caret]
    before = set(cache.rglob('*'))
    result = subprocess.run(
        [
            ccache,
            compiler,
            '-Wall',
            '-fdiagnostics-color=never',
            *flags,
            '-c',
            str(source),
            '-o',
            str(source.with_suffix('.o')),
        ],
        env={
            **runner,
            'CCACHE_DIR': str(cache),
            'CCACHE_CONFIGPATH': os.devnull,
            'CCACHE_NODIRECT': 'true',
            'LC_ALL': 'C',
        },
        cwd=scratch,
        capture_output=True,
        timeout=10,
        check=True,
    )
    assert b'unused variable' in result.stderr, 'An actual compiler warning is stored by ccache'
    assert (runtime.SOURCE_LINE in result.stderr) is reveal, (
        'Real compiler stderr contains the planted source line only in the unsafe control'
    )
    results = []
    for path in set(cache.rglob('*')) - before:
        if not path.is_file():
            continue
        inspect = subprocess.run(
            [ccache, '--inspect', str(path)],
            capture_output=True,
            timeout=5,
            check=False,
        )
        if inspect.returncode == 0 and b'(result)' in inspect.stdout:
            results.append(path)
    assert len(results) == 1, 'A successful compile wrote one actual ccache result'
    return results[0]


CACHE_ROUTES = [
    ('crysta-sdk.yml', 'build', 'crysta-sdk', '${{ runner.temp }}/crysta-ccache'),
    ('ci.yml', 'native', 'core', '~/.cache/edi-ccache'),
    ('ci.yml', 'app', 'app', '~/.cache/edi-ccache'),
    ('ci.yml', 'app-macos', 'app', '~/.cache/edi-ccache'),
    ('ci.yml', 'app-windows', 'app-windows', '${{ runner.temp }}/edi-ccache'),
    ('installers.yml', 'installers', 'installer', '${{ runner.temp }}/edi-ccache'),
    ('ci.yml', 'app-wasm', 'wasm', '~/.cache/edi-ccache'),
    ('pages.yml', 'wasm', 'wasm', '~/.cache/edi-ccache'),
]
ROUTE_IDS = [
    'sdk',
    'native',
    'app-linux',
    'app-macos',
    'app-windows',
    'installer',
    'ci-wasm',
    'pages-wasm',
]
WORKFLOWS = Path('.github/workflows')
ACTIONS = Path('.github/actions')


def yaml_file(root, path):
    return yaml.safe_load((root / path).read_text(encoding='utf-8'))


def action_steps(root, name):
    return yaml_file(root, ACTIONS / name / 'action.yml')['runs']['steps']


def uses(step, action):
    return step.get('uses', '').split('@', 1)[0] == action


def workflow_cache_restore(steps, family, path):
    candidates = [
        step
        for step in steps
        if uses(step, 'actions/cache/restore')
        and step['with']['path'] == path
        and f'ccache2-{family}-' in step['with']['restore-keys']
        and (family == 'app-windows' or 'ccache2-app-windows-' not in step['with']['restore-keys'])
    ]
    assert len(candidates) == 1, (
        'The actual workflow has one restore for this compiler cache family'
    )
    return candidates[0]['with']


def render_store_value(value, inputs, workspace):
    for key, content in inputs.items():
        value = value.replace('${{ inputs.' + key + ' }}', content)
    return value.replace('${{ github.workspace }}', str(workspace))


def run_compiler_cache_save(tmp_path, runner, inputs, store):
    resolved = {**inputs, 'artifact': ''}
    script = tmp_path / 'compiler-cache-step.sh'
    bindings = {f'inputs.{key}': value for key, value in resolved.items()}
    save = next(step for step in store if uses(step, 'actions/cache/save'))
    checks = [
        step
        for step in store[: store.index(save)]
        if 'run' in step and active(step, 'pull_request', bindings=bindings)
    ]
    assert len(checks) == 1 and 'continue-on-error' not in checks[0], (
        'Exactly one required composite check runs before the real cache save'
    )
    check = checks[0]
    args = {
        key: render_store_value(value, resolved, ROOT)
        for key, value in check.get('env', {}).items()
    }
    script.write_text(render_store_value(check['run'], resolved, ROOT), encoding='utf-8')
    shell = shlex.split(check['shell'].format(shlex.quote(str(script))))
    result = subprocess.run(
        shell, cwd=ROOT, env={**runner, **args}, capture_output=True, check=False, timeout=15
    )
    handoff = (
        {key: render_store_value(value, resolved, ROOT) for key, value in save['with'].items()}
        if active(
            save,
            'pull_request',
            bindings=bindings,
            states={'compiler-check': 'failure' if result.returncode else 'success'},
        )
        else None
    )
    return result, handoff


def compiler_runner(tmp_path, runner):
    # Preserve the workflow's selected Python environment at the pixi boundary without provisioning
    # remote runner environments. The actual store shell, checker and compiler cache still execute.
    launcher = tmp_path / 'pixi'
    launcher.write_text(
        '#!/bin/sh\n[ "$1" = run ] || exit 89\n'
        'while [ "$1" != python ]; do [ "$#" -gt 0 ] || exit 89; shift; done\n'
        'shift\nexec "$REPLAY_PYTHON" "$@"\n',
        encoding='utf-8',
    )
    launcher.chmod(0o755)
    return {
        **runner,
        'PATH': str(tmp_path) + os.pathsep + runner['PATH'],
        'REPLAY_PYTHON': sys.executable,
    }


def require_planted_diagnostic(tmp_path, planted):
    extracted = tmp_path / 'cache-result'
    extracted.mkdir()
    subprocess.run(
        [shutil.which('ccache'), '--extract-result', str(planted)],
        cwd=extracted,
        capture_output=True,
        timeout=5,
        check=True,
    )
    assert any(
        runtime.SOURCE_LINE in re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', entry.read_bytes())
        for entry in extracted.glob('*.stderr')
    ), 'The saved ccache result really contains the sensitive compiler diagnostic'


def compiler_save_inputs(workflow, job, family, path):
    steps = yaml_file(ROOT, WORKFLOWS / workflow)['jobs'][job]['steps']
    stores = [
        step
        for step in steps
        if uses(step, './.github/actions/store')
        and step['with'].get('ccache')
        and step['with']['path'] == path
    ]
    assert len(stores) == 1, 'The actual workflow selects a single checked save for this cache'
    store = stores[0]
    runner_os = {'app-windows': 'Windows', 'app-macos': 'macOS'}.get(job, 'Linux')
    assert active(
        store,
        'pull_request',
        bindings={'runner.os': runner_os},
        outputs={
            ('ccache', 'outcome'): 'success',
            ('compiler-inputs', 'outcome'): 'success',
            ('compiler-cache', 'outcome'): 'success',
            ('cache', 'cache-hit'): 'false',
            ('inputs', 'run'): 'true',
            ('wasm-cache', 'outcome'): 'success',
        },
    ), 'The actual workflow reaches the checked save on its declared build route'
    restore = workflow_cache_restore(
        action_steps(ROOT, 'wasm-cache') if family == 'wasm' else steps, family, path
    )
    expected_key = (
        '${{ steps.wasm-cache.outputs.objects }}' if family == 'wasm' else restore['key']
    )
    assert store['with']['key'] == expected_key, (
        'The checked save publishes the compiler cache under the same identity as its restore'
    )

    return store['with']


@pytest.mark.skipif(os.name != 'posix', reason='The cache save replay uses a POSIX C compiler')
@pytest.mark.parametrize(('workflow', 'job', 'family', 'path'), CACHE_ROUTES, ids=ROUTE_IDS)
def test_full_cache_save_omits_source_diagnostics_in_new_and_untouched_restored_entries(
    tmp_path, ci_runner, workflow, job, family, path
):
    inputs = compiler_save_inputs(workflow, job, family, path)
    env = compiler_runner(tmp_path, ci_runner)
    cold = tmp_path / 'cold-cache'
    warm = tmp_path / 'warm-cache'
    planted = compile_warning(tmp_path, cold, ci_runner, 'private', reveal=True)
    shutil.copytree(cold, warm)
    require_planted_diagnostic(tmp_path, planted)
    composite = action_steps(ROOT, 'store')
    for cache in (cold, warm):
        unsafe = cache / planted.relative_to(cold)
        before = (unsafe.read_bytes(), unsafe.stat().st_mtime_ns)
        allowed = compile_warning(tmp_path, cache, ci_runner, 'public', reveal=False)
        assert (unsafe.read_bytes(), unsafe.stat().st_mtime_ns) == before, (
            'Compiling a public object leaves the planted cache result untouched'
        )
        save_inputs = {**inputs, 'path': str(cache)}
        failed, handoff = run_compiler_cache_save(
            tmp_path,
            {**env, 'CRYSTA_SOURCE_BLOB_LIST': str(tmp_path / 'absent')},
            save_inputs,
            composite,
        )
        assert failed.returncode != 0 and handoff is None and unsafe.is_file(), (
            'The live save path stops before handoff if the compiler cache cannot be judged'
        )
        checked, handoff = run_compiler_cache_save(tmp_path, env, save_inputs, composite)
        assert checked.returncode == 0 and handoff == {'key': inputs['key'], 'path': str(cache)}, (
            'The live cache action hands off the exact directory and key after checking'
        )
        assert not unsafe.exists() and allowed.is_file(), (
            'The directory handed to the actual save drops unsafe and retains harmless results'
        )
        assert runtime.SOURCE_LINE not in checked.stdout + checked.stderr, (
            'The cache check does not print the discarded compiler diagnostic'
        )


@pytest.fixture
def policy_checkout(tmp_path):
    shutil.copytree(ROOT / '.github', tmp_path / '.github')
    checker = tmp_path / 'tools/ci/source_publishers.py'
    checker.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / checker.relative_to(tmp_path), checker)

    def check():
        return subprocess.run(
            [sys.executable, str(checker)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

    clean = check()
    assert clean.returncode == 0, (
        f'The committed workflow policy passes before mutation: {clean.stderr}'
    )
    return tmp_path, check


def rewrite_policy_file(root, path, document):
    (root / path).write_text(yaml.safe_dump(document, sort_keys=False), encoding='utf-8')


@pytest.mark.parametrize(('workflow', 'job', 'family', 'path'), CACHE_ROUTES, ids=ROUTE_IDS)
def test_actual_compiler_restore_rejects_foreign_cache_family(
    policy_checkout, workflow, job, family, path
):
    root, check = policy_checkout
    target = ACTIONS / 'wasm-cache/action.yml' if family == 'wasm' else WORKFLOWS / workflow
    document = yaml_file(root, target)
    steps = document['runs']['steps'] if family == 'wasm' else document['jobs'][job]['steps']
    restore = workflow_cache_restore(steps, family, path)
    foreign = 'core' if family == 'crysta-sdk' else 'crysta-sdk'
    foreign_key = 'ccache2-' + foreign + '-${{ runner.os }}-${{ runner.arch }}-'
    restore['restore-keys'] += '\n' + foreign_key
    rewrite_policy_file(root, target, document)
    refused = check()
    assert refused.returncode == 1 and any(
        f'{workflow}/{job}:' in line and foreign_key in line
        for line in refused.stderr.splitlines()
    ), 'Policy refuses a live restore whose fallback borrows a different compiler cache family'


@pytest.mark.parametrize(
    ('workflow', 'job', 'publisher', 'kind'),
    [
        ('ci.yml', 'system-time', 'system-time', 'actions/upload-artifact'),
        ('ci.yml', 'system-durations', 'test-durations-', 'actions/cache/save'),
        (
            'installer-accessibility.yml',
            'macos',
            'installer-accessibility-macos',
            'actions/upload-artifact',
        ),
        ('installers.yml', 'installer-pages', 'installer-pages-', 'actions/upload-artifact'),
        (
            'installers.yml',
            'qualify-release',
            'qualified-release-plan-',
            'actions/upload-artifact',
        ),
        ('release-plan.yml', 'plan', 'release-plan-', 'actions/upload-artifact'),
    ],
    ids=['system-time', 'durations', 'accessibility', 'installer-pages', 'qualified-plan', 'plan'],
)
def test_existing_publisher_rejects_an_unchecked_path(
    policy_checkout, workflow, job, publisher, kind
):
    root, check = policy_checkout
    target = WORKFLOWS / workflow
    document = yaml_file(root, target)
    step = next(
        step
        for step in document['jobs'][job]['steps']
        if uses(step, kind)
        and (step['with'].get('name') or step['with']['key']).startswith(publisher)
    )
    step['with']['path'] += '\nunverified/publisher-payload'
    rewrite_policy_file(root, target, document)
    refused = check()
    assert refused.returncode == 1 and f'{workflow}/{job}:' in refused.stderr, (
        'Keeping the approved publication action and name must not authorize additional paths'
    )
