"""Emit consumer references from approved coordinates and independent Oklab formulas."""

import json
from pathlib import Path

from reference import PALETTES, SCHEMES, assigned

root = Path(__file__).resolve().parents[3]
cases = []
for token, palette in zip(SCHEMES, PALETTES, strict=True):
    for count in (1, 2, 3, 5, 6, 11, 17, 100, 162, 1001):
        for theme in ('light', 'dark'):
            cases.extend(
                {
                    'scheme': token,
                    'role': role,
                    'count': count,
                    'theme': theme,
                    'colours': [assigned(palette, role, i, count, theme) for i in range(count)],
                }
                for role in ('measured', 'structures')
            )
(root / 'tests/fixtures/approved_palettes/assignments.json').write_text(
    json.dumps(cases, separators=(',', ':')) + '\n'
)
rows = [
    row for row in cases if row['role'] == 'structures' and row['count'] in {1, 2, 5, 6, 11, 17}
]
header = (
    '#pragma once\n#include <string>\n#include <vector>\nnamespace approved_palette {\n'
    'struct Case { std::string scheme; unsigned count; bool dark; '
    'std::vector<std::string> colours; };\ninline const std::vector<Case> cases{\n'
)
for row in rows:
    header += (
        '{"'
        + row['scheme']
        + '",'
        + str(row['count'])
        + ','
        + str(row['theme'] == 'dark').lower()
        + ',{'
        + ','.join('"' + c + '"' for c in row['colours'])
        + '}},\n'
    )
header += '};\n}\n'
(root / 'tests/fixtures/approved_palettes/assignments.hpp').write_text(header)
