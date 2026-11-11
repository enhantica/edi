# SPDX-License-Identifier: BSD-3-Clause
"""The guarded notebook installer, exercised against offline PEP 503 indexes.

IPython transforms the literal cell; a tiny magic adapter invokes the kernel's pip.
Real notebook execution is separately covered by the clean-wheel kernel gates.
"""

import base64
import hashlib
import importlib.util
import os
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest
from IPython.core.inputtransformer2 import TransformerManager

from tests.fixtures.tutorial_cases.install_cell import INSTALL_CELL

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    'prepare_notebooks', ROOT / 'website/prepare_notebooks.py'
)
PREPARE = importlib.util.module_from_spec(spec)
sys.modules['prepare_notebooks'] = PREPARE
spec.loader.exec_module(PREPARE)
VERSION = PREPARE.PACKAGE_VERSION
WHEEL_FILE = 'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n'


def wheel(directory, name, version, files, requires=()):
    """Write a pure-Python wheel with the given module files."""
    dist = f'{name.replace("-", "_")}-{version}'
    meta = f'Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n'
    meta += ''.join(f'Requires-Dist: {r}\n' for r in requires)
    entries = {
        **files,
        f'{dist}.dist-info/METADATA': meta,
        f'{dist}.dist-info/WHEEL': WHEEL_FILE,
    }
    record = []
    for path, text in entries.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(text.encode()).digest()).rstrip(b'=')
        record.append(f'{path},sha256={digest.decode()},{len(text.encode())}')
    record.append(f'{dist}.dist-info/RECORD,,')
    entries[f'{dist}.dist-info/RECORD'] = '\n'.join(record) + '\n'
    project = directory / name
    project.mkdir(parents=True, exist_ok=True)
    target = project / f'{dist}-py3-none-any.whl'
    with zipfile.ZipFile(target, 'w') as archive:
        for path, text in entries.items():
            archive.writestr(path, text)
    links = ''.join(
        f'<a href="{p.name}#sha256={hashlib.sha256(p.read_bytes()).hexdigest()}">{p.name}</a>\n'
        for p in sorted(project.glob('*.whl'))
    )
    (project / 'index.html').write_text(f'<html><body>\n{links}</body></html>\n')


@pytest.fixture(scope='module')
def indexes(tmp_path_factory):
    base = tmp_path_factory.mktemp('indexes')
    ours, pypi = base / 'ours', base / 'pypi'
    pypi.mkdir()
    wheel(
        ours,
        'easydiffraction',
        VERSION,
        {'easydiffraction/__init__.py': "ORIGIN = 'ours'\n"},
        requires=['edi-test-dependency'],
    )
    wheel(pypi, 'edi-test-dependency', '1.0', {'edi_test_dependency.py': 'VALUE = 1\n'})
    return ours, pypi


@pytest.fixture
def python(tmp_path):
    venv.EnvBuilder(with_pip=True).create(tmp_path / 'venv')
    scripts = 'Scripts' if os.name == 'nt' else 'bin'
    return tmp_path / 'venv' / scripts / ('python.exe' if os.name == 'nt' else 'python')


def environment(primary, **extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith(('PIP_', 'PYTHON'))}
    return {
        **env,
        'PIP_INDEX_URL': primary.as_uri(),
        'PIP_NO_CACHE_DIR': '1',
        'PIP_DISABLE_PIP_VERSION_CHECK': '1',
        **extra,
    }


def run_setup(python, index, env, cwd):
    source = PREPARE.setup_source('case', index=index.as_uri())
    expected = INSTALL_CELL.replace(
        'https://download.easydiffraction.org/pypi/simple/', index.as_uri()
    )
    assert source == expected, 'Notebook setup retains the exact guarded install contract'
    transformed = TransformerManager().transform_cell(source)
    adapter = """import shlex, subprocess, sys
class KernelMagic:
    def run_line_magic(self, name, arguments):
        assert name == 'pip', 'The install cell invokes only the pip line magic'
        print('INSTALL_MAGIC_CALLED', flush=True)
        result = subprocess.run([sys.executable, '-m', 'pip', *shlex.split(arguments)])
        if result.returncode:
            raise SystemExit(result.returncode)
def get_ipython():
    return KernelMagic()
"""
    return subprocess.run(
        [python, '-c', adapter + transformed],
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def installed(python, env, cwd):
    code = (
        'import easydiffraction as edi, importlib.metadata as m; '
        'import edi_test_dependency as d; print(edi.ORIGIN, m.version("easydiffraction"), d.VALUE)'
    )
    result = subprocess.run(
        [python, '-c', code], env=env, cwd=cwd, capture_output=True, text=True, check=False
    )
    return result.stdout.split() if result.returncode == 0 else []


@pytest.mark.parametrize('case', ['case', 'another-case'])
@pytest.mark.parametrize('portable', [False, True])
def test_setup_is_guarded_public_install_independent_of_case_and_portability(case, portable):
    assert PREPARE.setup_source(case, portable=portable) == INSTALL_CELL, (
        'Every released notebook uses the exact guarded official install cell'
    )


@pytest.mark.parametrize('channel', ['environment', 'configuration', 'find-links'])
def test_install_command_uses_the_kernel_environment_and_installs_declared_dependencies(
    channel,
    indexes,
    python,
    tmp_path,
):
    ours, pypi = indexes
    env = environment(pypi)
    if channel == 'configuration':
        config = python.parent.parent / ('pip.ini' if os.name == 'nt' else 'pip.conf')
        config.write_text(f'[global]\nindex-url = {pypi.as_uri()}\n')
        env.pop('PIP_INDEX_URL')
    elif channel == 'find-links':
        env['PIP_FIND_LINKS'] = (pypi / 'edi-test-dependency').as_uri()
    result = run_setup(python, ours, env, tmp_path)
    assert result.returncode == 0, (
        'The literal magic command installs the package and its dependency offline: '
        + result.stderr
    )
    assert installed(python, env, tmp_path) == ['ours', VERSION, '1'], (
        'The selected kernel interpreter imports the public wheel and its installed dependency'
    )


def test_unreachable_indexes_fail_without_claiming_a_successful_install(python, tmp_path):
    result = run_setup(
        python, tmp_path / 'missing-extra', environment(tmp_path / 'missing-primary'), tmp_path
    )
    assert result.returncode != 0 and 'SyntaxError' not in result.stderr, (
        'An unavailable package fails at pip resolution, never by treating a magic as Python'
    )
    assert installed(python, environment(tmp_path / 'missing-primary'), tmp_path) == [], (
        'A failed fresh install cannot claim an importable public package and dependency'
    )


def test_repeating_the_same_setup_keeps_a_complete_install(indexes, python, tmp_path):
    ours, pypi = indexes
    env = environment(pypi)
    for _ in range(2):
        result = run_setup(python, ours, env, tmp_path)
        assert result.returncode == 0, 'Rerunning the notebook install command stays successful'
    assert installed(python, env, tmp_path) == ['ours', VERSION, '1'], (
        'A repeated setup retains the installed public distribution and declared dependency'
    )


def test_an_interrupted_dependency_install_completes_on_the_next_run(indexes, python, tmp_path):
    ours, pypi = indexes
    dependency, hidden = pypi / 'edi-test-dependency', tmp_path / 'hidden-dependency'
    dependency.rename(hidden)
    try:
        first = run_setup(python, ours, environment(pypi), tmp_path)
    finally:
        hidden.rename(dependency)
    assert first.returncode != 0, 'The install command refuses an unavailable declared dependency'
    after = run_setup(python, ours, environment(pypi), tmp_path)
    assert after.returncode == 0, (
        'Restoring the declared dependency lets the unchanged setup finish'
    )
    assert installed(python, environment(pypi), tmp_path) == ['ours', VERSION, '1'], (
        'The recovered installation contains both the public package and its dependency'
    )


@pytest.mark.parametrize('kind', ['folder', 'file'])
def test_a_legacy_local_edi_name_does_not_shadow_the_public_import(
    kind, indexes, python, tmp_path
):
    ours, pypi = indexes
    if kind == 'folder':
        (tmp_path / 'edi').mkdir()
    else:
        (tmp_path / 'edi.py').write_text("ORIGIN = 'local'\n")
    result = run_setup(python, ours, environment(pypi), tmp_path)
    assert result.returncode == 0, (
        'A legacy local name does not obstruct ordinary pip installation'
    )
    assert installed(python, environment(pypi), tmp_path) == ['ours', VERSION, '1'], (
        'The public easydiffraction import resolves the installed wheel despite a local edi name'
    )


def test_existing_public_package_skips_pip_with_unreachable_indexes(indexes, python, tmp_path):
    ours, pypi = indexes
    env = environment(pypi)
    first = run_setup(python, ours, env, tmp_path)
    assert first.returncode == 0 and 'INSTALL_MAGIC_CALLED' in first.stdout, (
        'A missing public package reaches the install magic before the preservation control'
    )
    # A newer candidate makes an accidental upgrade observable as well as a magic call.
    wheel(ours, 'easydiffraction', '2099.1', {'easydiffraction/__init__.py': "ORIGIN = 'new'\n"})
    second = run_setup(
        python, tmp_path / 'missing-extra', environment(tmp_path / 'missing-primary'), tmp_path
    )
    assert second.returncode == 0 and 'INSTALL_MAGIC_CALLED' not in second.stdout, (
        'An existing public package bypasses pip even with unavailable indexes'
    )
    assert installed(python, env, tmp_path) == ['ours', VERSION, '1'], (
        'The guarded cell preserves the existing public package version and dependencies'
    )
