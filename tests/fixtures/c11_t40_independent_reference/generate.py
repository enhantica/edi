#!/usr/bin/env python3
"""Freeze an independent  public-surface snapshot from diffraction-lib source.

This generator belongs to the tests lane.  It deliberately does not import the production parity
generator or read its oracle.  The emitted Python source is a compact, AST-readable preservation
of every category-qualified public property found at the reviewed upstream pin, including public
selectors inherited from cross-cutting category bases.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import re
import subprocess
from pathlib import Path

PIN = '0ffba46f4b501066a73e77f00fa29fa13519b417'  # origin/master v0.20.1 ( P4)
SCAN_ROOT = 'src/easydiffraction/'
CATEGORY_RE = re.compile(r'categories/([a-z_0-9]+)/')
DESCRIPTOR_CALLS = {
    'EnumDescriptor',
    'IntegerDescriptor',
    'NumericDescriptor',
    'Parameter',
    'StringDescriptor',
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ['git', '-C', str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout


def _call_name(call: ast.Call) -> str | None:
    function = call.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return None


def _public_properties(tree: ast.AST) -> set[str]:
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith('_')
        and any(
            isinstance(decorator, ast.Name) and decorator.id == 'property'
            for decorator in node.decorator_list
        )
    }


def _descriptor_attributes(tree: ast.AST, public_properties: set[str]) -> set[str]:
    """Descriptor-backed public attributes, including inherited selectors such as ``type``."""
    attributes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            target, call = node.target, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, call = node.targets[0], node.value
        else:
            continue
        if not isinstance(call, ast.Call) or _call_name(call) not in DESCRIPTOR_CALLS:
            continue
        if not (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == 'self'
            and target.attr.startswith('_')
        ):
            continue
        attribute = target.attr.removeprefix('_')
        if attribute in public_properties:
            attributes.add(attribute)
    return attributes


def _python_paths(repo: Path) -> list[str]:
    return sorted(
        path
        for path in _git(repo, 'ls-tree', '-r', '--name-only', PIN, SCAN_ROOT).splitlines()
        if path.endswith('.py')
    )


def _snapshot(repo: Path) -> tuple[dict[str, set[str]], list[str], str]:
    paths = _python_paths(repo)
    sources = {path: _git(repo, 'show', f'{PIN}:{path}') for path in paths}
    trees: dict[str, ast.AST] = {}
    public_properties: set[str] = set()
    for path, source in sources.items():
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError:
            continue
        trees[path] = tree
        public_properties.update(_public_properties(tree))

    universe: dict[str, set[str]] = {}
    for path, tree in trees.items():
        match = CATEGORY_RE.search(path)
        if match is None:
            continue
        category = match.group(1)
        names = _public_properties(tree) | _descriptor_attributes(tree, public_properties)
        universe.setdefault(category, set()).update(names)
    universe = {category: names for category, names in universe.items() if names}

    blob_index = [f'{path}\0{_git(repo, "rev-parse", f"{PIN}:{path}").strip()}' for path in paths]
    digest = hashlib.sha256('\n'.join(blob_index).encode()).hexdigest()
    return universe, paths, digest


def _render(universe: dict[str, set[str]], paths: list[str], digest: str) -> str:
    lines = [
        '"""Generated external-reference snapshot; regenerate with the adjacent generator."""',
        '',
        f'SOURCE_COMMIT = {PIN!r}',
        f'SOURCE_FILE_COUNT = {len(paths)}',
        f'SOURCE_BLOB_INDEX_SHA256 = {digest!r}',
        '',
    ]
    for category, attributes in sorted(universe.items()):
        lines.append(f'class {category}:')
        for attribute in sorted(attributes):
            lines.extend([
                '    @property',
                f'    def {attribute}(self):',
                '        ...',
                '',
            ])
    return '\n'.join(lines).rstrip() + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path, help='a diffraction-lib checkout carrying the pin')
    parser.add_argument(
        '--output',
        type=Path,
        default=Path(__file__).with_name('upstream_surface.snapshot'),
    )
    args = parser.parse_args()

    resolved = _git(args.upstream, 'rev-parse', f'{PIN}^{{commit}}').strip()
    if resolved != PIN:
        raise SystemExit(f'expected {PIN}, resolved {resolved}')
    universe, paths, digest = _snapshot(args.upstream)
    args.output.write_text(_render(universe, paths, digest), encoding='utf-8')
    print(
        f'{len(universe)} categories, {sum(map(len, universe.values()))} attributes, '
        f'{len(paths)} source files -> {args.output}'
    )


if __name__ == '__main__':
    main()
