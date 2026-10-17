"""Chart amendments at independently declared fit and scan inputs."""

import csv
import json
import re
import shutil
from pathlib import Path

import edi
import pytest

from tests.integration.py.test_report_iucr_persistence import project

ROOT = Path(__file__).resolve().parents[3]
PALETTES = json.loads((ROOT / 'tests/fixtures/palette_sources/reference.json').read_text())


def model(source, **options):
    loaded = edi.Project.load(source)
    assert hasattr(loaded, 'report'), 'Every chart seam must reach the actual report builder'
    for name, value in options.items():
        setattr(loaded.report, name, value)
    return loaded, json.loads(loaded.report.model().to_json())


def test_unfitted_scan_evolution_names_every_free_parameter_without_points(tmp_path):
    source = tmp_path / 'scan'
    shutil.copytree(ROOT / 'tests/fixtures/scan_template/project', source)
    loaded, document = model(source)
    assert len(loaded.free_parameters) == 39, (
        'The independently committed cosio scan supplies 39 free parameters'
    )
    evolution = document.get('analysis', document).get('evolution')
    assert evolution is not None, (
        'The unfitted scan report retains its evolution parameter catalogue'
    )
    parameters = evolution
    assert len(parameters) == 39 and len({row['name'] for row in parameters}) == 39, (
        'Evolution lists every free parameter once before any dataset is fitted'
    )
    assert all(not row['points'] for row in parameters), (
        'Unfitted evolution parameters have no fabricated points'
    )


def test_pattern_reliability_text_uses_percent_and_two_decimal_metrics(tmp_path):
    source = project(tmp_path, '4()', None)
    analysis = source / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text()
        + """
_fit_result.result_kind deterministic
_fit_result.success true
_fit_result.message done
_fit_result.iterations 1
_fit_result.fitting_time 0
_fit_result.reduced_chi_square 75.62
_fit_result.objective_name chi_square
_fit_result.objective_value 226.86
_fit_result.n_data_points 9
_fit_result.n_parameters 6
_fit_result.n_free_parameters 6
_fit_result.degrees_of_freedom 3
_fit_result.covariance_available false
_fit_result.exit_reason done
_fit_result.prof_wr_factor 0.1635
_fit_result.profile_function cwl-tch-pseudo-voigt
_fit_result.background_function line-segment
_fit_result.descent ladder
"""
    )
    _, document = model(source)
    assert 'Rwp 16.35 % · χ² 75.62' in document['experiments'][0]['pattern']['title'], (
        'Every pattern report title carries percent Rwp and reduced '
        'chi-square with the dialog precision'
    )


def test_default_pattern_titles_are_coloured_segments_with_unstyled_separators(tmp_path):
    source = project(tmp_path, '4()', None)
    loaded = edi.Project.load(source)
    loaded.calculate()
    assert hasattr(loaded, 'report'), 'The coloured-title seam reaches the production report'
    document = json.loads(loaded.report.model().to_json())
    pattern = document['experiments'][0]['pattern']
    main = pattern['y_main']['segments']
    residual = pattern['y_residual']['segments']
    assert [(part['text'], part['style']) for part in main] == [
        ('meas', 'meas.0'),
        (', ', ''),
        ('calc', 'calc'),
        (', ', ''),
        ('bkg', 'bkg'),
    ], 'The shared main axis title names each series in its own style and leaves commas unstyled'
    assert [(part['text'], part['style']) for part in residual] == [
        ('meas', 'meas.0'),
        (' \N{MINUS SIGN} ', ''),
        ('calc', 'calc'),
    ], 'The residual title has separately coloured operands and an unstyled minus separator'
    assert pattern['legend'] is False, (
        'The legend box is hidden by default when coloured axis titles identify series'
    )


@pytest.mark.parametrize('dark', [False, True])
def test_palette_rows_are_data_with_default_first_colour_and_valid_hex(dark):
    directory = ROOT / 'data/palettes'
    paths = sorted(directory.glob('*.tsv'))
    assert len(paths) == 18 and {re.sub(r'[^a-z]', '', path.stem.lower()) for path in paths} == {
        re.sub(r'[^a-z]', '', scheme['id'].lower()) for scheme in PALETTES['schemes']
    }, (
        'ADR-0038 ships exactly the eighteen owner-selected schemes as data; '
        f'actual palette tables={[path.name for path in paths]}'
    )
    schemes = {}

    for path in paths:
        rows = list(csv.DictReader(path.open(), delimiter='\t'))
        assert all(set(row) == {'role', 'index', 'light', 'dark'} for row in rows), (
            'Each palette row declares role, index and both theme colours'
        )
        assert all(
            re.fullmatch(r'#[0-9a-fA-F]{6}', row[theme])
            for row in rows
            for theme in ['light', 'dark']
        ), 'Palette colours are complete RGB hex values in both themes'
        pattern = [row for row in rows if row['role'] == 'pattern']
        structure = [row for row in rows if row['role'] == 'structure']
        gradient = [row for row in rows if row['role'] == 'gradient']
        assert 1 <= len(pattern) <= 7 and 1 <= len(structure) <= 5 and len(gradient) == 2, (
            'ADR-0038 bounds each fixed measured set at seven and each structure set at five, '
            'with exactly two separate gradient endpoints'
        )
        assert {row['role'] for row in rows} == {'pattern', 'structure', 'gradient'}, (
            'The palette data has exactly the three documented colour roles'
        )
        assert [int(row['index']) for row in gradient] == list(range(len(gradient))), (
            'Gradient stops keep contiguous indices in their published order'
        )
        assert [int(row['index']) for row in pattern] == list(range(len(pattern))), (
            'Pattern palette rows have contiguous indices in their declared order'
        )
        assert [int(row['index']) for row in structure] == list(range(len(structure))), (
            'Structure palette rows have contiguous indices in their declared order'
        )
        theme = 'dark' if dark else 'light'
        assert len({row[theme].lower() for row in pattern}) == len(pattern), (
            'Every declared distinct pattern colour differs within a theme'
        )
        forbidden = {'#f44336', '#607d8b', '#8bc34a', '#8c8c8c'}
        assert not forbidden.intersection(row[theme].lower() for row in rows), (
            'No data colour can collide with calculated, background, residual or excluded roles'
        )
        schemes[path.stem.lower()] = pattern
    default = schemes.get(PALETTES['default'])
    assert PALETTES['default'] == 'coast' and default is not None, (
        'ADR-0038 makes Coast the default with an explicit stable scheme identity'
    )
    blue = default[0]['dark' if dark else 'light'].lower()
    red, green, channel_blue = (int(blue[index : index + 2], 16) for index in (1, 3, 5))
    assert channel_blue > max(red, green), (
        f'Coast keeps blue first in each theme while allowing contrast-safe shades; '
        f'actual first colour={blue}'
    )
