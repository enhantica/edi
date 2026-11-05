# SPDX-License-Identifier: BSD-3-Clause
"""Stage qualified native artifacts without rebuilding or changing their identities."""

import argparse
import hashlib
import json
import re
import shutil
import stat
import subprocess
import xml.etree.ElementTree as ET  # noqa: S405 - bounded metadata rejects DTDs before parsing
import zipfile
from pathlib import Path, PurePosixPath

from plan import markdown_notes, validate_history, version_key

PLATFORMS = {'Linux': 'linux-x86_64', 'macOS': 'macos-arm64', 'Windows': 'windows-x86_64'}
ROOT = Path(__file__).resolve().parents[2]


def api(repo: str, suffix: str) -> dict:
    """Read GitHub's own workflow and artifact evidence."""
    return json.loads(subprocess.check_output(['gh', 'api', f'repos/{repo}/{suffix}']))


def qualified_artifacts(run: dict, artifacts: list[dict], jobs: list[dict]) -> dict[str, int]:
    """Require all native platforms and the retained plan from one successful main attempt."""
    if (
        run.get('path') != '.github/workflows/installers.yml'
        or run.get('head_branch') != 'main'
        or run.get('status') != 'completed'
        or run.get('conclusion') != 'success'
        or run.get('event') != 'workflow_dispatch'
    ):
        raise ValueError('Promote only a successful manual installer qualification on main')
    attempt = run['run_attempt']
    for name in [
        *[f'installer · {platform}' for platform in PLATFORMS],
        'record qualified release inputs',
    ]:
        matches = [job for job in jobs if job['name'] == name and job['run_attempt'] == attempt]
        if len(matches) != 1 or matches[0]['conclusion'] != 'success':
            raise ValueError('Every platform and prepared input must qualify in the same attempt')
    names = [f'qualified-release-plan-{attempt}']
    for platform in PLATFORMS:
        names += [f'installer-{platform}-{attempt}', f'installer-components-{platform}-{attempt}']
    selected = {}
    for name in names:
        matches = [item for item in artifacts if item['name'] == name and not item['expired']]
        if len(matches) != 1:
            raise ValueError('Qualified artifacts are missing, expired or ambiguous')
        selected[name] = matches[0]['id']
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
        + policy['repository_path'].format(channel='stable', platform=platform)
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
    name = metadata['zip']
    if name != f'EasyDiffraction-{version}-{platform}-online.zip':
        raise ValueError('Unexpected installer ZIP filename')
    archive = folder / name
    if archive.is_symlink() or digest(archive) != metadata['zip_sha256']:
        raise ValueError('Qualified installer ZIP bytes differ')
    return archive


def validate_repository(folder: Path, version: str) -> None:
    """Require matching component identity and the framework's original archive checksums."""
    content = (folder / 'Updates.xml').read_bytes()
    if len(content) > 1024 * 1024 or b'<!' in content:
        raise ValueError('Component metadata must be bounded without declarations')
    root = ET.fromstring(content)  # noqa: S314 - declarations rejected above
    packages = root.findall('PackageUpdate')
    expected = {'org.easyscience.edi', 'org.easyscience.edi.assistant'}
    if len(packages) != len(expected) or {p.findtext('Name') for p in packages} != expected:
        raise ValueError('Component repository does not match the qualified release')
    for package in packages:
        if package.findtext('Version') != version:
            raise ValueError('Component repository does not match the qualified release')
        component = folder / package.findtext('Name')
        archives = package.findtext('DownloadableArchives', '').split(',')
        if not archives or any(
            not name
            or Path(name).name != name
            or '\\' in name
            or ':' in name
            or not name.endswith('.7z')
            for name in archives
        ):
            raise ValueError('Component archive names are invalid')
        for name in archives:
            path = component / (version + name)
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha1').hexdigest()
            if actual != path.with_suffix(path.suffix + '.sha1').read_text().strip():
                raise ValueError('Component archive checksum differs')
        with (component / (version + 'meta.7z')).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha1').hexdigest() != package.findtext('SHA1'):
                raise ValueError('Component metadata archive checksum differs')


def stage(repo: str, identity: int, output: Path) -> None:
    """Download immutable qualified artifacts and assemble publication inputs."""
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or identity <= 0:
        raise ValueError('Expected a repository and positive qualified run ID')
    run = api(repo, f'actions/runs/{identity}')
    artifacts = api(repo, f'actions/runs/{identity}/artifacts?per_page=100')
    jobs = api(repo, f'actions/runs/{identity}/attempts/{run["run_attempt"]}/jobs?per_page=100')
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
    attempt = run['run_attempt']
    plan = output / f'qualified-release-plan-{attempt}'
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
    for platform, target in PLATFORMS.items():
        archive = validate_delivery(
            output / f'installer-{platform}-{attempt}',
            release,
            digest(plan / 'release-history.json'),
            target,
        )
        shutil.copy2(archive, assets / archive.name)
        build = json.loads(
            (output / f'installer-{platform}-{attempt}' / 'build-inputs.json').read_text()
        )
        engine_sources.add(build['crysta_commit'])
        components = output / f'installer-components-{platform}-{attempt}'
        if {item.name for item in components.iterdir()} != {'stable'} or {
            item.name for item in (components / 'stable').iterdir()
        } != {target}:
            raise ValueError('Qualified components must contain exactly their stable platform')
        validate_repository(components / 'stable' / target, release['version'])
        shutil.copytree(components / 'stable' / target, incoming / 'repository/stable' / target)
    if len(engine_sources) != 1 or not re.fullmatch(r'[0-9a-f]{40}', next(iter(engine_sources))):
        raise ValueError('All qualified platforms must build the same exact engine source')
    for name in ['release.json', 'release-history.json']:
        shutil.copy2(plan / name, assets / name)
    shutil.copy2(plan / 'notes.md', output / 'notes.md')
    (incoming / 'releases').mkdir()
    shutil.copy2(plan / 'release-history.json', incoming / 'releases/stable.json')
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
