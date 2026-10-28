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


def _whole_window_objects_expression():
    # FIRST actual-Main compact UI observer: Popup visual/data children may
    # be outside ApplicationWindow.contentItem. Read only; never reveal/focus.
    return ("(function(){const out=[],seen=new Set(),queue=[window];"
            "while(queue.length){const x=queue.shift();if(!x||seen.has(x))continue;"
            "seen.add(x);out.push(x);for(const key of ['children','data']){"
            "let values=null;try{values=x[key];}catch(error){}"
            "if(!values||typeof values.length!=='number')continue;"
            "for(let i=0;i<values.length;i++)if(Qt.isQtObject(values[i]))queue.push(values[i]);}}"
            "return out;})()")


def control_expression(name):
    return '(' + _whole_window_objects_expression() + '.find(x=>x.objectName===' + json.dumps(name) + ')||null)'


def _scene_control_expression(name):
    # Normal original controls and this test's observer Item belong to the
    # current Main visual tree. Follow each actual visual child only: no QObject
    # data graph, aliases or Set identity traversal. The finite acyclic parent
    # tree bounds the read, and absence still returns null without creating UI.
    return ("(function(){const root=window.contentItem,queue=root?[root]:[];"
            "const panel=typeof assistantPanel==='undefined'?null:assistantPanel;"
            "if(panel&&panel.assistant===Session.assistant&&panel.parent&&panel.parent.Window.window===window){"
            "const content=panel.contentItem;if(content&&content!==root)queue.push(content);}"
            "while(queue.length){const x=queue.shift();if(x.objectName===" + json.dumps(name) + ")return x;"
            "const children=x.children;for(let i=0;i<children.length;i++){const child=children[i];"
            "if(child&&child.parent===x)queue.push(child);}}return null;})()")


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

# Independent H92/H937 regressions. Reference: original public Rows role lists
# at Edi9d06c4eb; pinned092d WebSearchItem.results are opaque JSON. The probe's
# model counter measures actual public Qt data/get reads, never ui_snapshot.
def _rows_probe(actor, mode='snapshot', **values):
    return actor.command('messages_probe', mode=mode, **values)['reply']


def _rows_wait(actor, predicate, *, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = _rows_probe(actor)
        if predicate(value):
            return value
    raise AssertionError('The finite public messages-model boundary did not reach its stated condition; '
                         + str(actor.folder / 'last-observation.json'))


def _rows_read(actor, row, role, *, model='messages', api='get', repetitions=1):
    return _rows_probe(actor, 'read', row=row, role=role, model=model,
                       api=api, repetitions=repetitions)['read']


def _rows_values(actor, model, row):
    names = (_rows_probe(actor, model=model)['role_names'] if model != 'messages'
             else ['id', 'kind', 'text', 'status'])
    return {name: _rows_read(actor, row, name, model=model)['scalar'] for name in names}


def _rows_history_file(actor):
    paths = list(Path(actor.last['test_storage']).rglob('assistant/history.json'))
    assert len(paths) == 1, 'Canonical history has one actual run-owned normal app-storage owner'
    return paths[0]


def _rows_research(identity, *, opaque='', held=None):
    result = {'type': 'text_result', 'ref_id': 'source-' + identity,
              'url': 'https://www.ill.eu/sites/fullprof/', 'title': 'Public reference',
              'snippet': 'Independent finite public-source result',
              'future_field': {'literal': opaque, 'null_value': None, 'values': [3, False]}}
    return {'call_id': identity, 'research': {
        'query': 'Public diffraction documentation ' + identity,
        'action': {'type': 'search', 'query': 'Public diffraction documentation', 'queries': None},
        'results': [result]}, **({'hold_complete': str(held)} if held else {})}


def test_message_scalar_roles_keep_opaque_backend_and_announce_only_changed_rows(main_actor, tmp_path):
    # One genuinely large opaque event, not multiplied into every history row.
    marker = 'independent-opaque-backend-only-7ec635e6:'
    opaque = marker + 'x' * (1024 * 1024)
    actor = main_actor([[]])
    actor.connect()
    release = actor.folder / 'release-second-research'
    actor.configure_turns([[_rows_research('small'), _rows_research('large', opaque=opaque)],
                           [_rows_research('held', held=release)]])
    actor.request('Read the public references and preserve their literal result evidence.')
    _rows_wait(actor, lambda value: value['state'] == 'idle' and value['count'] >= 4)
    count = _rows_probe(actor)['count']
    initial = [_rows_values(actor, 'messages', row) for row in range(count)]
    activities = [row for row in initial if row['kind'] == 'activity']
    assert len(activities) == 2, 'Both actual pinned research items are distinct retained activities'
    indices = [next(i for i, row in enumerate(initial) if row['id'] == item['id']) for item in activities]
    measurements = []
    for index in indices:
        roles = _rows_probe(actor, 'roles', row=index, marker=marker)['roles']
        assert not any(role['marker_present'] for role in roles), (
            'Collapsed presentation roles expose no full opaque technical result from canonical backend')
        for role in ('id', 'kind', 'text', 'status'):
            for api in ('data', 'get'):
                sample = _rows_read(actor, index, role, api=api, repetitions=256)
                assert sample['scalar'] == initial[index][role], (
                    'Role-specific public data/get preserves the original scalar value')
                measurements.append({'row_id': initial[index]['id'], **sample})
    (actor.folder / 'scalar-role-measurements.json').write_text(json.dumps(measurements, indent=2))
    # No universal allocation/clock guarantee: structural absence and measured
    # read times are separate facts, with no blanket machine-dependent threshold.
    _rows_probe(actor, 'watch')
    _rows_probe(actor, 'send', text='Read one further public reference.')
    _rows_wait(actor, lambda value: value['count'] > count and value['state'] != 'idle')
    insertion = _rows_probe(actor, 'events', clear=True)['events']
    assert not any(event['kind'] in ('reset', 'move') for event in insertion), (
        'Appending an actual activity retains original Qt row identities and order')
    assert not any(event['kind'] == 'dataChanged' and event['first'] < count
                   for event in insertion), 'An append does not invalidate unchanged original history rows'
    pending_count = _rows_probe(actor)['count']
    before = [_rows_probe(actor, 'roles', row=i)['roles'] for i in range(pending_count)]
    release.touch()
    _rows_wait(actor, lambda value: value['state'] == 'idle')
    events = _rows_probe(actor, 'stop')['events']
    after = [_rows_probe(actor, 'roles', row=i)['roles'] for i in range(pending_count)]
    for event in events:
        assert event['kind'] not in ('reset', 'move'), 'Completion preserves actual original model row identities'
        if event['kind'] == 'dataChanged':
            assert event['roles'], 'Actual changed-role notifications identify their changed public roles'
            for index in range(event['first'], event['last'] + 1):
                old = {role['name']: role['sha256'] for role in before[index]}
                new = {role['name']: role['sha256'] for role in after[index]}
                assert all(old.get(role) != new.get(role) for role in event['roles']), (
                    'Unchanged scalar/technical presentation roles are not spuriously invalidated')
    history = _rows_history_file(actor)
    raw = history.read_bytes()
    entries = list(objects(json.loads(raw)))
    assert any(entry.get('literal') == opaque for entry in entries), (
        'Original opaque research bytes remain in canonical durable backend despite compact presentation')
    (actor.folder / 'canonical-history-before-detail.json').write_bytes(raw)
    # Explicit public lazy lookup uses the exact original row identity tuple.
    large = activities[1]
    args = ','.join(json.dumps(large[key]) for key in ('id', 'kind', 'status'))
    detail = qml(actor, '(function(){const s=Session.assistant.activityTechnicalDetails(' + args
                 + ');return {literal:s.indexOf(' + json.dumps(marker) + ')>=0,bytes:s.length};})()')
    assert detail['literal'] and detail['bytes'] >= len(opaque), (
        'Explicit original-row technical lookup retains full backend evidence without presentation projection')
    stale = qml(actor, 'Session.assistant.activityTechnicalDetails(' + json.dumps(large['id'])
                + ',"user",' + json.dumps(large['status']) + ')')
    assert stale == '', 'A mismatched original row kind cannot disclose technical evidence'
    assert history.read_bytes() == raw, 'Lazy detail lookup does not rewrite canonical original history'


@pytest.mark.parametrize('model,roles', [
    ('selectedFiles', ['id', 'name', 'bytes', 'textReadable', 'format', 'pending']),
    ('models', ['id', 'displayName', 'efforts', 'available']),
    ('skills', ['id', 'version', 'title', 'summary', 'path', 'sha256', 'requires',
                'capabilities', 'references', 'content', 'available', 'blocked_reason']),
    ('skillSources', ['id', 'label', 'path', 'enabled', 'builtin', 'status']),
])
def test_nonmessage_rows_keep_their_original_public_roles_and_values(main_actor, tmp_path, model, roles):
    actor = main_actor([[]])
    actor.connect()
    fixture = tmp_path / 'independent-file-label.cif'
    # Real attachment bytes need no scientific parser: file admission is the
    # ordinary signed-in selected-file owner, not a planted model result.
    fixture.write_text('data_independent\n_audit_creation_method "ordinary attachment role witness"\n')
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(fixture)])['reply']['added'], (
        'The independent attachment is admitted through its original current file-selection owner')
    snapshot = _rows_probe(actor, model=model)
    assert set(snapshot['role_names']) == set(roles), (
        'Message-only lightweight projection does not change another original public Rows schema')
    assert snapshot['count'] > 0, 'The actual nonmessage model has a reached positive row'
    rows = [_rows_values(actor, model, index) for index in range(snapshot['count'])]
    if model == 'selectedFiles':
        row = next(row for row in rows if row['name'] == fixture.name)
        assert row['bytes'] == fixture.stat().st_size and row['textReadable'] is True, (
            'Attachment filename/raw byte count/readability retain actual admitted-file values')
        assert row['id'] and row['format'] and row['pending'] is False, (
            'The settled attachment keeps its own identity/format/current pending state')
    elif model == 'models':
        row = next(row for row in rows if row['id'] == 'gpt-6.1-sol')
        assert row['displayName'] == 'Independent offline model' and row['available'] is True, (
            'The pinned model/list fixture preserves its actual offered identity/name/availability')
        assert 'medium' in json.dumps(row['efforts']), 'Original model effort values survive message projection changes'
    elif model == 'skillSources':
        row = next(row for row in rows if row['id'] == 'builtin')
        assert row['label'] == 'EasyDiffraction' and row['enabled'] is True and row['builtin'] is True, (
            'Original builtin source labels and typed booleans retain their distinct source roles')
    else:
        embedded = actor.command('embedded_skills')['reply']
        indexed = {item['id']: item for item in embedded['index']['skills']}
        for row in rows:
            assert row['id'] in indexed and row['title'] and row['version'], (
                'Actual skill rows retain catalog identity/title/version rather than message-shaped empty values')
            source = ROOT / 'data/assistant/skills' / indexed[row['id']]['path']
            content = source.read_bytes()
            assert row['content'] == content.decode() and row['sha256'] == hashlib.sha256(content).hexdigest(), (
                'Original skill content/hash matches independently committed resource bytes')


def _rows_view_metrics(actor):
    view = control_expression('assistant.messages')
    return qml(actor, '(function(){const v=' + view + ';if(!v)return null;'
        'const rows=Array.from(v.contentItem.children).filter(x=>typeof x.rowId==="string");'
        'function details(x){if(typeof x.humanDetailsSnapshot!=="undefined")return '
        '[{id:x.rowId,loaded:x.humanDetailsSnapshot!==null}];'
        'return Array.from(x.children||[]).flatMap(details);}'
        'return {count:v.count,height:v.height,cache:v.cacheBuffer,contentY:v.contentY,'
        'rows:rows.map(x=>({id:x.rowId,index:x.index,height:x.height,visible:x.visible,'
        'details:details(x)}))};})()')


def test_actual_long_history_virtualizes_lazy_details_and_restores_exact_original_bytes(
    main_actor, tmp_path, monkeypatch
):
    marker = 'independent-long-history-opaque-28bf:'
    opaque = marker + 'q' * (1024 * 1024)
    # Many independently framed actual items, one large backend result only.
    actor = main_actor([[_rows_research('history-' + str(i), opaque=opaque if i == 47 else '')
                         for i in range(96)]])
    actor.connect()
    actor.request('Read the finite public references and retain their actual outcomes.')
    _rows_wait(actor, lambda value: value['state'] == 'idle' and value['count'] >= 98)
    original = _rows_history_file(actor).read_bytes()
    history_copy = actor.folder / 'original-history-for-restore.json'
    history_copy.write_bytes(original)
    # No manufactured rows or alternate store: source is the first real run's
    # original durable file, installed before the next ordinary Session ctor.
    monkeypatch.setenv('EDI_TEST_ASSISTANT_RESTORE_HISTORY', str(history_copy))
    restored = main_actor([[]])
    witness = restored.last['history_restore']
    assert witness['exact_copy'] and witness['sha256'] == hashlib.sha256(original).hexdigest(), (
        'Restart uses byte-exact genuine original history before constructing its ordinary Session')
    assert Path(witness['destination']).read_bytes() == original, (
        'History restore does not synthesize rows or rewrite canonical backend bytes')
    _rows_wait(restored, lambda value: value['count'] >= 98)
    count = _rows_probe(restored)['count']
    view = control_expression('assistant.messages')
    observed = []
    for position in (0, count // 2, count - 1):
        started = time.monotonic()
        restored.command('evaluate', expression='(function(){const v=' + view
                         + ';v.positionViewAtIndex(' + str(position) + ',ListView.Center);})()')
        metrics = _rows_view_metrics(restored)
        assert metrics and metrics['rows'], 'Ordinary actual ListView realizes reached rows for its current viewport'
        heights = [row['height'] for row in metrics['rows'] if row['height'] > 0]
        assert heights, 'Virtualization witness has real nonempty row geometry'
        # Conservative two boundary delegates plus normal cache on both sides;
        # this is a fixture geometry bound, not a production history quota.
        bound = int((metrics['height'] + 2 * metrics['cache']) / min(heights)) + 4
        assert len(metrics['rows']) <= bound and len(metrics['rows']) < count // 2, (
            'Actual rendered delegates remain viewport/cache bounded rather than proportional to history length')
        assert all(not detail['loaded'] for row in metrics['rows'] for detail in row['details']), (
            'Collapsed and reused actual delegates do not retain full human detail snapshots')
        observed.append({'target': position, 'elapsed_seconds': time.monotonic() - started,
                         'geometric_bound': bound, **metrics})
    # One currently realized genuine activity control, never a virtual row
    # fabricated solely to make input succeed.
    restored.command('evaluate', expression='(function(){const v=' + view
                     + ';v.positionViewAtIndex(48,ListView.Center);})()')
    metrics = _rows_view_metrics(restored)
    candidates = []
    for row in metrics['rows']:
        value = _rows_read(restored, row['index'], 'kind')['scalar']
        if value == 'activity':
            candidates.append(row)
    assert candidates, 'The ordinary scroll genuinely realizes an activity before physical expansion'
    chosen = next(row for row in candidates if row['index'] == 48)
    click = restored.command('message_input', row_id=chosen['id'],
                             name='assistant.activity.toggle', action='click')['reply']
    assert click['reached'] and click['same_row_after'] and click['same_window_after'], (
        'Expansion input is delivered to the exact original realized activity in the current Main window')
    expanded = _rows_view_metrics(restored)
    assert any(d['id'] == chosen['id'] and d['loaded'] for row in expanded['rows'] for d in row['details']), (
        'Only explicit original-row expansion resolves its full human description')
    restored.command('message_input', row_id=chosen['id'], name='assistant.activity.toggle', action='hover')
    default_copy = restored.command('message_input', row_id=chosen['id'],
                                    name='assistant.activity.copy', action='click')['reply']
    assert qml(restored, 'Preferences.assistantCopyTechnicalDetails') is False, (
        'Technical Copy remains opt-in with the original preference default false')
    assert default_copy['reached'] and default_copy['clipboard'] and marker not in default_copy['clipboard'], (
        'Default genuine Copy publishes human descriptions without opaque technical evidence')
    restored.command('click', name='appBar.button.preferences')
    restored.command('click', name='preferences.tab.aiAssistance')
    restored.command('click', name='preferences.ai.copyTechnicalDetails')
    assert qml(restored, 'Preferences.assistantCopyTechnicalDetails') is True, (
        'Only the original explicit AI preference enables technical Copy')
    restored.command('manual_key', key='escape')
    restored.command('message_input', row_id=chosen['id'], name='assistant.activity.toggle', action='hover')
    technical = restored.command('message_input', row_id=chosen['id'],
                                 name='assistant.activity.copy', action='click')['reply']
    assert technical['reached'] and technical['clipboard'].startswith(default_copy['clipboard'] + '\n\n') and opaque in technical['clipboard'], (
        'Explicit opted-in original-row Copy includes unchanged full technical evidence and human descriptions')
    restored.command('message_input', row_id=chosen['id'], name='assistant.activity.toggle', action='click')
    collapsed = _rows_view_metrics(restored)
    assert all(not d['loaded'] for row in collapsed['rows'] for d in row['details']), (
        'Collapsing releases the original lazy detail snapshot before later reuse')
    assert _rows_history_file(restored).read_bytes() == original, (
        'Ordinary scrolling/expansion/default Copy leaves full canonical original history unchanged')
    (restored.folder / 'restore-scroll-measurements.json').write_text(json.dumps({
        'source_sha256': hashlib.sha256(original).hexdigest(), 'source_bytes': len(original),
        'restored_count': count, 'positions': observed}, indent=2))


def _attachment_rows(actor):
    return [_rows_values(actor, 'selectedFiles', i)
            for i in range(_rows_probe(actor, model='selectedFiles')['count'])]


def _attachment_fixtures(tmp_path, count):
    paths = []
    for index in range(count):
        path = tmp_path / ('admitted-' + str(index) + '.cif')
        path.write_text('data_independent_' + str(index) + '\n_audit_creation_method "attachment-only literal input"\n')
        paths.append(path)
    return paths


def _attachment_geometry(actor, prefix):
    return qml(actor, '(function(){const all=' + _whole_window_objects_expression()
        + ';return all.filter(x=>String(x.objectName).indexOf(' + json.dumps(prefix)
        + ')===0&&x.visible).map(x=>{const p=x.mapToItem(contentItem,0,0);let labels=[];'
        'function texts(y){if(typeof y.text==="string"&&y.visible)labels.push(y.text);'
        'Array.from(y.children||[]).forEach(texts);}texts(x);'
        'return {id:x.objectName,x:p.x,y:p.y,width:x.width,height:x.height,labels:labels};});})()')


def test_attachment_admission_is_six_per_pending_message_preserving_existing_draft(main_actor, tmp_path):
    actor = main_actor([[]])
    files = _attachment_fixtures(tmp_path, 7)
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=list(map(str, files[:4])))['reply']['added'], (
        'Ordinary file admission accepts the first actual pending group')
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=list(map(str, files[4:6])))['reply']['added'], (
        'Pending admissions accumulate to the owner-selected per-message maximum of six')
    before = _attachment_rows(actor)
    assert len([row for row in before if row['pending']]) == 6, (
        'Six actual pending attachments are retained with their original IDs and exact byte counts')
    actor.command('click', name='assistant.composer')
    actor.command('manual_text', text='Preserve this exact unsent user draft.')
    token = actor.begin_current_file_selection()
    refused = actor.command('selected_add', token=token, paths=[str(files[6])])
    assert refused['reply']['added'] is False, (
        'A seventh pending file is refused rather than silently replacing/truncating the existing draft')
    assert _attachment_rows(actor) == before, 'Excess admission preserves all previously admitted file identities/bytes/pending flags'
    editor = qml(actor, control_expression('assistant.composer') + '.text')
    assert editor == 'Preserve this exact unsent user draft.', 'Excess attachment admission preserves the original literal composer text'
    assert actor.last['ui'].get('last_error') or qml(actor, 'Session.assistant.lastError'), (
        'Excess attachment refusal is stated to the user instead of silently dropping input')
    assert not any(row.get('method') == 'turn/start' for row in map(json.loads, actor.trace.read_text().splitlines())), (
        'File-admission refusal never submits a provider turn or invents a scientific request')


def test_file_only_send_retains_literal_empty_user_text_task_files_and_new_pending_draft(main_actor, tmp_path):
    actor = main_actor([[], []])
    files = _attachment_fixtures(tmp_path, 7)
    actor.connect()
    no_files = qml(actor, control_expression('assistant.send') + '.enabled')
    assert no_files is False, 'Empty text without genuinely pending admitted files is not sendable'
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=list(map(str, files[:6])))['reply']['added'], (
        'The first file-only draft contains six genuinely admitted files')
    first = _attachment_rows(actor)
    actor.command('accept_context')
    actor.until(lambda value: value['ui']['connected'] and value['ui']['state'] == 'idle'
                and any(c['name'] == 'assistant.send' and c['enabled'] and c['fully_exposed']
                        for c in value['ui']['controls']))
    assert qml(actor, control_expression('assistant.composer') + '.text') == '', (
        'A file-only request does not fabricate a placeholder user prompt or scientific instruction')
    actor.command('click', name='assistant.send')
    actor.until(lambda value: value['ui']['state'] == 'idle' and not value['ui']['can_cancel'])
    canonical = json.loads(_rows_history_file(actor).read_bytes())
    users = [row for row in objects(canonical) if row.get('kind') == 'user'
             and isinstance(row.get('payload'), dict) and row['payload'].get('type') == 'ediInput']
    assert len(users) == 1 and users[0]['text'] == '', (
        'Accepted file-only history retains the exact literal empty user text')
    actual = users[0]['payload']['files']
    assert {row['id'] for row in actual} == {row['id'] for row in first}, (
        'The sent history owns all and only the actually admitted first-message files')
    for entry, path in zip(first, files[:6]):
        assert entry['name'] == path.name and entry['bytes'] == path.stat().st_size, (
            'Sent-file labels preserve original names/raw bytes independently of their KB presentation')
    assert not any(row['pending'] for row in _attachment_rows(actor)), (
        'Accepted submission consumes only the original pending draft without losing task file authority')
    assert not _attachment_geometry(actor, 'assistant.file.'), (
        'Consumed attachments are hidden from the current composer after accepted submission')
    sent = _attachment_geometry(actor, 'assistant.sentFile.')
    assert len(sent) == 6, 'All six consumed attachments remain visibly attached to their sent user message'
    assert len({row['y'] for row in sent}) == 6, 'Each sent attachment occupies its own original history line'
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(files[6])])['reply']['added'], (
        'A later pending message has its own six-file allowance rather than a lifetime attachment cap')
    later = _attachment_rows(actor)
    assert {row['id'] for row in first} <= {row['id'] for row in later}, (
        'Newly pending files do not erase consumed files still needed by the current task reader')
    assert [row['name'] for row in later if row['pending']] == [files[6].name], (
        'Only the newly admitted file belongs to the next pending composer draft')


def test_pending_attachment_lines_follow_literal_text_with_separate_normal_line_gaps(main_actor, tmp_path):
    actor = main_actor([[]])
    files = _attachment_fixtures(tmp_path, 3)
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=list(map(str, files)))['reply']['added'], (
        'The layout witness uses three genuinely admitted current files')
    actor.command('click', name='assistant.composer')
    actor.command('manual_text', text='A literal user draft above its files.')
    rows = sorted(_attachment_geometry(actor, 'assistant.file.'), key=itemgetter('y'))
    editor = qml(actor, '(function(){const e=' + control_expression('assistant.composer')
                 + ',p=e.mapToItem(contentItem,0,0);return {y:p.y,height:e.height,text:e.text};})()')
    assert len(rows) == 3 and all(row['height'] > 0 for row in rows), (
        'The actual composer exposes all three original attachment rows')
    assert rows[0]['y'] >= editor['y'] + editor['height'], (
        'Files appear below the literal main text rather than above or inline with the editor')
    assert all(a['y'] + a['height'] <= b['y'] for a, b in zip(rows, rows[1:])), (
        'Every actual attachment has its own nonoverlapping line')
    assert abs(rows[1]['x'] - rows[0]['x']) < 0.5 and abs(rows[2]['x'] - rows[0]['x']) < 0.5, (
        'Attachment lines share the original normal text alignment')
    labels = [text for row in rows for text in row['labels'] if any(p.name in text for p in files)]
    assert len(labels) == 3 and all('undefined' not in label and 'KB' in label for label in labels), (
        'Actual composer file labels preserve their names and consistently display KB instead of undefined raw roles')
    gaps = [b['y'] - (a['y'] + a['height']) for a, b in zip(rows, rows[1:])]
    assert rows[0]['y'] - (editor['y'] + editor['height']) > max(gaps), (
        'The main-text-to-first-file gap is larger than ordinary inter-file line spacing')


def _session_fixture(actor, **archive):
    # These fixed provider rows come from independently pinned schema fixtures,
    # never a materialized application model or fabricated local chat history.
    source = json.loads('{"thread_list": {"threads": [{"id": "019a0290-0000-7000-9000-000000000001", "cliVersion": "0.162.1", "createdAt": 1, "updatedAt": 1792751460, "cwd": "{CURRENT_WORKSPACE}", "ephemeral": false, "modelProvider": "openai", "preview": "", "projectId": null, "sessionId": "independent-provider-session", "source": "vscode", "forkedFromId": null, "parentThreadId": null, "section": null, "sectionEnteredAt": null, "historyMode": "legacy", "recencyAt": null, "model": "gpt-6.1-sol", "reasoningEffort": "medium", "path": null, "originator": "edi", "threadSource": null, "agentNickname": null, "agentRole": null, "gitInfo": null, "name": "Historical Edi VSCode source", "status": {"type": "idle"}, "turns": []}, {"id": "019a0290-0000-7000-9000-000000000002", "cliVersion": "0.162.1", "createdAt": 1, "updatedAt": 1792837860, "cwd": "/independent/other-app-workspace", "ephemeral": false, "modelProvider": "openai", "preview": "", "projectId": null, "sessionId": "independent-provider-session", "source": "vscode", "forkedFromId": null, "parentThreadId": null, "section": null, "sectionEnteredAt": null, "historyMode": "legacy", "recencyAt": null, "model": "gpt-6.1-sol", "reasoningEffort": "medium", "path": null, "originator": "edi", "threadSource": null, "agentNickname": null, "agentRole": null, "gitInfo": null, "name": "Another app workspace", "status": {"type": "idle"}, "turns": []}, {"id": "019a0290-0000-7000-9000-000000000003", "cliVersion": "0.162.1", "createdAt": 1, "updatedAt": 1792924260, "cwd": "{CURRENT_WORKSPACE}", "ephemeral": false, "modelProvider": "openai", "preview": "", "projectId": null, "sessionId": "independent-provider-session", "source": "appServer", "forkedFromId": null, "parentThreadId": null, "section": null, "sectionEnteredAt": null, "historyMode": "legacy", "recencyAt": null, "model": "gpt-6.1-sol", "reasoningEffort": "medium", "path": null, "originator": "edi", "threadSource": null, "agentNickname": null, "agentRole": null, "gitInfo": null, "name": "Explicit app-server Edi source", "status": {"type": "idle"}, "turns": []}, {"id": "019a0290-0000-7000-9000-000000000004", "cliVersion": "0.162.1", "createdAt": 1, "updatedAt": 1793097060, "cwd": "{CURRENT_WORKSPACE}", "ephemeral": false, "modelProvider": "openai", "preview": "", "projectId": null, "sessionId": "independent-provider-session", "source": "vscode", "forkedFromId": null, "parentThreadId": null, "section": null, "sectionEnteredAt": null, "historyMode": "legacy", "recencyAt": null, "model": "gpt-6.1-sol", "reasoningEffort": "medium", "path": null, "originator": "vscode", "threadSource": null, "agentNickname": null, "agentRole": null, "gitInfo": null, "name": "Foreign at identical cwd/source", "status": {"type": "idle"}, "turns": []}, {"id": "019a0290-0000-7000-9000-000000000005", "cliVersion": "0.162.1", "createdAt": 1, "updatedAt": 1793183460, "cwd": "{CURRENT_WORKSPACE}", "ephemeral": false, "modelProvider": "openai", "preview": "", "projectId": null, "sessionId": "independent-provider-session", "source": "vscode", "forkedFromId": null, "parentThreadId": null, "section": null, "sectionEnteredAt": null, "historyMode": "legacy", "recencyAt": null, "model": "gpt-6.1-sol", "reasoningEffort": "medium", "path": null, "originator": null, "threadSource": null, "agentNickname": null, "agentRole": null, "gitInfo": null, "name": "Unknown originator at identical cwd/source", "status": {"type": "idle"}, "turns": []}, {"id": "019a0290-0000-7000-9000-000000000006", "cliVersion": "0.162.1", "createdAt": 1, "updatedAt": 1793010660, "cwd": "{CURRENT_WORKSPACE}", "ephemeral": false, "modelProvider": "openai", "preview": "", "projectId": null, "sessionId": "independent-provider-session", "source": "appServer", "forkedFromId": null, "parentThreadId": null, "section": null, "sectionEnteredAt": null, "historyMode": "legacy", "recencyAt": null, "model": "gpt-6.1-sol", "reasoningEffort": "medium", "path": null, "originator": "other-application", "threadSource": null, "agentNickname": null, "agentRole": null, "gitInfo": null, "name": "Foreign app-server client", "status": {"type": "idle"}, "turns": []}], "page_size": 2, "expected_owned_ids": ["019a0290-0000-7000-9000-000000000003", "019a0290-0000-7000-9000-000000000002", "019a0290-0000-7000-9000-000000000001"], "expected_request_sort": {"sortKey": "updated_at", "sortDirection": "desc"}, "nonempty_originators_error": "Local pinned app-server rejects a nonempty originator filter", "cwd_filter_must_not_hide_other_owned_workspace": true}}')
    path = actor.folder / 'peer.json'
    config = json.loads(path.read_bytes())
    config['session_fixture'] = {**source['thread_list'], **archive}
    path.write_text(json.dumps(config))
    return source


def _session_wait(actor):
    actor.until(lambda _value: not qml(actor, 'Session.assistant.sessionsLoading'))
    return [_rows_values(actor, 'sessions', i)
            for i in range(_rows_probe(actor, model='sessions')['count'])]


def test_app_session_browser_pages_updated_sessions_without_foreign_cwd_or_source_ownership(main_actor):
    actor = main_actor([[]])
    fixture = _session_fixture(actor)
    actor.connect()
    actor.command('click', name='assistant.sessions')
    rows = _session_wait(actor)
    pages = 1
    while qml(actor, 'Session.assistant.sessionsHaveMore'):
        assert pages < 10, 'The finite seven-row provider fixture completes without a cursor cycle'
        qml(actor, 'Session.assistant.refreshSessions(true)')
        rows = _session_wait(actor)
        pages += 1
    expected = fixture['thread_list']['expected_owned_ids']
    known = {row['id'] for row in fixture['thread_list']['threads']}
    found = [row['id'] for row in rows if row['id'] in known]
    assert found == expected, (
        'All app-created workspaces, including historical vscode and appServer sessions, are listed newest-modified first')
    assert len({row['id'] for row in rows}) == len(rows), (
        'Opaque pagination preserves unique original session identities without duplicated rows')
    assert all(row['name'] and re.fullmatch(r'\d{1,2} [A-Za-z]{3} \d{4} at \d{2}:\d{2}', row['modified'])
               for row in rows if row['id'] in known), (
        'App-owned metadata retains the actual session title and owner-requested human timestamp form')
    wire = list(map(json.loads, actor.trace.read_text().splitlines()))
    requests = [row['params'] for row in wire if row.get('method') == 'thread/list']
    assert len(requests) >= 2 and any(row.get('cursor') for row in requests), (
        'Actual supported thread/list follows opaque continuation rather than treating a page as total history')
    assert all(not row.get('originators') for row in requests), (
        'Local pinned runtime never receives its unsupported nonempty hosted-only originator filter')
    assert all(row.get('sortKey') == 'updated_at' and row.get('sortDirection', 'desc') == 'desc'
               and not row.get('cwd') for row in requests), (
        'Original supported list request sorts modified time and does not hide other app-owned workspaces')
    # No account field exists in the pinned returned Thread. Account association
    # belongs to the actual current authenticated owner, never invented metadata.
    assert all('account' not in row for row in fixture['thread_list']['threads']), (
        'Session ownership fixture preserves the pinned absence of a returned account field')


@pytest.mark.parametrize('outcome', ['held_ack', 'error'])
def test_archive_preserves_original_row_until_actual_ack_without_science_or_account_change(main_actor, outcome):
    actor = main_actor([[]])
    release = actor.folder / 'release-original-archive'
    fixture = _session_fixture(actor, **({'archive_hold': str(release)} if outcome == 'held_ack'
                                         else {'archive_error': True}))
    actor.connect()
    account = qml(actor, 'Session.assistant.account')
    project = qml(actor, 'Session.project===null ? null : String(Session.project)')
    qml(actor, 'Session.assistant.refreshSessions()')
    _session_wait(actor)
    while qml(actor, 'Session.assistant.sessionsHaveMore'):
        qml(actor, 'Session.assistant.refreshSessions(true)')
        _session_wait(actor)
    victim = fixture['thread_list']['expected_owned_ids'][0]
    before = [_rows_values(actor, 'sessions', i)
              for i in range(_rows_probe(actor, model='sessions')['count'])]
    original = next(row for row in before if row['id'] == victim)
    assert original['canArchive'], 'The finite archive fixture reaches a genuine idle noncurrent app-owned session'
    qml(actor, 'Session.assistant.archiveSession(' + json.dumps(victim) + ')')
    pending = [_rows_values(actor, 'sessions', i)
               for i in range(_rows_probe(actor, model='sessions')['count'])]
    assert victim in {row['id'] for row in pending}, (
        'An unacknowledged or failed archive cannot optimistically erase the original active-list row')
    if outcome == 'held_ack':
        release.touch()
        actor.command('refresh_usage')
        settled = _session_wait(actor)
        assert victim not in {row['id'] for row in settled}, (
            'Only actual acknowledged runtime archive removes its original active-list row')
        state = json.loads(actor.trace.with_suffix('.provider-state.json').read_bytes())
        assert victim in state['archived_threads'] and victim in state['threads'], (
            'Archive organizes the actual runtime session while retaining its persisted log identity')
    else:
        actor.until(lambda _row: bool(qml(actor, 'Session.assistant.sessionsError')))
        assert victim in {row['id'] for row in _session_wait(actor)}, (
            'Explicit archive failure retains the original row and exposes its actual diagnostic')
    assert qml(actor, 'Session.assistant.connected') and qml(actor, 'Session.assistant.account') == account, (
        'Session organization preserves the current authenticated account')
    assert qml(actor, 'Session.project===null ? null : String(Session.project)') == project, (
        'Browsing or archiving another workspace never implicitly adopts or modifies a scientific project')
    requests = [row for row in map(json.loads, actor.trace.read_text().splitlines()) if row.get('method')]
    assert len([row for row in requests if row['method'] == 'thread/archive']) == 1, (
        'The original archive operation is sent once without hidden replay')
    assert not any(row['method'] == 'turn/start' for row in requests), (
        'Metadata browsing and archive do not invent provider work or scientific actions')


def test_healthy_live_session_transport_lists_but_active_and_unsettled_input_stay_guarded(main_actor):
    actor = main_actor([[_rows_research('live-session-metadata-reference')]], hold_final=True)
    _session_fixture(actor)
    actor.connect()
    requests = lambda: [row for row in map(json.loads, actor.trace.read_text().splitlines()) if row.get('method')]
    records = list(map(json.loads, actor.trace.read_text().splitlines()))
    runtimes = [row['fixture_runtime_started'] for row in records if 'fixture_runtime_started' in row]
    assert len(runtimes) == 1, 'The metadata fixture has one genuine original stdio runtime process'
    runtime_pid = runtimes[0]['pid']
    os.kill(runtime_pid, 0)
    assert actor.last['ui']['connected'] and actor.last['ui']['state'] == 'idle', (
        'Session metadata admission begins with an actual healthy connected settled transport')
    before = len([row for row in requests() if row['method'] == 'thread/list'])
    actor.command('click', name='assistant.sessions')
    _session_wait(actor)
    assert len([row for row in requests() if row['method'] == 'thread/list']) > before, (
        'Healthy Live transport reaches the actual supported thread/list RPC without being retired to Released')
    actor.command('manual_key', key='escape')
    token = actor.begin_current_file_selection()
    assert token, 'The unresolved-input guard is an actual original selection intent, not a forced private flag'
    before = len([row for row in requests() if row['method'] == 'thread/list'])
    qml(actor, 'Session.assistant.refreshSessions()')
    assert len([row for row in requests() if row['method'] == 'thread/list']) == before, (
        'A captured unsettled input authority still refuses session work on the otherwise healthy live transport')
    qml(actor, 'Session.assistant.cancelFileSelection(' + json.dumps(token) + ')')
    actor.request('Read the public reference without scientific edits.')
    actor.until(lambda value: value['ui']['can_cancel'])
    before = len([row for row in requests() if row['method'] in ('thread/list', 'thread/read', 'thread/archive')])
    qml(actor, 'Session.assistant.refreshSessions()')
    qml(actor, 'Session.assistant.archiveSession("019a0290-0000-7000-9000-000000000003")')
    assert len([row for row in requests() if row['method'] in ('thread/list', 'thread/read', 'thread/archive')]) == before, (
        'Active original work cannot be bypassed by either metadata refresh or direct Archive invocation')
    actor.command('cancel');actor.until(lambda value: not value['ui']['can_cancel'] and value['ui']['state'] == 'idle')
    before = len([row for row in requests() if row['method'] == 'thread/list'])
    qml(actor, 'Session.assistant.refreshSessions()');_session_wait(actor)
    assert len([row for row in requests() if row['method'] == 'thread/list']) > before, (
        'After genuine Stop settles, the same retained healthy transport can list sessions again')
    os.kill(runtime_pid, 0)
    assert len([row for row in requests() if row['method'] == 'initialize']) == 1, (
        'Listing is not made possible by killing/restarting or replacing the original connected runtime')
    (actor.folder / 'live-session-admission-boundaries.json').write_text(json.dumps({
        'runtime_pid': runtime_pid, 'requests': [row['method'] for row in requests()],
        'healthy_list_reached': True, 'active_guard_reached': True, 'unsettled_input_guard_reached': True,
        'uncertain_mutation_guard': 'not independently fabricated or claimed; original guard remains'}, indent=2))


def _protocol_item(method, item):
    clock = {'startedAtMs': 1} if method == 'item/started' else {'completedAtMs': 2}
    return {'notification': {'method': method, 'params': {'item': item, **clock}}}


def test_lazy_command_human_details_preserve_first_supported_meanings_without_technical_copy(main_actor):
    # Labels are the immutable FIRST formatter's human compatibility contract
    # (Edi9d06 AssistantMessage.qml), not current projection output as oracle.
    hidden = 'independent-raw-command-output-NEVER-DISPLAY-69bb'
    cases = [
        ('workflow', 'cat .agents/skills/project-assistance/SKILL.md', [],
         'Read assistant workflow instructions'),
        ('strategy', 'cat .agents/skills/refinement-strategy/SKILL.md', [],
         'Read assistant refinement instructions'),
        ('read', 'cat /approved/counts.xye', [{'type': 'read', 'command': 'cat /approved/counts.xye',
           'name': 'counts.xye', 'path': '/approved/counts.xye'}], 'Read counts.xye'),
        ('list', 'ls /approved/references', [{'type': 'listFiles', 'command': 'ls /approved/references',
           'path': 'reference-directory'}], 'List reference-directory'),
        ('search', 'rg atomic /approved/input.cif', [{'type': 'search', 'command': 'rg atomic /approved/input.cif',
           'query': 'atomic coordinates', 'path': '/approved/input.cif'}], 'Search for atomic coordinates'),
        ('declared', '# Edi purpose: Inspect selected input headings\nopaque unread technical script',
         [{'type': 'unknown', 'command': '# Edi purpose: Inspect selected input headings\nopaque unread technical script'}],
         'Inspect selected input headings'),
    ]
    steps = []
    for identity, command, actions, _ in cases:
        item = {'type': 'commandExecution', 'id': 'human-' + identity,
                'pluginId': None, 'scriptPath': None, 'command': command,
                'cwd': '/independent/approved-workspace', 'processId': None, 'source': 'agent',
                'status': 'inProgress', 'commandActions': actions,
                'aggregatedOutput': None, 'exitCode': None, 'durationMs': None}
        steps.extend([_protocol_item('item/started', item),
                      _protocol_item('item/completed', {**item, 'status': 'completed',
                                      'aggregatedOutput': hidden, 'exitCode': 0, 'durationMs': 1})])
    actor = main_actor([steps])
    actor.connect()
    starts = [row for row in map(json.loads, actor.trace.read_text().splitlines())
              if row.get('method') == 'thread/start']
    assert starts, 'The command fixture belongs to an actual original bootstrapped runtime workspace'
    for step in steps:
        step['notification']['params']['item']['cwd'] = starts[-1]['params']['cwd']
    actor.configure_turns([steps])
    actor.request('Read the already selected public information; do not change the scientific model.')
    _rows_wait(actor, lambda value: value['state'] == 'idle' and value['count'] >= len(cases) + 2)
    assert qml(actor, 'Preferences.assistantCopyTechnicalDetails') is False, (
        'Original human command meanings remain available without technical opt-in')
    rows = [_rows_values(actor, 'messages', i) for i in range(_rows_probe(actor)['count'])]
    activities = [row for row in rows if row['kind'] == 'activity']
    assert len(activities) == len(cases), 'All independently pinned command item pairs reach actual retained activity rows'
    view = control_expression('assistant.messages')
    observed = []
    for current, (identity, command, actions, expected) in zip(activities, cases):
        index = next(i for i, row in enumerate(rows) if row['id'] == current['id'])
        actor.command('evaluate', expression='(function(){const v=' + view
                      + ';v.positionViewAtIndex(' + str(index) + ',ListView.Center);})()')
        response = actor.command('message_input', row_id=current['id'],
                                  name='assistant.activity.toggle', action='click')['reply']
        assert response['reached'] and response['same_row_after'], (
            'Known command description is expanded through its exact original realized Qt activity control')
        expression = '(function seek(x){if(x.rowId===' + json.dumps(current['id']) + '\
&&typeof x.humanDetailsSnapshot!=="undefined"){const out=[];function visit(y){\
if(y.objectName==="assistant.activity.details")out.push(y.text);\
Array.from(y.children||[]).forEach(visit);}visit(x);return out;}\
for(const c of (x.children||[])){const r=seek(c);if(r)return r;}return null;})(contentItem)'
        displayed = qml(actor, expression)
        assert displayed and expected in '\n'.join(displayed), (
            'Lazy full-human expansion preserves the FIRST known skill/read/list/search/declared-purpose meaning')
        assert hidden not in '\n'.join(displayed) and 'opaque unread technical script' not in '\n'.join(displayed), (
            'Human expansion never displays raw command/output trees as a substitute for the missing description')
        actor.command('message_input', row_id=current['id'], name='assistant.activity.toggle', action='hover')
        copied = actor.command('message_input', row_id=current['id'], name='assistant.activity.copy', action='click')['reply']
        assert copied['reached'] and expected in copied['clipboard'] and hidden not in copied['clipboard'], (
            'Default original-row Copy retains the useful human command meaning without technical output')
        args = ','.join(json.dumps(current[key]) for key in ('id', 'kind', 'status'))
        technical = qml(actor, 'Session.assistant.activityTechnicalDetails(' + args + ')')
        original = json.loads(technical)
        assert original['payload']['command'] == command and original['payload']['aggregatedOutput'] == hidden, (
            'Explicit exact-row technical lookup still retains immutable original command/output evidence')
        actor.command('message_input', row_id=current['id'], name='assistant.activity.toggle', action='click')
        observed.append({'fixture': identity, 'row_id': current['id'], 'human': displayed,
                         'default_copy': copied['clipboard']})
    (actor.folder / 'command-human-compatibility.json').write_text(json.dumps(observed, indent=2))


def test_sparse_interruption_notifies_only_original_changed_status_cells(main_actor):
    # Legal overlapping public research items; a deliberate real peer EOF then
    # invokes the FIRST interrupt-pending-rows publication in one native owner.
    # Completed middle B is the independent unchanged-cell control.
    def item(identity):
        return {'type': 'webSearch', 'id': identity, 'query': '', 'action': None, 'results': None}
    a, b, c = (item('sparse-' + identity) for identity in ('A', 'B', 'C'))
    steps = [_protocol_item('item/started', a), _protocol_item('item/started', b),
             _protocol_item('item/completed', {**b, 'query': 'Independent completed reference',
                 'action': {'type': 'search', 'query': 'reference', 'queries': None}, 'results': []}),
             _protocol_item('item/started', c)]
    actor = main_actor([steps], hold_final=True)
    config_path = actor.folder / 'peer.json'
    config = json.loads(config_path.read_bytes());config['terminal_status'] = 'process_exit'
    config_path.write_text(json.dumps(config))
    actor.connect();actor.request('Read these public sources without changing the scientific model.')
    _rows_wait(actor, lambda value: value['count'] >= 4 and value['state'] != 'idle')
    before = [_rows_values(actor, 'messages', i) for i in range(_rows_probe(actor)['count'])]
    activities = [(i, row) for i, row in enumerate(before) if row['kind'] == 'activity']
    assert len(activities) == 3, 'The sparse fixture reaches all three original distinct activity rows before EOF'
    assert activities[0][1]['status'] in ('pending', 'in_progress') and activities[1][1]['status'] == 'completed' \
        and activities[2][1]['status'] in ('pending', 'in_progress'), (
        'The reached original rows contain pending A, unchanged completed B, and pending C')
    _rows_probe(actor, 'watch', capture_cells=True)
    actor.gate.touch()
    actor.command('refresh_usage')
    actor.until(lambda value: bool(value['ui']['last_error']))
    events = _rows_probe(actor, 'stop')['events']
    after = [_rows_values(actor, 'messages', i) for i in range(len(before))]
    assert after[activities[1][0]] == before[activities[1][0]], (
        'The completed middle activity remains byte/value-identical across real transport interruption')
    assert all(after[activities[i][0]]['status'] == 'interrupted' for i in (0, 2)), (
        'Both genuine pending endpoints reach the original single-publication interruption owner')
    signals = [event for event in events if event['kind'] == 'dataChanged']
    assert signals and all('changed_cells' in event for event in signals), (
        'Sparse witness retains actual signal-time independent before/after public cell hashes')
    for event in signals:
        actual = {(cell['row'], cell['role']) for cell in event['changed_cells']}
        roles = event['roles'] or event['all_role_names']
        announced = {(row, role) for row in range(event['first'], event['last'] + 1) for role in roles}
        assert announced <= actual, (
            'Original Rows never announces an unchanged intermediate row or an unchanged endpoint role')
    (actor.folder / 'sparse-interruption-signals.json').write_text(json.dumps({
        'before': before, 'after': after, 'signals': events,
        'intentional_peer_eof': True, 'mixed_status_text_publication': 'not claimed'}, indent=2))


def _draft_text(actor):
    return qml(actor, control_expression('assistant.composer') + '.text')


def _type_original_draft(actor, text):
    actor.command('click', name='assistant.composer')
    actor.command('manual_key', key='select_all')
    actor.command('manual_text', text=text)
    assert _draft_text(actor) == text, 'The Clear witness starts from literal actual original TextArea input'


def test_explicit_clear_clears_only_captured_draft_and_preserves_account_and_project(main_actor, tmp_path):
    actor = main_actor([[]])
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'Clear changes conversation/draft ownership, not the current ordinary scientific project')
    actor.connect();actor.request('Retain this completed conversation as the original Clear positive.')
    actor.until(lambda value: value['ui']['state'] == 'idle' and bool(value['ui']['messages']))
    account = qml(actor, 'Session.assistant.account')
    science = actor.last['ui']['project']
    _type_original_draft(actor, 'This captured unsent draft should clear.')
    files = _attachment_fixtures(tmp_path, 1)
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(files[0])])['reply']['added'], (
        'The captured unsent draft owns a genuinely pending attachment')
    actor.command('click', name='assistant.clear')
    actor.until(lambda value: not value['ui']['messages'])
    assert _draft_text(actor) == '', 'Only successful explicit Clear removes its captured literal unsent text'
    assert not any(row['pending'] for row in _attachment_rows(actor)), (
        'Successful explicit Clear also retires its captured pending files')
    assert qml(actor, 'Session.assistant.connected') and qml(actor, 'Session.assistant.account') == account, (
        'Explicit conversation/draft Clear does not sign out the actual account')
    assert actor.command('inspect')['ui']['project'] == science, (
        'Conversation Clear preserves the original current scientific project and parameter state')
    _type_original_draft(actor, 'Fresh text typed after successful Clear remains.')
    actor.command('refresh_usage')
    assert _draft_text(actor) == 'Fresh text typed after successful Clear remains.', (
        'Later notifications cannot erase a fresh draft after the captured Clear has committed')


def test_clear_requested_callback_newer_original_editor_input_is_not_erased(main_actor):
    actor = main_actor([[]]);actor.connect()
    actor.request('An original completed message before explicit Clear.')
    actor.until(lambda value: value['ui']['state'] == 'idle' and bool(value['ui']['messages']))
    old = 'Captured before Clear.'
    suffix = ' Newer text during the original requested signal.'
    _type_original_draft(actor, old)
    # Ordinary editor method in a public synchronous UI callback; no backend
    # history setter, property force, fabricated consent or altered owner.
    expression = '(function(){const a=Session.assistant,e=' + control_expression('assistant.composer') + ';'
    expression += 'const once=function(intent){a.conversationClearRequested.disconnect(once);e.insert(e.length,' + json.dumps(suffix) + ');};'
    expression += 'a.conversationClearRequested.connect(once);return true;})()'
    assert qml(actor, expression), 'The genuine original Clear requested signal has one test-owned ordinary editing observer'
    actor.command('click', name='assistant.clear')
    actor.until(lambda value: not value['ui']['messages'])
    assert _draft_text(actor) == old + suffix, (
        'A newer editor revision arriving after Clear capture survives the old intent commit')


def test_unrelated_ordinary_project_context_change_preserves_unsent_draft(main_actor, tmp_path):
    actor = main_actor([[]]);actor.connect()
    text = 'Unsent user text belongs to this composer, not a context retirement.'
    _type_original_draft(actor, text)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'An ordinary native project Open reaches a real context/owner transition')
    assert _draft_text(actor) == text, (
        'Project/context retirement does not impersonate explicit conversation Clear or erase unsent text')


def test_short_attachment_remove_cross_follows_rendered_label_by_normal_space_width(main_actor, tmp_path):
    actor = main_actor([[]]);file = _attachment_fixtures(tmp_path, 1)[0]
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(file)])['reply']['added'], (
        'Remove-cross geometry uses an original genuinely admitted current attachment')
    identity = next(row['id'] for row in _attachment_rows(actor) if row['pending'])
    info = qml(actor, '(function(){const row=' + control_expression('assistant.file.' + identity)
        + ';if(!row)return null;const label=Array.from(row.children).find(x=>typeof x.text==="string"&&x.text.indexOf('
        + json.dumps(file.name) + ')>=0);const button=Array.from(row.children).find(x=>x.fontIcon==="times");'
        'if(!label||!button||!button.contentItem)return null;const icon=button.contentItem;'
        'const fm=Qt.createQmlObject("import QtQuick; FontMetrics {}",contentItem);fm.font=label.font;'
        'const space=fm.advanceWidth(" ");fm.destroy();'
        'return {gap:icon.mapToItem(contentItem,0,0).x-(label.mapToItem(contentItem,0,0).x+label.contentWidth),'
        'space:space,labelText:label.text,buttonVisible:button.visible,buttonEnabled:button.enabled};})()')
    assert info and info['buttonVisible'] and info['buttonEnabled'] and info['space'] > 0, (
        'Actual original label/font/remove control geometry is reached before spacing is judged')
    assert info['space'] - 1 <= info['gap'] <= 2 * info['space'] + 1, (
        'The actual remove glyph follows its short painted label by one to two normal font spaces, not the far line edge')


def test_hidden_chat_working_stop_group_is_immediately_left_of_original_fit_group(main_actor, tmp_path):
    actor = main_actor([[{'research': {'query': 'Public reference', 'action': None, 'results': None},
                          'call_id': 'working-layout-reference'}]], hold_final=True)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'Status layout reaches the real ordinary project and existing Fit controls')
    actor.connect();actor.request('Read the public reference without changing science.')
    actor.until(lambda value: value['ui']['can_cancel'])
    actor.command('click', name='assistant.toggle')
    working = control_expression('statusBar.assistant.working')
    fit = control_expression('statusBar.fit')
    info = qml(actor, '(function(){const w=' + working + ',f=' + fit
        + ';if(!w||!f)return null;const a=w.parent,ap=a.mapToItem(contentItem,0,0),fp=f.mapToItem(contentItem,0,0);'
        'return {assistant:{x:ap.x,y:ap.y,width:a.width,height:a.height,visible:a.visible},'
        'fit:{x:fp.x,y:fp.y,width:f.width,height:f.height,visible:f.visible},sameParent:a.parent===f.parent};})()')
    assert info and info['sameParent'] and info['assistant']['visible'] and info['fit']['visible'], (
        'Working and original Fit groups are both actually visible in the same real status bar')
    assert info['assistant']['x'] + info['assistant']['width'] <= info['fit']['x'], (
        'AI working/Stop group precedes the original Fit group without overlap')
    actor.command('click', name='assistant.stopVisibleAction')
    actor.until(lambda value: not value['ui']['can_cancel'])
    (actor.folder / 'statusbar-working-fit-geometry.json').write_text(json.dumps({
        'actual_geometry': info, 'latency_qualification': 'No pointer hitch/frame-cost measurement is inferred'}, indent=2))


def test_empty_session_table_keeps_dialog_width_and_refresh_next_to_original_close(main_actor):
    actor = main_actor([[]])
    _session_fixture(actor)
    path = actor.folder / 'peer.json'
    config = json.loads(path.read_bytes())
    # An authenticated runtime may have no materialized saved logs before the
    # first user turn. This is a valid empty provider list, not injected UI rows.
    config['session_fixture'].update(threads=[], list_only_fixture_threads=True)
    path.write_text(json.dumps(config))
    actor.connect();actor.command('click', name='assistant.sessions')
    assert not _session_wait(actor), 'A genuine empty runtime list reaches the original empty sessions owner'
    dialog = control_expression('assistant.sessionsDialog')
    table = control_expression('assistant.sessions.list')
    info = qml(actor, '(function(){const d=' + dialog + ',t=' + table + ';if(!d||!t)return null;'
        'const f=d.footer,c=f.standardButton(Dialog.Close);let refresh=null;'
        'function scan(x){if(x.text==="Refresh"&&x.visible)refresh=x;Array.from(x.children||[]).forEach(scan);}scan(f);'
        'if(!c||!refresh)return null;const r=refresh.mapToItem(contentItem,0,0),p=c.mapToItem(contentItem,0,0);'
        'return {dialogWidth:d.contentWidth,tableWidth:t.width,tableHeight:t.height,info:t.defaultInfoText,'
        'footerHeight:f.height,refresh:{x:r.x,y:r.y,width:refresh.width,height:refresh.height,enabled:refresh.enabled},'
        'close:{x:p.x,y:p.y,width:c.width,height:c.height,enabled:c.enabled}};})()')
    assert info and info['tableHeight'] > 0 and abs(info['tableWidth'] - info['dialogWidth']) <= 1, (
        'The genuine empty sessions table retains stable full dialog content width instead of collapsing to its label')
    assert info['info'] and 'No app-created sessions' in info['info'], (
        'An empty runtime list remains an explicit useful state rather than blank content')
    assert info['refresh']['enabled'] and info['close']['enabled'] \
        and abs(info['refresh']['y'] - info['close']['y']) <= 1, (
        'Original Refresh and Close controls are adjacent in the same real dialog footer')


@pytest.mark.parametrize('show_actions', [False, True])
def test_native_estimate_then_ids_matches_separate_original_methods_and_undo_sequence(
    main_actor, tmp_path, show_actions
):
    # Independent reference is the two original ordinary Qt owners, not an
    # assistant-generated expected ID or a claimed atomic combined operation.
    reference = main_actor([[]])
    original_path = copied_estimate_project(tmp_path / 'ordinary-reference')
    assert reference.command('open', path=str(original_path))['reply']['opened'], (
        'The naming reference uses a genuine ordinary complete project')
    reference.until(lambda value: not value['ui']['project']['calculating'])
    original = point_rows(reference)
    original_can_undo = reference.last['ui']['project']['can_undo']
    assert qml(reference, 'Session.project.estimateBackground()'), (
        'The original ordinary native Estimate produces the independently exercised reference prefix')
    reference.until(lambda value: not value['ui']['project']['calculating'])
    raw = point_rows(reference)
    qml(reference, 'Session.project.namePointsByPosition()')
    reference.until(lambda value: not value['ui']['project']['calculating'])
    named = point_rows(reference)
    assert [{k: v for k, v in row.items() if k != 'id'} for row in named] == [
        {k: v for k, v in row.items() if k != 'id'} for row in raw], (
        'The original Id-from-position operation changes only IDs, preserving raw estimator science and flags')
    undo_states = []
    reference.command('undo');reference.until(lambda value: not value['ui']['project']['calculating'])
    undo_states.append(point_rows(reference))
    if undo_states[-1] != original:
        reference.command('undo');reference.until(lambda value: not value['ui']['project']['calculating'])
        undo_states.append(point_rows(reference))
    assert undo_states[-1] == original and reference.last['ui']['project']['can_undo'] == original_can_undo, (
        'The two original ordinary operations retain their actual separate Undo behavior, including naming no-op')
    reference.close()
    call = tool_call('estimate_background', 'estimate-then-original-ids', experiment='bank')
    actor = main_actor([[call]], show_actions=show_actions)
    current = copied_estimate_project(tmp_path / 'native-subject')
    assert actor.command('open', path=str(current))['reply']['opened'], (
        'The native subject uses the same independent initial project through ordinary Open')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    assert point_rows(actor) == original, 'The two ordinary/native subjects begin with identical native point identity/value state'
    if show_actions:
        # Positive setup only, to realize the real original control before its
        # read-only public pressed-signal observation. No fabricated click/slot.
        wait_positive_tab(actor, 'appBar.tab.experiment')
        actor.command('click', name='appBar.tab.experiment')
        button = _scene_control_expression('background.namePoints')
        observer = '(function(){const b=' + button + ';if(!b)return false;'
        observer += 'const t=' + _scene_control_expression('background.list') + ';if(!t||!t.sourceModel)return false;'
        observer += 'const m=t.sourceModel,o=Qt.createQmlObject(\'import QtQuick; Item {visible:false;objectName:"e11.test.namingPresses";property int presses:0;property bool exposed:false;property int shapeEvents:0;property var events:[];property var atPress:null}\',contentItem);'
        observer += 'function snap(kind){const p=b.mapToItem(contentItem,0,0),n=Math.min(t.count,t.maxRowCountShow),last=n>0?t.itemAtIndex(n-1):null,lp=last?last.mapToItem(t,0,0):null;return {kind:kind,nativeCount:m.count,viewCount:t.count,tableHeight:t.height,contentHeight:t.contentHeight,cap:t.maxRowCountShow,buttonY:p.y,lastShownRow:last?{y:lp.y,height:last.height}:null};}'
        observer += 'function shape(kind){o.shapeEvents++;o.events=o.events.concat([snap(kind)]);}'
        observer += 'm.modelReset.connect(function(){shape("modelReset");});m.rowsInserted.connect(function(){shape("rowsInserted");});m.rowsRemoved.connect(function(){shape("rowsRemoved");});'
        observer += 'm.countChanged.connect(function(){o.events=o.events.concat([snap("sourceCountChanged")]);});'
        observer += 't.countChanged.connect(function(){o.events=o.events.concat([snap("viewCountChanged")]);});'
        observer += 't.heightChanged.connect(function(){o.events=o.events.concat([snap("tableHeightChanged")]);});'
        observer += 'b.pressedChanged.connect(function(){if(b.pressed){o.presses++;o.exposed=b.visible&&b.enabled;o.atPress=snap("genuineNamePress");}});return true;})()'
        assert qml(actor, observer), 'The Show ON witness attaches only to the actual original Id-from-position button'
    actor.connect();actor.request('Estimate the background using the current native settings.')
    actor.until(lambda value: bool(actor.responses()) and value['ui']['state'] == 'idle', visible_progress=show_actions)
    assert len(actor.responses()) == 1, 'Estimate and naming settle one original native call without replaying an uncertain Estimate'
    if show_actions:
        naming_geometry = qml(actor, '(function(){const o=' + _scene_control_expression('e11.test.namingPresses')
                              + ';return {shapeEvents:o.shapeEvents,events:o.events,atPress:o.atPress,presses:o.presses,exposed:o.exposed};})()')
        (actor.folder / 'actual-estimate-model-layout-and-name-input.json').write_text(json.dumps(naming_geometry, indent=2))
    result = native_result(actor.responses()[0])
    assert result['applied'] and result['complete'] and result['atomic'] is False, (
        'The combined native receipt truthfully reports its applied non-atomic ordinary prefix and naming completion')
    assert point_rows(actor) == named, (
        'Both modes match the two independent original native Estimate/Id-from-position owners exactly')
    if show_actions:
        proof = qml(actor, '(function(){const o=' + _scene_control_expression('e11.test.namingPresses')
                    + ';return {presses:o.presses,exposed:o.exposed};})()')
        assert proof['presses'] == 1 and proof['exposed'], (
            'Show ON genuinely presses the exposed original naming button once, including an ordinary naming no-op')
        assert naming_geometry['shapeEvents'] > 0 and naming_geometry['atPress'], (
            'Actual background shape replacement is reached before naming input is judged; no modelReset-only assumption')
        at_press = naming_geometry['atPress']
        assert at_press['nativeCount'] == len(named) and at_press['viewCount'] == len(named), (
            'The original point table adopts the actual model count before genuine Id-from-position input')
        shown = at_press['lastShownRow']
        assert at_press['tableHeight'] > 0 and shown and shown['y'] >= -1 and shown['y'] + shown['height'] <= at_press['tableHeight'] + 1, (
            'The original capped point rows have coherent visible viewport height before the naming press')
    for expected in undo_states:
        actor.command('undo');actor.until(lambda value: not value['ui']['project']['calculating'])
        assert point_rows(actor) == expected, (
            'Each native workflow Undo matches its separate ordinary-owner reference step without invented extra Undo')
    assert actor.last['ui']['project']['can_undo'] == original_can_undo, (
        'Native Estimate/naming ends at the exact original Undo boundary')
    (actor.folder / 'ordinary-estimate-name-reference.json').write_text(json.dumps({
        'original': original, 'raw_estimate': raw, 'named': named, 'undo_states': undo_states,
        'mode': show_actions, 'native_receipt': result}, indent=2))


def _session_page_fixture(actor, *, foreign=24, owned=96, page=12):
    original = _session_fixture(actor)
    template = original['thread_list']['threads'][0]
    rows = []
    for index in range(foreign + owned):
        is_foreign = index < foreign
        row = {**template, 'id': '019a0290-0000-7000-a000-' + f'{index + 1:012d}',
               'name': ('Foreign' if is_foreign else 'App conversation') + ' ' + str(index),
               'originator': 'unrelated-editor' if is_foreign else 'edi',
               'updatedAt': 1800000000 - index, 'parentThreadId': None}
        rows.append(row)
    path = actor.folder / 'peer.json';config = json.loads(path.read_bytes())
    config['session_fixture'].update(threads=rows, page_size=page, list_only_fixture_threads=True)
    path.write_text(json.dumps(config))
    return rows


def test_sessions_prefetch_near_real_scroll_boundary_and_skip_empty_filtered_pages(main_actor):
    actor = main_actor([[]]);fixture = _session_page_fixture(actor)
    actor.connect();actor.command('click', name='assistant.sessions')
    actor.until(lambda _value: _rows_probe(actor, model='sessions')['count'] > 0
                and not qml(actor, 'Session.assistant.sessionsLoading'))
    initial = _rows_probe(actor, model='sessions')['count']
    owned = [row for row in fixture if row['originator'] == 'edi']
    assert 0 < initial < len(owned) and qml(actor, 'Session.assistant.sessionsHaveMore'), (
        'Open follows initial/empty filtered pages but does not eagerly drain all runtime pages at the top')
    requests = lambda: [row for row in map(json.loads, actor.trace.read_text().splitlines())
                       if row.get('method') == 'thread/list']
    assert len(requests()) >= 3, 'Empty foreign-only initial pages advance automatically before concluding the table is empty'
    more = qml(actor, _whole_window_objects_expression()
               + '.filter(x=>x.visible&&typeof x.text==="string"&&x.text==="More sessions").length')
    assert more == 0, 'The ordinary scrollable session browser exposes no manual More link'
    original_count = len(requests());samples=[];deadline=time.monotonic()+10
    while time.monotonic() < deadline and len(requests()) == original_count:
        samples.append(actor.command('session_wheel', angle_y=-120)['reply'])
    assert samples and any(row['accepted'] and row['content_y_after'] > row['content_y_before'] for row in samples), (
        'Prefetch is judged only after a real wheel is accepted and moves the original exposed session viewport')
    assert all(row['same_window'] and row['same_source_model'] for row in samples), (
        'Ordinary wheel delivery stays on its exact original Main viewport/model owner')
    actor.until(lambda _value: not qml(actor, 'Session.assistant.sessionsLoading'))
    after = [_rows_values(actor, 'sessions', i) for i in range(_rows_probe(actor, model='sessions')['count'])]
    assert len(requests()) > original_count and len(after) > initial, (
        'Approaching the actual scroll boundary asynchronously requests and publishes the next supported cursor page')
    expected = {row['id']: row['updatedAt'] for row in owned}
    assert len({row['id'] for row in after}) == len(after) and all(row['id'] in expected for row in after), (
        'Prefetch retains unique app-owned rows without admitting foreign metadata')
    assert [expected[row['id']] for row in after] == sorted((expected[row['id']] for row in after), reverse=True), (
        'Actual last-modified ordering survives incremental page publication')
    (actor.folder / 'session-wheel-prefetch.json').write_text(json.dumps({
        'initial_rows':initial,'after_rows':len(after),'wheel':samples,
        'list_requests':[row['params'] for row in requests()]},indent=2))


def test_session_names_keep_semantic_prefix_strip_legacy_context_and_center_archive(main_actor):
    actor = main_actor([[]]);original = _session_fixture(actor)
    rows = original['thread_list']['threads'][:3]
    rows[0].update(name='Powder refinement')
    rows[1].update(name='Shared displacement comparison\n\nEDI_APPROVED_CONTEXT {"path":"/tmp/private-stage","files":[1]}')
    rows[2].update(name=None, preview='Compare the measured profile.\n\nEDI_APPROVED_CONTEXT\n{"path":"/tmp/private-stage"}')
    path=actor.folder/'peer.json';config=json.loads(path.read_bytes())
    config['session_fixture'].update(threads=rows,page_size=12,list_only_fixture_threads=True);path.write_text(json.dumps(config))
    actor.connect();actor.command('click',name='assistant.sessions');published=_session_wait(actor)
    actual={row['id']:row['name'] for row in published}
    assert actual[rows[0]['id']]=='Powder refinement', 'An already concise meaningful runtime title retains its actual human text'
    assert 'Shared displacement comparison' in actual[rows[1]['id']], (
        'Legacy technical suffix stripping preserves the original meaningful human title prefix')
    assert all(name and '\n' not in name and 'EDI_APPROVED_CONTEXT' not in name and '/tmp/' not in name
               and '{' not in name and '"files"' not in name for name in actual.values()), (
        'Session display names never expose serialized approved context, machine paths or multiline technical payload')
    state=json.loads(actor.trace.with_suffix('.provider-state.json').read_bytes())
    assert all(state['threads'][row['id']]['name']==row['name'] and state['threads'][row['id']]['preview']==row['preview']
               for row in rows), 'Readonly display fallback keeps the full original runtime metadata bytes separately'
    button=control_expression('assistant.session.archive.0')
    icon=qml(actor,'(function(){const b='+button+';if(!b||!b.contentItem)return null;const c=b.contentItem,p=c.mapToItem(b,0,0);'
             'return {visible:b.visible,enabled:b.enabled,width:b.width,height:b.height,x:p.x,y:p.y,cw:c.width,ch:c.height,'
             'textWidth:c.contentWidth,textHeight:c.contentHeight,horizontal:c.horizontalAlignment,vertical:c.verticalAlignment};})()')
    assert icon and icon['visible'] and icon['enabled'], 'The Archive centering witness reaches the genuine original idle row button'
    assert abs(icon['x']+icon['cw']/2-icon['width']/2)<=1 and abs(icon['y']+icon['ch']/2-icon['height']/2)<=1, (
        'Original Archive content remains centered in its actual same-sized table button')
    assert (icon['horizontal'] & 4 or abs(icon['cw']-icon['textWidth'])<=1) \
        and (icon['vertical'] & 128 or abs(icon['ch']-icon['textHeight'])<=1), (
        'Actual archive glyph alignment is centered, rather than only a full-width left-aligned content box')

# Independent owner contracts: H session/disclosure/cache decisions, review57,
# pinned092d thread.rs and request_processors/thread_processor.rs. These tests
# use actual first-run app/provider state, never hand-written local history.
def _session_wire(actor, method=None):
    rows = [json.loads(line) for line in actor.trace.read_text().splitlines()] if actor.trace.exists() else []
    return [row for row in rows if row.get('method') == method] if method else rows


def _session_state(actor):
    return json.loads(actor.trace.with_suffix('.provider-state.json').read_bytes())


def _session_configure(actor, **settings):
    path = actor.folder / 'peer.json'
    value = json.loads(path.read_bytes());value.update(settings)
    path.write_text(json.dumps(value))


def _session_request_with_original_disclosure(actor, text):
    # Positive fixture prelude only. Genuine current dialog acceptance preserves
    # the captured draft; neither approval state nor provider inputs are seeded.
    required = actor.last['ui']['context_consent_required']
    actor.request(text)
    if required and actor.last['ui']['context_consent_required']:
        def current_disclosure(value):
            controls = value['ui']['controls']
            def exposed(name):
                return any(row['name'] == name and row['fully_exposed'] and row['enabled']
                           for row in controls)
            return exposed('AssistantConnectionDialog') and exposed('assistant.contextDisclosureScroll')
        actor.until(current_disclosure)
        before = len(_session_state(actor)['inputs'])
        assert actor.command('accept_dialog')['reply']['accepted'], (
            'The original currently exposed disclosure owner accepts its captured fixture draft through the normal dialog operation')
        actor.until(lambda value: not value['ui']['context_consent_required'])
        (actor.folder / ('original-disclosure-acceptance-' + str(before) + '.json')).write_text(json.dumps({
            'original_pending_input_count': before,
            'disclosure_owner': 'AssistantConnectionDialog',
            'scope': 'positive fixture prelude; no seeded approval or injected user input',
            'after': {'connected': actor.last['ui']['connected'],
                      'context_consent_required': actor.last['ui']['context_consent_required']}}, indent=2))


def _session_completed(actor, count):
    actor.until(lambda value: value['ui']['state'] == 'idle'
                and len(_session_state(actor)['inputs']) == count
                and sum(len(row['turns']) for row in _session_state(actor)['threads'].values()) == count)


@pytest.mark.parametrize('operation', ['refresh', 'archive'])
@pytest.mark.parametrize('retirement', ['close_project', 'destroy_engine'])
def test_session_notification_retirement_stops_original_metadata_continuation(main_actor, tmp_path, operation, retirement):
    actor = main_actor([[]]);fixture = _session_fixture(actor)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'Metadata retirement uses an actual current ordinary scientific owner before its public notification')
    actor.connect()
    if operation == 'archive':
        qml(actor, 'Session.assistant.refreshSessions()');_session_wait(actor)
        while qml(actor, 'Session.assistant.sessionsHaveMore'):
            qml(actor, 'Session.assistant.refreshSessions(true)');_session_wait(actor)
    before = _session_wire(actor)
    assert actor.command('arm_session_notification', signal='sessions', action=retirement)['reply']['armed'], (
        'The original public metadata notification has a one-shot ordinary retirement observer')
    receipt = actor.command('session_operation', operation=operation,
        thread_id=fixture['thread_list']['expected_owned_ids'][0])
    facts = actor.command('session_fault_facts')['reply']
    assert facts['notification_hits'] >= 1 and facts['original_vm_before'], (
        'The genuine synchronous original sessionsChanged notification actually reaches the retirement callback')
    after = _session_wire(actor)[len(before):]
    assert not any(row.get('method') in ('thread/list', 'thread/read', 'thread/archive') for row in after), (
        'Retired metadata work cannot dispatch through the old account/project/browser continuation after notification')
    assert not any(row.get('method') == 'turn/start' for row in after), (
        'Read-only metadata retirement never becomes model work or a scientific mutation')
    if retirement == 'destroy_engine':
        assert not receipt['ui']['alive'], 'The actual original QML engine is destroyed before the metadata caller returns'
    else:
        assert not receipt['ui']['project'], 'Ordinary closeProject actually retires the original scientific owner'
    (actor.folder / 'metadata-retirement-receipt.json').write_text(json.dumps({
        'operation': operation, 'retirement': retirement, 'facts': facts,
        'requests_after_original_notification': after}, indent=2))


def test_optional_usage_preemption_renews_original_metadata_owner(main_actor, tmp_path):
    actor = main_actor([[]]);_session_fixture(actor)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'Optional usage preemption begins with the actual original project and current Main owner')
    release = actor.folder / 'release-actual-optional-usage'
    _session_configure(actor, hold_usage_until=str(release))
    actor.connect()
    actor.until(lambda _row: bool(_session_wire(actor, 'account/rateLimits/read')))
    original_usage = _session_wire(actor, 'account/rateLimits/read')[-1]
    replies = [row for row in map(json.loads, actor.trace.with_suffix('.sent.jsonl').read_text().splitlines())
               if row.get('id') == original_usage['id']]
    assert not replies, 'The original optional usage request is genuinely outstanding rather than an invented private state'
    assert actor.command('arm_session_notification', signal='usage', action='destroy_engine')['reply']['armed'], (
        'The actual usageChanged notification has a direct original-owner destruction observer')
    before = len(_session_wire(actor))
    receipt = actor.command('session_operation', operation='refresh')
    facts = actor.command('session_fault_facts')['reply']
    assert facts['notification_hits'] >= 1 and facts['original_vm_before'] and not receipt['ui']['alive'], (
        'Admitting real metadata preempts pending usage and reaches actual synchronous owner destruction')
    assert not any(row.get('method') == 'thread/list' for row in _session_wire(actor)[before:]), (
        'The old metadata caller cannot continue dispatch after optional-usage presentation retires its original receiver')
    (actor.folder / 'usage-preemption-owner.json').write_text(json.dumps({
        'original_usage_request': original_usage, 'actual_notification': facts}, indent=2))


def test_session_caption_projection_handles_embedded_technical_names_and_previews(main_actor):
    actor = main_actor([[]]);fixture = _session_fixture(actor)
    template = fixture['thread_list']['threads'][0]
    candidates = ['Refine using /tmp/input.cif', 'Task /var/data/measurement.xye',
                  'Task {"cwd":"/tmp/run"}', r'Task C:\\private\\input.cif']
    rows = [{**template, 'id': '019a0290-0000-7000-b000-' + f'{index+1:012d}',
             'name': value if index % 2 == 0 else None,
             'preview': value if index % 2 else '', 'updatedAt': 1800000000-index}
            for index, value in enumerate(candidates)]
    _session_configure(actor, session_fixture={'threads': rows, 'page_size': 12, 'list_only_fixture_threads': True})
    actor.connect();actor.command('click', name='assistant.sessions')
    actual = {row['id']: row['name'] for row in _session_wait(actor)}
    assert set(actual) == {row['id'] for row in rows}, 'Every independent owned raw name/preview candidate reaches its actual display projection'
    assert all(name and not any(token in name for token in ('/tmp/', '/var/', 'private', '{', '}', 'cwd', '\\'))
               for name in actual.values()), (
        'Human session names never display embedded filesystem paths or serialized objects from stored names or previews')
    raw = _session_state(actor)['threads']
    assert all(raw[row['id']]['name'] == row['name'] and raw[row['id']]['preview'] == row['preview'] for row in rows), (
        'Display-only fallback keeps the complete original runtime metadata separately without rewriting it')


@pytest.mark.parametrize('title', ['Task {"cwd":"/tmp/run"}', 'a' * 79 + '\U0001f9ea' + 'z'])
def test_outgoing_session_name_remains_human_and_valid_unicode(main_actor, tmp_path, title):
    actor = main_actor([[]]);_session_configure(actor, session_fixture={'threads': [], 'page_size': 12})
    assert actor.command('open', path=str(copied_estimate_project(tmp_path)))['reply']['opened'], (
        'Outgoing title uses the original ordinary project owner rather than a fabricated thread metadata setter')
    qml(actor, 'Session.project.title=' + json.dumps(title))
    actor.connect()
    actor.until(lambda _value: bool(_session_wire(actor, 'thread/name/set')))
    names = [row['params']['name'] for row in _session_wire(actor, 'thread/name/set')]
    assert all(name and '\ufffd' not in name and not any(0xD800 <= ord(c) <= 0xDFFF for c in name) for name in names), (
        'Actual supported outgoing name requests retain valid Unicode at the original eighty-UTF16-unit shortening boundary')
    assert all('/tmp/' not in name and '{' not in name and 'cwd' not in name for name in names), (
        'Outgoing project-derived names obey the same human-only rule as stored-name and preview display')
    (actor.folder / 'outgoing-name-source.json').write_text(json.dumps({'original_title': title, 'requests': names}, ensure_ascii=False, indent=2))


def test_reconnect_preserves_existing_semantic_name_without_project_fallback_overwrite(main_actor):
    actor = main_actor([[], []])
    semantic = 'Compare magnetic models'
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12},
        automatic_thread_name_after_first_turn=semantic, disconnect_after_turn=True)
    actor.connect();actor.request('Keep this actual first conversation for a later continuation.')
    actor.until(lambda value: not value['ui']['connected'] and len(_session_state(actor)['inputs']) == 1)
    first_id = _session_state(actor)['inputs'][0]['threadId']
    assert _session_state(actor)['threads'][first_id]['name'] == semantic, (
        'The fixture runtime actually persists its semantic name on the completed original conversation')
    boundary = len(_session_wire(actor))
    _session_configure(actor, disconnect_after_turn=False)
    actor.connect()
    resumes = _session_wire(actor, 'thread/resume')
    assert resumes and resumes[-1]['params']['threadId'] == first_id, (
        'The existing resume entrance reaches the real original persisted conversation ID')
    renames = [row['params'] for row in _session_wire(actor)[boundary:] if row.get('method') == 'thread/name/set']
    assert all(row['name'] == semantic for row in renames) and _session_state(actor)['threads'][first_id]['name'] == semantic, (
        'Project-free bootstrap cannot downgrade an existing semantic runtime name to a neutral setup fallback')


def test_genuine_session_row_click_restores_original_thread_task_and_input_reader(main_actor, tmp_path):
    actor = main_actor([[_rows_research('original-thread-public-source'),
                         tool_call('inspect_project', 'original-thread-native-inspection')], []])
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'Session selection uses one actual unchanged ordinary scientific project throughout both conversations')
    actor.connect()
    source = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], (
        'The original conversation genuinely admits its actual CIF before session selection')
    admitted = actor.last['ui']['selected_files'];file_id = admitted[0]['id']
    first_task = 'Retain the attached original CIF and compare its structure on this project.'
    actor.request(first_task);_session_completed(actor, 1)
    manifest = actor.last['ui']['selected_files']
    first_rows = [_rows_values(actor, 'messages', index) for index in range(_rows_probe(actor)['count'])]
    assert {'user', 'assistant', 'activity'} <= {row['kind'] for row in first_rows}, (
        'The genuine first conversation reaches user text, final assistant reply and actual native/research activity before restoration')
    native_result(actor.responses()[0])
    first_activity = {row['id']: qml(actor, 'Session.assistant.activityHumanDetails(' + json.dumps(row['id']) + ',' + json.dumps(row['kind']) + ',' + json.dumps(row['status']) + ')')
                      for row in first_rows if row['kind'] == 'activity'}
    assert first_activity and all(value for value in first_activity.values()), (
        'Actual completed first-thread activities have meaningful canonical human details before cache selection')
    native_before_selection = len(actor.responses())
    original = _session_state(actor)['inputs'][0]
    first_id = original['threadId'];first_model = original['effective_model']
    first_hash = hashlib.sha256(json.dumps(original['input'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    actor.command('click', name='assistant.clear')
    actor.until(lambda value: not value['ui']['messages'])
    actor.request('A separate second conversation without the original scientific task.');_session_completed(actor, 2)
    second_id = _session_state(actor)['inputs'][1]['threadId']
    assert first_id != second_id, 'Ordinary explicit Clear actually creates a distinct second provider conversation'
    starts_before = len(_session_wire(actor, 'thread/start'))
    actor.command('click', name='assistant.sessions');rows = _session_wait(actor)
    assert first_id in {row['id'] for row in rows}, 'The real first app-created conversation is present in the original session browser'
    click = actor.command('session_row_click', thread_id=first_id)['reply']
    assert click['reached'] and click['actual_pressed_changes'] > 0, (
        'Selecting a session is genuine input on the realized original row-owned MouseArea rather than a direct success slot')
    actor.until(lambda value: value['ui']['connected'] and not qml(actor, control_expression('assistant.sessionsDialog') + '.opened'))
    resumes = _session_wire(actor, 'thread/resume')
    assert resumes and resumes[-1]['params']['threadId'] == first_id and len(_session_wire(actor, 'thread/start')) == starts_before, (
        'Confirmed row selection cold-resumes the exact original runtime ID without substituting a new thread')
    assert first_task in json.dumps(actor.last['ui']['messages'], ensure_ascii=False), (
        'Only the original selected thread activity is displayed after actual provider confirmation')
    assert actor.last['ui']['selected_files'] == manifest, (
        'Selected-thread restoration retains original admitted attachment identities rather than merely cached labels')
    restored_rows = [_rows_values(actor, 'messages', index) for index in range(_rows_probe(actor)['count'])]
    restored_by_id = {row['id']: row for row in restored_rows}
    assert all(restored_by_id.get(row['id']) == row for row in first_rows), (
        'The original selected-thread cache restores all actual user, assistant and activity rows with their exact identities/text/status')
    assert len(actor.responses()) == native_before_selection, (
        'Restoring native activity is display/readback only and never replays the original inspection or another native call')
    for row in first_rows:
        if row['kind'] != 'activity':
            continue
        details = qml(actor, 'Session.assistant.activityHumanDetails(' + json.dumps(row['id']) + ',' + json.dumps(row['kind']) + ',' + json.dumps(row['status']) + ')')
        assert details == first_activity[row['id']], (
            'Selected-thread activity details come from the original canonical row rather than a user-only transcript surrogate')
        restored_index = next(index for index, candidate in enumerate(restored_rows) if candidate['id'] == row['id'])
        qml(actor, '(function(){const view=' + control_expression('assistant.messages')
            + ';view.positionViewAtIndex(' + str(restored_index) + ',ListView.Center);})()')
        metrics = _rows_view_metrics(actor)
        assert metrics and any(candidate['id'] == row['id'] for candidate in metrics['rows']), (
            'Ordinary original history positioning genuinely realizes the restored activity before exact-row physical input')
        action = actor.command('message_input', row_id=row['id'], name='assistant.activity.toggle', action='click')['reply']
        assert action['reached'], (
            'The restored actual native/research activity is realized and accepts original-row disclosure input in the real history viewport')
        actor.command('message_input', row_id=row['id'], name='assistant.activity.toggle', action='click')
    frame = actor.folder / 'selected-original-all-kinds.png'
    assert actor.command('capture_frame', path=str(frame))['reply']['saved'], (
        'The real selected-thread history retains a current rendered Main frame for all-kind display review')
    actor.append_turn([tool_call('read_selected_file', 'read-after-real-session-selection',
        file_id=file_id, offset=0, max_bytes=source.stat().st_size)])
    actor.request('Continue by reading the original attached CIF without changing scientific values.')
    _session_completed(actor, 3)
    state = _session_state(actor);followup = state['inputs'][-1]
    assert followup['threadId'] == first_id and followup['actual_prior_input_count'] == 1 \
        and followup['first_actual_input_sha256'] == first_hash and followup['effective_model'] == first_model, (
        'The genuine next request continues the actual first thread/input/model rather than injecting a cached task into a fresh thread')
    result = native_result(actor.responses()[-1])
    assert any(value == source.read_text() for row in objects(result) for value in row.values() if isinstance(value, str)), (
        'The resumed actual native input reader retains original approved bytes, not only visible attachment metadata')
    (actor.folder / 'selected-thread-continuity.json').write_text(json.dumps({
        'first_thread': first_id, 'second_thread': second_id, 'click': click,
        'first_actual_input_sha256': first_hash, 'followup': followup,
        'original_manifest': manifest, 'resume_requests': [row['params'] for row in resumes]}, indent=2))


def test_preferences_cached_history_clear_keeps_runtime_task_inputs_project_and_reports(main_actor, tmp_path):
    actor = main_actor([[tool_call('inspect_project', 'cache-only-original-inspection')], []])
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    assert actor.command('open', path=str(copied_estimate_project(tmp_path)))['reply']['opened'], (
        'Cache-only clear begins with a genuine complete saved scientific project')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    actor.connect();source = _attachment_fixtures(tmp_path, 1)[0]
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], (
        'Cached-history clearing must preserve a genuinely admitted task input rather than only a label')
    first = 'Keep this actual conversation while clearing only its local displayed activity cache.'
    actor.request(first);_session_completed(actor, 1);native_result(actor.responses()[0])
    account = qml(actor, 'Session.assistant.account')
    manifest = actor.command('inspect')['ui']['selected_files']
    model = actor.last['ui']['project']
    rows = [_rows_values(actor, 'messages', index) for index in range(_rows_probe(actor)['count'])]
    assert {'user', 'assistant', 'activity'} <= {row['kind'] for row in rows}, (
        'Cache clearing is tested against actual user, assistant and native activity rather than an empty display')
    details = {row['id']: qml(actor, 'Session.assistant.activityHumanDetails(' + json.dumps(row['id']) + ',' + json.dumps(row['kind']) + ',' + json.dumps(row['status']) + ')')
               for row in rows if row['kind'] == 'activity'}
    original_thread = _session_state(actor)['inputs'][0]['threadId']
    project_path = Path(model['path'])
    before_files = {str(path.relative_to(project_path)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in project_path.rglob('*') if path.is_file()}
    before_requests = len(_session_wire(actor))
    actor.command('click', name='appBar.button.preferences')
    actor.command('click', name='preferences.tab.aiAssistance')
    actor.until(lambda value: any(control['name'] == 'preferences.ai.clearCachedHistory'
                and control['enabled'] and control['fully_exposed'] for control in value['ui']['controls']))
    actor.command('click', name='preferences.ai.clearCachedHistory')
    actor.until(lambda _value: not qml(actor, 'Session.assistant.cachedHistoryClearing'))
    assert not qml(actor, 'Session.assistant.cachedHistoryError'), (
        'A successful cache-clear result represents its original durable write completion without concealing a local failure')
    assert _rows_probe(actor)['count'] == 0, 'Successful cache-only clear hides old displayed rows without starting another conversation'
    assert all(qml(actor, 'Session.assistant.activityHumanDetails(' + json.dumps(row['id']) + ',' + json.dumps(row['kind']) + ',' + json.dumps(row['status']) + ')') == details[row['id']]
               for row in rows if row['kind'] == 'activity'), (
        'Removing cached display retains the immutable canonical native activity evidence and its actual human outcome')
    after_requests = _session_wire(actor)[before_requests:]
    assert not any(row.get('method') in ('thread/archive', 'thread/start', 'thread/resume', 'turn/start') for row in after_requests), (
        'Local cache cleanup cannot archive, replace, resume or send work to the actual runtime conversation')
    assert qml(actor, 'Session.assistant.connected') and qml(actor, 'Session.assistant.account') == account, (
        'Cache-only history cleanup retains the original authenticated connection and account')
    snapshot = actor.command('inspect')['ui']
    assert snapshot['project'] == model and snapshot['selected_files'] == manifest, (
        'Cache-only clearing preserves actual scientific values, current project and retained task admissions')
    assert all((project_path / relative).is_file() and hashlib.sha256((project_path / relative).read_bytes()).hexdigest() == digest
               for relative, digest in before_files.items()), (
        'Every preexisting scientific/report file remains byte-identical after local chat-cache clearing')
    qml(actor, '(function(){const dialog=' + control_expression('preferences') + ';if(dialog)dialog.close();})()')
    actor.request('Continue the same original conversation after local display cleanup.');_session_completed(actor, 2)
    assert _session_state(actor)['inputs'][-1]['threadId'] == original_thread, (
        'The next genuine message continues the same model conversation after cache-only cleanup rather than silently creating one')
    visible = [_rows_values(actor, 'messages', index) for index in range(_rows_probe(actor)['count'])]
    assert not ({row['id'] for row in visible} & {row['id'] for row in rows}), (
        'A later successful publication cannot resurrect the old cleared display rows from canonical or delayed cache state')
    (actor.folder / 'cache-only-boundaries.json').write_text(json.dumps({
        'original_thread': original_thread, 'original_rows': rows,
        'new_rows': visible, 'preserved_project_file_hashes': before_files,
        'requests_during_clear': after_requests}, indent=2))


def _two_genuine_session_threads(actor):
    actor.connect();actor.request('First genuine app-owned conversation for exact selection.')
    _session_completed(actor, 1)
    original = _session_state(actor)['inputs'][0]['threadId']
    actor.command('click', name='assistant.clear')
    actor.until(lambda value: not value['ui']['messages'])
    actor.request('Second distinct current conversation before selecting the original.')
    _session_completed(actor, 2)
    current = _session_state(actor)['inputs'][1]['threadId']
    assert original != current, 'The selector fixture obtains two distinct actual provider IDs through ordinary conversation owners'
    return original, current


def test_session_selection_preserves_required_current_disclosure_until_real_dialog_acceptance(main_actor, tmp_path):
    actor = main_actor([[], []])
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12})
    original, current = _two_genuine_session_threads(actor)
    source = _attachment_fixtures(tmp_path, 1)[0]
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], (
        'A genuinely new admitted file changes the current outgoing disclosure after the earlier approval')
    assert actor.last['ui']['connected'] and actor.last['ui']['context_consent_required'], (
        'The consent discriminator actually reaches authenticated idle state with required new context approval')
    before = len(_session_wire(actor))
    actor.command('click', name='assistant.sessions');_session_wait(actor)
    clicked = actor.command('session_row_click', thread_id=original)['reply']
    assert clicked['reached'] and clicked['actual_pressed_changes'] > 0, (
        'The consent boundary is exercised by actual original-row selection input, not direct approval or a success signal')
    actor.until(lambda value: any(row['name'] == 'assistant.contextSummary' and row['visible'] for row in value['ui']['texts']))
    pending = _session_wire(actor)[before:]
    assert not any(row.get('method') in ('thread/resume', 'thread/start', 'turn/start') for row in pending), (
        'Discovering/selecting an owned runtime ID cannot stage or transmit newly unapproved context before its original disclosure owner accepts')
    assert actor.last['ui']['context_consent_required'], 'Selection intent itself cannot manufacture approval of the changed captured disclosure'
    assert actor.command('accept_dialog')['reply']['accepted'], (
        'Only genuine acceptance through the original displayed context dialog grants the required current approval')
    actor.until(lambda value: value['ui']['connected'] and not value['ui']['context_consent_required'])
    resumes = _session_wire(actor, 'thread/resume')
    assert resumes and resumes[-1]['params']['threadId'] == original, (
        'After actual disclosure acceptance the pending original selector resumes its exact target rather than the prior or a new thread')
    (actor.folder / 'selection-consent-boundary.json').write_text(json.dumps({
        'original': original, 'previous_current': current, 'physical_click': clicked,
        'requests_before_acceptance': pending, 'confirmed_resume': resumes[-1]}, indent=2))


@pytest.mark.parametrize('operation', ['list', 'select_read', 'archive_read'])
def test_actual_metadata_transport_failure_settles_original_browser_waiter(main_actor, operation):
    actor = main_actor([[], []]);release = actor.folder / 'release-original-metadata'
    fixture = _session_fixture(actor)
    settings = fixture['thread_list'].copy()
    settings['list_hold' if operation == 'list' else 'read_hold'] = str(release)
    _session_configure(actor, session_fixture=settings)
    if operation == 'select_read':
        original, _current = _two_genuine_session_threads(actor)
    else:
        actor.connect();original = fixture['thread_list']['expected_owned_ids'][0]
    actor.command('click', name='assistant.sessions')
    if operation != 'list':
        _session_wait(actor)
        while qml(actor, 'Session.assistant.sessionsHaveMore'):
            qml(actor, 'Session.assistant.refreshSessions(true)');_session_wait(actor)
        if operation == 'select_read':
            clicked = actor.command('session_row_click', thread_id=original)['reply']
            assert clicked['reached'] and clicked['actual_pressed_changes'] > 0, (
                'The failed select-read fixture reaches actual original-row input before the transport interruption')
        else:
            actor.command('session_operation', operation='archive', thread_id=original)
    actor.until(lambda _value: qml(actor, 'Session.assistant.sessionsLoading'))
    wanted = 'thread/list' if operation == 'list' else 'thread/read'
    request = _session_wire(actor, wanted)[-1]
    emitted = [row for row in map(json.loads, actor.trace.with_suffix('.sent.jsonl').read_text().splitlines()) if row.get('id') == request['id']]
    assert not emitted, 'The original browser operation really has an outstanding correlated server request before transport failure'
    facts = actor.command('close_owned_transport_write')['reply']
    assert facts['original_vm_child'] and facts['public_close_write_channel_invoked'], (
        'The physical fault closes only the proved current fixture-owned child transport through its public QProcess operation')
    actor.until(lambda value: not value['ui']['connected'] and not qml(actor, 'Session.assistant.sessionsLoading'))
    error = qml(actor, 'Session.assistant.sessionsError')
    assert error, 'Terminal transport failure releases the original browser waiter while retaining its actual failed-operation cause'
    assert qml(actor, control_expression('assistant.sessionsDialog') + '.opened'), (
        'A failed operation does not falsely confirm selection or dismiss the original session browser')
    (actor.folder / 'failed-browser-original-waiter.json').write_text(json.dumps({
        'operation': operation, 'outstanding_request': request, 'physical_fault': facts,
        'retained_error': error, 'newer_operation_ordering': 'not exercised'}, indent=2))


def test_exact_selection_bootstrap_refusal_releases_loading_without_success_or_replay(main_actor):
    actor = main_actor([[], []])
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12, 'resume_error': True})
    original, current = _two_genuine_session_threads(actor)
    before_native = len(actor.responses());before_turns = len(_session_wire(actor, 'turn/start'))
    actor.command('click', name='assistant.sessions');_session_wait(actor)
    clicked = actor.command('session_row_click', thread_id=original)['reply']
    assert clicked['reached'] and clicked['actual_pressed_changes'] > 0, 'The bootstrap failure begins with real input on the exact original session row'
    actor.until(lambda _value: bool(_session_wire(actor, 'thread/resume')) and not qml(actor, 'Session.assistant.sessionsLoading'))
    assert qml(actor, 'Session.assistant.sessionsError'), (
        'A refused original resume is terminal failed browser work, with a visible cause and released loading state')
    assert qml(actor, control_expression('assistant.sessionsDialog') + '.opened'), (
        'The selector closes only on actual successful confirmation, never an error or deliberate old-transport retirement')
    assert len(actor.responses()) == before_native and len(_session_wire(actor, 'turn/start')) == before_turns, (
        'Failed metadata/bootstrap selection cannot replay a prior native operation or invent a replacement user turn')
    (actor.folder / 'failed-selection-bootstrap.json').write_text(json.dumps({
        'target': original, 'previous_current': current, 'physical_click': clicked,
        'resume_requests': _session_wire(actor, 'thread/resume'),
        'preparation_filesystem_failure': 'not exercised', 'newer_waiter_ordering': 'not exercised'}, indent=2))

# Original public archive API, real current app snapshots, and the exact-path
# read/sync/rename witness. No canonical rows or native receipts are invented.
def _archive_candidates(actor):
    storage = Path(actor.last['test_storage'])
    app_data = Path(actor.last['test_settings']['app_local_data'])
    assert app_data.resolve().is_relative_to(storage.resolve()), 'Archive capture first proves the actual Qt-owned app-cache root belongs to this run'
    directory = app_data / 'assistant'
    return [directory / 'history.json', *directory.glob('history-recovered-*.json'), *directory.joinpath('history').glob('*.json')]


def _capture_genuine_archive(actor, label):
    actual_rows = [_rows_values(actor, 'messages', index) for index in range(_rows_probe(actor)['count'])]
    # Hf51d49068/H92: activity/error display text is intentionally blank. Full
    # canonical text belongs only to the backend, never to these view cells.
    desired = {row['id']: {key: value for key, value in row.items()
               if key != 'text' or row['kind'] in ('user', 'assistant')}
               for row in actual_rows}
    original_ids = set(desired)
    assert original_ids, 'A captured archive comes from actual nonempty first-run app rows rather than a constructed snapshot'
    receipt = qml(actor, 'Session.assistant.workReportReceipt')
    report_paths = set()
    def reported_paths(value):
        if isinstance(value, dict):
            for child in value.values():reported_paths(child)
        elif isinstance(value, list):
            for child in value:reported_paths(child)
        elif isinstance(value, str) and value.endswith('.json'):
            from urllib.parse import unquote, urlparse
            path = Path(unquote(urlparse(value).path)) if value.startswith('file:') else Path(value)
            if path.is_absolute():report_paths.add(path)
    reported_paths(receipt)
    storage = Path(actor.last['test_storage']).resolve()
    project_path = actor.last['ui'].get('project', {}).get('path')
    report_root = Path(project_path).resolve() / 'reports' if project_path else None
    observation = {};reports = {};report_copies = {}
    def actual_report_rows():
        if report_root and report_root.is_dir():report_paths.update(report_root.glob('*.json'))
        def modified(path):
            try:return (path.stat().st_mtime_ns, str(path))
            except OSError:return (-1, str(path))
        # Current canonical publication wins over older same-status snapshots;
        # filesystem freshness only orders actual reports, never creates rows.
        for path in sorted(report_paths, key=modified):
            try:
                actual = path.resolve(strict=True)
                allowed = actual.is_relative_to(storage) or (report_root and actual.is_relative_to(report_root))
                if not allowed or path.is_symlink() or actual.stat().st_uid != os.geteuid():continue
                raw = actual.read_bytes();document = json.loads(raw)
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(document, dict) or not isinstance(document.get('history_evidence'), list):continue
            fingerprint = hashlib.sha256(raw).hexdigest()
            for entry in document['history_evidence']:
                row = entry.get('row') if isinstance(entry, dict) else None
                if not isinstance(row, dict) or row.get('id') not in original_ids:continue
                # A stale report is evidence of its old state, never a reason to
                # demand that the current cache regress to an older status.
                if row.get('status') != desired[row['id']]['status']:continue
                reports[row['id']] = {'row': row, 'source': str(actual), 'sha256': fingerprint}
            if any(row['source'] == str(actual) and row['sha256'] == fingerprint for row in reports.values()):
                copied = actor.folder / ('genuine-' + label + '-report-' + fingerprint[:16] + '.json')
                if not copied.exists():copied.write_bytes(raw)
                report_copies[fingerprint] = {'source': str(actual), 'copy': str(copied), 'sha256': fingerprint}
        return reports
    def ready(_value):
        actual_report_rows()
        for path in _archive_candidates(actor):
            try:
                raw = path.read_bytes();rows = json.loads(raw)
            except (OSError, json.JSONDecodeError):
                continue
            indexed = {row['id']: row for row in rows if isinstance(row, dict) and 'id' in row} if isinstance(rows, list) else {}
            if not original_ids <= indexed.keys():continue
            if not all(all(indexed[identity].get(key) == value for key, value in expected.items())
                       for identity, expected in desired.items()):continue
            # Cross-check actual canonical report text where genuinely retained;
            # never manufacture canonical rows from compact display values.
            if not all(all(indexed[identity].get(key) == value['row'].get(key)
                           for key in ('id', 'kind', 'status', 'text'))
                       for identity, value in reports.items()):continue
            observation.update(source=path, raw=raw, rows=rows)
            return True
        return False
    try:
        actor.until(ready)
    except BaseException:
        # Preserve reached raw files before the temporary ordinary owner closes.
        # These are failed-boundary observations, NOT positive restore fixtures.
        failed = []
        for index, path in enumerate(_archive_candidates(actor)):
            try:raw = path.read_bytes()
            except OSError:continue
            copied = actor.folder / ('failed-' + label + '-cache-' + str(index) + '.json')
            copied.write_bytes(raw);failed.append({'source': str(path), 'copy': str(copied),
                'sha256': hashlib.sha256(raw).hexdigest(), 'qualification': 'failed capture boundary only'})
        (actor.folder / ('failed-' + label + '-capture.json')).write_text(json.dumps({
            'raw_observations': failed, 'canonical_report_copies': list(report_copies.values()),
            'display_projection': actual_rows, 'positive_snapshot': False}, indent=2))
        raise
    copied = actor.folder / ('genuine-' + label + '.json')
    copied.write_bytes(observation['raw'])
    result = {'source': str(observation['source']), 'captured': str(copied),
        'sha256': hashlib.sha256(observation['raw']).hexdigest(), 'bytes': len(observation['raw']),
        'original_visible_ids': sorted(original_ids),
        'source_bytes_unchanged': observation['source'].read_bytes() == copied.read_bytes(),
        'canonical_report_crosschecked_ids': sorted(reports),
        'canonical_report_copies': list(report_copies.values()),
        'report_crosscheck': 'observed matching canonical rows' if reports else 'not observed; no report-derived cache content invented',
        'projection_contract': 'IDs/kinds/status plus exact user/assistant text; full raw canonical bytes copied unchanged'}
    (actor.folder / ('genuine-' + label + '-provenance.json')).write_text(json.dumps(result, indent=2))
    assert result['source_bytes_unchanged'], 'Only byte-exact genuine app history is supplied to the original public archive owner'
    return copied, observation['rows'], result


def _arm_owned_archive_io(gate, actor, target, mode):
    target = Path(target);storage = Path(actor.last['test_storage']).resolve()
    assert target.resolve().is_relative_to(storage) and not target.is_symlink(), (
        'Every archive I/O fault is confined to the exact fixture-owned normal cache target')
    assert mode in ('hold', 'hold_read', 'fail'), 'Only the explicitly elected sync/read/atomic-replace boundaries are scheduled'
    gate.target = target;gate.epoch += 1
    gate.release = gate.folder / ('release-owned-archive-' + str(gate.epoch))
    gate.release.unlink(missing_ok=True)
    control = gate.control.with_suffix('.new')
    control.write_text(f'{mode}\n{target}\n{gate.release}\n{gate.epoch}\n')
    control.replace(gate.control)
    (actor.folder / ('archive-io-target-' + str(gate.epoch) + '.json')).write_text(json.dumps({
        'target': str(target), 'mode': mode, 'epoch': gate.epoch,
        'exists_at_admission': target.exists(), 'release': str(gate.release)}, indent=2))


def _archive_wait(actor, key, predicate):
    actual = {}
    def reached(_value):
        actual.clear();actual.update(actor.command('archive_probe_view', key=key)['reply'])
        return predicate(actual)
    actor.until(reached)
    return actual


def _archive_durable(view):
    return view['loaded'] and not view['working'] and not view['pending'] and view['durable'] >= view['accepted']


def _archive_first_snapshot(main_actor):
    actor = main_actor([[tool_call('inspect_project', 'genuine-cache-native-row')]])
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12})
    actor.connect();actor.request('Retain the actual user, assistant and native inspection rows for the original archive boundary.')
    _session_completed(actor, 1);native_result(actor.responses()[0])
    source, rows, receipt = _capture_genuine_archive(actor, 'settled-native')
    assert {'user', 'assistant', 'activity'} <= {row.get('kind') for row in rows}, (
        'The actual immutable archive witness contains all three reached app-history kinds including a native result')
    return actor, source, rows, receipt


def test_public_archive_initial_merge_keeps_current_same_id_and_unique_real_rows(main_actor, history_sync_gate):
    gate = history_sync_gate
    release = gate.folder / 'release-actual-research-completion'
    actor = main_actor([[_rows_research('actual-history-identity', held=release)]], hold_final=True)
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12})
    actor.connect();actor.request('Keep the original source activity identity through its actual completion.')
    _rows_wait(actor, lambda value: any(_rows_read(actor, index, 'status')['scalar'] in ('pending', 'in_progress')
        for index in range(value['count']) if _rows_read(actor, index, 'kind')['scalar'] == 'activity'))
    older_source, older, _older_receipt = _capture_genuine_archive(actor, 'genuine-pending')
    release.touch();actor.gate.touch();actor.command('refresh_usage');_session_completed(actor, 1)
    current_source, current, current_receipt = _capture_genuine_archive(actor, 'genuine-completed')
    old_by_id = {row['id']: row for row in older};new_by_id = {row['id']: row for row in current}
    changed = [identity for identity in old_by_id.keys() & new_by_id.keys()
               if old_by_id[identity].get('status') in ('pending', 'in_progress') and new_by_id[identity].get('status') == 'completed']
    assert changed, 'The collision oracle uses an actual original pending row that genuinely completed with the same ID'
    expected = {**old_by_id, **new_by_id}
    merged = actor.command('archive_probe_merge', initial_source=str(older_source), current_source=str(current_source))['reply']['rows']
    assert len(merged) == len({row['id'] for row in merged}) and {row['id']: row for row in merged} == expected, (
        'Current accepted canonical rows outrank older same-ID cache rows while unrelated real initial rows survive exactly once')
    normal_root = _archive_candidates(actor)[0].parent
    relative = 'assistant/history/' + hashlib.sha256(b'original-public-owner-merge').hexdigest() + '.json'
    target = normal_root.parent / relative
    target.parent.mkdir(parents=True, exist_ok=True);target.write_bytes(older_source.read_bytes());target.chmod(0o600)
    _arm_owned_archive_io(gate, actor, target, 'hold_read')
    try:
        actor.command('archive_probe_open', key='delayed-real-owner', relative=relative)
        actor.until(lambda _value: any(row['epoch'] == gate.epoch and row['phase'] == 'read_descriptor' for row in gate.rows()))
        reached = [row for row in gate.rows() if row['epoch'] == gate.epoch]
        assert any(row['phase'] == 'entered' and row['operation'] == 'read' and not row['main_thread'] for row in reached), (
            'The genuine initial cache read is held on its exact original worker descriptor before newer canonical admission')
        assert target.read_bytes() == older_source.read_bytes(), 'Scheduling the original read does not alter any captured cache bytes'
        retained = actor.command('archive_probe_retain', key='delayed-real-owner', source=str(current_source), includes_initial=False)['reply']
        assert retained['accepted'], 'The public original owner actually admits the newer complete real snapshot before the initial read returns'
        assert not any(row['phase'] in ('released', 'auto_release') for row in reached), (
            'The newer snapshot is admitted while the actual old read boundary remains held')
        gate.finish()
        view = _archive_wait(actor, 'delayed-real-owner', _archive_durable)
        disk = json.loads(Path(view['path']).read_bytes())
        assert len(disk) == len({row['id'] for row in disk}) and {row['id']: row for row in disk} == expected, (
            'The original worker merge writes each original ID once and preserves all newer actual fields/outcomes after delayed initialization')
        assert not any(row['phase'] == 'auto_release' for row in gate.rows()), 'No scheduling safety release substitutes for the explicitly reached/read/release ordering'
        (actor.folder / 'actual-delayed-archive-merge.json').write_text(json.dumps({
            'changed_real_ids': changed, 'current_source': current_receipt, 'view': view,
            'io_receipts': gate.rows(), 'state_history_completed_channel': 'direct shared merge plus original archive worker; no separate State-race claim'}, indent=2))
    finally:
        gate.finish()


def test_cache_clear_reaches_accepted_owner_before_file_materializes_without_token_theft(main_actor, history_sync_gate):
    gate = history_sync_gate;actor, source, rows, _receipt = _archive_first_snapshot(main_actor)
    relative = 'assistant/history/' + hashlib.sha256(b'accepted-unmaterialized-owner').hexdigest() + '.json'
    opened = actor.command('archive_probe_open', key='accepted-before-file', relative=relative)['reply']
    target = Path(opened['requested_path'])
    assert not target.exists(), 'The inventory witness begins with an accepted logical archive whose final file has never existed'
    _arm_owned_archive_io(gate, actor, target, 'hold')
    try:
        assert actor.command('archive_probe_retain', key='accepted-before-file', source=str(source), includes_initial=True)['reply']['accepted'], (
            'The original archive owner genuinely accepts the actual snapshot before any file can be inventoried')
        actor.until(lambda _value: gate.opened())
        assert not target.exists(), 'The actual held pre-publish sync proves the accepted target is still absent from filename enumeration'
        actor.command('evaluate', expression='Session.assistant.clearCachedHistory()')
        gate.finish()
        actor.until(lambda _value: not qml(actor, 'Session.assistant.cachedHistoryClearing'))
        assert not qml(actor, 'Session.assistant.cachedHistoryError'), 'Known accepted owners receive a successful actual durable clear, not a guessed filename-only completion'
        view = _archive_wait(actor, 'accepted-before-file', _archive_durable)
        assert view['clear'] > 0 and view['durable'] >= view['clear'] and json.loads(Path(view['path']).read_bytes()) == [], (
            'The accepted but previously absent owner receives the same ordered clear barrier and cannot publish old rows after reported completion')
        assert actor.command('archive_probe_retain', key='accepted-before-file', logical_clear=True, includes_initial=True)['reply']['accepted'], (
            'Inventory clearing cannot activate an alias and steal the original normal writer owner token')
    finally:
        gate.finish()


def test_failed_cache_clear_settles_and_retries_original_barrier_without_hiding_error(main_actor, history_sync_gate):
    gate = history_sync_gate;actor, source, _rows, _receipt = _archive_first_snapshot(main_actor)
    relative = 'assistant/history/' + hashlib.sha256(b'genuine-inactive-failed-clear').hexdigest() + '.json'
    opened = actor.command('archive_probe_open', key='failed-clear-owner', relative=relative, source=str(source))['reply']
    target = Path(opened['requested_path']);_archive_wait(actor, 'failed-clear-owner', lambda view: view['loaded'])
    _arm_owned_archive_io(gate, actor, target, 'fail')
    try:
        actor.command('evaluate', expression='Session.assistant.clearCachedHistory()')
        actor.until(lambda _value: any(row['phase'] == 'failed' and row['epoch'] == gate.epoch for row in gate.rows()))
        actor.until(lambda _value: not qml(actor, 'Session.assistant.cachedHistoryClearing'))
        failed = actor.command('archive_probe_view', key='failed-clear-owner')['reply']
        cause = qml(actor, 'Session.assistant.cachedHistoryError')
        assert cause and failed['failure_revision'] >= failed['clear'] > failed['durable'] and not failed['working'], (
            'An actual failed accepted clear is terminal failed work with its exact revision/cause retained, rather than permanent busy or false durability')
        assert target.read_bytes() == source.read_bytes(), 'The failed atomic clear preserves the complete original genuine cache bytes'
        (actor.folder / 'original-failed-clear-receipt.json').write_text(json.dumps({'view': failed, 'actual_error': cause, 'io': gate.rows()}, indent=2))
        actor.append_turn([]);actor.request('A genuinely newer message after the original failed cache clear.')
        _session_completed(actor, 2)
        newer_ids = {_rows_read(actor, index, 'id')['scalar'] for index in range(_rows_probe(actor)['count'])}
        assert newer_ids, 'The retry discriminator reaches genuine newer visible rows after the original clear failure has settled'
        gate.finish()
        actor.command('evaluate', expression='Session.assistant.clearCachedHistory()')
        actor.until(lambda _value: not qml(actor, 'Session.assistant.cachedHistoryClearing'))
        settled = _archive_wait(actor, 'failed-clear-owner', _archive_durable)
        assert not qml(actor, 'Session.assistant.cachedHistoryError') and settled['durable'] >= failed['clear'], (
            'A genuine explicit same-owner retry can durably finish the original failed barrier after storage is repaired')
        assert settled['clear'] == failed['clear'], 'A guarded retry finishes the original clear barrier rather than inventing a newer logical discard'
        assert {_rows_read(actor, index, 'id')['scalar'] for index in range(_rows_probe(actor)['count'])} == newer_ids, (
            'Retrying the old failed durable barrier cannot hide or clear genuinely newer accepted display rows')
        assert json.loads(target.read_bytes()) == [], 'The repaired durable clear actually publishes empty cache bytes instead of merely releasing its button'
        assert actor.command('archive_probe_retain', key='failed-clear-owner', logical_clear=True, includes_initial=True)['reply']['accepted'], (
            'Retry leaves the original archive owner token usable for later accepted snapshots')
    finally:
        gate.finish()


@pytest.mark.parametrize('owner_lifecycle', ['active_recovered', 'persisted_after_owner_drop'])
def test_cache_clear_reaches_real_recovery_path_without_replacing_original_owner(main_actor, history_sync_gate, owner_lifecycle):
    gate = history_sync_gate;actor, source, _rows, receipt = _archive_first_snapshot(main_actor)
    relative = 'assistant/history/' + hashlib.sha256(('original-recovered-owner-' + owner_lifecycle).encode()).hexdigest() + '.json'
    app_data = Path(actor.last['test_settings']['app_local_data']);target = app_data / relative
    target.parent.mkdir(parents=True, exist_ok=True);target.write_bytes(source.read_bytes());target.chmod(0)
    assert target.stat().st_mode & 0o777 == 0, 'Recovery is reached through an actual unreadable original owned file, never invented damaged rows'
    try:
        actor.command('archive_probe_open', key='genuine-recovered-owner', relative=relative)
        recovered = _archive_wait(actor, 'genuine-recovered-owner', lambda view: view['loaded'] and view['recovered'])
        assert Path(recovered['path']) != target, 'The real original archive owner reports its actual changed recovery destination'
        assert actor.command('archive_probe_retain', key='genuine-recovered-owner', source=str(source), includes_initial=True)['reply']['accepted'], (
            'The surviving original owner genuinely accepts unchanged captured rows at its recovered destination')
        durable = _archive_wait(actor, 'genuine-recovered-owner', _archive_durable)
        actual_recovery = Path(durable['path'])
        assert json.loads(actual_recovery.read_bytes()) == json.loads(source.read_bytes()), (
            'The generated recovery cache contains the actual original rows without fabricated receipts or replacement science')
        if owner_lifecycle == 'persisted_after_owner_drop':
            assert actor.command('archive_probe_drop', key='genuine-recovered-owner')['reply']['dropped'], (
                'The persisted-recovery discriminator destroys its original test owner rather than keeping an artificial active handle')
        actor.command('evaluate', expression='Session.assistant.clearCachedHistory()')
        actor.until(lambda _value: not qml(actor, 'Session.assistant.cachedHistoryClearing'))
        assert not qml(actor, 'Session.assistant.cachedHistoryError') and json.loads(actual_recovery.read_bytes()) == [], (
            'Actual cache-only clearing reaches the real recovery destination instead of reporting completion for only its old requested spelling')
        if owner_lifecycle == 'active_recovered':
            assert actor.command('archive_probe_retain', key='genuine-recovered-owner', logical_clear=True, includes_initial=True)['reply']['accepted'], (
                'Requested/current recovery aliases cannot activate another owner token over the surviving normal archive writer')
        (actor.folder / 'actual-recovery-owner-boundary.json').write_text(json.dumps({
            'requested_path': str(target), 'actual_recovery_path': str(actual_recovery),
            'actual_source': receipt, 'lifecycle': owner_lifecycle,
            'recovery_during_clear': 'not claimed by an already recovered owner',
            'legacy_bootstrap_owner': 'not exercised by this per-thread original-owner fixture'}, indent=2))
    finally:
        target.chmod(0o600)
        assert target.read_bytes() == source.read_bytes(), (
            'Recovery and cache cleanup preserve the unreadable original evidence bytes instead of overwriting the failure original')
        gate.finish()

# Review60 original account/project association and FIRST afterChanges owner.
# Both associations below are created by genuine ordinary projects/conversations.
def _two_genuine_project_session_records(main_actor, tmp_path):
    actor = main_actor([[], []])
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    target = copied_estimate_project(tmp_path);current = tmp_path / 'other-complete-current-project'
    shutil.copytree(target, current)
    assert actor.command('open', path=str(target))['reply']['opened'], 'The original target association is established by a genuine normal saved-project Open'
    actor.until(lambda value: not value['ui']['project']['calculating'])
    actor.connect();actor.request('First actual conversation associated with its original saved project.')
    _session_completed(actor, 1);target_id = _session_state(actor)['inputs'][0]['threadId']
    actor.command('click', name='assistant.clear');actor.until(lambda value: not value['ui']['messages'])
    assert actor.command('open', path=str(current))['reply']['opened'], 'An unrelated complete current project is adopted through the same original normal Open owner'
    actor.until(lambda value: not value['ui']['project']['calculating'])
    actor.connect();actor.request('A distinct actual conversation belongs to the now-current other project.')
    _session_completed(actor, 2);current_id = _session_state(actor)['inputs'][1]['threadId']
    assert current_id != target_id, 'The fixture proves two genuine distinct runtime IDs and physical project associations before selection'
    return actor, target, current, target_id, current_id


def _watch_original_project_open(actor, marker):
    expression = '(function(){const o=Qt.createQmlObject(\'import QtQuick; Item {objectName:"' + marker + '";property int changes:0;property var current:null;property var callback:null}\',contentItem);'
    expression += 'o.current=Session.project;o.callback=function(){o.changes++;};Session.projectAboutToChange.connect(o.callback);return true;})()'
    assert qml(actor, expression), 'The project-opening discriminator observes the actual public projectAboutToChange owner without changing application state'


def test_manual_selection_cannot_substitute_current_project_for_missing_original_association(main_actor, tmp_path):
    actor, target, current, target_id, _current_id = _two_genuine_project_session_records(main_actor, tmp_path)
    current_state = actor.last['ui']['project'];missing = tmp_path / 'preserved-original-project-temporarily-unavailable'
    target.rename(missing)
    assert not target.exists() and missing.is_dir(), 'The original associated path is genuinely unavailable while its exact scientific bytes remain preserved elsewhere'
    marker = 'e11.session.missing-project-observer';_watch_original_project_open(actor, marker)
    try:
        before = len(_session_wire(actor, 'thread/resume'))
        actor.command('click', name='assistant.sessions');rows = _session_wait(actor)
        assert target_id in {row['id'] for row in rows}, 'A missing scientific workspace does not hide app-owned historical metadata from discovery'
        click = actor.command('session_row_click', thread_id=target_id)['reply']
        assert click['reached'] and click['actual_pressed_changes'] > 0, 'Manual restore is attempted by genuine input on the original target row'
        actor.until(lambda _value: not qml(actor, 'Session.assistant.sessionsLoading'))
        cause = qml(actor, 'Session.assistant.sessionsError')
        assert cause and len(_session_wire(actor, 'thread/resume')) == before, (
            'Unavailable original project identity yields an honest terminal restore refusal rather than an implicit resume against the current project')
        assert actor.command('inspect')['ui']['project'] == current_state and qml(actor, '(' + control_expression(marker) + ').changes') == 0, (
            'Failed manual association restore cannot replace or decorate the unrelated current scientific owner')
        (actor.folder / 'missing-original-project-refusal.json').write_text(json.dumps({
            'original_target': str(target), 'preserved_bytes_at': str(missing), 'current_path': str(current),
            'target_thread': target_id, 'actual_cause': cause, 'click': click}, indent=2))
        missing.rename(target)
        # A separate explicit intent after the actual resource is repaired; no
        # uncertain native action or model input is replayed.
        click = actor.command('session_row_click', thread_id=target_id)['reply']
        assert click['reached'], 'The repaired original row remains available for a genuinely new explicit restore intent'
        actor.until(lambda value: value['ui']['connected'] and Path(value['ui']['project'].get('path', '')).resolve() == target.resolve())
        assert _session_wire(actor, 'thread/resume')[-1]['params']['threadId'] == target_id, (
            'A failed missing-project attempt retains the original association instead of overwriting it with the unrelated current project')
    finally:
        if missing.exists() and not target.exists():
            missing.rename(target)


def test_recorded_account_mismatch_refuses_before_any_original_project_open(main_actor, tmp_path):
    actor, target, current, target_id, _current_id = _two_genuine_project_session_records(main_actor, tmp_path)
    first_account = qml(actor, 'Session.assistant.account')
    actor.command('sign_out');_session_configure(actor, account_email='other-actual-fixture-account@example.invalid')
    actor.connect();second_account = qml(actor, 'Session.assistant.account')
    assert first_account != second_account, 'The account discriminator reaches two actual distinct pinned account/read identities rather than adding an invented Thread.account field'
    before = actor.last['ui']['project'];marker = 'e11.session.account-project-observer'
    _watch_original_project_open(actor, marker)
    actor.command('click', name='assistant.sessions');rows = _session_wait(actor)
    assert target_id in {row['id'] for row in rows}, 'The local pinned backend exposes the original recorded app-owned metadata independently of the current account association'
    boundary = len(_session_wire(actor, 'thread/resume'))
    click = actor.command('session_row_click', thread_id=target_id)['reply']
    assert click['reached'] and click['actual_pressed_changes'] > 0, 'The mismatched-account request reaches the genuine original row input boundary'
    actor.until(lambda _value: not qml(actor, 'Session.assistant.sessionsLoading'))
    assert qml(actor, 'Session.assistant.sessionsError') and len(_session_wire(actor, 'thread/resume')) == boundary, (
        'Recorded original account mismatch is settled honestly before any exact-thread resume can be admitted')
    assert actor.command('inspect')['ui']['project'] == before and qml(actor, '(' + control_expression(marker) + ').changes') == 0, (
        'Account association must be validated before opening the other project, even when that original project still exists')
    assert qml(actor, 'Session.assistant.connected') and qml(actor, 'Session.assistant.account') == second_account, (
        'Refusing an old-account association preserves the actual current account and connection')


@pytest.mark.parametrize('boundary', ['cancel_selection', 'new_session', 'sign_out', 'successor_project'])
def test_deferred_original_project_open_renews_restore_intent_and_current_project_before_effect(main_actor, tmp_path, boundary):
    actor, target, current, target_id, _current_id = _two_genuine_project_session_records(main_actor, tmp_path)
    qml(actor, 'Session.project.description="An actual unsaved ordinary metadata edit before deferred restore."')
    assert qml(actor, 'Session.project.modified'), 'The actual original public metadata setter reaches the normal unsaved-change owner before selection'
    actor.command('click', name='assistant.sessions');_session_wait(actor)
    click = actor.command('session_row_click', thread_id=target_id)['reply']
    assert click['reached'] and click['actual_pressed_changes'] > 0, 'The deferred restore begins with actual input on the original runtime session row'
    actor.until(lambda _value: bool(qml(actor, control_expression('unsavedChanges') + '.opened')))
    intent = qml(actor, 'Session.assistant.sessionSelection')
    assert intent and Path(actor.last['ui']['project']['path']).resolve() == current.resolve(), (
        'The real FIRST afterChanges dialog actually holds the original restore intent before any target project opens')
    marker = 'e11.session.deferred-original-project';_watch_original_project_open(actor, marker)
    if boundary == 'cancel_selection':
        qml(actor, 'Session.assistant.cancelSessionSelection()')
    elif boundary == 'new_session':
        actor.command('clear_history')
    elif boundary == 'sign_out':
        actor.command('sign_out')
    else:
        successor = tmp_path / 'actual-independent-successor';shutil.copytree(current, successor)
        assert actor.command('open', path=str(successor))['reply']['opened'], (
            'The stale-project discriminator genuinely adopts another complete project through the original normal Open API')
    if boundary != 'successor_project':
        assert qml(actor, 'Session.assistant.sessionSelection') != intent, (
            'The selected lifecycle boundary actually retires the original pending restore before claiming a stale-continuation exercise')
    qml(actor, '(function(){const o=' + control_expression(marker) + ';o.current=Session.project;return true;})()')
    changes_before = qml(actor, '(' + control_expression(marker) + ').changes')
    expected_path = actor.command('inspect')['ui']['project']['path']
    # The original actual standard button and QTest click deliver the old
    # captured afterChanges continuation; no synthetic discarded signal.
    delivery = actor.command('dialog_ok', name='unsavedChanges', role='discard')['reply']
    assert delivery['pressed_changes'] > 0 and delivery['actual_dialog_name'] == 'unsavedChanges', (
        'The original deferred action is released by genuine input on its existing ordinary Discard button')
    snapshot = actor.command('inspect')['ui']['project']
    assert snapshot['path'] == expected_path and qml(actor, '(function(){const o=' + control_expression(marker) + ';return o.current===Session.project&&o.changes===' + str(changes_before) + ';})()'), (
        'A queued old restore must renew both its original intent and current project immediately before opening; it cannot replace the surviving successor')
    (actor.folder / 'deferred-original-open-boundary.json').write_text(json.dumps({
        'boundary': boundary, 'original_intent': intent, 'original_target_thread': target_id,
        'expected_surviving_path': expected_path, 'actual_standard_button': delivery,
        'original_row_click': click, 'post_dialog_project': snapshot}, indent=2))


@pytest.mark.parametrize('outcome', ['ordinary_cancel', 'actual_open_refused'])
def test_abandoned_original_deferred_open_settles_intent_and_unblocks_real_attachment_rows(main_actor, tmp_path, outcome):
    actor, target, current, target_id, current_id = _two_genuine_project_session_records(main_actor, tmp_path)
    qml(actor, 'Session.project.description="Ordinary unsaved edit before an abandoned restore."')
    assert qml(actor, 'Session.project.modified'), 'The abandoned-open witness actually reaches the FIRST unsaved-project choice owner'
    actor.command('click', name='assistant.sessions');_session_wait(actor)
    click = actor.command('session_row_click', thread_id=target_id)['reply']
    assert click['reached'] and click['actual_pressed_changes'] > 0, 'The original pending restore comes from actual current session-row input'
    actor.until(lambda _value: qml(actor, control_expression('unsavedChanges') + '.opened'))
    intent = qml(actor, 'Session.assistant.sessionSelection')
    assert intent, 'There is a genuine admitted original restore intent before ordinary cancellation or Open refusal'
    moved = tmp_path / 'preserved-target-unavailable-at-real-open'
    try:
        if outcome == 'actual_open_refused':
            target.rename(moved)
            role = 'discard'
        else:
            role = 'cancel'
        delivered = actor.command('dialog_ok', name='unsavedChanges', role=role)['reply']
        assert delivered['pressed_changes'] > 0, 'The original unsaved-change outcome is delivered through genuine Qt input on its existing standard button'
        actor.until(lambda _value: not qml(actor, 'Session.assistant.sessionSelection') and not qml(actor, 'Session.assistant.sessionsLoading'))
        assert Path(actor.command('inspect')['ui']['project']['path']).resolve() == current.resolve(), (
            'An abandoned/refused deferred target leaves the actual surviving original project in place')
        target_resumes_before = sum(row['params']['threadId'] == target_id for row in _session_wire(actor, 'thread/resume'))
        if qml(actor, control_expression('assistant.sessionsDialog') + '.opened'):
            actor.command('manual_key', key='escape')
        source = _attachment_fixtures(tmp_path, 1)[0]
        token = actor.begin_current_file_selection()
        assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], (
            'After actual abandonment, the genuine original file chooser owner can still admit a new current draft file')
        assert any(row['name'] == source.name and row['pending'] for row in _attachment_rows(actor)), (
            'No stale selection target may suppress normal selected-file model publication after the abandoned Open')
        assert sum(row['params']['threadId'] == target_id for row in _session_wire(actor, 'thread/resume')) == target_resumes_before, (
            'Later ordinary Connect/input admission cannot revive the abandoned target against the surviving current project')
        (actor.folder / 'actual-deferred-abandonment.json').write_text(json.dumps({
            'outcome': outcome, 'original_intent': intent, 'target_thread': target_id,
            'surviving_thread': current_id, 'actual_standard_button': delivered,
            'actual_current_project': actor.last['ui']['project'], 'new_input_rows': _attachment_rows(actor)}, indent=2))
    finally:
        if moved.exists() and not target.exists():
            moved.rename(target)

# Exact genuine app/provider persistence is copied into normal fresh paths before
# Session construction. Scientific inputs and their physical identities stay put.
def _capture_exact_cache_manifest(actor, label):
    app_root = Path(actor.last['test_settings']['app_local_data'])
    folder = actor.folder / ('genuine-cache-' + label);folder.mkdir()
    entries = []
    for original in _archive_candidates(actor):
        if not original.is_file():
            continue
        relative = original.relative_to(app_root)
        copy = folder / 'cache-files' / relative;copy.parent.mkdir(parents=True, exist_ok=True)
        raw = original.read_bytes();copy.write_bytes(raw)
        assert copy.read_bytes() == raw, 'First-run cache capture preserves every original byte without changing rows, IDs, paths or timestamps inside the document'
        entries.append({'relative': str(relative), 'source': str(copy), 'original_source': str(original),
                        'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    assert entries, 'Restart capture includes actual first-run cache files rather than a fabricated empty history manifest'
    manifest = folder / 'cache-manifest.json';manifest.write_text(json.dumps({'files': entries}, indent=2))
    return manifest


def _finish_genuine_restart_sources(actor, manifest):
    # Destroy the actual ordinary engine/Session first, so last-session settings
    # come from its original teardown owner, not a manually authored setting.
    first_account = qml(actor, 'Session.assistant.account')
    before = actor.command('inspect')
    identity = before['test_settings'];provider_source = actor.trace.with_suffix('.provider-state.json')
    actor.command('destroy')
    assert not actor.last['ui']['alive'], 'Restart source settings are captured after actual ordinary Session/engine teardown'
    settings_source = Path(identity['path']);folder = manifest.parent
    saved_settings = folder / 'settings' / settings_source.name;saved_settings.parent.mkdir()
    saved_settings.write_bytes(settings_source.read_bytes())
    saved_backend = folder / 'genuine-provider-state.json';saved_backend.write_bytes(provider_source.read_bytes())
    assert saved_settings.read_bytes() == settings_source.read_bytes() and saved_backend.read_bytes() == provider_source.read_bytes(), (
        'Restart uses byte-exact genuine QSettings and backend persistence, never rewritten thread/account/project/input records')
    record = {'actual_account': first_account, 'application_name': identity['application_name'], 'organization_name': identity['organization_name'],
        'original_settings': str(settings_source), 'settings_source': str(saved_settings),
        'settings_sha256': hashlib.sha256(saved_settings.read_bytes()).hexdigest(),
        'backend_source': str(saved_backend), 'backend_sha256': hashlib.sha256(saved_backend.read_bytes()).hexdigest(),
        'cache_manifest': str(manifest), 'cache_manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'actual_inputs': json.loads(saved_backend.read_bytes())['inputs']}
    (folder / 'original-restart-sources.json').write_text(json.dumps(record, indent=2))
    actor.close()
    (folder / 'first-host-closure.json').write_text(json.dumps({'pid': actor.process.pid, 'exit': actor.process.returncode,
        'ordinary_engine_destroyed': True}, indent=2))
    return record


def _start_exact_original_fixture_restart(tmp_path, monkeypatch, sources, turn_calls, *, session_fixture=None):
    monkeypatch.setenv('EDI_TEST_ASSISTANT_APPLICATION_NAME', sources['application_name'])
    monkeypatch.setenv('EDI_TEST_ASSISTANT_RESTORE_SETTINGS', sources['settings_source'])
    monkeypatch.setenv('EDI_TEST_ASSISTANT_RESTORE_CACHE_MANIFEST', sources['cache_manifest'])
    monkeypatch.setenv('EDI_TEST_CODEX_PROVIDER_STATE_SOURCE', sources['backend_source'])
    monkeypatch.delenv('EDI_TEST_ASSISTANT_RESTORE_HISTORY', raising=False)
    binary = Path(os.environ['EDI_ASSISTANT_UI_PROBE']) if os.environ.get('EDI_ASSISTANT_UI_PROBE') else ROOT / 'build/app/assistant_real_owner_probe'
    folder = tmp_path / 'original-fixture-restart';folder.mkdir()
    previous_count = len(sources['actual_inputs'])
    config = {'turns': [[] for _ in range(previous_count)] + [turn_calls],
        'session_fixture': {'threads': [], 'page_size': 12, 'items_page_size': 2, **(session_fixture or {})},
        'observe_context_continuity': True}
    # Same existing class, host, stdio protocol, normal controls and isolation;
    # explicit initial config exists before any genuine auto-bootstrap can run.
    actor = MainActor.__new__(MainActor)
    try:
        MainActor.__init__(actor, binary, folder, config, False)
    except BaseException:
        if hasattr(actor, 'process'):
            actor.close()
        raise
    assert actor.last['test_settings']['application_name'] == sources['application_name'], (
        'A normal restart retains the genuine first application identity while its OS data/config root remains isolated')
    assert actor.last['settings_restore']['exact_copy'] and actor.last['cache_restore']['keys_or_rows_rewritten'] is False, (
        'The second real Session constructor consumes unchanged first settings/cache bytes rather than fixture-authored associations')
    return actor


def _ordinary_restart_connect(actor):
    actor.until(lambda value: value['ui']['connected'] or any(row['name'] == 'assistant.connection'
        and row['enabled'] and row['fully_exposed'] for row in value['ui']['controls']))
    auto = _session_wire(actor)
    actor.connect()
    return auto


def _close_explicit_restart_actor(actor):
    actor.close()
    stderr = (actor.folder / 'host.stderr').read_text(errors='replace')
    assert not re.search(r'ReferenceError|TypeError|Unable to assign \[undefined\]|Cannot assign to non-existent property|Detected function .*Connections', stderr), (
        'The explicitly owned restarted Main keeps the same original QML coding-warning oracle as the existing actor fixture')


def test_ordinary_restart_reopens_actual_last_thread_project_all_history_and_original_input_bytes(main_actor, tmp_path, monkeypatch):
    actor = main_actor([[]]);_session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], 'Restart positive begins with an actual saved ordinary project outside temporary app storage'
    actor.connect();source = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], 'Original restart inputs are genuinely admitted from their unchanged physical source files'
    file_id = actor.last['ui']['selected_files'][0]['id']
    actor.configure_turns([[tool_call('read_selected_file', 'original-pre-restart-native-read', file_id=file_id, offset=0, max_bytes=source.stat().st_size)]])
    original_task = 'Keep this actual original project and attached CIF for a later continuation.'
    _session_request_with_original_disclosure(actor, original_task);_session_completed(actor, 1);native_result(actor.responses()[0])
    first = _session_state(actor)['inputs'][0];thread = first['threadId']
    original_manifest = actor.command('inspect')['ui']['selected_files']
    first_rows = [_rows_values(actor, 'messages', index) for index in range(_rows_probe(actor)['count'])]
    assert {'user', 'assistant', 'activity'} <= {row['kind'] for row in first_rows}, 'The actual first run reaches user, assistant and native activity before restart capture'
    _capture_genuine_archive(actor, 'restart-full-current')
    manifest = _capture_exact_cache_manifest(actor, 'full-current')
    sources = _finish_genuine_restart_sources(actor, manifest)
    restored = _start_exact_original_fixture_restart(tmp_path, monkeypatch, sources,
        [tool_call('read_selected_file', 'actual-post-restart-native-read', file_id=file_id, offset=0, max_bytes=source.stat().st_size)])
    try:
        auto = _ordinary_restart_connect(restored)
        restored.until(lambda value: value['ui']['connected'] and Path(value['ui']['project'].get('path', '')).resolve() == project.resolve())
        wire = _session_wire(restored)
        assert not any(row.get('method') == 'thread/start' for row in wire), 'Actual last-session restoration must not disguise a fresh provider thread as the resumed conversation'
        resumes = _session_wire(restored, 'thread/resume')
        assert qml(restored, 'Session.assistant.account') == sources['actual_account'], 'A genuine cold restart establishes the same actual account by its correlated read rather than treating helper readiness as an identity change'
        assert resumes and resumes[-1]['params']['threadId'] == thread, 'Normal login/restart cold-resumes the actual original last-connected runtime ID'
        assert not _session_wire(restored, 'turn/start'), 'Restoration does not replay or inject the original user request or native read as new model work'
        current = restored.command('inspect')['ui']
        assert current['selected_files'] == original_manifest, 'Restart restores original opaque input identities and consumed markers rather than substituting copied files or labels'
        displayed = [_rows_values(restored, 'messages', index) for index in range(_rows_probe(restored)['count'])]
        by_id = {row['id']: row for row in displayed}
        assert all(by_id.get(row['id']) == row for row in first_rows), 'Genuine full app cache restores all original user, assistant and native activity rows exactly after runtime confirmation'
        restored.request('Continue the same original task by reading the original attached file.')
        _session_completed(restored, 2)
        followup = _session_state(restored)['inputs'][-1]
        assert followup['threadId'] == thread and followup['actual_prior_input_count'] == 1, 'The actual next request is a continuation of the original persisted conversation rather than a new first message'
        readback = native_result(restored.responses()[-1])
        assert any(value == source.read_text() for row in objects(readback) for value in row.values() if isinstance(value, str)), 'The genuine resumed Controller can still read approved original bytes at unchanged physical identity'
        (restored.folder / 'ordinary-last-session-restart.json').write_text(json.dumps({
            'original_sources': sources, 'auto_events_before_manual_connect': auto,
            'actual_resumes': resumes, 'original_rows': first_rows, 'restored_rows': displayed,
            'actual_followup': followup}, indent=2))
    finally:
        _close_explicit_restart_actor(restored)


def test_partial_genuine_cache_does_not_suppress_later_actual_runtime_users_replies_and_activities(main_actor, tmp_path, monkeypatch):
    actor = main_actor([[_rows_research('first-real-history-source')], [_rows_research('second-real-history-source')], []])
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12, 'items_page_size': 2}, observe_context_continuity=True,
        final_text='The first genuinely emitted reply is present in the early app cache.')
    actor.connect();actor.request('First real user message belongs to the early cached turn.');_session_completed(actor, 1)
    _capture_genuine_archive(actor, 'actual-early-prefix')
    early_rows = [_rows_values(actor, 'messages', index) for index in range(_rows_probe(actor)['count'])]
    early_manifest = _capture_exact_cache_manifest(actor, 'real-early-prefix')
    _session_configure(actor, final_text='Second actually emitted assistant reply missing from that early cache.')
    second_user = 'A different second real user message must remain recoverable by its own original turn.'
    actor.request(second_user);_session_completed(actor, 2)
    _session_configure(actor, final_text='Third actually emitted assistant reply is also absent from the early cache.')
    third_user = 'A third actual user message has another distinct original runtime item.'
    actor.request(third_user);_session_completed(actor, 3)
    early_files = json.loads(early_manifest.read_bytes())['files']
    assert all(second_user.encode() not in Path(entry['source']).read_bytes() and third_user.encode() not in Path(entry['source']).read_bytes() for entry in early_files), (
        'The actual early cache snapshot truly predates the later missing user turns instead of accidentally preloading their complete history')
    genuine_state = _session_state(actor);thread = genuine_state['inputs'][0]['threadId']
    assert all(row['threadId'] == thread for row in genuine_state['inputs']), 'The partial-cache oracle uses later real turns on the same original conversation, not a hand-seeded second history'
    original_items = genuine_state['item_history'][thread]
    expected_later = [entry for entry in original_items if entry['turnId'] != genuine_state['inputs'][0]['turnId']]
    assert any(entry['item']['type'] == 'userMessage' for entry in expected_later) and any(entry['item']['type'] == 'agentMessage' for entry in expected_later), (
        'Missing-history expectations come from actual acknowledged later inputs and actual emitted replies, not invented fallback outcomes')
    sources = _finish_genuine_restart_sources(actor, early_manifest)
    restored = _start_exact_original_fixture_restart(tmp_path, monkeypatch, sources, [])
    try:
        _ordinary_restart_connect(restored)
        restored.until(lambda value: value['ui']['connected'] and bool(_session_wire(restored, 'thread/items/list')))
        restored.until(lambda value: second_user in json.dumps(value['ui']['messages'], ensure_ascii=False)
            and third_user in json.dumps(value['ui']['messages'], ensure_ascii=False)
            and 'Second actually emitted assistant reply' in json.dumps(value['ui']['messages'], ensure_ascii=False)
            and 'Third actually emitted assistant reply' in json.dumps(value['ui']['messages'], ensure_ascii=False))
        reads = _session_wire(restored, 'thread/items/list')
        assert len(reads) > 1 and any(row['params'].get('cursor') for row in reads), 'Full older-history recovery follows actual supported exact-thread item cursors beyond a single page'
        assert all(row['params']['threadId'] == thread for row in reads), 'Runtime history paging remains bound to the original selected conversation ID'
        _source, canonical, _receipt = _capture_genuine_archive(restored, 'restored-real-partial-coverage')
        imported = [row for row in canonical if row.get('historyOrigin') == 'runtime']
        assert imported and all('nativeOutcome' not in row and 'workScope' not in row for row in imported), (
            'Runtime-sourced missing history is explicitly identified and cannot acquire fabricated app/native receipt authority')
        assert not _session_wire(restored, 'turn/start'), 'Reading actual older runtime items cannot manufacture a replacement provider task or replay scientific work'
        early_ids = {row['id'] for row in early_rows}
        after = [_rows_values(restored, 'messages', index) for index in range(_rows_probe(restored)['count'])]
        assert early_ids <= {row['id'] for row in after}, 'Recovering missing later runtime turns preserves all genuine matching early app rows'
        (restored.folder / 'genuine-partial-cache-runtime-coverage.json').write_text(json.dumps({
            'original_sources': sources, 'actual_later_runtime_items': expected_later,
            'supported_item_reads': reads, 'early_app_rows': early_rows,
            'unknown_turn_user_branch': 'only reached if an actual early source row lacks its original turn; no synthetic deletion'}, indent=2))
    finally:
        _close_explicit_restart_actor(restored)


def test_confirmed_same_current_session_click_settles_its_original_browser_waiter(main_actor):
    actor = main_actor([[tool_call('inspect_project', 'actual-rich-current-session')]])
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    actor.connect();actor.request('Retain the rich current conversation before selecting its actual same row.')
    _session_completed(actor, 1);native_result(actor.responses()[0])
    current = _session_state(actor)['inputs'][0]['threadId']
    before_resumes = len(_session_wire(actor, 'thread/resume'))
    actor.command('click', name='assistant.sessions');rows = _session_wait(actor)
    assert current in {row['id'] for row in rows}, 'The original browser genuinely realizes the already confirmed current runtime session'
    click = actor.command('session_row_click', thread_id=current)['reply']
    assert click['reached'] and click['actual_pressed_changes'] > 0, 'Same-current selection reaches actual original row input rather than a forged success signal'
    actor.until(lambda _value: not qml(actor, control_expression('assistant.sessionsDialog') + '.opened')
                and not qml(actor, 'Session.assistant.sessionsLoading'))
    assert len(_session_wire(actor, 'thread/resume')) == before_resumes, 'Confirming the already current original session cannot require a new resume or replace its real transport'
    boundary = len(_session_wire(actor, 'thread/list'))
    actor.command('click', name='assistant.sessions');_session_wait(actor)
    assert len(_session_wire(actor, 'thread/list')) > boundary, 'Successful same-current confirmation releases the original loading owner so the next real browser refresh is admitted'
    assert not qml(actor, 'Session.assistant.sessionsError'), 'A successful confirmed selection cannot leave a fabricated failure or permanently busy selector'


def test_old_runtime_history_error_cannot_settle_newer_pending_browser_refresh(main_actor, tmp_path, monkeypatch):
    actor = main_actor([[], []])
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12, 'items_page_size': 2}, observe_context_continuity=True)
    actor.connect();actor.request('First actual cached user turn before later runtime history exists.');_session_completed(actor, 1)
    _capture_genuine_archive(actor, 'history-error-early-prefix')
    early = _capture_exact_cache_manifest(actor, 'history-error-early-prefix')
    actor.request('Second genuine user turn requires actual missing-history recovery.');_session_completed(actor, 2)
    sources = _finish_genuine_restart_sources(actor, early)
    release_items = tmp_path / 'release-original-history';release_list = tmp_path / 'release-newer-list'
    restored = _start_exact_original_fixture_restart(tmp_path, monkeypatch, sources, [], session_fixture={
        'items_hold': str(release_items), 'items_error_on_release': True, 'list_hold': str(release_list)})
    try:
        _ordinary_restart_connect(restored)
        restored.until(lambda value: value['ui']['connected'] and bool(_session_wire(restored, 'thread/items/list')))
        original_history = _session_wire(restored, 'thread/items/list')[-1]
        restored.command('click', name='assistant.sessions')
        restored.until(lambda _value: qml(restored, 'Session.assistant.sessionsLoading') and bool(_session_wire(restored, 'thread/list')))
        newer_list = _session_wire(restored, 'thread/list')[-1]
        before_error = qml(restored, 'Session.assistant.sessionsError')
        release_items.touch();restored.command('refresh_usage')
        sent = lambda: [json.loads(line) for line in restored.trace.with_suffix('.sent.jsonl').read_text().splitlines()]
        restored.until(lambda _value: any(row.get('id') == original_history['id'] and 'error' in row for row in sent()))
        assert not any(row.get('id') == newer_list['id'] for row in sent()), 'The newer original browser request is still genuinely outstanding when the older history error arrives'
        assert qml(restored, 'Session.assistant.sessionsLoading') and qml(restored, 'Session.assistant.sessionsError') == before_error, (
            'An unrelated older history completion/failure cannot release or overwrite the newer browser operation owner')
        release_list.touch();restored.command('refresh_usage');rows = _session_wait(restored)
        assert rows and not qml(restored, 'Session.assistant.sessionsError'), 'The still-current original newer browser response remains admissible and settles normally after the unrelated error'
        (restored.folder / 'old-history-new-browser-receipts.json').write_text(json.dumps({
            'original_history': original_history, 'newer_browser': newer_list,
            'actual_old_error': next(row for row in sent() if row.get('id') == original_history['id'])}, indent=2))
    finally:
        release_items.touch();release_list.touch();_close_explicit_restart_actor(restored)


@pytest.mark.parametrize('plan', ['plus', None], ids=['known-plan', 'transitional-plan-metadata'])
@pytest.mark.parametrize('target_age', ['oldest', 'newer_retained'])
def test_same_account_mode_notification_before_cold_selection_read_preserves_exact_original_identity(main_actor, plan, target_age):
    actor = main_actor([[], []]);_session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    target, previous = _two_genuine_session_threads(actor)
    if target_age == 'newer_retained':
        target = previous
        actor.append_turn([]);actor.command('click', name='assistant.clear')
        actor.until(lambda value: not value['ui']['messages'])
        actor.request('A third actual conversation makes the recent second thread a genuine noncurrent target.')
        _session_completed(actor, 3);previous = _session_state(actor)['inputs'][-1]['threadId']
    account = qml(actor, 'Session.assistant.account')
    assert actor.last['ui']['connected'] and not actor.last['ui']['context_consent_required'], (
        'The account-selection witness begins with an actually authenticated unchanged approved current scope')
    _session_configure(actor, account_notification_before_read={'authMode': 'chatgpt', 'planType': plan})
    boundary = len(_session_wire(actor));sent_path = actor.trace.with_suffix('.sent.jsonl')
    sent_before = len(sent_path.read_text().splitlines())
    actor.command('click', name='assistant.sessions');_session_wait(actor)
    click = actor.command('session_row_click', thread_id=target)['reply']
    assert click['reached'] and click['actual_pressed_changes'] > 0, 'The actual cold-selection path is initiated through the exposed original row-owned MouseArea'
    actor.until(lambda _value: not qml(actor, 'Session.assistant.sessionsLoading') and any(row['params']['threadId'] == target for row in _session_wire(actor, 'thread/resume')))
    assert qml(actor, 'Session.assistant.connected') and qml(actor, 'Session.assistant.account') == account, (
        'A mode/partial-plan notification cannot prove an account change before the actual correlated identical account/read result')
    assert not qml(actor, 'Session.assistant.sessionsError') and not qml(actor, control_expression('assistant.sessionsDialog') + '.opened'), (
        'Exact original same-account selection confirms and settles without forcing a fresh conversation or erasing its browser owner')
    new_requests = _session_wire(actor)[boundary:]
    mode_events = [row['fixture_mode_before_account_read'] for row in new_requests if 'fixture_mode_before_account_read' in row]
    account_ids = {row['request_id'] for row in mode_events}
    sent = [json.loads(line) for line in sent_path.read_text().splitlines()[sent_before:]]
    updates = [index for index, row in enumerate(sent) if row.get('method') == 'account/updated']
    replies = [index for index, row in enumerate(sent) if row.get('id') in account_ids and 'result' in row]
    assert mode_events and updates and replies and all(any(update < reply for update in updates) for reply in replies), (
        'The pinned mode-only notification really arrives before the new helper/preflight correlated identity response rather than after interactive login')
    assert not any(row.get('method') in ('thread/start', 'turn/start') for row in new_requests), (
        'Recovering the actual original same-account runtime thread does not inject cached context into a replacement first message')
    (actor.folder / 'actual-same-account-selection-mode-order.json').write_text(json.dumps({
        'target': target, 'previous': previous, 'original_account': account, 'mode_notification': {'authMode': 'chatgpt', 'planType': plan},
        'new_requests': new_requests, 'actual_mode_read_owners': mode_events, 'actual_sent': sent, 'physical_row_click': click}, indent=2))


def test_failed_original_input_preparation_preserves_usable_current_thread_and_precise_cause(main_actor, tmp_path):
    # The old changed-input premise is retained in the app18-critical2 preimage:
    # unavailable old attachments may honestly permit a partial restore. This
    # case requires a real fatal preparation failure, not that stronger policy.
    actor = main_actor([[], [], []]);_session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    actor.connect();source = _attachment_fixtures(tmp_path, 1)[0];original_bytes = source.read_bytes()
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], (
        'Target preparation is associated with an actually admitted original file, not a fabricated saved record')
    _session_request_with_original_disclosure(actor, 'Original target conversation retains this exact admitted input identity.');_session_completed(actor, 1)
    target = _session_state(actor)['inputs'][0]['threadId']
    actor.command('click', name='assistant.clear');actor.until(lambda value: not value['ui']['messages'])
    actor.request('The current separate conversation remains usable if the target cannot prepare.');_session_completed(actor, 2)
    current = _session_state(actor)['inputs'][1]['threadId'];account = qml(actor, 'Session.assistant.account')
    original_stat = source.stat()
    starts = _session_wire(actor, 'thread/start')
    current_workspace = Path(starts[-1]['params']['cwd']).resolve()
    storage = Path(actor.last['test_storage']).resolve()
    parent = current_workspace.parent.parent
    assert current_workspace.is_relative_to(storage) and parent.is_relative_to(storage) \
        and parent.name == 'agent' and parent.parent.name == 'assistant', (
            'The storage fault targets only the exact genuine fixture-owned preparation parent recorded by the real thread bootstrap')
    original_mode = parent.stat().st_mode & 0o777
    assert os.geteuid() != 0 and parent.stat().st_uid == os.geteuid() \
        and os.access(current_workspace, os.R_OK | os.W_OK | os.X_OK), (
            'The actual fixture user owns the narrowly scoped parent and the existing current workspace remains usable before the fault')
    actor.command('click', name='assistant.sessions');_session_wait(actor)
    parent.chmod(original_mode & ~0o222)
    try:
        assert not os.access(parent, os.W_OK) and os.access(current_workspace, os.R_OK | os.W_OK | os.X_OK), (
            'Only new preparation-directory creation is denied; existing current workspace access is preserved')
        before = len(_session_wire(actor, 'thread/resume'))
        click = actor.command('session_row_click', thread_id=target)['reply']
        assert click['reached'] and click['actual_pressed_changes'] > 0, (
            'Fatal target preparation is reached through actual original session-selection input')
        actor.until(lambda _value: not qml(actor, 'Session.assistant.sessionsLoading'))
        cause = qml(actor, 'Session.assistant.sessionsError')
        assert cause and re.search(r'\b(workspace|storage|prepar\w*|permission|directory|writ\w*)\b', cause, re.I), (
            'The actual fatal target workspace/storage preparation cause survives instead of a generic abandoned-selector fallback')
        assert qml(actor, 'Session.assistant.connected') and qml(actor, 'Session.assistant.account') == account, (
            'Fatal target preparation finishes before retiring the still-usable actual current connection')
        assert len(_session_wire(actor, 'thread/resume')) == before, (
            'An unprepared target cannot be falsely adopted or resumed')
        assert source.read_bytes() == original_bytes and source.stat().st_ino == original_stat.st_ino, (
            'Original admitted bytes and physical input identity stay unchanged throughout the storage-only fault')
        (actor.folder / 'fatal-target-preparation-boundary.json').write_text(json.dumps({
            'target': target, 'surviving_current': current, 'actual_error': cause,
            'actual_current_workspace': str(current_workspace), 'preparation_parent': str(parent),
            'parent_mode_before': original_mode, 'parent_mode_during': parent.stat().st_mode & 0o777,
            'existing_workspace_accessible': os.access(current_workspace, os.R_OK | os.W_OK | os.X_OK),
            'original_file_sha256': hashlib.sha256(original_bytes).hexdigest(),
            'actual_physical_click': click}, indent=2))
    finally:
        parent.chmod(original_mode)
    actor.command('manual_key', key='escape')
    actor.request('Continue the still-current original conversation after the refused target.')
    _session_completed(actor, 3)
    followup = _session_state(actor)['inputs'][-1]
    assert followup['threadId'] == current and followup['actual_prior_input_count'] == 1, (
        'After target refusal, genuine next work remains on the previous viable thread without executing an abandoned target intent')
    (actor.folder / 'failed-target-usable-original.json').write_text(json.dumps({
        'target': target, 'surviving_current': current, 'actual_followup': followup,
        'fault_boundary': 'fatal-target-preparation-boundary.json',
        'original_file_sha256': hashlib.sha256(original_bytes).hexdigest()}, indent=2))

# Actual FIRST message/document/resource/input owners, not a TeX test parser.
def _genuine_math_message(main_actor, source):
    actor = main_actor([[]])
    if callable(source):
        source = source(actor)
    _session_configure(actor, final_text=source)
    actor.connect();actor.request('Present the actual retained mathematical reply through the normal current chat document.')
    _session_completed(actor, 1)
    rows = [_rows_values(actor, 'messages', index) for index in range(_rows_probe(actor)['count'])]
    row = next(row for row in rows if row['kind'] == 'assistant' and row['text'] == source)
    observed = {}
    def reached(_value):
        observed.clear();observed.update(actor.command('markdown_probe', row_id=row['id'])['reply'])
        return observed['reached']
    actor.until(reached)
    assert observed['same_window'] and observed['source'] == source, 'Math observation reaches the realized original assistant row/document with the complete actual retained source'
    return actor, row, observed


def test_native_math_real_document_images_keep_source_and_every_original_copy_entrance(main_actor):
    inline = r'$\alpha+\frac{x^2}{1+x}$'
    source = 'Inline ' + inline + ' follows ordinary body text.\n\n' + r'\[\boxed{\frac{a}{b}}\]'
    actor, row, document = _genuine_math_message(main_actor, source)
    assert len(document['images']) == 2 and all(not image['resource_null'] and image['nontransparent']
        and image['resource_width'] > 0 and image['resource_height'] > 0 for image in document['images']), (
        'Both eligible real inline/display expressions produce actual nonempty native resources rather than unchanged backslash text or empty placeholders')
    assert document['whole_source_copy'] == source, 'Whole-document source copying preserves every original delimiter and TeX byte independently of the generated image representation'
    assert document['center_exposed'], 'The finite visual/copy witness reaches an actually exposed original message in the current Main viewport'
    frame = actor.folder / 'actual-native-math-inline-display.png'
    assert actor.command('capture_frame', path=str(frame))['reply']['saved'], 'The baseline frame is retained before selection highlighting can obscure the original native expression'
    copies = []
    for mode in ('public', 'keyboard', 'selection'):
        actual = actor.command('markdown_copy', row_id=row['id'], image_index=0, mode=mode)['reply']
        assert actual['reached'] and actual['same_row'] and actual['same_window'], (
            'Each copy entrance is exercised on the genuinely mouse-selected formula in its original current row/window')
        assert actual['clipboard'] == inline and '\ufffc' not in actual['clipboard'], (
            'Public TextEdit.copy, Ctrl+C and Linux primary selection preserve the original formula source rather than an image-object replacement character')
        copies.append(actual)
    (actor.folder / 'native-math-original-copy-entrances.json').write_text(json.dumps({
        'source': source, 'actual_document': document, 'actual_copy_entrances': copies,
        'frame': str(frame), 'baseline_semantic_acceptance': 'requires actual rendered-frame assessment; no baselineOffset-only success claim'}, indent=2))


def test_native_math_parser_errors_keep_exact_complete_readable_source(main_actor):
    first = r'$x+\frac{1}$';second = r'\[a+\ThisIsNotARealInstruction{z}\]'
    source = first + '\n\n' + second
    actor, _row, document = _genuine_math_message(main_actor, source)
    assert not document['images'], 'A nonnull recovered parser tree cannot install a plausible image that omits a failed fraction or unknown instruction'
    assert first in document['plain_text'] and second in document['plain_text'], 'Malformed/unsupported complete expressions remain exact readable literal source instead of silently losing their failed terms'
    assert document['whole_source_copy'] == source, 'Error fallback preserves the complete retained mathematical source and ordinary copying'
    assert actor.last['ui']['connected'] and actor.last['ui']['state'] == 'idle', 'A local presentation fallback cannot refuse scientific work, retire authentication or leave the actual conversation busy'


def test_math_capture_preserves_real_link_destinations_container_code_and_unmatched_backtick_context(main_actor):
    first = 'https://independent-fixture.invalid/path/$x$?q=$y$'
    second = 'https://independent-fixture.invalid/reference/$z$'
    source = ('[MATH-LINK-PRESERVE](' + first + ')\n\n[REFERENCE-LINK][ref]\n\n'
        '[ref]: ' + second + ' "Original $literalTitle$"\n\n'
        '>     $quotedCode$\n\n- List item\n\n      $nestedListCode$\n\n'
        '`an unmatched inline delimiter\n\nLater actual math $p+q$.')
    actor, _row, document = _genuine_math_message(main_actor, source)
    assert len(document['images']) == 1, 'Only the actual later eligible math renders; link metadata and container-relative code remain owned by ordinary Markdown literals'
    assert '$quotedCode$' in document['plain_text'] and '$nestedListCode$' in document['plain_text'], 'Nested quote/list code keeps its literal dollars instead of receiving native equation images'
    links = {anchor['href'] for anchor in document['anchors'] if anchor['href']}
    assert {first, second} <= links, 'Actual Qt-parsed ordinary and reference destinations preserve their original dollars rather than protected-token substitutions'
    assert any(anchor['tooltip'] == 'Original $literalTitle$' for anchor in document['anchors']), 'Hidden reference titles remain literal Markdown metadata rather than being captured as visible math'
    assert actor.command('click_link', marker='MATH-LINK-PRESERVE')['reply']['found'], 'The normal current TextEdit link receives actual original-window input'
    assert first in actor.last['activated_urls'], 'Clicking the original history link reaches the FIRST system-browser dispatcher with its unchanged actual destination'
    assert document['whole_source_copy'] == source and actor.last['image_requests'] == 0, 'Lexical protection preserves raw copying and cannot create an authored network-image resource door'


@pytest.mark.parametrize('form', ['nested_groups', 'nested_environments', 'unbraced_command_chain'])
def test_recursive_math_input_stays_complete_and_live_without_scientific_quota(main_actor, form):
    depth = 4096
    if form == 'nested_groups':
        expression = '{' * depth + 'x' + '}' * depth
    elif form == 'nested_environments':
        expression = r'\begin{matrix}' * depth + 'x' + r'\end{matrix}' * depth
    else:
        expression = r'\sqrt' * depth + 'x'
    source = '$' + expression + '$'
    actor, _row, document = _genuine_math_message(main_actor, source)
    assert document['source'] == source and document['whole_source_copy'] == source, (
        'Finite deep grammar inputs retain their full original text/copy even when native presentation eligibility requires literal fallback')
    assert actor.last['ui']['connected'] and actor.last['ui']['state'] == 'idle', (
        'Recursive presentation input cannot crash/block the real Main or turn a local render fallback into an account/work quota failure')
    assert not actor.responses(), 'Rendering a retained equation cannot invent a native scientific call or alter the project'
    (actor.folder / 'recursive-presentation-boundary.json').write_text(json.dumps({
        'form': form, 'constructed_depth': depth, 'depth_provenance': 'finite adversarial grammar fixture, not a measured crash threshold or mandated product limit',
        'source_sha256': hashlib.sha256(source.encode()).hexdigest(), 'source_bytes': len(source.encode()),
        'actual_images': document['images'], 'general_recursion_proof': 'static owner proof remains separate from this finite reached input'}, indent=2))



def test_math_reference_identity_and_incomplete_backslash_body_keep_original_markdown_roles(main_actor):
    urls = ['https://independent-fixture.invalid/full', 'https://independent-fixture.invalid/collapsed', 'https://independent-fixture.invalid/shortcut']
    incomplete = r'\[\text{a\_b}'
    def source(actor):
        return ('[full reference][eq $x$]\n\n[collapsed $y$][]\n\n[shortcut $z$]\n\n'
            '[eq $x$]: ' + urls[0] + '\n[collapsed $y$]: ' + urls[1] + '\n[shortcut $z$]: ' + urls[2] + '\n\n'
            '![image label][image $w$]\n\n[image $w$]: ' + actor.last['image_url'] + '\n\n'
            + incomplete + '\n\nA later unrelated paragraph retains actual math $p+q$.')
    actor, row, document = _genuine_math_message(main_actor, source)
    assert set(urls) <= {anchor['href'] for anchor in document['anchors']}, (
        'Full, collapsed and shortcut references resolve their matching original labels before any per-occurrence math presentation tokenization')
    assert 'image label' in document['plain_text'] and '![image label]' not in document['plain_text'] and actor.last['image_requests'] == 0, (
        'A matching reference image keeps normal parsed/denied-image semantics rather than becoming an unresolved metadata-token literal or a resource fetch')
    assert incomplete in document['plain_text'], 'An incomplete backslash formula preserves its entire literal body including escaped underscores rather than protecting only its opener'
    copied = actor.command('markdown_probe', row_id=row['id'], literal=incomplete)['reply']['literal_copy']
    assert copied['found'] and copied['selected_source'] == incomplete, (
        'Actual partial document selection retains the unchanged incomplete mathematical source, independently of whole-message copying')
    assert document['images'], 'An unfinished earlier formula cannot consume a separate later paragraph that contains complete eligible math'


@pytest.mark.parametrize('container', ['list', 'heading'])
@pytest.mark.parametrize('position', ['beginning', 'middle', 'end'])
def test_display_math_keeps_original_list_and_heading_semantic_membership(main_actor, container, position):
    formula = r'\[x+1\]'
    body = {'beginning': formula + ' after', 'middle': 'Before ' + formula + ' after', 'end': 'Before ' + formula}[position]
    source = ('1. ' if container == 'list' else '# ') + body
    actor, _row, document = _genuine_math_message(main_actor, source)
    assert len(document['images']) == 1, 'The original finite display expression genuinely reaches native image placement inside its ordinary Markdown container'
    role_blocks = [block for block in document['blocks'] if block['list_item']] if container == 'list' else [block for block in document['blocks'] if block['heading'] > 0]
    assert len(role_blocks) == 1, 'Presentation-only equation splitting cannot invent additional actual list items or heading blocks from one original semantic container'
    assert document['whole_source_copy'] == source, 'Display placement preserves the complete original list/heading source for copying and backend history'
    frame = actor.folder / ('actual-display-' + container + '-' + position + '.png')
    assert actor.command('capture_frame', path=str(frame))['reply']['saved'], 'The original semantic display placement has an actual current-window frame for visual qualification'


# Independently authored original-owner gate packet: explicit_new_project_saved_ready.py
# Qualified materialization: only saved-current New; old full private parameterization retained unchanged.
# PRIVATE/UNRUN: Hd8055f37d explicit NEW authority, original GetStarted Create /
# AppState.afterChanges, independent byte conservation and ordinary Session Save
# owners. This is a focused native transition gate, not provider intent or full
# powder/scientific qualification. No destination is planted for native Create.

def _new_project_scientific_bytes(root):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob('*') if path.is_file()
            and 'reports' not in path.relative_to(root).parts}


def _new_project_file_hashes(values):
    return {name: hashlib.sha256(raw).hexdigest() for name, raw in values.items()}


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
@pytest.mark.parametrize('old_choice', ['saved'])
def test_explicit_new_project_never_reuses_current_and_preserves_original_choices_inputs_and_task(
    main_actor, tmp_path, show_actions, old_choice
):
    description = 'An explicit unsaved description belonging only to the original project.'
    # A separate original ordinary Save provides the byte-level transition
    # baseline when the user elects Save. No output from native Create supplies
    # scientific expected values, and no new numerical correctness is claimed.
    expected_saved = None
    if old_choice == 'modified_save':
        reference = main_actor([[]]);reference_root = copied_estimate_project(tmp_path / 'ordinary-save-reference')
        assert reference.command('open', path=str(reference_root))['reply']['opened'], (
            'The Save reference opens an independent complete source through the original ordinary owner')
        reference.until(lambda value: not value['ui']['project']['calculating'])
        qml(reference, 'Session.project.description=' + json.dumps(description))
        assert reference.command('save')['reply']['saved'], (
            'The independent original Save owner persists the explicit old-project edit without native New')
        reference.until(lambda value: not value['ui']['project']['calculating'])
        expected_saved = _new_project_scientific_bytes(reference_root)
        reference.close()
    actor = main_actor([[]], show_actions=show_actions)
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    old_root = copied_estimate_project(tmp_path / 'original-current')
    assert actor.command('open', path=str(old_root))['reply']['opened'], (
        'Explicit New begins with a genuinely already-open complete project instead of a seeded empty Session')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    original_bytes = _new_project_scientific_bytes(old_root)
    shutil.copytree(old_root, actor.folder / 'original-project-byte-preimage')
    current_old_root = old_root
    if old_choice != 'saved':
        qml(actor, 'Session.project.description=' + json.dumps(description))
        assert qml(actor, 'Session.project.modified'), (
            'Modified-state branches reach a genuine ordinary metadata edit before the new-project request')
    if old_choice == 'ordinary_save_as_before_new':
        # Explicit driver fixture preparation through the public original owner,
        # never fabricated native chooser acceptance. This is NOT a claim that
        # queued Create->SaveAs chooser continuation has been exercised.
        current_old_root = tmp_path / 'ordinary-user-selected-save-as-copy'
        assert not current_old_root.exists(), 'The actual original SaveAs owner creates its absent fixture destination'
        assert actor.command('save_as', path=str(current_old_root))['reply']['saved'], (
            'The explicitly elected ordinary SaveAs uses the existing Session API and actual write result')
        assert _new_project_scientific_bytes(old_root) == original_bytes, (
            'Ordinary SaveAs preserves the prior source project bytes instead of overwriting the old location')
    before_new = _new_project_scientific_bytes(current_old_root)
    original_project = actor.last['ui']['project']
    source = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    original_input = source.stat();input_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], (
        'Explicit New retains a genuinely admitted unchanged source input rather than substituting copied or inferred attachments')
    selected = actor.last['ui']['selected_files']
    original_files = [{key: row[key] for key in ('id', 'name', 'bytes')} for row in selected]
    name = 'new_' + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    title = 'Explicitly requested distinct new project'
    new_description = 'Independent original-current-project preservation gate.'
    documents = Path(actor.last['ui']['environment']['documents_root']);destination = documents / name
    assert not destination.exists() and destination != current_old_root, (
        'The native new-project action owns an absent ordinary Documents destination distinct from the original project')
    actor.configure_turns([[
        tool_call('create_project', 'explicit-new-from-existing', name=name, title=title, description=new_description),
        tool_call('read_selected_file', 'same-original-file-after-new-choice', file_id=original_files[0]['id'],
                  offset=0, max_bytes=source.stat().st_size)]])
    actor.connect();marker='e11.new.original-project-change';_watch_original_project_open(actor, marker)
    actor.command('clear_ui_sequence')
    task = 'Create and save a new project using the attached files. One phase, NPD, wavelength 1.49 Å. Refine the structure and show the report.'
    _session_request_with_original_disclosure(actor, task)
    if old_choice in ('modified_save', 'modified_cancel'):
        actor.until(lambda value: any(c['name'] == 'unsavedChanges' and c['fully_exposed'] and c['enabled']
            for c in value['ui']['controls']))
        assert Path(actor.last['ui']['project']['path']).resolve() == current_old_root.resolve() \
            and qml(actor, '(' + _scene_control_expression(marker) + ').changes') == 0, (
                'The original unsaved-work decision is reached before New can retire or replace the still-current original project')
        assert _new_project_scientific_bytes(old_root) == original_bytes and not destination.exists(), (
            'Pending user choice neither silently saves/discards old work nor precreates the requested new destination')
        role = 'save' if old_choice == 'modified_save' else 'cancel'
        button = actor.command('dialog_ok', name='unsavedChanges', role=role)['reply']
        assert button['pressed_changes'] > 0 and button['actual_dialog_name'] == 'unsavedChanges', (
            'Only genuine input on the original standard Save or Cancel button settles the old-work choice')
    actor.until(lambda value: len(actor.responses()) == 2 and value['ui']['state'] == 'idle',
                visible_progress=show_actions)
    current = actor.last['ui']['project']
    actual_create = actor.responses()[0]['result']
    create_body = json.loads(actual_create['contentItems'][0]['text'])
    if old_choice == 'modified_cancel':
        assert not create_body.get('adopted') and not create_body.get('complete') and create_body.get('status') != 'created', (
            'Cancel cannot be published as successful adoption or completed New merely because old science remains usable')
        assert Path(current['path']).resolve() == current_old_root.resolve() \
            and qml(actor, 'Session.project.modified') and qml(actor, 'Session.project.description') == description, (
                'Cancel retains the same original modified scientific owner and its unsaved edit rather than silently reusing it as New')
        assert qml(actor, '(' + _scene_control_expression(marker) + ').changes') == 0 \
            and not destination.exists() and _new_project_scientific_bytes(old_root) == original_bytes, (
                'Canceled explicit New performs no project replacement or write to old/new science destinations')
    else:
        assert actual_create['success'] and create_body['adopted'] and create_body['complete'], (
            'A genuine new current project also settles its original Create call truthfully rather than hiding an unconfirmed applied prefix')
        assert Path(current['path']).resolve() == destination.resolve() and destination != current_old_root, (
            'Explicit New adopts a genuinely distinct actual project at the requested normal destination, never the matching old project')
        assert current['structures'] == 0 and current['backgrounds'] == [] \
            and qml(actor, 'Session.project.name') == name and qml(actor, 'Session.project.title') == title \
            and qml(actor, 'Session.project.description') == new_description, (
                'The new ordinary project owns only its requested metadata and original empty scientific defaults, not old structures or data')
        assert (destination / 'project.edi').is_file(), 'The original ordinary Create actually saves its new project rather than reporting a boolean alone'
        if old_choice == 'modified_save':
            assert _new_project_scientific_bytes(old_root) == expected_saved, (
                'Choosing Save before New matches the independently exercised original Save owner for every old source byte')
        else:
            assert _new_project_scientific_bytes(current_old_root) == before_new \
                and _new_project_scientific_bytes(old_root) == original_bytes, (
                    'A saved old project and any real ordinary SaveAs source remain byte-exact after explicit New')
    assert [{key: row[key] for key in ('id', 'name', 'bytes')} for row in actor.last['ui']['selected_files']] == original_files, (
        'The explicitly delegated original task retains all actual selected-input identities across either New or Cancel')
    readback = native_result(actor.responses()[1])
    assert any(value == source.read_text() for row in objects(readback) for value in row.values() if isinstance(value, str)), (
        'The continuing real native reader still reaches the original approved source bytes without reattachment or substitute input')
    assert source.stat().st_ino == original_input.st_ino and hashlib.sha256(source.read_bytes()).hexdigest() == input_sha, (
        'Neither project transition changes the physical original source identity or byte authority')
    inputs = _session_state(actor)['inputs']
    assert len(inputs) == 1 and any(task in str(value) for value in inputs[0]['input']), (
        'The original captured New objective is one genuine model input, not a fresh injected continuation or an added placeholder task')
    events = actor.last['ui']['ui_sequence']
    if show_actions and old_choice != 'modified_cancel':
        assert any(e['kind'] == 'mouse_press' and e.get('create_contains_press') for e in events), (
            'Show ON genuinely clicks the FIRST normal current-window Create control even while an old project was open')
        assert any(e['kind'] in {'key_press', 'input_method'} and e.get('focus') == 'createProject.name'
                   and e.get('dialog_visible') for e in events), (
            'Show ON enters the supplied new name through the actual original Create dialog editor')
        assert any(e['kind'] == 'mouse_press' and e.get('confirm_contains_press')
                   and e.get('dialog_name') == name and e.get('dialog_title') == title
                   and e.get('dialog_description') == new_description for e in events), (
            'Show ON confirms the real original form with all requested new metadata instead of a hidden backend shortcut')
    elif not show_actions:
        assert not any(e['kind'].startswith('pointer_') or e.get('dialog_visible') for e in events), (
            'Show OFF retains ordinary required unsaved-work choice while avoiding assistant-driven Create presentation')
    (actor.folder / 'explicit-new-from-original-current.json').write_text(json.dumps({
        'old_choice': old_choice, 'mode': show_actions, 'original_path': str(old_root),
        'current_before_new': str(current_old_root), 'requested_new': str(destination),
        'original_byte_hashes': _new_project_file_hashes(original_bytes),
        'current_old_byte_hashes': _new_project_file_hashes(_new_project_scientific_bytes(current_old_root)),
        'actual_create_reply': actual_create, 'original_selected_files': original_files,
        'task_input': inputs[0], 'normal_save_as_qualification': 'explicit ordinary API preparation only; queued native chooser continuation not exercised',
        'workflow_qualification': 'creation/choice/task-input transition only; no fit/provider/scientific matrix acceptance'}, indent=2))


# Independently authored original-owner gate packet: review66_private_gates.py
# Independent review66 classes: actual current account proof, admitted human
# input/settings continuation, and preservation of viable A before B consent.
# This append is PRIVATE/UNRUN. It requires the same peer's pinned question and
# correlated account-read hold carriers, not a production hook or seeded state.

def _review66_hold_original_identity(actor, release):
    value = json.loads((actor.folder / 'peer.json').read_bytes())
    fixture = dict(value.get('session_fixture', {}));fixture['account_read_hold'] = str(release)
    _session_configure(actor, session_fixture=fixture,
        usage_notifications=[{'method': 'account/updated', 'params': {'authMode': 'chatgpt', 'planType': None}}])
    before = len(_session_wire(actor, 'account/read'))
    actor.command('refresh_usage')
    actor.until(lambda _value: len(_session_wire(actor, 'account/read')) > before)
    request = _session_wire(actor, 'account/read')[-1]
    sent = [json.loads(line) for line in actor.trace.with_suffix('.sent.jsonl').read_text().splitlines()]
    assert not any(row.get('id') == request['id'] and ('result' in row or 'error' in row) for row in sent), (
        'The admission witness really holds the original correlated account reply after a mode-only notification')
    return request


@pytest.mark.parametrize('answer_kind', ['free_text', 'offered_option'])
def test_existing_human_question_retains_original_waiter_until_same_account_confirmation(main_actor, answer_kind):
    question = {'id': 'original-question', 'header': 'Current task',
        'question': 'Should the current read-only task continue?', 'isOther': True,
        'isSecret': False, 'options': [{'label': 'Keep current', 'description': 'Keep the original task.'}]}
    actor = main_actor([[{'human_question': question, 'call_id': 'original-question-owner'}]])
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    actor.connect();actor.request('Ask the existing question before continuing this original read-only task.')
    actor.until(lambda value: bool(value['ui']['pending_question']))
    original = actor.last['ui']['pending_question'];account = qml(actor, 'Session.assistant.account')
    release = actor.folder / 'release-original-question-identity'
    try:
        held = _review66_hold_original_identity(actor, release)
        answer = 'The original task may continue.' if answer_kind == 'free_text' else 'Keep current'
        qml(actor, 'Session.assistant.answerQuestion(' + json.dumps(original['question_id']) + ',' + json.dumps(answer) + ')')
        actor.command('refresh_usage')
        assert actor.last['ui']['pending_question'] == original and not _session_state(actor).get('human_answers'), (
            'Neither free-text nor offered-option input is transmitted or consumes its already displayed original human waiter while identity is unconfirmed')
        assert qml(actor, 'Session.assistant.connected') and qml(actor, 'Session.assistant.account') == account, (
            'Holding new human input preserves the original connection and known account without manufacturing its pending identity result')
        release.touch();actor.command('refresh_usage')
        actor.until(lambda _value: any(row.get('id') == held['id'] and 'result' in row
            for row in map(json.loads, actor.trace.with_suffix('.sent.jsonl').read_text().splitlines())))
        qml(actor, 'Session.assistant.answerQuestion(' + json.dumps(original['question_id']) + ',' + json.dumps(answer) + ')')
        _session_completed(actor, 1)
        actual = _session_state(actor)['human_answers']
        assert len(actual) == 1 and actual[0]['result']['answers']['original-question']['answers'] == [answer], (
            'After exact unchanged-account proof, one genuine answer settles the retained original question once without replaying earlier work')
        (actor.folder / 'original-question-account-boundary.json').write_text(json.dumps({
            'held_read': held, 'original_question': original, 'actual_answers': actual}, indent=2))
    finally:
        release.touch()


def test_latest_selected_model_and_effort_continue_after_exact_unchanged_identity(main_actor):
    models = [{'id': model, 'model': model, 'displayName': model,
        'description': 'Independent offline settings fixture', 'hidden': False,
        'isDefault': model == 'gpt-6.1-sol', 'defaultReasoningEffort': 'medium',
        'supportedReasoningEfforts': [{'reasoningEffort': effort, 'description': effort}
            for effort in ['medium', 'high']]} for model in ['gpt-6.1-sol', 'gpt-5.6-luna']]
    actor = main_actor([[]]);_session_configure(actor, fixture_models=models,
        session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    actor.connect();account = qml(actor, 'Session.assistant.account')
    release = actor.folder / 'release-original-settings-identity'
    try:
        held = _review66_hold_original_identity(actor, release)
        boundary = len(_session_wire(actor, 'thread/settings/update'))
        actor.command('select_effort', id='high')
        actor.command('select_model', id='gpt-5.6-luna')
        actor.command('select_effort', id='medium')
        assert len(_session_wire(actor, 'thread/settings/update')) == boundary, (
            'Actual model and effort setters cannot send new thread policy while the correlated original account check is outstanding')
        release.touch();actor.command('refresh_usage')
        actor.until(lambda _value: len(_session_wire(actor, 'thread/settings/update')) > boundary)
        updates = _session_wire(actor, 'thread/settings/update')[boundary:]
        assert len(updates) == 1 and updates[0]['params']['model'] == 'gpt-5.6-luna' \
            and updates[0]['params']['effort'] == 'medium', (
                'Exact unchanged identity reconciles the latest actual selected model/effort rather than reviving an older intermediate choice')
        assert qml(actor, 'Session.assistant.account') == account, (
            'A deferred settings continuation is not a new account or a fabricated identity success')
        actor.request('Continue the same read-only conversation with the selected current settings.')
        _session_completed(actor, 1)
        (actor.folder / 'latest-settings-after-identity.json').write_text(json.dumps({
            'held_read': held, 'actual_updates': updates, 'actual_input': _session_state(actor)['inputs'][-1]}, indent=2))
    finally:
        release.touch()


def test_declining_unapproved_other_project_session_preserves_original_before_open(main_actor, tmp_path):
    actor = main_actor([[], [], []]);_session_configure(actor,
        session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    target = copied_estimate_project(tmp_path);current = tmp_path / 'viable-original-current-project'
    shutil.copytree(target, current)
    assert actor.command('open', path=str(target))['reply']['opened'], (
        'The target association begins with an actual ordinary complete project')
    actor.connect();source = _attachment_fixtures(tmp_path, 1)[0];original_bytes = source.read_bytes()
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], (
        'The target has a genuine admitted original file whose later identity change requires honest current disclosure')
    _session_request_with_original_disclosure(actor, 'Remember this original project and actual attached input.')
    _session_completed(actor, 1);target_id = _session_state(actor)['inputs'][0]['threadId']
    assert actor.command('open', path=str(current))['reply']['opened'], (
        'The viable unrelated original current project is adopted through ordinary Open before selecting the target')
    actor.connect();actor.request('Keep this distinct original current conversation usable until another target is approved.')
    _session_completed(actor, 2);current_id = _session_state(actor)['inputs'][1]['threadId']
    account = qml(actor, 'Session.assistant.account');marker = 'e11.session.before-other-consent'
    _watch_original_project_open(actor, marker)
    source.write_bytes(original_bytes + b'\n_audit_update_record "genuine changed old attachment disclosure"\n')
    try:
        before = len(_session_wire(actor, 'thread/resume'))
        actor.command('click', name='assistant.sessions');_session_wait(actor)
        clicked = actor.command('session_row_click', thread_id=target_id)['reply']
        assert clicked['reached'] and clicked['actual_pressed_changes'] > 0, (
            'The unapproved other-project intent is initiated by genuine input on its original realized session row')
        actor.until(lambda value: any(c['name'] == 'AssistantConnectionDialog' and c['fully_exposed'] and c['enabled']
            for c in value['ui']['controls']))
        assert actor.last['ui']['context_consent_required'], (
            'The discriminator genuinely reaches required current disclosure rather than assuming a saved boolean is approval')
        assert Path(actor.last['ui']['project']['path']).resolve() == current.resolve() \
            and qml(actor, '(' + _scene_control_expression(marker) + ').changes') == 0, (
                'Required other-project consent is offered before any original project replacement can retire the viable current conversation')
        actor.command('manual_key', key='escape')
        actor.until(lambda _value: not qml(actor, 'Session.assistant.sessionSelection'))
        assert len(_session_wire(actor, 'thread/resume')) == before \
            and qml(actor, 'Session.assistant.connected') and qml(actor, 'Session.assistant.account') == account, (
                'Genuine original-dialog cancellation adopts no unapproved target and preserves the actual original account/connection')
        actor.request('Continue the still-current original conversation after declining that other project.')
        _session_completed(actor, 3);followup = _session_state(actor)['inputs'][-1]
        assert followup['threadId'] == current_id and followup['actual_prior_input_count'] == 1, (
            'Cancellation preserves real original model continuity instead of injecting old display text into another or a fresh thread')
        (actor.folder / 'declined-other-project-preserved-original.json').write_text(json.dumps({
            'target': target_id, 'original_current': current_id, 'physical_click': clicked,
            'actual_followup': followup, 'original_path': str(current)}, indent=2))
    finally:
        source.write_bytes(original_bytes)


# Independently authored original-owner gate packet: review67_archive_private_gates.py
# PRIVATE/UNRUN Archive property gates from H review67 Finding1 and the original
# owned-ID authority. Static metadata is a pinned RPC fixture, never app history,
# account evidence or a scientific outcome. Native subtree disk policy remains
# independently sourced from pinned092d thread_processor.rs1709-1792.

def _archive_original_row_input(actor, identity):
    rows = _session_wait(actor)
    index = next(i for i, row in enumerate(rows) if row['id'] == identity)
    name = 'assistant.session.archive.' + str(index)
    def actual_owner(_value):
        return qml(actor, '(function(){const b=' + _scene_control_expression(name)
            + ';if(!b)return null;let r=b;while(r&&typeof r.threadId!=="string")r=r.parent;'
            'if(!r)return null;const p=b.mapToItem(window.contentItem,0,0);return {'
            'threadId:r.threadId,button:String(b),name:b.objectName,visible:b.visible,enabled:b.enabled,'
            'x:p.x,y:p.y,width:b.width,height:b.height};})()')
    owner = actual_owner(actor.last)
    assert owner and owner['threadId'] == identity and owner['visible'] and owner['enabled'], (
        'The original enabled Archive button belongs to the exact currently realized session row before genuine input')
    assert any(row['name'] == name and row['fully_exposed'] and row['enabled']
               for row in actor.last['ui']['controls']), (
        'The original Archive button is exposed in its current Main window rather than merely visible below a clip')
    actor.command('click', name=name)
    return owner


@pytest.mark.parametrize('status', [{'type': 'systemError'}, {'type': 'active', 'activeFlags': []}],
                         ids=['retained-system-error', 'native-loaded-active'])
def test_owned_archive_ignores_old_workspace_and_ui_status_without_read_dependency(main_actor, status):
    actor = main_actor([[]]);release = actor.folder / 'release-original-owned-archive'
    fixture = _session_fixture(actor, archive_hold=str(release), read_error=True,
                               list_only_fixture_threads=True, page_size=12)
    victim = fixture['thread_list']['expected_owned_ids'][0]
    value = json.loads((actor.folder / 'peer.json').read_bytes())
    original = next(row for row in value['session_fixture']['threads'] if row['id'] == victim)
    original['cwd'] = str(actor.folder / 'unavailable-original-workspace')
    original['status'] = status
    assert not Path(original['cwd']).exists(), (
        'The listed creation-owned legacy target genuinely has no usable old scientific workspace')
    (actor.folder / 'peer.json').write_text(json.dumps(value));actor.connect()
    actor.command('click', name='assistant.sessions');before = _session_wait(actor)
    account = qml(actor, 'Session.assistant.account')
    project = qml(actor, 'Session.project===null ? null : String(Session.project)')
    try:
        physical = _archive_original_row_input(actor, victim)
        actor.until(lambda _value: any(row['params']['threadId'] == victim
            for row in _session_wire(actor, 'thread/archive')))
        assert victim in {row['id'] for row in _session_wait(actor)}, (
            'A live Archive request preserves the original row until its exact correlated native acknowledgement')
        release.touch();actor.command('refresh_usage')
        actor.until(lambda _value: victim not in {row['id'] for row in _session_wait(actor)})
        requests = _session_wire(actor, 'thread/archive')
        assert len(requests) == 1 and requests[0]['params'] == {'threadId': victim}, (
            'Owned-ID Archive delegates once to the ordinary runtime operation without making old cwd/read/UI status into authority')
        assert qml(actor, 'Session.assistant.connected') and qml(actor, 'Session.assistant.account') == account \
            and qml(actor, 'Session.project===null ? null : String(Session.project)') == project, (
                'Organizing a different owned runtime target preserves the current account and scientific owner')
        (actor.folder / 'owned-archive-without-science-prerequisites.json').write_text(json.dumps({
            'target': victim, 'published_before': before, 'physical_owner': physical,
            'actual_archive_requests': requests, 'status': status,
            'actual_peer_archived': _session_state(actor)['archived_threads'],
            'qualification': 'app-to-native RPC delegation, not a real-provider filesystem Archive execution'}, indent=2))
    finally:
        release.touch()


def test_last_remaining_owned_row_keeps_its_identity_after_prior_archives_and_prefetch(main_actor):
    actor = main_actor([[]]);fixture = _session_page_fixture(actor, foreign=0, owned=5, page=2)
    actor.connect();actor.command('click', name='assistant.sessions');_session_wait(actor)
    remaining = {row['id'] for row in fixture};observed=[]
    while remaining:
        rows = _session_wait(actor)
        candidates = [row['id'] for row in rows if row['id'] in remaining]
        if not candidates:
            delivery = actor.command('session_wheel', angle_y=-120)['reply']
            assert delivery['same_window'] and delivery['same_source_model'], (
                'Only a genuine wheel on the original current session viewport requests the next pending page')
            actor.until(lambda _value: any(row['id'] in remaining for row in _session_wait(actor)))
            rows = _session_wait(actor);candidates = [row['id'] for row in rows if row['id'] in remaining]
        victim = candidates[0]
        before = len(_session_wire(actor, 'thread/archive'))
        physical = _archive_original_row_input(actor, victim)
        actor.until(lambda _value: len(_session_wire(actor, 'thread/archive')) > before
            and victim not in {row['id'] for row in _session_wait(actor)})
        actual = _session_wire(actor, 'thread/archive')[before:]
        assert len(actual) == 1 and actual[0]['params'] == {'threadId': victim}, (
            'Every original Archive input retains its row-owned opaque ID after deletion, reuse and page publication rather than using a display ordinal')
        observed.append({'target': victim, 'physical_owner': physical, 'actual_request': actual[0]})
        remaining.remove(victim)
    assert len(_session_wire(actor, 'thread/list')) > 1, (
        'The final-row discriminator actually includes native pagination before all listed owned targets are archived')
    actual = _session_state(actor)['archived_threads']
    assert set(actual) == {row['id'] for row in fixture} and len(actual) == len(fixture), (
        'The final remaining original row is archived once with no foreign or duplicate target inferred from list disappearance')
    (actor.folder / 'last-owned-row-archive-inputs.json').write_text(json.dumps({
        'actual_inputs': observed, 'actual_archived': actual,
        'delegate_reuse_observed': len({row['physical_owner']['button'] for row in observed}) < len(observed),
        'reuse_qualification': 'only an actual repeated QObject string is a reached reuse witness'}, indent=2))


def test_idle_current_native_archive_owns_its_loaded_descendant_closure_and_notifications(main_actor):
    actor = main_actor([[]]);fixture = _session_fixture(actor, page_size=12,
        native_archive_subtree=True, emit_archived_notifications=True)
    actor.connect();current = next(iter(_session_state(actor)['threads']))
    value = json.loads((actor.folder / 'peer.json').read_bytes())
    child = value['session_fixture']['threads'][0]
    child['parentThreadId'] = current;child['status'] = {'type': 'active', 'activeFlags': []}
    unrelated = value['session_fixture']['threads'][1]['id']
    (actor.folder / 'peer.json').write_text(json.dumps(value))
    actor.request('Retain one actual read-only current conversation before organizing it.');_session_completed(actor, 1)
    actor.command('click', name='assistant.sessions');_session_wait(actor)
    before = len(_session_wire(actor, 'thread/archive'))
    physical = _archive_original_row_input(actor, current)
    actor.until(lambda _value: len(_session_wire(actor, 'thread/archive')) > before)
    actor.until(lambda _value: current not in {row['id'] for row in _session_wait(actor)})
    requests = _session_wire(actor, 'thread/archive')[before:]
    assert len(requests) == 1 and requests[0]['params'] == {'threadId': current}, (
        'An idle current owned target with descendants is delegated as one exact native subtree operation rather than app-owned child policy')
    state = _session_state(actor)
    assert {current, child['id']} <= set(state['archived_threads']) and unrelated not in state['archived_threads'], (
        'The pinned native peer acknowledges its actual parent closure without optimistically deleting unrelated runtime owners')
    sent = [json.loads(line) for line in actor.trace.with_suffix('.sent.jsonl').read_text().splitlines()]
    ids = {row['params']['threadId'] for row in sent if row.get('method') == 'thread/archived'}
    assert {current, child['id']} <= ids, (
        'Affected rows are reconciled from actual captured native archived notifications rather than assumed from the requested parent')
    (actor.folder / 'native-archive-loaded-subtree.json').write_text(json.dumps({
        'physical_owner': physical, 'native_request': requests[0], 'actual_notifications': sorted(ids),
        'actual_archived': state['archived_threads'],
        'real_provider_shutdown': 'not exercised by this offline metadata peer'}, indent=2))


@pytest.mark.parametrize('boundary', ['nonowned', 'pending_identity', 'active_work', 'sign_out'])
def test_archive_preserves_real_account_and_active_operation_admission_boundaries(main_actor, boundary):
    actor = main_actor([[_rows_research('original-active-archive-boundary')]], hold_final=True)
    fixture = _session_fixture(actor);actor.connect();actor.command('click', name='assistant.sessions');rows=_session_wait(actor)
    victim = fixture['thread_list']['expected_owned_ids'][0]
    release = actor.folder / 'release-original-negative-archive-identity'
    try:
        if boundary == 'nonowned':
            victim = next(row['id'] for row in fixture['thread_list']['threads'] if row['originator'] != 'edi')
        elif boundary == 'pending_identity':
            _review66_hold_original_identity(actor, release)
        elif boundary == 'sign_out':
            actor.command('sign_out')
        else:
            actor.command('manual_key', key='escape');actor.request('Keep one real read-only task active before metadata organization.')
            actor.until(lambda value: value['ui']['can_cancel'])
        before = len(_session_wire(actor, 'thread/archive'))
        qml(actor, 'Session.assistant.archiveSession(' + json.dumps(victim) + ')')
        actor.command('refresh_usage')
        assert len(_session_wire(actor, 'thread/archive')) == before, (
            'Foreign creation identity, pending account proof, signed-out old ownership and actual active work cannot admit a new Archive write')
    finally:
        release.touch();actor.gate.touch()

# Uncertain Stop is explicitly UNREACHED here: the existing peer immediately
# acknowledges turn/interrupt. A completed Stop must not become a permanent
# Archive prohibition; no stronger policy is inferred or synthesized.


# Independently authored original-owner gate packet: review70_archive_async_private_gates.py
# PRIVATE/UNRUN review70 actual asynchronous Archive owners. All late frames
# belong to genuine fixture-received original requests and captured runtime IDs;
# no old scientific operation is replayed and no app receipt is manufactured.

@pytest.mark.parametrize('late_reply', ['success', 'refusal'])
def test_actual_archived_notice_retires_original_pending_turn_start_without_resurrection(main_actor, late_reply):
    actor = main_actor([[], []]);_session_configure(actor,
        session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    actor.connect();account = qml(actor, 'Session.assistant.account')
    original_thread = next(iter(_session_state(actor)['threads']))
    release = actor.folder / 'release-original-admitted-start-after-archive'
    _session_configure(actor, archive_before_start_reply={'hold': str(release), 'reply': late_reply})
    original_task = 'An original read-only input awaiting its actual native runtime admission reply.'
    actor.request(original_task)
    actor.until(lambda _value: bool(_session_wire(actor, 'turn/start')) and any(
        row.get('method') == 'thread/archived' and row['params']['threadId'] == original_thread
        for row in map(json.loads, actor.trace.with_suffix('.sent.jsonl').read_text().splitlines())))
    original_request = _session_wire(actor, 'turn/start')[0]
    before_release = [json.loads(line) for line in actor.trace.with_suffix('.sent.jsonl').read_text().splitlines()]
    assert not any(row.get('id') == original_request['id'] and ('result' in row or 'error' in row)
                   for row in before_release), (
        'The actual original turn/start is still awaiting its own reply when the matching archived-ID notification arrives')
    try:
        release.touch();actor.command('refresh_usage')
        actor.until(lambda _value: any(row.get('id') == original_request['id'] and ('result' in row or 'error' in row)
            for row in map(json.loads, actor.trace.with_suffix('.sent.jsonl').read_text().splitlines())))
        actor.until(lambda value: value['ui']['state'] == 'idle' and not value['ui']['can_cancel'])
        assert qml(actor, 'Session.assistant.connected') and qml(actor, 'Session.assistant.account') == account, (
            'A late start acknowledgement or refusal settles only its retired input and cannot resurrect busy state or revoke the unchanged valid account')
        assert len(_session_wire(actor, 'turn/start')) == 1, (
            'Archive uncertainty never authorizes an automatic replay of the original admitted user input')
        _session_configure(actor, archive_before_start_reply=None)
        next_task = 'A distinct fresh read-only input after the original archived owner is settled.'
        actor.request(next_task)
        actor.until(lambda value: value['ui']['state'] == 'idle' and len(_session_state(actor)['inputs']) == 2)
        inputs = _session_state(actor)['inputs']
        assert inputs[0]['threadId'] == original_thread and inputs[1]['threadId'] != original_thread, (
            'The next explicit input obtains its own current runtime thread and cannot inherit the archived late reply')
        assert len(_session_wire(actor, 'turn/start')) == 2 and original_task in str(inputs[0]['input']) \
            and next_task in str(inputs[1]['input']), (
                'Only the two actually submitted user inputs reach the runtime, with original text kept once under its captured identity')
        (actor.folder / 'actual-archive-pending-start-boundary.json').write_text(json.dumps({
            'original_request': original_request, 'reply_case': late_reply, 'actual_inputs': inputs,
            'actual_before_release': before_release, 'account_preserved': True}, indent=2))
    finally:
        release.touch()


@pytest.mark.parametrize('entrance', ['root_ack', 'actual_notice'])
def test_archive_retires_original_inflight_history_before_later_same_current_read(main_actor, entrance):
    actor = main_actor([[], []]);_session_configure(actor,
        session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    actor.connect();actor.request('First genuine read-only A conversation before its current history walk.')
    _session_completed(actor, 1);original_thread = _session_state(actor)['inputs'][0]['threadId']
    release = actor.folder / 'release-original-A-history'
    value = json.loads((actor.folder / 'peer.json').read_bytes());fixture = dict(value['session_fixture'])
    fixture['read_hold'] = str(release);_session_configure(actor, session_fixture=fixture)
    actor.command('click', name='assistant.sessions');_session_wait(actor)
    before = len(_session_wire(actor, 'thread/read'))
    actual = actor.command('session_row_click', thread_id=original_thread)['reply']
    assert actual['reached'] and actual['actual_pressed_changes'] > 0, (
        'A real current-row click starts the original current runtime-history owner before Archive')
    actor.until(lambda _value: len(_session_wire(actor, 'thread/read')) > before)
    original_history = _session_wire(actor, 'thread/read')[-1]
    assert original_history['params']['threadId'] == original_thread, (
        'The deliberately held history request belongs to the exact original current A thread')
    try:
        if entrance == 'root_ack':
            qml(actor, 'Session.assistant.archiveSession(' + json.dumps(original_thread) + ')')
            actor.until(lambda _value: any(row['params']['threadId'] == original_thread
                for row in _session_wire(actor, 'thread/archive')))
        else:
            _session_configure(actor, usage_notifications=[{'method': 'thread/archived', 'params': {'threadId': original_thread}}])
            actor.command('refresh_usage')
        actor.until(lambda value: not value['ui']['can_cancel'] and value['ui']['connected'])
        actor.request('A new explicit B conversation after original A was archived with history still outstanding.')
        actor.until(lambda value: value['ui']['state'] == 'idle' and len(_session_state(actor)['inputs']) == 2)
        current_thread = _session_state(actor)['inputs'][-1]['threadId']
        assert current_thread != original_thread, 'The later history owner is a genuinely different actually submitted B thread'
        release.touch();actor.command('refresh_usage')
        actor.until(lambda _value: any(row.get('id') == original_history['id'] and 'result' in row
            for row in map(json.loads, actor.trace.with_suffix('.sent.jsonl').read_text().splitlines())))
        actor.command('click', name='assistant.sessions');_session_wait(actor)
        boundary = len(_session_wire(actor, 'thread/read'))
        selected = actor.command('session_row_click', thread_id=current_thread)['reply']
        assert selected['reached'] and selected['actual_pressed_changes'] > 0, (
            'The later same-current B coverage request is also exercised through its original realized row input')
        actor.until(lambda _value: any(row['params']['threadId'] == current_thread
            for row in _session_wire(actor, 'thread/read')[boundary:]))
        assert not qml(actor, 'Session.assistant.sessionsError') and qml(actor, 'Session.assistant.connected'), (
            'A retired A history reply cannot leave immortal loading state or suppress the actual new same-current B history request')
        (actor.folder / 'retired-A-current-B-history-owner.json').write_text(json.dumps({
            'entrance': entrance, 'original_held_history': original_history,
            'current_B': current_thread, 'actual_B_reads': _session_wire(actor, 'thread/read')[boundary:]}, indent=2))
    finally:
        release.touch()


def test_failed_durable_archive_last_write_survives_successful_ordinary_browser_refresh(main_actor):
    actor = main_actor([[]]);_session_configure(actor,
        session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    actor.connect();actor.request('One genuine current conversation retained by the original normal session settings owner.')
    _session_completed(actor, 1);original = _session_state(actor)['inputs'][0]['threadId']
    observed = actor.command('inspect');identity = observed['test_settings'];settings = Path(identity['path'])
    assert settings.name == 'EasyDiffraction.ini' and settings.parent.name == 'EasyScience' \
        and settings.stat().st_uid == os.geteuid() and not settings.is_symlink() and os.geteuid() != 0, (
            'The storage fault is confined to the exact genuine isolated fixture QSettings file reported by its current Main owner')
    original_bytes = settings.read_bytes();saved = actor.folder / 'genuine-settings-before-archive.ini';saved.write_bytes(original_bytes)
    assert original.encode() in original_bytes, (
        'The genuine first normal settings write actually contains the original connected runtime ID before the durable Archive fault')
    file_mode = settings.stat().st_mode & 0o777;parent_mode = settings.parent.stat().st_mode & 0o777
    account = qml(actor, 'Session.assistant.account')
    actor.command('click', name='assistant.sessions');_session_wait(actor)
    marker = 'e11.archive.durable-failure'
    assert qml(actor, '(function(){const o=Qt.createQmlObject(\'import QtQuick; Item {objectName:"' + marker + '";property var errors:[]}\',contentItem);Session.assistant.sessionsChanged.connect(function(){const error=Session.assistant.sessionsError;if(error)o.errors=o.errors.concat([error]);});return true;})()'), (
        'The unresolved original settings failure is observed at its real public notification before any automatic refresh can hide it')
    settings.chmod(file_mode & ~0o222);settings.parent.chmod(parent_mode & ~0o222)
    try:
        assert not os.access(settings, os.W_OK) and not os.access(settings.parent, os.W_OK), (
            'The exact file and its atomic-save directory are genuinely unwritable for this fixture user; no global filesystem hook is used')
        qml(actor, 'Session.assistant.archiveSession(' + json.dumps(original) + ')')
        actor.until(lambda _value: any(row['params']['threadId'] == original for row in _session_wire(actor, 'thread/archive')))
        actor.until(lambda _value: bool(qml(actor, '(' + _scene_control_expression(marker) + ').errors.length')))
        failure = qml(actor, '(' + _scene_control_expression(marker) + ').errors[0]')
        assert settings.read_bytes() == original_bytes, (
            'The failed original durable-last update preserves the exact preexisting settings evidence instead of pretending it was committed')
        before = len(_session_wire(actor, 'thread/list'))
        qml(actor, 'Session.assistant.refreshSessions()');_session_wait(actor)
        assert len(_session_wire(actor, 'thread/list')) > before, (
            'The failure-retention property is exercised after an actual later successful ordinary browser metadata refresh')
        assert qml(actor, 'Session.assistant.sessionsError') == failure and settings.read_bytes() == original_bytes, (
            'A successful list refresh cannot erase the unresolved distinct original durable-last persistence failure or upgrade it to saved intent')
        assert qml(actor, 'Session.assistant.connected') and qml(actor, 'Session.assistant.account') == account, (
            'Valid native Archive and failed local durability remain distinct from account revocation')
        (actor.folder / 'failed-durable-last-after-actual-refresh.json').write_text(json.dumps({
            'original_thread': original, 'settings_identity': identity,
            'original_settings_sha256': hashlib.sha256(original_bytes).hexdigest(),
            'actual_unresolved_error': failure, 'actual_archive': _session_wire(actor, 'thread/archive'),
            'actual_later_lists': _session_wire(actor, 'thread/list')[before:],
            'automatic_reopen_proven_prevented': False}, indent=2))
    finally:
        settings.parent.chmod(parent_mode);settings.chmod(file_mode)


# Independently authored original-owner gate packet: review72_unsaved_flow_private_gates.py
# PRIVATE/UNRUN review72. Routine delegated Save may choose the genuine normal
# role itself; this gate does not require an unnecessary second user approval.
# Read-only original signals prove guard-before-write and SaveAs abandonment.

def _watch_first_unsaved_flow(actor, marker):
    expression = '(function(){const d=unsavedChanges,p=Session.project;if(!d||!p)return false;'
    expression += 'const o=Qt.createQmlObject(\'import QtQuick; Item {objectName:"' + marker + '";property var original:null;property var events:[];property int savePresses:0;property bool saveButtonBound:false;property int saveAsOffers:0}\',contentItem);o.original=p;'
    expression += 'function event(kind){o.events=o.events.concat([{kind:kind,sameOriginal:Session.project===p,modified:p.modified,needsSaveAs:Session.needsSaveAs}]);}'
    expression += 'function bindSave(){if(o.saveButtonBound)return;const b=d.standardButton(Dialog.Save);if(b){o.saveButtonBound=true;b.pressedChanged.connect(function(){if(b.pressed)o.savePresses++;});}}d.aboutToShow.connect(function(){event("originalUnsavedGuard");bindSave();});d.opened.connect(bindSave);p.modifiedChanged.connect(function(){event(p.modified?"originalModified":"originalMarkedSaved");});'
    expression += 'bindSave();'
    expression += 'saveAsChoice.aboutToShow.connect(function(){o.saveAsOffers++;});return true;})()'
    assert qml(actor, expression), (
        'The unsaved-flow witness attaches only to original current Main dialog, model and standard Save owners without forcing state or outcomes')


def _unsaved_flow_observation(actor, marker):
    return qml(actor, '(function(){const o=' + _scene_control_expression(marker)
        + ';return {events:o.events,savePresses:o.savePresses,saveButtonBound:o.saveButtonBound,saveAsOffers:o.saveAsOffers,sameOriginal:Session.project===o.original};})()')


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_native_new_enters_original_unsaved_guard_before_any_preservation_save(main_actor, tmp_path, show_actions):
    name = 'guard_' + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    actor = main_actor([[tool_call('create_project', 'original-unsaved-before-new', name=name)]], show_actions=show_actions)
    old = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(old))['reply']['opened'], (
        'Original unsaved-flow ordering begins with a genuine complete saved project')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    description = 'The original user edit must enter the first ordinary unsaved guard before it is saved.'
    qml(actor, 'Session.project.description=' + json.dumps(description))
    assert qml(actor, 'Session.project.modified') and not qml(actor, 'Session.needsSaveAs'), (
        'The specific preservation-write case really is modified ordinary in-place work before New')
    original = _new_project_scientific_bytes(old)
    destination = Path(actor.last['ui']['environment']['documents_root']) / name
    assert not destination.exists(), 'The normal new-project destination remains absent before its real owner acts'
    actor.connect();marker='e11.new.first-unsaved-order';_watch_first_unsaved_flow(actor, marker)
    actor.command('clear_ui_sequence');actor.request('Create a genuinely new project while preserving my current unsaved work through the normal app choices.')
    actor.until(lambda value: len(actor.responses()) == 1 and value['ui']['state'] == 'idle', visible_progress=show_actions)
    proof = _unsaved_flow_observation(actor, marker)
    guards = [i for i, row in enumerate(proof['events']) if row['kind'] == 'originalUnsavedGuard']
    saves = [i for i, row in enumerate(proof['events']) if row['kind'] == 'originalMarkedSaved']
    assert guards and saves and guards[0] < saves[0] and proof['events'][guards[0]]['sameOriginal'] \
        and proof['events'][guards[0]]['modified'], (
            'A real FIRST unsaved decision precedes every preservation Save; calling afterChanges only after a preemptive write is insufficient')
    if show_actions:
        assert proof['saveButtonBound'], (
            'The ON Save input witness must reach its actual original standard button before interpreting a missing press')
        assert proof['savePresses'] > 0, (
            'Show ON actually delivers the original normal Save choice rather than replacing it with a pre-guard Save cue/API shortcut')
    created = native_result(actor.responses()[0])
    assert created['adopted'] and created['complete'] and Path(actor.last['ui']['project']['path']) == destination, (
        'After the original Save decision succeeds, the same captured creation action adopts the genuinely new requested ordinary project')
    assert description in (old / 'project.edi').read_text() and _new_project_scientific_bytes(old) != original, (
        'The legitimate preservation write actually kept the original explicit user edit rather than silently Discarding it')
    (actor.folder / 'first-unsaved-before-new-save.json').write_text(json.dumps({
        'mode': show_actions, 'proof': proof, 'old_source_hashes': _new_project_file_hashes(original),
        'actual_old_after': _new_project_file_hashes(_new_project_scientific_bytes(old)),
        'requested_new': str(destination), 'actual_create': created}, indent=2))


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_native_new_preserves_original_save_as_abandonment_without_resurrecting_create(main_actor, tmp_path, show_actions):
    actor = main_actor([[]], show_actions=show_actions);source = copied_estimate_project(tmp_path)
    original = _new_project_scientific_bytes(source)
    modes = {path: path.stat().st_mode & 0o777 for path in [source, *source.rglob('*')]}
    try:
        for path in source.rglob('*'):path.chmod(0o555 if path.is_dir() else 0o444)
        source.chmod(0o555)
        assert actor.command('open', path=str(source))['reply']['opened'], (
            'An actual ordinary read-only source Open creates its normal mutable working-copy owner')
        assert qml(actor, 'Session.needsSaveAs'), (
            'The SaveAs branch is reached from the real original Session predicate, never a forced saved/path property')
        actor.until(lambda value: not value['ui']['project']['calculating'])
        qml(actor, 'Session.project.description="A genuine modified read-only-source working copy before New."')
        assert qml(actor, 'Session.project.modified'), 'The original mutable working copy has a real unsaved user edit'
        name='abandon_' + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
        destination=Path(actor.last['ui']['environment']['documents_root']) / name
        assert not destination.exists(), 'The requested New destination is absent before the original guard'
        actor.configure_turns([[tool_call('create_project', 'new-with-original-save-as-abandonment', name=name)]])
        actor.connect();marker='e11.new.original-save-as-abandon';_watch_first_unsaved_flow(actor, marker)
        actor.request('Create a new project and preserve current work through the app\'s original Save choices.')
        actor.until(lambda value: len(actor.responses()) == 1 and value['ui']['state'] == 'idle', visible_progress=show_actions)
        proof=_unsaved_flow_observation(actor,marker)
        assert any(row['kind']=='originalUnsavedGuard' and row['needsSaveAs'] and row['modified'] for row in proof['events']) \
            and proof['saveAsOffers'] > 0, (
                'The actual original needs-SaveAs guard and ordinary SaveAs offer are both observed before classifying abandonment')
        body=json.loads(actor.responses()[0]['result']['contentItems'][0]['text'])
        assert not body.get('adopted') and not body.get('complete') and proof['sameOriginal'] and not destination.exists(), (
            'The FIRST SaveAs branch abandons its captured original New action; later SaveAs cannot silently keep or resume that queued creation')
        assert _new_project_scientific_bytes(source)==original, (
            'Readonly-source preservation never overwrites the real original source while a different place is selected or abandoned')
        # If the original offer remains open, cancel it using genuine keyboard
        # input. No chooser acceptance or destination is manufactured.
        open_offer=qml(actor,'saveAsChoice.opened')
        if open_offer:
            assert any(c['name']=='saveAs.folder' and c['fully_exposed'] for c in actor.last['ui']['controls']), (
                'A pending ordinary SaveAs offer belongs to the actual exposed original Main controls before Cancel input')
            actor.command('manual_key',key='escape')
            actor.until(lambda _value:not qml(actor,'saveAsChoice.opened'))
        assert not destination.exists() and _unsaved_flow_observation(actor,marker)['sameOriginal'], (
            'Canceling or settling a later format offer cannot revive the abandoned original New continuation')
        (actor.folder/'original-save-as-abandons-new.json').write_text(json.dumps({
            'mode':show_actions,'proof':proof,'actual_create_reply':body,
            'offer_was_pending':open_offer,'old_source_hashes':_new_project_file_hashes(original),
            'new_destination_absent':not destination.exists(),
            'platform_chooser_accepted':False},indent=2))
    finally:
        # Restore only this isolated source's exact original modes.
        source.chmod(modes[source])
        for path,mode in modes.items():
            if path.exists():path.chmod(mode)


# Independently authored original-owner gate packet: ordinary_partial_projects_private_gates.py
# PRIVATE/UNRUN Hf51d49068 / review74. This supersedes only the explicitly
# complete-only ordinary Open expectation, not schema/reference/data integrity.
# Preparation and all positives use original Session/PVM APIs and native Save;
# no hidden load flag, placeholder observations or direct passing file rewrite.

def _construction_enabled_tabs(actor):
    names = sorted({row['name'] for row in actor.last['ui']['controls']
                    if row['name'].startswith('appBar.tab.')})
    assert names, 'Partial-state tab restoration observes actual normal Main tab controls'
    def settled(_value):
        values = qml(actor, '[' + ','.join('(function(){const b=' + _scene_control_expression(name)
            + ';return b?{name:b.objectName,enabled:b.enabled,preparing:b.preparing===true}:null;})()'
            for name in names) + ']')
        return values if all(value and not value['preparing'] for value in values) else None
    actor.until(lambda value: bool(settled(value)))
    return {value['name']: value['enabled'] for value in settled(actor.last)}


def _construction_science(actor):
    project = actor.command('inspect')['ui']['project']
    metadata = qml(actor, '({name:Session.project.name,title:Session.project.title,description:Session.project.description,'
        'authors:Session.project.authors,rule:Session.project.suRule,libraries:Session.project.report.embedLibraries})')
    return {'metadata': metadata, 'structures': project['structures'],
        'structure_rows': project['structure_rows'], 'parameters': project['parameters'],
        'backgrounds': project['backgrounds'], 'aliases': project['aliases'],
        'constraints': project['constraints']}


def _prepare_ordinary_construction_state(actor, state, name):
    if any(row['name'] == 'home.start' and row['fully_exposed'] and row['enabled'] for row in actor.last['ui']['controls']):
        actor.command('click', name='home.start')
    assert actor.command('create', name=name)['reply']['created'], (
        'The actual original Session Create owner constructs the unsaved working state without an assistant recipe or fixture science write')
    if state != 'empty':
        source = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
        assert qml(actor, 'Session.project.loadStructures([' + json.dumps(source.as_uri()) + '])'), (
            'The structure-only construction member comes through the original ordinary CIF reader at its unchanged source identity')
    if state == 'experiment_without_data':
        assert qml(actor, 'Session.project.createExperiment()'), (
            'The original default experiment owner is exercised without adding measurements or a scientific starting seed')
        actual = actor.command('scientific_receipt')['reply']['files']
        experiment = next(row for row in actual if row['relative'].startswith('experiments/') and row['relative'].endswith('.edi'))
        # A legitimate Text-tab edit removes an optional range, if the ordinary
        # factory supplied one. It never writes a fake disk postimage or grid.
        without_range = ''.join(line for line in experiment['text'].splitlines(keepends=True)
                                if not line.lstrip().startswith('_data_range.'))
        if without_range != experiment['text']:
            assert qml(actor, 'Session.project.applyText(' + json.dumps(experiment['relative']) + ',' + json.dumps(without_range) + ')') == '', (
                'Ordinary Text apply accepts a lawful construction state with no optional calculation range while retaining native reference checks')
        actor.until(lambda value: not value['ui']['project']['calculating'])
        banks = actor.last['ui']['project']['backgrounds']
        assert len(banks) == 1 and banks[0]['input_count'] == 0 and banks[0]['input_intensity_count'] == 0, (
            'The missing-data discriminator actually has neither original observations nor a fabricated calculation grid')
    # The same normal Text owner must also accept metadata on an empty or
    # structure-only project; completeness is not a reason to reject that edit.
    files = actor.command('scientific_receipt')['reply']['files']
    project_text = next(row['text'] for row in files if row['relative'] == 'project.edi')
    text = ''.join(line for line in project_text.splitlines(keepends=True)
                   if not line.lstrip().startswith('_metadata.description'))
    text += '\n_metadata.description "Ordinary construction-state Text edit survives Save and Open."\n'
    assert qml(actor, 'Session.project.applyText("project.edi",' + json.dumps(text) + ')') == '', (
        'The ordinary Text-tab copy/readback shares construction-state Open semantics rather than a hidden permissive test loader')
    actor.until(lambda value: not value['ui']['project']['calculating'])


@pytest.mark.parametrize('state', ['empty', 'structure_only', 'experiment_without_data'])
@pytest.mark.parametrize('format_kind', ['folder', 'record', 'zip'])
def test_ordinary_saved_construction_state_reopens_and_restarts_with_real_members_tabs_and_history(
    main_actor, tmp_path, monkeypatch, state, format_kind
):
    actor = main_actor([[tool_call('inspect_project', 'genuine-construction-state-history')]])
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    name = 'partial_' + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:14]
    _prepare_ordinary_construction_state(actor, state, name)
    target = tmp_path / ('ordinary-state.zip' if format_kind == 'zip' else 'ordinary-state-folder')
    assert not target.exists(), 'The genuine ordinary Save format owner creates its absent fixture destination'
    assert actor.command('save_project_as', path=str(target), zip=format_kind == 'zip', copy=False)['reply']['saved'], (
        'Normal Session SaveAs actually writes the construction state through its original folder/archive format owner')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    original = _construction_science(actor);tabs = _construction_enabled_tabs(actor)
    before = ({'archive': target.read_bytes()} if target.is_file() else _new_project_scientific_bytes(target))
    location = target / 'project.edi' if format_kind == 'record' else target
    assert actor.command('open', path=str(location))['reply']['opened'], (
        'Ordinary Open restores its own genuinely saved empty/intermediate state rather than imposing computation completeness')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    assert _construction_science(actor) == original and _construction_enabled_tabs(actor) == tabs, (
        'Actual serialized metadata, members, optional uncertainties, flags, references and enabled normal tabs roundtrip without invented placeholders')
    assert qml(actor, 'Session.lastError') == '', 'Successful construction-state Open is not a dismissed ordinary startup/load error'
    after = ({'archive': target.read_bytes()} if target.is_file() else _new_project_scientific_bytes(target))
    assert after == before, 'Ordinary Open never repairs, deletes or overwrites the original saved project to manufacture successful restore'
    actor.connect();actor.request('Inspect this actual saved work-in-progress without inventing missing structures, observations or a fit.')
    _session_completed(actor, 1);native_result(actor.responses()[0])
    thread = _session_state(actor)['inputs'][0]['threadId']
    _capture_genuine_archive(actor, 'construction-state-current')
    manifest = _capture_exact_cache_manifest(actor, 'construction-state-current')
    sources = _finish_genuine_restart_sources(actor, manifest)
    restored = _start_exact_original_fixture_restart(tmp_path, monkeypatch, sources, [])
    try:
        _ordinary_restart_connect(restored)
        restored.until(lambda value: value['ui']['connected'] and bool(value['ui']['project']))
        assert _construction_science(restored) == original and _construction_enabled_tabs(restored) == tabs, (
            'A real fresh ordinary restart restores the same partial scientific state/tab availability through the normal Session project owner')
        resumes = _session_wire(restored, 'thread/resume')
        assert resumes and resumes[-1]['params']['threadId'] == thread and not _session_wire(restored, 'turn/start'), (
            'Construction-state project restoration binds the actual original conversation without replaying a prompt or any scientific operation')
        (restored.folder / 'ordinary-construction-state-roundtrip.json').write_text(json.dumps({
            'state': state, 'format': format_kind, 'saved_source': str(target), 'opened_location': str(location),
            'original_tabs': tabs, 'original_science': original, 'actual_resume': resumes[-1],
            'source_sha256': hashlib.sha256(before['archive']).hexdigest() if 'archive' in before else _new_project_file_hashes(before),
            'platform_chooser_input': 'not claimed; public original Session format API exercised'}, indent=2))
    finally:
        _close_explicit_restart_actor(restored)


@pytest.mark.parametrize('corruption', ['malformed_metadata', 'unsupported_schema', 'dangling_structure', 'malformed_present_data'])
def test_construction_state_open_preserves_original_schema_data_and_held_reference_refusals(main_actor, tmp_path, corruption):
    actor = main_actor([[]]);_prepare_ordinary_construction_state(actor, 'empty', 'safe_partial_current')
    safe = tmp_path / 'safe-original-partial'
    assert actor.command('save_as', path=str(safe))['reply']['saved'], (
        'The refusal control has an independently saved viable ordinary partial original before reading the malformed target')
    original = _construction_science(actor);original_files = _new_project_scientific_bytes(safe)
    broken = copied_estimate_project(tmp_path / 'explicit-corrupted-complete-source', overrides=False)
    if corruption == 'malformed_metadata':
        with (broken / 'project.edi').open('a') as output:output.write('\n_metadata.title "unterminated deliberate negative fixture\n')
    elif corruption == 'unsupported_schema':
        path = broken / 'project.edi';path.write_text(path.read_text().replace('_edi.schema_version 3', '_edi.schema_version 999999', 1))
    elif corruption == 'dangling_structure':
        linked = broken / 'structures/phase.edi'
        assert linked.is_file(), 'The actual original reference fixture contains the held phase member before explicit negative removal'
        linked.unlink()  # Only the corrupted copy loses its real referenced member.
    else:
        path = broken / 'experiments/bank.edi';text = path.read_text()
        old = '10 167 12.6'
        assert old in text, 'Malformed-present-data control mutates one actual original numeric row, not an invented empty category'
        path.write_text(text.replace(old, '10 not-a-number 12.6', 1))
    malformed = _new_project_scientific_bytes(broken)
    assert not actor.command('open', path=str(broken))['reply']['opened'] and qml(actor, 'Session.lastError'), (
        'Allowing absent construction members cannot permit malformed schema/metadata/present observations or actual dangling held references')
    assert _construction_science(actor) == original and _new_project_scientific_bytes(safe) == original_files, (
        'A truthful malformed-target refusal preserves the actual viable original partial project and its saved source bytes')
    assert _new_project_scientific_bytes(broken) == malformed, (
        'Ordinary Open does not silently delete or repair the deliberately failing source to hide an integrity error')

# Strict computation/model loading, web stored/recovery, readonly/example
# copies and all installer platforms remain separately unrun. These positives
# use only ordinary Session restoration; they do not relax the strict consumer.


# Independently authored original-owner gate packet: review73_74_76_private_gates.py
# PRIVATE / AUTHORED / UNRUN. Append candidate for the existing real Main actor.
# Expectations: owner truthful terminal/Stop/currentness contracts, reviews73/74/76,
# pinned092d Turn Option<TurnError>; no expected values read from repair drafts.

def _provider_actual_report(actor, project, status=None):
    path = project / 'reports/work-report.json'
    def ready(_value):
        if not path.is_file():
            return False
        try:
            report = json.loads(path.read_bytes())
        except (OSError, ValueError):
            return False
        turns = report.get('scope_coverage', {}).get('turns', [])
        return bool(turns) and turns[-1].get('terminal', {}).get('value') in ('completed', 'interrupted', 'failed') \
            and (status is None or turns[-1].get('terminal', {}).get('value') == status)
    actor.until(ready)
    original = path.read_bytes();value = json.loads(original)
    destination = actor.folder / ('actual-provider-report-' + str(len(list(actor.folder.glob('actual-provider-report-*.json')))) + '.json')
    destination.write_bytes(original)
    (destination.with_suffix('.identity.json')).write_text(json.dumps({'source': str(path),
        'copy': str(destination), 'bytes': len(original), 'sha256': hashlib.sha256(original).hexdigest(),
        'exact_copy': original == destination.read_bytes()}, indent=2))
    rows = [entry['row'] for entry in value['history_evidence']]
    return value, rows


def _provider_read_then_terminal(main_actor, tmp_path, terminal, *, hold=False):
    call = {'tool': 'inspect_project', 'call_id': 'original-read-before-terminal',
        'arguments': {'purpose': 'Read the actual original current project before the finite runtime terminal.'}}
    actor = main_actor([[call]], hold_final=hold)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'Terminal ownership starts with a genuine ordinary current project, not fabricated native output')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12},
        observe_context_continuity=True, fixture_provider_terminal=terminal)
    actor.connect();_session_request_with_original_disclosure(actor,
        'Observe the current project through the original read-only native operation once.')
    actor.until(lambda _value: len(actor.responses()) == 1)
    native_result(actor.responses()[0])
    return actor, project, call


def test_real_stop_with_null_error_does_not_invent_provider_failure(main_actor, tmp_path):
    actor, project, call = _provider_read_then_terminal(main_actor, tmp_path, None, hold=True)
    before = json.loads(json.dumps(actor.responses()[0]))
    assert actor.last['ui']['can_cancel'], (
        'The original accepted task remains genuinely cancellable after its completed native read and before a final runtime response')
    actor.command('cancel')
    actor.until(lambda value: value['ui']['state'] == 'idle' and not value['ui']['can_cancel'])
    report, rows = _provider_actual_report(actor, project, 'interrupted')
    sent = [json.loads(line) for line in actor.trace.with_suffix('.sent.jsonl').read_text().splitlines()]
    ended = [row for row in sent if row.get('method') == 'turn/completed'][-1]['params']
    assert ended['turn']['status'] == 'interrupted' and ended['turn']['error'] is None, (
        'The actual Stop reaches its original supported interrupted/null-error runtime boundary')
    assert len(_session_wire(actor, 'turn/interrupt')) == 1 and len(_session_wire(actor, 'turn/start')) == 1, (
        'One real Stop sends one interrupt and never resubmits the original user work')
    assert not [row for row in rows if row.get('payload', {}).get('type') == 'providerError'], (
        'A successful interruption with no supplied provider error must not fabricate a failed provider-error observation')
    assert actor.responses() == [before] and call['call_id'] in json.dumps(report), (
        'Stop preserves the exact already-completed original native receipt and factual partial history once')


@pytest.mark.parametrize('status', ['completed', 'interrupted', 'failed'])
@pytest.mark.parametrize('presence', ['absent', 'null', 'actual'])
def test_runtime_terminal_preserves_supplied_error_truth_and_original_native_owner(main_actor, tmp_path, status, presence):
    message = 'Original supplied public runtime failure explanation.'
    secret = 'PRIVATE-ADDITIONAL-DETAILS-MUST-NOT-BE-PUBLISHED'
    terminal = {'status': status, 'error_presence': presence}
    if presence == 'actual':
        terminal['error'] = {'message': message, 'codexErrorInfo': 'rateLimitExceeded',
            'additionalDetails': secret, 'misalignment': None}
    actor, project, call = _provider_read_then_terminal(main_actor, tmp_path, terminal)
    actor.until(lambda value: value['ui']['state'] == 'idle' and not value['ui']['can_cancel'])
    report, rows = _provider_actual_report(actor, project, status)
    provider = [row for row in rows if row.get('payload', {}).get('type') == 'providerError']
    if presence == 'actual':
        assert any(row['payload'].get('message') == message for row in provider), (
            'An actual supplied public error remains observable even on completed or interrupted terminals')
    elif status != 'failed':
        assert not provider, (
            'Absent or null optional error on completed/interrupted work is terminal metadata, not an invented provider failure')
    else:
        assert not any(row['payload'].get('message') for row in provider), (
            'A failed turn without an explanation must remain explicitly unknown rather than invent an observed public message')
    assert secret not in json.dumps(report), (
        'Private additionalDetails are not an allowed public error explanation or report payload')
    assert len(actor.responses()) == 1 and len(_session_wire(actor, 'turn/start')) == 1 \
        and call['call_id'] in json.dumps(report), (
            'Terminal diagnostic publication neither replays the user input nor loses or mutates its completed native result')
    ended = [row for row in map(json.loads, actor.trace.with_suffix('.sent.jsonl').read_text().splitlines())
        if row.get('method') == 'turn/completed'][-1]['params']['turn']
    assert ('error' in ended) == (presence != 'absent'), (
        'The absent compatibility input is distinguished from the pinned normal explicit-null serialization')


@pytest.mark.parametrize('will_retry', [False, True])
def test_actual_error_notification_keeps_retry_and_native_facts_without_client_replay(main_actor, tmp_path, will_retry):
    message = 'Original runtime notification before its terminal boundary.'
    terminal = {'status': 'completed' if will_retry else 'failed', 'error_presence': 'null',
        'notification': {'error': {'message': message, 'codexErrorInfo': 'serverOverloaded',
            'additionalDetails': None, 'misalignment': None}, 'willRetry': will_retry, 'duplicate': True}}
    actor, project, call = _provider_read_then_terminal(main_actor, tmp_path, terminal)
    actor.until(lambda value: value['ui']['state'] == 'idle' and not value['ui']['can_cancel'])
    report, rows = _provider_actual_report(actor, project, terminal['status'])
    observed = [row for row in rows if row.get('payload', {}).get('type') == 'providerError'
        and row['payload'].get('source') == 'notification' and row['payload'].get('message') == message]
    assert len(observed) == 1 and observed[0]['payload']['willRetry'] is will_retry, (
        'Duplicate identical actual notifications retain their original factual retry decision once')
    assert len(_session_wire(actor, 'turn/start')) == 1 and len(actor.responses()) == 1 \
        and call['call_id'] in json.dumps(report), (
            'Provider retry metadata does not authorize any client input/native replay')


@pytest.mark.parametrize('email', [None, ''])
def test_nullable_current_account_metadata_is_not_proof_of_change_or_new_admission(main_actor, email):
    actor = main_actor([[], []]);_session_configure(actor,
        session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    actor.connect();_session_request_with_original_disclosure(actor, 'First actual input under a proved managed account.')
    _session_completed(actor, 1)
    original = _session_state(actor)['inputs'][0]
    before = len(_session_wire(actor, 'account/read'))
    _session_configure(actor, fixture_account_read_reply={'account': {'type': 'chatgpt',
        'email': email, 'planType': 'plus'}, 'requiresOpenaiAuth': False},
        fixture_usage_notification_generation=1,
        fixture_usage_notifications=[{'method': 'account/updated', 'params': {'authMode': 'chatgpt', 'planType': None}}])
    actor.command('refresh_usage')
    actor.until(lambda _value: len(_session_wire(actor, 'account/read')) > before)
    identity_expression = '(JSON.parse(Session.assistant.workReportDocument()).scope_coverage.current_session_browser.account_check || {}).same_identity'
    actor.until(lambda _value: qml(actor, identity_expression) == 'unknown')
    pending_text = 'Second explicit input after actual unchanged nonempty identity proof.'
    qml(actor, 'Session.assistant.send(' + json.dumps(pending_text) + ')')
    actor.command('inspect')
    assert len(_session_state(actor)['inputs']) == 1 and len(_session_wire(actor, 'turn/start')) == 1, (
        'Nullable/empty optional account metadata is not authority to start or replay user work')
    retained = actor.last['ui']['messages']
    assert any(row.get('kind') == 'user' and 'First actual input' in row.get('text', '') for row in retained), (
        'Unavailable current identity proof must not erase original accepted current history')
    _session_configure(actor, fixture_account_read_reply={'account': {'type': 'chatgpt',
        'email': 'integration@example.invalid', 'planType': 'plus'}, 'requiresOpenaiAuth': False},
        fixture_usage_notification_generation=2,
        fixture_usage_notifications=[{'method': 'account/updated', 'params': {'authMode': 'chatgpt', 'planType': None}}])
    actor.command('refresh_usage')
    actor.until(lambda _value: qml(actor, identity_expression) is True)
    # Do not resubmit the attempted input: whether a blocked draft is retained
    # or refused is a separate public contract. Read-only Refresh reaches the
    # restored account authority without an uncertain second turn/start.
    boundary = len(_session_wire(actor, 'thread/list'))
    qml(actor, 'Session.assistant.refreshSessions()');_session_wait(actor)
    actor.until(lambda _value: len(_session_wire(actor, 'thread/list')) > boundary)
    inputs = _session_state(actor)['inputs']
    assert len(inputs) <= 2 and inputs[0] == original and all(
        row['threadId'] == original['threadId'] and pending_text in str(row['input'])
        for row in inputs[1:]), (
        'Restored identity cannot replay accepted old input, duplicate the blocked new input, or silently switch its conversation')
    (actor.folder / 'nullable-current-account-boundary.json').write_text(json.dumps({
        'supplied_optional_email': email, 'original_input': original, 'actual_inputs': inputs,
        'actual_account_reads': _session_wire(actor, 'account/read')}, indent=2))


@pytest.mark.parametrize('status', ['completed', 'interrupted', 'failed'])
@pytest.mark.parametrize('invalid_error', ['NOT-A-TURN-ERROR', {'message': 17, 'codexErrorInfo': None}])
def test_wrong_typed_terminal_error_stays_unknown_not_a_supplied_public_message(main_actor, tmp_path, status, invalid_error):
    # Explicit parser-negative inputs. Pinned normal runtime uses TurnError|null;
    # these never count as positive stock-runtime serialization proof.
    terminal = {'status': status, 'error_presence': 'malformed', 'error': invalid_error}
    actor, project, call = _provider_read_then_terminal(main_actor, tmp_path, terminal)
    actor.until(lambda value: value['ui']['state'] == 'idle' and not value['ui']['can_cancel'])
    report, rows = _provider_actual_report(actor, project)
    provider = [row for row in rows if row.get('payload', {}).get('type') == 'providerError']
    assert not any(row['payload'].get('message') for row in provider), (
        'A wrong-typed optional terminal field is not evidence of an actual supplied public provider message')
    assert any(row.get('error_presence') == 'invalid' or row.get('message_presence') == 'invalid'
        or isinstance(row.get('event_failure'), dict) for row in objects(report)), (
        'Wrong-typed terminal input retains an explicit invalid/processing diagnostic rather than silently becoming a usable provider error')
    assert 'NOT-A-TURN-ERROR' not in json.dumps(report), (
        'Malformed raw terminal values cannot become user-facing error explanations or public diagnostic payloads')
    assert len(actor.responses()) == 1 and len(_session_wire(actor, 'turn/start')) == 1 \
        and call['call_id'] in json.dumps(report), (
            'A malformed terminal diagnostic never erases or repeats the completed original native read')
    (actor.folder / 'parser-negative-terminal-classification.json').write_text(json.dumps({
        'classification': 'EXPLICIT_NEGATIVE_NOT_PINNED_VALID', 'terminal_status': status,
        'supplied_error': invalid_error, 'observed_provider_rows': provider,
        'actual_ui_state': actor.last['ui']['state'], 'actual_native_responses': actor.responses()}, indent=2))


# Independently authored original-owner gate packet: reset_pending_attachments_private_gates.py
# PRIVATE AUTHORED / UNRUN. Hd85e919d0: FIRST toolbar Reset/afterChanges,
# immutable pending input owners and real standard Save/Discard/Cancel controls.
# No assumption that old project approval transfers to the no-project successor.

@pytest.mark.parametrize('outcome', ['save', 'discard', 'cancel'])
@pytest.mark.parametrize('draft_kind', ['connected_mixed', 'connected_file_only', 'disconnected_file_only'])
def test_original_reset_preserves_only_genuine_pending_draft_inputs_and_rejects_late_picker(main_actor, tmp_path, outcome, draft_kind):
    actor = main_actor([[]]);project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'Reset begins with its genuine ordinary current saved project')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    files = _attachment_fixtures(tmp_path, 3)
    consumed = None
    if draft_kind != 'disconnected_file_only':
        actor.connect()
    if draft_kind == 'connected_mixed':
        _session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
        token = actor.begin_current_file_selection()
        assert actor.command('selected_add', token=token, paths=[str(files[0])])['reply']['added'], (
            'The consumed prefix is an actual first admitted input, not a hand-written history row')
        consumed = _attachment_rows(actor)[0]['id']
        _session_request_with_original_disclosure(actor, 'Keep this accepted original input in its original task history.')
        _session_completed(actor, 1)
        assert not any(row['id'] == consumed and row['pending'] for row in _attachment_rows(actor)), (
            'The original file was genuinely consumed before the new pending draft is composed')
    token = qml(actor, 'Session.assistant.beginFileSelection(' + ('false' if draft_kind == 'disconnected_file_only' else 'true') + ')')
    assert token and actor.command('selected_add', token=token, paths=[str(files[1])])['reply']['added'], (
        'The pending file is admitted by the actual original selected-input owner, even for disconnected composition')
    pending = [row for row in _attachment_rows(actor) if row['pending']]
    assert len(pending) == 1 and pending[0]['name'] == files[1].name, (
        'Exactly the newly chosen unsent file belongs to this actual pending draft')
    text = 'Keep this exact unsent mixed draft.' if draft_kind == 'connected_mixed' else ''
    editor = _scene_control_expression('assistant.composer')
    if text:
        actor.command('click', name='assistant.composer');actor.command('manual_text', text=text)
    assert qml(actor, '(' + editor + ').text') == text, (
        'The real composer owns the exact literal file-only or mixed draft before Reset')
    late = qml(actor, 'Session.assistant.beginFileSelection(' + ('false' if draft_kind == 'disconnected_file_only' else 'true') + ')')
    assert late, 'A real outstanding picker token exists before the original project reset intent'
    hashes = {str(path): {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'dev': path.stat().st_dev, 'ino': path.stat().st_ino} for path in files}
    source_before = (project / 'project.edi').read_bytes()
    description = 'A genuine unsaved ordinary edit before the original Reset choice.'
    qml(actor, 'Session.project.description=' + json.dumps(description))
    assert qml(actor, 'Session.project.modified'), 'The ordinary Reset really has an unsaved current owner requiring its normal choice'
    start_count = len(_session_wire(actor, 'turn/start'))
    actor.command('click', name='appBar.button.reset')
    actor.until(lambda _value: qml(actor, 'typeof unsavedChanges!=="undefined"&&unsavedChanges.opened'
        '&&unsavedChanges.visible&&!!unsavedChanges.contentItem&&unsavedChanges.contentItem.Window.window===window'))
    chosen = actor.command('dialog_ok', name='unsavedChanges', role=outcome)['reply']
    assert chosen['pressed_changes'] > 0 and chosen['role'] == outcome, (
        'The original standard Save/Discard/Cancel button receives genuine current-window input; no direct closeProject bypass qualifies')
    if outcome == 'cancel':
        actor.until(lambda value: value['ui']['project'] and value['ui']['project']['path'] == str(project))
        assert qml(actor, 'Session.project.modified') and (project / 'project.edi').read_bytes() == source_before, (
            'Cancelling Reset preserves the modified original project and its last saved bytes')
    else:
        actor.until(lambda value: not value['ui']['project'])
        if outcome == 'save':
            assert description in (project / 'project.edi').read_text(), (
                'The actual standard Save choice preserves the original ordinary metadata edit before close')
        else:
            assert (project / 'project.edi').read_bytes() == source_before, (
                'The actual standard Discard choice closes without silently writing the unsaved original edit')
    after = _attachment_rows(actor)
    assert [row for row in after if row['pending']] == pending and qml(actor, '(' + editor + ').text') == text, (
        'Accepted Reset and cancellation retain the same genuine pending descriptors and exact draft text without synthesizing input')
    if consumed:
        assert not any(row['id'] == consumed and row['pending'] for row in after), (
            'An accepted history attachment is never revived as a fresh pending input by Reset')
    if outcome != 'cancel':
        before_late = json.loads(json.dumps(after))
        assert actor.command('selected_add', token=late, paths=[str(files[2])])['reply']['added'] is False, (
            'A retired original picker callback cannot add files under the reset successor project context')
        assert _attachment_rows(actor) == before_late, (
            'Refusing a late picker callback preserves the current actual pending draft unchanged')
    assert len(_session_wire(actor, 'turn/start')) == start_count, (
        'Reset choices, draft retention and late chooser cleanup never submit or replay a provider task')
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == entry['sha256']
        and Path(path).stat().st_dev == entry['dev'] and Path(path).stat().st_ino == entry['ino']
        for path, entry in hashes.items()), (
        'Draft retention keeps the original physical admitted inputs rather than replacing them with copied scientific files')
    (actor.folder / 'ordinary-reset-pending-input-boundary.json').write_text(json.dumps({
        'choice': outcome, 'draft_kind': draft_kind, 'before_pending': pending, 'after': after,
        'original_consumed_id': consumed, 'source_input_identities': hashes,
        'actual_project_after': actor.last['ui']['project'], 'ordinary_button_receipt': chosen}, indent=2))


@pytest.mark.parametrize('retirement', ['awaiting_ack', 'lost_transport'])
def test_original_reset_does_not_revive_wire_admitted_or_uncertain_ack_files_as_new_pending(main_actor, tmp_path, retirement):
    # Negative counterpart to genuinely-pending Reset. The client request is
    # actually received; only its original RPC reply is held or lost. A visible
    # pending history status is not proof that this input was never written.
    actor = main_actor([[]]);project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'Admitted-input Reset uses its actual ordinary saved project and original owner')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    release = actor.folder / 'release-original-before-reset-start-ack'
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12},
        observe_context_continuity=True, fixture_unacked_start_hold=str(release))
    actor.connect();source = _attachment_fixtures(tmp_path, 1)[0]
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], (
        'The original outgoing file was genuinely admitted through the existing immutable file owner')
    first_file = [row for row in _attachment_rows(actor) if row['pending']]
    saved = {str(path.relative_to(project)): path.read_bytes() for path in project.rglob('*.edi')}
    _session_request_with_original_disclosure(actor, 'This actually written original read-only input is not a fresh draft after Reset.')
    actor.until(lambda _value: len(_session_wire(actor, 'turn/start')) == 1
        and len(_session_state(actor).get('actual_unacked_requests', [])) == 1)
    original = _session_wire(actor, 'turn/start')[0]
    accepted = _session_state(actor)['actual_unacked_requests'][0]
    emitted = [json.loads(line) for line in actor.trace.with_suffix('.sent.jsonl').read_text().splitlines()]
    assert accepted == original and not any(row.get('id') == original['id'] and ('result' in row or 'error' in row) for row in emitted), (
        'The original request is genuinely on the runtime wire while its own acknowledgement remains unobserved')
    before = json.loads(json.dumps(_attachment_rows(actor)))
    fault = None
    try:
        if retirement == 'lost_transport':
            fault = actor.command('close_owned_transport_write')['reply']
            assert fault['original_vm_child'] and fault['public_close_write_channel_invoked'], (
                'Only the proved original fixture-owned helper loses its unacknowledged transport; no provider or global process is touched')
            actor.until(lambda value: not value['ui']['connected'])
        actor.command('clear_ui_sequence');actor.command('click', name='appBar.button.reset')
        actor.until(lambda value: not value['ui']['project'])
        after = _attachment_rows(actor)
        assert not any(row['pending'] for row in after), (
            'Reset cannot reintroduce an actually wire-admitted or delivery-uncertain attachment as a new pending file merely because its history row was not completed')
        assert _session_wire(actor, 'turn/start') == [original], (
            'Reset and actual original-helper retirement never replay the uncertain original request into a no-project successor')
        assert {str(path.relative_to(project)): path.read_bytes() for path in project.rglob('*.edi')} == saved, (
            'Retiring an admitted read-only task does not mutate the original saved scientific project')
        (actor.folder / 'reset-actual-admitted-input-negative.json').write_text(json.dumps({
            'retirement': retirement, 'actual_original_request': original, 'actual_server_received': accepted,
            'original_response_absent_at_boundary': True, 'original_file_descriptors': first_file,
            'actual_before_reset': before, 'actual_after_reset': after, 'actual_owned_transport_fault': fault,
            'actual_ui_sequence': actor.last['ui']['ui_sequence'],
            'classification': 'WIRE_ADMITTED_UNACKNOWLEDGED_NOT_GENUINELY_UNSENT; no completed-provider/native-outcome claim'}, indent=2))
    finally:
        release.touch()


# Independently authored original-owner gate packet: single_approval_admission_private_gates.py
# PRIVATE / UNRUN. Hda0eda0c6 class: volatile presentation-clock bytes must not
# consume the original draft or require a second Send after genuine approval.

@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_one_actual_send_and_visible_share_after_real_clock_crossing_admits_original_input_once(main_actor, tmp_path, show_actions):
    actor = main_actor([[]], show_actions=show_actions)
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    actor.connect();source = _attachment_fixtures(tmp_path, 1)[0]
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], (
        'The new draft has a genuine immutable user-selected file and actual original chooser owner')
    pending = [row for row in _attachment_rows(actor) if row['pending']]
    assert len(pending) == 1 and pending[0]['name'] == source.name, (
        'Approval begins with one actual pending attachment rather than a planted context or seeded receipt')
    text = 'Use this original attached input for the current read-only task.'
    source_bytes = source.read_bytes();source_inode = (source.stat().st_dev, source.stat().st_ino)
    before_inputs = len(_session_state(actor)['inputs'])
    actor.command('send_text', text=text)
    actor.until(lambda value: any(row['name'] == 'AssistantConnectionDialog' and row['fully_exposed']
        for row in value['ui']['controls']))
    assert len(_session_state(actor)['inputs']) == before_inputs, (
        'The actual first Send reaches its original sharing dialog before any provider input is admitted')
    original_preview = qml(actor, 'Session.assistant.contextPreview')
    marker = 'e11.original-approval-clock-boundary'
    timer_source = ('import QtQuick; Item {id:clockBoundary;objectName:"' + marker + '"; '
        'property double startSecond: Math.floor(Date.now()/1000); property double endSecond: startSecond; '
        'property bool crossed:false; Timer {interval:20;repeat:true;running:true; '
        'onTriggered:{clockBoundary.endSecond=Math.floor(Date.now()/1000);if(clockBoundary.endSecond>clockBoundary.startSecond){clockBoundary.crossed=true;stop();}}}}')
    assert qml(actor, '(function(){const item=Qt.createQmlObject(' + json.dumps(timer_source)
        + ',window.contentItem);return item!==null;})()'), (
        'The fixture observes a real Qt clock transition without changing the app clock or approval state')
    watched = _scene_control_expression(marker)
    actor.until(lambda _value: qml(actor, '(' + watched + ').crossed'))
    clock = qml(actor, '(function(){const o=' + watched
        + ';return {start:o.startSecond,end:o.endSecond,crossed:o.crossed};})()')
    assert clock['crossed'] and clock['end'] > clock['start'], (
        'Approval genuinely occurs after a real second boundary; no arbitrary delay substitutes for reaching the volatile-clock escape')
    current_preview = qml(actor, 'Session.assistant.contextPreview')
    delivery = actor.command('dialog_ok', name='AssistantConnectionDialog', role='ok')['reply']
    assert delivery['pressed_changes'] > 0 and delivery['actual_dialog_name'] == 'AssistantConnectionDialog', (
        'One physical click reaches the original currently exposed Share project information standard button')
    _session_completed(actor, before_inputs + 1)
    inputs = _session_state(actor)['inputs']
    assert len(_session_wire(actor, 'turn/start')) == before_inputs + 1 and text in str(inputs[-1]['input']), (
        'The original captured draft is admitted exactly once after approval without a second Send or fabricated placeholder text')
    assert not any(row['pending'] and row['id'] == pending[0]['id'] for row in _attachment_rows(actor)), (
        'Only actual admission consumes the original pending attachment')
    editor = _scene_control_expression('assistant.composer')
    assert qml(actor, '(' + editor + ').text') == '', (
        'The admitted original text clears once instead of leaving an apparently unsent draft requiring resubmission')
    assert source.read_bytes() == source_bytes and (source.stat().st_dev, source.stat().st_ino) == source_inode, (
        'The accepted input remains the original immutable physical file throughout sharing and admission')
    (actor.folder / 'single-send-after-real-clock-approval.json').write_text(json.dumps({
        'actual_clock': clock, 'original_preview': original_preview, 'preview_at_approval': current_preview,
        'physical_approval': delivery, 'original_pending': pending, 'actual_inputs': inputs,
        'send_count': 1, 'approval_count': 1, 'source_sha256': hashlib.sha256(source_bytes).hexdigest()}, indent=2))


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_one_send_share_waits_for_real_same_account_readiness_without_losing_original_draft(main_actor, tmp_path, show_actions):
    # The original user clicks Send and Share once. A held genuine correlated
    # account/read is a proved prewire wait, not an uncertain turn admission.
    actor = main_actor([[]], show_actions=show_actions)
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    actor.connect();source = _attachment_fixtures(tmp_path, 1)[0]
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], (
        'Waiting admission owns a genuinely selected original input and its immutable descriptor')
    pending = [row for row in _attachment_rows(actor) if row['pending']]
    text = 'Continue this exact original attached read-only task after sharing approval.'
    account = qml(actor, 'Session.assistant.account')
    actor.command('send_text', text=text)
    actor.until(lambda value: any(row['name'] == 'AssistantConnectionDialog' and row['fully_exposed']
        for row in value['ui']['controls']))
    marker = 'e11.original-send-actual-readiness'
    watch_source = ('import QtQuick; Item {id:witness;objectName:"' + marker + '";'
        'property var events:[];property int readinessChanges:0;property double startSecond:Math.floor(Date.now()/1000);'
        'property double endSecond:startSecond;property bool crossed:false;'
        'Timer {interval:20;running:true;repeat:true;onTriggered:{witness.endSecond=Math.floor(Date.now()/1000);'
        'if(witness.endSecond>witness.startSecond){witness.crossed=true;stop();}}}}')
    assert qml(actor, '(function(){const vm=Session.assistant,o=Qt.createQmlObject(' + json.dumps(watch_source)
        + ',window.contentItem);vm.draftAdmissionReadyChanged.connect(function(){if(Qt.isQtObject(o)&&Session.assistant===vm){'
        'o.readinessChanges++;o.events.push({ready:vm.draftAdmissionReady,connected:vm.connected,state:vm.state});}});return true;})()'), (
        'A read-only witness observes the actual original public readiness signal and Qt clock, without inventing admission status')
    release = actor.folder / 'release-original-send-account-read'
    try:
        request = _review66_hold_original_identity(actor, release)
        actor.until(lambda _value: not qml(actor, 'Session.assistant.draftAdmissionReady'))
        assert qml(actor, 'Session.assistant.connected') and qml(actor, 'Session.assistant.account') == account, (
            'The actual supported account verification is pending while the original same-account connection remains viable')
        watcher = _scene_control_expression(marker)
        actor.until(lambda _value: qml(actor, '(' + watcher + ').crossed'))
        delivery = actor.command('dialog_ok', name='AssistantConnectionDialog', role='ok')['reply']
        assert delivery['pressed_changes'] > 0 and delivery['actual_dialog_name'] == 'AssistantConnectionDialog', (
            'The user shares once through the original exposed standard button while real prewire readiness remains pending')
        # Pump through the existing actual command/event loop; no resubmission.
        actor.command('inspect')
        assert not _session_wire(actor, 'turn/start') and not _session_state(actor)['inputs'], (
            'Before the captured account reply is released, approval must not admit the original user input on unproved authority')
        editor = _scene_control_expression('assistant.composer')
        assert qml(actor, '(' + editor + ').text') == text \
            and [row for row in _attachment_rows(actor) if row['pending']] == pending, (
            'A proved waiting admission keeps the exact original text and genuinely pending input instead of clearing them early')
        release.touch();actor.command('refresh_usage')
        _session_completed(actor, 1)
        actual = _session_state(actor)['inputs']
        assert len(_session_wire(actor, 'turn/start')) == 1 and len(actual) == 1 and text in str(actual[0]['input']), (
            'The actual unchanged-account readiness wake admits the originally approved draft once, with no second Send or artificial input')
        observed = qml(actor, '(function(){const o=' + watcher + ';return {events:o.events,changes:o.readinessChanges,'
            'start:o.startSecond,end:o.endSecond,crossed:o.crossed};})()')
        assert observed['changes'] > 0 and any(row['ready'] for row in observed['events']) \
            and observed['crossed'] and observed['end'] > observed['start'], (
            'The test genuinely reaches a public readiness transition after a real clock crossing, not merely an idle UI observation')
        assert qml(actor, '(' + editor + ').text') == '' \
            and not any(row['pending'] and row['id'] == pending[0]['id'] for row in _attachment_rows(actor)), (
            'Only the actual admitted original input consumes its original draft text and pending attachment')
        sent = [json.loads(line) for line in actor.trace.with_suffix('.sent.jsonl').read_text().splitlines()]
        reply = [row for row in sent if row.get('id') == request['id'] and 'result' in row]
        assert len(reply) == 1 and reply[0]['result']['account']['email'] == 'integration@example.invalid', (
            'The readiness transition belongs to the original genuinely received unchanged nonempty account proof, never a fabricated success')
        (actor.folder / 'one-send-share-actual-prewire-wait.json').write_text(json.dumps({
            'original_held_account_request': request, 'actual_correlated_reply': reply,
            'actual_signal_and_clock_observations': observed, 'actual_approval': delivery,
            'original_pending_files': pending, 'actual_inputs': actual, 'send_count': 1,
            'share_count': 1, 'classification': 'ACTUAL_PREWIRE_WAIT_THEN_READINESS_NOT_UNCERTAIN_WRITE'}, indent=2))
    finally:
        release.touch()


def test_uncertain_original_send_write_does_not_auto_replay_on_actual_same_owner_readiness(main_actor, tmp_path):
    # The opt-in existing probe fault reaches the actual pending-row publication
    # inside original admission, before its transport write. It does not return
    # a fake admission map or preemptively turn the owner disconnected.
    actor = main_actor([[]]);_session_configure(actor,
        session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    actor.connect();source = _attachment_fixtures(tmp_path, 1)[0]
    original_account = qml(actor, 'Session.assistant.account')
    original_vm = qml(actor, 'String(Session.assistant)')
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], (
        'Uncertain admission begins with a real pending original input and disclosure owner')
    pending = [row for row in _attachment_rows(actor) if row['pending']]
    text = 'This original draft must not be replayed after an uncertain transport write.'
    actor.command('send_text', text=text)
    actor.until(lambda value: any(row['name'] == 'AssistantConnectionDialog' and row['fully_exposed']
        for row in value['ui']['controls']))
    armed = actor.command('arm_pending_send_write_fault', text=text)['reply']
    assert armed['armed'] and armed['original_vm'] and armed['original_message_model'], (
        'The one-shot fault is armed on the actual original connected ready model before the original approval')
    approval = actor.command('dialog_ok', name='AssistantConnectionDialog', role='ok')['reply']
    assert approval['pressed_changes'] > 0, 'One real original Share click precedes the reached uncertain admission boundary'
    actor.until(lambda _value: actor.command('session_fault_facts')['reply'].get('pending_user_row_inserted'))
    facts = actor.command('session_fault_facts')['reply']
    assert facts['pending_user_row_id'] and facts['original_vm_before'] and facts['original_message_model_before'] \
        and facts.get('original_vm_child') and facts.get('public_close_write_channel_invoked') \
        and not facts.get('pending_send_fault_error'), (
        'The actual matching pending user row synchronously reaches the already-proved same-owned-child public write-channel close')
    actor.until(lambda _value: actor.command('session_fault_facts')['reply'].get('actual_transport_failed_signal'))
    facts = actor.command('session_fault_facts')['reply']
    assert facts['actual_transport_error'], (
        'A real transport failure is observed; merely arming a callback or disconnecting before admission is not a reached uncertain-write witness')
    before_reconnect = json.loads(json.dumps(_session_wire(actor, 'turn/start')))
    editor = _scene_control_expression('assistant.composer')
    assert qml(actor, '(' + editor + ').text') == text \
        and [row for row in _attachment_rows(actor) if row['pending']] == pending, (
        'An unconfirmed write cannot acknowledge/clear the original unsent draft as if real admission had completed')
    # Ordinary sign-in/reconnect is explicit; no second Send or second Share.
    # If actual normal readiness cannot be reached, classify this channel as
    # unreached instead of approving context or fabricating a replacement ID.
    actor.command('sign_in')
    actor.until(lambda value: value['ui']['connected'] and qml(actor, 'Session.assistant.draftAdmissionReady'))
    assert qml(actor, 'Session.assistant.account') == original_account and qml(actor, 'String(Session.assistant)') == original_vm, (
        'The no-replay boundary reaches actual readiness on the same original current account/window VM rather than a substituted fixture owner')
    boundary = len(_session_wire(actor, 'thread/list'))
    qml(actor, 'Session.assistant.refreshSessions()')
    actor.until(lambda _value: len(_session_wire(actor, 'thread/list')) > boundary)
    _session_wait(actor)
    barrier = 'e11.uncertain-send-real-ready-loop'
    tick = ('import QtQuick; Item {id:owner;objectName:"' + barrier + '";property bool done:false;'
        'Timer {interval:0;running:true;onTriggered:Qt.callLater(function(){owner.done=true;})}}')
    assert qml(actor, '(function(){return Qt.createQmlObject(' + json.dumps(tick) + ',window.contentItem)!==null;})()'), (
        'The post-readiness witness uses a real owned Qt event-loop turn, not an inflated sleep or a second submission')
    actor.until(lambda _value: qml(actor, '(' + _scene_control_expression(barrier) + ').done'))
    assert _session_wire(actor, 'turn/start') == before_reconnect, (
        'Actual same-owner readiness must not replay an old unconfirmed input after its uncertain original write')
    assert qml(actor, '(' + editor + ').text') == text \
        and [row for row in _attachment_rows(actor) if row['pending']] == pending, (
        'The refused automatic replay leaves the original draft available for a genuinely new explicit user decision')
    (actor.folder / 'uncertain-original-send-no-replay.json').write_text(json.dumps({
        'original_pending_row': facts['pending_user_row_id'], 'actual_owned_fault': facts,
        'actual_original_approval': approval, 'actual_turn_requests_before_readiness': before_reconnect,
        'actual_turn_requests_after_readiness': _session_wire(actor, 'turn/start'),
        'send_count': 1, 'share_count': 1, 'actual_ready': actor.last['ui']['connected'],
        'typed_return': 'NOT_DIRECTLY_INTERCEPTED; source-qualified original request/write failure, no fabricated return',
        'scope': 'Reached original pending-row write fault and actual later readiness; not a real-provider/server delivery guarantee'}, indent=2))


# Independently authored original-owner gate packet: visible_offered_choice_private_gates.py
# PRIVATE / UNRUN: He496132d6 actual offered-list selection, original controls.
# Read-only signal witnesses do not create delegates, change popup/scroll state,
# set currentIndex, focus a field or dispatch a replacement scientific mutation.

def _watch_original_offered_choices(actor, marker):
    observer = r'''(function(){
        const original=Session.project,vm=Session.assistant;
        const probe=Qt.createQmlObject('import QtQuick; Item {id:choiceProbe;property var facts:[];property var combos:[];property var rows:[];property var lastPointer:null;property bool finished:false;property var scan:null;Timer {interval:16;repeat:true;running:!choiceProbe.finished;onTriggered:if(choiceProbe.scan)choiceProbe.scan();}}',window.contentItem);
        probe.objectName=MARKER;
        function current(){return Session.project===original&&Session.assistant===vm;}
        function rect(item){const p=item.mapToItem(null,0,0);return {x:p.x,y:p.y,width:item.width,height:item.height};}
        function visible(item){if(!item||item.Window.window!==window||!item.visible||!item.enabled||item.width<=0||item.height<=0)return false;
            const b=rect(item);let clip={x:0,y:0,right:window.width,bottom:window.height};
            for(let p=item;p;p=p.parent){if(!p.visible||p.opacity===0)return false;if(p.clip){const r=rect(p);clip.x=Math.max(clip.x,r.x);clip.y=Math.max(clip.y,r.y);clip.right=Math.min(clip.right,r.x+r.width);clip.bottom=Math.min(clip.bottom,r.y+r.height);}}
            return b.x>=clip.x&&b.y>=clip.y&&b.x+b.width<=clip.right&&b.y+b.height<=clip.bottom;}
        function snap(kind,box,row,index){const p=box.popup;return {kind:kind,control:box.objectName,controlObject:String(box),popupObject:String(p),
            popupOpened:p.opened,popupVisible:p.visible,popupWindow:String(p.contentItem?p.contentItem.Window.window:null),sameWindow:box.Window.window===window,
            rowObject:row?String(row):null,rowText:row&&typeof row.text==='string'?row.text:null,index:index,
            offered:index>=0&&index<box.count?box.textAt(index):null,searchText:box.searchText,
            rowVisible:row?visible(row):false,rowBounds:row?rect(row):null,pointer:probe.lastPointer,ownerCurrent:current()};}
        vm.actionPointerMoved.connect(function(position){if(current())probe.lastPointer={x:position.x,y:position.y};});
        function bindRow(box,row){if(probe.rows.indexOf(row)>=0||!row.pressedChanged||!row.clicked)return;
            probe.rows.push(row);row.pressedChanged.connect(function(){if(current()&&Qt.isQtObject(box)&&Qt.isQtObject(row)&&row.pressed){const index=typeof row.index==='number'?row.index:box.find(row.text);probe.facts.push(snap('real_delegate_pressed',box,row,index));}});}
        function bind(box){if(probe.combos.indexOf(box)>=0||!box.popup||!box.activated)return;
            probe.combos.push(box);box.popup.visibleChanged.connect(function(){if(current()&&box.popup.visible)probe.facts.push(snap('original_popup_visible',box,null,-1));});
            box.activated.connect(function(index){if(current())probe.facts.push(snap('original_choice_activated',box,null,index));});
            box.popup.closed.connect(function(){if(current())probe.facts.push(snap('original_popup_closed',box,null,-1));});}
        probe.scan=function(){if(!current()||probe.finished)return;
            const stack=[window.contentItem];while(stack.length){const item=stack.pop();
                if(item.objectName==='parameters.category'||String(item.objectName).startsWith('alias.parameter.'))bind(item);
                const kids=item.children;for(let i=0;i<kids.length;i++)if(kids[i].parent===item)stack.push(kids[i]);}
            for(let k=0;k<probe.combos.length;k++){const box=probe.combos[k];if(!Qt.isQtObject(box))continue;const popup=box.popup;if(!Qt.isQtObject(popup))continue;const list=popup.contentItem;
                if(!popup.visible||!Qt.isQtObject(list))continue;const root=list.contentItem||list;const rows=root.children;
                for(let i=0;i<rows.length;i++)if(rows[i].parent===root)bindRow(box,rows[i]);}};
        probe.scan();return true;
    })()'''.replace('MARKER', json.dumps(marker))
    assert qml(actor, observer), 'Read-only witnesses bind only genuine original offered selectors in the actual current Main window'


def test_show_on_alias_search_physically_chooses_actual_offered_row_once(main_actor, tmp_path):
    actor = main_actor([[]], show_actions=True);project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'Visible offered choices begin with a genuine ordinary project and its original Analysis owners')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    if any(row['name'] == 'home.start' and row['visible'] and row['enabled'] for row in actor.last['ui']['controls']):
        actor.command('click', name='home.start')
    actor.until(lambda value: any(row['name'] == 'appBar.tab.analysis' and row['enabled'] and row['fully_exposed']
        for row in value['ui']['controls']))
    actor.command('click', name='appBar.tab.analysis')
    actor.until(lambda value: any(row['name'] == 'parameters.category' and row['visible']
        for row in value['ui']['controls']))
    original = json.loads(json.dumps(actor.last['ui']['project']))
    reference_before, expected_aliases, parameter, ordinary_unique_name, ordinary_default_alias, ordinary_undo_states = \
        _ordinary_changed_alias_reference(actor, 'visible_original_cell')
    assert reference_before['aliases'] == original['aliases'] and reference_before['parameters'] == original['parameters'], (
        'The actual ordinary reference begins at the unchanged original science and chooses a genuinely different offered parameter')
    marker = 'e11.original-visible-offered-choice'
    _watch_original_offered_choices(actor, marker)
    call = {'tool': 'add_relations', 'call_id': 'original-visible-search-choice',
        'arguments': {'purpose': 'Create one alias for the exact actually offered original parameter.',
            'aliases': [{'id': 'visible_original_cell', 'path': parameter['path']}], 'constraints': []}}
    actor.configure_turns([[call]]);actor.connect();_session_request_with_original_disclosure(actor,
        'Use the exact ordinary original offered parameter for this one explicitly requested alias.')
    actor.until(lambda value: bool(actor.responses()) and value['ui']['state'] == 'idle', visible_progress=True)
    result = native_result(actor.responses()[0])
    watcher = _scene_control_expression(marker)
    qml(actor, '(' + watcher + ').finished=true')
    facts = qml(actor, '(' + watcher + ').facts')
    physical = [row for row in facts if row['kind'] == 'real_delegate_pressed'
        and row['control'].startswith('alias.parameter.')]
    assert physical, (
        'A real offered alias row must receive actual ordinary button input; popup visibility or keyboard-currentIndex alone is insufficient')
    for row in physical:
        b = row['rowBounds'];point = row['pointer']
        assert row['ownerCurrent'] and row['sameWindow'] and row['popupOpened'] and row['popupVisible'] and row['rowVisible'], (
            'The physically chosen offered row belongs to the original open popup and is fully exposed in the same current window')
        assert row['offered'] == row['rowText'] and row['searchText'] == row['offered'], (
            'The original searchable alias control contains the exact desired offered name when its actual row is chosen')
        assert point and b['x'] <= point['x'] <= b['x'] + b['width'] and b['y'] <= point['y'] <= b['y'] + b['height'], (
            'The existing assistant pointer actually reaches the visible original offered row before its physical selection')
    current = actor.last['ui']['project']
    assert current['aliases'] == expected_aliases, (
        'Visible choice creates exactly one original native alias for its requested path, stored using the FIRST ordinary offered parameter unique name')
    assert len(actor.responses()) == 1, 'The visible chooser does not repeat the scientific operation through a second backend setter'
    _match_original_alias_undo_sequence(actor, original, ordinary_undo_states, True)
    (actor.folder / 'actual-visible-offered-choice.json').write_text(json.dumps({
        'actual_call': call, 'actual_result': result, 'original_offered_parameter': parameter,
        'original_ordinary_parameter_unique_name': ordinary_unique_name,
        'ordinary_default_alias': ordinary_default_alias, 'ordinary_undo_states': ordinary_undo_states,
        'actual_original_control_events': facts}, indent=2))


def test_show_on_original_background_filter_choice_has_visible_row_pointer_and_physical_input(main_actor, tmp_path):
    actor = main_actor([[]], show_actions=True);project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'Whole-group visible choice begins with an actual ordinary saved background model')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    if any(row['name'] == 'home.start' and row['visible'] and row['enabled'] for row in actor.last['ui']['controls']):
        actor.command('click', name='home.start')
    actor.until(lambda value: any(row['name'] == 'appBar.tab.analysis' and row['enabled'] and row['fully_exposed']
        for row in value['ui']['controls']))
    actor.command('click', name='appBar.tab.analysis')
    actor.until(lambda value: any(row['name'] == 'parameters.category' and row['visible']
        for row in value['ui']['controls']))
    original = json.loads(json.dumps(actor.last['ui']['project']))
    group = [row for row in original['parameters'] if row['category'] == 'background' and row['field'] == 'intensity']
    assert group, 'The original model actually offers a nonempty background intensity group before a whole-group request'
    requested = not all(row['free'] for row in group)
    marker = 'e11.original-filter-offered-choice'
    _watch_original_offered_choices(actor, marker)
    call = {'tool': 'set_free', 'call_id': 'original-visible-whole-background-choice',
        'arguments': {'purpose': 'Change the flags of the exact currently offered whole background intensity group.',
            'values': [{'path': row['path'], 'free': requested} for row in group]}}
    actor.configure_turns([[call]]);actor.connect();_session_request_with_original_disclosure(actor,
        'Use the original offered whole background group for these explicit free flags.')
    actor.until(lambda value: bool(actor.responses()) and value['ui']['state'] == 'idle', visible_progress=True)
    result = native_result(actor.responses()[0]);watcher = _scene_control_expression(marker)
    qml(actor, '(' + watcher + ').finished=true');facts = qml(actor, '(' + watcher + ').facts')
    chosen = [row for row in facts if row['kind'] == 'real_delegate_pressed' and row['control'] == 'parameters.category']
    assert chosen, (
        'The genuinely needed original category choice must physically press its offered row rather than hide keyboard selection behind a box cue')
    for row in chosen:
        bounds = row['rowBounds'];point = row['pointer']
        assert row['ownerCurrent'] and row['sameWindow'] and row['popupOpened'] and row['popupVisible'] and row['rowVisible'] \
            and row['offered'] == row['rowText'], (
            'The actual chosen category is an offered visible original row in its own current popup')
        assert point and bounds['x'] <= point['x'] <= bounds['x'] + bounds['width'] \
            and bounds['y'] <= point['y'] <= bounds['y'] + bounds['height'], (
            'The original assistant pointer reaches the real category row before its ordinary press')
    category_events = [row for row in facts if row['control'] == 'parameters.category']
    activated = [index for index, row in enumerate(category_events) if row['kind'] == 'original_choice_activated']
    closed = [index for index, row in enumerate(category_events) if row['kind'] == 'original_popup_closed']
    assert activated and closed and activated[0] < closed[-1], (
        'The genuine selected popup reaches its original asynchronous closed signal after activation, before this native caller is accepted as settled')
    assert not category_events[closed[-1]]['popupVisible'], (
        'The actual original closed signal, rather than an immediate post-click visibility guess or a fixed sleep, establishes the popup exit boundary')
    after = {row['path']: row for row in actor.last['ui']['project']['parameters']}
    targeted = {row['path'] for row in group}
    assert all(after[row['path']]['free'] is requested for row in group), (
        'The one actual bulk choice reaches exactly the requested whole background flags')
    assert all(after[row['path']] == row for row in original['parameters'] if row['path'] not in targeted), (
        'Visible choice does not broaden the original offered group or mutate unrelated parameters')
    actor.command('undo');actor.until(lambda value: value['ui']['project']['parameters'] == original['parameters'])
    assert len(actor.responses()) == 1, 'One visible original operation remains one native result and one ordinary Undo'
    (actor.folder / 'actual-original-filter-offered-row.json').write_text(json.dumps({
        'actual_call': call, 'actual_result': result, 'actual_original_control_events': facts}, indent=2))


# Independently authored original-owner gate packet: relation_optional_purpose_private_gates.py
# PRIVATE / UNRUN. seq118 owner5c071122: purpose is optional, while a present
# value remains validated. Uses existing ordinary relation owners as reference;
# no new relation-creation oracle or example-specific relation identity.

_RELATION_PURPOSE_CASES = ['alias_rename', 'alias_target', 'alias_remove',
    'constraint_rename', 'constraint_expression', 'constraint_enabled_false',
    'constraint_enabled_true', 'constraint_remove']


def _ordinary_relation_purpose_fixture(actor, tmp_path, case):
    project = tmp_path / 'ordinary-original-relations'
    shutil.copytree(ROOT / 'tests/fixtures/constraint_expressions/project', project)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'Optional-purpose coverage opens the existing genuine ordinary relation fixture')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    initial = actor.last['ui']['project']
    canonical = {row['field']: row['path'] for row in initial['parameters']
        if row['category'] == 'cell' and row['field'] in ('length_a', 'length_b')}
    offered = qml(actor, 'Session.project.analysis.aliases.parameterNames')
    original_names = {}
    for field in canonical:
        matching = [name for name in offered if name.endswith('.cell.' + field)]
        assert len(matching) == 1, (
            'Reference relation target uses the unique actually offered original ordinary parameter name')
        original_names[field] = matching[0]
    unused = 'e11_optional_purpose_alias'
    assert unused not in {row['id'] for row in initial['aliases']}, (
        'The unused fixture alias is a new test declaration, never an assumed live example ID')
    prep = qml(actor, '(function(){const rows=Session.project.analysis.aliases;rows.append();const n=rows.count-1;'
        'const a=rows.setText(n,"id",' + json.dumps(unused) + ');'
        'return a&&rows.setText(n,"parameter",' + json.dumps(original_names['length_a']) + ');})()')
    assert prep, 'The unused alias is prepared by the original ordinary AliasListModel setters, not serialized fixture postimages'
    actor.until(lambda value: not value['ui']['project']['calculating'])
    if case == 'constraint_enabled_true':
        count = len(actor.last['ui']['project']['constraints'])
        assert count and qml(actor, 'Session.project.analysis.constraints.setEnabled(' + str(count - 1) + ',false)'), (
            'The true-enable case genuinely begins disabled through its ordinary original checkbox owner')
        actor.until(lambda value: not value['ui']['project']['calculating'])
    before = json.loads(json.dumps(actor.command('inspect')['ui']['project']))
    target = before['aliases'][-1] if case.startswith('alias_') else before['constraints'][-1]
    row = len(before['aliases']) - 1 if case.startswith('alias_') else len(before['constraints']) - 1
    operation = 'constraint_enabled' if case.startswith('constraint_enabled_') else case
    args = {'operation': operation, 'id': target['id']}
    reference = {'row': row, 'operation': operation}
    if case == 'alias_rename':
        args['value'] = unused + '_renamed';reference.update(role='id', value=args['value'])
    elif case == 'alias_target':
        args['value'] = canonical['length_b'];reference.update(role='parameter', value=original_names['length_b'])
    elif case == 'constraint_rename':
        args['value'] = 'e11_optional_purpose_constraint';reference.update(role='id', value=args['value'])
        assert args['value'] not in {entry['id'] for entry in before['constraints']}, (
            'The requested replacement identifier is independently distinct from all actual original constraint IDs')
    elif case == 'constraint_expression':
        args['value'] = target['expression'] + ' + 0.125';reference.update(role='expression', value=args['value'])
    elif operation == 'constraint_enabled':
        args['value'] = case.endswith('_true');reference['value'] = args['value']
        assert target['enabled'] is not args['value'], 'Each enabled boolean case requests a real state transition, not a no-op'
    return project, before, args, reference


def _ordinary_relation_reference(actor, reference):
    group = 'aliases' if reference['operation'].startswith('alias_') else 'constraints'
    owner = 'Session.project.analysis.' + group
    if reference['operation'].endswith('_remove'):
        qml(actor, '(function(){const rows=' + owner + ';rows.remove(' + str(reference['row']) + ');return rows.count;})()')
    elif reference['operation'] == 'constraint_enabled':
        assert qml(actor, owner + '.setEnabled(' + str(reference['row']) + ',' + json.dumps(reference['value']) + ')'), (
            'The independent expected enabled effect is reached through the original ordinary checkbox setter')
    else:
        assert qml(actor, owner + '.setText(' + str(reference['row']) + ',' + json.dumps(reference['role'])
            + ',' + json.dumps(reference['value']) + ')'), (
            'The independent expected rename/expression/target effect is reached through its original ordinary row setter')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    return {key: json.loads(json.dumps(actor.last['ui']['project'][key])) for key in ('aliases', 'constraints', 'parameters')}


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
@pytest.mark.parametrize('purpose_kind', ['omitted', 'provided'])
@pytest.mark.parametrize('case', _RELATION_PURPOSE_CASES)
def test_original_relation_edits_preserve_all_semantics_with_or_without_optional_purpose(main_actor, tmp_path, show_actions, purpose_kind, case):
    actor = main_actor([[]], show_actions=show_actions)
    project, before, args, reference = _ordinary_relation_purpose_fixture(actor, tmp_path, case)
    expected = _ordinary_relation_reference(actor, reference)
    actor.command('undo');actor.until(lambda value: not value['ui']['project']['calculating'])
    assert all(actor.last['ui']['project'][key] == before[key] for key in expected), (
        'One ordinary reference Undo restores the exact pre-native relation/parameter model before exercising the new call')
    if purpose_kind == 'provided':
        args['purpose'] = 'Edit the original requested relationship — once.'
    call = {'tool': 'edit_relation', 'call_id': 'original-optional-purpose-' + case, 'arguments': args}
    actor.configure_turns([[call]]);actor.connect();actor.command('clear_ui_sequence')
    _session_request_with_original_disclosure(actor, 'Apply this explicit original relation edit once and report its actual outcome.')
    actor.until(lambda value: len(actor.responses()) == 1 and value['ui']['state'] == 'idle', visible_progress=show_actions)
    outcome = native_result(actor.responses()[0])
    actual = actor.last['ui']['project']
    assert all(actual[key] == expected[key] for key in expected), (
        'Omitting or supplying optional purpose must preserve the same original ordinary relation and scientific effect in both modes')
    assert len(actor.responses()) == 1, 'Optional-purpose handling cannot replay the original native relation call'
    actor.command('undo');actor.until(lambda value: not value['ui']['project']['calculating'])
    assert all(actor.last['ui']['project'][key] == before[key] for key in expected), (
        'One native relation edit remains exactly one ordinary Undo, including enabled flags and coupled parameter values')
    if show_actions:
        events = actor.last['ui']['ui_sequence']
        assert any(row['kind'] == 'pointer_pressed' for row in events), (
            'Show actions ON reaches genuine original input rather than reporting only a backend reference effect')
    (actor.folder / 'optional-purpose-original-relation.json').write_text(json.dumps({
        'case': case, 'purpose_kind': purpose_kind, 'show_actions': show_actions,
        'actual_call': call, 'actual_outcome': outcome, 'ordinary_reference': expected,
        'original_current_ids': {'aliases': [row['id'] for row in before['aliases']],
            'constraints': [row['id'] for row in before['constraints']]}}, indent=2))


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
@pytest.mark.parametrize('invalid_purpose', [None, '', '   ', 17, {}, 'invalid\ncontrol'])
def test_present_invalid_relation_purpose_refuses_before_original_effect_or_presentation(main_actor, tmp_path, show_actions, invalid_purpose):
    actor = main_actor([[]], show_actions=show_actions)
    project, before, args, _reference = _ordinary_relation_purpose_fixture(actor, tmp_path, 'constraint_enabled_false')
    assert qml(actor, 'Session.save()'), 'The invalid-input negative begins from a genuinely saved original model'
    actor.until(lambda value: not value['ui']['project']['calculating'])
    before = json.loads(json.dumps(actor.command('inspect')['ui']['project']))
    saved = {str(path.relative_to(project)): path.read_bytes() for path in project.rglob('*.edi')}
    args['purpose'] = invalid_purpose
    call = {'tool': 'edit_relation', 'call_id': 'original-invalid-present-purpose', 'arguments': args}
    actor.configure_turns([[call]]);actor.connect();actor.command('clear_ui_sequence')
    _session_request_with_original_disclosure(actor, 'Exercise one explicit invalid argument without changing the original model.')
    actor.until(lambda value: len(actor.responses()) == 1 and value['ui']['state'] == 'idle')
    response = actor.responses()[0]['result']
    assert response['success'] is False, 'A present null/blank/nonstring/control-character purpose remains invalid despite the field being optional'
    after = actor.last['ui']['project']
    assert all(after[key] == before[key] for key in ('aliases', 'constraints', 'parameters', 'can_undo', 'can_redo')), (
        'Purpose validation refuses before any actual relation, scientific, or ordinary history effect')
    assert {str(path.relative_to(project)): path.read_bytes() for path in project.rglob('*.edi')} == saved, (
        'A rejected purpose does not modify original saved scientific bytes')
    assert not any(row['kind'].startswith('pointer_') for row in actor.last['ui']['ui_sequence']), (
        'Invalid purpose is rejected before assistant-driven Show actions presentation or original control input')
    (actor.folder / 'invalid-present-purpose-original-relation.json').write_text(json.dumps({
        'actual_call': call, 'actual_refusal': response, 'actual_ui_sequence': actor.last['ui']['ui_sequence'],
        'saved_source_sha256': {name: hashlib.sha256(raw).hexdigest() for name, raw in saved.items()}}, indent=2))


# Added distinct regression: original manually connected restart gate above remains unchanged.
def test_actual_auto_restart_first_send_keeps_original_thread_history_and_inputs_without_manual_connect(main_actor, tmp_path, monkeypatch):
    actor = main_actor([[]]);_session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], 'Restart positive begins with an actual saved ordinary project outside temporary app storage'
    actor.connect();source = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], 'Original restart inputs are genuinely admitted from their unchanged physical source files'
    file_id = actor.last['ui']['selected_files'][0]['id']
    actor.configure_turns([[tool_call('read_selected_file', 'original-pre-restart-native-read', file_id=file_id, offset=0, max_bytes=source.stat().st_size)]])
    original_task = 'Keep this actual original project and attached CIF for a later continuation.'
    _session_request_with_original_disclosure(actor, original_task);_session_completed(actor, 1);native_result(actor.responses()[0])
    first = _session_state(actor)['inputs'][0];thread = first['threadId']
    original_manifest = actor.command('inspect')['ui']['selected_files']
    first_rows = [_rows_values(actor, 'messages', index) for index in range(_rows_probe(actor)['count'])]
    assert {'user', 'assistant', 'activity'} <= {row['kind'] for row in first_rows}, 'The actual first run reaches user, assistant and native activity before restart capture'
    _capture_genuine_archive(actor, 'restart-full-current')
    manifest = _capture_exact_cache_manifest(actor, 'full-current')
    sources = _finish_genuine_restart_sources(actor, manifest)
    restored = _start_exact_original_fixture_restart(tmp_path, monkeypatch, sources,
        [tool_call('read_selected_file', 'actual-post-restart-native-read', file_id=file_id, offset=0, max_bytes=source.stat().st_size)])
    try:
        # Observe the owner's actual startup path; manual Connect, Sessions,
        # selectSession and forced project Open would mask this regression.
        _ordinary_expose_automatically_restored_composer(restored, original_task)
        restored.until(lambda value: original_task in json.dumps(value['ui']['messages'], ensure_ascii=False)
            and any(row['name'] == 'assistant.send' and row['enabled'] and row['fully_exposed']
                for row in value['ui']['controls']))
        auto = _session_wire(restored)
        startup = restored.command('inspect')['ui']
        followup_text = 'Continue the same original task by reading the original attached file.'
        restored.command('click', name='assistant.composer')
        restored.command('manual_text', text=followup_text)
        assert qml(restored, '(' + _scene_control_expression('assistant.composer') + ').text') == followup_text, (
            'Actual physical typing reaches the exposed original composer before its first startup continuation')
        restored.command('click', name='assistant.send')
        if any(row['name'] == 'AssistantConnectionDialog' and row['fully_exposed']
               for row in restored.last['ui']['controls']):
            approval = restored.command('dialog_ok', name='AssistantConnectionDialog', role='ok')['reply']
            assert approval['pressed_changes'] > 0, (
                'If original startup requires sharing, one genuine current Share click authorizes the captured first draft without a second Send')
        _session_completed(restored, 2)
        wire = _session_wire(restored)
        assert not any(row.get('method') == 'thread/start' for row in wire), 'Actual last-session restoration must not disguise a fresh provider thread as the resumed conversation'
        resumes = _session_wire(restored, 'thread/resume')
        assert qml(restored, 'Session.assistant.account') == sources['actual_account'], 'A genuine cold restart establishes the same actual account by its correlated read rather than treating helper readiness as an identity change'
        assert resumes and resumes[-1]['params']['threadId'] == thread, 'Normal login/restart cold-resumes the actual original last-connected runtime ID'
        assert len(_session_wire(restored, 'turn/start')) == 1, 'Startup restoration admits only the one actual first followup and never replays the original user request or native read'
        current = restored.command('inspect')['ui']
        assert current['selected_files'] == original_manifest, 'Restart restores original opaque input identities and consumed markers rather than substituting copied files or labels'
        displayed = [_rows_values(restored, 'messages', index) for index in range(_rows_probe(restored)['count'])]
        by_id = {row['id']: row for row in displayed}
        assert all(by_id.get(row['id']) == row for row in first_rows), 'Genuine full app cache restores all original user, assistant and native activity rows exactly after runtime confirmation'
        followup = _session_state(restored)['inputs'][-1]
        assert followup['threadId'] == thread and followup['actual_prior_input_count'] == 1, 'The actual next request is a continuation of the original persisted conversation rather than a new first message'
        readback = native_result(restored.responses()[-1])
        assert any(value == source.read_text() for row in objects(readback) for value in row.values() if isinstance(value, str)), 'The genuine resumed Controller can still read approved original bytes at unchanged physical identity'
        (restored.folder / 'actual-auto-startup-first-send.json').write_text(json.dumps({
            'original_sources': sources, 'auto_events_before_manual_connect': auto,
            'actual_startup_before_first_send': startup, 'manual_connect_or_session_selection': False,
            'first_send_count': 1, 'actual_resumes': resumes, 'original_rows': first_rows, 'restored_rows': displayed,
            'actual_followup': followup}, indent=2))
    finally:
        _close_explicit_restart_actor(restored)


def test_actual_main_engine_load_emits_owned_first_reply_without_component_errors(main_actor):
    actor = main_actor([[]])
    first = actor.last
    assert all(first['ui'][key] for key in ('singleton_identity', 'engine_parent', 'cpp_ownership')), (
        'The first actual Main protocol reply must come from the prepared Session/module/Main owner after real QQmlApplicationEngine load')
    assert not first['ui']['project'], 'The startup component check observes the genuine empty Main before any project or provider request'
    stderr = (actor.folder / 'host.stderr').read_text(errors='replace')
    bad = [line for line in stderr.splitlines() if re.search(
        r'QQmlApplicationEngine failed to load component|Type [^\n]+ unavailable|Invalid property assignment[^\n]*(?:read.only|read only)|(?:AppPreferencesDialog|AppDialog)[^\n]*Binding loop detected for property', line)]
    assert not bad, (
        'Real Main startup must reject unavailable components/read-only QML assignments and original Preferences/dialog binding loops; qmlcache compile success alone is not component-load evidence')
    (actor.folder / 'actual-main-component-load.json').write_text(json.dumps({
        'host_pid': actor.process.pid, 'first_owned_reply': True,
        'owner_checks': {key: first['ui'][key] for key in ('singleton_identity', 'engine_parent', 'cpp_ownership')},
        'actual_stderr': str(actor.folder / 'host.stderr'), 'component_errors': bad}, indent=2))


# PRIVATE / UNRUN. Review88 owner primitive/currentness contract, FIRST normal
# AliasListModel operations as independent reference, not assistant receipt output.
def _ordinary_changed_alias_reference(actor, alias_id):
    before = json.loads(json.dumps(actor.command('inspect')['ui']['project']))
    model = 'Session.project.analysis.aliases'
    offered = qml(actor, model + '.parameterNames')
    assert alias_id not in {row['id'] for row in before['aliases']}, (
        'The isolated reference declares one genuinely new alias without reusing a live alias identity')
    assert qml(actor, '(function(){' + model + '.append();return ' + model + '.count;})()') == len(before['aliases']) + 1, (
        'The FIRST ordinary alias owner independently supports appending one alias without any constraint')
    appended = actor.command('inspect')['ui']['project']['aliases'][-1]
    offered_mapping = qml(actor, '(function(){const project=Session.project,table=project.parameters;'
        'return project.analysis.aliases.parameterNames.map(function(name){const number=project.parameterNumber(name);'
        'return {unique_name:name,number:number,path:number>0&&number<=table.count?table.text(number-1,"path"):null};});})()')
    canonical = {row['path']: row for row in before['parameters']}
    options = [(canonical[item['path']], item['unique_name']) for item in offered_mapping
        if item['unique_name'] in offered and item['unique_name'] != appended['parameter']
        and item['path'] in canonical and item['number'] > 0]
    # Prefer an independent cell input when actually offered; cubic fixtures
    # can offer only their already-default cell input, so retain any other real
    # offered independent parameter rather than inventing a cell spelling.
    options.sort(key=lambda pair: pair[0]['category'] != 'cell')
    assert options, 'A genuinely different ordinary offered parameter exists; an already-selected no-op cannot qualify post-write settlement'
    parameter, unique_name = options[0]
    index = len(before['aliases'])
    assert qml(actor, model + '.setText(' + str(index) + ',"id",' + json.dumps(alias_id) + ')'), (
        'The normal reference gives its new alias the requested explicit identity')
    before_parameter_choice = json.loads(json.dumps(actor.command('inspect')['ui']['project']['aliases']))
    assert qml(actor, model + '.setText(' + str(index) + ',"parameter",' + json.dumps(unique_name) + ')'), (
        'The normal reference physically supported model setter changes the new alias to an actually offered canonical parameter name')
    expected = json.loads(json.dumps(actor.command('inspect')['ui']['project']['aliases']))
    assert expected[-1]['parameter'] != appended['parameter'], (
        'The reference actually changes the selected parameter; a native no-op would not exercise an own-write stamp transition')
    undo_states = []
    # At most the three genuinely invoked ordinary setters can add Undo. Stop
    # at the measured baseline; an ordinary no-op never invents an Undo step.
    for _ in range(3):
        if actor.last['ui']['project']['aliases'] == before['aliases']:
            break
        assert actor.last['ui']['project']['can_undo'], 'The FIRST ordinary reference retains its actual Undo before restoring the isolated baseline'
        actor.command('undo');actor.until(lambda value: not value['ui']['project']['calculating'])
        state = actor.command('inspect')['ui']['project']
        undo_states.append({key: json.loads(json.dumps(state[key])) for key in ('aliases', 'constraints', 'parameters')})
    assert undo_states and undo_states[0]['aliases'] == before_parameter_choice, (
        'The first genuine ordinary Undo reverses only the last effectful parameter choice while retaining its appended alias and explicit ID')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    actual = actor.command('inspect')['ui']['project']
    assert actual['aliases'] == before['aliases'] and actual['constraints'] == before['constraints'] \
        and actual['parameters'] == before['parameters'], (
            'Only ordinary Undo restores the genuine pre-reference science before the separately requested native action')
    return before, expected, parameter, unique_name, appended, undo_states


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_alias_only_changed_parameter_matches_first_ordinary_owner_once_and_undo(main_actor, tmp_path, show_actions):
    actor = main_actor([[]], show_actions=show_actions)
    project = copied_estimate_project(tmp_path)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'Standalone alias coverage uses a genuine complete ordinary project in an isolated copy')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    before, expected, parameter, unique_name, appended, reference_undo_states = _ordinary_changed_alias_reference(actor, 'standalone_original_cell')
    if show_actions:
        wait_positive_tab(actor, 'appBar.tab.analysis');actor.command('click', name='appBar.tab.analysis')
        actor.until(lambda value: any(row['name'] == 'parameters.category' and row['visible'] for row in value['ui']['controls']))
        _watch_original_offered_choices(actor, 'e11.standalone-alias-actual-choice')
    call = {'tool': 'add_relations', 'call_id': 'standalone-original-alias-once',
        'arguments': {'purpose': 'Add only this exact original offered alias without inventing a constraint.',
            'aliases': [{'id': 'standalone_original_cell', 'path': parameter['path']}], 'constraints': []}}
    actor.configure_turns([[call]]);actor.connect();_session_request_with_original_disclosure(actor,
        'Add the one requested original alias and no constraint; retain its actual ordinary Undo.')
    actor.until(lambda value: bool(actor.responses()) and value['ui']['state'] == 'idle', visible_progress=show_actions)
    response = actor.responses()[0];result = native_result(response)
    after = actor.command('inspect')['ui']['project']
    assert after['aliases'] == expected and after['constraints'] == before['constraints'], (
        'Alias-only native admission must match the FIRST independent ordinary alias owner and never fabricate a constraint')
    assert after['parameters'] == before['parameters'] and len(actor.responses()) == 1, (
        'One real changed alias choice does not replay science or change unrelated values, flags or uncertainties')
    physical = []
    if show_actions:
        watcher = _scene_control_expression('e11.standalone-alias-actual-choice')
        qml(actor, '(' + watcher + ').finished=true')
        facts = qml(actor, '(' + watcher + ').facts')
        physical = [row for row in facts if row['kind'] == 'real_delegate_pressed' and row['control'].startswith('alias.parameter.')]
        assert physical and all(row['ownerCurrent'] and row['sameWindow'] and row['popupVisible'] and row['rowVisible'] for row in physical), (
            'Show ON standalone alias reaches actual input on the original exposed offered row, not merely a setter or popup visibility')
    _match_original_alias_undo_sequence(actor, before, reference_undo_states, show_actions)
    (actor.folder / 'standalone-alias-original-owner.json').write_text(json.dumps({
        'call': call, 'result': result, 'ordinary_reference_aliases': expected,
        'normal_unique_name': unique_name, 'original_default_alias': appended,
        'reference_undo_states': reference_undo_states, 'actual_physical_choices': physical}, indent=2))


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_empty_alias_and_constraint_request_refuses_without_creating_science(main_actor, tmp_path, show_actions):
    call = {'tool': 'add_relations', 'call_id': 'genuinely-empty-relations',
        'arguments': {'purpose': 'An empty declaration must refuse without inventing scientific work.', 'aliases': [], 'constraints': []}}
    actor = main_actor([[call]], show_actions=show_actions)
    assert actor.command('open', path=str(copied_estimate_project(tmp_path)))['reply']['opened'], (
        'Empty relation refusal is exercised against an actual available ordinary project, not an unavailable-owner precondition')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    before = json.loads(json.dumps(actor.command('inspect')['ui']['project']))
    actor.connect();_session_request_with_original_disclosure(actor, 'Do not create any alias or constraint for an empty declaration.')
    actor.until(lambda value: bool(actor.responses()) and value['ui']['state'] == 'idle', visible_progress=show_actions)
    response = actor.responses()[0]
    assert not response['result']['success'], 'The actual native API must refuse a genuinely empty relation request instead of fabricating an action'
    after = actor.command('inspect')['ui']['project']
    assert after['aliases'] == before['aliases'] and after['constraints'] == before['constraints'] \
        and after['parameters'] == before['parameters'] and after['can_undo'] == before['can_undo'], (
            'The empty declaration refuses before any alias/constraint/parameter mutation or invented Undo')
    (actor.folder / 'empty-original-relations-refusal.json').write_text(json.dumps({
        'call': call, 'actual_reply': response, 'original_project': before, 'after_project': after}, indent=2))


# PRIVATE / UNRUN. Owner's actual casual no-project startup continuation, distinct
# from the retained saved-project plus attachment restart characterization.
def test_actual_no_project_auto_restart_first_send_keeps_original_conversation_without_manual_connect(main_actor, tmp_path, monkeypatch):
    actor = main_actor([[]])
    _session_configure(actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True)
    actor.connect()
    assert not actor.last['ui']['project'] and not actor.last['ui']['selected_files'], (
        'The casual conversation starts in the actual original empty Main without a planted project or attachment')
    first_text = 'Hello. Keep this actual ordinary conversation for my later question.'
    _session_request_with_original_disclosure(actor, first_text);_session_completed(actor, 1)
    first_input = _session_state(actor)['inputs'][0];thread = first_input['threadId']
    first_rows = [_rows_values(actor, 'messages', index) for index in range(_rows_probe(actor)['count'])]
    assert {'user', 'assistant'} <= {row['kind'] for row in first_rows}, (
        'Expected history comes from a genuinely admitted first user message and actually emitted original assistant reply')
    assert not actor.command('inspect')['ui']['project'], 'The actual first conversation remains project-free through its normal completion'
    _capture_genuine_archive(actor, 'casual-no-project-original')
    manifest = _capture_exact_cache_manifest(actor, 'casual-no-project-full-current')
    sources = _finish_genuine_restart_sources(actor, manifest)
    restored = _start_exact_original_fixture_restart(tmp_path, monkeypatch, sources, [])
    try:
        # No manual Connect, Open, refreshSessions or selectSession is allowed
        # before the actual first ordinary Send on the restarted application.
        _ordinary_expose_automatically_restored_composer(restored, first_text)
        restored.until(lambda value: first_text in json.dumps(value['ui']['messages'], ensure_ascii=False)
            and any(row['name'] == 'assistant.send' and row['enabled'] and row['fully_exposed']
                for row in value['ui']['controls']))
        startup = restored.command('inspect')['ui'];before_wire = _session_wire(restored)
        assert not startup['project'] and not startup['selected_files'], (
            'Automatic startup keeps the original no-project association instead of opening a substitute project')
        followup_text = 'What was my earlier message in this same ordinary conversation?'
        restored.command('click', name='assistant.composer');restored.command('manual_text', text=followup_text)
        assert qml(restored, '(' + _scene_control_expression('assistant.composer') + ').text') == followup_text, (
            'Actual physical typing reaches the original exposed composer, not a synthetic send or injected history row')
        restored.command('click', name='assistant.send')
        approval = None
        if any(row['name'] == 'AssistantConnectionDialog' and row['fully_exposed']
               for row in restored.last['ui']['controls']):
            approval = restored.command('dialog_ok', name='AssistantConnectionDialog', role='ok')['reply']
            assert approval['pressed_changes'] > 0, (
                'Any genuinely required original sharing disclosure receives one actual approval and no second Send')
        _session_completed(restored, 2)
        wire = _session_wire(restored);actual = _session_state(restored)['inputs']
        assert len(actual) == 2 and actual[-1]['threadId'] == thread \
            and actual[-1]['actual_prior_input_count'] == 1, (
                'The first actual post-startup question continues the exact original persisted runtime thread with its genuine prior input')
        assert not any(row.get('method') == 'thread/start' for row in wire) \
            and len(_session_wire(restored, 'turn/start')) == 1, (
                'Automatic no-project continuation cold-resumes the original conversation without a new thread, replayed prompt or duplicate admission')
        resumes = _session_wire(restored, 'thread/resume')
        assert resumes and resumes[-1]['params']['threadId'] == thread, (
            'Original history visibility is accompanied by an actual supported exact-ID runtime resume, not only cached user bubbles')
        displayed = [_rows_values(restored, 'messages', index) for index in range(_rows_probe(restored)['count'])]
        by_id = {row['id']: row for row in displayed}
        assert all(by_id.get(row['id']) == row for row in first_rows), (
            'The first Send preserves every actual original user and assistant history row with its original identity/status/text')
        final_ui = restored.command('inspect')['ui']
        assert not final_ui['project'] and not final_ui['selected_files'], (
            'A casual restored conversation cannot acquire scientific project or file authority as a side effect of its first question')
        (restored.folder / 'actual-casual-auto-startup-first-send.json').write_text(json.dumps({
            'original_sources': sources, 'original_thread': thread, 'original_rows': first_rows,
            'actual_startup_before_send': startup, 'actual_wire_before_send': before_wire,
            'manual_connect_or_session_selection': False, 'physical_send_count': 1,
            'actual_sharing_approval': approval, 'actual_resumes': resumes,
            'actual_inputs': actual, 'actual_after_rows': displayed}, indent=2))
    finally:
        _close_explicit_restart_actor(restored)



def _match_original_alias_undo_sequence(actor, before, ordinary_undo_states, show_actions):
    expected_states = ordinary_undo_states if show_actions else [
        {key: before[key] for key in ('aliases', 'constraints', 'parameters')}]
    assert expected_states, 'Undo qualification requires genuine original ordinary reference states, never a guessed fixed edit count'
    actual_states = []
    for expected in expected_states:
        assert actor.last['ui']['project']['can_undo'], 'Each actual scientific Undo remains available on its original current project owner'
        actor.command('undo');actor.until(lambda value: not value['ui']['project']['calculating'])
        state = actor.command('inspect')['ui']['project']
        actual = {key: state[key] for key in ('aliases', 'constraints', 'parameters')}
        actual_states.append(actual)
        assert actual == expected, (
            'Show ON Undo follows each FIRST ordinary applied control prefix; Show OFF retains its one atomic relation Undo, with unrelated science unchanged')
    assert actor.last['ui']['project']['aliases'] == before['aliases'] \
        and actor.last['ui']['project']['constraints'] == before['constraints'] \
        and actor.last['ui']['project']['parameters'] == before['parameters'] \
        and actor.last['ui']['project']['can_undo'] == before['can_undo'], (
            'The measured ordinary Undo sequence returns to the original declaration without an extra or duplicate scientific edit')
    (actor.folder / 'actual-alias-ordinary-undo-sequence.json').write_text(json.dumps({
        'show_actions': show_actions, 'independent_ordinary_states': ordinary_undo_states,
        'actual_native_undo_states': actual_states}, indent=2))


def _ordinary_expose_automatically_restored_composer(actor, original_text):
    actor.until(lambda value: original_text in json.dumps(value['ui']['messages'], ensure_ascii=False))
    before = actor.command('inspect')['ui']
    before_wire = _session_wire(actor)
    before_draft = qml(actor, '(' + _scene_control_expression('assistant.composer') + ').text')
    delivery = None
    if any(row['name'] == 'home.start' and row['enabled'] and row['fully_exposed'] for row in before['controls']):
        delivery = actor.command('click', name='home.start')['reply']
    after = actor.command('inspect')['ui']
    assert (after['project'] or {}).get('path') == (before['project'] or {}).get('path') \
        and after['selected_files'] == before['selected_files'], (
            'Entering the actual ordinary Start page preserves the automatically restored current project and original input descriptors')
    after_rows = {row['id']: row for row in after['messages']}
    assert all(after_rows.get(row['id']) == row for row in before['messages']) \
        and qml(actor, '(' + _scene_control_expression('assistant.composer') + ').text') == before_draft, (
            'The normal Start input does not substitute restored history rows or erase the original draft before the first Send')
    assert not _session_wire(actor, 'thread/start') and not _session_wire(actor, 'turn/start'), (
        'Normal UI exposure cannot silently bootstrap a fresh conversation or replay an old user input')
    (actor.folder / 'ordinary-start-after-actual-auto-restore.json').write_text(json.dumps({
        'actual_pre_start': before, 'actual_wire_before_start': before_wire,
        'actual_pre_start_draft': before_draft, 'actual_start_input': delivery,
        'actual_after_start': after, 'no_manual_connect_select_or_open': True}, indent=2))


# PRIVATE / UNRUN. The existing one-Send/same-account positive is actual-red
# in app21. These finite independent negatives do not replace that positive.
@pytest.mark.parametrize('boundary', ['cancel', 'account', 'draft', 'files', 'model'])
def test_original_share_wait_cannot_approve_changed_or_cancelled_input(main_actor, tmp_path, boundary):
    actor = main_actor([[]], show_actions=True)
    models = [{'id': name, 'model': name, 'displayName': name, 'description': 'Offline protocol fixture',
        'hidden': False, 'isDefault': name == 'gpt-6.1-sol', 'defaultReasoningEffort': 'medium',
        'supportedReasoningEfforts': [{'reasoningEffort': 'medium', 'description': 'Fixture'}]}
        for name in ['gpt-6.1-sol', 'gpt-5.6-luna']]
    _session_configure(actor, fixture_models=models, session_fixture={'threads': [], 'page_size': 12},
        observe_context_continuity=True)
    actor.connect();original_account = qml(actor, 'Session.assistant.account');files = _attachment_fixtures(tmp_path, 2)
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(files[0])])['reply']['added'], (
        'The original Share wait owns a genuinely admitted pending file')
    late = actor.begin_current_file_selection() if boundary == 'files' else None
    text = 'Use this exact original pending input only after the original Share.'
    actor.command('send_text', text=text)
    actor.until(lambda value: any(row['name'] == 'AssistantConnectionDialog' and row['fully_exposed']
        for row in value['ui']['controls']))
    if boundary == 'account':
        _session_configure(actor, fixture_account_read_reply={'account': {'type': 'chatgpt',
            'email': 'different-fixture-account@example.invalid', 'planType': 'plus'}, 'requiresOpenaiAuth': False})
    release = actor.folder / 'release-original-share-boundary-account'
    try:
        held = _review66_hold_original_identity(actor, release)
        delivered = actor.command('dialog_ok', name='AssistantConnectionDialog',
                                  role='cancel' if boundary == 'cancel' else 'ok')['reply']
        assert delivered['pressed_changes'] > 0, 'The existing original Share/Cancel standard button receives actual current-window input'
        if boundary == 'draft':
            actor.until(lambda value: any(row['name'] == 'assistant.composer' and row['enabled'] and row['fully_exposed']
                for row in value['ui']['controls']))
            actor.command('click', name='assistant.composer');actor.command('manual_text', text=' Changed by the user before readiness.')
            assert qml(actor, '(' + _scene_control_expression('assistant.composer') + ').text') != text, (
                'The negative actually reaches changed draft text through the original physical editor')
        elif boundary == 'files':
            assert late and actor.command('selected_add', token=late, paths=[str(files[1])])['reply']['added'], (
                'A genuine outstanding original picker changes the pending files rather than mutating a model property')
        elif boundary == 'model':
            actor.until(lambda value: any(row['name'] == 'assistant.modelEffort' and row['enabled'] and row['fully_exposed']
                for row in value['ui']['controls']))
            actor.command('click', name='assistant.modelEffort')
            actor.until(lambda value: any(row['name'] == 'assistant.choice.model.gpt-5.6-luna' and row['enabled'] and row['fully_exposed']
                for row in value['ui']['controls']))
            actor.command('click', name='assistant.choice.model.gpt-5.6-luna')
            assert qml(actor, 'Session.assistant.selectedModel') == 'gpt-5.6-luna', (
                'The changed-model negative physically chooses an actually offered original model')
        assert not _session_wire(actor, 'turn/start'), 'No original pending input may be sent while its correlated account proof is held'
        release.touch();actor.command('refresh_usage')
        actor.until(lambda _value: any(row.get('id') == held['id'] and 'result' in row
            for row in map(json.loads, actor.trace.with_suffix('.sent.jsonl').read_text().splitlines())))
        if boundary == 'account':
            actor.until(lambda value: not value['ui']['connected'] or qml(actor, 'Session.assistant.account') != original_account)
        else:
            actor.until(lambda value: value['ui']['connected'] and qml(actor, 'Session.assistant.draftAdmissionReady'))
        actor.command('inspect') # A genuine subsequent Qt command turn after the actual readiness/retirement boundary.
        assert not _session_wire(actor, 'turn/start') and not _session_state(actor)['inputs'], (
            'Readiness cannot approve or resubmit an old cancelled/changed account, draft, file or model offer without a new explicit user action')
        (actor.folder / 'original-share-invalidated-before-readiness.json').write_text(json.dumps({
            'boundary': boundary, 'held_correlated_read': held, 'actual_original_button': delivered,
            'send_count': 1, 'share_count': 0 if boundary == 'cancel' else 1,
            'actual_requests': _session_wire(actor), 'actual_final': actor.command('inspect')['ui']}, indent=2))
    finally:
        release.touch()


def _observe_original_toolbar_press(actor, marker, paths=()):
    source = r'''(function(){const vm=Session.assistant,project=Session.project,toggle=assistantToggle;
        if(!project||!toggle||toggle.Window.window!==window)return false;
        const o=Qt.createQmlObject('import QtQuick; Item {property var presses:[];property var cues:[];}',window.contentItem);o.objectName=MARKER;
        function values(){const table=project.parameters,out={};for(const path of PATHS){out[path]=null;for(let n=0;n<table.count;n++)if(table.text(n,'path')===path){out[path]=table.get(n,'value');break;}}return out;}
        function state(){if(!Qt.isQtObject(project)||!Qt.isQtObject(vm)||!Qt.isQtObject(toggle)||Session.project!==project||Session.assistant!==vm)return {ownerCurrent:false,unavailable:true};return {ownerCurrent:true,project:String(project),
            paneVisible:assistantPanel.visible,paneOpened:assistantPanel.opened,selected:toggle.assistantSelected,
            icon:toggle.fontIcon,fitRunning:project.fit.running,fitOutcome:project.fit.outcome,
            values:values(),showingActions:vm.showingActions,canCancel:vm.canCancel};}
        toggle.pressedChanged.connect(function(){if(Qt.isQtObject(o)&&Qt.isQtObject(toggle)&&toggle.pressed)o.presses.push(state());});
        vm.actionPointerMoved.connect(function(point){if(Qt.isQtObject(o)){const s=state();s.x=point.x;s.y=point.y;o.cues.push(s);}});
        return true;})()'''.replace('MARKER', json.dumps(marker)).replace('PATHS', json.dumps(list(paths)))
    assert qml(actor, source), 'The read-only witness binds the actual original toolbar, current project and window before genuine input'


def _original_toolbar_pane_state(actor):
    return qml(actor, '({visible:assistantPanel.visible,opened:assistantPanel.opened,selected:assistantToggle.assistantSelected,'
        'icon:assistantToggle.fontIcon,project:String(Session.project),showingActions:Session.assistant.showingActions})')


def test_manual_original_assistant_toolbar_keeps_exact_visible_prefix_then_new_reveal(main_actor, tmp_path):
    actor = main_actor([[]], show_actions=True)
    assert actor.command('open', path=str(copied_estimate_project(tmp_path)))['reply']['opened'], (
        'The manual toolbar witness uses a genuine complete isolated ordinary project')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    before = json.loads(json.dumps(actor.command('inspect')['ui']['project']))
    first = next(row for row in before['parameters'] if row['category'] == 'instrument' and row['field'] == 'calib_twotheta_offset')
    second = next(row for row in before['parameters'] if row['category'] == 'instrument' and row['field'] == 'setup_wavelength')
    wanted = {first['path']: first['value'] + 0.013, second['path']: second['value'] * 1.01}
    call = tool_call('set_parameters', 'manual-toolbar-original-prefix', values=[{'path': row['path'], 'value': wanted[row['path']]} for row in [first, second]])
    actor.configure_turns([[call]]);marker = 'e11.manual.toolbar.original-prefix'
    _observe_original_toolbar_press(actor, marker, wanted)
    actor.connect();_session_request_with_original_disclosure(actor, 'Apply these two explicit original scalar edits once through their ordinary visible owners.')
    def prefix(value):
        rows = {row['path']: row for row in value['ui']['project']['parameters']}
        return value['ui']['can_cancel'] and rows[first['path']]['value'] == wanted[first['path']] \
            and rows[second['path']]['value'] == second['value']
    actor.until(prefix, visible_progress=True)
    actor.command('click', name='assistant.toggle')
    presses = qml(actor, '(' + _scene_control_expression(marker) + ').presses')
    assert presses and presses[-1]['ownerCurrent'] and presses[-1]['showingActions'] \
        and presses[-1]['values'][first['path']] == wanted[first['path']] \
        and presses[-1]['values'][second['path']] == second['value'], (
            'The actual physical toolbar press must reach the original partially applied visible operation before the second scientific edit; otherwise this channel is unreached')
    actor.until(lambda _value: _original_toolbar_pane_state(actor)['visible'] and _original_toolbar_pane_state(actor)['opened'])
    pane = _original_toolbar_pane_state(actor)
    assert pane['selected'] and pane['icon'] == 'columns', 'After the actual manual Open Assistant action, pane and toolbar icon must agree on the visible Assistant'
    actor.until(lambda value: bool(actor.responses()) and value['ui']['state'] == 'idle', visible_progress=True)
    partial = json.loads(actor.responses()[0]['result']['contentItems'][0]['text'])
    after = actor.command('inspect')['ui']['project'];rows = {row['path']: row for row in after['parameters']}
    assert rows[first['path']]['value'] == wanted[first['path']] and rows[second['path']]['value'] == second['value'] \
        and partial.get('complete') is False and partial.get('steps_completed') == 1, (
            'Manual toolbar takeover retains the actual single applied prefix and truthfully retires its unperformed continuation without an extra edit')
    before_cues = len(qml(actor, '(' + _scene_control_expression(marker) + ').cues'))
    actor.append_turn([tool_call('inspect_project', 'inspect-actual-retained-manual-prefix'),
        tool_call('set_parameters', 'later-new-original-reveal', values=[{'path': second['path'], 'value': wanted[second['path']]}])])
    _session_request_with_original_disclosure(actor, 'Apply this separate new remaining original edit once after inspecting the retained prefix.')
    actor.until(lambda value: len(actor.responses()) == 3 and value['ui']['state'] == 'idle', visible_progress=True)
    native_result(actor.responses()[-1])
    cues = qml(actor, '(' + _scene_control_expression(marker) + ').cues')[before_cues:]
    assert cues and any(row['ownerCurrent'] and row['showingActions'] and not row['paneVisible'] for row in cues), (
        'A later separately requested native operation can genuinely reveal its original control after the manual Assistant override')
    current = {row['path']: row for row in actor.command('inspect')['ui']['project']['parameters']}
    assert all(current[path]['value'] == value for path, value in wanted.items()) \
        and all(current[row['path']] == row for row in before['parameters'] if row['path'] not in wanted) \
        and all({key: value for key, value in current[row['path']].items() if key != 'value'}
                == {key: value for key, value in row.items() if key != 'value'} for row in before['parameters'] if row['path'] in wanted), (
            'The later newly owned action changes only its requested remaining value; manual sidebar switching preserves all unrelated values, flags and metadata')
    (actor.folder / 'manual-toolbar-prefix-and-new-reveal.json').write_text(json.dumps({
        'physical_press': presses, 'visible_pane': pane, 'actual_partial': partial,
        'retained_prefix': after, 'later_cues': cues, 'actual_results': actor.responses()}, indent=2))


def test_manual_original_assistant_toolbar_does_not_stop_active_background_fit(main_actor, tmp_path):
    actor = main_actor([[tool_call('run_fit', 'toolbar-during-original-background-fit')]], show_actions=True)
    project = tmp_path / 'ordinary-original-fit';shutil.copytree(ROOT / 'tests/fixtures/fit_quality/fullprof-model', project)
    assert actor.command('open', path=str(project))['reply']['opened'], 'The background-Fit toolbar witness opens the unchanged existing native fit fixture'
    actor.until(lambda value: not value['ui']['project']['calculating'])
    wait_positive_tab(actor, 'appBar.tab.structure');actor.command('click', name='appBar.tab.structure')
    assert qml(actor, 'Session.project.fit.available'), 'A real current native Fit is available before the toolbar action'
    marker = 'e11.manual.toolbar.original-background-fit';_observe_original_toolbar_press(actor, marker)
    actor.connect();_session_request_with_original_disclosure(actor, 'Fit this current original fixture while retaining its ordinary native result and Undo.')
    actor.until(lambda _value: qml(actor, 'Session.project.fit.running'), visible_progress=True)
    actor.command('click', name='assistant.toggle')
    presses = qml(actor, '(' + _scene_control_expression(marker) + ').presses')
    assert presses and presses[-1]['ownerCurrent'] and presses[-1]['fitRunning'], (
        'Only a genuine original toolbar press during actual background Fit qualifies this channel; a naturally completed earlier fit does not')
    actor.until(lambda _value: _original_toolbar_pane_state(actor)['visible'] and _original_toolbar_pane_state(actor)['opened'])
    pane = _original_toolbar_pane_state(actor)
    assert pane['selected'] and pane['icon'] == 'columns', 'Manual Assistant visibility and its real toolbar icon agree while a native Fit runs'
    actor.until(lambda value: bool(actor.responses()) and not qml(actor, 'Session.project.fit.running'), visible_progress=True)
    result = native_result(actor.responses()[0]);outcome = qml(actor, 'Session.project.fit.outcome')
    assert outcome not in ['stopped', 'superseded'] and qml(actor, 'Session.project.fit.canUndo'), (
        'Opening the Assistant is not Stop Fit or a project retirement; the same actual background result and ordinary Undo survive')
    (actor.folder / 'manual-toolbar-preserves-original-background-fit.json').write_text(json.dumps({
        'actual_running_press': presses, 'actual_pane': pane, 'actual_native_result': result,
        'actual_fit_outcome': outcome, 'timing_qualification': 'No forced worker hold or elapsed-time performance claim; actual running press is mandatory.'}, indent=2))

# PRIVATE / UNRUN seq133. Original IUCr decimal meaning and original formatter,
# not an oracle generated by the new assistantParameterText bridge.
def _independent_parenthetic_decimal_meaning(literal):
    match = re.fullmatch(r'([+-]?\d+(?:\.\d+)?)(?:\((\d+)\))', literal)
    assert match, 'The independent SU witness uses a literal with explicit decimal places and bracket digits'
    mean = Decimal(match.group(1))
    return mean, Decimal(match.group(2)).scaleb(mean.as_tuple().exponent)


def test_original_iucr_literal_meaning_distinguishes_one_lost_uncertainty_digit():
    assert _independent_parenthetic_decimal_meaning('3.86512(41)') == (Decimal('3.86512'), Decimal('.00041')), (
        'An IUCr bracket is an integer in the units of the written value last decimal place')
    assert _independent_parenthetic_decimal_meaning('3.86512(4)')[1] == Decimal('.00004'), (
        'Dropping the final uncertainty digit changes the reported uncertainty tenfold; it is not a display synonym')
    assert _independent_parenthetic_decimal_meaning('-386.512(41)') == (Decimal('-386.512'), Decimal('.041')), (
        'Signed and scaled nontrivial values preserve the same original decimal convention')


def test_actual_parameter_inspection_keeps_first_native_value_and_uncertainty_spelling(main_actor, tmp_path):
    project = tmp_path / 'independent-su-literal'
    shutil.copytree(ROOT / 'tests/fixtures/fit_quality/uncertainty', project)
    source = project / 'structures/phase.edi'; original = source.read_bytes()
    assert original.count(b'_cell.length_a 4.1\n') == 1, (
        'The independent literal replaces only the named original fixture cell, not a generated fitted result')
    source.write_bytes(original.replace(b'_cell.length_a 4.1\n', b'_cell.length_a 3.86512(41)\n'))
    actor = main_actor([[tool_call('list_parameters', 'original-native-su-pair')]])
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'The literal enters through the ordinary original project loader, with genuine observations and no refit')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    assert qml(actor, '(function(){Session.project.suRule="iucr_99";return Session.project.suRule;})()') == 'iucr_99', (
        'The normal original project uncertainty rule, not an assistant-only formatter, owns the spelling')
    before_parameters = json.loads(json.dumps(actor.command('inspect')['ui']['project']['parameters']))
    original_parameter = next(row for row in before_parameters
        if row['category'] == 'cell' and row['field'] == 'length_a')
    item = qml(actor, '(function(){const p=Session.project,t=p.parameters;for(let i=0;i<t.count;i++){'
        'if(t.text(i,"path")!==' + json.dumps(original_parameter['path']) + ')continue;'
        'const x=t.parameterAt(i);return {path:x.path,value:x.value,su:x.uncertainty,hasSu:x.hasUncertainty,'
        'file_value:x.fileValue,file_su:x.fileSu};}return null;})()')
    expected_mean, expected_su = _independent_parenthetic_decimal_meaning('3.86512(41)')
    assert item and item['hasSu'] and Decimal(str(item['value'])) == expected_mean \
        and Decimal(str(item['su'])) == expected_su, (
            'The original native parameter preserves the independently decoded actual literal mean and SU')
    assert item['file_value'] == '3.86512' and item['file_su'] == '0.00041', (
        'FIRST already-published ordinary GUI/file cells retain the full native two-digit uncertainty')
    actor.connect();_session_request_with_original_disclosure(actor, 'Read the actual current parameter values and uncertainties without changing them.')
    actor.until(lambda value: bool(actor.responses()) and value['ui']['state'] == 'idle')
    result = native_result(actor.responses()[0])
    row = next(row for row in result['parameters'] if row['path'] == original_parameter['path'])
    assert Decimal(str(row['value'])) == expected_mean and Decimal(str(row['uncertainty'])) == expected_su, (
        'The model-visible actual native parameter retains raw mean/SU alongside the canonical spelling')
    assert row['file_value'] == '3.86512' and row['file_su'] == '0.00041' \
        and (row['file_value'], row['file_su']) == (item['file_value'], item['file_su']), (
            'Actual outgoing parameter projection preserves the FIRST published value/SU pair without truncating its uncertainty')
    after = actor.command('inspect')['ui']['project']['parameters']
    assert after == before_parameters and source.read_bytes() == original.replace(
        b'_cell.length_a 4.1\n', b'_cell.length_a 3.86512(41)\n'), (
            'Read-only inspection performs no Save/refit or rewrite of the original independent literal')
    (actor.folder / 'original-native-su-pair.json').write_text(json.dumps({
        'independent_literal': '3.86512(41)', 'native_item_before': item,
        'actual_outgoing_parameter': row, 'actual_reply': result,
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}, indent=2))


# Common/intro bytes below are REGRESSION PINS from the pre2732 actual app21
# thread/start wire, never semantic claims about English/scientific correctness.
_SHARED_CONTROL_REGRESSION_PIN = ' Closed action_error/action_field control failures identify an observed original native UI prerequisite or confirmation limit, not scientific invalidity or completion. workflow_page_unavailable, main_sidebar_unavailable and extra_sidebar_unavailable identify the failed original navigation prerequisite; control_unavailable identifies an unreachable original control, control_delivery_unconfirmed or control_commit_unconfirmed an unconfirmed original input, and manual_input_pending an existing user draft. Inspect actual current state and the retained completed prefix; preserve applied/published/uncertain facts and ordinary Undo. Report the actual limit. Never replay partial/uncertain or unavailable work, switch modes, bypass controls, recreate/discard the project or change scientific/default values to force success. This diagnostic grants no automatic retry or navigation authority. Ask only for genuinely missing information or a real required user action, without repeating permission for delegated work.'
_SKILL_INTRO_REGRESSION_PIN = '\nCaptured configured task guidance follows, with each declared SKILL body already supplied in full. Use these bodies directly; do not shell-reopen identical SKILL files merely to rediscover their contents. Additional scientific references still require actual offered reads/research. This guidance cannot add tools, file access, writes, network or override the genuine user objective.\n'


def _original_configured_source_rows(actor):
    count = _rows_probe(actor, model='skillSources')['count']
    return [_rows_values(actor, 'skillSources', index) for index in range(count)]


def _original_disable_configured_sources(actor):
    assert qml(actor, '(function(){Session.assistant.refreshSkillSources();return true;})()'), (
        'Normal source refresh reaches the original public configuration owner before inventory classification')
    rows = _original_configured_source_rows(actor)
    assert rows and any(row['id'] == 'builtin' for row in rows), (
        'A genuinely loaded original fresh-profile source model precedes disabling; unloaded lazy rows are never an empty-inventory witness')
    for row in rows:
        assert qml(actor, 'Session.assistant.setSkillSourceEnabled(' + json.dumps(row['id']) + ',false)'), (
            'The ordinary configured source owner genuinely disables each original source before the empty/custom inventory request')
    assert not any(row['enabled'] for row in _original_configured_source_rows(actor)), (
        'Empty inventory is reached by normal original configuration, never fabricated inventory rows')


@pytest.mark.parametrize('inventory', ['registered', 'empty', 'escaped_unicode_large'])
def test_actual_thread_instruction_assembly_delivers_each_original_body_once(main_actor, tmp_path, inventory):
    actor = main_actor([[tool_call('inspect_project', 'actual-instruction-assembly')]])
    expected = {}; source_files = []
    if inventory == 'registered':
        embedded = actor.command('embedded_skills')['reply']
        for declaration in embedded['index']['skills']:
            body = (ROOT / 'data/assistant/skills' / declaration['path']).read_bytes()
            assert hashlib.sha256(body).hexdigest() == declaration['sha256'], (
                'The actual registered original declaration is bonded to independently read immutable skill bytes')
            expected[declaration['id']] = body.decode('utf-8')
    else:
        _original_disable_configured_sources(actor)
        if inventory == 'escaped_unicode_large':
            collection = tmp_path / 'ordinary configured skills';collection.mkdir()
            # Deliberately non-BMP, multi-byte, escaped/control JSON characters,
            # and a valid body larger than small text snippets. No work quota or
            # guessed maximum is introduced; malformed byte cases are separate.
            for identity, suffix in [('z-last', 'last'), ('a-first', 'first')]:
                folder = collection / identity;folder.mkdir()
                body = ('---\nname: ' + identity + '\ndescription: Original instruction assembly witness\n---\n'
                    + ('é Å 😀 \\" quoted\tline\n' * 4097) + '\n' + suffix + '\n')
                file = folder / 'SKILL.md';file.write_bytes(body.encode('utf-8'))
                source_files.append((file, file.read_bytes()));expected[identity] = body
                # Captured resource bytes are not declared instructions.
                (folder / 'read-only-reference.txt').write_text('opaque noninstruction resource: ' + identity)
            token = qml(actor, 'Session.assistant.beginSkillSourceSelection()')
            assert token and qml(actor, 'Session.assistant.addSkillSource(' + json.dumps(token) + ','
                + json.dumps(collection.as_uri()) + ')'), (
                    'A real local source is captured through the original chooser token, not a manufactured staged inventory')
    actor.command('create', name='actual-instruction-owner')
    actor.connect();_session_request_with_original_disclosure(actor, 'Inspect the current project through its actual offered operation without edits.')
    actor.until(lambda value: bool(actor.responses()) and value['ui']['state'] == 'idle')
    starts = [row['params'] for row in _session_wire(actor, 'thread/start')]
    assert len(starts) == 1, 'Exactly one original thread admission supplies the actual assembled instruction boundary'
    instructions = starts[0]['developerInstructions'];common = _SHARED_CONTROL_REGRESSION_PIN
    assert instructions.startswith(common) and instructions.count(common) == 1, (
        'The unchanged pre2732 common-contract regression bytes are delivered globally exactly once')
    descriptions = actor.command('tool_specs')['reply']['tools']
    assert descriptions and all(common not in tool['description'] for tool in descriptions), (
        'The globally delivered common bytes are not redundantly recopied into each original tool descriptor')
    intro = _SKILL_INTRO_REGRESSION_PIN
    assert instructions.count(intro) == (1 if expected else 0), (
        'One genuine nonempty inventory gets one captured-guidance introduction; empty inventory gets none')
    if expected:
        # Original inventory declaration-ID ordering is a regression property;
        # byte-exact bodies and once delivery are the ownership invariant.
        tail = intro + ''.join(expected[key] + '\n' for key in sorted(expected))
        assert instructions.endswith(tail), (
            'Actual developerInstructions retains each entire original body once in its established declaration order with exact separators')
        assert all(instructions.count(body) == 1 for body in expected.values()), (
            'No complete original body is duplicated or truncated during UTF-8/UTF-16/JSON assembly')
    assert all(file.read_bytes() == original for file, original in source_files), (
        'Instruction capture leaves the physically admitted original source bytes unchanged')
    assert 'opaque noninstruction resource:' not in instructions, (
        'Captured package resources remain data and do not enter the declared instruction-body exception')
    (actor.folder / 'actual-assembled-instructions.json').write_text(json.dumps({
        'inventory': inventory, 'original_bodies': {key: hashlib.sha256(value.encode()).hexdigest() for key, value in expected.items()},
        'actual_utf8_bytes': len(instructions.encode()), 'actual_utf16_units': len(instructions.encode('utf-16-le')) // 2,
        'actual_json_utf8_bytes': len(json.dumps(instructions, ensure_ascii=False).encode()),
        'actual_instruction_sha256': hashlib.sha256(instructions.encode()).hexdigest(),
        'actual_thread_start': starts[0]}, indent=2))


@pytest.mark.parametrize('malformed', ['nul', 'invalid_utf8'])
def test_original_skill_source_refuses_malformed_text_before_instruction_admission(main_actor, tmp_path, malformed):
    actor = main_actor([[]]);_original_disable_configured_sources(actor)
    folder = tmp_path / 'invalid-original-source';folder.mkdir()
    original = b'---\nname: invalid-original-source\ndescription: Explicit malformed byte negative\n---\n' + (
        b'actual\0NUL\n' if malformed == 'nul' else b'actual\xffinvalid UTF-8\n')
    file = folder / 'SKILL.md';file.write_bytes(original)
    token = qml(actor, 'Session.assistant.beginSkillSourceSelection()')
    assert token, 'The malformed negative first reaches the actual ordinary current source-selection owner'
    assert not qml(actor, 'Session.assistant.addSkillSource(' + json.dumps(token) + ',' + json.dumps(folder.as_uri()) + ')'), (
        'Real malformed UTF-8/NUL input refuses at original source capture before it can become runtime instructions')
    assert qml(actor, 'Session.assistant.skillSourceError') and not _session_wire(actor, 'thread/start') \
        and not _session_wire(actor, 'turn/start') and file.read_bytes() == original, (
            'Malformed source refusal stays explicit, pre-admission, and preserves the original raw negative evidence')

# PRIVATE / UNRUN seq133. Same-call second alias after the first own write,
# using FIRST ordinary offered-name/path mapping and its measured Undo states.
@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_same_call_two_changed_aliases_and_disabled_constraint_keep_exact_once_prefix_and_undo(main_actor, tmp_path, show_actions):
    actor = main_actor([[]], show_actions=show_actions)
    path = tmp_path / 'ordinary-two-aliases'
    shutil.copytree(ROOT / 'tests/fixtures/constraint_expressions/project', path)
    assert actor.command('open', path=str(path))['reply']['opened'], (
        'Two-alias ownership begins with a complete ordinary independent fixture, not a live specimen or fabricated result')
    actor.until(lambda value: not value['ui']['project']['calculating'])
    wait_positive_tab(actor, 'appBar.tab.analysis');actor.command('click', name='appBar.tab.analysis')
    actor.until(lambda value: any(row['name'] == 'parameters.category' and row['visible'] for row in value['ui']['controls']))
    before, first_aliases, first_parameter, first_unique, first_default, first_undos = \
        _ordinary_changed_alias_reference(actor, 'e11_first_original_alias')
    # Reproduce only the independently measured ordinary first-alias reference
    # so the second reference starts at its actual predecessor, never a postimage.
    model = 'Session.project.analysis.aliases';index = len(before['aliases'])
    assert qml(actor, '(function(){const m=' + model + ';m.append();return m.setText(' + str(index)
        + ',"id","e11_first_original_alias")&&m.setText(' + str(index) + ',"parameter",'
        + json.dumps(first_unique) + ');})()'), (
            'The second ordinary reference begins after the actual first append/id/changed-parameter operations')
    assert actor.command('inspect')['ui']['project']['aliases'] == first_aliases, (
        'The first ordinary alias prefix is reproduced exactly through original setters before measuring the second')
    first_state, expected_aliases, second_parameter, second_unique, second_default, second_undos = \
        _ordinary_changed_alias_reference(actor, 'e11_second_original_alias')
    assert first_state['aliases'] == first_aliases and second_parameter['path'], (
        'The second reference has its own actually offered changed choice and retains the first alias prefix')
    _match_original_alias_undo_sequence(actor, before, first_undos, True)
    marker = 'e11.same-call-two-original-aliases'
    if show_actions:
        _watch_original_offered_choices(actor, marker)
    constraint = {'id': 'e11_explicit_disabled_relation',
        'expression': 'e11_first_original_alias = e11_second_original_alias', 'enabled': False}
    assert constraint['id'] not in {row['id'] for row in before['constraints']}, (
        'The requested disabled constraint has a genuinely new fixture identity, never an assumed live ID')
    call = {'tool': 'add_relations', 'call_id': 'same-call-two-original-aliases',
        'arguments': {'purpose': 'Create both explicitly requested offered aliases and their disabled relation once.',
            'aliases': [{'id': 'e11_first_original_alias', 'path': first_parameter['path']},
                {'id': 'e11_second_original_alias', 'path': second_parameter['path']}],
            'constraints': [constraint]}, 'replay_request_once': True}
    actor.configure_turns([[call]]);actor.connect();_session_request_with_original_disclosure(actor,
        'Create these two exact original aliases and their explicitly disabled relation; retain each ordinary Undo.')
    actor.until(lambda value: bool(actor.responses()) and value['ui']['state'] == 'idle', visible_progress=show_actions)
    result = native_result(actor.responses()[0]);after = actor.command('inspect')['ui']['project']
    assert after['aliases'] == expected_aliases and after['constraints'] == before['constraints'] + [constraint], (
        'The exact second alias and final declared relation survive the first own-write boundary with no silent partial success')
    assert after['parameters'] == before['parameters'], (
        'Explicitly disabled relation declaration preserves every unrelated actual parameter value, uncertainty and free flag')
    sent = [json.loads(line) for line in actor.trace.with_suffix('.sent.jsonl').read_text().splitlines()]
    assert len([row for row in sent if row.get('method') == 'item/tool/call']) == 2 \
        and len(actor.responses()) == 2, (
            'The legal duplicate RPC is actually delivered and settled without executing a second scientific prefix')
    assert actor.responses()[1]['result'] == actor.responses()[0]['result'], (
        'Legal duplicate delivery returns the original settled result without a second ordinary edit')
    physical = []
    if show_actions:
        watcher = _scene_control_expression(marker);qml(actor, '(' + watcher + ').finished=true')
        facts = qml(actor, '(' + watcher + ').facts')
        physical = [row for row in facts if row['kind'] == 'real_delegate_pressed' and row['control'].startswith('alias.parameter.')]
        requested_rows = {'alias.parameter.' + str(len(before['aliases']) + n) for n in (0, 1)}
        assert requested_rows <= {row['control'] for row in physical}, (
            'Each original first and second alias choice reaches its own real offered popup row, not only a cue or first-alias prefix')
        assert all(row['ownerCurrent'] and row['sameWindow'] and row['popupOpened'] and row['popupVisible']
            and row['rowVisible'] and row['searchText'] == row['offered'] == row['rowText'] for row in physical), (
                'Every actual choice is current, same-window, visible and exact at its ordinary physical input boundary')
        actor.command('undo');actor.until(lambda value: not value['ui']['project']['calculating'])
        undone = actor.command('inspect')['ui']['project']
        assert undone['constraints'] == before['constraints'] and undone['aliases'] == expected_aliases \
            and undone['parameters'] == before['parameters'], (
                'The last complete ordinary constraint declaration has its own Undo, leaving both already-applied aliases intact')
        _match_original_alias_undo_sequence(actor, before, second_undos + first_undos, True)
    else:
        _match_original_alias_undo_sequence(actor, before, [], False)
    (actor.folder / 'same-call-two-original-aliases.json').write_text(json.dumps({
        'actual_call': call, 'actual_result': result, 'independent_first_alias': first_aliases,
        'independent_both_aliases': expected_aliases, 'first_ordinary_undos': first_undos,
        'second_ordinary_undos': second_undos, 'actual_physical_choices': physical}, indent=2))
