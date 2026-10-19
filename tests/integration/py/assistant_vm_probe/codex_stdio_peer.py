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

from approved_context import context_inputs

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



# Explicit closed native-array fixture only. Original defaults and GUI416 remain independent.
def array451_policy_fields(params):
    marker = config.get('native_array451_policy')
    assert type(marker) is dict and set(marker) == {'family', 'case'}, 'ARRAY451 SETUP: closed explicit native-array opt-in identity required'
    assert type(marker['family']) is str and marker['family'] in {'450', '451'} and type(marker['case']) is str, 'ARRAY451 SETUP: only independently predeclared native-array families'
    assert scenario == 'native:script' and 'gui415_policy' not in config and 'readonly409' not in config and 'input413' not in config, 'ARRAY451 SETUP: conflicting original opt-ins refuse, no policy echo/fallback'
    def call(identifier, purpose, values, tool='set_parameters'):
        return {'tool': tool, 'call_id': identifier, 'arguments': {'purpose': purpose, 'flags' if tool == 'set_free' else 'values': values}}
    la, ba, co = ['structure.atom_sites[' + name + '].adp_iso' for name in ['La', 'Ba', 'Co']]
    wavelength, cell = 'experiment.instrument.setup_wavelength', 'structure.cell.length_a'
    family, case = marker['family'], marker['case']
    if family == '450':
        assert case in {'normal-values','singleton','values','free','all-noop-values','all-noop-free','mixed-values','invalid-last','manual-draft','stop','takeover'}, 'ARRAY451 SETUP: original finite450 scripts only'
        first = call('array450-sentinel', 'Establish independent prior recorded Undo before ordered array', [{'path':wavelength,'value':1.495}])
        values = [{'path':la,'value':0.6},{'path':wavelength,'value':1.49},{'path':cell,'value':3.89}]
        if case == 'singleton': values = [{'path':la,'value':0.6}]
        elif case == 'all-noop-values': values = [{'path':la,'value':0.5},{'path':wavelength,'value':1.495},{'path':cell,'value':3.88}]
        elif case == 'mixed-values': values = [{'path':la,'value':0.5},{'path':ba,'value':0.7},{'path':cell,'value':3.88}]
        elif case == 'invalid-last': values = [{'path':la,'value':0.6},{'path':'original.absent.parameter','value':4.0}]
        elif case in {'stop','takeover'}: values = [{'path':la,'value':0.6},{'path':ba,'value':0.7},{'path':co,'value':0.8}]
        tool = 'set_free' if case in {'free','all-noop-free'} else 'set_parameters'
        if tool == 'set_free': values = [{'path':la,'free':case == 'all-noop-free'},{'path':ba,'free':True},{'path':co,'free':case == 'all-noop-free'}]
        expected = [[first],[call('array450-action-'+case,'Original ordered original-control array '+case,values,tool)]]
    else:
        assert case in {'hidden-change','hidden-noop','removed-noop','applied-replacement'}, 'ARRAY451 SETUP: original finite451 scripts only'
        purpose = 'Independent original current-member and retirement witness'
        if case == 'applied-replacement': expected = [[call('array451-original-A',purpose,[{'path':la,'value':0.6},{'path':ba,'value':0.7}])]]
        else:
            values = ([{'path':wavelength,'value':1.496},{'path':la,'value':0.5}] if case == 'removed-noop'
                else [{'path':la,'value':0.6},{'path':'experiment.instrument.calib_d_to_tof_linear','value':123.0 if case == 'hidden-noop' else 123.5}])
            expected = [[call('array451-sentinel',purpose,[{'path':wavelength,'value':1.495}])],
                        [call('array451-normal',purpose,values)],[call('array451-visible',purpose,values)]]
    assert json.dumps(config.get('native_turn_calls'),sort_keys=True,allow_nan=False) == json.dumps(expected,sort_keys=True,allow_nan=False), 'ARRAY451 SETUP: exact independent complete native scripts, no arbitrary tool/operand authority'
    assert (params.get('model') or 'gpt-6.1-sol') == 'gpt-6.1-sol', 'ARRAY451 SETUP: only independent originally offered primary model'
    supplied = params.get('config')
    if supplied is None: supplied = {}
    assert type(supplied) is dict and supplied.get('model_reasoning_effort','medium') == 'medium', 'ARRAY451 SETUP: independent originally offered medium effort, never arbitrary choice echo'
    return {'approvalPolicy':'never','approvalsReviewer':'user','model':'gpt-6.1-sol',
            'reasoningEffort':'medium','sandbox':{'type':'readOnly','networkAccess':False}}

# GUI416 opt-in only; native default peer behavior remains exact after reversal.
gui416_state = {'cursor': -1, 'choice': ('gpt-6.1-sol', 'medium'), 'threads': 0}
def gui416_choose(params, method):
    expected = config['gui415_policy']
    assert type(expected) is dict and set(expected) == {'case'} and scenario == 'native:script' and config['native_turn_calls'] == [[]], 'GUI416 SETUP: exact existing firstGUI owned fixture only'
    initial = ('gpt-6.1-sol', None)
    case = expected['case']
    if case == 'chooser-pointer':
        choices = [initial, ('gpt-6.1-sol','high'), ('gpt-6-sol',None), ('gpt-6-sol','medium')]
    elif case in ('chooser-space','chooser-return','chooser-enter'):
        choices = [initial, ('gpt-6.1-sol','high')]
    else:
        assert case in ('chooser-retirement','account','first-eye-clear','stale','remaining25','remaining24','remaining5','remaining4','remaining100','over100','unknown','zero-missing-recovered'), 'GUI416 SETUP: closed original GUI operands'
        choices = [initial]
    # UI Auto is distinct intent; the original literal catalogues resolve it to medium.
    defaults564 = {'gpt-6.1-sol': 'medium', 'gpt-6-sol': 'medium'}
    effective564 = []
    for model, intent in choices:
        choice = (model, defaults564[model] if intent is None else intent)
        # Alternate Auto then explicit medium may share ONE effective interval.
        if not effective564 or choice != effective564[-1]:
            effective564.append(choice)
    choices = effective564
    if method == 'thread/start':
        config416 = params.get('config')
        if config416 is None: config416 = {}
        assert type(config416) is dict, 'GUI416 SETUP: nullable official config must be a mapping when present'
        actual = (params.get('model') or initial[0], config416.get('model_reasoning_effort'))
    else:
        previous = gui416_state['choice']
        model = params.get('model') or previous[0]
        actual = (model, params.get('effort', previous[1] if model == previous[0] else None))
    assert actual in choices and choices.index(actual) >= gui416_state['cursor'], 'GUI416 SETUP: wrong-time/backwards/unoffered choice cannot become an effective echo'
    gui416_state.update(cursor=choices.index(actual),choice=actual)
    return actual

def emit(value):
    # Opt-in packet declaration closes before the existing real stdout write.
    if config.get('vm319_record_packets') is True:
        with trace.with_suffix('.vm319-packets.jsonl').open('a', encoding='utf-8') as output:
            output.write(json.dumps({'pid': os.getpid(), 'packet': value}, ensure_ascii=False,
                                    separators=(',', ':')) + '\n')
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
    # GUI404 opt-in literal table uses ONLY the existing genuine held original turn.
    # The ordinary peer/default scenarios and all event/envelope paths stay unchanged.
    if 'gui404_table_reply' in config:
        assert config['gui404_table_reply'] is True and scenario == 'native:script' and (
            ((config.get('native_turn_calls') == [[]] and turn_number == 1)
             or (config.get('readonly409') is True and config.get('native_turn_calls') == [[], []]
                 and turn_number in (1, 2))) and config.get('ux289_hold_input') is True
            and config.get('report_page_reply') is not True
        ), 'GUI404 SETUP: exact legal original no-native-operation held-table fixture only'
        item['text'] = 'Original fileauth reply 1\n\n| Item | Value |\n| --- | --- |\n| Alpha | 111 |\n| Bravo | 222 |\n| Charlie | 333 |\n| Delta | 444 |'
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


def reuse269_observe(request):
    """Opt-in original peer evidence; no account/model/scientific result is fabricated."""
    policy = config.get('reuse269')
    if policy is None:
        return
    cwd_path = Path(cwd)
    stage_name = policy.get('stage_name')
    path = cwd_path / 'inputs' / stage_name if stage_name else None
    original = None
    changed = False
    if path is not None and path.is_file():
        if not policy.get('_changed'):
            original = hashlib.sha256(path.read_bytes()).hexdigest()
            with path.open('ab') as output:
                output.write(b'Original provider-owned staged modification\n')
            policy['_changed'] = True
            changed = True
    with trace.with_suffix('.reuse269.jsonl').open('a', encoding='utf-8') as output:
        output.write(json.dumps({
            'original_request_id': request['id'], 'thread_id': thread_id,
            'cwd': str(cwd_path), 'stage_path': str(path) if path else None,
            'stage_changed': changed, 'stage_original_sha256': original,
            'stage_sha256': hashlib.sha256(path.read_bytes()).hexdigest()
                if path is not None and path.is_file() else None,
        }) + '\n')


def reuse280_observe_thread(request, result):
    """Retain actual effective public reply fields; never choose acceptance or credentials."""
    if config.get('reuse269') is None:
        return
    with trace.with_suffix('.reuse280-threads.jsonl').open('a', encoding='utf-8') as output:
        output.write(json.dumps({
            'request_id': request['id'], 'thread_id': result['thread']['id'],
            'requested_ephemeral': request['params'].get('ephemeral'),
            'effective_ephemeral': result['thread'].get('ephemeral'),
            'requested_cwd': request['params']['cwd'], 'effective_cwd': result['cwd'],
            'effective_roots': result['sandbox']['writableRoots'],
        }) + '\n')


# Actual native dynamic-tool bridge only; this peer never performs model edits or fits.
native_pending = {}
native_index = 0
native_rpc_sequence = 0
native_start_pending = None
native_steers = []
native_disclosed_parameters = []
native_disclosed_sources = []
#625 exact one-current-Context-ID fixture operand, no filenames/path or general resolver.
read625_files = []
#634 ID-only pins from genuine successful structure/atom replies, never fixture science.
structure634_ids = {}
native_action484_datasets = []


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
    if isinstance(value, dict) and set(value) == {'$structure634'}:
        assert config.get('structure634') is True and config.get('scenario') == 'native:script'
        key = value['$structure634']
        assert key in {'structure','first_atom','appended_atom'} and key in structure634_ids
        identifier = structure634_ids[key]
        assert type(identifier) is str and identifier
        return identifier
    if isinstance(value, dict) and set(value) == {'$read625_current_ordinal'}:
        assert config.get('read625') is True and config.get('scenario') == 'native:script'
        assert type(value['$read625_current_ordinal']) is int and value['$read625_current_ordinal'] == 0
        assert len(read625_files) == 1 and type(read625_files[0]['id']) is str and read625_files[0]['id']
        return read625_files[0]['id']
    if isinstance(value, dict) and set(value) == {'$original_selected_name'}:
        if config.get('main507_closed_files') is True:
            assert config.get('native_import267') is True and config.get('scenario') == 'native:script', (
                'MAIN507 SETUP: closed opaque selection is restricted to this explicit original native-import fixture')
            names = ('lbco.cif', 'hrpt.xye')
            assert value['$original_selected_name'] in names and len(native_disclosed_sources) == 2
            assert len({row['id'] for row in native_disclosed_sources}) == 2
            for row, byte_count in zip(native_disclosed_sources, (487, 83671), strict=True):
                assert type(row['id']) is str and row['id'] and type(row['bytes']) in (int, float) and row['bytes'] == byte_count
                assert type(row['format']) is str and row['format']
                if 'textReadable' in row:
                    assert row['textReadable'] is True
            return native_disclosed_sources[names.index(value['$original_selected_name'])]['id']
        matches = [row['id'] for row in native_disclosed_sources
                   if row['name'] == value['$original_selected_name'] and row['text_readable']]
        assert len(matches) == 1, 'IMPORT267 SETUP: actual original disclosed selected source ID is unique'
        return matches[0]
    if isinstance(value, dict) and set(value) == {'$original_action484_dataset'}:
        assert config.get('action484') is True and value['$original_action484_dataset'] is True, (
            'ACTION484 SETUP: only the closed declared ID selector is allowed')
        assert len(native_action484_datasets) == 1, (
            'ACTION484 SETUP: actual successful current inspection exposes exactly one dataset')
        identifier = native_action484_datasets[0]['id']
        assert type(identifier) is str and identifier, 'ACTION484 SETUP: current canonical dataset ID is mandatory'
        return identifier
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
    if config.get('input413') is True:
        assert spec['tool'] == 'acquire_inputs' and call_id == 'input413-acquire-original'
        Path(config['input413_arm']).touch()
        clear_observation('input413-acquisition-armed', {'rpc': rpc_id, 'call': call_id})
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
    if config.get('read625') is True:
        assert scenario == 'native:script' and config.get('readonly409') is True
        assert not any(config.get(k) for k in ['native_import267','main507_closed_files','input413','native_delay'])
        groups625 = config['native_turn_calls']
        assert len(groups625) == 2 and all(len(group) == 1 for group in groups625)
        assert all(group[0]['tool'] == 'read_selected_file' and group[0]['arguments'] == {
            'purpose':'Read independent selected text','file_id':{'$read625_current_ordinal':0},'offset':0,'max_bytes':65536
        } for group in groups625)
        context625 = context_inputs(request['params'])
        assert len(context625) == 1
        selection625 = context625[0]['selected_files']
        assert set(selection625) == {'collection_id','generation','files'} and len(selection625['files']) == 1
        row625 = selection625['files'][0]
        assert type(row625) is dict and type(row625['id']) is str and row625['id'] and row625['bytes'] == 18
        assert type(row625['format']) is str and row625['format']
        read625_files[:] = [row625]

    # Opt-in original genuine user scope, then the SAME public native RPC path.
    # Existing rpc83_context_inputs JSON-domain prior art; never a model path/ID.
    if config.get('input413') is True:
        assert scenario == 'fileauth' and turn_number == 1 and not native_pending
        contexts413 = context_inputs(request['params'])
        assert len(contexts413) == 1, 'INPUT413 SETUP: exactly one actual original current context'
        sources413 = contexts413[0]['input_scopes']['sources']
        assert type(sources413) is list and len(sources413) == 1
        source413 = sources413[0]
        assert type(source413) is dict and set(source413) == {'scope_id', 'ordinal', 'source_kind'}
        assert type(source413['scope_id']) is str and source413['scope_id'] and source413['source_kind'] == 'file'
        assert type(source413['ordinal']) is int
        config['native_calls'] = [{'tool': 'acquire_inputs', 'call_id': 'input413-acquire-original',
            'arguments': {'purpose': 'Original bounded input identity acquisition', 'scope_id': source413['scope_id']}}]
        trace.with_suffix('.input413-offered.json').write_text(json.dumps({
            'original_request': request, 'source': source413, 'literal_call': config['native_calls'][0]}))
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
        if config.get('main507_closed_files') is True:
            assert config.get('scenario') == 'native:script' and config.get('native_turn_calls')
            assert type(native_disclosed_sources) is list and len(native_disclosed_sources) == 2
            assert len({row['id'] for row in native_disclosed_sources}) == 2
            for row, byte_count in zip(native_disclosed_sources, (487, 83671), strict=True):
                assert type(row['id']) is str and row['id'] and type(row['bytes']) in (int, float) and row['bytes'] == byte_count
                assert type(row['format']) is str and row['format']
                if 'textReadable' in row:
                    assert row['textReadable'] is True
            clear_observation('main507-original-closed-source-addresses', {
                'request_id': request['id'],
                'sources': [{'id': row['id'], 'bytes': row['bytes'], 'format': row['format']}
                            for row in native_disclosed_sources],
            })
        else:
            clear_observation('import267-original-source-addresses', {
                'request_id': request['id'],
                'sources': [{'name': row['name'], 'id': row['id'], 'text_readable': row['text_readable']}
                            for row in native_disclosed_sources],
            })
    if config.get('structure634') is True and result and result.get('success'):
        tool634 = original['params']['tool']; args634 = original['params']['arguments']
        if tool634 in {'create_structure','edit_structure','edit_atom'}:
            value634 = json.loads(result['contentItems'][0]['text'])
            assert value634['status'] in {'completed','no_change'} and value634['complete'] is True
            structures634 = value634['structures']
            assert type(structures634) is list and len(structures634) == 1
            name634 = structures634[0]['id']; assert type(name634) is str and name634
            if tool634 == 'create_structure':
                sites634 = structures634[0]['sites']; assert len(sites634) == 1
                first634 = sites634[0]['id']; assert type(first634) is str and first634
                structure634_ids.update(structure=name634,first_atom=first634)
            else:
                assert args634['structure'] == structure634_ids['structure']
                structure634_ids['structure'] = name634
                if tool634 == 'edit_atom':
                    operation634 = args634['operation']
                    if operation634 == 'append':
                        atom634 = value634['atom_id']; assert type(atom634) is str and atom634
                        structure634_ids['appended_atom'] = atom634
                    elif operation634 == 'text' and args634['field'] == 'label':
                        atom634 = value634['atom_id']; assert type(atom634) is str and atom634
                        matches634 = [key for key in ('first_atom','appended_atom') if structure634_ids.get(key) == args634['atom']]
                        assert len(matches634) == 1
                        structure634_ids[matches634[0]] = atom634
    if (config.get('action484') is True and original['params']['tool'] == 'inspect_project'):
        native_action484_datasets.clear()
        disclosed = json.loads(result['contentItems'][0]['text']) if result and result.get('success') else {'datasets': []}
        datasets = disclosed['datasets']
        assert type(datasets) is list and all(type(row) is dict and type(row.get('id')) is str
                                             and row['id'] for row in datasets), (
            'ACTION484 SETUP: source is actual successful current dataset inspection, never fixture science')
        native_action484_datasets[:] = [{'id': row['id']} for row in datasets]
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


# Opt-in original protocol barrier. Only a genuine optional read AFTER a received
# input releases that exact input's ACK; no timer, fabricated flag or producer hook.
ux289_pending_input = None


def ux289_release_input(read_request):
    global ux289_pending_input  # noqa: PLW0603 -- original received RPC only
    original = ux289_pending_input
    if original is None:
        return
    ux289_pending_input = None
    clear_observation('ux289-original-ack-release', {
        'request_id': original['id'], 'read_id': read_request['id'],
        'method': original['method'], 'client_user_message_id':
            original['params']['clientUserMessageId'],
    })
    if config.get('ux295_refuse_original_input') is True:
        response = {'id': original['id'], 'error': {'code': -32600,
                    'message': 'Original explicit input admission refusal'}}
        clear_observation('ux295-original-input-refused', {'response': response})
        emit(response)
    else:
        native_start(original)


# PREFS419: exact Qt application-specific storage proof, never a grant from packet cwd.
def prefs419_pin_stage(discovery):
    import os
    original = config['prefs417_stage_change']
    receipt_path = Path(original['reference'])/'prefs419-storage.json'
    assert receipt_path.is_file() and not receipt_path.is_symlink(), 'PREFS419 SETUP: original QML storage observation is an owned regular reference receipt'
    storage = json.loads(receipt_path.read_text())
    expected = original['storage_identity']
    assert expected['application']==os.environ.get('EDI_TEST_APP_STORAGE_ID') and expected['invocation_root']==os.environ.get('EDI_TEST_APP_STORAGE_ROOT'), 'PREFS419 SETUP: exact native parent invocation environment, not arbitrary configuration grant'
    assert storage['application']==expected['application'] and storage['organization']=='EdiIndependentAcceptance', 'PREFS419 SETUP: actual Qt app identity equals exact launched isolated application'
    assert storage['application'].startswith('acceptance-') and len(storage['application'])==75 and all(c in '0123456789abcdef' for c in storage['application'][11:]), 'PREFS419 SETUP: original unique application identity, not generic home grant'
    root = Path(storage['app_local_data'])
    assert root.is_absolute() and root.parts[-2:]==('EdiIndependentAcceptance',expected['application']) and root.resolve()==root and root.is_dir() and not root.is_symlink(), 'PREFS419 SETUP: exact nonlink application-local root, never broad home or supplied cwd'
    assert len(discovery['params']['cwds'])==1, 'PREFS419 SETUP: actual original discovery owns exactly one workspace'
    workspace = Path(discovery['params']['cwds'][0])
    assert workspace.is_absolute() and workspace.resolve()==workspace and workspace!=root and workspace.is_relative_to(root), 'PREFS419 SETUP: original discovery cwd is physically inside exact fresh app-specific root'
    chain = [root]+[root.joinpath(*workspace.relative_to(root).parts[:i]) for i in range(1,len(workspace.relative_to(root).parts)+1)]
    chain += [workspace/'.agents',workspace/'.agents/skills']
    assert all(p.is_dir() and not p.is_symlink() for p in chain), 'PREFS419 SETUP: no parent-link escape from original owned workspace'
    dirs = [{'path':str(p),'dev':p.stat().st_dev,'ino':p.stat().st_ino} for p in chain]
    files = sorted((workspace/'.agents/skills').glob('*/SKILL.md'))
    assert len(files)==2 and all(p.is_file() and not p.is_symlink() and p.parent.is_dir() and not p.parent.is_symlink() and p.resolve().is_relative_to(workspace) for p in files), 'PREFS419 SETUP: exact two regular nonlink package paths'
    assert sorted(p.read_bytes().decode('utf-8') for p in files)==sorted([original['alphaA'],original['beta']]), 'PREFS419 SETUP: original healthy staged A is independently predeclared before arming'
    pins = [{'path':str(p),'dev':p.stat().st_dev,'ino':p.stat().st_ino,
             'parent_dev':p.parent.stat().st_dev,'parent_ino':p.parent.stat().st_ino} for p in files]
    result = {'storage':storage,'cwd':str(workspace),'directories':dirs,'files':pins}
    old = config.get('_prefs419_pin')
    assert old is None or not (Path(original['reference'])/'prefs417-arm').exists() or old==result, 'PREFS419 SETUP: after genuine arm no replacement workspace/file identity can be adopted'
    config['_prefs419_pin']=result
    clear_observation('prefs419-original-storage-pinned',{'request':discovery,**result})


def prefs417_stage_read(request):
    import os, stat
    original = config.get('prefs417_stage_change')
    if original is None or config.get('_prefs417_changed'):
        return
    reference = Path(original['reference'])
    if not (reference/'prefs417-arm').exists():
        return
    assert scenario=='native:script' and config['native_turn_calls']==[[]], 'PREFS417 SETUP: unchanged no-native script only'
    discovery = config['_prefs417_discovery']
    pin = config['_prefs419_pin']
    workspace = Path(pin['cwd'])
    assert discovery['params']['cwds']==[str(workspace)], 'PREFS419 SETUP: same originally pinned actual discovery workspace'
    for row in pin['directories']:
        path = Path(row['path']); current = path.stat(follow_symlinks=False)
        assert stat.S_ISDIR(current.st_mode) and (current.st_dev,current.st_ino)==(row['dev'],row['ino']), 'PREFS419 SETUP: original physical directory identity survives until actual read'
    files = [Path(row['path']) for row in pin['files']]
    for row,path in zip(pin['files'],files):
        current = path.stat(follow_symlinks=False); parent = path.parent.stat(follow_symlinks=False)
        assert stat.S_ISREG(current.st_mode) and current.st_nlink==1 and (current.st_dev,current.st_ino)==(row['dev'],row['ino']) and stat.S_ISDIR(parent.st_mode) and (parent.st_dev,parent.st_ino)==(row['parent_dev'],row['parent_ino']), 'PREFS419 SETUP: original regular file/package parent identity, not replaced path'
    before = [{'path':str(path),'hex':path.read_bytes().hex()} for path in files]
    assert sorted(bytes.fromhex(row['hex']).decode('utf-8') for row in before)==sorted([original['alphaA'],original['beta']]), 'PREFS417 SETUP: actual pre-change stage is independently approved A'
    targets = [row for row in pin['files'] if Path(row['path']).read_bytes()==original['alphaA'].encode('utf-8')]
    assert len(targets)==1, 'PREFS417 SETUP: exact original A content identifies one actual opaque staged path'
    target = targets[0]; path = Path(target['path']); descriptors=[]
    try:
        # Open every original directory relative to its original parent, no followed links.
        root = Path(pin['storage']['app_local_data'])
        fd = os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);descriptors.append(fd)
        expected_dirs = {row['path']:row for row in pin['directories']}
        rootfact = os.fstat(fd); rootpin = expected_dirs[str(root)]
        assert (rootfact.st_dev,rootfact.st_ino)==(rootpin['dev'],rootpin['ino']), 'PREFS419 SETUP: pinned exact root FD before any write'
        current = root
        for component in path.parent.relative_to(root).parts:
            fd = os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);descriptors.append(fd);current=current/component
            fact = os.fstat(fd)
            if str(current) in expected_dirs:
                row=expected_dirs[str(current)]; wanted=(row['dev'],row['ino'])
            else:
                assert current==path.parent, 'PREFS419 SETUP: no unproved intermediate package directory'
                wanted=(target['parent_dev'],target['parent_ino'])
            assert (fact.st_dev,fact.st_ino)==wanted, 'PREFS419 SETUP: each original directory descriptor remains exact'
        filefd=os.open(path.name,os.O_RDWR|os.O_NOFOLLOW,dir_fd=fd);descriptors.append(filefd)
        fact=os.fstat(filefd)
        assert stat.S_ISREG(fact.st_mode) and fact.st_nlink==1 and (fact.st_dev,fact.st_ino)==(target['dev'],target['ino']), 'PREFS419 SETUP: exact originally pinned file descriptor authorizes bounded own stimulus'
        with os.fdopen(os.dup(filefd),'r+b') as stream:
            assert stream.read()==original['alphaA'].encode('utf-8'), 'PREFS419 SETUP: same exact original body at final FD before mutation'
            stream.seek(0);stream.write(original['alphaB'].encode('utf-8'));stream.truncate()
    finally:
        for fd in reversed(descriptors):os.close(fd)
    after = [{'path':str(path),'hex':path.read_bytes().hex()} for path in files]
    config['_prefs417_changed'] = True
    clear_observation('prefs417-original-stage-changed',{'request':request,'discovery_request':discovery,
        'storage':pin['storage'],'cwd':str(workspace),'directories':pin['directories'],'before':before,'after':after})
    (reference/'prefs417-mutated').write_text(str(request['id']))
def usage_read(request):
    prefs417_stage_read(request)
    if config.get('ux289_hold_input') is True:
        ux289_release_input(request)
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
    if 'gui392_usage_reply' in config or 'gui392_usage_replies' in config:
        # Optional literal public-protocol operand, not a subject setter/clock.
        if 'gui392_usage_replies' in config:
            assert number <= len(config['gui392_usage_replies']), 'GUI392 SETUP: no undeclared extra usage reply'
            result = config['gui392_usage_replies'][number - 1]
        else:
            result = config['gui392_usage_reply']
        assert isinstance(result, dict) and set(result) == {
            'rateLimits', 'rateLimitsByLimitId', 'accountId', 'ordinaryUsageAllowed',
            'rateLimitResetCredits', 'rateLimitUpsell',
        }, 'GUI392 SETUP: complete independently authored usage reply only'

    def finish():
        if 'gui392_usage_reply' in config or 'gui392_usage_replies' in config:
            clear_observation('gui392-original-usage-reply', {'number': number, 'id': request['id'], 'result': result})
        else:
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



def transport304_dispatch(request):
    """Actual owned original process; no account, inference or subject callbacks."""
    mode = config['transport304_mode']
    if mode == 'human-wait' and request.get('method') is None:
        assert request.get('id') == 'human575-A-0', 'HUMAN575: only the original first request may be answered/rejected'
        clear_observation('human575-response', {'response': request})
        return
    if mode == 'human-wait' and request.get('method') == 'original/human575-eof':
        clear_observation('human575-real-eof', {})
        sys.exit(0)
    if request.get('method') != 'initialize':
        raise RuntimeError('transport304 accepts only the predeclared public initialize request')
    label = request['params']['clientInfo']['name'].removeprefix('independent-public-')
    assert label in {'A', 'B'}, 'TRANSPORT304 SETUP: independent caller labels are finite'
    clear_observation('transport304-request', {'label': label, 'request': request})
    if label == 'A' and mode == 'failed-eof':
        clear_observation('transport304-real-eof', {'label': label})
        sys.exit(0)
    if label == 'A' and mode == 'failed-deadline':
        clear_observation('transport304-real-pending', {'label': label, 'request_id': request['id']})
        return
    if label == 'A' and mode == 'failed-record':
        batch = [{'method': 'original/transport304-before-malformed',
                  'params': {'originalCaller': 'A', 'position': 'before-malformed'}}]
        wire = (json.dumps(batch[0], separators=(',', ':')) + '\n').encode() + (
            b'{"malformed":"ORIGINAL_TRANSPORT304_CANARY"\n')
    else:
        response = {'id': request['id'], 'result': {
            'userAgent': 'original-offline-peer/0.162.1',
            'codexHome': str(trace.parent / 'peer-unused-profile'),
            'platformFamily': 'unix', 'platformOs': 'linux'}}
        batch = [response]
        if mode == 'human-wait':
            batch.extend({'id': 'human575-' + label + '-' + str(index),
                          'method': 'item/tool/requestUserInput',
                          'params': {'originalCaller': label, 'questions': []}}
                         for index in range(3))
        elif label == 'A':
            batch.extend({'method': name, 'params': {'originalCaller': label}}
                         for name in ['original/transport304-boundary', 'original/transport304-tail'])
        wire = ''.join(json.dumps(x, separators=(',', ':')) + '\n' for x in batch).encode()
    pipe_bound = os.fpathconf(sys.stdout.fileno(), 'PC_PIPE_BUF')
    assert len(wire) <= pipe_bound, (
        'TRANSPORT304 SETUP: complete original batch fits the actual owned pipe atomic bound'
    )
    # This is a DECLARATION, closed before delivery. Callback retirement can kill
    # this process immediately after os.write; public exact receipts prove delivery.
    clear_observation('transport308-packet-declared', {'label': label, 'request_id': request['id'],
        'records': batch, 'wire_utf8': wire.decode(), 'bytes': len(wire),
        'sha256': hashlib.sha256(wire).hexdigest(), 'pipe_bound': pipe_bound, 'mode': mode})
    written = os.write(sys.stdout.fileno(), wire)
    assert written == len(wire), 'TRANSPORT304 SETUP: original complete bounded batch reaches actual pipe'

for line in sys.stdin:
    request = json.loads(line)
    with trace.open('a', encoding='utf-8') as output:
        output.write(json.dumps(request, ensure_ascii=False) + '\n')
    if config.get('vm319_record_packets') is True:
        with trace.with_suffix('.vm319-requests.jsonl').open('a', encoding='utf-8') as output:
            output.write(json.dumps({'pid': os.getpid(), 'request': request}, ensure_ascii=False,
                                    separators=(',', ':')) + '\n')
    method = request.get('method')
    params = request.get('params') or {}
    if config.get('transport304_mode'):
        transport304_dispatch(request)
        continue
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
    elif method == 'model/list' and 'gui393_model_reply' in config:
        # Literal independent provider input; every original scenario/default is unchanged.
        reply(request, config['gui393_model_reply'])
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
        if config.get('prefs417_stage_change') is not None:
            config['_prefs417_discovery'] = request
            prefs419_pin_stage(request)
        if config.get('gui392_record_skill_bytes') is True:
            for cwd in params.get('cwds', []):
                clear_observation('gui392-original-skill-files', {
                    'request': request, 'cwd': cwd,
                    'files': [{'path': str(skill), 'hex': skill.read_bytes().hex()}
                              for skill in sorted((Path(cwd) / '.agents/skills').glob('*/SKILL.md'))
                              if skill.is_file() and not skill.is_symlink()],
                })
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
    elif method == 'thread/settings/update' and config.get('gui415_policy') is not None:
        assert params['threadId'] == thread_id, 'GUI416 SETUP: actual settings belong to original emitted thread'
        model416, effort416 = gui416_choose(params, method)
        assert params.get('approvalPolicy','never') == 'never' and params.get('approvalsReviewer','user') == 'user', 'GUI416 SETUP: no approval expansion during actual choice history'
        assert params.get('sandboxPolicy',{'type':'readOnly','networkAccess':False}) == {'type':'readOnly','networkAccess':False}, 'GUI416 SETUP: no sandbox expansion during actual choice history'
        reply(request, {})
        notify('thread/settings/updated', {'threadId': thread_id, 'threadSettings': {
            'disabledPluginIds': [], 'cwd': cwd, 'approvalPolicy':'never', 'approvalsReviewer':'user',
            'sandboxPolicy':{'type':'readOnly','networkAccess':False}, 'activePermissionProfile':None,
            'model':model416, 'modelProvider':'openai', 'serviceTier':None, 'effort':effort416, 'summary':None,
            'collaborationMode':{'mode':'default','settings':{'model':model416,'reasoning_effort':effort416,'developer_instructions':None}},
            'multiAgentMode':'explicitRequestOnly','personality':None}})
    elif method == 'thread/settings/update' and config.get('policy410') is not None:
        # Complete independently declared offered choices; never accept arbitrary subject settings.
        expected = config['policy410']
        assert set(expected) == {'model', 'effort'} and expected['model'] in {'gpt-6.1-sol', 'gpt-6-sol'} and expected['effort'] in {'medium', 'high'}, (
            'POLICY410 SETUP: only literal independently supplied callback choices'
        )
        assert params['threadId'] == thread_id, 'POLICY410 SETUP: actual settings packet targets original emitted thread'
        pairs = [('gpt-6.1-sol', 'medium'), (expected['model'], expected['effort'])]
        actual = (params.get('model', 'gpt-6.1-sol'), params.get('effort', 'medium'))
        assert actual in pairs, 'POLICY410 SETUP: unsupported settings never become an effective echo'
        model, effort = next(pair for pair in pairs if pair == actual)
        assert params.get('approvalPolicy', 'never') == 'never' and params.get('approvalsReviewer', 'user') == 'user', (
            'POLICY410 SETUP: genuine selected choice cannot override read-only approval contract'
        )
        assert params.get('sandboxPolicy', {'type': 'readOnly', 'networkAccess': False}) == {'type': 'readOnly', 'networkAccess': False}, (
            'POLICY410 SETUP: actual requested policy stays read-only/no-network'
        )
        reply(request, {})
        notify('thread/settings/updated', {'threadId': thread_id, 'threadSettings': {
            'disabledPluginIds': [], 'cwd': cwd, 'approvalPolicy': 'never', 'approvalsReviewer': 'user',
            'sandboxPolicy': {'type': 'readOnly', 'networkAccess': False},
            'activePermissionProfile': None, 'model': model, 'modelProvider': 'openai',
            'serviceTier': None, 'effort': effort, 'summary': None,
            'collaborationMode': {'mode': 'default', 'settings': {'model': model,
                'reasoning_effort': effort, 'developer_instructions': None}},
            'multiAgentMode': 'explicitRequestOnly', 'personality': None,
        }})
    elif method == 'thread/settings/update' and config.get('readonly409') is True:
        # Existing peer, opt-in fixture only. The fixed catalogue operands are
        # independently declared; an ACK alone is never an effective receipt.
        assert params['threadId'] == thread_id, 'INPUT409 SETUP: settings target original actual thread'
        assert params.get('model', 'gpt-6.1-sol') == 'gpt-6.1-sol' and params.get('effort', 'medium') == 'medium', (
            'INPUT409 SETUP: this unchanged default catalogue offers only the declared model/effort'
        )
        assert params.get('approvalPolicy', 'never') == 'never' and params.get('approvalsReviewer', 'user') == 'user', (
            'INPUT409 SETUP: optional official overrides cannot request another approval policy'
        )
        assert params.get('sandboxPolicy', {'type': 'readOnly', 'networkAccess': False}) == {
            'type': 'readOnly', 'networkAccess': False
        }, 'INPUT409 SETUP: optional official policy override remains independently read-only'
        reply(request, {})
        notify('thread/settings/updated', {'threadId': thread_id, 'threadSettings': {
            'disabledPluginIds': [], 'cwd': cwd, 'approvalPolicy': 'never', 'approvalsReviewer': 'user',
            'sandboxPolicy': {'type': 'readOnly', 'networkAccess': False},
            'activePermissionProfile': None, 'model': 'gpt-6.1-sol', 'modelProvider': 'openai',
            'serviceTier': None, 'effort': 'medium', 'summary': None,
            'collaborationMode': {'mode': 'default', 'settings': {'model': 'gpt-6.1-sol',
                'reasoning_effort': 'medium', 'developer_instructions': None}},
            'multiAgentMode': 'explicitRequestOnly', 'personality': None,
        }})
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
        if config.get('reuse269') is not None:
            count = sum(json.loads(line).get('method') == 'thread/start'
                        for line in trace.read_text(encoding='utf-8').splitlines())
            thread_id = '019a0290-0000-7000-8000-' + f'{os.getpid() * 1000 + count:012d}'
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
        if config.get('gui415_policy') is not None:
            model416, effort416 = gui416_choose(params, method)
            gui416_state['threads'] += 1
            thread_id = '019a0290-0000-7000-8000-' + f"{os.getpid() * 1000 + gui416_state['threads']:012d}"
            value['thread']['id'] = thread_id
            value.update(approvalPolicy='never', approvalsReviewer='user', model=model416,
                         reasoningEffort=effort416, sandbox={'type':'readOnly','networkAccess':False})
        if config.get('native_array451_policy') is not None:
            value.update(array451_policy_fields(params))
        if config.get('readonly409') is True:
            assert scenario in {
                'complete', 'different-cwd', 'different-provider',
                'different-reviewer', 'fileauth', 'gn:account-apikey',
                'gn:account-chatgpt', 'gn:account-chatgptAuthTokens', 'gn:account-null',
                'gn:catalogue-within', 'gn:finished-commandExecution', 'gn:finished-fileChange',
                'gn:immutable-delta', 'gn:immutable-duplicate', 'gn:immutable-type',
                'gn:lifetime-events', 'gn:lifetime-stderr', 'gn:lifetime-wire',
                'gn:logout-hold', 'gn:logout-late-start', 'gn:missing-delta-turn',
                'gn:missing-item-turn', 'gn:missing-request-turn', 'gn:question-stale-answer',
                'gn:question-wrong-resolve', 'gn:r:final-message-snapshot', 'gn:r:interruption:commandExecution:failed',
                'gn:r:interruption:commandExecution:interrupted', 'gn:r:interruption:fileChange:failed', 'gn:r:interruption:fileChange:interrupted',
                'gn:r:partial-message', 'gn:r:progress:command', 'gn:r:progress:plan',
                'gn:r:progress:question', 'gn:r:progress:reasoning', 'gn:r:progress:summary',
                'gn:r:status-:collabAgentToolCall:item:completed', 'gn:r:status-:collabAgentToolCall:item:inProgress', 'gn:r:status-:collabAgentToolCall:item:missing',
                'gn:r:status-:collabAgentToolCall:snapshot:inProgress', 'gn:r:status-:collabAgentToolCall:snapshot:missing', 'gn:r:status-:dynamicToolCall:item:completed',
                'gn:r:status-:dynamicToolCall:item:inProgress', 'gn:r:status-:dynamicToolCall:item:missing', 'gn:r:status-:dynamicToolCall:snapshot:inProgress',
                'gn:r:status-:dynamicToolCall:snapshot:missing', 'gn:r:status-:mcpToolCall:item:completed', 'gn:r:status-:mcpToolCall:item:inProgress',
                'gn:r:status-:mcpToolCall:item:missing', 'gn:r:status-:mcpToolCall:snapshot:inProgress', 'gn:r:status-:mcpToolCall:snapshot:missing',
                'gn:r:stop-unsettled', 'gn:steer-missing', 'gn:steer-wrong',
                'gn:unfinished-commandExecution', 'gn:unfinished-fileChange', 'gn:unknown-control',
                'gn:workspace-change', 'gn:x:mcp-active', 'gn:x:mcp-final',
                'gn:x:mcp-stale', 'gn:x:question-answer', 'gn:x:stop-existing',
                'gn:x:stop-new', 'hold', 'native:script',
                'network-enabled', 'start-pending',
            }, (
                'INPUT409 SETUP: explicit finite preserved fileauth/effective-policy fixture only'
            )
            if scenario == 'native:script':
                assert 'gui415_policy' not in config and 'native_array451_policy' not in config, (
                    'IMPORT464 SETUP: strict current default script cannot combine conflicting policy opt-ins'
                )
                # Actual independent trace chronology; Clear must not reuse an old thread identity.
                count = sum(json.loads(line).get('method') == 'thread/start'
                            for line in trace.read_text(encoding='utf-8').splitlines())
                thread_id = '019a0290-0000-7000-8000-' + f'{count:012d}'
                value['thread']['id'] = thread_id
            # Independent original catalogue constants, not an echo of subject policy/choices.
            value.update(approvalPolicy='never', approvalsReviewer='user',
                         model='fixture-model-0' if scenario == 'gn:catalogue-within' else 'gpt-6.1-sol',
                         reasoningEffort='medium', sandbox={'type': 'readOnly', 'networkAccess': False})
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
        reuse280_observe_thread(request, value)
        reply(request, value)
    elif method == 'turn/start':
        reuse269_observe(request)
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
        if scenario.startswith('native:') or config.get('input413') is True:
            if config.get('ux289_hold_input') is True:
                assert ux289_pending_input is None, 'UX289 SETUP: original input has one pending envelope'
                ux289_pending_input = request
                clear_observation('ux289-original-input-received', {
                    'request_id': request['id'],
                    'client_user_message_id': request['params']['clientUserMessageId'],
                })
            else:
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
