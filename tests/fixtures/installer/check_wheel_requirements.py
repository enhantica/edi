# SPDX-License-Identifier: BSD-3-Clause
"""The release wheel declares what the installed package needs at run time.

The binding returns NumPy arrays, so a wheel installed into a fresh environment (a notebook's
setup cell installs the wheel's declared requirements) must bring NumPy with it.
"""

import email.parser
import os
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/installer'))
import python_wheel  # noqa: E402


def test_the_wheel_metadata_requires_every_declared_runtime_dependency(tmp_path):
    extension = tmp_path / '_edi.abi3.so'
    extension.write_bytes(b'stand-in for the built module')
    asset = tmp_path / 'easydiffraction-2026.11.99-cp312-abi3-linux_x86_64.whl'
    python_wheel.write_wheel(asset, extension, '2026.11.99', 'cp312-abi3-linux_x86_64')
    with zipfile.ZipFile(asset) as archive:
        metadata = archive.read('easydiffraction-2026.11.99.dist-info/METADATA').decode()
    required = email.parser.Parser().parsestr(metadata).get_all('Requires-Dist') or []
    declared = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['tool']['edi'][
        'wheel'
    ]['dependencies']
    assert required == declared, 'The wheel declares exactly the runtime dependencies listed.'
    assert any(item.split('>')[0].strip() == 'numpy' for item in required), (
        'NumPy is declared: the package returns NumPy arrays.'
    )


def stand_in_numpy(folder: Path) -> None:
    """A tiny wheel named numpy, so the install resolves offline from a local folder."""
    dist = 'numpy-99.0.0.dist-info'
    files = {
        'numpy/__init__.py': b'STAND_IN = True\n',
        f'{dist}/METADATA': b'Metadata-Version: 2.1\nName: numpy\nVersion: 99.0.0\n',
        f'{dist}/WHEEL': b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
    }
    with zipfile.ZipFile(folder / 'numpy-99.0.0-py3-none-any.whl', 'w') as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr(
            f'{dist}/RECORD', ''.join(f'{name},,\n' for name in [*files, f'{dist}/RECORD'])
        )


def test_a_fresh_environment_installing_the_wheel_gets_numpy(tmp_path):
    extension = tmp_path / '_edi.abi3.so'
    extension.write_bytes(b'stand-in for the built module')
    links = tmp_path / 'links'
    links.mkdir()
    tag = python_wheel.TAGS[python_wheel.SYSTEM]
    asset = links / f'easydiffraction-2026.11.99-{tag}.whl'
    python_wheel.write_wheel(asset, extension, '2026.11.99', tag)
    stand_in_numpy(links)
    subprocess.run([sys.executable, '-m', 'venv', tmp_path / 'env'], check=True)
    bin_dir = tmp_path / 'env' / ('Scripts' if os.name == 'nt' else 'bin')
    python = bin_dir / ('python.exe' if os.name == 'nt' else 'python')
    environment = {k: v for k, v in os.environ.items() if not k.startswith('PIP_')}
    subprocess.run(
        [python, '-m', 'pip', 'install', '-q', '--no-index', '--find-links', links, asset],
        check=True,
        env=environment,
    )
    shown = subprocess.run(
        [python, '-c', 'import numpy; print(numpy.STAND_IN)'],
        capture_output=True,
        text=True,
        check=True,
    )
    assert shown.stdout.strip() == 'True', (
        'Installing the wheel brings NumPy into a fresh environment.'
    )
