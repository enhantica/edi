#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""The weak-reference policy gate (ADR-0013).

Production weak references are PROHIBITED in edi: ``nb::is_weak_referenceable()`` is test
instrumentation confined to the ADR's enumerated classes, and production ownership stays
``shared_ptr`` + ``keep_alive``. This gate enforces the prohibition as ONE parsed capability
class, not a pair of literal spellings:

- the PYTHON family is closed by construction: the stdlib ``weakref`` module is the capability's
  sole Python entry point, so ANY import of it (plain, aliased, from-import, or a literal
  dynamic ``importlib.import_module``/``__import__``) on a production path is red — alias closure
  rides the import graph rather than a token grep;
- the C++/binding family is a DECLARED spelling table (an enumerated family over an open
  language, held up by the runtime lifetime falsifiers and the ADR): the ratified set from the
  plan-accept row — ``std::weak_ptr``/``boost::weak_ptr``, ``weak_from_this``,
  ``PyWeakref_NewRef``/``PyWeakref_NewProxy``, direct ``tp_weaklistoffset`` enablement and
  ``nb::weakref`` — and nothing the pinned CPython/nanobind headers do not actually define;
- ``nb::is_weak_referenceable`` is admitted ONLY in the bindings registration file and only on
  exactly the ADR's enumerated classes;
- the test-path exclusion carries DEPENDENCY CLOSURE: a production module importing, or a
  production TU including, anything that resolves into a test path is itself red, so the
  put-it-in-a-test-helper escape is closed.

The capability-class table below is declared SEPARATELY from edi's path sets — the org-wide
test-only-capability registry (separately admitted) absorbs the table verbatim and drives it
over each repo's declared paths; nothing edi-specific is baked into the class definition.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# --- The capability class (repo-independent; the org registry's future input) -------------------

CAPABILITY = {
    # The sole stdlib entry point; importing it IS acquiring the capability. The API family is
    # recorded for the record/report, but detection closes over the import, not the names.
    'python': {
        'entry_module': 'weakref',
        'api_family': [
            'ref',
            'proxy',
            'WeakValueDictionary',
            'WeakKeyDictionary',
            'WeakSet',
            'WeakMethod',
            'finalize',
            'ReferenceType',
            'ProxyType',
            'CallableProxyType',
        ],
    },
    # The declared C++/binding spelling table (ratified 2026-09-22, the r15 accept row —
    # nb::weakref included; nothing the pinned headers do not define).
    'cpp': [
        'std::weak_ptr',
        'boost::weak_ptr',
        'weak_from_this',
        'PyWeakref_NewRef',
        'PyWeakref_NewProxy',
        'tp_weaklistoffset',
        'nb::weakref',
    ],
    # The registration flag, admissible only at the registration site on the enumerated classes.
    'registration_flag': 'is_weak_referenceable',
}

# --- edi's path sets (the repo-specific half the org registry replaces per repo) ----------------

PRODUCTION_PATHS = ['lib', 'core']
TEST_PATH_PREFIXES = ['tests']
REGISTRATION_FILE = Path('lib/src/bindings.cpp')
# ADR-0013's enumerated test-instrumentation classes (the one edge with no lender backedge;
# every other edge is falsified by lender-refcount-delta restoration at zero cost).
ALLOWED_WEAKREF_CLASSES = {'AtomSite', 'Structure', 'LineSegment', 'BraggPdExperiment'}

PY_SUFFIX = {'.py'}
CPP_SUFFIX = {'.cpp', '.hpp', '.h', '.cc', '.hh'}

# enable_shared_from_this is NOT in the prohibited table: it mints shared identity; the weak
# minting call is weak_from_this, which is.


def production_files() -> list[Path]:
    out: list[Path] = []
    for base in PRODUCTION_PATHS:
        root = ROOT / base
        if not root.is_dir():
            continue
        for path in sorted(root.rglob('*')):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if any(str(rel).startswith(f'{prefix}/') for prefix in TEST_PATH_PREFIXES):
                continue
            if path.suffix in PY_SUFFIX | CPP_SUFFIX:
                out.append(path)
    return out


def _is_test_module(name: str) -> bool:
    head = name.split('.', 1)[0]
    return head in {p.rstrip('/') for p in TEST_PATH_PREFIXES} or head == 'conftest'


def _resolve_local(name: str) -> Path | None:
    """Resolve a dotted module name to a repo-local file, wherever it lives."""
    parts = name.split('.')
    for base in (ROOT, ROOT / 'lib'):
        as_file = base.joinpath(*parts).with_suffix('.py')
        if as_file.is_file():
            return as_file
        as_pkg = base.joinpath(*parts) / '__init__.py'
        if as_pkg.is_file():
            return as_pkg
    return None


def _module_imports(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    except SyntaxError:
        return []
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def _reaches_weakref(name: str, seen: set[str]) -> list[str] | None:
    """Return the module chain through which *name* (a local module) reaches weakref."""
    entry = CAPABILITY['python']['entry_module']
    if name == entry or name.startswith(entry + '.'):
        return [name]
    if name in seen:
        return None
    seen.add(name)
    local = _resolve_local(name)
    if local is None:
        return None
    for imported in _module_imports(local):
        chain = _reaches_weakref(imported, seen)
        if chain is not None:
            return [name] + chain
    return None


def _check_dynamic_import(node: ast.Call, rel: str, entry: str, violations: list[str]) -> None:
    # Literal dynamic imports of the entry module.
    target = ''
    if isinstance(node.func, ast.Name) and node.func.id == '__import__':
        target = '__import__'
    elif isinstance(node.func, ast.Attribute) and node.func.attr == 'import_module':
        target = 'import_module'
    if target and node.args and isinstance(node.args[0], ast.Constant):
        value = node.args[0].value
        if isinstance(value, str) and (value == entry or value.startswith(entry + '.')):
            violations.append(
                f'{rel}:{node.lineno}: dynamic {target}({value!r}) acquires the '
                'weak-reference capability on a production path'
            )


def _check_import(node: ast.Import, rel: str, entry: str, violations: list[str]) -> None:
    for alias in node.names:
        if alias.name == entry or alias.name.startswith(entry + '.'):
            violations.append(
                f'{rel}:{node.lineno}: imports the weak-reference capability module '
                f'({alias.name!r}) on a production path'
            )
        if _is_test_module(alias.name):
            violations.append(
                f'{rel}:{node.lineno}: production module imports a test path '
                f'({alias.name!r}) — dependency closure'
            )
        else:
            chain = _reaches_weakref(alias.name, set())
            if chain:
                violations.append(
                    f'{rel}:{node.lineno}: production import reaches the weak-reference '
                    f'capability through a re-export chain ({" -> ".join(chain)})'
                )


def _check_import_from(node: ast.ImportFrom, rel: str, entry: str, violations: list[str]) -> None:
    module = node.module or ''
    if module == entry or module.startswith(entry + '.'):
        violations.append(
            f'{rel}:{node.lineno}: from-imports the weak-reference capability module '
            f'({module!r}) on a production path'
        )
    if _is_test_module(module):
        violations.append(
            f'{rel}:{node.lineno}: production module imports a test path '
            f'({module!r}) — dependency closure'
        )
    elif module:
        chain = _reaches_weakref(module, set())
        if chain:
            violations.append(
                f'{rel}:{node.lineno}: production import reaches the weak-reference '
                f'capability through a re-export chain ({" -> ".join(chain)})'
            )


def check_python(path: Path, rel: str, violations: list[str]) -> None:
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=rel)
    except SyntaxError as err:  # a production file that does not parse cannot be cleared
        violations.append(f'{rel}: unparseable production module ({err.msg}) — fail closed')
        return
    entry = CAPABILITY['python']['entry_module']
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            _check_import(node, rel, entry, violations)
        elif isinstance(node, ast.ImportFrom):
            _check_import_from(node, rel, entry, violations)
        elif isinstance(node, ast.Call):
            _check_dynamic_import(node, rel, entry, violations)


_INCLUDE = re.compile(r'^\s*#\s*include\s*["<]([^">]+)[">]', re.MULTILINE)
_CLASS_FLAG = re.compile(
    r'nb::class_<\s*edi::(\w+)[^;]*?nb::is_weak_referenceable\s*\(\s*\)', re.DOTALL
)
_CPP_COMMENT = re.compile(r'//[^\n]*|/\*.*?\*/', re.DOTALL)


def _strip_cpp_comments(text: str) -> str:
    # A comment cannot acquire a capability; newlines are preserved so line numbers hold.
    return _CPP_COMMENT.sub(lambda m: '\n' * m.group(0).count('\n'), text)


def check_cpp(path: Path, rel: str, violations: list[str], flagged: dict[str, str]) -> None:
    text = _strip_cpp_comments(path.read_text(encoding='utf-8', errors='replace'))
    is_registration_file = Path(rel) == REGISTRATION_FILE
    for spelling in CAPABILITY['cpp']:
        for match in re.finditer(re.escape(spelling), text):
            line = text.count('\n', 0, match.start()) + 1
            violations.append(
                f'{rel}:{line}: prohibited weak-reference spelling {spelling!r} on a '
                'production path'
            )
    flag = CAPABILITY['registration_flag']
    if flag in text:
        if not is_registration_file:
            line = text.count('\n', 0, text.find(flag)) + 1
            violations.append(
                f'{rel}:{line}: {flag!r} outside the registration file {REGISTRATION_FILE}'
            )
        else:
            for match in _CLASS_FLAG.finditer(text):
                flagged[match.group(1)] = rel
            declared = len(re.findall(re.escape(flag), text))
            matched = len(_CLASS_FLAG.findall(text))
            if declared != matched:
                violations.append(
                    f'{rel}: {declared} {flag!r} registrations but only {matched} resolve to a '
                    'nb::class_<edi::...> statement — unattributable flag, fail closed'
                )
    for match in _INCLUDE.finditer(text):
        target = match.group(1)
        if any(
            target.startswith(f'{prefix}/') or f'/{prefix}/' in target
            for prefix in TEST_PATH_PREFIXES
        ):
            line = text.count('\n', 0, match.start()) + 1
            violations.append(
                f'{rel}:{line}: production TU includes a test path ({target!r}) — dependency '
                'closure'
            )


def main() -> int:
    violations: list[str] = []
    flagged: dict[str, str] = {}
    for path in production_files():
        rel = str(path.relative_to(ROOT))
        if path.suffix in PY_SUFFIX:
            check_python(path, rel, violations)
        else:
            check_cpp(path, rel, violations, flagged)
    if set(flagged) != ALLOWED_WEAKREF_CLASSES:
        extra = sorted(set(flagged) - ALLOWED_WEAKREF_CLASSES)
        missing = sorted(ALLOWED_WEAKREF_CLASSES - set(flagged))
        detail = []
        if extra:
            detail.append(f'outside the ADR set: {extra}')
        if missing:
            detail.append(f'missing from the registration: {missing}')
        violations.append(
            'is_weak_referenceable registration set != ADR-0013 enumerated classes ('
            + '; '.join(detail)
            + ')'
        )
    if violations:
        print('weakref-policy: RED — the prohibited capability class is reachable:')
        for item in violations:
            print(f'  {item}')
        return 1
    print(
        'weakref-policy: OK — no production path acquires the weak-reference capability '
        f'({len(production_files())} files; flag confined to '
        f'{sorted(ALLOWED_WEAKREF_CLASSES)} in {REGISTRATION_FILE})'
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
