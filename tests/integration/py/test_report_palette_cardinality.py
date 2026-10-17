"""The real report's Bragg keys retain every frozen structure colour and wraparound."""

import csv
import json
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
SCHEMES = [
    'coast',
    'garden',
    'peaceful',
    'fogForest',
    'sage',
    'okabeIto',
    'paulTolBright',
    'paulTolMuted',
    'tableau',
    'observable',
    'carbon',
    'dark2',
    'petroff',
    'vivid',
    'nord',
    'solarized',
    'catppuccin',
    'apple',
]


def palette(token):
    filename = ''.join('-' + char.lower() if char.isupper() else char for char in token)
    with (ROOT / 'data/palettes' / (filename + '.tsv')).open() as file:
        return [row for row in csv.DictReader(file, delimiter='\t') if row['role'] == 'structure']


@pytest.fixture(scope='module')
def multiphase():
    project = edi.Project.load(ROOT / 'tests/fixtures/report_palette/project')
    project.calculate()
    return project


@pytest.mark.parametrize('scheme', SCHEMES)
def test_captured_report_serializes_all_structure_styles_and_row_labels(multiphase, scheme):
    table = palette(scheme)
    model = json.loads(multiphase.report.model(colour_scheme=scheme).to_json())
    styles = {row['key']: row for row in model['pattern_styles']}
    pattern = model['experiments'][0]['pattern']
    series = [row for row in pattern['series'] if row['kind'] == 'bragg']
    assert len(series) == len(multiphase.structures) and len(series) > 2 * len(table), (
        'Every real structure, both complete palette cycles and the final '
        'wraparound reach the report'
    )
    for place, row in enumerate(series):
        expected = table[place % len(table)]
        assert styles[row['style']]['light'].lower() == expected['light'].lower(), (
            'Captured report Bragg ticks retain each frozen light-theme structure colour'
        )
        assert styles[row['style']]['dark'].lower() == expected['dark'].lower(), (
            'Captured report Bragg ticks retain each frozen dark-theme structure colour'
        )
        assert pattern['bragg_labels'][place]['style'] == row['style'], (
            'Serialized row labels and their ticks carry the same complete structure identity'
        )
