# SPDX-License-Identifier: BSD-3-Clause
"""The four-pattern LATP test project: the LATP scan case on four of its 73 patterns."""

from __future__ import annotations

import shutil
from pathlib import Path

from catalogue_common import CLI

SOURCE = CLI / 'pd-xray-cwl_latp-bm01_scan' / 'project'
FIXTURE = 'pd-xray-cwl_latp_scan-4f'
# The template first, then every 8th pattern below it, in the order the scan fits them (reverse).
# With every 24th, latp_240 seeded from latp_264 ends without a convergence verdict.
PATTERNS = ['latp_312.dat', 'latp_304.dat', 'latp_296.dat', 'latp_288.dat']


def pd_xray_cwl_latp_scan_4f() -> dict[str, str]:
    files = {
        path.relative_to(SOURCE).as_posix(): path.read_text(encoding='utf-8')
        for path in sorted(SOURCE.rglob('*.edi'))
    }
    record = files['project.edi']
    name = '_metadata.name             '
    description = '_metadata.description "3 phases · {} · Linked displacement parameters"'
    for old, new in (
        (name + 'pd-xray-cwl_latp-bm01_scan', name + FIXTURE),
        (
            description.format('73 synchrotron patterns'),
            description.format('4 of the 73 synchrotron patterns'),
        ),
    ):
        if record.count(old) != 1:
            raise SystemExit(f'{SOURCE / "project.edi"}: expected one {old!r}')
        record = record.replace(old, new)
    files['project.edi'] = record
    return files


def copy_patterns(project: Path) -> None:
    """The four patterns, copied byte for byte after the builder writes the project."""
    target = project / 'experiments' / 'bm01_scan'
    target.mkdir(parents=True, exist_ok=True)
    for name in PATTERNS:
        shutil.copyfile(SOURCE / 'experiments' / 'bm01_scan' / name, target / name)


CASES = {FIXTURE: pd_xray_cwl_latp_scan_4f}
AFTER = {FIXTURE: copy_patterns}
