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
Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).with_suffix('.peer-pid').write_text(
    str(os.getpid()), encoding='utf-8'
)
scenario = config.get('scenario', 'complete')
thread_id = '019a0290-0000-7000-8000-000000000001'
turn_id = '019a0290-0000-7000-8000-000000000002'
server_id = 'original-approval-1'
turn_number = 0
pending_starts = []


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


# These additional finite scenarios use ordinary published messages. They do not
# add a production control channel or execute any command/model tool.
def original_item(kind='commandExecution', status='completed'):
    if kind == 'agentMessage':
        return {'type': kind, 'id': 'authority-item', 'text': 'Original immutable text'}
    if kind == 'fileChange':
        return {'type': kind, 'id': 'authority-item', 'status': status, 'changes': []}
    value = {
        'type': kind,
        'id': 'authority-item',
        'status': status,
        'command': 'original harmless command, never executed',
        'commandActions': [],
        'cwd': str(Path.cwd()),
    }
    if status == 'completed':
        value.update(exitCode=0, aggregatedOutput='Original complete output', durationMs=1)
    return value


def publish_item(item, *, completed=False, bound=True):
    params = {'threadId': thread_id, 'item': item}
    if bound:
        params['turnId'] = turn_id
    if completed:
        params['completedAtMs'] = 1
    notify('item/completed' if completed else 'item/started', params)


def ask_original(*, bound=True):
    publish_item({
        'type': 'dynamicToolCall',
        'id': 'original-question-item',
        'tool': 'request_user_input',
        'arguments': {},
        'status': 'inProgress',
    })
    request = {
        'id': 'original-question-rpc',
        'method': 'item/tool/requestUserInput',
        'params': {
            'threadId': thread_id,
            'turnId': turn_id,
            'itemId': 'original-question-item',
            'isBlocking': True,
            'questions': [
                {
                    'id': 'original-question',
                    'header': 'Original choice',
                    'question': 'Which original option?',
                    'options': [{'label': 'Original answer', 'description': 'Fixture choice'}],
                }
            ],
        },
    }
    if not bound:
        del request['params']['turnId']
    emit(request)


def lifetime_output(channel):
    if channel == 'events':
        for _ in range(4300):
            notify('original/ignored', {})
    elif channel == 'wire':
        for _ in range(5):
            emit(exact_record(1048576))
    elif channel == 'stderr':
        sys.stderr.write('x' * 5000000)
        sys.stderr.flush()
    complete()


def status_tool(kind, status):
    value = {'id': 'authority-item', 'type': kind, 'status': status}
    if kind == 'mcpToolCall':
        value.update(server='original-offline-server', tool='original-tool', arguments={})
    elif kind == 'dynamicToolCall':
        value.update(tool='original-tool', arguments={})
    else:
        value.update(tool='wait', senderThreadId=thread_id, receiverThreadIds=[], agentsStates={})
    return value


def gn_remaining_start(case):
    if case == 'partial-message':
        publish_item(original_item('agentMessage'))
        notify(
            'item/agentMessage/delta',
            {
                'threadId': thread_id,
                'turnId': turn_id,
                'itemId': 'authority-item',
                'delta': ' original partial suffix',
            },
        )
        notify('turn/completed', {'threadId': thread_id, 'turn': turn('completed')})
    elif case == 'final-message-snapshot':
        publish_item(original_item('agentMessage'))
        final = turn('completed')
        final['items'] = [original_item('agentMessage')]
        notify('turn/completed', {'threadId': thread_id, 'turn': final})
    elif case.startswith('status-'):
        _, kind, route, status = case.split(':')
        publish_item(status_tool(kind, 'inProgress'))
        item = status_tool(kind, status)
        if status == 'missing':
            del item['status']
        final = turn('completed')
        if route == 'item':
            publish_item(item, completed=True)
        else:
            final['items'] = [item]
        notify('turn/completed', {'threadId': thread_id, 'turn': final})
    elif case.startswith('interruption:'):
        _, kind, outcome = case.split(':')
        prior = original_item()
        prior['id'] = 'prior-genuine-final'
        publish_item(prior)
        publish_item(prior, completed=True)
        unfinished = original_item(kind, 'inProgress')
        publish_item(unfinished)
        final = turn(outcome)
        final['items'] = [prior, unfinished]
        if outcome == 'failed':
            final['error'] = {'message': 'Original bounded failed turn'}
        notify('turn/completed', {'threadId': thread_id, 'turn': final})
    elif case.startswith('progress:'):
        progress_original(case.split(':')[1])
    else:
        publish_item(original_item('agentMessage'))


def progress_original(kind):
    if kind == 'question':
        ask_original()
    elif kind == 'command':
        publish_item(original_item('commandExecution', 'inProgress'))
    elif kind == 'plan':
        publish_item({'id': 'authority-item', 'type': 'plan', 'text': 'Original plan'})
    else:
        publish_item({'id': 'authority-item', 'type': 'reasoning', 'summary': [], 'content': []})


def gn_progress(case):
    kind = case.split(':')[1]
    if kind == 'question':
        return
    methods = {
        'command': 'item/commandExecution/outputDelta',
        'plan': 'item/plan/delta',
        'summary': 'item/reasoning/summaryTextDelta',
        'reasoning': 'item/reasoning/textDelta',
    }
    params = {
        'threadId': thread_id,
        'turnId': turn_id,
        'itemId': 'authority-item',
        'delta': 'Original bounded current progress',
    }
    if kind == 'summary':
        params['summaryIndex'] = 0
    elif kind == 'reasoning':
        params['contentIndex'] = 0
    notify(methods[kind], params)


def gn82_start(case):
    if case in {'stop-existing', 'question-answer'}:
        ask_original()
    elif case.startswith('mcp-'):
        publish_item(status_tool('mcpToolCall', 'inProgress'))
        if case == 'mcp-final':
            publish_item(status_tool('mcpToolCall', 'completed'), completed=True)
    else:
        publish_item(original_item('agentMessage'))


def gn82_steer(case):
    if case.startswith('mcp-'):
        notify(
            'item/mcpToolCall/progress',
            {
                'threadId': thread_id,
                'turnId': 'unrelated-turn' if case == 'mcp-stale' else turn_id,
                'itemId': 'authority-item',
                'message': 'Original bounded MCP progress',
            },
        )


def gn_start(request):
    if scenario == 'gn:logout-late-start':
        pending_starts.append(request)
        return
    reply(request, {'turn': turn('inProgress')})
    notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
    case = scenario.removeprefix('gn:')
    if case.startswith('x:'):
        gn82_start(case[2:])
    elif case.startswith('r:'):
        gn_remaining_start(case[2:])
    elif case in {'question-wrong-resolve', 'question-stale-answer'}:
        ask_original()
    elif case in {'immutable-duplicate', 'immutable-type', 'immutable-delta'}:
        item = original_item('agentMessage' if case == 'immutable-delta' else 'commandExecution')
        publish_item(item)
        publish_item(item, completed=True)
    elif case.startswith('finished-'):
        item = original_item(case.removeprefix('finished-'))
        publish_item(item)
        publish_item(item, completed=True)
        notify('turn/completed', {'threadId': thread_id, 'turn': turn('completed')})
    elif case.startswith('unfinished-'):
        publish_item(original_item(case.removeprefix('unfinished-'), 'inProgress'))
        notify('turn/completed', {'threadId': thread_id, 'turn': turn('completed')})
    elif case.startswith('lifetime-'):
        lifetime_output(case.removeprefix('lifetime-'))
    elif case == 'workspace-change':
        selected = Path.cwd() / 'inputs' / 'original-selected.txt'
        # Only the application-staged, task-owned copy is modified. This is an
        # ownership witness, not actual runtime/tool execution evidence.
        selected.write_bytes(b'Changed only inside the first admitted workspace')
        sys.exit(0)
    elif case in {'effort-auto', 'effort-model'}:
        complete()
    else:
        publish_item(original_item('agentMessage'))


def gn_steer(request):
    case = scenario.removeprefix('gn:')
    if case in {'steer-missing', 'steer-wrong'}:
        reply(request, {} if case == 'steer-missing' else {'turnId': 'unrelated-turn'})
        return
    reply(request, {'turnId': turn_id})
    gn_steer_notification(case)


def gn_steer_notification(case):
    if case.startswith('x:'):
        gn82_steer(case[2:])
    elif case.startswith('r:progress:'):
        gn_progress(case[2:])
    elif case.startswith('account-'):
        mode = case.removeprefix('account-')
        notify('account/updated', {'authMode': None if mode == 'null' else mode})
    elif case == 'missing-request-turn':
        ask_original(bound=False)
    elif case == 'missing-item-turn':
        publish_item(
            {'type': 'agentMessage', 'id': 'unbound-item', 'text': 'Unbound text'}, bound=False
        )
    elif case == 'missing-delta-turn':
        notify(
            'item/agentMessage/delta',
            {
                'threadId': thread_id,
                'itemId': 'authority-item',
                'delta': 'UNBOUND APPEND',
            },
        )
    elif case == 'immutable-duplicate':
        item = original_item()
        item['aggregatedOutput'] = 'CHANGED finalized output'
        publish_item(item, completed=True)
    elif case == 'immutable-type':
        publish_item(original_item('fileChange'), completed=True)
    elif case == 'immutable-delta':
        notify(
            'item/agentMessage/delta',
            {
                'threadId': thread_id,
                'turnId': turn_id,
                'itemId': 'authority-item',
                'delta': 'LATE APPEND',
            },
        )
    elif case == 'question-wrong-resolve':
        notify(
            'serverRequest/resolved',
            {
                'requestId': 'original-question-rpc',
                'threadId': 'unrelated-thread',
            },
        )
    elif case == 'question-stale-answer':
        sys.exit(0)
    elif case == 'unknown-control':
        notify('original/unknown', {'threadId': thread_id, 'turnId': turn_id})


for line in sys.stdin:
    request = json.loads(line)
    with trace.open('a', encoding='utf-8') as output:
        output.write(json.dumps(request, ensure_ascii=False) + '\n')
    method = request.get('method')
    params = request.get('params') or {}
    if method is None:
        if request.get('id') == server_id:
            complete()
        elif request.get('id') == 'original-question-rpc' and scenario == 'gn:x:question-answer':
            publish_item(
                {
                    'type': 'dynamicToolCall',
                    'id': 'original-question-item',
                    'tool': 'request_user_input',
                    'arguments': {},
                    'status': 'completed',
                },
                completed=True,
            )
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
    elif method == 'model/list' and scenario.startswith('gn:effort-'):
        reply(
            request,
            {
                'data': [
                    {
                        'id': slug,
                        'model': slug,
                        'displayName': 'Original ' + slug,
                        'description': 'Independent catalogue effort choice',
                        'hidden': False,
                        'isDefault': index == 0,
                        'defaultReasoningEffort': 'medium',
                        'supportedReasoningEfforts': [
                            {'reasoningEffort': effort, 'description': 'Original ' + effort}
                            for effort in (['medium', 'high'] if index == 0 else ['medium'])
                        ],
                    }
                    for index, slug in enumerate(['gpt-6.1-sol', 'gpt-6-sol'])
                ]
            },
        )
    elif method == 'model/list' and scenario.startswith('gn:catalogue-'):
        # Complete supplied metadata, not normalized labels, defines this budget.
        page = 1 if params.get('cursor') else 0
        model = {
            'id': 'fixture-model-' + str(page),
            'model': 'fixture-model-' + str(page),
            'displayName': 'Original catalogue ' + str(page),
            'hidden': False,
            'isDefault': page == 0,
            'defaultReasoningEffort': 'medium',
            'supportedReasoningEfforts': [
                {'reasoningEffort': 'medium', 'description': 'Original'}
            ],
            'description': 'x' * (530000 if scenario.endswith('over') else 500000),
        }
        reply(request, {'data': [model], 'nextCursor': 'original-page-2' if page == 0 else None})
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
        turn_number += 1
        if scenario.startswith('gn:'):
            # New independent turns have distinct authoritative original IDs.
            turn_id = '019a0290-0000-7000-8000-' + f'{turn_number + 1:012d}'
            gn_start(request)
            continue
        if scenario == 'start-pending':
            continue  # Genuine received request; no turn ID is admitted yet.
        reply(request, {'turn': turn('inProgress')})
        notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
        if scenario in {'hold', 'steer-no-ack'}:
            continue
        if scenario == 'approval-expansion':
            notify(
                'item/started',
                {
                    'threadId': thread_id,
                    'turnId': turn_id,
                    'item': {
                        'type': 'commandExecution',
                        'id': 'original-command',
                        'status': 'inProgress',
                        'command': 'original command, never executed by peer',
                        'commandActions': [],
                        'cwd': params['sandboxPolicy']['writableRoots'][0],
                    },
                },
            )
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
        if scenario.startswith('gn:'):
            gn_steer(request)
            continue
        if scenario == 'steer-no-ack':
            sys.exit(0)  # Actual process EOF after receiving, before acknowledging the steer.
        reply(request, {'turnId': turn_id})
    elif method == 'turn/interrupt':
        if scenario == 'gn:x:stop-new':
            ask_original()
            continue
        if scenario in {'gn:r:stop-unsettled', 'gn:x:stop-existing'}:
            continue  # A genuine unsettled first revoke; no fabricated terminal/ack.
        reply(request, {})
        notify('turn/completed', {'threadId': thread_id, 'turn': turn('interrupted')})
    elif method in {'account/logout', 'account/login/cancel'}:
        if scenario == 'gn:logout-late-start' and pending_starts:
            reply(pending_starts[0], {'turn': turn('inProgress')})
            notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
        if scenario not in {'gn:logout-hold', 'gn:logout-late-start'}:
            reply(request, {})
    elif 'id' in request:
        emit({
            'id': request['id'],
            'error': {'code': -32601, 'message': 'Original peer unsupported request'},
        })
