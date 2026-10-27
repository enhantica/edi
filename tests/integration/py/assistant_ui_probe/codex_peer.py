"""Finite offline Codex 0.162.1 protocol fixture for the existing real Main host.

Wire shapes are independently retained in the earlier assistant stdio fixture at
77ba02de. This peer executes no commands, accesses no account and calls no service.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

config = json.loads(Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).read_text(encoding='utf-8'))
trace = Path(config['trace'])
thread_id = '019a0290-0000-7000-8000-000000000001'
turn_id = '019a0290-0000-7000-8000-000000000002'
pending = {}
calls = []
turn_number = 0
thread_number = 0
cursor = {'position': 0, 'sequence': 0, 'pending_final': False, 'research': None}
native_ids = {}


def emit(value):
    with trace.with_suffix('.sent.jsonl').open('a', encoding='utf-8') as output:
        output.write(json.dumps(value) + '\n')
    print(json.dumps(value, ensure_ascii=False), flush=True)


def reply(request, value):
    emit({'id': request['id'], 'result': value})


def notify(method, params):
    emit({'method': method, 'params': params})


def turn(status):
    return {'id': turn_id, 'items': [], 'status': status}


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
        notify('turn/completed', {'threadId': thread_id, 'turn': turn('completed')})
        return
    spec = calls[cursor['position']]
    cursor['position'] += 1
    cursor['sequence'] += 1
    call_id = spec.get('call_id', 'integration-call-' + str(cursor['sequence']))
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
    notify('item/started', binding)
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
        thread_id = '019a0290-0000-7000-8000-' + f'{thread_number:012d}'
        cwd = params['cwd']
        reply(
            request,
            {
                'approvalPolicy': 'never',
                'approvalsReviewer': 'user',
                'cwd': cwd,
                'model': 'gpt-6.1-sol',
                'modelProvider': 'openai',
                'reasoningEffort': 'medium',
                'sandbox': {'type': 'readOnly', 'networkAccess': False},
                'thread': {
                    'id': thread_id,
                    'cliVersion': '0.162.1',
                    'createdAt': 1,
                    'updatedAt': 1,
                    'cwd': cwd,
                    'ephemeral': params.get('ephemeral') is True,
                    'modelProvider': 'openai',
                    'preview': '',
                    'projectId': None,
                    'sessionId': 'integration-session',
                    'source': 'appServer',
                    'status': {'type': 'idle'},
                    'turns': [],
                },
            },
        )
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
        calls = config['turns'][turn_number - 1]
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
