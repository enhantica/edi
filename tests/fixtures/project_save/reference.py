"""Decimal save references; no product imports (ADR-0092)."""

from decimal import ROUND_HALF_UP, Decimal

from tests.fixtures.report_units.iucr_reference import rounded_pair

PAIRS = [
    (2.16352, 0.00481),
    (-2.16352, 0.00481),
    (1.54249, 0.01532),
    (0.4637, 0.0196),
    (54912.0, 1234.0),
    (0.000183461, 0.000087),
    (0.1234567, 0.00201),
]


def expected_pair(value, su, rule):
    return rounded_pair(value, su, rule or 'iucr_99')


def six_digits(value):
    number = Decimal(str(value))
    quantum = Decimal(1).scaleb(number.copy_abs().adjusted() - 5)
    return float(number.quantize(quantum, rounding=ROUND_HALF_UP))
