# SPDX-License-Identifier: BSD-3-Clause
"""Round-trip interface labels from a merged PR through GitHub and the docs."""

import datetime
import hashlib
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
    # The desktop page has an online and an offline button per platform, each with a size line.
    source = '<p>Desktop installers will appear here when published.</p>' + ''.join(
        f'<a data-download-platform="{platform}" data-download-kind="{kind}" aria-disabled="true">'
        f'<small data-download-size="{platform}-{kind}">{kind.capitalize()}</small></a>'
        for kind in ('online', 'offline')
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
                    'size': 23_400_000,
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
    assert 'Online · 23 MB' in page, 'Desktop downloads link only published platform assets.'
    assert (
        'data-download-platform="windows-x86_64" data-download-kind="online" aria-disabled="true"'
        in page
    ), 'Desktop downloads link only published platform assets.'
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


def wheel_release(version='2026.11.6', payload=b'a wheel'):
    name = f'easydiffraction-{version}-cp312-abi3-linux_x86_64.whl'
    url = f'https://github.com/enhantica/edi/releases/download/v{version}/{name}'
    asset = {
        'name': name,
        'state': 'uploaded',
        'browser_download_url': url,
        'digest': 'sha256:' + hashlib.sha256(payload).hexdigest(),
    }
    return name, payload, asset, {'draft': False, 'tag_name': f'v{version}', 'assets': [asset]}


def test_preview_index_serves_the_current_wheels_and_links_older_releases(tmp_path):
    index = load('website/render_package_index.py')
    name, payload, asset, release = wheel_release('2026.11.10')
    old, _, old_asset, older = wheel_release('2026.11.6', b'an older wheel')
    fetched = []

    def fetch(tag, wanted, folder):
        fetched.append((tag, wanted))
        (folder / wanted).write_bytes(payload)

    project = tmp_path / 'pypi/simple/easydiffraction'
    page = project / 'index.html'
    for listed in (
        [{**release, 'draft': True}],
        [{**release, 'assets': [{**asset, 'digest': None}]}],
    ):
        index.write_package_index(tmp_path, [listed], fetch)
        assert name not in page.read_text(encoding='utf-8') and not fetched, (
            'The index lists only published wheels with a recorded digest.'
        )
    (project / old).write_bytes(b'an older wheel')
    index.write_package_index(tmp_path, [[older, release]], fetch)
    text = page.read_text(encoding='utf-8')
    digest = hashlib.sha256(payload).hexdigest()
    assert f'href="{name}#sha256={digest}"' in text, (
        'The current release links its wheels relatively, with their digests.'
    )
    assert (
        f'href="{old_asset["browser_download_url"]}#{old_asset["digest"].replace(":", "=")}"'
        in text
    ), 'An older release links its GitHub asset with its digest.'
    assert text.count('data-requires-python="&gt;=3.12"') == 2, (
        'Every entry states the Python it needs.'
    )
    assert fetched == [('v2026.11.90', name)], 'Only the current release is fetched.'
    assert [p.name for p in project.glob('*.whl')] == [name], (
        'The site serves only the current release.'
    )
    assert (project / name).read_bytes() == payload, 'The served wheel is the fetched one.'
    index.write_package_index(tmp_path, [[older, release]], fetch)
    assert len(fetched) == 1, 'A current wheel already on the site is not fetched again.'


def test_preview_index_refuses_a_wheel_that_differs_from_its_digest(tmp_path):
    index = load('website/render_package_index.py')
    name, _, _, release = wheel_release()

    def fetch(_tag, wanted, folder):
        (folder / wanted).write_bytes(b'other bytes')

    with pytest.raises(SystemExit, match='does not match its recorded sha256'):
        index.write_package_index(tmp_path, [[release]], fetch)
    assert not (tmp_path / 'pypi/simple/easydiffraction' / name).exists(), (
        'A wheel that differs from its recorded digest is not published.'
    )
