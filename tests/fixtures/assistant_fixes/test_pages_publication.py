# SPDX-License-Identifier: BSD-3-Clause
import importlib.util
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

    assert MODULE.deployed_base(items, jobs)['id'] == 2
    assert calls == [(2, 2)]


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

    assert MODULE.deployed_base(items, jobs)['id'] == 1


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
    assert (site / 'index.html').read_text() == 'new docs without footer'
    assert not (site / 'removed.html').exists()
    assert (site / 'webapp/index.html').read_text() == 'old app'
    assert (site / 'webapp/app.wasm').read_bytes() == b'original compiled app'


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
    assert (site / 'index.html').read_text() == 'latest docs'
    assert (site / 'webapp/index.html').read_text() == 'new app'
    assert (site / 'webapp/kit/edi_app.wasm').read_bytes() == b'new compiled app'


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
    assert (site / 'index.html').read_text() == 'old docs'
    assert (site / 'webapp/index.html').read_text() == 'old app'


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
    assert (repository / 'Updates.xml').read_text() == 'original components'


def test_installers_update_preserves_other_platforms_docs_and_app(tmp_path):
    site, incoming = tmp_path / 'site', tmp_path / 'incoming'
    (site / 'webapp').mkdir(parents=True)
    (site / 'webapp/index.html').write_text('app')
    (site / 'index.html').write_text('docs')
    previous = site / 'repository/testing/windows-x86_64'
    previous.mkdir(parents=True)
    (previous / 'Updates.xml').write_text('previous Windows')
    part = incoming / 'testing/linux-x86_64'
    part.mkdir(parents=True)
    (part / 'Updates.xml').write_text('new Linux')
    MODULE.overlay_component(site, incoming, 'installers')
    assert (previous / 'Updates.xml').read_text() == 'previous Windows'
    assert (site / 'repository/testing/linux-x86_64/Updates.xml').read_text() == 'new Linux'
    assert (site / 'index.html').read_text() == 'docs'
    assert (site / 'webapp/index.html').read_text() == 'app'


def test_incomplete_installer_update_keeps_previous_components(tmp_path):
    site, incoming = tmp_path / 'site', tmp_path / 'incoming'
    (site / 'webapp').mkdir(parents=True)
    (site / 'webapp/index.html').write_text('app')
    (site / 'index.html').write_text('docs')
    (incoming / 'testing/linux-x86_64').mkdir(parents=True)
    with pytest.raises(RuntimeError, match='incomplete'):
        MODULE.overlay_component(site, incoming, 'installers')
    assert (site / 'index.html').read_text() == 'docs'


def test_installer_deployment_is_a_valid_base():
    item = artifact(3, 'pages-site-installers-1', '2026-11-04T21:00:00Z')
    assert (
        MODULE.deployed_base([item], lambda *_: deployed('Deploy installers to GitHub Pages'))
        == item
    )


def test_pages_size_limit_fails_before_publication(tmp_path):
    (tmp_path / 'payload').write_bytes(b'12345')
    assert MODULE.check_site_size(tmp_path, limit=5) == 5
    with pytest.raises(RuntimeError, match='too large'):
        MODULE.check_site_size(tmp_path, limit=4)


def test_new_metadata_retains_previous_downloads_and_rejects_reused_identity(tmp_path):
    site, incoming = tmp_path / 'site', tmp_path / 'incoming'
    (site / 'webapp').mkdir(parents=True)
    (site / 'webapp/index.html').write_text('app')
    (site / 'index.html').write_text('docs')
    old = site / 'repository/testing/linux-x86_64'
    old.mkdir(parents=True)
    (old / 'Updates.xml').write_text('old metadata')
    (old / '1.0.0content.7z').write_bytes(b'old download in flight')
    new = incoming / 'testing/linux-x86_64'
    new.mkdir(parents=True)
    (new / 'Updates.xml').write_text('new metadata')
    (new / '2.0.0content.7z').write_bytes(b'new download')
    MODULE.overlay_component(site, incoming, 'installers')
    assert (old / '1.0.0content.7z').read_bytes() == b'old download in flight'
    assert (old / 'Updates.xml').read_text() == 'new metadata'
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
    assert library.read_bytes() == b'pinned report library'


def test_invalid_channel_cannot_escape_the_repository_root(tmp_path):
    site, incoming = tmp_path / 'site', tmp_path / 'incoming'
    (incoming / 'unexpected/linux-x86_64').mkdir(parents=True)
    with pytest.raises(RuntimeError, match='channel'):
        MODULE.overlay_installers(site, incoming)
    assert not site.exists()
