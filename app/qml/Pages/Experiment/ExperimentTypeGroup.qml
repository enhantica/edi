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

    property ProjectViewModel project: null
    property ExperimentViewModel experiment: null
    property int experimentIndex: -1
    readonly property bool editable: experiment !== null && experiment.calculationOnly
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
    EaElements.ParamComboBox {
        id: beamMode
        objectName: "experimentType.beamMode"
        width: row.cellWidth
        Component.onCompleted: FieldTitles.align(beamMode)
        enabled: row.editable
        currentIndex: permittedValues.indexOf(value)
        parameter: ({
                "value": row.experiment ? row.experiment.beamModeToken : "",
                "shortPrettyName": qsTr("beam mode"),
                "permittedValues": ["constant wavelength", "time-of-flight"]
            })
        onActivated: index => row.choose(beamMode, "beamMode", index)
    }
    EaElements.ParamComboBox {
        id: radiationProbe
        objectName: "experimentType.radiationProbe"
        width: row.cellWidth
        Component.onCompleted: FieldTitles.align(radiationProbe)
        enabled: row.editable
        currentIndex: permittedValues.indexOf(value)
        parameter: ({
                "value": row.experiment ? row.experiment.radiationProbeToken : "",
                "shortPrettyName": qsTr("probe"),
                "permittedValues": ["neutron", "xray"]
            })
        onActivated: index => row.choose(radiationProbe, "radiationProbe", index)
    }
    EaElements.ParamComboBox {
        id: scatteringType
        objectName: "experimentType.scatteringType"
        width: row.cellWidth
        Component.onCompleted: FieldTitles.align(scatteringType)
        enabled: row.editable
        currentIndex: permittedValues.indexOf(value)
        parameter: ({
                "value": row.experiment ? row.experiment.scatteringTypeToken : "",
                "shortPrettyName": qsTr("scattering type"),
                "permittedValues": ["bragg", "total"]
            })
        onActivated: index => row.choose(scatteringType, "scatteringType", index)
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
