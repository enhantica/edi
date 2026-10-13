"""Owner GUI review build/CI contracts, independent of application code and Python API."""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import runpy
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from tests.fixtures.cwl_family.historical import original_tokens
from tests.fixtures.table_display.metadata_bytes import pre_catalogue_bytes

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = tomllib.loads((ROOT / 'pixi.toml').read_text())
CHECKS = ('app-lint', 'app-format-check', 'app-test', 'app-ui-test', 'group-app')
# Owner decisions 2026-10-02: retain manual check nodes, omit both tiers automatically.
AUTOMATIC_CHECKS = ('app-lint', 'app-format-check', 'group-app')


def tasks():
    result = dict(MANIFEST.get('tasks', {}))
    for feature in MANIFEST.get('feature', {}).values():
        result.update(feature.get('tasks', {}))
    return result


def command(task):
    spec = tasks()[task]
    cmd = spec if isinstance(spec, str) else spec.get('cmd', '')
    return shlex.join(cmd) if isinstance(cmd, list) else cmd


def dependencies(name, visited=None):
    visited = set() if visited is None else visited
    assert name not in visited, 'note 20: check task dependency graph is acyclic'
    visited.add(name)
    spec = tasks().get(name, {})
    result = set()
    for item in spec.get('depends-on', []) if isinstance(spec, dict) else []:
        dep = item if isinstance(item, str) else item['task']
        result.add(dep)
        result.update(dependencies(dep, visited.copy()))
    return result


def sandbox(tmp_path):
    """Copy visible launch/check scripts; fake executables record forbidden side effects."""

    shutil.copytree(ROOT / 'tools', tmp_path / 'tools')
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    for name in ('pixi', 'python', 'python3', 'cmake', 'ninja', 'git', 'curl', 'wget'):
        spy = bin_dir / name
        spy.write_text('#!/bin/sh\nprintf "%s\\n" "' + name + ' $*" >> "$E04_CALLS"\nexit 97\n')
        spy.chmod(0o755)
    return {
        **os.environ,
        'PATH': str(bin_dir) + os.pathsep + os.environ['PATH'],
        'E04_CALLS': str(tmp_path / 'calls'),
        'EDI_APP_TEST_RUNNER': '',
    }


def test_app_run_launches_existing_binary_without_build_or_network(tmp_path):
    assert 'app-run' in tasks(), 'note 15: app environment declares app-run'
    assert not dependencies('app-run'), 'note 15: app-run has no build/check dependencies'
    env = sandbox(tmp_path)
    binary = tmp_path / 'build/app/app/edi_app'
    binary.parent.mkdir(parents=True)
    binary.write_text('#!/bin/sh\necho LAUNCHED\n')
    binary.chmod(0o755)
    run = subprocess.run(
        ['bash', '-c', command('app-run')],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert run.returncode == 0 and 'LAUNCHED' in run.stdout, (
        f'note 15: app-run executes the existing host: {run.stdout} {run.stderr}'
    )
    assert not (tmp_path / 'calls').exists(), (
        'note 15: launching cannot invoke network/build/Python tools'
    )


def test_app_run_missing_binary_is_one_line_hint(tmp_path):
    assert 'app-run' in tasks(), 'note 15: app-run exists independently of app-build'
    env = sandbox(tmp_path)
    run = subprocess.run(
        ['bash', '-c', command('app-run')],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    lines = (run.stdout + run.stderr).strip().splitlines()
    assert run.returncode != 0 and len(lines) == 1 and 'app-build' in lines[0], (
        'note 15: a missing app produces one actionable app-build hint'
    )
    assert not (tmp_path / 'calls').exists(), (
        'note 15: missing artifacts never trigger a build or fetch'
    )


def test_qt_check_reads_committed_expectations_without_python_or_build(tmp_path):
    env = sandbox(tmp_path)
    runner = tmp_path / 'build/app/app/edi_app_tests'
    runner.parent.mkdir(parents=True)
    runner.write_text('#!/bin/sh\necho "Totals: 1 passed, 0 failed, 0 skipped, 0 blacklisted"\n')
    runner.chmod(0o755)
    env['EDI_APP_TEST_RUNNER'] = str(runner)
    cases = tmp_path / 'tests/unit/app'
    cases.mkdir(parents=True)
    (cases / 'tst_witness.qml').write_text('// collection witness\n')
    # Copy committed reference files only: this test never manufactures app values.

    shutil.copytree(ROOT / 'tests/fixtures', tmp_path / 'tests/fixtures')
    run = subprocess.run(
        ['bash', 'tools/ci/app-test.sh'],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert run.returncode == 0 and 'Totals: 1 passed, 0 failed' in run.stdout, (
        'note 16: the Qt check actually consumes its committed expectations and runs its runner; '
        f'{run.stdout} {run.stderr}'
    )
    assert not (tmp_path / 'calls').exists(), (
        'note 16: the Qt runtime never launches Python, builds or fetches'
    )


def expanded_jobs():
    document = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    rows = []
    for key, job in document['jobs'].items():
        matrix = job.get('strategy', {}).get('matrix', {})
        include = matrix.get('include')
        if include:
            variants = include
        elif matrix:
            axes = {
                name: values
                for name, values in matrix.items()
                if name not in {'exclude', 'include'}
            }
            variants = [
                dict(zip(axes, values, strict=True))
                for values in itertools.product(*axes.values())
            ]
        else:
            variants = [{}]
        for variant in variants:
            name = job.get('name', key)
            for field, value in variant.items():
                if isinstance(value, (str, int)):
                    name = re.sub(
                        r'\$\{\{\s*matrix\.' + re.escape(field) + r'\s*\}\}', str(value), name
                    )
            rows.append((key, name, job))
    return rows


def test_ci_job_names_state_area_and_platform_and_share_matrices():
    rows = expanded_jobs()
    names = {name for _, name, _ in rows}
    from tests.integration.py.test_e09_t75_native_workflow import (  # noqa: PLC0415
        jobs,
        public_profile,
    )

    public = public_profile(jobs())
    required = {
        'pin currency',
        'native · Linux',
        'native · macOS',
        'core · Linux',
        'core · macOS',
        'app · Linux',
        'app · macOS',
        'app · WebAssembly',
        'cli-python · Linux',
        'cli-python · macOS',
        'cli-native · Linux',
        'cli-native · macOS',
        'notebooks',
        'docs',
        'lint',
        'audit',
        'changes',
    }
    if public:
        # Parallel system parts and their push-only duration collector identify
        # the same area/platform, with a concrete part suffix on every test job.
        required |= {
            f'system · {platform} · {part}/3'
            for platform in ('Linux', 'macOS')
            for part in (1, 2, 3)
        } | {f'system durations · {platform}' for platform in ('Linux', 'macOS')}
        pages = yaml.safe_load((ROOT / '.github/workflows/pages.yml').read_text())
        assert {job.get('name') for job in pages['jobs'].values()} == {
            'build the site',
            'deploy the site',
        }, 'the separate Pages workflow retains the named build and deployment jobs'
    else:
        required.add('pages')
    assert names == required, (
        f'note 18: CI job display names identify area/platform: {names ^ required}'
    )
    for area in ('native', 'core', 'app', 'cli-python', 'cli-native'):
        keys = {key for key, name, _ in rows if name in {area + ' · Linux', area + ' · macOS'}}
        expected = 2 if area in {'native', 'core'} and not public else 1
        assert len(keys) == expected, (
            f'{area} uses the declared per-platform jobs or shared matrix'
        )


def test_native_cli_placeholder_is_dispatch_only_and_honest():
    rows = [(name, job) for _, name, job in expanded_jobs() if name.startswith('cli-native · ')]
    assert rows, 'note 18: disabled native CLI placeholder is declared now'
    for _, job in rows:
        assert re.fullmatch(
            r"\s*(?:\$\{\{\s*)?github.event_name\s*==\s*'workflow_dispatch'(?:\s*\}\})?\s*",
            job.get('if', ''),
        ), 'note 18: native CLI placeholder executes only on manual dispatch'
        scripts = '\n'.join(step.get('run', '') for step in job['steps'])
        assert re.search(r'not yet|placeholder|not.*exercis', scripts, re.IGNORECASE), (
            'note 18: placeholder states that native CLI coverage is not exercised'
        )


@pytest.mark.parametrize(
    'source',
    sorted({
        case['file']
        for case in json.loads((ROOT / 'tests/fixtures/e04_t2/loops.json').read_text())['loops']
    }),
)
def test_loop_expectations_cover_fixture_bytes(source):
    generator = runpy.run_path(str(ROOT / 'tests/fixtures/e04_t2/generate.py'))
    frozen = json.loads((ROOT / 'tests/fixtures/e04_t2/loops.json').read_text())
    cases = [case for case in frozen['loops'] if case['file'] == source]
    path = ROOT / source
    parsed = generator['loops'](path)
    assert cases, 'gate 3: independent per-file loop inventory is nonempty'
    assert len(cases) == len(parsed), (
        'gate 3: no input-file loop is omitted from the frozen inventory'
    )
    for case in cases:
        digest = case['sha256']
        contents = original_tokens(pre_catalogue_bytes(path))
        replacement = json.loads(
            (ROOT / 'tests/fixtures/e04_t2/replacement-input.json').read_text()
        )
        if source == replacement['file']:
            assert replacement['before_sha256'] == digest, (
                'Gate 3 retains the exact original retired-model input receipt'
            )
            assert re.search(
                r'^_peak\.type\s+' + re.escape(replacement['after_selector']) + r'$',
                path.read_text(),
                re.MULTILINE,
            ), 'Gate 3 replacement input must declare the owner-selected Npr5 shape'
            digest = replacement['after_sha256']
        assert hashlib.sha256(contents).hexdigest() == digest, (
            'Gate 3 frozen loop oracle retains exact input provenance at the selector seam'
        )
        assert {k: case[k] for k in ('category', 'columns', 'rows')} in parsed, (
            'gate 3: every table expectation comes from an actual file declaration'
        )


def test_analysis_inputs_have_no_calculator_category():
    for path in (ROOT / 'tests/fixtures/e04_t1').glob('*-project/analysis/*.edi'):
        categories = set(re.findall(r'^_(\w+)\.', path.read_text(), re.MULTILINE))
        assert 'calculator' not in categories, (
            'note 11: committed analysis.edi has no calculator category'
        )


def test_desktop_ci_builds_once_and_recovery_is_change_scoped():
    app = next((job for _, name, job in expanded_jobs() if name == 'app · Linux'), None)
    assert app is not None, 'notes 20/21: desktop app job exists'
    build_steps = [
        step
        for step in app['steps']
        if re.search(r'pixi run(?: -e app)? app-build(?:\s|$)', step.get('run', ''))
    ]
    assert len(build_steps) == 1, 'note 20: desktop CI explicitly builds once'
    recovery = [step for step in app['steps'] if 'app-build-recovery' in step.get('run', '')]
    assert recovery and all(
        'recovery' in step.get('if', '') or 'app_build' in step.get('if', '') for step in recovery
    ), 'note 21: recovery is conditional on a declared app-build script change output'
    workflow = (ROOT / '.github/workflows/ci.yml').read_text()
    assert 'tools/ci/app-build.sh' in workflow, (
        'note 21: recovery change filter names its input script'
    )
    commands = '\n'.join(step.get('run', '') for step in app['steps'])
    for check in ('app-lint', 'app-test', 'app-ui-test'):
        assert check in commands, f'note 20: desktop job retains separately named {check} check'
    assert 'group-app' in commands or 'pytest tests/integration/app' in commands, (
        'note 20: desktop CI retains the app Python check through its task or direct checker'
    )


def test_crysta_build_and_prefix_are_isolated_by_environment(tmp_path):
    env = sandbox(tmp_path)
    locations = []
    for environment in ('default', 'app'):
        run = subprocess.run(
            ['bash', '-x', 'tools/ci/build-crysta.sh'],
            cwd=tmp_path,
            env={
                **env,
                'PIXI_ENVIRONMENT_NAME': environment,
                'CONDA_PREFIX': str(tmp_path / 'envs' / environment),
                'CRYSTA_SRC': str(tmp_path / 'absent-sibling'),
                'CRYSTA_CONSUMER_SRC': '',
                'GITHUB_TOKEN': '',
            },
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        # Observe the production shell's evaluated paths before our git refusal.
        # This is a shell convention gate, not a claim to run a real compiler.
        values = {}
        # Before: separate source build and install. After ADR-0017: SDK-only prefixes.
        for key in ('PREFIX',):
            matches = re.findall(r'^\+ ' + key + r'=(.+)$', run.stderr, re.MULTILINE)
            assert matches, (
                f'note 19: build script exposes its evaluated {key} path before fetching'
            )
            values[key] = matches[-1]
        locations.append(values)
    assert locations[0]['PREFIX'] != locations[1]['PREFIX'], (
        'note 19: default and app environments cannot overwrite the same crysta install prefix'
    )


def test_owner_note_captures_are_registered_in_the_shared_image_set():
    path = ROOT / 'docs/dev/design/app-review-captures.json'
    assert path.is_file(), (
        'capture rule: note-to-image evidence map is committed for visual review'
    )
    data = json.loads(path.read_text())
    captures = data['captures']
    assert captures, 'capture rule: the evidence map is nonempty'
    notes = {note for capture in captures for note in capture['notes']}
    assert set(range(1, 15)) <= notes, (
        'capture rule: every visible owner note has an image to review'
    )
    assert {'light', 'dark', 'system'} <= {capture['theme'] for capture in captures}, (
        'capture rule: demo switches light/dark/system, with system injected through the app seam'
    )
    expanded = {group for capture in captures for group in capture.get('expanded', [])}
    assert {'instrument', 'linked_structure'} <= expanded, (
        'capture rule: instrument and linked structures are expanded in their evidence images'
    )
    report = [capture for capture in captures if 13 in capture['notes']]
    assert report and all(capture.get('timestamp') for capture in report), (
        'note 13: Report Text captures declare their pinned timestamp'
    )
    for capture in captures:
        image = ROOT / 'docs/dev/design/app-screenshots/edi' / capture['image']
        assert image.is_file() and image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'), (
            'capture rule: each note points to a real shared-baseline PNG checked by app-ui-test'
        )
    # This inventory does NOT certify appearance; reviewer/conductor inspect these images.


def sequence_sandbox(tmp_path):
    """Execute real orchestration scripts, substituting only builders and terminal tools."""
    env = sandbox(tmp_path)
    for key in tuple(env):
        if key.startswith('EDI_APP_'):
            env.pop(key)
    shutil.copyfile(ROOT / 'pixi.toml', tmp_path / 'pixi.toml')
    for name in ('docs/user/cli/projects.yml', 'app/examples/metadata.json'):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    for source in (ROOT / 'docs/user/cli', ROOT / 'app/examples'):
        for project in source.glob('*/project'):
            for child in ('', 'experiments', 'structures', 'analysis'):
                for path in (project / child).glob('*.edi'):
                    target = tmp_path / path.relative_to(ROOT)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
    dispatcher = ROOT / 'tests/fixtures/e04_t2/task_spy.py'
    shutil.copyfile(dispatcher, tmp_path / 'task_spy.py')
    env['CONDA_PREFIX'] = str(tmp_path / 'prefix')
    env['PIXI_ENVIRONMENT_NAME'] = 'default'
    env['PYTHONPATH'] = ''

    def script(path, body):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('#!/bin/bash\nset -eu\n' + body + '\n')
        target.chmod(0o755)

    for task in ('app-build', 'core-build'):
        script(
            f'tools/ci/{task}.sh',
            'if [ "$#" -ne 0 ]; then echo query >> "$E04_CALLS"; exit 97; fi\n'
            f'echo build:{task} >> "$E04_CALLS"\nexit "${{E04_BUILD_RC:-0}}"',
        )
    script('bin/pixi', f'exec {shlex.quote(sys.executable)} task_spy.py "$@"')
    script(
        'bin/python',
        'if [ "${1:-}" = -m ] && [ "${2:-}" = pytest ]; then\n'
        'echo check:group-app >> "$E04_CALLS"\nexit 0\nfi\n'
        'if [ "${1:-}" = tests/integration/cmake/check_gui_base.py ]; then\n'
        'echo check:gui-base >> "$E04_CALLS"\nexit "${BASE_CHECK_RC:-0}"\nfi\n'
        f'exec {shlex.quote(sys.executable)} "$@"',
    )
    shutil.copyfile(tmp_path / 'bin/python', tmp_path / 'bin/python3')
    script('prefix/lib/qt6/bin/qmllint', 'echo check:app-lint >> "$E04_CALLS"')
    script(
        'prefix/lib/qt6/bin/qmlformat',
        'echo check:app-format-check >> "$E04_CALLS"\ncat "$1"',
    )
    script(
        'build/app/app/edi_app_tests',
        'echo check:app-test >> "$E04_CALLS"\n'
        'echo "Totals: 1 passed, 0 failed, 0 skipped, 0 blacklisted"',
    )
    script('build/app/app/edi_app', 'echo check:app-ui-test >> "$E04_CALLS"')
    script('build/app/app/edi_app_ui_compare', 'echo compare >> "$E04_CALLS"')
    script(
        'tools/ci/app-platform.sh', 'app_capture_platform() { export QT_QPA_PLATFORM=offscreen; }'
    )
    for directory in ('build/app/qml/edi/app', 'tests/unit/app', 'app/qml'):
        (tmp_path / directory).mkdir(parents=True, exist_ok=True)
    (tmp_path / 'app/qml/Witness.qml').write_text('import QtQuick\nItem {}\n')
    (tmp_path / 'tests/unit/app/tst_witness.qml').write_text('// collection witness\n')
    record = tmp_path / 'build/app/app/meta_types/qt6edi_app_module_metatypes.json'
    record.parent.mkdir()
    record.write_text(
        json.dumps([
            {
                'classes': [
                    {
                        'qualifiedClassName': 'Witness',
                        'properties': [{'name': 'value', 'notify': 'valueChanged'}],
                    }
                ]
            }
        ])
    )
    shutil.copytree(ROOT / 'tests/fixtures', tmp_path / 'tests/fixtures')
    return env


def run_task(tmp_path, env, name):
    return subprocess.run(
        [str(tmp_path / 'bin/pixi'), 'run', name],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def calls(tmp_path):
    path = tmp_path / 'calls'
    return path.read_text().splitlines() if path.exists() else []


@pytest.mark.parametrize('name', CHECKS)
def test_standalone_step_builds_first_every_time(tmp_path, name):
    env = sequence_sandbox(tmp_path)
    for _ in range(2):
        (tmp_path / 'calls').unlink(missing_ok=True)
        result = run_task(tmp_path, env, name)
        observed = calls(tmp_path)
        assert result.returncode == 0, (
            f'corrected note 20: standalone {name} builds and checks: {result.stderr}'
        )
        assert observed.count('build:app-build') == 1, (
            f'corrected note 20: standalone always builds once: {observed}'
        )
        assert f'check:{name}' in observed, (
            f'corrected note 20: standalone {name} reaches its actual checker: {observed}'
        )
        assert observed.index('build:app-build') < observed.index(f'check:{name}'), (
            f'corrected note 20: standalone {name} builds before its checker: {observed}'
        )


@pytest.mark.parametrize('name', [*CHECKS, 'app-build-recovery'])
def test_standalone_failed_build_prevents_checks(tmp_path, name):
    env = sequence_sandbox(tmp_path)
    result = run_task(tmp_path, {**env, 'E04_BUILD_RC': '23'}, name)
    observed = calls(tmp_path)
    assert result.returncode != 0 and any(item.startswith('build:') for item in observed), (
        f'corrected note 20: standalone {name} propagates the failed build: {observed}'
    )
    assert not any(item.startswith('check:') for item in observed), (
        f'corrected note 20: {name} cannot run a check after its build failed: {observed}'
    )


def assert_sequence(observed, checks=AUTOMATIC_CHECKS):
    assert observed.count('build:app-build') == 1, (
        f'corrected note 20: a full sequence builds the app exactly once: {observed}'
    )
    for name in checks:
        assert observed.count(f'check:{name}') == 1, (
            f'corrected note 20: sequence retains each check once: {name}: {observed}'
        )
        assert observed.index('build:app-build') < observed.index(f'check:{name}'), (
            f'corrected note 20: the shared app build precedes every check: {name}: {observed}'
        )


@pytest.mark.parametrize(
    'name', ['app-verify', 'app-gates', 'verify-quick', 'verify-full', 'verify', 'merge-tasks']
)
def test_full_sequence_builds_once_before_checks(tmp_path, name):
    env = sequence_sandbox(tmp_path)
    result = run_task(tmp_path, env, name)
    assert result.returncode == 0, (
        f'corrected note 20: {name} completes its shell sequence: {result.stderr}'
    )
    observed = calls(tmp_path)
    checks = tuple(
        check for check in AUTOMATIC_CHECKS if name != 'app-gates' or check != 'group-app'
    )
    assert_sequence(observed, checks)
    assert not {'check:app-test', 'check:app-ui-test'} & set(observed), (
        ' owner decisions: automatic local sequences execute neither disabled app tier'
    )


@pytest.mark.parametrize('platform', ['Linux', 'macOS'])
def test_desktop_ci_sequence_builds_once_before_checks(tmp_path, platform):
    env = sequence_sandbox(tmp_path)
    job = next(job for _, name, job in expanded_jobs() if name == f'app · {platform}')
    # Actions stringifies YAML env values (EDI_NATIVE_ARTIFACT is declared as 1).
    env.update({key: str(value) for key, value in job.get('env', {}).items()})
    for step in job['steps']:
        if step.get('if') is False:
            continue
        cmd = step.get('run', '')
        # Recovery is a separate change-scoped rebuild exercise (note 21).
        if not re.search(
            r'\b(?:app-build|core-build|app-lint|app-format-check|app-test|app-ui-test)'
            r'(?:\.sh)?(?:\s|$)|\bgroup-app(?:\s|$)|pytest tests/integration/app',
            cmd,
        ):
            continue
        step_env = {**env, **{key: str(value) for key, value in step.get('env', {}).items()}}
        result = subprocess.run(
            ['bash', '-c', cmd],
            cwd=tmp_path,
            env=step_env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, (
            f'corrected note 20: CI {platform} completes its declared step {cmd}: {result.stderr}'
        )
    assert_sequence(calls(tmp_path))
    assert not {'check:app-test', 'check:app-ui-test'} & set(calls(tmp_path)), (
        ' owner decisions: both desktop CI sequences execute neither disabled app tier'
    )


@pytest.mark.parametrize(
    'damage', ['missing-build', 'double-build', 'late-build', 'missing-check']
)
def test_sequence_observer_rejects_wrong_order_or_cardinality(damage):
    observed = ['build:app-build', *(f'check:{name}' for name in CHECKS)]
    assert_sequence(observed)
    if damage == 'missing-build':
        observed.pop(0)
    elif damage == 'double-build':
        observed.insert(1, 'build:app-build')
    elif damage == 'late-build':
        observed.append(observed.pop(0))
    else:
        observed.pop()
    with pytest.raises(AssertionError, match='corrected note 20:'):
        assert_sequence(observed)


@pytest.mark.parametrize('qualified', [False, True])
def test_dispatcher_preserves_explicit_and_inherited_build_identity(tmp_path, qualified):
    env = sequence_sandbox(tmp_path)
    dependency = '{ task = "app-build", environment = "app" }' if qualified else '"app-build"'
    # Independent replay of review-7's real-run defect: direct explicit build,
    # then a check with either that same identity or the inherited spelling.
    (tmp_path / 'pixi.toml').write_text(
        '[tasks]\n'
        'app-build = { cmd = ["bash", "tools/ci/app-build.sh"] }\n'
        'app-lint = { cmd = "echo check:app-lint >> $E04_CALLS", '
        f'depends-on = [{dependency}] }}\n'
        'app-verify = { depends-on = [{ task = "app-build", environment = "app" }, '
        '{ task = "app-lint", environment = "app" }] }\n'
    )
    result = run_task(tmp_path, env, 'app-verify')
    assert result.returncode == 0, 'note 20: identity control must execute both dependency edges'
    observed = calls(tmp_path)
    assert observed.count('build:app-build') == (1 if qualified else 2), (
        'note 20: inherited and explicit environment references cannot collapse into one build'
    )
    if qualified:
        assert_sequence(observed, ('app-lint',))
    else:
        with pytest.raises(AssertionError, match='exactly once'):
            assert_sequence(observed, ('app-lint',))


@pytest.mark.parametrize('options', [[], ['-e', 'app'], ['--environment', 'app']])
@pytest.mark.parametrize('skip_first', [False, True])
def test_dispatcher_skip_deps_keeps_checker_and_environment(tmp_path, options, skip_first):
    env = sequence_sandbox(tmp_path)
    flags = ['--skip-deps', *options] if skip_first else [*options, '--skip-deps']
    # Include recovery: its dedicated CI invocation skips the initial build,
    # while retaining the recovery command (whose own rebuild is intentional).
    for task in (*CHECKS, 'app-build-recovery'):
        (tmp_path / 'calls').unlink(missing_ok=True)
        (tmp_path / 'pixi.toml').write_text(
            '[tasks]\n'
            'app-build = { cmd = ["bash", "tools/ci/app-build.sh"] }\n'
            f'{task} = {{ cmd = "echo check:{task}:$PIXI_ENVIRONMENT_NAME >> $E04_CALLS", '
            'depends-on = [{ task = "app-build", environment = "app" }] }\n'
        )
        result = subprocess.run(
            [str(tmp_path / 'bin/pixi'), 'run', *flags, task],
            cwd=tmp_path,
            env={**env, 'E04_BUILD_RC': '23'},
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        expected_env = 'app' if options else 'default'
        assert result.returncode == 0 and calls(tmp_path) == [f'check:{task}:{expected_env}'], (
            'note 20: skip-deps omits even a failing dependency but retains the selected checker'
        )


def test_sequence_retains_the_source_checker_failure_barrier(tmp_path):
    env = sequence_sandbox(tmp_path)
    result = run_task(tmp_path, {**env, 'BASE_CHECK_RC': '23'}, 'app-lint')
    observed = calls(tmp_path)
    assert result.returncode != 0 and observed == ['build:app-build', 'check:gui-base'], (
        'The real lint sequence must build first, execute the source checker and '
        'refuse Qt lint after that checker fails'
    )
