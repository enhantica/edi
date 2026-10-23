"""The owner requires every table status column to use the existing icon cell.

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
    'Project/RecentProjectsGroup.qml': ('Status', 2),
    'Experiment/ExperimentsGroup.qml': ('Fit', 2),
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
        if headings:
            actual[path.relative_to(PAGES).as_posix()] = headings
    assert actual == {path: [heading] for path, (heading, _) in COLUMNS.items()}, (
        'Every table Status or Fit column belongs to the coloured-icon convention census'
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
        assert re.search(r'^EaComponents\.ListViewLabel\s*\{', numeric_cell, re.MULTILINE), (
            'Numeric cells counted in the status census inherit the canonical list-view label'
        )
    index = COLUMNS[path][1]
    assert len(cells) > index, 'The declared status column has an actual row cell'
    kind, body = cells[index]
    assert kind == 'IconCell', (
        'Every status column uses the shared coloured icon and tooltip cell, including calculation'
    )
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
