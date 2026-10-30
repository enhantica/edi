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
// Above them, the facility and the instrument that measured the experiment (ADR-0052), chosen from lists for an
// experiment made from a data file and shown as its file states them otherwise (the owner, 2026-10-27).
Column {
    id: group

    property ExperimentViewModel experiment: null
    readonly property bool singleCrystalTimeOfFlight: experiment !== null && experiment.sampleForm === ExperimentViewModel.SingleCrystal && experiment.beamMode === ExperimentViewModel.TimeOfFlight
    readonly property SingleCrystalReflectionModel reflections: experiment ? experiment.singleCrystalReflections : null

    function band(low, high) {
        return ApplicationInfo.instrumentWavelengthBand(low, high);
    }

    spacing: AppSizes.groupContentSpacing

    EaElements.GroupRow {
        spacing: AppSizes.inputSpacing
        SelectorField {
            objectName: "instrument.facility"
            label: qsTr("Facility")
            options: group.experiment ? group.experiment.facilityOptions : null
            token: group.experiment ? group.experiment.facilityToken : ""
            writable: group.experiment !== null && group.experiment.descriptionEditable
            onSelected: token => group.experiment.facilityToken = token
        }
        SelectorField {
            objectName: "instrument.name"
            label: qsTr("Instrument")
            options: group.experiment ? group.experiment.instrumentOptions : null
            token: group.experiment ? group.experiment.instrumentToken : ""
            writable: group.experiment !== null && group.experiment.descriptionEditable
            onSelected: token => group.experiment.instrumentToken = token
        }
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
}
