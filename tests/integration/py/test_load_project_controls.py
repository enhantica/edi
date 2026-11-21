"""Project entry controls follow the requested three-button and four-choice design."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'app/qml/Pages/Project/GetStartedGroup.qml'
TOKEN = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\w+(?:\.\w+)*|[^\s]')


def objects(source):
    tokens = [lexeme for lexeme in TOKEN.findall(source) if not lexeme.startswith(('//', '/*'))]
    stack = []
    for index, lexeme in enumerate(tokens):
        if lexeme == '{':
            stack.append((tokens[index - 1] if index else '', index))
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


def test_load_popup_declares_the_four_program_choices_in_order():
    expected = ['Open EasyDiffraction file', 'Import cryspy', 'Import FullProf', 'Import GSAS-II']
    candidates = [
        [label for label in labels(body) if label in expected]
        for kind, body in objects(SOURCE.read_text(encoding='utf-8'))
        if kind in {'Menu', 'Popup', 'AppDialog', 'EaElements.Menu', 'EaElements.Popup'}
    ]
    assert expected in candidates, (
        'One Load project popup offers Open EasyDiffraction file, Import cryspy, '
        'Import FullProf and Import GSAS-II in that order'
    )


def test_save_as_popup_declares_the_five_destination_choices_in_order():
    expected = ['As EasyDiffraction folder', 'As Zip', 'As cryspy', 'As FullProf', 'As GSAS-II']
    candidates = [
        [label for label in labels(body) if label in expected]
        for path in [SOURCE, ROOT / 'app/qml/Main.qml']
        for kind, body in objects(path.read_text(encoding='utf-8'))
        if kind in {'Menu', 'Popup', 'AppDialog', 'EaElements.Menu', 'EaElements.Popup'}
    ]
    assert expected in candidates, (
        'One Save project as popup offers As EasyDiffraction folder, As Zip, '
        'As cryspy, As FullProf and As GSAS-II in that order'
    )
