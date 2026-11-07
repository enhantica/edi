# SPDX-License-Identifier: BSD-3-Clause
"""Package and exercise the native Python bindings built by the release job."""

import base64
import hashlib
import json
import os
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

from package import ROOT, SYSTEM, run, sha256

TAGS = {
    'linux': 'cp312-abi3-linux_x86_64',
    'windows': 'cp312-abi3-win_amd64',
    'macos': 'cp312-abi3-macosx_14_0_arm64',
}


def write_wheel(asset: Path, extension: Path, version: str, tag: str) -> None:
    """Write the binary wheel and its hashed RECORD using the project metadata."""
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']
    metadata = f'easydiffraction-{version}.dist-info'
    package = ROOT / 'lib/edi'
    files = {f'edi/{path.name}': path.read_bytes() for path in sorted(package.glob('*.py'))}
    files[f'edi/{extension.name}'] = extension.read_bytes()
    for path in sorted((ROOT / 'data/report/vendor').iterdir()):
        if path.is_file():
            files[f'edi/data/report/vendor/{path.name}'] = path.read_bytes()
    licenses = [*project['license-files'], 'THIRD-PARTY-NOTICES']
    for path in licenses:
        files[f'{metadata}/licenses/{path}'] = (ROOT / path).read_bytes()
    files[f'{metadata}/METADATA'] = (
        f'Metadata-Version: 2.4\nName: {project["name"]}\nVersion: {version}\n'
        f'Summary: {project["description"]}\nRequires-Python: {project["requires-python"]}\n'
        f'License-Expression: {project["license"]}\n'
        + ''.join(f'License-File: {path}\n' for path in licenses)
        + '\n'
    ).encode()
    files[f'{metadata}/WHEEL'] = (
        f'Wheel-Version: 1.0\nGenerator: edi release\nRoot-Is-Purelib: false\nTag: {tag}\n'
    ).encode()
    record = f'{metadata}/RECORD'
    with zipfile.ZipFile(asset, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        rows = []
        for name, data in files.items():
            archive.writestr(name, data)
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
            rows.append(f'{name},sha256={digest},{len(data)}')
        archive.writestr(record, '\n'.join([*rows, f'{record},,', '']))


def qualify_wheel(asset: Path, version: str, commit: str) -> None:
    """Install without an index and exercise the public Python surface."""
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            'PYTHONPATH',
            'PYTHONHOME',
            'EDI_EXTENSION_DIR',
            'LD_LIBRARY_PATH',
            'DYLD_LIBRARY_PATH',
            'DYLD_FALLBACK_LIBRARY_PATH',
        }
    }
    project = ROOT / 'docs/user/cli/pd-neut-cwl_lab6-11b-echidna_basic/project'
    with tempfile.TemporaryDirectory(prefix='edi-wheel-') as folder:
        root = Path(folder)
        run([sys.executable, '-m', 'venv', root / 'env'], env=env, cwd=root)
        python = root / 'env' / ('Scripts/python.exe' if SYSTEM == 'windows' else 'bin/python')
        run([python, '-m', 'pip', 'install', '--no-index', '--no-deps', asset], env=env, cwd=root)
        run([python, '-m', 'edi', '--help'], env=env, cwd=root)
        run(
            [
                python,
                '-c',
                (
                    'import sys, edi; from importlib.metadata import version; '
                    'assert version("easydiffraction") == sys.argv[1]; '
                    'assert edi.__build_commit__ == sys.argv[2]; '
                    'p = edi.Project.load(sys.argv[3]); result = p.analysis.fit(); '
                    'assert abs(result.reduced_chi_square - 8.821296155) < 1e-6; '
                    'assert "Plotly" in p.report.as_html(offline=True)'
                ),
                version,
                commit,
                project,
            ],
            env=env,
            cwd=root,
        )


def build_wheel(cli: Path, work: Path, version: str, commit: str, platform: str) -> None:
    """Build the extension with the release SDK and qualify the shipped bytes."""
    run(['cmake', '--build', cli, '--target', '_edi', '--parallel', '4'])
    (extension,) = (cli / 'python/edi').glob('_edi.pyd' if SYSTEM == 'windows' else '_edi.abi3.so')
    if SYSTEM == 'macos':
        run([
            '/usr/bin/install_name_tool',
            '-change',
            '@rpath/libc++.1.dylib',
            '/usr/lib/libc++.1.dylib',
            extension,
        ])
        run(['/usr/bin/codesign', '--force', '--sign', '-', extension])
    tag = TAGS[SYSTEM]
    asset = work / f'easydiffraction-{version}-{tag}.whl'
    write_wheel(asset, extension, version, tag)
    qualify_wheel(asset, version, commit)
    (work / 'wheel-qualification.json').write_text(
        json.dumps({
            'version': version,
            'commit': commit,
            'platform': platform,
            'wheel': asset.name,
            'sha256': sha256(asset),
            'passed': True,
        })
        + '\n',
        encoding='utf-8',
    )
