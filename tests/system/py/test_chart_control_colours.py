"""Owner coordinates and published colour mathematics observed through the actual core."""

import csv
import importlib.util
import json
import os
import re
import shutil
import subprocess
from operator import itemgetter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/chart_controls'
OWNER = json.loads((FIXTURE / 'owner.json').read_text())
_spec = importlib.util.spec_from_file_location(
    'independent_colour_math', ROOT / 'tests/fixtures/approved_palettes/reference.py'
)
_math = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_math)
_oracle_spec = importlib.util.spec_from_file_location(
    'independent_gamut_math', ROOT / 'tests/fixtures/palette_sources/oklab_reference.py'
)
_oracle = importlib.util.module_from_spec(_oracle_spec)
_oracle_spec.loader.exec_module(_oracle)


def invoke(binary, *arguments):
    result = subprocess.run(
        [str(binary), *map(str, arguments)], capture_output=True, text=True, check=False, timeout=4
    )
    assert result.returncode == 0, (
        'The actual colour observer must complete its requested operation'
    )
    return result.stdout.splitlines()


@pytest.fixture(scope='module')
def colour_probe(tmp_path_factory):
    directory = tmp_path_factory.mktemp('chart-colour-core')
    cmake = (ROOT / 'cmake/edi_core_sources.cmake').read_text()
    generated = []
    for key, folder, stem, tag in (
        ('EDI_PALETTES', 'palettes', 'palette_data', 'edi_palette'),
        ('EDI_COLOUR_MAPS', 'colormaps', 'colour_map_data', 'edi_colour_map'),
    ):
        found = re.search(r'set\(' + key + r'\s+([^)]*)\)', cmake)
        assert found is not None, 'The observer embeds the production CMake catalogue'
        names = found[1].split()
        template = (ROOT / f'core/src/{stem}.cpp.in').read_text()
        tables = ''.join(
            f'R"{tag}(' + (ROOT / f'data/{folder}/{name}.tsv').read_text() + f'){tag}",\n'
            for name in names
        )
        replacements = {
            '@EDI_PALETTE_TABLES@': tables,
            '@EDI_COLOUR_MAP_TABLES@': tables,
            '@EDI_COLOUR_MAP_COUNT@': str(len(names)),
            '@EDI_COLOUR_MAP_NAMES@': ''.join(f'"{name}",\n' for name in names),
        }
        for source, value in replacements.items():
            template = template.replace(source, value)
        path = directory / f'{stem}.cpp'
        path.write_text(template)
        generated.append(str(path))
    compiler = os.environ.get('CXX') or shutil.which('c++')
    assert compiler, 'The native acceptance observer requires a C++20 compiler'
    binary = directory / 'colour-probe'
    compiled = subprocess.run(
        [
            compiler,
            *(
                ['-DHAS_FIGURE_COLOURS']
                if 'enum class FigureKind' in (ROOT / 'core/include/edi/palette.hpp').read_text()
                else []
            ),
            '-std=c++20',
            '-O0',
            '-I',
            str(ROOT / 'core/include'),
            str(ROOT / 'core/src/palette.cpp'),
            str(ROOT / 'core/src/scan_views.cpp'),
            *generated,
            str(FIXTURE / 'probe.cpp'),
            '-o',
            str(binary),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=25,
    )
    assert compiled.returncode == 0, (
        'The real core colour sources compile independently of a product sibling: '
        + compiled.stderr
    )
    return binary


def catalogue(binary):
    rows = [line.split('\t') for line in invoke(binary, 'catalogue')]
    return {title: token for token, title in rows[:-1]}, rows[-1][1]


def test_exact_palette_names_order_and_earth_default(colour_probe):
    names, default = catalogue(colour_probe)
    assert list(names) == [row['name'] for row in OWNER['palettes']], (
        'Preferences and the core offer exactly Earth, Classic, Soft, Natural, Colour-blind safe'
    )
    assert default == 'Earth', 'A new user defaults to the owner-selected Earth palette'


@pytest.mark.parametrize('palette', OWNER['palettes'], ids=itemgetter('name'))
@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_palette_coordinates_and_calc_match_owner_bytes(colour_probe, palette, theme):
    names, _ = catalogue(colour_probe)
    token = names.get(palette['name'])
    assert token is not None, 'Every owner-approved palette is present in the native catalogue'
    output = invoke(colour_probe, 'colours', token, theme)
    assert output[0].split('\t')[1] == OWNER['calc'][theme], (
        'All five palettes have the exact common calculation colour for the requested theme'
    )
    table_paths = list((ROOT / 'data/palettes').glob('*.tsv'))
    actual = []
    for path in table_paths:
        rows = list(csv.DictReader(path.read_text().splitlines(), delimiter='\t'))
        colours = [
            row[theme]
            for row in rows
            if row['role'] not in {'total_calculation', 'background', 'difference'}
        ]
        actual.append(colours)
    assert palette[theme] in actual, (
        'The embedded palette data retains all eleven owner colours in exact assignment order'
    )


def test_every_palette_retains_prefix_when_more_items_are_added(colour_probe):
    names, _ = catalogue(colour_probe)
    for palette in OWNER['palettes']:
        token = names.get(palette['name'])
        assert token is not None, 'Every shared palette must expose its assignment function'
        for theme in ('light', 'dark'):
            rows = [line.split('\t') for line in invoke(colour_probe, 'colours', token, theme)[1:]]
            patterns = [row[1] for row in rows]
            if palette['name'] == 'Earth':
                assert patterns[:2] == palette[theme][:2], (
                    'Earth retains its first two reserved experiment colours at eleven items'
                )
            else:
                assert patterns == palette[theme], (
                    'Eleven experiments use eleven categorical colours before any shade'
                )


def test_map_catalogue_has_only_the_six_named_choices(colour_probe):
    names = [line.split('\t')[1] for line in invoke(colour_probe, 'maps')]
    assert names == OWNER['maps'], (
        'The map catalogue has exactly six capitalised names with an ASCII hyphen in Blue-Red'
    )


@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_blue_red_stops_and_nontrivial_oklab_interpolation(colour_probe, theme):
    rows = [line.split('\t') for line in invoke(colour_probe, 'maps')]
    token = next((token for token, title in rows if title == 'Blue-Red'), None)
    assert token is not None, 'Blue-Red is offered as the owner-selected map'
    samples = [
        list(map(int, line.split('\t'))) for line in invoke(colour_probe, 'map', token, theme)
    ]
    assert len(samples) >= 3, 'A colour bar has a nonempty interior and both endpoint colours'
    stops = OWNER['blue_red'][theme]
    for index in (
        0,
        len(samples) // 7,
        len(samples) // 2,
        len(samples) * 4 // 5,
        len(samples) - 1,
    ):
        t = index / (len(samples) - 1)
        segment = min(int(t * 2), 1)
        expected = _math.gradient(stops[segment], stops[segment + 1], t * 2 - segment)
        actual = '#' + ''.join(f'{channel:02X}' for channel in samples[index][1:4])
        assert actual == expected and samples[index][4] == 255, (
            'The map samples the recorded OKLab stops, including its interior'
        )


def luminance(colour):
    channels = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
    return sum(a * b for a, b in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))


def contrast(first, second):
    a, b = sorted((luminance(first), luminance(second)))
    return (b + 0.05) / (a + 0.05)


def contrast_rounding_bound(colour, backgrounds):
    channels = [int(colour[i : i + 2], 16) for i in (1, 3, 5)]
    # The accepted error is one RGB encoding step, computed from the actual
    # quantisation cell, independently of edi's output arithmetic.
    neighbours = [
        '#' + ''.join(f'{min(255, max(0, v + shift)):02X}' for v in channels) for shift in (-1, 1)
    ]
    return max(
        abs(contrast(value, bg) - contrast(colour, bg))
        for value in neighbours
        for bg in backgrounds
    )


@pytest.mark.parametrize('scheme', ['jmol', 'vesta'])
@pytest.mark.parametrize(
    'backgrounds',
    [['#FFFFFF', '#F2F2F2', '#E6E6E6'], ['#444444', '#393939', '#333333']],
    ids=['light', 'dark'],
)
def test_element_adjustment_reaches_two_to_one_without_unneeded_movement(
    colour_probe, scheme, backgrounds
):
    rows = list(
        csv.DictReader(
            (ROOT / 'data/elements/element-styles.tsv').read_text().splitlines(), delimiter='\t'
        )
    )
    tested = 0
    for row in rows:
        source = row[scheme]
        if not re.fullmatch(r'#[0-9A-Fa-f]{6}', source):
            continue
        actual = invoke(colour_probe, 'readable', source, *backgrounds)[0]
        assert min(contrast(actual, bg) for bg in backgrounds) >= 2 - contrast_rounding_bound(
            actual, backgrounds
        ), 'Each Jmol and VESTA element meets 2:1 on every independently supplied underlay'
        if min(contrast(source, bg) for bg in backgrounds) >= 2:
            assert actual.upper() == source.upper(), (
                'Elements reaching 2:1 keep their bytes even when below 3:1'
            )
        else:
            origin = _math.lab(source)[0]
            endpoint = (
                0
                if min(contrast('#000000', bg) for bg in backgrounds)
                > min(contrast('#FFFFFF', bg) for bg in backgrounds)
                else 1
            )
            passing, failing = endpoint, origin
            for _ in range(36):
                middle = (passing + failing) / 2
                candidate = _oracle.gamut_ray(source, middle)
                if min(_oracle.lab_contrast(candidate, bg) for bg in backgrounds) >= 2:
                    passing = middle
                else:
                    failing = middle
            assert abs(_math.lab(actual)[0] - passing) <= _oracle.full_step_lightness_tolerance(
                actual
            ), 'Every element makes the least lightness move to the shared 2:1 feasible boundary'
            assert _oracle.gamut_hue_chroma_preserved(source, actual), (
                'Both element schemes retain hue and maximal in-gamut chroma'
            )
        tested += 1
    assert (
        tested == sum(bool(re.fullmatch(r'#[0-9A-Fa-f]{6}', row[scheme])) for row in rows)
        and tested > 0
    ), 'The common rule reaches every valid colour of each published element scheme'


def test_hydrogen_and_carbon_are_distinct_in_light_tables(colour_probe):
    h = invoke(colour_probe, 'readable', '#FFFFFF', '#FFFFFF', '#F2F2F2')[0]
    c = invoke(colour_probe, 'readable', '#909090', '#FFFFFF', '#F2F2F2')[0]
    assert h != c, (
        'The revised element rule no longer collapses Jmol hydrogen and carbon to one grey'
    )


def test_independent_colour_observer_controls():
    assert contrast('#000000', '#FFFFFF') == 21, (
        'WCAG black and white give the published 21:1 control'
    )
    assert _math.gradient('#000000', '#FFFFFF', 0.5) == '#636363', (
        'The independent OKLab midpoint differs from encoded-sRGB interpolation'
    )


@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_overflow_keeps_categorical_prefix_and_uses_first_two_colour_family(colour_probe, theme):
    names, _ = catalogue(colour_probe)
    for palette in OWNER['palettes'][1:]:
        token = names.get(palette['name'])
        assert token is not None, 'Each pool palette is available before testing overflow'
        a, b = map(_math.lab, palette[theme][:2])
        for count in (12, 17, 162):
            rows = [
                line.split('\t')
                for line in invoke(colour_probe, 'colours', token, theme, count)[1:]
            ]
            assert [row[1] for row in rows[:11]] == palette[theme], (
                'Adding overflow items retains all eleven occupied categorical positions'
            )
            for row in rows[11:]:
                value = _math.lab(row[1])
                delta = [y - x for x, y in zip(a, b, strict=True)]
                t = max(
                    0,
                    min(
                        1,
                        sum((v - x) * d for v, x, d in zip(value, a, delta, strict=True))
                        / sum(d * d for d in delta),
                    ),
                )
                segment_error = (
                    sum((v - (x + t * d)) ** 2 for v, x, d in zip(value, a, delta, strict=True))
                    ** 0.5
                )
                hue_error = min(
                    sum((v - x) ** 2 for v, x in zip(value[1:], anchor[1:], strict=True)) ** 0.5
                    for anchor in (a, b)
                )
                tolerance = 2 * _oracle.full_step_lightness_tolerance(row[1])
                assert min(segment_error, hue_error) <= tolerance, (
                    'Overflow uses the first two colours within RGB quantisation'
                )


@pytest.mark.parametrize('palette', OWNER['palettes'], ids=itemgetter('name'))
def test_one_assignment_function_reserves_only_earth_and_reuses_holes(colour_probe, palette):
    names, _ = catalogue(colour_probe)
    token = names.get(palette['name'])
    assert token is not None, 'Every palette participates in the shared assignment contract'
    reserved = palette['name'] == 'Earth'
    for kinds in ('sesese', 'eeesss', 'ssseee', 'ssssss', 'eeeeee', ''):
        output = invoke(colour_probe, 'positions', token, *kinds)
        assert all(value.isdecimal() for value in output), (
            'One native pure function assigns both experiment and structure positions'
        )
        used, expected = set(), []
        for kind in kinds:
            position = 2 if reserved and kind == 's' else 0
            while position in used:
                position += 1
            expected.append(position)
            used.add(position)
        assert list(map(int, output)) == expected, (
            'Items take the lowest free position, with two Earth reservations only'
        )
    retained = ('e:4', 's:6', 'e', 's', 'e:4')
    output = list(map(int, invoke(colour_probe, 'positions', token, *retained)))
    assert output[:2] == [4, 6] and len(set(output)) == len(output), (
        'Existing positions survive additions while duplicate claims cannot share one colour'
    )
    assert output[2] == 0 and output[3] == (2 if reserved else 1), (
        'Removing earlier items frees holes for the next experiment or structure'
    )


def test_original_element_scheme_data_is_unchanged_for_three_dimensions():
    assert (ROOT / 'data/elements/element-styles.tsv').read_bytes() == (
        FIXTURE / 'element-styles.tsv'
    ).read_bytes(), (
        'The 2D adaptation never edits the source Jmol or VESTA colours used by the 3D renderer'
    )
