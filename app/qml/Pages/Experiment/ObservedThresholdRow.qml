// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// `reflns`: which of a single crystal's reflections count as observed (edi ADR-0050), the n of the su and the basis
// (I or F), each blank until set, with the default I > 2u(I) as placeholder; the expression they make follows. It
// decides the counts and R factors a save reports, never which reflections the fit uses.
Grid {
    id: row

    property ExperimentViewModel experiment: null
    readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - 2 * row.columnSpacing) / 3

    columns: 3
    columnSpacing: AppSizes.inputSpacing
    rowSpacing: AppSizes.groupContentSpacing

    ValueField {
        objectName: "reflns.thresholdSigma"
        width: row.fieldWidth
        label: qsTr("observed above (su)")
        fieldValue: row.experiment && !isNaN(row.experiment.reflnsThresholdSigma) ? row.experiment.reflnsThresholdSigma : ""
        placeholderText: "2"
        accepts: "number"
        clearable: true
        onCommitted: text => row.experiment.reflnsThresholdSigma = text === "" ? NaN : Number(text)
    }
    SelectorField {
        objectName: "reflns.thresholdBasis"
        width: row.fieldWidth
        label: qsTr("on")
        options: row.experiment ? row.experiment.reflnsThresholdBasisOptions : null
        token: row.experiment ? (row.experiment.reflnsThresholdBasis || "intensity") : ""
        onSelected: token => row.experiment.reflnsThresholdBasis = token
    }
    ValueField {
        objectName: "reflns.thresholdExpression"
        width: row.fieldWidth
        label: qsTr("threshold")
        fieldValue: row.experiment ? row.experiment.reflnsThresholdExpression : ""
        editable: false
    }
}
