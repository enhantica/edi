"""Finite task-owned stdio dependency, not an official runtime/provider witness.

Original IDs/text and complete structures follow public codex0.162.1 schemas.
The peer never executes commands, reads accounts or calls a service.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from threading import Timer

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
result_thread_number = 0
pending_starts = []
experimental_api = False
clear_prior = None


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
    item = {'type': 'agentMessage', 'id': turn_id + '-message' if scenario == 'fileauth'
            else 'original-message', 'text': f'Original fileauth reply {turn_number}'
            if scenario == 'fileauth' else 'Original offline reply'}
    notify('item/started', {'threadId': thread_id, 'turnId': turn_id, 'item': item})
    notify(
        'item/completed',
        {'threadId': thread_id, 'turnId': turn_id, 'item': item, 'completedAtMs': 1},
    )
    notify('turn/completed', {'threadId': thread_id, 'turn': turn('completed')})


def clear_observation(kind, original):
    with trace.with_suffix('.clear-events.jsonl').open('a', encoding='utf-8') as output:
        output.write(json.dumps({'kind': kind, 'pid': os.getpid(), **original}) + '\n')


def clear_completion(original, text, *, old=False):
    clear_observation('old-emission' if old else 'completion', original)
    binding = {'threadId': original['threadId'], 'turnId': original['turnId']}
    if original.get('work'):
        work = {**original['work'], 'status': 'completed', 'exitCode': 0}
        notify('item/completed', {**binding, 'item': work, 'completedAtMs': 1})
    suffix = '-late-message' if old else '-message'
    item = {'type': 'agentMessage', 'id': original['turnId'] + suffix, 'text': text}
    notify('item/started', {**binding, 'item': item})
    notify('item/completed', {**binding, 'item': item, 'completedAtMs': 1})
    notify('turn/completed', {
        'threadId': original['threadId'],
        'turn': {'id': original['turnId'], 'items': [], 'status': 'completed'},
    })


def clear_start(request):
    global clear_prior, turn_id  # noqa: PLW0603 -- ordinary peer protocol state
    # Real request trace survives a process replacement; never reuse a thread
    # identity or manufacture an old-channel emission in a replacement process.
    starts = [json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()
              if json.loads(line).get('method') == 'turn/start']
    turn_id = '019a0290-0000-7000-8000-' + f'{7000 + len(starts):012d}'
    if clear_prior is not None:
        clear_completion(clear_prior, 'Original late reply after Clear', old=True)
    original = {'threadId': thread_id, 'turnId': turn_id}
    reply(request, {'turn': turn('inProgress')})
    notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
    if len(starts) == 1 and (scenario == 'clear:active'
                            or scenario.startswith('clear:ordered:')
                            or scenario in {'clear:stop-ack', 'clear:pending-ack'}):
        work = {
            'id': 'clear-prior-work', 'type': 'commandExecution', 'status': 'inProgress',
            'command': 'Original harmless held command, never executed', 'commandActions': [],
            'cwd': request['params']['sandboxPolicy']['writableRoots'][0],
        }
        original['work'] = work
        notify('item/started', {
            'threadId': original['threadId'], 'turnId': original['turnId'], 'item': work,
        })
        clear_prior = original
        clear_observation('active', original)
        return
    clear_observation('start', original)
    clear_completion(original, 'Original before Clear reply' if len(starts) == 1
                     else 'Original fresh after Clear reply')
    if len(starts) == 1:
        clear_prior = original


def clear_ordered_interrupt(request):
    """Finite ordinary protocol delay, not a producer clock or fault control."""
    original = clear_prior
    clear_observation('interrupt-received', {**original, 'request_id': request['id']})

    def acknowledge():
        clear_observation('interrupt-ack', {**original, 'request_id': request['id']})
        reply(request, {})

    def terminal():
        clear_completion(original, 'Original late reply after Clear', old=True)
        clear_observation('control-terminal', original)

    terminal_first = scenario in {'clear:ordered:terminal-first', 'clear:pending-ack'}
    if terminal_first:
        terminal()
    else:
        acknowledge()
    # Enough ordinary owner-event deliveries to observe the actual open gap;
    # every test verifies that the delayed event is still absent at its action.
    timer = Timer(0.6, acknowledge if terminal_first else terminal)
    timer.daemon = True
    timer.start()


def handoff_metadata(value):
    if isinstance(value, str) and 'EDI_RESULT_HANDOFF_V1\n' in value:
        return json.JSONDecoder().raw_decode(
            value.split('EDI_RESULT_HANDOFF_V1\n', 1)[1].lstrip()
        )[0]
    children = (
        value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
    )
    for child in children:
        found = handoff_metadata(child)
        if found is not None:
            return found
    return None


def result_start(request):  # noqa: PLR0912, PLR0914, PLR0915 -- finite original-input cases
    """Ordinary owned peer files; never a tool/model or host publication API."""
    metadata = handoff_metadata(request['params'])
    observed = {'metadata': metadata, 'cwd': cwd, 'prepared': False}
    if metadata is not None:
        root = Path(cwd).resolve()
        project = root / metadata['project']
        receipt = root / metadata['receipt']
        if not project.resolve().is_relative_to(root) or not receipt.resolve().is_relative_to(
            root
        ):
            raise ValueError('H2 SETUP: issued fixture paths remain inside the owned workspace')
        project.mkdir(parents=True, exist_ok=True)
        originals = sorted(Path(config['result_fixture']).rglob('*.edi'))
        entries = []
        for original in originals:
            relative = original.relative_to(config['result_fixture'])
            target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
            data = original.read_bytes()
            entries.append({
                'path': relative.as_posix(),
                'bytes': len(data),
                'sha256': hashlib.sha256(data).hexdigest(),
            })
        result = {
            'schema': 'edi.assistant.result/1',
            'intent': metadata['intent'],
            'project': 'project',
            'files': entries,
        }
        variant = scenario.split(':', 1)[1]
        if variant == 'hash':
            result['files'][0]['sha256'] = '0' * 64
        elif variant == 'foreign':
            result['intent'] = 'different-original-intent'
        elif variant == 'undeclared':
            shutil.copyfile(originals[0], project / 'undeclared.edi')
        elif variant == 'symlink':
            chosen = project / entries[0]['path']
            outside = trace.parent / 'outside-original.edi'
            shutil.copyfile(chosen, outside)
            chosen.unlink()
            chosen.symlink_to(outside)
        elif variant == 'directories':
            # Approved SelectedFileLimits::files32 also bounds represented entries.
            for index in range(33):
                (project / ('extra-original-directory-' + str(index))).mkdir()
        elif variant == 'data-fifo':
            chosen = project / entries[0]['path']
            chosen.unlink()
            os.mkfifo(chosen)
        elif variant == 'calculation-only':
            chosen = project / 'experiments/hrpt.edi'
            prefix = chosen.read_text().split('loop_\n_data.two_theta\n', 1)[0]
            chosen.write_text(
                prefix + '_data_range.two_theta_min 10\n'
                '_data_range.two_theta_max 10.2\n_data_range.two_theta_step 0.1\n'
            )
            entry = next(v for v in entries if v['path'] == 'experiments/hrpt.edi')
            data = chosen.read_bytes()
            entry.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        elif variant == 'depth':
            nested = None
            for _ in range(65):  # Public Limits::json_depth64; harmless finite input.
                nested = [nested]
            result['original_nested_metadata'] = nested
        text = json.dumps(result)
        if variant == 'duplicates':
            text = '{"intent":' + json.dumps(metadata['intent']) + ',' + text[1:]
        elif variant == 'receipt-bytes':
            # Legal JSON whitespace, beyond approved1MiB receipt budget.
            text = ' ' * 1048577 + text
        if variant == 'receipt-fifo':
            os.mkfifo(receipt)
        elif variant == 'receipt-link':
            outside = trace.parent / 'outside-original-receipt.json'
            outside.write_text(text)
            receipt.symlink_to(outside)
        else:
            receipt.write_text(text, encoding='utf-8')
        observed.update(prepared=True, receipt=str(receipt), project=str(project), files=entries)
    trace.with_suffix('.result.json').write_text(json.dumps(observed), encoding='utf-8')
    reply(request, {'turn': turn('inProgress')})
    notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
    if scenario in {'result:hold', 'result:late', 'result:steer'}:
        return
    if scenario == 'result:failed':
        notify('turn/completed', {'threadId': thread_id, 'turn': turn('failed')})
    else:
        complete()


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
    # Pinned092d3acd message_processor gates annotated params before dispatch.
    # This is protocol qualification, not a model/runtime execution simulator.
    if method in {'turn/start', 'turn/steer'} and not experimental_api:
        annotated = next(
            (
                key
                for key in ('additionalContext', 'responsesapiClientMetadata')
                if params.get(key) is not None
            ),
            None,
        )
        if annotated is not None:
            emit({
                'id': request['id'],
                'error': {
                    'code': -32600,
                    'message': method + '.' + annotated + ' requires experimentalApi capability',
                },
            })
            continue
    if method == 'initialize':
        experimental_api = (params.get('capabilities') or {}).get('experimentalApi') is True
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
                                'name': skill.parent.name,
                                'description': 'Original fixture ' + skill.parent.name,
                                'enabled': True,
                                'scope': 'repo',
                                'path': str(skill),
                            }
                            for skill in sorted((Path(cwd) / '.agents/skills').glob('*/SKILL.md'))
                            if skill.is_file() and not skill.is_symlink()
                        ],
                    }
                    for cwd in params.get('cwds', [])
                ]
            },
        )
    elif method == 'thread/start':
        cwd = params['cwd']
        if scenario.startswith('result:'):
            result_thread_number += 1
            thread_id = '019a0290-0000-7000-8000-' + f'{5000 + result_thread_number:012d}'
        elif scenario.startswith('clear:') or scenario == 'fileauth':
            count = sum(json.loads(line).get('method') == 'thread/start'
                        for line in trace.read_text(encoding='utf-8').splitlines())
            thread_id = '019a0290-0000-7000-8000-' + f'{6000 + count:012d}'
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
        if scenario.startswith('rpc83:unknown:'):
            variant = scenario.rsplit(':', 1)[1]
            if variant == 'eof':
                sys.exit(0)
            message = 'ORIGINAL_PRIVATE_PAYLOAD must never be rendered'
            if variant == 'spoof':
                message = (
                    'turn/start.additionalContext requires experimentalApi capability ' + message
                )
            emit({
                'id': request['id'],
                'error': {
                    'code': -32600,
                    'message': message,
                    'data': {'secret': 'ORIGINAL_PRIVATE_ERROR_DATA'},
                },
            })
            continue
        turn_number += 1
        if scenario == 'fileauth':
            turn_id = '019a0290-0000-7000-8000-' + f'{8000 + turn_number:012d}'
        if scenario.startswith('clear:'):
            clear_start(request)
            continue
        if scenario.startswith('result:'):
            turn_id = '019a0290-0000-7000-8000-' + f'{turn_number + 1:012d}'
            result_start(request)
            continue
        if scenario.startswith('gn:'):
            # New independent turns have distinct authoritative original IDs.
            turn_id = '019a0290-0000-7000-8000-' + f'{turn_number + 1:012d}'
            gn_start(request)
            continue
        if scenario == 'start-pending':
            continue  # Genuine received request; no turn ID is admitted yet.
        reply(request, {'turn': turn('inProgress')})
        notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
        if scenario in {'hold', 'steer-no-ack'} or scenario.startswith('rpc83:'):
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
        if scenario == 'result:steer':
            reply(request, {'turnId': turn_id})
            complete()
            continue
        if scenario.startswith('rpc83:refuse:'):
            kind = scenario.rsplit(':', 1)[1]
            if kind == 'no-active':
                # The original really finishes before this delayed request is refused.
                complete()
                message = 'no active turn to steer'
            else:
                message = 'cannot steer a ' + kind + ' turn'
            emit({'id': request['id'], 'error': {'code': -32600, 'message': message}})
            continue
        if scenario.startswith('gn:'):
            gn_steer(request)
            continue
        if scenario == 'steer-no-ack':
            sys.exit(0)  # Actual process EOF after receiving, before acknowledging the steer.
        reply(request, {'turnId': turn_id})
    elif method == 'turn/interrupt':
        if scenario.startswith('clear:ordered:') or scenario in {
            'clear:stop-ack', 'clear:pending-ack'
        }:
            clear_ordered_interrupt(request)
            continue
        if scenario.startswith('clear:') and clear_prior is not None:
            reply(request, {})
            clear_completion(clear_prior, 'Original late reply after Clear', old=True)
            continue
        if scenario == 'result:late':
            reply(request, {})
            complete()
            continue
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
