"""confidential controls for the visible edi CLI vocabulary checker."""

from __future__ import annotations

import argparse
import importlib.util
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / 'tools/checks/cli_vocabulary.py'
EXCEPTIONS = ROOT / 'tests/fixtures/c11_t51_cli_superset/exceptions.toml'


def _i0163_row(capability: str = 'option:fit:solver_rung') -> dict[str, str]:
    return {
        'capability': capability,
        'issue': 'four-surface-boundary',
        'remove_after': 'four-surface-boundary',
        'reason': 'the four-surface boundary is deferred to its ADR task',
    }


def _checker():
    spec = importlib.util.spec_from_file_location('edi_cli_vocabulary', CHECKER)
    assert spec is not None and spec.loader is not None, (
        ' control: the visible edi CLI checker must be importable'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parser_help_checker_rejects_a_suppressed_option() -> None:
    checker = _checker()
    parser = argparse.ArgumentParser(prog='seed')
    subcommands = parser.add_subparsers(dest='command', required=True)
    fit = subcommands.add_parser('fit')
    fit.add_argument('--not-advertised', help=argparse.SUPPRESS)
    assert checker.parser_help_findings(parser) == [
        'help: fit:--not-advertised is accepted but absent'
    ], ' control: an accepted argparse option suppressed from help must be red'


def test_superset_checker_rejects_unregistered_duplicate_and_stale_exceptions() -> None:
    checker = _checker()
    rows = [_i0163_row()]
    unregistered = checker.superset_findings(
        {'command:fit', 'command:new', 'option:fit:solver_rung'}, {'command:fit'}, rows
    )
    assert unregistered == ['superset: command:new matched 0 exceptions'], (
        ' control: a new crysta command without an exception must be red'
    )
    stale = checker.superset_findings({'command:fit'}, {'command:fit'}, rows)
    assert stale == ['superset: option:fit:solver_rung is a stale exception'], (
        ' control: a resolved exact option divergence must retire its exception'
    )
    duplicate = checker.superset_findings(
        {'command:fit', 'option:fit:solver_rung'}, {'command:fit'}, [*rows, *rows]
    )
    assert duplicate == ['superset: option:fit:solver_rung matched 2 exceptions'], (
        ' control: each real divergence must match exactly one exception'
    )


def test_crysta_honoured_set_requires_parser_and_project_guard_agreement() -> None:
    checker = _checker()
    source = """
bool is_project_supported_flag(const std::string& flag) {
    return flag == "--honoured" || flag == "--allowlist-only";
}
Args parse_args(int argc, char** argv) {
    if (token == "--honoured") {}
    else if (token == "--parser-only") {}
}
void write_results() {}
"""
    assert checker.crysta_honoured_project_flags(source) == {'--honoured'}, (
        ' control: a refused parser spelling and a dead allow-list spelling are not '
        'capabilities edi must reach'
    )


def test_non_calc_exceptions_must_name_the_boundary_issue() -> None:
    checker = _checker()
    row = _i0163_row()
    assert checker.exception_registry_findings([row]) == [], (
        ' control: exact non-calc divergences name the deferred boundary question'
    )
    assert checker.superset_findings({'command:fit'}, {'command:fit'}, [row]) == [
        'superset: option:fit:solver_rung is a stale exception'
    ], ' control: resolving an four-surface-boundary divergence must retire its exact row'
    wrong = {**row, 'issue': 'edi:'}
    assert checker.exception_registry_findings([wrong]) == [
        (
            'exceptions: option:fit:solver_rung must name four-surface-boundary as '
            'issue and removal boundary'
        )
    ], ' control: a non-calc exception cannot lose the owner-directed issue'
    retired_calc = {
        'capability': 'command:calc',
        'issue': 'edi:',
        'remove_after': '',
        'reason': 'retired once edi exposes calc',
    }
    assert checker.exception_registry_findings([retired_calc]) == [
        'exceptions: command:calc must register an exact option:* capability'
    ], ' control: the retired calc command exception must no longer be admissible'


def test_non_calc_command_exceptions_cannot_wildcard_exact_option_gaps() -> None:
    checker = _checker()
    broad_fit = {
        'capability': 'command:fit',
        'issue': 'four-surface-boundary',
        'remove_after': 'four-surface-boundary',
        'reason': 'broad replacement for every missing fit option',
    }
    broad_root = {
        'capability': 'command:<root>',
        'issue': 'four-surface-boundary',
        'remove_after': 'four-surface-boundary',
        'reason': 'broad replacement for every missing root option',
    }
    registry_findings = checker.exception_registry_findings([
        broad_fit,
        broad_root,
    ])
    assert {
        'exceptions: command:fit must register an exact option:* capability',
        'exceptions: command:<root> must register an exact option:* capability',
    } <= set(registry_findings), (
        ' control: every four-surface-boundary divergence must remain an exact '
        'self-retiring option row'
    )
    missing = {
        'option:fit:solver_rung',
        'option:fit:output_file',
        'option:<root>:build_commit',
    }
    superset_findings = checker.superset_findings(missing, set(), [broad_fit, broad_root])
    assert all(
        f'superset: {capability} matched 0 exceptions' in superset_findings
        for capability in missing
    ), ' control: broad command rows cannot cover any exact option gap'


def test_calc_exception_is_retired_without_wildcarding_child_options() -> None:
    checker = _checker()
    assert not checker.exception_matches('option:calc:dry', 'command:calc'), (
        ' control: a retired command:calc row must not cover future child options'
    )
    document = tomllib.loads(EXCEPTIONS.read_text(encoding='utf-8'))
    rows = document['exception']
    capabilities = {row['capability'] for row in rows}
    expected = {
        'option:<root>:build_commit',
        'option:<root>:perf_info',
        'option:fit:chi_square_tolerance',
        'option:fit:cutoff_policy',
        'option:fit:descent',
        'option:fit:list_descents',
        'option:fit:output_file',
        'option:fit:parameter_tolerance',
        'option:fit:perf_info',
        'option:fit:solver_rung',
    }
    assert capabilities == expected, (
        '/ control: keep calc retired and register exactly the declared '
        f'four-surface-boundary exceptions, observed {sorted(capabilities)}'
    )
    assert all(row['issue'] == row['remove_after'] == 'four-surface-boundary' for row in rows), (
        ' control: every retained row must remain bound to four-surface-boundary'
    )


def test_descent_listing_checker_rejects_non_byte_equal_output() -> None:
    checker = _checker()
    assert checker.listing_byte_findings(b'{"schema":1}\n', b'{"schema":2}\n') == [
        'descent-listing: edi output differs from pinned crysta'
    ], ' control: any byte-level registry divergence must make the checker red'
