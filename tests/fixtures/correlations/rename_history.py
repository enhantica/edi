"""Declared history addresses and actual collection exits for rename witnesses."""

import shutil
from pathlib import Path

import edi

from tests.fixtures.constraint_expressions.project import materialize

ROOT = Path(__file__).resolve().parent
CASES = {
    'term-remove': ('bank.background.curve.coef',),
    'term-switch': ('bank.background.curve.coef',),
    'point-remove': ('bank.background.left.position', 'bank.background.left.intensity'),
    'point-switch': ('bank.background.left.position', 'bank.background.left.intensity'),
    'site-remove': tuple(
        'phase.atom_site.A.' + f for f in ['fract_x', 'fract_y', 'fract_z', 'occupancy', 'adp_iso']
    ),
    'tensor-switch': tuple(
        'phase.atom_site_aniso.A.adp_' + f for f in ['11', '22', '33', '12', '13', '23']
    ),
    'link-remove': ('bank.linked_structure.phase.scale', 'bank.phase.scale'),
    'texture-remove': (
        'bank.preferred_orientation.phase.march_r',
        'bank.preferred_orientation.phase.march_random_fract',
        'bank.phase.march_r',
        'bank.phase.march_random_fract',
    ),
    'profile-switch': ('bank.peak.broad_lorentz_x', 'bank.peak.broad_lorentz_y'),
}


def owners(namespace):
    return (
        ('shared', 'shared')
        if namespace == 'shared'
        else (('background', 'bank') if namespace == 'category' else ('phase', 'bank'))
    )


def address(name, namespace):
    structure, experiment = owners(namespace)
    if name.startswith('phase.'):
        return structure + '.' + name.removeprefix('phase.')
    return (experiment + '.' + name.removeprefix('bank.')).replace(
        '.phase.', '.' + structure + '.'
    )


def seed(directory, kind, namespace='ordinary'):
    if kind.startswith('term'):
        shutil.copytree(ROOT / 'polynomial-3', directory)
    else:
        materialize(directory)
    structure = directory / 'structures/phase.edi'
    if kind == 'tensor-switch':
        structure.write_text(
            structure.read_text().replace('A La a Biso', 'A La a Bani')
            + '\nloop_\n_atom_site_aniso.id\n_atom_site_aniso.adp_11\n'
            '_atom_site_aniso.adp_22\n_atom_site_aniso.adp_33\n'
            '_atom_site_aniso.adp_12\n_atom_site_aniso.adp_13\n'
            '_atom_site_aniso.adp_23\nA .3 .4 .5 .01 .02 .03\n'
        )
    bank = directory / 'experiments/bank.edi'
    if kind == 'texture-remove':
        bank.write_text(
            bank.read_text() + '\nloop_\n_preferred_orientation.structure_id\n'
            '_preferred_orientation.march_r\n'
            '_preferred_orientation.march_random_fract\n'
            '_preferred_orientation.index_h\n_preferred_orientation.index_k\n'
            '_preferred_orientation.index_l\nphase .73 .2 0 0 1\n'
        )
    structure_name, experiment_name = owners(namespace)
    structure.write_text(structure.read_text().replace('data_phase', 'data_' + structure_name, 1))
    bank.write_text(
        bank
        .read_text()
        .replace('data_bank', 'data_' + experiment_name, 1)
        .replace('phase ', structure_name + ' ')
    )
    return directory


def historical_loop(names, structure='phase', experiment='bank'):
    text = (
        '\nloop_\n_fit_parameter_correlation.id\n'
        '_fit_parameter_correlation.source_kind\n'
        '_fit_parameter_correlation.parameter_unique_name_i\n'
        '_fit_parameter_correlation.parameter_unique_name_j\n'
        '_fit_parameter_correlation.correlation\n'
    )
    # Coefficient text is an independently authored storage witness, not a physics oracle.
    for index, name in enumerate(names):
        text += f'h{index}i deterministic {name} {structure}.cell.length_b -.625\n'
        text += f'h{index}j deterministic {structure}.cell.length_b {name} -.625\n'
    text += (
        f'control deterministic {structure}.cell.length_a '
        f'{experiment}.instrument.setup_wavelength .375\n'
    )
    return text


def remove_live_row(project, kind, structure='phase'):
    if kind == 'term-remove':
        project.experiment.background_terms = project.experiment.background_terms[:2]
    elif kind == 'term-switch':
        project.experiment.background_terms = []
        project.experiment.background_type = 'line-segment'
        project.experiment.background_origin = None
        points = []
        for position, intensity in [(20, 3), (100, 9)]:
            point = edi.LineSegment()
            point.position = position
            point.intensity = intensity
            points.append(point)
        project.experiment.background = points
    elif kind == 'point-remove':
        project.experiment.background = list(project.experiment.background)[1:]
    elif kind == 'point-switch':
        project.experiment.background = []
        project.experiment.background_type = 'polynomial'
        project.experiment.background_origin = 40.0
        term = edi.PolynomialTerm()
        term.order = 0
        term.coef = 4.125
        project.experiment.background_terms = [term]
    elif kind == 'site-remove':
        project.structure.atom_sites.remove('A')
    elif kind == 'tensor-switch':
        project.structure.atom_sites['A'].adp_type = 'Biso'
    elif kind == 'link-remove':
        project.experiment.linked_structures.remove(structure)
    elif kind == 'texture-remove':
        project.experiment.preferred_orientation.remove(structure)
    elif kind == 'profile-switch':
        project.experiment.peak.type = 'cwl-gaussian'


def frozen_loop(namespace):
    text = (ROOT / 'loop-3.edi').read_text().replace('bank.', owners(namespace)[1] + '.')
    reversed_rows = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) == 5 and fields[1] == 'deterministic':
            identity, source, first, second, value = fields
            reversed_rows.append(' '.join([identity + '_reverse', source, second, first, value]))
    return text.rstrip() + '\n' + '\n'.join(reversed_rows) + '\n'
