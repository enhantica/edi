"""Palette source facts are frozen from publishers, independently of the product."""

import csv
import json
import math
import operator
from pathlib import Path

import pytest

from tests.fixtures.approved_palettes.reference import PALETTES
from tests.fixtures.palette_sources.oklab_reference import (
    full_step_lightness_tolerance,
    gamut_hue_chroma_preserved,
    hue_chroma_preserved,
    linear_rgb,
    nearest_passing_lightness,
    nearest_passing_lightness_error,
    oklab,
    polar,
    quantisation_tolerance,
    smallest_adaptation,
    smallest_lightness_shift,
)

ROOT = Path(__file__).resolve().parents[3]


def rgb(value):
    return tuple(int(value[i : i + 2], 16) for i in (1, 3, 5))


def on_published_curve(colour, anchors):
    """Published sequential scales may be trimmed at any interpolated point.

    Tol explicitly prescribes linear RGB interpolation. The pinned Matplotlib
    tables have 256 close samples. One encoded channel's rounding is allowed,
    never a colour-distance tolerance calibrated from the product's output.
    """
    target = rgb(colour)
    for left, right in zip(anchors, anchors[1:], strict=False):
        a, b = rgb(left), rgb(right)
        delta = [y - x for x, y in zip(a, b, strict=True)]
        denominator = sum(v * v for v in delta)
        position = (
            sum((t - x) * d for t, x, d in zip(target, a, delta, strict=True)) / denominator
            if denominator
            else 0
        )
        if 0 <= position <= 1 and all(
            abs(t - (x + position * d)) <= 1 for t, x, d in zip(target, a, delta, strict=True)
        ):
            return True
    return colour.upper() in {value.upper() for value in anchors}


def in_calc_hue(colour):
    # The short OKLCH arc spanning the independently specified light/dark calc
    # colours, enlarged only by their half-LSB hue uncertainty. Neutral has no hue.
    if polar(colour)[1] <= quantisation_tolerance(colour)[0]:
        return False
    hues = [polar(value)[2] for value in ('#F44336', '#EF9A9A')]
    margin = max(quantisation_tolerance(value)[1] for value in ('#F44336', '#EF9A9A'))
    start, end = sorted(hues)
    hue = polar(colour)[2]
    return start - margin <= hue <= end + margin


def test_oklab_observer_reaches_independent_black_white_and_hue_controls():
    assert oklab('#000000') == (0, 0, 0), (
        'The independent Oklab black control has zero coordinates'
    )
    assert oklab('#FFFFFF') == pytest.approx((1, 0, 0), abs=1e-7), (
        'Ottosson updated matrices map neutral sRGB white to the unit-lightness neutral'
    )
    assert smallest_lightness_shift('#FFFFFF', '#FFFFFF') == pytest.approx(
        0.3 ** (1 / 3), abs=1e-7
    ), 'The independent minimum-shift oracle reaches the closed-form neutral 3:1 boundary'
    assert hue_chroma_preserved('#4477AA', '#4477AA'), (
        'The quantisation-box tolerance admits a genuinely unchanged published colour'
    )
    assert not hue_chroma_preserved('#4477AA', '#AA4477'), (
        'The independent Oklab observer rejects a substantial hue rotation'
    )
    for source in ('#E69F00', '#03A9F4', '#BCBD22', '#F0E442', '#FFFF33'):
        lab = smallest_adaptation(source, '#FFFFFF')
        published = oklab(source)
        assert min(linear_rgb((lab[0], *published[1:]))) < 0, (
            f'Published chroma is outside sRGB at the 3:1 boundary: {source}'
        )
        assert all(-1e-10 <= c <= 1 + 1e-10 for c in linear_rgb(lab)), (
            f'The independently gamut-mapped hue lies inside linear sRGB: {source}'
        )
        expanded = (lab[0], lab[1] * 1.0001, lab[2] * 1.0001)
        assert any(c < -1e-10 or c > 1 + 1e-10 for c in linear_rgb(expanded)), (
            f'Increasing the retained chroma crosses the gamut boundary: {source}'
        )
    assert gamut_hue_chroma_preserved('#FFFF33', '#9A9A00'), (
        'The independent gamut observer admits the published yellow mapped to its sRGB edge'
    )
    assert not gamut_hue_chroma_preserved('#FFFF33', '#949494'), (
        'The independent gamut observer rejects avoidable desaturation to neutral grey'
    )
    assert not gamut_hue_chroma_preserved('#4477AA', '#AA4477'), (
        'The independent gamut observer rejects an altered published hue'
    )
    adjusted = smallest_adaptation('#E41A1C', '#FFFFFF', '#F44336')
    assert math.dist(adjusted, oklab('#F44336')) == pytest.approx(0.10, abs=1e-9), (
        'A near-calc source moves to the nearest distance boundary while retaining 3:1 contrast'
    )
    assert smallest_adaptation('#4477AA', '#FFFFFF') == pytest.approx(oklab('#4477AA')), (
        'An already compliant source keeps its lightness and chroma without adaptation'
    )


@pytest.mark.parametrize(
    ('actual', 'expected'),
    [('#808080', True), ('#FF0000', False), ('#010100', True)],
)
def test_published_curve_observer_reaches_numeric_interpolation_controls(actual, expected):
    assert on_published_curve(actual, ['#000000', '#FFFFFF']) is expected, (
        f'The independent published-curve observer accepts neutral interpolation with one '
        f'encoded-channel rounding and rejects an unrelated hue; actual={actual}'
    )


@pytest.mark.parametrize(
    'witness',
    json.loads((ROOT / 'tests/fixtures/palette_sources/quantisation-proof.json').read_text())[
        'witnesses'
    ],
    ids=lambda w: w['scheme'] + w['source'] + w['theme'],
)
def test_one_sided_quantisation_matches_exhaustive_independent_lattice(witness):
    background = '#FFFFFF' if witness['theme'] == 'light' else '#444444'
    calculated = '#F44336' if witness['theme'] == 'light' else '#EF9A9A'
    colour, error, half = witness['nearest_passing_within_full_step']
    assert witness['half_step_passing'] == [], (
        'The independent exhaustive 8-bit census found no passing half-step colour'
    )
    assert error > half and error <= full_step_lightness_tolerance(colour), (
        'Each independently impossible half-step projection has a passing full-step lattice point'
    )
    assert nearest_passing_lightness_error(
        witness['source'], background, calculated
    ) == pytest.approx(error, abs=1e-10), (
        'The bounded nearest-passing observer agrees with the independent exhaustive RGB lattice'
    )
    assert nearest_passing_lightness(witness['source'], colour, background, calculated), (
        'The quantisation correction admits the nearest passing one-sided colour'
    )
    assert not nearest_passing_lightness(
        witness['source'], witness['source'], background, calculated
    ), 'The wrong side of each strict projection boundary stays refused'
    ideal = smallest_adaptation(witness['source'], background, calculated)[0]
    bad = '#000000' if ideal < oklab(witness['source'])[0] else '#FFFFFF'
    assert not nearest_passing_lightness(witness['source'], bad, background, calculated), (
        'A passing-side overshoot beyond one full quantisation step stays refused'
    )


@pytest.mark.parametrize(
    ('colour', 'expected'),
    [('#F44336', True), ('#EF9A9A', True), ('#0055A0', False), ('#808080', False)],
)
def test_calc_hue_observer_reaches_independent_red_blue_and_neutral_controls(colour, expected):
    assert in_calc_hue(colour) is expected, (
        'The independent OKLCH observer identifies both calculated hues, excludes blue '
        'and treats neutral quantisation uncertainty as hue-less'
    )


@pytest.mark.parametrize('palette', PALETTES, ids=operator.itemgetter('name'))
def test_approved_palette_rows_keep_exact_coordinates_and_role_order(palette):
    filename = palette['name'].lower().replace(' ', '-') + '.tsv'
    with (ROOT / 'data/palettes' / filename).open() as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    expected = []
    for role, field in [('measured', 'measured'), ('structure', 'structures')]:
        expected.extend(
            {
                'role': role,
                'index': str(index),
                'light': palette['light'][field][index],
                'dark': palette['dark'][field][index],
            }
            for index in range(5)
        )
    for _index, field in enumerate(('total_calculation', 'background', 'difference')):
        expected.append({
            'role': field,
            'index': '0',
            'light': palette['light'][field],
            'dark': palette['dark'][field],
        })
    assert rows == expected, (
        'Every shipped coordinate and role position equals the independent owner table'
    )


def test_exactly_five_approved_tables_and_attribution_are_published():
    actual = {p.stem for p in (ROOT / 'data/palettes').glob('*.tsv')}
    assert actual == {p['name'].lower().replace(' ', '-') for p in PALETTES}, (
        'Only the five owner-approved Edi palettes remain in the shipped catalogue'
    )
    text = (ROOT / 'data/palettes/PROVENANCE.md').read_text()
    assert all(p['name'] in text for p in PALETTES), (
        'Every approved palette retains its provenance'
    )
    assert 'Okabe' in text and 'custom' in text.lower(), (
        'Edi Contrast is attributed as a custom inspiration rather than the Okabe-Ito table'
    )
