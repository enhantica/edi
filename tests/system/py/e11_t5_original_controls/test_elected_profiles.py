"""Full original contract/census escapes; these data controls never qualify a Main run."""

import copy
import hashlib
import json
import os
from pathlib import Path

import pytest

from . import original_profile as profile
from . import test_current_original as controller


def _sample(case_id):
    root = Path(os.environ['EDI_E11_ORIGINAL96_READONLY'])
    assert root.is_absolute(), 'Use the explicit immutable original96 custody root'
    path = root / controller.REGISTRY[case_id]['original96_folder']
    raw = (path / 'intentional-qml-contract-assessment.json').read_bytes()
    custody = json.loads(Path(__file__).with_name('original96_samples.json').read_text())
    assert hashlib.sha256(raw).hexdigest() == custody[case_id], 'Never sample current output'
    facts = json.loads(raw)
    assert facts['body_failed'] is False and facts['host_exit'] == 0
    mapping = json.loads(Path(__file__).with_name('action_line_map.json').read_text())
    for scope in facts['scopes']:
        scope['step'] = mapping.get(scope['step'], scope['step'])
    case = controller.REGISTRY[case_id]
    _case, contract = controller.elected_case(case['function'], case['arguments'])
    return facts, contract


@pytest.mark.parametrize(
    'case_id',
    [
        'browser_open',
        'browser_restore_owner',
        'browser_retire_account',
        'browser_leave_null',
        'browser_footer',
        'composer_null_publication',
    ],
)
def test_complete_original96_data_matches_only_its_elected_original_contract(case_id):
    facts, contract = _sample(case_id)
    assert not controller.ERRORS.assess_qml_contract(
        facts['events'], facts['scopes'], contract, facts['stderr']
    ), 'Synthetic exact-data check only; original96 remains its actual failed run'


@pytest.mark.parametrize(
    'escape',
    [
        'missing',
        'extra',
        'wrong_source',
        'wrong_owner',
        'wrong_step',
        'cross_case',
        'missing_raw',
        'ambiguous_raw_suffix',
    ],
)
def test_full_composer_contract_refuses_independent_receipt_escapes(escape):
    facts, contract = _sample('composer_null_publication')
    warning = next(row for row in facts['events'] if row['event'] == 'warning')
    if escape == 'missing':
        facts['events'].remove(warning)
    elif escape == 'extra':
        facts['events'].insert(-1, dict(warning))
    elif escape == 'wrong_source':
        warning['url'] = 'qrc:/unrelated/AssistantComposer.qml'
    elif escape == 'wrong_owner':
        warning['object_available'] = True
        warning['object_name'] = 'unrelated-owner'
    elif escape == 'wrong_step':
        contract['expected'][0]['step'] += ':unrelated'
    elif escape == 'cross_case':
        _other, contract = _sample('browser_open')
    elif escape == 'missing_raw':
        facts['stderr'] = facts['stderr'].replace(warning['rendered'] + '\n', '', 1)
    else:
        facts['stderr'] += 'unreviewed prefix: ' + warning['rendered'] + '\n'
    assert controller.ERRORS.assess_qml_contract(
        facts['events'], facts['scopes'], contract, facts['stderr']
    ), 'Every attempted full-contract escape must be refused'


def _declared_profile():
    case = controller.REGISTRY['browser_restore_owner']
    ui = dict.fromkeys(['alive', 'singleton_identity', 'engine_parent', 'cpp_ownership'], True)
    ui['available_efforts'] = ['medium']
    ui['controls'] = [{'name': name} for name in profile.CHOICE_NAMES]
    ui['controls'] += [{'name': 'assistant.session.archive.' + str(i)} for i in range(2)]
    requests = [{'id': 'model-witness', 'method': 'model/list'}]
    responses = [
        {
            'id': 'model-witness',
            'result': {'data': [copy.deepcopy(profile.MODEL)], 'nextCursor': None},
        }
    ]
    return case, ui, requests, responses


def test_source_declared_model_and_retained_delegate_profile_is_an_armed_control():
    case, ui, requests, responses = _declared_profile()
    profile.require_census(ui, case)
    profile.require_model_wire(requests, responses)


@pytest.mark.parametrize('escape', ['missing', 'extra', 'duplicate', 'cross_case', 'effort'])
def test_closed_profile_refuses_missing_extra_stale_and_cross_case_delegates(escape):
    case, ui, _requests, _responses = _declared_profile()
    if escape == 'missing':
        ui['controls'].pop()
    elif escape == 'extra':
        ui['controls'].append({'name': 'assistant.choice.effort.value.high'})
    elif escape == 'duplicate':
        ui['controls'].append(dict(ui['controls'][0]))
    elif escape == 'cross_case':
        case = controller.REGISTRY['browser_footer']
    else:
        ui['available_efforts'] = ['high']
    with pytest.raises(AssertionError):
        profile.require_census(ui, case)


@pytest.mark.parametrize('escape', ['changed_model', 'missing_reply', 'duplicate_reply'])
def test_wire_profile_refuses_changed_model_or_unproven_genuine_reply(escape):
    _case, _ui, requests, responses = _declared_profile()
    if escape == 'changed_model':
        responses[0]['result']['data'][0]['supportedReasoningEfforts'].append({
            'reasoningEffort': 'high',
            'description': 'different population',
        })
    elif escape == 'missing_reply':
        responses.clear()
    else:
        responses.append(copy.deepcopy(responses[0]))
    with pytest.raises(AssertionError):
        profile.require_model_wire(requests, responses)


def test_unqualified_case_cannot_reuse_a_neighbouring_elected_contract():
    case = controller.REGISTRY['browser_restore_owner']
    with pytest.raises(AssertionError):
        controller.elected_case(case['function'], {'activation_effect': 'unqualified'})


@pytest.mark.parametrize('escape', ['declared_positive', 'extra_model', 'wrong_turns', 'fake_row'])
def test_peer_population_is_closed_before_the_armed_census(escape):
    case = controller.REGISTRY['browser_restore_owner']
    folder = Path('/explicit-source-only-peer-profile')
    peer = {
        'turns': [[], []],
        'trace': str(folder / 'wire.jsonl'),
        'final_text': controller.ACTUAL.FINAL,
        'session_fixture': {'threads': [], 'page_size': 12},
    }
    if escape == 'extra_model':
        peer['fixture_models'] = [copy.deepcopy(profile.MODEL)]
    elif escape == 'wrong_turns':
        peer['turns'] = [[]]
    elif escape == 'fake_row':
        peer['session_fixture']['threads'] = [{'id': 'invented'}]
    else:
        profile.require_peer(peer, case, folder, controller.ACTUAL.FINAL)
        return
    with pytest.raises(AssertionError):
        profile.require_peer(peer, case, folder, controller.ACTUAL.FINAL)


def test_stale_binary_profile_refuses_before_a_host_can_start(tmp_path, monkeypatch):
    changed = tmp_path / 'stale-binary-bond.json'
    changed.write_text('{}\n')
    monkeypatch.setenv('EDI_E11_ORIGINAL_BINARY_BOND', str(changed))
    with pytest.raises(AssertionError, match='Exact original baseline87'):
        controller._source_inputs()


def test_actual101_compact_model_packet_is_not_a_current_full_scene():
    raw = Path(__file__).with_name('original101_compact_packet.json').read_bytes()
    assert (
        hashlib.sha256(raw).hexdigest()
        == '058c0c36659f0fe23f0be77a0736bb09826bce7434912a778ea5ec77985d3579'
    )
    packet = json.loads(raw)
    with pytest.raises(KeyError, match='singleton_identity'):
        profile.require_census(packet['ui'], controller.REGISTRY['browser_footer'])
