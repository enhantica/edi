"""A participating fixed second wavelength breaks Bragg's dilation null direction."""

import math

import edi as engine
import pytest

from tests.fixtures.xray_doublet import anchoring


@pytest.mark.parametrize('key', anchoring.GRAPHS)
@pytest.mark.parametrize('state', ['fixed-second', 'inactive', 'free-second'])
@pytest.mark.parametrize('entry', ['direct', 'analysis'])
def test_doublet_fit_admission_follows_each_active_anchor(tmp_path, key, state, entry):
    root = tmp_path / 'input'
    mode, admitted = anchoring.write(root, key, state, reverse=entry == 'analysis')
    project = engine.Project.load(root)
    call = (
        project.analysis.fit
        if entry == 'analysis'
        else project.fit
        if mode == 'single'
        else project.fit_joint
    )
    if admitted:
        result = call(should_cancel=lambda: True)
        assert result is not None, 'An admitted fit must return its structured result'
        assert result.status == engine.FitStatus.CANCELLED, (
            'A fixed active second wavelength must admit the requested single or connected '
            'joint fit before cancellation'
        )
    else:
        with pytest.raises(ValueError, match=r'dilation|null direction'):
            call(should_cancel=lambda: True)


@pytest.mark.parametrize('key', anchoring.RELATION_GRAPHS)
@pytest.mark.parametrize('relation', anchoring.RELATIONS)
@pytest.mark.parametrize('stage', ['cold', 'calculated', 'reopened'])
@pytest.mark.parametrize('entry', ['direct', 'analysis'])
def test_relation_anchor_uses_effective_components_and_dilation_derivatives(
    tmp_path, key, relation, stage, entry
):
    root = tmp_path / 'input'
    mode = anchoring.write_relation(root, key, relation, reverse=entry == 'analysis')
    project = engine.Project.load(root)
    if stage == 'cold' and relation in {'constant-ratio', 'disabled-ratio', 'zero-ratio'}:
        raw_ratio = 0.375 if relation == 'zero-ratio' else 0.0
        for bank in anchoring.GRAPHS[key][2]:
            assert (
                project.experiments[bank].instrument.setup_wavelength_2_to_1_ratio.value
                == raw_ratio
            ), 'Cold admission must retain the authored stored ratio before applying its relation'
    if stage == 'calculated':
        project.analysis.calculate()
    elif stage == 'reopened':
        saved = tmp_path / 'saved'
        project.save_as(saved)
        project = engine.Project.load(saved)
    wavelengths, slopes, ratio = anchoring.relation_geometry(relation)
    cell = 2.2
    response = tuple(
        (slope - wavelength) / (cell * math.sqrt(1 - (wavelength / (2 * cell)) ** 2))
        for wavelength, slope in zip(wavelengths, slopes, strict=True)
    )
    anchored = abs(response[0]) > 1e-12 or (ratio > 0 and abs(response[1]) > 1e-12)
    if relation.startswith('moving'):
        assert response == (0.0, 0.0), (
            'Homogeneous wavelength derivatives must preserve both Bragg positions under dilation'
        )
    elif ratio > 0:
        assert anchored, 'A fixed participating line must have a nonzero Bragg dilation response'
    if stage != 'cold':
        for bank in anchoring.GRAPHS[key][2]:
            instrument = project.experiments[bank].instrument
            assert instrument.setup_wavelength_2_to_1_ratio.value == ratio, (
                'Calculation and reopen must retain the effective enabled relation component ratio'
            )
    if anchored:
        result = invoke_relation(project, mode, entry)
        assert result is not None, 'A genuine relation-defined fixed line must admit its fit'
        assert result.status == engine.FitStatus.CANCELLED, (
            'An admitted consumer fit must reach its public cancelled status'
        )
    else:
        with pytest.raises(ValueError, match=r'dilation|null direction'):
            invoke_relation(project, mode, entry)


def invoke_relation(project, mode, entry):
    call = (
        project.analysis.fit
        if entry == 'analysis'
        else project.fit
        if mode == 'single'
        else project.fit_joint
    )
    return call(should_cancel=lambda: True)


@pytest.mark.parametrize('key', anchoring.RELATION_GRAPHS)
@pytest.mark.parametrize('relation', anchoring.ZERO_BOUNDARY_RELATIONS)
@pytest.mark.parametrize('stage', ['cold', 'calculated', 'reopened'])
@pytest.mark.parametrize('entry', ['direct', 'analysis'])
def test_zero_ratio_admission_retains_observable_relation_derivative(
    tmp_path, key, relation, stage, entry
):
    root = tmp_path / 'input'
    mode = anchoring.write_zero_boundary(root, key, relation, reverse=entry == 'analysis')
    project = engine.Project.load(root)
    project = prepare_stage(project, stage, tmp_path)
    for bank in anchoring.GRAPHS[key][2]:
        assert project.experiments[bank].instrument.setup_wavelength_2_to_1_ratio.value == 0, (
            'The boundary witness must retain an exactly zero ratio at every lifecycle stage'
        )
    ratio_slope, compensator_slope = anchoring.zero_boundary_slopes(relation)
    # At ratio zero, dy/dt = dy1/dt + ratio_prime*y2; ratio*y2_prime vanishes.
    first_bragg_slope = (1.54 - 1.54) / (2.2 * math.sqrt(1 - (1.54 / 4.4) ** 2))
    assert first_bragg_slope == 0, 'The first-line cell/wavelength dilation must remain null'
    if relation.startswith('compensated'):
        master_slope = 2.2 if relation.endswith('cell') else 1.54
        assert math.isclose(0.25 * master_slope - compensator_slope, 0, abs_tol=1e-14), (
            'An independent second wavelength can compensate the zero-boundary ratio slope'
        )
    admitted = ratio_slope != 0
    if admitted:
        assert ratio_slope > 0, (
            'A positive-domain step must create a nonzero first-order unit second-component signal'
        )
    assert_boundary(project, mode, entry, admitted)


@pytest.mark.parametrize('key', anchoring.RELATION_GRAPHS)
@pytest.mark.parametrize('source', anchoring.IDLE_SOURCES)
@pytest.mark.parametrize('stage', ['cold', 'calculated', 'reopened'])
@pytest.mark.parametrize('entry', ['direct', 'analysis'])
def test_idle_phase_geometry_does_not_create_solver_dilation_direction(
    tmp_path, key, source, stage, entry
):
    root = tmp_path / 'input'
    mode = anchoring.write_idle_source(root, key, source, reverse=entry == 'analysis')
    project = engine.Project.load(root)
    project = prepare_stage(project, stage, tmp_path)
    assert project.structures['gamma'].cell.length_a.free == (source != 'unlinked-fixed'), (
        'Retaining idle geometry must preserve its independently authored free flag'
    )
    source_slope = 3.3 if anchoring.idle_source_is_solved(source) else 0.0
    if source == 'active-fixed-bank':
        source_slope = 0.0
    wavelength = 0.5 * 3.3
    response = (0.5 * source_slope - wavelength) / (2.2 * math.sqrt(1 - (wavelength / 4.4) ** 2))
    admitted = anchoring.idle_source_admits(source)
    assert (response != 0) == admitted, (
        'Only enabled phase-plan cell columns may co-dilate the relation-defined second line'
    )
    assert_boundary(project, mode, entry, admitted)


def prepare_stage(project, stage, tmp_path):
    if stage == 'calculated':
        project.analysis.calculate()
    elif stage == 'reopened':
        saved = tmp_path / 'saved'
        project.save_as(saved)
        project = engine.Project.load(saved)
    return project


def assert_boundary(project, mode, entry, admitted):
    if admitted:
        result = invoke_relation(project, mode, entry)
        assert result is not None, (
            'An observable participating anchor must admit the requested fit'
        )
        assert result.status == engine.FitStatus.CANCELLED, (
            'The admitted consumer fit must reach its public cancellation status'
        )
    else:
        with pytest.raises(ValueError, match=r'dilation|null direction'):
            invoke_relation(project, mode, entry)
