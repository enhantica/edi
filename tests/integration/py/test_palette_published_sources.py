"""Palette source facts are frozen from publishers, independently of the product."""

import csv
import json
import math
import re
from operator import itemgetter
from pathlib import Path

import pytest

from tests.fixtures.palette_sources.oklab_reference import (
    angle_difference,
    contrast,
    distance,
    full_step_lightness_tolerance,
    gamut_hue_chroma_preserved,
    hue_chroma_preserved,
    lightness_quantisation_tolerance,
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
REFERENCE = json.loads((ROOT / 'tests/fixtures/palette_sources/reference.json').read_text())


def normalized(value):
    return re.sub(r'[^a-z]', '', value.lower())


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


def palette_rows(scheme):
    files = [
        path
        for path in (ROOT / 'data/palettes').glob('*.tsv')
        if normalized(path.stem) == normalized(scheme['id'])
    ]
    assert len(files) == 1, (
        f'Every one of the eighteen named schemes has one actual table; '
        f'scheme={scheme["label"]}, actual={files}'
    )
    with files[0].open() as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


def cited_section(scheme):
    text = (ROOT / 'data/palettes/PROVENANCE.md').read_text()
    headings = list(re.finditer(r'^(#{1,6})\s+(.+)$', text, re.MULTILINE))
    for i, heading in enumerate(headings):
        title = normalized(heading[2])
        if title not in {normalized(scheme['id']), normalized(scheme['label'])}:
            continue
        following = next(
            (h.start() for h in headings[i + 1 :] if len(h[1]) <= len(heading[1])), len(text)
        )
        return text[heading.end() : following]
    return ''


def source_pair(scheme, row, section):
    light, dark = row['light'].upper(), row['dark'].upper()
    allowed = scheme['sources_by_theme']
    candidates = set()
    for line in section.splitlines():
        colours = [value.upper() for value in re.findall(r'#[0-9a-fA-F]{6}', line)]
        if len(colours) in {3, 4} and colours[-2:] == [light, dark]:
            pair = (colours[0], colours[0] if len(colours) == 3 else colours[1])
            if all(
                value in {c.upper() for c in allowed[theme]}
                for value, theme in zip(pair, ('light', 'dark'), strict=True)
            ):
                candidates.add(pair)
    if (
        light in {c.upper() for c in allowed['light']}
        and dark in {c.upper() for c in allowed['dark']}
        and light in section.upper()
        and dark in section.upper()
    ):
        candidates.add((light, dark))
    assert len(candidates) == 1, (
        'Every selected published categorical colour cites its real light/dark source '
        f'coordinates under its own scheme; scheme={scheme["label"]}, row={row}, '
        f'actual source mappings={candidates}'
    )
    return candidates.pop()


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


def test_exactly_eighteen_schemes_are_published_with_coast_default():
    actual = {normalized(p.stem) for p in (ROOT / 'data/palettes').glob('*.tsv')}
    expected = {normalized(row['id']) for row in REFERENCE['schemes']}
    assert len(expected) == 18 and actual == expected, (
        f'The owner selects exactly eighteen named schemes; actual={actual}, expected={expected}'
    )
    assert REFERENCE['default'] == 'coast', 'The independently recorded default is Coast'


@pytest.mark.parametrize('scheme', REFERENCE['schemes'], ids=itemgetter('id'))
def test_each_palette_retains_its_cited_published_source_coordinates(scheme):
    rows = palette_rows(scheme)
    section = cited_section(scheme)
    assert section, (
        f'Each of the eighteen schemes has its own provenance section: {scheme["label"]}'
    )
    assert any(url in section for url in scheme['source_urls']), (
        f'Each scheme cites its actual primary source or declared '
        f'inspiration; scheme={scheme["label"]}'
    )
    if scheme['kind'] == 'design':
        assert re.search(r'inspir|design', section, re.IGNORECASE), (
            f'An owner-inspired design is labelled as a design, without '
            f'claiming published RGB truth: {scheme["label"]}'
        )
    failures = []
    for row in rows:
        assert row['role'] in {'pattern', 'structure', 'gradient'} and all(
            re.fullmatch(r'#[0-9A-Fa-f]{6}', row[t]) for t in ('light', 'dark')
        ), f'Each stored row has a known role and explicit 8-bit RGB coordinates: {row}'
        if row['role'] == 'gradient' or scheme['kind'] == 'design':
            continue
        sources = source_pair(scheme, row, section)
        for source, theme, background in zip(
            sources, ('light', 'dark'), ('#FFFFFF', '#444444'), strict=True
        ):
            actual = row[theme]
            calculated = (
                ('#F44336' if theme == 'light' else '#EF9A9A')
                if row['role'] == 'pattern'
                else None
            )
            ideal = smallest_adaptation(source, background, calculated)
            others = [r[theme] for r in rows if r['role'] == row['role'] and r != row]
            if not gamut_hue_chroma_preserved(source, actual):
                failures.append(('hue/maximal gamut chroma', source, actual, theme))
            if contrast(actual, background) < 3:
                failures.append(('WCAG 3:1', actual, theme))
            if all(
                math.dist(ideal, oklab(other)) >= 0.08 for other in others
            ) and not nearest_passing_lightness(source, actual, background, calculated):
                failures.append((
                    'nearest passing one-sided lattice lightness',
                    source,
                    actual,
                    theme,
                ))
    assert not failures, (
        'Published adaptations retain source hue/maximal gamut chroma and nearest passing '
        f'8-bit lightness with strict contrast; scheme={scheme["label"]}, actual={failures}'
    )


@pytest.mark.parametrize('scheme', REFERENCE['schemes'], ids=itemgetter('id'))
def test_adapted_palette_sets_keep_the_declared_minimum_oklab_distance(scheme):
    provenance = (ROOT / 'data/palettes/PROVENANCE.md').read_text()
    declaration = re.search(
        r'minimum\s+Oklab\s+distance[^\n\d]*([0-9]+(?:\.[0-9]+)?)|at\s+least\s+([0-9]+(?:\.[0-9]+)?)\s+apart\s+in\s+Oklab',
        provenance,
        re.IGNORECASE,
    )
    assert declaration is not None and float(declaration[1] or declaration[2]) > 0, (
        'The accepted positive minimum Oklab set separation remains explicitly declared'
    )
    minimum = float(declaration[1] or declaration[2])
    rows = palette_rows(scheme)
    failures = []
    for role in ('pattern', 'structure'):
        selected = [r for r in rows if r['role'] == role]
        for theme in ('light', 'dark'):
            for i, first in enumerate(selected):
                failures.extend(
                    (role, theme, first['index'], second['index'])
                    for second in selected[i + 1 :]
                    if distance(first[theme], second[theme]) < minimum
                )
    assert not failures, (
        f'All eighteen schemes retain the declared within-set Oklab separation; '
        f'scheme={scheme["label"]}, actual shortfalls={failures}'
    )


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


@pytest.mark.parametrize('scheme', REFERENCE['schemes'], ids=itemgetter('id'))
def test_two_gradient_endpoints_rise_in_lightness_and_avoid_calculated_hues(scheme):
    endpoints = [row for row in palette_rows(scheme) if row['role'] == 'gradient']
    assert len(endpoints) == 2, (
        f'Each of eighteen schemes has exactly two gradient colours;'
        f' scheme={scheme["label"]}, actual={endpoints}'
    )
    for theme, background, calc in [
        ('light', '#FFFFFF', '#F44336'),
        ('dark', '#444444', '#EF9A9A'),
    ]:
        first, last = [row[theme] for row in endpoints]
        assert oklab(first)[0] < oklab(last)[0], (
            f'The gradient rises from its first dataset to its last in both '
            f'themes: {scheme["label"]}/{theme}'
        )
        assert all(
            contrast(c, background) >= 3 and distance(c, calc) >= 0.10 and not in_calc_hue(c)
            for c in (first, last)
        ), (
            f'Both gradient ends meet strict WCAG/calc-distance and avoid calc '
            f'hues; scheme={scheme["label"]}, theme={theme}'
        )


@pytest.mark.parametrize('scheme', REFERENCE['schemes'], ids=itemgetter('id'))
def test_pattern_sets_keep_the_theme_calculated_colour_distance(scheme):
    files = [
        p
        for p in (ROOT / 'data/palettes').glob('*.tsv')
        if normalized(p.stem) == normalized(scheme['id'])
    ]
    assert len(files) == 1, (
        f'The calculated-colour gate reaches the selected pattern table; scheme={scheme["id"]}, '
        f'actual tables={files}'
    )
    with files[0].open() as stream:
        rows = [
            row
            for row in csv.DictReader(stream, delimiter='\t')
            if row['role'] in {'pattern', 'gradient'}
        ]
    for theme, calculated in [('light', '#F44336'), ('dark', '#EF9A9A')]:
        failures = [
            (row['index'], row[theme], distance(row[theme], calculated))
            for row in rows
            if distance(row[theme], calculated) < 0.10
        ]
        assert not failures, (
            'Every stored pattern colour, including each end-of-set colour and gradient endpoint, '
            f'keeps at least 0.10 Oklab from its theme calculated colour; scheme={scheme["id"]}, '
            f'theme={theme}, calculated={calculated}, actual failures={failures}'
        )


@pytest.mark.parametrize('scheme', REFERENCE['schemes'], ids=itemgetter('id'))
def test_pattern_sets_move_near_calculated_hues_to_the_end_in_both_themes(scheme):
    rows = [row for row in palette_rows(scheme) if row['role'] == 'pattern']
    section = cited_section(scheme)
    nearby = []
    for row in rows:
        near = any(in_calc_hue(row[theme]) for theme in ('light', 'dark'))
        if scheme['kind'] != 'design':
            sources = source_pair(scheme, row, section)
            near |= any(
                math.dist(smallest_adaptation(source, bg), oklab(calc)) < 0.10
                for source, bg, calc in zip(
                    sources, ('#FFFFFF', '#444444'), ('#F44336', '#EF9A9A'), strict=True
                )
            )
        nearby.append(near)
    assert nearby == sorted(nearby), (
        f'Every calc-range or originally calc-near measured hue follows the safer colours '
        f'in both themes; scheme={scheme["label"]}, actual near flags={nearby}'
    )


@pytest.mark.parametrize('scheme', REFERENCE['schemes'], ids=itemgetter('id'))
def test_fixed_and_structure_sets_are_bounded_distinct_and_indexed(scheme):
    rows = palette_rows(scheme)
    roles = {
        role: [r for r in rows if r['role'] == role]
        for role in ('pattern', 'structure', 'gradient')
    }
    assert (
        1 <= len(roles['pattern']) <= 7
        and 1 <= len(roles['structure']) <= 5
        and len(roles['gradient']) == 2
    ), (
        f'Each eighteen-scheme table has at most seven fixed measured and '
        f'five structure colours, plus two gradient endpoints: {scheme["label"]}'
    )
    for role, selected in roles.items():
        assert [int(row['index']) for row in selected] == list(range(len(selected))), (
            f'Each actual colour role retains consecutive places with no '
            f'duplicate indices: {scheme["label"]}/{role}'
        )
    for theme in ('light', 'dark'):
        structures = [r[theme] for r in roles['structure']]
        measured = [r[theme] for r in roles['pattern']]
        for i, first in enumerate(structures):
            for other in structures[i + 1 :]:
                assert angle_difference(polar(first)[2], polar(other)[2]) > sum(
                    quantisation_tolerance(c)[1] for c in (first, other)
                ), (
                    f'Each structure colour has a distinct OKLCH hue beyond half-LSB '
                    f'uncertainty: {scheme["label"]}/{theme}'
                )
                assert abs(oklab(first)[0] - oklab(other)[0]) > sum(
                    lightness_quantisation_tolerance(c) for c in (first, other)
                ), (
                    f'Each structure colour has its own lightness step beyond half-LSB '
                    f'uncertainty: {scheme["label"]}/{theme}'
                )
            assert all(
                distance(first, c) > sum(lightness_quantisation_tolerance(v) for v in (first, c))
                for c in measured
            ), (
                f'Every structure colour is distinct from every measured-data '
                f'colour in both themes: {scheme["label"]}/{theme}'
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
