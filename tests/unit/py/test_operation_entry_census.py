"""Every public operation has an explicit owner domain in the escape inventory."""

import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CENSUS = json.loads((ROOT / 'tests/fixtures/operation_boundaries/entry_points.json').read_text())


@pytest.mark.parametrize('name', sorted(CENSUS['classes']))
def test_public_entries_cannot_appear_outside_the_ownership_inventory(name):
    group = CENSUS['classes'][name]
    source = (ROOT / group['header']).read_text().split('class ' + name + ' :', 1)[1]
    actual = Counter(re.findall(r'Q_INVOKABLE\s+(?:[\w:<>,*&]+\s+)+(\w+)\s*\(', source))
    assert actual == Counter({
        entry: row['overloads'] for entry, row in group['entries'].items()
    }), 'Every public entry and same-name overload requires an explicit ownership disposition'
    for entry in group['entries'].values():
        assert entry['domain'], 'An enumerated public entry must name its ownership domain'
        if entry['proof']:
            assert (ROOT / entry['proof']).is_file(), (
                'Each behavioral proof pointer must resolve to a committed gate family'
            )
        else:
            assert entry['domain'] == 'read-only query', (
                'Only explicitly classified read-only queries have no behavioral actor pointer'
            )


@pytest.mark.parametrize('name', sorted(CENSUS['classes']))
def test_writable_properties_cannot_bypass_the_ownership_inventory(name):
    group = CENSUS['classes'][name]
    source = (ROOT / group['header']).read_text().split('class ' + name + ' :', 1)[1]
    actual = Counter(re.findall(r'Q_PROPERTY\([^)]*\bWRITE\s+(\w+)', source))
    assert actual == Counter({
        entry: row['bindings'] for entry, row in group['property_writers'].items()
    }), 'Every writable Qt property requires an explicit ownership disposition'
    for row in group['property_writers'].values():
        assert row['domain'] and (ROOT / row['proof']).is_file(), (
            'A writable property names its boundary family and resolves its gate pointer'
        )
