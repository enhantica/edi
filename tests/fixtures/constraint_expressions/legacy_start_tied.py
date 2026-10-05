"""Give the start_tied numeric witnesses their explicitly declared legacy companions.

ADR-0078 keeps the old column readable; current example projects instead declare
only the independent x free. This source-only fixture retains the old Al1 flags
so the locale tests reach number parsing and undo, without changing the examples.
"""

import re
from pathlib import Path


def restore_legacy_companions(project):
    path = Path(project) / 'structures/ncaf.edi'
    text = path.read_text()
    rows = list(re.finditer(r'(?m)^Al1[^\n]*$', text))
    if len(rows) != 1:
        raise ValueError('the numeric witness needs exactly one Al1 declaration')
    row = rows[0]
    tokens = list(re.finditer(r'\S+', row[0]))
    leader = tokens[2][0]
    bare = re.sub(r'\([^)]*\)', '', leader)
    if (
        '(' not in leader
        or tokens[5][0] != 'a'
        or any(tokens[index][0] != bare for index in (3, 4))
    ):
        raise ValueError('legacy companions require the declared free x on an x,x,x site')
    changed = row[0]
    for index in (4, 3):
        token = tokens[index]
        changed = changed[: token.start()] + leader + changed[token.end() :]
    path.write_text(text[: row.start()] + changed + text[row.end() :])
