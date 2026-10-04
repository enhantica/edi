""": production weak-reference capability is closed as one class."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / 'tools/checks/weakref_policy.py'
POLICY_ADR = ROOT / 'docs/dev/adrs/0013-weak-reference-policy.md'
PYTHON_APIS = (
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
)
CPP_CAPABILITIES = {
    'std-weak-ptr': 'std::weak_ptr<int> c34_reference;',
    'boost-weak-ptr': 'boost::weak_ptr<int> c34_reference;',
    'weak-from-this': 'auto c34_reference = value.weak_from_this();',
    'cpython-new-ref': 'auto *c34_reference = PyWeakref_NewRef(value, nullptr);',
    'cpython-new-proxy': 'auto *c34_reference = PyWeakref_NewProxy(value, nullptr);',
    'weak-list-offset': 'type.tp_weaklistoffset = 24;',
    'nanobind-flag': ('nb::class_<Forbidden>(module, "Forbidden", nb::is_weak_referenceable());'),
    'nanobind-weakref': 'nb::weakref c34_reference(value);',
}
ALLOWED_FLAG_CLASSES = ('Structure', 'BraggPdExperiment', 'AtomSite', 'LineSegment')


def _run(checkout: Path) -> subprocess.CompletedProcess[str]:
    checker = checkout / CHECKER.relative_to(ROOT)
    return subprocess.run(
        [sys.executable, os.fspath(checker)],
        cwd=checkout,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def _baseline(tmp_path: Path) -> Path:
    assert CHECKER.is_file(), (
        ' I13 requires tools/checks/weakref_policy.py to gate the capability class'
    )
    assert POLICY_ADR.is_file(), (
        ' I13 requires ADR 0013 to own the production weak-reference prohibition'
    )
    baseline = tmp_path / 'baseline'
    for relative in ('core', 'lib', 'tools/checks', 'docs/dev/adrs', 'data'):
        source = ROOT / relative
        if source.exists():
            shutil.copytree(source, baseline / relative)
    for relative in ('pixi.toml', 'pyproject.toml'):
        source = ROOT / relative
        if source.exists():
            destination = baseline / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    control = _run(baseline)
    assert control.returncode == 0, (
        ' weakref-policy fixture must begin from the ordinary green product tree; '
        f'output={control.stdout}{control.stderr}'
    )
    return baseline


def _case_from(baseline: Path, destination: Path) -> Path:
    shutil.copytree(baseline, destination, copy_function=os.link)
    return destination


def _write(case: Path, relative: str, text: str) -> None:
    path = case / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _assert_red(case: Path, *, channel: str, required_path: str) -> None:
    result = _run(case)
    output = result.stdout + result.stderr
    assert result.returncode != 0, (
        f' weakref capability channel {channel} must be rejected; output={output}'
    )
    assert required_path in output, (
        f' weakref rejection for {channel} must identify the reached production path; '
        f'output={output}'
    )


def test_c34_t1a_python_capability_closure_reaches_every_api_and_import_route(
    tmp_path: Path,
) -> None:
    baseline = _baseline(tmp_path)
    case_number = 0
    for api in PYTHON_APIS:
        sources = {
            'from-alias': f'from weakref import {api} as capability\nvalue = capability\n',
            'module-alias': f'import weakref as refs\nvalue = refs.{api}\n',
        }
        for route, source in sources.items():
            case_number += 1
            case = _case_from(baseline, tmp_path / f'python-{case_number}')
            relative = 'lib/edi/c34_weakref_poison.py'
            _write(case, relative, source)
            _assert_red(case, channel=f'Python {api} via {route}', required_path=relative)

        case_number += 1
        case = _case_from(baseline, tmp_path / f'python-{case_number}')
        helper = 'tools/checks/c34_weakref_export.py'
        consumer = 'lib/edi/c34_weakref_consumer.py'
        _write(
            case,
            helper,
            f'from weakref import {api} as exported\n__all__ = ["exported"]\n',
        )
        _write(case, consumer, 'from tools.checks.c34_weakref_export import exported\n')
        _assert_red(
            case,
            channel=f'Python {api} via re-export closure',
            required_path=consumer,
        )


def test_c34_t1a_cpp_capability_table_reaches_every_declared_spelling(tmp_path: Path) -> None:
    baseline = _baseline(tmp_path)
    for index, (channel, spelling) in enumerate(CPP_CAPABILITIES.items()):
        case = _case_from(baseline, tmp_path / f'cpp-{index}')
        relative = 'core/src/c34_weakref_poison.cpp'
        _write(case, relative, f'void c34_poison() {{ {spelling} }}\n')
        _assert_red(case, channel=channel, required_path=relative)


@pytest.mark.parametrize(
    ('language', 'helper', 'consumer', 'source'),
    [
        (
            'Python',
            'tests/c34_weakref_helper.py',
            'lib/edi/c34_dependency_poison.py',
            'from tests.c34_weakref_helper import capability\n',
        ),
        (
            'C++',
            'tests/c34_weakref_helper.hpp',
            'core/src/c34_dependency_poison.cpp',
            '#include "tests/c34_weakref_helper.hpp"\n',
        ),
    ],
)
def test_c34_t1a_production_cannot_depend_on_a_test_capability_helper(
    tmp_path: Path,
    language: str,
    helper: str,
    consumer: str,
    source: str,
) -> None:
    baseline = _baseline(tmp_path)
    case = _case_from(baseline, tmp_path / f'dependency-{language.casefold()}')
    helper_source = (
        'from weakref import ref as capability\n'
        if language == 'Python'
        else 'using capability = std::weak_ptr<int>;\n'
    )
    _write(case, helper, helper_source)
    _write(case, consumer, source)
    _assert_red(
        case,
        channel=f'{language} production-to-test dependency closure',
        required_path=consumer,
    )


def test_c34_t1a_declared_spelling_table_matches_the_pinned_capabilities() -> None:
    assert CHECKER.is_file(), ' weakref policy checker must exist before its table is audited'
    source = CHECKER.read_text(encoding='utf-8')
    assert 'nb::weakref' in source, ' capability table must include nanobind 2.13.0 nb::weakref'
    assert 'Py_tp_weaklist' not in source, (
        ' capability table must not carry the nonexistent Py_tp_weaklist spelling'
    )


def test_c34_t1a_binding_flag_set_is_exactly_the_four_instrumented_items() -> None:
    bindings = ROOT / 'lib/src/bindings.cpp'
    source = bindings.read_text(encoding='utf-8')
    flagged = set(
        re.findall(
            r'nb::class_<\s*(?:edi::)?([A-Za-z_]\w*)[^;]{0,600}?is_weak_referenceable',
            source,
            re.DOTALL,
        )
    )
    assert flagged == set(ALLOWED_FLAG_CLASSES), (
        ' bindings must make exactly Structure, BraggPdExperiment, AtomSite, and '
        f'LineSegment weak-referenceable; observed declared classes={sorted(flagged)}'
    )


def test_c34_t1a_weakref_policy_is_wired_into_both_verify_chains() -> None:
    pixi = (ROOT / 'pixi.toml').read_text(encoding='utf-8')
    assert 'weakref-policy' in pixi or 'weakref_policy.py' in pixi, (
        ' weakref checker must have a named pixi task or direct task invocation'
    )
    for task in ('verify-quick', 'verify-full'):
        marker = f'{task} ='
        start = pixi.find(marker)
        assert start >= 0, f' fixture must resolve the existing {task} task'
        end = pixi.find('\n', start)
        declaration = pixi[start : end if end >= 0 else len(pixi)]
        assert 'weakref' in declaration, (
            f' weakref policy gate must run inside {task}, not remain an optional tool'
        )
