"""The real report's Bragg keys retain every frozen structure colour and whole-group gradient."""

import json
from pathlib import Path

import edi
import pytest

from tests.fixtures.approved_palettes.reference import PALETTES, SCHEMES, assigned

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def multiphase():
    project = edi.Project.load(ROOT / 'tests/fixtures/report_palette/project')
    project.calculate()
    return project


@pytest.mark.parametrize('scheme', SCHEMES)
def test_captured_report_serializes_all_structure_styles_and_row_labels(multiphase, scheme):
    palette = PALETTES[SCHEMES.index(scheme)]
    model = json.loads(multiphase.report.model(colour_scheme=scheme).to_json())
    styles = {row['key']: row for row in model['pattern_styles']}
    pattern = model['experiments'][0]['pattern']
    series = [row for row in pattern['series'] if row['kind'] == 'bragg']
    assert len(series) == len(multiphase.structures) and len(series) > 10, (
        'Every real structure, the whole-group gradient beyond five, including the final '
        'endpoint reach the report'
    )
    for place, row in enumerate(series):
        expected = {
            theme: assigned(palette, 'structures', place, len(series), theme)
            for theme in ('light', 'dark')
        }
        assert styles[row['style']]['light'].lower() == expected['light'].lower(), (
            'Captured report Bragg ticks retain each frozen light-theme structure colour'
        )
        assert styles[row['style']]['dark'].lower() == expected['dark'].lower(), (
            'Captured report Bragg ticks retain each frozen dark-theme structure colour'
        )
        assert pattern['bragg_labels'][place]['style'] == row['style'], (
            'Serialized row labels and their ticks carry the same complete structure identity'
        )
