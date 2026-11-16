"""Independent CLI metadata invariants and declared model projection (ADRs 0057/0123/0124)."""

import os
from decimal import Decimal


def check_persisted_iterations(actual, producing):
    assert Decimal(actual['_fit_result.iterations']) == Decimal(producing['iterations']), (
        'The saved iteration count must echo its producing fit rather than a historical trajectory'
    )


def selected_parameter_count(row):
    names = row['parameter_names']
    assert len(names) == row['n_parameters'], (
        'The retained external count must agree with its named slots'
    )
    # ADR-0123 retires only ABSCOR2; every other independent projected slot remains.
    return sum(not name.endswith('.abscor2') for name in names)


def pin_declared_descent(path, expected):
    text = path.read_text()
    tokens = [line.split() for line in text.splitlines() if line.startswith('_minimizer.descent ')]
    if tokens:
        assert len(tokens) == 1, 'A CLI fixture must have one explicit descent declaration'
        assert tokens[0][1] == expected, (
            'An explicitly declared CLI descent must match its historical fixture'
        )
    else:
        # ADR-0125 changed the default; this fixture compares an explicitly captured algorithm.
        path.write_text(text + '\n_minimizer.descent ' + expected + '\n')


def cli_environment():
    # Match the single-thread context used by the visible historical capture producer.
    return {**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}
