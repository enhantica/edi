# SPDX-License-Identifier: BSD-3-Clause
"""Build and qualify the native CLI release archive."""

import json
import math
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

from native_runtime import (
    bundle_runtime,
    linux_dependencies,
    macos_dependencies,
    runtime_notices,
    verify_dependencies,
    windows_dependencies,
)
from package import ROOT, SYSTEM, run, sha256
from python_wheel import build_wheel

__all__ = (
    'linux_dependencies',
    'macos_dependencies',
    'verify_dependencies',
    'windows_dependencies',
)


def build_cli(
    prefix: Path,
    work: Path,
    common: list[str],
    version: str,
    commit: str,
    platform: str,
) -> None:
    """Build and qualify the CLI and wheel from the same SDK used by the desktop app."""
    cli = work / 'cli-build'
    flags = list(common)
    options = [
        '-DEDI_BUILD_APP=OFF',
        '-DEDI_BUILD_BINDINGS=ON',
        '-DEDI_RELEASE_WHEEL=ON',
        '-DEDI_BUILD_ASSISTANT_NATIVE=OFF',
        f'-DEDI_RELEASE_VERSION={version}',
        f'-DCMAKE_PREFIX_PATH={prefix.as_posix()}',
        '-DCMAKE_SKIP_RPATH=ON',
    ]
    if SYSTEM == 'linux':
        options.extend([
            '-DCMAKE_EXE_LINKER_FLAGS=-static-libstdc++ -static-libgcc',
            # The Python module keeps its C++ runtime private: a process that has already loaded
            # the system libstdc++ (a Jupyter kernel, through pyzmq) must not bind to it.
            '-DCMAKE_MODULE_LINKER_FLAGS=-static-libstdc++ -static-libgcc -Wl,--exclude-libs,ALL',
        ])
    if SYSTEM == 'macos':
        options.extend([
            '-DCMAKE_EXE_LINKER_FLAGS=-Wl,-headerpad_max_install_names',
            '-DCMAKE_MODULE_LINKER_FLAGS=-Wl,-headerpad_max_install_names',
        ])
    run(['cmake', '-S', ROOT, '-B', cli, *flags, *options])
    run(['cmake', '--build', cli, '--target', 'easydiffraction', '--parallel', '4'])

    source = cli / 'cli'
    suffix = '.exe' if SYSTEM == 'windows' else ''
    executable = 'edi' + suffix
    binary = source / ('easydiffraction' + suffix)
    if SYSTEM == 'linux':
        run(['strip', '--strip-unneeded', binary])
    libraries = bundle_runtime(binary, prefix)
    runtime_notices(libraries, source / 'licenses/dependencies')
    asset = work / f'EasyDiffraction-{version}-{platform}-cli.zip'
    with zipfile.ZipFile(asset, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(binary, executable)
        archive.write(source / 'LICENSE', 'LICENSE')
        runtime = binary.parent if SYSTEM == 'windows' else binary.parent / '.runtime'
        for library in sorted(runtime.iterdir()):
            if library.is_file() and (SYSTEM != 'windows' or library.suffix.lower() == '.dll'):
                archive.write(
                    library, library.name if SYSTEM == 'windows' else '.runtime/' + library.name
                )
        for notice in sorted((source / 'licenses').rglob('*')):
            if notice.is_file():
                archive.write(
                    notice, 'licenses/' + notice.relative_to(source / 'licenses').as_posix()
                )

    qualify_cli(asset, executable, version)
    build_wheel(cli, work, version, commit, platform, prefix)
    (work / 'cli-qualification.json').write_text(
        json.dumps({
            'version': version,
            'commit': commit,
            'platform': platform,
            'zip': asset.name,
            'sha256': sha256(asset),
            'passed': True,
        })
        + '\n',
        encoding='utf-8',
    )


def qualify_cli(asset: Path, executable: str, version: str) -> None:
    """Run the shipped executable from a fresh extraction directory."""
    project = ROOT / 'docs/user/cli/pd-neut-cwl_lab6-11b-echidna_basic/project'
    with tempfile.TemporaryDirectory(prefix='edi-cli-') as folder:
        with zipfile.ZipFile(asset) as archive:
            archive.extractall(folder)
        installed = Path(folder) / executable
        installed.chmod(0o755)
        verify_dependencies(installed)
        env = {
            key: value
            for key, value in os.environ.items()
            if key
            not in {
                'LD_LIBRARY_PATH',
                'DYLD_LIBRARY_PATH',
                'DYLD_FALLBACK_LIBRARY_PATH',
                'PYTHONPATH',
                'PYTHONHOME',
            }
        }
        reported = subprocess.check_output([installed, '--version'], text=True, env=env).strip()
        if reported != f'edi {version}':
            raise RuntimeError(f'Unexpected standalone CLI identity: {reported}')
        result = Path(folder) / 'refined'
        output = subprocess.check_output(
            [installed, 'fit', project, '--output', result, '--report', 'machine'],
            text=True,
            env=env,
            cwd=folder,
        )
        fields = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
        expected = json.loads((project.parent / 'expected.json').read_text(encoding='utf-8'))
        chi_square = expected['quantities']['reduced_chi_square']
        if (
            fields.get('record') != 'fit'
            or fields.get('status') != 'done'
            or not math.isclose(
                float(fields['reduced_chi_square']),
                chi_square['value'],
                rel_tol=0,
                abs_tol=chi_square['tol_abs'],
            )
            or not (result / 'project.edi').is_file()
        ):
            raise RuntimeError('The standalone CLI did not converge and save the fixture project')
