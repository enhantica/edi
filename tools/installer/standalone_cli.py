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
from python_wheel import build_wheel

# The operating system libraries the standalone executable may load, by exact name; anything else
# refuses the build, which is how a library missing from a user's system is caught here. Each ships
# with every supported system, so it is admitted, never bundled. On Windows WinHTTP carries the
# downloads (edi ADR-0075) and names compare case-insensitively; on Linux libdl loads the system
# libcurl only when a download needs it; on macOS the C++ runtime is the system's (the release
# rewrites its install name to /usr/lib/libc++.1.dylib) and libSystem carries the rest.
SYSTEM_LIBRARIES = {
    'linux': frozenset({
        'ld-linux-x86-64.so.2',
        'libc.so.6',
        'libm.so.6',
        'libpthread.so.0',
        'libdl.so.2',
        'librt.so.1',
    }),
    'windows': frozenset({
        'kernel32.dll',
        'advapi32.dll',
        'bcrypt.dll',
        'shell32.dll',
        'user32.dll',
        'ole32.dll',
        'ws2_32.dll',
        'ucrtbase.dll',
        'winhttp.dll',
    }),
    'macos': frozenset({'/usr/lib/libSystem.B.dylib', '/usr/lib/libc++.1.dylib'}),
}


def linux_dependencies(listing: str) -> list[str]:
    """The NEEDED entries of `readelf -d`; a NEEDED row in another shape refuses."""
    names = []
    for line in listing.splitlines():
        if '(NEEDED)' not in line:
            continue
        match = re.search(r'Shared library: \[(.+)\]\s*$', line)
        if not match:
            raise RuntimeError(f'Cannot read the dependency row {line.strip()!r}')
        names.append(match[1])
    return names


def macos_dependencies(listing: str) -> list[str]:
    """The install names `otool -L` lists after the binary's own line; another shape refuses."""
    names = []
    for line in listing.splitlines()[1:]:
        if not line.strip():
            continue
        name, marker, _ = line.strip().partition(' (compatibility version ')
        if not marker:
            raise RuntimeError(f'Cannot read the dependency row {line.strip()!r}')
        names.append(name)
    return names


def windows_dependencies(listing: str) -> list[str]:
    """Every row of every dependency section `dumpbin /dependents` prints, delay-load ones too.

    A section is its heading, then one name per line from the first row to the next blank line; the
    rows are taken whole, so a name with any character is compared, never skipped.
    """
    lines = listing.splitlines()
    names, sections = [], 0
    for index, line in enumerate(lines):
        if not re.search(r'has the following (delay load )?dependencies:\s*$', line):
            continue
        sections += 1
        started = False
        for row in lines[index + 1 :]:
            if row.strip():
                started = True
                names.append(row.strip())
            elif started:
                break
    if not sections:
        raise RuntimeError('Cannot find the dependency section in the dumpbin listing')
    return names


def verify_dependencies(binary: Path) -> None:
    """Admit only the exact operating system libraries named for this platform."""
    if SYSTEM == 'linux':
        listing = subprocess.check_output(['readelf', '-d', binary], text=True)
        libraries = linux_dependencies(listing)
        external = set(libraries) - SYSTEM_LIBRARIES['linux']
    elif SYSTEM == 'macos':
        listing = subprocess.check_output(['otool', '-L', binary], text=True)
        libraries = macos_dependencies(listing)
        external = set(libraries) - SYSTEM_LIBRARIES['macos']
    else:
        listing = subprocess.check_output(['dumpbin', '/dependents', binary], text=True)
        libraries = windows_dependencies(listing)
        external = {name for name in libraries if name.lower() not in SYSTEM_LIBRARIES['windows']}
    print(f'standalone dependencies: {sorted(libraries)}', flush=True)
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
    elif SYSTEM == 'macos':
        # The packaging toolchain records its own libc++ install name. Use the
        # OS runtime and refresh the ad hoc signature before testing the ZIP.
        run([
            '/usr/bin/install_name_tool',
            '-change',
            '@rpath/libc++.1.dylib',
            '/usr/lib/libc++.1.dylib',
            binary,
        ])
        run(['/usr/bin/codesign', '--force', '--sign', '-', binary])
    asset = work / f'EasyDiffraction-{version}-{platform}-cli.zip'
    with zipfile.ZipFile(asset, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(binary, executable)
        archive.write(source / 'LICENSE', 'LICENSE')
        for notice in sorted((source / 'licenses').iterdir()):
            archive.write(notice, 'licenses/' + notice.name)

    qualify_cli(asset, executable, version)
    build_wheel(cli, work, version, commit, platform)
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
