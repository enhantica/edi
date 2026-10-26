"""A deferred experiment import has one terminal reason and no partial warnings."""

import pytest


def reason(message):
    assert message.count('Reading CIF files is not supported yet') == 1, (
        'An experiment CIF unsupported on main gives the shared refusal reason once: ' + message
    )


def no_warnings(messages, stderr):
    assert not messages, 'A deferred CIF import emits no partial-import warning before refusal'
    assert not stderr.strip(), 'A deferred CIF import has no unaccounted native diagnostic'


def main_values(experiment):
    assert experiment.instrument.setup_wavelength.value == pytest.approx(1.494), (
        'Main already imports the frozen diffraction-lib wavelength'
    )
    assert experiment.instrument.calib_twotheta_offset.value == pytest.approx(0.6225), (
        'Main already imports the frozen diffraction-lib nonzero angular offset'
    )
    assert [
        getattr(experiment.peak, 'broad_gauss_' + axis).value for axis in 'uvw'
    ] == pytest.approx([0.0834, -0.1168, 0.123]), (
        'Main already imports the classic CIF Gaussian profile coefficients'
    )
    assert list(experiment.data.two_theta) == pytest.approx([10.5, 11.25]), (
        'Main already imports both measured angular coordinates'
    )
    assert list(experiment.data.intensity_meas) == pytest.approx([100, 121]), (
        'Main already imports both measured intensities'
    )
    assert list(experiment.data.intensity_meas_su) == pytest.approx([10, 11]), (
        'Main already imports both measured standard uncertainties'
    )
