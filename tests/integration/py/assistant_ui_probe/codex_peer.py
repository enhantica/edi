"""Finite offline Codex 0.162.1 protocol fixture for the existing real Main host.

Wire shapes are independently retained in the earlier assistant stdio fixture at
77ba02de. This peer executes no commands, accesses no account and calls no service.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

config = json.loads(Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).read_text(encoding='utf-8'))
trace = Path(config['trace'])
thread_id = '019a0290-0000-7000-8000-000000000001'
turn_id = '019a0290-0000-7000-8000-000000000002'
pending = {}
retry_after_response = {}
first_response_for_retry = {}
calls = []
turn_number = 0
thread_number = 0
cursor = {'position': 0, 'sequence': 0, 'pending_final': False, 'research': None}
native_ids = {}
emit_lock = threading.RLock()
usage_notifications_delivered = False
pending_archive = None
client_originator = None
if config.get("session_fixture"):
    with trace.open("a", encoding="utf-8") as output:
        output.write(json.dumps({"fixture_runtime_started": {"pid": os.getpid(), "parent_pid": os.getppid()}}) + "\n")
# Provider-owned offline persistence, using pinned092d Thread/Resume/Read shapes.
# This never fabricates application state or scientific results. A killed helper
# must resume the original stored ID, rather than silently starting another one.
state_path = trace.with_suffix('.provider-state.json')
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
    return {
        'thread': saved_thread(exclude_turns), 'model': 'gpt-6.1-sol',
        'modelProvider': 'openai', 'serviceTier': None, 'disabledPluginIds': [],
        'cwd': cwd, 'instructionSources': [], 'approvalPolicy': 'never',
        'approvalsReviewer': 'user',
        'sandbox': {'type': 'readOnly', 'networkAccess': False},
        'reasoningEffort': 'medium', 'collaborationMode': None,
        'turnsBackwardsCursor': None, 'itemsBackwardsCursor': None,
    }


def emit(value):
    with emit_lock:
        with trace.with_suffix('.sent.jsonl').open('a', encoding='utf-8') as output:
            output.write(json.dumps(value) + '\n')
        print(json.dumps(value, ensure_ascii=False), flush=True)


def reply(request, value):
    emit({'id': request['id'], 'result': value})


def notify(method, params):
    emit({'method': method, 'params': params})


def turn(status):
    return {'id': turn_id, 'rootTurnId': None, 'items': [], 'itemsView': 'full',
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
        item = {'type': 'agentMessage', 'id': turn_id + '-final', 'text': text}
        binding = {'threadId': thread_id, 'turnId': turn_id, 'item': item}
        notify('item/started', binding)
        notify('item/completed', {**binding, 'completedAtMs': 1})
        completed = turn('completed')
        state['threads'][thread_id]['turns'].append(completed)
        persist()
        notify('turn/completed', {'threadId': thread_id, 'turn': completed})
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
        item = {'type': 'agentMessage', 'id': call_id, 'text': ''}
        notify('item/started', {**binding, 'item': item})
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


for line in sys.stdin:
    request = json.loads(line)
    with trace.open('a', encoding='utf-8') as output:
        output.write(json.dumps(request) + '\n')
    if 'method' not in request:
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
    elif method == 'account/read':
        reply(
            request,
            {
                'account': {
                    'type': 'chatgpt',
                    'email': 'integration@example.invalid',
                    'planType': 'plus',
                },
                'requiresOpenaiAuth': False,
            },
        )
    elif method == 'account/rateLimits/read':
        reply(request, {'rateLimits': None, 'rateLimitsByLimitId': {}})
        current = json.loads(Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).read_text(encoding='utf-8'))
        if current.get('usage_notifications') and not usage_notifications_delivered:
            usage_notifications_delivered = True
            for event in current['usage_notifications']:
                notify(event['method'], {**event['params'], 'threadId': thread_id})
        if pending_archive and Path(config['session_fixture']['archive_hold']).exists():
            original = pending_archive
            pending_archive = None
            state.setdefault('archived_threads', []).append(original['params']['threadId'])
            persist()
            reply(original, {})
        if cursor['research'] and Path(cursor['research'][0]).exists():
            notify('item/completed', cursor['research'][1])
            cursor['research'] = None
            advance()
        if cursor['pending_final'] and Path(config['final_gate']).exists():
            advance()
    elif method == 'model/list':
        reply(
            request,
            {
                'data': [
                    {
                        'id': 'gpt-6.1-sol',
                        'model': 'gpt-6.1-sol',
                        'displayName': 'Independent offline model',
                        'description': 'Protocol fixture',
                        'hidden': False,
                        'isDefault': True,
                        'defaultReasoningEffort': 'medium',
                        'supportedReasoningEfforts': [
                            {'reasoningEffort': 'medium', 'description': 'Fixture'}
                        ],
                    }
                ],
                'nextCursor': None,
            },
        )
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
        reply(request, {'data': [{**row, 'turns': []} for row in page],
                        'nextCursor': 'independent-page:' + str(offset + count) if offset + count < len(rows) else None})
    elif method == 'thread/archive':
        fixture = config.get('session_fixture', {})
        if params['threadId'] not in state['threads']:
            emit({'id': request['id'], 'error': {'code': -32000, 'message': 'independent original session unavailable'}})
        elif fixture.get('archive_error'):
            emit({'id': request['id'], 'error': {'code': -32000, 'message': 'independent archive refusal'}})
        elif fixture.get('archive_hold') and not Path(fixture['archive_hold']).exists():
            pending_archive = request
        else:
            state.setdefault('archived_threads', []).append(params['threadId'])
            persist()
            reply(request, {})
    elif method == 'thread/resume':
        # Actual pinned selector and metadata, not history-based reconstruction.
        assert params['threadId'] in state['threads']
        assert not params.get('history') and not params.get('path')
        thread_id = params['threadId']
        assert not state['threads'][thread_id]['ephemeral']
        cwd = state['threads'][thread_id]['cwd']
        assert params.get('cwd', cwd) == cwd
        reply(request, thread_response(params.get('excludeTurns') is True))
    elif method == 'thread/read':
        assert params['threadId'] in state['threads']
        original_id = thread_id
        thread_id = params['threadId']
        reply(request, {'thread': saved_thread(not params.get('includeTurns', False))})
        thread_id = original_id
    elif method == 'thread/settings/update':
        assert params['threadId'] == thread_id
        assert params.get('approvalPolicy', 'never') == 'never'
        assert params.get('sandboxPolicy', {'type': 'readOnly', 'networkAccess': False}) == {
            'type': 'readOnly',
            'networkAccess': False,
        }
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
                    'model': 'gpt-6.1-sol',
                    'modelProvider': 'openai',
                    'serviceTier': None,
                    'effort': 'medium',
                    'summary': None,
                    'collaborationMode': {
                        'mode': 'default',
                        'settings': {
                            'model': 'gpt-6.1-sol',
                            'reasoning_effort': 'medium',
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
        state['inputs'].append({'threadId': thread_id, 'turnId': turn_id, 'input': params.get('input')})
        persist()
        calls = current['turns'][turn_number - 1]
        cursor['position'] = 0
        reply(request, {'turn': turn('inProgress')})
        notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
        advance()
    elif method == 'turn/interrupt':
        reply(request, {})
        notify('turn/completed', {'threadId': thread_id, 'turn': turn('interrupted')})
    elif 'id' in request:
        emit({
            'id': request['id'],
            'error': {'code': -32601, 'message': 'Not in the finite fixture'},
        })
