# SPDX-License-Identifier: BSD-3-Clause
"""Build, package and exercise native offline installers (ADR-0071)."""

import argparse
import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import urllib.request
import xml.etree.ElementTree as ET  # noqa: S405 - generated XML only, never external XML
import zipfile
from pathlib import Path

import py7zr

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = {'Linux': 'linux', 'Darwin': 'macos', 'Windows': 'windows'}[platform.system()]
SUFFIX = '.exe' if SYSTEM == 'windows' else ''


def run(args, **kwargs: object) -> None:
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch_tools(destination: Path) -> Path:
    pin = json.loads((ROOT / 'tools/installer/ifw.json').read_text())['platforms'][SYSTEM]
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / 'ifw.7z'
    if not archive.exists() or sha256(archive) != pin['sha256']:
        if not pin['url'].startswith('https://download.qt.io/'):
            raise RuntimeError('Installer tools must come from the official HTTPS feed')
        with (
            urllib.request.urlopen(pin['url'], timeout=30) as response,  # noqa: S310
            archive.open('wb') as stream,
        ):
            shutil.copyfileobj(response, stream)
    if sha256(archive) != pin['sha256']:
        raise RuntimeError('Installer Framework archive checksum differs')
    tools = destination / 'tools'
    if tools.exists():
        shutil.rmtree(tools)
    with py7zr.SevenZipFile(archive) as package:
        for name in package.getnames():
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise RuntimeError('Installer Framework archive escapes its tool directory')
        package.extractall(tools)
    creator = tools / ('bin/binarycreator' + SUFFIX)
    if not creator.is_file():
        raise RuntimeError('Installer Framework has no binarycreator')
    return tools


def xml_file(path, root_name, values) -> ET.ElementTree:
    root = ET.Element(root_name)
    for name, value in values.items():
        ET.SubElement(root, name).text = str(value)
    ET.indent(root)
    tree = ET.ElementTree(root)
    tree.write(path, encoding='utf-8', xml_declaration=True)
    return tree


def payload_manifest(stage: Path) -> dict:
    result = {}
    for path in sorted(stage.rglob('*')):
        relative = path.relative_to(stage).as_posix()
        if path.is_symlink():
            if (
                path.readlink().is_absolute()
                or not path.resolve().is_relative_to(stage.resolve())
                or not path.exists()
            ):
                raise RuntimeError(f'Payload link escapes or is broken: {relative}')
            result[relative] = {'link': str(path.readlink())}
        elif path.is_file():
            result[relative] = {'sha256': sha256(path), 'bytes': path.stat().st_size}
        elif not path.is_dir():
            raise RuntimeError(f'Payload contains a special file: {relative}')
    if not result:
        raise RuntimeError('Application stage is empty')
    return result


def package_app(stage: Path, tools: Path, output: Path, version: str) -> Path:
    stage, tools, output = stage.resolve(), tools.resolve(), output.resolve()
    executable = stage / (
        'EasyDiffraction.app/Contents/MacOS/EasyDiffraction'
        if SYSTEM == 'macos'
        else 'bin/edi_app' + SUFFIX
    )
    if not executable.is_file():
        raise RuntimeError('Stage does not contain the native application')
    if output.is_relative_to(stage):
        raise RuntimeError('Installer output must be outside the application stage')
    manifest = payload_manifest(stage)
    output.mkdir(parents=True, exist_ok=True)
    source = output / 'source'
    if source.exists():
        raise RuntimeError('Installer source already exists; choose a fresh output directory')
    config = source / 'config'
    meta = source / 'packages/org.easyscience.edi/meta'
    data = meta.parent / 'data'
    config.mkdir(parents=True)
    meta.mkdir(parents=True)
    shutil.copytree(stage, data, symlinks=True)
    (data / 'payload-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    shutil.copy2(ROOT / 'LICENSE', meta / 'LICENSE')
    xml_file(
        config / 'config.xml',
        'Installer',
        {
            'Name': 'EasyDiffraction',
            'Version': version,
            'Title': 'EasyDiffraction installer',
            'Publisher': 'EasyScience',
            'ProductUrl': 'https://enhantica.github.io/edi/',
            'TargetDir': '@HomeDir@/Applications/EasyDiffraction'
            if SYSTEM == 'macos'
            else '@HomeDir@/EasyDiffraction',
            'MaintenanceToolName': 'MaintenanceTool',
            'AllowNonAsciiCharacters': 'true',
            'AllowSpaceInPath': 'true',
            'WizardStyle': 'Modern',
        },
    )
    root = xml_file(
        meta / 'package.xml',
        'Package',
        {
            'DisplayName': 'EasyDiffraction',
            'Description': 'Diffraction analysis with crysta, Qt and the assistant runtime.',
            'Version': version,
            'ReleaseDate': datetime.datetime.now(datetime.UTC).date().isoformat(),
            'Default': 'true',
            'ForcedInstallation': 'true',
            'RequiresAdminRights': 'false',
        },
    )
    licenses = ET.SubElement(root.getroot(), 'Licenses')
    ET.SubElement(licenses, 'License', {'name': 'EasyDiffraction licence', 'file': 'LICENSE'})
    ET.indent(root)
    root.write(meta / 'package.xml', encoding='utf-8', xml_declaration=True)
    name = f'EasyDiffraction-{version}-{SYSTEM}-{platform.machine()}'
    installer = output / (
        name + ('.app' if SYSTEM == 'macos' else '.exe' if SYSTEM == 'windows' else '.run')
    )
    run([
        tools / ('bin/binarycreator' + SUFFIX),
        '--verbose',
        '--compression',
        '1',
        '--offline-only',
        '-c',
        config / 'config.xml',
        '-p',
        source / 'packages',
        installer,
    ])
    archive = output / (name + '.zip')
    if SYSTEM == 'macos':
        run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', installer, archive])
    else:
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
            zipped.write(installer, installer.name)
    (output / 'installer.json').write_text(
        json.dumps(
            {
                'installer': installer.name,
                'zip': archive.name,
                'zip_sha256': sha256(archive),
                'ifw': '4.11.0',
                'platform': SYSTEM,
                'version': version,
            },
            indent=2,
        )
        + '\n'
    )
    return installer


def clean_environment(home: Path) -> dict:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(('CONDA', 'PIXI', 'QT_', 'QML', 'EDI_', 'LD_', 'DYLD_', 'PYTHON'))
    }
    if SYSTEM == 'windows':
        system = Path(env['SystemRoot'])
        env['PATH'] = str(system / 'System32') + os.pathsep + str(system)
    else:
        env['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'
    env.update(
        HOME=str(home),
        USERPROFILE=str(home),
        XDG_CONFIG_HOME=str(home / 'config'),
        XDG_DATA_HOME=str(home / 'data'),
        XDG_CACHE_HOME=str(home / 'cache'),
        CODEX_HOME=str(home / 'codex'),
        APPDATA=str(home / 'appdata/roaming'),
        LOCALAPPDATA=str(home / 'appdata/local'),
        QML_DISABLE_DISK_CACHE='1',
    )
    if SYSTEM == 'linux':
        env.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
    return env


def check_linux_dependencies(root: Path, env: dict) -> dict:
    receipts = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open('rb') as stream:
            if stream.read(4) != b'\x7fELF':
                continue
        result = subprocess.run(
            ['/usr/bin/ldd', str(path)], env=env, capture_output=True, text=True, check=False
        )
        text = result.stdout + result.stderr
        if result.returncode and (
            'not a dynamic executable' in text or 'statically linked' in text
        ):
            continue
        if result.returncode or 'not found' in text:
            raise RuntimeError(f'Unresolved installed dependency: {path}\n{text}')
        for line in text.splitlines():
            if '=> /' in line:
                resolved = Path(line.split('=>', 1)[1].strip().split(' (', 1)[0])
                if not resolved.is_relative_to(root) and not any(
                    resolved.is_relative_to(Path(prefix))
                    for prefix in ['/usr/lib', '/lib', '/lib64']
                ):
                    raise RuntimeError(f'Installed dependency escapes the package: {line}')
        receipts[path.relative_to(root).as_posix()] = text
    return receipts


def test_installer(installer: Path, output: Path) -> None:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    home, target = output / 'isolated home', output / 'installed app'
    home.mkdir(exist_ok=True)
    if target.exists():
        raise RuntimeError('Installation target already exists; choose a fresh test directory')
    env = clean_environment(home)
    command = installer.resolve()
    if SYSTEM == 'macos':
        command = next((command / 'Contents/MacOS').iterdir())
    with (output / 'install.log').open('w') as log:
        run(
            [
                command,
                '--root',
                target,
                '--accept-licenses',
                '--default-answer',
                '--confirm-command',
                'install',
            ],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
    app = target / (
        'EasyDiffraction.app/Contents/MacOS/EasyDiffraction'
        if SYSTEM == 'macos'
        else 'bin/edi_app' + SUFFIX
    )
    try:
        manifest = json.loads((target / 'payload-manifest.json').read_text())
        for name, expected in manifest.items():
            path = target / name
            if 'sha256' in expected and (not path.is_file() or sha256(path) != expected['sha256']):
                raise RuntimeError(f'Installed bytes differ: {name}')
            if 'link' in expected and (
                not path.is_symlink() or str(path.readlink()) != expected['link']
            ):
                raise RuntimeError(f'Installed link differs: {name}')
        app = target / (
            'EasyDiffraction.app/Contents/MacOS/EasyDiffraction'
            if SYSTEM == 'macos'
            else 'bin/edi_app' + SUFFIX
        )
        with (output / 'app.log').open('w') as log:
            run(
                [app, '--testmode', output / 'smoke'],
                env=env,
                cwd=home,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=45,
            )
        receipt = json.loads((output / 'smoke/result.json').read_text())
        if not receipt.get('passed') or not (output / 'smoke/window.png').is_file():
            raise RuntimeError('Installed application smoke check failed')
        if SYSTEM == 'linux':
            dependencies = check_linux_dependencies(target, env)
            (output / 'dependencies.json').write_text(json.dumps(dependencies, indent=2) + '\n')
    finally:
        maintenance = target / (
            'MaintenanceTool.app/Contents/MacOS/MaintenanceTool'
            if SYSTEM == 'macos'
            else 'MaintenanceTool' + SUFFIX
        )
        with (output / 'uninstall.log').open('w') as log:
            run(
                [maintenance, '--confirm-command', '--default-answer', 'purge'],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=120,
            )
    if app.exists():
        raise RuntimeError('Uninstaller left the application installed')
    (output / 'passed.json').write_text(
        json.dumps({'passed': True, 'smoke': receipt}, indent=2) + '\n'
    )


def relocate_linux(stage: Path, patchelf: Path, qt_prefix: Path) -> None:
    stage = stage.resolve()
    if SYSTEM != 'linux':
        raise RuntimeError('ELF relocation is Linux only')
    for name in ['libssl.so.3', 'libcrypto.so.3']:
        source = qt_prefix / 'lib' / name
        if source.is_file():
            shutil.copy2(source.resolve(), stage / 'lib' / name)
    if (stage / 'lib/libc.so.6').exists():
        raise RuntimeError('The application must not bundle the operating system C library')
    for path in sorted(stage.rglob('*')):
        if path.is_symlink() or not path.is_file():
            continue
        if path.is_relative_to(stage / 'libexec/edi/codex'):
            continue
        with path.open('rb') as stream:
            if stream.read(4) != b'\x7fELF':
                continue
        relative = os.path.relpath(stage / 'lib', path.parent)
        run([patchelf, '--set-rpath', '$ORIGIN/' + relative, path])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    relocate = commands.add_parser('relocate-linux')
    relocate.add_argument('--stage', type=Path, required=True)
    relocate.add_argument('--patchelf', type=Path, required=True)
    relocate.add_argument('--qt-prefix', type=Path, required=True)
    fetch = commands.add_parser('tools')
    fetch.add_argument('--output', type=Path, required=True)
    package = commands.add_parser('package')
    package.add_argument('--stage', type=Path, required=True)
    package.add_argument('--tools', type=Path, required=True)
    package.add_argument('--output', type=Path, required=True)
    package.add_argument('--version', default='0.0.0')
    test = commands.add_parser('test')
    test.add_argument('--installer', type=Path, required=True)
    test.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'relocate-linux':
        relocate_linux(args.stage, args.patchelf, args.qt_prefix)
    elif args.command == 'tools':
        fetch_tools(args.output)
    elif args.command == 'package':
        package_app(args.stage, args.tools, args.output, args.version)
    else:
        test_installer(args.installer, args.output)


if __name__ == '__main__':
    main()
