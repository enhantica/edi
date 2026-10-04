"""Independent token witnesses for the source-text app oracle generator."""

import runpy
from pathlib import Path

NUMERIC = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'fixtures/e04_t1/generate.py'))[
    'numeric'
]


def test_app_oracle_preserves_symbolic_and_incomplete_numeric_tokens():
    for token in ('e', 'E', '+', '-', '.', '1e', '1e+', '1.2.3'):
        assert NUMERIC(token) == token, (
            'I19 : source-text oracle preserves Wyckoff letters and nonnumeric tokens'
        )


def test_app_oracle_retains_number_free_flag_and_uncertainty():
    witnesses = {
        '-1.25e+2()': {'value': -125.0, 'free': True, 'uncertainty': None},
        '1.230(4)': {'value': 1.23, 'free': True, 'uncertainty': 0.004},
        '1.230e2(4)': {'value': 123.0, 'free': True, 'uncertainty': 0.4},
        '+.5': {'value': 0.5, 'free': False, 'uncertainty': 0.0},
        '5.': {'value': 5.0, 'free': False, 'uncertainty': 0.0},
    }
    for token, expected in witnesses.items():
        assert NUMERIC(token) == expected, (
            'I19 : independent decimal/exponent witnesses retain value and free uncertainty'
        )
