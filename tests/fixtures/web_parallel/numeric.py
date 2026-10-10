"""Compare saved scientific fields with an independent native fit capture."""

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


def compare_scientific(actual, expected, relative=1e-9, absolute=1e-11):
    if actual.keys() != expected.keys():
        raise ValueError('web fit must retain the native scientific document inventory')
    for name, rows in expected.items():
        current = actual[name]
        if len(current) != len(rows):
            raise ValueError('web fit changed the native scientific row inventory: ' + name)
        for observed, reference in zip(current, rows, strict=True):
            if len(observed) != len(reference):
                raise ValueError('web fit changed a native scientific row shape: ' + name)
            for a, b in zip(observed, reference, strict=True):
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
                    if au is not None and abs(au - bu) > max(
                        _UNCERTAINTY_RELATIVE * abs(bu), _UNCERTAINTY_ABSOLUTE
                    ):
                        raise ValueError('web fit changed a native parameter uncertainty: ' + name)
                elif a != b:
                    raise ValueError('web fit changed a native scientific token: ' + name)
