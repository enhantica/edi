"""Status columns retain icon cells; the Fit column uses its declared checkbox.

The closed census is a mechanical convention gate, paired with live delegate
checks in TableInteractions and TableNotes. It does not claim pixel correctness.
"""

import re
from pathlib import Path

import pytest

from tests.integration.py.test_scan_app_contract import block

ROOT = Path(__file__).resolve().parents[3]
PAGES = ROOT / 'app/qml/Pages'
COLUMNS = {
    'Project/RecentProjectsGroup.qml': ('', 2),
    'Experiment/ExperimentsGroup.qml': ('Fit', 3),
    'Experiment/MeasuredRangeGroup.qml': ('status', 8),
}
# Mask comments and string interiors before balancing QML braces. Keep positions.
LEXICAL = re.compile(
    r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`',
    re.DOTALL,
)


def mask(source):
    return LEXICAL.sub(lambda match: ' ' * len(match.group()), source)


def children(source, start, end):
    """Direct object declarations only; nested handlers cannot impersonate cells."""
    masked = mask(source)
    result = []
    cursor = start
    while cursor < end:
        opened = masked.find('{', cursor, end)
        if opened < 0:
            break
        depth = 1
        closed = opened + 1
        while closed < end and depth:
            depth += (masked[closed] == '{') - (masked[closed] == '}')
            closed += 1
        assert depth == 0, 'Status-column inventory requires balanced QML objects'
        prefix = masked[cursor:opened]
        name = re.search(r'([A-Za-z][\w.]*)\s*$', prefix)
        if name:
            result.append((name[1], source[opened + 1 : closed - 1]))
        cursor = closed
    return result


def table_cells(source):
    masked = mask(source)
    if re.search(r'delegate\s*:\s*TableRow\s*\{', masked):
        shared = (ROOT / 'app/qml/Components/TableRow.qml').read_text()
        assert re.search(r'^EaComponents\.ListViewDelegate\s*\{', shared, re.MULTILINE), (
            'The shared TableRow remains the canonical production list-view delegate'
        )
    match = re.search(r'delegate\s*:\s*(?:EaComponents\.ListViewDelegate|TableRow)\s*\{', masked)
    assert match, 'The table status census locates the actual production row delegate'
    depth = 1
    end = match.end()
    while end < len(masked) and depth:
        depth += (masked[end] == '{') - (masked[end] == '}')
        end += 1
    assert depth == 0, 'Status census refuses an unterminated production delegate'
    return children(source, match.end(), end - 1)


def test_every_status_column_is_in_the_convention_census():
    actual = {}
    for path in PAGES.rglob('*.qml'):
        contents = path.read_text()
        declaration = re.search(r'\bheader\s*:', mask(contents))
        if declaration is None:
            continue
        start = declaration.start()
        header = contents[start : start + len(block(mask(contents[start:]), 'header:'))]
        headings = re.findall(r'text\s*:\s*qsTr\("(Status|status|Fit)"\)', header)
        if re.search(r'HeaderLabel\s*\{[^}]*uid:\s*"data.calc_status"', header):
            headings.append('status')
        relative = path.relative_to(PAGES).as_posix()
        expected = COLUMNS.get(relative)
        if expected is not None and not expected[0]:
            # Recent projects retains the icon column, with its header cell unnamed.
            labels = children(header, header.index('{') + 1, len(header) - 1)
            assert len(labels) == 4, 'Recent projects retains its four aligned header cells'
            status_header = labels[expected[1]][1]
            text = re.search(r'(?m)^\s*text\s*:\s*(.+)', status_header)
            assert text is None or text[1].strip() in {'""', "''", 'qsTr("")', "qsTr('')"}, (
                'The Recent projects status header is empty while its row icons keep word tooltips'
            )
            headings.append('')
        if headings:
            actual[relative] = headings
    assert actual == {path: [heading] for path, (heading, _) in COLUMNS.items()}, (
        'Every named or headerless table status column belongs to the coloured-icon '
        'convention census'
    )


@pytest.mark.parametrize('path', COLUMNS)
def test_status_columns_use_shared_icons_with_word_tooltips(path):
    source = (PAGES / path).read_text()
    # MouseArea and TapHandler are overlays, not table cells; Item is a real cell.
    cells = [
        (kind, body)
        for kind, body in table_cells(source)
        if kind in {'IconCell', 'TextCell', 'NumberLabel', 'ParameterCell', 'Item'}
        or kind.startswith('EaComponents.ListView')
    ]
    if any(kind == 'NumberLabel' for kind, _ in cells):
        numeric_cell = (ROOT / 'app/qml/Components/NumberLabel.qml').read_text()
        text_cell = (ROOT / 'app/qml/Components/CellLabel.qml').read_text()
        assert re.search(r'^CellLabel\s*\{', numeric_cell, re.MULTILINE) and re.search(
            r'^EaComponents\.ListViewLabel\s*\{', text_cell, re.MULTILINE
        ), 'Numeric status cells inherit the canonical list-view label through CellLabel'
    index = COLUMNS[path][1]
    assert len(cells) > index, 'The declared status column has an actual row cell'
    kind, body = cells[index]
    if path == 'Experiment/ExperimentsGroup.qml':
        assert kind == 'Item' and 'EaElements.CheckBox {' in body, (
            'The experiment Fit column uses its declared checkbox with a separate word tooltip'
        )
        checkbox = block(body, 'EaElements.CheckBox {')
        assert 'FitOutcomes.color(row.fitOutcome)' in checkbox, (
            'The Fit checkbox retains its row outcome colour'
        )
        assert 'FitOutcomes.word(row.fitOutcome)' in body, (
            'The Fit checkbox retains the outcome word in its hover tooltip'
        )
        # The preceding unnamed data-status icon is a distinct retained column.
        kind, body = cells[index - 1]
    assert kind == 'IconCell', 'Other status columns retain the shared icon and word tooltip cell'
    for binding in ('icon', 'iconColor', 'toolTip'):
        assert re.search(rf'(?m)^\s*{binding}\s*:\s*\S', body), (
            'Status icons declare their glyph, state colour and word tooltip'
        )
    assert not re.search(r'(?m)^\s*text\s*:', body), (
        'Status words remain in tooltips rather than visible text columns'
    )


def test_nested_declarations_and_comment_icons_cannot_fake_a_status_cell():
    source = """Item {
        delegate: EaComponents.ListViewDelegate {
            EaComponents.ListViewLabel {
                text: "{quoted brace}"
                // IconCell { icon: "check-circle" }
                Item { IconCell { icon: "check-circle" } }
            }
        }
        IconCell { icon: "check-circle" }
    }"""
    actual = table_cells(source)
    assert [kind for kind, _ in actual] == ['EaComponents.ListViewLabel'], (
        'Nested, commented and sibling icons cannot satisfy the actual table-cell convention'
    )


def test_status_header_census_ignores_comment_quotes_and_balances_literal_braces():
    source = """Item {
        header: Row {
            // owner's header: this apostrophe is not a string opener
            Label { text: qsTr("Status") }
            Label { text: "{literal brace}" }
        }
        Label { text: qsTr("Fit") }
    }"""
    start = source.index('header:')
    header = source[start : start + len(block(mask(source), 'header:'))]
    assert re.findall(r'text\s*:\s*qsTr\("(Status|status|Fit)"\)', header) == ['Status'], (
        'the header census ignores comment punctuation and excludes headings outside the header'
    )
