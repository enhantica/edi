"""Anti-gaming gates for 's two edi unit-coverage metrics."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[3]
UNIT = ROOT / 'tests' / 'unit'
CONTRACT = ROOT / 'data' / 'unit-coverage.json'
CPP_GATE = ROOT / 'tools' / 'ci' / 'cpp-coverage-unit.sh'

ASSERTION_CALLS = {'fail', 'raises', 'warns'}
CPP_ASSERTION = re.compile(r'\b(?:CHECK|REQUIRE|FAIL|SUCCEED)[A-Z_]*\s*\(')
CPP_CALL = re.compile(r'\b([A-Za-z_]\w*)\s*\(')
CPP_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/', re.DOTALL)


def _load_json(path: Path) -> dict[str, Any]:
    assert path.is_file(), f' requires the committed coverage contract: {path.relative_to(ROOT)}'
    value = json.loads(path.read_text(encoding='utf-8'))
    assert isinstance(value, dict), f'{path.relative_to(ROOT)} must contain a JSON object'
    return value


def _contract() -> dict[str, Any]:
    document = _load_json(CONTRACT)
    assert document.get('schema') == 1, 'the coverage contract schema must remain version one'
    assert document.get('repo') == 'edi', 'the coverage contract must remain edi-scoped'
    assert document.get('tier') == 'tests/unit', 'the coverage contract must remain unit-tier only'
    assert isinstance(document.get('metrics'), dict), 'the coverage contract must declare metrics'
    assert isinstance(document.get('exclusions'), list), (
        'the coverage contract must declare an exclusion register'
    )
    return document


def _call_name(call: ast.Call) -> str:
    function = call.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return ''


class _AssertionVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.functions: dict[str, ast.AST] = {}
        self.calls: dict[str, set[str]] = {}
        self.asserting: set[str] = set()
        self._stack: list[str] = []

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.functions[node.name] = node
        self.calls.setdefault(node.name, set())
        self._stack.append(node.name)
        for statement in node.body:
            self.visit(statement)
        self._stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        if self._stack:
            self.asserting.add(self._stack[-1])
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if self._stack:
            name = _call_name(node)
            self.calls[self._stack[-1]].add(name)
            if name in ASSERTION_CALLS or name.startswith('assert'):
                self.asserting.add(self._stack[-1])
        self.generic_visit(node)


def _python_asserting_nodes(path: Path) -> tuple[dict[str, ast.AST], set[str]]:
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    visitor = _AssertionVisitor()
    visitor.visit(tree)
    asserting = set(visitor.asserting)
    changed = True
    while changed:
        changed = False
        for name, function_calls in visitor.calls.items():
            if name not in asserting and function_calls & asserting:
                asserting.add(name)
                changed = True
    return visitor.functions, asserting


def _without_cpp_comments(source: str) -> str:
    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        if not token.startswith('/'):
            return token
        return ''.join('\n' if character == '\n' else ' ' for character in token)

    return CPP_TOKEN.sub(replace, source)


def _balanced_body(source: str, opening: int) -> str:
    depth = 0
    quote = ''
    escaped = False
    for index in range(opening, len(source)):
        character = source[index]
        if quote:
            if escaped:
                escaped = False
            elif character == '\\':
                escaped = True
            elif character == quote:
                quote = ''
            continue
        if character in {"'", '"'}:
            quote = character
        elif character == '{':
            depth += 1
        elif character == '}':
            depth -= 1
            if depth == 0:
                return source[opening : index + 1]
    raise AssertionError('unbalanced C++ test/helper body')


def _cpp_cases_and_asserting_helpers(path: Path) -> tuple[list[tuple[str, str]], set[str]]:
    source = _without_cpp_comments(path.read_text(encoding='utf-8'))
    cases: list[tuple[str, str]] = []
    for match in re.finditer(r'\bTEST_CASE\s*\(\s*"([^"]+)"', source):
        opening = source.find('{', match.end())
        assert opening >= 0, f'{path.name}: TEST_CASE {match.group(1)!r} has no body'
        cases.append((match.group(1), _balanced_body(source, opening)))

    helpers: dict[str, str] = {}
    definition = re.compile(
        r'(?:^|\n)\s*(?:template\s*<[^;{]+>\s*)?'
        r'(?:[\w:<>]+(?:\s*[*&])?\s+)+([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:const\s*)?\{'
    )
    for match in definition.finditer(source):
        helpers[match.group(1)] = _balanced_body(source, match.end() - 1)

    asserting = {name for name, body in helpers.items() if CPP_ASSERTION.search(body)}
    changed = True
    while changed:
        changed = False
        for name, body in helpers.items():
            if name not in asserting and set(CPP_CALL.findall(body)) & asserting:
                asserting.add(name)
                changed = True
    return cases, asserting


def _task_text(task: object) -> str:
    if isinstance(task, str):
        return task
    if isinstance(task, list):
        return ' '.join(str(token) for token in task)
    if isinstance(task, dict):
        return _task_text(task.get('cmd', ''))
    return ''


def test_e09_t55_declares_edi_denominators_and_thresholds() -> None:
    metrics = _contract()['metrics']
    assert metrics == {
        'cpp': {
            'kind': 'line',
            'minimum': 80,
            'roots': ['core/include', 'core/src'],
        },
        'python': {
            'kind': 'line',
            'minimum': 80,
            'roots': ['lib/edi'],
        },
    }, 'edi has separate package-line denominators for C++ and Python'


def test_e09_t55_only_unit_tiers_feed_edi_metrics() -> None:
    pyproject = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    assert pyproject['tool']['coverage']['run']['source'] == ['edi'], (
        'Python coverage must retain only the edi package root'
    )
    assert pyproject['tool']['coverage']['report']['fail_under'] == 80, (
        'Python unit coverage must fail below eighty percent'
    )
    assert pyproject['tool']['edi']['coverage']['cpp_lines_min'] == 80, (
        'C++ unit coverage must fail below eighty percent'
    )
    tasks = tomllib.loads((ROOT / 'pixi.toml').read_text(encoding='utf-8'))['tasks']
    python_task = _task_text(tasks['py-cov-unit'])
    assert 'tests/unit' in python_task and '--cov=edi' in python_task, (
        'Python coverage must collect only edi unit tests against the edi package'
    )
    assert not any(
        tier in python_task for tier in ('tests/integration', 'tests/system', 'tests/fitting')
    ), 'non-unit Python tiers must not feed edi coverage'
    cpp_script = CPP_GATE.read_text(encoding='utf-8')
    assert 'tests/unit/cpp' in cpp_script, 'C++ coverage must collect only C++ unit tests'
    assert 'core/src core/include' in cpp_script, (
        'C++ coverage must retain both declared package roots'
    )
    cmake = (ROOT / 'core' / 'CMakeLists.txt').read_text(encoding='utf-8')
    assert 'WHOLE_ARCHIVE,edi_core' in cmake or re.search(
        r'add_library\s*\(\s*edi_core\s+OBJECT\b', cmake
    ), 'the C++ denominator must contain every core translation unit, not only linked reach'


def test_e09_t55_every_counted_edi_unit_test_reaches_an_assertion() -> None:
    missing: list[str] = []
    for path in sorted(candidate for candidate in UNIT.rglob('*') if candidate.is_file()):
        if path.suffix == '.py':
            functions, asserting = _python_asserting_nodes(path)
            missing.extend(
                f'{path.relative_to(ROOT)}::{name}'
                for name in functions
                if name.startswith('test') and name not in asserting
            )
        elif path.suffix in {'.c', '.cc', '.cpp', '.cxx'}:
            cases, asserting_helpers = _cpp_cases_and_asserting_helpers(path)
            for title, body in cases:
                if not CPP_ASSERTION.search(body) and not (
                    set(CPP_CALL.findall(body)) & asserting_helpers
                ):
                    missing.append(f'{path.relative_to(ROOT)}::{title}')
    assert missing == [], (
        'counted unit tests with no direct or local-helper assertion:\n' + '\n'.join(missing)
    )


def test_e09_t55_edi_exclusions_are_exact_reasoned_live_lines() -> None:
    contract = _contract()
    roots = {
        language: tuple(f'{root}/' for root in metric['roots'])
        for language, metric in contract['metrics'].items()
    }
    seen: set[tuple[str, int]] = set()
    for entry in contract['exclusions']:
        assert set(entry) == {'language', 'line', 'path', 'reason', 'text'}, (
            'each edi exclusion must use the complete exact-line schema'
        )
        assert entry['language'] in {'cpp', 'python'}, (
            'each edi exclusion must name a measured language'
        )
        assert entry['path'].startswith(roots[entry['language']]), (
            f'excluded line is outside the declared {entry["language"]} denominator: '
            f'{entry["path"]}'
        )
        path = ROOT / entry['path']
        assert path.is_file(), f'excluded path does not exist: {entry["path"]}'
        assert isinstance(entry['line'], int) and entry['line'] > 0, (
            'each edi exclusion line must be a positive integer'
        )
        lines = path.read_text(encoding='utf-8').splitlines()
        assert entry['line'] <= len(lines), (
            f'excluded line is stale: {entry["path"]}:{entry["line"]}'
        )
        assert lines[entry['line'] - 1] == entry['text'], (
            f'excluded line no longer matches: {entry["path"]}:{entry["line"]}'
        )
        assert isinstance(entry['reason'], str) and len(entry['reason'].strip()) >= 12, (
            'each edi exclusion must carry a substantive written reason'
        )
        key = (entry['path'], entry['line'])
        assert key not in seen, f'each edi exclusion location must be unique: {key}'
        seen.add(key)
    if contract['exclusions']:
        assert 'data/unit-coverage.json' in CPP_GATE.read_text(encoding='utf-8'), (
            'the C++ gate must consume the live exclusion register'
        )
        python_task = _task_text(
            tomllib.loads((ROOT / 'pixi.toml').read_text(encoding='utf-8'))['tasks']['py-cov-unit']
        )
        assert 'data/unit-coverage.json' in python_task, (
            'the Python gate must consume the live exclusion register'
        )


@pytest.mark.parametrize(('measured', 'expected_code'), [('79.99', 1), ('80.00', 0)])
def test_e09_t55_edi_cpp_threshold_control(measured: str, expected_code: int) -> None:
    script = CPP_GATE.read_text(encoding='utf-8')
    match = re.search(
        r'if ! python - "\$line_pct" "\$cpp_lines_min" <<\'PY\'\n(.*?)\nPY\nthen',
        script,
        flags=re.DOTALL,
    )
    assert match, 'the C++ gate must expose its actual threshold comparator to the red control'
    control = subprocess.run(
        [sys.executable, '-', measured, '80'],
        input=match.group(1),
        text=True,
        capture_output=True,
        check=False,
    )
    assert control.returncode == expected_code, (
        'the live C++ comparator must fail below and pass at eighty percent: '
        + control.stdout
        + control.stderr
    )
