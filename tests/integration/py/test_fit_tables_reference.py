"""The table reference follows the textbook R definitions on frozen crysta curves."""

import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3] / 'tests/fixtures/fit_tables'
REFERENCE = json.loads((ROOT / 'reference.json').read_text())


def curves(name):
    text = (ROOT / 'five/experiments' / f'{name}.edi').read_text()
    block = next(part for part in text.split('loop_\n')[1:] if part.startswith('_data.'))
    lines = block.splitlines()
    columns = []
    while lines and lines[0].startswith('_'):
        columns.append(lines.pop(0))
    rows = [dict(zip(columns, line.split(), strict=True)) for line in lines if line.strip()]
    return [row for row in rows if row['_data.calc_status'] == 'incl']


def independent_factors(rows, parameters):
    residual = [
        float(row['_data.intensity_meas']) - float(row['_data.intensity_calc']) for row in rows
    ]
    y = [float(row['_data.intensity_meas']) for row in rows]
    b = [float(row['_data.intensity_bkg']) for row in rows]
    weights = [1 / float(row['_data.intensity_meas_su']) ** 2 for row in rows]
    numerator = math.fsum(w * r * r for w, r in zip(weights, residual, strict=True))
    denominator = math.fsum(w * a * a for w, a in zip(weights, y, strict=True))
    return [
        math.fsum(abs(r) for r in residual) / math.fsum(abs(a) for a in y),
        math.sqrt(numerator / denominator),
        math.sqrt((len(rows) - parameters) / denominator),
        math.fsum(abs(r) for r in residual)
        / math.fsum(abs(a - c) for a, c in zip(y, b, strict=True)),
        math.sqrt(
            numerator / math.fsum(w * (a - c) ** 2 for w, a, c in zip(weights, y, b, strict=True))
        ),
    ]


@pytest.mark.parametrize('name', [row['name'] for row in REFERENCE['banks']] + ['All datasets'])
def test_saved_curve_factors_equal_the_table_reference(name):
    if name == 'All datasets':
        rows = [row for bank in REFERENCE['banks'] for row in curves(bank['name'])]
        expected = REFERENCE['global_values']
    else:
        rows = curves(name)
        expected = next(bank['values'] for bank in REFERENCE['banks'] if bank['name'] == name)
    assert independent_factors(rows, REFERENCE['parameters']) == pytest.approx(
        expected, rel=2e-13
    ), (
        'Agreement-table expectations come from the saved measured, '
        'calculated and background curves'
    )


def test_ncaf_bank_one_retains_the_external_brief_values():
    actual = independent_factors(curves('wish_1_10'), REFERENCE['parameters'])
    assert [value * 100 for value in actual] == pytest.approx(
        [12.03, 4.66, 4.45, 29.41, 15.34], abs=0.02
    ), (
        'The NCAF bank-one reference agrees with the brief within its '
        'displayed precision and fit variation'
    )
