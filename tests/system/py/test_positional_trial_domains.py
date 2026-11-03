"""Trial-domain fitting uses proposed positions, with independently authored limits."""

import math

import edi as engine
import numpy as np
import pytest

from tests.fixtures.xray_doublet import trial_domains


@pytest.mark.parametrize('family', trial_domains.CASES)
@pytest.mark.parametrize('entry', ['direct', 'analysis', 'joint'])
@pytest.mark.parametrize('stage', ['cold', 'reopened'])
def test_coordinate_domain_fit_rejects_invalid_proposal_and_keeps_valid_state(
    tmp_path, family, entry, stage
):
    root = trial_domains.write(tmp_path / 'input', family, joint=entry == 'joint')
    project = engine.Project.load(root)
    source = project.structures['phase'].atom_sites['X'].fract_x
    points = trial_domains.grid(family)
    source.value = 0.125
    project.analysis.calculate()
    base = {bank.name: np.asarray(bank.data.intensity_calc).copy() for bank in project.experiments}
    h = 1e-5
    source.value = 0.125 + h
    project.analysis.calculate()
    plus = {bank.name: np.asarray(bank.data.intensity_calc).copy() for bank in project.experiments}
    source.value = 0.125 - h
    project.analysis.calculate()
    minus = {
        bank.name: np.asarray(bank.data.intensity_calc).copy() for bank in project.experiments
    }
    source.value = 0.125
    project.analysis.calculate()
    motion = 0.0
    for bank in project.experiments:
        slope = (plus[bank.name] - minus[bank.name]) / (2 * h)
        motion += float(np.linalg.norm(slope))
        observed = base[bank.name] + slope * (0.4 - 0.125)
        values = {'intensity_meas': observed.tolist(), 'intensity_meas_su': [1] * len(points)}
        bank.data = (
            engine.PdTofData(time_of_flight=points, **values)
            if family == 'tof-calibration'
            else engine.PdCwlData(two_theta=points, **values)
        )
    assert motion > 1e-12, (
        'The combined drive-only observations must require an actual coordinate step'
    )
    if stage == 'reopened':
        project.save_as(tmp_path / 'saved')
        project = engine.Project.load(tmp_path / 'saved')
    assert not trial_domains.admitted_source(family, 0.4), (
        'The authored unconstrained coordinate proposal must cross the dependent domain'
    )
    assert trial_domains.admitted_source(family, 0.1), (
        'The independently authored recovery coordinate must remain inside the domain'
    )
    result = (
        project.fit_joint()
        if entry == 'joint'
        else project.analysis.fit()
        if entry == 'analysis'
        else project.fit()
    )
    assert result is not None, 'A refused trial must not abort the consumer fit boundary'
    assert math.isfinite(result.reduced_chi_square), (
        'A fit touching the dependent domain must return a finite objective'
    )
    value = project.structures['phase'].atom_sites['X'].fract_x.value
    assert trial_domains.admitted_source(family, value), (
        'The consumer fit must publish only a valid relation-dependent coordinate'
    )
