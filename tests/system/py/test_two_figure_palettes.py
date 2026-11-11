"""Approved coordinates and dataset interpolation observed through the native core."""

import csv
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.approved_palettes.ciede import delta, srgb_lab
from tests.fixtures.approved_palettes.reference import gradient
from tests.system.py import test_approved_palettes as prior

palette_probe = prior.palette_probe

ROOT = Path(__file__).resolve().parents[3]
COLOURS = {
    'main': {
        'light': ['#618EC8', '#8B9762', '#DB7A12', '#2E8F8A', '#C877B7'],
        'dark': ['#6E92CB', '#94935C', '#F5961A', '#55B1B3', '#C375C2'],
        'calc': ['#E5533D', '#F26A55'],
    },
    'colourBlindSafe': {
        'light': ['#548CF1', '#7E996B', '#DD7C0F', '#1E7679', '#C577B1'],
        'dark': ['#6A93F8', None, '#F99A1D', '#73C2C0', '#C175B6'],
        'calc': ['#D04B37', '#F1634C'],
    },
}


def invoke(probe, *args):
    result = subprocess.run(
        [str(probe), *args], capture_output=True, text=True, timeout=3, check=False
    )
    assert result.returncode == 0, (
        'Each approved palette must be available through the actual native API'
    )
    return result.stdout.splitlines()


def test_only_two_palettes_and_main_default(palette_probe):
    assert invoke(palette_probe) == ['main', 'colourBlindSafe', 'default=main'], (
        'The core must expose exactly Main and Colour-blind safe and default to Main'
    )


@pytest.mark.parametrize('scheme', COLOURS)
@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_exact_approved_roles(palette_probe, scheme, theme):
    rows = invoke(palette_probe, scheme, 'table', theme)
    colours = {int(row.split('\t')[0]): row.split('\t')[1].upper() for row in rows}
    for i, expected in enumerate(COLOURS[scheme][theme]):
        if expected is not None:
            assert colours[i] == expected, (
                'The core must retain each approved experiment and structure coordinate'
            )
    roles = invoke(palette_probe, scheme, 'roles')
    assert (
        roles[3 if theme == 'dark' else 0].upper() == COLOURS[scheme]['calc'][theme == 'dark']
    ), 'Each palette must use its own approved calculation colour'


@pytest.mark.parametrize('scheme', COLOURS)
@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_pattern_threshold_reservations_and_oklab(palette_probe, scheme, theme):
    tables = []
    for path in (ROOT / 'data/palettes').glob('*.tsv'):
        rows = list(csv.DictReader(path.read_text().splitlines(), delimiter='\t'))
        figures = [r[theme].upper() for r in rows if r['role'] == 'figure']
        if figures and figures[0] == COLOURS[scheme][theme][0]:
            tables.append(figures)
    assert len(tables) == 1, 'Each approved palette must have one native data table'
    figures = tables[0]
    rows = invoke(palette_probe, scheme, 'patterns', theme)
    for line in rows:
        structures, count, place, actual = line.split('\t')
        structures, count, place = int(structures), int(count), int(place)
        taken = set(range(2, structures + 2))
        free = [i for i in range(len(figures)) if i not in taken]
        limit = 8 - max(0, structures - 3)
        if count <= limit:
            expected = figures[free[place]]
        else:
            expected = gradient(figures[0], figures[1], place / (count - 1))
        assert actual.upper() == expected, (
            'Pattern sets must use free discrete colours through eight datasets, reduce capacity '
            'for extra structures, then use OKLab shades with exact endpoints'
        )


def test_independent_interpolation_has_nonidentity_witness():
    assert gradient('#000000', '#FFFFFF', 0.5) == '#636363', (
        'The independent OKLab observer must distinguish perceptual mixing from encoded RGB mixing'
    )


def test_independent_ciede_observer_matches_published_pair():
    assert delta((50, 2.6772, -79.7751), (50, 0, -82.7485)) == pytest.approx(
        2.0425, abs=0.00005
    ), 'The CIEDE2000 observer must agree with Sharma supplementary pair 1'
    assert delta((50, 0, 0), (50, 0, 0)) == 0, (
        'Identical CIELAB coordinates must have zero difference'
    )


def test_colour_blind_dark_gradient_stays_clear_of_background(palette_probe):
    rows = invoke(palette_probe, 'colourBlindSafe', 'patterns', 'dark')
    background = prior.ROLE_GREYS['dark']['background']
    for row in rows:
        structures, count, _, colour = row.split('\t')
        if int(structures) == 3 and int(count) >= 9:
            assert delta(srgb_lab(colour), srgb_lab(background)) >= 8, (
                'Every sampled dark Colour-blind safe gradient shade must stay at least eight '
                'CIEDE2000 units from the retained background grey'
            )
