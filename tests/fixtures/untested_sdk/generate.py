"""Independent SDK bytes, manifest fields and ABI inventory for qualification boundaries."""

import hashlib
import json
import os
from pathlib import Path

ABI = {
    'linux-64': (
        'gcc_impl_linux-64',
        'gxx_impl_linux-64',
        'libgcc',
        'libgcc-devel_linux-64',
        'libstdcxx',
        'libstdcxx-devel_linux-64',
        'libgomp',
        'sysroot_linux-64',
        'eigen',
        'sleef',
    ),
    'osx-arm64': (
        'clang_impl_osx-arm64',
        'clangxx_impl_osx-arm64',
        'libcxx',
        'libcxx-devel',
        'llvm-openmp',
        'eigen',
        'sleef',
    ),
}
PAYLOAD = {
    'lib/libcrysta_core.a': b'independent SDK library bytes\x00\x17',
    'bin/crysta': b'#!/bin/sh\nexit 0\n',
    'lib/crysta-runtime/libfixture.so': b'independent SDK runtime bytes\x00\x31',
}
MANIFEST = 'share/crysta-sdk/manifest.json'


def clean_env():
    prefixes = (
        'CRYSTA_',
        'EDI_',
        'PIXI_',
        'GITHUB_',
        'GIT_',
        'HUB_',
        'RELAY_',
        'RUNNER_',
        'ACTIONS_',
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(prefixes)
        and key not in {'CI', 'GH_TOKEN', 'MACOSX_DEPLOYMENT_TARGET'}
    }
    env['PIXI_ENVIRONMENT_NAME'] = 'default'
    return env


def make(root, platform='linux-64'):
    root = Path(root)
    prefix, repo, environment, tree = [
        root / name for name in ['prefix', 'repo', 'environment', 'tree']
    ]
    repo.mkdir(parents=True)
    for name, data in PAYLOAD.items():
        path = prefix / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        qualified = tree / (
            Path(name).name if not name.startswith('lib/crysta-runtime/') else name
        )
        qualified.parent.mkdir(parents=True, exist_ok=True)
        qualified.write_bytes(data)
    packages = [
        {'name': name, 'version': '3.4.0' if name == 'eigen' else '1.0', 'build': 'fixture_0'}
        for name in ABI[platform]
    ]
    metadata = environment / 'conda-meta'
    metadata.mkdir(parents=True)
    for package in packages:
        (metadata / (package['name'] + '.json')).write_text(json.dumps(package))
    config = prefix / 'lib/cmake/crysta'
    config.mkdir(parents=True)
    (config / 'crystaConfig.cmake').write_text('find_dependency(Eigen3 3.4.0 EXACT)\n')
    (config / 'crystaConfigVersion.cmake').write_text('set(PACKAGE_VERSION "0.0.0")\n')
    lock = 'version: 7\nplatforms:\n- name: ' + platform + '\nenvironments:\n'
    lock += '  default:\n    channels: []\n    packages:\n      ' + platform + ':\n'
    for package in packages:
        filename = '-'.join(package[key] for key in ['name', 'version', 'build']) + '.conda'
        lock += (
            '      - conda: https://conda.anaconda.org/conda-forge/'
            + platform
            + '/'
            + filename
            + '\n'
        )
    lock += 'packages: []\n'
    (repo / 'pixi.lock').write_text(lock)
    manifest = {
        'schema': 1,
        'source_sha': 'a7' * 20,
        'source_tree': '3b' * 20,
        'identity': 'git:' + 'a7' * 20,
        'platform': platform,
        'fingerprint': {
            'packages': packages,
            'macos_deployment_target': '11.0' if platform == 'osx-arm64' else None,
        },
        'tested': {
            'cpp_tier': {'passed': 7, 'total': 7},
            'corpus': {'passed': 3, 'total': 3},
            'sha256': {name: hashlib.sha256(data).hexdigest() for name, data in PAYLOAD.items()},
        },
    }
    return prefix, repo, environment, tree, manifest


def write_manifest(prefix, manifest):
    path = prefix / MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest))
    return path
