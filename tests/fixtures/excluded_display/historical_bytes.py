"""Compare modern excluded cells with the retained pre-convention byte pins."""

import math
import re

from tests.fixtures.project_save.reference import six_digits


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_d(row, scalar, *, saved_precision=False):
    def number(key, default=None):
        raw = scalar.get(b'_instrument.' + key)
        return default if raw is None else float(raw.split(b'(')[0])

    d = float(row[b'_data.d_spacing'])
    require(
        math.isfinite(d) and d > 0, 'Excluded d-spacing must retain a positive physical conversion'
    )
    if b'_data.two_theta' in row:
        x = float(row[b'_data.two_theta'])
        expected = number(b'setup_wavelength') / (2 * math.sin(math.radians(x / 2)))
        correct = math.isclose(d, expected, rel_tol=2e-7, abs_tol=2e-7)
    else:
        require(b'_data.time_of_flight' in row, 'A physical d comparison requires its native axis')
        x = float(row[b'_data.time_of_flight'])
        expected = (
            number(b'calib_d_to_tof_offset', 0)
            + number(b'calib_d_to_tof_linear') * d
            + number(b'calib_d_to_tof_quadratic', 0) * d * d
            + number(b'calib_d_to_tof_reciprocal', 0) / d
        )
        correct = math.isclose(x, expected, rel_tol=2e-7, abs_tol=2e-7)
    if saved_precision:
        if b'_data.time_of_flight' in row:
            require(
                number(b'calib_d_to_tof_reciprocal', 0) == 0,
                'The saved TOF witness uses the declared quadratic calibration',
            )
            # diffraction-lib tof_to_d: TOF = offset + linear*d + quadratic*d*d.
            # Rationalize its smaller positive root to avoid cancellation.
            shifted = x - number(b'calib_d_to_tof_offset', 0)
            linear = number(b'calib_d_to_tof_linear')
            quadratic = number(b'calib_d_to_tof_quadratic', 0)
            expected = (
                2 * shifted / (linear + math.sqrt(linear * linear + 4 * quadratic * shifted))
            )
        correct = d.hex() == six_digits(expected).hex()
    require(correct, 'Excluded d-spacing must match the independent native-axis conversion')


def legacy_row(line, tags, scalar, *, saved_precision=False):
    cells = list(re.finditer(rb'\S+', line))
    require(len(cells) == len(tags), 'Historical comparison requires complete canonical data rows')
    row = {tag: cells[i].group() for i, tag in enumerate(tags)}
    if row[b'_data.calc_status'] != b'excl':
        return line
    check_d(row, scalar, saved_precision=saved_precision)
    replacements = {b'_data.d_spacing'}
    for key in (b'intensity_calc', b'intensity_bkg', b'intensity_diff'):
        tag = b'_data.' + key
        if tag in row:
            require(
                row[tag] == b'.',
                'Excluded derived cells must be inapplicable dots before comparison',
            )
            replacements.add(tag)
    result = line
    for offset in reversed(range(len(tags))):
        if tags[offset] in replacements:
            start, end = cells[offset].span()
            result = result[:start] + b'0.' + result[end:]
    return result


def transform_excluded_bytes(name, contents, converter):
    if not name.startswith('experiments/') or not name.endswith('.edi'):
        return contents
    lines = contents.splitlines(keepends=True)
    tags = []
    in_header = False
    scalar = dict(re.findall(rb'(?m)^(_instrument\.[\w_]+)[ \t]+([^\s]+)', contents))
    for index, line in enumerate(lines):
        token = line.strip()
        if token == b'loop_':
            tags, in_header = [], True
        elif in_header and token.startswith(b'_'):
            tags.append(token)
        elif token and not token.startswith((b'#', b'_', b'data_')):
            in_header = False
            if b'_data.calc_status' in tags and b'_data.d_spacing' in tags:
                lines[index] = converter(line, tags, scalar)
    return b''.join(lines)


def retained_hashes(observed, converted, expected):
    require(
        observed.keys() == converted.keys() == expected.keys(),
        'The excluded-cell transition must retain the complete pinned file inventory',
    )
    return {
        name: observed[name] if observed[name] == expected[name] else converted[name]
        for name in observed
    }


def historical_excluded_bytes(name, contents, *, saved_precision=False):
    def convert(line, tags, scalar):
        return legacy_row(line, tags, scalar, saved_precision=saved_precision)

    return transform_excluded_bytes(name, contents, convert)


def modern_row(line, tags, scalar):
    cells = list(re.finditer(rb'\S+', line))
    require(len(cells) == len(tags), 'Historical input must retain a rectangular data loop')
    row = {tag: cells[i].group() for i, tag in enumerate(tags)}
    if row[b'_data.calc_status'] != b'excl':
        return line

    def number(key, default=None):
        raw = scalar.get(b'_instrument.' + key)
        return default if raw is None else float(raw.split(b'(')[0])

    replacements = {}
    d = row[b'_data.d_spacing']
    if d == b'.' or re.fullmatch(rb'[+-]?0+(?:\.0*)?(?:[eE][+-]?\d+)?', d) is not None:
        if b'_data.two_theta' in row:
            x = float(row[b'_data.two_theta'])
            value = number(b'setup_wavelength') / (2 * math.sin(math.radians(x / 2)))
        else:
            require(
                number(b'calib_d_to_tof_reciprocal', 0) == 0,
                'The historical TOF inputs use the declared quadratic calibration',
            )
            x = float(row[b'_data.time_of_flight']) - number(b'calib_d_to_tof_offset', 0)
            linear, quadratic = (
                number(b'calib_d_to_tof_linear'),
                number(b'calib_d_to_tof_quadratic', 0),
            )
            value = 2 * x / (linear + math.sqrt(linear * linear + 4 * quadratic * x))
        replacements[b'_data.d_spacing'] = format(value, '.12g').encode()
    for key in (b'intensity_calc', b'intensity_bkg', b'intensity_diff'):
        tag = b'_data.' + key
        if tag in row:
            require(
                row[tag] == b'.'
                or re.fullmatch(rb'[+-]?0+(?:\.0*)?(?:[eE][+-]?\d+)?', row[tag]) is not None,
                'Only old excluded zeros or inapplicable dots may undergo the input transition',
            )
            replacements[tag] = b'.'
    result = line
    for offset in reversed(range(len(tags))):
        if tags[offset] in replacements:
            start, end = cells[offset].span()
            result = result[:start] + replacements[tags[offset]] + result[end:]
    legacy_row(result, tags, scalar)
    return result


def current_excluded_bytes(name, contents):
    return transform_excluded_bytes(name, contents, modern_row)
