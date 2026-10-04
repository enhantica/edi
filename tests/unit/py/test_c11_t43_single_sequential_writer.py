""": edi surfaces crysta's sequential loop and owns no CSV writer."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
WRITER_METHODS = {
    'open',
    'to_csv',
    'write',
    'write_bytes',
    'write_text',
    'writer',
    'writerow',
    'writerows',
}


def _production_sources() -> tuple[Path, ...]:
    python = (ROOT / 'lib' / 'edi').rglob('*.py')
    cpp = (ROOT / 'core' / 'src').rglob('*.cpp')
    headers = (ROOT / 'core' / 'include').rglob('*.hpp')
    sources = tuple(sorted((*python, *cpp, *headers)))
    assert sources, ' writer inventory must derive at least one edi production source'
    return sources


def _analysis_fit_node() -> ast.FunctionDef:
    source = ROOT / 'lib' / 'edi' / '__init__.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    matches = [
        item
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'Analysis'
        for item in node.body
        if isinstance(item, ast.FunctionDef) and item.name == 'fit'
    ]
    assert len(matches) == 1, (
        ' requires exactly one edi.Analysis.fit definition in the production AST'
    )
    return matches[0]


def _python_module_owns_results_writer(text: str) -> bool:
    tree = ast.parse(text)
    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    writer_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    owns_contract = any(
        'results.csv' in literal or 'fit_result.reduced_chi_square' in literal
        for literal in literals
    )
    return owns_contract and bool(writer_calls & WRITER_METHODS)


def _assert_sequential_native_delegate(node: ast.FunctionDef) -> str:
    branches: list[str] = []
    for candidate in ast.walk(node):
        if not isinstance(candidate, ast.If):
            continue
        comparisons = [
            comparison
            for comparison in ast.walk(candidate.test)
            if isinstance(comparison, ast.Compare)
            and len(comparison.ops) == 1
            and isinstance(comparison.ops[0], ast.Eq)
            and any(
                isinstance(child, ast.Attribute)
                and child.attr == 'fitting_mode'
                and isinstance(child.value, ast.Attribute)
                and child.value.attr == '_project'
                and isinstance(child.value.value, ast.Name)
                and child.value.value.id == 'self'
                for child in ast.walk(comparison)
            )
            and any(
                isinstance(child, ast.Constant) and child.value == 'sequential'
                for child in ast.walk(comparison)
            )
        ]
        if len(comparisons) != 1:
            continue
        returns = [
            child
            for statement in candidate.body
            for child in ast.walk(statement)
            if isinstance(child, ast.Return)
        ]
        assert len(returns) == 1 and isinstance(returns[0].value, ast.Call), (
            ' requires the sequential fitting_mode branch to return exactly one '
            'crysta Project call'
        )
        callee = returns[0].value.func
        assert (
            isinstance(callee, ast.Attribute)
            and isinstance(callee.value, ast.Attribute)
            and isinstance(callee.value.value, ast.Name)
            and callee.value.value.id == 'self'
            and callee.value.attr == '_project'
        ), ' requires the sequential branch to delegate directly to the crysta Project'
        assert callee.attr not in {'fit', 'fit_joint'}, (
            ' requires a dedicated crysta sequential entry point, not an edi-side loop '
            'over the existing single/joint calls'
        )
        branches.append(callee.attr)
    assert len(branches) == 1, (
        ' requires exactly one fitting_mode == sequential delegation branch in Analysis.fit'
    )
    return branches[0]


def test_edi_production_inventory_contains_no_results_csv_writer() -> None:
    offenders = []
    for path in _production_sources():
        text = path.read_text(encoding='utf-8')
        if path.suffix == '.py':
            if _python_module_owns_results_writer(text):
                offenders.append(str(path.relative_to(ROOT)))
        else:
            uncommented = re.sub(r'//[^\n]*|/\*.*?\*/', '', text, flags=re.DOTALL)
            owns_contract = (
                'results.csv' in uncommented or 'fit_result.reduced_chi_square' in uncommented
            )
            writes = bool(
                re.search(r'\b(?:std::)?ofstream\b|\b(?:fwrite|write|rename)\s*\(', uncommented)
            )
            if owns_contract and writes:
                offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, (
        ' requires the only results.csv implementation to live in crysta; the '
        f'structurally derived edi production inventory contains writer-contract tokens in '
        f'{offenders!r}'
    )
    split_helpers = """
RESULT = 'results.csv'
COLUMNS = ('fit_result.reduced_chi_square',)
def hidden_writer(path, payload):
    path.write_text(payload)
"""
    assert _python_module_owns_results_writer(split_helpers), (
        ' writer ownership must remain detectable when contract literals and the '
        'writer-capable call are split across module-level helpers'
    )


def test_analysis_fit_routes_sequential_mode_to_one_native_entry_point() -> None:
    _assert_sequential_native_delegate(_analysis_fit_node())


def test_sequential_route_rejects_literal_only_and_single_fit_escape() -> None:
    literal_only = ast.parse(
        "def fit(self):\n    marker = 'sequential'\n    return self._project.fit()\n"
    ).body[0]
    assert isinstance(literal_only, ast.FunctionDef), (
        ' literal-only escape control must parse as a function definition'
    )
    with pytest.raises(AssertionError, match='delegation branch'):
        _assert_sequential_native_delegate(literal_only)

    single_fit = ast.parse(
        'def fit(self):\n'
        "    if self._project.fitting_mode == 'sequential':\n"
        '        return self._project.fit()\n'
    ).body[0]
    assert isinstance(single_fit, ast.FunctionDef), (
        ' single-fit escape control must parse as a function definition'
    )
    with pytest.raises(AssertionError, match='dedicated crysta sequential entry point'):
        _assert_sequential_native_delegate(single_fit)

    inverted = ast.parse(
        'def fit(self):\n'
        "    if self._project.fitting_mode != 'sequential':\n"
        '        return self._project.fit_sequential()\n'
    ).body[0]
    assert isinstance(inverted, ast.FunctionDef), (
        ' inverted-mode escape control must parse as a function definition'
    )
    with pytest.raises(AssertionError, match='delegation branch'):
        _assert_sequential_native_delegate(inverted)


def test_analysis_fit_body_has_no_python_csv_implementation() -> None:
    node = _analysis_fit_node()
    forbidden = {
        child.func.attr
        for child in ast.walk(node)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Attribute)
        and child.func.attr in {'open', 'write', 'writer', 'writerow', 'writerows', 'write_text'}
    }
    assert not forbidden, (
        ' requires the edi Analysis.fit facade to delegate rather than grow a second '
        f'CSV implementation; writer-capable calls={sorted(forbidden)!r}'
    )
