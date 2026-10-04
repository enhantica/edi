# SPDX-License-Identifier: BSD-3-Clause
"""Observe real CMake configuration through its independent File API.

No production receipt is trusted: cache, compiler inputs and Eigen's own header
macros identify what configured. The absent-system leg hides system prefixes
from CMake; disconnected FetchContent prevents a network fallback.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def configure(root, scratch, system, extra=()):
    prefix = Path(os.environ.get('CONDA_PREFIX', sys.prefix)).resolve()
    query = scratch / '.cmake/api/v1/query'
    query.mkdir(parents=True)
    (query / 'codemodel-v2').touch()
    args = [
        str(prefix / 'bin/cmake'),
        '-S',
        str(root),
        '-B',
        str(scratch),
        '-G',
        'Ninja',
        '-DCMAKE_BUILD_TYPE=Release',
        '-DFETCHCONTENT_FULLY_DISCONNECTED=ON',
    ]
    sdk = None
    if (root / 'core/CMakeLists.txt').is_file():
        sdk_name = 'crysta-prefix-app' if '-DEDI_BUILD_APP=ON' in extra else 'crysta-prefix'
        sdk = Path(os.environ.get('CRYSTA_SDK_DIR', root / 'build' / sdk_name)).resolve()
        args += ['-DCMAKE_PREFIX_PATH=' + str(sdk) + ';' + str(prefix)]
    else:
        args += ['-DCRYSTA_CXX_PACKAGE=ON', '-DCMAKE_PREFIX_PATH=' + str(prefix)]
    if system:
        args += ['-DEigen3_DIR=' + str(system_eigen(prefix, scratch))]
    if not system:
        args += ['-DCMAKE_IGNORE_PREFIX_PATH=/usr;/usr/local;/opt/homebrew;/opt/local']
    args.extend(extra)
    result = subprocess.run(
        args, env=os.environ.copy(), text=True, capture_output=True, check=False
    )
    cache = {}
    for line in (scratch / 'CMakeCache.txt').read_text().splitlines():
        match = re.match(r'([^#/:][^:]*):([^=]+)=(.*)', line)
        if match:
            cache[match[1]] = (match[2], match[3])
    paths = []
    reply = scratch / '.cmake/api/v1/reply'
    for target in reply.glob('target-*.json'):
        doc = json.loads(target.read_text())
        for group in doc.get('compileGroups', []):
            paths += [
                (doc['name'] + ':include', Path(p['path'])) for p in group.get('includes', [])
            ]
        for fragment in doc.get('link', {}).get('commandFragments', []):
            if fragment['role'] == 'libraries':
                paths += [
                    (doc['name'] + ':link', Path(p))
                    for p in shlex.split(fragment['fragment'])
                    if p.startswith('/')
                ]
    paths.extend(cache_paths(cache))
    return {
        'result': result,
        'prefix': prefix,
        'sdk': sdk,
        'scratch': scratch,
        'root': root,
        'cache': cache,
        'paths': paths,
    }


def system_eigen(prefix, scratch, *, fleet=Path('/usr/share/eigen3/cmake')):
    """Actual fleet package when present; a real external package on hosted CI."""
    if (fleet / 'Eigen3Config.cmake').is_file():
        return fleet
    external = scratch / 'external-eigen'
    shutil.copytree(prefix / 'share/eigen3', external / 'share/eigen3')
    shutil.copytree(prefix / 'include/eigen3', external / 'include/eigen3')
    return external / 'share/eigen3/cmake'


def cache_paths(cache):
    paths = []
    for key, (_kind, value) in cache.items():
        if key == 'FETCHCONTENT_BASE_DIR':
            continue  # CMake's generated source staging area, not a resolved package.
        if key.startswith('CMAKE_') and key != 'CMAKE_CXX_COMPILER':
            continue
        if key.endswith(('_SOURCE_DIR', '_BINARY_DIR')):
            continue
        if value.startswith('/') and (
            key.endswith(('_DIR', '_LIBRARY', '_EXECUTABLE', '_INCLUDE_DIR'))
            or key == 'CMAKE_CXX_COMPILER'
        ):
            paths.extend((key, Path(p)) for p in value.split(';') if p.startswith('/'))
    return paths


def escapes(observed):
    """Only project inputs and the explicitly selected engine SDK are exempt.

    Resolving symlinks closes an apparent in-prefix package redirecting outside.
    Compiler OS libraries are below the locked sysroot, on Linux; system SDK
    framework paths on macOS are platform inputs rather than third-party packages.
    """
    allowed = [observed['prefix'], observed['root'], observed['scratch']]
    if observed['sdk']:
        allowed.append(observed['sdk'])
    bad = []
    for name, path in observed['paths']:
        resolved = path.resolve()
        if (
            sys.platform == 'darwin'
            and not name.endswith('_DIR')
            and any(
                resolved.is_relative_to(base)
                for base in (
                    '/Library/Developer/CommandLineTools/SDKs',
                    '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs',
                    '/System/Library/Frameworks',
                )
            )
        ):
            continue
        bases = allowed
        if (name.endswith('_DIR') or name in observed.get('cache', {})) and name != 'crysta_DIR':
            bases = [observed['prefix']]
        if not any(resolved.is_relative_to(base) for base in bases):
            bad.append((name, str(resolved)))
    return sorted(set(bad))


def eigen_version(observed):
    includes = [p for _, p in observed['paths'] if (p / 'Eigen/src/Core/util/Macros.h').is_file()]
    assert includes, 'Locked dependency accuracy requires actual configured Eigen headers'
    versions = set()
    for include in includes:
        text = (include / 'Eigen/src/Core/util/Macros.h').read_text()
        versions.add(
            '.'.join(
                re.search(r'#define EIGEN_' + part + r'_VERSION\s+(\d+)', text)[1]
                for part in ('WORLD', 'MAJOR', 'MINOR')
            )
        )
    assert len(versions) == 1, 'One build must not mix different Eigen header versions'
    return versions.pop()


def packages(prefix):
    return {
        doc['name']: doc
        for path in (prefix / 'conda-meta').glob('*.json')
        for doc in [json.loads(path.read_text())]
    }


def fingerprint_mismatches(observed, manifest):
    installed = packages(observed['prefix'])
    claimed = {p['name']: p for p in manifest['fingerprint']['packages']}
    bad = []
    for name, package in claimed.items():
        actual = installed.get(name, {})
        if (package['version'], package['build']) != (actual.get('version'), actual.get('build')):
            bad.append(name + ': manifest differs from the resolved environment')
    if claimed.get('eigen', {}).get('version') != eigen_version(observed):
        bad.append('eigen: manifest differs from configured header macros')

    headers = {p / 'sleef.h' for _, p in observed['paths'] if (p / 'sleef.h').is_file()}
    if headers and 'sleef' in claimed:
        versions = {
            '.'.join(
                re.search(r'#define SLEEF_VERSION_' + part + r'\s+(\d+)', header.read_text())[1]
                for part in ('MAJOR', 'MINOR', 'PATCHLEVEL')
            )
            for header in headers
        }
        if versions != {claimed['sleef']['version']}:
            bad.append('sleef: manifest differs from configured header macros')
    compiler = observed['cache'].get('CMAKE_CXX_COMPILER', ('', ''))[1]
    if compiler and 'gxx_impl_linux-64' in claimed:
        version = subprocess.run(
            [compiler, '-dumpfullversion'], text=True, capture_output=True, check=True
        ).stdout.strip()
        if version != claimed['gxx_impl_linux-64']['version']:
            bad.append('gxx_impl_linux-64: manifest differs from the selected compiler')
    return bad
