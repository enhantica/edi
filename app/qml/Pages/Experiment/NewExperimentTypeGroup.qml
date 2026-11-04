// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// With no experiment selected: the type the next experiment takes when measured data is loaded for a new one
// (ProjectViewModel.newExperiment…). The three axes a user chooses, since the data fixes them afterwards; the
// selectors of a selected experiment are ExperimentTypeGroup's.
Grid {
    id: row

    property ProjectViewModel project: null
    readonly property bool singleCrystal: project !== null && project.newExperimentSampleFormToken === "single crystal"
    readonly property real cellWidth: (EaStyle.Sizes.sideBarContentWidth - (row.columns - 1) * row.columnSpacing) / row.columns

    objectName: "newExperimentType"
    columns: 3
    columnSpacing: AppSizes.inputSpacing
    rowSpacing: AppSizes.groupContentSpacing

    SelectorField {
        objectName: "newExperimentType.sampleForm"
        width: row.cellWidth
        uid: "experiment_type.sample_form"
        options: row.project ? row.project.newExperimentSampleFormOptions : null
        token: row.project ? row.project.newExperimentSampleFormToken : ""
        onSelected: token => row.project.setNewExperimentType("sampleForm", token)
    }
    SelectorField {
        objectName: "newExperimentType.beamMode"
        width: row.cellWidth
        uid: "experiment_type.beam_mode"
        options: row.project ? row.project.newExperimentBeamModeOptions : null
        token: row.project ? row.project.newExperimentBeamModeToken : ""
        onSelected: token => row.project.setNewExperimentType("beamMode", token)
    }
    // A single crystal is computed for neutrons only for now, as for a selected experiment.
    Item {
        width: row.cellWidth
        height: radiationProbe.height

        SelectorField {
            id: radiationProbe
            objectName: "newExperimentType.radiationProbe"
            width: row.cellWidth
            uid: "experiment_type.radiation_probe"
            options: row.project ? row.project.newExperimentRadiationProbeOptions : null
            token: row.project ? row.project.newExperimentRadiationProbeToken : ""
            enabled: !row.singleCrystal
            onSelected: token => row.project.setNewExperimentType("radiationProbe", token)
        }
        HoverHandler {
            id: radiationProbeHover
        }
        EaElements.ToolTip {
            text: qsTr("Single crystals are neutron only for now")
            visible: row.singleCrystal && radiationProbeHover.hovered && EaGlobals.Vars.showToolTips
        }
    }
}
