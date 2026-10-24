// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `experiment_type` (easydiffractionbeta's Diffraction radiation group), in the Experiments explorer under its
// table: the selected experiment's four type axes, editable while it has no measured data and fixed once it has
// (its data sets them), and two placeholders, disabled until they are implemented: dimensionality (1D) and
// polarization (None, for a neutron probe only). A choice makes the experiment anew with that type
// (ProjectViewModel.setExperimentType). The four axes show their values by the dictionary's names (edi ADR-0051).
// A grid three wide, so each name fits (edi ADR-0017 §2): each box sets its own width, as the base's divides the
// row by its parent's children.
Grid {
    id: row

    property ProjectViewModel project: null
    property ExperimentViewModel experiment: null
    property int experimentIndex: -1
    readonly property bool editable: experiment !== null && experiment.calculationOnly
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

    // Disabled while edi computes one choice only, with a tool tip saying so (the owner, 2026-10-08, note 44);
    // the tool tip is the cell's, since a disabled box takes no hover.
    Item {
        width: row.cellWidth
        height: sampleForm.height

        SelectorField {
            id: sampleForm
            objectName: "experimentType.sampleForm"
            width: row.cellWidth
            uid: "experiment_type.sample_form"
            options: row.experiment ? row.experiment.sampleFormOptions : null
            token: row.experiment ? row.experiment.sampleFormToken : ""
            writable: false
            onSelected: token => row.choose("sampleForm", token)
        }
        HoverHandler {
            id: sampleFormHover
        }
        EaElements.ToolTip {
            text: qsTr("Only powder samples are supported for now")
            visible: sampleFormHover.hovered && EaGlobals.Vars.showToolTips
        }
    }
    SelectorField {
        id: beamMode
        objectName: "experimentType.beamMode"
        width: row.cellWidth
        uid: "experiment_type.beam_mode"
        options: row.experiment ? row.experiment.beamModeOptions : null
        token: row.experiment ? row.experiment.beamModeToken : ""
        writable: row.editable
        onSelected: token => row.choose("beamMode", token)
    }
    SelectorField {
        id: radiationProbe
        objectName: "experimentType.radiationProbe"
        width: row.cellWidth
        uid: "experiment_type.radiation_probe"
        options: row.experiment ? row.experiment.radiationProbeOptions : null
        token: row.experiment ? row.experiment.radiationProbeToken : ""
        writable: row.editable
        onSelected: token => row.choose("radiationProbe", token)
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
            writable: false
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
    EaElements.ParamComboBox {
        id: dimensionality
        objectName: "experimentType.dimensionality"
        width: row.cellWidth
        Component.onCompleted: FieldTitles.align(dimensionality)
        enabled: false
        currentIndex: 0
        parameter: ({
                "value": "1D",
                "shortPrettyName": qsTr("dimensionality"),
                "permittedValues": ["1D"]
            })
    }
    EaElements.ParamComboBox {
        id: polarization
        objectName: "experimentType.polarization"
        width: row.cellWidth
        Component.onCompleted: FieldTitles.align(polarization)
        visible: row.experiment !== null && row.experiment.radiationProbe === ExperimentViewModel.Neutron
        enabled: false
        currentIndex: 0
        parameter: ({
                "value": "None",
                "shortPrettyName": qsTr("polarization"),
                "permittedValues": ["None"]
            })
    }
}
