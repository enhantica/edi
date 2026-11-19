"""Bind every source-declared tab to native state and its actual rendered frame."""

from tests.fixtures.ui_responsiveness.tab_inventory import SCENARIO, tab_targets
from tests.integration.py.ui_causal_witnesses import actions, gui_thread, need, unique


def tab_actions(trace, inventory):
    observed = unique(trace, 'tab-inventory')
    owner = gui_thread(trace)
    need(
        observed.get('witness') == 'qml-tab-bars' and observed.get('thread') == owner,
        'tab inventory is sampled from actual native GUI tab bars',
    )
    need(
        observed.get('pages') == inventory,
        'native page and tab inventory equals every source declaration, including empty pages',
    )
    targets = tab_targets(inventory)
    for state in (r for r in trace if r['event'] == 'state'):
        need(
            all(field in state for field in ('tab', 'sidebar_tab', 'selected_object')),
            'native tab state explicitly samples both tab areas and the selected object',
        )
    actions(trace, SCENARIO, [target['name'] for target in targets])
    for target in targets:
        action = unique(trace, 'action', name=target['name'])
        state = unique(trace, 'state', request=action['request'])
        need(
            action.get('thread') == state.get('thread') == owner,
            'tab issuance and selected state belong to the native GUI owner',
        )
        need(state.get('page') == target['page'], 'tab selection reaches its requested page')
        for area, field in [('main', 'tab'), ('sidebar', 'sidebar_tab')]:
            available = {tab['key'] for tab in inventory[target['page']][area]}
            need(
                state.get(field) in (available or {'', None}),
                'selected main and sidebar states belong to that page declaration',
            )
            if area == target['area']:
                need(
                    state[field] == target['key'],
                    'every requested main or sidebar tab is actually selected',
                )
                need(
                    state.get('selected_object') == target['object'],
                    'the selected tab is the declared native button rather than a label',
                )
