"""Owner dcb14f59b: tutorial captures use WebP; existing feature screenshots keep their format."""

import json
import sys
from pathlib import Path

import pytest

from tests.fixtures.docs_image_reference.build import build
from tests.fixtures.docs_image_reference.capture import execute
from tests.fixtures.tutorial_cases.contract import ROOT
from tests.fixtures.tutorial_cases.screenshots import (
    PNG,
    assert_no_tutorial_png,
    assert_page_webp,
    assert_webp_asset,
    control_webp,
    tutorial_folders,
    webp_info,
)

DOCS = ROOT / 'website/surfaces/docs'


def test_tutorial_screenshot_folders_have_no_png():
    assert_no_tutorial_png(DOCS)


def test_tutorial_capture_records_name_webp_images_and_matching_sidecars():
    manifests = {p for folder in tutorial_folders(DOCS) for p in folder.rglob('manifest.json')}
    assert manifests, 'Gate 4: tutorial screenshot custody includes actual capture records'
    for manifest in sorted(manifests):
        document = json.loads(manifest.read_text())
        for scene in document['scenes']:
            if scene.get('status') != 'captured':
                continue
            image = Path(scene['image'])
            assert image.suffix == '.webp' and (manifest.parent / image).is_file(), (
                'Gate 4: each captured tutorial scene names an existing WebP: ' + str(manifest)
            )
            metadata = json.loads((manifest.parent / scene['metadata']).read_text())
            assert metadata['image'] == scene['image'], (
                'Gate 4: tutorial scene and sidecar name the same WebP file'
            )


@pytest.mark.parametrize(
    'fault', ['suffix', 'uppercase', 'disguised-png', 'declared-tutorial-folder']
)
def test_unused_tutorial_png_cannot_escape_folder_sweep(tmp_path, fault):
    docs = tmp_path / 'docs'
    folder = docs / 'assets/gui/cases/control/dark'
    folder.mkdir(parents=True)
    # Existing feature PNGs are deliberately outside this decision.
    feature = docs / 'assets/gui/y2o3'
    feature.mkdir()
    (feature / 'kept.png').write_bytes(PNG)
    assert_no_tutorial_png(docs)
    name = {
        'suffix': 'unused.png',
        'uppercase': 'unused.PNG',
        'disguised-png': 'unused.webp',
        'declared-tutorial-folder': 'unused.png',
    }[fault]
    if fault == 'declared-tutorial-folder':
        folder = docs / 'assets/gui/another-tutorial'
        folder.mkdir()
        (folder / 'manifest.json').write_text(json.dumps({'workflow': 'tutorial'}))
    (folder / name).write_bytes(PNG)
    with pytest.raises(AssertionError, match='Gate 4:'):
        assert_no_tutorial_png(docs)


@pytest.mark.parametrize('fault', [None, 'png-as-webp', 'truncated', 'missing', 'escaping-root'])
def test_webp_resolution_requires_real_complete_pixels(tmp_path, fault):
    docs = tmp_path / 'docs'
    docs.mkdir()
    page = docs / 'index.html'
    page.write_text('<main></main>')
    image = docs / 'capture.webp'
    image.write_bytes(control_webp())
    assert webp_info(image)['loaded'], 'The authored WebP control must fully decode independently'
    address = 'capture.webp?v=control#view'
    if fault == 'png-as-webp':
        image.write_bytes(PNG)
    elif fault == 'truncated':
        image.write_bytes(image.read_bytes()[:24])
    elif fault == 'missing':
        image.unlink()
    elif fault == 'escaping-root':
        outside = tmp_path / 'outside.webp'
        outside.write_bytes(image.read_bytes())
        address = '../outside.webp'
    if fault:
        with pytest.raises(AssertionError, match='Gate 4:'):
            assert_webp_asset(address, page, docs)
    else:
        assert assert_webp_asset(address, page, docs) == image, (
            'Gate 4: query strings and fragments preserve a valid local WebP target'
        )


@pytest.mark.parametrize(
    'markup',
    [
        '<img src="bad.png">',
        '<svg><image href="bad.png"/></svg>',
        '<picture><source srcset="good.webp 1x, bad.png 2x"></picture>',
        '<a class="gui-image-link" href="bad.png">Enlarge</a>',
        '<img src="good.webp" data-gui-dark="control">',
        '<svg><image/></svg>',
    ],
)
def test_all_tutorial_image_entrances_enforce_webp(tmp_path, markup):
    (tmp_path / 'good.webp').write_bytes(control_webp())
    (tmp_path / 'bad.png').write_bytes(PNG)
    page = tmp_path / 'index.html'
    page.write_text('<main>' + markup + '</main>')
    with pytest.raises(AssertionError, match='Gate 4:'):
        assert_page_webp(page, tmp_path)


@pytest.mark.parametrize('fault', [None, 'png-as-webp', 'truncated', 'alternate-tutorial-folder'])
def test_executed_capture_qualifies_tutorial_webp_with_real_decoder(tmp_path, fault, monkeypatch):
    _site, project, manifest = build(tmp_path)
    folder = 'another-tutorial' if fault == 'alternate-tutorial-folder' else 'assistant'
    if fault == 'alternate-tutorial-folder':
        declared = project / 'website/surfaces/docs/assets/gui' / folder
        declared.mkdir()
        (declared / 'manifest.json').write_text(json.dumps({'workflow': 'tutorial'}))
    rows = [
        {'theme': theme, 'path': 'assets/gui/' + folder + '/' + sub + 'control.webp'}
        for theme, sub in [('light', ''), ('dark', 'dark/')]
    ]
    for row in rows:
        target = project / 'inputs' / row['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        content = control_webp()
        if fault == 'png-as-webp':
            content = PNG
        elif fault == 'truncated':
            content = content[:24]
        target.write_bytes(content)
    (project / 'plan.json').write_text(json.dumps(rows))
    manifest['images'] = rows
    required = {(row['theme'], row['path']) for row in rows}
    run = tmp_path / 'run'
    run.mkdir()
    monkeypatch.setenv('EDI_DOCS_BROWSER_PYTHON', sys.executable)
    if fault in {'png-as-webp', 'truncated'}:
        with pytest.raises(AssertionError, match='captured tutorial'):
            execute(project, manifest, required, run)
    else:
        assert execute(project, manifest, required, run) == required, (
            'Gate 4: the actual capture qualification decodes every produced tutorial WebP'
        )
