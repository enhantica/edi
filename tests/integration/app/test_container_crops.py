"""Texture crops follow the crossing-clip fault reproduced by shapes-app."""

import hashlib
import re
from pathlib import Path

from tests.integration.app.test_shared_ui_census import binding
from tests.integration.py.test_table_and_about_contract import qml_objects, table_delegates

ROOT = Path(__file__).resolve().parents[3]
CONTAINERS = {
    'Components/SideBarColumn.qml': 'Flickable',
    'Elements/GroupBox.qml': 'GroupBox',
    'Components/ListView.qml': 'ListView',
    'Components/SideBar.qml': 'SwipeView',
    'Components/MainContent.qml': 'SwipeView',
}
REASON = (
    'A crossing child clip must not intersect its enclosing clip; use a texture layer '
    'on the container, or remove the ListView cells\' inner clips. '
    'Rendered acceptance remains the owner\'s look on dev with a GPU.'
)


def pinned_gui():
    cmake = (ROOT / 'cmake/EdiGuiBase.cmake').read_text()
    cache = (ROOT / 'build/app/CMakeCache.txt').read_text()
    match = re.search(r'^FETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS:[^=]*=(.+)$', cache, re.MULTILINE)
    if not match or not match[1].strip():
        match = re.search(r'^gui_components_SOURCE_DIR:[^=]*=(.+)$', cache, re.MULTILINE)
    assert match, 'The crop census requires the GUI source resolved by the configured edi build'
    src = Path(match[1]) / 'src'
    expected = re.search(r'set\(EDI_GUI_COMPONENTS_SRC_SHA256\s+([0-9a-f]{64})\)', cmake)
    assert expected and src.is_dir(), 'The configured GUI must carry edi\'s pinned source tree'
    inventory = ''.join(
        f'{path.relative_to(src).as_posix()} {hashlib.sha256(path.read_bytes()).hexdigest()}\n'
        for path in sorted(src.rglob('*'), key=lambda p: p.relative_to(src).as_posix())
        if path.is_file()
    )
    assert hashlib.sha256(inventory.encode()).hexdigest() == expected[1], (
        'The crop gate must read the current edi pin, never stale or locally edited GUI files'
    )
    return src / 'EasyApplication/Gui'


def cell_clips(gui):
    sources = {p.stem: p.read_text() for p in gui.rglob('*.qml')}
    app = list((ROOT / 'app/qml').rglob('*.qml'))
    sources.update({p.stem: p.read_text() for p in app})
    pending = []
    for path in app:
        for body in table_delegates(path.read_text()):
            pending.extend(kind.rsplit('.', 1)[-1] for kind, _ in qml_objects(' '.join(body)))
    # These reusable cells also appear through dynamically populated example/text views.
    pending.extend(['ParameterCell', 'ExampleCell', 'TextTab'])
    seen = set()
    failures = []
    while pending:
        name = pending.pop()
        if name in seen or name not in sources:
            continue
        seen.add(name)
        for kind, body in qml_objects(sources[name]):
            clip = binding(body, 'clip')
            if clip and clip != ['false']:
                failures.append(name)
            pending.append(kind.rsplit('.', 1)[-1])
    return failures


def crop_safe(body, cells=()):
    clip = binding(body, 'clip')
    layer = binding(body, 'layer.enabled')
    return (layer == ['true'] and (not clip or clip == ['false'])) or (
        clip == ['true'] and not cells
    )


def test_crossing_containers_use_texture_crops():
    gui = pinned_gui()
    failures = []
    for path, target in CONTAINERS.items():
        objects = list(qml_objects((gui / path).read_text()))
        selected = [body for kind, body in objects if kind.rsplit('.', 1)[-1] == target]
        assert len(selected) == 1, (
            'The crop census must reach the actual crossing container: ' + path
        )
        cells = cell_clips(gui) if path == 'Components/ListView.qml' else ['crossing child']
        if not crop_safe(selected[0], cells):
            failures.append(path)
    assert not failures, REASON + ' Violations: ' + ', '.join(failures)


def test_crop_census_rejects_nested_clip_and_unrelated_layer():
    for source in (
        'Item { clip: true }',
        'Item { clip: true; layer.enabled: true }',
        'Item { clip: true; Item { layer.enabled: true } }',
        'Item { clip: false; layer.enabled: false }',
        'Item { clip: false /* layer.enabled: true */ }',
    ):
        body = list(qml_objects(source))[-1][1]
        assert not crop_safe(body, ['clipped cell']), REASON
    layer = list(qml_objects('Item { clip: false; layer.enabled: true }'))[-1][1]
    fallback = list(qml_objects('Item { clip: true }'))[-1][1]
    assert crop_safe(layer, ['clipped cell']), REASON
    assert crop_safe(fallback), REASON
