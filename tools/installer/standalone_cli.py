# SPDX-License-Identifier: BSD-3-Clause
"""Build and qualify a single-executable CLI release asset."""

import json
import math
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

from package import ROOT, SYSTEM, run, sha256


def verify_dependencies(binary: Path) -> None:
    """Allow platform libraries only, even on a runner with build dependencies installed."""
    if SYSTEM == 'linux':
        output = subprocess.check_output(['readelf', '-d', binary], text=True)
        libraries = re.findall(r'\(NEEDED\).*?\[([^\]]+)\]', output)
        allowed = {'libc.so.6', 'libm.so.6', 'libpthread.so.0', 'libdl.so.2', 'librt.so.1'}
        external = set(libraries) - allowed
    elif SYSTEM == 'macos':
        output = subprocess.check_output(['otool', '-L', binary], text=True)
        libraries = [
            line.split(' (compatibility version', 1)[0].strip()
            for line in output.splitlines()[1:]
            if line.strip()
        ]
        external = {
            name for name in libraries if not name.startswith(('/usr/lib/', '/System/Library/'))
        }
    else:
        output = subprocess.check_output(['dumpbin', '/dependents', binary], text=True)
        libraries = re.findall(r'^\s+([\w.-]+\.dll)\s*$', output.lower(), re.MULTILINE)
        allowed = {
            'kernel32.dll',
            'advapi32.dll',
            'bcrypt.dll',
            'shell32.dll',
            'user32.dll',
            'ole32.dll',
            'ws2_32.dll',
            'ucrtbase.dll',
        }
        external = {
            name
            for name in libraries
            if name not in allowed and not name.startswith('api-ms-win-')
        }
    if not libraries or external:
        raise RuntimeError(f'Cannot qualify standalone dependencies: {sorted(external)}')


def build_cli(
    crysta: Path,
    work: Path,
    common: list[str],
    engine_options: list[str],
    version: str,
    commit: str,
    platform: str,
) -> None:
    """Build a lean SDK and test the exact executable carried in the ZIP."""
    engine, prefix, cli = (work / name for name in ('cli-engine', 'cli-prefix', 'cli-build'))
    flags = list(common)
    if SYSTEM == 'windows':
        flags.append('-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded')
    run([
        'cmake',
        '-S',
        crysta,
        '-B',
        engine,
        *flags,
        *engine_options,
        '-DCRYSTA_OPENMP=OFF',
        '-DCRYSTA_STD_THREADS=ON',
        '-DCRYSTA_SLEEF=OFF',
    ])
    run(['cmake', '--build', engine, '--target', 'crysta_core', 'crysta_cli', '--parallel', '4'])
    run(['cmake', '--install', engine, '--prefix', prefix])
    options = [
        '-DEDI_BUILD_APP=OFF',
        '-DEDI_BUILD_BINDINGS=OFF',
        '-DEDI_BUILD_ASSISTANT_NATIVE=OFF',
        f'-DEDI_RELEASE_VERSION={version}',
        f'-DCMAKE_PREFIX_PATH={prefix.as_posix()}',
        '-DCMAKE_SKIP_RPATH=ON',
    ]
    if SYSTEM == 'linux':
        options.append('-DCMAKE_EXE_LINKER_FLAGS=-static-libstdc++ -static-libgcc')
    run(['cmake', '-S', ROOT, '-B', cli, *flags, *options])
    run(['cmake', '--build', cli, '--target', 'easydiffraction', '--parallel', '4'])

    source = cli / 'cli'
    suffix = '.exe' if SYSTEM == 'windows' else ''
    executable = 'edi' + suffix
    binary = source / ('easydiffraction' + suffix)
    if SYSTEM == 'linux':
        run(['strip', '--strip-unneeded', binary])
    asset = work / f'EasyDiffraction-{version}-{platform}-cli.zip'
    with zipfile.ZipFile(asset, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(binary, executable)
        archive.write(source / 'LICENSE', 'LICENSE')
        for notice in sorted((source / 'licenses').iterdir()):
            archive.write(notice, 'licenses/' + notice.name)

    qualify_cli(asset, executable, version)
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
