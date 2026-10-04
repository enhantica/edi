#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""No entity-path composition from a name in edi (ADR-0016 item 7).

A datablock name becomes a file only through crysta's ``entity_path`` — reached from edi's core as
``edi::entity_path`` (defined in ``core/src/adapter.cpp`` as a call into crysta) and from Python as
the private ``edi._entity_path`` — which refuses a name outside the persisted-name allow-list.
edi composes no such path itself, so ANY spelling that builds ``<name>.edi`` here bypasses that
refusal: the reviews found edi's Python CLI writer doing exactly that.

It scans the product sources — C++ (``core/``, ``lib/src/``, ``app/src/``) and Python (``lib/``) —
and refuses:

* C++: a ``".edi"`` literal joined to an expression by ``+`` (``name + ".edi"``);
* Python: an f-string ending in ``{…}.edi``, ``+ '.edi'``, or ``.with_suffix('.edi')``.

Fixed file names (``"analysis/analysis.edi"``, ``"project.edi"``) and extension comparisons
(``== ".edi"``) are not compositions and pass; comments are ignored.

There is no exemption: the app's Text-tab lookups read the saved text through ``entity_path``
too, so every product file is held to the rule.

Run: ``python tools/checks/entity_path_convention.py``. Exit 0 when clean, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CPP_ROOTS = ('core', 'lib/src', 'app/src')
CPP_SUFFIXES = frozenset({'.cpp', '.hpp', '.h', '.cc'})
PY_ROOTS = ('lib',)

CPP_PATTERNS = (re.compile(r'\+\s*"\.edi"'), re.compile(r'"\.edi"\s*\+'))
PY_PATTERNS = (
    re.compile(r"""f(['"])[^'"]*\{[^}]*\}\.edi\1"""),
    re.compile(r"""\+\s*(['"])\.edi\1"""),
    re.compile(r"""(['"])\.edi\1\s*\+"""),
    re.compile(r"""with_suffix\(\s*(['"])\.edi\1"""),
)


def scan(roots: tuple[str, ...], suffixes: frozenset[str], comment: str, patterns) -> list[str]:
    """Return ``file:line: text`` for every composition the patterns find under ``roots``."""
    found: list[str] = []
    for root in roots:
        for path in sorted((REPO_ROOT / root).rglob('*')):
            if path.suffix not in suffixes or not path.is_file():
                continue
            relative = path.relative_to(REPO_ROOT).as_posix()
            for index, line in enumerate(path.read_text(encoding='utf-8').splitlines()):
                code = line.split(comment, 1)[0]
                if any(pattern.search(code) for pattern in patterns):
                    found.append(f'{relative}:{index + 1}: {line.strip()}')
    return found


def main() -> int:
    """Scan the product sources; fail on any composition of an entity path from a name."""
    violations = scan(CPP_ROOTS, CPP_SUFFIXES, '//', CPP_PATTERNS) + scan(
        PY_ROOTS, frozenset({'.py'}), '#', PY_PATTERNS
    )
    if violations:
        sys.stderr.write(
            'entity_path_convention: an entity path is composed from a name outside '
            "crysta's entity_path (ADR-0016 item 7):\n"
        )
        for violation in violations:
            sys.stderr.write('  ' + violation + '\n')
        return 1
    sys.stdout.write('entity_path_convention: no entity path is composed from a name in edi\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
