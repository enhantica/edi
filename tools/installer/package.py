# SPDX-License-Identifier: BSD-3-Clause
"""Build, package and exercise native offline installers (ADR-0071)."""

import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tarfile
import urllib.request
import xml.etree.ElementTree as ET  # noqa: S405 - generated XML only, never external XML
import zipfile
from pathlib import Path

import py7zr

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = {'Linux': 'linux', 'Darwin': 'macos', 'Windows': 'windows'}[platform.system()]
SUFFIX = '.exe' if SYSTEM == 'windows' else ''
PLATFORM_ID = {'linux': 'linux-x86_64', 'macos': 'macos-arm64', 'windows': 'windows-x86_64'}[
    SYSTEM
]


def read_release_plan(directory: Path, source_commit: str | None = None) -> dict:
    """Require one immutable identity shared by prepared metadata and source."""
    documents = {}
    for name in ['plan.json', 'release.json', 'release-history.json']:
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
            raise RuntimeError('Release inputs must be bounded regular metadata files')
        documents[name] = json.loads(path.read_text(encoding='utf-8'))
    plan, release, history = (
        documents[name] for name in ['plan.json', 'release.json', 'release-history.json']
    )
    version = plan['version']
    if (
        not re.fullmatch(r'[0-9]{4}\.(0[1-9]|1[0-2])\.(0|[1-9][0-9]*)', version)
        or int(version[:4]) < 2000
    ):
        raise RuntimeError('Prepared release requires a calendar identity')
    if plan.get('reused'):
        raise RuntimeError('This release already exists; reuse its published artifacts')
    if (
        not re.fullmatch(r'[0-9a-f]{40}', plan['commit'])
        or release['version'] != version
        or release['commit'] != plan['commit']
    ):
        raise RuntimeError('Prepared release identities disagree')
    if source_commit is not None and plan['commit'] != source_commit:
        raise RuntimeError('Prepared release does not match this source commit')
    matches = [item for item in history['releases'] if item['version'] == version]
    if history['schema'] != 'edi.releases/1' or matches != [release]:
        raise RuntimeError('Prepared release is not uniquely recorded in its history')
    return release


def repository_urls(channel: str) -> tuple[str, ...]:
    """Return the primary repository and configured mirrors for this build platform."""
    policy = json.loads((ROOT / 'data/distribution.json').read_text(encoding='utf-8'))
    tail = policy['repository_path'].format(channel=channel, platform=PLATFORM_ID)
    return tuple(
        base.rstrip('/') + '/' + tail for base in [policy['primary_base'], *policy['mirror_bases']]
    )


def run(args, **kwargs: object) -> None:
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch_tools(destination: Path) -> Path:
    pin = json.loads((ROOT / 'tools/installer/ifw.json').read_text(encoding='utf-8'))['platforms'][
        SYSTEM
    ]
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
        package.extractall(tools)  # noqa: S202 - verified archive with checked member paths
    creator = tools / ('bin/binarycreator' + SUFFIX)
    if not creator.is_file():
        raise RuntimeError('Installer Framework has no binarycreator')
    if SYSTEM == 'linux':
        acquire_installer_licenses(tools, destination)
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


def write_metadata(
    config: Path,
    meta: Path,
    version: str,
    repository_url: str | None,
    mirrors: tuple[str, ...] = (),
) -> None:
    """Write the installer configuration and component metadata for either transport."""
    shutil.copy2(ROOT / 'LICENSE', meta / 'LICENSE')
    shutil.copy2(ROOT / 'COPYING', meta / 'COPYING')
    configuration = xml_file(
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
    if repository_url:
        if not repository_url.startswith(('https://', 'file://')):
            raise RuntimeError('Online repositories require HTTPS or a local fixture URL')
        remote = ET.SubElement(configuration.getroot(), 'RemoteRepositories')
        repository = ET.SubElement(remote, 'Repository')
        ET.SubElement(repository, 'Url').text = repository_url
        ET.SubElement(repository, 'Enabled').text = '1'
        for mirror_url in mirrors:
            mirror = ET.SubElement(remote, 'Repository')
            ET.SubElement(mirror, 'Url').text = mirror_url
            ET.SubElement(mirror, 'Enabled').text = '0'
            ET.SubElement(mirror, 'DisplayName').text = 'EasyDiffraction mirror'
        ET.indent(configuration)
        configuration.write(config / 'config.xml', encoding='utf-8', xml_declaration=True)
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
    ET.SubElement(
        licenses,
        'License',
        {'name': 'GNU General Public License v3 (application)', 'file': 'COPYING'},
    )
    ET.indent(root)
    root.write(meta / 'package.xml', encoding='utf-8', xml_declaration=True)


def acquire_installer_licenses(tools: Path, destination: Path) -> None:
    """Acquire pinned licence files before the network-free installer checks."""
    value = os.environ.get('PIXI_ENVIRONMENT_PREFIX') or os.environ.get('CONDA_PREFIX')
    if not value:
        raise RuntimeError('Acquire installer tools inside the packaging workspace')
    prefix = Path(value).resolve()
    probe = destination / 'license-probe'
    probe.mkdir()
    env = clean_environment(destination / 'tool-home')
    env['LD_LIBRARY_PATH'] = str(probe)
    copied = collect_linux_installer_libraries(
        tools / 'bin/installerbase', probe, prefix, shutil.which('patchelf'), env
    )
    for record in (prefix / 'conda-meta').glob('*.json'):
        metadata = json.loads(record.read_text(encoding='utf-8'))
        files = set(metadata.get('files', []))
        if not any(
            Path(source).is_relative_to(prefix)
            and Path(source).relative_to(prefix).as_posix() in files
            for source in copied.values()
        ):
            continue
        cached = Path(metadata.get('link', {}).get('source', '')) / 'info/licenses'
        target = tools / 'licenses' / metadata['name']
        if cached.is_dir():
            shutil.copytree(cached, target)
        else:
            acquire_package_licenses(metadata, destination, target)
    shutil.rmtree(probe)


def bundled_runtime_licenses(metadata: dict, target: Path) -> bool:
    """Supply verified upstream notices omitted by known split runtime packages."""
    root = ROOT / 'tools/installer/licenses'
    policy = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    package = policy['packages'].get(metadata['name'])
    if (
        not package
        or metadata['version'] != package['version']
        or metadata['license'] != package['license']
    ):
        return False
    target.mkdir(parents=True)
    for name in package['files']:
        source = root / name
        if source.is_symlink() or sha256(source) != policy['files'][name]['sha256']:
            raise RuntimeError('Pinned upstream dependency licence differs')
        shutil.copy2(source, target / name)
    shutil.copy2(root / 'NOTICE', target / 'NOTICE')
    return True


def acquire_package_licenses(metadata: dict, destination: Path, target: Path) -> None:
    """Recover pinned licence files when CI restores the environment without its cache."""
    if bundled_runtime_licenses(metadata, target):
        return
    print('Acquire dependency licences:', metadata['name'], flush=True)
    url = metadata['url']
    if not url.startswith('https://conda.anaconda.org/conda-forge/'):
        raise RuntimeError('Dependency licences must use the pinned conda-forge archive')
    archive = destination / (metadata['name'] + '.conda')
    with urllib.request.urlopen(url, timeout=30) as response, archive.open('wb') as stream:  # noqa: S310
        shutil.copyfileobj(response, stream)
    if sha256(archive) != metadata['sha256']:
        raise RuntimeError('Dependency licence archive checksum differs')
    target.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zipped:
        members = [name for name in zipped.namelist() if name.endswith('.tar.zst')]
        if (
            sum(name.startswith('info-') for name in members) != 1
            or sum(name.startswith('pkg-') for name in members) != 1
            or len(members) != 2
        ):
            raise RuntimeError('Dependency archive has no unique info and payload members')
        for name in members:
            extract_license_member(zipped, name, target)

    if not any(target.rglob('*')):
        raise RuntimeError(f'Dependency archive contains no licence files: {metadata["name"]}')


def extract_license_member(zipped: zipfile.ZipFile, name: str, target: Path) -> None:
    """Read licence files from either conda member without extracting executable payloads."""
    with zipped.open(name) as stream, tarfile.open(fileobj=stream, mode='r|zst') as info:
        for member in info:
            relative = Path(member.name)
            if relative.parts[:2] != ('info', 'licenses'):
                continue
            if '..' in relative.parts or not (member.isdir() or member.isfile()):
                raise RuntimeError('Dependency licence archive contains an unsafe member')
            if member.isfile():
                path = target / Path(*relative.parts[2:])
                path.parent.mkdir(parents=True, exist_ok=True)
                with info.extractfile(member) as source, path.open('wb') as sink:
                    shutil.copyfileobj(source, sink)


def installer_runtime_notices(
    copied: dict, prefix: Path | None, notices: Path, acquired: Path
) -> None:
    """Collect the licence files for every bundled installer library."""
    for name, source_path in copied.items():
        source = Path(source_path)
        if prefix and source.is_relative_to(prefix.resolve()):
            found = False
            for record in (prefix / 'conda-meta').glob('*.json'):
                metadata = json.loads(record.read_text(encoding='utf-8'))
                if source.relative_to(prefix.resolve()).as_posix() in metadata.get('files', []):
                    licenses = Path(metadata.get('link', {}).get('source', '')) / 'info/licenses'
                    if not licenses.is_dir():
                        licenses = acquired / metadata['name']
                    if licenses.is_dir():
                        shutil.copytree(licenses, notices / metadata['name'], dirs_exist_ok=True)
                        found = True
            if not found:
                raise RuntimeError(f'No dependency licence files found for {name}')
        else:
            result = subprocess.run(
                ['dpkg-query', '-S', str(source)], capture_output=True, text=True, check=False
            )
            if result.returncode and str(source).startswith('/usr/lib/'):
                result = subprocess.run(
                    ['dpkg-query', '-S', str(source).removeprefix('/usr')],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            packages = [
                line.split(': ', 1)[0].split(':', 1)[0] for line in result.stdout.splitlines()
            ]
            licenses = [Path('/usr/share/doc') / package / 'copyright' for package in packages]
            if not licenses or not any(path.is_file() for path in licenses):
                raise RuntimeError(f'No operating-system dependency licence found for {name}')
            for path in licenses:
                if path.is_file():
                    shutil.copy2(path, notices / (path.parent.name + '-copyright'))


def collect_linux_installer_libraries(
    template: Path, libraries: Path, prefix: Path | None, patchelf: str, env: dict
) -> dict:
    """Resolve and relocate the non-glibc dependency closure of the IFW template."""
    core = re.compile(r'lib(?:c|m|dl|pthread|rt|resolv|util|anl)\.so\.')
    copied = {}
    for _ in range(32):
        result = subprocess.run(
            ['/usr/bin/ldd', str(template)], env=env, capture_output=True, text=True, check=False
        )
        missing = []
        progress = False
        for line in result.stdout.splitlines():
            match = re.fullmatch(r'\s*(\S+) => (not found|/\S+)(?: \(.*\))?\s*', line)
            if not match:
                continue
            name, resolved = match.groups()
            if core.match(name):
                continue
            destination = libraries / name
            if destination.exists():
                if resolved == 'not found':
                    raise RuntimeError(f'Installer cannot load its bundled library: {name}')
                continue
            if resolved == 'not found':
                candidate = prefix / 'lib' / name if prefix else None
                if not candidate or not candidate.is_file():
                    missing.append(name)
                    continue
                source = candidate.resolve()
            else:
                source = Path(resolved).resolve()
            shutil.copy2(source, destination)
            run([patchelf, '--set-rpath', '$ORIGIN', destination])
            copied[name] = str(source)
            progress = True
        if not progress:
            if result.returncode or missing or 'not found' in result.stdout + result.stderr:
                raise RuntimeError(
                    f'Unresolved installer dependency: {result.stdout}{result.stderr}'
                )
            break
    else:
        raise RuntimeError('Installer dependency closure did not converge')
    return copied


def linux_installer_runtime(tools: Path, output: Path) -> tuple[Path, Path, dict]:
    """Relocate the IFW template before payload append; leave glibc to the OS."""
    template = output / 'installerbase'
    shutil.copy2(tools / 'bin/installerbase', template)
    libraries = output / 'installer-runtime/lib'
    notices = output / 'installer-runtime/licenses'
    libraries.mkdir(parents=True)
    notices.mkdir()
    patchelf = shutil.which('patchelf')
    if not patchelf:
        raise RuntimeError('Linux installer packaging requires patchelf')
    env = clean_environment(output / 'tool-home')
    env['LD_LIBRARY_PATH'] = str(libraries)
    prefix_value = os.environ.get('PIXI_ENVIRONMENT_PREFIX') or os.environ.get('CONDA_PREFIX')
    prefix = Path(prefix_value) if prefix_value else None
    copied = collect_linux_installer_libraries(template, libraries, prefix, patchelf, env)
    installer_runtime_notices(copied, prefix, notices, tools / 'licenses')
    run([patchelf, '--set-rpath', '$ORIGIN/installer-runtime/lib', template])
    (output / 'installer-runtime/dependencies.json').write_text(
        json.dumps({name: sha256(libraries / name) for name in copied}, indent=2) + '\n'
    )
    return template, libraries.parent, env


def archive_installer(installer: Path, runtime: Path | None) -> Path:
    """Archive the complete bootstrap including its portable runtime libraries."""
    archive = installer.with_suffix('.zip')
    if SYSTEM == 'macos':
        run(['codesign', '--force', '--deep', '--sign', '-', installer])
        run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', installer, archive])
    else:
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
            zipped.write(installer, installer.name)
            if runtime:
                for path in sorted(runtime.rglob('*')):
                    if path.is_file():
                        zipped.write(path, path.relative_to(installer.parent))
    return archive


def prepare_installer_source(
    stage: Path,
    tools: Path,
    output: Path,
    version: str,
    repository_url: str | None,
    mirrors: tuple[str, ...],
) -> tuple:
    """Prepare the payload and platform bootstrap runtime before framework packaging."""
    source = output / 'source'
    if source.exists():
        raise RuntimeError('Installer source already exists; choose a fresh output directory')
    config = source / 'config'
    meta = source / 'packages/org.easyscience.edi/meta'
    data = meta.parent / 'data'
    config.mkdir(parents=True)
    meta.mkdir(parents=True)
    shutil.copytree(stage, data, symlinks=True)
    template_args, tool_environment = [], None
    runtime = None
    if SYSTEM == 'linux':
        template, runtime, tool_environment = linux_installer_runtime(tools, output)
        template_args = ['-t', template]
        shutil.copytree(runtime, data / runtime.name)
    (data / 'payload-manifest.json').write_text(
        json.dumps(payload_manifest(data), indent=2) + '\n'
    )
    write_metadata(config, meta, version, repository_url, mirrors)
    return source, template_args, tool_environment, runtime


def package_app(
    stage: Path,
    tools: Path,
    output: Path,
    version: str,
    repository_url: str | None = None,
    mirrors: tuple[str, ...] = (),
) -> Path:
    if not re.fullmatch(r'[0-9]+(?:[.-][0-9]+)*', version):
        raise RuntimeError('Installer version must contain only numeric components')
    stage, tools, output = stage.resolve(), tools.resolve(), output.resolve()
    if not (
        stage
        / (
            'EasyDiffraction.app/Contents/MacOS/EasyDiffraction'
            if SYSTEM == 'macos'
            else 'bin/edi_app' + SUFFIX
        )
    ).is_file():
        raise RuntimeError('Stage does not contain the native application')
    if output.is_relative_to(stage):
        raise RuntimeError('Installer output must be outside the application stage')
    payload_manifest(stage)
    inputs_path = stage / 'build-inputs.json'
    inputs = json.loads(inputs_path.read_text(encoding='utf-8')) if inputs_path.is_file() else {}
    if inputs.get('release_version') and inputs['release_version'] != version:
        raise RuntimeError('Application and installer release versions disagree')
    output.mkdir(parents=True, exist_ok=True)
    source, template_args, tool_environment, runtime = prepare_installer_source(
        stage, tools, output, version, repository_url, mirrors
    )
    if repository_url:
        run(
            [
                tools / ('bin/repogen' + SUFFIX),
                '--verbose',
                '--component-metadata',
                '--compression',
                '1',
                '-p',
                source / 'packages',
                output / 'repository',
            ],
            env=tool_environment,
        )
    kind = 'online' if repository_url else 'offline'
    name = f'EasyDiffraction-{version}-{PLATFORM_ID}-{kind}'
    installer = output / (
        name + ('.app' if SYSTEM == 'macos' else '.exe' if SYSTEM == 'windows' else '.run')
    )
    run(
        [
            tools / ('bin/binarycreator' + SUFFIX),
            '--verbose',
            *template_args,
            '--compression',
            '1',
            '--online-only' if repository_url else '--offline-only',
            '-c',
            source / 'config/config.xml',
            '-p',
            source / 'packages',
            installer,
        ],
        env=tool_environment,
    )
    archive = archive_installer(installer, runtime)
    (output / 'installer.json').write_text(
        json.dumps(
            {
                'installer': installer.name,
                'zip': archive.name,
                'zip_sha256': sha256(archive),
                'ifw': '4.11.0',
                'platform': PLATFORM_ID,
                'version': version,
                'kind': kind,
                'repository_url': repository_url,
                'edi_commit': inputs.get('edi_commit'),
                'release_history_sha256': inputs.get('release_history_sha256'),
            },
            indent=2,
        )
        + '\n'
    )
    return installer


def clean_environment(home: Path) -> dict:
    temporary = home / 'tmp'
    temporary.mkdir(parents=True, exist_ok=True)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(('CONDA', 'PIXI', 'QT_', 'QML', 'EDI_', 'LD_', 'DYLD_', 'PYTHON'))
    }
    if SYSTEM == 'windows':
        system_root = next(
            (value for key, value in env.items() if key.casefold() == 'systemroot'), None
        )
        if not system_root:
            raise RuntimeError('Windows installer check requires the operating-system directory')
        system = Path(system_root)
        env['PATH'] = str(system / 'System32') + os.pathsep + str(system)
    else:
        env['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'
    env.update(
        HOME=str(home),
        TMP=str(temporary),
        TEMP=str(temporary),
        TMPDIR=str(temporary),
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


def unpack_installer(archive: Path, output: Path) -> Path:
    """Unpack our distribution archive and restore executable permissions."""
    output.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            if Path(member.filename).is_absolute() or '..' in Path(member.filename).parts:
                raise RuntimeError('Installer archive escapes its extraction directory')
        if SYSTEM == 'macos':
            run(['ditto', '-x', '-k', archive, output])
        else:
            zipped.extractall(output)  # noqa: S202 - validated paths; zip extraction creates no links
            for member in zipped.infolist():
                path = output / member.filename
                if path.is_file():
                    path.chmod((member.external_attr >> 16) & 0o777)
    suffix = '.app' if SYSTEM == 'macos' else '.exe' if SYSTEM == 'windows' else '.run'
    candidates = list(output.glob('*' + suffix))
    if len(candidates) != 1:
        raise RuntimeError('Installer archive must contain one platform bootstrap')
    return candidates[0]


def exercise_installer(installer: Path, output: Path, repository: str | None = None) -> None:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    metadata_path = installer.parent / 'installer.json'
    metadata = (
        json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.is_file() else {}
    )
    if installer.suffix == '.zip':
        installer = unpack_installer(installer, output / 'downloaded installer')
    home, target = output / 'isolated home', output / 'installed app'
    home.mkdir(exist_ok=True)
    if target.exists():
        raise RuntimeError('Installation target already exists; choose a fresh test directory')
    env = clean_environment(home)
    command = installer.resolve()
    if SYSTEM == 'macos':
        command = next((command / 'Contents/MacOS').iterdir())
    repository_args = ['--set-temp-repository', repository] if repository else []
    with (output / 'install.log').open('w') as log:
        run(
            [
                command,
                *repository_args,
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
        manifest = json.loads((target / 'payload-manifest.json').read_text(encoding='utf-8'))
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
        receipt = json.loads((output / 'smoke/result.json').read_text(encoding='utf-8'))
        if metadata.get('release_history_sha256') and (
            receipt.get('app_version') != metadata['version']
            or receipt.get('release_history_sha256') != metadata['release_history_sha256']
        ):
            raise RuntimeError('Installed release identity or bundled history differs')
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
    package.add_argument('--version')
    package.add_argument(
        '--release-plan', type=Path, default=os.environ.get('EDI_RELEASE_PLAN') or None
    )
    package.add_argument('--kind', choices=['offline', 'online'], default='offline')
    package.add_argument('--repository-url')
    package.add_argument('--channel', choices=['testing', 'stable'])
    test = commands.add_parser('test')
    test.add_argument('--installer', type=Path, required=True)
    test.add_argument('--output', type=Path, required=True)
    test.add_argument('--repository')
    args = parser.parse_args()
    if args.command == 'relocate-linux':
        relocate_linux(args.stage, args.patchelf, args.qt_prefix)
    elif args.command == 'tools':
        fetch_tools(args.output)
    elif args.command == 'package':
        urls = repository_urls(args.channel or ('stable' if args.release_plan else 'testing'))
        version = args.version or os.environ.get('EDI_INSTALLER_VERSION') or '0.0.0'
        if args.release_plan:
            release = read_release_plan(args.release_plan)
            if args.version and args.version != release['version']:
                raise RuntimeError('Explicit version disagrees with the prepared release')
            version = release['version']
            inputs = json.loads((args.stage / 'build-inputs.json').read_text(encoding='utf-8'))
            if inputs.get('edi_commit') != release['commit'] or inputs.get(
                'release_history_sha256'
            ) != sha256(args.release_plan / 'release-history.json'):
                raise RuntimeError('Staged application does not match the prepared release')
        package_app(
            args.stage,
            args.tools,
            args.output,
            version,
            (args.repository_url or urls[0]) if args.kind == 'online' else None,
            urls[1:] if args.kind == 'online' else (),
        )
    else:
        exercise_installer(args.installer, args.output, args.repository)


if __name__ == '__main__':
    main()
