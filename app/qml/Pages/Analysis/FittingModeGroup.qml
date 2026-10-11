// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// `fitting_mode`: single, joint, sequential or independent (the core's declared modes); joint shows
// the joint-fit weights, the scan modes the sequential-fit declaration.
EaElements.GroupRow {
    id: row
    spacing: AppSizes.inputSpacing

    property AnalysisViewModel analysis: null

    SelectorField {
        objectName: "fittingMode.type"
        label: qsTr("mode")
        options: row.analysis ? row.analysis.fittingModeOptions : null
        token: row.analysis ? row.analysis.fittingMode : ""
        onSelected: token => row.analysis.fittingMode = token
    }
}
