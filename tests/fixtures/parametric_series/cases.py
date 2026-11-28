"""Small handwritten projects for the four sharing states and linear inverse fits."""

import csv
import shutil
from pathlib import Path

import numpy as np

from tests.fixtures.joint_series import cases

BANKS = ('zeta', 'alpha', 'third')
PATHS = ('peak.broad_gauss_w', 'linked_structure.phase.scale', 'background.1.intensity')
SHARED_TAG = '_parametric_fit_shared.parameter_unique_name'
START_TAGS = (
    '_parametric_fit_start.point',
    '_parametric_fit_start.parameter_unique_name',
    '_parametric_fit_start.value',
)


def append_retired_starts(root, *rows, with_over=False):
    """Write input in the removed point-start format for a compatibility witness."""
    path = root / 'analysis/analysis.edi'
    tags = (*START_TAGS, '_parametric_fit_start.over') if with_over else START_TAGS
    path.write_text(path.read_text() + '\nloop_\n' + '\n'.join((*tags, *rows)) + '\n')


def assert_no_persisted_starts(root):
    text = (root / 'analysis/analysis.edi').read_text()
    assert '_parametric_fit_start.' not in text, 'Project writes omit the retired start loop'
    assert not (root / 'analysis/scan-starts-used.csv').exists(), (
        'Scan runs keep no used-starts receipt on disk'
    )


def parameter(project, bank, path):
    experiment = project.experiments[bank]
    if path == 'linked_structure.phase.scale':
        return experiment.linked_structures['phase'].scale
    if path == 'background.1.intensity':
        return experiment.background[0].intensity
    return experiment.peak.broad_gauss_w


def append_shared(root, names):
    path = root / 'analysis/analysis.edi'
    path.write_text(path.read_text() + '\nloop_\n' + SHARED_TAG + '\n' + '\n'.join(names) + '\n')


def model(root, mode='joint'):
    root = cases.base_project(root)
    (root / 'experiments/2_third.edi').write_text(
        cases.experiment('third', scale=7, wavelength=1.81)
    )
    analysis = root / 'analysis/analysis.edi'
    text = analysis.read_text().replace('alpha 1\n', 'alpha 1\nthird 1\n')
    text += (
        '\nloop_\n_experiment_set.id\n_experiment_set.template_experiment_id\n'
        'paired zeta\nloop_\n_experiment_set_member.experiment_id\n'
        '_experiment_set_member.set_id\nzeta paired\nalpha paired\n'
    )
    analysis.write_text(text.replace('_fitting_mode.type joint', '_fitting_mode.type ' + mode))
    return root


def scan(root, *, shared=True, fixed=False, mode='joint'):
    root = cases.base_project(root)
    (root / 'experiments/1_alpha.edi').unlink()
    (root / 'structures/phase.edi').write_text(cases.structure(free=False))
    positions = np.linspace(12, 105, 5)
    local = (7.75, 9.25, 6.5)
    noise = np.array([1, -2, 2, -2, 1]) * 0.03
    template = cases.experiment('zeta', scale=0).split('loop_\n_data.two_theta')[0]
    template = template.replace('phase 0()', 'phase 0').replace(
        '1 12 2', '1 12 3.25' + ('' if fixed else '()')
    )
    template = template.replace('2 105 2', '2 105 5()')
    rows = '\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    rows += ''.join(f'{x} 1 1\n' for x in positions)
    (root / 'experiments/0_zeta.edi').write_text(template + rows)
    for index, endpoint in enumerate(local):
        t = np.linspace(0, 1, 5)
        y = 3.25 * (1 - t) + endpoint * t + noise * (index + 1)
        (root / 'scan' / f'p{index}.xy').write_text(
            ''.join(f'{x:.17g} {v:.17g} 1\n' for x, v in zip(positions, y, strict=True))
        )
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_fitting_mode.type ' + mode + '\n'
        '_minimizer.max_iterations 60\n_minimizer.chi_square_tolerance 1e-12\n'
        '_sequential_fit.data_dir scan\n_sequential_fit.file_pattern "p?.xy"\n'
    )
    if shared:
        append_shared(root, ['zeta.background.1.intensity'])
    return root


def rows(root):
    path = root / 'analysis/results.csv'
    with path.open() as stream:
        return list(csv.DictReader(line for line in stream if not line.startswith('#')))


def linear_covariance(*, shared=True, fixed=False):
    t = np.linspace(0, 1, 5)
    size = 3 if fixed else (4 if shared else 6)
    matrix = np.zeros((15, size))
    for block in range(3):
        if not fixed:
            matrix[block * 5 : (block + 1) * 5, 0 if shared else block * 2] = 1 - t
        column = block if fixed else (block + 1 if shared else block * 2 + 1)
        matrix[block * 5 : (block + 1) * 5, column] = t
    residual_square = 14 * 0.03**2 * (1 + 4 + 9)
    return np.linalg.inv(matrix.T @ matrix) * residual_square / (15 - size)


def scale_scan(root, *, fixed=False):
    """Use a frozen pre-solver profile as a regressor with authored scale/background."""
    fixture = Path(__file__).parent
    shutil.copytree(fixture / 'cubic', root)
    structure = root / 'structures/phase.edi'
    structure.write_text(structure.read_text().replace('()', ''))
    experiment = root / 'experiments/0_zeta.edi'
    text = experiment.read_text().split('loop_\n_data.two_theta')[0]
    text = text.replace('_peak.broad_gauss_u 0.1()', '_peak.broad_gauss_u 0.12')
    text = text.replace('_peak.broad_gauss_v -0.02()', '_peak.broad_gauss_v -0.03')
    text = text.replace('_peak.broad_gauss_w 0.17()', '_peak.broad_gauss_w 0.15')
    text = text.replace('phase 2.0()', 'phase ' + ('2.5' if fixed else '1.8()'))
    text = text.replace('1 12 2', '1 12 1()').replace('2 105 2', '2 105 1()')
    data = np.loadtxt(fixture / 'cubic/scan/p0.xy')
    x, profile = data[:, 0], (data[:, 1] - 2) / 2
    t = (x - 12) / 93
    design = np.column_stack((profile, 1 - t, t))
    raw = np.sin(np.arange(len(x)) * 1.7) * 0.03
    noise = raw - design @ np.linalg.lstsq(design, raw, rcond=None)[0]
    for path in (root / 'scan').glob('*.xy'):
        path.unlink()
    for index in range(3):
        y = 2.5 * profile + (3.25 + index) * (1 - t) + (8.75 - index) * t
        y += noise * (index + 1)
        np.savetxt(root / 'scan' / f'p{index}.xy', np.column_stack((x, y, np.ones(len(x)))))
    experiment.write_text(
        text
        + '\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
        + ''.join(f'{a} {b} 1\n' for a, b in zip(x, data[:, 1], strict=True))
    )
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_fitting_mode.type joint\n'
        '_minimizer.max_iterations 60\n_minimizer.chi_square_tolerance 1e-12\n'
        '_sequential_fit.data_dir scan\n_sequential_fit.file_pattern "p?.xy"\n'
    )
    append_shared(root, ['zeta.linked_structure.phase.scale'])
    size = 6 if fixed else 7
    matrix = np.zeros((3 * len(x), size))
    for block in range(3):
        if not fixed:
            matrix[block * len(x) : (block + 1) * len(x), 0] = profile
        start = 2 * block + (0 if fixed else 1)
        matrix[block * len(x) : (block + 1) * len(x), start : start + 2] = design[:, 1:]
    return np.linalg.inv(matrix.T @ matrix) * (noise @ noise) * 14 / (3 * len(x) - size)
