# SPDX-License-Identifier: BSD-3-Clause
"""Package and exercise the native Python bindings built by the release job."""

import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

from package import ROOT, SYSTEM, run, sha256
from wheel_layout import package_files

TAGS = {
    'linux': 'cp312-abi3-linux_x86_64',
    'windows': 'cp312-abi3-win_amd64',
    'macos': 'cp312-abi3-macosx_14_0_arm64',
}


def write_wheel(asset: Path, extension: Path, version: str, tag: str) -> None:
    """Write the binary wheel and its hashed RECORD using the project metadata."""
    pyproject = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    project, requires = pyproject['project'], pyproject['tool']['edi']['wheel']['dependencies']
    metadata = f'easydiffraction-{version}.dist-info'
    files = {name: path.read_bytes() for name, path in package_files().items()}
    files[f'edi/{extension.name}'] = extension.read_bytes()
    licenses = [*project['license-files'], 'THIRD-PARTY-NOTICES']
    for path in licenses:
        files[f'{metadata}/licenses/{path}'] = (ROOT / path).read_bytes()
    files[f'{metadata}/METADATA'] = (
        f'Metadata-Version: 2.4\nName: {project["name"]}\nVersion: {version}\n'
        f'Summary: {project["description"]}\nRequires-Python: {project["requires-python"]}\n'
        f'License-Expression: {project["license"]}\n'
        + ''.join(f'Requires-Dist: {requirement}\n' for requirement in requires)
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
    case = ROOT / 'docs/user/cli/pd-neut-cwl_lab6-11b-echidna_basic'
    project = case / 'project'
    # The example's own pin, so a re-pinned example cannot leave this check behind.
    pin = json.loads((case / 'expected.json').read_text(encoding='utf-8'))['quantities']
    chi2 = pin['reduced_chi_square']
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
                    'import sys; import easydiffraction as edi; '
                    'from importlib.metadata import version; '
                    'assert version("easydiffraction") == sys.argv[1]; '
                    'assert edi.__build_commit__ == sys.argv[2]; '
                    'p = edi.Project.load(sys.argv[3]); result = p.analysis.fit(); '
                    'chi2 = result.reduced_chi_square; '
                    'assert abs(chi2 - float(sys.argv[4])) <= float(sys.argv[5]); '
                    'assert "Plotly" in p.report.as_html(offline=True)'
                ),
                version,
                commit,
                project,
                str(chi2['value']),
                str(chi2['tol_abs']),
            ],
            env=env,
            cwd=root,
        )


def private_runtime(extension: Path) -> None:
    """Refuse a Linux module that exports the C++ runtime's own symbols.

    The runtime is linked in statically. Exported, its symbols bind to the system libstdc++ in a
    process that already loaded it, such as a Jupyter kernel through pyzmq, and the module crashes.
    """
    exported = subprocess.check_output(['nm', '-D', '--defined-only', extension], text=True)
    prefixes = ('_ZNSt', '_ZSt', '_ZNKSt', '__cxa_', '__gxx_')
    # Strong definitions (T, D, B, R) come from the static runtime itself; the weak template
    # instantiations (W, V, u) edi's own code emits are harmless and stay.
    entries = [line.split() for line in exported.splitlines()]
    strong = [e[-1] for e in entries if len(e) >= 2 and e[-2] in 'TDBR']
    runtime = [name for name in strong if name.startswith(prefixes)]
    if runtime:
        raise RuntimeError(f'The module exports C++ runtime symbols, e.g. {runtime[:3]}')


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
    if SYSTEM == 'linux':
        private_runtime(extension)
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
