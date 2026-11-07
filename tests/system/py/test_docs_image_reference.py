# SPDX-License-Identifier: BSD-3-Clause
"""Built documentation images follow both schemes and a bounded lighter border."""

import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[3]


def luminance(channels):
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return sum(
        weight * channel for weight, channel in zip((0.2126, 0.7152, 0.0722), linear, strict=True)
    )


@pytest.fixture(scope='module')
def images(tmp_path_factory):
    site = Path(os.environ.get('EDI_DOCS_SITE', str(ROOT / 'website/_build'))).resolve()
    assert (site / 'index.html').is_file(), (
        'The image gate requires the actual built documentation site'
    )
    temporary = tmp_path_factory.mktemp('docs-image-reference')
    output = temporary / 'observed.json'
    browser_environment = ROOT / 'tools/installer/.pixi/envs/default'
    declared_python = browser_environment / ('python.exe' if os.name == 'nt' else 'bin/python')
    interpreter = os.environ.get(
        'EDI_DOCS_BROWSER_PYTHON',
        str(declared_python) if declared_python.is_file() else sys.executable,
    )
    log = temporary / 'browser.log'
    with log.open('w', encoding='utf-8') as stream:
        result = subprocess.run(
            [
                interpreter,
                str(ROOT / 'tests/fixtures/docs_image_reference/observe.py'),
                str(site),
                str(output),
            ],
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
            check=False,
            env={**os.environ, 'TMPDIR': str(temporary), 'PYTHONDONTWRITEBYTECODE': '1'},
        )
        assert result.returncode == 0 and output.is_file(), (
            'The offline browser must observe the built site through its real scheme control: '
            + log.read_text(encoding='utf-8')[-8000:]
        )
    data = json.loads(output.read_text())
    assert data['pages'] and data['images'], 'The built-site image inventory must be nonempty'
    return site, data['prefix'], data['images']


def asset(site, source, prefix):
    parsed = urlparse(source)
    assert parsed.hostname == 'docs.invalid', (
        'Every content image must resolve within the built site'
    )
    assert parsed.path.startswith(prefix), 'An image must resolve within the deployed site prefix'
    path = (site / unquote(parsed.path[len(prefix) :])).resolve()
    assert path.is_relative_to(site) and path.is_file(), (
        'Every scheme-selected image must resolve to an existing built asset'
    )
    return path


def test_every_content_image_resolves_distinct_scheme_variants(images):
    site, prefix, rows = images
    groups = defaultdict(lambda: defaultdict(set))
    for row in rows:
        assert row['loaded'], 'Every visible content image, including the hero, must load'
        groups[row['document'], row['key']][row['theme']].add(asset(site, row['source'], prefix))
    assert any('hero' in row['source'] for row in rows), (
        'The built image inventory must include the landing hero'
    )
    for identity, themes in groups.items():
        assert set(themes) == {'light', 'dark'} and all(
            len(paths) == 1 for paths in themes.values()
        ), 'Each logical content image must select exactly one variant in each scheme: ' + str(
            identity
        )
        light, dark = next(iter(themes['light'])), next(iter(themes['dark']))
        assert (
            light != dark
            and hashlib.sha256(light.read_bytes()).digest()
            != hashlib.sha256(dark.read_bytes()).digest()
        ), 'Light and dark variants must resolve to distinct existing image bytes: ' + str(
            identity
        )


def test_every_image_border_is_a_small_lighter_step_from_its_page(images):
    _, _, rows = images
    colours = defaultdict(lambda: defaultdict(set))
    for row in rows:
        assert row['borderWidth'] > 0 and row['borderAlpha'] > 0, (
            'Every content image must have a visible computed border in its active scheme'
        )
        colours[row['document'], row['key']][row['theme']].add(tuple(row['border']))
        border, page = luminance(row['border']), luminance(row['page'])
        contrast = (border + 0.05) / (page + 0.05)
        assert border > page and 1.01 <= contrast <= 1.25, (
            'A scheme border must be lighter than its page by a WCAG luminance contrast of '
            f'1.01 through 1.25: {row["document"]}, {row["theme"]}, observed {contrast}'
        )

    for identity, themes in colours.items():
        assert set(themes) == {'light', 'dark'} and themes['light'].isdisjoint(themes['dark']), (
            'Computed image border colours must change with the active scheme: ' + str(identity)
        )


def test_capture_command_manifest_covers_every_theme_image(images):
    site, prefix, rows = images
    path = Path(
        os.environ.get('EDI_DOCS_CAPTURE_MANIFEST', str(site / 'assets/capture-manifest.json'))
    )
    assert path.is_file(), 'The capture command must publish its image manifest'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    assert (
        isinstance(manifest.get('command'), list)
        and manifest['command']
        and all(isinstance(part, str) and part for part in manifest['command'])
    ), 'The capture manifest must identify its one executable capture command'
    assert isinstance(manifest.get('images'), list), (
        'The capture manifest must list its theme image outputs'
    )
    declared = {(item['theme'], (site / item['path']).resolve()) for item in manifest['images']}
    required = {(row['theme'], asset(site, row['source'], prefix)) for row in rows}
    assert required <= declared, (
        'The capture command manifest must include every built content image in both themes'
    )
