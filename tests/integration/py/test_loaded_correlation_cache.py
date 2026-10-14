"""Observe loaded-number reuse and invalidation through both production view entry points."""

import json
import subprocess
from pathlib import Path

import edi
import pytest

from tests.conftest import crysta_reference_prefix

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'repeat',
    'name-rename',
    'coefficient-write',
    'same-value-write',
    'alias-replace',
    'alias-reorder',
    'tail-alias-replace',
    'second-coefficient-write',
    'owner-replace',
    'replace-undo',
    'clear-undo',
    'clear-write-undo',
    'file-switch',
]


@pytest.fixture(scope='module')
def cache_probe(tmp_path_factory):
    build = tmp_path_factory.mktemp('loaded-correlation-cache')
    core = Path(edi._edi.__file__).resolve().parents[2] / 'core/libedi_core.a'
    subprocess.run(
        [
            'pixi',
            'run',
            '-e',
            'app',
            'python',
            str(ROOT / 'tests/fixtures/loaded_correlation_cache/build_probe.py'),
            '--root',
            str(ROOT),
            '--build',
            str(build),
            '--sdk',
            str(crysta_reference_prefix()),
            '--core',
            str(core),
        ],
        check=True,
    )
    return build / 'cmake/cache_probe'


def cells(frame):
    return {(cell['left'], cell['right']): cell['value'] for cell in frame['cells']}


@pytest.mark.parametrize('channel', ['rows', 'record'])
@pytest.mark.parametrize('scenario', CASES)
def test_loaded_numeric_cache_tracks_current_rows_and_recorded_coefficient_writes(
    cache_probe, channel, scenario
):
    observed = json.loads(
        subprocess.check_output([str(cache_probe), channel, scenario], text=True)
    )
    frames = observed['frames']
    assert observed['sameOwner'], 'The alias escapes must reach genuinely shared ownership blocks'
    assert all(frame['admitted'] for frame in frames), (
        'Native ItemVec admission must retain the actual row handles used by each publication'
    )
    base, ramp, curve = (
        'bank.background.base.coef',
        'bank.background.ramp.coef',
        'bank.background.curve.coef',
    )
    a = {(base, ramp): 0.5}
    b = {(base, curve): -0.25}
    if scenario == 'alias-reorder':
        expected = [a | b, a | b]
        parses = [2, 4]
        assert frames[0]['pointers'] == list(reversed(frames[1]['pointers'])), (
            'The reorder escape must exchange actual pointees under their one shared owner'
        )
    elif scenario == 'repeat':
        expected, parses = [a, a, a], [1, 1, 1]
    elif scenario == 'tail-alias-replace':
        expected = [a | b, a | {(curve, ramp): 0.125}]
        parses = [2, 4]
        assert frames[0]['pointers'][0] == frames[1]['pointers'][0], (
            'A tail-only replacement must keep the earlier row object unchanged'
        )
        assert frames[0]['pointers'][1] != frames[1]['pointers'][1], (
            'The tail escape must replace a later pointee under the same shared owner'
        )
    elif scenario == 'second-coefficient-write':
        expected = [a | b, a | {(base, curve): 0.125}]
        parses = [2, 4]
        assert frames[0]['pointers'] == frames[1]['pointers'], (
            'A later coefficient write must preserve every row object'
        )
        assert frames[0]['writes'][0] == frames[1]['writes'][0], (
            'The later-slot escape must leave the earlier coefficient unwritten'
        )
    elif scenario == 'owner-replace':
        expected, parses = [a, {(base, ramp): -0.875}], [1, 2]
        assert frames[0]['pointers'] == frames[1]['pointers'], (
            'Replacing an unbound row within its live owner must exercise address reuse'
        )
        assert frames[0]['writes'] != frames[1]['writes'], (
            'The new object at a reused address must carry its fresh coefficient identity'
        )
    elif scenario == 'name-rename':
        expected = [a, {('renamed.background.base.coef', 'renamed.background.ramp.coef'): 0.5}]
        parses = [1, 1]
    elif scenario in {'coefficient-write', 'same-value-write'}:
        expected = [a, {(base, ramp): -0.25 if scenario == 'coefficient-write' else 0.5}]
        parses = [1, 2]
        assert frames[0]['pointers'] == frames[1]['pointers'], (
            'Coefficient writes must reach the same still-live row object'
        )
        assert frames[0]['writes'] != frames[1]['writes'], (
            'The coefficient-write escape must carry its newly recorded write identity'
        )
    elif scenario == 'alias-replace':
        expected, parses = [a, b], [1, 2]
        assert frames[0]['pointers'] != frames[1]['pointers'], (
            'Alias replacement must change the pointee while preserving its ownership block'
        )
    elif scenario == 'replace-undo':
        expected, parses = [a, b, a], [1, 2, 3]
    elif scenario in {'clear-undo', 'clear-write-undo'}:
        expected = [a, {}, a if scenario == 'clear-undo' else {(base, ramp): -0.25}]
        parses = [1, 1, 1 if scenario == 'clear-undo' else 2]
        assert frames[1]['available'] == 0, (
            'Clearing current rows must leave no stale matrix cells'
        )
    else:
        other = {('other.background.base.coef', 'other.background.ramp.coef'): -0.25}
        expected = [a, b if channel == 'rows' else other, a]
        parses = [1, 2, 2] if channel == 'rows' else [2, 2, 2]
    assert [cells(frame) for frame in frames] == expected, (
        'Every loaded matrix must describe the current row object and coefficient at ' + scenario
    )
    assert [frame['parses'] for frame in frames] == parses, (
        'Unchanged repeats and name-only changes reuse numbers; changed input parses '
        'before display '
        'at ' + scenario
    )
