# SPDX-License-Identifier: BSD-3-Clause
"""Source-build crysta before deploying the native edi application."""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from audit import audit_bundle
from package import ROOT, SYSTEM, acquire_package_licenses, payload_manifest, relocate_linux, run


def collect_notices(stage: Path, qt: Path, crysta: Path, inputs: Path) -> None:
    """Retain licences for the deployed runtime rather than the entire build toolchain."""
    notices = stage / (
        'EasyDiffraction.app/Contents/Resources/licenses/dependencies'
        if SYSTEM == 'macos'
        else 'share/doc/edi/dependencies'
    )
    notices.mkdir(parents=True, exist_ok=True)
    shutil.copy2(crysta / 'LICENSE', notices / 'crysta-LICENSE')
    records = (qt.parent if SYSTEM == 'windows' else qt) / 'conda-meta'
    if not records.is_dir():
        raise RuntimeError(
            'Packaging requires the locked dependency records for its licence inventory'
        )
    deployed_names = set()
    for path in stage.rglob('*'):
        if path.is_file() and not path.is_symlink():
            with path.open('rb') as stream:
                if stream.read(4)[:2] not in {
                    b'\x7fE',
                    b'MZ',
                    b'\xfe\xed',
                    b'\xce\xfa',
                    b'\xcf\xfa',
                    b'\xca\xfe',
                    b'\xbe\xba',
                    b'\xbf\xba',
                }:
                    continue
            deployed_names.add(path.name)
    inputs.mkdir(parents=True, exist_ok=True)
    for record in records.glob('*.json'):
        metadata = json.loads(record.read_text(encoding='utf-8'))
        if not any(Path(name).name in deployed_names for name in metadata.get('files', [])):
            continue
        licenses = Path(metadata.get('link', {}).get('source', '')) / 'info/licenses'
        if not licenses.is_dir():
            licenses = inputs / metadata['name']
            if not licenses.is_dir():
                acquire_package_licenses(metadata, inputs, licenses)
        if not any(path.is_file() for path in licenses.rglob('*')):
            raise RuntimeError(f'Missing deployed dependency licences: {metadata["name"]}')
        shutil.copytree(licenses, notices / metadata['name'])


def sign_macos_app(bundle: Path) -> None:
    """Sign owned application code without rewriting the verified upstream runtime."""
    runtime = bundle / 'Contents/libexec/edi/codex'
    signatures = {
        b'\xfe\xed\xfa\xce',
        b'\xfe\xed\xfa\xcf',
        b'\xce\xfa\xed\xfe',
        b'\xcf\xfa\xed\xfe',
        b'\xca\xfe\xba\xbe',
        b'\xbe\xba\xfe\xca',
        b'\xca\xfe\xba\xbf',
        b'\xbf\xba\xfe\xca',
    }
    paths = sorted(bundle.rglob('*'), key=lambda path: len(path.parts), reverse=True)
    for path in paths:
        if path.is_symlink() or path.is_relative_to(runtime) or not path.is_file():
            continue
        with path.open('rb') as stream:
            if stream.read(4) not in signatures:
                continue
        run(['codesign', '--force', '--sign', '-', path])
    for path in paths:
        if (
            path.is_dir()
            and not path.is_symlink()
            and not path.is_relative_to(runtime)
            and path.suffix in {'.framework', '.app', '.bundle', '.xpc'}
        ):
            run(['codesign', '--force', '--sign', '-', path])
    run(['codesign', '--force', '--sign', '-', bundle])
    run(['codesign', '--verify', '--deep', '--strict', bundle])


def verify_assistant_payload(stage: Path, expected: Path) -> None:
    """Require the exact verified runtime membership and bytes after deployment/signing."""
    root = stage / (
        'EasyDiffraction.app/Contents/libexec/edi/codex'
        if SYSTEM == 'macos'
        else 'libexec/edi/codex'
    )
    actual = payload_manifest(root)
    wanted = json.loads(expected.read_text(encoding='utf-8'))
    if set(actual) != set(wanted) or any(
        actual[name].get('sha256') != digest for name, digest in wanted.items()
    ):
        raise RuntimeError('Deployment or signing changed the verified assistant runtime')


def build(crysta: Path, work: Path, qt: Path | None, patchelf: Path | None) -> None:
    crysta, work = crysta.resolve(), work.resolve()
    if not (crysta / 'include/crysta/model.hpp').is_file():
        raise RuntimeError('The crysta source checkout is missing')
    if (work / 'stage').exists():
        raise RuntimeError('Stage already exists; choose a fresh build directory')
    if qt is None:
        value = os.environ.get('PIXI_ENVIRONMENT_PREFIX') or os.environ.get('CONDA_PREFIX')
        if not value:
            raise RuntimeError('Specify the installed Qt prefix')
        qt = Path(value)
    qt = qt.resolve()
    if SYSTEM == 'windows':
        qt /= 'Library'
    engine, prefix, app, stage = [work / name for name in ['crysta', 'prefix', 'app', 'stage']]
    common = [
        '-G',
        'Ninja',
        '-DCMAKE_BUILD_TYPE=Release',
        f'-DPython_EXECUTABLE={sys.executable}',
        '-DCMAKE_OSX_DEPLOYMENT_TARGET=' + os.environ.get('MACOSX_DEPLOYMENT_TARGET', '14.0'),
    ]
    options = ['-DCRYSTA_CXX_PACKAGE=ON', '-DCRYSTA_LTO=OFF']
    if SYSTEM == 'windows':
        common.append('-DCMAKE_CXX_FLAGS=/utf-8')
        options.extend([
            f'-DEigen3_DIR={qt.as_posix()}/share/eigen3/cmake',
            f'-DCMAKE_PREFIX_PATH={qt.as_posix()}',
        ])
    run(['cmake', '-S', crysta, '-B', engine, *common, *options])
    run(['cmake', '--build', engine, '--target', 'crysta_core', 'crysta_cli', '--parallel', '4'])
    run(['cmake', '--install', engine, '--prefix', prefix])
    options = [
        '-DEDI_BUILD_APP=ON',
        '-DEDI_BUILD_BINDINGS=OFF',
        '-DEDI_DEPLOY_APP=ON',
        f'-DCMAKE_PREFIX_PATH={prefix.as_posix()};{qt.as_posix()}',
    ]
    run(['cmake', '-S', ROOT, '-B', app, *common, *options])
    run(['cmake', '--build', app, '--target', 'edi_app', '--parallel', '4'])
    run(['cmake', '--install', app, '--component', 'desktop', '--prefix', stage])
    if SYSTEM == 'windows':
        run([
            'cmake',
            f'-DSTAGE={stage.as_posix()}',
            f'-DPREFIX={qt.parent.as_posix()}',
            '-P',
            ROOT / 'tools/installer/windows-runtime.cmake',
        ])
    if SYSTEM == 'linux':
        if not patchelf:
            found = shutil.which('patchelf')
            if not found:
                raise RuntimeError('Linux deployment requires the patchelf build tool')
            patchelf = Path(found)
        relocate_linux(stage, patchelf, qt)
    collect_notices(stage, qt, crysta, work / 'licence-inputs')
    if SYSTEM == 'macos':
        sign_macos_app(stage / 'EasyDiffraction.app')
    verify_assistant_payload(stage, app / 'app/assistant-runtime-installed.json')
    (stage / 'bundle-audit.json').write_text(
        json.dumps(audit_bundle(stage), indent=2) + '\n', encoding='utf-8'
    )
    commit = subprocess.check_output(
        ['git', '-C', str(crysta), 'rev-parse', 'HEAD'], text=True
    ).strip()
    (stage / 'build-inputs.json').write_text(
        json.dumps(
            {
                'crysta_commit': commit,
                'platform': SYSTEM,
                'architecture': platform.machine(),
                'edi_commit': subprocess.check_output(
                    ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True
                ).strip(),
            },
            indent=2,
        )
        + '\n'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crysta-source', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--qt-prefix', type=Path)
    parser.add_argument('--patchelf', type=Path)
    args = parser.parse_args()
    build(args.crysta_source, args.work, args.qt_prefix, args.patchelf)


if __name__ == '__main__':
    main()
