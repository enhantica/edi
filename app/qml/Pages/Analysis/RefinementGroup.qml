// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// `refine_ls`: a single-crystal fit's reflection cutoff (edi ADR-0050). Blank fits every reflection; n fits only those
// with F² > n su(F²), as FullProf's Rmub does.
Grid {
    id: row

    property AnalysisViewModel analysis: null
    readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - row.columnSpacing) / 2

    columns: 2
    columnSpacing: AppSizes.inputSpacing
    rowSpacing: AppSizes.groupContentSpacing

    ValueField {
        objectName: "refine_ls.thresholdSigma"
        width: row.fieldWidth
        label: qsTr("fit reflections above (su)")
        fieldValue: row.analysis && !isNaN(row.analysis.refineLsThresholdSigma) ? row.analysis.refineLsThresholdSigma : ""
        placeholderText: qsTr("all")
        accepts: "number"
        clearable: true
        onCommitted: text => row.analysis.refineLsThresholdSigma = text === "" ? NaN : Number(text)
    }
}
