"""Owner 7dea80601 boundaries; decimal expectations never read product output."""

import re
from decimal import Decimal

from tests.fixtures.report_units.iucr_reference import rounded_pair, rounded_token

VALUES = [
    0.0,
    0.000999,
    0.001,
    999.9,
    1000.0,
    -0.000999,
    -0.001,
    -999.9,
    -1000.0,
    0.000000000186515,
    7453675696.0,
]
SU_VALUES = VALUES[1:9]
POWERS = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺', '0123456789-+')


def scientific(value):
    return value != 0 and not Decimal('.001') <= abs(Decimal(str(value))) < Decimal(1000)


def parse(text):
    value = str(text).strip().replace('\u2212', '-').replace(' ', '').replace('\u202f', '')
    value = value.replace('\u00d710', 'e').replace('·10', 'e').translate(POWERS)
    match = re.fullmatch(r'([+-]?\d+(?:\.\d+)?)(?:[eE]([+-]?\d+))?', value)
    if not match:
        raise ValueError(
            'A parameter cell must contain one readable decimal or scientific number: '
            + repr(text)
        )
    return Decimal(match[1]), int(match[2]) if match[2] is not None else None


def expected_plain(value):
    if value == 0:
        return Decimal(0), None
    number = Decimal(str(value))
    if scientific(value):
        power = number.copy_abs().adjusted()
        rounded = number.quantize(Decimal(1).scaleb(power - 2))
        power = rounded.copy_abs().adjusted()
        return rounded.scaleb(-power), power
    return number, None


def expected_pair(value, su, rule):
    shown, error = rounded_pair(value, su, rule)
    source = f'{value}({su})'.encode()
    token = rounded_token(re.fullmatch(rb'(.+)\((.+)\)', source), rule).decode()
    written = Decimal(token.split('(', 1)[0])
    power = Decimal(str(shown)).copy_abs().adjusted() if scientific(value) else None
    divisor = Decimal(1).scaleb(power) if power is not None else Decimal(1)
    return written / divisor, Decimal(str(error)) / divisor, power
