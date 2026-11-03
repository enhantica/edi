"""Valid authored CIF inputs distinguish a deferred feature from a parse error."""

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CIF = """data_cif_only
_cell.length_a 5.1234
_cell.length_b 6.2345
_cell.length_c 7.3456
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_H-M_alt 'P 1'
loop_
_atom_site.label
_atom_site.type_symbol
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.B_iso_or_equiv
CifOnly La 0.173 0.281 0.397 0.63 0.47
"""


def text(style):
    if style == 'underscore':
        return re.sub(r'^(_\S+)', lambda m: m[1].replace('.', '_', 1), CIF, flags=re.MULTILINE)
    if style == 'upper':
        return re.sub(r'^(_\S+)', lambda m: m[1].upper(), CIF, flags=re.MULTILINE)
    if style == 'multiblock':
        return (
            'data_publication\n_cell.length_a ?\n_audit.note before\n'
            + CIF
            + '\ndata_later\n_cell.length_a 8.9\n'
        )
    return CIF


def project(directory):
    destination = directory / 'project'
    shutil.copytree(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', destination)
    return destination


def poisoned_project(directory, style, layout):
    destination = project(directory)
    filename = {'distinct': 'cif_only.cif', 'shadow': 'phase.cif', 'upper-suffix': 'cif_only.CIF'}[
        layout
    ]
    (destination / 'structures' / filename).write_text(text(style))
    return destination


def snapshot(directory):
    return {
        str(p.relative_to(directory)): p.read_bytes() for p in directory.rglob('*') if p.is_file()
    }


def saved_model(directory):
    return {
        name: data
        for name, data in snapshot(directory).items()
        if name.startswith(('structures/', 'experiments/', 'analysis/'))
    }
