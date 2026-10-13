"""Final Data exclusion defaults and the independently declared measured point inventory."""

import json
import re
import shutil
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]


def input_project(tmp_path, include_all):
    path = tmp_path / 'data_block'
    shutil.copytree(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', path)
    file = path / 'project.edi'
    if include_all:
        # The accepted record spelling writes an explicit empty list in double quotes.
        file.write_text(file.read_text() + '\n_report.excluded ""\n')
    return path


@pytest.mark.parametrize('include_all', [False, True], ids=['absent-default', 'explicit-empty'])
def test_data_default_and_explicit_include_all_reach_report_and_html(tmp_path, include_all):
    path = input_project(tmp_path, include_all)
    original = (path / 'project.edi').read_bytes()
    loaded = edi.Project.load(path)
    loaded.calculate()
    assert hasattr(loaded, 'report'), 'The Data seam reaches the production project-owned report'
    document = json.loads(loaded.report.model().to_json())
    expected_keys = ['charts', 'correlations', 'reflections', 'data']
    contents = document['contents']
    assert [row['key'] for row in contents] == expected_keys, (
        'A non-scan report exposes only the four final optional group keys in their declared order'
    )
    assert all(row.get('depth', 0) == 0 for row in contents), (
        'Optional Contents groups are a flat list rather than a category tree'
    )
    assert next(row['included'] for row in contents if row['key'] == 'data') is include_all, (
        'An absent excluded item leaves Data out while an explicit empty item includes it'
    )
    assert all(row['included'] for row in contents if row['key'] != 'data'), (
        'The Data default leaves every other optional group included'
    )
    categories = document['experiments'][0]['categories']
    blocks = [row for row in categories if row['id'] == 'data']
    assert bool(blocks) is include_all, (
        'The Data group controls the entire per-experiment Data block'
    )
    if include_all:
        assert len(blocks) == 1, 'Each experiment has exactly one included Data block'
        table = blocks[0]['table']
        assert len(table['rows']) == 9, (
            'The Data block retains all nine independently declared measured points'
        )
        assert len(table['columns']) >= 5, (
            'Data includes the axis, Imeas, its s.u., Icalc and Ibkg'
        )
        axis = [float(row[0]) for row in table['rows']]
        assert axis == [40, 44, 48, 52, 56, 60, 64, 68, 72], (
            'The Data table preserves each declared native axis value in order'
        )
        assert [float(row[2]) for row in table['rows']] == [1] * 9, (
            'Data retains every independently declared measurement uncertainty'
        )
        for index in range(5):
            cells = [row[index] for row in table['rows']]
            assert all(re.fullmatch(r'[-+]?\d+(?:\.\d+)?', value) for value in cells), (
                'Computed Data values use plain fixed decimals without exponent notation'
            )
            decimals = {len(value.partition('.')[2]) for value in cells if float(value) != 0}
            assert len(decimals) <= 1, (
                'Each numeric Data column uses one decimal precision for every nonzero row'
            )
        rows = blocks[0]['rows']
        assert any('point' in row['label'].lower() and '9' in row['text'] for row in rows), (
            'The Data summary names the independent point count'
        )
        assert any(
            'range' in row['label'].lower() and '40' in row['text'] and '72' in row['text']
            for row in rows
        ), 'The Data summary includes the independently declared native axis range'
        assert any('file' in row['label'].lower() for row in rows), (
            'The Data block names the data-file source even for embedded observations'
        )
        html = loaded.report.as_html()
        assert all(row[0] in html for row in table['rows']), (
            'HTML contains the same Data axis cells as the shared preview model'
        )
    assert (path / 'project.edi').read_bytes() == original, (
        'Building Data with project options never rewrites those options into the input file'
    )
