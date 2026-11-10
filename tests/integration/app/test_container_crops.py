"""Texture crops follow the crossing-clip fault reproduced by shapes-app."""

from pathlib import Path

from tests.integration.app.test_shared_ui_census import binding, pinned_gui
from tests.integration.py.test_table_and_about_contract import qml_objects

ROOT = Path(__file__).resolve().parents[3]
CONTAINERS = {
    'Components/SideBarColumn.qml': 'Flickable',
    'Elements/GroupBox.qml': 'GroupBox',
    'Components/ListView.qml': 'ListView',
    'Components/SideBar.qml': 'SwipeView',
    'Components/MainContent.qml': 'SwipeView',
}
REASON = (
    'A clipped item crossing its enclosing clip needs a layer boundary between them; '
    'the container may keep its clip under its own layer, or ListView may remove '
    "its cells' inner clips. "
    "Rendered acceptance remains the owner's look on dev with a GPU."
)


def cell_clips(gui):
    sources = {p.stem: p.read_text() for p in gui.rglob('*.qml')}
    app = list((ROOT / 'app/qml').rglob('*.qml'))
    sources.update({p.stem: p.read_text() for p in app})
    pending = []
    for path in app:
        for kind, body in qml_objects(path.read_text()):
            if kind.rsplit('.', 1)[-1] == 'TableRow':
                pending.extend(
                    child.rsplit('.', 1)[-1] for child, _ in qml_objects(' '.join(body))
                )
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
    return layer == ['true'] or (clip == ['true'] and not cells)


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
    assert not failures, (
        'Crossing clips require a layer boundary. '
        + REASON
        + ' Violations: '
        + ', '.join(failures)
    )


def test_crop_census_rejects_nested_clip_and_unrelated_layer(tmp_path, monkeypatch):
    for source in (
        'Item { clip: true }',
        'Item { clip: true; layer.enabled: foldAnimation.running }',
        'Item { clip: true; layer.enabled: !collapsed }',
        'Item { clip: true; layer.enabled: parent.moving }',
        'Item { clip: true; Item { layer.enabled: true } }',
        'Item { clip: false; layer.enabled: false }',
        'Item { clip: false /* layer.enabled: true */ }',
    ):
        body = list(qml_objects(source))[-1][1]
        assert not crop_safe(body, ['clipped cell']), (
            'Crossing clips require a layer boundary. ' + REASON
        )
    layer = list(qml_objects('Item { clip: false; layer.enabled: true }'))[-1][1]
    fallback = list(qml_objects('Item { clip: true }'))[-1][1]
    assert crop_safe(layer, ['clipped cell']), 'Crossing clips require a layer boundary. ' + REASON
    retained = list(qml_objects('Item { clip: true; layer.enabled: true }'))[-1][1]
    assert crop_safe(retained, ['clipped cell']), (
        'Crossing clips require a layer boundary. ' + REASON
    )
    assert crop_safe(fallback), 'Crossing clips require a layer boundary. ' + REASON

    monkeypatch.setitem(globals(), 'ROOT', tmp_path)
    app = tmp_path / 'app/qml'
    app.mkdir(parents=True)
    (app / 'Page.qml').write_text('Item { TableRow { NewCell {} } }')
    cell = app / 'NewCell.qml'
    cell.write_text('Item { Item { clip: true } }')
    assert cell_clips(tmp_path) == ['NewCell'], (
        'Crossing clips require a layer boundary. ' + REASON
    )
    cell.write_text('Item { Item { clip: false } }')
    assert cell_clips(tmp_path) == [], 'Crossing clips require a layer boundary. ' + REASON
