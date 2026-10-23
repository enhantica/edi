// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// `instrument` (easydiffractionbeta's Diffractometer): the fields of the experiment's beam mode —
// constant wavelength: wavelength and 2θ offset, and for X-rays the second wavelength, its intensity ratio and the
// monochromator polarization (the wavelengths on one row, the corrections on the next); time-of-flight: bank angle
// and the d→TOF terms. While the second line's intensity ratio is above 0, the first wavelength reads "Wavelength 1".
// A time-of-flight single crystal measures each reflection at its own wavelength and its calculation reads no
// instrument parameter, so it shows only the band of its reflections' wavelengths, read-only (the owner, 2026-10-23).
Column {
    id: group

    property ExperimentViewModel experiment: null
    readonly property bool singleCrystalTimeOfFlight: experiment !== null && experiment.sampleForm === ExperimentViewModel.SingleCrystal && experiment.beamMode === ExperimentViewModel.TimeOfFlight
    readonly property SingleCrystalReflectionModel reflections: experiment ? experiment.singleCrystalReflections : null

    function band(low, high) {
        if (isNaN(low) || isNaN(high))
            return "";
        return low === high ? low.toFixed(4) : `${low.toFixed(4)}–${high.toFixed(4)}`;
    }

    ParameterGrid {
        id: grid

        // The doublet's intensity ratio, X-ray CW only (null otherwise); read again when the fields change.
        readonly property ParameterItem ratio: fields && fields.count >= 0 ? fields.parameterNamed("setup_wavelength_2_to_1_ratio") : null

        visible: !group.singleCrystalTimeOfFlight
        fields: group.experiment && !group.singleCrystalTimeOfFlight ? group.experiment.instrument : null
        labels: ratio !== null && ratio.value > 0 ? {
            "setup_wavelength": qsTr("Wavelength 1")
        } : ({})
        prefix: "instrument"
        fillRows: true
    }
    EaElements.GroupRow {
        visible: group.singleCrystalTimeOfFlight
        spacing: AppSizes.inputSpacing
        ValueField {
            objectName: "instrument.wavelengthBand"
            editable: false
            label: qsTr("Wavelength band")
            unit: "Å"
            fieldValue: group.reflections ? group.band(group.reflections.wavelengthLow, group.reflections.wavelengthHigh) : ""
        }
    }
}
