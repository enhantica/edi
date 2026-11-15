"""Keep exact current CLI pins separately attributed to their unchanged historical witnesses."""

import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[2]


def current_quantities(selected, historical, expected_bytes):
    receipt = json.loads((HERE / 'selector-current.json').read_text())
    assert hashlib.sha256(expected_bytes).hexdigest() == receipt['corpus_expected_sha256'], (
        'Current selector pins must first authenticate the unchanged complete engine corpus '
        'witness'
    )
    result = copy.deepcopy(historical)
    for name, pair in receipt['records'][selected]['quantity_changes'].items():
        assert (
            name in result
            and result[name]['kind'] == 'regression-pin'
            and result[name]['value'] == pair[0]
        ), 'A selector projection may replace only its exactly named historical regression value'
        bound = max(result[name]['tol_abs'] or 0, (result[name]['tol_rel'] or 0) * abs(pair[0]))
        assert abs(pair[1] - pair[0]) <= bound, (
            'A current exact regression pin must stay inside every unchanged historical corpus '
            'bound'
        )
        result[name]['value'] = pair[1]
    return result


def historical_ladder_record(current):
    row = json.loads((HERE / 'selector-current.json').read_text())['records']['ladder']
    assert current == row['record'], (
        'The current ladder must retain every byte of its separately captured terminal record'
    )
    old = (
        ROOT / 'tests/fixtures/c11_t35_descent_selector/default-record-no-elapsed.txt'
    ).read_text()
    assert hashlib.sha256(old.encode()).hexdigest() == row['historical_sha256'], (
        'The original ladder record must retain its complete historical captured identity'
    )
    before = dict(line.split('=', 1) for line in old.splitlines())
    after = dict(line.split('=', 1) for line in current.splitlines())
    changes = {name: [before[name], after[name]] for name in before if before[name] != after[name]}
    assert changes == row['changes'] and set(changes) <= {
        'stopping_rule',
        'last_shift_su',
        'unevaluable_trials',
        'terminal_unevaluable_trials',
    }, (
        'The historical ladder stage changes only truthful terminal metadata and the named '
        'restart counters'
    )
    restored = current
    for name, pair in changes.items():
        token = name + '=' + pair[1] + '\n'
        assert restored.count(token) == 1, (
            'Each terminal metadata projection changes one unique row'
        )
        restored = restored.replace(token, name + '=' + pair[0] + '\n', 1)
    assert restored == old, (
        'Reversing terminal metadata must retain every original record byte and its order'
    )
    return restored
