"""Absent basis constants and the admitted value -1 have different Auto semantics."""

import edi as engine
import numpy as np
import pytest

from tests.fixtures.background_estimate.review3 import (
    estimate_control,
    materialize,
    persisted_settings,
    rows,
)


@pytest.mark.parametrize(
    ('kind', 'field'),
    [
        ('polynomial', 'origin'),
        ('chebyshev', 'x_min'),
        ('chebyshev', 'x_max'),
    ],
)
@pytest.mark.parametrize('route', ['setter', 'reload'])
def test_clearing_minus_one_basis_refreshes_derives_and_round_trips(tmp_path, kind, field, route):
    project = engine.Project.load(materialize(tmp_path / 'input', kind))
    e = project.experiment
    e.background_estimate.use_model = 'ignore'
    if field == 'x_max':
        e.background_x_min = -160.0  # -1 is a valid upper endpoint, not an invalid domain.
    setattr(e, 'background_' + field, -1.0)
    project.analysis.calculate()
    assert float.hex(getattr(e, 'background_' + field)) == float.hex(-1.0), (
        'The presence witness must settle an admitted explicit -1 basis before clearing it'
    )
    original = rows(e)
    project.save_as(tmp_path / 'explicit')
    explicit_digest = persisted_settings(tmp_path / 'explicit')[
        '_background_estimate.inputs_digest'
    ]
    if route == 'reload':
        project = engine.Project.load(tmp_path / 'explicit')
        e = project.experiment
    setattr(e, 'background_' + field, None)
    assert getattr(e, 'background_' + field) is None, (
        'Clearing before or after reload must reach the actual absent state'
    )
    control = engine.Project.load(materialize(tmp_path / 'control', kind))
    c = control.experiment
    c.background_estimate.use_model = 'ignore'
    c.background_origin = e.background_origin
    c.background_x_min = e.background_x_min
    c.background_x_max = e.background_x_max
    expected = estimate_control(control)  # A seam control, not a physical coefficient oracle.
    included = np.asarray(e.data.calc_status) == 'incl'
    grid = np.asarray(e.data.two_theta)[included]
    expected_basis = float(
        (grid[0] + grid[-1]) / 2
        if field == 'origin'
        else grid[0]
        if field == 'x_min'
        else grid[-1]
    )
    assert getattr(c, 'background_' + field) == expected_basis, (
        'The fresh seam control must independently derive the included-grid midpoint or endpoint'
    )
    assert expected_basis is not None, 'An absent basis must derive a finite grid constant'
    assert float.hex(expected_basis) != float.hex(-1.0), (
        'The absent basis must derive a grid constant distinct from the explicit -1 stimulus'
    )
    assert original != expected, (
        'The basis presence change must require genuinely different coefficients'
    )
    project.analysis.calculate()
    assert getattr(e, 'background_' + field) == expected_basis, (
        'Auto must derive the missing basis before calculating instead of retaining the -1 digest'
    )
    np.testing.assert_allclose(
        [r[2] for r in rows(e)],
        [r[2] for r in expected],
        rtol=1e-11,
        atol=1e-8,
        err_msg='Cleared Auto basis coefficients must equal a fresh estimate in the derived basis',
    )
    project.save_as(tmp_path / 'derived')
    settings = persisted_settings(tmp_path / 'derived')
    assert settings['_background_estimate.inputs_digest'] != explicit_digest, (
        'Saved provenance must distinguish an explicit -1 basis from its derived replacement'
    )
    loaded = engine.Project.load(tmp_path / 'derived')
    before = rows(loaded.experiment)
    loaded.analysis.calculate()
    assert rows(loaded.experiment) == before, (
        'An unchanged reload must retain the derived basis and exact saved coefficient values'
    )
    assert getattr(loaded.experiment, 'background_' + field) == expected_basis, (
        'The refreshed derived basis must survive save and reload exactly'
    )
    loaded.save_as(tmp_path / 'again')
    assert persisted_settings(tmp_path / 'again') == settings, (
        'An unchanged saved/reloaded derived basis must retain both estimate digests'
    )
