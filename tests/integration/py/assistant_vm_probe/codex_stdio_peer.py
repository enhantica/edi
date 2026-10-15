"""Finite task-owned stdio dependency, not an official runtime/provider witness.

Original IDs/text and complete structures follow public codex0.162.1 schemas.
The peer never executes commands, reads accounts or calls a service.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

config = json.loads(Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).read_text(encoding='utf-8'))
trace = Path(config['trace'])
scenario = config.get('scenario', 'complete')
thread_id = '019a0290-0000-7000-8000-000000000001'
turn_id = '019a0290-0000-7000-8000-000000000002'
server_id = 'original-approval-1'


def emit(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')
    sys.stdout.flush()


def exact_record(byte_count):
    value = {'method': 'original/ignored', 'params': {'padding': ''}}
    prefix = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()
    value['params']['padding'] = 'x' * (byte_count - len(prefix))
    assert len(json.dumps(value, separators=(',', ':')).encode()) == byte_count, (
        'GR2 SETUP: independent complete JSONL encoding has exact declared byte count'
    )
    return value


def reply(request, value):
    emit({'id': request['id'], 'result': value})


def notify(method, params):
    emit({'method': method, 'params': params})


def turn(status):
    return {'id': turn_id, 'items': [], 'status': status}


def complete():
    item = {'type': 'agentMessage', 'id': 'original-message', 'text': 'Original offline reply'}
    notify('item/started', {'threadId': thread_id, 'turnId': turn_id, 'item': item})
    notify(
        'item/completed',
        {'threadId': thread_id, 'turnId': turn_id, 'item': item, 'completedAtMs': 1},
    )
    notify('turn/completed', {'threadId': thread_id, 'turn': turn('completed')})


for line in sys.stdin:
    request = json.loads(line)
    with trace.open('a', encoding='utf-8') as output:
        output.write(json.dumps(request, ensure_ascii=False) + '\n')
    method = request.get('method')
    params = request.get('params') or {}
    if method is None:
        if request.get('id') == server_id:
            complete()
        continue
    if method == 'initialize':
        reply(
            request,
            {
                'userAgent': 'original-offline-peer/0.162.1',
                'codexHome': str(trace.parent / 'peer-unused-profile'),
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
                    'email': 'original@example.invalid',
                    'planType': 'plus',
                },
                'requiresOpenaiAuth': False,
            },
        )
    elif method == 'model/list':
        reply(
            request,
            {
                'data': [
                    {
                        'id': 'gpt-6.1-sol',
                        'model': 'gpt-6.1-sol',
                        'displayName': 'Original offline model',
                        'description': 'Fixture',
                        'hidden': False,
                        'isDefault': True,
                        'defaultReasoningEffort': 'medium',
                        'supportedReasoningEfforts': [
                            {'reasoningEffort': 'medium', 'description': 'Original'}
                        ],
                    }
                ]
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
                                'name': name,
                                'description': 'Original fixture ' + name,
                                'enabled': True,
                                'scope': 'repo',
                                'path': str(Path(cwd) / '.agents/skills' / name / 'SKILL.md'),
                            }
                            for name in ['project-assistance', 'fullprof-intake', 'gsas-intake']
                        ],
                    }
                    for cwd in params.get('cwds', [])
                ]
            },
        )
    elif method == 'thread/start':
        cwd = params['cwd']
        value = {
            'approvalPolicy': 'on-request',
            'approvalsReviewer': 'user',
            'cwd': cwd,
            'model': 'gpt-6.1-sol',
            'modelProvider': 'openai',
            'sandbox': {
                'type': 'workspaceWrite',
                'writableRoots': [cwd],
                'networkAccess': False,
                'excludeSlashTmp': True,
                'excludeTmpdirEnvVar': True,
            },
            'thread': {
                'id': thread_id,
                'cliVersion': '0.162.1',
                'createdAt': 1,
                'updatedAt': 1,
                'cwd': cwd,
                'ephemeral': True,
                'modelProvider': 'openai',
                'preview': '',
                'projectId': None,
                'sessionId': 'original-session',
                'source': 'appServer',
                'status': {'type': 'idle'},
                'turns': [],
            },
        }
        if scenario == 'different-cwd':
            value['cwd'] = str(trace.parent / 'unadmitted-workspace')
        elif scenario == 'network-enabled':
            value['sandbox']['networkAccess'] = True
        elif scenario == 'different-reviewer':
            value['approvalsReviewer'] = 'auto_review'
        elif scenario == 'different-provider':
            value['modelProvider'] = 'other-original-provider'
        reply(request, value)
    elif method == 'turn/start':
        reply(request, {'turn': turn('inProgress')})
        notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
        if scenario in {'hold', 'steer-no-ack'}:
            continue
        if scenario == 'approval-expansion':
            emit({
                'id': server_id,
                'method': 'item/commandExecution/requestApproval',
                'params': {
                    'threadId': thread_id,
                    'turnId': turn_id,
                    'itemId': 'original-command',
                    'startedAtMs': 1,
                    'command': 'original command, never executed by peer',
                    'proposedExecpolicyAmendment': ['original-command'],
                },
            })
        elif scenario == 'record-overflow':
            emit(exact_record(1048577))
        elif scenario == 'wire-overflow':
            for _ in range(9):
                emit(exact_record(1048576))
        elif scenario == 'events-overflow':
            for _ in range(8193):
                notify('original/ignored', {})
        elif scenario == 'stderr-overflow':
            sys.stderr.write('x' * 8388609)
            sys.stderr.flush()
        elif scenario == 'record-exact':
            emit(exact_record(1048576))
            complete()
        else:
            complete()
    elif method == 'turn/steer':
        if scenario == 'steer-no-ack':
            sys.exit(0)  # Actual process EOF after receiving, before acknowledging the steer.
        reply(request, {'turnId': turn_id})
    elif method == 'turn/interrupt':
        reply(request, {})
        notify('turn/completed', {'threadId': thread_id, 'turn': turn('interrupted')})
    elif method in {'account/logout', 'account/login/cancel'}:
        reply(request, {})
    elif 'id' in request:
        emit({
            'id': request['id'],
            'error': {'code': -32601, 'message': 'Original peer unsupported request'},
        })
