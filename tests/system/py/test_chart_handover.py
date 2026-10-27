"""Late scene callbacks must not acknowledge a replacement handover."""

import os
import subprocess

import pytest

from tests.fixtures.chart_handover.harness import build


@pytest.fixture(scope='module')
def handover_actor(tmp_path_factory):
    return build(tmp_path_factory.mktemp('chart-handover'))


@pytest.mark.parametrize('view', ['pattern', 'selection'])
@pytest.mark.parametrize('identity', ['different-file', 'same-file'])
def test_stale_synchronized_callback_keeps_replacement_pending(handover_actor, view, identity):
    result = subprocess.run(
        [str(handover_actor), view, identity],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, (
        'An earlier synchronized frame cannot count, clear or release a replacement handover: '
        + result.stdout
        + result.stderr
    )
    assert f'HANDOVER_OK {view} {identity}' in result.stdout, (
        'The requested late-callback case must complete its own-frame positive control'
    )
