"""Generate noiseless observations from declared cubic parameters for inverse recovery."""

import json
from pathlib import Path

import crysta
import numpy as np

from tests.fixtures.joint_series import cases

TRUTH = {
    'cell': [4.1, 4.16, 4.08, 4.12, 4.06],
    'scale': [2.0, 2.6, 1.7, 2.3, 1.9],
    'biso': [0.3, 0.4, 0.2, 0.5, 0.35],
    'profile': {'broad_gauss_u': 0.12, 'broad_gauss_v': -0.03, 'broad_gauss_w': 0.15},
}


def generate(root):
    root = cases.base_project(root)
    (root / 'experiments/1_alpha.edi').unlink()
    structure = cases.structure().replace('_cell.length_b 5.3', '_cell.length_b 4.1')
    structure = structure.replace('_cell.length_c 6.7', '_cell.length_c 4.1')
    structure = structure.replace('"P 1"', '"P m -3 m"').replace('0.17 0.23 0.31', '0 0 0')
    structure = structure.replace('1 0.3\n', '1 0.3()\n')
    (root / 'structures/phase.edi').write_text(structure)
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text('_edi.schema_version 3\n_fitting_mode.type single\n')
    project = crysta.Project.load(root)
    for name, value in TRUTH['profile'].items():
        getattr(project.experiments['zeta'].peak, name).value = value
    for index, cell in enumerate(TRUTH['cell']):
        project.structure.cell.length_a.value = cell
        project.structure.atom_sites[0].adp_iso.value = TRUTH['biso'][index]
        project.experiments['zeta'].linked_structures['phase'].scale.value = TRUTH['scale'][index]
        project.analysis.calculate()
        observed = np.asarray(project.experiments['zeta'].data.intensity_calc)
        (root / 'scan' / f'p{index}.xy').write_text(
            ''.join(f'{x:.17g} {y:.17g} 1\n' for x, y in zip(cases.GRID, observed, strict=True))
        )
    experiment = root / 'experiments/0_zeta.edi'
    text = experiment.read_text()
    for name, start in (
        ('broad_gauss_u', 0.10),
        ('broad_gauss_v', -0.02),
        ('broad_gauss_w', 0.17),
    ):
        old = next(line for line in text.splitlines() if line.startswith('_peak.' + name + ' '))
        text = text.replace(old, f'_peak.{name} {start}()')
    experiment.write_text(text)
    analysis.write_text(
        '_edi.schema_version 3\n_fitting_mode.type parametric\n'
        '_minimizer.max_iterations 100\n_minimizer.chi_square_tolerance 1e-12\n'
        '_sequential_fit.data_dir scan\n_sequential_fit.file_pattern p?.xy\n'
        'loop_\n_parametric_fit_shared.parameter_unique_name\n'
        + ''.join(f'zeta.peak.{name}\n' for name in TRUTH['profile'])
    )
    (root.parent / 'cubic-truth.json').write_text(json.dumps(TRUTH, indent=2) + '\n')


if __name__ == '__main__':
    generate(Path(__file__).parent / 'cubic')
