"""Independent literal carry and passthrough controls for the FIRST shared IUCr reference."""

import math
import re
from decimal import ROUND_HALF_UP, Decimal

import pytest

from tests.fixtures.project_save.reference import expected_pair, saved_triplet
from tests.fixtures.report_units.iucr_reference import rounded_pair, rounded_record, rounded_token

# Independently authored decimal literals. None is copied from fitted output.
# Each pair and token follows the same last place after upward SU carry.
CARRY_CASES = [
    (12.345, 0.0991, (12.35, 0.1), (12.35, 0.1), b'12.35(10)', b'12.35(10)'),
    (-12.345, 0.0991, (-12.35, 0.1), (-12.35, 0.1), b'-12.35(10)', b'-12.35(10)'),
    (123.45, 0.991, (123.5, 1.0), (123.5, 1.0), b'123.5(10)', b'123.5(10)'),
    (-123.45, 0.991, (-123.5, 1.0), (-123.5, 1.0), b'-123.5(10)', b'-123.5(10)'),
    (1234.5, 9.91, (1235.0, 10.0), (1235.0, 10.0), b'1235(10)', b'1235(10)'),
    (-1234.5, 9.91, (-1235.0, 10.0), (-1235.0, 10.0), b'-1235(10)', b'-1235(10)'),
    (0.12345, 0.000991, (0.1235, 0.001), (0.1235, 0.001), b'0.1235(10)', b'0.1235(10)'),
    (-0.12345, 0.000991, (-0.1235, 0.001), (-0.1235, 0.001), b'-0.1235(10)', b'-0.1235(10)'),
    (123450.0, 991.0, (123500.0, 1000.0), (123500.0, 1000.0), b'123500(1000)', b'123500(1000)'),
    (
        -123450.0,
        991.0,
        (-123500.0, 1000.0),
        (-123500.0, 1000.0),
        b'-123500(1000)',
        b'-123500(1000)',
    ),
    (12.344, 0.099, (12.34, 0.1), (12.344, 0.099), b'12.34(10)', b'12.344(99)'),
    (12.345, 0.1, (12.35, 0.1), (12.35, 0.1), b'12.35(10)', b'12.35(10)'),
    (12.345, 0.1001, (12.35, 0.11), (12.35, 0.11), b'12.35(11)', b'12.35(11)'),
    (12.345, 0.0191, (12.35, 0.02), (12.345, 0.02), b'12.35(2)', b'12.345(20)'),
    (0.0, 0.0991, (0.0, 0.1), (0.0, 0.1), b'0.00(10)', b'0.00(10)'),
]

PARAMETER_TOKEN = re.compile(
    rb'([-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?)\((\d+(?:\.\d*)?(?:[eE][-+]?\d+)?)\)'
)


def test_quantum_exponent_is_distinct_from_its_numeric_value():
    # The operand's exponent, not equality or magnitude, selects the last place.
    assert Decimal('1.0') == Decimal(1), (
        'Required: quantum exponent is distinct from its numeric value.'
    )
    assert Decimal('12.5').quantize(Decimal('1.0'), rounding=ROUND_HALF_UP) == Decimal('12.5'), (
        'Required: quantum exponent is distinct from its numeric value.'
    )
    assert Decimal('12.5').quantize(Decimal(1), rounding=ROUND_HALF_UP) == Decimal(13), (
        'Required: quantum exponent is distinct from its numeric value.'
    )


@pytest.mark.parametrize('case', CARRY_CASES)
@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
def test_decade_carry_direct_pair_keeps_the_literal_su_last_place(case, rule):
    value, su = case[:2]
    expected = case[2 if rule == 'iucr_19' else 3]
    assert rounded_pair(value, su, rule) == expected, (
        'The direct pair must round at the carried last place before token re-quantization'
    )
    assert rounded_pair(*expected, rule) == expected, (
        'The independently rounded pair remains unchanged on its next observation'
    )


@pytest.mark.parametrize('value', [-1.23456789, 1.23456789, -0.0, 0.0])
@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
def test_pair_absent_and_zero_uncertainties_keep_the_original_passthrough(value, rule):
    assert rounded_pair(value, None, rule) == (value, None), (
        'Required: pair absent and zero uncertainties keep the original passthrough.'
    )
    for zero in (0.0, -0.0):
        actual = rounded_pair(value, zero, rule)
        assert actual == (value, zero), (
            'Required: pair absent and zero uncertainties keep the original passthrough.'
        )
        assert math.copysign(1, actual[0]) == math.copysign(1, value), (
            'Required: pair absent and zero uncertainties keep the original passthrough.'
        )
        assert math.copysign(1, actual[1]) == math.copysign(1, zero), (
            'Required: pair absent and zero uncertainties keep the original passthrough.'
        )
    assert rounded_pair(-0.0001, 0.02, rule) == (-0.0001, 0.02), (
        'The separate nonzero-value fallback must remain unchanged'
    )


@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
def test_record_absent_and_zero_markers_remain_literal(rule):
    source = b'_background.coef -1.23456789()\n_background.intensity 1.23456789(0)\n'
    assert rounded_record(source, rule) == source, (
        'Required: record absent and zero markers remain literal.'
    )


@pytest.mark.parametrize('case', CARRY_CASES)
@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
def test_token_record_and_triplet_carry_agree_with_independent_literals(case, rule):
    value, su = case[:2]
    expected = case[2 if rule == 'iucr_19' else 3]
    token = case[4 if rule == 'iucr_19' else 5]
    original = f'{value}({su})'.encode()
    match = PARAMETER_TOKEN.fullmatch(original)
    assert match is not None, (
        'Required: token record and triplet carry agree with independent literals.'
    )
    assert expected_pair(value, su, rule) == expected, (
        'Required: token record and triplet carry agree with independent literals.'
    )
    assert saved_triplet(value, su, True, rule) == (*expected, True), (
        'Required: token record and triplet carry agree with independent literals.'
    )
    assert saved_triplet(*expected, True, rule) == (*expected, True), (
        'Required: token record and triplet carry agree with independent literals.'
    )
    assert rounded_token(match, rule) == token, (
        'Required: token record and triplet carry agree with independent literals.'
    )
    repeated = PARAMETER_TOKEN.fullmatch(token)
    assert repeated is not None, (
        'Required: token record and triplet carry agree with independent literals.'
    )
    assert rounded_token(repeated, rule) == token, (
        'Required: token record and triplet carry agree with independent literals.'
    )
    source = (
        b'data_control\n_metadata.title "opaque 12.345(0.0991)"\n_background.coef '
        + original
        + b'\n'
    )
    source += (
        b'loop_\n_background.id\n_background.order\n_background.coef\nrow0 0 ' + original + b'\n'
    )
    wanted = (
        b'data_control\n_metadata.title "opaque 12.345(0.0991)"\n_background.coef ' + token + b'\n'
    )
    wanted += (
        b'loop_\n_background.id\n_background.order\n_background.coef\nrow0 0 ' + token + b'\n'
    )
    assert rounded_record(source, rule) == wanted, (
        'Required: token record and triplet carry agree with independent literals.'
    )
    assert rounded_record(wanted, rule) == wanted, (
        'Required: token record and triplet carry agree with independent literals.'
    )


@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
@pytest.mark.parametrize(('value', 'written'), [(1.23456789, 1.23457), (-1.23456789, -1.23457)])
def test_persisted_scalar_fixed_absent_and_zero_branches_remain_exact(rule, value, written):
    for su in (None, 0.0):
        assert saved_triplet(value, su, False, rule) == (written, 0.0, False), (
            'Required: persisted scalar fixed absent and zero branches remain exact.'
        )
    assert saved_triplet(value, None, True, rule) == (
        written,
        None,
        True,
    ), 'Required: persisted scalar fixed absent and zero branches remain exact.'
    assert saved_triplet(value, 0.0, True, rule) == (written, 0.0, True), (
        'Required: persisted scalar fixed absent and zero branches remain exact.'
    )
