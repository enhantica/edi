"""Census of the app's source-declared field labels and table headings."""

import re
from pathlib import Path

from tests.integration.py.test_status_columns import LEXICAL, mask

QML = Path(__file__).resolve().parents[3] / 'app/qml'
# Case-significant notation from the crystallographic controls and table columns.
SYMBOLS = re.compile(
    r'^(?:2θ|TOF|s\.u\.|h k l|μR|\u03c3[₀₁₂]²|x[123]{2}|[abcdfhklqrxyz\u03b1-\u03b3φθ])'
    r'(?=$|[\s(:/\u2032])'
)
BLOCK = re.compile(r'(?:(?P<kind>[\w.]+)\s*)?\{|\}')
PROPERTY = re.compile(
    r'(?m)(?:^|[;{])[ \t]*(?:(?:readonly )?property \w+ )?'
    r'(?P<name>label|shortPrettyName|text|title)[ \t]*:[ \t]*(?P<binding>[^\n]+)'
)
QUOTED_PRETTY = re.compile(r"""(?m)^\s*["']shortPrettyName["']\s*:\s*([^\n]+)""")
LITERAL = r"""(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')"""
CAPTION = re.compile(rf'qsTr\(\s*({LITERAL})|(?:^|\?\??|:)\s*({LITERAL})(?=\s*(?:$|[:,+;}}]))')
FIELD_TYPES = {
    'CheckBox',
    'ParamComboBox',
    'ParamTextField',
    'SearchableComboBox',
    'SelectorField',
    'ValueField',
}
COLUMN_LABEL_TYPES = {'HeaderLabel', 'ListViewLabel', 'Label'}


def check_caption(text):
    first_letter = next((char for char in text if char.isalpha()), '')
    return not first_letter or first_letter.isupper() or SYMBOLS.match(text)


def source_captions(path):
    source = path.read_text(encoding='utf-8')
    bare = mask(source)
    # Keep string literals while blanking comments for expression inspection.
    contents = LEXICAL.sub(
        lambda match: ' ' * len(match[0]) if match[0].startswith(('//', '/*')) else match[0],
        source,
    )
    blocks = iter(BLOCK.finditer(bare))
    block = next(blocks, None)
    scopes = []
    bindings = [
        (m.start('name'), m['name'], m.span('binding')) for m in PROPERTY.finditer(contents)
    ]
    bindings.extend(
        (m.start(), 'shortPrettyName', m.span(1)) for m in QUOTED_PRETTY.finditer(contents)
    )
    for offset, prop, (start, end) in sorted(bindings):
        # Reject text inside a multiline comment or template literal.
        if prop != 'shortPrettyName' and not bare[offset : offset + len(prop)].strip():
            continue
        while block and block.start() < offset:
            if block[0] == '}':
                scopes.pop()
            else:
                scopes.append((block['kind'] or '').split('.')[-1])
            block = next(blocks, None)
        owner = scopes[-1] if scopes else ''
        is_field = prop in {'label', 'shortPrettyName'} or (
            prop in {'title', 'text'} and owner in FIELD_TYPES
        )
        is_column = prop == 'text' and 'ListViewHeader' in scopes and owner in COLUMN_LABEL_TYPES
        if is_field or is_column:
            for match in CAPTION.finditer(contents[start:end].rstrip()):
                token = match[1] or match[2]
                yield source.count('\n', 0, offset) + 1, token[1:-1], is_column


def test_app_field_labels_and_table_headings_start_with_a_capital(tmp_path):
    witness = tmp_path / 'Example.qml'
    witness.write_text(
        """
        Item {
            // ValueField { label: qsTr("comment") }
            ValueField { label: qsTr("new field") }
            ValueField { label: "d spacing" }
            ListViewHeader {
                Repeater {
                    delegate: ListViewLabel { text: qsTr("new column") }
                }
            }
            Label { text: qsTr("row content") }
        }
        """,
        encoding='utf-8',
    )
    assert [(text, column) for _, text, column in source_captions(witness)] == [
        ('new field', False),
        ('d spacing', False),
        ('new column', True),
    ], 'The census discovers inline captions and nested table headings while ignoring row content'
    assert all(
        check_caption(text)
        for text in ['2θ', 'd spacing', 'TOF', 's.u. (μB)', '\N{GREEK SMALL LETTER ALPHA}', '|M|']
    ), 'Scientific symbol spellings are accepted as written'
    assert all(not check_caption(text) for text in ['details', 'sample form', 'new column']), (
        'Lowercase prose is refused even when it starts with a symbol letter'
    )
    census = [
        (path.relative_to(QML), line, text, column)
        for path in sorted(QML.rglob('*.qml'))
        for line, text, column in source_captions(path)
        if text
    ]
    assert any(column for _, _, _, column in census), 'The caption census reaches table headers'
    assert any(not column for _, _, _, column in census), 'The caption census reaches field labels'
    offenders = [
        f'{path}:{line}: {text}' for path, line, text, _ in census if not check_caption(text)
    ]
    assert not offenders, (
        'App field labels and table headings start with a capital or case-significant notation:\n'
        + '\n'.join(offenders)
    )
