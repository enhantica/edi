"""Versioned report JSON at nontrivial numeric and UTF-8 seams."""

import json
import math
import struct

import edi
import pytest

TITLE = 'Quotes " and \\, tab\t, separators\u2028\u2029 and \U0001d6c2'
VALUES = [0.1, -0.0, 5e-324, 1.7976931348623157e308]


def group(document, name):
    return document.get(name, document)


def number(row):
    return row['value'] if isinstance(row['value'], dict) else row


def report_model():
    assert hasattr(edi, 'ReportModel'), (
        'The core report model must have its planned Python binding'
    )
    project = edi.Project(name='numeric_report')
    assert hasattr(project, 'report'), 'The model builder must be reached through Project.report'
    project.report.parameters = 'all'
    model = project.report.model()
    document = json.loads(model.to_json())
    assert document['schema_version'] == 1, 'Report JSON must identify its schema version as one'
    return document


@pytest.mark.parametrize(
    'value', VALUES, ids=['decimal', 'negative-zero', 'subnormal', 'max-double']
)
def test_report_json_numbers_have_shortest_roundtrip_bits(value):
    document = report_model()
    rows = group(document, 'analysis')['parameters']
    assert rows, 'The default project supplies a parameter row for the numeric seam'
    row = dict(rows[0])
    number(row).update(value=value, su=value if value >= 0 else 0.0)
    row['start'] = value
    group(document, 'analysis')['parameters'] = [row]
    serialized = json.dumps(document, ensure_ascii=False, allow_nan=False)
    model = edi.ReportModel.from_json(serialized)
    actual = model.to_json()
    restored = json.loads(actual)
    restored_row = group(restored, 'analysis')['parameters'][0]
    for key in ('value', 'su', 'start'):
        assert struct.pack(
            '>d', (restored_row[key] if key == 'start' else number(restored_row)[key])
        ) == struct.pack('>d', row[key] if key == 'start' else number(row)[key]), (
            'Report doubles must round-trip by bits, including signed zero and subnormals'
        )
    assert edi.ReportModel.from_json(actual).to_json() == actual, (
        'Canonical report JSON must be byte-identical after every parse and re-serialization'
    )
    assert restored == document, 'No schema field may disappear in a report JSON round trip'


def test_report_json_utf8_nulls_and_fixed_generated_roundtrip():
    document = report_model()
    document['generated'] = '2026-10-13 16:00 UTC'
    group(document, 'project')['title'] = TITLE
    group(document, 'project')['authors'] = "Ada Lovelace; Émile O'Brien"
    row = dict(group(document, 'analysis')['parameters'][0])
    number(row).update(value=0.1, su=None)
    row['start'] = None
    group(document, 'analysis')['parameters'] = [row]
    model = edi.ReportModel.from_json(json.dumps(document, ensure_ascii=False))
    actual = model.to_json()
    assert json.loads(actual) == document, (
        'Report JSON must retain every UTF-8 text, explicit null and fixed UTC generated field'
    )
    assert edi.ReportModel.from_json(actual).to_json() == actual, (
        'Text and absent values must retain canonical JSON bytes across a round trip'
    )


def test_report_builder_serializes_nonfinite_uncertainty_as_null():
    assert hasattr(edi, 'ReportModel'), (
        'The planned report model must exist before numeric projection'
    )
    project = edi.Project(name='nonfinite_report')
    project.structure.cell.length_a = edi.Parameter(5.1, math.nan, True)
    project.report.parameters = 'all'
    text = project.report.model().to_json()
    assert 'NaN' not in text and 'Infinity' not in text, (
        'A nonfinite model number must serialize as JSON null rather than invalid numeric text'
    )
    rows = group(json.loads(text), 'analysis')['parameters']
    assert any(number(row)['value'] == 5.1 and number(row)['su'] is None for row in rows), (
        'The builder must project a real nonfinite standard uncertainty to explicit null'
    )
