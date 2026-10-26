"""A real catch-up backlog keeps each receipt with its synchronized measured file."""

import json
import os

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture
from tests.fixtures.scan_app.harness import files, measured

FULL = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project'


@pytest.fixture(scope='module')
def backlog_frames():
    status, output = capture(
        [
            os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'),
            '-input',
            ROOT / 'tests/system/app/BackloggedFrames.qml',
            '-o',
            '-,txt',
        ],
        timeout=150,
    )
    assert status == 0 and '::BackloggedFrames::test_backlog_identity_and_no_view()' in output, (
        'The real backlog and no-view actor must complete its exact case: ' + output
    )
    rows = [
        json.loads(line.split('BACKLOG_FRAMES ', 1)[1])
        for line in output.splitlines()
        if 'BACKLOG_FRAMES ' in line
    ]
    assert len(rows) == 1, 'One complete synchronized backlog receipt is required'
    return rows[0]


def test_backlogged_frames_keep_their_own_file_and_points(backlog_frames):
    expected = files(FULL)
    seen = {}
    previous = 0
    for frame in backlog_frames:
        count = frame['count']
        assert type(count) is int and 1 <= count <= len(expected), (
            'Each synchronized receipt counts exactly one of the independently enumerated files'
        )
        assert count in {previous, previous + 1}, (
            'Synchronized frames consume consecutive files without skips or backward replay'
        )
        previous = count
        path = expected[count - 1]
        assert frame['file'] == path.name, (
            'Every frame names the oldest queued file in independent filename order'
        )
        assert frame['points'] and frame['calculatedCount'] > 0, (
            'Each named frame contains actual measured and calculated chart points'
        )
        reference = {x: y for x, y, _ in measured(path)}
        assert all(reference.get(round(x, 4)) == y for x, y in frame['points']), (
            'Every measured point consumed by the scene belongs to its named file'
        )
        assert count not in seen or seen[count] == frame['points'], (
            'An unchanged receipt cannot conceal replacement measured points on a later frame'
        )
        seen[count] = frame['points']
    assert sorted(seen) == list(range(1, len(expected) + 1)), (
        'The complete backlogged scan presents every file exactly in its counted frame sequence'
    )
