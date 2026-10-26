"""Hand-written complement constraint with derivative minus one."""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def project_input(destination, *, with_su=False):
    shutil.copytree(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', destination)
    structure = destination / 'structures/phase.edi'
    text = structure.read_text().replace('0.31 0.7 0.3', '0.31 0.58 0.3')
    if with_su:
        text = text.replace('0.31 0.58 0.3', '0.31 0.58(3) 0.3')
        text = text.replace('0.31 0.3 0.8', '0.31 0.42(3) 0.8')
    structure.write_text(text)
    analysis = destination / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text() + '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
        'a phase.atom_site.A.occupancy\nb phase.atom_site.B.occupancy\n'
        'loop_\n_constraint.expression\n"b = 1 - a"\n'
    )
    return destination
