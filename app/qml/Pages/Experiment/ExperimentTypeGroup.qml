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
// (ProjectViewModel.setExperimentType). Each box binds its index to the value's position in its permitted list:
// the base binds currentIndex to indexOfValue(value), which runs before the model is populated and re-runs only
// when the value changes, so a value that never changes stayed at -1 and showed nothing. A grid three wide, so
// each name fits (edi ADR-0017 §2): each box sets its own width, as the base's divides the row by its parent's
// children.
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

    // A choice on one axis: the experiment made anew, or the box back at the stored value.
    function choose(box, axis, index) {
        const token = box.permittedValues[index];
        if (token !== box.value && row.project)
            row.project.setExperimentType(row.experimentIndex, axis, token);
        box.currentIndex = Qt.binding(() => box.permittedValues.indexOf(box.value));
    }

    objectName: "experimentType"
    columns: 3
    columnSpacing: AppSizes.inputSpacing
    rowSpacing: AppSizes.groupContentSpacing

    EaElements.ParamComboBox {
        id: sampleForm
        objectName: "experimentType.sampleForm"
        width: row.cellWidth
        Component.onCompleted: FieldTitles.align(sampleForm)
        enabled: row.editable
        currentIndex: permittedValues.indexOf(value)
        parameter: ({
                "value": row.experiment ? row.experiment.sampleFormToken : "",
                "shortPrettyName": qsTr("sample form"),
                "permittedValues": ["powder", "single crystal"]
            })
        onActivated: index => row.choose(sampleForm, "sampleForm", index)
    }
    // A single crystal is computed for neutrons at constant wavelength only for now: those two boxes are fixed
    // for it, with a tool tip saying so (the owner, 2026-10-22).
    Item {
        width: row.cellWidth
        height: beamMode.height

        EaElements.ParamComboBox {
            id: beamMode
            objectName: "experimentType.beamMode"
            width: row.cellWidth
            Component.onCompleted: FieldTitles.align(beamMode)
            enabled: row.editable && !row.singleCrystal
            currentIndex: permittedValues.indexOf(value)
            parameter: ({
                    "value": row.experiment ? row.experiment.beamModeToken : "",
                    "shortPrettyName": qsTr("beam mode"),
                    "permittedValues": ["constant wavelength", "time-of-flight"]
                })
            onActivated: index => row.choose(beamMode, "beamMode", index)
        }
        HoverHandler {
            id: beamModeHover
        }
        EaElements.ToolTip {
            text: qsTr("Single crystals are constant wavelength only for now")
            visible: row.singleCrystal && row.editable && beamModeHover.hovered && EaGlobals.Vars.showToolTips
        }
    }
    Item {
        width: row.cellWidth
        height: radiationProbe.height

        EaElements.ParamComboBox {
            id: radiationProbe
            objectName: "experimentType.radiationProbe"
            width: row.cellWidth
            Component.onCompleted: FieldTitles.align(radiationProbe)
            enabled: row.editable && !row.singleCrystal
            currentIndex: permittedValues.indexOf(value)
            parameter: ({
                    "value": row.experiment ? row.experiment.radiationProbeToken : "",
                    "shortPrettyName": qsTr("probe"),
                    "permittedValues": ["neutron", "xray"]
                })
            onActivated: index => row.choose(radiationProbe, "radiationProbe", index)
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

        EaElements.ParamComboBox {
            id: scatteringType
            objectName: "experimentType.scatteringType"
            width: row.cellWidth
            Component.onCompleted: FieldTitles.align(scatteringType)
            enabled: false
            currentIndex: permittedValues.indexOf(value)
            parameter: ({
                    "value": row.experiment ? row.experiment.scatteringTypeToken : "",
                    "shortPrettyName": qsTr("scattering type"),
                    "permittedValues": ["bragg", "total"]
                })
            onActivated: index => row.choose(scatteringType, "scatteringType", index)
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
