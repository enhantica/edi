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
            'aliases': [{'id': 'manual_cell', 'parameter': 'phase.cell.length_a'}],
            'constraints': [
                {
                    'id': 'manual_disabled',
                    'expression': 'manual_cell = a + 5.873',
                    'enabled': False,
                }
            ],
        },
    }
    actor = main_actor([[call, call]], show_actions=show_actions)
    project = tmp_path / 'relation-project'
    shutil.copytree(ROOT / 'tests/fixtures/constraint_expressions/project', project)
    assert actor.command('open', path=str(project))['reply']['opened']
    actor.until(lambda row: not row['ui']['project']['calculating'])
    original = actor.last['ui']['project']
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
