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
    },
    'instrument': {'setup_wavelength', 'calib_twotheta_offset'},
    'linked_structure': {'scale'},
    'background': {'coef'},
}


def count_project():
    result = []
    for kind, directory in [('structure', 'structures'), ('experiment', 'experiments')]:
        for file in sorted((HERE / 'project' / directory).glob('*.edi')):
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
