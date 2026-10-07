"""Compare saved scientific fields with an independent native fit capture."""

import math
import re
import shlex
from pathlib import Path

_NUMBER = re.compile(r'^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(?:\((\d+)\))?$')


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
                aa, bb = _NUMBER.fullmatch(a), _NUMBER.fullmatch(b)
                if aa or bb:
                    if not aa or not bb:
                        raise ValueError(
                            'web fit invalidated a native parameter or pattern operand: ' + name
                        )
                    av, bv = float(aa[1]), float(bb[1])
                    if (
                        not math.isfinite(av)
                        or not math.isfinite(bv)
                        or not math.isclose(av, bv, rel_tol=relative, abs_tol=absolute)
                    ):
                        raise ValueError(
                            'web fit changed a native parameter or pattern operand: ' + name
                        )
                    if aa[2] != bb[2]:
                        raise ValueError('web fit changed a native parameter uncertainty: ' + name)
                elif a != b:
                    raise ValueError('web fit changed a native scientific token: ' + name)
