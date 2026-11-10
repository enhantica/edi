#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Tutorial code is code a user copies, so it names every parameter plainly and fits in stages.

A tutorial source (``docs/user/tutorials/*.py``) sets and frees parameters by plain attribute
access, one per line (``experiment.peak.broad_gauss_u.free = True``). This check refuses
``getattr``, ``setattr`` and ``delattr``, and a loop over a written-out list of names. A tutorial
that fits teaches the fit in stages: it fits at least twice, and frees parameters after its first
fit, so not everything is freed at once.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / 'docs/user/tutorials'
REFUSED_CALLS = {'getattr', 'setattr', 'delattr'}


def _names(node: ast.expr) -> bool:
    """A literal tuple, list or set of strings."""
    return (
        isinstance(node, (ast.Tuple, ast.List, ast.Set))
        and bool(node.elts)
        and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.elts)
    )


def violations(path: Path) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'), str(path))):
        at = node.iter if isinstance(node, ast.comprehension) else node
        where = f'{path.relative_to(ROOT)}:{getattr(at, "lineno", 0)}'
        call = isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        if call and node.func.id in REFUSED_CALLS:
            found.append(f'{where}: {node.func.id}() — write the attribute out')
        if isinstance(node, (ast.For, ast.comprehension)) and _names(node.iter):
            found.append(f'{where}: a loop over written-out names — one parameter per line')
    return found


def _fits(tree: ast.AST) -> list[int]:
    """The lines of the tutorial's ``.fit()`` calls."""
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'fit'
    )


def _frees(tree: ast.AST) -> list[int]:
    """The lines that free a parameter.

    ``... .free = True``, or in a loop over a group ``... .free = not ...`` (free unless symmetry
    or a constraint holds it).
    """
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Attribute) and t.attr == 'free' for t in node.targets)
        and (
            (isinstance(node.value, ast.Constant) and node.value.value is True)
            or (isinstance(node.value, ast.UnaryOp) and isinstance(node.value.op, ast.Not))
        )
    )


def stages(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'), str(path))
    fits = _fits(tree)
    if not fits:
        return []
    where = path.relative_to(ROOT)
    found = []
    if len(fits) < 2:
        found.append(f'{where}: fits once; a tutorial fits in at least two stages')
    if not any(line > fits[0] for line in _frees(tree)):
        found.append(f'{where}: frees nothing after its first fit; free one group per stage')
    return found


def main() -> int:
    sources = sorted(TUTORIALS.glob('*.py'))
    if not sources:
        where = TUTORIALS.relative_to(ROOT)
        print(f'tutorial-code: no tutorial sources in {where}', file=sys.stderr)
        return 1
    found = [line for source in sources for line in (*violations(source), *stages(source))]
    for line in found:
        print(line, file=sys.stderr)
    if found:
        return 1
    print(f'tutorial-code: {len(sources)} tutorials name parameters plainly and fit in stages')
    return 0


if __name__ == '__main__':
    sys.exit(main())
