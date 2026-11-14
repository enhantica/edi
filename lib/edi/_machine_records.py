# SPDX-License-Identifier: BSD-3-Clause
"""The version header of the linked engine's shared machine record."""

import re


def schema_line(report: str) -> str:
    """Refuse malformed emitter output rather than invent a machine schema version."""
    lines = report.splitlines(keepends=True) if isinstance(report, str) else []
    if (
        len(lines) < 2
        or re.fullmatch(r'schema=[1-9][0-9]*\n', lines[0]) is None
        or lines[1] != 'record=error\n'
        or not report.endswith('\n')
        or any(line.startswith('schema=') for line in lines[1:])
    ):
        raise ValueError('linked edi report schema is malformed')
    return lines[0]
