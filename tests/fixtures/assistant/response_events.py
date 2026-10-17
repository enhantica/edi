"""Literal public Responses message lifecycle from the official streaming-event schema."""


def message_start(*, item_id='message-one', channel='output_text'):
    part = (
        {'type': 'refusal', 'refusal': ''}
        if channel == 'refusal'
        else {'type': 'output_text', 'text': '', 'annotations': [], 'logprobs': []}
    )
    return [
        {
            'type': 'response.output_item.added',
            'output_index': 0,
            'sequence_number': 0,
            'item': {
                'id': item_id,
                'type': 'message',
                'role': 'assistant',
                'status': 'in_progress',
                'content': [],
            },
        },
        {
            'type': 'response.content_part.added',
            'item_id': item_id,
            'output_index': 0,
            'content_index': 0,
            'sequence_number': 1,
            'part': part,
        },
    ]


def text_fragment(text, *, item_id='message-one', sequence_number=2, channel='output_text'):
    event = {
        'type': 'response.' + channel + '.delta',
        'item_id': item_id,
        'output_index': 0,
        'content_index': 0,
        'delta': text,
        'sequence_number': sequence_number,
    }
    if channel == 'output_text':
        event['logprobs'] = []
    return event


def message_complete(
    text, *, item_id='message-one', response_id='response-one', channel='output_text'
):
    part = (
        {'type': 'refusal', 'refusal': text}
        if channel == 'refusal'
        else {'type': 'output_text', 'text': text, 'annotations': [], 'logprobs': []}
    )
    done = {
        'type': 'response.' + channel + '.done',
        'item_id': item_id,
        'output_index': 0,
        'content_index': 0,
        'sequence_number': 3,
        ('refusal' if channel == 'refusal' else 'text'): text,
    }
    if channel == 'output_text':
        done['logprobs'] = []
    item = {
        'type': 'message',
        'id': item_id,
        'role': 'assistant',
        'status': 'completed',
        'content': [part],
    }
    return [
        done,
        {
            'type': 'response.content_part.done',
            'item_id': item_id,
            'output_index': 0,
            'content_index': 0,
            'sequence_number': 4,
            'part': part,
        },
        {
            'type': 'response.output_item.done',
            'output_index': 0,
            'sequence_number': 5,
            'item': item,
        },
        {
            'type': 'response.completed',
            'sequence_number': 6,
            'response': {'id': response_id, 'status': 'completed', 'output': [item]},
        },
    ]
