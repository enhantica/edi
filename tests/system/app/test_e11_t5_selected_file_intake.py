"""Private accepted FILE1 draft. Public URL staging is NOT an OS chooser proof."""
import json
import os
from pathlib import Path

import pytest
from tests.system.app import test_e11_t5_vm_retention as prior

signer = prior.signer
RAW = '12\tαβ🙂\r\n7.5000\n'
PROJECT = prior.ROOT / 'tests/fixtures/e04_t1/editable-project'


@pytest.fixture
def selected_vm(monkeypatch):
    binary = Path(os.environ['EDI_ASSISTANT_SELECTED_VM_PROBE'])
    assert binary.is_file(), 'I12/I15/files: real selected VM consumer must build first'
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    actor = prior.Component(binary)
    actor.command('inspect')
    assert actor.command('open', path=str(PROJECT))['reply']['opened'], 'I4/files: independent real project establishes initiating owner'
    try:
        yield actor
    finally:
        actor.close()


def begin(vm):
    result = vm.command('selected_begin')
    token = result['reply']['request_id']
    assert isinstance(token, str) and token, 'I15/FILE1: public initiation mints original authority before reading any URL'
    assert result['vm']['can_cancel'], 'I15/FILE1: genuine pending intake exposes ordinary Stop'
    return token


def add(vm, token, paths):
    return vm.command('selected_add', request_id=token, urls=[p.as_uri() for p in paths])


def planted(tmp_path, name='selected.dat', data=RAW.encode()):
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_original_begin_admit_remove_and_duplicate_are_one_shot(selected_vm, tmp_path):
    vm = selected_vm; path = planted(tmp_path); before = vm.last
    token = begin(vm); admitted = add(vm, token, [path])
    assert admitted['reply']['accepted'], 'I15/FILE1: exact original initiating capability admits selected local bytes'
    rows = admitted['vm']['selected_files']
    assert len(rows) == 1, 'I15/files: one genuine file publishes one admitted row'
    assert set(rows[0]) == {'id', 'name', 'bytes', 'textReadable', 'format'}, 'I15/files: actual visible rows expose metadata without native paths'
    assert rows[0]['name'] == path.name and rows[0]['bytes'] == len(RAW.encode()) and rows[0]['textReadable'], 'I15/files: metadata describes independently planted UTF8 bytes'
    assert admitted['vm']['project'] == before['vm']['project'] and admitted['requests'] == before['requests'], 'I4/I15/files: selection edits no scientific state and sends no provider request'
    assert token in admitted['vm']['retired_selections'], 'I15/FILE1: successful intake retires exactly its initiating capability'
    path.write_text('later host replacement', encoding='utf-8')
    replay = add(vm, token, [path])
    assert not replay['reply']['accepted'] and replay['vm']['selected_files'] == rows, 'I15/FILE1: duplicate completion cannot reread changed host bytes'
    assert replay['vm']['last_error'] == admitted['vm']['last_error'], 'I15/FILE1: consumed completion is inert rather than a new error'
    removed = vm.command('selected_remove', id=rows[0]['id'])
    assert removed['reply']['accepted'] and removed['vm']['selected_files'] == [], 'I15/files: explicit removal addresses an actual opaque selected identity'


def test_old_cancel_and_completion_do_not_retire_new_pending_intake(selected_vm, tmp_path):
    vm = selected_vm; path = planted(tmp_path)
    old = begin(vm); current = begin(vm); before = vm.last
    assert old != current and old in before['vm']['retired_selections'], 'I15/FILE1: successful new initiation retires the previous original token'
    for token in [old, 'never-issued-fixture-token']:
        result = add(vm, token, [path])
        assert not result['reply']['accepted'] and result['vm']['selected_files'] == [], 'I15/FILE1: retired or foreign token grants no bytes'
        assert result['vm']['last_error'] == before['vm']['last_error'], 'I15/FILE1: stale callback cannot overwrite a newer operation error'
        vm.command('selected_cancel', request_id=token)
        assert vm.last['vm']['can_cancel'], 'I15/FILE1: mismatched cancel cannot consume current intake'
    vm.command('inspect')
    assert add(vm, current, [path])['reply']['accepted'], 'I15/FILE1: unchanged actual owner preserves its legitimate pending authority'


@pytest.mark.parametrize('retirement', ['selected_cancel', 'cancel', 'clear_history', 'close_project', 'sign_out', 'destroy'])
def test_retirement_rejects_later_old_admission(selected_vm, tmp_path, retirement):
    vm = selected_vm; path = planted(tmp_path); token = begin(vm)
    vm.command(retirement, **({'request_id': token} if retirement == 'selected_cancel' else {}))
    if retirement == 'destroy':
        vm.command('recreate')
    before = vm.last; after = add(vm, token, [path])
    assert not after['reply']['accepted'], 'I15/FILE1: explicit retired owner cannot admit a later old callback'
    assert after['vm']['selected_files'] == before['vm']['selected_files'], 'I15/FILE1: stale completion publishes no rows into a retired or recreated owner'
    assert after['requests'] == before['requests'] and after['vm']['project'] == before['vm']['project'], 'I4/I15/files: stale intake has no inference or scientific effect'


def test_pending_blocks_send_and_manual_revision_stales_its_capture(selected_vm, signer, tmp_path):
    vm = selected_vm; prior.authenticate(vm, signer)
    path = planted(tmp_path); token = begin(vm); before = vm.last
    vm.command('send_text', text='Cannot bypass unfinished selection')
    assert vm.last['requests'] == before['requests'] and vm.last['vm']['messages'] == before['vm']['messages'], 'I15/FILE1: pending intake cannot be bypassed by prompt admission'
    entry = vm.last['vm']['project']['parameters'][0]
    changed = vm.command('manual_value', path=entry['path'], value=entry['value'] + 0.125)
    assert not changed['reply']['error'], 'I4/files: ordinary accepted manual action creates genuine revision change'
    result = add(vm, token, [path])
    assert not result['reply']['accepted'] and result['vm']['project'] == changed['vm']['project'], 'I4/I15/FILE1: stale selected scope cannot roll back or inherit the new manual revision'


@pytest.mark.parametrize('bad', ['directory', 'missing', 'same-basename', 'remote'])
def test_matching_failed_staging_is_atomic_and_consumed(selected_vm, tmp_path, bad):
    vm = selected_vm; good = planted(tmp_path, name='baseline.txt')
    assert add(vm, begin(vm), [good])['reply']['accepted'], 'I15/files: actual prior admitted bytes supply preservation control'
    token = begin(vm); before = vm.last
    if bad == 'directory':
        candidates = [tmp_path]
    elif bad == 'missing':
        candidates = [tmp_path / 'missing.txt']
    elif bad == 'same-basename':
        other = tmp_path / 'other'; other.mkdir()
        candidates = [planted(tmp_path, name='duplicate.txt'), planted(other, name='duplicate.txt')]
    else:
        candidates = None
    result = add(vm, token, candidates) if candidates is not None else vm.command('selected_add', request_id=token, urls=['https://invalid.example/selected.dat'])
    assert not result['reply']['accepted'], 'I15/files: real conflicting/invalid selected input refuses its whole batch'
    assert result['vm']['selected_files'] == before['vm']['selected_files'] and result['vm']['project'] == before['vm']['project'], 'I4/I15/files: failed read/staging preserves exact prior collection and project'
    assert token in result['vm']['retired_selections'], 'I15/FILE1: matching failed staging consumes its original token'
    assert not add(vm, token, [good])['reply']['accepted'], 'I15/FILE1: failed admission retry requires a new initiation'
    retry = planted(tmp_path, name='retry.txt', data=b'retry original')
    assert add(vm, begin(vm), [retry])['reply']['accepted'], 'I15/FILE1: genuine new initiation remains usable after atomic staging refusal'


def test_actual_consent_and_native_continuation_receive_immutable_original_bytes(selected_vm, signer, tmp_path):
    vm = selected_vm; prior.authenticate(vm, signer); path = planted(tmp_path)
    assert add(vm, begin(vm), [path])['reply']['accepted'], 'I15/files: connected intake retains original chooser authority'
    admitted = vm.last; manifest = admitted['vm']['context']['selected_files']; row = manifest['files'][0]
    assert admitted['vm']['context_consent_required'], 'I15/files: changed selected manifest invalidates displayed context consent'
    vm.command('send_text', text='Not consented yet')
    assert prior.responses(vm) == [], 'I15/files: changed scope sends no inference before actual host consent'
    vm.command('sign_in')  # Existing actual consent acknowledgement, not OS-picker automation.
    assert not vm.last['vm']['context_consent_required'], 'I15/files: actual host acknowledges the current selected scope'
    path.write_text('changed after admission', encoding='utf-8')
    index = prior.begin(vm, 'Read original selected bytes')
    args = {'collection_id': manifest['collection_id'], 'generation': manifest['generation'], 'file_id': row['id'], 'offset': 0, 'max_bytes': 65536}
    prior.events(vm, index, prior.function('read_selected_file', args, call='selected-original'))
    outgoing = prior.responses(vm)
    assert len(outgoing) == 2, 'I3/I15/files: actual read completion produces exactly one native continuation'
    body = json.loads(outgoing[-1][1]['body'])
    calls = [item for item in body['input'] if item.get('type') == 'function_call' and item.get('call_id') == 'selected-original']
    results = [item for item in body['input'] if item.get('type') == 'function_call_output' and item.get('call_id') == 'selected-original']
    assert len(calls) == len(results) == 1, 'I3/files: actual outgoing wire pairs one original call with one complete output'
    value = json.loads(results[0]['output'])['result']
    assert value == {'collection_id': manifest['collection_id'], 'generation': manifest['generation'], 'file_id': row['id'], 'name': path.name, 'offset': '0', 'next_offset': None, 'eof': True, 'text': RAW}, 'I11/I15/files: independently planted immutable original bytes and exact offsets survive the complete correlated native result'
    assert vm.last['vm']['project'] == admitted['vm']['project'], 'I4/files: read and continuation leave actual scientific state exact'


def test_genuine_active_inference_refuses_intake_without_cancelling_it(selected_vm, signer):
    vm = selected_vm; prior.authenticate(vm, signer)
    vm.command('sign_in')  # Genuine acknowledgement of this ready connection's current disclosure.
    assert not vm.last['vm']['context_consent_required'], 'I15/files: actual current context consent precedes genuine inference setup'
    index = prior.begin(vm, 'Keep this genuine current provider operation')
    before = vm.last; result = vm.command('selected_begin')
    assert result['reply']['request_id'] == '', 'I15/FILE1: real active inference refuses opening an intake'
    assert result['requests'] == before['requests'] and result['vm']['messages'] == before['vm']['messages'], 'I3/I15/files: failed initiation creates no extra request or phantom prompt'
    assert result['requests'][index]['cancelled'] is False and before['requests'][index]['cancelled'] is False, 'I3/I15/FILE1: selection refusal does not cancel genuine current provider work'
    assert result['vm']['can_cancel'], 'I15/FILE1: genuine current inference keeps its ordinary Stop affordance'


def test_real_connection_retirement_does_not_rebind_old_intake(selected_vm, signer, tmp_path):
    vm = selected_vm; prior.authenticate(vm, signer); path = planted(tmp_path)
    previous_browser = vm.last['browsers'][-1]
    previous_browser_count = len(vm.last['browsers'])
    old = begin(vm)
    vm.command('sign_out')
    assert not vm.last['vm']['connected'], 'I12/FILE1: actual owner sign-out genuinely retires the native connection'
    revocations = [(i, request) for i, request in enumerate(vm.last['requests'])
                   if request['url'] == prior.native.AUTH + '/independent-revoke' and not request['cancelled']]
    assert len(revocations) == 1, 'I12/FILE1: real sign-out exposes its actual outstanding offline revocation'
    revoke_index = revocations[0][0]
    vm.respond(revoke_index, None)
    vm.handled.add(revoke_index)
    prior.authenticate(vm, signer)
    assert len(vm.last['browsers']) == previous_browser_count + 1, 'I12/FILE1: reconnect opens one genuine fresh authorization instead of reusing an old callback'
    old_query = prior.native.parse_qs(prior.native.urlsplit(previous_browser).query)
    fresh_query = prior.native.parse_qs(prior.native.urlsplit(vm.last['browsers'][-1]).query)
    assert fresh_query['nonce'] != old_query['nonce'], 'I12/FILE1: new signed authentication is bound to its genuinely fresh nonce'
    before = vm.last; rejected = add(vm, old, [path])
    assert not rejected['reply']['accepted'] and rejected['vm']['selected_files'] == [], 'I12/I15/FILE1: a new real connection cannot reuse previous initiating authority'
    assert rejected['requests'] == before['requests'], 'I15/FILE1: stale account-scope completion performs no new request'
    assert add(vm, begin(vm), [path])['reply']['accepted'], 'I15/FILE1: newly initiated actual current connection still admits local selection'


def test_home_projectless_selection_and_exact_native_read_continuation(selected_vm, signer, tmp_path):
    vm = selected_vm
    closed = vm.command('close_project')
    assert closed['vm']['project_present'] is False, 'I4/I15/files: actual public Session close establishes projectless Home, not a dummy project'
    path = planted(tmp_path, name='home-original.txt')
    token = begin(vm)
    admitted = add(vm, token, [path])
    assert admitted['reply']['accepted'] and admitted['vm']['project_present'] is False, 'I15/FILE1: original projectless initiation admits genuine selected bytes without creating scientific state'
    manifest = admitted['vm']['context']['selected_files']; row = manifest['files'][0]
    assert admitted['requests'] == closed['requests'], 'I15/files: projectless selection alone performs no inference or provider upload'
    prior.authenticate(vm, signer)
    vm.command('sign_in')  # Real existing consent acknowledgement for the displayed Home manifest.
    index = prior.begin(vm, 'Read only my selected Home file')
    arguments = {'collection_id': manifest['collection_id'], 'generation': manifest['generation'], 'file_id': row['id'], 'offset': 0, 'max_bytes': 65536}
    prior.events(vm, index, prior.function('read_selected_file', arguments, call='home-original'))
    outgoing = prior.responses(vm)
    assert len(outgoing) == 2, 'I3/I15/files: projectless selected read produces a genuine native continuation'
    body = json.loads(outgoing[-1][1]['body'])
    calls = [item for item in body['input'] if item.get('type') == 'function_call' and item.get('call_id') == 'home-original']
    outputs = [item for item in body['input'] if item.get('type') == 'function_call_output' and item.get('call_id') == 'home-original']
    assert len(calls) == len(outputs) == 1, 'I3/files: actual Home continuation preserves the original selected-file call/output pairing'
    result = json.loads(outputs[0]['output'])['result']
    assert result == {'collection_id': manifest['collection_id'], 'generation': manifest['generation'], 'file_id': row['id'], 'name': path.name, 'offset': '0', 'next_offset': None, 'eof': True, 'text': RAW}, 'I11/I15/files: projectless native wire carries the complete independently planted original bytes and exact correlation'
    assert vm.last['vm']['project_present'] is False and vm.last['vm']['project'] == {}, 'I4/files: Home read and provider continuation create or mutate no scientific project'
