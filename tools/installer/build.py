# SPDX-License-Identifier: BSD-3-Clause
"""Source-build crysta before deploying the native edi application."""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

import jinja2
import py7zr
import yaml
from package import ROOT, SYSTEM, relocate_linux, run, sha256


def download(url: str, digest: str, path: Path) -> None:
    if not url.startswith(('https://download.qt.io/', 'https://github.com/openai/codex/')):
        raise RuntimeError('Build input must use its pinned official HTTPS source')
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file() or sha256(path) != digest:
        with (
            urllib.request.urlopen(url, timeout=30) as response,  # noqa: S310
            path.open('wb') as stream,
        ):
            shutil.copyfileobj(response, stream)
    if sha256(path) != digest:
        raise RuntimeError(f'Build input checksum differs: {path.name}')


def windows_inputs(work: Path) -> tuple[Path, Path]:
    kit = json.loads((ROOT / 'tools/installer/windows-qt.json').read_text())
    sdk = work / 'qt'
    for index, archive in enumerate(kit['archives']):
        path = work / 'downloads' / f'qt-{index}.7z'
        download(archive['url'], archive['sha256'], path)
        with py7zr.SevenZipFile(path) as compressed:
            compressed.extractall(sdk)  # noqa: S202 - checksum-pinned 7z, not tarfile
    qt = sdk
    (qt / 'bin/qt.conf').write_text('[Paths]\nPrefix=..\n')
    recipe = yaml.safe_load((ROOT / 'tools/deps/assistant-runtime/recipe.yaml').read_text())
    template = jinja2.Environment(
        variable_start_string='${{',
        variable_end_string='}}',
        undefined=jinja2.StrictUndefined,
        autoescape=False,  # noqa: S701 - recipe expressions, not HTML
    )
    context = {'target_platform': 'win-64'}
    for name, value in recipe['context'].items():
        context[name] = template.from_string(str(value)).render(context)
    source = recipe['source'][0]
    url = template.from_string(source['url']).render(context)
    digest = template.from_string(source['sha256']).render(context)
    archive = work / 'downloads/assistant.tar.gz'
    download(url, digest, archive)
    unpacked = work / 'upstream-runtime'
    unpacked.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as compressed:
        compressed.extractall(unpacked, filter='data')
    manifests = list(unpacked.rglob('codex-package.json'))
    if len(manifests) != 1:
        raise RuntimeError('Official assistant archive has no unique package root')
    runtime = work / 'runtime-prefix'
    run([
        sys.executable,
        ROOT / 'tools/deps/assistant-runtime/install.py',
        '--source',
        manifests[0].parent,
        '--licenses',
        ROOT / 'data/assistant/runtime',
        '--prefix',
        runtime,
        '--target',
        context['target'],
        '--archive-sha256',
        digest,
    ])
    return qt, runtime


def collect_notices(stage: Path, qt: Path, crysta: Path) -> None:
    notices = stage / (
        'EasyDiffraction.app/Contents/Resources/licenses/dependencies'
        if SYSTEM == 'macos'
        else 'share/doc/edi/dependencies'
    )
    notices.mkdir(parents=True, exist_ok=True)
    shutil.copy2(crysta / 'LICENSE', notices / 'crysta-LICENSE')
    records = qt / 'conda-meta'
    if records.is_dir():
        for record in records.glob('*.json'):
            metadata = json.loads(record.read_text())
            cached = Path(metadata.get('link', {}).get('source', '')) / 'info/licenses'
            if cached.is_dir():
                shutil.copytree(cached, notices / metadata['name'], dirs_exist_ok=True)
    else:
        for folder in qt.rglob('LICENSES'):
            if folder.is_dir():
                shutil.copytree(folder, notices / folder.relative_to(qt), dirs_exist_ok=True)


def build(crysta: Path, work: Path, qt: Path | None, patchelf: Path | None) -> None:
    crysta, work = crysta.resolve(), work.resolve()
    if not (crysta / 'include/crysta/model.hpp').is_file():
        raise RuntimeError('The crysta source checkout is missing')
    if (work / 'stage').exists():
        raise RuntimeError('Stage already exists; choose a fresh build directory')
    runtime = None
    if SYSTEM == 'windows':
        qt, runtime = windows_inputs(work)
    if qt is None:
        value = os.environ.get('PIXI_ENVIRONMENT_PREFIX') or os.environ.get('CONDA_PREFIX')
        if not value:
            raise RuntimeError('Specify the installed Qt prefix')
        qt = Path(value)
    qt = qt.resolve()
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
            '-DCRYSTA_EIGEN_FETCH=ON',
            '-DBUILD_TESTING=OFF',
            '-DEIGEN_BUILD_TESTING=OFF',
            '-DEIGEN_BUILD_DOC=OFF',
        ])
    run(['cmake', '-S', crysta, '-B', engine, *common, *options])
    run(['cmake', '--build', engine, '--target', 'crysta_core', 'crysta_cli', '--parallel', '4'])
    run(['cmake', '--install', engine, '--prefix', prefix])
    options = [
        '-DEDI_BUILD_APP=ON',
        '-DEDI_BUILD_BINDINGS=OFF',
        '-DEDI_DEPLOY_APP=ON',
        f'-DCMAKE_PREFIX_PATH={prefix};{qt}',
    ]
    if runtime:
        options.append(f'-DEDI_ASSISTANT_RUNTIME_PREFIX={runtime}')
    run(['cmake', '-S', ROOT, '-B', app, *common, *options])
    run(['cmake', '--build', app, '--target', 'edi_app', '--parallel', '4'])
    run(['cmake', '--install', app, '--component', 'desktop', '--prefix', stage])
    if SYSTEM == 'linux':
        if not patchelf:
            raise RuntimeError('Linux deployment requires the patchelf build tool')
        relocate_linux(stage, patchelf, qt)
    collect_notices(stage, qt, crysta)
    if SYSTEM == 'macos':
        run(['codesign', '--force', '--deep', '--sign', '-', stage / 'EasyDiffraction.app'])
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
