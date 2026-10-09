// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
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

    readonly property real cellWidth: (EaStyle.Sizes.sideBarContentWidth - (row.columns - 1) * row.columnSpacing) / row.columns
    readonly property bool editable: experiment !== null && experiment.calculationOnly
    property ExperimentViewModel experiment: null
    property int experimentIndex: -1
    property ProjectViewModel project: null

    // A choice on one axis: the experiment made anew, or the box back at the stored value.
    function choose(box, axis, index) {
        const token = box.permittedValues[index];
        if (token !== box.value && row.project)
            row.project.setExperimentType(row.experimentIndex, axis, token);
        box.currentIndex = Qt.binding(() => box.permittedValues.indexOf(box.value));
    }

    columnSpacing: AppSizes.fieldSpacing
    columns: 3
    objectName: "experimentType"
    rowSpacing: AppSizes.groupContentSpacing

    EaElements.ParamComboBox {
        id: sampleForm

        currentIndex: permittedValues.indexOf(value)
        enabled: row.editable
        objectName: "experimentType.sampleForm"
        parameter: ({
                "value": row.experiment ? row.experiment.sampleFormToken : "",
                "shortPrettyName": qsTr("sample form"),
                "permittedValues": ["powder", "single crystal"]
            })
        width: row.cellWidth

        Component.onCompleted: FieldTitles.align(sampleForm)
        onActivated: index => row.choose(sampleForm, "sampleForm", index)
    }
    EaElements.ParamComboBox {
        id: beamMode

        currentIndex: permittedValues.indexOf(value)
        enabled: row.editable
        objectName: "experimentType.beamMode"
        parameter: ({
                "value": row.experiment ? row.experiment.beamModeToken : "",
                "shortPrettyName": qsTr("beam mode"),
                "permittedValues": ["constant wavelength", "time-of-flight"]
            })
        width: row.cellWidth

        Component.onCompleted: FieldTitles.align(beamMode)
        onActivated: index => row.choose(beamMode, "beamMode", index)
    }
    EaElements.ParamComboBox {
        id: radiationProbe

        currentIndex: permittedValues.indexOf(value)
        enabled: row.editable
        objectName: "experimentType.radiationProbe"
        parameter: ({
                "value": row.experiment ? row.experiment.radiationProbeToken : "",
                "shortPrettyName": qsTr("probe"),
                "permittedValues": ["neutron", "xray"]
            })
        width: row.cellWidth

        Component.onCompleted: FieldTitles.align(radiationProbe)
        onActivated: index => row.choose(radiationProbe, "radiationProbe", index)
    }
    EaElements.ParamComboBox {
        id: scatteringType

        currentIndex: permittedValues.indexOf(value)
        enabled: row.editable
        objectName: "experimentType.scatteringType"
        parameter: ({
                "value": row.experiment ? row.experiment.scatteringTypeToken : "",
                "shortPrettyName": qsTr("scattering type"),
                "permittedValues": ["bragg", "total"]
            })
        width: row.cellWidth

        Component.onCompleted: FieldTitles.align(scatteringType)
        onActivated: index => row.choose(scatteringType, "scatteringType", index)
    }
    EaElements.ParamComboBox {
        id: dimensionality

        currentIndex: 0
        enabled: false
        objectName: "experimentType.dimensionality"
        parameter: ({
                "value": "1D",
                "shortPrettyName": qsTr("dimensionality"),
                "permittedValues": ["1D"]
            })
        width: row.cellWidth

        Component.onCompleted: FieldTitles.align(dimensionality)
    }
    EaElements.ParamComboBox {
        id: polarization

        currentIndex: 0
        enabled: false
        objectName: "experimentType.polarization"
        parameter: ({
                "value": "None",
                "shortPrettyName": qsTr("polarization"),
                "permittedValues": ["None"]
            })
        visible: row.experiment !== null && row.experiment.radiationProbe === ExperimentViewModel.Neutron
        width: row.cellWidth

        Component.onCompleted: FieldTitles.align(polarization)
    }
}
