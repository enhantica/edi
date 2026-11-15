"""Known-input series and algebraic covariance witnesses."""

import csv
import math
import re
import shutil
from pathlib import Path

import numpy as np

POINTS = ('T050K', 'T300K', 'T500K')
BANKS = ('zeta', 'alpha')
CELLS = (4.1, 4.16, 4.08)
SCALES = ((2.0, 5.0), (2.6, 4.2), (1.7, 6.0))
GRID = np.linspace(12, 105, 721)


def structure(name='phase', *, a=4.1, free=True):
    return f"""data_{name}
_edi.schema_version 3
_cell.length_a {a}{'()' if free else ''}
_cell.length_b 5.3
_cell.length_c 6.7
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
A La a Biso 0.17 0.23 0.31 1 0.3
"""


def experiment(name, *, scale=2, wavelength=1.54, phases=('phase',)):
    text = f"""data_{name}
_edi.schema_version 3
_calculator.type crysta
_experiment_type.sample_form powder
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.15
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 8
_instrument.calib_twotheta_offset 0
_instrument.setup_wavelength {wavelength}
_background.type line-segment
loop_
_background.id
_background.position
_background.intensity
1 12 2
2 105 2
loop_
_linked_structure.structure_id
_linked_structure.scale
"""
    text += ''.join(f'{phase} {scale}()\n' for phase in phases)
    text += '\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    return text + ''.join(f'{x:.17g} 1 1\n' for x in GRID)


def base_project(root, *, phases=('phase',)):
    root = Path(root)
    for directory in ('structures', 'experiments', 'analysis', 'scan'):
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name series\n')
    for phase in phases:
        (root / 'structures' / f'{phase}.edi').write_text(structure(phase))
    for index, bank in enumerate(BANKS):
        (root / 'experiments' / f'{index}_{bank}.edi').write_text(
            experiment(bank, scale=SCALES[0][index], wavelength=(1.54, 1.27)[index], phases=phases)
        )
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_fitting_mode.type joint\n'
        '_minimizer.max_iterations 60\n_minimizer.chi_square_tolerance 1e-10\n'
        'loop_\n_joint_fit.experiment_id\n_joint_fit.weight\nzeta 1\nalpha 1\n'
    )
    return root


def declare_series(root, keys=POINTS, *, single=False, mode='sequential'):
    analysis = root / 'analysis/analysis.edi'
    text = analysis.read_text().replace('_fitting_mode.type joint', f'_fitting_mode.type {mode}')
    text += '\n_sequential_fit.data_dir scan\n_sequential_fit.reverse false\n'
    if single:
        text += '_sequential_fit.file_pattern "*_b5.xy"\n'
    else:
        text += (
            'loop_\n_sequential_fit_experiment.experiment_id\n'
            '_sequential_fit_experiment.file_pattern\nzeta "*_b5.xy"\nalpha "*_b1.xy"\n'
        )
    analysis.write_text(text)
    return keys


def generated_series(root, engine, *, keys=POINTS, varying=True, single=False, mode='sequential'):
    """Calculation supplies observations; the authored inputs are the recovery oracle."""
    root = base_project(root)
    if single:
        (root / 'experiments/1_alpha.edi').unlink()
        analysis = root / 'analysis/analysis.edi'
        analysis.write_text(analysis.read_text().replace('alpha 1\n', ''))
    project = engine.Project.load(root)
    for point_index, key in enumerate(keys):
        project.structure.cell.length_a.value = CELLS[point_index % 3] if varying else CELLS[0]
        for bank_index, bank in enumerate(BANKS[:1] if single else BANKS):
            project.experiments[bank].linked_structures['phase'].scale.value = (
                SCALES[point_index % 3][bank_index] if varying else SCALES[0][bank_index]
            )
        project.analysis.calculate()
        for bank_index, bank in enumerate(BANKS[:1] if single else BANKS):
            calculated = np.asarray(project.experiments[bank].data.intensity_calc)
            sigma = np.maximum(0.01, np.sqrt(np.maximum(calculated, 0.0)))
            measured = calculated + 0.2 * sigma * np.sin(np.arange(len(GRID)) * math.sqrt(2))
            suffix = ('b5', 'b1')[bank_index]
            (root / 'scan' / f'{key}_{suffix}.xy').write_text(
                ''.join(
                    f'{x:.17g} {y:.17g} {su:.17g}\n'
                    for x, y, su in zip(GRID, measured, sigma, strict=True)
                )
            )
    declare_series(root, keys, single=single, mode=mode)
    return root


def csv_rows(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def write_rows(path, header, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def relations(root, aliases, expressions):
    analysis = root / 'analysis/analysis.edi'
    text = analysis.read_text() + '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
    text += ''.join(f'{name} {target}\n' for name, target in aliases)
    text += '\nloop_\n_constraint.expression\n'
    text += ''.join(f'"{expression}"\n' for expression in expressions)
    analysis.write_text(text)


def ratio_covariance_project(root, engine, *, source):
    """Equal ZMV phases: member scales t,t*v/u make w_beta = v/(u+v)."""
    root = base_project(root, phases=('phase', 'other'))
    for name in ('phase', 'other'):
        path = root / 'structures' / f'{name}.edi'
        path.write_text(structure(name, free=False))
    aliases = [
        ('u', 'zeta.linked_structure.phase.scale'),
        ('v', 'zeta.linked_structure.other.scale'),
        ('t', 'alpha.linked_structure.phase.scale'),
        ('dependent', 'alpha.linked_structure.other.scale'),
    ]
    member = root / 'experiments/1_alpha.edi'
    member.write_text(member.read_text().replace('other 5.0()', 'other 5.0'))
    relations(root, aliases, ['dependent = t*v/u'])
    analysis = root / 'analysis/analysis.edi'
    if source == 'leader':
        analysis.write_text(
            analysis.read_text()
            + """
loop_
_fit_parameter_correlation.id
_fit_parameter_correlation.source_kind
_fit_parameter_correlation.parameter_unique_name_i
_fit_parameter_correlation.parameter_unique_name_j
_fit_parameter_correlation.correlation
uv deterministic zeta.linked_structure.phase.scale zeta.linked_structure.other.scale 0.5
"""
        )
    project = engine.Project.load(root)
    for bank, phase, value, sigma in (
        ('zeta', 'phase', 2, 0.04 if source == 'leader' else 0),
        ('zeta', 'other', 1, 0.03 if source == 'leader' else 0),
        ('alpha', 'phase', 3, 0.1 if source == 'member' else 0),
    ):
        parameter = project.experiments[bank].linked_structures[phase].scale
        parameter.value = value
        parameter.free = sigma > 0
        if sigma:
            parameter.uncertainty = sigma
    return project


def direct_unit_basis(angles):
    alpha, beta, gamma = angles
    ca, cb, cg = np.cos(np.radians([alpha, beta, gamma]))
    sg = math.sin(math.radians(gamma))
    return np.array([
        [1, cg, cb],
        [0, sg, (ca - cb * cg) / sg],
        [0, 0, math.sqrt(1 - cb * cb - ((ca - cb * cg) / sg) ** 2)],
    ])


def spherical(inputs):
    """Cartesian x || a, z || c*: use normalized direct-axis basis vectors."""
    x, y, z = direct_unit_basis(inputs[6:]) @ np.array(inputs[:3])
    modulus = math.sqrt(x * x + y * y + z * z)
    return np.array([
        modulus,
        math.degrees(math.acos(z / modulus)),
        math.degrees(math.atan2(y, x)) % 360,
    ])


def propagated_spherical(inputs, covariance):
    jacobian = np.empty((3, len(inputs)))
    for index, value in enumerate(inputs):
        delta = 1e-5 * max(1, abs(value))
        upper, lower = np.array(inputs, dtype=float), np.array(inputs, dtype=float)
        upper[index] += delta
        lower[index] -= delta
        jacobian[:, index] = (spherical(upper) - spherical(lower)) / (2 * delta)
    return spherical(inputs), np.sqrt(np.diag(jacobian @ covariance @ jacobian.T))


def clear_free_flags(text):
    return re.sub(r'(?<=[\d.])\([^()\s]*\)', '', text)


def calculation_covariance(project, parameters):
    start = np.array([p.value for p in parameters])
    observations = np.concatenate([
        np.asarray(project.experiments[b].data.intensity_meas) for b in BANKS
    ])

    def calculated(vector):
        for parameter, value in zip(parameters, vector, strict=True):
            parameter.value = value
        project.analysis.calculate()
        return np.concatenate([
            np.asarray(project.experiments[b].data.intensity_calc).copy() for b in BANKS
        ])

    weights = np.concatenate([
        np.asarray(project.experiments[b].data.intensity_meas_su) for b in BANKS
    ])
    columns = []
    for index, value in enumerate(start):
        step = 1e-5 * max(abs(value), 0.01)
        upper, lower = start.copy(), start.copy()
        upper[index] += step
        lower[index] -= step
        columns.append((calculated(upper) - calculated(lower)) / (2 * step) / weights)
    residual = (calculated(start) - observations) / weights
    jacobian = np.array(columns).T
    chi_square = (residual @ residual) / (len(residual) - len(parameters))
    return np.linalg.inv(jacobian.T @ jacobian) * chi_square, chi_square


def derived_series(source, root, engine):
    shutil.copytree(source, root)
    main = root / 'structures/phase.edi'
    text = clear_free_flags(main.read_text())
    text = re.sub(r'(?m)^_cell.length_a .*$', '_cell.length_a 4.1()', text)
    main.write_text(text)
    other = text.split('loop_\n_space_group_symop_magn_operation')[0]
    (root / 'structures/other.edi').write_text(
        other.replace('data_phase', 'data_other').replace('4.1()', '4.1')
    )
    for index, bank in enumerate(BANKS):
        (root / 'experiments' / f'{index}_{bank}.edi').write_text(
            experiment(bank, wavelength=(1.54, 1.27)[index], phases=('phase', 'other'))
        )
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(
        '_fitting_mode.type joint\n_minimizer.max_iterations 60\n_minimizer.'
        'chi_square_tolerance 1e-10\nloop_\n_joint_fit.experiment_id\n_joint_'
        'fit.weight\nzeta 1\nalpha 1\n'
    )
    aliases = [('a', 'phase.cell.length_a'), ('oa', 'other.cell.length_a')]
    aliases += [(axis, 'phase.atom_site_moment.A.crystalaxis_' + axis) for axis in 'xyz']
    aliases += [
        ('u', 'zeta.linked_structure.phase.scale'),
        ('v', 'zeta.linked_structure.other.scale'),
        ('t', 'alpha.linked_structure.phase.scale'),
        ('d', 'alpha.linked_structure.other.scale'),
    ]
    relations(
        root, aliases, ['oa = a', 'x = 1.2*a', 'y = -0.7+0.2*(a-4.1)', 'z = 2.3', 'd = t*v/u']
    )
    project = engine.Project.load(root)
    (root / 'scan').mkdir(exist_ok=True)
    for index, key in enumerate(POINTS):
        project.structures['phase'].cell.length_a.value = CELLS[index]
        for bank, phase, value in [
            ('zeta', 'phase', 2 + 0.2 * index),
            ('zeta', 'other', 1 + 0.3 * index),
            ('alpha', 'phase', 3 + 0.6 * index),
        ]:
            project.experiments[bank].linked_structures[phase].scale.value = value
        project.analysis.calculate()
        for b, bank in enumerate(BANKS):
            values = np.asarray(project.experiments[bank].data.intensity_calc)
            sigma = np.maximum(1, np.sqrt(np.maximum(values, 0)))
            observed = values + (index + 1) * 0.1 * sigma * np.sin(
                np.arange(len(values)) * 1.7 + b
            )
            (root / 'scan' / f'{key}_{("b5", "b1")[b]}.xy').write_text(
                ''.join(
                    f'{x:.17g} {y:.17g} {su:.17g}\n'
                    for x, y, su in zip(GRID, observed, sigma, strict=True)
                )
            )
    declare_series(root)
    return root
