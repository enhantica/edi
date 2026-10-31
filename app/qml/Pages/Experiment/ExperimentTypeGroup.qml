// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `experiment_type` (easydiffractionbeta's Diffraction radiation group), in the Experiments explorer under its
// table: the selected experiment's four type axes, editable while it has no measured data and fixed once it has
// (its data sets them), and its dimensionality and polarisation, each with the one value it admits (ADR-0053). A choice makes the experiment anew with that type
// (ProjectViewModel.setExperimentType). The four axes show their values by the dictionary's names (edi ADR-0051).
// A grid three wide, so each name fits (edi ADR-0017 §2): each box sets its own width, as the base's divides the
// row by its parent's children.
Grid {
    id: row

    property ProjectViewModel project: null
    property ExperimentViewModel experiment: null
    property int experimentIndex: -1
    // The type axes may change while nothing measured is held: a calculation grid, or a single crystal with no
    // reflections loaded yet.
    readonly property bool editable: experiment !== null && experiment.calculationOnly
    readonly property bool singleCrystal: experiment !== null && experiment.sampleForm === ExperimentViewModel.SingleCrystal
    readonly property real cellWidth: (EaStyle.Sizes.sideBarContentWidth - (row.columns - 1) * row.columnSpacing) / row.columns

    // A choice on one axis makes the experiment anew; the selector returns to the stored value otherwise.
    function choose(axis, token) {
        if (row.project)
            row.project.setExperimentType(row.experimentIndex, axis, token);
    }

    objectName: "experimentType"
    columns: 3
    columnSpacing: AppSizes.inputSpacing
    rowSpacing: AppSizes.groupContentSpacing

    SelectorField {
        id: sampleForm
        objectName: "experimentType.sampleForm"
        width: row.cellWidth
        uid: "experiment_type.sample_form"
        options: row.experiment ? row.experiment.sampleFormOptions : null
        token: row.experiment ? row.experiment.sampleFormToken : ""
        enabled: row.editable
        onSelected: token => row.choose("sampleForm", token)
    }
    SelectorField {
        id: beamMode
        objectName: "experimentType.beamMode"
        width: row.cellWidth
        uid: "experiment_type.beam_mode"
        options: row.experiment ? row.experiment.beamModeOptions : null
        token: row.experiment ? row.experiment.beamModeToken : ""
        enabled: row.editable
        onSelected: token => row.choose("beamMode", token)
    }
    // A single crystal is computed for neutrons only for now: its probe box is fixed, with a tool tip saying so
    // (the owner, 2026-10-22).
    Item {
        width: row.cellWidth
        height: radiationProbe.height

        SelectorField {
            id: radiationProbe
            objectName: "experimentType.radiationProbe"
            width: row.cellWidth
            uid: "experiment_type.radiation_probe"
            options: row.experiment ? row.experiment.radiationProbeOptions : null
            token: row.experiment ? row.experiment.radiationProbeToken : ""
            enabled: row.editable && !row.singleCrystal
            onSelected: token => row.choose("radiationProbe", token)
        }
        HoverHandler {
            id: radiationProbeHover
        }
        EaElements.ToolTip {
            text: qsTr("Single crystals are neutron only for now")
            visible: row.singleCrystal && row.editable && radiationProbeHover.hovered && EaGlobals.Vars.showToolTips
        }
    }
    // Disabled while edi computes one choice only, with a tool tip saying so (the owner, 2026-10-08, note 44);
    // the tool tip is the cell's, since a disabled box takes no hover.
    Item {
        width: row.cellWidth
        height: scatteringType.height

        SelectorField {
            id: scatteringType
            objectName: "experimentType.scatteringType"
            width: row.cellWidth
            uid: "experiment_type.scattering_type"
            options: row.experiment ? row.experiment.scatteringTypeOptions : null
            token: row.experiment ? row.experiment.scatteringTypeToken : ""
            enabled: false
            onSelected: token => row.choose("scatteringType", token)
        }
        HoverHandler {
            id: scatteringTypeHover
        }
        EaElements.ToolTip {
            text: qsTr("Only Bragg scattering is supported for now")
            visible: scatteringTypeHover.hovered && EaGlobals.Vars.showToolTips
        }
    }
    // One admitted value each, so the boxes show it and take no choice: the dimensionality, and the polarisation of
    // the probe (ADR-0053).
    SelectorField {
        id: dimensionality
        objectName: "experimentType.dimensionality"
        width: row.cellWidth
        uid: "experiment_type.dimensionality"
        options: row.experiment ? row.experiment.dimensionalityOptions : null
        token: row.experiment ? row.experiment.dimensionalityToken : ""
        enabled: false
    }
    SelectorField {
        id: polarisation
        objectName: "experimentType.polarisation"
        width: row.cellWidth
        uid: "experiment_type.polarisation"
        options: row.experiment ? row.experiment.polarisationOptions : null
        token: row.experiment ? row.experiment.polarisationToken : ""
        enabled: false
    }
}
