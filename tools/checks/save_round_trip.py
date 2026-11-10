#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Check that a fitted project with anisotropic sites saves and reloads without warnings.

An anisotropic site's adp_iso is its tensor's equivalent value. A save that wrote its s.u. made the
reload read the bracket as a free flag on a dependent parameter, and every reload warned. This fits
the Pr2NiO4 case (anisotropic, a second to fit), saves it, refuses a bracket after any anisotropic
site's adp_iso in the saved file, then reloads it and refuses any warning.

    python tools/checks/save_round_trip.py
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

import easydiffraction as edi

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / 'docs/user/cli/sc-neut-cwl_pr2nio4-5c2/project'


def main() -> int:
    with tempfile.TemporaryDirectory() as scratch:
        copy = Path(scratch) / 'project'
        shutil.copytree(CASE, copy)
        project = edi.Project.load(str(copy))
        project.analysis.fit()
        project.save()
        problems = []
        for structure in sorted((copy / 'structures').glob('*.edi')):
            for line in structure.read_text(encoding='utf-8').splitlines():
                cells = line.split()
                # An atom-site row: its adp_iso is the cell before the ADP type at its end.
                if (
                    len(cells) > 2
                    and cells[-1] in {'Bani', 'Uani', 'beta'}
                    and re.search(r'\(', cells[-2])
                ):
                    problems.append(f'{structure.name}: {cells[0]} adp_iso saved as {cells[-2]}')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            edi.Project.load(str(copy))
        problems += [f'reload warns: {warning.message}' for warning in caught]
    if problems:
        print('save round trip: ' + '\n'.join(problems))
        return 1
    print('save round trip: an anisotropic fit saves and reloads with no warnings')
    return 0


if __name__ == '__main__':
    sys.exit(main())
