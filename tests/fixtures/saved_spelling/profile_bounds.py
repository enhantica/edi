"""Triangle-inequality bounds for polynomial-background quantization and profile ratios."""

import numpy as np

from tests.fixtures.saved_spelling.fit_state import half_step
from tests.fixtures.saved_spelling.reference import decode


def polynomial_values(tokens, grid, *, constrained):
    values = [decode(token)[0] if '(' in token else float(token) for token in tokens]
    if constrained:
        values[2] = values[0] - values[1]
    t = np.asarray(grid) / 40 - 1
    return values[0] + values[1] * t + values[2] * t**2


def polynomial_error(tokens, grid, *, constrained):
    steps = [float(half_step(token)) if '(' in token else 0.0 for token in tokens]
    assert len(steps) == 3, (
        'The authored profile vehicle has exactly three background coefficients'
    )
    if constrained:
        # c=a-b can be reapplied after reading its independently rounded token.
        steps[2] = max(steps[2], steps[0] + steps[1])
    t = np.asarray(grid) / 40 - 1
    return steps[0] + abs(t) * steps[1] + t**2 * steps[2]


def ratio_error(ratio, denominator, delta):
    assert denominator > delta, (
        'A rounding envelope must leave the independently computed metric denominator positive'
    )
    return delta * (1 + ratio) / (denominator - delta)


def factor_errors(observed, calculated, sigma, background, radius, expected):
    residual = observed - calculated
    corrected = observed - background
    absolute = float(np.sum(radius))
    weighted = float(np.linalg.norm(radius / sigma))
    return {
        'prof_r_factor': absolute / np.sum(abs(observed)),
        'prof_wr_factor': weighted / np.linalg.norm(observed / sigma),
        'prof_wr_expected': 0.0,
        'prof_cr_factor': ratio_error(
            expected['prof_cr_factor'], np.sum(abs(corrected)), absolute
        ),
        'prof_cwr_factor': ratio_error(
            expected['prof_cwr_factor'], np.linalg.norm(corrected / sigma), weighted
        ),
        'chi_square': np.sum((2 * abs(residual) * radius + radius**2) / sigma**2),
    }


def assert_factor_rounding(actual, expected, errors):
    for field in expected:
        assert abs(actual[field] - expected[field]) <= errors[field] + 1e-12, (
            'Every profile metric requires its independent triangle-inequality rounding bound: '
            + field
        )


def phase_errors(observed, calculated, radius):
    bragg = np.sum(abs(observed - calculated)) / np.sum(abs(observed))
    amplitudes = np.sqrt(observed / calculated)
    amplitude = np.sum(abs(amplitudes - 1)) / np.sum(amplitudes)
    spread = np.maximum(
        np.sqrt((observed + radius) / calculated) - amplitudes,
        amplitudes - np.sqrt(np.maximum(0, observed - radius) / calculated),
    )
    return (
        ratio_error(bragg, np.sum(abs(observed)), np.sum(radius)),
        ratio_error(amplitude, np.sum(amplitudes), np.sum(spread)),
    )
