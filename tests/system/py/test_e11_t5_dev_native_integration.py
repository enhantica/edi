"""Finite native OFF/ON checks through the existing actual Main acceptance host.

The offline stdio peer supplies protocol events, never scientific answers or app
state. Native Estimate values come from frozen diffraction-lib reference bytes;
Undo and filesystem conservation compare pre-action native state and planted data.
"""

from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SUPPORT = ROOT / 'tests/integration/py/assistant_ui_probe'
REFERENCE = json.loads((ROOT / 'tests/fixtures/background_estimate/reference.json').read_text())
FINAL = 'Observed improvement recommendation: expose saved Estimate settings in tool diagnostics.'


class MainActor:
    def __init__(self, binary, folder, config, show_actions):
        self.folder = folder
        self.trace = folder / 'wire.jsonl'
        self.gate = folder / 'release-final'
        config_path = folder / 'peer.json'
        config_path.write_text(
            json.dumps({**config, 'trace': str(self.trace), 'final_text': FINAL})
        )
        executable = folder / 'codex'
        executable.write_text(f'#!{sys.executable}\n' + (SUPPORT / 'codex_peer.py').read_text())
        executable.chmod(0o700)
        self.stderr = (folder / 'host.stderr').open('w')
        self.process = subprocess.Popen(
            [str(binary), '--codex'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr,
            text=True,
            encoding='utf-8',
            bufsize=1,
            env={
                **os.environ,
                'EDI_CODEX_DEVELOPMENT_EXECUTABLE': str(executable),
                'EDI_TEST_CODEX_PEER_INPUT': str(config_path),
                'QT_QPA_PLATFORM': 'offscreen',
                'QT_QUICK_BACKEND': 'software',
            },
        )
        self.last = self.command('show_actions', enabled=show_actions)

    def command(self, op, **arguments):
        assert self.process.poll() is None, 'The real Main host must remain alive'
        self.process.stdin.write(json.dumps({'op': op, **arguments}) + '\n')
        self.process.stdin.flush()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            ready, _, _ = select.select(
                [self.process.stdout], [], [], max(0, deadline - time.monotonic())
            )
            assert ready, f'The finite Main command {op} must return a complete observation'
            line = self.process.stdout.readline()
            assert line, f'The actual Main host closed during {op}'
            if not line.startswith('{'):
                continue
            value = json.loads(line)
            assert 'host_error' not in value, value
            self.last = value
            return value
        raise AssertionError(f'No actual observation returned for {op}')

    def until(self, predicate):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            value = self.command('inspect')
            if predicate(value):
                return value
        raise AssertionError(
            'The actual native lifecycle did not settle: ' + json.dumps(self.last)
        )

    def connect(self):
        self.command('sign_in')
        self.until(lambda row: row['ui']['connected'])
        self.command('accept_context')
        assert not self.last['ui']['context_consent_required'], (
            'Ordinary current context consent must be established before delegated work'
        )

    def request(self, text='Use the current native operation and report actual outcomes.'):
        self.command('send_text', text=text)

    def responses(self):
        if not self.trace.exists():
            return []
        return [
            row
            for row in map(json.loads, self.trace.read_text().splitlines())
            if 'method' not in row and 'result' in row
        ]

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)
        self.process.stdout.close()
        self.stderr.close()


@pytest.fixture
def main_actor(tmp_path):
    actors = []

    def create(turns, *, show_actions=False, hold_final=False):
        supplied = os.environ.get('EDI_ASSISTANT_UI_PROBE')
        binary = Path(supplied) if supplied else ROOT / 'build/app/assistant_real_owner_probe'
        assert binary.is_file(), (
            'Build assistant_real_owner_probe in the single implementation-owned kit, '
            'then set EDI_ASSISTANT_UI_PROBE to that exact binary'
        )
        folder = tmp_path / ('actor-' + str(len(actors)))
        folder.mkdir()
        config = {'turns': turns}
        if hold_final:
            config['final_gate'] = str(folder / 'release-final')
        actor = MainActor(binary, folder, config, show_actions)
        actors.append(actor)
        return actor

    yield create
    for actor in reversed(actors):
        actor.close()


def copied_estimate_project(tmp_path, *, overrides=True):
    destination = tmp_path / 'native-project'
    shutil.copytree(ROOT / 'tests/fixtures/background_estimate/projects/hrpt', destination)
    if overrides:
        options = REFERENCE['cases']['hrpt']['methods']['arpls']['override']['options']
        path = destination / 'experiments/bank.edi'
        with path.open('a') as output:
            for key in ('method', 'width', 'smoothness', 'n_points'):
                output.write(f'\n_background_estimate.{key} {options[key]}\n')
    return destination


def point_rows(actor):
    return actor.last['ui']['project']['backgrounds'][0]['points']


def native_result(response):
    result = response['result']
    assert result['success'], f'The actual app must accept the native operation: {result}'
    return json.loads(result['contentItems'][0]['text'])


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


def test_actual_registry_offers_closed_estimate_and_optional_compound_background(main_actor):
    actor = main_actor([[]])
    tools = actor.command('tool_specs')['reply']['tools']
    names = [row['name'] for row in tools]
    assert len(names) == len(set(names)), 'Actual executable tool identities must be unique'
    offered = {row['name']: row for row in tools}
    schema = offered['estimate_background']['inputSchema']
    assert schema['type'] == 'object' and schema['additionalProperties'] is False
    assert set(schema['properties']) == {'purpose', 'experiment'}
    assert set(schema['required']) == {'purpose', 'experiment'}
    recipes = [
        row
        for row in objects(offered['create_cwl_project']['inputSchema'])
        if 'background' in row.get('properties', {})
    ]
    assert recipes, 'Explicit manual compound backgrounds remain supported'
    assert all('background' not in row.get('required', []) for row in recipes), (
        'The ordinary compound route cannot require invented manual anchors'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_native_estimate_uses_saved_nondefault_options_once_and_ordinary_undo(
    main_actor,
    tmp_path,
    show_actions,
):
    call = {
        'tool': 'estimate_background',
        'call_id': 'native-estimate-original',
        'arguments': {
            'purpose': 'Estimate from current measured data and saved settings',
            'experiment': 'bank',
        },
    }
    actor = main_actor([[call]], show_actions=show_actions)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    original = point_rows(actor)
    prior_undo = actor.last['ui']['project']['can_undo']
    actor.connect()
    actor.request()
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle')
    assert len(actor.responses()) == 1, 'Exactly one actual native tool response must settle'
    native_result(actor.responses()[0])
    expected = REFERENCE['cases']['hrpt']['methods']['arpls']['override']['anchors']
    points = point_rows(actor)
    assert len(points) == len(expected)
    for point, (position, intensity) in zip(points, expected, strict=True):
        assert point['position'] == pytest.approx(position, abs=1e-9, rel=0)
        assert point['intensity'] == pytest.approx(intensity, abs=1e-9, rel=1e-6)
        assert point['free'] is False
    if show_actions:
        assert True in actor.last['ui']['action_transitions'], (
            'Show actions must actually enter its native visible flow'
        )
    assert actor.command('save')['reply']['saved']
    actor.command('undo')
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert point_rows(actor) == original, 'One ordinary Undo restores the whole prior background'
    assert actor.last['ui']['project']['can_undo'] == prior_undo
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert point_rows(actor) == points, (
        'Save/reload preserves exact native estimated IDs and values'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_refused_estimate_cannot_mutate_and_does_not_block_next_native_operation(
    main_actor,
    tmp_path,
    show_actions,
):
    calls = [
        {
            'tool': 'estimate_background',
            'call_id': 'wrong-current-experiment',
            'arguments': {
                'purpose': 'Exercise an unavailable native target',
                'experiment': 'absent-bank',
            },
        },
        {
            'tool': 'estimate_background',
            'call_id': 'valid-after-refusal',
            'arguments': {
                'purpose': 'Continue from actual unchanged native state',
                'experiment': 'bank',
            },
        },
    ]
    actor = main_actor([calls], show_actions=show_actions)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    original = point_rows(actor)
    actor.connect()
    actor.request()
    actor.until(lambda row: len(actor.responses()) == 2 and row['ui']['state'] == 'idle')
    first, second = actor.responses()
    assert first['result']['success'] is False, 'The invalid exact target must really refuse'
    native_result(second)
    assert point_rows(actor) != original, (
        'The subsequent valid native action must actually execute'
    )
    actor.command('undo')
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert point_rows(actor) == original, 'The refused prefix must add no mutation or Undo entry'
    assert not actor.last['ui']['project']['can_undo']


def test_automatic_step_report_precedes_final_and_retains_latest_assessment(main_actor, tmp_path):
    call = {
        'tool': 'estimate_background',
        'call_id': 'automatic-step-native-estimate',
        'arguments': {'purpose': 'Observe a meaningful settled native step', 'experiment': 'bank'},
    }
    actor = main_actor([[call]], hold_final=True)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    actor.connect()
    actor.request()
    report = project / 'reports/work-report.json'
    actor.until(lambda _row: bool(actor.responses()) and report.is_file())
    native_result(actor.responses()[0])
    first = json.loads(report.read_bytes())
    assert first['scope_coverage']['trigger'] == 'automatic'
    assert call['call_id'] in json.dumps(first['history_evidence'])
    assert FINAL not in json.dumps(first['agent_assessment']), (
        'The held final assessment has not happened at this settled step'
    )
    actor.gate.touch()
    actor.command('refresh_usage')
    actor.until(lambda row: row['ui']['state'] == 'idle' and FINAL in report.read_text())
    final = json.loads(report.read_bytes())
    assert FINAL in json.dumps(final['agent_assessment'])
    assert final['identity_inputs']['skills'], (
        'Automatic diagnostic identity retains actual skills'
    )
    assert FINAL in json.dumps(actor.last['ui']['messages']), (
        'The final recommendation is user-visible'
    )


@pytest.mark.parametrize('collision', ['file', 'symlink'])
def test_report_refusal_preserves_unrelated_bytes_and_cannot_veto_science(
    main_actor,
    tmp_path,
    collision,
):
    call = {
        'tool': 'estimate_background',
        'call_id': 'science-despite-report-refusal',
        'arguments': {
            'purpose': 'Perform native science despite optional storage refusal',
            'experiment': 'bank',
        },
    }
    actor = main_actor([[call]])
    project = copied_estimate_project(tmp_path)
    reports = project / 'reports'
    reports.mkdir()
    destination = reports / 'work-report.json'
    unrelated = tmp_path / 'unrelated-original.json'
    protected = b'{"unrelated":"original user bytes"}\n'
    unrelated.write_bytes(protected)
    if collision == 'symlink':
        destination.symlink_to(unrelated)
    else:
        destination.write_bytes(protected)
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    original = point_rows(actor)
    actor.connect()
    actor.request()
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle')
    native_result(actor.responses()[0])
    assert point_rows(actor) != original, 'Report refusal cannot veto actual native Estimate'
    assert destination.read_bytes() == protected and unrelated.read_bytes() == protected
    if collision == 'symlink':
        assert destination.is_symlink(), 'The unrelated link itself must be preserved'
    assert actor.last['ui']['work_report'].get('disposition') not in {
        'saved',
        'saved_incomplete',
    }, 'The actual report receipt cannot falsely claim this protected collision was saved'
