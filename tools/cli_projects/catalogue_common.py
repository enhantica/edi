# SPDX-License-Identifier: BSD-3-Clause
"""Shared pieces of the example catalogue builders: data loops, flat backgrounds, project files."""

from __future__ import annotations

import math
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / 'docs' / 'user' / 'cli'
# The one small isotropic displacement every fitted case starts from, on every site.
BISO = 0.5


def free(value: float | str) -> str:
    """A start value marked free."""
    return f'{value}()'


Row = tuple[str, str, str, float, float]


def read_points(path: Path, *, x_min: float = -math.inf, x_max: float = math.inf) -> list[Row]:
    """(x, y, su) rows of a plain two- or three-column data file; header lines are skipped.

    A file without uncertainties gets sqrt(y), with at least 1 so that no point has a zero sigma; a
    point whose stated uncertainty is zero or negative is left out, since edi refuses it.
    """
    rows = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            values = [float(p) for p in parts[:3]]
        except ValueError:
            continue
        x, y = values[0], values[1]
        if not x_min <= x <= x_max:
            continue
        su = values[2] if len(values) > 2 else math.sqrt(max(y, 1.0))
        if su <= 0:
            continue
        rows.append((parts[0], parts[1], parts[2] if len(values) > 2 else f'{su:.6g}', x, y))
    return rows


def data_loop(rows: list[Row], axis: str) -> list[str]:
    """The `_data` loop of an experiment; `axis` is two_theta or time_of_flight."""
    lines = ['loop_', f'_data.{axis}', '_data.intensity_meas', '_data.intensity_meas_su']
    lines += [f'{x} {y} {su}' for x, y, su, _, _ in rows]
    return lines


def two_significant(value: float) -> float:
    if value == 0:
        return 0.0
    digits = 1 - math.floor(math.log10(abs(value)))
    return round(value, digits)


def flat_level(rows: list[Row], excluded: list[tuple[float, float]] = ()) -> float:
    """A flat background a user would read off the pattern.

    The 10th percentile of the fitted intensities, to two significant figures.
    """
    ys = sorted(y for _, _, _, x, y in rows if not any(lo <= x <= hi for lo, hi in excluded))
    return two_significant(ys[len(ys) // 10])


def loop(names: list[str], rows: list[list[str]]) -> list[str]:
    return ['loop_', *names, *(' '.join(str(v) for v in row) for row in rows)]


def write_project(pid: str, files: dict[str, str], *, overwrite: bool) -> Path:
    """Write docs/user/cli/<pid>/project/ from relative path -> text.

    An existing tree is refused unless asked to overwrite it.
    """
    target = CLI / pid / 'project'
    if target.exists():
        if not overwrite:
            raise SystemExit(f'refusing: {target} exists')
        shutil.rmtree(target)
    for rel, text in files.items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text if text.endswith('\n') else text + '\n', encoding='utf-8')
    return target


def text(*blocks: str | list[str]) -> str:
    """Join blocks (strings or lists of lines) with a blank line between them."""
    parts = []
    for block in blocks:
        if isinstance(block, str):
            parts.append(block)
        else:
            parts.append('\n'.join(block))
    return '\n\n'.join(parts) + '\n'


def project_record(
    name: str,
    title: str,
    description: str,
    *,
    purpose: str = 'refinement',
    instrument: str | None = None,
    facility: str | None = None,
    neutron: bool = True,
) -> str:
    def quoted(value: str | None) -> str:
        return f'"{value}"' if value else '?'

    lines = [
        '_edi.schema_version 3',
        '',
        f'_metadata.name {name}',
        f'_metadata.title "{title}"',
        f'_metadata.description "{description}"',
        f'_metadata.purpose "{purpose}"',
        '_metadata.dimensionality "1D"',
        f'_metadata.instrument {quoted(instrument)}',
        f'_metadata.facility {quoted(facility)}',
    ]
    if neutron:
        lines.append('_metadata.polarisation "none"')
    return '\n'.join(lines) + '\n'


def structure(
    name: str,
    cell: list[str],
    group: str,
    sites: list[str],
    *,
    system: str | None = None,
    extra: list[str] = (),
) -> str:
    """A structure file.

    `sites` are atom_site rows: id type x y z wyckoff occupancy adp_iso adp_type.
    """
    head = [
        f'data_{name}',
        '',
        '_edi.schema_version 3',
        '',
        *cell,
        '',
        f'_space_group.name_h_m "{group}"',
    ]
    if system is not None:
        head.append(f'_space_group.coord_system_code {system}')
    site_loop = loop(
        [
            '_atom_site.id',
            '_atom_site.type_symbol',
            '_atom_site.fract_x',
            '_atom_site.fract_y',
            '_atom_site.fract_z',
            '_atom_site.wyckoff_letter',
            '_atom_site.occupancy',
            '_atom_site.adp_iso',
            '_atom_site.adp_type',
        ],
        [s.split() for s in sites],
    )
    blocks = [head, site_loop]
    if extra:
        blocks.append(list(extra))
    return text(*blocks)


def cell_lines(a, b, c, alpha=90, beta=90, gamma=90) -> list[str]:
    return [
        f'_cell.length_a {a}',
        f'_cell.length_b {b}',
        f'_cell.length_c {c}',
        f'_cell.angle_alpha {alpha}',
        f'_cell.angle_beta {beta}',
        f'_cell.angle_gamma {gamma}',
    ]
