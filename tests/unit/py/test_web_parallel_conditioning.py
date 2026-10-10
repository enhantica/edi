"""Covariance diagonal sensitivity held to closed-form positive definite matrices."""

import copy
import hashlib
import json
import math

import pytest

from tests.fixtures.web_parallel import numeric


def reference(rho=1 - 2**-28, sigma=1.0):
    expected = {'phase.edi': [['_scale.value', f'2.125({sigma})']]}
    d = 1 - rho * rho
    conditioning = {
        'scientific_sha256': hashlib.sha256(
            json.dumps(expected, sort_keys=True).encode()
        ).hexdigest(),
        'n_data': 8,
        'labels': ['a', 'b'],
        'scaled_normal': [[1.0, rho], [rho, 1.0]],
        'scaled_inverse_normal': [[1 / d, -rho / d], [-rho / d, 1 / d]],
        'bindings': [['phase.edi', 0, 1, 0]],
    }
    return expected, conditioning


@pytest.mark.parametrize('rho', [0.0, 0.5, 1 - 2**-28])
def test_covariance_roundoff_bound_matches_closed_form_diagonal_sensitivity(rho):
    expected, conditioning = reference(rho)
    u = 2**-53

    def gamma(k):
        return k * u / (1 - k * u)

    delta = 4 * (gamma(12) + gamma(2))
    d = 1 - rho * rho
    norm = (1 + abs(rho)) / d
    q = delta * (1 + rho * rho) / d / (1 - delta * norm)
    bound = max(5e-9, q / (1 + math.sqrt(1 - q)))
    actual = numeric.uncertainty_tolerances(expected, conditioning)
    assert math.isclose(actual['phase.edi', 0, 1], bound, rel_tol=1e-14), (
        'Covariance uncertainty bound must follow the independent two-by-two inverse derivation'
    )


@pytest.mark.parametrize('scale', [0.125, 2.5, 1e6])
def test_conditioning_bound_scales_with_physical_uncertainty_units(scale):
    expected, conditioning = reference(sigma=scale)
    unit, unit_conditioning = reference()
    scaled = numeric.uncertainty_tolerances(expected, conditioning)['phase.edi', 0, 1]
    baseline = numeric.uncertainty_tolerances(unit, unit_conditioning)['phase.edi', 0, 1]
    assert math.isclose(scaled, scale * baseline, rel_tol=1e-14), (
        'A covariance bound must preserve physical uncertainty units at nontrivial scales'
    )


@pytest.mark.parametrize('direction', [-1, 1])
def test_conditioned_comparison_accepts_inside_and_refuses_outside_derived_bound(direction):
    expected, conditioning = reference()
    bound = numeric.uncertainty_tolerances(expected, conditioning)['phase.edi', 0, 1]
    actual = {'phase.edi': [['_scale.value', f'2.125({1 + direction * bound / 2:.17f})']]}
    assert numeric.compare_scientific(actual, expected, conditioning=conditioning), (
        'Conditioned uncertainty parity must accept a quantity inside the independent bound'
    )
    actual['phase.edi'][0][1] = f'2.125({1 + direction * bound * 2:.17f})'
    with pytest.raises(ValueError, match='uncertainty'):
        numeric.compare_scientific(actual, expected, conditioning=conditioning)


def test_conditioning_never_changes_parameter_values_or_presence():
    expected, conditioning = reference()
    for token in ['2.12501(1.0)', '2.125', '2.125()', '2.125(0)']:
        with pytest.raises(ValueError, match=r'parameter|uncertainty'):
            numeric.compare_scientific(
                {'phase.edi': [['_scale.value', token]]}, expected, conditioning=conditioning
            )


@pytest.mark.parametrize(
    'damage', ['hash', 'shape', 'nan', 'singular', 'negative', 'indefinite', 'binding', 'missing']
)
def test_invalid_native_conditioning_refuses_instead_of_relaxing_the_gate(damage):
    expected, conditioning = reference()
    if damage == 'hash':
        conditioning['scientific_sha256'] = '0' * 64
    elif damage == 'shape':
        conditioning['scaled_inverse_normal'][0].pop()
    elif damage == 'nan':
        conditioning['scaled_inverse_normal'][0][0] = float('nan')
    elif damage == 'singular':
        conditioning['scaled_inverse_normal'] = [[1e20, -1e20], [-1e20, 1e20]]
    elif damage == 'negative':
        conditioning['scaled_inverse_normal'][0][0] *= -1
    elif damage == 'indefinite':
        conditioning['labels'] = ['a', 'b', 'c']
        matrix = [[(1 if i == j else 0) - 2 / 3 for j in range(3)] for i in range(3)]
        conditioning['scaled_normal'] = matrix
        conditioning['scaled_inverse_normal'] = matrix
    elif damage == 'binding':
        conditioning['bindings'][0][3] = 2
    else:
        conditioning['bindings'] = []
    with pytest.raises(ValueError, match='conditioning'):
        numeric.compare_scientific(expected, expected, conditioning=conditioning)


def test_derived_bound_is_independent_of_observed_browser_operands():
    expected, conditioning = reference()
    before = numeric.uncertainty_tolerances(expected, conditioning)
    bad = copy.deepcopy(expected)
    bad['phase.edi'][0][1] = '2.125(1000.0)'
    with pytest.raises(ValueError, match='uncertainty'):
        numeric.compare_scientific(bad, expected, conditioning=conditioning)
    assert numeric.uncertainty_tolerances(expected, conditioning) == before, (
        'Observed browser gaps must never participate in the conditioning tolerance derivation'
    )
