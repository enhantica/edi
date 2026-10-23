"""Saved parameter comparison against decimal units and native conformance bounds."""

import pytest

from tests.fixtures.web_parallel.numeric import compare_scientific


@pytest.mark.parametrize(
    ('actual', 'expected'),
    [
        ('1.234(7)', '1.234(.007)'),
        ('1.2340(70)', '1.234(7)'),
        ('1.0(1)', '1.00(10)'),
        ('-.5(3)', '-0.5(0.3)'),
        ('18.(1)', '18.0(1.0)'),
        # Native uncertainty conformance: max(5e-9 * abs(reference), 5e-10).
        ('2.125(0.250000001)', '2.125(0.25)'),
        ('2.125(.0000000004)', '2.125(.000000000001)'),
        # Values retain the tighter native capture bounds, independently of sigma.
        ('2.125000001(.25)', '2.125(.25)'),
        ('2.125()', '2.125000001()'),
        ('2.125e3', '2125.0'),
    ],
)
def test_saved_parameter_components_use_numeric_units_and_native_bounds(actual, expected):
    assert compare_scientific(
        {'experiment.edi': [['_scale.value', actual]]},
        {'experiment.edi': [['_scale.value', expected]]},
    ), 'Saved parameter components must agree in physical units and native conformance bounds'


@pytest.mark.parametrize(
    ('actual', 'expected'),
    [
        ('2.12501(.25)', '2.125(.25)'),
        ('1.0(1)', '1.00(1)'),
        ('2.125(.250000002)', '2.125(.25)'),
        ('2.125(.000000002)', '2.125(.000000000001)'),
        ('2.125', '2.125(.25)'),
        ('2.125()', '2.125(0)'),
        ('2.125()', '2.125'),
        ('2.125(nan)', '2.125(nan)'),
        ('2.125(inf)', '2.125(inf)'),
        ('2.125(-0.25)', '2.125(-0.25)'),
        ('2.125(.25)junk', '2.125(.25)junk'),
        ('nan', 'nan'),
        ('inf', 'inf'),
        ('1.2e3(4)', '1.2e3(4)'),
        ('2.125(.25)', 'not-a-number'),
    ],
)
def test_saved_parameter_refuses_changed_components_and_invalid_operands(actual, expected):
    with pytest.raises(ValueError, match=r'uncertainty|parameter|operand|token'):
        compare_scientific(
            {'experiment.edi': [['_scale.value', actual]]},
            {'experiment.edi': [['_scale.value', expected]]},
        )


@pytest.mark.parametrize(
    'actual',
    [
        {},
        {'experiment.edi': []},
        {'experiment.edi': [['_scale.value']]},
        {'experiment.edi': [['_changed.value', '2.125(.25)']]},
    ],
)
def test_saved_numeric_comparison_retains_document_row_and_token_inventory(actual):
    with pytest.raises(ValueError, match=r'inventory|shape|token'):
        compare_scientific(actual, {'experiment.edi': [['_scale.value', '2.125(.25)']]})


@pytest.mark.parametrize(
    ('actual', 'expected'),
    [
        ('1.542(16)', '1.54249(0.01532)'),
        ('2.164(5)', '2.16352(0.00481)'),
        ('0.12(2)', '0.1234(0.0196)'),
        ('1.23(10)', '1.234(0.0991)'),
        ('-1.24(2)', '-1.235(0.02)'),
        ('54900(1300)', '54912(1234.)'),
        ('0.000(13)', '0(0.0123)'),
        ('-0.0001(0.02)', '-0.0001(0.02)'),
        ('3.9(100000000000000000000.)', '3.88(1' + '0' * 20 + '.)'),
    ],
)
def test_saved_iucr_parameters_follow_independent_decimal_rule(actual, expected):
    # ADR-0092's worked examples and decimal carry/tie cases, not writer output.
    assert compare_scientific(
        {'experiment.edi': [['_scale.value', actual]]},
        {'experiment.edi': [['_scale.value', expected]]},
        saved_iucr=True,
    ), 'Saved fitted values and uncertainties must follow the native capture rounded by IUCr 19'


@pytest.mark.parametrize(
    ('actual', 'expected'),
    [
        ('1.54(2)', '1.54249(0.01532)'),
        ('1.543(16)', '1.54249(0.01532)'),
        ('1.542(15)', '1.54249(0.01532)'),
        ('-1.23(2)', '-1.235(0.02)'),
        ('1.54', '1.54249'),
        ('1.54()', '1.54249()'),
        ('1.54(0)', '1.54249(0)'),
        ('1.542(16)', '1.54249'),
    ],
)
def test_saved_iucr_comparison_refuses_wrong_rounding_and_unfitted_changes(actual, expected):
    with pytest.raises(ValueError, match=r'uncertainty|parameter|operand'):
        compare_scientific(
            {'experiment.edi': [['_scale.value', actual]]},
            {'experiment.edi': [['_scale.value', expected]]},
            saved_iucr=True,
        )
