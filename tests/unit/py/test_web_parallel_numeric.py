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
    compare_scientific(
        {'experiment.edi': [['_scale.value', actual]]},
        {'experiment.edi': [['_scale.value', expected]]},
    )


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
