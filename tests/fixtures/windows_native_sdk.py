"""Independently authored Windows SDK protocol bytes and installer lock identities."""

import hashlib
import json
from pathlib import Path

PACKAGES = [
    {'name': 'vs2022_win-64', 'version': '19.44.35217', 'build': 'fixture_0'},
    {'name': 'vc14_runtime', 'version': '14.44.35208', 'build': 'fixture_0'},
    {'name': 'vcomp14', 'version': '14.44.35208', 'build': 'fixture_0'},
    {'name': 'eigen', 'version': '3.4.0', 'build': 'fixture_0'},
]
MANIFEST = 'share/crysta-sdk/manifest.json'
PAYLOADS = {
    'lib/crysta_core.lib': b'independent qualified Windows library protocol bytes',
    'bin/crysta.exe': b'MZindependent Windows CLI protocol bytes',
    'bin/VCOMP140.DLL': b'MZindependent OpenMP protocol bytes',
    'bin/MSVCP140.dll': b'MZindependent C++ runtime protocol bytes',
}


def make(root):
    root = Path(root)
    prefix, repo = root / 'sdk', root / 'repo'
    repo.mkdir(parents=True)
    for name, data in PAYLOADS.items():
        path = prefix / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    manifest = {
        'schema': 1,
        'source_sha': 'a7' * 20,
        'source_tree': '3b' * 20,
        'identity': 'git:' + 'a7' * 20,
        'platform': 'win-64',
        'fingerprint': {
            'packages': [dict(p) for p in PACKAGES],
            'macos_deployment_target': None,
            'compiler': {
                'id': 'MSVC',
                'version': '19.44.35221.0',
                'architecture': 'x64',
                'runtime': 'MultiThreadedDLL',
            },
        },
        'tested': {
            'cpp_tier': {'passed': 7, 'total': 7},
            'corpus': {'passed': 3, 'total': 3},
            'sha256': {name: hashlib.sha256(data).hexdigest() for name, data in PAYLOADS.items()},
        },
    }
    lock = 'version: 7\nplatforms:\n- name: win-64\nenvironments:\n'
    for environment in ('default', 'installer'):
        lock += f'  {environment}:\n    channels: []\n    packages:\n      win-64:\n'
        for package in PACKAGES:
            version = package['version'] if environment == 'installer' else '0.0.0'
            name = package['name'] + '-' + version + '-' + package['build'] + '.conda'
            lock += '      - conda: https://conda.anaconda.org/conda-forge/win-64/' + name + '\n'
    lock += 'packages: []\n'
    (repo / 'installer.lock').write_text(lock, encoding='utf-8')
    (repo / 'pixi.lock').write_text(lock.replace('fixture_0', 'wrong_build'), encoding='utf-8')
    (repo / 'pixi.toml').write_text(
        '[activation.env]\nCRYSTA_COMMIT="' + 'a7' * 20 + '"\n', encoding='utf-8'
    )
    write_manifest(prefix, manifest)
    return prefix, repo, manifest


def write_manifest(prefix, manifest):
    path = prefix / MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest), encoding='utf-8')
