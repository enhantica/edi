"""Independent decimal bins and calculation round trips at the predicted written state."""

from decimal import Decimal

import numpy as np

from tests.fixtures.saved_spelling.reference import VALUE_SU, saved_pair, spelling


def half_step(token):
    match = VALUE_SU.fullmatch(token.encode())
    assert match, 'A written-precision bound requires one complete value/uncertainty token'
    value, bracket = (part.decode() if part else '' for part in match.groups())
    if not bracket or not Decimal(bracket):
        return Decimal(0)
    step = Decimal(1).scaleb(Decimal(value).as_tuple().exponent)
    if '.' not in bracket and 'e' not in bracket.lower():
        digits = int(bracket)
        while digits > 19 and digits % 10 == 0:
            digits //= 10
            step *= 10
        assert 2 <= digits <= 19, (
            'The default IUCr integer bracket must encode the declared two-to-nineteen digits'
        )
    return step / 2


def parameter_state(project):
    return [
        (p.name, p.value, p.uncertainty, p.free, p.user_constrained) for p in project.parameters
    ]


def written_pair(state):
    _name, value, su, free, dependent = state
    if (free or dependent) and su is not None and su > 0:
        result = saved_pair(value, su)
        radius = half_step(spelling(value, su))
        assert abs(Decimal(str(result[0])) - Decimal(str(value))) <= radius, (
            'The independently predicted written value must remain within half its last digit'
        )
        return result
    return value, su


def assert_written_parameters(project, before):
    parameters = list(project.parameters)
    assert len(parameters) == len(before), (
        'A written-state calculation must retain the entire original parameter population'
    )
    for parameter, state in zip(parameters, before, strict=True):
        name, _value, su, free, dependent = state
        assert parameter.name == name and parameter.free is free, (
            'Saving and reopening must retain every parameter identity, order and free flag'
        )
        expected_value, expected_su = written_pair(state)
        assert parameter.value == expected_value, (
            'Every reopened value must match the independent IUCr or fixed-value prediction'
        )
        if (free or dependent) and su is not None and su > 0:
            assert parameter.uncertainty == expected_su, (
                'Every written fitted uncertainty must equal the independent upward-rounded digits'
            )


def predicted_patterns(reference, before, unrounded):
    parameters = list(reference.parameters)
    assert [p.name for p in parameters] == [state[0] for state in before], (
        'The independent written-state vehicle must have the original complete parameter order'
    )
    for parameter, state in zip(parameters, before, strict=True):
        parameter.value = state[1]
        if parameter.free is not state[3]:
            parameter.free = state[3]
        parameter.uncertainty = state[2]
    reference.analysis.calculate()
    for experiment in reference.experiments:
        np.testing.assert_array_equal(
            np.asarray(experiment.data.intensity_calc),
            unrounded[experiment.name],
            err_msg='A fresh raw-state calculation must reproduce every live fit column',
        )
    for parameter, state in zip(parameters, before, strict=True):
        parameter.value, parameter.uncertainty = written_pair(state)
    reference.analysis.calculate()
    return {
        experiment.name: np.asarray(experiment.data.intensity_calc).copy()
        for experiment in reference.experiments
    }
