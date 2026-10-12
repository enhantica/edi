// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `fitting_mode`: the modes that apply to the project, by their descriptive names (the owner, 2026-10-11): single for
// one experiment, joint for several, sequential, independent or single (the shown dataset) for a scan. With only
// one, the selector shows it disabled and says why. Joint shows the joint-fit weights, the scan modes the
// sequential-fit declaration.
EaElements.GroupRow {
    id: row
    spacing: AppSizes.inputSpacing

    property AnalysisViewModel analysis: null
    readonly property bool onlyMode: row.analysis !== null && row.analysis.fittingModeOptions.count === 1

    SelectorField {
        objectName: "fittingMode.type"
        label: qsTr("mode")
        options: row.analysis ? row.analysis.fittingModeOptions : null
        token: row.analysis ? row.analysis.fittingMode : ""
        writable: !row.onlyMode
        onSelected: token => row.analysis.fittingMode = token
    }

    // A disabled selector takes no hover, so the row says why it is the only mode.
    HoverHandler {
        id: hover
    }
    EaElements.ToolTip {
        text: !row.onlyMode ? "" : row.analysis.fittingMode === "joint" ? qsTr("A project with several experiments fits them all at once") : qsTr("A project with one experiment fits it on its own")
        visible: text !== "" && hover.hovered && EaGlobals.Vars.showToolTips
    }
}
