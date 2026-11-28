# SPDX-License-Identifier: BSD-3-Clause
"""Stage qualified native artifacts without rebuilding or changing their identities."""

import argparse
import hashlib
import json
import operator
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import xml.etree.ElementTree as ET  # noqa: S405 - bounded metadata rejects DTDs before parsing
import zipfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from assistants import DISTRIBUTION_SETTINGS, distributed_assistants
from legacy_feed import write_feeds
from plan import installer_stem, markdown_notes, validate_history, version_key
from versions import is_version

PLATFORMS = {'Linux': 'linux-x86_64', 'macOS': 'macos-arm64', 'Windows': 'windows-x86_64'}
ROOT = Path(__file__).resolve().parents[2]
# The one installer file users download (edi ADR-0071); Linux keeps its runtime libraries in a ZIP.
INSTALLER_SUFFIXES = {'linux-x86_64': '.zip', 'macos-arm64': '.dmg', 'windows-x86_64': '.exe'}
# The platform as installer names show it (tools/installer/package.py INSTALLER_PLATFORM).
INSTALLER_PLATFORMS = {
    'linux-x86_64': 'Linux-x64',
    'macos-arm64': 'macOS-arm64',
    'windows-x86_64': 'Windows-x64',
}


def installer_name(version: str, platform: str, kind: str) -> str:
    """The file name of a platform's online or offline installer download."""
    return (
        installer_stem(version, INSTALLER_PLATFORMS[platform], kind) + INSTALLER_SUFFIXES[platform]
    )


def api(repo: str, suffix: str) -> dict:
    """Read GitHub's own workflow and artifact evidence."""
    return json.loads(subprocess.check_output(['gh', 'api', f'repos/{repo}/{suffix}']))


def qualified_artifacts(run: dict, artifacts: list[dict], jobs: list[dict]) -> dict[str, int]:
    """Each platform's installer and the plan from their latest successful attempt of one run.

    A re-run of only a failed job leaves the other jobs' artifacts in their earlier attempt, so a
    platform is taken from the attempt that ran its latest successful job. Every attempt of a run
    builds the same commit, so the run fixes the source and the plan. A platform or the plan with
    no successful attempt, or with two candidates in one attempt, is refused. A full re-run runs
    every job again (and deletes the earlier attempts' artifacts), so its own attempt is taken.
    """
    if (
        run.get('path') != '.github/workflows/installers.yml'
        or run.get('head_branch') != 'main'
        or run.get('status') != 'completed'
        or run.get('conclusion') != 'success'
        or run.get('event') != 'workflow_dispatch'
    ):
        raise ValueError('Promote only a successful manual installer qualification on main')
    wanted = {
        'qualified-release-plan': ('record qualified release inputs', ['qualified-release-plan'])
    }
    for platform in PLATFORMS:
        wanted[f'installer-{platform}'] = (
            f'installer · {platform}',
            [f'installer-{platform}', f'installer-components-{platform}'],
        )
    selected = {}
    for job_name, prefixes in wanted.values():
        named = [job for job in jobs if job['name'] == job_name]
        attempts = [job['run_attempt'] for job in named]
        if len(attempts) != len(set(attempts)):
            raise ValueError(f'{job_name} has two jobs in one attempt')
        passed = [job for job in named if job['conclusion'] == 'success']
        if not passed:
            raise ValueError(f'{job_name} has no successful attempt')
        latest = max(passed, key=operator.itemgetter('run_attempt'))

        # A re-run of the failed jobs copies each passed job into the new attempt with its
        # original times; its artifacts keep the name of the attempt that ran it. A job without
        # times is its own run.
        def ran(job: dict) -> tuple:
            times = (job.get('started_at'), job.get('completed_at'))
            return times if all(times) else ('job', job.get('id'), job['run_attempt'])

        attempt = min(job['run_attempt'] for job in passed if ran(job) == ran(latest))
        for prefix in prefixes:
            name = f'{prefix}-{attempt}'
            # Runs made before artifacts were named by runner.os called the Windows ones x64:
            # the MSVC setup step exported Platform=x64 over the workflow's PLATFORM.
            aliases = {name, name.replace('-Windows-', '-x64-')}
            matches = [
                item for item in artifacts if item['name'] in aliases and not item['expired']
            ]
            if len(matches) != 1:
                raise ValueError(f'The artifact {name} is missing, expired or ambiguous')
            selected[prefix] = matches[0]['id']
    return selected


def extract(archive: Path, destination: Path) -> None:
    """Extract bounded regular artifact members without links or path escapes."""
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        if len({item.filename for item in members}) != len(members):
            raise ValueError('Artifact has duplicate paths')
        if sum(item.file_size for item in members) > 2_000_000_000:
            raise ValueError('Artifact exceeds the qualification size limit')
        for item in members:
            path = PurePosixPath(item.filename)
            if (
                path.is_absolute()
                or '..' in path.parts
                or '\\' in item.filename
                or ':' in item.filename
                or stat.S_IFMT(item.external_attr >> 16) not in {0, stat.S_IFREG, stat.S_IFDIR}
            ):
                raise ValueError('Artifact has an unsafe member')
        destination.mkdir(parents=True)
        for item in members:
            target = destination / item.filename
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(item) as data, target.open('wb') as output:
                    shutil.copyfileobj(data, output)


def digest(path: Path) -> str:
    """Hash immutable artifact bytes."""
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_delivery(folder: Path, release: dict, history_hash: str, platform: str) -> Path:
    """Compare delivered ZIP, staged source and executed application identity."""
    metadata = json.loads((folder / 'installer.json').read_text())
    build = json.loads((folder / 'build-inputs.json').read_text())
    qualification = json.loads((folder / 'qualification.json').read_text())
    version, commit = release['version'], release['commit']
    policy = json.loads((ROOT / 'data/distribution.json').read_text())
    url = (
        policy['primary_base'].rstrip('/')
        + '/'
        + policy['repository_paths']['stable'].format(platform=platform)
    )
    expected = [
        (
            metadata,
            {
                'version': version,
                'platform': platform,
                'kind': 'online',
                'repository_url': url,
                'edi_commit': commit,
                'release_history_sha256': history_hash,
            },
        ),
        (
            build,
            {
                'edi_commit': commit,
                'release_version': version,
                'release_history_sha256': history_hash,
            },
        ),
        (qualification, {'passed': True}),
        (
            qualification.get('smoke', {}),
            {'passed': True, 'app_version': version, 'release_history_sha256': history_hash},
        ),
    ]
    if any(
        type(document.get(key)) is not type(value) or document[key] != value
        for document, fields in expected
        for key, value in fields.items()
    ):
        raise ValueError(
            'Delivered installer and executed application do not share the prepared identity'
        )
    name = metadata['download']
    if name != installer_name(version, platform, 'online'):
        raise ValueError('Unexpected installer filename')
    archive = folder / name
    if archive.is_symlink() or digest(archive) != metadata['download_sha256']:
        raise ValueError('Qualified installer bytes differ')
    return archive


def validate_cli(folder: Path, version: str, commit: str, platform: str) -> Path | None:
    """Read optional CLI evidence from a platform delivery, preserving older releases."""
    name = f'EasyDiffraction-{version}-{platform}-cli.zip'
    receipt = folder / 'cli-qualification.json'
    archive = folder / name
    if not receipt.exists() and not archive.exists():
        return None
    evidence = json.loads(receipt.read_text(encoding='utf-8'))
    expected = {'version': version, 'commit': commit, 'platform': platform, 'zip': name}
    if evidence.get('passed') is not True or any(
        evidence.get(key) != value for key, value in expected.items()
    ):
        raise ValueError('Qualified CLI identity or ZIP bytes differ')
    if archive.is_symlink() or digest(archive) != evidence.get('sha256'):
        raise ValueError('Qualified CLI identity or ZIP bytes differ')
    return archive


def validate_offline(folder: Path, version: str, commit: str, platform: str) -> Path | None:
    """Read the optional tested offline installer of a platform delivery."""
    name = installer_name(version, platform, 'offline')
    metadata, receipt = folder / 'offline-installer.json', folder / 'offline-qualification.json'
    archive = folder / name
    if not metadata.exists() and not archive.exists():
        return None
    identity = json.loads(metadata.read_text(encoding='utf-8'))
    qualification = json.loads(receipt.read_text(encoding='utf-8'))
    expected = {
        'version': version,
        'platform': platform,
        'kind': 'offline',
        'download': name,
        'edi_commit': commit,
    }
    if (
        any(identity.get(key) != value for key, value in expected.items())
        or qualification.get('passed') is not True
        or qualification.get('smoke', {}).get('app_version') != version
    ):
        raise ValueError('Qualified offline installer identity differs')
    if archive.is_symlink() or digest(archive) != identity.get('download_sha256'):
        raise ValueError('Qualified offline installer bytes differ')
    return archive


def validate_wheel(folder: Path, version: str, commit: str, platform: str) -> Path | None:
    """Require the exact Python wheel qualified on this release platform."""
    tags = {
        'linux-x86_64': 'linux_x86_64',
        'windows-x86_64': 'win_amd64',
        'macos-arm64': 'macosx_14_0_arm64',
    }
    name = f'easydiffraction-{version}-cp312-abi3-{tags[platform]}.whl'
    wheel = folder / name
    receipt = folder / 'wheel-qualification.json'
    if not receipt.exists() and not list(folder.glob('*.whl')):
        return None
    evidence = json.loads(receipt.read_text(encoding='utf-8'))
    expected = {
        'passed': True,
        'version': version,
        'commit': commit,
        'platform': platform,
        'wheel': name,
    }
    if evidence.get('passed') is not True or any(
        evidence.get(key) != value for key, value in expected.items()
    ):
        raise ValueError('Qualified Python wheel identity differs')
    if wheel.is_symlink() or digest(wheel) != evidence.get('sha256'):
        raise ValueError('Qualified Python wheel bytes differ')
    return wheel


def components_name(version: str, platform: str, channel: str) -> str:
    return f'EasyDiffraction-{version}-{platform}-{channel}-components.zip'


def pack_components(repository: Path, archive: Path) -> None:
    """Write one archive of a tested component repository, keeping its relative paths.

    Unpacked at any folder it is the same repository the online installers read, so a release on
    GitHub carries everything needed to host its components elsewhere.
    """
    files = sorted(path for path in repository.rglob('*') if not path.is_dir())
    with zipfile.ZipFile(archive, 'x') as target:
        for path in files:
            if path.is_symlink() or not path.is_file():
                raise ValueError('Component repositories hold regular files only')
            member = zipfile.ZipInfo(
                path.relative_to(repository).as_posix(), (1980, 1, 1, 0, 0, 0)
            )
            member.external_attr = (stat.S_IFREG | 0o644) << 16
            with path.open('rb') as data, target.open(member, 'w') as output:
                shutil.copyfileobj(data, output)


def components_validator(channel: str) -> Callable[[Path, str, str, str], Path | None]:
    """Read the optional component archive of a platform delivery for one channel."""

    def validate_components(
        folder: Path, version: str, _commit: str, platform: str
    ) -> Path | None:
        archive = folder / components_name(version, platform, channel)
        if not archive.exists():
            return None
        if archive.is_symlink():
            raise ValueError('Component archives must be regular files')
        with tempfile.TemporaryDirectory() as scratch:
            extract(archive, Path(scratch) / 'repository')
            validate_repository(
                Path(scratch) / 'repository', version, expected=component_names(platform)
            )
        return archive

    return validate_components


def stage_optional_assets(output: Path, assets: Path, release: dict) -> None:
    """Add complete sets of standalone ZIPs and wheels when the build provides them."""
    for validator in (
        validate_cli,
        validate_wheel,
        validate_offline,
        components_validator('stable'),
    ):
        archives = [
            validator(
                output / f'installer-{platform}',
                release['version'],
                release['commit'],
                target,
            )
            for platform, target in PLATFORMS.items()
        ]
        qualified = [archive for archive in archives if archive is not None]
        if qualified and len(qualified) != len(PLATFORMS):
            raise ValueError('The release must carry each asset family for all platforms together')
        for archive in qualified:
            shutil.copy2(archive, assets / archive.name)


APP_COMPONENT = 'org.easydiffraction.app'
# The app and its distributed assistant components (tools/release/assistants.py, edi ADR-0108).
APP_COMPONENTS = frozenset({APP_COMPONENT, *distributed_assistants()})
# macOS and Windows install their separately signed maintenance tool from it (edi ADR-0091).
MAINTENANCE_COMPONENT = 'org.easydiffraction.app.maintenancetool'
MAINTENANCE_PLATFORMS = frozenset({'macos-arm64', 'windows-x86_64'})


def component_names(platform: str) -> frozenset[str]:
    """The components a release repository holds for one platform."""
    if platform in MAINTENANCE_PLATFORMS:
        return APP_COMPONENTS | {MAINTENANCE_COMPONENT}
    return APP_COMPONENTS


# Each stable component archive is attached to the release as its own asset, which GitHub keeps
# under 2 GiB (edi ADR-0071). The earlier 95 MB cap was for GitHub's 100 MiB limit on files pushed
# to edi-sites, which used to hold the archives; the download site's host never refused one.
ARCHIVE_LIMIT = 2_000_000_000

# A component archive's release asset is component-<platform>-<component>-<version><archive>,
# in the characters GitHub keeps in asset names. The archive name starts with a letter so the
# download site's redirect can tell it from the version in front of it.
COMPONENT_ID = r'org\.easydiffraction(?:\.[A-Za-z0-9_-]+)+'
ARCHIVE_NAME = r'[A-Za-z][A-Za-z0-9._-]*\.7z'

# The data/distribution.json setting that can keep a component off the release and the download
# site; the component is published only while its setting says "public": Claude's and GitHub
# Copilot's (tools/release/assistants.py, edi ADR-0108).
WITHHOLDING_SETTINGS: dict[str, str] = DISTRIBUTION_SETTINGS


def require_archive_size(path: Path, limit: int | None = None) -> None:
    size, limit = path.stat().st_size, ARCHIVE_LIMIT if limit is None else limit
    if size > limit:
        raise ValueError(f'{path.name} is {size:,} bytes, over the {limit:,}-byte limit')


def component_asset(platform: str, component: str, version: str, archive: str) -> str:
    """The release asset name of one component archive."""
    if (
        platform not in INSTALLER_PLATFORMS
        or not re.fullmatch(COMPONENT_ID, component)
        or not re.fullmatch(ARCHIVE_NAME, archive)
    ):
        raise ValueError(f'{component}/{version}{archive} cannot be named as a release asset')
    return f'component-{platform}-{component}-{version}{archive}'


def withheld(component: str) -> bool:
    """Whether the distribution policy keeps this component off every public download."""
    setting = WITHHOLDING_SETTINGS.get(component)
    if setting is None:
        return False
    policy = json.loads((ROOT / 'data/distribution.json').read_text(encoding='utf-8'))
    return policy.get(setting) != 'public'


def validate_repository(
    folder: Path,
    version: str,
    *,
    expected: frozenset[str] = APP_COMPONENTS,
    limit: int | None = None,
    reused: dict[str, str] | None = None,
) -> None:
    """Require matching component identity and the framework's original archive checksums.

    Every component is at `version`, except those in `reused`, which keep the earlier version the
    record names (reuse_unchanged).
    """
    reused = reused or {}
    if any(version_key(earlier) >= version_key(version) for earlier in reused.values()):
        raise ValueError('A reused component must come from an earlier release')
    # Publication copies the whole tree, so every file in it meets the size limit, listed or not.
    for path in sorted(folder.rglob('*')):
        if path.is_file():
            require_archive_size(path, limit)
    content = (folder / 'Updates.xml').read_bytes()
    if len(content) > 1024 * 1024 or b'<!' in content:
        raise ValueError('Component metadata must be bounded without declarations')
    root = ET.fromstring(content)  # noqa: S314 - declarations rejected above
    packages = root.findall('PackageUpdate')
    if len(packages) != len(expected) or {p.findtext('Name') for p in packages} != expected:
        raise ValueError('Component repository does not match the qualified release')
    for package in packages:
        own = reused.get(package.findtext('Name'), version)
        if package.findtext('Version') != own:
            raise ValueError('Component repository does not match the qualified release')
        component = folder / package.findtext('Name')
        archives = package.findtext('DownloadableArchives', '').split(',')
        # Each archive becomes a release asset, so its name must fit one (component_asset).
        if not re.fullmatch(COMPONENT_ID, package.findtext('Name')) or any(
            not re.fullmatch(ARCHIVE_NAME, name) for name in archives
        ):
            raise ValueError('Component archive names are invalid')
        for name in archives:
            path = component / (own + name)
            require_archive_size(path, limit)
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha1').hexdigest()
            if actual != path.with_suffix(path.suffix + '.sha1').read_text().strip():
                raise ValueError('Component archive checksum differs')
        require_archive_size(component / (own + 'meta.7z'), limit)
        with (component / (own + 'meta.7z')).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha1').hexdigest() != package.findtext('SHA1'):
                raise ValueError('Component metadata archive checksum differs')


# Each stable release attaches this record of its components: per platform and component, the
# release that last changed it, its input identity and its archive assets (edi ADR-0111).
RECORD = 'components.json'
RECORD_SCHEMA = 'edi.components/1'
IDENTITY = re.compile(r'[0-9a-f]{64}')

Fetch = Callable[[str, str, Path], None]


def component_identities(metadata: dict, platform: str) -> dict[str, str]:
    """The input identity installer.json names for each component of the platform."""
    identities = metadata.get('component_identities')
    if (
        not isinstance(identities, dict)
        or set(identities) != component_names(platform)
        or not all(isinstance(v, str) and IDENTITY.fullmatch(v) for v in identities.values())
    ):
        raise ValueError(f"{platform}: the installer does not name each component's identity")
    return identities


def archive_assets(platform: str, package: ET.Element) -> list[str]:
    """The release assets of one Updates.xml entry's archives."""
    name, version = package.findtext('Name'), package.findtext('Version')
    archives = package.findtext('DownloadableArchives', '').split(',')
    return [component_asset(platform, name, version, archive) for archive in archives if archive]


def read_record(path: Path, version: str) -> dict:
    """The component record of release `version`, refused unless every entry is well formed."""
    record = json.loads(path.read_text(encoding='utf-8'))
    platforms = record.get('platforms') if isinstance(record, dict) else None
    if (
        not isinstance(platforms, dict)
        or (record.get('schema'), record.get('version')) != (RECORD_SCHEMA, version)
        or not set(platforms) <= set(INSTALLER_PLATFORMS)
        or not all(isinstance(c, dict) and c for c in platforms.values())
    ):
        raise ValueError(f'The {RECORD} of {version} is malformed')
    for platform, components in record['platforms'].items():
        for component, entry in components.items():
            if not (
                isinstance(entry, dict)
                and set(entry) == {'version', 'identity', 'archives'}
                and isinstance(entry['version'], str)
                and is_version(entry['version'])
                and version_key(entry['version']) <= version_key(version)
                and isinstance(entry['identity'], str)
                and IDENTITY.fullmatch(entry['identity'])
                and isinstance(entry['archives'], list)
                and all(isinstance(name, str) for name in entry['archives'])
            ):
                raise ValueError(f'The {RECORD} of {version} is malformed: {platform} {component}')
    return record


def release_asset(repo: str) -> Fetch:
    """Download one asset of a published release into a folder."""

    def fetch(tag: str, name: str, folder: Path) -> None:
        subprocess.run(
            ['gh', 'release', 'download', tag, '--repo', repo, '--pattern', name],
            cwd=folder,
            check=True,
        )
        if not (folder / name).is_file():
            raise ValueError(f'{tag} has no asset {name}')

    return fetch


def previous_record(repo: str, version: str, fetch: Fetch) -> dict | None:
    """The record of the latest published release; None if it was published without one."""
    latest = api(repo, 'releases/latest')
    earlier = latest['tag_name'].removeprefix('v')
    if not is_version(earlier) or version_key(earlier) >= version_key(version):
        raise ValueError(f'The latest release {latest["tag_name"]} is not older than {version}')
    if RECORD not in {asset['name'] for asset in latest['assets']}:
        return None
    with tempfile.TemporaryDirectory() as scratch:
        fetch(latest['tag_name'], RECORD, Path(scratch))
        return read_record(Path(scratch) / RECORD, earlier)


def reuse_unchanged(
    repository: Path,
    platform: str,
    version: str,
    identities: dict[str, str],
    previous: dict | None,
    fetch: Fetch,
) -> dict[str, dict]:
    """Give each unchanged component the files of the release that last changed it.

    `repository` is this release's repository for `platform`, every component built at `version`.
    A component whose identity equals the one the latest release's record (`previous`) holds takes
    that release's Updates.xml entry, meta.7z and .sha1 files from its repository index, and its
    archives from the release its version names. The Maintenance Tool then sees the version and
    content checksum already installed and does not offer it. Returns this platform's record.
    """
    earlier = previous['platforms'].get(platform, {}) if previous else {}
    tag = f'v{previous["version"]}' if previous else ''
    updates = ET.fromstring((repository / 'Updates.xml').read_bytes())  # noqa: S314 - validated
    record, index, listed = {}, None, None
    with tempfile.TemporaryDirectory() as scratch:
        for package in updates.findall('PackageUpdate'):
            name = package.findtext('Name')
            entry = earlier.get(name)
            if entry is None or entry['identity'] != identities[name]:
                record[name] = {
                    'version': version,
                    'identity': identities[name],
                    'archives': archive_assets(platform, package),
                }
                continue
            if index is None:
                fetch(tag, f'repoindex-stable-{platform}.tar.gz', Path(scratch))
                with tarfile.open(Path(scratch) / f'repoindex-stable-{platform}.tar.gz') as opened:
                    opened.extractall(Path(scratch) / 'index', filter='data')
                index = Path(scratch) / 'index/repository' / platform
                listed = ET.fromstring((index / 'Updates.xml').read_bytes())  # noqa: S314
            old = [p for p in listed.findall('PackageUpdate') if p.findtext('Name') == name]
            if (
                len(old) != 1
                or old[0].findtext('Version') != entry['version']
                or archive_assets(platform, old[0]) != entry['archives']
            ):
                raise ValueError(f'The record of {tag} disagrees with its index: {name}')
            shutil.rmtree(repository / name)
            (repository / name).mkdir()
            prefix = entry['version']
            shutil.copy2(index / name / f'{prefix}meta.7z', repository / name)
            names = [a for a in old[0].findtext('DownloadableArchives', '').split(',') if a]
            for archive, asset in zip(names, entry['archives'], strict=True):
                shutil.copy2(index / name / f'{prefix}{archive}.sha1', repository / name)
                fetch(f'v{prefix}', asset, repository / name)
                (repository / name / asset).rename(repository / name / f'{prefix}{archive}')
            updates.insert(list(updates).index(package), old[0])
            updates.remove(package)
            record[name] = dict(entry)
    if any(entry['version'] != version for entry in record.values()):
        ET.ElementTree(updates).write(
            repository / 'Updates.xml', encoding='UTF-8', xml_declaration=True
        )
    return record


def publish_components(
    repository: Path,
    platform: str,
    version: str,
    metadata: dict,
    previous: dict | None,
    fetch: Fetch,
) -> dict[str, dict]:
    """Turn a qualified repository into the one the release publishes; return its record.

    `metadata` is the platform's installer.json, `previous` the latest release's record.
    """
    identities = component_identities(metadata, platform)
    entries = reuse_unchanged(repository, platform, version, identities, previous, fetch)
    reused = {name: e['version'] for name, e in entries.items() if e['version'] != version}
    validate_repository(repository, version, expected=component_names(platform), reused=reused)
    return entries


def stage(repo: str, identity: int, output: Path) -> None:  # noqa: PLR0914 - one step after another
    """Download immutable qualified artifacts and assemble publication inputs."""
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or identity <= 0:
        raise ValueError('Expected a repository and positive qualified run ID')
    run = api(repo, f'actions/runs/{identity}')
    artifacts = api(repo, f'actions/runs/{identity}/artifacts?per_page=100')
    # Every attempt's jobs: a platform may pass in an earlier attempt than the run's last.
    jobs = api(repo, f'actions/runs/{identity}/jobs?filter=all&per_page=100')
    if artifacts['total_count'] > len(artifacts['artifacts']) or jobs['total_count'] > len(
        jobs['jobs']
    ):
        raise ValueError('Unexpected qualification evidence count')
    selected = qualified_artifacts(run, artifacts['artifacts'], jobs['jobs'])
    subprocess.run(
        ['git', 'merge-base', '--is-ancestor', run['head_sha'], 'origin/main'],
        cwd=ROOT,
        check=True,
    )
    output.mkdir(parents=True)
    for name, artifact in selected.items():
        archive = output / (name + '.zip')
        with archive.open('wb') as stream:
            subprocess.run(
                ['gh', 'api', f'repos/{repo}/actions/artifacts/{artifact}/zip'],
                stdout=stream,
                check=True,
            )
        extract(archive, output / name)
        archive.unlink()
    plan = output / 'qualified-release-plan'
    release = json.loads((plan / 'release.json').read_text())
    history = json.loads((plan / 'release-history.json').read_text())
    prepared = json.loads((plan / 'plan.json').read_text())
    validate_history(history)
    if (
        prepared != {'version': release['version'], 'commit': run['head_sha'], 'reused': False}
        or release['version']
        != max(history['releases'], key=lambda item: version_key(item['version']))['version']
        or release['commit'] != run['head_sha']
        or [item for item in history['releases'] if item['version'] == release['version']]
        != [release]
        or (plan / 'notes.md').read_text() != markdown_notes(release)
    ):
        raise ValueError('Qualified history does not describe the exact source and user notes')
    assets, incoming = output / 'assets', output / 'incoming'
    assets.mkdir()
    engine_sources = set()
    fetch = release_asset(repo)
    previous = previous_record(repo, release['version'], fetch)
    record: dict = {'schema': RECORD_SCHEMA, 'version': release['version'], 'platforms': {}}
    for platform, target in PLATFORMS.items():
        archive = validate_delivery(
            output / f'installer-{platform}',
            release,
            digest(plan / 'release-history.json'),
            target,
        )
        shutil.copy2(archive, assets / archive.name)
        build = json.loads((output / f'installer-{platform}' / 'build-inputs.json').read_text())
        engine_sources.add(build['crysta_commit'])
        components = output / f'installer-components-{platform}'
        if {item.name for item in components.iterdir()} != {'stable'} or {
            item.name for item in (components / 'stable').iterdir()
        } != {target}:
            raise ValueError('Qualified components must contain exactly their stable platform')
        validate_repository(
            components / 'stable' / target, release['version'], expected=component_names(target)
        )
        shutil.copytree(components / 'stable' / target, incoming / 'repository/stable' / target)
        record['platforms'][target] = publish_components(
            incoming / 'repository/stable' / target,
            target,
            release['version'],
            json.loads((output / f'installer-{platform}' / 'installer.json').read_text()),
            previous,
            fetch,
        )
    (assets / RECORD).write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    stage_optional_assets(output, assets, release)
    if len(engine_sources) != 1 or not re.fullmatch(r'[0-9a-f]{40}', next(iter(engine_sources))):
        raise ValueError('All qualified platforms must build the same exact engine source')
    for name in ['release.json', 'release-history.json']:
        shutil.copy2(plan / name, assets / name)
    shutil.copy2(plan / 'notes.md', output / 'notes.md')
    # stable-v2.json for current apps, and stable.json for apps up to v2026.11.31, which drop a
    # feed holding any YY.N version (edi ADR-0106); refused if their parser would drop it too.
    write_feeds(plan / 'release-history.json', incoming / 'releases')
    (assets / 'SHA256SUMS').write_text(
        ''.join(f'{digest(path)}  {path.name}\n' for path in sorted(assets.iterdir()))
    )
    (output / 'release.json').write_text(json.dumps(release, indent=2) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--run', required=True, type=int)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    stage(args.repo, args.run, args.output)


if __name__ == '__main__':
    main()
