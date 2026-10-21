"""Approved colours and Ottosson's independent Oklab interpolation.

The matrices are from https://bottosson.github.io/posts/oklab/ (2020,
updated 2021). The owner-supplied coordinates are copied by the fixture generator.
"""

import json
import math
import os
import re
import shutil
import subprocess
from operator import itemgetter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/approved_palettes'
PALETTES = json.loads((FIXTURE / 'colours.json').read_text())['palettes']


def normalized(value):
    return re.sub(r'[^a-z]', '', value.lower()).removeprefix('edi')


def multiply(matrix, values):
    return tuple(sum(a * b for a, b in zip(row, values, strict=True)) for row in matrix)


def lab(colour):
    rgb = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    lms = multiply(
        (
            (0.4122214708, 0.5363325363, 0.0514459929),
            (0.2119034982, 0.6806995451, 0.1073969566),
            (0.0883024619, 0.2817188376, 0.6299787005),
        ),
        linear,
    )
    return multiply(
        (
            (0.2104542553, 0.7936177850, -0.0040720468),
            (1.9779984951, -2.4285922050, 0.4505937099),
            (0.0259040371, 0.7827717662, -0.8086757660),
        ),
        [math.cbrt(v) for v in lms],
    )


def gradient(first, second, t):
    if t == 0:
        return first
    if t == 1:
        return second
    mixed = [a + (b - a) * t for a, b in zip(lab(first), lab(second), strict=True)]
    lms = multiply(
        (
            (1, 0.3963377774, 0.2158037573),
            (1, -0.1055613458, -0.0638541728),
            (1, -0.0894841775, -1.2914855480),
        ),
        mixed,
    )
    rgb = multiply(
        (
            (4.0767416621, -3.3077115913, 0.2309699292),
            (-1.2684380046, 2.6097574011, -0.3413193965),
            (-0.0041960863, -0.7034186147, 1.7076147010),
        ),
        [v**3 for v in lms],
    )
    encoded = [12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055 for v in rgb]
    return '#' + ''.join(f'{math.floor(min(1, max(0, v)) * 255 + 0.5):02X}' for v in encoded)


@pytest.fixture(scope='module')
def palette_probe(tmp_path_factory):
    directory = tmp_path_factory.mktemp('palette-native')
    source = (ROOT / 'cmake/edi_core_sources.cmake').read_text()
    declaration = re.search(r'set\(EDI_PALETTES\s+([^)]*)\)', source)
    assert declaration is not None, 'The native probe must embed the production palette catalogue'
    entries = []
    for name in declaration[1].split():
        text = (ROOT / f'data/palettes/{name}.tsv').read_text()
        entries.append('R"edi_palette(' + text + ')edi_palette",\n')
    embedded = directory / 'palette_data.cpp'
    embedded.write_text(
        (ROOT / 'core/src/palette_data.cpp.in')
        .read_text()
        .replace('@EDI_PALETTE_TABLES@', ''.join(entries))
    )
    binary = directory / 'palette-probe'
    compiler = os.environ.get('CXX') or shutil.which('c++')
    assert compiler, 'The native palette acceptance probe requires the configured C++ compiler'
    flags = (
        ['-DHAS_CHART_ROLES']
        if 'enum class ChartRole' in (ROOT / 'core/include/edi/palette.hpp').read_text()
        else []
    )
    result = subprocess.run(
        [
            compiler,
            *flags,
            '-std=c++20',
            '-O0',
            '-I',
            str(ROOT / 'core/include'),
            str(ROOT / 'core/src/palette.cpp'),
            str(embedded),
            str(FIXTURE / 'probe.cpp'),
            '-o',
            str(binary),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=25,
    )
    assert result.returncode == 0, (
        'The actual palette source must compile for acceptance: ' + result.stderr
    )
    return binary


def catalogue(probe):
    result = subprocess.run([str(probe)], capture_output=True, text=True, check=True, timeout=2)
    lines = result.stdout.splitlines()
    return lines[:-1], lines[-1].removeprefix('default=')


def test_exact_catalogue_order_and_natural_default(palette_probe):
    names, default = catalogue(palette_probe)
    assert list(map(normalized, names)) == [normalized(p['name']) for p in PALETTES], (
        'The core catalogue lists exactly the five approved palettes in display order'
    )
    assert normalized(default) == 'natural', 'A new user and an unknown preference use Edi Natural'


@pytest.mark.parametrize('palette', PALETTES, ids=itemgetter('name'))
@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('role', ['measured', 'structures'])
def test_actual_colour_assignment_matches_approved_order_and_oklab(
    palette_probe, palette, theme, role
):
    names, _ = catalogue(palette_probe)
    token = next((name for name in names if normalized(name) == normalized(palette['name'])), None)
    assert token is not None, 'Each approved palette must be available through the actual core API'
    result = subprocess.run(
        [str(palette_probe), token, role, theme],
        capture_output=True,
        text=True,
        check=True,
        timeout=2,
    )
    seen = []
    for line in result.stdout.splitlines():
        count, place, actual = line.split('\t')
        count, place = int(count), int(place)
        if role == 'structures' and count > 0 and place >= count:
            continue
        colours = palette[theme][role]
        # The existing empty/index contract clamps categorical indices to the stored set.
        expected = (
            colours[min(place, 4)]
            if count <= 5
            else gradient(colours[0], colours[1], min(place, count - 1) / (count - 1))
        )
        assert actual.upper() == expected, (
            'Both groups use their own five approved colours, then a whole-group Oklab gradient; '
            f'{palette["name"]}/{theme}/{role}, count={count}, place={place}'
        )
        seen.append((count, place))
    assert {count for count, _ in seen} == {0, 1, 2, 5, 6, 17}, (
        'The core assignment must reach empty, categorical, threshold and larger groups'
    )


def test_independent_oklab_observer_reaches_neutral_and_nonidentity_controls():
    assert lab('#000000') == (0, 0, 0), 'The independent Oklab black control is the origin'
    assert lab('#FFFFFF') == pytest.approx((1, 0, 0), abs=1e-7), (
        'Ottosson matrices map white to unit neutral lightness'
    )
    assert gradient('#000000', '#FFFFFF', 0.5) == '#636363', (
        'A half-lightness Oklab grey is not the encoded-sRGB midpoint'
    )
    assert gradient('#039EDC', '#8989F7', 0.4) != gradient('#039EDC', '#8989F7', 0.5), (
        'A nontrivial sampling control distinguishes the required t from a fixed midpoint'
    )


@pytest.mark.parametrize('palette', PALETTES, ids=itemgetter('name'))
def test_actual_role_colours_match_approved_light_and_dark(palette_probe, palette):
    names, _ = catalogue(palette_probe)
    token = next((name for name in names if normalized(name) == normalized(palette['name'])), None)
    assert token is not None, 'Each approved palette supplies its own chart role colours'
    result = subprocess.run(
        [str(palette_probe), token, 'roles'], capture_output=True, text=True, check=True, timeout=2
    )
    expected = [
        palette[theme][role]
        for theme in ('light', 'dark')
        for role in ('total_calculation', 'background', 'difference')
    ]
    assert [line.upper() for line in result.stdout.splitlines()] == expected, (
        'Total calculation, background and difference use the exact approved theme role colours'
    )
