"""Inspect actual saved PNG pixels after native camera and preference input."""

import json
import os
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import capture

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('kind', ['structure', 'pattern'])
@pytest.mark.parametrize('background', ['default', 'chart'])
def test_real_saved_image_background(kind, background):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Saved-image acceptance requires the actual Qt app test host'
    case = 'SavedImageAlpha::test_saved_png_background_follows_preferences'
    status, output = capture(
        [
            binary,
            '-input',
            ROOT / 'tests/unit/app/tst_saved_image_alpha.qml',
            f'{case}:{kind}-{background}',
        ],
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
    )
    assert status == 0, 'The actual camera and Preferences workflow completes: ' + output
    assert f'{case}({kind}-{background})' in output and '0 failed' in output, (
        'The requested real saved-image witness completes without an empty selector'
    )
    assert 'SKIP' not in output, 'Every saved-image background contract executes'
    images = [
        json.loads(line.split('SAVED_PNG_FACTS ', 1)[1])
        for line in output.splitlines()
        if 'SAVED_PNG_FACTS ' in line
    ]
    assert len(images) == 1, 'The actual saved image has one independent disk-decoder observation'
    facts = images[0]
    assert facts['format'] == 'png', 'The real saved image retains the PNG format'
    assert facts['width'] > 0 and facts['height'] > 0 and facts['opaque'] > 0, (
        'The independently decoded real PNG has a nonempty opaque foreground'
    )
    if background == 'default':
        assert facts['transparent'] > 0, (
            'The default saved image contains a transparent background'
        )
    else:
        assert facts['opaque'] == facts['width'] * facts['height'], (
            'Choosing the chart background makes every saved pixel opaque'
        )
