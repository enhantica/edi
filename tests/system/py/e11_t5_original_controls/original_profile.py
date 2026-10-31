"""Closed original warning premises; inspect existing returned facts, never drive Qt."""

from collections import Counter

MODEL = {
    'id': 'gpt-6.1-sol',
    'model': 'gpt-6.1-sol',
    'displayName': 'Independent offline model',
    'description': 'Protocol fixture',
    'hidden': False,
    'isDefault': True,
    'defaultReasoningEffort': 'medium',
    'supportedReasoningEfforts': [{'reasoningEffort': 'medium', 'description': 'Fixture'}],
}
CHOICE_NAMES = [
    'assistant.choice.effort.' + token + suffix
    for token in ['default', 'value.medium']
    for suffix in ['', '.row', '.label']
]


def require_peer(peer, case, folder, final_text):
    """The bound original peer must own the exact source-declared model and rows."""
    expected = {
        'turns': case['turns'],
        'trace': str(folder / 'wire.jsonl'),
        'final_text': final_text,
    }
    if case['archives'] or case['function'].startswith('test_original_browser_'):
        expected['session_fixture'] = {'threads': [], 'page_size': 12}
    assert peer == expected, 'Undeclared peer/model/session population cannot inherit counts'


def require_census(ui, case):
    """Off-window retained delegates count too; no global first-match or filtering."""
    for key in ['alive', 'singleton_identity', 'engine_parent', 'cpp_ownership']:
        assert ui[key] is True, key
    assert ui['available_efforts'] == ['medium'], 'Original Auto plus the sole native effort'
    names = Counter(row['name'] for row in ui['controls'])
    choices = Counter({
        name: count for name, count in names.items() if name.startswith('assistant.choice.effort.')
    })
    archives = Counter({
        name: count
        for name, count in names.items()
        if name.startswith('assistant.session.archive.')
    })
    assert choices == Counter(CHOICE_NAMES), 'Exact two retained original effort delegates'
    expected_archives = ['assistant.session.archive.' + str(i) for i in range(case['archives'])]
    assert archives == Counter(expected_archives), 'Exact source-declared actual session rows'


def require_model_wire(requests, responses):
    """Join genuine model/list IDs, including all replies, without guessing a data shape."""
    identifiers = [row['id'] for row in requests if row.get('method') == 'model/list']
    assert identifiers, 'The actual peer must have supplied the original model profile'
    expected = {'data': [MODEL], 'nextCursor': None}
    for identifier in identifiers:
        replies = [row for row in responses if row.get('id') == identifier]
        assert len(replies) == 1, 'Every actual model request has exactly one genuine reply'
        assert replies[0]['result'] == expected, 'Changed model data cannot retain old counts'
