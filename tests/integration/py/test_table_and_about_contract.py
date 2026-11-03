"""The QML catalogue and dependency overview follow the shared table rules."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QML = ROOT / 'app/qml'
TOKEN = re.compile(
    r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`|[\w.]+|[^\s]',
    re.DOTALL,
)


def tokens(text):
    return [m.group() for m in TOKEN.finditer(text) if not m.group().startswith(('//', '/*'))]


def qml_objects(text):
    words = tokens(text)
    stack = []
    for index, word in enumerate(words):
        if word == '{':
            stack.append(index)
        elif word == '}' and stack:
            start = stack.pop()
            if start and re.fullmatch(r'(?:\w+\.)*[A-Z]\w*', words[start - 1]):
                yield words[start - 1], words[start + 1 : index]


def properties(body):
    depth = 0
    for index, word in enumerate(body[:-2]):
        if word in {'{', '[', '('}:
            depth += 1
        elif word in {'}', ']', ')'}:
            depth -= 1
        elif depth == 0 and body[index + 1] == ':':
            yield word, body[index + 2]


def table_census():
    result = []
    for path in sorted(QML.rglob('*.qml')):
        for kind, body in qml_objects(path.read_text()):
            values = dict(properties(body))
            if kind.split('.')[-1] in {'DataTable', 'ListView'} and 'delegate' in values:
                result.append((str(path.relative_to(QML)), values['delegate']))
    return result


def test_no_old_tableview_type_in_any_qml_file():
    offenders = []
    for path in sorted(QML.rglob('*.qml')):
        types = [
            kind
            for kind, _ in qml_objects(path.read_text())
            if kind.split('.')[-1].startswith('TableView')
        ]
        if path.stem.startswith('TableView') or types:
            offenders.append((str(path.relative_to(QML)), types))
    assert not offenders, (
        'Every table cell is a ListView cell, including local component definitions: '
        + repr(offenders)
    )


def test_every_table_instantiates_the_one_row_type():
    rows = table_census()
    assert rows, 'The census must reach production table delegates, not an empty source glob'
    kinds = {kind for _, kind in rows}
    assert kinds == {'TableRow'}, (
        'Every actual table delegate uses the one shared TableRow: ' + repr(rows)
    )


def test_gui_component_pin_moves_with_all_listview_cell_kinds():
    source = (ROOT / 'cmake/EdiGuiBase.cmake').read_text()
    pin = re.search(r'set\(EDI_GUI_COMPONENTS_SHA\s+([0-9a-f]{40})\)', source)
    assert pin and pin[1] != '3897d339b60f5707bfe952fed59a20f73340e236', (
        'The gui-components pin must move to the branch carrying the new cells'
    )
    for cell in ('Label', 'Button', 'CheckBox', 'ComboBox', 'Parameter', 'TextInput'):
        assert re.search(r'\bListView' + cell + r'\b', source), (
            'The pinned module registers every cell kind used by edi: ' + cell
        )
    for field in ('ARCHIVE_SHA256', 'SRC_SHA256'):
        assert re.search(r'set\(EDI_GUI_COMPONENTS_' + field + r'\s+[0-9a-f]{64}\)', source), (
            'The moved pin retains both archive and full source-tree integrity checks'
        )


def test_about_has_no_tabbed_or_explanatory_licence_pages():
    source = (QML / 'Pages/Home/AboutDialog.qml').read_text()
    kinds = {kind.split('.')[-1] for kind, _ in qml_objects(source)}
    assert not kinds & {'TabBar', 'AppBarTabButton', 'SwipeView'}, (
        'About shows the app details, licence links and contributors together without tabs'
    )
    assert 'EasyDiffraction is free software' not in source, (
        'Licence texts replace the former explanatory licence page'
    )
    assert 'Third-party licences' in source, 'The dependency link is named Third-party licences'


def dependency_matrix():
    text = (ROOT / 'DEPENDENCIES.md').read_text()
    rows = [
        [cell.strip() for cell in line.strip().strip('|').split('|')]
        for line in text.splitlines()
        if line.lstrip().startswith('|')
    ]
    wanted = ('desktop', 'web', 'python', 'cli')
    header = next(
        (row for row in rows if all(any(name in c.casefold() for c in row) for name in wanted)),
        None,
    )
    assert header is not None, (
        'DEPENDENCIES.md has separate desktop, web, Python package and CLI columns'
    )
    indices = {
        name: next(i for i, cell in enumerate(header) if name in cell.casefold())
        for name in wanted
    }
    result = {}
    for row in rows[rows.index(header) + 1 :]:
        if len(row) != len(header) or set(''.join(row)) <= {'-', ':', ' '} or row == header:
            continue
        result[row[0].strip('`')] = {name: row[index] for name, index in indices.items()}
    assert result, 'The dependency overview must contain actual component rows'
    return result


def test_dependency_matrix_declares_all_distribution_surfaces():
    matrix = dependency_matrix()
    for component in ('crysta', 'Eigen', 'nanobind', 'Qt', 'plotly.js'):
        assert component in matrix, (
            'The overview covers compiled, linked and report-only components: ' + component
        )


def test_qml_census_observer_catches_nested_cells_but_ignores_comments():
    sample = (
        '// TableViewLabel {}\nDataTable { delegate: TableRow { text: "}"; ListViewLabel {} } }'
    )
    objects = list(qml_objects(sample))
    assert [kind for kind, _ in objects] == ['ListViewLabel', 'TableRow', 'DataTable'], (
        'The census handles nesting and quoted braces without counting commented-out types'
    )
    assert dict(properties(objects[-1][1]))['delegate'] == 'TableRow', (
        'The census reads the actual table delegate rather than a nested picker delegate'
    )
