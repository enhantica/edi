# SPDX-License-Identifier: BSD-3-Clause
"""Build the example catalogue's projects, each from the start a user's own measurement would have.

Every fitted case starts the same way: zero shift 0, peak-profile parameters only roughly right
(one significant figure, asymmetry 0), the same small isotropic displacement (Biso 0.5) on every
site, free coordinates rounded to two decimals, and a flat background at the level a user would
read off the pattern (`catalogue_common.flat_level`). The free set is what a user fits: scale,
zero shift, cell, profile, background, free coordinates and displacements. Each case's
PROVENANCE.md names its model and data sources and any case-specific choice.

Usage (writes ``docs/user/cli/<id>/project/``)::

    pixi run python tools/cli_projects/build_catalogue_projects.py <id> [<id> ...] [--overwrite]
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

import edi
from catalogue_common import CLI, write_project

# Every sibling catalogue_<group>.py module contributes its CASES.
GROUPS = [
    importlib.import_module(path.stem)
    for path in sorted(Path(__file__).parent.glob('catalogue_*.py'))
    if path.stem != 'catalogue_common'
]
CASES = {pid: build for group in GROUPS for pid, build in group.CASES.items()}
AFTER = {pid: step for group in GROUPS for pid, step in getattr(group, 'AFTER', {}).items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('ids', nargs='*', help='the case ids to build (default: all)')
    parser.add_argument('--overwrite', action='store_true', help='replace an existing project/')
    args = parser.parse_args(argv)
    unknown = sorted(set(args.ids) - set(CASES))
    if unknown:
        print(f'unknown case ids: {unknown}', file=sys.stderr)
        return 1
    for pid in args.ids or CASES:
        target = write_project(pid, CASES[pid](), overwrite=args.overwrite)
        if pid in AFTER:
            AFTER[pid](target)
        edi.Project.load(str(target))  # the loader's refusals, before anything is kept
        print(f'built {target.relative_to(CLI.parents[2])}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
