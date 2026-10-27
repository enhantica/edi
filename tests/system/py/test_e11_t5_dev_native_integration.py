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
        assert not self.trace.exists(), 'Only the unstarted offline peer may be configured'
        path = self.folder / 'peer.json'
        value = json.loads(path.read_text(encoding='utf-8'))
        value['turns'] = turns
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


def test_unsaved_native_work_reports_unavailable_without_autosave_or_appdata_fallback(main_actor):
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
    assert not list(Path(actor.last['test_storage']).rglob('work-report.json')), (
        'Unsaved scientific diagnostics cannot fall back to unrelated app-data storage'
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
    project_name = 'e11_native_create_' + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    destination = documents / project_name
    assert not destination.exists(), (
        'The native ordinary Create action owns creating its previously absent project destination'
    )
    offered = {row['name']: row for row in actor.command('tool_specs')['reply']['tools']}
    schema = offered['create_project']['inputSchema']
    assert set(schema['required']) == {'purpose'} and set(schema['properties']) == {
        'purpose', 'name', 'description'
    }, 'Normal current-session Create exposes only ordinary name and description metadata'
    cif = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    token = actor.command('selected_begin')['reply']['token']
    assert actor.command('selected_add', token=token, paths=[str(cif)])['reply']['added'], (
        'The empty current Session admits the genuine published selected CIF before native Create'
    )
    selected = actor.last['ui']['selected_files']
    assert len(selected) == 1 and selected[0]['id'], (
        'Native Create and subsequent import retain the actually admitted selected-input identity'
    )
    actor.configure_turns([[
        tool_call('create_project', 'ordinary-empty-create', name=project_name,
                  description='Independent ordinary Create continuation'),
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
            and created['name'] == project_name and Path(created['path']) == destination), (
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
        assert any(row['kind'] == 'mouse_press' and row['dialog_visible']
                   and row['dialog_name'] == project_name and row.get('confirm_contains_press')
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


def test_fresh_actual_main_has_no_startup_report_capacity_failure(main_actor):
    actor = main_actor([[]])
    assert not actor.last['ui']['project'], (
        'The independent startup-report check observes the actual empty current Main Session'
    )
    diagnostics = {key: actor.last['ui'][key] for key in ('last_error', 'messages')}
    assert 'report_capacity' not in json.dumps(diagnostics), (
        'Optional diagnostic setup cannot emit a report-capacity failure before any assistant work'
    )
