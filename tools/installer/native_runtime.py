# SPDX-License-Identifier: BSD-3-Clause
"""Relocate the qualified native SDK runtime for CLI and wheel packages."""

import json
import os
import re
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path

from package import SYSTEM, collect_dependency_licenses, run, sha256

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
        'oleaut32.dll',
        'ntdll.dll',
    }),
    'macos': frozenset({'/usr/lib/libSystem.B.dylib', '/usr/lib/libc++.1.dylib'}),
}

SYSTEM_LIBRARIES['windows'] |= frozenset({
    'api-ms-win-crt-conio-l1-1-0.dll',
    'api-ms-win-crt-convert-l1-1-0.dll',
    'api-ms-win-crt-environment-l1-1-0.dll',
    'api-ms-win-crt-filesystem-l1-1-0.dll',
    'api-ms-win-crt-heap-l1-1-0.dll',
    'api-ms-win-crt-locale-l1-1-0.dll',
    'api-ms-win-crt-math-l1-1-0.dll',
    'api-ms-win-crt-multibyte-l1-1-0.dll',
    'api-ms-win-crt-private-l1-1-0.dll',
    'api-ms-win-crt-process-l1-1-0.dll',
    'api-ms-win-crt-runtime-l1-1-0.dll',
    'api-ms-win-crt-stdio-l1-1-0.dll',
    'api-ms-win-crt-string-l1-1-0.dll',
    'api-ms-win-crt-time-l1-1-0.dll',
    'api-ms-win-crt-utility-l1-1-0.dll',
})


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


def dependencies(binary: Path) -> list[str]:
    """Read every dynamic dependency with the platform's actual image inspector."""
    if SYSTEM == 'linux':
        return linux_dependencies(subprocess.check_output(['readelf', '-d', binary], text=True))
    if SYSTEM == 'macos':
        return macos_dependencies(subprocess.check_output(['otool', '-L', binary], text=True))
    listing = subprocess.check_output(
        ['dumpbin', '/dependents', binary], text=True, env={**os.environ, 'VSLANG': '1033'}
    )
    return windows_dependencies(listing)


def system_library(name: str, *, python_module: bool = False) -> bool:
    """Only platform libraries may be loaded without a bundled SDK file."""
    if SYSTEM == 'windows':
        key = name.lower()
        if python_module and key == 'python3.dll':
            return True
        return key in SYSTEM_LIBRARIES[SYSTEM]
    return name in SYSTEM_LIBRARIES[SYSTEM]


def runtime_directory(binary: Path) -> Path:
    return binary.parent if SYSTEM == 'windows' else binary.parent / '.runtime'


def runtime_key(name: str) -> str:
    return Path(name).name.lower() if SYSTEM == 'windows' else Path(name).name


def sdk_runtime(prefix: Path) -> dict[str, tuple[Path, str]]:
    """Index only flat runtime files whose bytes the SDK manifest qualified."""
    manifest = json.loads((prefix / 'share/crysta-sdk/manifest.json').read_text())
    result = {}
    for name, digest in manifest['tested']['sha256'].items():
        root = 'bin/' if SYSTEM == 'windows' else 'lib/crysta-runtime/'
        if not name.startswith(root) or (
            SYSTEM == 'windows' and not name.lower().endswith('.dll')
        ):
            continue
        leaf = name.removeprefix(root)
        if not re.fullmatch(r'[A-Za-z0-9_.+-]+', leaf):
            raise RuntimeError(f'Unsafe SDK runtime path: {name!r}')
        key = runtime_key(leaf)
        if key in result or sha256(prefix / name) != digest:
            raise RuntimeError(f'SDK runtime is ambiguous or differs from qualified bytes: {name}')
        result[key] = (prefix / name, digest)
    if not result:
        raise RuntimeError('The SDK has no qualified runtime files')
    return result


def runtime_notices(libraries: list[Path], notices: Path) -> Path:
    """Use the same actual-package notice inventory as desktop deployment."""
    prefix = Path(os.environ.get('CONDA_PREFIX') or sys.prefix)
    files = [Path('Library/bin' if SYSTEM == 'windows' else 'lib') / p.name for p in libraries]
    collect_dependency_licenses(
        files,
        prefix / 'conda-meta',
        notices,
        notices.parent / 'runtime-licence-inputs',
        require_owned=True,
    )
    return notices


def relocate(binary: Path, libraries: list[Path]) -> None:
    """Make every packaged image load only its adjacent SDK runtime or system libraries."""
    if SYSTEM == 'linux':
        for image in [binary, *libraries]:
            run([
                'patchelf',
                '--set-rpath',
                '$ORIGIN/.runtime' if image == binary else '$ORIGIN',
                image,
            ])
    elif SYSTEM == 'macos':
        names = {p.name for p in libraries}
        for image in [*libraries, binary]:
            for name in dependencies(image):
                leaf = Path(name).name
                if leaf in names:
                    replacement = '@loader_path/' + ('.runtime/' if image == binary else '') + leaf
                    run(['/usr/bin/install_name_tool', '-change', name, replacement, image])
            run(['/usr/bin/codesign', '--force', '--sign', '-', image])


def bundle_runtime(binary: Path, prefix: Path) -> list[Path]:
    """Copy the required SDK dependency closure, never rebuilding the engine."""
    available = sdk_runtime(prefix)
    destination = runtime_directory(binary)
    destination.mkdir(exist_ok=True)
    queue, copied = deque([binary]), {}
    while queue:
        image = queue.popleft()
        for name in dependencies(image):
            key = runtime_key(name)
            if key in copied:
                continue
            if key not in available:
                if not system_library(name, python_module=image.suffix == '.pyd'):
                    raise RuntimeError(f'No qualified SDK runtime for {name!r}')
                continue
            source, digest = available[key]
            target = destination / source.name
            shutil.copy2(source, target)
            if sha256(target) != digest:
                raise RuntimeError(f'The copied SDK runtime changed: {source.name}')
            copied[key] = target
            queue.append(target)
    libraries = list(copied.values())
    relocate(binary, libraries)
    verify_dependencies(binary)
    return libraries


def verify_dependencies(binary: Path) -> None:
    """Prove the extracted artifact's entire non-system dependency closure is present."""
    directory = runtime_directory(binary)
    available = {
        runtime_key(p.name): p
        for p in directory.glob('*')
        if p.is_file() and (SYSTEM != 'windows' or p.suffix.lower() == '.dll')
    }
    queue, visited = deque([binary]), set()
    while queue:
        image = queue.popleft()
        names = dependencies(image)
        if image == binary and not names:
            raise RuntimeError('The packaged binary has no inspectable dynamic dependencies')
        for name in names:
            key = runtime_key(name)
            if key not in available:
                if not system_library(name, python_module=image.suffix == '.pyd'):
                    raise RuntimeError(f'Unbundled native dependency: {name!r}')
                continue
            expected = (
                key
                if SYSTEM != 'macos'
                else '@loader_path/'
                + ('.runtime/' if image == binary else '')
                + available[key].name
            )
            if (name.lower() if SYSTEM == 'windows' else name) != expected:
                raise RuntimeError(
                    f'Native dependency searches outside its packaged runtime: {name!r}'
                )
            if key not in visited:
                visited.add(key)
                queue.append(available[key])
    print(f'qualified native runtime: {sorted(visited)}', flush=True)
