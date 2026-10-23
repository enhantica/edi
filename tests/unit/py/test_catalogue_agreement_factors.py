"""Exercise the comparison calculator against independently evaluated sums."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads((ROOT / 'tests/fixtures/example_catalogue/agreement-factors.json').read_text())


def calculator():
    path = ROOT / 'tools/comparison/fit_quality.py'
    assert path.is_file(), 'The comparison table needs its reproducible arithmetic implementation'
    spec = importlib.util.spec_from_file_location('catalogue_fit_quality', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, 'agreement_factors'), (
        'The comparison calculator must expose its documented agreement-factor seam'
    )
    return module.agreement_factors


@pytest.mark.parametrize(('count', 'expected'), [(1, 'single'), (2, 'pooled')])
def test_weighted_factors_pool_sums_and_use_only_the_common_point_mask(count, expected):
    actual = calculator()(DATA['banks'][:count], DATA['n_free'])
    for field, value in DATA[expected].items():
        assert actual[field] == pytest.approx(value, rel=1e-12, abs=1e-12), (
            'Agreement factors must use the closed-form pooled sums and masked degrees of freedom'
        )


@pytest.mark.parametrize(
    'damage',
    [
        'zero-sigma',
        'negative-sigma',
        'nan',
        'infinity',
        'ragged',
        'empty',
        'no-dof',
        'negative-free',
    ],
)
def test_invalid_agreement_factor_inputs_fail_closed(damage):
    banks = copy.deepcopy(DATA['banks'][:1])
    n_free = 1
    if damage == 'zero-sigma':
        banks[0]['sigma'][0] = 0
    elif damage == 'negative-sigma':
        banks[0]['sigma'][0] = -1
    elif damage == 'nan':
        banks[0]['calculated'][0] = float('nan')
    elif damage == 'infinity':
        banks[0]['observed'][0] = float('inf')
    elif damage == 'ragged':
        banks[0]['sigma'].pop()
    elif damage == 'empty':
        banks[0]['included'] = [False] * 5
    elif damage == 'no-dof':
        n_free = 4
    else:
        n_free = -1
    function = calculator()
    with pytest.raises(ValueError, match=r'.'):
        function(banks, n_free)
