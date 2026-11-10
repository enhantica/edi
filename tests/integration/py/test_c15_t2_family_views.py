"""F1 explicit, factory and retained X-ray views cannot lose live state."""

import re

import edi
import pytest

from tests.fixtures.c15_t2_polarization.family_projects import family_project

TERMS = ('setup_polarization_coefficient', 'setup_monochromator_twotheta')


def _refusal(error):
    assert re.search(r'polarization|monochromator|X-ray|xray', str(error), re.IGNORECASE), (
        ' F1 refusal must name the incompatible X-ray polarization state: ' + str(error)
    )


@pytest.mark.parametrize('term', TERMS)
@pytest.mark.parametrize('family', ['neutron-cw', 'tof'])
@pytest.mark.parametrize('route', ['explicit', 'factory', 'retained'])
@pytest.mark.parametrize('state', ['value', 'free', 'declared'])
@pytest.mark.parametrize('endpoint', ['calculate', 'single-fit', 'joint-fit', 'save'])
def test_foreign_view_cannot_hide_polarization(
    tmp_path,
    term,
    family,
    route,
    state,
    endpoint,
):
    loaded_family = 'xray-bare' if route == 'retained' else family
    project = edi.Project.load(family_project(tmp_path / 'input', loaded_family))
    try:  # noqa: PLW0717
        if route == 'explicit':
            instrument = edi.CwlPdXrayInstrument(project.experiment)
        elif route == 'factory':
            instrument = edi.InstrumentFactory.create('cwl-pd-xray', project.experiment)
        else:
            instrument = project.experiment.instrument
        parameter = edi.Parameter(0.37 if term == TERMS[0] else 41.0, None, state == 'free')
        if state != 'value':
            parameter.value = 0.0
        if state == 'declared':
            parameter.uncertainty = 0.0
        setattr(instrument, term, parameter)
        if route == 'retained':
            project.experiment.experiment_type.radiation_probe = edi.RadiationProbeEnum.NEUTRON
            if family == 'tof':
                project.experiment.experiment_type.beam_mode = edi.BeamModeEnum.TIME_OF_FLIGHT
        if endpoint == 'calculate':
            project.analysis.calculate()
        elif endpoint == 'single-fit':
            project.analysis.fit()
        elif endpoint == 'joint-fit':
            project.fitting_mode = 'joint'
            project.analysis.fit()
        else:
            project.save_as(tmp_path / 'saved')
    except (ValueError, RuntimeError, edi.IoError) as error:
        _refusal(error)
        return
    pytest.fail(
        ' F1 explicit/factory/retained views must refuse incompatible polarization '
        'before consumption instead of silently dropping visible parameter state'
    )


@pytest.mark.parametrize('route', ['explicit', 'factory', 'retained'])
def test_valid_xray_views_preserve_each_live_parameter(tmp_path, route):
    project = edi.Project.load(family_project(tmp_path / 'input', 'xray'))
    instrument = (
        edi.CwlPdXrayInstrument(project.experiment)
        if route == 'explicit'
        else edi.InstrumentFactory.create('cwl-pd-xray', project.experiment)
        if route == 'factory'
        else project.experiment.instrument
    )
    for term, value in zip(TERMS, (0.37, 41.0), strict=True):
        setattr(instrument, term, edi.Parameter(value, None, True))
    project.analysis.calculate()
    project.save_as(tmp_path / 'saved')
    restored = edi.Project.load(tmp_path / 'saved')
    for term, value in zip(TERMS, (0.37, 41.0), strict=True):
        actual = getattr(restored.experiment.instrument, term)
        assert actual.value == value and actual.free, (
            ' F1 valid explicit/factory/retained views preserve both nonidentity free terms'
        )
