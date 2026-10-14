"""Palette source facts are frozen from publishers, independently of the product."""

import csv
import json
import math
import re
from operator import itemgetter
from pathlib import Path

import pytest

from tests.fixtures.palette_sources.oklab_reference import (
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


@pytest.mark.parametrize('scheme', REFERENCE['schemes'], ids=itemgetter('id'))
def test_each_palette_retains_its_cited_published_source_coordinates(scheme):  # noqa: PLR0914 - independent named colour coordinates
    files = [
        path
        for path in (ROOT / 'data/palettes').glob('*.tsv')
        if normalized(path.stem) == normalized(scheme['id'])
    ]
    assert len(files) == 1, (
        f'The five published schemes each have one data table; scheme={scheme["label"]}, '
        f'actual matching tables={[p.name for p in files]}'
    )
    with files[0].open() as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    assert rows and {'pattern', 'structure'} <= {row['role'] for row in rows} <= {
        'pattern',
        'structure',
        'gradient',
    }, f'Each scheme defines both pattern and structure source colours; actual={rows}'
    provenance = (ROOT / 'data/palettes/PROVENANCE.md').read_text()
    triples = []
    for line in provenance.splitlines():
        colours = re.findall(r'#[0-9A-Fa-f]{6}', line)
        if line.strip().startswith('|') and len(colours) == 3:
            triples.append(tuple(value.upper() for value in colours))
    assert triples, (
        'Palette provenance lists each original published RGB beside its light and dark '
        'adaptations; actual source/light/dark coordinate rows=0'
    )
    mismatches, retained = [], set()
    for row in rows:
        light, dark = row['light'].upper(), row['dark'].upper()
        assert all(re.fullmatch(r'#[0-9A-F]{6}', colour) for colour in (light, dark)), (
            f'Published palettes use explicit RGB coordinates: {files[0].name}, actual={row}'
        )
        if row['role'] == 'gradient' or (
            row['role'] == 'pattern'
            and all(on_published_curve(colour, scheme['gradient']) for colour in (light, dark))
        ):
            if not all(on_published_curve(colour, scheme['gradient']) for colour in (light, dark)):
                mismatches.append(('published gradient curve', row))
            continue  # trimmed gradient stops have no categorical lightness adaptation
        candidates = [
            source
            for source, light_value, dark_value in triples
            if light_value == light and dark_value == dark
        ]
        candidates = [
            source
            for source in candidates
            if source in {value.upper() for value in scheme[row['role']]}
        ]
        if len(candidates) != 1:
            mismatches.append(('published source association', row, candidates))
            continue
        source = candidates[0]
        if row['role'] == 'pattern':
            retained.add(source)
        for theme, actual, background in [('light', light, '#FFFFFF'), ('dark', dark, '#444444')]:
            if not gamut_hue_chroma_preserved(source, actual):
                mismatches.append((
                    'Oklab hue/maximal gamut chroma',
                    source,
                    actual,
                    theme,
                    polar(source),
                    polar(actual),
                    quantisation_tolerance(actual),
                ))
            if contrast(actual, background) < 3:
                mismatches.append(('WCAG contrast', actual, theme, contrast(actual, background)))
            # A separate set-distance constraint can require an additional shift.
            # Where the independent minimum already meets it, extra lightness is unjustified.
            calculated = (
                ('#F44336' if theme == 'light' else '#EF9A9A')
                if row['role'] == 'pattern'
                else None
            )
            ideal = smallest_adaptation(source, background, calculated)
            minimum = ideal[0]
            other_colours = [r[theme] for r in rows if r['role'] == row['role'] and r != row]
            if (
                gamut_hue_chroma_preserved(source, actual)
                and all(math.dist(ideal, oklab(other)) >= 0.08 for other in other_colours)
                and not nearest_passing_lightness(source, actual, background, calculated)
            ):
                mismatches.append((
                    'nearest passing one-sided 8-bit lightness',
                    source,
                    actual,
                    theme,
                    minimum,
                    oklab(actual)[0],
                    lightness_quantisation_tolerance(actual),
                ))
    required = set(REFERENCE['required_pattern_hues'][scheme['id']])
    assert required <= retained, (
        f'Each scheme retains every original published categorical hue; scheme={scheme["label"]}, '
        f'actual retained={sorted(retained)}, missing={sorted(required - retained)}'
    )
    assert not mismatches, (
        'Published-source mappings preserve hue and the largest in-gamut chroma within the '
        'half-LSB quantisation box, retain every hue, use the smallest feasible lightness '
        'and meet 3:1 and the pattern calc-distance rule; '
        f'scheme={scheme["label"]}, actual mismatches={mismatches}'
    )


@pytest.mark.parametrize('scheme', REFERENCE['schemes'], ids=itemgetter('id'))
def test_adapted_palette_sets_keep_the_declared_minimum_oklab_distance(scheme):
    provenance = (ROOT / 'data/palettes/PROVENANCE.md').read_text()
    declaration = re.search(
        r'minimum\s+Oklab\s+distance[^\n\d]*([0-9]+(?:\.[0-9]+)?)'
        r'|at\s+least\s+([0-9]+(?:\.[0-9]+)?)\s+apart\s+in\s+Oklab',
        provenance,
        re.IGNORECASE,
    )
    assert declaration is not None and float(declaration[1] or declaration[2]) > 0, (
        'The accepted palette design declares a positive minimum Oklab distance before '
        'its adapted sets can be checked; actual declaration=' + str(declaration)
    )
    minimum = float(declaration[1] or declaration[2])
    files = [
        p
        for p in (ROOT / 'data/palettes').glob('*.tsv')
        if normalized(p.stem) == normalized(scheme['id'])
    ]
    assert len(files) == 1, (
        f'The distance gate reaches the selected actual palette: {scheme["id"]}'
    )
    with files[0].open() as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    failures = []
    for role in ('pattern', 'structure'):
        selected = [
            r
            for r in rows
            if r['role'] == role
            and not (
                role == 'pattern'
                and all(on_published_curve(r[t], scheme['gradient']) for t in ('light', 'dark'))
            )
        ]
        for theme in ('light', 'dark'):
            for i, first in enumerate(selected):
                for second in selected[i + 1 :]:
                    actual = distance(first[theme], second[theme])
                    if actual < minimum:
                        failures.append((role, theme, first['index'], second['index'], actual))
    assert not failures, (
        'Every adapted categorical set retains its declared minimum Oklab separation; '
        f'scheme={scheme["id"]}, declared={minimum}, actual shortfalls={failures}'
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
def test_gradient_endpoints_trim_the_full_published_contrast_range(scheme):
    files = [
        p
        for p in (ROOT / 'data/palettes').glob('*.tsv')
        if normalized(p.stem) == normalized(scheme['id'])
    ]
    assert len(files) == 1, (
        f'The gradient gate reaches the actual published palette table; scheme={scheme["id"]}, '
        f'actual tables={files}'
    )
    with files[0].open() as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    endpoints = [
        row
        for row in rows
        if row['role'] == 'gradient'
        or (
            row['role'] == 'pattern'
            and all(
                on_published_curve(row[theme], scheme['gradient']) for theme in ('light', 'dark')
            )
        )
    ]
    assert len(endpoints) >= 2, (
        f'The palette retains its two actual published gradient endpoints; '
        f'scheme={scheme["id"]}, actual endpoints={endpoints}'
    )
    for theme, background in [('light', '#FFFFFF'), ('dark', '#444444')]:
        calculated = '#F44336' if theme == 'light' else '#EF9A9A'
        runs, run = [], []
        for colour in scheme['gradient']:
            if contrast(colour, background) >= 3 and distance(colour, calculated) >= 0.10:
                run.append(colour)
            elif run:
                runs.append(run)
                run = []
        if run:
            runs.append(run)
        maximum = max(map(len, runs))
        longest = [run for run in runs if len(run) == maximum]
        actual = [endpoints[0][theme].upper(), endpoints[-1][theme].upper()]
        expected = [[run[0].upper(), run[-1].upper()] for run in longest]
        assert actual in expected, (
            'Gradients retain a longest contiguous publisher-table run passing both 3:1 and '
            '0.10 Oklab distance from the theme calculated colour; '
            f'publisher table; scheme={scheme["id"]}, theme={theme}, actual={actual}, '
            f'expected longest-run endpoints={expected}'
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
    files = [
        p
        for p in (ROOT / 'data/palettes').glob('*.tsv')
        if normalized(p.stem) == normalized(scheme['id'])
    ]
    assert len(files) == 1, (
        f'The order gate reaches the selected actual set; scheme={scheme["id"]}, tables={files}'
    )
    with files[0].open() as stream:
        rows = [row for row in csv.DictReader(stream, delimiter='\t') if row['role'] == 'pattern']
    provenance = (ROOT / 'data/palettes/PROVENANCE.md').read_text()
    triples = [
        tuple(value.upper() for value in re.findall(r'#[0-9A-Fa-f]{6}', line))
        for line in provenance.splitlines()
        if line.strip().startswith('|') and len(re.findall(r'#[0-9A-Fa-f]{6}', line)) == 3
    ]
    nearby = []
    for row in rows:
        sources = {
            source
            for source, light, dark in triples
            if (light, dark) == (row['light'].upper(), row['dark'].upper())
            and source in {colour.upper() for colour in scheme['pattern']}
        }
        assert len(sources) == 1, (
            'Each categorical pattern row keeps one published source identity before its '
            f'calc-distance adaptation; scheme={scheme["id"]}, row={row}, sources={sources}'
        )
        source = sources.pop()
        nearby.append(
            any(
                math.dist(smallest_adaptation(source, background), oklab(calculated)) < 0.10
                for background, calculated in [('#FFFFFF', '#F44336'), ('#444444', '#EF9A9A')]
            )
        )
    assert nearby == sorted(nearby), (
        'A hue too close to calc in either theme goes after every safer hue in the shared '
        f'light/dark set order, without changing its identity; scheme={scheme["id"]}, '
        f'actual places/colours={rows}, nearby in either theme={nearby}'
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
