"""Auto provenance includes the selected series basis before every consuming boundary."""

# Saved Auto inputs now include the series basis in their independently authored
# provenance. The fit/retention assertions and numerical bounds remain unchanged.

import re

import edi as engine
import numpy as np
import pytest

from tests.fixtures.background_estimate.fitted_baseline import curve
from tests.fixtures.background_estimate.review3 import (
    KINDS,
    basis,
    estimate_control,
    materialize,
    persisted_settings,
    rows,
    state,
)
from tests.fixtures.project_save.reference import (
    six_digits,
)


@pytest.mark.parametrize(
    ('kind', 'change'),
    [
        ('polynomial', 'origin'),
        ('chebyshev', 'x_min'),
        ('chebyshev', 'x_max'),
    ],
)
@pytest.mark.parametrize('route', ['calculate', 'fit', 'reload'])
def test_auto_basis_edit_reestimates_like_a_fresh_normalized_control(
    tmp_path, kind, change, route
):
    source = materialize(tmp_path / 'source', kind)
    project = engine.Project.load(source)
    project.experiment.background_estimate.use_model = 'ignore'
    project.analysis.calculate()
    initial = rows(project.experiment)
    control = engine.Project.load(source)
    control.experiment.background_estimate.use_model = 'ignore'
    control.analysis.calculate()
    basis(control.experiment, change)
    expected = estimate_control(control)
    assert (
        np.max(np.abs(np.asarray([r[2] for r in expected]) - np.asarray([r[2] for r in initial])))
        > 1e-5
    ), 'The declared basis change must require different coefficient values'
    if route == 'reload':
        project.save_as(tmp_path / 'persisted')
        file = tmp_path / 'persisted/experiments/d20.edi'
        values = {'origin': 105.25, 'x_min': 3.375, 'x_max': 160.625}
        file.write_text(
            re.sub(
                r'(?m)^_background\.' + change + r' .*$',
                '_background.' + change + ' ' + str(values[change]),
                file.read_text(),
            )
        )
        project = engine.Project.load(tmp_path / 'persisted')
    else:
        basis(project.experiment, change)
    if route == 'fit':
        for parameter in project.parameters:
            parameter.free = False
        project.structure.cell.length_a.free = True

        # The host remains unchanged while a snapshot fits. Judge the solver's
        # pre-fit record against a forward calculation of the normalized Manual
        # control, rather than requiring unpublished work rows on the live host.
        control.analysis.calculate()
        data = control.experiment.data
        included = np.asarray(data.calc_status) == 'incl'
        residual = (
            (np.asarray(data.intensity_meas) - np.asarray(data.intensity_calc))
            / np.asarray(data.intensity_meas_su)
        )[included]
        expected_chi = float(np.dot(residual, residual))
        expected_reduced_chi = expected_chi / max(1, int(included.sum()) - 1)
        starts = []

        def started(record):
            starts.append(record)
            assert record.pre_fit.reduced_chi_square == pytest.approx(
                expected_reduced_chi, rel=1e-11, abs=1e-8
            ), 'The actual fit cost must use the normalized new basis before iteration one'

        project.fit(on_start=started)
        assert len(starts) == 1, 'A direct single fit must expose exactly one actual pre-fit cost'
        saved = tmp_path / 'after-fit'
        expected = [
            (name, coordinate, six_digits(value), free)
            for name, coordinate, value, free in expected
        ]
        project.save_as(saved)
        settings = persisted_settings(saved)
        assert re.fullmatch(
            r'[0-9a-f]{16}', settings.get('_background_estimate.inputs_digest', '')
        ), (
            'A direct fit that refreshes a due basis must publish and save '
            'its current inputs digest'
        )
        project.analysis.calculate()
        project.save_as(tmp_path / 'after-calculate')
        assert persisted_settings(tmp_path / 'after-calculate') == settings, (
            'An unchanged post-fit calculation must retain the published estimate provenance'
        )
    else:
        project.analysis.calculate()
    np.testing.assert_allclose(
        [r[2] for r in rows(project.experiment)],
        [r[2] for r in expected],
        rtol=1e-11,
        atol=1e-8,
        err_msg='Auto must re-estimate coefficients in an edited or reloaded basis',
    )
    assert project.experiment.background_estimate.mode == 'auto', (
        'A legitimate series-basis edit must retain Auto without a Manual recovery'
    )


@pytest.mark.parametrize('kind', ['polynomial', 'chebyshev'])
@pytest.mark.parametrize('trigger', ['settings', 'data'])
def test_delegated_multibank_save_preserves_the_complete_due_host_background(
    tmp_path, kind, trigger
):
    project = engine.Project.load(materialize(tmp_path / 'input', kind, second=True))
    project.analysis.calculate()
    assert len(project.experiments) == 2, (
        'Delegated saving must exercise two real calculated banks'
    )
    bank = project.experiments[0]
    if trigger == 'settings':
        bank.background_estimate.max_terms = 1
    else:
        data = bank.data
        bank.data = engine.PdCwlData(
            two_theta=np.asarray(data.two_theta),
            intensity_meas=np.asarray(data.intensity_meas) + 125,
            intensity_meas_su=np.asarray(data.intensity_meas_su),
        )
    before = [state(e) for e in project.experiments]
    expected_saved = [
        (
            *snapshot[:-1],
            [
                (name, coordinate, six_digits(value), free)
                for name, coordinate, value, free in snapshot[-1]
            ],
        )
        for snapshot in before
    ]
    project.save_as(tmp_path / 'saved')
    assert state(project.experiments[0]) == before[0], (
        'Saving a due series beside a current bank must not mutate the live due host background'
    )
    assert state(project.experiments[1]) == expected_saved[1], (
        'Save adopts independently rounded six-digit current-bank coefficients '
        'with exact identities, flags, basis and mode'
    )
    reloaded = engine.Project.load(tmp_path / 'saved')
    assert [state(e) for e in reloaded.experiments] == expected_saved, (
        'Delegated save writes independently rounded coefficients in both banks '
        'with exact identities, flags, origin/domain, mode and layout'
    )
    project.analysis.calculate()
    reloaded.analysis.calculate()
    assert [state(e) for e in reloaded.experiments] == [state(e) for e in project.experiments], (
        'A saved due series must reload with coherent provenance'
    )


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('mode', ['single', 'joint'])
@pytest.mark.parametrize('route', ['analysis', 'project'])
def test_mixed_measured_simulated_fit_adopts_fitted_auto_rows(tmp_path, kind, mode, route):
    source = materialize(tmp_path / 'input', kind, second=True, simulation=True, mode=mode)
    project = engine.Project.load(source)
    bank = project.experiments[0]
    initial = rows(bank)
    assert len(project.experiments[0].data.intensity_meas) > 0, (
        'The fit must have a real measured bank'
    )
    assert len(project.experiments[1].data.intensity_meas) == 0, (
        'The fit must traverse the mixed-bank subset path'
    )
    if route == 'analysis':
        project.analysis.fit()
    elif mode == 'single':
        project.fit()
    else:
        project.fit_joint()
    fitted = rows(bank)
    assert (
        np.max(np.abs(np.asarray([r[2] for r in fitted]) - np.asarray([r[2] for r in initial])))
        > 1e-5
    ), 'The mixed-subset stimulus must actually change free background values'
    included = np.asarray(bank.data.calc_status) == 'incl'
    calculated = np.asarray(bank.data.intensity_calc)
    background = np.asarray(bank.data.intensity_bkg)
    assert included.any(), 'The mixed fit must publish included measured samples'
    assert np.isfinite(calculated[included]).all(), (
        'Mixed-bank fitted Auto publication must immediately retain its finite calculated pattern'
    )
    assert np.max(np.abs(calculated[included] - background[included])) > 1e-5, (
        'The mixed fitted pattern must retain nonzero crystal peaks'
    )
    np.testing.assert_allclose(
        background[included],
        curve(project)[included],
        rtol=1e-11,
        atol=1e-8,
        err_msg='Immediate mixed-fit publication must evaluate its fitted background rows',
    )
    project.structure.cell.length_a.value += 0.00025
    project.analysis.calculate()
    assert rows(bank) == fitted, (
        'A later calculation must retain fitted Auto subset values exactly'
    )
    project.save_as(tmp_path / 'saved')
    saved = engine.Project.load(tmp_path / 'saved')
    stored = rows(saved.experiments[0])
    saved.analysis.calculate()
    assert rows(saved.experiments[0]) == stored, (
        'The mixed-bank fitted baseline must save and reload without an unauthorized-edit refusal'
    )


@pytest.mark.parametrize(
    ('source_kind', 'target'),
    [
        ('polynomial', 'chebyshev'),
        ('chebyshev', 'polynomial'),
    ],
)
@pytest.mark.parametrize('spelling', ['background_type', 'background.type'])
def test_compatible_python_series_type_transition_reestimates_without_manual_recovery(
    tmp_path, source_kind, target, spelling
):
    project = engine.Project.load(materialize(tmp_path / 'input', source_kind))
    project.experiment.background_estimate.use_model = 'ignore'
    project.analysis.calculate()
    e = project.experiment
    # Clear the source model's optional constants before declaring the destination's valid shape.
    try:
        e.background_origin = 80 if target == 'polynomial' else None
        e.background_x_min = 8.0953 if target == 'chebyshev' else None
        e.background_x_max = 149.7953 if target == 'chebyshev' else None
    except TypeError as error:
        pytest.fail(
            'Public optional background constants must accept None to clear the old type: '
            + str(error)
        )
    if spelling == 'background_type':
        e.background_type = target
    else:
        e.background.type = target
    control = engine.Project.load(materialize(tmp_path / 'control', target))
    control.experiment.background_estimate.use_model = 'ignore'
    expected = estimate_control(control)
    project.analysis.calculate()
    np.testing.assert_allclose(
        [r[2] for r in rows(e)],
        [r[2] for r in expected],
        rtol=1e-11,
        atol=1e-8,
        err_msg='Both Python type spellings must refresh a compatible series in its new basis',
    )
    assert e.background_estimate.mode == 'auto', (
        'A compatible type transition must retain Auto without Manual recovery'
    )
