"""Locked ABI admission must precede every cold SDK bootstrap or compilation."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.fixtures.e09_t75_workflow import active

ROOT = Path(__file__).resolve().parents[3]
PACKAGES = {
    'linux-64': (
        'gcc_impl_linux-64',
        'gxx_impl_linux-64',
        'libgcc',
        'libgcc-devel_linux-64',
        'libstdcxx',
        'libstdcxx-devel_linux-64',
        'libgomp',
        'sysroot_linux-64',
        'eigen',
        'sleef',
    ),
    'osx-arm64': (
        'clang_impl_osx-arm64',
        'clangxx_impl_osx-arm64',
        'libcxx',
        'libcxx-devel',
        'llvm-openmp',
        'eigen',
        'sleef',
    ),
    'win-64': ('vs2022_win-64', 'vc14_runtime', 'vcomp14', 'eigen'),
}
COORDINATES = [(platform, name) for platform, names in PACKAGES.items() for name in names]
WINDOWS_LOCKED = {
    'vs2022_win-64': ('19.44.35207', 'ha74f236_42'),
    'vc14_runtime': ('14.51.36247', 'habf1de7_42'),
    'vcomp14': ('14.51.36247', 'habf1de7_42'),
    'eigen': ('3.4.0', 'h5112557_2'),
}


@pytest.fixture
def reader():
    path = Path(os.environ.get('EDI_SDK_READER_CONTRACT_TOOL', ROOT / 'tools/ci/crysta_sdk.py'))
    spec = importlib.util.spec_from_file_location('sdk_preflight_reader', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def locked(platform):
    return dict.fromkeys(PACKAGES[platform], ('1.2.3', 'independent_7'))


def write_lock(path, platform, environments):
    lines = [
        'version: 7',
        'platforms:',
        '- name: selected',
        f'  subdir: {platform}',
        'environments:',
    ]
    for environment, packages in environments.items():
        lines.extend([f'  {environment}:', '    packages:', '      selected:'])
        for name, (version, build) in packages.items():
            lines.append(
                f'      - conda: https://conda.anaconda.org/conda-forge/{platform}/'
                f'{name}-{version}-{build}.conda'
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join([*lines, 'packages: []', '']))
    return path


def arguments(source, consumer, platform, environment='default'):
    return [
        'preflight',
        '--source-lock',
        str(source),
        '--platform',
        platform,
        '--lockfile',
        str(consumer),
        '--environment',
        environment,
    ]


@pytest.mark.parametrize('platform', PACKAGES)
def test_preflight_accepts_exact_required_tuples_in_the_selected_environments(
    reader, tmp_path, platform
):
    packages = locked(platform)
    source = write_lock(tmp_path / 'producer.lock', platform, {'cpp-ci': packages, 'default': {}})
    consumer = write_lock(tmp_path / 'consumer.lock', platform, {'app': packages, 'default': {}})
    assert reader.main(arguments(source, consumer, platform, 'app')) == 0, (
        'Cold SDK admission must compare cpp-ci with the explicitly selected consumer environment'
    )


@pytest.mark.parametrize(('platform', 'name'), COORDINATES)
@pytest.mark.parametrize('side', ['producer', 'consumer'])
@pytest.mark.parametrize('defect', ['missing', 'version', 'build'])
def test_preflight_refuses_each_missing_or_unequal_abi_operand(
    reader, tmp_path, capsys, platform, name, side, defect
):
    producer, consumer = locked(platform), locked(platform)
    selected = producer if side == 'producer' else consumer
    if defect == 'missing':
        del selected[name]
    elif defect == 'version':
        selected[name] = ('9.8.7', selected[name][1])
    else:
        selected[name] = (selected[name][0], 'different_8')
    source = write_lock(tmp_path / 'producer.lock', platform, {'cpp-ci': producer})
    target = write_lock(tmp_path / 'consumer.lock', platform, {'default': consumer})
    assert reader.main(arguments(source, target, platform)) == 1, (
        'All required compiler, runtime, OpenMP, sysroot and numerical tuples must match exactly'
    )
    error = capsys.readouterr().err
    assert 'REFUSED' in error, 'An incompatible cold SDK must stop with a typed refusal'
    assert name in error, 'The early ABI refusal must identify the incompatible or missing package'


@pytest.mark.parametrize(('platform', 'name'), COORDINATES)
def test_preflight_refuses_a_required_package_missing_from_both_sides(
    reader, tmp_path, platform, name
):
    packages = locked(platform)
    del packages[name]
    source = write_lock(tmp_path / 'producer.lock', platform, {'cpp-ci': packages})
    consumer = write_lock(tmp_path / 'consumer.lock', platform, {'default': packages})
    assert reader.main(arguments(source, consumer, platform)) == 1, (
        'Two equal missing operands cannot prove the required compiler/runtime ABI inventory'
    )


def test_actual_windows_compiler_build_39_refuses_installer_42_and_aligned_42_passes(
    reader, tmp_path, capsys
):
    consumer = ROOT / 'tools/installer/pixi.lock'
    assert {
        name: reader.lock_packages('default', 'win-64', consumer)[name] for name in WINDOWS_LOCKED
    } == WINDOWS_LOCKED, (
        'The regression witness binds the actual installer compiler/CRT/OpenMP/Eigen lock tuples'
    )
    old = dict(WINDOWS_LOCKED)
    old['vs2022_win-64'] = ('19.44.35207', 'ha74f236_39')
    source = write_lock(tmp_path / 'producer.lock', 'win-64', {'cpp-ci': old})
    assert reader.main(arguments(source, consumer, 'win-64')) == 1, (
        'The observed compiler build39 versus installer build42 must refuse before compilation'
    )
    error = capsys.readouterr().err
    assert 'ha74f236_39' in error, 'The refusal must expose the actual old producer build'
    assert 'ha74f236_42' in error, 'The refusal must expose the actual required consumer build'
    write_lock(source, 'win-64', {'cpp-ci': WINDOWS_LOCKED})
    assert reader.main(arguments(source, consumer, 'win-64')) == 0, (
        'The aligned exact Windows compiler build42 admits the existing runtime ABI family'
    )


@pytest.mark.parametrize('side', ['producer', 'consumer'])
@pytest.mark.parametrize(
    'defect', ['missing-file', 'empty', 'malformed', 'wrong-environment', 'wrong-platform']
)
def test_preflight_refuses_unavailable_or_unresolvable_lock_inputs(
    reader, tmp_path, side, defect, capsys
):
    platform = 'linux-64'
    source = write_lock(tmp_path / 'producer.lock', platform, {'cpp-ci': locked(platform)})
    consumer = write_lock(tmp_path / 'consumer.lock', platform, {'default': locked(platform)})
    selected = source if side == 'producer' else consumer
    if defect == 'missing-file':
        selected.unlink()
    elif defect in {'empty', 'malformed'}:
        selected.write_text('' if defect == 'empty' else 'not a lock document\n')
    else:
        write_lock(
            selected,
            'win-64' if defect == 'wrong-platform' else platform,
            {
                ('cpp-ci' if side == 'producer' else 'default')
                if defect == 'wrong-platform'
                else 'unselected': locked(platform)
            },
        )
    assert reader.main(arguments(source, consumer, platform)) == 1, (
        'Missing, malformed or unresolvable lock inputs must refuse before any compiler bootstrap'
    )
    assert 'REFUSED' in capsys.readouterr().err, (
        'Bad lock input must retain the concise refusal boundary'
    )


@pytest.mark.parametrize('environment', ['', 'absent', '../default', ' default'])
def test_preflight_cannot_fall_back_from_an_invalid_explicit_environment(
    reader, tmp_path, environment
):
    platform = 'linux-64'
    source = write_lock(tmp_path / 'producer.lock', platform, {'cpp-ci': locked(platform)})
    consumer = write_lock(tmp_path / 'consumer.lock', platform, {'default': locked(platform)})
    assert reader.main(arguments(source, consumer, platform, environment)) == 1, (
        'An explicit invalid consumer environment cannot silently select default ABI packages'
    )


@pytest.mark.parametrize('platform', ['linux', 'win-32', 'osx-64', ''])
def test_preflight_cli_refuses_unsupported_platform_before_opening_locks(reader, platform):
    with pytest.raises(SystemExit, match='2'):
        reader.main(arguments(Path('missing-producer'), Path('missing-consumer'), platform))


def workflow_contract(steps):
    checkout = next(step for step in steps if 'git init -q' in step.get('run', ''))
    python = next(step for step in steps if step.get('uses') == 'actions/setup-python@v6')
    preflight = next(step for step in steps if ' preflight ' in step.get('run', ''))
    bootstrap = next(step for step in steps if step.get('uses') == './.github/actions/setup-pixi')
    package = next(step for step in steps if 'sdk-pack' in step.get('run', ''))
    assert (
        steps.index(checkout)
        < steps.index(python)
        < steps.index(preflight)
        < steps.index(bootstrap)
        < steps.index(package)
    ), 'Cold admission must follow exact source/Python setup and precede binding bootstrap'
    assert python['with'].get('update-environment') is False, (
        'Metadata Python setup must preserve the later Pixi bootstrap interpreter environment'
    )
    assert python.get('id') == 'sdk-python', (
        'The metadata interpreter output must be addressable explicitly'
    )
    assert python['with']['python-version'] == '3.14', (
        'ABI metadata parsing must use the declared Python3.14 tool'
    )
    for step in (python, preflight):
        for hit in ('true', 'false'):
            assert active(step, 'pull_request', outputs={('cache', 'cache-hit'): hit}) == (
                hit == 'false'
            ), 'Only cold builds run early admission; warm archives retain manifest checks'
    return preflight


def test_workflow_preflight_orders_cold_build_and_rejects_reordered_or_warm_admission():
    steps = yaml.safe_load((ROOT / '.github/workflows/crysta-sdk.yml').read_text())['jobs'][
        'build'
    ]['steps']
    preflight = workflow_contract(steps)
    for defect in ('late', 'early', 'warm', 'python-env', 'python-output'):
        changed = copy.deepcopy(steps)
        index = next(i for i, step in enumerate(changed) if step.get('name') == preflight['name'])
        if defect.startswith('python-'):
            setup = next(step for step in changed if step.get('uses') == 'actions/setup-python@v6')
            if defect == 'python-env':
                setup['with']['update-environment'] = True
            else:
                setup.pop('id')
        elif defect == 'warm':
            changed[index]['if'] = "steps.cache.outputs.cache-hit == 'true'"
        else:
            step = changed.pop(index)
            changed.insert(0 if defect == 'early' else len(changed), step)
        with pytest.raises(AssertionError):
            workflow_contract(changed)


def python_calls(tmp_path):
    bindir = tmp_path / 'metadata python'
    bindir.mkdir()
    records = tmp_path / 'python-calls.jsonl'
    program = (
        '#!' + Path(sys.executable).as_posix() + '\nimport json,os,runpy,sys\n'
        'with open(os.environ["PREFLIGHT_CALLS"],"a") as output:\n'
        ' output.write(json.dumps(sys.argv[1:])+"\\n")\n'
        'sys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n'
    )
    for name in ('python', 'python3'):
        path = bindir / name
        path.write_bytes(program.encode())
        path.chmod(0o755)
    ambient = tmp_path / 'ambient-python'
    ambient.mkdir()
    for name in ('python', 'python3'):
        path = ambient / name
        path.write_text('#!/bin/sh\nprintf ambient-called > ambient-called\nexit 91\n')
        path.chmod(0o755)
    return (
        records,
        {
            **os.environ,
            'PATH': str(ambient) + os.pathsep + os.environ['PATH'],
            'Python_ROOT_DIR': 'untouched-pixi-interpreter-root',
            'PREFLIGHT_CALLS': str(records),
        },
        bindir / 'python',
    )


@pytest.mark.parametrize('platform', PACKAGES)
@pytest.mark.parametrize('ambient', ['absent', 'poisoned'])
def test_actual_preflight_step_checks_installer_and_only_supported_root_environments(
    tmp_path, platform, ambient
):
    steps = yaml.safe_load((ROOT / '.github/workflows/crysta-sdk.yml').read_text())['jobs'][
        'build'
    ]['steps']
    step = workflow_contract(steps)
    assert '${{ matrix.platform }}' in step['run'], (
        'The shell must receive literal matrix identity without step environment delivery'
    )
    (tmp_path / 'tools/ci').mkdir(parents=True)
    shutil.copy2(ROOT / 'tools/ci/crysta_sdk.py', tmp_path / 'tools/ci/crysta_sdk.py')
    source = write_lock(
        tmp_path / 'runner/crysta/pixi.lock', platform, {'cpp-ci': locked(platform)}
    )
    installer = write_lock(
        tmp_path / 'tools/installer/pixi.lock', platform, {'default': locked(platform)}
    )
    root_lock = write_lock(
        tmp_path / 'pixi.lock', platform, {'default': locked(platform), 'app': locked(platform)}
    )
    records, env, interpreter = python_calls(tmp_path)
    env['RUNNER_TEMP'] = str(tmp_path / 'runner')
    env.pop('PLATFORM', None)
    env.pop('sdk_platform', None)
    if ambient == 'poisoned':
        env['PLATFORM'] = 'not-the-matrix-platform'
    script = step['run'].replace('${{ matrix.platform }}', platform)
    script = script.replace('${{ steps.sdk-python.outputs.python-path }}', str(interpreter))
    assert '${{' not in script, (
        'The bounded shell replay must resolve every actual matrix expression'
    )
    script += '\nprintf bootstrap-admitted > admitted\n'
    script += 'printf "%s\\n" "$PATH" "${Python_ROOT_DIR-}" > environment-after\n'

    def run():
        return subprocess.run(
            ['bash', '-e', '-c', script],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

    good = run()
    assert good.returncode == 0, (
        'The actual cold preflight step admits every declared aligned consumer'
    )
    assert good.stdout.count('SDK ABI package locks match') == 3, (
        'Every platform checks installer, root default and app through the same admission step'
    )
    assert (tmp_path / 'environment-after').read_text().splitlines() == [
        env['PATH'],
        env['Python_ROOT_DIR'],
    ], 'Metadata checks must leave the ambient PATH and Pixi Python root unchanged'
    assert not (tmp_path / 'ambient-called').exists(), (
        'Metadata checks must use the explicit action output rather than ambient Python lookup'
    )
    observed = [json.loads(line) for line in records.read_text().splitlines()]
    assert all(call[call.index('--platform') + 1] == platform for call in observed), (
        'Every reader call must receive the matrix platform despite absent or poisoned env'
    )
    for selected, environment in [
        (installer, 'default'),
        (root_lock, 'default'),
        (root_lock, 'app'),
    ]:
        (tmp_path / 'admitted').unlink(missing_ok=True)
        broken = locked(platform)
        broken[PACKAGES[platform][0]] = ('9.8.7', 'wrong_9')
        environments = (
            {'default': locked(platform), 'app': locked(platform)}
            if selected == root_lock
            else {'default': locked(platform)}
        )
        environments[environment] = broken
        write_lock(selected, platform, environments)
        bad = run()
        assert bad.returncode != 0, (
            'A mismatch in any real consumer must stop the actual pre-bootstrap step'
        )
        assert not (tmp_path / 'admitted').exists(), (
            'No bootstrap marker can execute after failed lock admission'
        )
        write_lock(selected, platform, {name: locked(platform) for name in environments})
    assert source.is_file(), (
        'The actual pinned producer lock remains present throughout the admission controls'
    )


@pytest.mark.parametrize('missing', [False, True])
@pytest.mark.parametrize('field', ['platform', 'python'])
def test_preflight_missing_matrix_identity_refuses_before_any_python_call(
    tmp_path, missing, field
):
    steps = yaml.safe_load((ROOT / '.github/workflows/crysta-sdk.yml').read_text())['jobs'][
        'build'
    ]['steps']
    step = workflow_contract(steps)
    assert '${{ matrix.platform }}' in step['run'], (
        'The missing-context control must address the real matrix-to-shell assignment'
    )
    records, env, interpreter = python_calls(tmp_path)
    script = step['run'].replace('${{ matrix.platform }}', '' if field == 'platform' else 'win-64')
    script = script.replace(
        '${{ steps.sdk-python.outputs.python-path }}',
        '' if field == 'python' else str(interpreter),
    )
    variable = 'sdk_platform' if field == 'platform' else 'metadata_python'
    if missing:
        script = '\n'.join(line for line in script.splitlines() if variable + '=' not in line)
    for key in ('PLATFORM', 'sdk_platform', 'metadata_python'):
        env.pop(key, None)
    result = subprocess.run(
        ['bash', '-e', '-u', '-c', script],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert result.returncode != 0, (
        'Missing matrix identity or metadata interpreter must refuse immediately'
    )
    assert not records.exists(), (
        'Missing metadata context must refuse before any Python or bootstrap call'
    )
