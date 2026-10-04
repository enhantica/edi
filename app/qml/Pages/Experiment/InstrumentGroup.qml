// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import edi.app

// `instrument` (easydiffractionbeta's Diffractometer): the fields of the experiment's beam mode —
// constant wavelength: wavelength and 2θ offset; time-of-flight: bank angle and the d→TOF terms.
ParameterGrid {
    property ExperimentViewModel experiment: null

    fields: experiment ? experiment.instrument : null
    prefix: "instrument"
    fillRows: true
}
