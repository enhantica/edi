# SPDX-License-Identifier: BSD-3-Clause
"""The notebook setup cell installs easydiffraction only from our index, offline.

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
    assert result.returncode == 0, result.stderr
    assert installed(python, env, tmp_path) == ['ours', VERSION]
    dependency = subprocess.run(
        [python, '-c', 'import edi_test_dependency'], env=env, capture_output=True, check=False
    )
    assert dependency.returncode == 0


def test_unreachable_index_refuses_instead_of_falling_back(indexes, python, tmp_path):
    _, pypi = indexes
    env = environment(pypi)
    result = run_setup(python, tmp_path / 'missing-index', env, tmp_path)
    assert result.returncode != 0
    assert installed(python, env, tmp_path) == []


def test_a_pip_installed_wrong_package_is_replaced(indexes, python, tmp_path):
    ours, pypi = indexes
    env = environment(pypi)
    pip_install(python, env, f'easydiffraction=={VERSION}')
    assert installed(python, env, tmp_path) == ['pypi', VERSION]
    result = run_setup(python, ours, env, tmp_path)
    assert result.returncode == 0, result.stderr
    assert installed(python, env, tmp_path) == ['ours', VERSION]


def test_a_source_build_is_kept_without_installing(indexes, python, tmp_path):
    _, pypi = indexes
    source = tmp_path / 'source'
    (source / 'edi').mkdir(parents=True)
    (source / 'edi/__init__.py').write_text("ORIGIN = 'source'\n")
    env = environment(pypi, PYTHONPATH=str(source))
    result = run_setup(python, tmp_path / 'missing-index', env, tmp_path)
    assert result.returncode == 0, result.stderr
    code = 'import edi, importlib.util as u; print(edi.ORIGIN, u.find_spec("easydiffraction"))'
    out = subprocess.run(
        [python, '-c', code], env=env, capture_output=True, text=True, check=False
    ).stdout
    assert out.split() == ['source', 'None']


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
    assert result.returncode == 0, result.stderr
    assert installed(python, env, tmp_path) == ['ours', VERSION]


def test_the_dependency_pass_cannot_reselect_the_package(indexes, python, tmp_path):
    ours, pypi = indexes
    configure_pip(python, pypi)
    env = environment(pypi, PIP_FORCE_REINSTALL='1', PIP_IGNORE_INSTALLED='1')
    result = run_setup(python, ours, env, tmp_path)
    assert result.returncode == 0, result.stderr
    assert installed(python, env, tmp_path) == ['ours', VERSION]


def test_an_imported_wrong_package_refuses_until_the_kernel_restarts(indexes, python, tmp_path):
    ours, pypi = indexes
    env = environment(pypi)
    pip_install(python, env, f'easydiffraction=={VERSION}')
    cell = tmp_path / 'setup_cell.py'
    cell.write_text(PREPARE.setup_source('case', index=ours.as_uri()))
    kernel = f'import edi\nexec(open({str(cell)!r}).read())\n'
    result = subprocess.run(
        [python, '-c', kernel], env=env, cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert result.returncode != 0
    assert 'Restart the kernel' in result.stderr
    assert installed(python, env, tmp_path) == ['pypi', VERSION]
    assert run_setup(python, ours, env, tmp_path).returncode == 0
    rerun = subprocess.run(
        [python, '-c', kernel], env=env, cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert rerun.returncode == 0, rerun.stderr
    assert installed(python, env, tmp_path) == ['ours', VERSION]
