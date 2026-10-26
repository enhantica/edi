"""Pattern-chart raster parity for both Stacked paths on physical DPR 1 and 2."""

import json
import os
import time

import numpy as np
import pytest

from tests.fixtures.fast_chart_redraws.line_quality import metrics, read_png, violations
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
                ref, got = map(read_png, paths)
                result = metrics(ref, got, row)
                print('LINE_QUALITY_RESULT ' + json.dumps(dict(row, metrics=result)), flush=True)
                pairs[key] = {'result': result, 'row': row, 'reference': ref}
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
        'Stacked matches the Pattern reference within the stated raster tolerances: '
        + json.dumps(result)
        + '; failed='
        + ','.join(violations(result))
    )


def test_quality_comparison_rejects_degraded_reference_controls(raster_pairs):
    pair = raster_pairs[2, 'gpu', 'peak']
    assert 'error' not in pair, (
        'The quality controls require a fresh actual DPR-2 Pattern chart raster'
    )
    ref, row = pair['reference'], pair['row']
    assert not violations(metrics(ref, ref, row)), (
        'The independent Pattern reference must pass identity without relaxed tolerances'
    )
    thin = np.round(255 - (255 - ref.astype(float)) * 0.5).astype(np.uint8)
    gap = ref.copy()
    gap[gap.shape[0] // 3 : gap.shape[0] // 3 + 12] = 255
    yy, xx = np.ogrid[: ref.shape[0], : ref.shape[1]]
    w, h = round(row['width'] * 2), round(row['height'] * 2)
    vertex = (xx - 30 / 70 * w) ** 2 + (yy - 25.5 / 306 * h) ** 2 <= 10**2
    blot = ref.copy()
    blot[vertex] = np.clip(255 - (255 - ref[vertex].astype(float)) * 1.7, 0, 255)
    notch = ref.copy()
    notch[vertex] = 255
    uneven = ref.copy()
    uneven[:, : w // 2] = thin[:, : w // 2]
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
