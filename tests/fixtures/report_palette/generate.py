"""Materialize enough independent phase identities to pass every palette's wraparound."""

import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def generate():
    sizes = [
        sum(row['role'] == 'structure' for row in csv.DictReader(table.open(), delimiter='\t'))
        for table in (ROOT / 'data/palettes').glob('*.tsv')
    ]
    count = 2 * max(sizes) + 1
    destination = HERE / 'project'
    shutil.copytree(
        ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', destination, dirs_exist_ok=True
    )
    structure = (destination / 'structures/phase.edi').read_text()
    (destination / 'structures/phase.edi').unlink()
    names = [f'phase_{index:02}' for index in range(count)]
    for name in names:
        (destination / 'structures' / (name + '.edi')).write_text(
            structure.replace('data_phase', 'data_' + name)
        )
    experiment = destination / 'experiments/bank.edi'
    text = experiment.read_text()
    text = text.replace('phase 0.7\n', ''.join(name + ' 0.7\n' for name in names))
    text = text.replace('phase ', names[0] + ' ')
    experiment.write_text(text)
    (HERE / 'count.txt').write_text(str(count) + '\n')


if __name__ == '__main__':
    generate()
