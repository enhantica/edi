"""Write a sparse P1 input from the independently published element inventory."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def generate():
    with (ROOT / 'tests/fixtures/e04_t10/published-elements.tsv').open() as stream:
        symbols = [row['symbol'] for row in csv.DictReader(stream, delimiter='\t')]
    project = HERE / 'project'
    (project / 'structures').mkdir(parents=True, exist_ok=True)
    (project / 'experiments').mkdir(exist_ok=True)
    source = ROOT / 'tests/fixtures/loop_parameter_ids/line-segment/experiments/bank.edi'
    experiment = source.read_text()
    (project / 'experiments/bank.edi').write_text(experiment.replace('phase ', 'zzcalculation '))
    original = ROOT / 'tests/fixtures/loop_parameter_ids/line-segment/structures/phase.edi'
    (project / 'structures/zzcalculation.edi').write_text(
        original.read_text().replace('data_phase', 'data_zzcalculation')
    )
    (project / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name elements\n')
    header = """data_elements
_edi.schema_version 3
_cell.length_a 30
_cell.length_b 30
_cell.length_c 30
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
"""
    rows = [
        f'{s} {s} a Biso {(i % 5 + 0.5) / 5:.1f} '
        f'{(i // 5 % 5 + 0.5) / 5:.1f} {(i // 25 + 0.5) / 5:.1f} 1 0.5\n'
        for i, s in enumerate(symbols)
    ]
    (project / 'structures/elements.edi').write_text(header + ''.join(rows))


if __name__ == '__main__':
    generate()
