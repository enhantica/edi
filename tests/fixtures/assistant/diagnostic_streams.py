"""Independently planted public SSE diagnostic preservation inputs, never owner traffic.

Schema: https://developers.openai.com/api/reference/resources/responses/streaming-events
SIWC: https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery
Two deliberately invalid streams and one interrupted valid prefix distinguish feed/finish.
Expected parser-to-native/card equality is a preservation invariant, not an error-text golden.
"""

import json

PRIVATE_MARKER = 'PRIVATE_FIXTURE_CONTENT_MUST_NOT_APPEAR'


def sse(events):
    return b''.join(
        b'data: ' + json.dumps(event, ensure_ascii=False, separators=(',', ':')).encode() + b'\n\n'
        for event in events
    )


def diagnostic_wire(case):
    if case == 'malformed-json':
        return ('data: {"private_note":"' + PRIVATE_MARKER + '","type":\n\n').encode()
    if case == 'changed-completed-item':

        def message(text):
            return {
                'id': 'fixed-message',
                'type': 'message',
                'role': 'assistant',
                'status': 'completed',
                'content': [
                    {'type': 'output_text', 'text': text, 'annotations': [], 'logprobs': []}
                ],
            }

        return sse([
            {
                'type': 'response.output_item.done',
                'output_index': 0,
                'item': message('Original public text'),
            },
            {
                'type': 'response.output_item.done',
                'output_index': 0,
                'item': message(PRIVATE_MARKER),
            },
        ])
    if case == 'truncated':
        return sse([
            {
                'type': 'response.created',
                'sequence_number': 0,
                'response': {'id': 'fixture-response', 'status': 'in_progress', 'output': []},
            }
        ])
    raise ValueError('unknown bounded independent stream fixture')
