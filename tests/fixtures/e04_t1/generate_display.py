"""Freeze displayed-value witnesses from .edi inputs, without importing edi.

The ITA number/system table is an independent crystallographic identity oracle
for the names in this corpus. Explicit IT numbers are checked against it. The
legacy experiment-axis defaults are the accepted  P1 directory-loader
contract; declared values always take precedence.
"""

import hashlib
import json
from pathlib import Path

import yaml
from generate import ROOT, measured_range, scalars, tables

IDENTITIES = {
    'P m -3 m': (221, 'cubic'),
    'F m -3 m': (225, 'cubic'),
    'F d -3 m': (227, 'cubic'),
    'I m -3 m': (229, 'cubic'),
    'I 21 3': (199, 'cubic'),
    'I a -3': (206, 'cubic'),
    'P n m a': (62, 'orthorhombic'),
    # Independent owner FullProf output gives the number and crystal system.
    'P b n m': (62, 'orthorhombic'),
    'R -3 c': (167, 'trigonal'),
    'P m m a': (51, 'orthorhombic'),
}


# CrySPY b37f9f3148d2771c6d84ee91f57331676d93746f,
# function_2_space_group.get_default_it_coordinate_system_code_by_it_number:
# ordinary orthorhombic settings use abc; these ordinary cubic settings use 1;
# the double-origin Fd-3m reference uses 2. Explicit file codes still win.
DEFAULT_COORDINATE_CODES = {
    51: 'abc',
    62: 'abc',
    199: '1',
    206: '1',
    221: '1',
    225: '1',
    227: '2',
    229: '1',
}


def scalar_text(value):
    return str(value['value']).removesuffix('.0') if isinstance(value, dict) else value


def displayed_steps(path):
    """Owner  idea 16: adjacent-step bounds at the independent 3-digit display precision."""
    data = tables(path, ('_data',))['data']
    axis = 'two_theta' if 'two_theta' in data[0] else 'time_of_flight'
    values = [row[axis]['value'] for row in data]
    steps = [right - left for left, right in zip(values, values[1:], strict=False)]
    low, high = (float(format(value, '.3g')) for value in (min(steps), max(steps)))
    if low == high:
        return measured_range(path)[2], 'number'
    return f'{low:g}\u2013{high:g}', 'readonly'


def generate():
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())['projects']
    projects = [ROOT / 'docs/user/cli' / entry['id'] / 'project' for entry in registry]
    projects += [
        Path(__file__).parent / (name + '-project') for name in ('xray', 'editable', 'warning')
    ]
    cases = []
    sources = {}

    def read(path):
        sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return scalars(path)

    def add(project, page, tier, group, fields, selection=None):
        path = str(project.relative_to(ROOT))
        cases.append({
            'tag': path + ':' + group + (':' + selection if selection else ''),
            'path': path,
            'page': page,
            'tier': tier,
            'group': group,
            'selection': selection,
            'fields': fields,
        })

    for project in projects:
        for structure in sorted((project / 'structures').glob('*.edi')):
            values = read(structure)
            name = values['_space_group.name_h_m']
            number, system = IDENTITIES[name]
            declared = values.get('_space_group.it_number', {'value': number})['value']
            if declared != number:
                raise ValueError(f'ITA identity disagrees with declared number: {structure}')
            add(
                project,
                'structure',
                'basic',
                'space_group',
                [
                    ['spaceGroup.crystalSystem', system, 'readonly'],
                    ['spaceGroup.itNumber', str(number), 'text'],
                    ['spaceGroup.nameHM', name, 'text'],
                    [
                        'spaceGroup.coordSystemCode',
                        scalar_text(
                            values['_space_group.coord_system_code']
                            if '_space_group.coord_system_code' in values
                            else DEFAULT_COORDINATE_CODES[number]
                        ),
                        'text',
                    ],
                ],
                structure.stem,
            )
        for experiment in sorted((project / 'experiments').glob('*.edi')):
            values = read(experiment)
            mode = (
                'time-of-flight'
                if values['_peak.type'].startswith('tof-')
                else 'constant wavelength'
            )
            axes = [
                ('sampleForm', 'sample_form', 'powder'),
                ('beamMode', 'beam_mode', mode),
                ('radiationProbe', 'radiation_probe', 'neutron'),
                ('scatteringType', 'scattering_type', 'bragg'),
            ]
            add(
                project,
                'experiment',
                'basic',
                'experiment_type',
                [
                    [
                        'experimentType.' + role,
                        values.get('_experiment_type.' + tag, default),
                        'disabled',
                    ]
                    for role, tag, default in axes
                ],
                experiment.stem,
            )
            add(
                project,
                'experiment',
                'extras',
                'data',
                [
                    [
                        'range.' + role,
                        *(displayed_steps(experiment) if role == 'step' else (value, 'number')),
                    ]
                    for role, value in zip(
                        ('minimum', 'maximum', 'step', 'points'),
                        measured_range(experiment),
                        strict=True,
                    )
                ],
                experiment.stem,
            )
        analysis = project / 'analysis/analysis.edi'
        values = read(analysis)
        if values.get('_fitting_mode.type') == 'sequential':
            add(
                project,
                'analysis',
                'extras',
                'sequential_fit',
                [
                    ['sequentialFit.' + role, values['_sequential_fit.' + tag], 'readonly']
                    for role, tag in [
                        ('dataDir', 'data_dir'),
                        ('filePattern', 'file_pattern'),
                        ('reverse', 'reverse'),
                    ]
                ],
            )
        # The engine is the accepted single-engine contract, even when a legacy
        # file retains an unsupported minimizer token (warning-project/scan-3f).
        add(
            project,
            'analysis',
            'extras',
            'engines',
            [
                ['statusBar.calculator', 'crysta', 'label'],
                ['statusBar.minimizer', 'crysta', 'label'],
            ],
        )
    output = Path(__file__).with_name('display_oracle.js')
    output.write_text(
        '// Generated by generate_display.py; .edi + ITA identities, never app output.\n'
        'var frozen = ' + json.dumps({'sources': sources, 'cases': cases}, indent=2) + ';\n'
    )


if __name__ == '__main__':
    generate()
