"""Judge real CI app traces against the owner's interval and view invariants."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from tests.integration.py.ui_causal_witnesses import actions
from tests.integration.py.ui_responsiveness_oracle import (
    events,
    first_frames,
    hidden_refreshes,
    one,
    timing,
    work_delivery,
)

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads((ROOT / 'tests/fixtures/ui_responsiveness/contract.json').read_text())


def load_observations():
    folder = Path(os.environ.get('EDI_UI_EVIDENCE', ROOT / 'build/ui-responsiveness'))
    manifest_path = folder / 'manifest.json'
    assert manifest_path.is_file(), (
        'UI acceptance requires fresh app scenario observations from CI preparation'
    )
    manifest = json.loads(manifest_path.read_text())
    current = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert manifest['source'] == current, 'UI observations must belong to this source head'
    binary = Path(manifest['binary']).read_bytes()
    assert hashlib.sha256(binary).hexdigest() == manifest['binary_sha256'], (
        'The observed app bytes must remain available and unchanged'
    )
    markers = set(re.findall(rb'edi-build-commit:([0-9a-f]{40})([^\n]*)\n', binary))
    assert markers == {(current.encode(), b'')}, (
        'The observed app must prove the actual clean current build identity'
    )
    traces = {}
    for key, run in manifest['runs'].items():
        path = (folder / run['path']).resolve()
        assert path.is_relative_to(folder.resolve()), (
            'UI trace paths must stay inside their run directory'
        )
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == run['sha256'], (
            'UI trace bytes must match the actual producer receipt'
        )
        traces[key] = [json.loads(line) for line in data.splitlines()]
    expected = set(CONTRACT['scenarios'])
    assert set(traces) == expected | {name + '-control' for name in expected}, (
        'Each scenario requires its own real blocking control'
    )
    return traces, manifest


@pytest.fixture(scope='module')
def observations():
    return load_observations()


@pytest.mark.parametrize('scenario', CONTRACT['scenarios'])
def test_actual_watchdog_and_blocking_control(observations, scenario):
    traces, manifest = observations
    for trace in (traces[scenario], traces[scenario + '-control']):
        actions(trace, scenario, CONTRACT['scenarios'][scenario])
        validate_input(trace, scenario, manifest)
    assert (
        one(traces[scenario], 'input')['identity']
        == one(traces[scenario + '-control'], 'input')['identity']
    ), 'Blocking controls must use the same actual scenario input as their ordinary run'
    timing(traces[scenario], scenario, CONTRACT['scenarios'][scenario])
    with pytest.raises(AssertionError, match='U8 permits no counted gap'):
        timing(
            traces[scenario + '-control'], scenario, CONTRACT['scenarios'][scenario], control=True
        )


def validate_input(trace, scenario, manifest):
    observed_input = one(trace, 'input')
    if scenario in {'e58-pages', 'e58-pattern'}:
        assert observed_input['patterns'] == (43802 if manifest['full_scan'] else 4000), (
            'The app must actually load the declared scan scale'
        )
        assert observed_input['structures'] == 2 and observed_input['measured'] is True, (
            'The owner scan has two linked phases and measured powder data'
        )
    elif scenario == 'e58-banks':
        assert observed_input['banks'] == 5, (
            'Bank switching must actually open all five committed NCAF WISH banks'
        )
    else:
        assert observed_input['points'] == 100 and observed_input['banks'] == 5, (
            'The end-transition scenario must run the actual one-hundred-point five-bank series'
        )
        assert one(trace, 'fit-finished')['completed'] == 100, (
            'The complete series must finish before the end transition is judged'
        )


def test_hidden_views_catch_up_once_and_deliver_newest_snapshots(observations):
    traces, _ = observations
    trace = traces['e58-series']
    hidden_refreshes(trace, CONTRACT['views'])
    work_delivery(trace)
    assert events(trace, 'fit-finished'), (
        'Hidden work is observed through a real running series and its end transition'
    )


def test_pattern_layout_is_complete_at_the_first_real_swap(observations):
    traces, _ = observations
    first_frames(traces['e58-pattern'])
