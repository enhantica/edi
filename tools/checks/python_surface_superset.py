#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""edi-py carries crysta-py's declared public names — the existence gate.

crysta declares its public Python interface in a committed file, ``data/python-surface.json``,
that crysta's C++ package installs at ``share/crysta/python-surface.json``. This check reads that
file from the prefix edi's own ``core-build`` populates (``build/crysta-prefix``; or
``build/crysta-consumer-prefix`` when ``EDI_USE_CONSUMER_BUILD`` selects the crysta->edi consumer
direction, exactly as ``tools/ci/core-build.sh`` does), imports the built ``edi`` package, and
proves that every declared name exists in edi and, for a declared class, that every declared
member exists on edi's class — ``__all__`` and ``dir()`` on crysta's side, attribute lookup on
edi's. That is the rule that crysta may not get ahead of edi, and nothing more (the gate checks
existence, and real scripts prove behaviour"): no signature, default, type, base chain or
behaviour is compared here. Whether a script works under ``s/crysta/edi/`` is demonstrated by
crysta's substitution scripts (``tools/substitution/``), which run against both libraries and
compare results for the paths they cover. It reports OK only at zero findings — there is no
register and no allow-list.

It never imports crysta-py: the committed manifest is the seam, so edi's environment never needs
the crysta extension. See ``EXISTENCE_LIMIT``.

Where it runs. While the fetched crysta main predates the declaration, this
checker can only refuse against edi's own prefix, so it is not in edi's ``verify-quick`` /
``verify-full`` chains yet; edi's own verify proves the refusal branch through the hidden
installed-prefix gate, and the real existence property is proven at crysta's pull-request gate,
which builds edi against the PR's crysta tree into the consumer prefix and runs this checker there.
Moving the pin to a crysta that carries the declaration, and adding the task back to both chains,
is the follow-up that makes edi's own verify prove the property again (see ``pixi.toml``).
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
import types
from pathlib import Path
from typing import Any

SCHEMA = 4
DIRECTIONALITY = (
    'crysta-py ⊆ edi-py is a standing constraint on edi: a name enters crysta.__all__ only in a '
    "commit where edi carries it; a public crysta name edi lacks is red at crysta's PR consumer "
    "job today, and at edi's verify against the pinned crysta once edi's tools/ci/crysta.pin "
    'carries the declaration — crysta cannot add a public name without edi '
    'following'
)
EXISTENCE_LIMIT = (
    'This check proves EXISTENCE only: every declared name, and every declared member of a '
    'declared class, resolves in edi by attribute lookup - the rule that crysta may not get ahead '
    'of edi, and nothing more. It records and compares no signature, default, type, base chain or '
    'behaviour - surface existence, never semantics; whether refine computes the same thing on '
    'both is demonstrated by the substitution scripts (crysta tools/substitution/) for the paths '
    'they cover and proven by tests, never by this gate.'
)
SCHEMA_BOUND = (
    f'Schema v{SCHEMA} is generated internal data, not hostile input: this check does not '
    'exhaustively reject malformed public-record shape.'
)
MODULE_NAME = 'edi'
MANIFEST_RELATIVE = Path('share') / 'crysta' / 'python-surface.json'
BUILD_REMEDY = 'run `pixi run core-build` first (it installs the pinned crysta into the prefix)'


# ---------------------------------------------------------------------------------------------
# The comparison: existence, by attribute lookup.
# ---------------------------------------------------------------------------------------------
def check_header(manifest: dict[str, Any]) -> list[str]:
    """Return the findings against the manifest header (schema and direction)."""
    findings = []
    if manifest.get('schema') != SCHEMA:
        findings.append(f'header: schema {manifest.get("schema")!r} is not {SCHEMA}')
    # crysta's text may carry a parenthetical citation of its private records; edi states the same
    # direction without it, so the comparison reads both without parentheticals.
    stated = re.sub(r' \([^()]*\)', '', str(manifest.get('directionality', '')))
    if stated != DIRECTIONALITY:
        findings.append('header: directionality text does not state the I6 direction')
    return findings


def check_name(module: types.ModuleType, name: str, record: Any) -> list[str]:  # noqa: ANN401
    """Return the findings for one declared public name: it and its declared members exist."""
    if not hasattr(module, name):
        return [f'{name}: absent in edi']
    members = record.get('members', []) if isinstance(record, dict) else []
    live = getattr(module, name)
    return [
        f'{name}.{member}: absent in edi'
        for member in members
        if isinstance(member, str) and not hasattr(live, member)
    ]


def check_manifest(manifest: dict[str, Any], module: types.ModuleType) -> list[str]:
    """Return every finding of the manifest's ``public`` section against the live edi package."""
    findings = check_header(manifest)
    public = manifest.get('public', {})
    if not isinstance(public, dict):
        return [*findings, 'public: section is not a mapping of declared names']
    for name, record in sorted(public.items()):
        findings.extend(check_name(module, str(name), record))
    return findings


# ---------------------------------------------------------------------------------------------
# Prefix resolution (mirrors tools/ci/core-build.sh) and the CLI.
# ---------------------------------------------------------------------------------------------
def resolve_prefix(root: Path, environ: dict[str, str]) -> Path:
    """Return the crysta prefix ``core-build`` populates under this environment."""
    # ONE definition of the consumer selection, shared verbatim by all four sites —
    # lib/edi/__init__.py, lib/edi/verification.py (_consumer_source_selects),
    # tools/ci/crysta-consumer.sh and here: the explicit EDI_USE_CONSUMER_BUILD selector, the
    # hidden control's exact literal (exempt BY NAME), or a CRYSTA_CONSUMER_SRC carrying the
    # source-tree witness CMakeLists.txt. Never a bare string or a mere existing directory — two
    # components disagreeing about which tree is in play is the defect names.
    src = environ.get('CRYSTA_CONSUMER_SRC', '')
    selects = src == 'hidden-surface-control' or (
        bool(src) and (Path(src) / 'CMakeLists.txt').is_file()
    )
    if environ.get('EDI_USE_CONSUMER_BUILD') or selects:
        return root / 'build' / 'crysta-consumer-prefix'
    return root / 'build' / 'crysta-prefix'


def _emit(line: str) -> None:
    sys.stdout.write(line + '\n')


def _counts(manifest: dict[str, Any]) -> tuple[int, int]:
    public = manifest.get('public', {})
    if not isinstance(public, dict):
        return 0, 0
    members = sum(
        len(record.get('members', [])) for record in public.values() if isinstance(record, dict)
    )
    return len(public), members


def report(findings: list[str], manifest: dict[str, Any] | None) -> int:
    """Print the findings (or the OK line) and the standing bounds; return the exit code."""
    for finding in findings:
        _emit(finding)
    if findings:
        _emit(f'python-surface superset: RED - {len(findings)} finding(s)')
        _emit(DIRECTIONALITY)
    else:
        names, members = _counts(manifest or {})
        _emit(f'python-surface superset OK - {names} name(s), {members} member(s) exist in edi')
    _emit(EXISTENCE_LIMIT)
    _emit(SCHEMA_BOUND)
    return 1 if findings else 0


def main(argv: list[str] | None = None) -> int:
    """Entry point: read the installed manifest and prove edi carries its declared names."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--prefix', type=Path, help='override the resolved crysta prefix')
    parser.add_argument('--manifest', type=Path, help='override the manifest file itself')
    args = parser.parse_args(argv)
    prefix = args.prefix or resolve_prefix(args.root, dict(os.environ))
    manifest_path = args.manifest or prefix / MANIFEST_RELATIVE
    if not manifest_path.is_file():
        message = (
            f'manifest: {manifest_path} is absent - the crysta prefix carries no python-surface '
            f'declaration; {BUILD_REMEDY}; a crysta older than the declaration cannot be '
            f'proven and is refused, never skipped'
        )
        return report([message], None)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    module = importlib.import_module(MODULE_NAME)
    return report(check_manifest(manifest, module), manifest)


if __name__ == '__main__':
    sys.exit(main())
