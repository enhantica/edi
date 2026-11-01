"""Independent physical-pixel stroke coverage for both Stacked paths and DPRs."""

import json
import math
import os
import time
from operator import itemgetter

import numpy as np
import pytest

from tests.fixtures.fast_chart_redraws.line_quality import (
    coverage,
    metrics,
    physical_points,
    read_png,
    stroke_reference,
    violations,
)
from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture

CASES = [
    (dpr, mode, shape)
    for dpr in (1, 2)
    for mode in ('gpu', 'software')
    for shape in ('peak', 'needle')
]


@pytest.fixture(scope='module')
def raster_pairs():
    pairs = {}
    for dpr in (1, 2):
        started = time.time()
        env = dict(os.environ, QT_SCALE_FACTOR=str(dpr))
        status, output = capture(
            [
                os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'),
                '-input',
                ROOT / 'tests/system/app/LineQuality.qml',
                '-o',
                '-,txt',
            ],
            env=env,
            timeout=150,
        )
        receipts = [
            json.loads(line.split('LINE_QUALITY_CAPTURE ', 1)[1])
            for line in output.splitlines()
            if 'LINE_QUALITY_CAPTURE ' in line
        ]
        for mode in ('gpu', 'software'):
            for shape in ('peak', 'needle'):
                matches = [
                    row for row in receipts if row['mode'] == mode and row['shape'] == shape
                ]
                key = dpr, mode, shape
                if status != 0 or len(matches) != 1:
                    pairs[key] = {'error': output}
                    continue
                row = matches[0]
                paths = [
                    ROOT
                    / 'build'
                    / (
                        'line-quality-'
                        + mode
                        + '-'
                        + shape
                        + '-'
                        + str(dpr)
                        + '-'
                        + suffix
                        + '.png'
                    )
                    for suffix in ('pattern', 'stacked')
                ]
                if row['dpr'] != dpr or any(
                    not path.exists() or path.stat().st_mtime < started for path in paths
                ):
                    pairs[key] = {
                        'error': 'The actual DPR and fresh paired image files are required'
                    }
                    continue
                qt_reference, got = map(read_png, paths)
                ref = stroke_reference(row)
                result = metrics(ref, got, row)
                print('LINE_QUALITY_RESULT ' + json.dumps(dict(row, metrics=result)), flush=True)
                pairs[key] = {
                    'result': result,
                    'row': row,
                    'reference': ref,
                    'qt_reference': qt_reference,
                }
    return pairs


@pytest.mark.parametrize('case', CASES, ids=lambda case: f'dpr{case[0]}-{case[1]}-{case[2]}')
def test_stacked_matches_pattern_line_quality(raster_pairs, case):
    pair = raster_pairs[case]
    assert 'error' not in pair, (
        'Both production renderers must complete the paired raster actor: '
        + str(pair.get('error'))
    )
    result = pair['result']
    assert not violations(result), (
        'Stacked matches the independent fractional-width stroke '
        'within the stated raster tolerances: '
        + json.dumps(result)
        + '; failed='
        + ','.join(violations(result))
    )


def assert_reference_calibration(receipt):
    flat = dict(receipt)
    level = receipt['y_range'][1] - 100.25 / (receipt['height'] * receipt['dpr']) * (
        receipt['y_range'][1] - receipt['y_range'][0]
    )
    flat['points'] = [[10, level], [80, level]]
    profile = (
        coverage(stroke_reference(flat), receipt['colour'])[
            :, round(receipt['width'] * receipt['dpr']) // 2
        ]
        / receipt['reference_opacity']
    )
    radius = receipt['stroke_width'] * receipt['dpr'] / 2
    pixels = np.arange(profile.size)
    expected = np.maximum(
        0, np.minimum(pixels + 1, 100.25 + radius) - np.maximum(pixels, 100.25 - radius)
    )
    direction = 255 - np.array([int(receipt['colour'][i : i + 2], 16) for i in (1, 3, 5)])
    rounding = 0.5 * direction.sum() / np.dot(direction, direction) / receipt['reference_opacity']
    assert np.max(np.abs(profile - expected)) <= rounding + 1e-9, (
        'A fractional flat stroke equals exact pixel-square overlap within RGB rounding only'
    )
    assert abs(profile.sum() - 2 * radius) <= np.count_nonzero(expected) * rounding + 1e-9, (
        'The independent flat profile integrates to the declared physical stroke width'
    )
    slant = dict(receipt, points=[[20, 60], [70, 200]])
    area = (
        2 * radius * np.linalg.norm(np.diff(physical_points(slant), axis=0))
        + math.pi * radius * radius
    )
    observed = (
        coverage(stroke_reference(slant), receipt['colour']).sum() / receipt['reference_opacity']
    )
    assert abs(observed / area - 1) <= 0.01, (
        'A slanted round stroke integrates to length times width plus its circular end caps'
    )
    precise = (
        coverage(stroke_reference(slant, samples=32), receipt['colour']).sum()
        / receipt['reference_opacity']
    )
    assert abs(precise - observed) / area <= 0.01, (
        'Doubling the independent subpixel grid converges within one percent of exact area'
    )
    split = dict(slant, points=[[20, 60], [45, 130], [70, 200]])
    assert np.array_equal(stroke_reference(split), stroke_reference(slant)), (
        'Splitting a straight segment neither adds join opacity nor changes physical coverage'
    )


def gap_control(reference, receipt):
    core = coverage(reference, receipt['colour']) / receipt['reference_opacity'] > 0.24
    points = physical_points(receipt)
    gap_y = round((points[0, 1] + points[1, 1]) / 2)
    band = slice(gap_y - 6, gap_y + 6)
    assert np.count_nonzero(core[band]) > 0, (
        'The injected gap crosses independently located stroke-core pixels at the declared opacity'
    )
    gap = reference.copy()
    gap[band] = 255
    assert np.all(coverage(gap[band], receipt['colour'])[core[band]] == 0), (
        'The gap control actually erases the identified reference stroke pixels'
    )
    return gap


def join_controls(reference, receipt):
    yy, xx = np.ogrid[: reference.shape[0], : reference.shape[1]]
    vertex = min(physical_points(receipt), key=itemgetter(1))
    region = (xx - vertex[0]) ** 2 + (yy - vertex[1]) ** 2 <= (5 * receipt['dpr']) ** 2
    core = coverage(reference, receipt['colour']) / receipt['reference_opacity'] > 0.24
    assert np.count_nonzero(core & region) > 0, (
        'The join controls reach independently located stroke-core pixels'
    )
    blot = reference.copy()
    blot[region] = np.clip(255 - (255 - reference[region].astype(float)) * 1.7, 0, 255)
    notch = reference.copy()
    notch[region] = 255
    return notch, blot


@pytest.mark.parametrize('case', CASES, ids=lambda case: f'dpr{case[0]}-{case[1]}-{case[2]}')
def test_quality_comparison_rejects_degraded_reference_controls(raster_pairs, case):
    pair = raster_pairs[case]
    assert 'error' not in pair, (
        'The quality controls require a fresh paired raster '
        'and independent opacity-declared reference'
    )
    ref, row = pair['reference'], pair['row']
    if case[1:] == ('gpu', 'peak'):
        assert_reference_calibration(row)
    assert not violations(metrics(ref, ref, row)), (
        'The independent area-coverage reference must pass identity without relaxed tolerances'
    )
    thin = np.round(255 - (255 - ref.astype(float)) * 0.5).astype(np.uint8)
    gap = gap_control(ref, row)
    notch, blot = join_controls(ref, row)
    uneven = ref.copy()
    uneven[:, : round(row['width'] * row['dpr']) // 2] = thin[
        :, : round(row['width'] * row['dpr']) // 2
    ]
    shifted = np.roll(ref, 2, axis=1)
    for name, degraded, required in [
        ('thin', thin, 'width'),
        ('uneven', uneven, 'width'),
        ('gap', gap, 'gaps'),
        ('vertex-notch', notch, 'vertex_notches'),
        ('double-alpha', blot, 'double_alpha_join'),
        ('physical-grid-shift', shifted, 'antialiasing_or_device_pixel_reduction'),
    ]:
        assert required in violations(metrics(ref, degraded, row)), (
            'The quality comparator rejects its exercised reference degradation: ' + name
        )
