"""Independent opaque native/SDK transport; no scientific build qualification is claimed."""

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

from tests.fixtures.untested_sdk.generate import clean_env, make, write_manifest

ROOT = Path(__file__).resolve().parents[2]


def git(root, *args):
    return subprocess.check_output(
        [
            'git',
            '-C',
            str(root),
            '-c',
            'user.name=Fixture',
            '-c',
            'user.email=fixture@example.invalid',
            '-c',
            'commit.gpgsign=false',
            *args,
        ],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def world(tmp_path, platform, event, *, matching_pin=True):
    prefix, root, _, _, manifest = make(tmp_path, platform)
    pin = manifest['source_sha']
    (root / 'pixi.toml').write_text('[activation.env]\nCRYSTA_COMMIT = "' + pin + '"\n')
    (root / '.gitignore').write_text('build/\n__pycache__/\n')
    (root / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.28)\n')
    for name in (
        'edi_native.py',
        'crysta_sdk.py',
        'core-build.sh',
        'build-crysta.sh',
        'crysta-src.sh',
        'producer-lock.sh',
    ):
        target = root / 'tools/ci' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'tools/ci' / name, target)
    package = root / 'lib/edi'
    package.mkdir(parents=True)
    (package / '__init__.py').write_text(
        'import importlib.util,os,sys\nfrom pathlib import Path\n'
        'p=Path(os.environ["EDI_EXTENSION_DIR"])/"_edi.py"\n'
        's=importlib.util.spec_from_file_location("edi._edi",p)\n'
        '_edi=importlib.util.module_from_spec(s);sys.modules["edi._edi"]=_edi\n'
        's.loader.exec_module(_edi)\n'
        '__build_commit__=_edi.__build_commit__\n'
    )
    git(root, 'init', '-q')
    git(root, 'add', '.')
    git(root, 'commit', '-qm', 'Record independent native transport inputs')
    head, tree = git(root, 'rev-parse', 'HEAD'), git(root, 'rev-parse', 'HEAD^{tree}')
    payloads = {
        'build/ci/.crysta-linked-sha': (pin + '\n').encode(),
        'build/ci/python/edi/_edi.py': ('__build_commit__ = ' + repr(head) + '\n').encode(),
        'build/ci/cli/easydiffraction': b'#!/bin/sh\necho "edi protocol witness"\n',
        'build/ci/core/edi_tests': b'#!/bin/sh\necho unit-protocol-witness\n',
        'build/ci/core/edi_integration_tests': b'#!/bin/sh\necho integration-protocol-witness\n',
    }
    for name, data in payloads.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(
            0o755
            if name.endswith(('easydiffraction', 'edi_tests', 'edi_integration_tests'))
            else 0o644
        )
    if not matching_pin:
        manifest['source_sha'] = 'd8' * 20
        manifest['identity'] = 'git:' + manifest['source_sha']
    write_manifest(prefix, manifest)
    destination = root / 'build/crysta-prefix'
    shutil.copytree(prefix, destination)
    (destination / '.crysta-sha').write_text(manifest['source_sha'] + '\n')
    sdk_archive(root, prefix, pin, platform)
    (root / 'build/crysta-src').mkdir()
    (root / 'build/crysta-src/CRYSTA_SOURCE_SHA').write_text(pin + '\n')
    commands = tmp_path / 'commands'
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    for name in ('cmake', 'ninja', 'c++', 'clang++', 'g++'):
        path = binaries / name
        path.write_text('#!/bin/sh\necho forbidden-compile >> "$NATIVE_COMMAND_LOG"\nexit 87\n')
        path.chmod(0o755)
    (binaries / 'python').symlink_to(sys.executable)
    env = clean_env() | {
        'PATH': str(binaries) + os.pathsep + os.environ['PATH'],
        'PIXI_PLATFORM': platform,
        'PIXI_ENVIRONMENT_NAME': 'default',
        'MACOSX_DEPLOYMENT_TARGET': '11.0' if platform == 'osx-arm64' else '',
        'GITHUB_WORKSPACE': str(root),
        'GITHUB_SHA': head,
        'GITHUB_RUN_ID': '75134',
        'GITHUB_RUN_ATTEMPT': '2',
        'GITHUB_JOB': 'native',
        'GITHUB_EVENT_NAME': event,
        'RUNNER_TEMP': str(tmp_path),
        'EDI_NATIVE_ARCHIVES': str(tmp_path / 'edi-native'),
        'EDI_CORE_BUILD_LOCK_WAIT_S': '0',
        'NATIVE_COMMAND_LOG': str(commands),
    }
    return SimpleNamespace(
        root=root,
        env=env,
        head=head,
        tree=tree,
        pin=pin,
        platform=platform,
        payloads=payloads,
        commands=commands,
    )


def run(context, *args):
    return subprocess.run(
        [sys.executable, str(context.root / 'tools/ci/edi_native.py'), *args],
        cwd=context.root,
        env=context.env,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )


def sdk_archive(root, prefix, pin, platform):
    archives = root / 'build/crysta-sdk-archives'
    archives.mkdir()
    archive = archives / f'crysta-sdk-{pin}-{platform}.tar.gz'
    with tarfile.open(archive, 'w:gz') as packed:
        for member in prefix.iterdir():
            packed.add(member, arcname=member.name)
    (Path(str(archive) + '.sha256')).write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n',
        encoding='utf-8',
    )
