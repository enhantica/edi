"""Element displays use published colours with independent WCAG and Oklab checks."""

import csv
import json
import math
import os
import re
import signal
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.palette_sources.oklab_reference import contrast, hue_chroma_preserved

ROOT = Path(__file__).resolve().parents[3]
TAGS = [f'{scheme}-{theme}' for scheme in ('jmol', 'vesta') for theme in ('light', 'dark')]


def instance_colour(linear_channels):
    # Qt Quick 3D 6.11.2 qssgutils.cpp uses this monotone cubic in its instance buffer.
    # Decode its published 8-bit lattice; WCAG arithmetic is used only for 2D contrast.
    def qt_linear(value):
        return value * (value * (value * 0.305306011 + 0.682171111) + 0.012522878)

    if len(linear_channels) != 3 or any(
        not math.isfinite(value) or not 0 <= value <= 1 for value in linear_channels
    ):
        raise ValueError('The instance buffer must carry three finite unit channels')
    values = [
        min(range(256), key=lambda byte: abs(qt_linear(byte / 255) - value))
        for value in linear_channels
    ]
    return '#' + ''.join(f'{value:02x}' for value in values)


def composite(foreground, background):
    if len(foreground) == 7:
        return foreground
    alpha = int(foreground[1:3], 16) / 255
    values = [
        math.floor(
            alpha * int(foreground[i + 2 : i + 4], 16)
            + (1 - alpha) * int(background[i : i + 2], 16)
            + 0.5
        )
        for i in (1, 3, 5)
    ]
    return '#' + ''.join(f'{value:02x}' for value in values)


def test_independent_contrast_and_colour_observers_reject_escapes():
    assert instance_colour([0, 0.21678297836003518, 1]) == '#0080ff', (
        'The independent Qt instance lattice identifies black, encoded 128 and white'
    )
    assert contrast('#000000', '#ffffff') == 21, (
        'The independent W3C computation reaches the published 21:1 black/white endpoint'
    )
    assert contrast('#949494', '#ffffff') >= 3 > contrast('#959595', '#ffffff'), (
        'Adjacent encoded greys straddle the strict 3:1 boundary without a contrast tolerance'
    )
    assert composite('#80000000', '#ffffff') == '#7f7f7f', (
        'The independent encoded-sRGB compositor reaches the half-opacity black control'
    )
    assert hue_chroma_preserved('#575961', '#575961'), (
        'The independent Oklab bounds retain an exactly unchanged published colour'
    )
    assert not hue_chroma_preserved('#ffff30', '#949494'), (
        'Replacing sulfur with a passing neutral cannot defeat the hue/chroma observer'
    )
    assert not hue_chroma_preserved('#ff0d0d', '#0d0dff'), (
        'A rotated element hue cannot defeat the independent Oklab observer'
    )


@pytest.fixture(scope='module')
def observations():
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    command = [
        'bash',
        str(ROOT / 'tests/fixtures/scan_views/run.sh'),
        str(runner),
        '-input',
        str(ROOT / 'tests/unit/app/tst_element_contrast.qml'),
        '-o',
        '-,txt',
    ]
    process = subprocess.Popen(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate()
        pytest.fail('Element colour observations exceeded their bounded actor watchdog: ' + output)
    print(output)
    assert process.returncode == 0 and 'ElementContrast::cleanupTestCase()' in output, (
        'All real element consumers must execute completely before their colours count: ' + output
    )
    rows = [
        json.loads(line.partition('ELEMENT_CONTRAST ')[2])
        for line in output.splitlines()
        if 'ELEMENT_CONTRAST ' in line
    ]
    assert {row['tag'] for row in rows} == set(TAGS) and len(rows) == len(TAGS), (
        'Both published schemes execute exactly once on each actual theme background'
    )
    with (ROOT / 'tests/fixtures/e04_t10/published-elements.tsv').open() as stream:
        reference = list(csv.DictReader(stream, delimiter='\t'))
    for row in rows:
        facts = row['facts']
        assert [fact['symbol'] for fact in facts] == [r['symbol'] for r in reference], (
            'Every physical colour observation retains the complete independent element order'
        )
        scheme = row['tag'].split('-')[0]
        for fact, published in zip(facts, reference, strict=True):
            expected = (published[scheme] or published['jmol']).lower()
            assert fact['source'] == expected, (
                'Every oracle is the independently captured scheme, including VESTA fallback'
            )
            for key in ('background', 'viewBackground', 'reportBackground'):
                assert re.fullmatch(r'#[0-9a-fA-F]{6}', fact[key]), (
                    'Every element observation names its actual opaque production underlay'
                )
            fact['legendBackground'] = composite(fact['legendFill'], fact['viewBackground'])
            fact['reportBackground'] = composite(
                fact['reportLegendFill'], fact['reportBackground']
            )
    return {row['tag']: row for row in rows}


@pytest.mark.parametrize('tag', TAGS)
def test_all_2d_element_uses_reach_three_to_one(observations, tag):
    failures = []
    for row in observations[tag]['facts']:
        for use, background in [
            ('accessor', 'background'),
            ('table', 'background'),
            ('parameter', 'background'),
            ('parameterLabel', 'background'),
            ('legend', 'legendBackground'),
            ('report', 'reportBackground'),
        ]:
            value = contrast(row[use], row[background])
            if value < 3:
                failures.append((row['symbol'], use, row[use], row[background], value))
    assert not failures, (
        'Every element icon, parameter label and live/report legend reaches WCAG 3:1 '
        + repr(failures)
    )


@pytest.mark.parametrize('tag', TAGS)
def test_all_2d_element_uses_keep_oklab_hue_and_chroma(observations, tag):
    failures = [
        (row['symbol'], use, row['source'], row[use])
        for row in observations[tag]['facts']
        for use in ('accessor', 'table', 'parameter', 'parameterLabel', 'legend', 'report')
        if not hue_chroma_preserved(row['source'], row[use])
    ]
    assert not failures, (
        'Hue and chroma stay within independent half-LSB RGB quantisation bounds: '
        + repr(failures)
    )


@pytest.mark.parametrize('tag', TAGS)
def test_already_passing_elements_are_exactly_unchanged(observations, tag):
    failures = []
    for row in observations[tag]['facts']:
        for use, background in [
            ('accessor', 'background'),
            ('table', 'background'),
            ('parameter', 'background'),
            ('parameterLabel', 'background'),
            ('legend', 'legendBackground'),
            ('report', 'reportBackground'),
        ]:
            if contrast(row['source'], row[background]) >= 3 and row[use].lower() != row['source']:
                failures.append((row['symbol'], use, row['source'], row[use]))
    assert not failures, (
        'Every colour already passing 3:1 retains the exact published bytes: ' + repr(failures)
    )


@pytest.mark.parametrize('tag', TAGS)
def test_3d_sphere_instances_keep_exact_published_colours(observations, tag):
    failures = [
        (row['symbol'], row['source'], instance_colour(row['sphereLinear']))
        for row in observations[tag]['facts']
        if instance_colour(row['sphereLinear']) != row['source']
    ]
    assert not failures, (
        'Every actual unshaded 3D sphere retains the exact independent scheme colour: '
        + repr(failures)
    )


@pytest.mark.parametrize('tag', TAGS)
def test_scheme_selector_explains_display_adjustment(observations, tag):
    row = observations[tag]
    assert row['names'] == ['jmol', 'vesta'], (
        'The unchanged published scheme names remain jmol and vesta'
    )
    assert re.search(r'adjusted.*contrast.*labels.*tables', row['tooltip'], re.IGNORECASE), (
        'The real scheme selector explains contrast adjustment in labels and tables'
    )
