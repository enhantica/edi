"""Canonical usage/account relations in explicit fresh original and native cohorts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
from pathlib import Path

import pytest
import test_e11_t5_dev_native_integration as base

ROOT = Path(__file__).resolve().parents[3]
main_actor = base.main_actor
HERE = Path(__file__).resolve().parent
CASES = json.loads((HERE / 'e11_t5_usage_canonical_cases.json').read_text())


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _absolute(value):
    path = Path(value)
    assert path.is_absolute(), 'Comparison custody requires an explicit absolute input'
    return path.resolve(strict=True)


USAGE_HEADER = 'tests/unit/app/e11_t5_usage_account_phase.hpp'
USAGE_HEADER_HASHES = {
    'native': 'b726b7b713befaf6cd278810f39985ce65c4caebbc30b4b88a944758fb6305bc',
    'original': '88a78241a487ff474a833b82e57c5ed3aab0cd594b7e8526194d310f4426c22d',
}
ACTIVITY_HEADER_SHA256 = '07cddf1a8fa777efac7c92a5133c3a1f659a2a5966495ef30d538b1905d946fe'
ACTIVITY_ADAPTER_SHA256 = '12a9d9eab412576680cef19a8f0b74ec176e011413f54ad6abd561c31b362e9d'
PROBE_SOURCE_SHA256 = '5cace5b63a55b0b373848242d63646121e4532f4a7071d8ac6a4c3e68930bd5c'
ACTIVITY_INPUTS = {
    'tests/unit/app/e11_t5_a2a_phase_adapter_impl.hpp': ACTIVITY_HEADER_SHA256,
    'tests/unit/app/e11_t5_a2a_phase_adapter.hpp': ACTIVITY_ADAPTER_SHA256,
    'tests/unit/app/e11_t5_test_inputs.hpp': (
        '94ff6f84183d464f9c0079a0b1db58a58274831f3bb286cfa0712a99061a6ad5'
    ),
    'tests/integration/py/assistant_ui_probe/probe.cpp': PROBE_SOURCE_SHA256,
}
CALLER_KEYS = {
    'graph/app/.rcc/qmlcache/edi_app_module_qml_Components_AssistantComposer_qml.cpp',
    'graph/app/.rcc/qmlcache/edi_app_module_qml_Components_AssistantPanel_qml.cpp',
}


def _compiled_phase_inputs(bond, usage_phase):
    _usage_header_input(bond, usage_phase)
    _activity_source_inputs(bond)
    _activity_object_input(bond)


def _usage_header_input(bond, usage_phase):
    source, graph = _absolute(bond['root']), _absolute(bond['real_build_root'])
    selected = bond['selected_header']
    expected = USAGE_HEADER_HASHES[usage_phase]
    assert _absolute(selected['path']) == source / USAGE_HEADER, 'Required:  usage header input.'
    assert selected['sha256'] == bond['selected_header_sha256'] == expected, (
        'Required:  usage header input.'
    )
    assert _sha(_absolute(selected['path'])) == expected, 'Required:  usage header input.'
    usage_object = (
        'app/CMakeFiles/edi_app_tests.dir/__/tests/unit/app/test_e11_t5_usage_account.cpp.o'
    )
    assert selected['object'] == usage_object, 'The selected header belongs to the usage unit'
    assert selected['selected_targets'] == ['edi_app_tests'], 'Required:  usage header input.'
    assert _sha(graph / usage_object) == selected['object_sha256'], (
        'Required:  usage header input.'
    )
    dependencies = selected['dependency_record']
    assert (
        hashlib.sha256(dependencies.encode()).hexdigest() == selected['dependency_record_sha256']
    ), 'Required:  usage header input.'
    assert '(VALID)' in dependencies.splitlines()[0], 'Required:  usage header input.'
    assert str(source / USAGE_HEADER) in {
        line.strip() for line in dependencies.splitlines()[1:]
    }, 'Required:  usage header input.'


def _activity_source_inputs(bond):
    source = _absolute(bond['root'])
    built = bond['build_observation']['data']
    for relative, digest in ACTIVITY_INPUTS.items():
        row = built['source_inputs'][relative]
        assert _absolute(row['path']) == source / relative, 'Required:  activity source inputs.'
        assert row['sha256'] == _sha(_absolute(row['path'])) == digest, (
            ('Required:  activity source inputs.'),
            relative,
        )
    probe_source = 'tests/integration/py/assistant_ui_probe/probe.cpp'
    assert bond['compiled_sources'][probe_source] == ACTIVITY_INPUTS[probe_source], (
        'Required:  activity source inputs.'
    )


def _activity_object_input(bond):
    graph = _absolute(bond['real_build_root'])
    built = bond['build_observation']['data']
    activity_object = 'assistant-ui-probe/CMakeFiles/assistant_real_owner_probe.dir/probe.cpp.o'
    object_path = graph / activity_object
    witness = built['object_witnesses'][activity_object]
    assert _absolute(witness['path']) == object_path, 'Required:  activity object input.'
    assert _sha(object_path) == witness['sha256'], 'Required:  activity object input.'
    target = 'assistant_real_owner_probe'
    record = built['active_target_input_records'][target]
    assert _sha(_absolute(record['path'])) == record['sha256'], 'Required:  activity object input.'
    assert record['sha256'] == bond['active_target_inputs'][target]['record_sha256'], (
        'Required:  activity object input.'
    )
    inputs = _absolute(record['path']).read_text().splitlines()
    assert str(object_path) in {str((graph / value).resolve()) for value in inputs if value}, (
        'Required:  activity object input.'
    )
    _activity_compile_command(bond, graph, object_path)


def _activity_compile_command(bond, graph, object_path):
    database = bond['native_consumer_graph']
    commands = _absolute(database['compile_commands'])
    assert _sha(commands) == database['compile_commands_sha256'], (
        'Required:  activity compile command.'
    )
    probe_source = _absolute(bond['root']) / 'tests/integration/py/assistant_ui_probe/probe.cpp'
    rows = [row for row in json.loads(commands.read_text()) if Path(row['file']) == probe_source]
    assert len(rows) == 1, 'Activity has one genuine owning probe translation unit'
    arguments = shlex.split(rows[0]['command'])
    output = Path(arguments[arguments.index('-o') + 1])
    assert _absolute(rows[0]['directory']) == graph, 'Required:  activity compile command.'
    assert (graph / output).resolve() == object_path, 'Required:  activity compile command.'


def _compiled_callers(bond, bond_hash, record, registry_path):
    expected = record['generated_inputs']
    assert set(expected) == CALLER_KEYS, 'Both actual Composer/Panel caller units are mandatory'
    for key, digest in expected.items():
        assert isinstance(digest, str) and len(digest) == 64, (
            'This boundary requires isinstance(digest, str) and len(digest) == 64'
        )
        observed = bond['generated_inputs'][key]
        assert observed['sha256'] == digest, (
            "This boundary requires observed['sha256'] == digest",
            key,
        )
        assert _sha(_absolute(observed['path'])) == digest, (
            "This boundary requires _sha(_absolute(observed['path'])) == digest",
            key,
        )
    reference = record['source_proof']
    path = _absolute(reference['path'])
    assert _sha(path) == reference['sha256'], 'Caller attribution is an immutable source proof'
    proof = json.loads(path.read_text())
    assert proof['bond_sha256'] == bond_hash, (
        "This boundary requires proof['bond_sha256'] == bond_hash"
    )
    assert proof['compiled_source'] == bond['source'] and proof['compiled_tree'] == bond['tree'], (
        "This boundary requires proof['compiled_source'] == bond['source'] and "
        "proof['compiled_tree'] == bond['tree']"
    )
    assert proof['family_phases'] == bond['family_phases'], (
        "This boundary requires proof['family_phases'] == bond['family_phases']"
    )
    assert proof['generated_inputs'] == expected, (
        "This boundary requires proof['generated_inputs'] == expected"
    )
    assert proof['case_registry_sha256'] == _sha(registry_path), (
        "This boundary requires proof['case_registry_sha256'] == _sha(registry_path)"
    )
    assert proof['cases'] == json.loads(registry_path.read_text()), (
        'Source attribution covers the complete exact six-case registry, not only generated hashes'
    )


def _bound_receipt(variable):
    path = Path(os.environ[variable]).resolve(strict=True)
    expected = os.environ[variable + '_SHA256']
    assert len(expected) == 64 and all(
        character in '0123456789abcdef' for character in expected
    ), (
        'This boundary requires len(expected) == 64 and all((character in '
        "'0123456789abcdef' for character in expected))"
    )
    assert _sha(path) == expected, 'This boundary requires _sha(path) == expected'
    return json.loads(path.read_text())


def _mount_native_phase():
    assert os.environ['EDI_E11_USAGE_ACCOUNT_PHASE'] == 'native', (
        'The current mount invocation must explicitly select the native source phase'
    )
    assert _absolute(os.environ['EDI_E11_USAGE_ACCOUNT_SOURCE_ROOT']) == ROOT, (
        'The current mount invocation must name this actual test source checkout'
    )
    header = ROOT / USAGE_HEADER
    assert _sha(header) == USAGE_HEADER_HASHES['native'], (
        'The current mount uses the declared native adapter, never an inferred original phase'
    )
    declared = re.search(r'panelHash\(\).*?"([0-9a-f]{64})"', header.read_text())
    assert declared and _sha(ROOT / 'app/qml/Components/AssistantPanel.qml') == declared[1], (
        'The current native Panel must match its explicitly declared adapter source'
    )
    probe = _absolute(os.environ['EDI_ASSISTANT_UI_PROBE'])
    assert probe == _absolute(ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe'), (
        'The current mount check uses its own ordinary native graph, not a foreign cohort'
    )
    expected = os.environ['EDI_E11_USAGE_ACCOUNT_PROBE_SHA256']
    assert len(expected) == 64 and _sha(probe) == expected, (
        'The native mount invocation must retain the exact selected probe executable'
    )
    return {
        'phase': 'native',
        'scope': 'current_native_mount',
        'allowance_call': 'p.allowanceWindow(MINUTES)',
        'source_root': str(ROOT),
        'header_sha256': _sha(header),
        'panel_sha256': declared[1],
        'probe': str(probe),
        'probe_sha256': expected,
    }


def _phase():
    if os.environ.get('EDI_E11_USAGE_ACCOUNT_MODE') == 'mount-native':
        return _mount_native_phase()
    phase = json.loads((HERE / 'e11_t5_usage_canonical_phase.json').read_text())
    assert phase['binding_status'] == 'BOUND', 'Root must bind the completed fresh comparison'
    assert phase['caller_binding_status'] == 'BOUND', 'Both fresh caller maps require source proof'
    assert phase['namespace'] == 'fresh-usage-original-native', (
        "This boundary requires phase['namespace'] == 'fresh-usage-original-native'"
    )
    assert phase['phase'] in {'original', 'native'}, (
        "This boundary requires phase['phase'] in {'original', 'native'}"
    )
    assert os.environ['EDI_E11_USAGE_ACCOUNT_PHASE'] == phase['phase'], (
        "This boundary requires os.environ['EDI_E11_USAGE_ACCOUNT_PHASE'] == phase['phase']"
    )
    assert (
        Path(base.__file__).resolve()
        == ROOT / 'tests/system/py/test_e11_t5_dev_native_integration.py'
    ), (
        'This boundary requires Path(base.__file__).resolve() == ROOT / '
        "'tests/system/py/test_e11_t5_dev_native_integration.py'"
    )
    files = phase['files']
    for path, expected in files.items():
        assert _sha(ROOT / path) == expected, (
            'This boundary requires _sha(ROOT / path) == expected',
            path,
        )
    bond = _bound_receipt('EDI_E11_USAGE_ACCOUNT_BINARY_BOND')
    original = _bound_receipt('EDI_E11_USAGE_ACCOUNT_ORIGINAL_BINARY_BOND')
    assert original['source'] == phase['original_source'], (
        "This boundary requires original['source'] == phase['original_source']"
    )
    assert bond['source'] == phase['compiled_source'], (
        "This boundary requires bond['source'] == phase['compiled_source']"
    )
    assert (
        os.environ['EDI_E11_USAGE_ACCOUNT_ORIGINAL_BINARY_BOND_SHA256']
        == phase['original_bond_sha256']
    ), (
        'This boundary requires '
        "os.environ['EDI_E11_USAGE_ACCOUNT_ORIGINAL_BINARY_BOND_SHA256'] == "
        "phase['original_bond_sha256']"
    )
    original_families = {
        'activity': 'native',
        'composer': 'native',
        'browser': 'native',
        'usage': 'original',
    }
    assert original['family_phases'] == original_families, (
        "This boundary requires original['family_phases'] == original_families"
    )
    assert bond['family_phases'] == {
        **original_families,
        'usage': phase['phase'],
    }, (
        "This boundary requires bond['family_phases'] == {**original_families, "
        "'usage': phase['phase']}"
    )
    for name, expected in phase['native'].items():
        assert original['native'][name] == expected, (
            "This boundary requires original['native'][name] == expected",
            name,
        )
        assert bond['native'][name] == expected, (
            "This boundary requires bond['native'][name] == expected",
            name,
        )
    assert (
        original['bundled_runtime']['config_sha256'] == phase['original_runtime_config_sha256']
    ), (
        "This boundary requires original['bundled_runtime']['config_sha256'] == "
        "phase['original_runtime_config_sha256']"
    )
    assert bond['bundled_runtime']['config_sha256'] == phase['current_runtime_config_sha256'], (
        "This boundary requires bond['bundled_runtime']['config_sha256'] == "
        "phase['current_runtime_config_sha256']"
    )
    if phase['phase'] == 'original':
        assert bond == original, 'This boundary requires bond == original'
    else:
        expected = os.environ['EDI_E11_USAGE_ACCOUNT_COMPILED_SOURCE']
        assert len(expected) == 40 and all(
            character in '0123456789abcdef' for character in expected
        ), (
            'This boundary requires len(expected) == 40 and all((character in '
            "'0123456789abcdef' for character in expected))"
        )
        assert bond['source'] == expected == phase['compiled_source'], (
            "This boundary requires bond['source'] == expected == phase['compiled_source']"
        )
    assert files[USAGE_HEADER] == USAGE_HEADER_HASHES[phase['phase']], (
        "This boundary requires files[USAGE_HEADER] == USAGE_HEADER_HASHES[phase['phase']]"
    )
    assert (
        files['tests/unit/app/e11_t5_a2a_phase_adapter_impl.hpp']
        == ACTIVITY_INPUTS['tests/unit/app/e11_t5_a2a_phase_adapter_impl.hpp']
    ), (
        'This boundary requires '
        "files['tests/unit/app/e11_t5_a2a_phase_adapter_impl.hpp'] == "
        "ACTIVITY_INPUTS['tests/unit/app/e11_t5_a2a_phase_adapter_impl.hpp']"
    )
    for observed, key in ((bond, 'current'), (original, 'original')):
        _compiled_phase_inputs(observed, observed['family_phases']['usage'])
        _compiled_callers(
            observed,
            os.environ['EDI_E11_USAGE_ACCOUNT_BINARY_BOND_SHA256']
            if key == 'current'
            else phase['original_bond_sha256'],
            phase['compiled_caller_proof'][key],
            HERE / 'e11_t5_original_controls/native_case_registry.json'
            if key == 'current'
            else _absolute(original['root'])
            / 'tests/system/py/e11_t5_original_controls/native_case_registry.json',
        )
    for path in (
        'app/qml/Components/AssistantPanel.qml',
        'app/qml/Components/AssistantComposer.qml',
        'app/src/app_info.cpp',
        'app/src/assistant_view_model.cpp',
        'tests/integration/py/assistant_ui_probe/probe.cpp',
    ):
        assert bond['compiled_sources'][path] == files[path], (
            "This boundary requires bond['compiled_sources'][path] == files[path]",
            path,
        )
    for section, keys in {
        'compiler_kit': ['compiler_sha256', 'package_metadata'],
        'dependency_environment': ['root_lock_sha256', 'dependency_only_lock_sha256'],
        'gui_components': ['commit', 'pin_file_sha256', 'source_sha256'],
        'bundled_runtime': ['files'],
    }.items():
        for key in keys:
            assert bond[section][key] == original[section][key], (
                'Recorded source and Original input identities agree',
                (section, key),
            )
    assert (
        _sha(Path(os.environ['EDI_ASSISTANT_UI_PROBE']))
        == (bond['binaries']['assistant_real_owner_probe']['sha256'])
    ), (
        "This boundary requires _sha(Path(os.environ['EDI_ASSISTANT_UI_PROBE'])) == "
        "bond['binaries']['assistant_real_owner_probe']['sha256']"
    )
    assert os.environ['EDI_E11_T5_A2A_PHASE'] == 'native', (
        "This boundary requires os.environ['EDI_E11_T5_A2A_PHASE'] == 'native'"
    )
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
    assert value['problems'] == [], "This boundary requires value['problems'] == []"
    assert all(
        envelope['ui'][key]
        for key in (
            'singleton_identity',
            'engine_parent',
            'cpp_ownership',
        )
    ), (
        "This boundary requires all((envelope['ui'][key] for key in "
        "('singleton_identity', 'engine_parent', 'cpp_ownership')))"
    )
    assert value['owner'] and value['imported_info'], (
        "This boundary requires value['owner'] and value['imported_info']"
    )
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
    assert value['usage'] == value['canonical'] and value['plain_projection'], (
        "This boundary requires value['usage'] == value['canonical'] and value['plain_projection']"
    )
    assert value['usage']['available'] and not value['usage']['stale'], (
        "This boundary requires value['usage']['available'] and (not value['usage']['stale'])"
    )
    assert value['usage']['state'] == 'ready' and not value['usage']['loading'], (
        "This boundary requires value['usage']['state'] == 'ready' and (not "
        "value['usage']['loading'])"
    )
    assert [row['id'] for row in value['usage']['buckets']] == expected['bucket_ids'], (
        "This boundary requires [row['id'] for row in value['usage']['buckets']] == "
        "expected['bucket_ids']"
    )
    for key in ('global', 'remaining', 'session_path', 'weekly_path', 'button', 'caption'):
        assert value[key] == expected[key], (
            'This boundary requires value[key] == expected[key]',
            key,
        )
    assert value['accessible'] == expected['caption'], (
        "This boundary requires value['accessible'] == expected['caption']"
    )
    assert value['independent_session'] and value['independent_weekly'], (
        "This boundary requires value['independent_session'] and value['independent_weekly']"
    )
    assert value['strict_string_duration'], (
        "This boundary requires value['strict_string_duration']"
    )
    rows = value['rows']
    assert [row['key'] for row in rows] == expected['descriptors'], (
        "This boundary requires [row['key'] for row in rows] == expected['descriptors']"
    )
    assert [row['percent'] for row in rows] == expected['percent'], (
        "This boundary requires [row['percent'] for row in rows] == expected['percent']"
    )
    descriptors = {
        'session': {'title': 'Session limit', 'minutes': 300, 'key': 'session'},
        'weekly': {'title': 'Weekly', 'minutes': 10080, 'key': 'weekly'},
    }
    assert [row['descriptor'] for row in rows] == [
        descriptors[key] for key in expected['descriptors']
    ], (
        "This boundary requires [row['descriptor'] for row in rows] == "
        "[descriptors[key] for key in expected['descriptors']]"
    )
    assert all(row['selected_member'] for row in rows), (
        "This boundary requires all((row['selected_member'] for row in rows))"
    )
    assert all(
        row['current']
        and row['visible']
        and row['percent_current']
        and row['reset_current']
        and row['reset'] == 'Reset unavailable'
        for row in rows
    ), (
        "This boundary requires all((row['current'] and row['visible'] and "
        "row['percent_current'] and row['reset_current'] and (row['reset'] == 'Reset "
        "unavailable') for row in rows))"
    )
    assert [row['sceneY'] for row in rows] == sorted(row['sceneY'] for row in rows), (
        "This boundary requires [row['sceneY'] for row in rows] == "
        "sorted((row['sceneY'] for row in rows))"
    )
    if rows:
        assert not value['status']['visible'], (
            "This boundary requires not value['status']['visible']"
        )
    else:
        assert value['status'] == {
            'visible': True,
            'text': 'Session and weekly usage were not reported.',
        }, (
            "This boundary requires value['status'] == {'visible': True, 'text': "
            "'Session and weekly usage were not reported.'}"
        )


def _check_account_projection(value, case, expected, *, phase):
    public = {key: case['account'][key] for key in ('email', 'planType') if key in case['account']}
    if phase.get('scope') == 'current_native_mount':
        # ADR-0015 account is now a fixed typed value with both string members.
        public = {key: case['account'].get(key, '') for key in ('email', 'planType')}
    assert value['account'] == public and value['canonical_account'] == public, (
        'Required:  check account projection.'
    )
    for key in ('plan', 'plan_label', 'initial'):
        assert value[key] == expected[key], (
            ('Required:  check account projection.'),
            key,
        )
    assert value['connection'] == expected['initial'], 'Required:  check account projection.'


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
    }, (
        "This boundary requires value == {'identity': expected['identity'], "
        "'identity_plain': True, 'identity_visible': True, 'identity_current': True, "
        "'plan': expected['plan_label'], 'plan_plain': True, 'plan_visible': "
        "expected['plan_visible'], 'plan_current': True}"
    )
    assert not any(
        'NEVER_ACCOUNT_DISPLAY_269' in row['display']
        for row in envelope['ui']['texts']
        if row['visible']
    ), (
        "This boundary requires not any(('NEVER_ACCOUNT_DISPLAY_269' in "
        "row['display'] for row in envelope['ui']['texts'] if row['visible']))"
    )

    # The fixture owns opening Account and closes that modal through ordinary input.
    actor.command('manual_key', key='escape')
    actor.until(
        lambda _row: (
            not base.qml(actor, base.control_expression('assistant.accountDialog') + '.visible')
        )
    )


def _wire_proof(actor, case):
    wire = base._session_wire(actor)
    sent_path = actor.trace.with_suffix('.sent.jsonl')
    sent = [json.loads(line) for line in sent_path.read_text().splitlines()]
    _retain(actor, 'canonical-wire-proof', {'wire': wire, 'sent': sent})
    account_requests = [row for row in wire if row.get('method') == 'account/read']
    usage_requests = [row for row in wire if row.get('method') == 'account/rateLimits/read']
    assert account_requests and usage_requests, (
        'This boundary requires account_requests and usage_requests'
    )
    account_results = [
        row['result']
        for row in sent
        if row.get('id') == account_requests[0]['id'] and 'result' in row
    ]
    assert account_results == [{'account': case['account'], 'requiresOpenaiAuth': False}], (
        "This boundary requires account_results == [{'account': case['account'], "
        "'requiresOpenaiAuth': False}]"
    )
    assert any(
        row.get('id') in {request['id'] for request in usage_requests}
        and row.get('result') == case['usage']
        for row in sent
    ), (
        "This boundary requires any((row.get('id') in {request['id'] for request in "
        "usage_requests} and row.get('result') == case['usage'] for row in sent))"
    )
    if 'update' in case:
        assert any(
            row.get('id') in {request['id'] for request in usage_requests}
            and row.get('result') == case['update']
            for row in sent
        ), (
            "This boundary requires any((row.get('id') in {request['id'] for request "
            "in usage_requests} and row.get('result') == case['update'] for row in "
            'sent))'
        )
    assert not any(row.get('method') == 'turn/start' for row in wire), (
        "This boundary requires not any((row.get('method') == 'turn/start' for row in wire))"
    )


@pytest.mark.parametrize('case', CASES, ids=[case['id'] for case in CASES])
def test_original_canonical_usage_selection_account_and_visible_labels(main_actor, case):
    phase = _phase()
    actor = main_actor([[]])
    if phase.get('scope') == 'current_native_mount':
        _retain(actor, 'current-native-inputs', phase)
    else:
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
    _check_account_projection(value, case, case['expected'], phase=phase)
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
        _check_account_projection(value, case, expected, phase=phase)
    _account_display(actor, expected)
    _wire_proof(actor, case)
    assert _phase() == phase, 'Exact source/phase/binary input custody remains unchanged'
