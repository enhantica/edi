"""Finite native OFF/ON checks through the existing actual Main acceptance host.

The offline stdio peer supplies protocol events, never scientific answers or app
state. Native Estimate values come from frozen diffraction-lib reference bytes;
Undo and filesystem conservation compare pre-action native state and planted data.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import select
import shutil
import subprocess
import sys
import time
from operator import itemgetter
from decimal import Decimal, ROUND_HALF_UP
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
                'QT_QPA_PLATFORM': os.environ.get('QT_QPA_PLATFORM', 'offscreen'),
                'QT_QUICK_BACKEND': os.environ.get('QT_QUICK_BACKEND', 'software'),
            },
        )
        self.last = self.command('show_actions', enabled=show_actions)
        (folder / 'environment.json').write_text(
            json.dumps(self.last['ui'].get('environment', {}), indent=2) + '\n'
        )

    def configure_turns(self, turns):
        requests = list(map(json.loads, self.trace.read_text().splitlines())) if self.trace.exists() else []
        assert not any(row.get('method') == 'turn/start' for row in requests), (
            'Only an offline peer with no submitted model turn may receive its finite calls'
        )
        path = self.folder / 'peer.json'
        value = json.loads(path.read_text(encoding='utf-8'))
        value['turns'] = turns
        path.write_text(json.dumps(value), encoding='utf-8')

    def append_turn(self, calls):
        assert self.last['ui']['state'] == 'idle', (
            'Only a settled offline peer may receive its next finite test turn'
        )
        path = self.folder / 'peer.json'
        value = json.loads(path.read_text(encoding='utf-8'))
        value['turns'].append(calls)
        path.write_text(json.dumps(value), encoding='utf-8')

    def command(self, op, **arguments):
        if getattr(self, '_stream_unusable', None):
            raise RuntimeError('Main command stream is unusable after an unsettled original request; no successor command was sent')
        # Manual GUI fixtures must enter the normal app before choosing its
        # tabs. This is driver input, never assistant-driven OFF presentation.
        if op == 'click' and arguments.get('name', '').startswith('appBar.tab.') and hasattr(self, 'last'):
            if any(row['name'] == 'home.start' and row['visible'] and row['enabled']
                   for row in self.last['ui'].get('controls', [])):
                self.command('click', name='home.start')
        assert self.process.poll() is None, 'The real Main host must remain alive'
        sequence = getattr(self, '_command_sequence', 0) + 1
        self._command_sequence = sequence
        started = time.monotonic()
        reads = []
        def unsettled(reason, pending):
            self._stream_unusable = {'sequence': sequence, 'op': op, 'reason': reason}
            self._unsettled_bytes = pending
            self._unsettled_command = {
                **self._stream_unusable, 'started_monotonic': started,
                'failed_monotonic': time.monotonic(), 'read_chunks': reads,
                'pending_bytes': len(pending), 'pid': self.process.pid,
                'process_exit': self.process.poll(),
            }
            try:
                (self.folder / 'unsettled-command-bytes.bin').write_bytes(pending)
                (self.folder / 'unsettled-command.json').write_text(
                    json.dumps(self._unsettled_command, indent=2) + '\n')
            except OSError as failure:
                self._unsettled_command['evidence_persistence_error'] = type(failure).__name__
        (self.folder / 'command-boundary.json').write_text(json.dumps({
            'op': op, 'pid': self.process.pid, 'started_monotonic': time.monotonic(),
            'reply_observed': False, 'process_exit_before_command': self.process.poll(),
        }, indent=2))
        request = json.dumps({'op': op, **arguments}) + '\n'
        try:
            self.process.stdin.write(request)
            self.process.stdin.flush()
        except (OSError, ValueError):
            unsettled('command write failed with uncertain delivery', getattr(self, '_stdout_bytes', b''))
            raise
        deadline = time.monotonic() + 10
        buffered = getattr(self, '_stdout_bytes', b'')
        while time.monotonic() < deadline:
            if b'\n' not in buffered:
                try:
                    ready, _, _ = select.select([self.process.stdout], [], [], max(0, deadline - time.monotonic()))
                except (OSError, ValueError):
                    unsettled('stdout readiness failed before original reply', buffered)
                    raise
                if not ready:
                    unsettled('stdout observation boundary expired before a complete reply', buffered)
                    raise AssertionError(f'The finite Main command {op} must return a complete observation')
                try:
                    chunk = os.read(self.process.stdout.fileno(), 65536)
                except OSError:
                    unsettled('stdout read failed before original reply', buffered)
                    raise
                if not chunk:
                    unsettled('stdout EOF before the original complete reply', buffered)
                    raise AssertionError(f'The actual Main host closed during {op}')
                reads.append({'monotonic': time.monotonic(), 'bytes': len(chunk)})
                buffered += chunk
                self._stdout_bytes = buffered
                continue
            raw, buffered = buffered.split(b'\n', 1)
            self._stdout_bytes = buffered
            try:
                line = raw.decode('utf-8')
            except UnicodeDecodeError:
                unsettled('invalid UTF-8 reply framing', raw + b'\n' + buffered)
                raise
            if not line.startswith('{'):
                try:
                    with (self.folder / 'host.stdout-diagnostics').open('a') as output:
                        output.write(line + '\n')
                except OSError:
                    unsettled('stdout notice persistence failed before original reply', raw + b'\n' + buffered)
                    raise
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                unsettled('invalid JSON reply framing', raw + b'\n' + buffered)
                raise
            if not isinstance(value, dict) or ('host_error' not in value and not {'ui','reply'} <= value.keys()):
                unsettled('unrecognized original reply envelope', raw + b'\n' + buffered)
                raise AssertionError('The Main reply must retain its actual ui/reply envelope')
            assert 'host_error' not in value, value
            self.last = value
            ui = value.get('ui', {})
            (self.folder / 'last-observation.json').write_text(json.dumps({
                'op': op, 'pid': self.process.pid, 'observed_monotonic': time.monotonic(),
                'process_exit': self.process.poll(),
                'ui': {key: ui[key] for key in (
                    'alive', 'project', 'controls', 'texts', 'state', 'connected',
                    'last_error', 'can_cancel', 'pending_question', 'pending_plan',
                    'singleton_identity', 'engine_parent', 'cpp_ownership',
                ) if key in ui},
            }, indent=2))
            (self.folder / 'command-boundary.json').write_text(json.dumps({
                'sequence': sequence, 'op': op, 'pid': self.process.pid, 'started_monotonic': started,
                'read_chunks': reads, 'reply_sha256': hashlib.sha256(raw).hexdigest(),
                'completed_monotonic': time.monotonic(),
                'reply_observed': True, 'process_exit': self.process.poll(),
            }, indent=2))
            if 'ui_sequence' in value.get('ui', {}):
                (self.folder / 'ui-sequence.json').write_text(json.dumps(value['ui']['ui_sequence'], indent=2))
            return value
        unsettled('original command deadline expired with no assigned complete reply', buffered)
        raise AssertionError(f'No actual observation returned for {op}')

    def until(self, predicate, *, seconds=10, visible_progress=False):
        started = time.monotonic()
        deadline = started + seconds
        outer = started + (120 if visible_progress else seconds)
        last_progress = None
        advances = 0
        while time.monotonic() < deadline and time.monotonic() < outer:
            value = self.command('inspect')
            if predicate(value):
                return value
            if visible_progress:
                ui = value['ui']
                controls = sorted((c['name'],c['visible'],c['enabled'],c['exposed'])
                    for c in ui['controls'] if c['visible'] and not c['name'].startswith(('assistant.','statusBar.assistant')))
                texts = sorted((t['name'],t['display']) for t in ui['texts']
                    if t['visible'] and 'Agent working' not in t['display'] and not t['name'].startswith(('assistant.','statusBar.assistant')))
                activities = [(m.get('id'),m.get('status')) for m in ui['messages'] if m.get('kind')=='activity']
                progress = json.dumps([ui.get('project'),controls,texts,activities],sort_keys=True)
                if last_progress is None:
                    last_progress = progress
                elif progress != last_progress:
                    advances += 1
                    last_progress = progress
                    deadline = time.monotonic() + seconds
        if visible_progress:
            elapsed = time.monotonic()-started
            sequence = self.last['ui'].get('ui_sequence',[])
            receipt = {'elapsed_seconds':elapsed,'semantic_advances':advances,
                'cue_moves':sum(x['kind']=='pointer_moved' for x in sequence),
                'presses':sum(x['kind']=='pointer_pressed' for x in sequence),
                'reason':'finite outer observation bound' if time.monotonic()>=outer else 'no semantic progress',
                'stall_seconds':seconds,'outer_seconds':120}
            (self.folder/'visible-observation-boundary.json').write_text(json.dumps(receipt,indent=2)+'\n')
        receipt = self.folder / 'last-lifecycle-receipt.json'
        receipt.write_text(json.dumps(self.last, indent=2) + '\n')
        ui = self.last.get('ui', {})
        summary = {key: ui.get(key) for key in ('state','connected','can_cancel','last_error')}
        summary['project_name'] = (ui.get('project') or {}).get('name')
        raise AssertionError('The actual native lifecycle did not settle: ' + json.dumps(summary)
                             + '; complete receipt: ' + str(receipt))

    def connect(self):
        if not self.last['ui']['connected']:
            if any(row['name'] == 'home.start' and row['visible'] and row['enabled']
                   for row in self.last['ui']['controls']):
                self.command('click', name='home.start')
            self.until(lambda row: any(c['name'] == 'assistant.connection' and c['fully_exposed']
                                      and c['enabled'] for c in row['ui']['controls']))
            self.command('sign_in')
            self.until(lambda row: row['ui']['connected'])
        self.command('accept_context')
        assert not self.last['ui']['context_consent_required'], (
            'Ordinary current context consent must be established before delegated work'
        )

    def begin_current_file_selection(self):
        # The actual generic Controller is created by the original connection
        # bootstrap. Normal AssistantComposer.chooseFiles also requires connected
        # and calls this public selection operation with requireSignedIn=true.
        self.connect()
        token = self.command('evaluate', expression='Session.assistant.beginFileSelection(true)')['reply']['value']
        assert token, 'Normal current file admission has an actual signed-in owner before selecting input bytes'
        return token

    def request(self, text='Use the current native operation and report actual outcomes.'):
        required = self.last['ui']['context_consent_required']
        self.command('send_text', text=text)
        # Same fixture authorization, through the actual original context
        # disclosure owner. Never accept a file/project chooser as a substitute.
        if required and any(row['name'] == 'assistant.contextSummary' and row['visible']
                            for row in self.last['ui']['texts']):
            assert self.command('accept_dialog')['reply']['accepted'], (
                'The actual current context disclosure must accept its original captured user draft'
            )

    def responses(self):
        if not self.trace.exists():
            return []
        return [
            row
            for row in map(json.loads, self.trace.read_text().splitlines())
            if 'method' not in row and 'result' in row
        ]

    def close(self):
        # Read-only failure-tail evidence before this host's temporary Documents
        # disappears. Never Save, create science, follow links or alter the owner.
        if self.process.poll() is None and not getattr(self, '_stream_unusable', None):
            try:
                final = self.command('evaluate', expression='Session.lastError')
                (self.folder / 'final-owner-error.json').write_text(
                    json.dumps({'session_last_error': final['reply']['value'],
                                'assistant_last_error': final['ui']['last_error'],
                                'state': final['ui']['state']}, indent=2) + '\n')
                path = final['ui'].get('project', {}).get('path')
                temporary = Path(final['test_storage']).resolve()
                if path:
                    current = Path(path)
                    if current.is_dir() and current.resolve().is_relative_to(temporary):
                        shutil.copytree(current, self.folder / 'actual-project-before-teardown',
                                        symlinks=True)
            except Exception as error:
                (self.folder / 'failure-tail-gap.json').write_text(
                    json.dumps({'exception_class': type(error).__name__}) + '\n')
        # A dead child is itself evidence; cleanup must not erase its real exit
        # status behind a secondary BrokenPipe from closing the command stream.
        before = self.process.poll()
        try:
            self.process.stdin.close()
        except BrokenPipeError:
            pass
        killed = False
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            killed = True
            self.process.kill()
            self.process.wait(timeout=2)
        (self.folder / 'host-exit.json').write_text(json.dumps({
            'pid': self.process.pid, 'exit_before_cleanup': before,
            'exit': self.process.returncode, 'cleanup_killed_after_deadline': killed,
        }, indent=2) + '\n')
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
    coding_errors = []
    for actor in actors:
        coding_errors.extend(
            line
            for line in (actor.folder / 'host.stderr').read_text(errors='replace').splitlines()
            if re.search(
                r'ReferenceError|TypeError|Unable to assign \[undefined\]|'
                r'Cannot assign to non-existent property|Detected function .*Connections',
                line,
            )
        )
    assert not coding_errors, (
        'E11 F4 actual successful and intentional-refusal flows have no undefined QML hooks: '
        + '\n'.join(coding_errors)
    )



def wait_positive_tab(actor, name):
    """Normal setup only: wait for the actual loader-backed enabled tab, without revealing controls."""
    if any(c['name'] == 'home.start' and c['visible'] and c['enabled'] for c in actor.last['ui']['controls']):
        actor.command('click', name='home.start')
    actor.until(lambda row: any(c['name'] == name and c['visible'] and c['enabled'] and c['exposed']
                              for c in row['ui']['controls']))

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


def qml(actor, expression):
    # QQmlExpression represents JS objects/arrays as QJSValue; the existing host
    # QVariant bridge supports primitive strings, not QJSValue materialization.
    # Transfer the actual JSON value explicitly without changing the app owner.
    value = actor.command('evaluate', expression='JSON.stringify((' + expression + '))')['reply']['value']
    return json.loads(value) if isinstance(value, str) else None


def control_expression(name):
    return (
        '(function seek(item) { if (item.objectName === '
        + json.dumps(name)
        + ') return item; for (const child of (item.children || [])) '
        '{ const found=seek(child); if(found) return found; } return null; })(contentItem)'
    )


def tool_call(tool, identity, **arguments):
    return {
        'tool': tool,
        'call_id': identity,
        'arguments': {
            'purpose': 'Exercise the existing native boundary with explicit current inputs',
            **arguments,
        },
    }


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
    sites = [
        row
        for row in objects(offered['create_cwl_project']['inputSchema'])
        if 'wyckoff_letter' in row.get('properties', {})
    ]
    assert sites and all('wyckoff_letter' not in row.get('required', []) for row in sites), (
        'Manual mapped construction must permit the ordinary native omitted Wyckoff letter'
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
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle', visible_progress=show_actions)
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
    # Immutable reference: Crysta058166 su_format.cpp round_plain is SIX
    # significant figures, HALF-AWAY; save_project.cpp keeps positions exact.
    # This is an independent decoded-codec expectation, never writer output.
    def ordinary_no_su(value):
        number=Decimal(str(value))
        if number.is_zero():return float(number)
        return float(number.quantize(Decimal(1).scaleb(number.adjusted()-5),rounding=ROUND_HALF_UP))
    decoded=[{**point,'intensity':ordinary_no_su(point['intensity'])} for point in points]
    before_background=json.loads(actor.last['ui']['context'])['datasets'][0]['background']
    assert all(point.get('uncertainty') in (None,0) for point in before_background['anchors']), (
        'The independently specified six-figure rule is exercised only by this genuine no-SU background fixture'
    )
    settings={key:before_background[key] for key in ('type','estimate')}
    assert actor.command('save')['reply']['saved']
    assert point_rows(actor)==decoded, (
        'Ordinary Save adopts precisely the independently specified no-SU six-figure tokens while IDs, order, positions and flags stay exact'
    )
    actor.command('undo')
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert point_rows(actor) == original, 'One ordinary Undo restores the whole prior background'
    assert actor.last['ui']['project']['can_undo'] == prior_undo
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert point_rows(actor) == decoded, (
        'Genuine Open preserves exact IDs, order, positions and flags plus the independent decoded ordinary intensity codec'
    )
    reopened_background=json.loads(actor.last['ui']['context'])['datasets'][0]['background']
    assert {key:reopened_background[key] for key in ('type','estimate')}==settings, (
        'Background family and every independently retained native Estimate setting remain exact through Save and genuine Open'
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
    actor.until(lambda row: len(actor.responses()) == 2 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    first, second = actor.responses()
    assert first['result']['success'] is False, 'The invalid exact target must really refuse'
    model_visible = json.loads(first['result']['contentItems'][0]['text'])
    assert isinstance(model_visible.get('message'), str) and model_visible['message'].strip(), (
        'The actual model-visible refusal retains its bounded human app diagnostic, not only debug history'
    )
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


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
@pytest.mark.parametrize(
    ('code', 'length_a', 'length_c', 'gamma'),
    [
        ('9008506', 3.20927, 5.21033, 120),
        ('1000041', 5.62, 5.62, 90),
    ],
)
def test_selected_published_cif_reaches_native_load_without_recreating_structure(
    main_actor,
    tmp_path,
    show_actions,
    code,
    length_a,
    length_c,
    gamma,
):
    actor = main_actor([[]], show_actions=show_actions)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    before = actor.last['ui']['project']['structure_rows']
    path = ROOT / f'tests/fixtures/dictionary_display/published_cod_{code}.cif'
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(path)])['reply']['added']
    selected = actor.last['ui']['selected_files']
    assert len(selected) == 1 and selected[0]['id'], (
        'A genuine admitted opaque file ID is required'
    )
    actor.configure_turns([
        [
            {
                'tool': 'load_structure',
                'call_id': 'published-cif-' + code,
                'arguments': {
                    'purpose': 'Import the genuine attached published CIF',
                    'file_id': selected[0]['id'],
                },
            }
        ]
    ])
    actor.connect()
    actor.request('Use the attached CIF through native Load structure.')
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle', visible_progress=show_actions)
    native_result(actor.responses()[0])
    after = actor.last['ui']['project']['structure_rows']
    assert len(after) == len(before) + 1 and after[:-1] == before
    imported = after[-1]
    assert imported['length_a'] == length_a and imported['length_c'] == length_c
    assert imported['gamma'] == gamma
    actor.command('undo')
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert actor.last['ui']['project']['structure_rows'] == before


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_explicit_manual_native_setup_does_not_import_the_attached_cif(
    main_actor,
    show_actions,
):
    override = 6.173
    turns = [
        [
            {
                'tool': 'create_structure',
                'call_id': 'manual-create-original',
                'arguments': {'purpose': 'Create a structure manually without CIF import'},
            },
            {
                'tool': 'set_parameters',
                'call_id': 'manual-explicit-value',
                'arguments': {
                    'purpose': 'Retain the explicit user-supplied manual cell value',
                    'values': [
                        {
                            'path': {'created_structure_parameter': 'cell.length_a'},
                            'value': override,
                        }
                    ],
                },
            },
        ]
    ]
    actor = main_actor(turns, show_actions=show_actions)
    assert actor.command('create', name='explicit-manual-fixture')['reply']['created']
    path = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(path)])['reply']['added']
    actor.connect()
    actor.request('Add the structure manually without loading the attached CIF. Use a=6.173.')
    actor.until(lambda row: len(actor.responses()) == 2 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    for response in actor.responses():
        native_result(response)
    rows = actor.last['ui']['project']['structure_rows']
    assert len(rows) == 1 and rows[0]['length_a'] == override
    assert rows[0]['length_c'] != 5.21033, 'The attached Mg CIF cannot replace native defaults'
    assert rows[0]['sites'] == 1, 'Manual Create retains its ordinary initial atom'


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_current_disabled_relation_preserves_ordinary_rows_and_duplicate_call_is_once(
    main_actor,
    tmp_path,
    show_actions,
):
    call = {
        'tool': 'add_relations',
        'call_id': 'same-native-disabled-relation',
        'arguments': {
            'purpose': 'Preserve the explicitly disabled ordinary relation',
            'aliases': [{'id': 'manual_cell', 'path': 'phase.cell.length_a'}],
            'constraints': [
                {
                    'id': 'manual_disabled',
                    'expression': 'manual_cell = a + 5.873',
                    'enabled': False,
                }
            ],
        },
    }
    actor = main_actor([[]], show_actions=show_actions)
    project = tmp_path / 'relation-project'
    shutil.copytree(ROOT / 'tests/fixtures/constraint_expressions/project', project)
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    original = actor.last['ui']['project']
    call['arguments']['aliases'][0]['path'] = next(
        row['path']
        for row in original['parameters']
        if row['category'] == 'cell' and row['field'] == 'length_a'
    )
    call['replay_request_once'] = True
    actor.configure_turns([[call]])
    actor.connect()
    actor.request()
    actor.until(
        lambda row: bool(actor.responses()) and row['ui']['state'] in {'idle', 'interrupted'}
    , visible_progress=show_actions)
    sent = [
        json.loads(line)
        for line in actor.trace.with_suffix('.sent.jsonl').read_text(encoding='utf-8').splitlines()
    ]
    assert len([row for row in sent if row.get('method') == 'item/tool/call']) == 2, (
        'The once witness must actually deliver both correlated native requests'
    )
    native_result(actor.responses()[0])
    current = actor.last['ui']['project']
    assert current['aliases'][:-1] == original['aliases']
    assert current['constraints'][:-1] == original['constraints']
    assert current['aliases'][-1] == {'id': 'manual_cell', 'parameter': 'phase.cell.length_a'}
    assert current['constraints'][-1] == {
        'id': 'manual_disabled',
        'expression': 'manual_cell = a + 5.873',
        'enabled': False,
    }
    assert current['parameters'] == original['parameters'], (
        'A disabled relation and duplicate delivery cannot change scientific values/flags'
    )
    if not show_actions:
        actor.command('undo')
        actor.until(lambda row: not row['ui']['project']['calculating'])
        assert actor.last['ui']['project']['aliases'] == original['aliases']
        assert actor.last['ui']['project']['constraints'] == original['constraints']


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_native_free_eligibility_follows_current_dev_marks_without_old_boolean_fields(
    main_actor,
    tmp_path,
    show_actions,
):
    actor = main_actor([[]], show_actions=show_actions)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    parameters = actor.last['ui']['project']['parameters']
    blocked = next(row for row in parameters if row['fit_blocker'] != 0 and not row['free'])
    eligible = next(
        row
        for row in parameters
        if row['fit_blocker'] == 0 and row['refinable'] and not row['free']
    )
    assert blocked['fit_reason'], 'The current dev rule must give a real exclusion reason'
    actor.configure_turns([
        [
            {
                'tool': 'set_free',
                'call_id': 'current-native-ineligible',
                'arguments': {
                    'purpose': 'Exercise the existing native fittability refusal',
                    'flags': [{'path': blocked['path'], 'free': True}],
                },
            },
            {
                'tool': 'set_free',
                'call_id': 'current-native-eligible',
                'arguments': {
                    'purpose': 'Continue with an actually eligible native parameter',
                    'flags': [{'path': eligible['path'], 'free': True}],
                },
            },
        ]
    ])
    actor.connect()
    actor.request()
    actor.until(lambda row: len(actor.responses()) == 2 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    assert actor.responses()[0]['result']['success'] is False
    native_result(actor.responses()[1])
    after = {row['path']: row for row in actor.last['ui']['project']['parameters']}
    assert after[blocked['path']] == blocked
    assert after[eligible['path']]['free'] is True
    assert after[eligible['path']]['value'] == eligible['value']


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
@pytest.mark.parametrize('letter', [None, 'a'], ids=['omitted', 'explicit'])
def test_manual_mapped_wyckoff_omission_and_explicit_value_survive_save_reload(
    main_actor,
    tmp_path,
    show_actions,
    letter,
):
    actor = main_actor([[]], show_actions=show_actions)
    assert actor.command('create', name='manual-mapped-native')['reply']['created']
    data = ROOT / 'tests/fixtures/background_estimate/meas-lbco-hrpt.xye'
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(data)])['reply']['added']
    file_id = actor.last['ui']['selected_files'][0]['id']
    site = {
        'id': 'manual_site',
        'type_symbol': 'Si',
        'fract_x': 0.173,
        'fract_y': 0.281,
        'fract_z': 0.419,
        'occupancy': 0.73,
    }
    if letter is not None:
        site['wyckoff_letter'] = letter
    mapped = {
        'name': 'manual_phase',
        'space_group': {'name_h_m': 'P 1', 'coord_system_code': ''},
        'cell': {
            'length_a': 6.173,
            'length_b': 5.917,
            'length_c': 4.863,
            'angle_alpha': 86.3,
            'angle_beta': 93.1,
            'angle_gamma': 112.7,
        },
        'atom_sites': [site],
        'atom_site_adps': [{'id': 'manual_site', 'adp_type': 'Biso', 'adp_iso': 0.37}],
    }
    recipe = {
        'project_name': 'manual-mapped-native',
        'description': 'Explicit synthetic test inputs',
        'experiment_name': 'manual_bank',
        'sample_form': 'powder',
        'beam_mode': 'constant wavelength',
        'radiation_probe': 'neutron',
        'scattering_type': 'bragg',
        'peak_profile': 'cwl-tch-pseudo-voigt',
        'wavelength': 1.237,
        'zero_offset': 0.013,
        'phase_scale': 1.1,
        'background': [{'position': 10, 'intensity': 167}, {'position': 164.85, 'intensity': 109}],
        'exclusions': [],
        'initial_parameters': [],
    }
    actor.configure_turns([
        [
            {
                'tool': 'create_cwl_project',
                'call_id': 'manual-mapped-letter',
                'arguments': {
                    'purpose': 'Construct explicit manual input with native Wyckoff policy',
                    'mapped_structure': mapped,
                    'data_file_id': file_id,
                    'recipe': recipe,
                },
            }
        ]
    ])
    actor.connect()
    actor.request('Construct this explicit manual setup and preserve supplied values.')
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle', visible_progress=show_actions)
    native_result(actor.responses()[0])
    actor.until(lambda row: not row['ui']['project']['calculating'])
    rows = actor.last['ui']['project']['structure_rows']
    assert len(rows) == 1 and rows[0]['id'] == mapped['name']
    assert rows[0]['length_a'] == mapped['cell']['length_a']
    actual_site = rows[0]['atom_rows'][0]
    assert actual_site['id'] == site['id'] and actual_site['type'] == site['type_symbol']
    assert [actual_site[key] for key in ('x', 'y', 'z', 'occupancy')] == [
        site[key] for key in ('fract_x', 'fract_y', 'fract_z', 'occupancy')
    ]
    if letter is not None:
        assert actual_site['wyckoff'] == letter, 'An explicit supplied letter remains exact'
    destination = tmp_path / 'saved-manual'
    assert actor.command('save_as', path=str(destination))['reply']['saved']
    assert actor.command('open', path=str(destination))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert actor.last['ui']['project']['structure_rows'] == rows, (
        'Omitted or explicit native site identity and values survive ordinary save/reload'
    )


def test_opening_a_saved_project_without_assistant_work_does_not_fabricate_a_report(
    main_actor,
    tmp_path,
):
    actor = main_actor([[]])
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert not (project / 'reports/work-report.json').exists()
    receipt = actor.last['ui']['work_report']
    assert receipt.get('disposition') not in {'saved', 'saved_incomplete'}


def test_unsaved_work_retains_accessible_diagnostics_without_implicit_science_save(main_actor):
    actor = main_actor([
        [
            {
                'tool': 'create_structure',
                'call_id': 'unsaved-native-work',
                'arguments': {'purpose': 'Perform actual work in an unsaved project'},
            }
        ]
    ])
    assert actor.command('create', name='unsaved-native-report')['reply']['created']
    actor.connect()
    actor.request()
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle')
    native_result(actor.responses()[0])
    assert actor.last['ui']['project']['structures'] == 1
    native_path = actor.last['ui']['project']['path']
    assert isinstance(native_path, str) and not native_path, (
        'Optional reporting cannot implicitly save a project'
    )
    receipt = actor.last['ui']['work_report']
    assert receipt.get('disposition') not in {'saved', 'saved_incomplete'}
    assert 'storage_root_unavailable' in json.dumps(receipt), (
        'The unavailable native root must be reported honestly, not treated as saved or disabled'
    )
    # Owner2c9 explicitly elects a current/last diagnostic cache before a project
    # has a working root. This updates only the former no-appdata policy, while
    # retaining the original no-autosave and truthful missing-project-copy checks.
    document = qml(actor, 'Session.assistant.workReportDocument()')
    cached = json.loads(document)
    assert 'unsaved-native-work' in json.dumps(cached), (
        'The current diagnostic cache exposes actual unsaved work without another provider request'
    )
    assert isinstance(cached, dict) and not actor.last['ui']['project']['path'], (
        'The available diagnostic cache is distinct from the explicitly unavailable unsaved project mirror'
    )
    assert not actor.last['ui']['project']['path'], (
        'Explicit diagnostic cache access cannot turn unsaved scientific work into a project Save'
    )


def test_save_copy_keeps_automatic_final_report_at_the_actual_live_project_root(
    main_actor, tmp_path
):
    call = {
        'tool': 'estimate_background',
        'call_id': 'copy-root-native-step',
        'arguments': {
            'purpose': 'Keep the final report with the live owner after Save copy',
            'experiment': 'bank',
        },
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
    copied = tmp_path / 'ordinary-save-copy'
    assert actor.command('save_project_as', path=str(copied), zip=False, copy=True)['reply'][
        'saved'
    ]
    assert actor.last['ui']['project']['path'] == str(project)
    copy_report = copied / 'reports/work-report.json'
    copy_before = copy_report.read_bytes() if copy_report.exists() else None
    actor.gate.touch()
    actor.command('refresh_usage')
    actor.until(lambda row: row['ui']['state'] == 'idle' and FINAL in report.read_text())
    assert (copy_report.read_bytes() if copy_report.exists() else None) == copy_before, (
        'Later automatic captures cannot rebind the live writer to an ordinary saved copy'
    )


def test_late_old_turn_cannot_publish_its_report_into_a_switched_project(main_actor, tmp_path):
    call = {
        'tool': 'estimate_background',
        'call_id': 'old-owner-native-step',
        'arguments': {
            'purpose': 'Exercise the actual project switch retirement',
            'experiment': 'bank',
        },
    }
    actor = main_actor([[call]], hold_final=True)
    project = copied_estimate_project(tmp_path)
    successor = tmp_path / 'successor-project'
    shutil.copytree(ROOT / 'tests/fixtures/background_estimate/projects/hrpt', successor)
    successor_record = successor / 'project.edi'
    successor_record.write_text(
        successor_record.read_text().replace(
            '_metadata.name background-estimate', '_metadata.name successor-native-owner'
        )
    )
    original_successor = {
        str(path.relative_to(successor)): path.read_bytes()
        for path in successor.rglob('*')
        if path.is_file()
    }
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    actor.connect()
    actor.request()
    old_report = project / 'reports/work-report.json'
    actor.until(lambda _row: bool(actor.responses()) and old_report.is_file())
    native_result(actor.responses()[0])
    assert actor.command('open', path=str(successor))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    actor.gate.touch()
    actor.command('refresh_usage')
    actor.until(lambda row: row['ui']['state'] in {'idle', 'interrupted'})
    successor_report = successor / 'reports/work-report.json'
    assert not successor_report.exists() or FINAL not in successor_report.read_text(), (
        'A late old-provider final cannot become scientific evidence for the new project owner'
    )
    after = {
        str(path.relative_to(successor)): path.read_bytes()
        for path in successor.rglob('*')
        if path.is_file() and path != successor_report
    }
    assert after == original_successor, 'Old work cannot change the successor project files'


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
@pytest.mark.parametrize('kind', ['line-segment', 'polynomial', 'chebyshev'])
def test_actual_native_mixed_batch_cannot_bypass_automatic_background_owner(
    main_actor,
    tmp_path,
    show_actions,
    kind,
):
    actor = main_actor([[]], show_actions=show_actions)
    project = tmp_path / 'automatic-native-project'
    shutil.copytree(
        ROOT / 'tests/fixtures/background_estimate/projects' / ('fitted-auto-' + kind), project
    )
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    native = actor.last['ui']['project']
    assert native['backgrounds'][0]['mode'] == 'auto'
    parameters = native['parameters']
    owned = next(
        row
        for row in parameters
        if row['category'] == 'background' and row['field'] in {'intensity', 'coef'}
    )
    unrelated = next(
        row
        for row in parameters
        if row['category'] == 'cell' and row['field'] == 'length_a' and row['refinable']
    )
    actor.configure_turns([
        [
            {
                'tool': 'set_parameters',
                'call_id': 'mixed-auto-owner-native',
                'arguments': {
                    'purpose': 'Exercise complete native prewrite ownership validation',
                    'values': [
                        {'path': unrelated['path'], 'value': unrelated['value'] + 0.03125},
                        {'path': owned['path'], 'value': owned['value'] + 1.0},
                    ],
                },
            }
        ]
    ])
    actor.connect()
    actor.request()
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle', visible_progress=show_actions)
    assert actor.responses()[0]['result']['success'] is False
    assert actor.last['ui']['project']['parameters'] == parameters, (
        'Automatic point/poly/Chebyshev ownership must refuse the whole native batch before writes'
    )
    assert actor.last['ui']['project']['backgrounds'] == native['backgrounds']
    assert actor.last['ui']['project']['can_undo'] == native['can_undo']


@pytest.mark.parametrize(
    'name',
    [
        'sc-neut-cwl_tb2ti2o7-heidi_basic',
        'sc-neut-tof_taurine-unknown_basic',
    ],
)
def test_actual_native_outgoing_context_keeps_published_single_crystal_measurements(
    main_actor,
    tmp_path,
    name,
):
    actor = main_actor([[]])
    project = tmp_path / 'single-crystal-native'
    shutil.copytree(ROOT / 'docs/user/cli' / name / 'project', project)
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    context = json.loads(actor.last['ui']['context'])
    assert 'error' not in context
    native = actor.last['ui']['project']['backgrounds']
    assert len(context['datasets']) == len(native)
    for row, bank in zip(context['datasets'], native, strict=True):
        assert bank['reflection_count'] > 0
        assert row['id'] == bank['id'] and row['sample_form'] == 'single crystal'
        assert row['data_status'] == 'present'
        assert row['observations']['intensity_count'] == bank['reflection_count']
        assert row['observations']['sigma_count'] == bank['reflection_sigma_count']
        assert row['observations']['weighting'] == 'measured_standard_uncertainty'
        assert row['axis']['kind'] == 'miller_indices'
        assert row['axis']['count'] == bank['reflection_count']
        assert row['peak_profile_options'] == [] and row['absorption_type_options'] == []
        assert row['background'] is None, 'SC context cannot advertise a powder background'


def copied_point_project(tmp_path, mode):
    project = tmp_path / 'structural-background-native'
    shutil.copytree(
        ROOT / 'tests/fixtures/background_estimate/projects/fitted-auto-line-segment', project
    )
    if mode == 'manual':
        experiment = project / 'experiments/d20.edi'
        text = experiment.read_text(encoding='utf-8')
        assert text.count('_background_estimate.mode auto') == 1, (
            'The independent saved fixture must expose its actual declared automatic mode'
        )
        experiment.write_text(
            text.replace('_background_estimate.mode auto', '_background_estimate.mode manual'),
            encoding='utf-8',
        )
    return project


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
@pytest.mark.parametrize('mode', ['auto', 'manual'])
@pytest.mark.parametrize('operation', ['add', 'update', 'remove'])
def test_native_point_operations_respect_automatic_owner_and_keep_free_flag_continuation(
    main_actor,
    tmp_path,
    show_actions,
    mode,
    operation,
):
    actor = main_actor([[]], show_actions=show_actions)
    project = copied_point_project(tmp_path, mode)
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    original = actor.last['ui']['project']
    bank = original['backgrounds'][0]
    assert bank['mode'] == mode and bank['type'] == 'line-segment'
    points = bank['points']
    assert len(points) >= 3, 'The saved fixture supplies removable interior points'
    target = points[len(points) // 2]
    arguments = {
        'purpose': 'Exercise current native structural background ownership',
        'experiment': bank['id'],
        'operation': operation,
    }
    if operation == 'remove':
        arguments['id'] = target['id']
    elif operation == 'update':
        arguments.update(
            id=target['id'],
            position=target['position'],
            intensity=target['intensity'] + 0.375,
            free=not target['free'],
        )
    else:
        arguments.update(
            id='explicit_added_point',
            position=(points[0]['position'] + points[1]['position']) / 2,
            intensity=points[0]['intensity'] + 0.375,
            free=True,
        )
    flag = next(
        row
        for row in original['parameters']
        if row['category'] == 'background'
        and row['field'] == 'intensity'
        and row['row_label'] == points[0]['id']
    )
    calls = [
        {
            'tool': 'edit_background',
            'call_id': 'structural-native-' + operation,
            'arguments': arguments,
        },
        {
            'tool': 'set_free',
            'call_id': 'allowed-free-after-structural-result',
            'arguments': {
                'purpose': 'Retain separately permitted ordinary free-flag semantics',
                'flags': [{'path': flag['path'], 'free': not flag['free']}],
            },
        },
        {
            'tool': 'set_free',
            'call_id': 'restore-permitted-free-flag',
            'arguments': {
                'purpose': 'Restore the original native flag through the same allowed operation',
                'flags': [{'path': flag['path'], 'free': flag['free']}],
            },
        },
        {
            'tool': 'inspect_project',
            'call_id': 'inspect-after-structural-and-flags',
            'arguments': {'purpose': 'Continue with actual current native state'},
        },
    ]
    actor.configure_turns([calls])
    actor.connect()
    actor.request('Respect the current automatic owner and retain allowed free-flag operations.')
    actor.until(
        lambda row: (
            len(actor.responses()) == len(calls)
            and row['ui']['state'] == 'idle'
            and not row['ui']['project']['calculating']
        )
    , visible_progress=show_actions)
    responses = actor.responses()
    for response in responses[1:]:
        native_result(response)
    current = actor.last['ui']['project']
    assert current['structure_rows'] == original['structure_rows']
    assert current['backgrounds'][0]['mode'] == mode

    def unaffected(rows):
        return {row['path']: row for row in rows if row['category'] != 'background'}

    assert unaffected(current['parameters']) == unaffected(original['parameters'])
    if mode == 'auto':
        assert responses[0]['result']['success'] is False, (
            'Automatic ownership must refuse native add/update/remove before any structural write'
        )
        assert current['backgrounds'] == original['backgrounds']
        assert current['parameters'] == original['parameters']
        for _ in range(2):
            actor.command('undo')
        actor.until(lambda row: not row['ui']['project']['calculating'])
        assert actor.last['ui']['project']['can_undo'] == original['can_undo'], (
            'After undoing the two real flag edits, a refused structural operation adds no Undo'
        )
        assert actor.last['ui']['project']['backgrounds'] == original['backgrounds']
    else:
        native_result(responses[0])
        expected = [dict(row) for row in points]
        if operation in {'update', 'remove'}:
            expected = [row for row in expected if row['id'] != target['id']]
        if operation != 'remove':
            expected.append({
                key: arguments[key] for key in ('id', 'position', 'intensity', 'free')
            })
        expected.sort(key=itemgetter('position'))
        assert current['backgrounds'][0]['points'] == expected, (
            'Manual native structural edits retain exact explicit operands and all unaffected rows'
        )


@pytest.mark.parametrize('mode', ['throw', 'bad_alloc', 'retire'])
def test_estimate_actual_postwrite_outcome_preowns_undo_and_survives_retirement(
    main_actor, tmp_path, mode
):
    actor = main_actor([[]])
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'E11 F3 actual Estimate application, publication and preowned Undo remain truthful'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    before = point_rows(actor)
    actor.command('arm_estimate_publication', mode=mode, minimum_points=len(
        REFERENCE['cases']['hrpt']['methods']['arpls']['override']['anchors']))
    receipt = actor.command('estimate_outcome')['reply']
    fault = actor.command('publication_fault')['reply']
    assert fault['hits'] >= 1 and fault['undo_seen'], (
        'Actual postwrite presentation is reached with ordinary Undo already owned'
    )
    assert receipt['applied'] and not receipt['published'] and receipt['message'], (
        'Postwrite failure retains the real applied effect and failed publication'
    )
    if mode == 'retire':
        assert not actor.last['ui']['project'], (
            'The actual Session retirement must complete safely'
        )
    else:
        assert point_rows(actor) != before, 'The failure witness follows a real scientific write'
        actor.command('undo')
        actor.until(lambda row: not row['ui']['project']['calculating'])
        assert point_rows(actor) == before, (
            'One real ordinary Undo restores the prewrite background'
        )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_registered_estimate_partial_effects_are_not_relabelled_as_zero_steps(
    main_actor, tmp_path, show_actions
):
    actor = main_actor(
        [
            [
                tool_call('estimate_background', 'postwrite-estimate', experiment='bank'),
                tool_call('inspect_project', 'after-postwrite-inspection'),
            ]
        ],
        show_actions=show_actions,
    )
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'E11 F3 actual Estimate application, publication and preowned Undo remain truthful'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    before = point_rows(actor)
    actor.command('arm_estimate_publication', mode='throw')
    actor.connect()
    actor.request()
    actor.until(lambda row: len(actor.responses()) == 2 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    payload = json.loads(actor.responses()[0]['result']['contentItems'][0]['text'])
    receipts = [row for row in objects(payload) if 'applied' in row and 'steps_completed' in row]
    assert receipts and any(
        row['applied'] and row['steps_completed'] == 1 and not row.get('complete', True)
        for row in receipts
    ), 'Both registered modes disclose the actual applied Estimate despite failed presentation'
    assert point_rows(actor) != before, (
        'The registered refusal has a real independently visible effect'
    )
    native_result(actor.responses()[1])
    actor.command('undo')
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert point_rows(actor) == before, 'Registered partial Estimate keeps its one ordinary Undo'


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
@pytest.mark.parametrize('route', ['cif', 'mapped'])
def test_compound_default_estimate_refusal_preserves_and_discloses_actual_setup_prefix(
    main_actor, tmp_path, show_actions, route
):
    actor = main_actor([[]], show_actions=show_actions)
    assert actor.command('create', name='compound-prefix')['reply']['created'], (
        'The compound refusal witness starts from the actual ordinary empty project'
    )
    # One real observation is valid input for ordinary import but cannot supply
    # the distinct endpoints required by the native background Estimate action.
    data = tmp_path / 'one-observation.xye'
    data.write_text('34.25 17.25 .75\n')
    cif = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(data), str(cif)])['reply'][
        'added'
    ], 'The compound witness uses actual selected immutable inputs'
    files = actor.last['ui']['selected_files']
    data_id = next(row['id'] for row in files if row['name'] == data.name)
    cif_id = next(row['id'] for row in files if row['name'] == cif.name)
    recipe = {
        'project_name': 'compound-prefix',
        'description': 'Explicit bounded input witness',
        'experiment_name': 'one_point',
        'sample_form': 'powder',
        'beam_mode': 'constant wavelength',
        'radiation_probe': 'neutron',
        'scattering_type': 'bragg',
        'peak_profile': 'cwl-tch-pseudo-voigt',
        'wavelength': 1.237,
        'zero_offset': 0.013,
        'phase_scale': 1.1,
        'exclusions': [],
        'initial_parameters': [],
    }
    arguments = {'data_file_id': data_id, 'recipe': recipe}
    if route == 'cif':
        arguments['cif_file_id'] = cif_id
    else:
        arguments['mapped_structure'] = {
            'name': 'manual_prefix',
            'space_group': {'name_h_m': 'P 1', 'coord_system_code': ''},
            'cell': {
                'length_a': 6.173,
                'length_b': 5.917,
                'length_c': 4.863,
                'angle_alpha': 86.3,
                'angle_beta': 93.1,
                'angle_gamma': 112.7,
            },
            'atom_sites': [
                {
                    'id': 'Si1',
                    'type_symbol': 'Si',
                    'fract_x': 0.173,
                    'fract_y': 0.281,
                    'fract_z': 0.419,
                    'occupancy': 0.73,
                }
            ],
            'atom_site_adps': [{'id': 'Si1', 'adp_type': 'Biso', 'adp_iso': 0.37}],
        }
    actor.configure_turns([
        [tool_call('create_cwl_project', 'compound-default-estimate', **arguments)]
    ])
    actor.connect()
    actor.request(
        'Construct this explicit manual setup without CIF import.'
        if route == 'mapped'
        else 'Import the selected CIF and measurement and use native Estimate.'
    )
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle', visible_progress=show_actions)
    payload = json.loads(actor.responses()[0]['result']['contentItems'][0]['text'])
    current = actor.last['ui']['project']
    assert current['structures'] == 1 and len(current['backgrounds']) == 1, (
        'The real compound setup prefix must be adopted before the expected Estimate refusal'
    )
    receipts = [row for row in objects(payload) if 'complete' in row and 'steps_completed' in row]
    assert any(not row['complete'] and row['steps_completed'] > 0 for row in receipts), (
        'Default Estimate refusal cannot become completed setup or erase its actual applied prefix'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_relation_receipts_cover_all_existing_alias_and_constraint_operations(
    main_actor, tmp_path, show_actions
):
    actor = main_actor([[]], show_actions=show_actions)
    project = tmp_path / 'ordinary-relations'
    shutil.copytree(ROOT / 'tests/fixtures/constraint_expressions/project', project)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'E11 F6 actual current relation controls retain complete original row semantics'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    qml(
        actor,
        '(function(){ const rows=Session.project.analysis.aliases; rows.append(); '
        'const n=rows.count-1; rows.setText(n,"id","fixture_unused"); '
        'return rows.setText(n,"parameter","phase.cell.length_a"); })()',
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    original = actor.command('inspect')['ui']['project']
    identity = original['constraints'][-1]['id']
    edits = [
        ('alias_rename', 'fixture_unused', 'fixture_renamed'),
        (
            'alias_target',
            'fixture_renamed',
            next(
                row['path']
                for row in original['parameters']
                if row['category'] == 'cell' and row['field'] == 'length_b'
            ),
        ),
        ('alias_remove', 'fixture_renamed', None),
        ('constraint_rename', identity, 'changed_relation'),
        ('constraint_expression', 'changed_relation', 'b = 2.75*a + 0.5'),
        ('constraint_enabled', 'changed_relation', False),
        ('constraint_enabled', 'changed_relation', True),
        ('constraint_remove', 'changed_relation', None),
    ]
    calls = []
    for index, (operation, target, value) in enumerate(edits):
        arguments = {'operation': operation, 'id': target}
        if value is not None:
            arguments['value'] = value
        calls.append(tool_call('edit_relation', f'ordinary-relation-{index}', **arguments))
    actor.configure_turns([calls])
    actor.connect()
    actor.request()
    actor.until(lambda row: len(actor.responses()) == len(calls) and row['ui']['state'] == 'idle', visible_progress=show_actions)
    for response in actor.responses():
        native_result(response)
    current = actor.last['ui']['project']
    assert current['aliases'] == original['aliases'][:-1], (
        'Alias rename retarget and remove retain every unrelated original declaration'
    )
    assert current['constraints'] == original['constraints'][:-1], (
        'Constraint id expression enabled and remove operations reach their ordinary receipts'
    )
    for _ in edits:
        actor.command('undo')
        actor.until(lambda row: not row['ui']['project']['calculating'])
    restored = actor.last['ui']['project']
    assert restored['aliases'] == original['aliases'], (
        'E11 F6 actual current relation controls retain complete original row semantics'
    )
    assert restored['constraints'] == original['constraints'], (
        'E11 F6 actual current relation controls retain complete original row semantics'
    )
    assert restored['parameters'] == original['parameters'], (
        'The exact ordinary history restores all prior relation and scientific facts'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_grouped_fixed_and_free_use_exact_full_membership_with_mixed_and_subset_controls(
    main_actor, tmp_path, show_actions
):
    actor = main_actor([[]], show_actions=show_actions)
    project = copied_estimate_project(tmp_path)
    # Keep the original >2/full-vs-proper-subset escape meaningful. The base
    # source owns only two anchors; add one explicit fixture anchor from the
    # independent diffraction-lib reference rather than weaken that predicate.
    position, intensity = REFERENCE['cases']['hrpt']['methods']['arpls']['override']['anchors'][2]
    record = project / 'experiments/bank.edi'
    text = record.read_text()
    text = text.replace('old_b 164.84999999999999 0\n',
        f'fixture_middle {position:.17g} {intensity:.17g}\nold_b 164.84999999999999 0\n')
    record.write_text(text)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'E11 F8 grouped flags preserve exact requested membership and final state'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    original = actor.last['ui']['project']['parameters']
    group = [
        row
        for row in original
        if row['category'] == 'background'
        and row['refinable']
        and row['fit_blocker'] == 0
        and row['dependence'] == 0
    ]
    assert len(group) > 2, 'The native measured category supplies a genuine mixed full-set witness'
    subset = [group[0], group[-1]]
    mixed = [{'path': row['path'], 'free': index % 2 == 0} for index, row in enumerate(group)]
    fixed = [{'path': row['path'], 'free': False} for row in reversed(group)]
    free = [{'path': row['path'], 'free': True} for row in group]
    actor.configure_turns([
        [tool_call('set_free', 'prepare-real-mixed-category', flags=mixed)],
        [tool_call('set_free', 'whole-mixed-category-fixed', flags=fixed)],
        [tool_call('set_free', 'whole-already-fixed-noop', flags=fixed)],
        [tool_call('set_free', 'whole-fixed-category-free', flags=free)],
        [
            tool_call(
                'set_free',
                'proper-reordered-subset',
                flags=[{'path': row['path'], 'free': False} for row in reversed(subset)],
            )
        ],
    ])
    actor.connect()
    for turn in range(5):
        actor.request()
        actor.until(
            lambda row, turn=turn: (
                len(actor.responses()) == turn + 1 and row['ui']['state'] == 'idle'
            )
        , visible_progress=show_actions)
        native_result(actor.responses()[-1])
        by_path = {row['path']: row for row in actor.last['ui']['project']['parameters']}
        wanted = (
            mixed
            if turn == 0
            else fixed
            if turn < 3
            else free
            if turn == 3
            else [{'path': row['path'], 'free': row not in subset} for row in group]
        )
        assert all(by_path[row['path']]['free'] == row['free'] for row in wanted), (
            'Every complete menu action or proper subset reaches exactly its requested final flags'
        )
        untouched = {row['path']: row for row in original if row not in group}
        assert {path: by_path[path] for path in untouched} == untouched, (
            'Grouped actions cannot broaden the proved category membership'
        )
        if turn == 2:
            actor.command('undo')
            actor.until(lambda row: not row['ui']['project']['calculating'])
            current = {
                row['path']: row['free'] for row in actor.last['ui']['project']['parameters']
            }
            assert all(current[row['path']] == row['free'] for row in mixed), (
                'Already-fixed no-op contributes no extra Undo after one actual header action'
            )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_native_clear_keeps_the_current_blocked_but_free_parameter_policy(
    main_actor, tmp_path, show_actions
):
    actor = main_actor([[]], show_actions=show_actions)
    project = tmp_path / 'blocked-free-simulation'
    shutil.copytree(ROOT / 'tests/fixtures/excluded_display/cw', project)
    # FIRST tests/unit/app/tst_calculation_only_fitting.qml::open(false):
    # genuine simulation input plus a stored free scale blocked by no observations.
    # The previous unrelated TOF tag in a CW file was not a legal native fixture.
    record = project / 'experiments/pattern.edi'
    text = record.read_text()
    assert 'phase 1\n' in text and 'loop_\n_data.two_theta\n' in text, (
        'The prior ordinary simulation fixture supplies its real scale and explicit measured loop'
    )
    text = text.replace('phase 1\n', 'phase 1()\n')
    text = text.split('loop_\n_data.two_theta\n')[0] + (
        '_data_range.two_theta_min 10\n_data_range.two_theta_max 90\n_data_range.two_theta_step 0.5\n')
    record.write_text(text)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'The independent inactive free-term fixture loads through the ordinary owner'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    original = actor.last['ui']['project']['parameters']
    blocked = next(row for row in original if row['free'] and row['fit_blocker'] != 0)
    actor.configure_turns([
        [
            tool_call(
                'set_free',
                'clear-original-blocked-free',
                flags=[{'path': blocked['path'], 'free': False}],
            )
        ]
    ])
    actor.connect()
    actor.request()
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle', visible_progress=show_actions)
    native_result(actor.responses()[0])
    after = {row['path']: row for row in actor.last['ui']['project']['parameters']}
    assert not after[blocked['path']]['free'], (
        'Current fittability refusal cannot prevent clearing an already stored free flag'
    )
    assert all(after[row['path']] == row for row in original if row['path'] != blocked['path']), (
        'Clearing a blocked free member changes no unrelated parameter'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_unmodified_current_save_uses_the_same_ordinary_owner_once(
    main_actor, tmp_path, show_actions
):
    call = tool_call('save_project', 'valid-current-unmodified-save', destination='current')
    actor = main_actor([[call]], show_actions=show_actions)
    project = copied_estimate_project(tmp_path, overrides=False)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'E11 F11 unchanged current Save uses the ordinary owned project in both modes'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    before = actor.last['ui']['project']
    actor.connect()
    actor.request()
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle', visible_progress=show_actions)
    native_result(actor.responses()[0])
    assert len(actor.responses()) == 1, (
        'E11 F11 unchanged current Save uses the ordinary owned project in both modes'
    )
    assert actor.last['ui']['project']['path'] == str(project), (
        'E11 F11 unchanged current Save uses the ordinary owned project in both modes'
    )
    assert actor.last['ui']['project']['parameters'] == before['parameters'], (
        'E11 F11 unchanged current Save uses the ordinary owned project in both modes'
    )
    assert actor.last['ui']['project']['backgrounds'] == before['backgrounds'], (
        'Disabled ordinary Save presentation does not veto or edit a valid current project'
    )


@pytest.mark.parametrize('zip_output', [False, True], ids=['folder', 'zip'])
def test_later_automatic_captures_follow_actual_save_as_working_root(
    main_actor, tmp_path, zip_output
):
    actor = main_actor(
        [[tool_call('estimate_background', 'root-step', experiment='bank')]], hold_final=True
    )
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'E11 F10 captures retain the actual current root, scope and latest terminal state'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    actor.connect()
    actor.request()
    old_report = project / 'reports/work-report.json'
    actor.until(lambda _row: bool(actor.responses()) and old_report.is_file())
    native_result(actor.responses()[0])
    destination = tmp_path / ('moved.zip' if zip_output else 'moved-folder')
    assert actor.command('save_project_as', path=str(destination), zip=zip_output, copy=False)[
        'reply'
    ]['saved'], 'E11 F10 captures retain the actual current root, scope and latest terminal state'
    working = Path(actor.last['ui']['project']['path'])
    report = working / 'reports/work-report.json'
    actor.gate.touch()
    actor.command('refresh_usage')
    actor.until(
        lambda row: (
            row['ui']['state'] == 'idle' and report.is_file() and FINAL in report.read_text()
        )
    )
    assert actor.last['ui']['project']['path'] == str(working), (
        'E11 F10 captures retain the actual current root, scope and latest terminal state'
    )
    if working != project:
        assert not old_report.exists() or FINAL not in old_report.read_text(), (
            'Admitted writers retain their root; later captures follow Save As'
        )
    assert actor.command('save')['reply']['saved'], (
        'The existing explicit Session Save still owns normal archive packing'
    )


def test_busy_retired_scope_completion_retries_current_final_capture(main_actor, tmp_path):
    actor = main_actor([
        [tool_call('inspect_project', 'first-scope-inspection')],
        [tool_call('inspect_project', 'successor-inspection')],
    ])
    project = copied_estimate_project(tmp_path)
    successor = tmp_path / 'successor'
    shutil.copytree(ROOT / 'tests/fixtures/background_estimate/projects/hrpt', successor)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'E11 F10 captures retain the actual current root, scope and latest terminal state'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    actor.connect()
    actor.request()
    actor.until(
        lambda row: (
            len(actor.responses()) == 1
            and row['ui']['state'] == 'idle'
            and row['ui']['work_report'].get('phase') == 'terminal'
        )
    )
    sequence = actor.command(
        'capture_sequence',
        successor=str(successor),
        text='Inspect the new current owner and report its final state.',
    )['reply']
    assert sequence['opened'], (
        'E11 F10 captures retain the actual current root, scope and latest terminal state'
    )
    assert sequence['receipts'][0]['phase'] == 'accepted', (
        'The old writer is actually admitted before the successor capture'
    )
    assert sequence['receipts'][1]['disposition'] == 'busy', (
        'The successor witness must reach the real single busy writer before owner delivery'
    )
    report = successor / 'reports/work-report.json'
    actor.until(
        lambda row: (
            len(actor.responses()) == 2
            and row['ui']['state'] == 'idle'
            and report.is_file()
            and 'successor-inspection' in report.read_text()
        )
    )
    assert FINAL in report.read_text(), (
        'The latest current final state is retried after retired completion'
    )
    assert 'first-scope-inspection' not in report.read_text(), (
        'The old admitted receipt is never published as the new scope evidence'
    )


def test_compiled_registered_skill_bytes_and_effective_runtime_guidance_are_coherent(main_actor):
    actor = main_actor([[tool_call('inspect_project', 'effective-guidance-inspection')]])
    embedded = actor.command('embedded_skills')['reply']
    resources = {row['id']: row for row in embedded['resources']}
    for row in embedded['index']['skills']:
        actual = resources[row['id']]
        assert hashlib.sha256(actual['content'].encode()).hexdigest() == row['sha256'], (
            'E11 F12 actual registered skill and effective instruction identities remain coherent'
        )
        assert actual['sha256'] == row['sha256'], (
            'E11 F12 actual registered skill and effective instruction identities remain coherent'
        )
        assert (
            actual['content'].encode()
            == (ROOT / 'data/assistant/skills' / row['path']).read_bytes()
        ), 'E11 F12 actual registered skill and effective instruction identities remain coherent'
    active = '\n'.join(
        resources[key]['content'] for key in ('project-assistance', 'refinement-strategy')
    )
    assert (
        'Append creates a local Draft' not in active
        and 'requires its original Confirm' not in active
    ), 'Actual registered bodies cannot direct excluded manual relation controls'
    assert 'Estimate' in active, 'Actual registered guidance uses the ordinary default estimator'
    actor.command('create', name='effective-guidance-current-owner')
    actor.connect()
    actor.request()
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle')
    wire = [json.loads(line) for line in actor.trace.read_text().splitlines()]
    starts = [row['params'] for row in wire if row.get('method') == 'thread/start']
    assert len(starts) == 1, (
        'The assembled instruction must be captured at its actual runtime entrance'
    )
    instructions = starts[0].get('developerInstructions')
    assert isinstance(instructions, str) and instructions, (
        'The effective developer instruction is present at its real runtime boundary'
    )
    text = ' '.join(instructions.lower().split())
    assert 'only after all requested structure' not in text, (
        'E11 F12 actual registered skill and effective instruction identities remain coherent'
    )
    assert 'finish all requested structure' not in text, (
        'E11 F12 actual registered skill and effective instruction identities remain coherent'
    )
    assert 'then one fit and inspect before choosing the next' not in text, (
        'Effective runtime guidance cannot mandate a fixed planning recipe'
    )
    tools = actor.command('tool_specs')['reply']['tools']
    for tool in tools:
        description = ' '.join(tool['description'].lower().split())
        assert 'only after all requested structure' not in description, (
            'Registered operation descriptions cannot reinstate the removed global sequence'
        )


@pytest.mark.parametrize('ending', ['completed', 'cancelled', 'process_exit'])
def test_settled_public_research_retains_opaque_results_and_terminal_capture(
    main_actor, tmp_path, ending
):
    actor = main_actor([[]], hold_final=True)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'E11 F10 captures retain the actual current root, scope and latest terminal state'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    release = actor.folder / 'release-search'
    actions = [
        {
            'type': 'search',
            'query': 'FullProf background estimation documentation',
            'queries': None,
        },
        {'type': 'openPage', 'url': 'https://www.ill.eu/sites/fullprof/'},
        {
            'type': 'findInPage',
            'url': 'https://www.ill.eu/sites/fullprof/',
            'pattern': 'background',
        },
    ]
    steps = []
    for index, action in enumerate(actions):
        steps.append({
            'call_id': 'actual-research-' + str(index),
            'research': {
                'query': 'Public scientific software documentation',
                'action': action,
                'results': [
                    {
                        'type': 'text_result',
                        'ref_id': f'turn0search{index}',
                        'url': 'https://www.ill.eu/sites/fullprof/',
                        'title': 'FullProf documentation',
                        'snippet': 'Public background estimation reference',
                        'future_field': {'preserved': True},
                    },
                    {'type': 'error', 'message': 'Public service unavailable'},
                ],
            },
            **({'hold_complete': str(release)} if index == 0 else {}),
            **({'duplicate': True} if index == 1 else {}),
        })
    actor.configure_turns([steps + [tool_call('inspect_project', 'after-public-research')]])
    config_path = actor.folder / 'peer.json'
    config = json.loads(config_path.read_text())
    config['terminal_status'] = ending
    config_path.write_text(json.dumps(config))
    actor.connect()
    actor.request(
        'Consult public software documentation, retain citations, then inspect current state.'
    )
    actor.until(lambda row: row['ui']['can_cancel'])
    report = project / 'reports/work-report.json'
    if report.exists():
        pending = json.loads(report.read_bytes())
        assert 'turn0search0' not in json.dumps(pending['history_evidence']), (
            'A started empty research item cannot fabricate its not-yet-delivered result'
        )
    release.touch()
    actor.command('refresh_usage')
    actor.until(
        lambda _row: (
            bool(actor.responses()) and report.is_file() and 'turn0search2' in report.read_text()
        )
    )
    native_result(actor.responses()[0])
    settled = json.loads(report.read_bytes())
    assert settled['scope_coverage']['trigger'] == 'automatic', (
        'E11 F10 captures retain the actual current root, scope and latest terminal state'
    )
    for index in range(3):
        assert f'actual-research-{index}' in json.dumps(settled['history_evidence']), (
            'E11 F10 captures retain the actual current root, scope and latest terminal state'
        )
        assert f'turn0search{index}' in report.read_text(), (
            'E11 F10 captures retain the actual current root, scope and latest terminal state'
        )
    assert (
        'future_field' in report.read_text() and 'Public service unavailable' in report.read_text()
    ), 'Opaque result and unavailability evidence survive actual item settlement'
    assert FINAL not in json.dumps(settled['agent_assessment']), (
        'E11 F10 captures retain the actual current root, scope and latest terminal state'
    )
    if ending == 'cancelled':
        actor.command('cancel')
        actor.until(
            lambda row: (
                not row['ui']['can_cancel']
                and any(word in report.read_text().lower() for word in ('cancel', 'interrupt'))
            )
        )
    else:
        actor.gate.touch()
        actor.command('refresh_usage')
        actor.until(
            lambda row: (
                not row['ui']['can_cancel']
                and (
                    FINAL in report.read_text()
                    if ending == 'completed'
                    else bool(row['ui']['last_error'])
                    and row['ui']['last_error'] in report.read_text()
                )
            )
        )
    assert actor.last['ui']['project']['path'] == str(project), (
        'Research or provider terminal failure never substitutes another scientific owner'
    )


def test_actual_manual_text_editor_preserves_composition_escape_and_real_commit(main_actor):
    actor = main_actor([[]])
    assert actor.command('open', path=str(ROOT / 'tests/fixtures/constraint_expressions/project'))[
        'reply'
    ]['opened'], 'E11 F4 actual manual composition, publication and member lifetime remain safe'
    actor.until(lambda row: not row['ui']['project']['calculating'])
    original = actor.last['ui']['project']['structure_rows'][0]['id']
    wait_positive_tab(actor, 'appBar.tab.structure')
    actor.command('click', name='appBar.tab.structure')
    actor.command('click', name='structures.name.0')
    actor.command('manual_key', key='select_all')
    actor.command('manual_text', text='uncommitted_owner')
    actor.command('manual_ime', preedit='Q', commit='')
    assert actor.command('focused_input')['reply']['preedit'] == 'Q', (
        'E11 F4 actual manual composition, publication and member lifetime remain safe'
    )
    qml(actor, 'Session.project.currentStructure.cell.lengthA.value = 4.375')
    assert actor.command('focused_input')['reply']['preedit'] == 'Q', (
        'Ordinary clean scientific publication cannot erase real IME composition'
    )
    actor.command('manual_ime', preedit='', commit='')
    actor.command('manual_key', key='escape')
    assert actor.last['ui']['project']['structure_rows'][0]['id'] == original, (
        'E11 F4 actual manual composition, publication and member lifetime remain safe'
    )
    actor.command('click', name='structures.name.0')
    actor.command('manual_key', key='select_all')
    actor.command('manual_text', text='committed_owner')
    actor.command('manual_key', key='return')
    assert actor.last['ui']['project']['structure_rows'][0]['id'] == 'committed_owner', (
        'A genuine manual keyboard commit reaches the current text cell and its real model'
    )


def test_actual_parameter_cell_clean_publication_and_recycling_keep_original_member(main_actor):
    actor = main_actor([[]])
    assert actor.command('open', path=str(ROOT / 'tests/fixtures/constraint_expressions/project'))[
        'reply'
    ]['opened'], 'E11 F4 actual manual composition, publication and member lifetime remain safe'
    actor.until(lambda row: not row['ui']['project']['calculating'])
    wait_positive_tab(actor, 'appBar.tab.analysis')
    actor.command('click', name='appBar.tab.analysis')
    table = control_expression('parameters.list')
    qml(actor, f'{table}.sourceModel.nameFilter = "length_a"')
    actor.command('click', name='parameters.value.0')
    actor.command('manual_key', key='select_all')
    actor.command('manual_text', text='9.125')
    actor.command('manual_ime', preedit='7', commit='')
    qml(actor, 'Session.project.currentStructure.cell.lengthA.value = 5.375')
    focused = actor.command('focused_input')['reply']
    assert focused['text'] == '9.125' and focused['preedit'] == '7', (
        'Current parameter publication retains the actual manual draft and IME preedit'
    )
    actor.command('manual_ime', preedit='', commit='')
    actor.command('manual_key', key='escape')
    assert float(actor.command('focused_input')['reply']['text']) == 5.375, (
        'E11 F4 actual manual composition, publication and member lifetime remain safe'
    )
    original_b = next(
        row
        for row in actor.last['ui']['project']['parameters']
        if row['path'].endswith('cell.length_b')
    )['value']
    actor.command('manual_key', key='select_all')
    actor.command('manual_text', text='11.625')
    qml(actor, f'{table}.sourceModel.nameFilter = "length_b"')
    actor.command('manual_key', key='return')
    after_b = next(
        row
        for row in actor.last['ui']['project']['parameters']
        if row['path'].endswith('cell.length_b')
    )['value']
    assert after_b == original_b, (
        'A recycled delegate cannot commit an older member draft to its successor'
    )


@pytest.mark.parametrize('boundary', ['current_changes', 'removed', 'rejected'])
def test_ordinary_measurement_picker_keeps_its_original_experiment_intent(
    main_actor, tmp_path, boundary
):
    actor = main_actor([[]])
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'E11 F5 ordinary picker retains its exact original owner and selected bytes'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert qml(actor, 'Session.project.duplicateExperiment()'), (
        'E11 F5 ordinary picker retains its exact original owner and selected bytes'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    original = actor.last['ui']['project']['backgrounds']
    data = tmp_path / 'ordinary-picker.xye'
    data.write_text('21.5 17.25 .75\n22.75 31.75 1.25\n25.125 23.5 1.5\n')
    wait_positive_tab(actor, 'appBar.tab.experiment')
    actor.command('click', name='appBar.tab.experiment')
    actor.command('click', name='experiments.loadData.0')
    if boundary == 'removed':
        qml(actor, 'Session.project.removeExperiment(0)')
    elif boundary == 'current_changes':
        qml(actor, 'Session.project.currentExperimentIndex = 1')
    answer = actor.command('file_answer', path=str(data), reject=boundary == 'rejected')['reply']
    if boundary != 'removed':
        assert answer['answered'], (
            'The actual ordinary FileDialog consumes its real selection or rejection'
        )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    after = actor.last['ui']['project']['backgrounds']
    if boundary == 'current_changes':
        assert after[0]['id'] == original[0]['id'] and after[0]['input_count'] == 3, (
            'E11 F5 ordinary picker retains its exact original owner and selected bytes'
        )
        assert after[0]['input_first'] == [
            [21.5, 17.25, 0.75],
            [22.75, 31.75, 1.25],
            [25.125, 23.5, 1.5],
        ], 'E11 F5 ordinary picker retains its exact original owner and selected bytes'
        assert after[1] == original[1], (
            'Picker acceptance cannot substitute the newly selected experiment'
        )
    elif boundary == 'removed':
        assert after == original[1:], (
            'A removed picker owner cannot redirect its bytes into another row'
        )
    else:
        assert after == original, 'Ordinary picker rejection changes no scientific input'


@pytest.mark.parametrize('position', ['offscreen', 'clipped'])
def test_on_native_parameter_target_is_revealed_from_real_virtualized_or_clipped_geometry(
    main_actor, tmp_path, position
):
    actor = main_actor([[]], show_actions=True)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'E11 F7 actual clipped or virtualized member is revealed without broadening mutation'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    wait_positive_tab(actor, 'appBar.tab.analysis')
    actor.command('click', name='appBar.tab.analysis')
    eligible = {
        row['path']: row
        for row in actor.last['ui']['project']['parameters']
        if row['refinable'] and row['fit_blocker'] == 0 and row['dependence'] == 0
    }
    table = control_expression('parameters.list')
    qml(actor, f'{table}.sourceModel.clearFilters()')
    controls = actor.last['ui']['controls']
    exposed = {row['parameter_path'] for row in controls if row['exposed']}
    if position == 'offscreen':
        target = next(row for path, row in reversed(list(eligible.items())) if path not in exposed)
    else:
        row = next(row for row in controls if row['exposed'] and row['parameter_path'] in eligible)
        qml(actor, f'{table}.contentY += {row["height"] / 2}')
        controls = actor.last['ui']['controls']
        target_control = next(
            row
            for row in controls
            if row['parameter_path'] in eligible and row['exposed'] and not row['fully_exposed']
        )
        target = eligible[target_control['parameter_path']]
    before = actor.last['ui']['project']['parameters']
    actor.configure_turns([
        [
            tool_call(
                'set_free',
                'actual-revealed-target',
                flags=[{'path': target['path'], 'free': not target['free']}],
            )
        ]
    ])
    actor.connect()
    actor.request()
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle')
    native_result(actor.responses()[0])
    after = {row['path']: row for row in actor.last['ui']['project']['parameters']}
    assert after[target['path']]['free'] is not target['free'], (
        'E11 F7 actual clipped or virtualized member is revealed without broadening mutation'
    )
    assert all(after[row['path']] == row for row in before if row['path'] != target['path']), (
        'Real row reveal changes only the original requested member'
    )
    assert any(
        row['parameter_path'] == target['path'] and row['exposed']
        for row in actor.last['ui']['controls']
    ), 'The actual native ON route realizes and exposes its originally virtualized target'


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_empty_current_session_uses_normal_create_load_and_current_save(main_actor, tmp_path, show_actions):
    actor = main_actor([[]], show_actions=show_actions)
    initial = actor.last['ui']
    assert not initial['project'], (
        'Normal app Create starts from the actual empty current Session without a seeded project'
    )
    environment = initial['environment']
    documents = Path(environment['documents_root'])
    assert documents == Path(environment['temporary_documents_root']) and documents.is_dir(), (
        'Normal Create uses the isolated ordinary OS Documents parent without real-user writes'
    )
    project_name = 'e11_native_' + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    project_title = 'Independent published-cell continuation'
    project_description = 'Native Create followed by selected CIF import and ordinary current Save'
    assert re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_\-.]{1,30}', project_name), (
        'The autonomous Create fixture supplies a valid name under the unchanged original dialog validator'
    )
    destination = documents / project_name
    assert not destination.exists(), (
        'The native ordinary Create action owns creating its previously absent project destination'
    )
    offered = {row['name']: row for row in actor.command('tool_specs')['reply']['tools']}
    schema = offered['create_project']['inputSchema']
    assert set(schema['required']) == {'purpose'} and set(schema['properties']) == {
        'purpose', 'name', 'title', 'description'
    }, 'Normal current-session Create exposes the complete ordinary project metadata contract'
    cif = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    actor.connect()
    token = qml(actor, 'Session.assistant.beginFileSelection(true)')
    assert actor.command('selected_add', token=token, paths=[str(cif)])['reply']['added'], (
        'The empty current Session admits the genuine published selected CIF before native Create'
    )
    selected = actor.last['ui']['selected_files']
    assert len(selected) == 1 and selected[0]['id'], (
        'Native Create and subsequent import retain the actually admitted selected-input identity'
    )
    actor.configure_turns([[
        tool_call('create_project', 'ordinary-empty-create', name=project_name, title=project_title,
                  description=project_description),
        tool_call('load_structure', 'ordinary-created-cif', file_id=selected[0]['id']),
        tool_call('save_project', 'ordinary-created-current-save', destination='current'),
    ]])
    actor.connect()
    actor.command('clear_ui_sequence')
    actor.request('Create a new project, import the attached CIF and save it.')
    actor.until(lambda row: len(actor.responses()) == 3 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    outcomes = [native_result(response) for response in actor.responses()]
    created = outcomes[0]
    assert (created['status'] == 'created' and created['adopted'] and created['complete']
            and created['presentation_complete'] and created['saved'] is True
            and created['name'] == project_name and Path(created['path']) == destination
            and created['title'] == project_title and created['description'] == project_description), (
        'Normal Create reports actual adopted current-owner completion and its immediately saved destination'
    )
    assert actor.last['ui']['singleton_identity'] and actor.last['ui']['engine_parent'], (
        'Create, Load and Save retain the one actual current Main engine-owned Session'
    )
    events = actor.last['ui']['ui_sequence']
    before_adoption = []
    for event in events:
        if event['project_present']:
            break
        before_adoption.append(event)
    if show_actions:
        pointers = [row for row in before_adoption if row['kind'].startswith('pointer_')]
        assert pointers and all(not row['assistant_visible'] and row['create_visible']
                                and row['create_exposed'] for row in pointers), (
            'Show ON exposes the actual normal Project control and hides Assistant before locating or cueing Create'
        )
        # FIRST77 Main.qml175 defines assistantSelected as the return/preference
        # icon state. It may stay true while native presentation hides Assistant.
        # Preserve that observation and check its documented formula separately.
        assert qml(actor, 'assistantToggle.assistantSelected === (assistantPanel.shown || '
            '(Session.assistant.showingActions && Preferences.assistantShown))'), (
            'The original selected-bit observation retains its documented return/preference icon semantics'
        )
        assert any(row['kind'] == 'mouse_press' and row.get('create_contains_press')
                   and not row['dialog_visible'] for row in before_adoption), (
            'Show ON actually clicks the original normal-sidebar Create control before popup input'
        )
        assert any(row['dialog_visible'] and row['kind'] in {'key_press', 'input_method'}
                   and row['focus'] == 'createProject.name' for row in before_adoption), (
            'Show ON enters the original Create dialog through its genuine focused name control'
        )
        for field in ('createProject.title', 'createProject.description'):
            assert any(row['dialog_visible'] and row['kind'] in {'key_press', 'input_method'}
                       and row['focus'] == field for row in before_adoption), (
                'Show ON enters each supplied metadata field through its actual original dialog editor'
            )
        assert any(row['kind'] == 'mouse_press' and row['dialog_visible']
                   and row['dialog_name'] == project_name
                   and row['dialog_title'] == project_title
                   and row['dialog_description'] == project_description
                   and row.get('confirm_contains_press')
                   for row in before_adoption), (
            'Show ON confirms the actual original Create popup before ordinary Session adoption'
        )
    else:
        assert before_adoption and all(not row['kind'].startswith('pointer_')
            and not row['dialog_visible'] and row['assistant_preference'] for row in before_adoption), (
            'Show OFF keeps assistant presentation unchanged before ordinary project adoption'
        )
    owner = actor.last['ui']['project']
    assert owner['name'] == project_name and Path(owner['path']) == destination, (
        'Normal native Create retains its actual requested name and ordinary Documents destination'
    )
    assert qml(actor, 'Session.project.title') == project_title and qml(
        actor, 'Session.project.description') == project_description, (
        'The actual ordinary owner retains supplied title and description after native Create and Save'
    )
    assert (destination / 'project.edi').is_file(), (
        'Native ordinary Create and current Save write the actual owned project rather than a receipt only'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    rows = actor.last['ui']['project']['structure_rows']
    imported = [row for row in rows if row['length_a'] == 3.20927 and row['length_c'] == 5.21033]
    assert len(imported) == 1 and imported[0]['gamma'] == 120, (
        'The actual native CIF import preserves independent COD9008506 cell facts after normal Create'
    )
    assert imported[0]['sites'], 'The published native CIF contributes actual sites after ordinary Create'
    assert json.loads(actor.last['ui']['context'])['datasets'] == [], (
        'The original Create CIF Save sequence retains its actual partial state without silently adding science'
    )
    assert not actor.command('open', path=str(destination))['reply']['opened'] and (
        'project has no experiments/*.edi' in qml(actor, 'Session.lastError')), (
        'Ordinary whole-project Open retains the documented dev completeness refusal for this saved partial state'
    )
    assert actor.last['ui']['project']['structure_rows'] == rows, (
        'The actual incomplete-Open refusal preserves all native imported structure values and identities'
    )
    # Explicit separate prerequisite, owner interpretation69121c6c2: no observed
    # measurements are invented to make an isolated structure reopenable.
    actor.append_turn([tool_call('create_experiment', 'explicit-structure-persistence-simulation')])
    actor.request('For this separate persistence check add one ordinary calculation-only experiment; add no measured data.')
    actor.until(lambda row: len(actor.responses()) == 4 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    native_result(actor.responses()[-1])
    actor.until(lambda row: not row['ui']['project']['calculating'])
    simulation = json.loads(actor.last['ui']['context'])['datasets'][0]
    assert simulation['calculation_only'] and simulation['axis']['count'] > 0 and (
        simulation['observations']['intensity_count'] == 0), (
        'The explicit whole-project prerequisite is a real ordinary simulation grid, not fabricated observations'
    )
    flags = [(row['path'], row['free'], row['dependence']) for row in actor.last['ui']['project']['parameters']]
    assert actor.command('save')['reply']['saved'], (
        'The ordinary owner saves the explicitly complete calculation-only project after retaining partial-stage evidence'
    )
    assert actor.command('open', path=str(destination))['reply']['opened'], (
        'Independent ordinary Open reads the genuinely complete simulation project from its real saved destination'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert actor.last['ui']['project']['structure_rows'] == rows, (
        'Normal current Save conserves every original imported structure value through complete ordinary reopen'
    )
    assert [(row['path'], row['free'], row['dependence']) for row in actor.last['ui']['project']['parameters']] == flags, (
        'The separate complete-project readback preserves the actual simulation parameter membership and free/dependent flags'
    )

    assert qml(actor, 'Session.project.title') == project_title and qml(
        actor, 'Session.project.description') == project_description, (
        'Independent ordinary reopen reads the actually saved title and description without receipt derivation'
    )


def test_fresh_actual_main_has_no_startup_report_capacity_failure(main_actor):
    actor = main_actor([[]])
    assert not actor.last['ui']['project'], (
        'The independent startup-report check observes the actual empty current Main Session'
    )
    diagnostics = {key: actor.last['ui'][key] for key in ('last_error', 'messages')}
    assert 'report_capacity' not in json.dumps(diagnostics), (
        'Optional diagnostic setup cannot emit a report-capacity failure before any assistant work'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_ordinary_empty_to_created_transition_retains_original_task_and_approved_inputs(
    main_actor, tmp_path, show_actions
):
    actor = main_actor([[]], show_actions=show_actions)
    assert not actor.last['ui']['project'], (
        'The ordinary manual Create continuity witness starts with the actual empty Session'
    )
    files = [ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif',
             ROOT / 'tests/fixtures/background_estimate/meas-lbco-hrpt.xye']
    actor.connect()
    token = qml(actor, 'Session.assistant.beginFileSelection(true)')
    assert actor.command('selected_add', token=token, paths=list(map(str, files)))['reply']['added'], (
        'The pending original task admits its real selected inputs before ordinary project creation'
    )
    manifest = actor.last['ui']['selected_files']
    assert len(manifest) == 2, 'The original task owns both selected scientific inputs'
    cif_id = next(row['id'] for row in manifest if row['name'] == files[0].name)
    expected_text = files[0].read_text(encoding='utf-8')
    actor.configure_turns([[], [tool_call('read_selected_file', 'after-ordinary-create',
        file_id=cif_id, offset=0, max_bytes=len(files[0].read_bytes()))]])
    original = ('Create and save a new project using the attached files. One phase, NPD, '
                'wavelength 1.49 Å. Refine the structure and show the report.')
    actor.connect()
    actor.request(original)
    actor.until(lambda row: row['ui']['state'] == 'idle' and FINAL in json.dumps(row['ui']['messages']))
    before = actor.last['ui']['messages']
    assert original in json.dumps(before, ensure_ascii=False), (
        'The original complete scientific objective is retained before the ordinary Create action'
    )
    actor.command('click', name='assistant.toggle')
    actor.command('click', name='project.create')
    actor.until(lambda row: any(c['name'] == 'createProject.name' and c['visible']
                               for c in row['ui']['controls']))
    name = 'e11_manual_' + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    assert re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_\-.]{1,30}', name), (
        'The ordinary manual Create continuity fixture preserves unchanged native name validation'
    )
    actor.command('click', name='createProject.name')
    actor.command('manual_key', key='select_all')
    actor.command('manual_text', text=name)
    actor.command('dialog_ok', name='createProject.dialog')
    actor.until(lambda row: row['ui']['project'].get('name') == name)
    after = actor.last['ui']
    assert original in json.dumps(after['messages'], ensure_ascii=False), (
        'Ordinary empty-to-created replacement retains the full prior task rather than chat decoration alone'
    )
    assert after['selected_files'] == manifest, (
        'The same pending task retains its genuinely admitted attachment manifest across ordinary Create'
    )
    actor.command('click', name='assistant.toggle')
    actor.request('Continue the original request.')
    actor.until(lambda row: len(actor.responses()) == 1 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    readback = native_result(actor.responses()[0])
    assert any(value == expected_text for row in objects(readback) for value in row.values()
               if isinstance(value, str)), (
        'The actual new native Controller can read the retained approved file bytes, not just display its manifest'
    )
    wire = list(map(json.loads, actor.trace.read_text().splitlines()))
    turns = [row['params'] for row in wire if row.get('method') == 'turn/start']
    assert len(turns) == 2, 'The actual followup continues after the original task and ordinary Create'
    if turns[0]['threadId'] != turns[1]['threadId']:
        assert original in json.dumps(turns[1], ensure_ascii=False), (
            'A replacement provider thread receives the original objective rather than only the word Continue'
        )
    visible_inputs = turns if turns[0]['threadId'] == turns[1]['threadId'] else [turns[1]]
    actual_context = json.dumps(visible_inputs, ensure_ascii=False)
    assert all(path.name in actual_context for path in files), (
        'The actual provider followup can see the retained scientific input manifest after ordinary Create'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_native_fit_uses_current_statusbar_owner_from_structure_page(main_actor, tmp_path, show_actions):
    actor = main_actor([[tool_call('run_fit', 'actual-current-status-fit')]], show_actions=show_actions)
    path = tmp_path / 'fit-project'
    shutil.copytree(ROOT / 'tests/fixtures/fit_quality/uncertainty', path)
    assert actor.command('open', path=str(path))['reply']['opened'], (
        'The independent finite polynomial fixture opens through the actual current app owner'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    wait_positive_tab(actor, 'appBar.tab.structure')
    actor.command('click', name='appBar.tab.structure')
    actor.until(lambda row: any(c['name'] == 'statusBar.fit.button' and c['visible'] and c['enabled'] and c['exposed'] for c in row['ui']['controls']))
    controls = actor.last['ui']['controls']
    current = [row for row in controls if row['name'] == 'statusBar.fit.button']
    assert len(current) == 1 and current[0]['visible'] and current[0]['enabled'] and current[0]['exposed'], (
        'The one current dev status-bar Fit control is actually reachable outside the Analysis page'
    )
    assert not any(row['name'] == 'fitting.start' and row['visible'] for row in controls), (
        'Native fitting must not require or restore a duplicate obsolete sidebar Fit target'
    )
    assert qml(actor, 'Session.project.fit.available'), (
        'The independent fixture has real native free variables and measured observations before fitting'
    )
    before = actor.last['ui']['project']['parameters']
    actor.connect()
    actor.command('clear_ui_sequence')
    if show_actions:
        assert qml(actor,r'''(function(){const o=Qt.createQmlObject('import QtQuick; Item {objectName:"e11.fit.physical.sidebar";property var rows:[];property var cue:null;}',contentItem);o.cue=function(position){const page=window.assistantWorkflowPage;const seek=function(item){if(!item)return null;if(item.objectName==="sideBar.tab.basic")return item;for(const child of item.children||[]){const found=seek(child);if(found)return found;}return null;};const tab=seek(page);const point=tab?tab.mapToItem(contentItem,0,0):null;o.rows=o.rows.concat([{assistant_visible:assistantPanel.visible,logical_selected:assistantToggle.assistantSelected,formula_correct:assistantToggle.assistantSelected===(assistantPanel.shown||(Session.assistant.showingActions&&Preferences.assistantShown)),normal_exposed:!!page&&page.current&&page.enabled&&!!tab&&tab.visible&&tab.enabled&&point.x>=0&&point.y>=0&&point.x+tab.width<=contentItem.width&&point.y+tab.height<=contentItem.height}]);};Session.assistant.actionPointerMoved.connect(o.cue);return true;})()'''), (
            'The same Main observer reads physical normal controls and the original logical preference formula at the real Fit cue'
        )
    actor.request('Fit the current independent polynomial background using its existing free parameters.')
    actor.until(lambda row: len(actor.responses()) == 1 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    native_result(actor.responses()[0])
    assert qml(actor, 'Session.project.fit.canUndo'), (
        'The current native Fit owner actually adopts one result and owns its ordinary Undo'
    )
    after = actor.last['ui']['project']['parameters']
    assert any(a['value'] != b['value'] for a, b in zip(before, after, strict=True)), (
        'The registered native Fit produces actual changed scientific values, not a control-only success'
    )
    if show_actions:
        pointers = [row for row in actor.last['ui']['ui_sequence'] if row['kind'].startswith('pointer_')]
        assert pointers and all(not row['assistant_visible'] for row in pointers), (
            'The Show ON Fit operation physically hides Assistant before current-control presentation'
        )
        physical=qml(actor,'('+control_expression('e11.fit.physical.sidebar')+').rows')
        assert physical and all(row['normal_exposed'] and not row['assistant_visible'] and row['formula_correct'] for row in physical), (
            'Real current normal controls are exposed at every Fit cue while the retained selected-bit observation follows its original return/preference formula'
        )
        qml(actor,'(function(){const o='+control_expression('e11.fit.physical.sidebar')+';Session.assistant.actionPointerMoved.disconnect(o.cue);o.destroy();})()')
    assert not any('Local work report saved' in row['display'] for row in actor.last['ui']['texts'] if row['visible']), (
        'Automatic diagnostics remain written without unsolicited visible chat or footer status chatter'
    )
    actor.command('undo')
    assert [row['value'] for row in actor.last['ui']['project']['parameters']] == [row['value'] for row in before], (
        'One ordinary Undo restores the exact pre-fit scientific parameter values'
    )


def test_internal_transport_unlimited_clock_waits_and_bounded_control_deadlines(main_actor):
    actor = main_actor([[]])
    checks = actor.command('transport_clock')['reply']['checks']
    required = {'active_task_has_no_day_expiry', 'unlimited_native_work_accepted',
                'unlimited_native_presentation_wait_accepted', 'unlimited_human_wait_accepted',
                'native_identity_guard_retained', 'human_identity_guard_retained',
                'overlapping_unlimited_waits_do_not_expire', 'retired_generation_cannot_resume_wait',
                'individual_protocol_deadline_remains_bounded', 'explicit_short_deadline_positive_control'}
    assert required <= checks.keys() and all(checks.values()), (
        'Finite internal transport clock injection preserves unlimited active work, real wait correlation and bounded individual protocol controls'
    )


def test_actual_generic_submission_is_unlimited_and_stop_remains_usable(main_actor):
    actor = main_actor([[]], hold_final=True)
    actor.connect()
    actor.request('Continue the delegated app task while awaiting the next actual observation.')
    actor.until(lambda row: row['ui']['state'] == 'agent_active' and row['ui']['can_cancel'])
    timing = actor.command('transport_timing')['reply']
    assert timing['active'] and timing['total_ms'] == 0 and timing['idle_ms'] == 0, (
        'The actual generic VM submission, not a manufactured transport role, uses unlimited idle and total task budgets'
    )
    assert not timing['expired_after_day'], (
        'A finite future clock sample cannot expire the real held assistant task'
    )
    actor.command('cancel')
    actor.until(lambda row: not row['ui']['can_cancel'] and row['ui']['state'] != 'agent_active')
    assert actor.last['ui']['connected'], (
        'Explicit Stop settles the actual work while preserving the same signed-in account'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_native_single_crystal_extinction_matches_current_selectors_and_direct_mm_descriptor(
    main_actor, tmp_path, show_actions
):
    actor = main_actor([[]], show_actions=show_actions)
    project = tmp_path / 'sc-extinction'
    shutil.copytree(ROOT / 'docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_basic/project', project)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'The independently published SC fixture opens through the current ordinary owner'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    before = actor.last['ui']['project']['parameters']
    context = json.loads(actor.last['ui']['context'])['datasets'][0]
    expected = ['none', 'becker-coppens-type-1', 'becker-coppens-type-2',
                'becker-coppens-mixed', 'larson-isotropic', 'larson-anisotropic']
    ordinary = qml(actor, '(function(){const m=Session.project.currentExperiment.extinctionTypeOptions;'
                   'return Array.from({length:m.count},(_,i)=>m.tokenAt(i));})()')
    assert context['extinction_type_options'] == ordinary == expected, (
        'SC native context matches the unchanged ordinary six-family extinction selector contract'
    )
    distributions = qml(actor, '(function(){const m=Session.project.currentExperiment.mosaicDistributionOptions;'
                        'return Array.from({length:m.count},(_,i)=>m.tokenAt(i));})()')
    assert context['extinction_type'] == 'none' and context['mosaic_distribution_options'] == distributions == [], (
        'The ordinary none family has no applicable mosaic choices before a supported family is selected'
    )
    experiment = context['id']
    choices = [token for token in expected if token != context['extinction_type']]
    actor.configure_turns([[tool_call('edit_experiment', 'sc-family-' + str(i),
        experiment=experiment, operation='extinction_type', value=token)] for i,token in enumerate(choices)])
    actor.connect()
    for index, token in enumerate(choices):
        actor.request('Select the requested supported extinction family through its ordinary app owner.')
        actor.until(lambda row: len(actor.responses()) == index + 1 and row['ui']['state'] == 'idle', visible_progress=show_actions)
        native_result(actor.responses()[-1])
        assert qml(actor, 'Session.project.currentExperiment.extinctionType') == token, (
            'The registered SC family action changes the actual ordinary current experiment'
        )
        actor.command('undo')
        actor.until(lambda row: not row['ui']['project']['calculating'])
        assert qml(actor, 'Session.project.currentExperiment.extinctionType') == context['extinction_type'], (
            'One ordinary Undo restores the exact original SC extinction family'
        )
        assert actor.last['ui']['project']['parameters'] == before, (
            'SC family Undo preserves original parameter membership, values, free flags and eligibility'
        )
    # A separate actor supplies the owner-requested value as input, never as an algorithm default.
    scalar = main_actor([[]], show_actions=show_actions)
    assert scalar.command('open', path=str(project))['reply']['opened'], (
        'Direct millimetre editing uses the same independent SC input through a new real owner'
    )
    scalar.until(lambda row: not row['ui']['project']['calculating'])
    qml(scalar, 'Session.project.currentExperiment.extinctionType="becker-coppens-mixed"')
    scalar.until(lambda row: not row['ui']['project']['calculating'])
    radius = next(row for row in scalar.last['ui']['project']['parameters']
                  if row['category'] == 'extinction' and row['field'] == 'crystal_radius')
    assert not radius['refinable'] and not radius['free'], (
        'The original current-dev crystal-radius descriptor remains never fitted'
    )
    distributions = qml(scalar, '(function(){const m=Session.project.currentExperiment.mosaicDistributionOptions;'
                        'return Array.from({length:m.count},(_,i)=>m.tokenAt(i));})()')
    assert distributions == ['gaussian', 'lorentzian'], (
        'The applicable mixed family preserves the two original ordinary mosaic distribution tokens'
    )
    original_distribution = qml(scalar, 'Session.project.currentExperiment.mosaicDistribution')
    changed_distribution = next(token for token in distributions if token != original_distribution)
    scalar.configure_turns([[
        tool_call('edit_experiment', 'current-sc-distribution', experiment=experiment,
                  operation='mosaic_distribution', value=changed_distribution),
        tool_call('set_parameters', 'direct-mm-input', values=[{'path': radius['path'], 'value': 3.0}]),
    ]])
    scalar.connect()
    scalar.request('Set the crystal size field directly to 3 mm and keep it fixed.')
    scalar.until(lambda row: len(scalar.responses()) == 2 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    for response in scalar.responses():
        native_result(response)
    assert qml(scalar, 'Session.project.currentExperiment.mosaicDistribution') == changed_distribution, (
        'The native SC distribution action reaches the actual ordinary current selector'
    )
    actual = next(row for row in scalar.last['ui']['project']['parameters'] if row['path'] == radius['path'])
    assert actual['value'] == 3.0 and not actual['free'] and not actual['refinable'], (
        'The actual native ordinary descriptor setter retains direct3mm without diameter halving or fitted-flag changes'
    )
    scalar.command('undo')
    restored = next(row for row in scalar.last['ui']['project']['parameters'] if row['path'] == radius['path'])
    assert restored['value'] == radius['value'] and restored['free'] == radius['free'], (
        'One ordinary Undo restores the original crystal descriptor exactly'
    )
    scalar.command('undo')
    assert qml(scalar, 'Session.project.currentExperiment.mosaicDistribution') == original_distribution, (
        'One separate ordinary Undo restores the original mosaic selector token'
    )


def test_sc_raw_columns_invalidate_only_actual_input_consent_and_cache(main_actor, tmp_path):
    reached = set()
    for name in ['sc-neut-cwl_tb2ti2o7-heidi_basic', 'sc-neut-tof_taurine-unknown_basic']:
        actor = main_actor([[]])
        path = tmp_path / name
        shutil.copytree(ROOT / 'docs/user/cli' / name / 'project', path)
        assert actor.command('open', path=str(path))['reply']['opened'], (
            'The raw-input scope witness uses genuinely published CW and TOF SC observations'
        )
        actor.until(lambda row: not row['ui']['project']['calculating'])
        actor.connect()
        original_context = json.loads(actor.last['ui']['context'])
        original_revision = original_context['project']['revision']
        original_files = actor.last['ui']['selected_files']
        baseline = actor.command('sc_input')['reply']
        assert baseline['rectangular'] and baseline['sample_form'] == 'single crystal', (
            'The independent measured fixture is rectangular native single-crystal input'
        )
        for field, facts in baseline['columns'].items():
            assert facts['element_bytes'] == (4 if field in {'h', 'k', 'l'} else 8), (
                'Native SC identity accounts actual int32 Miller and float64 measured columns'
            )
            if not facts['count']:
                assert field == 'wavelength', 'Only CW per-reflection wavelength is absent'
                continue
            actor.command('sc_input', mode='equal', field=field)
            assert not actor.last['ui']['context_consent_required'], (
                'An equal native column replacement retains the same approved raw scientific bytes'
            )
            old = facts['first']
            new = old + ((17 if old >= 0 else -17) if field in {'h', 'k', 'l'} else abs(old) * 0.03125 + 0.125)
            changed = actor.command('sc_input', mode='column', field=field, value=new)['reply']
            assert changed['rectangular'] and changed['columns'][field]['count'] == facts['count'], (
                'The native mutation is a real same-shape measured-input change'
            )
            assert changed['columns'][field]['first'] == new, (
                'The actual independent raw field changes before testing disclosure invalidation'
            )
            now = json.loads(actor.last['ui']['context'])
            assert now['project']['revision'] == original_revision and actor.last['ui']['selected_files'] == original_files, (
                'No unrelated revision or selected-file change can mask the SC raw-input identity witness'
            )
            assert actor.last['ui']['context_consent_required'], (
                'Every changed SC measured column invalidates the actual approved input scope and cached disclosure'
            )
            actor.command('sc_input', mode='column', field=field, value=old)
            assert not actor.last['ui']['context_consent_required'], (
                'Restoring exact original raw bytes restores the original unchanged disclosure approval'
            )
            reached.add(field)
        field = 'intensity'
        old = baseline['columns'][field]['first']
        actor.command('sc_input', mode='replace', field=field, value=old + 0.375)
        assert actor.last['ui']['context_consent_required'], (
            'Replacing the complete native reflection owner cannot reuse a stale borrowed input stamp'
        )
        actor.command('sc_input', mode='column', field=field, value=old)
        assert not actor.last['ui']['context_consent_required'], (
            'A restored native reflection owner remains the original approved measured input'
        )
        actor.command('sc_input', mode='column', field='computed', value=0.73125)
        assert not actor.last['ui']['context_consent_required'], (
            'Calculated reflection values are not promoted into measured-input authority'
        )
        actor.command('sc_input', mode='column', field='sample_form', value='powder')
        assert actor.last['ui']['context_consent_required'], (
            'Declared sample form is actual disclosure identity even when all raw columns are unchanged'
        )
        assert json.loads(actor.last['ui']['context'])['datasets'][0]['sample_form'] == 'powder', (
            'The actual cached context refreshes its declared sample form rather than only an approval flag'
        )
        actor.command('sc_input', mode='column', field='sample_form', value='single crystal')
        assert not actor.last['ui']['context_consent_required'], (
            'Restoring the original declared sample form restores the original input scope'
        )
    assert reached == {'h', 'k', 'l', 'intensity', 'sigma', 'wavelength'}, (
        'The finite genuine CW and TOF witnesses reach every typed measured reflection channel'
    )


def test_result_projection_size_matches_real_wire_for_every_closed_code_and_message_shape(main_actor):
    actor = main_actor([[]])
    # Independent protocol vocabulary retained from d2, not a digest/value emitted by the changed projector.
    codes = ['refused', 'unavailable', 'cancelled', 'uncertain', 'resource_exhausted',
             'input_changed', 'policy_mismatch', 'request_stale', 'context_unready',
             'owner_unavailable', 'pending_operation', 'item_mismatch', 'duplicate_call',
             'invalid_arguments', 'calculation_busy', 'visible_unmapped', 'project_required',
             'unclassified', 'owner_retired', 'retention_blocked', 'attachments_clear',
             'publication_paused', 'account_unready', 'owner_retiring', 'consent_revoked',
             'history_unretained', 'agent_interrupted', 'context_pending', 'history_clearing',
             'question_pending', 'selection_pending', 'input_staging']
    escaped = 'Bounded app message: quote" backslash\\ newline\n tab\t Ω 𝛌'
    cases = [{'source': {'status': 'refused', 'code': code, 'message': escaped}} for code in codes]
    cases += [{'source': {'status': status, 'message': escaped}} for status in
              ['refused', 'unavailable', 'error', 'cancelled', 'interrupted', 'superseded',
               'unconfirmed', 'applied_unconfirmed', 'complete']]
    cases += [{'source': {'status': 'refused', 'code': None, 'message': None}},
              {'source': {'status': 'refused', 'code': {'unknown': True}, 'message': escaped}},
              {'role': 'diagnostic', 'source': {'code': 'native_diagnostic', 'message': escaped}}]
    valid_count = len(cases)
    cases += [{'source': {'status': 'refused', 'message': value}} for value in [True, {}, []]]
    actual = actor.command('outgoing_projection_cases', cases=cases)['reply']['cases']
    assert len(actual) == len(cases), 'The finite projector witness reaches every supplied result shape'
    for source, result in zip(cases[:valid_count], actual[:valid_count], strict=True):
        assert not result['rejected'], 'Each legal closed result can be counted and materialized'
        wire = result['wire'].encode('utf-8')
        assert result['size'] == result['wire_bytes'] == len(wire), (
            'The admission count equals actual compact QJson UTF8 wire bytes with one code owner'
        )
        decoded = json.loads(result['wire'])
        assert decoded == result['projected'], 'Materialized native JSON is the actual measured wire object'
        assert decoded.get('message') == source['source']['message'], (
            'Bounded human app messages, nulls and escaped Unicode survive the actual outgoing role'
        )
        if source.get('role') == 'diagnostic':
            assert decoded['code'] == 'native_diagnostic', 'Diagnostic code retains its separate original field owner'
        elif 'code' in decoded:
            assert decoded['code'] in codes and result['wire'].count('"code":') == 1, (
                'Explicit and derived native result codes occur once and remain in the closed protocol vocabulary'
            )
    assert all(row['rejected'] for row in actual[valid_count:]), (
        'Malformed message types refuse concretely instead of changing byte identity or retiring an account'
    )


def test_empty_create_actor_prelude_reaches_connection_before_selected_file_admission():
    # This guards the demonstrated wrong-function edit class in the test carrier:
    # checking an earlier similar fixture did not prove the actually selected node.
    import ast
    tree = ast.parse(Path(__file__).read_text(encoding='utf-8'))
    target = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                  and node.name == 'test_empty_current_session_uses_normal_create_load_and_current_save')
    calls = sorted((node for node in ast.walk(target) if isinstance(node, ast.Call)),
                   key=lambda node: (node.lineno, node.col_offset))
    connected = [node.lineno for node in calls if isinstance(node.func, ast.Attribute)
                 and node.func.attr == 'connect']
    admitted = [node.lineno for node in calls if isinstance(node.func, ast.Attribute)
                and node.func.attr == 'command' and node.args
                and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'selected_add']
    assert len(admitted) == 1 and connected and connected[0] < admitted[0], (
        'The exact executed empty-Create node establishes real connection before approved file admission'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_refused_empty_create_prefix_settles_load_and_save_without_account_loss(
    main_actor, show_actions
):
    actor = main_actor([[]], show_actions=show_actions)
    actor.connect()
    cif = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    token = qml(actor, 'Session.assistant.beginFileSelection(true)')
    assert actor.command('selected_add', token=token, paths=[str(cif)])['reply']['added'], (
        'The refused-prefix continuation retains a genuinely admitted native CIF input'
    )
    file_id = actor.last['ui']['selected_files'][0]['id']
    documents = Path(actor.last['ui']['environment']['documents_root'])
    name = 'e11_existing_destination'
    collision = documents / name
    collision.mkdir()
    marker = collision / 'independent-existing-bytes'
    original = b'Existing destination is not an adopted scientific project.\x00\xff'
    marker.write_bytes(original)
    # This is an intentional refusal fixture, never an autonomous live setup.
    actor.configure_turns([[
        tool_call('create_project', 'refused-create-prefix', name=name,
                  title='Must not overwrite an existing destination', description='Negative fixture'),
        tool_call('load_structure', 'load-after-refused-create', file_id=file_id),
        tool_call('save_project', 'save-after-refused-create', destination='current'),
    ], [tool_call('inspect_project', 'still-current-no-project')]])
    actor.request('Try the requested new-project name, then report the actual current Save outcome.')
    actor.until(lambda row: len(actor.responses()) == 3 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    responses = actor.responses()
    assert all(not row['result']['success'] for row in responses), (
        'Refused Create and subsequent no-project Save each settle their original actual provider call'
    )
    create, load, save = [json.loads(row['result']['contentItems'][0]['text']) for row in responses]
    assert not create.get('adopted') and not actor.last['ui']['project'], (
        'Existing-folder Create refusal cannot fabricate adoption or a project for subsequent Save'
    )
    assert load['code'] == 'project_required', (
        'Default native CIF import after refused Create reports the actual missing current project'
    )
    assert save['code'] == 'project_required' and isinstance(save['message'], str) and save['message'], (
        'The no-project Save refusal has a real closed code and model-visible bounded diagnostic'
    )
    assert marker.read_bytes() == original and list(collision.iterdir()) == [marker], (
        'The refused ordinary Create preserves every planted destination byte without overwrite or side effects'
    )
    assert actor.last['ui']['connected'] and not actor.last['ui']['can_cancel'], (
        'Native refusal encoding cannot retire the account or strand a pending provider reply'
    )
    actor.request('Inspect the actual current state without clearing the conversation.')
    actor.until(lambda row: len(actor.responses()) == 4 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    final = actor.responses()[-1]['result']
    assert not final['success'] and json.loads(final['contentItems'][0]['text'])['code'] == 'project_required', (
        'A later actual request remains usable after the refusal prefix without stale reply replay'
    )
    wire = list(map(json.loads, actor.trace.read_text().splitlines()))
    requests = [row for row in wire if row.get('method') == 'turn/start']
    assert len(requests) == 2 and requests[0]['params']['threadId'] == requests[1]['params']['threadId'], (
        'Ordinary refused actions preserve the actual original conversation rather than silently replacing it'
    )


def test_valid_large_stream_reaches_native_continuation_without_work_quota_logout(main_actor, tmp_path):
    # Finite test input crosses the former cumulative8192 event/4MiB retained
    # boundaries. These are provenance for the escape, never new product budgets.
    chunk = 'x'
    count = 8193
    larger = 'z' * (4 * 1024 * 1024 + 257)
    actor = main_actor([[
        {'call_id': 'valid-large-message', 'message_stream': {'chunk': chunk, 'count': count}},
        {'call_id': 'valid-large-snapshot', 'message_stream': {'chunk': larger, 'count': 1}},
        tool_call('inspect_project', 'native-after-large-valid-stream'),
    ]])
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'The valid large-output witness starts from an independently saved ordinary project'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    before = actor.last['ui']['project']
    actor.connect()
    actor.request('Retain the ongoing task and inspect the current project after valid streamed output.')
    actor.until(lambda row: len(actor.responses()) == 1 and row['ui']['state'] == 'idle', seconds=90)
    native_result(actor.responses()[0])
    assert actor.last['ui']['connected'] and not actor.last['ui']['can_cancel'], (
        'Valid cumulative text/events cannot cause app logout, a retention fence or a Clear requirement'
    )
    assert actor.last['ui']['project'] == before, (
        'Large read-only work preserves the actual current scientific model and owner state'
    )
    sent = [json.loads(line) for line in actor.trace.with_suffix('.sent.jsonl').read_text().splitlines()]
    deltas = [row for row in sent if row.get('method') == 'item/agentMessage/delta']
    assert (len(deltas) == count + 1 and all(row['params']['delta'] == chunk for row in deltas[:-1])
            and deltas[-1]['params']['delta'] == larger), (
        'The offline peer actually delivers the finite valid event/text escape before native continuation'
    )
    assert len(chunk.encode()) * count + len(larger.encode()) > 4 * 1024 * 1024, (
        'The independent finite input genuinely crosses the old cumulative retained-byte boundary'
    )
    document = json.loads(qml(actor, 'Session.assistant.workReportDocument()'))
    assert 'native-after-large-valid-stream' in json.dumps(document), (
        'Useful current diagnostics remain accessible after large valid work without another provider query'
    )


def test_same_project_reconnect_resumes_original_durable_thread_files_and_cached_report(main_actor, tmp_path):
    actor = main_actor([[tool_call('inspect_project', 'before-reconnect')],
                        [tool_call('inspect_project', 'after-reconnect')]])
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'The durable same-project witness uses the actual ordinary saved owner'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    actor.connect()
    selected_path = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    token = qml(actor, 'Session.assistant.beginFileSelection(true)')
    assert actor.command('selected_add', token=token, paths=[str(selected_path)])['reply']['added'], (
        'The original durable task genuinely admits its scientific input before transport loss'
    )
    selected = actor.last['ui']['selected_files']
    config_path = actor.folder / 'peer.json'
    config = json.loads(config_path.read_text()); config['disconnect_after_turn'] = True
    config_path.write_text(json.dumps(config))
    original = 'Keep this project and attached CIF; inspect its current scientific state.'
    actor.request(original)
    actor.until(lambda row: len(actor.responses()) == 1 and not row['ui']['connected'])
    native_result(actor.responses()[0])
    model = actor.last['ui']['project']
    document = qml(actor, 'Session.assistant.workReportDocument()')
    assert 'before-reconnect' in document, (
        'The completed-step diagnostic cache survives helper termination before any new query'
    )
    # Actual ordinary Preferences -> report popup -> Copy, without asking the model.
    actor.command('click', name='appBar.button.preferences')
    actor.command('click', name='preferences.tab.aiAssistance')
    actor.command('click', name='preferences.ai.workReport')
    actor.until(lambda row: any(c['name'] == 'assistant.workReport.copy' and c['fully_exposed']
                               for c in row['ui']['controls']))
    actor.command('click', name='assistant.workReport.copy')
    clipboard = qml(actor, "(function(){const item=Qt.createQmlObject('import QtQuick; TextEdit {}',contentItem);"
                    "item.paste();const value=item.text;item.destroy();return value;})()")
    assert json.loads(clipboard) == json.loads(document), (
        'The actual Preferences report Copy button copies the retained diagnostic document'
    )
    # Close the existing modal owners through their public QML close methods.
    for name in ('assistant.workReport', 'preferences'):
        qml(actor, f'(function(){{const item={control_expression(name)};if(item&&item.close)item.close();}})()')
    config['disconnect_after_turn'] = False;config_path.write_text(json.dumps(config))
    actor.command('click', name='assistant.connection')
    actor.until(lambda row: row['ui']['connected'])
    assert not actor.last['ui']['context_consent_required'] and actor.last['ui']['selected_files'] == selected, (
        'Actual same-project Connect resumes the unchanged approved task/files without Clear or new consent'
    )
    assert actor.last['ui']['project'] == model, (
        'Recoverable reconnection preserves current scientific state without replaying earlier native actions'
    )
    actor.request('Continue the same original task and inspect the current project.')
    actor.until(lambda row: len(actor.responses()) == 2 and row['ui']['state'] == 'idle')
    native_result(actor.responses()[1])
    wire = list(map(json.loads, actor.trace.read_text().splitlines()))
    starts = [row['params'] for row in wire if row.get('method') == 'thread/start']
    resumes = [row['params'] for row in wire if row.get('method') == 'thread/resume']
    turns = [row['params'] for row in wire if row.get('method') == 'turn/start']
    assert len(starts) == 1 and starts[0]['ephemeral'] is False, (
        'A resumable actual provider thread is durable from its original thread/start request'
    )
    assert len(resumes) == 1 and resumes[0]['threadId'] == turns[0]['threadId'] == turns[1]['threadId'], (
        'Recovery uses the supported actual original thread ID rather than a fresh thread disguised as resume'
    )
    assert resumes[0].get('excludeTurns') is True and not resumes[0].get('history') and not resumes[0].get('path'), (
        'Recovery uses the pinned threadId metadata resume contract without fabricated history hydration'
    )
    assert original in json.dumps(actor.last['ui']['messages'], ensure_ascii=False), (
        'The original natural task remains visible after genuine same-thread transport recovery'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_fresh_native_experiment_selects_real_sample_form_before_reflection_import(main_actor, tmp_path, show_actions):
    actor = main_actor([[]], show_actions=show_actions)
    actor.connect()
    attachment_root = Path('/home/andrewsazonov/.codex/attachments/f8212720-2fab-4f66-b3ce-a5c0ebb9c72c')
    retained = tmp_path / 'retained-sc-inputs'; retained.mkdir()
    for name in ('tbti.cif', 'heidi.dat'):
        shutil.copyfile(attachment_root / name, retained / name)
        assert hashlib.sha256((retained / name).read_bytes()).digest() == hashlib.sha256(
            (attachment_root / name).read_bytes()).digest(), (
            'The selected fixture retains exact genuinely supplied SC bytes without changing scientific input'
        )
    cif, measured = retained / 'tbti.cif', retained / 'heidi.dat'
    expected = [list(map(float, line.split())) for line in measured.read_text().splitlines() if line.strip()]
    assert expected and all(len(row) == 5 for row in expected), (
        'The independent supplied reflection input has actual h k l intensity sigma rows'
    )
    token = qml(actor, 'Session.assistant.beginFileSelection(true)')
    assert actor.command('selected_add', token=token, paths=[str(cif), str(measured)])['reply']['added'], (
        'Fresh native SC routing starts from genuinely admitted original CIF and reflection files'
    )
    ids = {row['name']: row['id'] for row in actor.last['ui']['selected_files']}
    name = 'e11_sc_' + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    actor.configure_turns([[
        tool_call('create_project', 'fresh-sc-normal-create', name=name,
                  title='Independent native single-crystal routing', description='Supplied reflection observations'),
        tool_call('load_structure', 'fresh-sc-native-cif', file_id=ids[cif.name]),
        tool_call('create_experiment', 'fresh-sc-normal-experiment'),
    ]])
    actor.request('Create a new project from the selected structure and prepare a normal experiment.')
    actor.until(lambda row: len(actor.responses()) == 3 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    result = [native_result(row) for row in actor.responses()]
    assert actor.last['ui']['project']['structures'] == 1, (
        'Fresh SC routing uses one actual native CIF import rather than a prepared SC project'
    )
    created_id = result[2]['datasets'][0]['id']
    context = json.loads(actor.last['ui']['context'])['datasets'][0]
    assert context['id'] == created_id and context['calculation_only'], (
        'The actual returned new experiment identity is the current ordinary calculation-only owner'
    )
    actor.append_turn([tool_call('set_experiment_type', 'fresh-native-sample-form',
                                experiment=created_id, axis='sampleForm', token='single crystal')])
    actor.request('Use the original sample form selector to select single-crystal neutron diffraction.')
    actor.until(lambda row: len(actor.responses()) == 4 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    selected = native_result(actor.responses()[-1])
    actual_id = selected['datasets'][0]['id']
    context = json.loads(actor.last['ui']['context'])['datasets'][0]
    assert context['id'] == actual_id and context['sample_form'] == 'single crystal', (
        'Native sampleForm reaches the real type-factory replacement and reports its actual resulting identity'
    )
    assert qml(actor, 'Session.project.currentExperiment.sampleFormToken') == 'single crystal', (
        'Native type selection agrees with the genuine current ordinary experiment selector'
    )
    actor.command('undo')
    actor.until(lambda row: not row['ui']['project']['calculating'])
    restored = json.loads(actor.last['ui']['context'])['datasets'][0]
    assert restored['id'] == created_id and restored['sample_form'] == result[2]['datasets'][0]['sample_form'], (
        'One ordinary Undo restores exact pre-replacement sample-form identity and type'
    )
    actor.append_turn([tool_call('set_experiment_type', 'fresh-native-sample-form-again',
                                experiment=created_id, axis='sampleForm', token='single crystal')])
    actor.request('Select the requested single-crystal sample form again after the explicit Undo.')
    actor.until(lambda row: len(actor.responses()) == 5 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    actual_id = native_result(actor.responses()[-1])['datasets'][0]['id']
    actor.append_turn([tool_call('load_data', 'fresh-sc-native-reflections',
                                experiment=actual_id, file_id=ids[measured.name])])
    actor.request('Load the genuine selected measured reflections into that current experiment.')
    actor.until(lambda row: len(actor.responses()) == 6 and row['ui']['state'] == 'idle', visible_progress=show_actions)
    native_result(actor.responses()[-1])
    actor.until(lambda row: not row['ui']['project']['calculating'])
    actual = actor.command('sc_input')['reply']
    assert actual['sample_form'] == 'single crystal' and actual['rectangular'], (
        'Normal fresh native routing produces real rectangular measured SC ownership'
    )
    for index, field in enumerate(('h', 'k', 'l', 'intensity', 'sigma')):
        assert actual['columns'][field]['count'] == len(expected) and actual['columns'][field]['first'] == expected[0][index], (
            'Native reflection import preserves independent source column counts and first observation values'
        )
    context = json.loads(actor.last['ui']['context'])['datasets'][0]
    assert context['observations']['intensity_count'] == len(expected) and context['axis']['kind'] == 'miller_indices', (
        'The actual fresh SC context exposes measured reflections rather than phantom powder observations'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_native_create_explicit_names_follow_original_dialog_without_silent_renaming(main_actor, show_actions):
    actor = main_actor([[]], show_actions=show_actions)
    actor.connect()
    actor.command('click', name='assistant.toggle')
    actor.command('click', name='project.create')
    actor.until(lambda row: any(c['name'] == 'createProject.name' and c['visible']
                               for c in row['ui']['controls']))
    validator = qml(actor, control_expression('createProject.name') + '.validator.regularExpression.toString()')
    assert validator.startswith('/') and validator.endswith('/'), (
        'The independent name boundary is read from the actual original ordinary dialog validator'
    )
    pattern = validator[1:-1]
    invalid = ['LBCO neutron refinement', 'a' * 34, '1starts_with_digit']
    assert all(re.fullmatch(pattern, name) is None for name in invalid), (
        'Each explicit invalid-name control genuinely violates the unchanged original GUI rule'
    )
    qml(actor, '(' + control_expression('createProject.dialog') + ').close()')
    actor.command('click', name='assistant.toggle')
    actor.configure_turns([[tool_call('create_project', 'invalid-explicit-name-' + str(i),
                                     name=name, title='Human-readable metadata belongs in title')
                            for i, name in enumerate(invalid)]])
    actor.command('clear_ui_sequence')
    actor.request('Try each exact requested name and explain any ordinary form validation refusal.')
    actor.until(lambda row: len(actor.responses()) == len(invalid) and row['ui']['state'] == 'idle', visible_progress=show_actions)
    for response in actor.responses():
        assert not response['result']['success'], (
            'Both native modes refuse exact names the original normal Create form cannot represent'
        )
        value = json.loads(response['result']['contentItems'][0]['text'])
        assert not value.get('adopted') and isinstance(value.get('message'), str) and value['message'], (
            'Invalid explicit project metadata yields a useful actual model-visible refusal'
        )
    assert not actor.last['ui']['project'] and actor.last['ui']['connected'], (
        'Invalid names cannot silently adopt renamed projects or retire the connected account'
    )
    documents = Path(actor.last['ui']['environment']['documents_root'])
    assert not list(documents.iterdir()), (
        'Native invalid-name refusal cannot create any implicit normalized project destination'
    )


def test_nonnative_event_failure_preserves_first_cause_and_actual_connect_recovery(main_actor, tmp_path):
    marker = 'UNTRUSTED_EVENT_BODY_MUST_NOT_BECOME_THE_DIAGNOSTIC'
    actor = main_actor([[
        {'notification': {'method': 'item/started', 'params': {'item': {
            'type': 'agentMessage', 'id': 'typed-event-negative', 'text': ''}}}},
        {'notification': {'method': 'item/agentMessage/delta', 'params': {
            'itemId': 'typed-event-negative', 'delta': [marker]}}, 'hold_after': True},
    ], [tool_call('inspect_project', 'after-typed-event-recovery')]])
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'The nonnative event-error control starts from an actual ordinary saved project'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    model = actor.last['ui']['project']
    actor.connect()
    original = 'Inspect this current project and retain the original task across recoverable errors.'
    actor.request(original)
    actor.until(lambda row: not row['ui']['can_cancel'] and row['ui']['state'] != 'connecting')
    assert actor.last['ui']['project'] == model, (
        'A genuinely malformed nonnative notification cannot change scientific state'
    )
    before = json.loads(qml(actor, 'Session.assistant.workReportDocument()'))

    def first_event(document):
        values = [row['event_failure'] for row in objects(document) if 'event_failure' in row]
        assert values, (
            'A no-NativeRecord notification failure persists its actual original event diagnostic in accessible evidence'
        )
        facts = values[0]
        def observed(value):
            return value.get('value') if isinstance(value, dict) else value
        return {key: observed(facts[key]) for key in ('method', 'first_stage', 'first_class')}

    first = first_event(before)
    assert first['method'] == 'TEXT_DELTA' and first['first_stage'] and first['first_class'], (
        'The retained event tuple identifies the actual typed text-delta method and closed first processing class'
    )
    assert 'client.event_processing' in json.dumps(before) and marker not in json.dumps(before), (
        'Actual nonnative error evidence has its concrete code without copying arbitrary malformed provider bodies'
    )
    if not actor.last['ui']['connected']:
        actor.until(lambda row: any(c['name'] == 'assistant.connection' and c['fully_exposed']
                                   and c['enabled'] for c in row['ui']['controls']))
        actor.command('click', name='assistant.connection')
        actor.until(lambda row: row['ui']['connected'])
    actor.request('Continue the same original task without clearing it; inspect actual current state.')
    actor.until(lambda row: len(actor.responses()) == 1 and row['ui']['state'] == 'idle')
    native_result(actor.responses()[0])
    after = json.loads(qml(actor, 'Session.assistant.workReportDocument()'))
    assert first_event(after) == first, (
        'Later successful work/report refresh preserves the original notification first cause rather than overwriting it'
    )
    assert actor.last['ui']['connected'] and original in json.dumps(actor.last['ui']['messages']), (
        'Actual recovery and later native work preserve the account and original conversation without Clear'
    )
    wire = list(map(json.loads, actor.trace.read_text().splitlines()))
    starts = [row for row in wire if row.get('method') == 'thread/start']
    turns = [row['params'] for row in wire if row.get('method') == 'turn/start']
    assert len(starts) == 1 and len(turns) == 2 and turns[0]['threadId'] == turns[1]['threadId'], (
        'Malformed-notification recovery resumes the durable original thread instead of silently replacing its task'
    )


def test_local_history_publication_failure_does_not_require_clear_or_retire_account(main_actor, tmp_path):
    actor = main_actor([[tool_call('inspect_project', 'history-before-fault')], [],
                        [tool_call('inspect_project', 'history-after-fault')]])
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'The local-history failure witness uses an actual ordinary project and its independent science bytes'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    actor.connect()
    original = 'Keep the original current scientific task while ordinary local diagnostics are maintained.'
    actor.request(original)
    actor.until(lambda row: len(actor.responses()) == 1 and row['ui']['state'] == 'idle')
    native_result(actor.responses()[0])
    before = actor.last['ui']['project']
    roots = list(Path(actor.last['test_storage']).rglob('assistant/history.json'))
    assert len(roots) == 1 and roots[0].is_file(), (
        'The fault targets the actual newly written history inside this isolated test storage only'
    )
    history = roots[0]
    retained = history.with_name('history.independent-preserved')
    history.rename(retained)
    history.mkdir()
    try:
        actor.request('Continue the same task while retaining actual local diagnostic outcomes.')
        actor.until(lambda row: not row['ui']['can_cancel'] and row['ui']['state'] == 'idle')
        assert actor.last['ui']['connected'], (
            'A real local history publication failure cannot turn valid provider work into account retirement'
        )
        document = qml(actor, 'Session.assistant.workReportDocument()')
        assert isinstance(json.loads(document), dict), (
            'Useful cached diagnostics remain accessible when ordinary history publication fails'
        )
        assert actor.last['ui']['project'] == before, (
            'Local diagnostic failure cannot mutate the independent scientific model or owner'
        )
    finally:
        history.rmdir()
        retained.rename(history)
    actor.request('Continue the original task without Clear and inspect the actual current project.')
    actor.until(lambda row: len(actor.responses()) == 2 and row['ui']['state'] == 'idle')
    native_result(actor.responses()[1])
    assert actor.last['ui']['connected'] and original in json.dumps(actor.last['ui']['messages']), (
        'A later valid action is usable with original conversation after local retention recovers, without Clear'
    )
    wire = list(map(json.loads, actor.trace.read_text().splitlines()))
    turns = [row['params'] for row in wire if row.get('method') == 'turn/start']
    assert len(turns) == 3 and len({row['threadId'] for row in turns}) == 1, (
        'Local history/report maintenance cannot replace the original provider thread or replay its prior calls'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_large_original_multiline_description_is_not_a_work_or_form_context_quota(main_actor, tmp_path, show_actions):
    actor = main_actor([[]], show_actions=show_actions)
    actor.connect()
    name = 'e11_desc_' + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    title = 'Independent extended Description control'
    description = ('Independent valid scientific metadata retained through the original multiline field.\n'
                   * 14000)
    assert len(description.encode()) > 1048576, (
        'The finite independent Description input crosses the historical one-MiB context admission boundary'
    )
    schema = next(row['inputSchema'] for row in actor.command('tool_specs')['reply']['tools']
                  if row['name'] == 'create_project')
    allowed = schema['properties']['description'].get('maxLength')
    actor.configure_turns([[tool_call('create_project', 'large-original-description',
                                     name=name, title=title, description=description)]])
    actor.request('Create the requested project preserving its complete supplied multiline description.')
    actor.until(lambda row: len(actor.responses()) == 1 and row['ui']['state'] == 'idle', seconds=90)
    result = native_result(actor.responses()[0])
    assert allowed is None or allowed >= len(description), (
        'The offered native schema cannot conceal an artificial work quota on the original multiline Description'
    )
    assert result['adopted'] and result['complete'] and result['saved'] is True, (
        'A valid larger Description reaches the actual ordinary saved project owner in each native mode'
    )
    assert qml(actor, 'Session.project.title') == title and qml(
        actor, 'Session.project.description') == description, (
        'Original title control semantics and complete multiline Description survive actual native Create'
    )
    actual = Path(result['path']) / 'project.edi'
    assert actual.is_file(), 'The ordinary writer produces its real metadata file before decoded readback'
    metadata_bytes = actual.read_bytes()
    complete = copied_estimate_project(tmp_path)
    (complete / 'project.edi').write_bytes(metadata_bytes)
    assert actor.command('open', path=str(complete))['reply']['opened'], (
        'An explicitly complete independent fixture permits ordinary parsing of the actual saved CIF metadata'
    )
    assert qml(actor, 'Session.project.description') == description and qml(actor, 'Session.project.title') == title, (
        'Decoded native CIF metadata preserves the complete original multiline Description and Title'
    )
    assert actual.read_bytes() == metadata_bytes, 'Decoded metadata observation never rewrites the original saved project'

    assert actor.last['ui']['connected'] and not actor.last['ui']['can_cancel'], (
        'A valid large form cannot retire the account or leave a retention/Clear fence'
    )


def test_prework_current_settings_error_has_accessible_first_cause_without_a_fake_turn(main_actor, tmp_path):
    actor = main_actor([[tool_call('inspect_project', 'after-prework-notification-recovery')]])
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'The prework fallback witness has a genuine current ordinary project without fabricated assistant work'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    model = actor.last['ui']['project']
    actor.connect()
    wire = list(map(json.loads, actor.trace.read_text().splitlines()))
    starts = [row['params'] for row in wire if row.get('method') == 'thread/start']
    assert len(starts) == 1 and not any(row.get('method') == 'turn/start' for row in wire), (
        'The pinned notification negative is delivered before the first real user turn or work attempt'
    )
    # Literal pinned092d ThreadSettingsUpdatedNotification/ThreadSettings shape.
    # Only model has the deliberately wrong type. This is not valid large work.
    settings = {'disabledPluginIds': [], 'cwd': starts[0]['cwd'], 'approvalPolicy': 'never',
        'approvalsReviewer': 'user', 'sandboxPolicy': {'type': 'readOnly', 'networkAccess': False},
        'activePermissionProfile': None, 'model': 17, 'modelProvider': 'openai', 'serviceTier': None,
        'effort': 'medium', 'summary': None, 'collaborationMode': {'mode': 'default',
            'settings': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'medium', 'developer_instructions': None}},
        'personality': None}
    config_path = actor.folder / 'peer.json'
    config = json.loads(config_path.read_text())
    config['usage_notifications'] = [{'method': 'thread/settings/updated', 'params': {'threadSettings': settings}}]
    config_path.write_text(json.dumps(config))
    actor.command('refresh_usage')
    actor.until(lambda row: not row['ui']['connected'] or bool(row['ui']['last_error']))
    assert actor.last['ui']['project'] == model, (
        'Rejecting a malformed current settings notification cannot mutate scientific project state'
    )
    wire = list(map(json.loads, actor.trace.read_text().splitlines()))
    assert not any(row.get('method') == 'turn/start' for row in wire), (
        'The actual no-attempt diagnostic cannot be manufactured by sending a test user turn'
    )
    stderr = (actor.folder / 'host.stderr').read_text(errors='replace')
    original = re.search(r'method=([A-Z_]+) first_stage=([A-Z_]+) first_class=([A-Z_]+)', stderr)
    assert original and 'SETTINGS' in original[1], (
        'The independent stderr witness identifies the actual original typed settings-processing failure'
    )
    expected = dict(zip(('method', 'first_stage', 'first_class'), original.groups()))

    def diagnostic(document):
        values = [row['event_failure'] for row in objects(document) if 'event_failure' in row]
        assert values, (
            'An actual prework notification error is accessible in current/last diagnostics without a native record'
        )
        return {key: (values[0][key].get('value') if isinstance(values[0][key], dict)
                      else values[0][key]) for key in expected}

    first = json.loads(qml(actor, 'Session.assistant.workReportDocument()'))
    assert not any(row.get('kind') == 'user' for row in actor.last['ui']['messages']) and not any(
        row.get('type') == 'dynamicToolCall' for row in objects(first)), (
        'A prework diagnostic must not invent a user request or native scientific record to create an attempt'
    )
    assert diagnostic(first) == expected and 'client.event_processing' in json.dumps(first), (
        'Before any work attempt the real diagnostic cache preserves the original closed method/stage/class tuple'
    )
    config['usage_notifications'] = [];config_path.write_text(json.dumps(config))
    if not actor.last['ui']['connected']:
        actor.until(lambda row: any(c['name'] == 'assistant.connection' and c['enabled'] and c['fully_exposed']
                                   for c in row['ui']['controls']))
        actor.command('click', name='assistant.connection')
        actor.until(lambda row: row['ui']['connected'])
    actor.request('Inspect the unchanged current project after retaining the real earlier diagnostic.')
    actor.until(lambda row: len(actor.responses()) == 1 and row['ui']['state'] == 'idle')
    native_result(actor.responses()[0])
    after = json.loads(qml(actor, 'Session.assistant.workReportDocument()'))
    assert diagnostic(after) == expected, (
        'The first legitimate work/report refresh cannot erase the actual prework event first cause'
    )


def test_native_simulation_snapshot_preserves_grid_without_inventing_observations(main_actor, tmp_path):
    actor = main_actor([[]])
    cif = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(cif)])['reply']['added'], (
        'The calculation-only lifecycle gate admits an actual independent published CIF'
    )
    selected = actor.last['ui']['selected_files'][0]['id']
    actor.configure_turns([[
        tool_call('create_project', 'simulation-normal-create', name='e11_simulation_observer'),
        tool_call('load_structure', 'simulation-native-cif', file_id=selected),
        tool_call('create_experiment', 'simulation-first-experiment'),
    ]])
    actor.request('Create this fixture and add one explicit ordinary calculation-only experiment; add no measurements.')
    actor.until(lambda row: len(actor.responses()) == 3 and row['ui']['state'] == 'idle')
    for response in actor.responses():
        native_result(response)
    actor.until(lambda row: not row['ui']['project']['calculating'])
    rows = actor.last['ui']['project']['backgrounds']
    assert len(rows) == 1 and rows[0]['calculation_only'] and rows[0]['input_count'] > 0, (
        'The actual native first experiment has a nonempty simulation grid, reproducing the original observer escape'
    )
    assert rows[0]['input_intensity_count'] == rows[0]['input_sigma_count'] == 0 and rows[0]['input_first'] == [], (
        'A calculation grid cannot become invented measured intensity or uncertainty rows in the Main observer'
    )
    context = json.loads(actor.last['ui']['context'])['datasets'][0]
    assert context['calculation_only'] and context['observations']['intensity_count'] == 0, (
        'The independent current native context agrees that simulation has no measured observations'
    )


def test_snapshot_preserves_unequal_sc_columns_as_invalid_without_padding(main_actor, tmp_path):
    actor = main_actor([[]])
    path = tmp_path / 'unequal-sc'
    shutil.copytree(ROOT / 'docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_basic/project', path)
    original = {str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*.edi')}
    assert actor.command('open', path=str(path))['reply']['opened'], (
        'The mismatched-column witness starts from genuine published native SC observations'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    before = actor.command('sc_input')['reply']
    count = before['columns']['h']['count']
    assert before['columns']['wavelength']['count'] == 0, (
        'The real CW source uses its global wavelength without requiring a per-reflection wavelength column'
    )
    assert before['rectangular'] and count > 1, (
        'The independent measured SC source is rectangular before deliberate fixture truncation'
    )
    actor.command('sc_input', mode='truncate', field='h', count=count-1)
    row = actor.last['ui']['project']['backgrounds'][0]
    assert not row['reflection_columns_rectangular'] and row['reflection_columns']['h'] == count-1, (
        'The Main observer preserves the actual shortened Miller column rather than padding physical input'
    )
    assert row['reflection_columns']['intensity'] == before['columns']['intensity']['count'], (
        'Unchanged measured observations retain their own independent native length'
    )
    assert json.loads(actor.last['ui']['context'])['datasets'][0]['data_status'] == 'invalid', (
        'Mismatched physical measured columns remain invalid and cannot be relabelled as valid simulation'
    )
    assert {str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*.edi')} == original, (
        'The malformed native fixture observation does not write or normalize original scientific source files'
    )


def test_main_event_loop_delivers_real_timer_and_provider_work_while_driver_is_quiet(main_actor, tmp_path):
    actor = main_actor([[]])
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'Idle delivery uses the ordinary actual current project, not a replacement service'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    actor.connect()
    qml(actor, "(function(){Qt.createQmlObject('import QtQuick; Item {id: idleWitness; objectName: \"e11.idle.observer\"; property int ticks: 0; Timer {interval: 16; repeat: true; running: true; onTriggered: idleWitness.ticks++}}', contentItem);return null;})()")
    baseline = qml(actor, control_expression('e11.idle.observer') + '.ticks')
    # Deliberate quiet-driver escape: no stdin commands may supply the Qt loop.
    time.sleep(0.6)
    after = qml(actor, control_expression('e11.idle.observer') + '.ticks')
    assert after - baseline >= 10, (
        'The existing Main host owns a live Qt event loop between commands rather than a thirty-ms drain only'
    )
    qml(actor, '(' + control_expression('e11.idle.observer') + ').destroy()')
    actor.configure_turns([[{**tool_call('inspect_project', 'actual-quiet-native-call'), 'idle_delay_ms': 150}]])
    actor.request('Inspect the actual current project after independently scheduled provider delivery.')
    # The peer emits later; no actor command is sent while the real Main handles
    # its request, returns native data and settles its actual report/terminal.
    time.sleep(1.5)
    responses = actor.responses()
    assert len(responses) == 1, (
        'An actual delayed provider native request receives its real response without command traffic'
    )
    native_result(responses[0])
    actor.until(lambda row: row['ui']['state'] == 'idle' and not row['ui']['can_cancel'])
    actor.command('destroy')
    assert actor.command('inspect')['ui']['alive'] is False, (
        'The same live protocol can observe retired Main ownership without dereferencing a dead receiver'
    )


@pytest.mark.parametrize('source_kind', ['folder', 'record', 'archive', 'readonly_archive', 'readonly_folder'])
def test_ordinary_open_reentry_preserves_adopted_successor_and_its_real_origin(main_actor, tmp_path, source_kind):
    import zipfile
    actor = main_actor([[]])
    roots = {}
    for name in ['initial_c', 'outer_a', 'successor_b']:
        target = tmp_path / name
        shutil.copytree(ROOT / 'tests/fixtures/background_estimate/projects/hrpt', target)
        record = target / 'project.edi'
        text = record.read_text()
        text = re.sub(r'(?m)^_metadata\.name\s+.*$', '_metadata.name ' + name, text)
        record.write_text(text)
        roots[name] = target
    initial, outer, successor = [roots[k] for k in ['initial_c', 'outer_a', 'successor_b']]
    before = {str(p.relative_to(successor)): p.read_bytes() for p in successor.rglob('*.edi')}
    assert actor.command('open', path=str(initial))['reply']['opened'], (
        'Reentrant ordinary Open starts from a genuinely complete independent current project'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    source = outer
    if source_kind == 'record':
        source = outer / 'project.edi'
    elif source_kind in {'archive', 'readonly_archive'}:
        source = tmp_path / 'outer_a.zip'
        with zipfile.ZipFile(source, 'w') as archive:
            for file in outer.rglob('*'):
                if file.is_file(): archive.write(file, str(file.relative_to(outer)))
        if source_kind == 'readonly_archive': source.chmod(0o444)
    elif source_kind == 'readonly_folder':
        for file in outer.rglob('*'):
            file.chmod(0o555 if file.is_dir() else 0o444)
        outer.chmod(0o555)
    # An actual public Session signal invokes actual nested ordinary Open. The
    # observer is a zero-size test Item, never a replacement Session or fake ACK.
    expression = '''(function(){const o=Qt.createQmlObject('import QtQuick; Item {objectName:"e11.open.reentry";property int calls:0;property bool innerOpened:false;property var callback:null}',contentItem);o.callback=function(){if(!Qt.isQtObject(o))return;o.calls++;if(o.calls===1)o.innerOpened=Session.openProject(%s);};Session.projectAboutToChange.connect(o.callback);return true;})()''' % json.dumps(successor.as_uri())
    assert qml(actor, expression), 'The actual original Session about-to-change signal admits the finite reentry observer'
    try:
        opened = actor.command('open', path=str(source))['reply']['opened']
        actor.until(lambda row: not row['ui']['project']['calculating'])
        witness = qml(actor, '(function(){const o=' + control_expression('e11.open.reentry')
                      + ';return {calls:o.calls,innerOpened:o.innerOpened};})()')
        assert witness['calls'] >= 2 and witness['innerOpened'], (
            'The real nested complete-project Open actually adopted its successor during the outer change signal'
        )
        assert not opened, (
            'The superseded outer ordinary Open cannot claim successful adoption after another project wins'
        )
        current = actor.last['ui']['project']
        assert current['name'] == 'successor_b' and Path(current['path']) == successor, (
            'Folder, record, archive and copy continuations cannot decorate the adopted successor with outer paths'
        )
        assert qml(actor, 'Session.locationText') == str(successor) and not qml(
            actor, 'Session.openedArchive') and not qml(actor, 'Session.openedExample'), (
            'Actual successor location and archive/example origins survive superseded ordinary Open continuations'
        )
        assert {str(p.relative_to(successor)): p.read_bytes() for p in successor.rglob('*.edi')} == before, (
            'Reentrant adoption never rewrites the independent successor scientific files or invents a rollback'
        )
    finally:
        try:
            qml(actor, '(function(){const o=' + control_expression('e11.open.reentry')
                + ';Session.projectAboutToChange.disconnect(o.callback);o.destroy();})()')
        finally:
            if source_kind == 'readonly_folder':
                outer.chmod(0o755)
                for file in outer.rglob('*'):file.chmod(0o755 if file.is_dir() else 0o644)
            if source_kind == 'readonly_archive':source.chmod(0o644)


@pytest.mark.parametrize('target_kind', ['working_folder', 'working_record', 'symlink_alias', 'descendant_copy', 'archive_inside'])
def test_open_current_archive_backing_root_preserves_real_files_and_current_data(main_actor, tmp_path, target_kind):
    import zipfile
    actor = main_actor([[]])
    source = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(source))['reply']['opened'], (
        'The backing-root cleanup control starts from a genuinely complete ordinary native project'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    archive = tmp_path / 'actual-current.zip'
    assert actor.command('save_project_as', path=str(archive), zip=True, copy=True)['reply']['saved'], (
        'The actual ordinary archive writer produces the complete input before its working root is reopened'
    )
    assert actor.command('open', path=str(archive))['reply']['opened'], (
        'Ordinary archive Open adopts its actual writable temporary working folder'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    working = Path(actor.last['ui']['project']['path'])
    assert working.is_dir() and (working / 'project.edi').is_file() and working != source, (
        'The witness reaches a real current archive backing root rather than an unrelated saved folder'
    )
    target = working
    if target_kind == 'working_record':
        target = working / 'project.edi'
    elif target_kind == 'symlink_alias':
        target = tmp_path / 'same-backing-alias'
        target.symlink_to(working, target_is_directory=True)
    elif target_kind == 'descendant_copy':
        target = working / 'explicit-child-project'
        assert actor.command('save_project_as', path=str(target), zip=False, copy=True)['reply']['saved'], (
            'A separate ordinary Save copy establishes the explicit complete descendant without fabricated science'
        )
    elif target_kind == 'archive_inside':
        target = working / 'nested-origin.zip'
        assert actor.command('save_project_as', path=str(target), zip=True, copy=True)['reply']['saved'], (
            'A real ordinary archive Save copy establishes its future origin inside the existing backing ancestor'
        )
    archive_bytes = target.read_bytes() if target_kind == 'archive_inside' else None
    before = actor.last['ui']['project']
    files = {str(path.relative_to(target if target.is_dir() else target.parent)): path.read_bytes()
             for path in (target if target.is_dir() else target.parent).rglob('*.edi')}
    assert files, 'The real target owns persisted scientific files before the same-backing Open'
    assert actor.command('open', path=str(target))['reply']['opened'], (
        'The actual ordinary same-backing Open reports its real adopted current project'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    current = actor.last['ui']['project']
    actual = Path(current['path'])
    assert working.is_dir() and actual.is_dir() and (actual / 'project.edi').is_file(), (
        'Previous archive/copy cleanup cannot delete the actual backing ancestor used by the adopted current project'
    )
    if target_kind == 'archive_inside':
        assert actual.resolve() != working.resolve() and target.is_file() and target.read_bytes() == archive_bytes, (
            'A newly unpacked working root retains its real archive origin inside the previous backing ancestor'
        )
        assert qml(actor, 'Session.locationText') == str(target), (
            'The actual current archive location remains the original future Save target, not merely the new path'
        )
    else:
        assert actual.resolve() == (target if target.is_dir() else target.parent).resolve(), (
            'The adopted normal owner retains the actual requested backing identity through aliases and descendant copies'
        )
    assert {str(path.relative_to(actual)): path.read_bytes() for path in actual.rglob('*.edi')} == files, (
        'The original complete scientific files survive cleanup byte-for-byte without rollback or regeneration'
    )
    assert current['structure_rows'] == before['structure_rows'] and current['backgrounds'] == before['backgrounds'], (
        'Same-backing adoption retains actual structures, measured data counts and sample values'
    )
    assert actor.command('save')['reply']['saved'], (
        'A subsequent ordinary Save still has its real current files and source data after same-backing adoption'
    )
    if target_kind == 'archive_inside':
        assert target.is_file() and working.is_dir() and Path(actor.last['ui']['project']['path']).is_dir(), (
            'Ordinary subsequent Save preserves both the retained archive origin ancestor and the current working closure'
        )
        with zipfile.ZipFile(target) as saved_archive:
            for relative, content in files.items():
                assert saved_archive.read(relative) == content, (
                    'The original future archive target actually receives the unchanged scientific files on ordinary Save'
                )


def test_main_reader_keeps_json_after_a_coalesced_native_diagnostic(tmp_path):
    program = "import sys,os;sys.stdin.readline();os.write(1,b'library notice\\n{\"ui\":{\"alive\":true},\"reply\":{\"value\":73}}\\n');sys.stdin.readline()"
    actor = MainActor.__new__(MainActor)
    actor.folder = tmp_path
    actor.process = subprocess.Popen([sys.executable, '-c', program], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    try:
        response = actor.command('inspect')
        assert response['ui']['alive'] and response['reply']['value'] == 73, (
            'A complete JSON response already read beside a library diagnostic cannot be stranded behind OS select readiness'
        )
        assert actor.process.poll() is None, 'The framing witness keeps its server alive awaiting the next real command'
    finally:
        actor.process.stdin.close()
        actor.process.wait(timeout=2)
        actor.process.stdout.close()
        actor.process.stderr.close()


def model_wire_contexts(actor, response):
    contexts = []
    for line in actor.trace.read_text().splitlines():
        request = json.loads(line)
        if request.get('method') != 'turn/start':
            continue
        for item in request['params']['input']:
            text = item.get('text', '')
            if text.startswith('EDI_APPROVED_CONTEXT_DATA_V1'):
                contexts.append(json.loads(text[text.index('{'):]))
    reply = native_result(response)
    assert reply.get('schema') == 'edi.assistant.outgoing/1' and isinstance(reply.get('datasets'),list), (
        'The successful native inspect endpoint must expose its actual typed outgoing context rather than an invented nested context envelope'
    )
    contexts.append(reply)
    assert len(contexts) >= 2, 'Both the actual approved provider context and native inspect reply expose their real typed context'
    return contexts


@pytest.mark.parametrize('kind', ['line-segment', 'polynomial', 'chebyshev'])
@pytest.mark.parametrize('mode', ['manual', 'auto'])
def test_model_visible_background_ownership_settings_and_terms_match_real_native_values(main_actor, tmp_path, kind, mode):
    actor = main_actor([[]])
    project = tmp_path / 'native-wire-background'
    shutil.copytree(ROOT / ('tests/fixtures/background_estimate/projects/fitted-auto-' + kind), project)
    path = project / 'experiments/d20.edi'
    text = path.read_text()
    assert text.count('_background_estimate.mode auto') == 1, 'The independent source fixture explicitly declares its original automatic owner'
    if mode == 'manual':
        path.write_text(text.replace('_background_estimate.mode auto', '_background_estimate.mode manual'))
    assert actor.command('open', path=str(project))['reply']['opened'], 'Model-visible ownership starts from the genuine native saved background fixture'
    actor.until(lambda row: not row['ui']['project']['calculating'])
    native = actor.last['ui']['project']['backgrounds'][0]
    assert native['mode'] == mode and native['type'] == kind, 'The ordinary native owner actually adopts the independently declared background type and mode'
    actor.configure_turns([[tool_call('inspect_project', 'actual-visible-background')]])
    actor.connect()
    actor.request('Inspect the actual current native background and saved settings.')
    actor.until(lambda row: len(actor.responses()) == 1 and row['ui']['state'] == 'idle')
    for context in model_wire_contexts(actor, actor.responses()[0]):
        background = next(row for row in context['datasets'] if row['id'] == native['id'])['background']
        assert background['type'] == kind, 'Actual approved/inspect wire preserves the real native background family'
        assert background['estimate'] == {'mode': mode, 'method': 'arpls', 'width': 6,
            'smoothness': 1000, 'n_points': 9, 'tolerance': 2, 'in_peaks': 'move',
            'use_model': 'auto', 'max_terms': 3}, (
            'Actual wire retains every independently stored native Estimate setting instead of silently dropping its typed object'
        )
        assert [{k:point[k] for k in ('id','position','intensity','free')} for point in background['anchors']] == native['points'], (
            'Approved context and inspect preserve actual native point identity, coordinates, intensities and free flags'
        )
        assert [{k:term[k] for k in ('id','order','coefficient','uncertainty','free')} for term in background['terms']] == native['term_rows'], (
            'Approved context and inspect preserve every current polynomial/Chebyshev term through the actual outgoing projection'
        )
        assert all(term['dependence'] == 'independent' for term in background['terms']), (
            'The independent unconstrained series fixture remains independent in model-visible native metadata'
        )


def test_model_visible_sc_choices_follow_actual_applicable_native_family(main_actor, tmp_path):
    actor = main_actor([[]])
    project = tmp_path / 'sc-visible-options'
    shutil.copytree(ROOT / 'docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_basic/project', project)
    assert actor.command('open', path=str(project))['reply']['opened'], 'Model-visible SC metadata uses the independently published measured single-crystal fixture'
    actor.until(lambda row:not row['ui']['project']['calculating'])
    original=actor.last['ui']['project']
    initial=json.loads(actor.last['ui']['context'])['datasets'][0]
    assert initial['extinction_type']=='none', 'The published fixture initially has no applicable mosaic family'
    actor.configure_turns([[tool_call('edit_experiment','inapplicable-mosaic',experiment=initial['id'],operation='mosaic_distribution',value='gaussian')]])
    actor.connect();actor.request('Report whether the current none family has an applicable mosaic selector.')
    actor.until(lambda row:len(actor.responses())==1 and row['ui']['state']=='idle')
    assert not actor.responses()[0]['result']['success'] and actor.last['ui']['project']==original, (
        'An inapplicable ordinary mosaic choice refuses without changing native science or creating a new field family'
    )
    qml(actor, 'Session.project.currentExperiment.extinctionType="becker-coppens-mixed"')
    actor.until(lambda row:not row['ui']['project']['calculating'])
    def options(name):
        return qml(actor, '(function(){const m=Session.project.currentExperiment.'+name+';return Array.from({length:m.count},(_,i)=>m.tokenAt(i));})()')
    ordinary_types, ordinary_distributions = options('extinctionTypeOptions'), options('mosaicDistributionOptions')
    assert ordinary_distributions == ['gaussian','lorentzian'], 'The genuinely selected mixed family has the original applicable two-token mosaic selector'
    actor.append_turn([tool_call('inspect_project','actual-visible-sc-options')])
    actor.connect();actor.request('Inspect the current actual single-crystal family and its available ordinary options.')
    actor.until(lambda row:len(actor.responses())==2 and row['ui']['state']=='idle')
    contexts=model_wire_contexts(actor,actor.responses()[-1])
    assert len(contexts)==3 and contexts[0]['datasets'][0]['mosaic_distribution_options']==[], 'Actual initial none context and both later applicable contexts retain their distinct native option scopes'
    for context in contexts[1:]:
        row=context['datasets'][0]
        assert row['sample_form']=='single crystal' and row['extinction_type']=='becker-coppens-mixed', (
            'Actual model-visible SC type/family agrees with the ordinary selected native owner'
        )
        assert row['extinction_type_options']==ordinary_types and row['mosaic_distribution_options']==ordinary_distributions, (
            'Actual approved/inspect context cannot erase currently applicable SC native selector choices'
        )


@pytest.mark.parametrize('kind', ['nested','readonly','example'])
def test_actual_retired_worker_and_repeat_copy_keep_live_native_file_identity(main_actor,tmp_path,kind):
    actor=main_actor([[]])
    readonly=None
    try:
        if kind=='example':
            initial=actor.command('open_first_example')['reply']
            assert initial['opened'], 'A real bundled example supplies its actual ordinary backing root before repeated Open'
            target=initial['id'];successor=''
        else:
            source=copied_estimate_project(tmp_path)
            if kind=='readonly':
                readonly=source
                for p in source.rglob('*'):p.chmod(0o555 if p.is_dir() else 0o444)
                source.chmod(0o555)
            assert actor.command('open',path=str(source))['reply']['opened'], 'The real native owner adopts the independent measured source before its worker lifetime witness'
            target=str(source);successor=''
            if kind=='nested':
                archive=tmp_path/'worker-original.zip'
                assert actor.command('save_project_as',path=str(archive),zip=True,copy=True)['reply']['saved'], 'The ordinary archive writer creates the actual worker-backed temporary root'
                assert actor.command('open',path=str(archive))['reply']['opened'], 'Ordinary archive Open supplies the actual removable backing root'
                outer=tmp_path/'outer';winner=tmp_path/'winner'
                shutil.copytree(source,outer);shutil.copytree(source,winner)
                target,successor=str(outer),str(winner)
        actor.until(lambda row:not row['ui']['project']['calculating'])
        result=actor.command('live_worker_root_boundary',kind=kind,target=target,successor=successor)['reply']
        assert result['actual_worker_entered'] and result['native_file_read_before'], (
            'The genuine original ProjectViewModel Worker reaches a real native experiment-file read before replacement'
        )
        assert result['file_identity_at_about'] and result['file_preserved_while_worker_live'], (
            'Neither fixed-copy staging nor reentrant cleanup may unlink or replace the live original native file before its owner releases it'
        )
        if kind=='nested':
            assert result['nested_reached'] and result['nested_opened'] and result['file_preserved_after_nested'], (
                'A genuine nested ordinary Open exercises the early-return branch while the retired original Worker owns its files'
            )
            assert actor.last['ui']['project']['path']==successor, 'Reentrant native replacement retains the actual independent successor rather than inventing rollback'
        else:
            assert result['opened'], 'A valid repeated read-only/example Open still adopts its real complete project'
        assert result['original_destroyed'] and result['actual_worker_finished'] and result['native_file_read_after'], (
            'The original QObject/Worker retirement completes its actual data read before reclaiming its backing root'
        )
    finally:
        if readonly is not None:
            readonly.chmod(0o755)
            for p in readonly.rglob('*'):p.chmod(0o755 if p.is_dir() else 0o644)


def test_pending_archive_source_survives_real_same_owner_save_as_publication(main_actor,tmp_path):
    actor=main_actor([[]]);source=copied_estimate_project(tmp_path)
    assert actor.command('open',path=str(source))['reply']['opened'], 'Pending source lifetime starts from an independently complete ordinary project'
    archive=tmp_path/'outer-current.zip'
    assert actor.command('save_project_as',path=str(archive),zip=True,copy=True)['reply']['saved'], 'Ordinary archive Save establishes the original owned temporary-root lifetime'
    assert actor.command('open',path=str(archive))['reply']['opened'], 'Ordinary archive Open adopts its actual current working root'
    actor.until(lambda row:not row['ui']['project']['calculating'])
    before=actor.last['ui']['project'];inside=Path(before['path'])/'pending-input.zip'
    assert actor.command('save_project_as',path=str(inside),zip=True,copy=True)['reply']['saved'], 'A real archive Save copy places its exact future Open source inside the existing owned root'
    destination=tmp_path/'actual-intervening-save'
    result=actor.command('pending_open_save_as',source=str(inside),destination=str(destination))['reply']
    assert result['hooked'] and result['saved'] and not result['hook_error'], (
        'A real pathChanged publication invokes the ordinary same-owner SaveAs before outer archive-origin installation'
    )
    assert result['source_preserved_during_pending_save'], (
        'The genuine archive input remains byte-identical through nested cleanup while its actual Open is still pending'
    )
    assert result['current_path']==str(destination) and result['location']==str(destination), (
        'The outer Open cannot reinstall stale archive origin over the actual intervening same-owner SaveAs location'
    )
    assert (destination/'project.edi').is_file() and actor.last['ui']['project']['structure_rows']==before['structure_rows'], (
        'Actual adopted scientific files and structure values survive the superseding native write without fabricated rollback'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off','on'])
def test_original_estimate_member_survives_ordinary_selection_callback_before_effect(main_actor,tmp_path,show_actions):
    actor=main_actor([[]],show_actions=show_actions);project=copied_estimate_project(tmp_path)
    source=project/'experiments/bank.edi';other=project/'experiments/bank_second.edi'
    other.write_text(source.read_text().replace('data_bank\n','data_bank_second\n',1).replace('old_a 10 0','other_a 10 7').replace('old_b 164.84999999999999 0','other_b 164.84999999999999 11'))
    assert actor.command('open',path=str(project))['reply']['opened'], 'The selection race uses two genuine independently identified native measured datasets'
    actor.until(lambda row:not row['ui']['project']['calculating'])
    qml(actor,'Session.project.currentExperimentIndex=0')
    before=actor.last['ui']['project'];requested=before['backgrounds'][0]['id']
    assert len(before['backgrounds'])==2 and before['backgrounds'][0]!=before['backgrounds'][1], (
        'The original and successor datasets have distinguishable native state before their ordinary selection callback'
    )
    actor.configure_turns([[tool_call('estimate_background','original-member-before-selection',experiment=requested),tool_call('inspect_project','continue-after-selected-member-refusal')]])
    actor.connect()
    marker='e11.estimate.selection'
    signal='Session.assistant.actionPointerMoved' if show_actions else 'Session.assistant.actionPageRequested'
    callback=('function(position){if(!o.fired){o.fired=true;o.before=Session.project.currentExperimentIndex;Session.project.currentExperimentIndex=1;o.after=Session.project.currentExperimentIndex;}}' if show_actions else
              'function(page,extra){if(!o.fired && page==="experiment"){o.fired=true;o.before=Session.project.currentExperimentIndex;Session.project.currentExperimentIndex=1;o.after=Session.project.currentExperimentIndex;}}')
    setup='(function(){const o=Qt.createQmlObject(\'import QtQuick; Item {objectName:"'+marker+'";property bool fired:false;property int before:-1;property int after:-1;property var callback:null}\',contentItem);const pointer=assistantPointer;o.callback='+callback+';'+signal+'.connect(o.callback);return true;})()'
    assert qml(actor,setup), 'The actual ordinary selection callback is attached to the current visible cue or OFF follow-page boundary'
    try:
        actor.request('Estimate the originally requested current measured dataset and inspect the resulting state.')
        actor.until(lambda row:len(actor.responses())==2 and row['ui']['state']=='idle', visible_progress=show_actions)
        changed=qml(actor,'(function(){const o='+control_expression(marker)+';return {fired:o.fired,before:o.before,after:o.after};})()')
        assert changed=={'fired':True,'before':0,'after':1}, 'A genuine same-owner ordinary selection setter actually executes during the admitted action boundary'
        assert not actor.responses()[0]['result']['success'], 'A changed requested member cannot be silently replaced by the newly selected dataset'
        native_result(actor.responses()[1])
        after=actor.last['ui']['project']
        assert after['backgrounds']==before['backgrounds'] and after['parameters']==before['parameters'], (
            'Both original and successor native datasets retain exact prewrite scientific values and flags after selection supersedes the request'
        )
        assert after['can_undo']==before['can_undo'], 'A prewrite selected-member refusal cannot add an Undo or hide a partial effect'
    finally:
        qml(actor,'(function(){const o='+control_expression(marker)+';const pointer=assistantPointer;'+signal+'.disconnect(o.callback);o.destroy();})()')


@pytest.mark.parametrize('boundary',['padding','header_width'])
def test_datatable_internal_ordinary_setter_retirement_preserves_live_width_contract(main_actor,tmp_path,boundary):
    actor=main_actor([[]]);source=copied_estimate_project(tmp_path);successor=tmp_path/'independent-successor'
    shutil.copytree(source,successor)
    assert actor.command('open',path=str(source))['reply']['opened'], 'Internal column lifetime uses the genuine ordinary project/page owner'
    actor.until(lambda row:not row['ui']['project']['calculating'])
    wait_positive_tab(actor,'appBar.tab.structure');actor.command('click',name='appBar.tab.structure')
    witness='e11.table.internal.witness'
    qml(actor,'(function(){Qt.createQmlObject(\'import QtQuick; import edi.app; Item {objectName:"'+witness+'";property bool armed:false;property string boundary:"'+boundary+'";property int hits:0;property bool opened:false;property var held:null;function padding(cell,table){if(armed && boundary==="padding" && table.basePaddings.has(cell)){armed=false;hits++;opened=Session.openProject('+json.dumps(successor.as_uri())+');}}function header(cell,table){if(armed && boundary==="header_width" && table.basePaddings.has(cell)){armed=false;hits++;opened=Session.openProject('+json.dumps(successor.as_uri())+');}}}\',contentItem);return true;})()')
    component=r'''import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Elements as E
import EasyApplication.Gui.Components as C
import edi.app
DataTable {
 id: t
 objectName: "e11.actual.column.fixture"
 width: parent.width-40
 height: 180
 columns: [numberColumnWidth,-1,-1]
 function findWitness(){const w=Window.window;if(!w)return null;const todo=[w.contentItem];while(todo.length){const v=todo.pop();if(v.objectName==="e11.table.internal.witness")return v;for(const c of v.children??[])todo.push(c);}return null;}
 readonly property var witness: findWitness()
 sourceModel: ListModel {ListElement {word:"Independent native column";amount:3.71} ListElement {word:"Second row";amount:14.6}}
 header: C.ListViewHeader {
  C.ListViewLabel {text:"#"}
  C.ListViewLabel {text:"Name"}
  C.ListViewLabel {id: headerValue;text:"Value";onWidthChanged:if(t.witness)t.witness.header(headerValue,t)}
 }
 delegate: C.ListViewDelegate {
  id: r
  required property int index
  required property string word
  required property real amount
  C.ListViewLabel {text:String(r.index+1)}
  E.Label {id: labelCell;text:r.word;onLeftPaddingChanged:if(t.witness)t.witness.padding(labelCell,t)}
  E.Label {property real number:r.amount;text:String(number)}
 }
}'''
    def create_table():
        return qml(actor,'(function(){const w='+control_expression(witness)+';w.held=Qt.createQmlObject('+json.dumps(component)+',assistantWorkflowPage);return Qt.isQtObject(w.held);})()')
    assert create_table(), 'The fixture instantiates the actual existing DataTable and FIRST row/header components rather than replacing their width logic'
    actor.until(lambda row:qml(actor,'(function(){const w='+control_expression(witness)+';return Qt.isQtObject(w.held)&&w.held.fittedWidths.length===3&&w.held.fittedWidths.every(x=>Number.isFinite(x)&&x>0);})()'))
    normal=qml(actor,'(function(){const w='+control_expression(witness)+';return {width:w.held.width,columns:w.held.columnWidths,rows:w.held.count};})()')
    assert normal['rows']==2 and all(value>0 for value in normal['columns']), 'Ordinary live column measurements and header widths are valid before the retirement escape'
    if boundary=='padding':
        qml(actor,'(function(){const w='+control_expression(witness)+';w.held.destroy();w.armed=true;})()')
        assert create_table(), 'A fresh ordinary row reaches its first genuine padding setter after the lifetime witness is armed'
    else:
        qml(actor,'('+control_expression(witness)+').armed=true')
        previous_width=actor.last['ui']['width']
        actor.command('resize',width=previous_width-103)
        assert actor.last['ui']['width']!=previous_width, (
            'The original ordinary window resize actually changes the live fitted-header geometry before claiming a width-setter retirement'
        )
    actor.until(lambda row:qml(actor,'('+control_expression(witness)+').hits')==1)
    observed=qml(actor,'(function(){const w='+control_expression(witness)+';return {hits:w.hits,opened:w.opened,retired:!Qt.isQtObject(w.held)};})()')
    assert observed=={'hits':1,'opened':True,'retired':True}, (
        'An actual inner padding/header-width setter invokes ordinary replacement and destroys the original table before its helper tail resumes'
    )
    actor.until(lambda row:not row['ui']['project']['calculating'])
    assert actor.last['ui']['project']['path']==str(successor), 'Ordinary replacement retains its real scientific successor through column-helper retirement'
    wait_positive_tab(actor,'appBar.tab.structure');actor.command('click',name='appBar.tab.structure')
    qml(actor,'('+control_expression(witness)+').armed=false')
    assert create_table(), 'A new current ordinary table still owns valid layout after the retired helper has settled'
    actor.until(lambda row:qml(actor,'(function(){const w='+control_expression(witness)+';return w.held.fittedWidths.length===3&&w.held.fittedWidths.every(x=>Number.isFinite(x)&&x>0);})()'))
    assert qml(actor,'('+control_expression(witness)+').held.count')==2, 'Normal current native row/column layout remains available after retiring the original callback owner'


@pytest.mark.parametrize('initial',['existing_empty','fresh'])
def test_direct_compound_population_stop_retains_prefix_without_default_estimate_or_successor_retarget(main_actor,tmp_path,initial):
    actor=main_actor([[]],show_actions=False)
    if initial=='existing_empty':
        assert actor.command('create',name='stoppedprefix')['reply']['created'], (
            'The existing-empty cancellation channel starts through the ordinary current Session Create owner'
        )
    original=actor.last['ui']['project']
    data=ROOT/'tests/fixtures/background_estimate/meas-lbco-hrpt.xye'
    cif=ROOT/'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    token=actor.begin_current_file_selection()
    assert actor.command('selected_add',token=token,paths=[str(data),str(cif)])['reply']['added'], (
        'The canceled compound uses genuine admitted measured and CIF inputs, with no preconstructed scientific graph'
    )
    selected=actor.last['ui']['selected_files']
    recipe={'project_name':'stoppedprefix','description':'Native population cancellation witness',
        'experiment_name':'stoppedbank','sample_form':'powder','beam_mode':'constant wavelength',
        'radiation_probe':'neutron','scattering_type':'bragg','peak_profile':'cwl-tch-pseudo-voigt',
        'wavelength':1.237,'zero_offset':0.013,'phase_scale':1.1,'exclusions':[],'initial_parameters':[]}
    actor.configure_turns([[tool_call('create_cwl_project','stop-before-next-default-estimate',
        recipe=recipe,data_file_id=next(r['id'] for r in selected if r['name']==data.name),
        cif_file_id=next(r['id'] for r in selected if r['name']==cif.name))]])
    marker='e11.compound.population.stop'
    setup=r'''(function(){const o=Qt.createQmlObject('import QtQuick; Item {objectName:"e11.compound.population.stop";property bool fired:false;property bool cancellable:false;property var owner:null;property var before:null;property var watch:null;property var attempt:null;property var snapshot:null}',contentItem);
    o.snapshot=function(p){if(!p||p.experiments.count!==1)return null;const e=p.experiments.item(0,"experiment");if(!e)return null;const points=[];for(let i=0;i<e.background.count;++i){const v=e.background.item(i,"intensity");points.push({id:e.background.text(i,"id"),position:e.background.text(i,"position"),intensity:v.value,free:v.free});}return {name:p.name,structures:p.structures.count,experiments:p.experiments.count,experiment:e.name,calculation_only:e.calculationOnly,data_file:e.dataFile,points:points};};
    o.attempt=function(){if(o.fired)return;const p=Session.project;const state=o.snapshot(p);if(!state||state.structures!==1||state.calculation_only||!state.data_file)return;o.fired=true;o.owner=p;o.before=state;o.cancellable=Session.assistant.canCancel;Session.assistant.cancel();};
    o.watch=function(){const p=Session.project;if(p)p.projectEdited.connect(o.attempt);o.attempt();};Session.projectChanged.connect(o.watch);o.watch();return true;})()'''
    assert qml(actor,setup), 'A genuine public population/adoption callback is armed before the requested native creation begins'
    try:
        actor.request('Import the selected CIF and measured data into the current app project and use native Estimate.')
        actor.until(lambda r: r['ui']['state']=='idle' and not r['ui']['can_cancel'])
        stopped=qml(actor,'(function(){const o='+control_expression(marker)+';return {fired:o.fired,cancellable:o.cancellable,before:o.before,after:o.snapshot(Session.project),same_owner:Session.project===o.owner};})()')
        assert stopped['fired'] and stopped['cancellable'], (
            'Stop actually executes inside publication of an adopted populated measured prefix, before the next distinct Estimate operation'
        )
        assert stopped['same_owner'] and stopped['after']==stopped['before'], (
            'Cancellation retains the actual adopted setup and every original background point, without a later default Estimate write'
        )
        prefix=actor.last['ui']['project']
        assert prefix['structures']==1 and len(prefix['backgrounds'])==1, (
            'A real canceled population remains an honest partial scientific prefix rather than fabricated rollback'
        )
        measured=[list(map(float,line.split())) for line in data.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
        assert prefix['backgrounds'][0]['input_intensity_count']==len(measured) and prefix['backgrounds'][0]['input_first']==measured[:4], (
            'The canceled retained prefix contains the actual independently supplied measurements, not merely a populated filename or placeholder grid'
        )
        original_rows=[r for r in actor.last['ui']['messages'] if (r.get('payload') or {}).get('tool')=='create_cwl_project']
        assert len(original_rows)==1 and any(not v['complete'] and v.get('adopted') is True and v.get('request_retired') is True and v.get('status')=='partial' and v.get('points')==len(measured) for v in objects(original_rows[0]) if isinstance(v,dict) and 'complete' in v), (
            'The original once row retains incomplete applied-prefix facts after its genuine Stop boundary'
        )
        settled_original=json.loads(json.dumps(original_rows[0].get('payload',{}).get('nativeOutcome')))
        response_count=len(actor.responses())
        actor.append_turn([tool_call('inspect_project','inspect-successor-after-stopped-population')])
        actor.request('Inspect the actual retained partial setup without editing or repeating the canceled operation.')
        actor.until(lambda r: len(actor.responses())==response_count+1 and r['ui']['state']=='idle' and not r['ui']['can_cancel'])
        native_result(actor.responses()[-1])
        later=actor.last['ui']['project']
        assert later['backgrounds']==prefix['backgrounds'] and later['parameters']==prefix['parameters'], (
            'A later admitted read cannot receive the old canceled Estimate effect or silently replay its scientific write'
        )
        later_original=[r for r in actor.last['ui']['messages'] if (r.get('payload') or {}).get('tool')=='create_cwl_project']
        assert len(later_original)==1 and later_original[0].get('payload',{}).get('nativeOutcome')==settled_original, (
            'Refreshing a successor call cannot overwrite or relabel the original canceled once receipt'
        )
        if initial=='existing_empty':
            assert later['name']==original['name'] and later['path']==original['path'] and later['can_undo'], (
                'Current empty-project population preserves its original owner/location and retains its real setup Undo'
            )
            actor.command('undo');actor.until(lambda r:not r['ui']['project']['calculating'])
            assert actor.last['ui']['project']['structures']==0 and actor.last['ui']['project']['backgrounds']==[], (
                'One ordinary population Undo restores the genuine empty graph; no extra canceled Estimate Undo may intervene'
            )
        else:
            assert not later['can_undo'], (
                'Fresh adopted setup has no extra default Estimate Undo after cancellation of that next separate write'
            )
    finally:
        qml(actor,'(function(){const o='+control_expression(marker)+';Session.projectChanged.disconnect(o.watch);if(o.owner)o.owner.projectEdited.disconnect(o.attempt);o.destroy();})()')


@pytest.mark.parametrize('prefix',[b'',b'{"ui":'],ids=['zero','partial'])
def test_main_reader_unsettled_original_reply_cannot_poison_a_successor_or_cleanup(tmp_path,monkeypatch,prefix):
    evidence=tmp_path/'server-evidence.json'
    program="import sys,json;first=json.loads(sys.stdin.readline());sys.stdout.buffer.write(bytes.fromhex(sys.argv[2]));sys.stdout.buffer.flush();rest=sys.stdin.read();reply={'ui':{'alive':True},'reply':{'op':first['op'],'later_input':rest}};open(sys.argv[1],'w').write(json.dumps(reply));sys.stdout.write(json.dumps(reply)+'\\n');sys.stdout.flush()"
    actor=MainActor.__new__(MainActor);actor.folder=tmp_path
    actor.process=subprocess.Popen([sys.executable,'-c',program,str(evidence),prefix.hex()],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    actor.stderr=actor.process.stderr
    actor.last={'ui':{'controls':[{'name':'home.start','visible':True,'enabled':True}]}}
    actual_select=select.select;calls=0
    def finite_boundary(*args):
        nonlocal calls
        calls+=1
        return actual_select(*args) if prefix and calls==1 else ([],[],[])
    monkeypatch.setattr(select,'select',finite_boundary)
    try:
        with pytest.raises(AssertionError,match='complete observation'):
            actor.command('original')
        boundary=json.loads((tmp_path/'command-boundary.json').read_text())
        assert (tmp_path/'unsettled-command-bytes.bin').read_bytes()==prefix, (
            'Actually received zero or partial bytes remain attached to the original outstanding command'
        )
        with pytest.raises(RuntimeError,match='no successor command was sent'):
            actor.command('click',name='appBar.tab.structure')
        assert json.loads((tmp_path/'command-boundary.json').read_text())==boundary, (
            'The automatic Home Start prelude cannot replace an unsettled original boundary or send another command'
        )
        monkeypatch.setattr(select,'select',actual_select)
        actor.close()
        late=json.loads(evidence.read_text())
        assert late['reply']=={'op':'original','later_input':''}, (
            'Independent child stdin proves neither successor nor automatic cleanup query was sent before its late original reply'
        )
        assert json.loads((tmp_path/'command-boundary.json').read_text())==boundary, (
            'Cleanup retires the owned process without relabeling original bytes as a Session last-error result'
        )
        assert json.loads((tmp_path/'host-exit.json').read_text())['exit']==0, (
            'The finite actual pipe server closes normally after its original late reply and stdin EOF'
        )
    finally:
        if actor.process.poll() is None:
            if not actor.process.stdin.closed:actor.process.stdin.close()
            actor.process.wait(timeout=2)
        if not actor.process.stdout.closed:actor.process.stdout.close()
        if not actor.stderr.closed:actor.stderr.close()


@pytest.mark.parametrize('packet',[b'{"ui":',b'{bad json}\n',b'{"ui":"\xff"}\n'],ids=['eof_partial','malformed_json','malformed_utf8'])
def test_main_reader_broken_frame_retains_original_bytes_and_refuses_reuse(tmp_path,packet):
    program="import sys;sys.stdin.readline();sys.stdout.buffer.write(bytes.fromhex(sys.argv[1]));sys.stdout.buffer.flush()"
    actor=MainActor.__new__(MainActor);actor.folder=tmp_path
    actor.process=subprocess.Popen([sys.executable,'-c',program,packet.hex()],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1);actor.stderr=actor.process.stderr
    try:
        with pytest.raises((AssertionError,UnicodeDecodeError,json.JSONDecodeError)):
            actor.command('broken-original')
        assert (tmp_path/'unsettled-command-bytes.bin').read_bytes()==packet, (
            'EOF, UTF-8 and JSON failures preserve the actual original raw frame before decoding or cleanup can discard it'
        )
        with pytest.raises(RuntimeError,match='no successor command was sent'):
            actor.command('successor')
        actor.close()
        assert json.loads((tmp_path/'unsettled-command.json').read_text())['op']=='broken-original', (
            'A broken original frame cannot become a successful response under another command label'
        )
    finally:
        if actor.process.poll() is None:actor.process.wait(timeout=2)
        if not actor.process.stdout.closed:actor.process.stdout.close()
        if not actor.stderr.closed:actor.stderr.close()


def test_main_reader_complete_fifo_and_predicate_timeout_keep_usable_ownership(tmp_path):
    program="import sys,json\nfor line in sys.stdin:\n x=json.loads(line);o=x['op'];print('ordinary library notice',flush=True);print(json.dumps({'host_error':'complete deliberate host failure'} if o=='host_failure' else {'ui':{'alive':True,'controls':[],'state':'idle','last_error':'','project':None},'reply':{'op':o,'value':''},'test_storage':sys.argv[1]}),flush=True)"
    actor=MainActor.__new__(MainActor);actor.folder=tmp_path
    actor.process=subprocess.Popen([sys.executable,'-c',program,str(tmp_path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1);actor.stderr=actor.process.stderr
    try:
        assert actor.command('first')['reply']['op']=='first', (
            'A normal complete FIFO reply remains correctly assigned while non-object diagnostic lines are retained'
        )
        with pytest.raises(AssertionError,match='did not settle'):
            actor.until(lambda value:False,seconds=0.001)
        assert json.loads((tmp_path/'command-boundary.json').read_text())['reply_observed'], (
            'The lifecycle predicate fails only after an actual complete response, leaving no unread command obligation'
        )
        with pytest.raises(AssertionError,match='complete deliberate host failure'):
            actor.command('host_failure')
        assert actor.command('successor')['reply']['op']=='successor', (
            'Fully replied predicate and correctly framed host errors do not poison a valid subsequent FIFO command'
        )
        assert (tmp_path/'last-lifecycle-receipt.json').is_file(), (
            'Compact lifecycle diagnostics retain the complete original receipt in their existing local artifact'
        )
        actor.close()
    finally:
        if actor.process.poll() is None:
            if not actor.process.stdin.closed:actor.process.stdin.close()
            actor.process.wait(timeout=2)
        if not actor.process.stdout.closed:actor.process.stdout.close()
        if not actor.stderr.closed:actor.stderr.close()


@pytest.mark.parametrize('evidence_fault',[False,True],ids=['notice_only','notice_and_failure_artifact'])
def test_main_reader_notice_io_failure_keeps_original_owner_through_cleanup(tmp_path,monkeypatch,evidence_fault):
    evidence=tmp_path/'server-evidence.json'
    packet=b'library notice\n{"ui":{"alive":true},"reply":{"value":"original"}}\n'
    program="import sys,json,os;first=json.loads(sys.stdin.readline());os.write(1,bytes.fromhex(sys.argv[2]));rest=sys.stdin.read();open(sys.argv[1],'w').write(json.dumps({'first':first,'later_input':rest}))"
    actor=MainActor.__new__(MainActor);actor.folder=tmp_path
    actor.process=subprocess.Popen([sys.executable,'-c',program,str(evidence),packet.hex()],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1);actor.stderr=actor.process.stderr
    original_open=Path.open
    def local_fault(path,*args,**kwargs):
        if path.name=='host.stdout-diagnostics' or (evidence_fault and path.name.startswith('unsettled-command')):
            raise PermissionError('deliberate local notice evidence failure')
        return original_open(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',local_fault)
    try:
        with pytest.raises(PermissionError,match='local notice evidence failure'):
            actor.command('original')
        boundary=json.loads((tmp_path/'command-boundary.json').read_text())
        assert actor._unsettled_bytes==packet and actor._unsettled_command['op']=='original', (
            'Actual coalesced notice and unread reply bytes remain original-owned even when both diagnostic persistence paths fail'
        )
        with pytest.raises(RuntimeError,match='no successor command was sent'):
            actor.command('successor')
        actor.close()
        observed=json.loads(evidence.read_text())
        assert observed['first']['op']=='original' and observed['later_input']=='', (
            'Independent actual pipe stdin proves notice-I/O failure cannot send successor or automatic cleanup queries'
        )
        assert json.loads((tmp_path/'command-boundary.json').read_text())==boundary, (
            'Local diagnostic I/O cannot overwrite the incomplete original command boundary with a fabricated cleanup result'
        )
    finally:
        if actor.process.poll() is None:
            if not actor.process.stdin.closed:actor.process.stdin.close()
            actor.process.wait(timeout=2)
        if not actor.process.stdout.closed:actor.process.stdout.close()
        if not actor.stderr.closed:actor.stderr.close()


@pytest.mark.parametrize('show_actions',[False,True],ids=['off','on'])
@pytest.mark.parametrize('category',['invalid_argument','out_of_scope','unsupported_model'])
def test_actual_native_preparation_refusals_keep_specific_projected_feedback_without_writes(main_actor,tmp_path,show_actions,category):
    actor=main_actor([[]],show_actions=show_actions)
    if category=='unsupported_model':
        assert actor.command('create',name='diagnostic_owner')['reply']['created'], (
            'Unsupported relation diagnostics retain a genuine ordinary current project with an empty scientific graph'
        )
        call=tool_call('add_relations','specific-preparation-refusal',aliases=[{'id':'native_alias','path':'structure.cell.length_a'}],
            constraints=[{'id':'native_constraint','expression':'native_alias = native_alias','enabled':True}])
    else:
        project=copied_estimate_project(tmp_path)
        assert actor.command('open',path=str(project))['reply']['opened'], (
            'Native parameter diagnostic controls use the unchanged independent measured fixture and current owner'
        )
        actor.until(lambda row:not row['ui']['project']['calculating'])
        if category=='invalid_argument':
            call=tool_call('set_parameters','specific-preparation-refusal',values=[{'path':'unknown.owner.field','value':1.237}])
        else:
            dependent=next(p for p in actor.last['ui']['project']['parameters'] if p['dependence']!=0)
            call=tool_call('set_free','specific-preparation-refusal',flags=[{'path':dependent['path'],'free':True}])
    before=actor.last['ui']['project']
    actor.configure_turns([[call,tool_call('inspect_project','continue-after-specific-refusal')]])
    actor.connect();actor.request('Validate this explicit rejected request and inspect the unchanged current project.')
    actor.until(lambda row:len(actor.responses())==2 and row['ui']['state']=='idle')
    first=actor.responses()[0]['result'];body=json.loads(first['contentItems'][0]['text'])
    expected={'invalid_argument':'invalid_arguments','out_of_scope':'refused','unsupported_model':'unavailable'}[category]
    assert first['success'] is False and body['code']==expected, (
        'Actual model-visible native bytes retain each original preparation refusal category after the production projector'
    )
    assert any(d['code']==category and d['message'] and d['severity']=='error' for d in body['diagnostics']) and body['message'], (
        'Specific sanitized native diagnostics and their useful app message survive instead of the generic scope/capacity text'
    )
    native_result(actor.responses()[1]);after=actor.last['ui']['project']
    def science(project):
        return {'name':project['name'],'path':project['path'],'structure_rows':project['structure_rows'],
            'backgrounds':project['backgrounds'],'aliases':project['aliases'],'constraints':project['constraints'],'can_undo':project['can_undo'],
            'parameters':[{k:p[k] for k in ('path','value','free','dependence')} for p in project['parameters']]}
    assert science(after)==science(before) and actor.last['ui']['connected'], (
        'Preparation refusals cannot write science, replace its owner, add Undo or retire the account before a valid read continuation'
    )


def test_recognized_preparation_categories_survive_actual_wire_and_byte_projection(main_actor):
    actor=main_actor([[]])
    # Resource allocation failure is a projection-only control: no forced OOM,
    # synthetic work quota or claim of end-to-end VM allocation-path execution.
    categories=[('invalid_argument','refused','invalid_arguments'),('out_of_scope','refused','refused'),
        ('unsupported_model','unavailable','unavailable'),('resource_exhausted','refused','resource_exhausted')]
    cases=[{'source':{'status':status,'code':code,'message':'Scoped native validation Ω',
        'diagnostics':[{'code':diagnostic,'message':'Scoped native validation Ω','severity':'error','actionable':True}]}}
        for diagnostic,status,code in categories]
    actual=actor.command('outgoing_projection_cases',cases=cases)['reply']['cases']
    for (diagnostic,status,code),row in zip(categories,actual,strict=True):
        wire=json.loads(row['wire'])
        assert not row['rejected'] and row['size']==row['wire_bytes']==len(row['wire'].encode()), (
            'Every recognized native refusal reaches the actual compact wire with one accurate byte-count owner'
        )
        assert wire['code']==code and wire['diagnostics'][0]['code']==diagnostic and wire['message']=='Scoped native validation Ω', (
            'Literal original category meanings survive real materialization rather than only a constructed catch object'
        )


"""Private assembly for the existing Main actor; no product state or new runner."""
class HistorySyncGate:
    def __init__(self, folder):
        self.folder = folder
        self.control = folder / 'history-sync-control'
        self.receipt = folder / 'history-sync-receipt.jsonl'
        self.release = folder / 'release-history-sync'
        self.epoch = 0
        self.target = None

    def rows(self):
        return [json.loads(line) for line in self.receipt.read_text().splitlines()] if self.receipt.exists() else []

    def arm(self, actor, mode):
        storage = Path(actor.last['test_storage']).resolve()
        candidates = list(storage.rglob('assistant/history.json'))
        assert len(candidates) == 1, 'The hold targets the actual normal canonical file created by genuine prior user work'
        self.target = candidates[0]
        assert self.target.resolve().is_relative_to(storage) and not self.target.is_symlink()
        assert self.target.stat().st_mode & 0o777 == 0o600
        assert '\n' not in str(self.target) and '\n' not in str(self.release)
        self.epoch += 1
        (self.folder / f'history-before-{self.epoch}.json').write_bytes(self.target.read_bytes())
        (self.folder / f'history-target-{self.epoch}.json').write_text(json.dumps({'target':str(self.target),'mode':mode,'epoch':self.epoch})+'\n')
        self.release.unlink(missing_ok=True)
        temporary = self.control.with_suffix('.new')
        temporary.write_text(f'{mode}\n{self.target}\n{self.release}\n{self.epoch}\n')
        temporary.replace(self.control)

    def opened(self):
        return any(row['epoch'] == self.epoch and row['phase'] == 'entered' for row in self.rows())

    def disk(self):
        return json.loads(self.target.read_text())

    def finish(self):
        self.release.touch()
        self.control.unlink(missing_ok=True)
        if self.target and self.target.is_file():
            (self.folder / f'history-at-release-{self.epoch}.json').write_bytes(self.target.read_bytes())


def seeded_history_actor(main_actor, gate, *, calls, project, hold_final=True):
    actor = main_actor([[], calls], hold_final=hold_final)
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    actor.gate.touch()
    actor.connect()
    actor.request('Establish ordinary canonical history before the independent persistence boundary.')
    actor.until(lambda row: row['ui']['state'] == 'idle' and not row['ui']['can_cancel'])
    candidates = list(Path(actor.last['test_storage']).rglob('assistant/history.json'))
    actor.until(lambda row: bool(list(Path(row['test_storage']).rglob('assistant/history.json'))))
    gate.target = next(Path(actor.last['test_storage']).rglob('assistant/history.json'))
    actor.until(lambda row: any(x.get('text') == 'Establish ordinary canonical history before the independent persistence boundary.' for x in gate.disk()))
    actor.gate.unlink()
    return actor


def canonical_row_map(rows):
    return {row['id']: row for row in rows}


def assert_canonical_disk_row(disk, expected):
    rows = canonical_row_map(disk)
    assert expected['id'] in rows, 'The actual native receipt survives the full canonical disk snapshot'
    actual = rows[expected['id']]
    for key in ('kind', 'status', 'text', 'payload', 'workScope'):
        if key in expected:
            assert actual[key] == expected[key], 'Disk retains exact canonical native/evidence fields, not a producer success flag'


@pytest.fixture(scope='module')
def history_sync_library(tmp_path_factory):
    folder=tmp_path_factory.mktemp('canonical-history-actual-sync')
    library=folder/'history-sync.so'
    command=['cc','-shared','-fPIC','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'tests/fixtures/report_storage'),str(ROOT/'tests/fixtures/report_storage/history_sync.c'),'-o',str(library),*([] if sys.platform=='darwin' else ['-ldl'])]
    result=subprocess.run(command,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
    (folder/'compile-command.json').write_text(json.dumps(command)+'\n')
    return library

@pytest.fixture
def history_sync_gate(tmp_path,monkeypatch,history_sync_library):
    gate=HistorySyncGate(tmp_path)
    monkeypatch.setenv('DYLD_INSERT_LIBRARIES' if sys.platform=='darwin' else 'LD_PRELOAD',str(history_sync_library))
    monkeypatch.setenv('EDI_TEST_HISTORY_CONTROL',str(gate.control))
    monkeypatch.setenv('EDI_TEST_HISTORY_RECEIPT',str(gate.receipt))
    yield gate
    gate.finish()


def history_poll(predicate,seconds=30):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        try:
            value=predicate()
            if value:return value
        except (FileNotFoundError,json.JSONDecodeError):pass
        time.sleep(.005)
    raise AssertionError('Actual bounded history-file/receipt condition was not observed')


def test_history_sync_keeps_main_heartbeat_stop_native_once_and_complete_disk_rows(main_actor,tmp_path,history_sync_gate):
    gate=history_sync_gate
    project=copied_estimate_project(tmp_path)
    calls=[tool_call('set_free','history-once-free',flags=[{'path':'experiment.instrument.calib_twotheta_offset','free':True}])]
    actor=seeded_history_actor(main_actor,gate,calls=calls,project=project)
    baseline=gate.disk()
    qml(actor,'Qt.createQmlObject(\'import QtQuick; Item { objectName: "e11.history.heartbeat"; visible:false; property int ticks:0; Timer { interval:1; repeat:true; running:true; onTriggered:parent.ticks++ } }\',contentItem) !== null')
    heartbeat=control_expression('e11.history.heartbeat')+'.ticks'
    before=qml(actor,heartbeat)
    try:
        gate.arm(actor,'hold')
        actor.request('Change this exact native flag once and retain the actual step evidence while history persistence is held.')
        history_poll(gate.opened,seconds=3)
        assert actor.command('inspect')['ui']['connected'],'Held archive I/O cannot retire the real account or stop Main observations'
        actor.until(lambda row:len(actor.responses())==1)
        native_result(actor.responses()[0])
        assert qml(actor,heartbeat)>before,'The real current Main Qt timer advances while the actual history sync remains held'
        assert not any(row['phase'] in {'released','auto_release'} for row in gate.rows()),'The writer is still actually held during the native/heartbeat observations'
        native=next(row for row in actor.last['ui']['messages'] if (row.get('payload') or {}).get('tool')=='set_free')
        changed=next(x for x in actor.last['ui']['project']['parameters'] if x['path']=='experiment.instrument.calib_twotheta_offset')
        assert changed['free'] is True
        actor.command('cancel')
        actor.until(lambda row:not row['ui']['can_cancel'] and row['ui']['state']=='idle')
        assert len(actor.responses())==1,'Genuine native Stop never replays the already applied native call'
        expected={row['id']:row for row in actor.last['ui']['messages']}
        gate.finish()
        history_poll(lambda:set(expected).issubset(canonical_row_map(gate.disk())))
        disk=gate.disk()
        for row in expected.values():
            assert_canonical_disk_row(disk,row)
        actual=canonical_row_map(disk)[native['id']]
        assert actual.get('workEvidence') and actual.get('workInputs') and actual.get('workRuntime'),'The latest canonical file retains the real supplement fields as well as primary native receipts'
        assert all(not row['main_thread'] for row in gate.rows() if row['phase']=='entered'),'Actual canonical sync happens off the GUI owner thread'
        assert any(row['phase']=='sync_returned' for row in gate.rows())
        assert not any(row['phase']=='auto_release' for row in gate.rows())
        assert baseline and actor.last['ui']['project']['parameters'],'Neither retained baseline nor scientific owner is replaced by the writer'
    finally:gate.finish()


def test_failed_clear_preserves_original_disk_cause_then_new_conversation_is_durable(main_actor,tmp_path,history_sync_gate):
    gate=history_sync_gate
    actor=seeded_history_actor(main_actor,gate,calls=[],project=copied_estimate_project(tmp_path))
    before=gate.disk();old_ids=set(canonical_row_map(before));model=actor.last['ui']['project']
    try:
        gate.arm(actor,'fail')
        actor.command('clear_history')
        history_poll(lambda:any(row['phase']=='failed' for row in gate.rows()),seconds=3)
        assert gate.disk()==before,'Failed atomic Clear preserves the exact previous canonical file before any diagnostic assertion'
        actor.until(lambda row:bool(row['ui']['last_error']),seconds=3)
        assert not actor.last['ui']['messages'],'Explicit logical Clear retires the old conversation immediately despite its failed disk replacement'
        assert gate.disk()==before,'Failed atomic Clear preserves the exact previously published canonical bytes/rows'
        assert actor.last['ui']['connected'] and actor.last['ui']['project']==model,'Storage failure cannot sign out or alter the current scientific owner'
        gate.finish()
        actor.gate.touch();actor.connect()
        actor.request('New conversation after the failed durable Clear, without replaying the discarded native authority.')
        actor.until(lambda row:row['ui']['state']=='idle' and not row['ui']['can_cancel'])
        expected={row['id']:row for row in actor.last['ui']['messages']}
        history_poll(lambda:set(expected).issubset(canonical_row_map(gate.disk())) and not (old_ids&set(canonical_row_map(gate.disk()))))
        for row in expected.values():
            assert_canonical_disk_row(gate.disk(),row)
        assert not old_ids&set(canonical_row_map(gate.disk())),'A later accepted full snapshot cannot resurrect pre-Clear canonical rows'
    finally:gate.finish()


def test_held_old_history_clear_new_conversation_and_vm_destruction_flush_latest(main_actor,tmp_path,history_sync_gate):
    gate=history_sync_gate
    actor=seeded_history_actor(main_actor,gate,calls=[tool_call('inspect_project','old-history-step')],project=copied_estimate_project(tmp_path))
    try:
        gate.arm(actor,'hold')
        actor.request('Old original conversation while the actual archive writer is held.')
        history_poll(gate.opened,seconds=3)
        actor.until(lambda row:len(actor.responses())==1)
        old_ids={row['id'] for row in actor.last['ui']['messages']}
        actor.command('clear_history')
        assert not actor.last['ui']['messages'],'Clear retires memory/authority before durable I/O can complete'
        actor.append_turn([tool_call('inspect_project','new-history-step')]);actor.gate.touch();actor.connect()
        actor.request('New original conversation that must survive owner destruction and supersede the held pre-Clear file.')
        actor.until(lambda row:len(actor.responses())==2 and row['ui']['state']=='idle')
        expected={row['id']:row for row in actor.last['ui']['messages']}
        assert expected and not old_ids&set(expected)
        native=next(row for row in expected.values() if (row.get('payload') or {}).get('tool')=='inspect_project')
        actor.command('destroy')
        assert actor.process.poll() is None,'Real VM/engine destruction returns while an accepted archive sync is still held'
        assert not any(row['phase'] in {'released','auto_release'} for row in gate.rows())
        gate.finish()
        history_poll(lambda:set(expected).issubset(canonical_row_map(gate.disk())) and not (old_ids&set(canonical_row_map(gate.disk()))))
        for row in expected.values():
            assert_canonical_disk_row(gate.disk(),row)
        assert not any(row['phase']=='auto_release' for row in gate.rows())
    finally:gate.finish()


# Independent defaults: unchanged dev08cafc45 ProjectMetadata/model.hpp4423,
# empty_project/io.cpp3258, Session::createProject/session.cpp599, original
# GetStartedGroup and ProjectDescriptionDialog; not candidate receipt values.
@pytest.mark.parametrize('show_actions',[False,True],ids=['off','on'])
def test_name_only_native_create_keeps_original_optional_metadata_defaults(main_actor,tmp_path,show_actions):
    name='optional_'+hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    actor=main_actor([[tool_call('create_project','normal-name-only',name=name)]],show_actions=show_actions)
    assert not actor.last['ui']['project']
    documents=Path(actor.last['ui']['environment']['documents_root'])
    expected=documents/name
    assert not expected.exists(),'Only the actual normal current Session owner may create its absent destination'
    preferences=qml(actor,'({rule:Preferences.newProjectSuRule,libraries:Preferences.newReportLibraries === "embedded"})')
    actor.connect();actor.command('clear_ui_sequence')
    actor.request('Create a new project with the requested name and retain every omitted ordinary metadata default.')
    actor.until(lambda row:len(actor.responses())==1 and row['ui']['state']=='idle',visible_progress=show_actions)
    result=native_result(actor.responses()[0])
    assert result['adopted'] and result['complete'] and result['saved'] is True and result['presentation_complete']
    assert result['name']==name and Path(result['path'])==expected
    assert result['title']=='Untitled Project' and result['description']=='',(
        'An omitted title/description retains original dev metadata defaults instead of becoming a false precondition')
    actual=qml(actor,'({name:Session.project.name,title:Session.project.title,description:Session.project.description,authors:Session.project.authors,rule:Session.project.suRule,libraries:Session.project.report.embedLibraries})')
    assert actual=={'name':name,'title':'Untitled Project','description':'','authors':'','rule':preferences['rule'],'libraries':preferences['libraries']}
    assert actor.last['ui']['project']['structures']==0 and actor.last['ui']['project']['backgrounds']==[]
    import shlex
    text=(expected/'project.edi').read_text()
    metadata={parts[0]:parts[1] for line in text.splitlines() if len(parts:=shlex.split(line,comments=True))==2 and parts[0] in {'_metadata.name','_metadata.title'}}
    assert metadata=={'_metadata.name':name,'_metadata.title':'Untitled Project'},'Real ordinary Save writes original defaults independently of the native reply'
    events=actor.last['ui']['ui_sequence']
    if show_actions:
        assert any(e['kind']=='mouse_press' and e.get('create_contains_press') for e in events)
        assert any(e['kind'] in {'key_press','input_method'} and e['focus']=='createProject.name' and e['dialog_visible'] for e in events)
        assert any(e['kind']=='mouse_press' and e.get('confirm_contains_press') and e['dialog_name']==name for e in events),(
            'Name-only ON actually opens, edits and confirms the original normal dialog')
    else:
        assert not any(e['kind'].startswith('pointer_') or e['dialog_visible'] for e in events if not e['project_present'])


@pytest.mark.parametrize('show_actions',[False,True],ids=['off','on'])
def test_native_fit_suppresses_auto_results_but_original_user_fit_still_opens_them(main_actor,tmp_path,show_actions):
    actor=main_actor([[tool_call('run_fit','assistant-fit-no-results-overlay')]],show_actions=show_actions)
    path=tmp_path/'ordinary-fit';shutil.copytree(ROOT/'tests/fixtures/fit_quality/uncertainty',path)
    assert actor.command('open',path=str(path))['reply']['opened']
    actor.until(lambda row:not row['ui']['project']['calculating'])
    wait_positive_tab(actor,'appBar.tab.structure');actor.command('click',name='appBar.tab.structure')
    actor.until(lambda row:any(c['name']=='statusBar.fit.button' and c['enabled'] and c['fully_exposed'] for c in row['ui']['controls']))
    before=actor.last['ui']['project']['parameters']
    actor.connect();actor.request('Fit this current native fixture without opening a separate fit-results popup.')
    actor.until(lambda row:len(actor.responses())==1 and row['ui']['state']=='idle',visible_progress=show_actions)
    native_result(actor.responses()[0])
    assert qml(actor,'Session.project.fit.canUndo')
    assert any(a['value']!=b['value'] for a,b in zip(before,actor.last['ui']['project']['parameters'],strict=True))
    def exposed_results(row):
        return any(c['name']=='fit.results.list' and c['visible'] and c['enabled'] and c['fully_exposed'] for c in row['ui']['controls'])
    assert not exposed_results(actor.last),(
        'Assistant-origin Fit leaves the real Main unobscured by automatic Results in both action modes')
    actor.command('undo')
    assert actor.last['ui']['project']['parameters']==before,'Original native fit Undo retains every value/free/dependent field'
    actor.until(lambda row:any(c['name']=='statusBar.fit.button' and c['enabled'] and c['fully_exposed'] for c in row['ui']['controls']))
    actor.command('click',name='statusBar.fit.button')
    actor.until(exposed_results)
    assert qml(actor,'Session.project.fit.canUndo'),'An actual ordinary user status-bar Fit still owns its result and original popup'
    actor.command('undo')
    assert actor.last['ui']['project']['parameters']==before,'Ordinary user Fit keeps its exact existing Undo behavior'


@pytest.mark.parametrize('show_actions',[False,True],ids=['off','on'])
def test_unsaved_native_setup_autonomous_save_uses_original_suggested_folder(main_actor,tmp_path,show_actions):
    actor=main_actor([[]],show_actions=show_actions)
    assert not actor.last['ui']['project']
    documents=Path(actor.last['ui']['environment']['documents_root'])
    data=ROOT/'tests/fixtures/background_estimate/meas-lbco-hrpt.xye'
    cif=ROOT/'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    token=actor.begin_current_file_selection()
    assert actor.command('selected_add',token=token,paths=[str(data),str(cif)])['reply']['added']
    files=actor.last['ui']['selected_files'];name='unsaved_'+hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    recipe={'project_name':name,'description':'Explicit native unsaved-setup persistence witness',
        'experiment_name':'sourcebank','sample_form':'powder','beam_mode':'constant wavelength',
        'radiation_probe':'neutron','scattering_type':'bragg','peak_profile':'cwl-tch-pseudo-voigt',
        'wavelength':1.237,'zero_offset':0.013,'phase_scale':1.1,'exclusions':[],'initial_parameters':[]}
    actor.configure_turns([[tool_call('create_cwl_project','native-unsaved-setup',recipe=recipe,
        data_file_id=next(x['id'] for x in files if x['name']==data.name),
        cif_file_id=next(x['id'] for x in files if x['name']==cif.name))]])
    actor.request('Create this requested native setup from its admitted files; do not save until the following separate action.')
    actor.until(lambda row:len(actor.responses())==1 and row['ui']['state']=='idle',visible_progress=show_actions)
    native_result(actor.responses()[0]);actor.until(lambda row:not row['ui']['project']['calculating'])
    assert actor.last['ui']['project']['path']=='','This exact channel genuinely begins unsaved; a normal pre-saved Create is not a substitute'
    expected=documents/name
    assert not expected.exists()
    # dev08cafc45 Session::suggestedSaveTarget670: an unsaved ordinary native
    # project defaults to Documents/folderNameFor(name); desktop original
    # Main.saveAsChoice defaults Folder and copy=false. No chooser is supplied.
    from urllib.parse import urlparse,unquote
    original=qml(actor,'String(Session.suggestedSaveTarget(false))')
    assert Path(unquote(urlparse(original).path))==expected
    actor.append_turn([tool_call('save_project','native-unsaved-current-save',destination='current')])
    actor.command('clear_ui_sequence')
    actor.request('Save this current unsaved project using the app\'s original normal defaults, without operator format or path assistance.')
    actor.until(lambda row:len(actor.responses())==2 and row['ui']['state']=='idle',visible_progress=show_actions)
    saved=native_result(actor.responses()[-1])
    assert saved['saved'] and saved['committed'] and saved['active'] and not saved.get('uncertain',False)
    assert Path(actor.last['ui']['project']['path'])==expected and (expected/'project.edi').is_file()
    assert not any(row['name'] in {'saveAs.folder','saveAs.zip','saveAs.copy'} and row['visible'] and row['enabled'] for row in actor.last['ui']['controls']),(
        'Native Save settles its ordinary owner instead of leaving the unanswerable format dialog pending')
    actor.until(lambda row:not row['ui']['project']['calculating'])
    before=actor.last['ui']['project'];flags=[(p['path'],p['free'],p['dependence']) for p in before['parameters']]
    assert before['structures']==1 and before['backgrounds'][0]['input_intensity_count']>0
    assert actor.command('open',path=str(expected))['reply']['opened'],'A genuinely complete CIF/measured native setup reopens through the original whole-project API'
    actor.until(lambda row:not row['ui']['project']['calculating'])
    after=actor.last['ui']['project']
    assert after['structure_rows']==before['structure_rows']
    assert [(p['path'],p['free'],p['dependence']) for p in after['parameters']]==flags
    for key in ('type','mode','points','input_count','input_intensity_count','input_sigma_count','input_first'):
        assert after['backgrounds'][0][key]==before['backgrounds'][0][key],(
            'Ordinary autonomous Save/Open preserves actual inputs and decoded background identity/values without a fabricated filename or measurement')


def test_original_reveal_accepts_same_exposed_target_after_real_window_resize_without_scroll(
    main_actor, tmp_path
):
    """A reached zero-delta reveal needs current geometry, not a scroll-delta proxy.

    NOT_REACHED is an explicit skip/artifact, never an expected red or pass.
    No forced contentY, group/popup/selection property or scientific seed.
    """
    actor = main_actor([[]], show_actions=True)
    project = tmp_path / 'ordinary-reveal-project'
    shutil.copytree(ROOT / 'tests/fixtures/constraint_expressions/project', project)
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    original = actor.last['ui']['project']
    paths = {
        row['field']: row['path'] for row in original['parameters']
        if row['category'] == 'cell'
    }
    call = tool_call(
        'add_relations', 'original-target-height-resize-once',
        aliases=[{'id': 'e11_reveal_a', 'path': paths['length_a']},
                 {'id': 'e11_reveal_b', 'path': paths['length_b']}],
        constraints=[{'id': 'e11_reveal_pair',
                      'expression': 'e11_reveal_b = e11_reveal_a', 'enabled': True}],
    )
    actor.configure_turns([[call]])
    actor.connect()
    wait_positive_tab(actor, 'appBar.tab.analysis')
    actor.command('click', name='appBar.tab.analysis')
    initial = qml(actor, '(function(){const before=window.height;window.height=window.minimumHeight;'
                  'return {before:before,requested:window.minimumHeight,actual:window.height};})()')
    marker = 'e11.reveal.resizeWitness'
    setup = r'''(function(){
        const group=GROUP,field=FIELD;
        if(!group||!field)return {installed:false,reason:'original_controls_absent'};
        const o=Qt.createQmlObject('import QtQuick; Item {objectName:"e11.reveal.resizeWitness"; visible:false; width:0;height:0; property bool fired:false; property var originalProject:null; property var originalAssistant:null; property var target:null; property var viewport:null; property var callback:null; property var before:null; property var resized:null; property var samples:[]; property real requestedHeight:0; property string reason:"no_pending_original_scroll_cue"}',contentItem);
        o.originalProject=Session.project;o.originalAssistant=Session.assistant;
        function rect(x,base){const points=[[0,0],[x.width,0],[0,x.height],[x.width,x.height]].map(p=>x.mapToItem(base,p[0],p[1]));return {left:Math.min(...points.map(p=>p.x)),right:Math.max(...points.map(p=>p.x)),top:Math.min(...points.map(p=>p.y)),bottom:Math.max(...points.map(p=>p.y))};}
        function owner(){const page=window.assistantWorkflowPage;return Session.project===o.originalProject&&Session.assistant===o.originalAssistant&&page&&page.current&&page.enabled&&page.pageName==='analysis'&&!page.assistantCovered&&!assistantPanel.visible;}
        function fullyExposed(x){
            if(!x||x.Window.window!==contentItem.Window.window||!owner())return false;
            const b=rect(x,contentItem);if(!Object.values(b).every(Number.isFinite)||b.right<=b.left||b.bottom<=b.top)return false;
            let clip={left:0,top:0,right:contentItem.width,bottom:contentItem.height};
            for(let a=x;a;a=a.parent){if(!a.visible||!a.enabled||a.opacity===0)return false;if(a.clip){const r=rect(a,contentItem);clip={left:Math.max(clip.left,r.left),top:Math.max(clip.top,r.top),right:Math.min(clip.right,r.right),bottom:Math.min(clip.bottom,r.bottom)};}if(a===contentItem)break;}
            return b.left>=clip.left&&b.right<=clip.right&&b.top>=clip.top&&b.bottom<=clip.bottom;
        }
        function snapshot(label){const v=o.viewport,t=o.target;return {label:label,ownerCurrent:owner(),project:String(Session.project),assistant:String(Session.assistant),target:String(t),viewport:String(v),window:String(contentItem.Window.window),height:window.height,requestedHeight:o.requestedHeight,targetEnabled:t?t.enabled:null,targetBounds:t?rect(t,contentItem):null,targetFullyExposed:t?fullyExposed(t):false,contentY:v?v.contentY:null,originY:v?v.originY:null,contentHeight:v?v.contentHeight:null,viewportHeight:v?v.height:null,interactive:v?v.interactive:null,atYEnd:v?v.atYEnd:null,atYBeginning:v?v.atYBeginning:null};}
        o.callback=function(position){
            if(o.fired||!owner())return;
            const wanted=group.collapsed?group.titleArea:field;
            if(!wanted||!wanted.visible||!wanted.enabled||wanted.Window.window!==contentItem.Window.window)return;
            let viewport=null,bounds=null;
            // The nearest actual clipping scroll ancestor is the original
            // layout owner, not the first arbitrary hover/list object.
            for(let a=wanted.parent;a;a=a.parent){
                if(Number.isFinite(a.contentY)&&Number.isFinite(a.contentHeight)&&a.height>0){const b=rect(wanted,a);if(b.top<0||b.bottom>a.height){viewport=a;bounds=b;break;}}
                if(String(a.objectName).endsWith('.manualSidebar'))break;
            }
            if(!viewport||bounds.top<0||bounds.bottom<=viewport.height||bounds.bottom-bounds.top>viewport.height)return;
            const vr=rect(viewport,contentItem);
            if(vr.left<0||vr.top<0||vr.right>contentItem.width||vr.bottom>contentItem.height)return;
            const center=viewport.mapToItem(contentItem,viewport.width/2,viewport.height/2);
            if(Math.abs(position.x-center.x)>1||Math.abs(position.y-center.y)>1)return;
            let available=0;try{available=Number(Screen.desktopAvailableHeight);}catch(error){o.reason='screen_height_unavailable';return;}
            const requested=Math.min(available,Math.ceil(window.height+bounds.bottom-viewport.height+wanted.height*2));
            if(!Number.isFinite(requested)||requested<=window.height){o.reason='no_safe_ordinary_resize_space';return;}
            o.target=wanted;o.viewport=viewport;o.requestedHeight=requested;o.before=snapshot('pending_original_scroll_cue');o.fired=true;o.reason='ordinary_resize_requested';
            // Ordinary QWindow geometry only: no target/group/scroll assignment.
            window.height=requested;
            o.samples=o.samples.concat([snapshot('height_setter_returned')]);
            Qt.callLater(function(){o.resized=snapshot('next_layout');o.samples=o.samples.concat([o.resized]);});
        };
        Session.assistant.actionPointerMoved.connect(o.callback);
        return {installed:true,height:window.height,minimumHeight:window.minimumHeight};
    })()'''.replace('GROUP', control_expression('group.constraint')).replace(
        'FIELD', control_expression('constraints.append'))
    installed = qml(actor, setup)
    receipt = {'scope': 'Single original-target reveal property; not a live-matrix or scientific gate',
               'initial_resize': initial, 'installed': installed}
    (actor.folder / 'stale-reveal-property.json').write_text(json.dumps(receipt, indent=2)+'\n')
    try:
        if not installed['installed']:
            receipt['classification'] = 'NOT_REACHED: original controls unavailable'
            (actor.folder / 'stale-reveal-property.json').write_text(json.dumps(receipt, indent=2)+'\n')
            pytest.skip(receipt['classification'])
        actor.request('Apply the original affine relation once and retain its actual native outcome.')
        actor.until(lambda row: len(actor.responses()) == 1 and row['ui']['state'] == 'idle',
                    visible_progress=True)
        witness = qml(actor, '(function(){const o='+control_expression(marker)+';return '
                      '{fired:o.fired,reason:o.reason,before:o.before,resized:o.resized,samples:o.samples};})()')
        response = actor.responses()[0]
        receipt.update({'witness': witness, 'response': response,
                        'project_after': actor.last['ui']['project']})
        before, resized = witness.get('before'), witness.get('resized')
        reached = (witness['fired'] and before and resized
                   and before['ownerCurrent'] and resized['ownerCurrent']
                   and before['target'] == resized['target']
                   and before['viewport'] == resized['viewport']
                   and not before['targetFullyExposed'] and resized['targetFullyExposed']
                   and resized['height'] > before['height']
                   and resized['contentY'] == before['contentY'])
        receipt['reached'] = bool(reached)
        wire = json.loads(response['result']['contentItems'][0]['text'])
        receipt['expected_original_zero_delta_refusal'] = bool(
            reached and not response['result']['success']
            and wire.get('message') == 'The genuine wheel did not move the current viewport'
        )
        receipt['classification'] = ('REACHED: actual zero-delta/current-original geometry boundary'
                                     if reached else 'NOT_REACHED: cue/resize/exposure/zero-delta not proved')
        (actor.folder / 'stale-reveal-property.json').write_text(json.dumps(receipt, indent=2)+'\n')
        if not reached:
            pytest.skip(receipt['classification'])
        result = native_result(response)
        assert result.get('complete') and result.get('steps_completed') == 7, (
            'A fully exposed SAME original target must complete its ordinary seven relation edits once; '
            'unchanged scroll position alone cannot refuse it. Complete receipt: '
            + str(actor.folder / 'stale-reveal-property.json')
        )
        after = actor.last['ui']['project']
        assert after['aliases'] == original['aliases'] + [
            {'id': 'e11_reveal_a', 'parameter': 'phase.cell.length_a'},
            {'id': 'e11_reveal_b', 'parameter': 'phase.cell.length_b'},
        ], 'Actual alias row readback retains all original declarations and exactly two requested additions'
        assert after['constraints'] == original['constraints'] + [
            {'id': 'e11_reveal_pair', 'expression': 'e11_reveal_b = e11_reveal_a', 'enabled': True}
        ], 'Actual enabled constraint and original declarations survive; no duplicate or retargeted effect'
        for _ in range(7):
            actor.command('undo')
            actor.until(lambda row: not row['ui']['project']['calculating'])
        restored = actor.last['ui']['project']
        assert restored['aliases'] == original['aliases']
        assert restored['constraints'] == original['constraints']
        assert restored['parameters'] == original['parameters'], (
            'The original ordinary Undo history exactly restores the scientific and relation preimage'
        )
    finally:
        if not getattr(actor, '_stream_unusable', None):
            qml(actor, '(function(){const o='+control_expression(marker)+';if(o){'
                'Session.assistant.actionPointerMoved.disconnect(o.callback);o.destroy();}'
                'window.height='+json.dumps(initial['before'])+';return true;})()')
