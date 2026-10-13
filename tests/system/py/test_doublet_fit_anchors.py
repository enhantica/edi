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
