"""Count the authored P1 project directly, without loading edi or crysta."""

import json
import shlex
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = {
    'cell': {'length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma'},
    'atom_site': {'fract_x', 'fract_y', 'fract_z', 'occupancy', 'adp_iso'},
    'peak': {
        'broad_gauss_u',
        'broad_gauss_v',
        'broad_gauss_w',
        'broad_lorentz_x',
        'broad_lorentz_y',
        'rise_alpha_0',
        'rise_alpha_1',
        'decay_beta_0',
        'decay_beta_1',
        'broad_gauss_sigma_0',
        'broad_gauss_sigma_1',
        'broad_gauss_sigma_2',
        'broad_gauss_size',
        'broad_gauss_strain',
        'broad_lorentz_gamma_0',
        'broad_lorentz_gamma_1',
        'broad_lorentz_gamma_2',
        'broad_lorentz_size',
        'broad_lorentz_strain',
    },
    'instrument': {
        'setup_wavelength',
        'calib_twotheta_offset',
        'setup_twotheta_bank',
        'calib_d_to_tof_offset',
        'calib_d_to_tof_linear',
        'calib_d_to_tof_quadratic',
        'calib_d_to_tof_reciprocal',
    },
    'absorption': {'abscor1', 'abscor2'},
    'linked_structure': {'scale'},
    'background': {'coef', 'intensity'},
}


def count_project(root=HERE / 'project'):
    result = []
    for kind, directory in [('structure', 'structures'), ('experiment', 'experiments')]:
        for file in sorted((root / directory).glob('*.edi')):
            result.extend(read_block(kind, file))
    return result


def read_block(kind, file):
    result = []
    lines = file.read_text().splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if line == 'loop_':
            tags = []
            while index < len(lines) and lines[index].startswith('_'):
                tags.append(lines[index].strip())
                index += 1
            while index < len(lines):
                line = lines[index].strip()
                if not line or line.startswith(('_', 'loop_', 'data_')):
                    break
                values = shlex.split(line)
                if len(values) != len(tags):
                    raise ValueError(
                        'The independent reference requires rectangular project loops'
                    )
                row = dict(zip(tags, values, strict=True))
                label = row.get(
                    '_atom_site.id',
                    row.get('_linked_structure.structure_id', row.get('_background.id', '')),
                )
                for tag, value in row.items():
                    append(result, kind, file.stem, tag, label, value)
                index += 1
        elif line.startswith('_'):
            parts = shlex.split(line)
            if len(parts) == 2:
                append(result, kind, file.stem, parts[0], '', parts[1])
    if kind == 'structure' and file.stem == 'ncaf':
        if '_space_group.it_number 199' not in file.read_text():
            raise ValueError('The NCAF oracle requires its declared cubic I 21 3 setting')
        constrained = {'Ca1', 'Al1', 'Na1', 'F3'}
        result = [
            row
            for row in result
            if not (row['category'] == 'cell' and row['name'] != 'length_a')
            and not (
                row['category'] == 'atom_site'
                and row['label'] in constrained
                and row['name'] in {'fract_y', 'fract_z'}
            )
        ]
    return result


def append(result, kind, block, tag, label, value):
    category, name = tag.removeprefix('_').split('.', 1)
    if name in FIELDS.get(category, set()):
        result.append({
            'kind': kind,
            'block': block,
            'category': category,
            'name': name,
            'label': label,
            'free': '(' in value,
        })


if __name__ == '__main__':
    (HERE / 'expected.json').write_text(json.dumps(count_project(), indent=2) + '\n')

    (HERE / 'ncaf.json').write_text(
        json.dumps(count_project(HERE.parent / 'fit_tables/five'), indent=2) + '\n'
    )
