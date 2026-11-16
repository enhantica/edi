"""Keep frozen saved bytes; compare only derived reflection intensities at parity precision."""

import base64
import hashlib
import json
import math
import re
import zlib
from pathlib import Path

from tests.fixtures.project_categories.historical_bytes import units

HOME = Path(__file__).resolve().parent


def reference_experiment(rule):
    main = json.loads((HOME / 'saved-main.json').read_text())
    record = json.loads((HOME / 'fitted-experiment-main.json').read_text())
    assert (
        record['source_commit'] == main['source_commit']
        and record['kind'] == 'immutable saved-main file recovery'
    ), 'The calculated-output witness recovers the original main regression, never a new pin'
    expected = main['fit_projects'][record['case']][rule]['experiments/experiment.edi']
    raw = zlib.decompress(base64.b64decode(record['experiments'][rule], validate=True))
    assert hashlib.sha256(raw).hexdigest() == expected, (
        'Every recovered reference byte must reproduce the existing immutable whole-file hash'
    )
    return raw


def _reflections(data):
    entries = [body for key, body in units(data)[1] if key == b'loop:_refln']
    assert len(entries) == 1, 'A fitted saved experiment has exactly one original reflection loop'
    body = entries[0]
    lines = body.splitlines(keepends=True)
    headers, rows = [], []
    for index, line in enumerate(lines):
        if line.strip() == b'loop_' or not line.strip():
            continue
        if line.startswith(b'_'):
            assert not rows, 'Reflection columns precede their complete original row population'
            headers.append(line.strip())
        else:
            tokens = list(re.finditer(rb'\S+', line))
            assert len(tokens) == len(headers), (
                'Every saved reflection retains every declared column'
            )
            rows.append((index, tokens))
    assert headers.count(b'_refln.intensity_calc') == 1 and headers.count(b'_refln.id') == 1, (
        'The fitted reflection witness identifies calculated intensity and original row identity'
    )
    ids = [tokens[headers.index(b'_refln.id')].group() for _, tokens in rows]
    assert rows and len(ids) == len(set(ids)), (
        'The original reflection population has unique nonempty row identities'
    )
    return body, lines, headers, rows


def restore_calculated_reflections(actual, reference):
    body, lines, headers, rows = _reflections(actual)
    _, _, expected_headers, expected_rows = _reflections(reference)
    assert headers == expected_headers and len(rows) == len(expected_rows), (
        'Calculated-output comparison preserves the exact original columns and sample population'
    )
    column = headers.index(b'_refln.intensity_calc')
    for (line_index, fields), (_, expected) in zip(rows, expected_rows, strict=True):
        assert all(
            a.group() == b.group()
            for i, (a, b) in enumerate(zip(fields, expected, strict=True))
            if i != column
        ), (
            'Every non-calculated reflection byte, row identity, index '
            'and measured value remains exact'
        )
        value, pin = float(fields[column].group()), float(expected[column].group())
        assert math.isfinite(value) and math.isfinite(pin), (
            'Calculated reflection intensities are finite'
        )
        assert math.isclose(value, pin, rel_tol=5e-9, abs_tol=5e-10), (
            'Derived reflection intensity retains ADR-0057 '
            'max(relative 5e-9, absolute 5e-10) at every sample'
        )
        token = fields[column]
        lines[line_index] = (
            lines[line_index][: token.start()]
            + expected[column].group()
            + lines[line_index][token.end() :]
        )
    assert actual.count(body) == 1, (
        'The original reflection loop has one unambiguous saved location'
    )
    return actual.replace(body, b''.join(lines), 1)
