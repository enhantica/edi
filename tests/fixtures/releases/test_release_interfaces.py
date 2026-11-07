# SPDX-License-Identifier: BSD-3-Clause
"""Round-trip interface labels from a merged PR through GitHub and the docs."""

import datetime
import importlib.util
from pathlib import Path

import pytest


def load(path):
    source = Path(__file__).resolve().parents[3] / path
    spec = importlib.util.spec_from_file_location(source.stem, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PLAN = load('tools/release/plan.py')
DOCS = load('website/render_release_notes.py')
COMMIT = 'a' * 40


def plan_with_labels(*labels):
    request = {
        'number': 3,
        'title': 'Improve plot zoom',
        'merged_at': '2026-11-04T12:00:00Z',
        'merge_commit_sha': COMMIT,
        'labels': ['[scope] bug', *labels],
    }
    return PLAN.release_plan(
        [request],
        [],
        COMMIT,
        {COMMIT},
        datetime.date(2026, 11, 5),
    )


def test_interface_labels_render_once():
    release = plan_with_labels('[interface] web', '[interface] desktop')
    assert release['notes']['Fixed'][0]['interfaces'] == ['desktop', 'web'], (
        'Interface labels render once.'
    )
    github = PLAN.markdown_notes(release)
    assert 'Improve plot zoom' in github, 'Interface labels render once.'
    assert github.rstrip().endswith('`desktop` `web` <!-- interfaces: desktop,web -->'), (
        'Interface labels render once.'
    )
    published = {
        'draft': False,
        'prerelease': True,
        'name': 'edi 2026.11.0',
        'published_at': '2026-11-05T12:00:00Z',
        'html_url': 'https://github.com/enhantica/edi/releases/tag/v2026.11.0',
        'body': github,
    }
    page = DOCS.render([[published, {**published, 'draft': True, 'name': 'Private draft'}]])
    assert page.count('.ed-release-interface') == 2, 'Interface labels render once.'
    assert ':fa5-desktop: Desktop app' in page, 'Interface labels render once.'
    assert ':fa5-globe: Web app' in page, 'Interface labels render once.'
    assert '`desktop`' not in page, 'Interface labels render once.'
    assert 'Private draft' not in page, 'Interface labels render once.'
    assert page.index('Improve plot zoom') < page.index(':fa5-desktop: Desktop app'), (
        'Interface labels render once.'
    )


def test_notes_without_interfaces_keep_their_existing_text():
    assert PLAN.markdown_note({'title': 'Improve plot zoom'}) == '- Improve plot zoom', (
        'Notes without interfaces keep their existing text.'
    )


def test_unknown_interface_fails_instead_of_losing_the_label():
    with pytest.raises(ValueError, match='unique known identifiers'):
        PLAN.markdown_note({'title': 'Improve plot zoom', 'interfaces': ['unknown']})


def test_new_notes_require_at_least_one_interface():
    with pytest.raises(ValueError, match='at least one release interface label'):
        plan_with_labels()


def test_one_note_can_affect_every_interface():
    interfaces = list(PLAN.INTERFACES)
    release = plan_with_labels(
        *(f'[interface] {PLAN.INTERFACES[key][2]}' for key in reversed(interfaces))
    )
    assert release['notes']['Fixed'][0]['interfaces'] == interfaces, (
        'One note can affect every interface.'
    )


def test_desktop_downloads_link_only_published_platform_assets():
    downloads = load('website/render_downloads.py')
    source = '<p>Desktop installers will appear here when published.</p>' + ''.join(
        f'<a data-download-platform="{platform}" aria-disabled="true"></a>'
        for platform in downloads.PLATFORMS
    )

    def release(version, *, draft=False, prerelease=False, platforms=downloads.PLATFORMS):
        base = f'https://github.com/enhantica/edi/releases/download/v{version}'
        return {
            'tag_name': f'v{version}',
            'published_at': '2026-11-05T11:30:00Z',
            'draft': draft,
            'prerelease': prerelease,
            'assets': [
                {
                    'state': 'uploaded',
                    'browser_download_url': (
                        f'{base}/EasyDiffraction-{version}-{platform}-online.zip'
                    ),
                }
                for platform in platforms
            ],
        }

    preview = release('2026.11.0', prerelease=True, platforms=('macos-arm64', 'linux-x86_64'))
    draft = release('2026.11.1', draft=True)
    assert downloads.render(source, [[draft]]) == source, (
        'Desktop downloads link only published platform assets.'
    )
    page = downloads.render(source, [[preview, draft]])
    assert 'Latest version 2026.11.0 (5 Nov 2026)' in page, (
        'Desktop downloads link only published platform assets.'
    )
    assert 'macos-arm64-online.zip' in page and 'linux-x86_64-online.zip' in page, (
        'Desktop downloads link only published platform assets.'
    )
    assert 'data-download-platform="windows-x86_64" aria-disabled="true"' in page, (
        'Desktop downloads link only published platform assets.'
    )
    stable = release('2026.10.2')
    page = downloads.render(source, [[preview, draft, stable]])
    assert 'Latest version 2026.10.2 (5 Nov 2026)' in page, (
        'Desktop downloads link only published platform assets.'
    )
    assert 'EasyDiffraction-2026.10.2-windows-x86_64-online.zip' in page, (
        'Desktop downloads link only published platform assets.'
    )


def test_standalone_downloads_select_only_published_cli_zips():
    downloads = load('website/render_downloads.py')
    root = Path(__file__).resolve().parents[3]
    source = (root / 'website/surfaces/docs/cli/standalone.md').read_text(encoding='utf-8')
    base = 'https://github.com/enhantica/edi/releases/download/v2026.11.4/'
    release = {
        'tag_name': 'v2026.11.4',
        'published_at': '2026-11-05T11:30:00Z',
        'draft': True,
        'prerelease': True,
        'assets': [
            {'state': 'uploaded', 'browser_download_url': base + name}
            for name in (
                'EasyDiffraction-2026.11.4-linux-x86_64-cli.zip',
                'EasyDiffraction-2026.11.4-windows-x86_64-online.zip',
            )
        ],
    }
    assert downloads.render(source, [[release]], kind='cli') == source, (
        'Standalone downloads select only published CLI zips.'
    )
    release['draft'] = False
    page = downloads.render(source, [[release]], kind='cli')
    assert 'Latest version 2026.11.4 (5 Nov 2026)' in page, (
        'Standalone downloads select only published CLI zips.'
    )
    assert base + 'EasyDiffraction-2026.11.4-linux-x86_64-cli.zip' in page, (
        'Standalone downloads select only published CLI zips.'
    )
    assert 'data-download-platform="windows-x86_64" aria-disabled="true"' in page, (
        'Standalone downloads select only published CLI zips.'
    )


def test_preview_index_links_only_published_hashed_python_wheels(tmp_path):
    index = load('website/render_package_index.py')
    name = 'easydiffraction-2026.11.6-cp312-abi3-linux_x86_64.whl'
    url = f'https://github.com/enhantica/edi/releases/download/v2026.11.6/{name}'
    asset = {'name': name, 'state': 'uploaded', 'browser_download_url': url}
    release = {'draft': False, 'tag_name': 'v2026.11.6', 'assets': [asset]}
    page = tmp_path / 'pypi/simple/easydiffraction/index.html'
    index.write_package_index(tmp_path, [[release]])
    assert name not in page.read_text(encoding='utf-8'), (
        'Preview index links only published hashed python wheels.'
    )
    asset['digest'] = 'sha256:' + 'a' * 64
    index.write_package_index(tmp_path, [[{**release, 'draft': True}]])
    assert name not in page.read_text(encoding='utf-8'), (
        'Preview index links only published hashed python wheels.'
    )
    index.write_package_index(tmp_path, [[release]])
    assert url + '#sha256=' + 'a' * 64 in page.read_text(encoding='utf-8'), (
        'Preview index links only published hashed python wheels.'
    )
