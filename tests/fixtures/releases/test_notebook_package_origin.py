# SPDX-License-Identifier: BSD-3-Clause
"""The notebook setup cell's contract (website ADR-0018), offline.

The wheel comes only from our index by URL and sha256; an edi already imported in the kernel
always ends in a restart request; a first import is admitted only for a file the installed
wheel's RECORD lists. A package planted on a deliberately prepended path is out of scope.

Two local PEP 503 indexes stand in for ours and for PyPI. The PyPI stand-in offers the same
version and a higher one with different content, and it is offered to pip every way pip takes
a source: environment variables, a configuration file in the environment, and find-links. Each
case runs the generated cell, then asks the environment which package ``import edi`` loads.
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

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    'prepare_notebooks', ROOT / 'website/prepare_notebooks.py'
)
PREPARE = importlib.util.module_from_spec(spec)
sys.modules['prepare_notebooks'] = PREPARE
spec.loader.exec_module(PREPARE)
VERSION = '2026.11.6'
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


def edi_files(origin):
    return {'edi/__init__.py': f'ORIGIN = {origin!r}\n'}


@pytest.fixture(scope='module')
def indexes(tmp_path_factory):
    base = tmp_path_factory.mktemp('indexes')
    ours, pypi = base / 'ours', base / 'pypi'
    wheel(ours, 'easydiffraction', VERSION, edi_files('ours'), requires=['edi-test-dependency'])
    wheel(pypi, 'easydiffraction', VERSION, edi_files('pypi'))
    wheel(pypi, 'easydiffraction', '9999.1.0', edi_files('pypi-higher'))
    wheel(pypi, 'edi-test-dependency', '1.0', {'edi_test_dependency.py': 'VALUE = 1\n'})
    return ours, pypi


@pytest.fixture
def python(tmp_path):
    venv.EnvBuilder(with_pip=True).create(tmp_path / 'venv')
    scripts = 'Scripts' if os.name == 'nt' else 'bin'
    return tmp_path / 'venv' / scripts / ('python.exe' if os.name == 'nt' else 'python')


def environment(pypi, **extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith(('PIP_', 'PYTHON'))}
    return {
        **env,
        'PIP_INDEX_URL': pypi.as_uri(),
        'PIP_EXTRA_INDEX_URL': pypi.as_uri(),
        'PIP_NO_CACHE_DIR': '1',
        'PIP_DISABLE_PIP_VERSION_CHECK': '1',
        **extra,
    }


def run_setup(python, index, env, cwd):
    cell = cwd / 'setup_cell.py'
    cell.write_text(PREPARE.setup_source('case', index=index.as_uri()))
    return subprocess.run(
        [python, cell], env=env, cwd=cwd, capture_output=True, text=True, check=False
    )


def installed(python, env, cwd):
    code = 'import edi, importlib.metadata as m; print(edi.ORIGIN, m.version("easydiffraction"))'
    return subprocess.run(
        [python, '-c', code], env=env, cwd=cwd, capture_output=True, text=True, check=False
    ).stdout.split()


def pip_install(python, env, *args):
    subprocess.run(
        [python, '-m', 'pip', 'install', *args], env=env, check=True, capture_output=True
    )


def test_ours_wins_over_equal_and_higher_versions_and_dependencies_come_from_pypi(
    indexes, python, tmp_path
):
    ours, pypi = indexes
    env = environment(pypi)
    result = run_setup(python, ours, env, tmp_path)
    assert result.returncode == 0, (
        'Ours wins over equal and higher versions and dependencies come from PyPI.',
        result.stderr,
    )
    assert installed(python, env, tmp_path) == ['ours', VERSION], (
        'Ours wins over equal and higher versions and dependencies come from PyPI.'
    )
    dependency = subprocess.run(
        [python, '-c', 'import edi_test_dependency'], env=env, capture_output=True, check=False
    )
    assert dependency.returncode == 0, (
        'Ours wins over equal and higher versions and dependencies come from PyPI.'
    )


def test_unreachable_index_refuses_instead_of_falling_back(indexes, python, tmp_path):
    _, pypi = indexes
    env = environment(pypi)
    result = run_setup(python, tmp_path / 'missing-index', env, tmp_path)
    assert result.returncode != 0, 'Unreachable index refuses instead of falling back.'
    assert installed(python, env, tmp_path) == [], (
        'Unreachable index refuses instead of falling back.'
    )


def test_a_pip_installed_wrong_package_is_replaced(indexes, python, tmp_path):
    ours, pypi = indexes
    env = environment(pypi)
    pip_install(python, env, f'easydiffraction=={VERSION}')
    assert installed(python, env, tmp_path) == ['pypi', VERSION], (
        'A pip installed wrong package is replaced.'
    )
    result = run_setup(python, ours, env, tmp_path)
    assert result.returncode == 0, ('A pip installed wrong package is replaced.', result.stderr)
    assert installed(python, env, tmp_path) == ['ours', VERSION], (
        'A pip installed wrong package is replaced.'
    )


def test_an_explicit_source_build_is_kept_without_installing(indexes, python, tmp_path):
    _, pypi = indexes
    source = tmp_path / 'source'
    (source / 'edi').mkdir(parents=True)
    (source / 'edi/__init__.py').write_text("ORIGIN = 'source'\n")
    env = environment(pypi, PYTHONPATH=str(source), EDI_SOURCE_BUILD='1')
    result = run_setup(python, tmp_path / 'missing-index', env, tmp_path)
    assert result.returncode == 0, ('A source build is kept without installing.', result.stderr)
    code = 'import edi, importlib.util as u; print(edi.ORIGIN, u.find_spec("easydiffraction"))'
    out = subprocess.run(
        [python, '-c', code], env=env, capture_output=True, text=True, check=False
    ).stdout
    assert out.split() == ['source', 'None'], 'A source build is kept without installing.'


def configure_pip(python, pypi):
    """A pip configuration file inside the environment, which --isolated does not ignore."""
    venv_root = python.parent.parent
    name = 'pip.ini' if os.name == 'nt' else 'pip.conf'
    (venv_root / name).write_text(
        f'[global]\nindex-url = {pypi.as_uri()}\nextra-index-url = {pypi.as_uri()}\n'
        f'find-links = {(pypi / "easydiffraction").as_uri()}\n'
    )


def test_configuration_files_and_find_links_cannot_supply_the_package(indexes, python, tmp_path):
    ours, pypi = indexes
    configure_pip(python, pypi)
    env = environment(pypi)
    result = run_setup(python, ours, env, tmp_path)
    assert result.returncode == 0, (
        'Configuration files and find links cannot supply the package.',
        result.stderr,
    )
    assert installed(python, env, tmp_path) == ['ours', VERSION], (
        'Configuration files and find links cannot supply the package.'
    )


def test_the_dependency_pass_cannot_reselect_the_package(indexes, python, tmp_path):
    ours, pypi = indexes
    configure_pip(python, pypi)
    env = environment(pypi, PIP_FORCE_REINSTALL='1', PIP_IGNORE_INSTALLED='1')
    result = run_setup(python, ours, env, tmp_path)
    assert result.returncode == 0, (
        'The dependency pass cannot reselect the package.',
        result.stderr,
    )
    assert installed(python, env, tmp_path) == ['ours', VERSION], (
        'The dependency pass cannot reselect the package.'
    )


def run_in_kernel(python, env, cwd, *steps):
    """Run steps then the setup cell in one interpreter, as one notebook kernel does."""
    cell = cwd / 'setup_cell.py'
    kernel = '\n'.join([*steps, f'exec(open({str(cell)!r}).read())', ''])
    return subprocess.run(
        [python, '-c', kernel], env=env, cwd=cwd, capture_output=True, text=True, check=False
    )


def write_cell(ours, cwd):
    (cwd / 'setup_cell.py').write_text(PREPARE.setup_source('case', index=ours.as_uri()))


def our_wheel(ours):
    (path,) = (ours / 'easydiffraction').glob('*.whl')
    return (
        f'easydiffraction @ {path.as_uri()}#sha256={hashlib.sha256(path.read_bytes()).hexdigest()}'
    )


def test_an_imported_wrong_package_asks_for_a_restart_and_works_after_it(
    indexes, python, tmp_path
):
    ours, pypi = indexes
    env = environment(pypi)
    pip_install(python, env, f'easydiffraction=={VERSION}')
    write_cell(ours, tmp_path)
    result = run_in_kernel(python, env, tmp_path, 'import edi')
    assert result.returncode != 0 and 'Restart the runtime' in result.stderr
    # Setup installed what was needed, so the restarted kernel imports ours.
    assert installed(python, env, tmp_path) == ['ours', VERSION]
    after_restart = run_setup(python, ours, env, tmp_path)
    assert after_restart.returncode == 0, after_restart.stderr


def test_a_live_kernel_upgraded_underneath_still_asks_for_a_restart(indexes, python, tmp_path):
    ours, pypi = indexes
    env = environment(pypi)
    pip_install(python, env, f'easydiffraction=={VERSION}')
    write_cell(ours, tmp_path)
    pip = 'import edi, subprocess, sys\nsubprocess.check_call([sys.executable, "-m", "pip", '
    upgrade = pip + f'"install", "-q", "--no-deps", "--force-reinstall", {our_wheel(ours)!r}])'
    result = run_in_kernel(python, env, tmp_path, upgrade)
    assert result.returncode != 0 and 'Restart the runtime' in result.stderr


def test_rerunning_setup_with_our_edi_imported_asks_for_a_restart(indexes, python, tmp_path):
    ours, pypi = indexes
    env = environment(pypi)
    assert run_setup(python, ours, env, tmp_path).returncode == 0
    result = run_in_kernel(python, env, tmp_path, 'import edi')
    assert result.returncode != 0 and 'Restart the runtime' in result.stderr


def test_a_package_uninstalled_under_a_live_kernel_asks_for_a_restart(indexes, python, tmp_path):
    ours, pypi = indexes
    env = environment(pypi)
    pip_install(python, env, f'easydiffraction=={VERSION}')
    write_cell(ours, tmp_path)
    pip = 'import edi, subprocess, sys\nsubprocess.check_call([sys.executable, "-m", "pip", '
    uninstall = pip + '"uninstall", "-y", "-q", "easydiffraction"])'
    result = run_in_kernel(python, env, tmp_path, uninstall)
    assert result.returncode != 0 and 'Restart the runtime' in result.stderr


def test_an_interrupted_dependency_install_is_completed_on_the_next_run(indexes, python, tmp_path):
    ours, pypi = indexes
    env = environment(pypi)
    dependency = pypi / 'edi-test-dependency'
    hidden = tmp_path / 'hidden-dependency'
    dependency.rename(hidden)
    try:
        first = run_setup(python, ours, env, tmp_path)
    finally:
        hidden.rename(dependency)
    assert first.returncode != 0
    assert run_setup(python, ours, env, tmp_path).returncode == 0
    check = subprocess.run(
        [python, '-c', 'import edi_test_dependency'], env=env, capture_output=True, check=False
    )
    assert check.returncode == 0


def test_a_folder_named_edi_in_the_working_directory_does_not_stop_the_install(
    indexes, python, tmp_path
):
    ours, pypi = indexes
    env = environment(pypi)
    (tmp_path / 'edi').mkdir()  # a checkout or work folder: a namespace package, no metadata
    result = run_setup(python, ours, env, tmp_path)
    assert result.returncode == 0, result.stderr
    assert installed(python, env, tmp_path) == ['ours', VERSION]


def test_a_local_edi_module_that_would_shadow_the_wheel_is_refused_by_name(
    indexes, python, tmp_path
):
    ours, pypi = indexes
    env = environment(pypi)
    (tmp_path / 'edi.py').write_text("ORIGIN = 'local'\n")
    result = run_setup(python, ours, env, tmp_path)
    assert result.returncode != 0
    assert 'edi.py' in result.stderr and 'move or rename' in result.stderr


def test_a_source_build_without_the_opt_in_is_not_taken_for_one(indexes, python, tmp_path):
    _, pypi = indexes
    source = tmp_path / 'source'
    (source / 'edi').mkdir(parents=True)
    (source / 'edi/__init__.py').write_text("ORIGIN = 'source'\n")
    env = environment(pypi, PYTHONPATH=str(source))
    result = run_setup(python, tmp_path / 'missing-index', env, tmp_path)
    assert result.returncode != 0
