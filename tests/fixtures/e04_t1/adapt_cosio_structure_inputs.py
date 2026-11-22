"""Bind the existing CoSiO oracles to the five reviewed example re-saves."""

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from tests.fixtures.e04_t1.generate import report_cell, scalars, tables

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BEFORE = '09c48d5a^'
AFTER = 'b1d25154'
STRUCTURES = {
    'pd-neut-cwl_cosio-d20_2k': ('cosio',),
    'pd-neut-cwl_cosio-d20_scan-213f': ('cosio',),
    'sc-neut-cwl_cosio-heidi': ('cosio_2k5', 'cosio_55k', 'cosio_300k'),
}


def archived(revision, path):
    return subprocess.check_output(['git', 'show', f'{revision}:{path}'], cwd=ROOT)


def summary(path):
    values = scalars(path)
    axes = ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma')
    cell = [values[f'_cell.{axis}']['value'] for axis in axes]
    return {
        'atoms': len(tables(path)['atom_site']),
        'cellA': cell[0],
        'displayCell': report_cell(path),
        'spaceGroup': values['_space_group.name_h_m'],
        'cell': cell,
    }


def refresh_structure(project, name, display_sources, old_input):
    relative = f'structures/{name}.edi'
    path = f'{project["path"]}/{relative}'
    before_bytes = archived(BEFORE, path)
    after_bytes = archived(AFTER, path)
    before = hashlib.sha256(before_bytes).hexdigest()
    after = hashlib.sha256(after_bytes).hexdigest()
    if before == after or (ROOT / path).read_bytes() != after_bytes:
        raise ValueError(f'The CoSiO source must match the reviewed re-save: {path}')
    for pins, key in ((project['files'], relative), (display_sources, path)):
        if pins[key] not in {before, after}:
            raise ValueError(f'The oracle must hold the reviewed input: {path}')
        pins[key] = after
    old_input.write_bytes(before_bytes)
    old, new = summary(old_input), summary(ROOT / path)
    witness = next(row for row in project['structures'] if row['name'] == name)
    if {key: witness[key] for key in old} not in (old, new):
        raise ValueError(f'The structure summary must match the reviewed input: {path}')
    witness.update(new)


def renew():
    oracle_path = HERE / 'oracle.js'
    display_path = HERE / 'display_oracle.js'
    outputs = {
        path: path.read_text(encoding='utf-8').split('var frozen = ', 1)
        for path in (oracle_path, display_path)
    }
    oracle, display = [
        json.loads(contents.removesuffix(';\n')) for _, contents in outputs.values()
    ]
    projects = {project['id']: project for project in oracle['projects']}
    with tempfile.TemporaryDirectory() as scratch:
        old_input = Path(scratch) / 'old.edi'
        for project_id, structures in STRUCTURES.items():
            for name in structures:
                refresh_structure(projects[project_id], name, display['sources'], old_input)
    for output, data in ((oracle_path, oracle), (display_path, display)):
        header, _ = outputs[output]
        contents = json.dumps(data, indent=2, ensure_ascii=output == display_path)
        output.write_text(
            header + 'var frozen = ' + contents + ';\n', encoding='utf-8', newline='\n'
        )


if __name__ == '__main__':
    renew()
