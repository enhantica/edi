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
            if 'ui_sequence' in value.get('ui', {}):
                (self.folder / 'ui-sequence.json').write_text(json.dumps(value['ui']['ui_sequence'], indent=2))
            return value
        raise AssertionError(f'No actual observation returned for {op}')

    def until(self, predicate, *, seconds=10):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            value = self.command('inspect')
            if predicate(value):
                return value
        raise AssertionError(
            'The actual native lifecycle did not settle: ' + json.dumps(self.last)
        )

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
    return actor.command('evaluate', expression=expression)['reply']['value']


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
    token = actor.command('selected_begin')['reply']['token']
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
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle')
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
    token = actor.command('selected_begin')['reply']['token']
    assert actor.command('selected_add', token=token, paths=[str(path)])['reply']['added']
    actor.connect()
    actor.request('Add the structure manually without loading the attached CIF. Use a=6.173.')
    actor.until(lambda row: len(actor.responses()) == 2 and row['ui']['state'] == 'idle')
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
    actor.configure_turns([[call, call]])
    actor.connect()
    actor.request()
    actor.until(
        lambda row: bool(actor.responses()) and row['ui']['state'] in {'idle', 'interrupted'}
    )
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
    actor.until(lambda row: len(actor.responses()) == 2 and row['ui']['state'] == 'idle')
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
    token = actor.command('selected_begin')['reply']['token']
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
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle')
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
    assert 'storage_root_unavailable' in json.dumps(cached), (
        'The diagnostic cache preserves the real missing project-report-root limitation'
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
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle')
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
    )
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
    actor.command('arm_estimate_publication', mode=mode)
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
    actor.until(lambda row: len(actor.responses()) == 2 and row['ui']['state'] == 'idle')
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
    token = actor.command('selected_begin')['reply']['token']
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
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle')
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
    actor.until(lambda row: len(actor.responses()) == len(calls) and row['ui']['state'] == 'idle')
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
        )
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
    project = copied_estimate_project(tmp_path)
    # Current-dev categories retain an out-of-profile stored free term, shown
    # disabled for fitting while its flag can still be cleared (ADR0053).
    with (project / 'experiments/bank.edi').open('a') as output:
        output.write('\n_peak.broad_gauss_sigma_0 1.123()\n')
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
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle')
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
    actor.until(lambda row: bool(actor.responses()) and row['ui']['state'] == 'idle')
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
    actor.until(lambda row: len(actor.responses()) == 3 and row['ui']['state'] == 'idle')
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
        assert pointers and all(not row['assistant_visible'] and not row['assistant_selected'] for row in pointers), (
            'Show ON selects the real normal sidebar before locating or cueing its Create control'
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
    assert actor.command('open', path=str(destination))['reply']['opened'], (
        'Independent ordinary reopen reads the genuinely saved new current project'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert actor.last['ui']['project']['structure_rows'] == rows, (
        'Normal current Save conserves the actual imported structure through independent ordinary reopen'
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
    actor.until(lambda row: len(actor.responses()) == 1 and row['ui']['state'] == 'idle')
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
    actor.command('click', name='appBar.tab.structure')
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
    actor.request('Fit the current independent polynomial background using its existing free parameters.')
    actor.until(lambda row: len(actor.responses()) == 1 and row['ui']['state'] == 'idle')
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
        assert pointers and all(not row['assistant_visible'] and not row['assistant_selected'] for row in pointers), (
            'The Show ON Fit operation exposes the real normal sidebar before current-control presentation'
        )
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
    assert context['mosaic_distribution_options'] == distributions == ['gaussian', 'lorentzian'], (
        'Native mosaic choices preserve the original ordinary SC distribution tokens'
    )
    experiment = context['id']
    choices = [token for token in expected if token != context['extinction_type']]
    actor.configure_turns([[tool_call('edit_experiment', 'sc-family-' + str(i),
        experiment=experiment, operation='extinction_type', value=token)] for i,token in enumerate(choices)])
    actor.connect()
    for index, token in enumerate(choices):
        actor.request('Select the requested supported extinction family through its ordinary app owner.')
        actor.until(lambda row: len(actor.responses()) == index + 1 and row['ui']['state'] == 'idle')
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
    original_distribution = qml(scalar, 'Session.project.currentExperiment.mosaicDistribution')
    changed_distribution = next(token for token in distributions if token != original_distribution)
    scalar.configure_turns([[
        tool_call('edit_experiment', 'current-sc-distribution', experiment=experiment,
                  operation='mosaic_distribution', value=changed_distribution),
        tool_call('set_parameters', 'direct-mm-input', values=[{'path': radius['path'], 'value': 3.0}]),
    ]])
    scalar.connect()
    scalar.request('Set the crystal size field directly to 3 mm and keep it fixed.')
    scalar.until(lambda row: len(scalar.responses()) == 2 and row['ui']['state'] == 'idle')
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
    actor.until(lambda row: len(actor.responses()) == 3 and row['ui']['state'] == 'idle')
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
    actor.until(lambda row: len(actor.responses()) == 4 and row['ui']['state'] == 'idle')
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
    cif, measured = attachment_root / 'tbti.cif', attachment_root / 'heidi.dat'
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
    actor.until(lambda row: len(actor.responses()) == 3 and row['ui']['state'] == 'idle')
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
    actor.until(lambda row: len(actor.responses()) == 4 and row['ui']['state'] == 'idle')
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
    actor.until(lambda row: len(actor.responses()) == 5 and row['ui']['state'] == 'idle')
    actual_id = native_result(actor.responses()[-1])['datasets'][0]['id']
    actor.append_turn([tool_call('load_data', 'fresh-sc-native-reflections',
                                experiment=actual_id, file_id=ids[measured.name])])
    actor.request('Load the genuine selected measured reflections into that current experiment.')
    actor.until(lambda row: len(actor.responses()) == 6 and row['ui']['state'] == 'idle')
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
    actor.until(lambda row: len(actor.responses()) == len(invalid) and row['ui']['state'] == 'idle')
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
