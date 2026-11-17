# SPDX-License-Identifier: BSD-3-Clause
"""Release consumers of the separately packaged macOS maintenance tool."""

import hashlib
import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import yaml

APP = 'org.easyscience.edi'
ASSISTANT = APP + '.assistant'
MAINTENANCE = APP + '.maintenancetool'
VERSION = '2026.11.1'
COMMIT = 'a' * 40
PLATFORMS = ('linux-x86_64', 'macos-arm64', 'windows-x86_64')


def load(root, relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, root / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def repository(folder, platform, maintenance_version, damage):
    names = [APP, ASSISTANT]
    if platform == 'macos-arm64' or damage == 'foreign-maintenance':
        names.append(MAINTENANCE)
    if damage == 'missing-maintenance':
        names.remove(MAINTENANCE)
    if damage == 'unknown-name':
        names[-1] += '.unknown'
    content = '<Updates>'
    for name in names:
        version = maintenance_version if name == MAINTENANCE else VERSION
        if name == APP and damage == 'application-version':
            version = '2026.11.9'
        component = folder / name
        component.mkdir(parents=True)
        for filename in ('content.7z', 'meta.7z'):
            path = component / (version + filename)
            path.write_bytes((name + '/' + filename).encode())
            path.with_suffix('.7z.sha1').write_text(
                hashlib.sha1(path.read_bytes(), usedforsecurity=False).hexdigest()
            )
        metadata_hash = (component / (version + 'meta.7z.sha1')).read_text()
        content += (
            f'<PackageUpdate><Name>{name}</Name><Version>{version}</Version>'
            '<DownloadableArchives>content.7z</DownloadableArchives>'
            f'<SHA1>{metadata_hash}</SHA1></PackageUpdate>'
        )
        if name == (MAINTENANCE if platform == 'macos-arm64' else APP):
            if damage == 'archive':
                (component / (version + 'content.7z')).write_bytes(b'corrupt archive')
            if damage == 'metadata':
                (component / (version + 'meta.7z')).write_bytes(b'corrupt metadata')
    (folder / 'Updates.xml').write_text(content + '</Updates>')
    return folder


def preview_delivery(root, folder, platform):
    folder.mkdir(parents=True)
    name = f'EasyDiffraction-{VERSION}-{platform}-online.zip'
    archive = folder / name
    archive.write_bytes(b'qualified installer')
    policy = json.loads((root / 'data/distribution.json').read_text())
    metadata = {
        'zip': name,
        'zip_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'version': VERSION,
        'platform': platform,
        'kind': 'online',
        'edi_commit': COMMIT,
        'repository_url': policy['primary_base']
        + policy['repository_paths']['testing'].format(platform=platform),
    }
    for name, value in [
        ('installer.json', metadata),
        ('build-inputs.json', {'edi_commit': COMMIT}),
        ('qualification.json', {'passed': True, 'smoke': {'passed': True}}),
    ]:
        (folder / name).write_text(json.dumps(value))
    return folder


def consume_archive(promote, folder, repo, platform, channel):
    delivery = folder / 'delivery'
    delivery.mkdir()
    archive = delivery / promote.components_name(VERSION, platform, channel)
    promote.pack_components(repo, archive)
    result = promote.components_validator(channel)(delivery, VERSION, COMMIT, platform)
    assert result == archive, (
        'Promotion must retain the qualified component archive for its platform and channel'
    )


def consume_preview(root, preview, folder, repo, platform):
    output = folder / 'recovered'
    output.mkdir()
    preview.copy_preview(
        preview_delivery(root, folder / 'delivery', platform),
        repo.parents[1],
        output,
        platform,
        VERSION,
        COMMIT,
    )
    copied = output / 'components/testing' / platform
    assert sorted(
        path.relative_to(copied) for path in copied.rglob('*') if path.is_file()
    ) == sorted(path.relative_to(repo) for path in repo.rglob('*') if path.is_file()), (
        'Preview recovery must retain exactly the qualified component files'
    )
    assert all(
        (copied / path.relative_to(repo)).read_bytes() == path.read_bytes()
        for path in repo.rglob('*')
        if path.is_file()
    ), 'Preview recovery must preserve component and checksum bytes'


def consume_stable_stage(promote, folder, repo, platform, monkeypatch):
    fixtures = folder / 'qualified'
    plan = fixtures / 'qualified-release-plan'
    plan.mkdir(parents=True)
    release = {
        'version': VERSION,
        'commit': COMMIT,
        'date': '2026-11-17',
        'notes': {
            'Added': [],
            'Fixed': [{'title': 'Repair update installation', 'pull_request': 1}],
            'Changed': [],
        },
    }
    for name, value in [
        ('release.json', release),
        (
            'release-history.json',
            {'schema': 'edi.releases/1', 'baseline_commit': 'b' * 40, 'releases': [release]},
        ),
        ('plan.json', {'version': VERSION, 'commit': COMMIT, 'reused': False}),
    ]:
        (plan / name).write_text(json.dumps(value))
    (plan / 'notes.md').write_text(promote.markdown_notes(release))
    for label, target in promote.PLATFORMS.items():
        delivery = fixtures / ('installer-' + label)
        delivery.mkdir()
        (delivery / 'build-inputs.json').write_text(json.dumps({'crysta_commit': 'b' * 40}))
        (delivery / 'qualified.zip').write_bytes(b'previously qualified installer')
        destination = fixtures / ('installer-components-' + label) / 'stable' / target
        if target == platform:
            promote.shutil.copytree(repo, destination)
        else:
            repository(destination, target, VERSION, 'none')
    selected = {path.name: index for index, path in enumerate(fixtures.iterdir(), 1)}
    artifacts = {}
    for name, index in selected.items():
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            for path in (fixtures / name).rglob('*'):
                if path.is_file():
                    archive.write(path, path.relative_to(fixtures / name))
        artifacts[index] = data.getvalue()

    def api(_repo, suffix):
        if '/artifacts?' in suffix:
            return {'total_count': 0, 'artifacts': []}
        if '/jobs?' in suffix:
            return {'total_count': 0, 'jobs': []}
        return {'head_sha': COMMIT}

    def transport(args, **kwargs):
        if args[0] == 'gh':
            kwargs['stdout'].write(artifacts[int(args[-1].split('/')[-2])])
        else:
            assert args[:3] == ['git', 'merge-base', '--is-ancestor'], (
                'Stable repository fixtures may fake only the external source ancestry check'
            )
        return SimpleNamespace(returncode=0)

    with monkeypatch.context() as patch:
        patch.setattr(promote, 'api', api)
        patch.setattr(promote, 'qualified_artifacts', lambda *_args: selected)
        patch.setattr(promote.subprocess, 'run', transport)
        patch.setattr(
            promote, 'validate_delivery', lambda delivery, *_args: delivery / 'qualified.zip'
        )
        promote.stage('enhantica/edi', 1, folder / 'staged')
    copied = folder / 'staged/incoming/repository/stable' / platform
    assert (copied / 'Updates.xml').read_bytes() == (repo / 'Updates.xml').read_bytes(), (
        'Stable staging must admit and retain the actual platform component repository'
    )


def feed_inputs(root, folder, platform, maintenance_version, damage):
    policy = json.loads((root / 'data/distribution.json').read_text())
    payload = json.dumps({'schema': 'edi.releases/1', 'releases': [{'version': VERSION}]}).encode()
    for channel, filename in [('testing', 'testing.json'), ('stable', 'stable.json')]:
        repo = folder / policy['repository_paths'][channel].format(platform=platform)
        repository(repo, platform, maintenance_version, damage)
        feed = folder / 'releases' / filename
        feed.parent.mkdir(exist_ok=True)
        feed.write_bytes(payload)
    return payload


def consume_workflow(root, folder, platform, maintenance_version, damage, monkeypatch):
    workflow = yaml.load(
        (root / '.github/workflows/installers.yml').read_text(), Loader=yaml.BaseLoader
    )
    steps = [
        step
        for job in workflow['jobs'].values()
        for step in job.get('steps', [])
        if step.get('name') == 'Prepare the testing update feed'
    ]
    assert len(steps) == 1, 'Fresh previews must retain one feed preparation step'
    run = steps[0]['run']
    opener, code = run.split("<<'PYTHON'\n", 1)
    assert 'python' in opener, 'The preview feed observer must execute the workflow Python body'
    code = code.rsplit('\nPYTHON', 1)[0]
    components = folder / 'components'
    payload = feed_inputs(root, components, platform, maintenance_version, damage)
    policy = json.loads((root / 'data/distribution.json').read_text())
    actual = components / policy['repository_paths']['testing'].format(platform=platform)
    destination = components / 'testing' / platform
    destination.parent.mkdir(parents=True)
    actual.rename(destination)
    for label in ('Linux', 'macOS', 'Windows'):
        history = folder / 'preview-delivery' / ('installer-' + label) / 'preview-history.json'
        history.parent.mkdir(parents=True)
        history.write_bytes(payload)
    with monkeypatch.context() as patch:
        patch.chdir(folder)
        patch.syspath_prepend(str(root))
        exec(compile(code, '<preview feed workflow>', 'exec'), {'__name__': '__main__'})  # noqa: S102 - actual workflow code
    assert (components / 'testing/feed.json').read_bytes() == payload, (
        'The workflow must publish the unchanged preview history after component agreement'
    )


def consumer_cases():
    for platform in PLATFORMS:
        names = ['none', 'application-version', 'archive', 'metadata', 'unknown-name']
        names += ['missing-maintenance'] if platform == 'macos-arm64' else ['foreign-maintenance']
        for consumer in (
            'stable-stage',
            'stable-archive',
            'testing-archive',
            'preview',
            'workflow',
            'pages',
        ):
            # Feed checks enforce version agreement; archive consumers also own byte validation.
            cases = (
                names if consumer not in {'workflow', 'pages'} else ['none', 'application-version']
            )
            for damage in cases:
                yield platform, consumer, damage


def exercise_consumer(root, modules, folder, identity, maintenance_version, monkeypatch):
    platform, consumer, damage = identity
    promote, preview, pages = modules
    if consumer == 'workflow':
        consume_workflow(root, folder, platform, maintenance_version, damage, monkeypatch)
    elif consumer == 'pages':
        feed_inputs(root, folder, platform, maintenance_version, damage)
        pages.check_feed_agreement(folder)
    else:
        repo = repository(
            folder / 'components/testing' / platform, platform, maintenance_version, damage
        )
        if consumer == 'stable-stage':
            consume_stable_stage(promote, folder, repo, platform, monkeypatch)
        elif consumer == 'preview':
            consume_preview(root, preview, folder, repo, platform)
        else:
            consume_archive(promote, folder, repo, platform, consumer.removesuffix('-archive'))


def observe_consumers(root, folder, maintenance_version, monkeypatch):
    failures = []
    with monkeypatch.context() as patch:
        patch.syspath_prepend(str(root / 'tools/release'))
        patch.setitem(sys.modules, 'plan', load(root, 'tools/release/plan.py'))
        promote = load(root, 'tools/release/promote.py')
        patch.setitem(sys.modules, 'promote', promote)
        modules = (
            promote,
            load(root, 'tools/release/preview.py'),
            load(root, 'tools/ci/pages_update.py'),
        )
        for identity in consumer_cases():
            platform, consumer, damage = identity
            case = folder / platform / consumer / damage
            case.mkdir(parents=True)
            try:
                exercise_consumer(root, modules, case, identity, maintenance_version, patch)
            except Exception as error:  # noqa: BLE001 - report independent consumers together
                if damage == 'none' or not isinstance(error, (ValueError, RuntimeError)):
                    failures.append(
                        f'{platform}/{consumer}/{damage}: {type(error).__name__}: {error}'
                    )
            else:
                if damage != 'none':
                    failures.append(f'{platform}/{consumer}/{damage}: accepted invalid repository')
    assert not failures, (
        'Release consumers must admit the produced platform components, preserve exact '
        'names/checksums and refuse app/feed drift or corrupt maintenance archives: '
        + '; '.join(failures)
    )
