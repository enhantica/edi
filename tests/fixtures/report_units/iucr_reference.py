"""Independent decimal arithmetic for IUCr Statistical Descriptors recommendation 12.

Round the uncertainty upward to two significant digits, keeping 10..19
(or all 10..99); above 19 the default uses one upward-rounded digit.
ROUND_HALF_UP is half away from zero for signed Decimal values.
No product imports. Fixed, absent and engaged-zero uncertainties retain bits.
"""

import re
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, localcontext


def rounded_pair(value, uncertainty, rule='iucr_19'):
    if uncertainty is None or uncertainty == 0:
        return float(value), uncertainty
    with localcontext() as context:
        context.prec = 800
        number = Decimal(str(value))
        su = abs(Decimal(str(uncertainty)))
        quantum = Decimal(1).scaleb(su.adjusted() - 1)
        digits = (su / quantum).to_integral_value(rounding=ROUND_CEILING)
        if digits == 100:
            quantum *= 10
            digits = Decimal(10)
        if rule == 'iucr_19' and digits > 19:
            quantum = Decimal(1).scaleb(su.adjusted())
            digits = (su / quantum).to_integral_value(rounding=ROUND_CEILING)
        return float(number.quantize(quantum, rounding=ROUND_HALF_UP)), float(digits * quantum)


def rounded_token(match):
    value, bracket = match.group(1).decode(), match.group(2).decode()
    number = Decimal(value)
    decimals = max(0, -number.as_tuple().exponent)
    uncertainty = Decimal(bracket)
    if '.' not in bracket and 'e' not in bracket.lower():
        uncertainty *= Decimal(1).scaleb(-decimals)
    if not uncertainty:
        return match.group()
    rounded_value, rounded_su = rounded_pair(float(value), float(uncertainty))
    with localcontext() as context:
        context.prec = 800
        su = Decimal(str(rounded_su))
        exponent = su.adjusted()
        while True:
            quantum = Decimal(1).scaleb(exponent)
            digits = su / quantum
            if digits == digits.to_integral_value() and 2 <= digits <= 19:
                break
            exponent -= 1
        shown = Decimal(str(rounded_value)).quantize(quantum)
        if not shown:
            shown = abs(shown)
        bracket_text = str(int(digits if exponent < 0 else su))
        return (format(shown, 'f') + '(' + bracket_text + ')').encode()


def rounded_record(contents):
    """Forward parameter s.u. and coefficient tokens; keep every other byte pinned."""

    numeric = re.compile(
        rb'(?<!\S)([-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?)\((\d+(?:\.\d*)?(?:[eE][-+]?\d+)?)\)(?!\S)'
    )
    token = re.compile(rb"'[^']*'|\"[^\"]*\"|[^\s]+")
    categories = {
        b'_cell',
        b'_peak',
        b'_instrument',
        b'_background',
        b'_atom_site',
        b'_atom_site_aniso',
        b'_linked_structure',
        b'_preferred_orientation',
        b'_absorption',
        b'_scattering_source',
    }
    identities = {b'id', b'type_symbol', b'wyckoff_letter', b'adp_type', b'structure_id', b'type'}

    def parameter(tag):
        category, _, field = tag.partition(b'.')
        return category in categories and field not in identities

    tags = []
    in_rows = False
    out = []
    for original_line in contents.splitlines(keepends=True):
        line = original_line
        word = line.strip()
        if word == b'loop_':
            tags = []
            in_rows = False
        elif word.startswith(b'_'):
            if b' ' not in word and b'\t' not in word:
                if in_rows:
                    tags = []
                    in_rows = False
                tags.append(word)
            else:
                tags = []
                if parameter(word.split()[0]):
                    line = numeric.sub(rounded_token, line)
        elif tags and word and not word.startswith(b'#'):
            in_rows = True
            cells = list(token.finditer(line))
            if len(cells) == len(tags):
                for index in reversed(range(len(cells))):
                    if (
                        parameter(tags[index])
                        or tags[index] == b'_fit_parameter_correlation.correlation'
                    ):
                        cell = cells[index]
                        line = (
                            line[: cell.start()]
                            + (
                                rounded_correlation(cell.group().decode()).encode()
                                if tags[index] == b'_fit_parameter_correlation.correlation'
                                else numeric.sub(rounded_token, cell.group())
                            )
                            + line[cell.end() :]
                        )
        out.append(line)
    return b''.join(out)


def rounded_correlation(value):
    """Recommendation 12; the documented near-unit boundary is |r| >= 0.95.

    Decimal shortest input and half-away rounding are independent of the writer.
    Two significant figures normally, three near unity; preserve trailing digits.
    """
    with localcontext() as context:
        context.prec = 800
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError('A correlation coefficient must be finite')
        if not number:
            return '0'
        figures = 3 if abs(number) >= Decimal('0.95') else 2
        quantum = Decimal(1).scaleb(number.copy_abs().adjusted() - figures + 1)
        rounded = number.quantize(quantum, rounding=ROUND_HALF_UP)
        if rounded.copy_abs().adjusted() > number.copy_abs().adjusted():
            quantum = Decimal(1).scaleb(quantum.adjusted() + 1)
            rounded = rounded.quantize(quantum)
        return format(rounded, 'f')
