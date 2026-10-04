"""P0c: keep the adapter mapping-vs-logic measurement re-derivable."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[3]
MEASUREMENT = ROOT / 'tests' / 'unit' / 'cpp' / 'e09_t55_adapter_classification.json'
CLASSIFICATION_SOURCE = (
    ROOT / 'tests' / 'unit' / 'cpp' / 'e09_t55_adapter_classification_source.txt'
)
FUNCTION_START = re.compile(r'^[A-Za-z_][^;=]*\(')


def _load() -> dict[str, Any]:
    document = json.loads(MEASUREMENT.read_text(encoding='utf-8'))
    assert isinstance(document, dict), 'the adapter measurement must be a JSON object'
    return document


def _function_end(  # noqa: PLR0912
    source: str, line_offsets: list[int], start_line: int
) -> int:
    opening = source.find('{', line_offsets[start_line - 1])
    assert opening >= 0, 'every classified adapter function must have a body'
    depth = 0
    mode = 'code'
    escaped = False
    index = opening
    while index < len(source):
        character = source[index]
        following = source[index + 1] if index + 1 < len(source) else ''
        if mode == 'code':
            if character == '/' and following == '/':
                mode = 'line-comment'
                index += 2
                continue
            if character == '/' and following == '*':
                mode = 'block-comment'
                index += 2
                continue
            if character == '"':
                mode = 'string'
                escaped = False
            elif character == "'":
                mode = 'character'
                escaped = False
            elif character == '{':
                depth += 1
            elif character == '}':
                depth -= 1
                if depth == 0:
                    return source.count('\n', 0, index) + 1
        elif mode == 'line-comment':
            if character == '\n':
                mode = 'code'
        elif mode == 'block-comment':
            if character == '*' and following == '/':
                mode = 'code'
                index += 2
                continue
        elif escaped:
            escaped = False
        elif character == '\\':
            escaped = True
        elif (mode == 'string' and character == '"') or (mode == 'character' and character == "'"):
            mode = 'code'
        index += 1
    raise AssertionError(f'unbalanced function beginning at line {start_line}')


def test_e09_t55_adapter_mapping_logic_measurement_is_total_and_anchored() -> None:
    document = _load()
    classification_source = document['classification_source']
    source_bytes = CLASSIFICATION_SOURCE.read_bytes()
    source = source_bytes.decode()
    lines = source.splitlines()
    assert document['schema'] == 2, 'the adapter measurement schema must remain version two'
    assert document['task'] == 'adapter-mapping-classification', (
        'the adapter measurement must identify its retained classification'
    )
    assert classification_source == {
        'anchor': 'content-sha256-v1',
        'path': 'tests/unit/cpp/e09_t55_adapter_classification_source.txt',
        'reason': (
            'The classification predates P0d, so its exact measured bytes are retained '
            'in-tree; content identity proves what was measured without requiring commit history.'
        ),
        'sha256': hashlib.sha256(source_bytes).hexdigest(),
        'lines': len(lines),
    }, 'the historical classification must remain tied to its exact working-tree source bytes'

    # Live source digests retired by the 2026-09-07 owner ruling ().
    # The frozen classification_source remains the measurement's exact reference.

    assert set(document['criterion']) == {'mapping', 'logic'}, (
        'the adapter classification must retain exactly mapping and logic outcomes'
    )
    assert all(document['criterion'].values()), (
        'each adapter classification outcome must carry its criterion'
    )

    rows = document['functions']
    starts = [
        line_number for line_number, line in enumerate(lines, 1) if FUNCTION_START.match(line)
    ]
    assert [row['start_line'] for row in rows] == starts, (
        'every named adapter function/overload must be classified exactly once'
    )
    assert len({row['id'] for row in rows}) == len(rows), (
        'every classified adapter function identifier must be unique'
    )
    assert all(row['classification'] in {'mapping', 'logic'} for row in rows), (
        'every adapter function must resolve to a declared outcome'
    )
    assert all(len(row['reason']) >= 20 for row in rows), (
        'every adapter classification must carry a substantive reason'
    )

    offsets = [0]
    offsets.extend(match.end() for match in re.finditer(r'\n', source))
    for row in rows:
        assert _function_end(source, offsets, row['start_line']) == row['end_line'], (
            f'the classified function span must match the anchored source: {row["id"]}'
        )

    mapping = [row for row in rows if row['classification'] == 'mapping']
    logic = [row for row in rows if row['classification'] == 'logic']

    def span(row: dict[str, Any]) -> int:
        return row['end_line'] - row['start_line'] + 1

    assert document['summary'] == {
        'named_functions': len(rows),
        'mapping_functions': len(mapping),
        'logic_functions': len(logic),
        'classified_function_span_lines': sum(span(row) for row in rows),
        'mapping_span_lines': sum(span(row) for row in mapping),
        'logic_span_lines': sum(span(row) for row in logic),
    }, 'the adapter summary must be derived exactly from classified function spans'
