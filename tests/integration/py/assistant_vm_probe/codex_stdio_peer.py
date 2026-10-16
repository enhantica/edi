"""Finite task-owned stdio dependency, not an official runtime/provider witness.

Original IDs/text and complete structures follow public codex0.162.1 schemas.
The peer never executes commands, reads accounts or calls a service.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from threading import Timer

config = json.loads(Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).read_text(encoding='utf-8'))
trace = Path(config['trace'])
Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).with_suffix('.peer-loaded.json').write_text(
    json.dumps({
        'sha256': hashlib.sha256(
            Path(os.environ['EDI_TEST_CODEX_PEER_INPUT']).read_bytes()
        ).hexdigest(),
        'native_turn_calls': config.get('native_turn_calls'),
    }), encoding='utf-8'
)
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
    item = {
        'type': 'agentMessage',
        'id': (
            turn_id + '-message'
            if scenario == 'fileauth' or config.get('native_turn_calls')
            else 'original-message'
        ),
        'text': f'Original fileauth reply {turn_number}'
        if scenario == 'fileauth'
        else 'Original offline reply',
    }
    # Opt-in fixed original acceptance text, published by the genuine retained-turn path.
    # Existing scenarios and account/skills/native protocols are unchanged.
    if config.get('report_page_reply') is True:
        item['text'] = (
            '[Open Report page](edi:report)\n\n'
            '[Unknown protected report](not-a-report:original)'
        )
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
    notify(
        'turn/completed',
        {
            'threadId': original['threadId'],
            'turn': {'id': original['turnId'], 'items': [], 'status': 'completed'},
        },
    )


def clear_start(request):
    global clear_prior, turn_id  # noqa: PLW0603 -- ordinary peer protocol state
    # Real request trace survives a process replacement; never reuse a thread
    # identity or manufacture an old-channel emission in a replacement process.
    starts = [
        json.loads(line)
        for line in trace.read_text(encoding='utf-8').splitlines()
        if json.loads(line).get('method') == 'turn/start'
    ]
    turn_id = '019a0290-0000-7000-8000-' + f'{7000 + len(starts):012d}'
    if clear_prior is not None:
        clear_completion(clear_prior, 'Original late reply after Clear', old=True)
    original = {'threadId': thread_id, 'turnId': turn_id}
    reply(request, {'turn': turn('inProgress')})
    notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
    if len(starts) == 1 and (
        scenario == 'clear:active'
        or scenario.startswith('clear:ordered:')
        or scenario in {'clear:stop-ack', 'clear:pending-ack'}
    ):
        work = {
            'id': 'clear-prior-work',
            'type': 'commandExecution',
            'status': 'inProgress',
            'command': 'Original harmless held command, never executed',
            'commandActions': [],
            'cwd': request['params']['sandboxPolicy']['writableRoots'][0],
        }
        original['work'] = work
        notify(
            'item/started',
            {
                'threadId': original['threadId'],
                'turnId': original['turnId'],
                'item': work,
            },
        )
        clear_prior = original
        clear_observation('active', original)
        return
    clear_observation('start', original)
    clear_completion(
        original,
        'Original before Clear reply' if len(starts) == 1 else 'Original fresh after Clear reply',
    )
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
    if scenario == 'result:notice-storage':

        def completed_notice_control():
            clear_observation(
                'notice-terminal-emission', {'threadId': thread_id, 'turnId': turn_id}
            )
            complete()

        timer = Timer(0.6, completed_notice_control)
        timer.daemon = True
        timer.start()
        return
    if scenario in {'result:hold', 'result:late', 'result:steer'}:
        return
    if scenario == 'result:failed':
        notify('turn/completed', {'threadId': thread_id, 'turn': turn('failed')})
    else:
        complete()


def original_pdf():
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Contents 4 0 R >>',
        b'<< /Length 0 >>\nstream\n\nendstream',
    ]
    output = bytearray(b'%PDF-1.4\n')
    offsets = []
    for index, value in enumerate(objects, 1):
        offsets.append(len(output))
        output += str(index).encode() + b' 0 obj\n' + value + b'\nendobj\n'
    start = len(output)
    output += b'xref\n0 5\n0000000000 65535 f \n'
    output += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets)
    output += b'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n'
    return bytes(output) + str(start).encode() + b'\n%%EOF\n'


def write_original_sized(path, size, prefix=b'/*', suffix=b'*/'):
    path.parent.mkdir(parents=True, exist_ok=True)
    remaining = size - len(prefix) - len(suffix)
    if remaining < 0:
        raise ValueError('independent fixture bound cannot hold its original format')
    with path.open('wb') as output:
        output.write(prefix)
        while remaining:
            part = min(remaining, 65536)
            output.write(b'X' * part)
            remaining -= part
        output.write(suffix)


def report_start(request):  # noqa: PLR0912, PLR0914, PLR0915 -- finite owned report fixtures
    """Only original owned artifacts, under the actually admitted thread workspace."""
    root = Path(cwd)
    variant = scenario.split(':', 1)[1]
    folder = root / ('reports-' + str(turn_number))
    folder.mkdir()
    html = folder / 'original.html'
    css = folder / 'style.css'
    image = folder / 'pixel.png'
    pdf = folder / 'original.pdf'
    css.write_text('/* Original harmless report style */ body { color: #123; }')
    image.write_bytes(
        base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5WQAAAAASUVORK5CYII='
        )
    )
    html.write_text(
        '<!doctype html><title>Original report</title>'
        '<link rel="stylesheet" href="style.css"><h1>Original local report</h1>'
        '<img src="pixel.png"><table><tr><td>Original cell</td></tr></table>'
    )
    pdf.write_bytes(original_pdf())
    limits = config.get('report_limits', {})
    if variant == 'file-bytes':
        write_original_sized(html, limits['file_bytes'] + 1, b'<!doctype html><!--', b'-->')
    elif variant in {'asset-count', 'collection-bytes'}:
        count = (
            limits['files']
            if variant == 'asset-count'
            else (limits['collection_bytes'] // limits['file_bytes'])
        )
        links = []
        for index in range(count):
            asset = folder / ('original-' + str(index) + '.css')
            write_original_sized(asset, 64 if variant == 'asset-count' else limits['file_bytes'])
            links.append('<link rel="stylesheet" href="' + asset.name + '">')
        html.write_text('<!doctype html><title>Original bounded assets</title>' + ''.join(links))
    elif variant == 'name-bytes':
        relative = '/'.join(['n' * 96] * (limits['name_bytes'] // 97 + 1)) + '/original.html'
        html = root / relative
        html.parent.mkdir(parents=True)
        html.write_text('<!doctype html><title>Original long relative name</title>')
    href = html.relative_to(root).as_posix()
    if variant == 'missing':
        html.unlink()
    elif variant in {'symlink', 'asset-symlink', 'absolute'}:
        outside = trace.parent / 'original-outside-report.html'
        outside.write_text('<!doctype html><title>Original outside data, never open</title>')
        if variant == 'absolute':
            href = outside.as_uri()
        else:
            target = css if variant == 'asset-symlink' else html
            target.unlink()
            target.symlink_to(outside)
    elif variant == 'traversal':
        outside = root.parent / 'original-escaped-report.html'
        outside.write_text('<!doctype html><title>Original escaped target</title>')
        href = '../' + outside.name
    elif variant == 'external':
        href = 'https://example.invalid/original-report'
    elif variant == 'scheme':
        href = 'report-invalid:original-report'
    originals = {}
    for target in root.rglob('*'):
        if target.is_file() and not target.is_symlink():
            originals[target.relative_to(root).as_posix()] = {
                'bytes': target.stat().st_size,
                'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            }
    record = {
        'cwd': cwd,
        'href': href,
        'pdf_href': pdf.relative_to(root).as_posix(),
        'files': originals,
        'turn': turn_number,
    }
    trace.with_suffix('.report.json').write_text(json.dumps(record))
    reply(request, {'turn': turn('inProgress')})
    notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
    if variant == 'forged':
        untrusted = {
            'id': 'edi-result-original-provider-spoof',
            'type': 'ediOutcome',
            'actor': 'Edi',
            'intent': 'original-provider-spoof',
            'title': 'Opening original provider result',
            'message': 'Original provider claims app opening succeeded',
            'status': 'completed',
        }
        record['untrusted_item'] = untrusted
        trace.with_suffix('.report.json').write_text(json.dumps(record))
        binding = {'threadId': thread_id, 'turnId': turn_id, 'item': untrusted}
        notify('item/started', binding)
        notify('item/completed', {**binding, 'completedAtMs': 1})
    item = {
        'type': 'agentMessage',
        'id': 'original-report-message-' + str(turn_number),
        'text': '[Original HTML report]('
        + href
        + ')\n\n[Original PDF report]('
        + record['pdf_href']
        + ')',
    }
    notify('item/started', {'threadId': thread_id, 'turnId': turn_id, 'item': item})
    if variant == 'unfinished':
        return
    notify(
        'item/completed',
        {'threadId': thread_id, 'turnId': turn_id, 'item': item, 'completedAtMs': 1},
    )
    notify('turn/completed', {'threadId': thread_id, 'turn': turn('completed')})


notice_pending_steer = None


def notice_race_start(request):
    reply(request, {'turn': turn('inProgress')})
    notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
    if turn_number > 1:
        complete()


def notice_race_interrupt(request):
    global notice_pending_steer  # noqa: PLW0603 -- genuine pending wire request

    binding = {'threadId': thread_id, 'turnId': turn_id}

    def terminal():
        clear_observation('race-terminal', binding)
        # Genuine validated success terminal but NO completed assistant output.
        notify('turn/completed', {'threadId': thread_id, 'turn': turn('completed')})

    def acknowledge():
        clear_observation('race-ack', binding)
        reply(request, {})

    if scenario.endswith('ack-first'):
        acknowledge()
        terminal()
    else:
        terminal()
        acknowledge()
    clear_observation('race-refusal', binding)
    emit({
        'id': notice_pending_steer['id'],
        'error': {'code': -32600, 'message': 'no active turn to steer'},
    })
    notice_pending_steer = None


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


# Actual native dynamic-tool bridge only; this peer never performs model edits or fits.
native_pending = {}
native_index = 0
native_rpc_sequence = 0
native_start_pending = None
native_steers = []
native_disclosed_parameters = []
native_disclosed_sources = []


def native_original_addresses(value):
    # Only an explicitly predeclared address selector is resolved from an actual
    # successful list_parameters reply. No value/uncertainty/scientific oracle
    # is inferred, and unknown/ambiguous references never fabricate a path.
    if isinstance(value, dict) and set(value) == {'$original_parameter_suffix'}:
        matches = [
            row['path'] for row in native_disclosed_parameters
            if row['path'].endswith(value['$original_parameter_suffix'])
            and row['dependence'] == 'independent'
        ]
        assert len(matches) == 1, 'CREATE SETUP: original current parameter address is unique'
        return matches[0]
    if isinstance(value, dict) and set(value) == {'$original_selected_name'}:
        matches = [row['id'] for row in native_disclosed_sources
                   if row['name'] == value['$original_selected_name'] and row['text_readable']]
        assert len(matches) == 1, 'IMPORT267 SETUP: actual original disclosed selected source ID is unique'
        return matches[0]
    if isinstance(value, dict):
        return {key: native_original_addresses(item) for key, item in value.items()}
    if isinstance(value, list):
        return [native_original_addresses(item) for item in value]
    return value


def native_emit_next():
    global native_index, native_rpc_sequence  # noqa: PLW0603 -- owned wire request lifecycle
    calls = config['native_calls']
    if native_index == len(calls):
        if not config.get('native_hold_after_calls'):
            complete()
        return
    spec = calls[native_index]
    if config.get('native_turn_calls'):
        spec = {**spec, 'arguments': native_original_addresses(spec['arguments'])}
    native_index += 1
    call_id = spec.get('call_id', 'original-native-call-' + str(native_index))
    native_rpc_sequence += 1
    rpc_id = 'original-native-envelope-' + str(native_rpc_sequence)
    item = {
        'type': 'dynamicToolCall',
        'id': call_id,
        'namespace': spec.get('item_namespace'),
        'tool': spec['tool'],
        'arguments': spec['arguments'],
        'status': 'inProgress',
        'contentItems': None,
        'success': None,
        'durationMs': None,
    }
    binding = {'threadId': thread_id, 'turnId': turn_id, 'item': item}
    params = {
        'threadId': spec.get('thread_id', thread_id),
        'turnId': spec.get('turn_id', turn_id),
        'callId': call_id,
        'namespace': spec.get('rpc_namespace'),
        'tool': spec['tool'],
        'arguments': spec['arguments'],
    }
    native_pending[rpc_id] = {'id': rpc_id, 'params': params, 'item': item, 'binding': binding}
    notify('item/started', binding)
    with trace.with_suffix('.native-emitted.jsonl').open('a') as output:
        output.write(json.dumps(native_pending[rpc_id]) + '\n')
    clear_observation('native-call-emitted', {'rpc': rpc_id, 'call': call_id})
    emit({'id': rpc_id, 'method': 'item/tool/call', 'params': params})
    if config.get('native_foreign_resolve'):
        clear_observation(
            'native-foreign-resolve', {'rpc': rpc_id, 'still_pending': rpc_id in native_pending}
        )
        notify(
            'serverRequest/resolved',
            {'threadId': '019a0290-0000-7000-8000-000000009999', 'requestId': rpc_id},
        )


def native_start(request):
    global native_start_pending, native_index, turn_id  # noqa: PLW0603 -- original delayed RPC envelope
    if config.get('native_turn_calls'):
        groups = config['native_turn_calls']
        assert 0 < turn_number <= len(groups), 'CREATE SETUP: only original declared real turns'
        assert not native_pending, 'CREATE SETUP: preceding original RPC group settled'
        config['native_calls'] = groups[turn_number - 1]
        turn_id = '019a0290-0000-7000-8000-' + f'{turn_number + 1:012d}'
        native_index = 0
        clear_observation('native-original-turn-script', {
            'turn': turn_number,
            'calls': [call['call_id'] for call in config['native_calls']],
        })
    if config.get('native_ack_order') == 'start-late':
        native_start_pending = request
        notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
        return
    reply(request, {'turn': turn('inProgress')})
    notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
    if config.get('native_capacity') == 'retained-live-reasoning':
        source = Path(config['native_capacity_source']).read_text(encoding='utf-8')
        sources = [
            {
                'type': 'reasoning',
                'id': 'original-live-source-' + str(index),
                'summary': [],
                'content': [source],
            }
            for index in range(config['native_capacity_count'])
        ]

        def encoded(value):
            return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()

        wires = [
            {
                'method': 'item/started',
                'params': {'threadId': thread_id, 'turnId': turn_id, 'item': item},
            }
            for item in sources
        ]
        # Before emission, so a genuine early bounded refusal cannot erase the
        # independently authored size/shape premises by closing the peer channel.
        clear_observation(
            'native-shared-capacity',
            {
                'count': len(sources),
                'source_bytes': sum(len(encoded(item)) for item in sources),
                'max_source_bytes': max(len(encoded(item)) for item in sources),
                'max_wire_bytes': max(len(encoded(wire)) for wire in wires),
                'wire_bytes': sum(len(encoded(wire)) + 1 for wire in wires),
                'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
                'presentation_rows': 0,
                'finalized_items': 0,
                'phase': 'one-active-turn-live-known-originals-before-native-request',
            },
        )
        for wire in wires:
            emit(wire)
    if config.get('native_exit_while_running'):

        def original_eof():
            clear_observation('native-original-eof', {'pending': list(native_pending)})
            os._exit(0)

        timer = Timer(0.2, original_eof)
        timer.daemon = True
        timer.start()
    if config.get('native_delay'):
        timer = Timer(0.6, native_emit_next)
        timer.daemon = True
        timer.start()
    else:
        native_emit_next()
        if config.get('native_parallel'):
            native_emit_next()


def native_steer(request):
    global native_start_pending, native_index  # noqa: PLW0603 -- genuine deferred ACK interleaving
    native_steers.append(request)
    clear_observation('native-steer-received', {'id': request['id'], 'params': request['params']})
    count = config.get('native_steer_count', 2)
    if len(native_steers) < count:
        return
    for original in reversed(native_steers):
        reply(original, {'turnId': turn_id})
        clear_observation('native-steer-ack', {'id': original['id']})
    if native_start_pending is not None:
        reply(native_start_pending, {'turn': turn('inProgress')})
        clear_observation('native-old-start-ack', {'id': native_start_pending['id']})
        native_start_pending = None
    config['native_calls'] = config['native_after_steer']
    native_index = 0
    native_emit_next()


def native_reply(request):
    if request.get('id') not in native_pending:
        with trace.with_suffix('.native-wrong-envelope.jsonl').open('a') as output:
            output.write(json.dumps(request) + '\n')
        return
    result = request.get('result')
    with trace.with_suffix('.native-replies.jsonl').open('a') as output:
        output.write(
            json.dumps({'original': native_pending[request['id']], 'response': request}) + '\n'
        )
    original = native_pending.pop(request['id'])
    if (config.get('native_turn_calls') and result and result.get('success')
            and original['params']['tool'] == 'list_parameters'):
        disclosed = json.loads(result['contentItems'][0]['text'])
        native_disclosed_parameters[:] = disclosed['parameters']
    if (config.get('native_import267') and result and result.get('success')
            and original['params']['tool'] == 'inspect_project'):
        disclosed = json.loads(result['contentItems'][0]['text'])
        native_disclosed_sources[:] = disclosed['selected_files']['files']
        clear_observation('import267-original-source-addresses', {
            'request_id': request['id'],
            'sources': [{'name': row['name'], 'id': row['id'], 'text_readable': row['text_readable']}
                        for row in native_disclosed_sources],
        })
    item = {
        **original['item'],
        'status': 'completed' if result and result.get('success') else 'failed',
        'contentItems': result.get('contentItems') if result else [],
        'success': bool(result and result.get('success')),
        'durationMs': 1,
    }
    if config.get('native_conflicting_final'):
        item = {
            **item,
            'tool': 'set_free',
            'namespace': 'original-provider-foreign',
            'arguments': {'purpose': 'Provider cannot rewrite admitted original'},
            'success': False,
            'contentItems': [
                {'type': 'inputText', 'text': 'Original provider contradicts actual host outcome'}
            ],
        }
    if config.get('native_conflicting_final') == 'snapshot':
        notify(
            'turn/completed',
            {'threadId': thread_id, 'turn': {**turn('completed'), 'items': [item]}},
        )
    else:
        notify('item/completed', {**original['binding'], 'item': item})
        if (result and result.get('success') and original['params']['callId']
                in config.get('relation246_wait_for_usage', [])):
            assert not native_pending, 'REL OWNER SETUP: only original completed edit waits'
            config['_relation246_waiting_next'] = original['params']['callId']
            clear_observation('relation246-waiting-after-edit', {
                'call_id': original['params']['callId'], 'request_id': request['id'],
            })
        elif not config.get('native_parallel'):
            native_emit_next()
        elif not native_pending:
            complete()


# Original protocol fixtures follow pinned092d3acd RateLimitSnapshot/Response.
# Values are authored inputs, never normalized output from the subject.
usage_requests = []
usage_held_steers = []


def usage_snapshot(percent=17, *, empty=False):
    primary = {'usedPercent': percent, 'windowDurationMins': 300, 'resetsAt': 1800000000}
    value = {
        'limitId': 'original-codex',
        'limitName': 'Original owned limit',
        'normalModelSlug': None,
        'primary': primary,
        'secondary': {'usedPercent': 83, 'windowDurationMins': 10080, 'resetsAt': 1800000900},
        'credits': {'hasCredits': True, 'unlimited': False, 'balance': '12.50'},
        'individualLimit': None,
        'spendControlReached': None,
        'planType': 'plus',
        'rateLimitReachedType': None,
    }
    if config.get('usage_many'):
        value['limitName'] = 'Original usage long ordinary label ' * 4
    buckets = {} if empty else {'original-codex': value}
    if config.get('usage_many') and not empty:
        buckets = {
            f'original-{index}': {
                **value,
                'limitId': f'original-{index}',
                'limitName': f'Original bucket {index} with a readable complete label',
            }
            for index in range(8)
        }
    return {
        'rateLimits': value,
        'rateLimitsByLimitId': buckets,
        'accountId': config.get('usage_account', 'original-account'),
        'ordinaryUsageAllowed': True,
        'rateLimitResetCredits': None,
        'rateLimitUpsell': None,
    }


def relation246_resolve_at_original_read():
    # Optional response is an existing public wire door, not a new app hook.
    # Only the real original pending native RPC may be resolved; no timer or
    # fabricated helper/worker state supplies the staging premise.
    call_id = config.get('relation246_resolve_on_usage')
    if not call_id:
        return
    matches = [(rpc, original) for rpc, original in native_pending.items()
               if original['params']['callId'] == call_id]
    if not matches:
        return  # The actor/wrapper must report the original interval unreached.
    assert len(matches) == 1, 'REL RESOLVE SETUP: original pending RPC identity is unique'
    rpc, original = matches[0]
    native_pending.pop(rpc)
    clear_observation('relation246-original-resolved', {
        'request_id': rpc, 'call_id': call_id,
        'thread_id': original['params']['threadId'],
        'arguments': original['params']['arguments'],
    })
    notify('serverRequest/resolved', {
        'threadId': original['params']['threadId'], 'requestId': rpc,
    })


def usage_read(request):
    relation246_resolve_at_original_read()
    waiting = config.pop('_relation246_waiting_next', None)
    if waiting is not None:
        assert waiting in config['relation246_wait_for_usage'], (
            'REL OWNER SETUP: only exact original edit IDs admit this public-event release'
        )
        assert not native_pending, 'REL OWNER SETUP: previous original edit really replied'
        clear_observation('relation246-release-after-observed-settlement', {
            'call_id': waiting, 'read_id': request['id'],
            'observed_at_ms': time.time_ns() // 1000000,
        })
        native_emit_next()
    usage_requests.append(request)
    number = len(usage_requests)
    mode = config.get('usage_mode', 'normal')
    clear_observation('usage-read', {'number': number, 'id': request['id']})
    if mode in {'control-capacity', 'reverse-capacity'}:
        return  # Genuine outstanding OPTIONAL response, not a producer clock/fault hook.
    if number > 1 and mode == 'failure':
        emit({
            'id': request['id'],
            'error': {'code': -32603, 'message': 'Original optional usage unavailable'},
        })
        clear_observation('usage-error-reply', {'number': number})
        return
    if number == 2 and mode == 'freshness':
        changed = usage_snapshot(29)['rateLimits']
        notify('account/rateLimits/updated', {'rateLimits': changed})
        clear_observation('usage-sparse-update', {'number': number})

        def older_reply():
            reply(request, usage_snapshot(17))
            clear_observation('usage-older-reply', {'number': number})

        timer = Timer(0.3, older_reply)
        timer.daemon = True
        timer.start()
        return
    percent = (
        43
        if (mode == 'freshness' and number >= 3) or (mode == 'popup' and number > 1)
        else 0
        if mode == 'zero-empty'
        else 137
        if mode == 'over-hundred'
        else 17
    )
    result = usage_snapshot(percent, empty=mode == 'zero-empty' and number == 2)

    def finish():
        clear_observation(
            'usage-result-reply',
            {'number': number, 'percent': percent, 'empty': not result['rateLimitsByLimitId']},
        )
        reply(request, result)

    # Bootstrap must deliver the automatic result after the required catalogue/skills work.
    # The peer delays a wire reply only; no subject event queue or priority is altered.
    timer = Timer(0.3, finish)
    timer.daemon = True
    timer.start()


def usage_start(request):
    reply(request, {'turn': turn('inProgress')})
    notify('turn/started', {'threadId': thread_id, 'turn': turn('inProgress')})
    if config.get('usage_mode') == 'eof':
        clear_observation('usage-process-eof', {})
        os._exit(0)
    if config.get('usage_mode') == 'reverse-capacity':
        ask_original()
    elif config.get('usage_mode') not in {'control-capacity', 'eof'}:
        # Genuine later public row supplies an ordered-channel delivery barrier.
        complete()


def usage_interrupt(request):
    for original in usage_held_steers:
        reply(original, {'turnId': turn_id})
    usage_held_steers.clear()
    reply(request, {})
    notify('turn/completed', {'threadId': thread_id, 'turn': turn('interrupted')})


# Opt-in offline protocol cases only; no accounts, browser or service is accessed.
signin206_state = {'completed': False}
SIGNIN206_CANARY = 'SIGNIN206_PRIVATE_REPLY_CANARY'
SIGNIN206_AUTH_URL = 'https://auth.openai.com/oauth/authorize?state=SIGNIN206_URL_CANARY'
SIGNIN206_LOGIN_ID = 'original-offline-chatgpt-login-206'


def signin206_record(value):
    with trace.with_suffix('.signin206-emissions.jsonl').open('a', encoding='utf-8') as output:
        output.write(json.dumps(value, ensure_ascii=False) + '\n')


def signin206_reply(request, result=None, *, error=None):
    envelope = {'id': request['id'], 'error' if error is not None else 'result':
                error if error is not None else result}
    signin206_record({'method': request['method'], 'envelope': envelope})
    emit(envelope)


def signin206_dispatch(request):  # noqa: PLR0911, PLR0912, PLR0915 -- finite public bootstrap shapes
    variant = config['signin206_variant']
    method = request['method']
    if method == 'account/read' and variant.startswith('account:'):
        kind = variant.removeprefix('account:')
        if signin206_state['completed']:
            account = {'type': 'chatgpt', 'email': 'original@example.invalid', 'planType': 'plus'}
        elif kind == 'api-key':
            account = {'type': 'apiKey'}
        elif kind == 'bedrock':
            account = {'type': 'amazonBedrock', 'usesCodexManagedCredentials': False}
        elif kind == 'none':
            account = None
        elif kind == 'unknown':
            account = {'type': SIGNIN206_CANARY}
        else:
            account = {'type': 'chatgpt', 'email': {'private': SIGNIN206_CANARY},
                       'planType': 'plus'}
        signin206_reply(request, {'account': account, 'requiresOpenaiAuth': account is None})
        return True
    if method == 'account/login/start' and variant.startswith('account:'):
        # A wrong method/variant is observed as a real RPC refusal, never faked success.
        if request.get('params', {}).get('type') != 'chatgpt':
            signin206_reply(request, error={'code': -32600, 'message': SIGNIN206_CANARY})
            return True
        signin206_reply(request, {'type': 'chatgpt', 'loginId': SIGNIN206_LOGIN_ID,
                                 'authUrl': SIGNIN206_AUTH_URL})
        signin206_state['completed'] = True
        completed = {'loginId': SIGNIN206_LOGIN_ID, 'success': True, 'error': None}
        signin206_record({'notification': 'account/login/completed', 'params': completed})
        notify('account/login/completed', completed)
        return True
    if method != 'skills/list':
        return False
    if variant == 'stage:shape':
        signin206_reply(request, SIGNIN206_CANARY)
        return True
    if variant == 'stage:rpc-refused':
        signin206_reply(request, error={'code': -32603, 'message': SIGNIN206_CANARY,
                                       'data': {'private': SIGNIN206_CANARY}})
        return True
    if not variant.startswith('skills:'):
        return False
    kind = variant.removeprefix('skills:')
    entries = []
    for cwd in request.get('params', {}).get('cwds', []):
        skills = [
            {'name': skill.parent.name, 'description': 'Original fixture ' + skill.parent.name,
             'enabled': True, 'scope': 'repo', 'path': str(skill)}
            for skill in sorted((Path(cwd) / '.agents/skills').glob('*/SKILL.md'))
            if skill.is_file() and not skill.is_symlink()
        ]
        # All source paths come from genuine admitted workspace files, not invented IDs.
        assert skills, 'SIGNIN206 SETUP: prepared real shipped skills exist before variant'
        required_path = skills[0]['path']
        errors = []
        if kind == 'unrelated':
            unrelated = Path(config['signin206_unrelated_path'])
            assert unrelated.is_file() and not unrelated.is_relative_to(Path(cwd)), (
                'SIGNIN206 SETUP: global discovery diagnostic is outside the staged workspace'
            )
            errors = [{'path': str(unrelated), 'message': SIGNIN206_CANARY}]
        elif kind == 'required-error':
            errors = [{'path': required_path, 'message': SIGNIN206_CANARY}]
        elif kind == 'malformed-error':
            errors = [{'path': required_path, 'message': {'private': SIGNIN206_CANARY}}]
        elif kind == 'missing':
            skills = skills[1:]
        elif kind == 'disabled':
            skills[0]['enabled'] = False
        elif kind == 'duplicate':
            skills.append(dict(skills[0]))
        entries.append({'cwd': cwd, 'skills': skills, 'errors': errors})
    signin206_reply(request, {'data': entries})
    return True


# Pinned092d3acd permissions/manager compatibility policy: cwd is implicit;
# writableRoots are additional. This changes opt-in RESPONSE projection only.
def roots207_response(request, value):
    cwd = request['params']['cwd']
    requested = request['params'].get('config', {}).get('sandbox_workspace_write', {}).get(
        'writable_roots', [cwd]
    )
    additional = [root for root in requested if root != cwd]
    variant = config['roots207_variant']
    roots = list(additional)
    if variant == 'extra':
        roots.append(config['roots207_ungranted'])
    elif variant == 'duplicate-cwd':
        roots.extend([cwd, cwd])
    elif variant == 'missing-chosen' and additional:
        roots = []
    elif variant == 'duplicate-chosen' and additional:
        roots.append(additional[0])
    value['sandbox']['writableRoots'] = roots
    with trace.with_suffix('.roots207-responses.jsonl').open('a', encoding='utf-8') as output:
        output.write(json.dumps({'request_id': request['id'], 'request_cwd': cwd,
            'requested_roots': requested, 'response_cwd': value['cwd'],
            'returned_roots': roots, 'sandbox': value['sandbox']}) + '\n')


for line in sys.stdin:
    request = json.loads(line)
    with trace.open('a', encoding='utf-8') as output:
        output.write(json.dumps(request, ensure_ascii=False) + '\n')
    method = request.get('method')
    params = request.get('params') or {}
    if method is None:
        if scenario.startswith('native:'):
            native_reply(request)
        elif scenario.startswith('usage:') and request.get('id') == 'original-question-rpc':
            clear_observation('usage-question-result', {'response': request})
            # Same genuine item finalization as gn:x:question-answer. A settled
            # reverse RPC alone does not complete its retained original item.
            publish_item({
                'type': 'dynamicToolCall',
                'id': 'original-question-item',
                'tool': 'request_user_input',
                'arguments': {},
                'status': 'completed',
            }, completed=True)
            complete()
        elif request.get('id') == server_id:
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
    if config.get('signin206_variant') and signin206_dispatch(request):
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
    elif method == 'account/rateLimits/read':
        usage_read(request)
    elif method == 'account/read':
        reply(
            request,
            {
                'account': {
                    'type': 'chatgpt',
                    'email': config.get('account_email', 'original@example.invalid'),
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
        elif scenario.startswith(('clear:', 'report:', 'notice-race:')) or scenario == 'fileauth':
            count = sum(
                json.loads(line).get('method') == 'thread/start'
                for line in trace.read_text(encoding='utf-8').splitlines()
            )
            thread_id = '019a0290-0000-7000-8000-' + f'{6000 + count:012d}'
        value = {
            'approvalPolicy': 'on-request',
            'approvalsReviewer': 'user',
            'cwd': cwd,
            'model': 'gpt-6.1-sol',
            'modelProvider': 'openai',
            'sandbox': {
                'type': 'workspaceWrite',
                'writableRoots': params.get('config', {}).get('sandbox_workspace_write', {}).get(
                    'writable_roots', [cwd]
                ),
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
                'ephemeral': params.get('ephemeral') is True,
                'modelProvider': 'openai',
                'preview': '',
                'projectId': None,
                'sessionId': 'original-session',
                'source': 'appServer',
                'status': {'type': 'idle'},
                'turns': [],
            },
        }
        if config.get('roots207_variant'):
            roots207_response(request, value)
        if scenario == 'different-cwd':
            value['cwd'] = str(trace.parent / 'unadmitted-workspace')
        elif scenario == 'network-enabled':
            value['sandbox']['networkAccess'] = True
        elif scenario == 'different-reviewer':
            value['approvalsReviewer'] = 'auto_review'
        elif scenario == 'different-provider':
            value['modelProvider'] = 'other-original-provider'
        if config.get('ephemeral257_variant'):
            variant = config['ephemeral257_variant']
            if variant == 'missing':
                value['thread'].pop('ephemeral')
            elif variant == 'false':
                value['thread']['ephemeral'] = False
            elif variant == 'malformed':
                value['thread']['ephemeral'] = 'true'
            with trace.with_suffix('.ephemeral257-responses.jsonl').open(
                'a', encoding='utf-8'
            ) as output:
                output.write(json.dumps({
                    'request': request,
                    'response': {'id': request['id'], 'result': value},
                }) + '\n')
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
        if scenario.startswith('usage:'):
            usage_start(request)
            continue
        if scenario.startswith('native:'):
            native_start(request)
            continue
        if scenario == 'fileauth':
            turn_id = '019a0290-0000-7000-8000-' + f'{8000 + turn_number:012d}'
        if scenario.startswith(('report:', 'notice-race:')):
            turn_id = '019a0290-0000-7000-8000-' + f'{9000 + turn_number:012d}'
            if scenario.startswith('report:'):
                report_start(request)
            else:
                notice_race_start(request)
            continue
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
        if scenario.startswith('usage:'):
            usage_held_steers.append(request)
            continue
        if scenario.startswith('native:'):
            native_steer(request)
            continue
        if scenario.startswith('notice-race:'):
            notice_pending_steer = request
            clear_observation('race-steer-received', {'threadId': thread_id, 'turnId': turn_id})
            continue
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
        if scenario.startswith('usage:'):
            usage_interrupt(request)
            continue
        if scenario.startswith('notice-race:'):
            notice_race_interrupt(request)
            continue
        if scenario.startswith('clear:ordered:') or scenario in {
            'clear:stop-ack',
            'clear:pending-ack',
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
