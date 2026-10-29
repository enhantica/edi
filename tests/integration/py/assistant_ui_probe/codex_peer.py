"""Finite offline Codex 0.162.1 protocol fixture for the existing real Main host.

Wire shapes are independently retained in the earlier assistant stdio fixture at
77ba02de. This peer executes no commands, accesses no account and calls no service.
"""

from __future__ import annotations

import json
import hashlib
import os
import sys
import threading
from pathlib import Path

config = json.loads(Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).read_text(encoding='utf-8'))
trace = Path(config['trace'])
thread_id = '019a0290-0000-7000-8000-000000000001'
turn_id = '019a0290-0000-7000-8000-000000000002'
pending = {}
human_pending = {}
human_native_pending = {}
human_native_scheduled = []
retry_after_response = {}
first_response_for_retry = {}
calls = []
turn_number = 0
thread_number = 0
cursor = {'position': 0, 'sequence': 0, 'pending_final': False, 'research': None, 'message_stream': None}
native_ids = {}
emit_lock = threading.RLock()
usage_notifications_delivered = False
fixture_usage_generation = None
account_mode_delivered = False
effective_configs = {}
subscribed_threads = set()
held_usage = []
pending_metadata = []
pending_archive = None
pending_turn_start = None
fixture_unacked_start = None
client_originator = None
if config.get("session_fixture"):
    with trace.open("a", encoding="utf-8") as output:
        output.write(json.dumps({"fixture_runtime_started": {"pid": os.getpid(), "parent_pid": os.getppid()}}) + "\n")
# Provider-owned offline persistence, using pinned092d Thread/Resume/Read shapes.
# This never fabricates application state or scientific results. A killed helper
# must resume the original stored ID, rather than silently starting another one.
state_path = trace.with_suffix('.provider-state.json')
source_state = os.environ.get('EDI_TEST_CODEX_PROVIDER_STATE_SOURCE')
if source_state and not state_path.exists():
    source = Path(source_state).resolve(strict=True)
    fixture_root = Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).resolve().parent.parent
    assert source.is_relative_to(fixture_root) and source.is_file() and source.stat().st_uid == os.geteuid()
    assert not state_path.exists() and config.get('session_fixture')
    original_state_bytes = source.read_bytes()
    original_state = json.loads(original_state_bytes)
    assert isinstance(original_state.get('threads'), dict) and isinstance(original_state.get('inputs'), list)
    state_path.write_bytes(original_state_bytes)
    with trace.open('a', encoding='utf-8') as output:
        output.write(json.dumps({'fixture_provider_restore': {'source': str(source),
            'destination': str(state_path), 'bytes': len(original_state_bytes),
            'sha256': hashlib.sha256(original_state_bytes).hexdigest(), 'exact_copy': True}}) + '\n')
state = json.loads(state_path.read_text()) if state_path.exists() else {
    'thread_number': 0, 'turn_number': 0, 'threads': {}, 'inputs': []}
thread_number = state['thread_number']
turn_number = state['turn_number']


def persist():
    temporary = state_path.with_suffix('.new')
    temporary.write_text(json.dumps(state), encoding='utf-8')
    temporary.replace(state_path)


def saved_thread(exclude_turns=False):
    value = dict(state['threads'][thread_id])
    if exclude_turns:
        value['turns'] = []
    return value


def thread_response(exclude_turns=False):
    effective = effective_configs.get(thread_id, {})
    return {
        'thread': saved_thread(exclude_turns), 'model': effective.get('model', 'gpt-6.1-sol'),
        'modelProvider': 'openai', 'serviceTier': None, 'disabledPluginIds': [],
        'cwd': effective.get('cwd', cwd), 'instructionSources': [], 'approvalPolicy': 'never',
        'approvalsReviewer': 'user',
        'sandbox': {'type': 'readOnly', 'networkAccess': False},
        'reasoningEffort': effective.get('effort', 'medium'), 'collaborationMode': None,
        'turnsBackwardsCursor': None, 'itemsBackwardsCursor': None,
    }


def emit(value):
    with emit_lock:
        with trace.with_suffix('.sent.jsonl').open('a', encoding='utf-8') as output:
            output.write(json.dumps(value) + '\n')
        print(json.dumps(value, ensure_ascii=False), flush=True)


def reply(request, value):
    emit({'id': request['id'], 'result': value})


def metadata_reply(request, value, family):
    current = json.loads(Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).read_text(encoding='utf-8'))
    gate = current.get('session_fixture', {}).get(family + '_hold')
    if gate and not Path(gate).exists():
        pending_metadata.append((request, json.loads(json.dumps(value)), family))
    else:
        reply(request, value)


def settle_captured_archived_start():
    global pending_turn_start
    original = pending_turn_start
    if not original or not Path(original['hold']).exists():
        return
    pending_turn_start = None
    request = original['request'];identity = original['thread'];started = original['turn']
    state.setdefault('late_start_outcomes', []).append({
        'request_id': request['id'], 'threadId': identity, 'turnId': started['id'],
        'actual_reply': original['reply']})
    if original['reply'] == 'refusal':
        persist()
        emit({'id': request['id'], 'error': {'code': -32000,
            'message': 'Independent original start refused after its thread was archived'}})
        return
    interrupted = {**started, 'status': 'interrupted'}
    state['threads'][identity]['turns'].append(interrupted)
    if original.get('user_entry'):
        state.setdefault('item_history', {}).setdefault(identity, []).append(original['user_entry'])
    persist()
    reply(request, {'turn': started})
    notify('turn/started', {'threadId': identity, 'turn': started})
    notify('turn/completed', {'threadId': identity, 'turn': interrupted})


def finish_native_archive(request):
    # Pinned092d ordinary thread/archive owns descendant closure. This offline
    # peer records RPC policy/notifications only, not real-provider disk cleanup.
    target = request['params']['threadId']
    affected = {target}
    if config.get('session_fixture', {}).get('native_archive_subtree'):
        while True:
            children = {identity for identity, row in state['threads'].items()
                        if row.get('parentThreadId') in affected}
            if children <= affected:
                break
            affected.update(children)
    state.setdefault('archive_operations', []).append({'target': target,
        'affected': sorted(affected),
        'actually_loaded_in_this_peer': sorted(affected.intersection(effective_configs))})
    archived = state.setdefault('archived_threads', [])
    for identity in sorted(affected):
        if identity not in archived:
            archived.append(identity)
    persist()
    reply(request, {})
    if config.get('session_fixture', {}).get('emit_archived_notifications'):
        for identity in sorted(affected):
            notify('thread/archived', {'threadId': identity})


def settle_fixture_unacked_start():
    # Exact actual received turn/start, server-side ACK scheduling only. Never
    # insert an app row/receipt, change its IDs, or execute scientific work.
    global fixture_unacked_start
    captured = fixture_unacked_start
    if not captured or not Path(captured['hold']).exists():
        return
    fixture_unacked_start = None
    identity = captured['thread'];original = captured['turn']
    reply(captured['request'], {'turn': original})
    notify('turn/started', {'threadId': identity, 'turn': original})
    item = agent_message(original['id'] + '-final', captured['final_text'])
    binding = {'threadId': identity, 'turnId': original['id'], 'item': item}
    notify('item/started', binding)
    notify('item/completed', {**binding, 'completedAtMs': 1})
    complete = {**original, 'status': 'completed',
        'items': [entry['item'] for entry in state.get('item_history', {}).get(identity, [])
                  if entry['turnId'] == original['id']], 'itemsView': 'full'}
    state['threads'][identity]['turns'].append(complete);persist()
    notify('turn/completed', {'threadId': identity,
        'turn': {**complete, 'items': [dict(item)], 'itemsView': 'summary'}})


def agent_message(identity, text):
    # Pinned092d event_mapping.rs406-420 and v2/item.rs252-263,889-904:
    # live item events and terminal Summary serialize the SAME nullable fields.
    return {'type': 'agentMessage', 'id': identity, 'text': text,
            'phase': None, 'memoryCitation': None, 'delivery': None, 'questions': None}


def remember_actual_item(method, params):
    if not config.get('observe_context_continuity') or method not in ('item/started', 'item/completed'):
        return
    identity = params.get('threadId')
    assert identity in state['threads'] and params.get('turnId') and isinstance(params.get('item'), dict)
    item = json.loads(json.dumps(params['item']))
    entries = state.setdefault('item_history', {}).setdefault(identity, [])
    key = (params['turnId'], item['id'])
    old = next((entry for entry in entries if (entry['turnId'], entry['item']['id']) == key), None)
    entry = {'turnId': params['turnId'], 'item': item,
             'startedAtMs': params.get('startedAtMs', old.get('startedAtMs') if old else None),
             'completedAtMs': params.get('completedAtMs') if method == 'item/completed' else None}
    if old is None:
        entries.append(entry)
    else:
        entries[entries.index(old)] = entry
    persist()


def notify(method, params):
    emit({'method': method, 'params': params})
    remember_actual_item(method, params)


def turn(status):
    return {'id': turn_id, 'rootTurnId': None, 'items': [], 'itemsView': 'notLoaded',
            'status': status, 'error': None, 'startedAt': None, 'completedAt': None,
            'durationMs': None}


def operands(value):
    if isinstance(value, dict):
        if set(value) == {'created_structure_parameter'}:
            return native_ids['structure'] + '.' + value['created_structure_parameter']
        return {key: operands(child) for key, child in value.items()}
    if isinstance(value, list):
        return [operands(child) for child in value]
    return value


def advance():
    if cursor['position'] == len(calls):
        gate = config.get('final_gate')
        if gate and not Path(gate).exists():
            cursor['pending_final'] = True
            return
        cursor['pending_final'] = False
        if config.get('terminal_status') == 'process_exit':
            sys.exit(23)
        text = config.get(
            'final_text', 'No supported improvement recommendation from this finite fixture.'
        )
        item = agent_message(turn_id + '-final', text)
        binding = {'threadId': thread_id, 'turnId': turn_id, 'item': item}
        notify('item/started', binding)
        notify('item/completed', {**binding, 'completedAtMs': 1})
        terminal_fixture = config.get('fixture_provider_terminal')
        # Explicit opt-in negative/terminal protocol carrier, not a native
        # result. Pinned Turn.error is Option<TurnError>; malformed cases are
        # labelled parser-negative inputs and never valid runtime goldens.
        completed = turn(terminal_fixture['status'] if terminal_fixture else 'completed')
        if terminal_fixture:
            presence = terminal_fixture['error_presence']
            assert presence in ('absent', 'null', 'actual', 'malformed')
            if presence == 'absent':
                completed.pop('error')
            elif presence != 'null':
                completed['error'] = terminal_fixture['error']
            event = terminal_fixture.get('notification')
            if event:
                notify('error', {'threadId': thread_id, 'turnId': turn_id,
                    'error': event['error'], 'willRetry': event['willRetry']})
                if event.get('duplicate'):
                    notify('error', {'threadId': thread_id, 'turnId': turn_id,
                        'error': event['error'], 'willRetry': event['willRetry']})
        if config.get('observe_context_continuity'):
            completed['items'] = [entry['item'] for entry in state.get('item_history', {}).get(thread_id, []) if entry['turnId'] == turn_id]
            completed['itemsView'] = 'full'
        state['threads'][thread_id]['turns'].append(completed)
        persist()
        # Pinned092d live notifications are summaries, not the persisted full
        # item history. bespoke_event_handling.rs1329-1349 and upstream test3480.
        summary = {**completed, 'items': [dict(item)], 'itemsView': 'summary'}
        notify('turn/completed', {'threadId': thread_id, 'turn': summary})
        title = config.get('automatic_thread_name_after_first_turn')
        if title and len(state['threads'][thread_id]['turns']) == 1:
            state['threads'][thread_id]['name'] = title
            persist()
            notify('thread/name/updated', {'threadId': thread_id, 'threadName': title})
        if config.get('disconnect_after_turn'):
            sys.exit(23)
        return
    spec = calls[cursor['position']]
    if 'idle_delay_ms' in spec:
        calls[cursor['position']] = {key: value for key, value in spec.items() if key != 'idle_delay_ms'}
        timer = threading.Timer(spec['idle_delay_ms'] / 1000, advance)
        timer.daemon = True
        timer.start()
        return
    cursor['position'] += 1
    cursor['sequence'] += 1
    call_id = spec.get('call_id', 'integration-call-' + str(cursor['sequence']))
    if 'message_stream' in spec:
        stream = spec['message_stream']
        chunks = [stream['chunk']] * stream['count']
        binding = {'threadId': thread_id, 'turnId': turn_id}
        item = agent_message(call_id, '')
        notify('item/started', {**binding, 'item': item})
        gate = stream.get('hold_after_first')
        if gate:
            assert len(chunks) > 1 and not cursor['message_stream']
            notify('item/agentMessage/delta', {**binding, 'itemId': call_id, 'delta': chunks[0]})
            cursor['message_stream'] = {'gate': gate, 'chunks': chunks, 'binding': binding, 'item': item}
            return
        for chunk in chunks:
            notify('item/agentMessage/delta', {**binding, 'itemId': call_id, 'delta': chunk})
        notify('item/completed', {**binding, 'item': {**item, 'text': ''.join(chunks)}, 'completedAtMs': 1})
        advance()
        return
    if 'notification' in spec:
        event = spec['notification']
        notify(event['method'], {**event['params'], 'threadId': thread_id, 'turnId': turn_id})
        if not spec.get('hold_after'):
            advance()
        return
    if 'research' in spec:
        # Official 0.162.1 ThreadItem WebSearchItem + WebSearchAction. Results
        # are opaque JSON; no invented typed status/refusal/citation fields.
        completed = {'type': 'webSearch', 'id': call_id, **spec['research']}
        started = {**completed, 'query': '', 'action': None, 'results': None}
        binding = {'threadId': thread_id, 'turnId': turn_id}
        notify('item/started', {**binding, 'item': started, 'startedAtMs': 1})
        completion = {**binding, 'item': completed, 'completedAtMs': 2}
        if spec.get('hold_complete') and not Path(spec['hold_complete']).exists():
            cursor['research'] = (spec['hold_complete'], completion)
            return
        notify('item/completed', completion)
        if spec.get('duplicate'):
            notify('item/completed', completion)
        advance()
        return
    if 'human_question' in spec or 'human_questions' in spec:
        # Pinned092d ToolRequestUserInputParams/Question and ordinary pending
        # ThreadItem lifecycle. This is runtime question metadata, no Edi result.
        questions = spec['human_questions'] if 'human_questions' in spec else [spec['human_question']]
        item = {'type': 'dynamicToolCall', 'id': call_id, 'namespace': None,
                'tool': 'request_user_input', 'arguments': {'questions': questions},
                'status': 'inProgress', 'contentItems': None, 'success': None, 'durationMs': None}
        binding = {'threadId': thread_id, 'turnId': turn_id}
        if spec.get('human_without_public_item'):
            binding['question_item_id'] = call_id  # Pinned callback call ID only, NOT a public item.
        else:
            binding['item'] = item
        request_id = 'independent-human-envelope-' + str(cursor['sequence'])
        human_pending[request_id] = binding
        for probe in spec.get('human_native_probes', []):
            human_native_scheduled.append((request_id, probe))
        if 'item' in binding:
            notify('item/started', {**binding, 'startedAtMs': 1})
        emit({'id': request_id, 'method': 'item/tool/requestUserInput', 'params': {
            'threadId': thread_id, 'turnId': turn_id, 'itemId': call_id,
            'questions': questions, 'isBlocking': True, 'autoResolutionMs': None}})
        return
    spec = {**spec, 'arguments': operands(spec['arguments'])}
    item = {
        'type': 'dynamicToolCall',
        'id': call_id,
        'namespace': None,
        'tool': spec['tool'],
        'arguments': spec['arguments'],
        'status': 'inProgress',
        'contentItems': None,
        'success': None,
        'durationMs': None,
    }
    binding = {'threadId': thread_id, 'turnId': turn_id, 'item': item}
    request_id = 'integration-envelope-' + str(cursor['sequence'])
    pending[request_id] = binding
    if spec.get('replay_request_once'):
        retry_after_response[request_id] = {
            'threadId': thread_id, 'turnId': turn_id, 'callId': call_id,
            'namespace': None, 'tool': spec['tool'], 'arguments': spec['arguments'],
        }
    notify('item/started', {**binding, 'startedAtMs': 1})
    emit({
        'id': request_id,
        'method': 'item/tool/call',
        'params': {
            'threadId': thread_id,
            'turnId': turn_id,
            'callId': call_id,
            'namespace': None,
            'tool': spec['tool'],
            'arguments': spec['arguments'],
        },
    })


def emit_released_question_native_probes():
    # Same original scripted runtime, real server requests only. The run-owned
    # gate controls WHEN to try input; it cannot forge an app refusal/outcome.
    for parent_rpc, probe in list(human_native_scheduled):
        if parent_rpc not in human_pending or not Path(probe['release']).exists():
            continue
        human_native_scheduled.remove((parent_rpc, probe))
        original = human_pending[parent_rpc]
        arguments = operands(probe['arguments'])
        item = {'type': 'dynamicToolCall', 'id': probe['call_id'], 'namespace': None,
                'tool': probe['tool'], 'arguments': arguments, 'status': 'inProgress',
                'contentItems': None, 'success': None, 'durationMs': None}
        binding = {'threadId': original['threadId'], 'turnId': original['turnId'], 'item': item}
        rpc = 'original-human-native-envelope-' + probe['call_id']
        assert rpc not in human_native_pending and rpc not in pending and rpc not in human_pending
        human_native_pending[rpc] = (parent_rpc, binding)
        notify('item/started', {**binding, 'startedAtMs': 1})
        emit({'id': rpc, 'method': 'item/tool/call', 'params': {
            'threadId': binding['threadId'], 'turnId': binding['turnId'],
            'callId': item['id'], 'namespace': None, 'tool': item['tool'], 'arguments': arguments}})


for line in sys.stdin:
    request = json.loads(line)
    with trace.open('a', encoding='utf-8') as output:
        output.write(json.dumps(request) + '\n')
    if 'method' not in request:
        if request['id'] in human_native_pending:
            parent_rpc, original = human_native_pending.pop(request['id'])
            state.setdefault('human_native_responses', []).append({
                'parent_rpc': parent_rpc, 'response': json.loads(json.dumps(request))})
            persist()
            result = request.get('result', {})
            item = {**original['item'], 'status': 'completed' if result.get('success') else 'failed',
                    'success': bool(result.get('success')), 'contentItems': result.get('contentItems', []), 'durationMs': 1}
            notify('item/completed', {**original, 'item': item, 'completedAtMs': 1})
            # This distinct real native reply cannot answer or advance the
            # original human RPC, nor execute another original scripted step.
            continue
        if request['id'] in human_pending:
            original = human_pending.pop(request['id'])
            state.setdefault('human_answers', []).append(json.loads(json.dumps(request)))
            persist()
            if 'item' in original:
                success = 'result' in request and 'error' not in request
                item = {**original['item'], 'status': 'completed' if success else 'failed',
                        'success': success, 'contentItems': [{'type': 'inputText',
                        'text': json.dumps(request.get('result', request.get('error')))}], 'durationMs': 1}
                notify('item/completed', {**original, 'item': item, 'completedAtMs': 2})
            # A real builtin callback resolves its original RPC without inventing
            # item/completed for an item the runtime never published.
            advance()
            continue
        original = pending.pop(request['id'])
        result = request.get('result', {})
        retry = retry_after_response.pop(request['id'], None)
        if retry is not None:
            # Simulate retransmission while the ONE logical item is still in
            # progress. Never reopen a completed item with item/started.
            retry_id = request['id'] + '-retry'
            pending[retry_id] = original
            first_response_for_retry[retry_id] = result
            emit({'id': retry_id, 'method': 'item/tool/call', 'params': retry})
            continue
        result = first_response_for_retry.pop(request['id'], result)
        if original['item']['tool'] == 'create_structure' and result.get('success'):
            result_value = json.loads(result['contentItems'][0]['text'])
            assert len(result_value['structures']) == 1
            native_ids['structure'] = result_value['structures'][0]['id']
        item = {
            **original['item'],
            'status': 'completed' if result.get('success') else 'failed',
            'success': bool(result.get('success')),
            'contentItems': result.get('contentItems', []),
            'durationMs': 1,
        }
        notify('item/completed', {**original, 'item': item, 'completedAtMs': 1})
        advance()
        continue
    method, params = request['method'], request.get('params', {})
    if method == 'initialize':
        client_originator = params.get('clientInfo', {}).get('name')
        reply(
            request,
            {
                'userAgent': 'edi-independent-integration/0.162.1',
                'codexHome': str(trace.parent / 'unused-profile'),
                'platformFamily': 'unix',
                'platformOs': 'linux',
            },
        )
    elif method == 'initialized':
        pass
    elif method == 'account/logout':
        reply(request, {})
    elif method == 'account/read':
        mode = config.get('account_notification_before_read')
        if mode is not None and not account_mode_delivered:
            account_mode_delivered = True
            with trace.open('a', encoding='utf-8') as output:
                output.write(json.dumps({'fixture_mode_before_account_read': {'request_id': request['id'], 'pid': os.getpid(), 'metadata': mode}}) + '\n')
            notify('account/updated', mode)
        current_account = json.loads(Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).read_text(encoding='utf-8'))
        normal_account = {'account': {'type': 'chatgpt',
            'email': config.get('account_email', 'integration@example.invalid'), 'planType': 'plus'},
            'requiresOpenaiAuth': False}
        metadata_reply(request, current_account.get('fixture_account_read_reply', normal_account), 'account_read')
    elif method == 'account/rateLimits/read':
        emit_released_question_native_probes()
        current = json.loads(Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).read_text(encoding='utf-8'))
        settle_captured_archived_start()
        settle_fixture_unacked_start()
        barrier = current.get('hold_usage_until')
        if barrier and not Path(barrier).exists():
            held_usage.append(request)
        else:
            for old in held_usage:
                reply(old, {'rateLimits': None, 'rateLimitsByLimitId': {}})
            held_usage.clear()
            reply(request, {'rateLimits': None, 'rateLimitsByLimitId': {}})
        for old, value, family in list(pending_metadata):
            gate = current.get('session_fixture', {}).get(family + '_hold')
            if not gate or Path(gate).exists():
                if current.get('session_fixture', {}).get(family + '_error_on_release'):
                    emit({'id': old['id'], 'error': {'code': -32000, 'message': 'Independent original ' + family + ' operation failure'}})
                else:
                    reply(old, value)
                pending_metadata.remove((old, value, family))
        generation = current.get('fixture_usage_notification_generation')
        if generation is not None and generation != fixture_usage_generation:
            fixture_usage_generation = generation
            for event in current.get('fixture_usage_notifications', []):
                notify(event['method'], event['params'])
        if current.get('usage_notifications') and not usage_notifications_delivered:
            usage_notifications_delivered = True
            for event in current['usage_notifications']:
                event_params = {'threadId': thread_id, **event['params']}
                if event['method'] == 'thread/archived':
                    archived = state.setdefault('archived_threads', [])
                    if event_params['threadId'] not in archived:
                        archived.append(event_params['threadId']);persist()
                notify(event['method'], event_params)
        if pending_archive and Path(config['session_fixture']['archive_hold']).exists():
            original = pending_archive
            pending_archive = None
            finish_native_archive(original)
        held_stream = cursor['message_stream']
        if held_stream and Path(held_stream['gate']).exists():
            cursor['message_stream'] = None
            binding, item, chunks = held_stream['binding'], held_stream['item'], held_stream['chunks']
            for chunk in chunks[1:]:
                notify('item/agentMessage/delta', {**binding, 'itemId': item['id'], 'delta': chunk})
            notify('item/completed', {**binding, 'item': {**item, 'text': ''.join(chunks)}, 'completedAtMs': 1})
            advance()
        if cursor['research'] and Path(cursor['research'][0]).exists():
            notify('item/completed', cursor['research'][1])
            cursor['research'] = None
            advance()
        if cursor['pending_final'] and Path(config['final_gate']).exists():
            advance()
    elif method == 'model/list':
        reply(request, {'data': config.get('fixture_models', [{'id': 'gpt-6.1-sol', 'model': 'gpt-6.1-sol', 'displayName': 'Independent offline model', 'description': 'Protocol fixture', 'hidden': False, 'isDefault': True, 'defaultReasoningEffort': 'medium', 'supportedReasoningEfforts': [{'reasoningEffort': 'medium', 'description': 'Fixture'}]}]), 'nextCursor': None})
    elif method == 'skills/list':
        reply(
            request,
            {
                'data': [
                    {
                        'cwd': cwd,
                        'errors': [],
                        'skills': [
                            {
                                'name': p.parent.name,
                                'description': 'Independent registration ' + p.parent.name,
                                'enabled': True,
                                'scope': 'repo',
                                'path': str(p),
                            }
                            for p in sorted((Path(cwd) / '.agents/skills').glob('*/SKILL.md'))
                            if p.is_file() and not p.is_symlink()
                        ],
                    }
                    for cwd in params.get('cwds', [])
                ]
            },
        )
    elif method == 'thread/start':
        thread_number += 1
        state['thread_number'] = thread_number
        thread_id = '019a0290-0000-7000-8000-' + f'{thread_number:012d}'
        cwd = params['cwd']
        state['threads'][thread_id] = {
            'id': thread_id, 'cliVersion': '0.162.1', 'createdAt': 1, 'updatedAt': 1,
            'cwd': cwd, 'ephemeral': params.get('ephemeral') is True,
            'modelProvider': 'openai', 'preview': '', 'projectId': None,
            'sessionId': 'integration-session', 'source': 'appServer',
            'forkedFromId': None, 'parentThreadId': None, 'section': None,
            'sectionEnteredAt': None, 'historyMode': 'legacy', 'recencyAt': None,
            'model': 'gpt-6.1-sol', 'reasoningEffort': 'medium', 'path': None,
            'originator': None, 'threadSource': None, 'agentNickname': None,
            'agentRole': None, 'gitInfo': None, 'name': None,
            'status': {'type': 'idle'}, 'turns': [],
        }
        if config.get('session_fixture'):
            # Actual stock0.162.1 CLI default; explicit launch flag takes priority.
            source = sys.argv[sys.argv.index('--session-source') + 1] if '--session-source' in sys.argv else 'vscode'
            state['threads'][thread_id]['source'] = source
            state['threads'][thread_id]['originator'] = client_originator
        persist()
        effective_configs[thread_id] = {'cwd': cwd, 'model': params.get('model', 'gpt-6.1-sol'),
                                        'effort': params.get('config', {}).get('model_reasoning_effort', 'medium')}
        subscribed_threads.add(thread_id)
        reply(request, thread_response())
    elif method == 'thread/list':
        fixture = config.get('session_fixture', {})
        if params.get('originators'):
            emit({'id': request['id'], 'error': {'code': -32602,
                  'message': 'nonempty originators filter is unavailable on the local app-server'}})
            continue
        if not state.get('session_fixtures_seeded'):
            for original in fixture.get('threads', []):
                value = {**original, 'cwd': cwd if original['cwd'] == '{CURRENT_WORKSPACE}' else original['cwd']}
                state['threads'][value['id']] = value
            state['session_fixtures_seeded'] = True
            persist()
        archived = set(state.get('archived_threads', []))
        rows = [row for key, row in state['threads'].items()
                if (key in archived) == bool(params.get('archived', False))]
        if fixture.get('list_only_fixture_threads'):
            known = {row['id'] for row in fixture.get('threads', [])}
            rows = [row for row in rows if row['id'] in known]
        if params.get('parentThreadId'):
            rows = [row for row in rows if row.get('parentThreadId') == params['parentThreadId']]
        if params.get('ancestorThreadId'):
            ancestor = params['ancestorThreadId']
            def descendant(row):
                seen = {row['id']}
                parent = row.get('parentThreadId')
                while parent is not None:
                    if parent == ancestor:
                        return True
                    if parent in seen:
                        return False
                    seen.add(parent)
                    parent = state['threads'].get(parent, {}).get('parentThreadId')
                return False
            rows = [row for row in rows if row['id'] != ancestor and descendant(row)]
        if params.get('sourceKinds'):
            rows = [row for row in rows if row['source'] in params['sourceKinds']]
        if params.get('modelProviders'):
            rows = [row for row in rows if row['modelProvider'] in params['modelProviders']]
        if params.get('cwd'):
            choices = params['cwd'] if isinstance(params['cwd'], list) else [params['cwd']]
            rows = [row for row in rows if row['cwd'] in choices]
        key = 'updatedAt' if params.get('sortKey') == 'updated_at' else 'createdAt'
        rows.sort(key=lambda row: (row[key], row['id']), reverse=params.get('sortDirection', 'desc') == 'desc')
        cursor_value = params.get('cursor')
        offset = 0 if cursor_value is None else int(cursor_value.removeprefix('independent-page:'))
        count = min(fixture.get('page_size', 2), params.get('limit', 100))
        page = rows[offset:offset + count]
        metadata_reply(request, {'data': [{**row, 'turns': []} for row in page],
                        'nextCursor': 'independent-page:' + str(offset + count) if offset + count < len(rows) else None}, 'list')
    elif method == 'thread/archive':
        fixture = config.get('session_fixture', {})
        if params['threadId'] not in state['threads']:
            emit({'id': request['id'], 'error': {'code': -32000, 'message': 'independent original session unavailable'}})
        elif fixture.get('archive_error'):
            emit({'id': request['id'], 'error': {'code': -32000, 'message': 'independent archive refusal'}})
        elif fixture.get('archive_hold') and not Path(fixture['archive_hold']).exists():
            pending_archive = request
        else:
            finish_native_archive(request)
    elif method == 'thread/resume':
        if config.get('session_fixture', {}).get('resume_error'):
            emit({'id': request['id'], 'error': {'code': -32000,
                  'message': 'Independent exact-session bootstrap refusal'}})
            continue
        assert params['threadId'] in state['threads']
        assert not params.get('history') and not params.get('path')
        thread_id = params['threadId']
        assert not state['threads'][thread_id]['ephemeral']
        stored_cwd = state['threads'][thread_id]['cwd']
        was_loaded = thread_id in effective_configs
        subscribed = thread_id in subscribed_threads
        # Pinned092 processor4348+: subscribed loaded threads retain effective
        # config. A fresh helper/cold thread may apply supported current overrides.
        if not was_loaded or not subscribed:
            effective_configs[thread_id] = {
                'cwd': params.get('cwd', stored_cwd),
                'model': params.get('model') or state['threads'][thread_id].get('model') or 'gpt-6.1-sol',
                'effort': params.get('config', {}).get('model_reasoning_effort', state['threads'][thread_id].get('reasoningEffort')),
            }
        cwd = effective_configs[thread_id]['cwd']
        subscribed_threads.add(thread_id)
        state.setdefault('resume_observations', []).append({'threadId': thread_id,
            'was_loaded': was_loaded, 'had_subscribers': subscribed,
            'historical_cwd': stored_cwd, 'effective_cwd': cwd,
            'overrides_applied': not was_loaded or not subscribed})
        persist()
        reply(request, thread_response(params.get('excludeTurns') is True))
    elif method == 'thread/unsubscribe':
        target = params['threadId']
        status = 'notLoaded' if target not in effective_configs else 'unsubscribed' if target in subscribed_threads else 'notSubscribed'
        subscribed_threads.discard(target)
        reply(request, {'status': status})
    elif method == 'thread/items/list':
        identity = params['threadId']
        assert identity in state['threads'] and config.get('observe_context_continuity')
        assert not params.get('history') and not params.get('path')
        entries = list(state.get('item_history', {}).get(identity, []))
        if params.get('turnId'):
            entries = [entry for entry in entries if entry['turnId'] == params['turnId']]
        direction = params.get('sortDirection') or 'asc'
        assert direction in ('asc', 'desc')
        if direction == 'desc':
            entries.reverse()
        cursor_value = params.get('cursor')
        assert cursor_value is None or isinstance(cursor_value, str)
        offset = 0 if cursor_value is None else int(cursor_value.removeprefix('genuine-items-page:'))
        count = min(config.get('session_fixture', {}).get('items_page_size', 2), (params.get('limit') or 100))
        assert count > 0
        page = entries[offset:offset + count]
        metadata_reply(request, {'data': page,
            'nextCursor': 'genuine-items-page:' + str(offset + count) if offset + count < len(entries) else None,
            'backwardsCursor': None}, 'items')
    elif method == 'thread/read':
        if config.get('session_fixture', {}).get('read_error'):
            emit({'id': request['id'], 'error': {'code': -32000, 'message': 'Independent original metadata read unavailable'}})
            continue
        assert params['threadId'] in state['threads']
        original_id = thread_id
        thread_id = params['threadId']
        metadata_reply(request, {'thread': saved_thread(not params.get('includeTurns', False))}, 'read')
        thread_id = original_id
    elif method == 'thread/name/set':
        assert set(params) == {'threadId', 'name'} and isinstance(params['name'], str)
        if params['threadId'] not in state['threads']:
            emit({'id': request['id'], 'error': {'code': -32000, 'message': 'Original session unavailable'}})
        else:
            state['threads'][params['threadId']]['name'] = params['name']
            persist()
            reply(request, {})
    elif method == 'thread/settings/update':
        assert params['threadId'] == thread_id
        assert params.get('approvalPolicy', 'never') == 'never'
        assert params.get('sandboxPolicy', {'type': 'readOnly', 'networkAccess': False}) == {
            'type': 'readOnly',
            'networkAccess': False,
        }
        effective = effective_configs.setdefault(thread_id, {})
        effective.update({key: params[key] for key in ('model', 'effort') if key in params})
        reply(request, {})
        notify(
            'thread/settings/updated',
            {
                'threadId': thread_id,
                'threadSettings': {
                    'disabledPluginIds': [],
                    'cwd': cwd,
                    'approvalPolicy': 'never',
                    'approvalsReviewer': 'user',
                    'sandboxPolicy': {'type': 'readOnly', 'networkAccess': False},
                    'activePermissionProfile': None,
                    'model': effective.get('model', 'gpt-6.1-sol'),
                    'modelProvider': 'openai',
                    'serviceTier': None,
                    'effort': effective.get('effort', 'medium'),
                    'summary': None,
                    'collaborationMode': {
                        'mode': 'default',
                        'settings': {
                            'model': effective.get('model', 'gpt-6.1-sol'),
                            'reasoning_effort': effective.get('effort', 'medium'),
                            'developer_instructions': None,
                        },
                    },
                    'multiAgentMode': 'explicitRequestOnly',
                    'personality': None,
                },
            },
        )
    elif method == 'turn/start':
        assert not pending
        turn_number += 1
        turn_id = '019a0290-0000-7000-8000-' + f'{turn_number + 1:012d}'
        # The finite test may configure calls after account bootstrap, before its first turn.
        current = json.loads(Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).read_text(encoding='utf-8'))
        config.update(current)
        state['turn_number'] = turn_number
        record = {'threadId': thread_id, 'turnId': turn_id, 'input': params.get('input')}
        if config.get('observe_context_continuity'):
            prior = [row for row in state['inputs'] if row['threadId'] == thread_id]
            record['actual_prior_input_count'] = len(prior)
            record['first_actual_input_sha256'] = hashlib.sha256(json.dumps(prior[0]['input'], sort_keys=True, ensure_ascii=False).encode()).hexdigest() if prior else None
            record['actual_request_model'] = params.get('model')
            record['effective_model'] = effective_configs.get(thread_id, {}).get('model')
        if config.get('observe_context_continuity'):
            # Pinned ThreadItem.userMessage retains the actual acknowledged
            # turn/start UserInput array. This is not app history injection.
            actual_user_entry = {
                'turnId': turn_id, 'item': {'type': 'userMessage', 'id': turn_id + '-actual-user',
                    'clientId': params.get('clientId'), 'content': json.loads(json.dumps(params.get('input', [])))},
                'startedAtMs': None, 'completedAtMs': None}
        state['inputs'].append(record)
        persist()
        calls = current['turns'][turn_number - 1]
        cursor['position'] = 0
        unacked_hold = current.get('fixture_unacked_start_hold')
        if unacked_hold and not Path(unacked_hold).exists():
            assert fixture_unacked_start is None and not calls, 'The narrow ACK fixture holds only one actual read-only no-tool turn'
            assert config.get('observe_context_continuity'), 'The actual accepted input must have its genuine pinned persistence owner'
            state.setdefault('item_history', {}).setdefault(thread_id, []).append(actual_user_entry)
            fixture_unacked_start = {'request': json.loads(json.dumps(request)), 'thread': thread_id,
                'turn': turn('inProgress'), 'hold': unacked_hold,
                'final_text': config.get('final_text', 'The original read-only fixture turn is settled.')}
            state.setdefault('actual_unacked_requests', []).append(json.loads(json.dumps(request)))
            persist()
            continue
        delayed = current.get('archive_before_start_reply')
        if delayed:
            assert pending_turn_start is None, 'Only one actual original pending start belongs to this fixture hold'
            assert delayed['reply'] in ('success', 'refusal'), 'Closed original pending-start reply cases only'
            pending_turn_start = {'request': json.loads(json.dumps(request)), 'thread': thread_id,
                'turn': turn('inProgress'), 'hold': delayed['hold'], 'reply': delayed['reply'],
                'user_entry': actual_user_entry if config.get('observe_context_continuity') else None}
            archived = state.setdefault('archived_threads', [])
            if thread_id not in archived:
                archived.append(thread_id)
            persist()
            notify('thread/archived', {'threadId': thread_id})
            continue
        reply(request, {'turn': turn('inProgress')})
        if config.get('observe_context_continuity'):
            state.setdefault('item_history', {}).setdefault(thread_id, []).append(actual_user_entry)
            persist()
        notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
        advance()
    elif method == 'turn/interrupt':
        if fixture_unacked_start and params.get('threadId') == fixture_unacked_start['thread']:
            original = fixture_unacked_start;fixture_unacked_start = None
            reply(original['request'], {'turn': original['turn']})
            reply(request, {})
            interrupted = {**original['turn'], 'status': 'interrupted'}
            state['threads'][original['thread']]['turns'].append(interrupted);persist()
            notify('turn/completed', {'threadId': original['thread'], 'turn': interrupted})
        else:
            reply(request, {})
            notify('turn/completed', {'threadId': thread_id, 'turn': turn('interrupted')})
    elif 'id' in request:
        emit({
            'id': request['id'],
            'error': {'code': -32601, 'message': 'Not in the finite fixture'},
        })
