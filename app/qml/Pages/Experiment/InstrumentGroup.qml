// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import edi.app

// `instrument` (easydiffractionbeta's Diffractometer): the fields of the experiment's beam mode —
// constant wavelength: wavelength and 2θ offset, and for X-rays the second wavelength, its intensity ratio and the
// monochromator polarization (the wavelengths on one row, the corrections on the next); time-of-flight: bank angle
// and the d→TOF terms. While the second line's intensity ratio is above 0, the first wavelength reads "Wavelength 1".
ParameterGrid {
    property ExperimentViewModel experiment: null
    // The doublet's intensity ratio, X-ray CW only (null otherwise); read again when the fields change.
    readonly property ParameterItem ratio: fields && fields.count >= 0 ? fields.parameterNamed("setup_wavelength_2_to_1_ratio") : null

    fields: experiment ? experiment.instrument : null
    labels: ratio !== null && ratio.value > 0 ? {
        "setup_wavelength": qsTr("Wavelength 1")
    } : ({})
    prefix: "instrument"
    fillRows: true
}
