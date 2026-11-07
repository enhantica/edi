# SPDX-License-Identifier: BSD-3-Clause
"""Release boundaries checked with synthetic receipts and filesystem conservation."""

import copy
import datetime
import hashlib
import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


@pytest.fixture
def release_modules(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools/release'))
    return module('release_plan_reference', 'tools/release/plan.py'), module(
        'release_promotion_reference', 'tools/release/promote.py'
    )


@pytest.mark.parametrize(
    ('known', 'date', 'expected'),
    [
        ([], '2026-11-07', '2026.11.0'),
        (['2026.11.9', '2026.11.10', '2026.10.99'], '2026-11-07', '2026.11.11'),
        (['2026.12.44'], '2027-01-01', '2027.01.0'),
    ],
)
def test_calendar_uses_numeric_monthly_sequence(release_modules, known, date, expected):
    plan, _ = release_modules
    assert plan.next_calendar_version(known, datetime.date.fromisoformat(date)) == expected, (
        'Calendar allocation must increment the numeric sequence and reset in a new month'
    )


def test_calendar_refuses_clock_rollback(release_modules):
    plan, _ = release_modules
    with pytest.raises(ValueError, match='backwards'):
        plan.next_calendar_version(['2027.01.0'], datetime.date(2026, 12, 31))


def qualification():
    run = {
        'path': '.github/workflows/installers.yml',
        'head_branch': 'main',
        'status': 'completed',
        'conclusion': 'success',
        'event': 'workflow_dispatch',
        'run_attempt': 3,
    }
    jobs = [
        {'name': name, 'run_attempt': 3, 'conclusion': 'success'}
        for name in [
            'installer · Linux',
            'installer · macOS',
            'installer · Windows',
            'record qualified release inputs',
        ]
    ]
    names = ['qualified-release-plan-3'] + [
        f'{kind}-{platform}-3'
        for platform in ['Linux', 'macOS', 'Windows']
        for kind in ['installer', 'installer-components']
    ]
    artifacts = [{'name': name, 'id': i + 1, 'expired': False} for i, name in enumerate(names)]
    return run, artifacts, jobs


def test_promotion_requires_complete_single_attempt(release_modules):
    _, promote = release_modules
    run, artifacts, jobs = qualification()
    selected = promote.qualified_artifacts(run, artifacts, jobs)
    assert set(selected.values()) == set(range(1, 8)), (
        'Promotion must retain all three platform deliveries, repositories and the exact plan'
    )


@pytest.mark.parametrize(
    'fault', ['missing-platform', 'older-attempt', 'expired', 'duplicate', 'red']
)
def test_promotion_refuses_incomplete_or_ambiguous_evidence(release_modules, fault):
    _, promote = release_modules
    run, artifacts, jobs = qualification()
    if fault == 'missing-platform':
        jobs.pop(1)
    elif fault == 'older-attempt':
        jobs[1]['run_attempt'] = 2
    elif fault == 'expired':
        artifacts[2]['expired'] = True
    elif fault == 'duplicate':
        artifacts.append(copy.deepcopy(artifacts[2]))
    else:
        jobs[1]['conclusion'] = 'failure'
    with pytest.raises(ValueError, match=r'qualify|missing|expired|ambiguous'):
        promote.qualified_artifacts(run, artifacts, jobs)


def tree(folder):
    return {
        p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()
    }


def test_docs_publication_conserves_deployed_components(tmp_path):
    pages = module('pages_reference', 'tools/ci/pages_update.py')
    site, incoming = tmp_path / 'site', tmp_path / 'incoming'
    originals = {
        'index.html': b'old docs',
        'stale.html': b'removed docs',
        'webapp/index.html': b'app',
        'webapp/module.wasm': b'\x00asm',
        'repository/testing/linux-x86_64/Updates.xml': b'qualified components',
        'repository/linux-x86_64/component.7z': b'immutable archive',
        'releases/testing.json': b'published feed',
        'third-party/vendor.js': b'offline report',
    }
    for relative, content in originals.items():
        path = site / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    incoming.mkdir()
    (incoming / 'index.html').write_text('new docs')
    pages.overlay_component(site, incoming, 'docs')
    expected = {k: v for k, v in originals.items() if k not in {'index.html', 'stale.html'}}
    assert tree(site) == {**expected, 'index.html': b'new docs'}, (
        'Publishing docs must preserve every deployed app, component, feed and vendor byte'
    )


def test_newer_undeployed_site_is_not_a_publication_reference():
    pages = module('pages_reference_select', 'tools/ci/pages_update.py')
    artifacts = [
        {
            'id': i,
            'name': 'pages-site-docs-1',
            'expired': False,
            'created_at': f'2026-11-0{i}T12:00:00Z',
            'workflow_run': {'id': i},
        }
        for i in [1, 2]
    ]

    def jobs(run, _attempt):
        return [
            {
                'steps': [
                    {
                        'name': 'Deploy documentation to GitHub Pages',
                        'conclusion': 'success' if run == 1 else 'failure',
                        'completed_at': f'2026-11-0{run}T13:00:00Z',
                    }
                ]
            }
        ]

    assert pages.deployed_base(artifacts, jobs)['id'] == 1, (
        'The preservation base must be deployed, even when a newer build artifact exists'
    )


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.append(dict(attrs))


def test_python_index_exposes_only_public_hash_bound_wheels(tmp_path):
    index = module('package_index_reference', 'website/render_package_index.py')
    version = '2026.11.6'
    name = f'easydiffraction-{version}-cp312-abi3-linux_x86_64.whl'
    url = f'https://github.com/enhantica/edi/releases/download/v{version}/{name}'
    checksum = hashlib.sha256(b'independent wheel bytes').hexdigest()
    asset = {
        'name': name,
        'browser_download_url': url,
        'state': 'uploaded',
        'digest': f'sha256:{checksum}',
    }
    public = {'tag_name': f'v{version}', 'draft': False, 'prerelease': True, 'assets': [asset]}
    draft = copy.deepcopy(public)
    draft['draft'] = True
    draft['assets'][0]['name'] = name.replace('linux_x86_64', 'win_amd64')
    bad = copy.deepcopy(asset)
    bad['digest'] = None
    public['assets'].append(bad)
    index.write_package_index(tmp_path, [[draft], [public]])
    parser = Links()
    parser.feed((tmp_path / 'pypi/simple/easydiffraction/index.html').read_text())
    assert parser.links == [
        {'href': f'{url}#sha256={checksum}', 'data-requires-python': '>=3.12'}
    ], 'The simple index must expose a published immutable wheel with its SHA-256 and Python floor'


def test_distribution_mirror_uses_the_declared_singular_host():
    policy = json.loads((ROOT / 'data/distribution.json').read_text())
    assert policy['mirror_bases'] == ['https://download.easydiffraction.org/'], (
        'The optional download mirror must use the singular host chosen for distribution'
    )


def deliveries(tmp_path):
    version, commit = '2026.11.17', 'a' * 40
    release = {
        'version': version,
        'commit': commit,
        'date': '2026-11-07',
        'notes': {
            'Added': [
                {'title': 'Save fitted projects', 'pull_request': 17, 'interfaces': ['desktop']}
            ],
            'Fixed': [],
            'Changed': [],
        },
    }
    history = json.dumps({
        'schema': 'edi.preview-releases/1',
        'sequence': 'calendar',
        'releases': [release],
    }).encode()
    result = []
    for platform in ['linux-x86_64', 'macos-arm64', 'windows-x86_64']:
        folder = tmp_path / platform
        folder.mkdir()
        archive = folder / f'EasyDiffraction-{version}-{platform}-online.zip'
        archive.write_bytes(b'qualified installer ' + platform.encode())
        (folder / 'preview-history.json').write_bytes(history)
        metadata = {
            'version': version,
            'platform': platform,
            'kind': 'online',
            'edi_commit': commit,
            'zip': archive.name,
            'zip_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'repository_url': f'https://enhantica.github.io/edi/repository/testing/{platform}/',
        }
        (folder / 'installer.json').write_text(json.dumps(metadata))
        (folder / 'qualification.json').write_text(
            json.dumps({
                'passed': True,
                'smoke': {
                    'passed': True,
                    'app_version': version,
                    'release_history_sha256': hashlib.sha256(history).hexdigest(),
                },
            })
        )
        result.append(folder)
    return commit, release, result


@pytest.mark.usefixtures('release_modules')
def test_draft_preparation_retains_qualified_platform_bytes(tmp_path):
    draft = module('draft_reference', 'tools/release/preview_draft.py')
    commit, release, folders = deliveries(tmp_path)
    before = {f.name: tree(f) for f in folders}
    actual, notes, assets = draft.prepare(commit, folders)
    assert actual == release and 'Save fitted projects' in notes, (
        'A draft must retain the source identity and user notes qualified by every platform'
    )
    assert len(assets) == 3 and all(
        hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in assets
    ), 'Draft preparation must return the exact qualified archive bytes without rebuilding'
    assert {f.name: tree(f) for f in folders} == before, (
        'Preparing a draft must not change the retained qualification evidence'
    )


@pytest.mark.parametrize('fault', ['bytes', 'source', 'history', 'missing-platform'])
@pytest.mark.usefixtures('release_modules')
def test_draft_preparation_refuses_identity_drift(tmp_path, fault):
    draft = module('draft_reference_bad', 'tools/release/preview_draft.py')
    commit, _, folders = deliveries(tmp_path)
    if fault == 'bytes':
        next(folders[0].glob('*.zip')).write_bytes(b'replaced delivery')
    elif fault == 'source':
        commit = 'b' * 40
    elif fault == 'history':
        (folders[0] / 'preview-history.json').write_text('{}')
    else:
        folders.pop()
    with pytest.raises(ValueError, match=r'differ|missing'):
        draft.prepare(commit, folders)


def test_skill_checker_refuses_an_independently_missing_target(tmp_path):
    checker = module('skill_checker_reference', 'tools/checks/assistant_skill_targets.py')
    guide = tmp_path / 'guide/SKILL.md'
    guide.parent.mkdir()
    guide.write_text('Open ui:independently.missing.control\n')
    errors = checker.check_targets(tmp_path, ROOT / 'app/qml')
    assert any('independently.missing.control' in error for error in errors), (
        'The skill check must reject a target absent from the current app object declarations'
    )
