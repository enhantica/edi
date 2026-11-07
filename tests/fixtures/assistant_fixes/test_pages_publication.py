# SPDX-License-Identifier: BSD-3-Clause
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('pages_update', ROOT / 'tools/ci/pages_update.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def artifact(run, name, created, *, expired=False):
    return {
        'id': run,
        'name': name,
        'created_at': created,
        'expired': expired,
        'workflow_run': {'id': run},
    }


def updates(version):
    """Repository metadata offering the application at one version."""
    return (
        '<Updates><PackageUpdate><Name>org.easyscience.edi</Name>'
        f'<Version>{version}</Version></PackageUpdate></Updates>'
    )


def preview_feed(version):
    return json.dumps({'schema': 'edi.preview-releases/1', 'releases': [{'version': version}]})


def deployed(step, state='success', completed='2026-11-04T22:00:00Z'):
    return [{'steps': [{'name': step, 'conclusion': state, 'completed_at': completed}]}]


def test_uses_deployed_component_while_other_build_is_running():
    items = [
        artifact(1, 'github-pages', '2026-11-04T18:00:00Z'),
        artifact(2, 'pages-site-docs-2', '2026-11-04T20:00:00Z'),
    ]
    calls = []

    def jobs(run, attempt):
        calls.append((run, attempt))
        return deployed('Deploy documentation to GitHub Pages') + [
            {'name': 'build WebAssembly', 'status': 'in_progress', 'steps': []}
        ]

    assert MODULE.deployed_base(items, jobs)['id'] == 2, (
        'Uses deployed component while other build is running.'
    )
    assert calls == [(2, 2)], 'Uses deployed component while other build is running.'


def test_rejected_and_not_yet_deployed_artifacts_do_not_replace_base():
    items = [
        artifact(1, 'github-pages', '2026-11-04T18:00:00Z'),
        artifact(2, 'pages-site-docs-1', '2026-11-04T19:00:00Z'),
        artifact(3, 'pages-site-wasm-1', '2026-11-04T20:00:00Z'),
    ]

    def jobs(run, _attempt):
        if run == 1:
            return deployed('Deploy to GitHub Pages')
        if run == 2:
            return deployed('Deploy documentation to GitHub Pages', 'failure')
        return deployed('Deploy WebAssembly to GitHub Pages', None)

    assert MODULE.deployed_base(items, jobs)['id'] == 1, (
        'Rejected and not yet deployed artifacts do not replace base.'
    )


def test_other_component_or_attempt_cannot_prove_deployment():
    items = [artifact(2, 'pages-site-docs-2', '2026-11-04T20:00:00Z')]
    with pytest.raises(RuntimeError, match='No retained deployed'):
        MODULE.deployed_base(
            items, lambda _run, _attempt: deployed('Deploy WebAssembly to GitHub Pages')
        )


def test_expired_and_unrelated_artifacts_are_not_used():
    items = [
        artifact(1, 'github-pages', '2026-11-04T18:00:00Z', expired=True),
        artifact(2, 'pages-docs', '2026-11-04T19:00:00Z'),
    ]
    with pytest.raises(RuntimeError, match='No retained deployed'):
        MODULE.deployed_base(items, lambda *_: pytest.fail('Invalid candidate queried'))


def test_docs_update_preserves_web_app_and_removes_stale_docs(tmp_path):
    site = tmp_path / 'site'
    (site / 'webapp').mkdir(parents=True)
    (site / 'webapp/index.html').write_text('old app')
    (site / 'webapp/app.wasm').write_bytes(b'original compiled app')
    (site / 'index.html').write_text('old docs')
    (site / 'removed.html').write_text('stale')
    docs = tmp_path / 'docs'
    docs.mkdir()
    (docs / 'index.html').write_text('new docs without footer')
    MODULE.overlay_component(site, docs, 'docs')
    assert (site / 'index.html').read_text() == 'new docs without footer', (
        'Docs update preserves web app and removes stale docs.'
    )
    assert not (site / 'removed.html').exists(), (
        'Docs update preserves web app and removes stale docs.'
    )
    assert (site / 'webapp/index.html').read_text() == 'old app', (
        'Docs update preserves web app and removes stale docs.'
    )
    assert (site / 'webapp/app.wasm').read_bytes() == b'original compiled app', (
        'Docs update preserves web app and removes stale docs.'
    )


def test_wasm_update_preserves_current_docs(tmp_path):
    site = tmp_path / 'site'
    (site / 'webapp').mkdir(parents=True)
    (site / 'webapp/index.html').write_text('old app')
    (site / 'index.html').write_text('latest docs')
    app = tmp_path / 'app'
    (app / 'kit').mkdir(parents=True)
    (app / 'index.html').write_text('new app')
    (app / 'build.json').write_text('{"singlethread": "kit"}')
    (app / 'coi-serviceworker.js').write_text('worker')
    (app / 'kit/edi_app.wasm').write_bytes(b'new compiled app')
    MODULE.overlay_component(site, app, 'wasm')
    assert (site / 'index.html').read_text() == 'latest docs', (
        'WebAssembly update preserves current docs.'
    )
    assert (site / 'webapp/index.html').read_text() == 'new app', (
        'WebAssembly update preserves current docs.'
    )
    assert (site / 'webapp/kit/edi_app.wasm').read_bytes() == b'new compiled app', (
        'WebAssembly update preserves current docs.'
    )


@pytest.mark.parametrize('reserved', ['webapp', 'repository', 'third-party'])
def test_docs_must_not_replace_reserved_component(tmp_path, reserved):
    site = tmp_path / 'site'
    (site / 'webapp').mkdir(parents=True)
    (site / 'index.html').write_text('old docs')
    (site / 'webapp/index.html').write_text('old app')
    docs = tmp_path / 'docs'
    (docs / reserved).mkdir(parents=True)
    (docs / 'index.html').write_text('new docs')
    with pytest.raises(RuntimeError, match='must not own'):
        MODULE.overlay_component(site, docs, 'docs')
    assert (site / 'index.html').read_text() == 'old docs', (
        'Docs must not replace reserved component.'
    )
    assert (site / 'webapp/index.html').read_text() == 'old app', (
        'Docs must not replace reserved component.'
    )


def test_docs_update_preserves_installer_components(tmp_path):
    site, docs = tmp_path / 'site', tmp_path / 'docs'
    (site / 'webapp').mkdir(parents=True)
    (site / 'webapp/index.html').write_text('app')
    (site / 'index.html').write_text('old docs')
    repository = site / 'repository/testing/linux-x86_64'
    repository.mkdir(parents=True)
    (repository / 'Updates.xml').write_text('original components')
    docs.mkdir()
    (docs / 'index.html').write_text('new docs')
    MODULE.overlay_component(site, docs, 'docs')
    assert (repository / 'Updates.xml').read_text() == 'original components', (
        'Docs update preserves installer components.'
    )


def test_installers_update_preserves_other_platforms_docs_and_app(tmp_path):
    site, incoming = tmp_path / 'site', tmp_path / 'incoming'
    (site / 'webapp').mkdir(parents=True)
    (site / 'webapp/index.html').write_text('app')
    (site / 'index.html').write_text('docs')
    previous = site / 'repository/testing/windows-x86_64'
    previous.mkdir(parents=True)
    (previous / 'Updates.xml').write_text(updates('2026.11.1') + '<!-- previous Windows -->')
    (site / 'releases').mkdir()
    (site / 'releases/testing.json').write_text(preview_feed('2026.11.1'))
    part = incoming / 'testing/linux-x86_64'
    part.mkdir(parents=True)
    (part / 'Updates.xml').write_text(updates('2026.11.1') + '<!-- new Linux -->')
    MODULE.overlay_component(site, incoming, 'installers')
    assert (previous / 'Updates.xml').read_text().endswith('<!-- previous Windows -->'), (
        'Installers update preserves other platforms docs and app.'
    )
    linux = site / 'repository/testing/linux-x86_64/Updates.xml'
    assert linux.read_text().endswith('<!-- new Linux -->'), (
        'Installers update preserves other platforms docs and app.'
    )
    assert (site / 'index.html').read_text() == 'docs', (
        'Installers update preserves other platforms docs and app.'
    )
    assert (site / 'webapp/index.html').read_text() == 'app', (
        'Installers update preserves other platforms docs and app.'
    )


def test_incomplete_installer_update_keeps_previous_components(tmp_path):
    site, incoming = tmp_path / 'site', tmp_path / 'incoming'
    (site / 'webapp').mkdir(parents=True)
    (site / 'webapp/index.html').write_text('app')
    (site / 'index.html').write_text('docs')
    (incoming / 'testing/linux-x86_64').mkdir(parents=True)
    with pytest.raises(RuntimeError, match='incomplete'):
        MODULE.overlay_component(site, incoming, 'installers')
    assert (site / 'index.html').read_text() == 'docs', (
        'Incomplete installer update keeps previous components.'
    )


def test_installer_deployment_is_a_valid_base():
    item = artifact(3, 'pages-site-installers-1', '2026-11-04T21:00:00Z')
    assert (
        MODULE.deployed_base([item], lambda *_: deployed('Deploy installers to GitHub Pages'))
        == item
    ), 'Installer deployment is a valid base.'


def test_pages_size_limit_fails_before_publication(tmp_path):
    (tmp_path / 'payload').write_bytes(b'12345')
    assert MODULE.check_site_size(tmp_path, limit=5) == 5, (
        'Pages size limit fails before publication.'
    )
    with pytest.raises(RuntimeError, match='too large'):
        MODULE.check_site_size(tmp_path, limit=4)


def test_new_metadata_retains_previous_downloads_and_rejects_reused_identity(tmp_path):
    site, incoming = tmp_path / 'site', tmp_path / 'incoming'
    (site / 'webapp').mkdir(parents=True)
    (site / 'webapp/index.html').write_text('app')
    (site / 'index.html').write_text('docs')
    old = site / 'repository/testing/linux-x86_64'
    old.mkdir(parents=True)
    (old / 'Updates.xml').write_text(updates('1.0.0'))
    (old / '1.0.0content.7z').write_bytes(b'old download in flight')
    new = incoming / 'testing/linux-x86_64'
    new.mkdir(parents=True)
    (new / 'Updates.xml').write_text(updates('2.0.0'))
    (new / '2.0.0content.7z').write_bytes(b'new download')
    (new.parent / 'feed.json').write_text(preview_feed('2.0.0'))
    MODULE.overlay_component(site, incoming, 'installers')
    assert (old / '1.0.0content.7z').read_bytes() == b'old download in flight', (
        'New metadata retains previous downloads and rejects reused identity.'
    )
    assert (old / 'Updates.xml').read_text() == updates('2.0.0'), (
        'New metadata retains previous downloads and rejects reused identity.'
    )
    (new / '2.0.0content.7z').write_bytes(b'changed under an existing version')
    with pytest.raises(RuntimeError, match='identity was reused'):
        MODULE.overlay_component(site, incoming, 'installers')


def test_docs_preserve_versioned_third_party_report_libraries(tmp_path):
    site, docs = tmp_path / 'site', tmp_path / 'docs'
    (site / 'webapp').mkdir(parents=True)
    (site / 'webapp/index.html').write_text('app')
    (site / 'index.html').write_text('old docs')
    library = site / 'third-party/plotly/1.0/plotly.min.js'
    library.parent.mkdir(parents=True)
    library.write_bytes(b'pinned report library')
    docs.mkdir()
    (docs / 'index.html').write_text('new docs')
    MODULE.overlay_component(site, docs, 'docs')
    assert library.read_bytes() == b'pinned report library', (
        'Docs preserve versioned third party report libraries.'
    )


def test_invalid_channel_cannot_escape_the_repository_root(tmp_path):
    site, incoming = tmp_path / 'site', tmp_path / 'incoming'
    (incoming / 'unexpected/linux-x86_64').mkdir(parents=True)
    with pytest.raises(RuntimeError, match='channel'):
        MODULE.overlay_installers(site, incoming)
    assert not site.exists(), 'Invalid channel cannot escape the repository root.'


def test_documentation_refresh_preserves_the_installed_app_release_feed(tmp_path):
    site, incoming = tmp_path / 'site', tmp_path / 'docs'
    (site / 'webapp').mkdir(parents=True)
    (site / 'webapp/index.html').write_text('app')
    (site / 'index.html').write_text('old docs')
    (site / 'releases').mkdir()
    (site / 'releases/stable.json').write_bytes(b'qualified release feed')
    incoming.mkdir()
    (incoming / 'index.html').write_text('new docs')
    MODULE.overlay_component(site, incoming, 'docs')
    assert (site / 'releases/stable.json').read_bytes() == b'qualified release feed', (
        'Documentation refresh preserves the installed app release feed.'
    )


def test_testing_feed_keeps_stable_and_rejects_stale_preview(tmp_path):
    site, incoming = tmp_path / 'site', tmp_path / 'incoming'
    stable = site / 'releases/stable.json'
    stable.parent.mkdir(parents=True)
    stable.write_text('stable history')
    (site / 'index.html').write_text('documentation')
    (site / 'webapp').mkdir()
    (site / 'webapp/index.html').write_text('web app')
    target = incoming / 'testing/macos-arm64'
    target.mkdir(parents=True)
    feed = target.parent / 'feed.json'

    for version in ['2026.11.1', '2026.11.2']:
        (target / 'Updates.xml').write_text(updates(version))
        feed.write_text(
            json.dumps({
                'schema': 'edi.preview-releases/1',
                'releases': [{'version': version}],
            })
        )
        MODULE.overlay_component(site, incoming, 'installers')
    actual = json.loads((stable.parent / 'testing.json').read_text())
    assert [entry['version'] for entry in actual['releases']] == ['2026.11.2', '2026.11.1'], (
        'Testing feed keeps stable and rejects stale preview.'
    )
    assert stable.read_text() == 'stable history', (
        'Testing feed keeps stable and rejects stale preview.'
    )
    feed.write_text(
        json.dumps({
            'schema': 'edi.preview-releases/1',
            'releases': [{'version': '2026.11.1'}],
        })
    )
    with pytest.raises(RuntimeError, match='cannot move backwards'):
        MODULE.overlay_component(site, incoming, 'installers')


def test_testing_retention_keeps_two_versions_and_preserves_stable(tmp_path):
    site = tmp_path / 'site'
    releases = site / 'releases'
    releases.mkdir(parents=True)
    existing = ['2026.11.1', '2026.11.0']
    (releases / 'testing.json').write_text(
        json.dumps({
            'schema': 'edi.preview-releases/1',
            'sequence': 'calendar',
            'releases': [{'version': version} for version in existing],
        })
    )
    for channel in ['testing', 'stable']:
        root = site / 'repository' / channel / 'macos-arm64/org.easyscience.edi'
        root.mkdir(parents=True)
        for version in [*existing, '2026.11.2', '0.0.49.1']:
            for suffix in ['.7z', '.7z.sha1']:
                (root / f'{version}bin{suffix}').write_text('archive fixture')
    incoming = tmp_path / 'incoming/feed.json'
    incoming.parent.mkdir()
    macos = incoming.parent / 'macos-arm64'
    macos.mkdir()
    (macos / 'Updates.xml').write_text('qualified metadata')
    windows = site / 'repository/testing/windows-x86_64/org.easyscience.edi'
    windows.mkdir(parents=True)
    (windows / '2026.11.0bin.7z').write_text('other platform')
    incoming.write_text(
        json.dumps({
            'schema': 'edi.preview-releases/1',
            'sequence': 'calendar',
            'releases': [{'version': '2026.11.2'}],
        })
    )
    MODULE.overlay_testing_feed(site, incoming)
    testing = site / 'repository/testing/macos-arm64/org.easyscience.edi'
    assert sorted(path.name for path in testing.iterdir()) == [
        '2026.11.1bin.7z',
        '2026.11.1bin.7z.sha1',
        '2026.11.2bin.7z',
        '2026.11.2bin.7z.sha1',
    ], 'Testing retention keeps two versions and preserves stable.'
    stable = site / 'repository/stable/macos-arm64/org.easyscience.edi'
    assert len(list(stable.iterdir())) == 8, (
        'Testing retention keeps two versions and preserves stable.'
    )
    assert (windows / '2026.11.0bin.7z').is_file(), (
        'Testing retention keeps two versions and preserves stable.'
    )


def test_production_components_use_the_public_platform_path(tmp_path):
    site = tmp_path / 'site'
    site.mkdir()
    incoming = tmp_path / 'incoming'
    repository = incoming / 'stable/macos-arm64'
    repository.mkdir(parents=True)
    (repository / 'Updates.xml').write_text('qualified metadata')

    MODULE.overlay_installers(site, incoming)

    public = site / 'repository/macos-arm64/Updates.xml'
    assert public.read_text() == 'qualified metadata', (
        'Production components use the public platform path.'
    )
    assert not (site / 'repository/stable').exists(), (
        'Production components use the public platform path.'
    )


def test_pages_budget_prunes_only_unreferenced_preview_archives(tmp_path):
    platform = tmp_path / 'repository/testing/macos-arm64'
    package = platform / 'org.easyscience.edi'
    package.mkdir(parents=True)
    metadata = platform / 'Updates.xml'
    metadata.write_text(
        '<Updates><PackageUpdate><Version>2026.11.2</Version></PackageUpdate></Updates>'
    )
    old = package / '2026.11.1bin.7z'
    old.write_bytes(b'older archive')
    live = package / '2026.11.2bin.7z'
    live.write_bytes(b'live archive')
    budget = metadata.stat().st_size + live.stat().st_size
    assert MODULE.check_site_size(tmp_path, limit=budget) == budget, (
        'Pages budget prunes only unreferenced preview archives.'
    )
    assert live.is_file() and not old.exists(), (
        'Pages budget prunes only unreferenced preview archives.'
    )


def calendar_site(tmp_path, version='2026.11.6'):
    """A deployed site whose three testing repositories agree with its calendar feed."""
    site = tmp_path / 'site'
    (site / 'webapp').mkdir(parents=True)
    (site / 'webapp/index.html').write_text('app')
    (site / 'index.html').write_text('docs')
    (site / 'releases').mkdir()
    feed = json.loads(preview_feed(version))
    (site / 'releases/testing.json').write_text(json.dumps({**feed, 'sequence': 'calendar'}))
    for platform in ['linux-x86_64', 'macos-arm64', 'windows-x86_64']:
        repository = site / 'repository/testing' / platform
        repository.mkdir(parents=True)
        (repository / 'Updates.xml').write_text(updates(version))
    return site


@pytest.mark.parametrize('route', ['installers', 'release-stable', 'stable-without-feed'])
def test_diagnostic_components_cannot_replace_a_calendar_feed(tmp_path, route):
    site, incoming = calendar_site(tmp_path), tmp_path / 'incoming'
    platforms = ['linux-x86_64', 'macos-arm64', 'windows-x86_64']
    channel = 'testing' if route == 'installers' else 'stable'
    root = incoming / 'repository' if route == 'release-stable' else incoming
    for platform in platforms:
        part = root / channel / platform
        part.mkdir(parents=True)
        (part / 'Updates.xml').write_text(updates('0.0.42.1'))
    if route == 'release-stable':
        (incoming / 'releases').mkdir()
        (incoming / 'releases/stable.json').write_text(
            json.dumps({'schema': 'edi.releases/1', 'releases': [{'version': '2026.11.0'}]})
        )
    component = 'release' if route == 'release-stable' else 'installers'
    with pytest.raises(RuntimeError, match='feed'):
        MODULE.overlay_component(site, incoming, component)


def test_one_platform_cannot_move_ahead_of_the_others(tmp_path):
    site, incoming = calendar_site(tmp_path), tmp_path / 'incoming'
    part = incoming / 'testing/linux-x86_64'
    part.mkdir(parents=True)
    (part / 'Updates.xml').write_text(updates('2026.11.7'))
    feed = json.loads(preview_feed('2026.11.7'))
    (part.parent / 'feed.json').write_text(json.dumps({**feed, 'sequence': 'calendar'}))
    with pytest.raises(RuntimeError, match='macos-arm64 offers'):
        MODULE.overlay_component(site, incoming, 'installers')


def test_a_complete_calendar_preview_moves_feed_and_repositories_together(tmp_path):
    site, incoming = calendar_site(tmp_path), tmp_path / 'incoming'
    for platform in ['linux-x86_64', 'macos-arm64', 'windows-x86_64']:
        part = incoming / 'testing' / platform
        part.mkdir(parents=True)
        (part / 'Updates.xml').write_text(updates('2026.11.7'))
    feed = json.loads(preview_feed('2026.11.7'))
    (incoming / 'testing/feed.json').write_text(json.dumps({**feed, 'sequence': 'calendar'}))
    MODULE.overlay_component(site, incoming, 'installers')
    published = json.loads((site / 'releases/testing.json').read_text())
    assert [entry['version'] for entry in published['releases']] == ['2026.11.7', '2026.11.6'], (
        'A complete calendar preview moves feed and repositories together.'
    )
