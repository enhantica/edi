""": independent two-experiment input declarations, without app calls."""

import hashlib
import json
import runpy
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'e04_t4/irregular'
REFERENCE = runpy.run_path(str(HERE.parent / 'e04_t1/generate.py'))


def declarations(path, kind):
    """Supported fields transcribed in  from diffraction-lib, plus CIF loops."""
    scalar = REFERENCE['scalars'](path)
    loops = REFERENCE['tables'](path)
    rows = []

    def add(category, label, name, value):
        rows.append({'category': category, 'row': label, 'name': name, 'free': value['free']})

    if kind == 'structure':
        for name in (
            'length_a',
            'length_b',
            'length_c',
            'angle_alpha',
            'angle_beta',
            'angle_gamma',
        ):
            add('cell', '', name, scalar['_cell.' + name])
        for site in loops['atom_site']:
            for name in ('fract_x', 'fract_y', 'fract_z', 'occupancy', 'adp_iso'):
                add('atom_site', site['id'], name, site[name])
    else:
        for name in REFERENCE['PROFILES'][scalar['_peak.type']]:
            add('peak', '', name, scalar['_peak.' + name])
        for name in REFERENCE['INSTRUMENT']['cwl']:
            add('instrument', '', name, scalar['_instrument.' + name])
        add('absorption', '', 'mu_r', scalar['_absorption.mu_r'])
        for category, names in (
            ('background', ('intensity',)),
            ('linked_structure', ('scale',)),
            ('preferred_orientation', ('march_r', 'march_random_fract')),
        ):
            for row in loops[category]:
                label = row.get('id', row.get('structure_id'))
                if isinstance(label, dict):
                    label = format(label['value'], 'g')
                for name in names:
                    add(category, str(label), name, row[name])
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'parameters': rows}


for mode in ('joint', 'sequential', 'independent'):
    destination = HERE / mode
    shutil.copytree(SOURCE, destination, dirs_exist_ok=True)
    # A different background inventory and different free flags expose cached
    # count consumers. Change only input text, without loading or saving in edi.
    second = destination / 'experiments/second.edi'
    text = second.read_text()
    text = text.replace('4 110. 175.27()\n5 165. 174.56()\n', '')
    text = text.replace('_peak.broad_gauss_u 0.1()', '_peak.broad_gauss_u 0.1')
    text = text.replace('lbco 10.0()', 'lbco 10.0')
    second.write_text(text)
    analysis = destination / 'analysis/analysis.edi'
    lines = [
        line
        for line in analysis.read_text().splitlines()
        if not line.startswith('_fitting_mode.type ')
    ]
    lines.insert(1, '_fitting_mode.type ' + mode)
    analysis.write_text('\n'.join(lines) + '\n')

    if mode != 'joint':
        with analysis.open('a') as stream:
            stream.write(
                '\n_sequential_fit.data_dir experiments\n'
                '_sequential_fit.file_pattern scan.dat\n'
                '_sequential_fit.reverse false\n'
            )
        (destination / 'experiments/scan.dat').write_text('10 100 1\n20 120 1\n30 90 1\n')

(HERE / 'counts.json').write_text(
    json.dumps(
        {
            'provenance': (
                'CIF declarations and  diffraction-lib field inventory; symmetry is applied '
                'by the independent crysta probe at test runtime'
            ),
            'structure': declarations(HERE / 'joint/structures/lbco.edi', 'structure'),
            'experiments': {
                name: declarations(HERE / f'joint/experiments/{name}.edi', 'experiment')
                for name in ('hrpt', 'second')
            },
        },
        indent=2,
    )
    + '\n'
)
