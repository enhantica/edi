"""Live covariance and independently rounded persistence at every series prefix."""

import shutil

import edi as engine
import numpy as np
import pytest

from tests.fixtures.joint_series import cases, oracle
from tests.integration.py.test_relation_derived_values import moment_project


@pytest.mark.parametrize('channel', ['modulus', 'polar', 'azimuthal', 'fraction', 'follower'])
def test_derived_series_columns_follow_each_point_covariance(tmp_path, channel):
    source = tmp_path / 'template'
    moment_project(source)
    root = cases.derived_series(source, tmp_path / 'series', engine)
    errors = []
    # Each prefix exposes its last full-precision live state. Earlier rows still exist,
    # so a writer reusing a predecessor's errors is exercised, without reconstructing a
    # calculation point from lossy CSV seeds or fitting an alternate reference solver.
    for count, key in enumerate(cases.POINTS, 1):
        run = tmp_path / f'prefix-{count}'
        shutil.copytree(root, run)
        for later in cases.POINTS[count:]:
            for file in (run / 'scan').glob(later + '_*'):
                file.unlink()
        model = engine.Project.load(run)
        model.analysis.fit()
        _, points = cases.csv_rows(run / 'analysis/results.csv')
        _, banks = cases.csv_rows(run / 'analysis/results_experiments.csv')
        assert [row['point'] for row in points] == list(cases.POINTS[:count]), (
            'Every prefix must retain its own point rows in declared order'
        )
        errors.append(check_point(model, run, points[-1], banks, key, channel))
    assert len(set(errors)) == 3, (
        'Magnitude, both angles, fraction and follower must each have varying errors'
    )


def moment_values(a):
    return cases.spherical([1.2 * a, -0.7 + 0.2 * (a - 4.1), 2.3, a, 6.2, 7.3, 90, 100.5, 90])


def check_point(model, root, row, banks, key, channel):
    oracle.outcome(row)
    observed = observe(model)
    selected = {bank['experiment']: bank for bank in banks if bank['point'] == key}
    model.analysis.fitting_mode = 'joint'
    for bank in cases.BANKS:
        data = np.loadtxt(root / selected[bank]['file_path'])
        model.experiments[bank].data = engine.PdCwlData(
            two_theta=data[:, 0], intensity_meas=data[:, 1], intensity_meas_su=data[:, 2]
        )
    parameters = [
        model.structures['phase'].cell.length_a,
        *[
            model.experiments[b].linked_structures[p].scale
            for b, p in [('zeta', 'phase'), ('zeta', 'other'), ('alpha', 'phase')]
        ],
    ]
    values = np.array([p.value for p in parameters])
    covariance, _ = cases.calculation_covariance(model, parameters)
    if channel in {'modulus', 'polar', 'azimuthal'}:
        return check_moments(observed, row, values, covariance, channel)
    return check_ratios(observed, selected, values, covariance, channel)


def observe(model):
    view = model.structures['phase'].atom_site_moment['A'].spherical
    moments = [
        (getattr(view, item).value, getattr(view, item).uncertainty)
        for item in ('modulus', 'polar', 'azimuth')
    ]
    fractions = [
        model.experiments[b].linked_structures['other'].weight_fraction for b in cases.BANKS
    ]
    follower = model.experiments['alpha'].linked_structures['other'].scale
    return {
        'moments': moments,
        'fractions': [(p.value, p.uncertainty) for p in fractions],
        'follower': (follower.value, follower.uncertainty),
    }


def check_moments(observed, row, values, covariance, channel):
    expected = moment_values(values[0])
    step = 1e-5 * values[0]
    derivative = (moment_values(values[0] + step) - moment_values(values[0] - step)) / (2 * step)
    moment_errors = np.abs(derivative) * np.sqrt(covariance[0, 0])
    assert all(error > 0 for error in moment_errors), (
        'The fitted series direction must give nonzero errors to both angles and magnitude'
    )
    for index, item in enumerate(('modulus', 'polar', 'azimuthal')):
        if item != channel:
            continue
        value, error = observed['moments'][index]
        assert value == pytest.approx(expected[index], rel=1e-9, abs=1e-9), (
            'Live spherical values must follow the closed-form oblique-cell conversion'
        )
        oracle.numeric_error(error, moment_errors[index])
        oracle.series_cells(row, 'phase.atom_site_moment.A.spherical_' + item, value, error)
    return moment_errors[('modulus', 'polar', 'azimuthal').index(channel)]


def check_ratios(observed, selected, values, covariance, channel):
    fractions, follower_pair = observed['fractions'], observed['follower']
    _, u, v, t = values
    gradient = np.array([0, -v, u, 0]) / (u + v) ** 2
    fraction_sigma = float(np.sqrt(gradient @ covariance @ gradient))
    for bank, (value, error) in (
        zip(cases.BANKS, fractions, strict=True) if channel == 'fraction' else []
    ):
        assert value == pytest.approx(v / (u + v), rel=1e-10), (
            'Equal-ZMV constrained banks must share the independent Hill-Howard fraction'
        )
        oracle.numeric_error(error, fraction_sigma)
        oracle.series_cells(selected[bank], 'linked_structure.other.weight_fraction', value, error)
    if channel == 'fraction':
        return fraction_sigma
    follower_gradient = np.array([0, -t * v / u**2, t / u, v / u])
    follower_sigma = float(np.sqrt(follower_gradient @ covariance @ follower_gradient))
    assert follower_pair[0] == pytest.approx(t * v / u, rel=1e-10), (
        'The follower value must compose the leader ratio and member scale'
    )
    oracle.numeric_error(follower_pair[1], follower_sigma)
    oracle.series_cells(selected['alpha'], 'linked_structure.other.scale', *follower_pair)
    return follower_sigma
