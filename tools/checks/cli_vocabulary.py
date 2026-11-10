#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Gate edi's advertised CLI and its reachability superset over pinned crysta."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import edi.__main__ as cli

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CRYSTA_FETCH = ROOT / 'build/crysta-src'
DEFAULT_CRYSTA_BINARY = ROOT / 'build/crysta-prefix/bin/crysta'
DEFAULT_EXCEPTIONS = ROOT / 'tests/fixtures/c11_t51_cli_superset/exceptions.toml'
EXCEPTION_KEYS = frozenset({'capability', 'issue', 'remove_after', 'reason'})
# The removal boundary every CLI exception row names: the ADR that settles which engine options
# edi's four surfaces expose decides them all at once.
BOUNDARY = 'four-surface-boundary'
CRYSTA_DESTINATION_OVERRIDES = {
    '--auto-cutoff': 'cutoff_policy',
    '--auto_cutoff': 'cutoff_policy',
    '--chi-square-tolerance': 'chi_square_tolerance',
    '--fast-descent': 'descent',
    '--ftol': 'chi_square_tolerance',
    '--guarded-linear-snap': 'descent',
    '--linear-snap': 'descent',
    '--no-ramp': 'cutoff_policy',
    '--out': 'output_file',
    '--parameter-tolerance': 'parameter_tolerance',
    '--ramp': 'cutoff_policy',
    '--rung': 'solver_rung',
    '--xtol': 'parameter_tolerance',
}


def subcommands(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    actions = [
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    ]
    if len(actions) != 1:
        raise ValueError(
            f'edi must have one argparse subcommand authority, observed {len(actions)}'
        )
    return dict(actions[0].choices)


def parser_help_findings(parser: argparse.ArgumentParser) -> list[str]:
    findings: list[str] = []
    parsers = {'<root>': parser, **subcommands(parser)}
    for command, current in parsers.items():
        rendered = current.format_help()
        findings.extend(
            f'help: {command}:{option} is accepted but absent'
            for action in current._actions
            for option in action.option_strings
            if option not in rendered
        )
    return sorted(findings)


def without_comments(source: str) -> str:
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
    return re.sub(r'(?m)//.*$', '', source)


def crysta_commands(source: str) -> set[str]:
    parser = source.split('Args parse_args', 1)[1].split('\nvoid write_results', 1)[0]
    return set(re.findall(r'std::string\(argv\[\d+\]\)\s*(?:==|!=)\s*"([a-z][a-z0-9-]*)"', parser))


def crysta_dry_commands(source: str) -> set[str]:
    starts = list(re.finditer(r'(?m)^int run_([a-z_]+)\([^\n]*\)\s*\{', source))
    commands: set[str] = set()
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(source)
        body = source[start.end() : end]
        if not re.search(r'if\s*\([^)]*!args\.dry', without_comments(body)):
            continue
        function = start.group(1)
        commands.add('fit' if function.endswith('_fit') else function)
    return commands


def crysta_listing_destinations(source: str) -> set[str]:
    parser = source.split('Args parse_args', 1)[1].split('\nvoid write_results', 1)[0]
    return {
        option.removeprefix('--').replace('-', '_')
        for option in re.findall(r'token\s*==\s*"(--list-[a-z0-9-]+)"', without_comments(parser))
    }


def crysta_parser_flags(source: str) -> set[str]:
    parser = source.split('Args parse_args', 1)[1].split('\nvoid write_results', 1)[0]
    parser = without_comments(parser)
    flags = set(re.findall(r'token\s*==\s*"(-{1,2}[a-z0-9_-]+)"', parser))
    flags.update(re.findall(r'flag\s*==\s*"(--[a-z0-9_-]+)"', parser))
    return flags


def crysta_honoured_project_flags(source: str) -> set[str]:
    """Derive spellings both parsed and admitted by the project-fit guard."""
    allowlist = source.split('bool is_project_supported_flag', 1)[1].split('\n}', 1)[0]
    admitted = set(re.findall(r'flag\s*==\s*"(--[a-z0-9_-]+)"', without_comments(allowlist)))

    def canonical(flag: str) -> str:
        return '--auto-cutoff' if flag == '--auto_cutoff' else flag

    return {flag for flag in crysta_parser_flags(source) if canonical(flag) in admitted}


def crysta_destination(flag: str) -> str:
    return CRYSTA_DESTINATION_OVERRIDES.get(flag, flag.lstrip('-').replace('-', '_'))


def crysta_capabilities(source: str) -> set[str]:
    commands = crysta_commands(source)
    capabilities = {f'command:{command}' for command in commands}
    honoured = crysta_honoured_project_flags(source)
    stale_mappings = CRYSTA_DESTINATION_OVERRIDES.keys() - honoured
    if stale_mappings:
        raise ValueError(f'stale crysta route mappings: {sorted(stale_mappings)}')
    capabilities.update(f'option:fit:{crysta_destination(flag)}' for flag in honoured)
    capabilities.update(f'option:{command}:dry' for command in crysta_dry_commands(source))
    capabilities.update(
        f'option:fit:{destination}' for destination in crysta_listing_destinations(source)
    )
    parser_flags = crysta_parser_flags(source)
    if {'-h', '--help'} <= parser_flags:
        capabilities.update(f'option:{command}:help' for command in commands)
    top_level = {
        option.removeprefix('--').replace('-', '_')
        for option in re.findall(
            r'std::string\(argv\[\d+\]\)\s*==\s*"(--[a-z0-9_-]+)"',
            without_comments(source),
        )
    }
    capabilities.update(f'option:<root>:{destination}' for destination in top_level)
    return capabilities


def edi_capabilities(parser: argparse.ArgumentParser) -> set[str]:
    commands = subcommands(parser)
    capabilities = {f'command:{command}' for command in commands}
    for command, subparser in commands.items():
        for action in subparser._actions:
            if action.option_strings:
                capabilities.add(f'option:{command}:{action.dest}')
    capabilities.update(
        f'option:<root>:{action.dest}' for action in parser._actions if action.option_strings
    )
    return capabilities


def read_exception_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        document = tomllib.loads(path.read_text(encoding='utf-8'))
    except (OSError, tomllib.TOMLDecodeError) as error:
        return [], [f'exceptions: cannot read {path}: {error}']
    findings: list[str] = []
    if document.get('schema') != 1:
        findings.append(f'exceptions: schema must be 1, observed {document.get("schema")!r}')
    if 'subset' not in str(document.get('directionality', '')):
        findings.append('exceptions: directionality must state the asymmetric subset relation')
    rows = document.get('exception', [])
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        return [], [*findings, 'exceptions: [[exception]] must be a list of tables']
    return rows, findings


def exception_registry_findings(exceptions: list[dict[str, Any]]) -> list[str]:
    findings: list[str] = []
    for row in exceptions:
        capability = str(row.get('capability', ''))
        if set(row) != EXCEPTION_KEYS:
            findings.append(
                f'exceptions: {capability or "<missing>"} must carry exactly '
                f'{sorted(EXCEPTION_KEYS)}'
            )
            continue
        # Retired the `command:calc` row — edi has calc, so a command-wide exception is no
        # longer admissible in any form: every remaining row is an exact option:* capability,
        # and a non-option capability gets exactly this one finding.
        if not re.fullmatch(r'option:(?:<root>|[a-z][a-z0-9-]*):[a-z][a-z0-9_]*', capability):
            findings.append(f'exceptions: {capability} must register an exact option:* capability')
            continue
        if row.get('issue') != BOUNDARY or row.get('remove_after') != BOUNDARY:
            findings.append(
                f'exceptions: {capability} must name {BOUNDARY} as issue and removal boundary'
            )
        if not str(row.get('reason', '')).strip():
            findings.append(f'exceptions: {capability} must carry a non-empty reason')
    return findings


def exception_matches(capability: str, registered: str) -> bool:
    """True iff the registered exception row covers this missing capability.

    Exact rows only. The retired command:calc row was the ONE exception authorized to cover a
    command's child options; with calc shipped, no wildcard survives it.
    """
    return capability == registered


def superset_findings(
    crysta: set[str], edi: set[str], exceptions: list[dict[str, Any]]
) -> list[str]:
    findings: list[str] = []
    missing = sorted(crysta - edi)
    for capability in missing:
        matches = [
            row
            for row in exceptions
            if exception_matches(capability, str(row.get('capability', '')))
        ]
        if len(matches) != 1:
            findings.append(f'superset: {capability} matched {len(matches)} exceptions')
    for row in exceptions:
        registered = str(row.get('capability', ''))
        if not any(exception_matches(capability, registered) for capability in missing):
            findings.append(f'superset: {registered} is a stale exception')
    return findings


def load_pinned_crysta_source(fetch: Path) -> tuple[str | None, list[str]]:
    sha_record = fetch / 'CRYSTA_SOURCE_SHA'
    source_path = fetch / 'src/cli/main.cpp'
    try:
        recorded = sha_record.read_text(encoding='utf-8').strip()
        result = subprocess.run(
            ['git', '-C', str(fetch), 'rev-parse', 'HEAD'],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            return None, [f'producer: cannot resolve fetched crysta HEAD: {result.stderr.strip()}']
        fetched = result.stdout.strip()
        if recorded != fetched:
            return None, [f'producer: recorded crysta {recorded!r} != fetched HEAD {fetched!r}']
        return source_path.read_text(encoding='utf-8'), []
    except OSError as error:
        return None, [f'producer: pinned crysta fetch is unavailable: {error}']


def listing_byte_findings(reference: bytes, candidate: bytes) -> list[str]:
    return (
        []
        if candidate == reference
        else ['descent-listing: edi output differs from pinned crysta']
    )


def edi_descents_record() -> bytes:
    """The descent registry edi links, rendered as crysta's ``fit --list-descents`` record.

    Retired edi's ``--list-descents`` (the descent is declared in analysis.edi, and edi's CLI
    carries no minimization condition), so the anti-drift comparison is aimed at the registry API
    edi resolves from the linked engine — the same ids its loader validates against.
    """
    import edi  # noqa: PLC0415 — the compiled registry, imported only where it is compared

    return (
        'schema=8\n'
        'record=descents\n'
        f'default={edi._default_descent()}\n'
        f'descents={",".join(edi._descent_ids())}\n'
    ).encode()


def descent_listing_findings(crysta_binary: Path) -> list[str]:
    try:
        reference = subprocess.run(
            [str(crysta_binary), 'fit', '--list-descents', '--version'],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        return [f'descent-listing: cannot execute pinned crysta: {error}']
    if reference.returncode != 0 or reference.stderr:
        oracle_stderr = reference.stderr.decode(errors='replace')
        return [
            (
                'descent-listing: pinned crysta oracle failed '
                f'(exit={reference.returncode}, stderr={oracle_stderr!r})'
            )
        ]
    return listing_byte_findings(reference.stdout, edi_descents_record())


def check_live(
    *,
    fetch: Path = DEFAULT_CRYSTA_FETCH,
    crysta_binary: Path = DEFAULT_CRYSTA_BINARY,
    exceptions_path: Path = DEFAULT_EXCEPTIONS,
) -> list[str]:
    """Return all findings against the live edi parser and the pinned crysta producer."""
    parser = cli.build_parser()
    findings = parser_help_findings(parser)
    rows, registry_findings = read_exception_rows(exceptions_path)
    findings.extend(registry_findings)
    findings.extend(exception_registry_findings(rows))
    source, producer_findings = load_pinned_crysta_source(fetch)
    findings.extend(producer_findings)
    if source is not None:
        try:
            findings.extend(
                superset_findings(crysta_capabilities(source), edi_capabilities(parser), rows)
            )
        except (IndexError, ValueError) as error:
            findings.append(f'superset: cannot derive the pinned crysta parser: {error}')
    findings.extend(descent_listing_findings(crysta_binary))
    return findings


def report(findings: list[str]) -> int:
    for finding in findings:
        print(f'cli-vocabulary: {finding}')
    if findings:
        print(f'cli-vocabulary: RED - {len(findings)} finding(s)')
        return 1
    print('cli-vocabulary: OK - help, crysta reachability, and descent listing agree')
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crysta-fetch', type=Path, default=DEFAULT_CRYSTA_FETCH)
    parser.add_argument('--crysta-binary', type=Path, default=DEFAULT_CRYSTA_BINARY)
    parser.add_argument('--exceptions', type=Path, default=DEFAULT_EXCEPTIONS)
    args = parser.parse_args(argv)
    try:
        findings = check_live(
            fetch=args.crysta_fetch,
            crysta_binary=args.crysta_binary,
            exceptions_path=args.exceptions,
        )
    except ValueError as error:
        findings = [f'parser: {error}']
    return report(findings)


if __name__ == '__main__':
    sys.exit(main())
