"""Project entry controls follow the requested button and ordered-popup design."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'app/qml/Pages/Project/GetStartedGroup.qml'
TOKEN = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\w+(?:\.\w+)*|[^\s]')


def objects(source):
    tokens = (
        [lexeme for lexeme in TOKEN.findall(source) if not lexeme.startswith(('//', '/*'))]
        if isinstance(source, str)
        else source
    )
    stack = []
    for index, lexeme in enumerate(tokens):
        if lexeme == '{':
            kind = tokens[index - 1] if index else ''
            if kind == ':' and index >= 2:
                kind = tokens[index - 2]
            stack.append((kind, index))
        elif lexeme == '}' and stack:
            kind, start = stack.pop()
            yield kind, tokens[start + 1 : index]


def labels(tokens):
    return [
        tokens[index + 4][1:-1].removesuffix('…').removesuffix('...')
        for index in range(len(tokens) - 5)
        if tokens[index : index + 4] == ['text', ':', 'qsTr', '(']
        and tokens[index + 4].startswith('"')
    ]


def test_get_started_declares_exactly_the_three_project_actions():
    buttons = [
        labels(body)[0]
        for kind, body in objects(SOURCE.read_text(encoding='utf-8'))
        if kind.endswith('SideBarButton') and labels(body)
    ]
    assert buttons == ['Create a new project', 'Load project', 'Save project as'], (
        'Get started offers exactly Create a new project, Load project and Save project as '
        'in that order; program imports belong in the Load project popup'
    )


def contains(tokens, source):
    expected = TOKEN.findall(source)
    return any(tokens[index : index + len(expected)] == expected for index in range(len(tokens)))


def check_load_popup(source):
    menus = [
        body
        for kind, body in objects(source)
        if kind == 'EaElements.Menu' and contains(body, 'objectName: "project.load.menu"')
    ]
    assert len(menus) == 1, 'One Load project popup owns native choices and registered imports'
    menu = menus[0]
    entries = [body for kind, body in objects(menu) if kind == 'LoadMenuItem']
    assert len(entries) == 4, (
        'Load declares three native entries and one common import template, '
        'without separate per-program GUI entries'
    )
    assert [labels(body) for body in entries[:3]] == [
        ['Open project folder'],
        ['Open project zip'],
        ['Open project from URL'],
    ], 'The Load popup declares folder, zip and URL in order before its import template'
    components = [body for kind, body in objects(menu) if kind == 'Component']
    assert len(components) == 1 and contains(components[0], 'id: importItem'), (
        'Registered programs share one import component rather than separate GUI importers'
    )
    assert [body for kind, body in objects(components[0]) if kind == 'LoadMenuItem'] == [
        entries[3]
    ], 'The sole import component owns the common fourth menu-entry template'
    assert contains(entries[3], '"project.import." + importer.key'), (
        'Common import action identity follows the registry descriptor key'
    )
    assert contains(entries[3], 'qsTr("Import %1…").arg(importer.program)'), (
        'The common import template names its registered program without separate GUI entries'
    )
    builders = [body for kind, body in objects(menu) if kind == 'Component.onCompleted']
    assert len(builders) == 1, 'The Load popup builds its registered entries once on completion'
    builder = builders[0]
    assert contains(builder, 'const importers = Session.projectImporters();'), (
        'The import entries come from the common core registry, including further programs'
    )
    assert contains(builder, 'for (let i = 0; i < importers.length; ++i) {'), (
        'Every registered importer gets an entry in registry order without a fixed program count'
    )
    assert contains(builder, 'const importer = importers[i];') and contains(
        builder,
        'const item = importItem.createObject(loadMenu.contentItem, { importer: importer }',
    ), 'Every generated menu item receives its own descriptor from the common registry'
    assert contains(builder, 'item.triggered.connect(() => group.importProject(importer));'), (
        'Every generated program action uses the common guarded import path'
    )
    assert contains(
        builder, 'const at = group.menuIndexAfter(loadMenu, importHeader);'
    ) and contains(builder, 'loadMenu.insertItem(at + i, item);'), (
        'Generated import choices are inserted after their header in registry order'
    )


def test_load_popup_declares_the_native_and_program_choices_in_order():
    check_load_popup(SOURCE.read_text(encoding='utf-8'))


def test_save_as_popup_declares_the_five_destination_choices_in_order():
    expected = ['As project folder', 'As project zip', 'As cryspy', 'As FullProf', 'As GSAS-II']
    candidates = [
        [label for label in labels(body) if label in expected]
        for path in [SOURCE, ROOT / 'app/qml/Main.qml']
        for kind, body in objects(path.read_text(encoding='utf-8'))
        if kind in {'Menu', 'Popup', 'AppDialog', 'EaElements.Menu', 'EaElements.Popup'}
    ]
    assert expected in candidates, (
        'One Save project as popup offers As project folder, As project zip, '
        'As cryspy, As FullProf and As GSAS-II in that order'
    )
