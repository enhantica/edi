// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `experiment_type` (easydiffractionbeta's Diffraction radiation group): the four type axes as
// disabled combo boxes — the type is read-only; an undeclared axis of a project opened whole shows its
// effective value. Each binds its index to the value's position in its permitted list: the base binds
// currentIndex to indexOfValue(value), which runs before the model is populated and re-runs only when
// the value changes, so a value that never changes stayed at -1 and showed nothing. A grid three wide,
// so each name fits and two more axes have their places (edi ADR-0017 §2): each box sets its own width,
// as the base's divides the row by its parent's children.
Grid {
    id: row

    property ExperimentViewModel experiment: null
    readonly property real cellWidth: (EaStyle.Sizes.sideBarContentWidth - (row.columns - 1) * row.columnSpacing) / row.columns

    columns: 3
    columnSpacing: AppSizes.fieldSpacing
    rowSpacing: AppSizes.groupContentSpacing

    EaElements.ParamComboBox {
        id: sampleForm
        objectName: "experimentType.sampleForm"
        width: row.cellWidth
        Component.onCompleted: FieldTitles.align(sampleForm)
        enabled: false
        currentIndex: permittedValues.indexOf(value)
        parameter: ({
                "value": row.experiment ? row.experiment.sampleFormToken : "",
                "shortPrettyName": qsTr("sample form"),
                "permittedValues": ["powder", "single crystal"]
            })
    }
    EaElements.ParamComboBox {
        id: beamMode
        objectName: "experimentType.beamMode"
        width: row.cellWidth
        Component.onCompleted: FieldTitles.align(beamMode)
        enabled: false
        currentIndex: permittedValues.indexOf(value)
        parameter: ({
                "value": row.experiment ? row.experiment.beamModeToken : "",
                "shortPrettyName": qsTr("beam mode"),
                "permittedValues": ["constant wavelength", "time-of-flight"]
            })
    }
    EaElements.ParamComboBox {
        id: radiationProbe
        objectName: "experimentType.radiationProbe"
        width: row.cellWidth
        Component.onCompleted: FieldTitles.align(radiationProbe)
        enabled: false
        currentIndex: permittedValues.indexOf(value)
        parameter: ({
                "value": row.experiment ? row.experiment.radiationProbeToken : "",
                "shortPrettyName": qsTr("probe"),
                "permittedValues": ["neutron", "xray"]
            })
    }
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
    }
}
