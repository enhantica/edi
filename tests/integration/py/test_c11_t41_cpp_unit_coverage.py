"""Acceptance gates for  unit 6's edi C++ unit and coverage tiers."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _edi_tests_link_findings(cmake: str) -> list[str]:
    link_blocks = re.findall(
        r'target_link_libraries\s*\(\s*edi_tests\s+PRIVATE(?P<libraries>.*?)\)',
        cmake,
        flags=re.DOTALL,
    )
    if len(link_blocks) != 1:
        return [
            f'edi_tests must have exactly one PRIVATE link declaration, found {len(link_blocks)}'
        ]
    if '"$<LINK_LIBRARY:WHOLE_ARCHIVE,edi_core>"' not in link_blocks[0]:
        return ['edi_tests must link the whole edi_core archive into the coverage denominator']
    return []


def test_edi_cpp_unit_tier_is_one_excluded_doctest_binary() -> None:
    cmake = (ROOT / 'core/CMakeLists.txt').read_text(encoding='utf-8')
    declarations = re.findall(
        r'add_executable\s*\(\s*edi_tests\s+EXCLUDE_FROM_ALL',
        cmake,
        flags=re.DOTALL,
    )
    assert len(declarations) == 1
    for required in (
        'find_package(doctest CONFIG QUIET)',
        'tests/unit/cpp/test_*.cpp',
        'tools/probes/edi_tests_main.cpp',
        'add_test(NAME edi_unit COMMAND edi_tests)',
        'edi_tests_case_files.txt',
    ):
        assert required in cmake
    assert _edi_tests_link_findings(cmake) == [], (
        'edi_tests must whole-archive edi_core so every core translation unit remains in the '
        'coverage denominator'
    )

    ordinary_static_link = cmake.replace('"$<LINK_LIBRARY:WHOLE_ARCHIVE,edi_core>"', 'edi_core')
    assert _edi_tests_link_findings(ordinary_static_link) == [
        'edi_tests must link the whole edi_core archive into the coverage denominator'
    ], 'the gate must reject a regression to demand-linked static-library coverage'

    entrypoint = (ROOT / 'tools/probes/edi_tests_main.cpp').read_text(encoding='utf-8')
    assert entrypoint.count('DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN') == 1
    assert list((ROOT / 'tests/unit/cpp').glob('test_*.cpp')), (
        'a green C++ tier must contain at least one test-owned doctest source'
    )


def test_cpp_test_is_a_per_commit_gate_once_the_tier_has_cases() -> None:
    manifest = tomllib.loads((ROOT / 'pixi.toml').read_text(encoding='utf-8'))
    tasks = manifest['tasks']
    assert tasks['cpp-test']['cmd'] == ['bash', 'tools/ci/cpp-test.sh']
    # : the tier rides the declared groups, and the full group is in the verify chain.
    assert 'cpp-test' in tasks['group-full']['depends-on'], (
        'the tier now has test-owned cases, so the temporary empty-tier routing exception is over'
    )
    assert 'group-full' in tasks['verify-full']['depends-on'], (
        'the full verification entry point must execute the declared full group'
    )


def test_cpp_coverage_port_is_isolated_explicit_total_and_report_only() -> None:
    manifest = tomllib.loads((ROOT / 'pixi.toml').read_text(encoding='utf-8'))
    assert manifest['tasks']['cpp-coverage-unit']['cmd'] == [
        'bash',
        'tools/ci/cpp-coverage-unit.sh',
    ]
    assert manifest['target']['linux-64']['dependencies'] == {
        'clangxx': '22.*',
        'llvm-tools': '22.*',
    }

    source = (ROOT / 'tools/ci/cpp-coverage-unit.sh').read_text(encoding='utf-8')
    for required in (
        'TREE=build/coverage-unit',
        'export OMP_NUM_THREADS=1',
        '-DCMAKE_C_COMPILER=clang',
        '-DCMAKE_CXX_COMPILER=clang++',
        '-O0 -fprofile-instr-generate -fcoverage-mapping',
        'mktemp -d "$TREE/profraw.XXXXXX"',
        '[ -s "$profile" ]',
        'ran=$(grep',
        'llvm-cov report',
        'llvm-cov export',
        #  (ruling 6712bee0): the line minimum is a GATE declared in pyproject.toml.
        '[tool.edi.coverage] cpp_lines_min',
        'gate: line coverage >=',
    ):
        assert required in source
    merge_calls = [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith('llvm-profdata merge')
    ]
    assert merge_calls == ['llvm-profdata merge -sparse "$profile" -o "$TREE/merged.profdata"']
    assert '*.profraw' not in merge_calls[0], 'a glob can silently merge a successful subset'
