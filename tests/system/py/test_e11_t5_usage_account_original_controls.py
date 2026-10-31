"""Canonical usage/account relations in explicit fresh original and native cohorts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
import test_e11_t5_dev_native_integration as base

ROOT = Path(__file__).resolve().parents[3]
main_actor = base.main_actor
HERE = Path(__file__).resolve().parent
CASES = json.loads((HERE / 'e11_t5_usage_canonical_cases.json').read_text())


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bound_receipt(variable):
    path = Path(os.environ[variable]).resolve(strict=True)
    expected = os.environ[variable + '_SHA256']
    assert len(expected) == 64 and all(character in '0123456789abcdef' for character in expected)
    assert _sha(path) == expected
    return json.loads(path.read_text())


def _phase():
    phase = json.loads((HERE / 'e11_t5_usage_canonical_phase.json').read_text())
    assert phase['binding_status'] == 'BOUND', 'Root must bind the completed fresh comparison'
    assert phase['namespace'] == 'fresh-usage-original-native'
    assert phase['phase'] in {'original', 'native'}
    assert os.environ['EDI_E11_USAGE_ACCOUNT_PHASE'] == phase['phase']
    assert (
        Path(base.__file__).resolve()
        == ROOT / 'tests/system/py/test_e11_t5_dev_native_integration.py'
    )
    files = phase['files']
    for path, expected in files.items():
        assert _sha(ROOT / path) == expected, path
    bond = _bound_receipt('EDI_E11_USAGE_ACCOUNT_BINARY_BOND')
    original = _bound_receipt('EDI_E11_USAGE_ACCOUNT_ORIGINAL_BINARY_BOND')
    assert original['source'] == phase['original_source']
    assert bond['source'] == phase['compiled_source']
    assert (
        os.environ['EDI_E11_USAGE_ACCOUNT_ORIGINAL_BINARY_BOND_SHA256']
        == phase['original_bond_sha256']
    )
    original_families = {
        'activity': 'native',
        'composer': 'native',
        'browser': 'native',
        'usage': 'original',
    }
    assert original['family_phases'] == original_families
    assert bond['family_phases'] == {**original_families, 'usage': phase['phase']}
    for name, expected in phase['native'].items():
        assert original['native'][name] == expected, name
        assert bond['native'][name] == expected, name
    assert original['bundled_runtime']['config_sha256'] == phase['original_runtime_config_sha256']
    assert bond['bundled_runtime']['config_sha256'] == phase['current_runtime_config_sha256']
    if phase['phase'] == 'original':
        assert bond == original
    else:
        expected = os.environ['EDI_E11_USAGE_ACCOUNT_COMPILED_SOURCE']
        assert len(expected) == 40 and all(
            character in '0123456789abcdef' for character in expected
        )
        assert bond['source'] == expected == phase['compiled_source']
    assert (
        bond['selected_header_sha256'] == files['tests/unit/app/e11_t5_a2a_phase_adapter_impl.hpp']
    )
    for path in (
        'app/qml/Components/AssistantPanel.qml',
        'app/qml/Components/AssistantComposer.qml',
        'app/src/app_info.cpp',
        'app/src/assistant_view_model.cpp',
        'tests/integration/py/assistant_ui_probe/probe.cpp',
    ):
        assert bond['compiled_sources'][path] == files[path], path
    for section, keys in {
        'compiler_kit': ['compiler_sha256', 'package_metadata'],
        'dependency_environment': ['root_lock_sha256', 'dependency_only_lock_sha256'],
        'gui_components': ['commit', 'pin_file_sha256', 'source_sha256'],
        'bundled_runtime': ['files'],
    }.items():
        for key in keys:
            assert bond[section][key] == original[section][key], (section, key)
    assert (
        _sha(Path(os.environ['EDI_ASSISTANT_UI_PROBE']))
        == (bond['binaries']['assistant_real_owner_probe']['sha256'])
    )
    assert os.environ['EDI_E11_T5_A2A_PHASE'] == 'native'
    return phase


def _retain(actor, name, value):
    # JSON escapes preserve original lone UTF16 units. Encode BEFORE opening/truncating.
    encoded = (json.dumps(value, ensure_ascii=True, indent=2) + '\n').encode('utf-8')
    written = (actor.folder / (name + '.json')).write_bytes(encoded)
    if written != len(encoded):
        raise OSError('JSON capture was not fully written')
    return value


def _observe(actor, phase, stage):
    source = (HERE / 'e11_t5_usage_canonical_observer.js').read_text()
    call = phase['allowance_call']
    source = source.replace('SESSION_CALL', call.replace('MINUTES', '300'))
    source = source.replace('WEEKLY_CALL', call.replace('MINUTES', '10080'))
    source = source.replace('STRING_CALL', call.replace('MINUTES', "'300'"))
    envelope = actor.command('evaluate', expression='JSON.stringify(' + source + ')')
    _retain(actor, stage + '-raw', {'observer': source, 'envelope': envelope})
    value = json.loads(envelope['reply']['value'])
    _retain(actor, stage, value)
    assert value['problems'] == []
    assert all(
        envelope['ui'][key]
        for key in (
            'singleton_identity',
            'engine_parent',
            'cpp_ownership',
        )
    )
    assert value['owner'] and value['imported_info']
    return value


def _usage_ready(actor):
    actor.until(lambda _row: base.qml(actor, 'Session.assistant.usage.state') == 'ready')


def _open_usage(actor):
    actor.command('click', name='assistant.usage')
    actor.until(
        lambda _row: base.qml(actor, base.control_expression('assistant.usageDialog') + '.opened')
    )
    _usage_ready(actor)


def _check_selection(value, expected):
    assert value['usage'] == value['canonical'] and value['plain_projection']
    assert value['usage']['available'] and not value['usage']['stale']
    assert value['usage']['state'] == 'ready' and not value['usage']['loading']
    assert [row['id'] for row in value['usage']['buckets']] == expected['bucket_ids']
    for key in ('global', 'remaining', 'session_path', 'weekly_path', 'button', 'caption'):
        assert value[key] == expected[key], key
    assert value['accessible'] == expected['caption']
    assert value['independent_session'] and value['independent_weekly']
    assert value['strict_string_duration']
    rows = value['rows']
    assert [row['key'] for row in rows] == expected['descriptors']
    assert [row['percent'] for row in rows] == expected['percent']
    descriptors = {
        'session': {'title': 'Session limit', 'minutes': 300, 'key': 'session'},
        'weekly': {'title': 'Weekly', 'minutes': 10080, 'key': 'weekly'},
    }
    assert [row['descriptor'] for row in rows] == [
        descriptors[key] for key in expected['descriptors']
    ]
    assert all(row['selected_member'] for row in rows)
    assert all(
        row['current']
        and row['visible']
        and row['percent_current']
        and row['reset_current']
        and row['reset'] == 'Reset unavailable'
        for row in rows
    )
    assert [row['sceneY'] for row in rows] == sorted(row['sceneY'] for row in rows)
    if rows:
        assert not value['status']['visible']
    else:
        assert value['status'] == {
            'visible': True,
            'text': 'Session and weekly usage were not reported.',
        }


def _check_account_projection(value, case, expected):
    public = {key: case['account'][key] for key in ('email', 'planType') if key in case['account']}
    assert value['account'] == public and value['canonical_account'] == public
    for key in ('plan', 'plan_label', 'initial'):
        assert value[key] == expected[key], key
    assert value['connection'] == expected['initial']


def _account_display(actor, expected):
    actor.command('manual_key', key='escape')
    actor.until(
        lambda _row: (
            not base.qml(actor, base.control_expression('assistant.usageDialog') + '.visible')
        )
    )
    actor.command('click', name='assistant.connection')
    actor.until(
        lambda _row: base.qml(
            actor, base.control_expression('assistant.accountDialog') + '.opened'
        )
    )
    source = """(function(){const all=testAppObjects.snapshot();
        function one(name){const a=all.filter(x=>Qt.isQtObject(x)&&x.objectName===name);
            return a.length===1?a[0]:null;}
        const identity=one('assistant.accountIdentity'),plan=one('assistant.accountPlan');
        const dialog=one('assistant.accountDialog');
        function current(item){if(!item||!dialog)return false;
            for(let p=item;p;p=p.parent)if(p===dialog.contentItem)
                return item.Window.window===window;return false;}
        return {identity:identity?identity.text:null,
            identity_plain:!!identity&&identity.textFormat===Text.PlainText,
            identity_visible:!!identity&&identity.visible,identity_current:current(identity),
            plan:plan?plan.text:null,
            plan_plain:!!plan&&plan.textFormat===Text.PlainText,plan_visible:!!plan&&plan.visible,
            plan_current:current(plan)};})()"""
    envelope = actor.command('evaluate', expression='JSON.stringify(' + source + ')')
    _retain(actor, 'account-visible-raw', envelope)
    value = json.loads(envelope['reply']['value'])
    _retain(actor, 'account-visible', value)
    assert value == {
        'identity': expected['identity'],
        'identity_plain': True,
        'identity_visible': True,
        'identity_current': True,
        'plan': expected['plan_label'],
        'plan_plain': True,
        'plan_visible': expected['plan_visible'],
        'plan_current': True,
    }
    assert not any(
        'NEVER_ACCOUNT_DISPLAY_269' in row['display']
        for row in envelope['ui']['texts']
        if row['visible']
    )


def _wire_proof(actor, case):
    wire = base._session_wire(actor)
    sent_path = actor.trace.with_suffix('.sent.jsonl')
    sent = [json.loads(line) for line in sent_path.read_text().splitlines()]
    _retain(actor, 'canonical-wire-proof', {'wire': wire, 'sent': sent})
    account_requests = [row for row in wire if row.get('method') == 'account/read']
    usage_requests = [row for row in wire if row.get('method') == 'account/rateLimits/read']
    assert account_requests and usage_requests
    account_results = [
        row['result']
        for row in sent
        if row.get('id') == account_requests[0]['id'] and 'result' in row
    ]
    assert account_results == [{'account': case['account'], 'requiresOpenaiAuth': False}]
    assert any(
        row.get('id') in {request['id'] for request in usage_requests}
        and row.get('result') == case['usage']
        for row in sent
    )
    if 'update' in case:
        assert any(
            row.get('id') in {request['id'] for request in usage_requests}
            and row.get('result') == case['update']
            for row in sent
        )
    assert not any(row.get('method') == 'turn/start' for row in wire)


@pytest.mark.parametrize('case', CASES, ids=[case['id'] for case in CASES])
def test_original_canonical_usage_selection_account_and_visible_labels(main_actor, case):
    phase = _phase()
    actor = main_actor([[]])
    _retain(
        actor,
        'explicit-original-qualification-inputs',
        {
            'phase': phase,
            'current_bond': os.environ['EDI_E11_USAGE_ACCOUNT_BINARY_BOND'],
            'current_bond_sha256': os.environ['EDI_E11_USAGE_ACCOUNT_BINARY_BOND_SHA256'],
            'original_bond': os.environ['EDI_E11_USAGE_ACCOUNT_ORIGINAL_BINARY_BOND'],
            'original_bond_sha256': os.environ[
                'EDI_E11_USAGE_ACCOUNT_ORIGINAL_BINARY_BOND_SHA256'
            ],
        },
    )
    base._session_configure(
        actor,
        session_fixture={'threads': [], 'page_size': 12},
        fixture_account_read_reply={'account': case['account'], 'requiresOpenaiAuth': False},
        fixture_usage_default_response={'result': case['usage']},
    )
    base.wait_positive_tab(actor, 'appBar.tab.project')
    actor.command('click', name='appBar.tab.project')
    actor.connect()
    _usage_ready(actor)
    _open_usage(actor)
    value = _observe(actor, phase, 'initial-canonical-presentation')
    _check_selection(value, case['expected'])
    _check_account_projection(value, case, case['expected'])
    expected = case['expected']
    if 'update' in case:
        before = len(base._session_wire(actor, 'account/rateLimits/read'))
        base._session_configure(actor, fixture_usage_default_response={'result': case['update']})
        actor.command('refresh_usage')
        actor.until(
            lambda _row: len(base._session_wire(actor, 'account/rateLimits/read')) > before
        )
        _usage_ready(actor)
        value = _observe(actor, phase, 'updated-canonical-presentation')
        expected = case['expected_update']
        _check_selection(value, expected)
        _check_account_projection(value, case, expected)
    _account_display(actor, expected)
    _wire_proof(actor, case)
    assert _phase() == phase, 'Exact source/phase/binary input custody remains unchanged'
