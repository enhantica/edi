"""U1 — surviving parameter-metadata failures and range boundaries."""

import edi
import pytest


def test_c11_t40_bare_parameter_metadata_access_fails_closed():
    bare = edi.Parameter(1.0)
    with pytest.raises(RuntimeError, match='no metadata spec'):
        _ = bare.units


def _cw_project():
    structure = edi.Structure()
    structure.name = 'demo'
    structure.space_group.name_h_m = 'P 1'

    experiment = edi.BraggPdExperiment()
    experiment.name = 'cw_bank'
    experiment.experiment_type.beam_mode = edi.BeamModeEnum.CONSTANT_WAVELENGTH
    experiment.peak.type = edi.PeakProfileTypeEnum.CWL_PSEUDO_VOIGT
    experiment.peak.cutoff_fwhm = 8.0
    experiment.peak.broad_gauss_u = edi.Parameter(0.1)
    experiment.peak.broad_gauss_v = edi.Parameter(-0.05)
    experiment.peak.broad_gauss_w = edi.Parameter(0.2)
    experiment.peak.broad_lorentz_x = edi.Parameter(0.0)
    experiment.peak.broad_lorentz_y = edi.Parameter(0.0)
    experiment.instrument.setup_wavelength = edi.Parameter(1.87)
    experiment.instrument.calib_twotheta_offset = edi.Parameter(0.0)
    experiment.linked_structure.structure_id = 'demo'
    experiment.linked_structure.scale = edi.Parameter(1.0)
    point = edi.LineSegment()
    point.position = 10.0
    point.intensity = edi.Parameter(100.0)
    experiment.background = [point]

    project = edi.Project(name='cw-range-boundary')
    project.structure = structure
    project.experiment = experiment
    return project


def test_c11_t40_cw_load_boundary_enforces_the_declared_range(tmp_path, capfd):
    """: nonpositive wavelengths refuse at the whole-project boundary.

    Before: -1.87 loaded, warned and survived save/reopen under F9. After:
    the engine's positive-wavelength domain refuses it at load, structurally.
    Wavelength's editing range is [0, infinity], so there is no physically valid
    out-of-editing-range wavelength. Saved ADP/occupancy warning gates retain
    that distinct rule. Keep the nonidentity positive round-trip control.
    """
    destination = tmp_path / 'cw-project'
    _cw_project().save_as(destination)

    experiment_file = destination / 'experiments' / 'cw_bank.edi'
    text = experiment_file.read_text()
    assert '_instrument.setup_wavelength 1.87' in text, (
        ' CW witness retains its original nontrivial wavelength seam'
    )
    text += (
        '\nloop_\n_data.two_theta\n_data.id\n_data.intensity_meas'
        '\n_data.intensity_meas_su\n10 1 100 1\n10.25 2 100 1\n11 3 100 1\n'
    )
    for token in ('-1.87', '0'):
        invalid = text.replace(
            '_instrument.setup_wavelength 1.87', '_instrument.setup_wavelength ' + token
        )
        experiment_file.write_text(invalid)
        capfd.readouterr()
        with pytest.raises(edi.DomainValidationError) as caught:
            edi.Project.load(destination)
        assert 'setup_wavelength' in str(caught.value), (
            ' CW load names the nonpositive wavelength physical-domain refusal'
        )
        assert caught.value.diagnostics, ' CW load refusal carries structured diagnostics'
        assert all(
            str(item.severity).lower().endswith('error') for item in caught.value.diagnostics
        ), ' CW physical-domain refusal has error severity'
        assert 'loaded as saved' not in capfd.readouterr().err, (
            ' CW physical-domain refusal never reports successful warning admission'
        )
        assert experiment_file.read_text() == invalid, (
            ' CW refused load preserves the original saved wavelength bytes'
        )

    experiment_file.write_text(text)
    loaded = edi.Project.load(destination)
    assert loaded.experiment.instrument.setup_wavelength.value == 1.87, (
        ' CW load preserves the exact physically valid positive wavelength'
    )
    with pytest.raises((ValueError, TypeError), match='admissible range'):
        loaded.experiment.instrument.setup_wavelength = edi.Parameter(-1.87)
    saved = tmp_path / 'cw-roundtrip'
    loaded.save_as(saved)
    capfd.readouterr()
    reopened = edi.Project.load(saved)
    assert reopened.experiment.instrument.setup_wavelength.value == 1.87, (
        ' save/reopen retains the original positive wavelength without clamping'
    )
    for token in ('nan', 'inf', '-inf', '-1.87oops'):
        experiment_file.write_text(
            text.replace(
                '_instrument.setup_wavelength 1.87', '_instrument.setup_wavelength ' + token
            )
        )
        with pytest.raises(edi.IoError):
            edi.Project.load(destination)
