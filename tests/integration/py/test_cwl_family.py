"""Closed forms and file-boundary witnesses for the CW profile family."""

import re

import edi as engine
import numpy as np
import pytest

from tests.fixtures.cwl_family import profiles


@pytest.mark.parametrize('token', profiles.TOKENS)
def test_each_declared_profile_calculates_and_roundtrips(tmp_path, token):
    project = engine.Project.load(profiles.write_project(tmp_path / 'input', token))
    project.analysis.calculate()
    before = np.asarray(project.experiments[0].data.intensity_calc).copy()
    assert np.isfinite(before).all(), 'Every declared CW profile must calculate finite values'
    assert np.any(before > 0), 'Every declared CW profile must calculate a finite nonzero pattern'
    project.save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/experiments/bank.edi').read_text()
    assert re.search(r'_peak.type\s+["\']?' + re.escape(token) + r'["\']?\s', text), (
        'Saving must retain the exact selected CW token'
    )
    reopened = engine.Project.load(tmp_path / 'saved')
    reopened.analysis.calculate()
    np.testing.assert_array_equal(
        before,
        reopened.experiments[0].data.intensity_calc,
        err_msg='A CW profile must retain its calculated values after reload',
    )


def test_supported_cw_inventory_contains_exactly_the_six_profiles(tmp_path, capsys):
    project = engine.Project.load(profiles.write_project(tmp_path, 'cwl-pseudo-voigt'))
    project.experiments[0].peak.show_supported()
    tokens = set(re.findall(r'cwl-[a-z-]+', capsys.readouterr().out))
    assert tokens == set(profiles.TOKENS), (
        'The selectable CW inventory must be exactly the declared six profiles'
    )


@pytest.mark.parametrize('token', profiles.RETIRED, ids=['retired-fcj', 'retired-beba'])
def test_retired_tokens_are_named_unknown_profile_errors(tmp_path, token):
    with pytest.raises((ValueError, RuntimeError)) as failure:
        engine.Project.load(profiles.write_project(tmp_path, token))
    assert token in str(failure.value), 'A retired token refusal must name the token'
    assert 'unknown' in str(failure.value).lower(), (
        'A retired token must be refused as an unknown profile and named in the diagnostic'
    )


@pytest.mark.parametrize('token', profiles.TOKENS[:4])
def test_npr_family_refuses_tch_lorentz_widths(tmp_path, token):
    engine.Project.load(profiles.write_project(tmp_path / 'valid', token))
    with pytest.raises((ValueError, RuntimeError)) as failure:
        engine.Project.load(
            profiles.write_project(tmp_path / 'foreign', token, extra='_peak.broad_lorentz_y .031')
        )
    assert 'broad_lorentz_y' in str(failure.value), (
        'A foreign-width refusal must name the parameter'
    )
    assert token in str(failure.value), (
        'A foreign TCH width must be refused by name and declared profile type'
    )


@pytest.mark.parametrize('wavelength', [1.54, 2.37])
@pytest.mark.parametrize('token', profiles.TOKENS[:3])
def test_npr_shapes_match_absolute_normalized_closed_forms(tmp_path, token, wavelength):
    project = engine.Project.load(profiles.write_project(tmp_path, token, wavelength))
    centre, width, grid, area = profiles.geometry(wavelength)
    eta = int(token != profiles.TOKENS[0])
    if token == profiles.TOKENS[2]:
        intercept, slope = profiles.mixing_parameters(project.experiments[0].peak)
        intercept.value, slope.value = profiles.ETA, profiles.SLOPE
        eta = profiles.ETA + profiles.SLOPE * centre
    project.analysis.calculate()
    expected = area * profiles.shape(grid - centre, width, eta)
    np.testing.assert_allclose(
        project.experiments[0].data.intensity_calc,
        expected,
        rtol=2e-10,
        atol=1e-10,
        err_msg='Npr 0/1/5 must use normalized shapes and reflection angles in degrees',
    )
