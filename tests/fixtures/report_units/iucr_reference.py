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
        shown = number.quantize(quantum, rounding=ROUND_HALF_UP)
        if number and not shown:
            figures = len(str(int(digits)))
            own_quantum = Decimal(1).scaleb(number.copy_abs().adjusted() - figures + 1)
            shown = number.quantize(own_quantum, rounding=ROUND_HALF_UP)
        return float(shown), float(digits * quantum)


def rounded_token(match, rule='iucr_19'):
    value, bracket = match.group(1).decode(), match.group(2).decode()
    number = Decimal(value)
    decimals = max(0, -number.as_tuple().exponent)
    uncertainty = Decimal(bracket)
    if '.' not in bracket and 'e' not in bracket.lower():
        uncertainty *= Decimal(1).scaleb(-decimals)
    if not uncertainty:
        return match.group()
    rounded_value, rounded_su = rounded_pair(float(value), float(uncertainty), rule)
    with localcontext() as context:
        context.prec = 800
        su = Decimal(str(rounded_su))
        exponent = su.adjusted()
        while True:
            quantum = Decimal(1).scaleb(exponent)
            digits = su / quantum
            if digits == digits.to_integral_value() and (
                10 <= digits <= 99 if rule == 'iucr_99' else 2 <= digits <= 19
            ):
                break
            exponent -= 1
        if number and not number.quantize(quantum, rounding=ROUND_HALF_UP):
            figures = len(str(int(digits)))
            own_quantum = Decimal(1).scaleb(number.copy_abs().adjusted() - figures + 1)
            shown = Decimal(str(rounded_value)).quantize(own_quantum)
            bracket_text = format(su.quantize(quantum), 'f')
            if '.' not in bracket_text:
                bracket_text += '.'
            return (format(shown, 'f') + '(' + bracket_text + ')').encode()
        shown = Decimal(str(rounded_value)).quantize(quantum)
        if not shown:
            shown = abs(shown)
        bracket_text = str(int(digits if exponent < 0 else su))
        return (format(shown, 'f') + '(' + bracket_text + ')').encode()


def rounded_record(contents, rule='iucr_19', *, six=False):
    """Forward parameter s.u. and coefficient tokens; keep every other byte pinned."""

    numeric = re.compile(
        rb'(?<!\S)([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\((\d+(?:\.\d*)?(?:[eE][-+]?\d+)?)\)(?!\S)'
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
        *({b'_extinction'} if six else set()),
    }
    identities = {b'id', b'type_symbol', b'wyckoff_letter', b'adp_type', b'structure_id', b'type'}

    def parameter(tag):
        category, _, field = tag.partition(b'.')
        fitted = category in categories and field not in identities
        if category == b'_background':
            # Anchor abscissae and series basis constants are exact configuration,
            # independently declared as non-Parameter fields in the dictionary.
            fitted = field in {b'intensity', b'coef'}
        return fitted or (
            six
            and (
                (
                    category == b'_fit_result'
                    and field
                    in {
                        b'fitting_time',
                        b'reduced_chi_square',
                        b'objective_value',
                        b'prof_wr_factor',
                    }
                )
                or (
                    category == b'_fit_result_bank'
                    and field not in {b'experiment_id', b'n_data_points'}
                )
                or (
                    category in {b'_data', b'_refln'}
                    and field
                    in {
                        b'd_spacing',
                        b'sin_theta_over_lambda',
                        b'f_calc',
                        b'f_squared_calc',
                        b'intensity_calc',
                        b'intensity_bkg',
                    }
                )
            )
        )

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
                    line = numeric.sub(lambda match: rounded_token(match, rule), line)
                    if six:
                        line = six_digit_scalar(line)
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
                                else (
                                    six_digit_token(
                                        numeric.sub(
                                            lambda match: rounded_token(match, rule), cell.group()
                                        )
                                    )
                                    if six
                                    else numeric.sub(
                                        lambda match: rounded_token(match, rule), cell.group()
                                    )
                                )
                            )
                            + line[cell.end() :]
                        )
        out.append(line)
    return b''.join(out)


def six_digit_scalar(line):
    return re.sub(
        rb'^(\s*_\S+\s+)(\S+)(\s*)$',
        lambda match: match[1] + six_digit_token(match[2]) + match[3],
        line,
    )


def six_digit_token(token):
    """Round only bare or no-positive-su numeric cells, preserving free-marker presence."""
    match = re.fullmatch(
        rb'([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)(\((?:0(?:\.0*)?)?\))?', token
    )
    if not match:
        return token
    with localcontext() as context:
        context.prec = 800
        value = Decimal(match[1].decode())
        quantum = Decimal(1).scaleb(value.copy_abs().adjusted() - 5)
        value = value.quantize(quantum, rounding=ROUND_HALF_UP)
        return format(float(value), '.6g').encode() + (match[2] or b'')


def saved_record(contents, rule='iucr_99'):
    """Independent save-token projection; the original archived bytes remain immutable."""
    return rounded_record(contents, rule, six=True)


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


def without_default_rule(name, contents):
    """Check the new default declaration before comparing historical project bytes."""
    if name != 'project.edi':
        return contents
    declaration = b'_su_format.rule iucr_99\n'
    assert contents.count(declaration) == 1, (
        'Saved projects require exactly one canonical two-digit default declaration'
    )
    assert len(re.findall(rb'(?m)^_su_format\.', contents)) == 1, (
        'The historical-byte comparison cannot hide an extra or unsupported s.u. setting'
    )
    return contents.replace(declaration, b'', 1)
