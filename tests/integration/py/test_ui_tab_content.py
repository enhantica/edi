"""Reject canonical collisions and selected tabs whose content never completes."""

import operator
import shutil

import pytest

from tests.fixtures.ui_responsiveness.tab_inventory import declared_tabs
from tests.integration.py.test_ui_all_tabs import INVENTORY, append_literal, qml_copy, tab_trace
from tests.integration.py.ui_tab_content_controls import with_content
from tests.integration.py.ui_tab_witnesses import tab_actions


@pytest.mark.parametrize('alias', ['Project', 'PROJECTPage'])
def test_distinct_mounted_types_cannot_share_a_canonical_page(tmp_path, alias):
    root = qml_copy(tmp_path)
    qml = root / 'app/qml'
    append_literal(qml / 'Main.qml', 'contentArea', alias + ' {}')
    shutil.copyfile(
        qml / 'Pages/Project/ProjectPage.qml', qml / ('Pages/Project/' + alias + '.qml')
    )
    with pytest.raises(ValueError, match='canonical page'):
        declared_tabs(root)


@pytest.mark.parametrize('area', ['main', 'sidebar'])
def test_tab_case_normalization_cannot_hide_a_second_button(tmp_path, area):
    root = qml_copy(tmp_path)
    qml = root / 'app/qml/Components'
    path = qml / ('MainView.qml' if area == 'main' else 'WorkflowPage.qml')
    name = 'mainArea.tab.Pattern' if area == 'main' else 'sideBar.tab.Basic'
    append_literal(path, 'tabs', 'TabButton { objectName: "' + name + '" }')
    with pytest.raises(ValueError, match='Duplicate native tab'):
        declared_tabs(root)


def content_trace():
    trace = tab_trace()
    if not any(r['event'] == 'content-selected' for r in trace):
        trace = with_content(trace, INVENTORY)
    return sorted(trace, key=operator.itemgetter('t_ms'))


CASES = [
    ('analysis', 'main', key)
    for key in ['structure', 'pattern', 'meascalc', 'correlations', 'stacked', 'map', 'evolution']
]
CASES += [('analysis', 'sidebar', key) for key in ['basic', 'extras', 'text', 'settings']]
CASES += [('project', 'main', 'description'), ('report', 'main', 'report')]


@pytest.mark.parametrize(('page', 'area', 'key'), CASES)
@pytest.mark.parametrize(
    'escape',
    [
        'absent',
        'hidden',
        'stale',
        'loading',
        'after-departure',
        'after-completion',
        'wrong-consumer',
        'empty',
        'disabled',
    ],
)
def test_selection_and_generic_render_do_not_substitute_for_tab_content(page, area, key, escape):
    trace = content_trace()
    chosen = next(
        r
        for r in trace
        if r['event'] == 'content-selected'
        and r['area'] == area
        and r['key'] == key
        and next(s for s in trace if s['event'] == 'state' and s['request'] == r['request'])[
            'page'
        ]
        == page
    )
    state = next(r for r in trace if r['event'] == 'state' and r['request'] == chosen['request'])
    publication = next(
        r
        for r in trace
        if r['event'] == 'transition-publication' and r['transition'] == state['transition']
    )
    frame = next(r for r in trace if r['event'] == 'render' and r['frame'] == publication['frame'])
    consumed = next(r for r in frame['contents'] if r['root'] == chosen['root'])
    if escape == 'absent':
        frame['contents'].remove(consumed)
    elif escape == 'hidden':
        consumed['visible'] = False
    elif escape == 'stale':
        consumed['source']['generation'] = 0
    elif escape == 'loading':
        consumed['pending'] = 1
    elif escape in {'after-departure', 'after-completion'}:
        if escape == 'after-departure':
            departure = next(
                (
                    r
                    for r in trace
                    if r['event'] == 'content-hidden'
                    and r['root'] == chosen['root']
                    and r['visit'] == chosen['visit']
                ),
                None,
            )
            if departure is None:
                departure = {
                    'event': 'content-hidden',
                    'root': chosen['root'],
                    'visit': chosen['visit'],
                    'thread': 'gui',
                }
                trace.append(departure)
            departure['t_ms'] = frame['t_ms'] - 0.1
        else:
            frame['t_ms'] = next(r for r in trace if r['event'] == 'complete')['t_ms'] + 1
    elif escape == 'wrong-consumer':
        consumed['digest'] = '0' * 64
    elif escape == 'empty':
        consumed['mode'], consumed['count'] = 'empty', 0
    else:
        chosen['tab_enabled'] = False
    with pytest.raises(AssertionError):
        tab_actions(trace, INVENTORY)


def test_label_only_tab_trace_is_not_content_completion():
    trace = content_trace()
    trace = [r for r in trace if not r['event'].startswith('content-')]
    for frame in (r for r in trace if r['event'] == 'render'):
        frame.pop('contents', None)
    with pytest.raises(AssertionError):
        tab_actions(trace, INVENTORY)


@pytest.mark.parametrize('cached', [False, True], ids=['asynchronous', 'cached'])
def test_real_content_publication_and_consuming_render_complete_the_visit(cached):
    trace = content_trace()
    chosen = next(r for r in trace if r['event'] == 'content-selected' and r['key'] == 'map')
    state = next(r for r in trace if r['event'] == 'state' and r['request'] == chosen['request'])
    completion = next(
        r
        for r in trace
        if r['event'] == 'transition-publication' and r['transition'] == state['transition']
    )
    frame = next(r for r in trace if r['event'] == 'render' and r['frame'] == completion['frame'])
    payload = next(
        r for r in trace if r['event'] == 'content-publication' and r['root'] == chosen['root']
    )
    payload['t_ms'] = -0.5 if cached else state['t_ms'] + 1.5
    completion['t_ms'] = state['t_ms'] + 2
    frame['t_ms'] = state['t_ms'] + 3
    step = next(r for r in trace if r['event'] == 'step' and r['request'] == chosen['request'])
    step['t_ms'] = frame['t_ms'] + 0.1
    tab_actions(trace, INVENTORY)


def test_declaration_defined_empty_sidebar_still_completes_with_its_rendered_note():
    trace = content_trace()
    notes = [r for r in trace if r['event'] == 'content-publication' and r['mode'] == 'empty']
    assert notes and all(r['count'] == 0 and r['reason'] == 'no-groups' for r in notes), (
        'The scan fixture must retain genuinely empty sidebar areas without demanding data'
    )
    tab_actions(trace, INVENTORY)


def test_a_data_bearing_view_cannot_claim_the_empty_sidebar_exception():
    trace = content_trace()
    for row in trace:
        if row['event'] == 'content-publication' and row['kind'] == 'EvolutionChart':
            row.update(mode='empty', count=0, reason='no-groups')
        if row['event'] == 'render':
            for item in row['contents']:
                if item['kind'] == 'EvolutionChart':
                    item.update(mode='empty', count=0, reason='no-groups')
    with pytest.raises(AssertionError):
        tab_actions(trace, INVENTORY)


@pytest.mark.parametrize(
    'escape',
    [
        'missing-publication',
        'stale-publication',
        'wrong-model',
        'wrong-kind',
        'unwitnessed',
        'partial-scan',
        'zero-payload',
        'hidden-root',
        'late-publication',
        'stale-selection-and-publication',
    ],
)
def test_ready_labels_cannot_replace_a_complete_native_publication_consumer_join(escape):
    trace = content_trace()
    chosen = next(r for r in trace if r['event'] == 'content-selected' and r['key'] == 'map')
    payload = next(
        r for r in trace if r['event'] == 'content-publication' and r['root'] == chosen['root']
    )
    consumers = [
        item
        for row in trace
        if row['event'] == 'render'
        for item in row['contents']
        if item['publication'] == payload['id']
    ]
    if escape == 'missing-publication':
        trace.remove(payload)
    elif escape in {'stale-publication', 'wrong-model', 'stale-selection-and-publication'}:
        field, value = (
            ('generation', 0)
            if escape == 'stale-publication'
            else ('data', 'previous-selected-model')
        )
        for item in [payload, *consumers]:
            item['source'][field] = value
        if escape == 'stale-selection-and-publication':
            chosen['source'][field] = value
    elif escape in {'wrong-kind', 'partial-scan', 'zero-payload'}:
        field, value = {
            'wrong-kind': ('kind', 'DescriptionTab'),
            'partial-scan': ('covered', 2),
            'zero-payload': ('count', 0),
        }[escape]
        for item in [payload, *consumers]:
            item[field] = value
    elif escape == 'unwitnessed':
        for item in consumers:
            item['witness'] = 'driver-ready'
    elif escape == 'hidden-root':
        trace = [
            r
            for r in trace
            if not (
                r['event'] == 'content-shown'
                and r['root'] == chosen['root']
                and r['visit'] == chosen['visit']
            )
        ]
    else:
        payload['t_ms'] = chosen['t_ms'] + 1000
    with pytest.raises(AssertionError):
        tab_actions(trace, INVENTORY)
