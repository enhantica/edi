"""A real catch-up backlog keeps each receipt with its synchronized measured file."""

import hashlib
import json
import math
import os
import re
import time

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture
from tests.fixtures.scan_app.harness import files, measured

FULL = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project'


@pytest.fixture(scope='module')
def backlog_frames(tmp_path_factory):
    started = time.time_ns()
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
    assert not re.search(r'ListViewParameter\.qml[^\n]*(?:undefined|Unable to assign)', output), (
        'The weight-fraction cell supplies defined values during backlog navigation'
    )
    rows = [
        json.loads(line.split('BACKLOG_FRAMES_FILE ', 1)[1])
        for line in output.splitlines()
        if 'BACKLOG_FRAMES_FILE ' in line
    ]
    assert len(rows) == 1 and re.fullmatch(r'backlog-[0-9]+-[0-9]+\.json', rows[0]['name']), (
        'One complete frame receipt identifies its own safe unique output filename'
    )
    path = ROOT / 'build' / rows[0]['name']
    assert path.is_file() and path.stat().st_mtime_ns >= started, (
        'The frame file is freshly published by this completed actor, not a stale receipt'
    )
    payload = path.read_bytes()
    (tmp_path_factory.mktemp('backlog-receipt') / 'frames.json').write_bytes(payload)
    path.unlink()
    frames = json.loads(payload)
    assert isinstance(frames, list) and len(frames) == rows[0]['count'], (
        'The complete file agrees with the actor receipt, without dropped or truncated frames'
    )
    for frame in frames:
        coordinates = frame['points']
        assert (
            isinstance(coordinates, list)
            and len(coordinates) % 2 == 0
            and all(type(value) in {int, float} and math.isfinite(value) for value in coordinates)
        ), 'The native Qt frame wire list contains complete finite interleaved x/y pairs'
        frame['points'] = [
            coordinates[index : index + 2] for index in range(0, len(coordinates), 2)
        ]
    print(
        'BACKLOG_FRAME_RECEIPT sha256='
        + hashlib.sha256(payload).hexdigest()
        + ' frames='
        + str(len(frames)),
        flush=True,
    )
    return frames


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
