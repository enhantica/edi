// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// `instrument` (easydiffractionbeta's Diffractometer): the fields of the experiment's beam mode —
// constant wavelength: wavelength and 2θ offset, and for X-rays the second wavelength, its intensity ratio and the
// monochromator polarization (the wavelengths on one row, the corrections on the next); time-of-flight: bank angle
// and the d→TOF terms. While the second line's intensity ratio is above 0, the first wavelength reads by the
// dictionary's doublet label, which the parameter registry gives it.
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
        const shown = value => Session.display("refln.wavelength", value);
        return low === high ? shown(low) : `${shown(low)}–${shown(high)}`;
    }

    ParameterGrid {
        id: grid

        visible: !group.singleCrystalTimeOfFlight
        fields: group.experiment && !group.singleCrystalTimeOfFlight ? group.experiment.instrument : null
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
            unit: Session.units("refln.wavelength")
            fieldValue: group.reflections ? group.band(group.reflections.wavelengthLow, group.reflections.wavelengthHigh) : ""
        }
    }
    // The instrument and facility that measured the experiment (ADR-0052), as its file states them.
    EaElements.GroupRow {
        spacing: AppSizes.inputSpacing
        ValueField {
            objectName: "instrument.name"
            editable: false
            label: Session.label("instrument.name")
            fieldValue: group.experiment && group.experiment.instrumentName !== "" ? group.experiment.instrumentName : qsTr("Not specified")
        }
        ValueField {
            objectName: "instrument.facility"
            editable: false
            label: Session.label("instrument.facility")
            fieldValue: group.experiment && group.experiment.facility !== "" ? group.experiment.facility : qsTr("Not specified")
        }
    }
}
