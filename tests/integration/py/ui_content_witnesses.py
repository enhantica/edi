"""Join selected native content, accepted models and actual render consumers."""

import math
import re

from tests.fixtures.ui_responsiveness.content_contract import (
    content_expectations,
    required_content,
)
from tests.fixtures.ui_responsiveness.tab_inventory import tab_targets
from tests.integration.py.ui_causal_witnesses import gui_thread, need, rows, unique


def identity(value):
    return (isinstance(value, str) and bool(value.strip())) or (type(value) is int and value > 0)


def consumed_payload(trace, selected, rendered, spec):
    consumed = [r for r in rendered.get('contents', []) if r.get('root') == selected['root']]
    need(len(consumed) == 1, 'the completion frame consumes the actual selected content item')
    consumed = consumed[0]
    need(identity(consumed.get('publication')), 'rendered content names an accepted publication')
    published = unique(trace, 'content-publication', id=consumed['publication'])
    need(
        published.get('root') == selected['root']
        and published.get('source') == consumed.get('source') == selected['source'],
        'published and rendered content belong to the wanted native input/model generation',
    )
    need(
        published.get('thread') == gui_thread(trace), 'content is accepted by the native GUI owner'
    )
    need(
        all(
            published.get(key) == consumed.get(key) == spec[key]
            for key in ('kind', 'mode', 'unit')
        ),
        'data-bearing and empty content follow the independent fixture expectation',
    )
    need(
        type(published.get('count')) is int
        and published['count'] >= 0
        and published['count'] == consumed.get('count')
        and isinstance(published.get('digest'), str)
        and re.fullmatch(r'[0-9a-f]{64}', published['digest']) is not None
        and published['digest'] == consumed.get('digest'),
        'the actual render consumer matches the accepted native payload count and digest',
    )
    need(
        published['count'] > 0 if spec['mode'] != 'empty' else published['count'] == 0,
        'only independently empty areas may complete without their data content',
    )
    if spec['mode'] == 'empty':
        need(
            published.get('reason') == consumed.get('reason') == spec['reason']
            and selected.get('object') == spec['object'],
            'an empty sidebar renders its actual declaration-defined note',
        )
    geometry = consumed.get('geometry')
    need(
        isinstance(geometry, list)
        and len(geometry) == 4
        and all(type(v) in {int, float} and math.isfinite(v) for v in geometry)
        and geometry[2] > 0
        and geometry[3] > 0,
        'the selected content has a nonempty native rendered rectangle',
    )
    need(
        consumed.get('witness') == 'native-render-consumer'
        and consumed.get('visible') is True
        and consumed.get('visual_count', 0) > 0
        and consumed.get('loading') == 0
        and consumed.get('pending') == 0,
        'the selected subtree is actually visible and all of its lazy/data work has settled',
    )
    if selected['key'] in {'stacked', 'map'}:
        patterns = unique(trace, 'input').get('patterns')
        need(
            type(patterns) is int
            and patterns > 0
            and published.get('loaded') == published.get('covered') == patterns
            and consumed.get('loaded') == consumed.get('covered') == patterns
            and published.get('failed') == consumed.get('failed') == 0,
            'scan completion covers every supplied dataset rather than a partly read/drawn view',
        )
    return published, consumed


def content_visit(trace, action, state, selected, rendered):
    need(
        identity(selected.get('root')) and identity(selected.get('visit')),
        'content identifies a native item and its shown-chain visit',
    )
    entered = unique(trace, 'content-shown', root=selected['root'], visit=selected['visit'])
    departed = [
        r
        for r in rows(trace, 'content-hidden')
        if r.get('root') == selected['root'] and r.get('visit') == selected['visit']
    ]
    need(
        len(departed) <= 1
        and entered.get('thread') == gui_thread(trace)
        and all(r.get('thread') == gui_thread(trace) for r in departed),
        'the content visit is a unique native GUI visibility interval',
    )
    need(
        action['t_ms'] <= selected['t_ms'] <= rendered['t_ms']
        and entered['t_ms'] <= selected['t_ms']
        and all(rendered['t_ms'] <= r['t_ms'] for r in departed),
        'content is rendered during its selected visit before actual departure',
    )
    fields = ['page'] + ({'main': ['tab'], 'sidebar': ['sidebar_tab']}.get(selected['area'], []))
    need(
        all(
            rendered['t_ms'] <= later['t_ms']
            for later in rows(trace, 'state')
            if later['t_ms'] > state['t_ms']
            and any(later.get(field) != state.get(field) for field in fields)
        ),
        'a later incompatible native selection cannot hide departure before content completion',
    )


def selected_content(trace, inventory, target, state, spec):
    action = unique(trace, 'action', request=state['request'])
    publication = unique(trace, 'transition-publication', transition=state['transition'])
    rendered = unique(trace, 'render', frame=publication['frame'])
    for area, key in required_content(target, state):
        expected = spec[state['page']][area][key]
        selected = unique(trace, 'content-selected', request=state['request'], area=area)
        source = state.get('content_sources', {}).get(area)
        binding = state.get('model_bindings', {}).get(expected['binding'])
        need(
            isinstance(source, dict)
            and isinstance(binding, dict)
            and all(source.get(field) == binding.get(field) for field in ('data', 'generation'))
            and source.get('input') == state['input']
            and identity(source.get('data'))
            and type(source.get('generation')) is int
            and source['generation'] >= 0
            and source.get('stage') == expected['stage'],
            'content uses the authoritative selected model, generation and prepared data stage',
        )
        button = next(
            (t['object'] for t in inventory[state['page']].get(area, []) if t['key'] == key), ''
        )
        need(
            selected.get('key') == key
            and selected.get('kind') == expected['kind']
            and selected.get('tab_object') == button
            and selected.get('source') == source
            and selected.get('thread') == gui_thread(trace)
            and selected.get('witness') == 'native-selected-content'
            and selected.get('tab_enabled') is True
            and selected.get('tab_visible') is True,
            'the actual selected enabled tab resolves its native content and current model source',
        )
        content_visit(trace, action, state, selected, rendered)
        published, consumed = consumed_payload(trace, selected, rendered, expected)
        need(
            published['t_ms'] <= publication['t_ms'] <= rendered['t_ms']
            and published['id'] in publication.get('content_publications', [])
            and consumed.get('visit') == selected['visit'],
            'completion includes accepted content and its consuming render in this visit',
        )


def tab_contents(trace, inventory):
    expectations = content_expectations(inventory)
    for target in tab_targets(inventory):
        action = unique(trace, 'action', name=target['name'])
        state = unique(trace, 'state', request=action['request'])
        selected_content(trace, inventory, target, state, expectations)
