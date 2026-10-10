"""Compare saved scientific fields with an independent native fit capture."""

import hashlib
import json
import math
import re
import shlex
from pathlib import Path

_MANTISSA = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)'
_NUMBER = re.compile(r'^' + _MANTISSA + r'(?:[eE][+-]?\d+)?$')
_PARAMETER = re.compile(r'^(' + _MANTISSA + r')\((\d+|\d*\.\d+|\d+\.)?\)$')
# The native machine-report contract places fitted uncertainties within these
# conformance bounds, including a floor for uncertainty near zero. Values and
# pattern operands keep the tighter bounds declared by their native captures.
_UNCERTAINTY_RELATIVE = 5e-9
_UNCERTAINTY_ABSOLUTE = 5e-10


def _positive_matrix(matrix):
    """Refuse a covariance/Gram matrix without symmetric positive definiteness."""
    n = len(matrix)
    lower = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            if abs(matrix[i][j] - matrix[j][i]) > 2**-53 * (abs(matrix[i][j]) + abs(matrix[j][i])):
                raise ValueError('native conditioning requires symmetric matrices')
            value = matrix[i][j] - math.fsum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                if value <= 0:
                    raise ValueError('native conditioning requires positive definite matrices')
                lower[i][j] = math.sqrt(value)
            else:
                lower[i][j] = value / lower[j][j]


def _conditioning_inverse(expected, conditioning):
    """Validate native identity, fit dimensions and independent inverse quantities."""
    digest = hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest()
    if conditioning.get('scientific_sha256') != digest:
        raise ValueError('native conditioning must belong to the exact scientific reference')
    labels = conditioning.get('labels', [])
    n = len(labels)
    m = conditioning.get('n_data')
    if not n or len(set(labels)) != n or type(m) is not int or m <= n:
        raise ValueError('native conditioning requires the determined fit dimensions')
    normal = conditioning.get('scaled_normal', [])
    inverse = conditioning.get('scaled_inverse_normal', [])
    for matrix in (normal, inverse):
        if len(matrix) != n or any(len(row) != n for row in matrix):
            raise ValueError('native conditioning requires complete square matrices')
        if any(not math.isfinite(x) for row in matrix for x in row):
            raise ValueError('native conditioning refuses nonfinite matrix quantities')
        if any(matrix[i][i] <= 0 for i in range(n)):
            raise ValueError('native conditioning requires positive covariance diagonals')
        _positive_matrix(matrix)
    u = 2**-53
    norm = max(math.fsum(abs(x) for x in row) for row in inverse)
    normal_norm = max(math.fsum(abs(x) for x in row) for row in normal)
    residual = max(
        math.fsum(
            abs(math.fsum(normal[i][k] * inverse[k][j] for k in range(n)) - (i == j))
            for j in range(n)
        )
        for i in range(n)
    )
    if residual > (_gamma(n) + 2 * u) * normal_norm * norm:
        raise ValueError('native conditioning inverse must resolve its captured Gram matrix')
    return inverse, norm, m


def _gamma(k):
    u = 2**-53
    if k * u >= 1:
        raise ValueError('native conditioning roundoff model is unbounded')
    return k * u / (1 - k * u)


def uncertainty_tolerances(expected, conditioning):
    """Derive physical SU bounds solely from an independently captured native Gram matrix."""
    inverse, norm, m = _conditioning_inverse(expected, conditioning)
    # Two independent binary64 backends; dot products, normalization and solve roundoff.
    delta = 2 * len(inverse) * (_gamma(m + 4) + _gamma(len(inverse)))
    h = delta * norm
    if h >= 1:
        raise ValueError('native conditioning cannot certify a stable covariance inverse')
    required = {
        (document, ri, ti)
        for document, rows in expected.items()
        for ri, row in enumerate(rows)
        for ti, token in enumerate(row)
        if (operand := _operand(token)) is not None and operand[1] is not None and operand[1] > 0
    }
    bounds = {}
    for binding in conditioning.get('bindings', []):
        if len(binding) != 4:
            raise ValueError('native conditioning requires a complete saved-operand binding')
        document, ri, ti, column = binding
        key = document, ri, ti
        if (
            key not in required
            or key in bounds
            or type(column) is not int
            or not 0 <= column < len(inverse)
        ):
            raise ValueError('native conditioning must uniquely bind each saved uncertainty')
        sigma = _operand(expected[document][ri][ti])[1]
        q = delta * math.fsum(x * x for x in inverse[column]) / inverse[column][column] / (1 - h)
        if not math.isfinite(q) or not 0 <= q < 1:
            raise ValueError('native conditioning cannot certify a positive covariance diagonal')
        relative = q / (1 + math.sqrt(1 - q))
        bounds[key] = max(
            _UNCERTAINTY_RELATIVE * sigma,
            _UNCERTAINTY_ABSOLUTE,
            relative * sigma,
        )
    if bounds.keys() != required:
        raise ValueError('native conditioning must cover every saved fitted uncertainty')
    return bounds


def _operand(token):
    parameter = _PARAMETER.fullmatch(token)
    if parameter:
        mantissa, suffix = parameter.groups()
        value = float(mantissa)
        sigma = None
        if suffix is not None:
            # Decimal SU is absolute; integer SU is in the mantissa's last units.
            digits = len(mantissa.partition('.')[2])
            sigma = float(suffix) if '.' in suffix else float(suffix) / 10**digits
        if not math.isfinite(value) or (sigma is not None and not math.isfinite(sigma)):
            raise ValueError('web fit has a nonfinite parameter or uncertainty operand')
        return value, sigma, True
    if _NUMBER.fullmatch(token):
        value = float(token)
        if not math.isfinite(value):
            raise ValueError('web fit has a nonfinite parameter or pattern operand')
        return value, None, False
    if token.lower().lstrip('+-') in {'nan', 'inf', 'infinity'}:
        raise ValueError('web fit has a nonfinite parameter or pattern operand')
    if re.match(r'^[+-]?(?:\d|\.\d)', token) and '(' in token:
        raise ValueError('web fit has an invalid parameter or uncertainty operand')
    return None


def scientific(root):
    result = {}
    for path in sorted(Path(root).rglob('*.edi')):
        rows, names, capture = [], [], False
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if line == 'loop_':
                names, capture = [], False
                continue
            tokens = shlex.split(line)
            if len(tokens) == 1 and tokens[0].startswith('_'):
                names.append(tokens[0])
                capture = any(
                    name.startswith((
                        '_atom_site.',
                        '_atom_site_aniso.',
                        '_background.',
                        '_data.',
                        '_pd_phase_block.',
                    ))
                    for name in names
                )
                continue
            if len(tokens) > 1 and tokens[0].startswith('_'):
                tag = tokens[0]
                if tag.startswith((
                    '_cell.',
                    '_space_group.',
                    '_peak.',
                    '_pd_instr.',
                    '_pd_calib.',
                    '_pd_phase_block.',
                    '_scale.',
                    '_fit_result.',
                )) and not re.search(r'time|elapsed|exit_reason|status|description', tag):
                    rows.append(tokens)
                names, capture = [], False
            elif capture:
                rows.append([*names, *tokens])
        if rows:
            result[path.relative_to(root).as_posix()] = rows
    return result


def compare_scientific(actual, expected, relative=1e-9, absolute=1e-11, *, conditioning=None):
    bounds = uncertainty_tolerances(expected, conditioning) if conditioning is not None else {}
    if actual.keys() != expected.keys():
        raise ValueError('web fit must retain the native scientific document inventory')
    for name, rows in expected.items():
        current = actual[name]
        if len(current) != len(rows):
            raise ValueError('web fit changed the native scientific row inventory: ' + name)
        for ri, (observed, reference) in enumerate(zip(current, rows, strict=True)):
            if len(observed) != len(reference):
                raise ValueError('web fit changed a native scientific row shape: ' + name)
            for ti, (a, b) in enumerate(zip(observed, reference, strict=True)):
                aa, bb = _operand(a), _operand(b)
                if aa is not None or bb is not None:
                    if aa is None or bb is None:
                        raise ValueError(
                            'web fit invalidated a native parameter or pattern operand: ' + name
                        )
                    av, au, bracketed = aa
                    bv, bu, reference_bracketed = bb
                    if (
                        not math.isfinite(av)
                        or not math.isfinite(bv)
                        or not math.isclose(av, bv, rel_tol=relative, abs_tol=absolute)
                    ):
                        raise ValueError(
                            'web fit changed a native parameter or pattern operand: ' + name
                        )
                    if bracketed != reference_bracketed or (au is None) != (bu is None):
                        raise ValueError('web fit changed a native parameter uncertainty: ' + name)
                    if au is not None and abs(au - bu) > bounds.get(
                        (name, ri, ti),
                        max(_UNCERTAINTY_RELATIVE * abs(bu), _UNCERTAINTY_ABSOLUTE),
                    ):
                        raise ValueError('web fit changed a native parameter uncertainty: ' + name)
                elif a != b:
                    raise ValueError('web fit changed a native scientific token: ' + name)
    return True
