"""One independent covariance reaches structure and experiment series outputs."""

import edi as engine
import numpy as np

from tests.fixtures.joint_series import cases, oracle
from tests.integration.py.test_relation_derived_values import moment_project


def test_derived_series_columns_follow_each_point_covariance(tmp_path):
    source = tmp_path / 'template'
    moment_project(source)
    root = cases.derived_series(source, tmp_path / 'series', engine)
    engine.Project.load(root).analysis.fit()
    _, points = cases.csv_rows(root / 'analysis/results.csv')
    _, banks = cases.csv_rows(root / 'analysis/results_experiments.csv')
    assert len(points) == 3, 'The derived witness must retain all three distinct series points'
    errors = []
    errors = [check_point(root, row, banks) for row in points]
    assert len(set(errors)) == 3, (
        'Distinct point inputs and noise must produce distinct errors to detect stale derived rows'
    )


def point_model(root, row, banks):
    model = engine.Project.load(root)
    model.analysis.fitting_mode = 'joint'
    selected = {bank['experiment']: bank for bank in banks if bank['point'] == row['point']}
    cell = model.structures['phase'].cell.length_a
    cell.value = float(row['phase.cell.length_a'])
    for bank in cases.BANKS:
        data = np.loadtxt(root / selected[bank]['file_path'])
        model.experiments[bank].data = engine.PdCwlData(
            two_theta=data[:, 0], intensity_meas=data[:, 1], intensity_meas_su=data[:, 2]
        )
    parameters = [
        cell,
        *[
            model.experiments[b].linked_structures[p].scale
            for b, p in [('zeta', 'phase'), ('zeta', 'other'), ('alpha', 'phase')]
        ],
    ]
    for parameter, value in zip(
        parameters[1:],
        [
            selected['zeta']['linked_structure.phase.scale'],
            selected['zeta']['linked_structure.other.scale'],
            selected['alpha']['linked_structure.phase.scale'],
        ],
        strict=True,
    ):
        parameter.value = float(value)
    return model, selected, parameters


def check_point(root, row, banks):
    oracle.outcome(row)
    model, selected, parameters = point_model(root, row, banks)
    covariance, _ = cases.calculation_covariance(model, parameters)
    values = [p.value for p in parameters]
    unit = cases.spherical([1.2, -0.7, 2.3, values[0], 6.2, 7.3, 90, 100.5, 90])
    expected_sigma = unit[0] * np.sqrt(covariance[0, 0])
    for index, item in enumerate(('modulus', 'polar', 'azimuthal')):
        actual_item = 'azimuthal' if index == 2 else item
        if index == 1:
            actual_item = 'polar'
        name = 'phase.atom_site_moment.A.spherical_' + actual_item
        oracle.series_cells(
            row,
            name,
            values[0] * unit[0] if index == 0 else unit[index],
            expected_sigma if index == 0 else 0.0,
        )
    gradient = np.array([0, -values[2], values[1], 0]) / (values[1] + values[2]) ** 2
    fraction_sigma = float(np.sqrt(gradient @ covariance @ gradient))
    for bank in cases.BANKS:
        record = selected[bank]
        name = 'linked_structure.other.weight_fraction'
        oracle.series_cells(record, name, values[2] / (values[1] + values[2]), fraction_sigma)
    return expected_sigma, fraction_sigma
