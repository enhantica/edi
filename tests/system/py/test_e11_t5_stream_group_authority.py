"""Whole group authority precedes normalized callable publication (review78/S-R2)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    'group_originals', Path(__file__).with_name('test_e11_t5_stream_membership.py')
)
originals = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(originals)
host = originals.host
wire = originals.wire


@pytest.mark.parametrize('entry', ['arguments-done', 'item-done'])
def test_complete_call_is_staged_until_the_whole_group_is_valid(host, entry):
    host.command('stream_start')
    first = originals.original('function_call', 'earlier-complete-call')
    if entry == 'arguments-done':
        added = {**first, 'status': 'in_progress', 'arguments': ''}
        events = [
            originals.item_event(added, done=False),
            {
                'type': 'response.function_call_arguments.done',
                'item_id': first['id'],
                'output_index': 0,
                'arguments': '{}',
            },
        ]
    else:
        events = [originals.item_event(first)]
    prefix = wire(host, events)
    assert prefix['reply']['ok'], 'S-R2: a complete valid callable prefix reaches staging'
    later = originals.original('function_call', 'later-incomplete-call')
    later['status'] = 'incomplete'
    rejected = wire(
        host,
        [
            originals.item_event(first),
            originals.item_event(later, 1),
            originals.complete([first, later]),
        ],
    )
    assert not any(e.get('type') == 'tool_call' for e in prefix['stream_events']), (
        'S-R2: neither arguments.done nor item.done alone publishes normalized executable work'
    )
    assert not rejected['reply']['ok'] and not any(
        e.get('type') == 'tool_call' for e in rejected['stream_events']
    ), 'S-R2: a later invalid sibling prevents all normalized publication of the earlier prefix'
