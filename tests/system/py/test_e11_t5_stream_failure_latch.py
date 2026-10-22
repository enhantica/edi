"""Rejected stream continuation fences despite one-shot diagnostic preparation failure.

No full Reply delivery is promised during permanent exhaustion. Scientific outputs are absent.
The existing allocator and public Sink exercise actual catch preparation and cached-copy siblings.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.assistant.diagnostic_streams import sse
from tests.fixtures.assistant.response_events import message_complete, message_start, text_fragment

ROOT = Path(__file__).resolve().parents[3]


def run(point, category, mode, *, as_length=False, natural=None):
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_STREAM_LATCH_PROBE',
            ROOT / 'build/assistant-tests/assistant_stream_failure_latch_probe',
        )
    )
    assert binary.is_file(), (
        'I13/R1: actual stream failure consumer must exist before fault claims'
    )
    text = 'Independent original public text'
    prefix = sse(message_start())
    trigger = sse([text_fragment(text)])
    if point == 'terminal':
        prefix += trigger
        trigger = sse(message_complete(text))
    call = {
        'type': 'function_call',
        'id': 'late-function',
        'call_id': 'late-call',
        'name': 'inspect_project',
        'arguments': '{}',
        'status': 'completed',
    }
    followup = sse([
        text_fragment(' forbidden later text'),
        {'type': 'response.output_item.done', 'output_index': 1, 'item': call},
    ])
    if category == 'valid':
        followup = b''
    if natural:
        prefix = b''
        trigger = b'data: {"type":\n\n' if natural == 'schema' else b'data: ' + b'x' * 1048576
    payload = {
        'point': point,
        'category': category,
        'mode': mode,
        'as_length': as_length,
        'prefix': prefix.decode(),
        'trigger': trigger.decode(),
        'followup': followup.decode(),
    }
    process = subprocess.run(
        [str(binary)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=4,
        check=False,
    )
    assert process.returncode == 0, (
        'I13/R1: tests-owned consumer preparation and ordinary observations survive; '
        'process/setup failure is not a qualified decoder-fence red'
    )
    result = json.loads(process.stdout)
    assert 'host_error' not in result and result['prefix_ok'], (
        'I13/R1: all wire/exception/observer preparation occurs before the actual armed boundary'
    )
    if category not in {'natural', 'valid'}:
        assert (
            result['sink_selected']
            and result['direct_caught']
            and (result['direct_seen'] == 0 and not result['direct_fired'])
        ), (
            'I13/R1: the same preconstructed actual exception rethrow consumes no counted '
            'allocation; the original real text/terminal Sink is reached before arming'
        )
    return result


def fenced(result):
    return (
        not result['observer_threw']
        and all(not result[key]['ok'] for key in ('finish_before', 'later', 'finish_after'))
        and result['attempts_before'] == result['attempts_after']
        and result['delivered_before'] == result['delivered_after']
        and result['tools_before'] == result['tools_after']
    )


@pytest.mark.parametrize('category', ['plain', 'refusal'])
@pytest.mark.parametrize('point', ['text', 'terminal'])
@pytest.mark.parametrize('as_length', [False, True], ids=['allocation', 'length'])
def test_diagnostic_preparation_failure_cannot_reopen_or_complete_rejected_stream(
    category, point, as_length
):
    result = run(point, category, 'preparation', as_length=as_length)
    assert result['preparation_fired'] and result['preparation_seen'] == 1, (
        'I13/R1: first one-shot failure occurs in actual producer catch preparation after '
        'the independently nonallocating Sink throw, before any test observer'
    )
    assert fenced(result), (
        'I3/I13/R1: diagnostic construction may throw, but recovered memory must not let '
        'a rejected stream finish successfully, consume another frame or emit late text/tools: '
        + str(result)
    )


@pytest.mark.parametrize('category', ['plain', 'refusal'])
@pytest.mark.parametrize('point', ['text', 'terminal'])
def test_unarmed_sink_failure_retains_complete_first_cause_and_rejection(category, point):
    result = run(point, category, 'ordinary')
    assert result['first_returned'] and not result['first']['ok'], (
        'I13/R1: an ordinary authentic Sink exception reaches the complete first-failure cache'
    )
    assert not result['preparation_fired'] and result['preparation_seen'] > 0, (
        'I13/R1: positive counting control reaches allocating catch preparation without a fault'
    )
    assert fenced(result) and all(
        result[key] == result['first'] for key in ('finish_before', 'later', 'finish_after')
    ), 'I3/I13/R1: ordinary rejection preserves the entire first safe Reply and nonexecution fence'


@pytest.mark.parametrize('category', ['plain', 'refusal'])
@pytest.mark.parametrize('point', ['text', 'terminal'])
def test_exhausted_copy_of_already_latched_reply_keeps_fence_and_original_cause(category, point):
    result = run(point, category, 'cached-copy')
    assert result['first_returned'] and not result['first']['ok'] and result['copy_fired'], (
        'I13/R1: the first complete cache exists before ordinary one-shot return-copy exhaustion'
    )
    assert result['copy_escaped'] in {1, 2} and all(
        result[key + '_before_copy'] == result[key + '_before']
        for key in ('attempts', 'delivered', 'tools')
    ), 'I13/R1: cached Reply copy may throw, but it neither reruns the decoder nor emits events'
    assert fenced(result) and all(
        result[key] == result['first'] for key in ('finish_before', 'later', 'finish_after')
    ), 'I3/I13/R1: memory recovery after cached-copy failure preserves first cause and rejection'


@pytest.mark.parametrize('natural', ['schema', 'quota'])
def test_natural_refusal_then_cached_copy_exhaustion_does_not_resume(natural):
    result = run('text', 'natural', 'cached-copy', natural=natural)
    assert result['first_returned'] and not result['first']['ok'] and result['copy_fired'], (
        'I13/R1: actual ordinary parser/quota refusal is latched before return-copy exhaustion'
    )
    assert fenced(result) and all(
        result[key] == result['first'] for key in ('finish_before', 'later', 'finish_after')
    ), 'I3/I13/R1: natural schema/quota refusal keeps first safe cause and emits no late tool/text'


def test_complete_nonthrowing_sink_remains_a_real_success_control():
    result = run('terminal', 'valid', 'ordinary')
    assert (
        result['first_returned']
        and result['first']['ok']
        and all(result[key]['ok'] for key in ('finish_before', 'later', 'finish_after'))
    ), 'I13/R1: a complete matching official response and nonthrowing Sink remain successful'
    assert not result['preparation_fired'] and result['tools_after'] == 0, (
        'I3/I13/R1: a valid text-only control invents neither allocation failure nor a tool call'
    )
