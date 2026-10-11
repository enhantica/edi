// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// `minimizer` (easydiffractionbeta's Minimization engine): the engine — crysta, the one edi supports —
// the descent flow over crysta's registry, the declared iteration bound, and the chi-square tolerance the
// fit uses (declared, or crysta's default). Two rows of two (the owner, 2026-10-06), so the descent list is wide
// enough for its names; spaced as ParameterGrid spaces the instrument's fields.
Grid {
    id: row

    property AnalysisViewModel analysis: null
    readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - row.columnSpacing) / 2

    columns: 2
    columnSpacing: AppSizes.inputSpacing
    rowSpacing: AppSizes.groupContentSpacing

    SelectorField {
        objectName: "minimizer.type"
        width: row.fieldWidth
        label: qsTr("minimizer")
        options: row.analysis ? row.analysis.minimizerTypeOptions : null
        token: row.analysis ? row.analysis.minimizerType : ""
    }
    SelectorField {
        objectName: "minimizer.descent"
        width: row.fieldWidth
        label: qsTr("descent")
        options: row.analysis ? row.analysis.descentOptions : null
        token: row.analysis ? row.analysis.descent : ""
        onSelected: token => row.analysis.descent = token
    }
    ValueField {
        objectName: "minimizer.maxIterations"
        width: row.fieldWidth
        label: qsTr("max iterations")
        // The declared bound, or the fit's own when none is declared: the value the fit uses, as the
        // tolerance beside it (edi ADR-0017 §5).
        fieldValue: !row.analysis ? "" : row.analysis.hasMaxIterations ? row.analysis.maxIterations : row.analysis.defaultMaxIterations
        accepts: "integer"
        onCommitted: text => row.analysis.maxIterations = Number(text)
    }
    ValueField {
        objectName: "minimizer.chiSquareTolerance"
        width: row.fieldWidth
        label: qsTr("tolerance")
        // The declared tolerance, or crysta's default when none is declared: the value the fit uses.
        fieldValue: !row.analysis ? "" : row.analysis.hasChiSquareTolerance ? row.analysis.chiSquareTolerance : row.analysis.defaultChiSquareTolerance
        accepts: "number"
        onCommitted: text => row.analysis.chiSquareTolerance = Number(text)
    }
}
