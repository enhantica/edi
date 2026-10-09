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

    columnSpacing: AppSizes.fieldSpacing
    columns: 2
    rowSpacing: AppSizes.groupContentSpacing

    SelectorField {
        label: qsTr("minimizer")
        objectName: "minimizer.type"
        options: row.analysis ? row.analysis.minimizerTypeOptions : null
        token: row.analysis ? row.analysis.minimizerType : ""
        width: row.fieldWidth
    }
    SelectorField {
        label: qsTr("descent")
        objectName: "minimizer.descent"
        options: row.analysis ? row.analysis.descentOptions : null
        token: row.analysis ? row.analysis.descent : ""
        width: row.fieldWidth

        onSelected: token => row.analysis.descent = token
    }
    ValueField {
        accepts: "integer"
        // The declared bound, or the fit's own when none is declared: the value the fit uses, as the
        // tolerance beside it (edi ADR-0017 §5).
        fieldValue: !row.analysis ? "" : row.analysis.hasMaxIterations ? row.analysis.maxIterations : row.analysis.defaultMaxIterations
        label: qsTr("max iterations")
        objectName: "minimizer.maxIterations"
        width: row.fieldWidth

        onCommitted: text => row.analysis.maxIterations = Number(text)
    }
    ValueField {
        accepts: "number"
        // The declared tolerance, or crysta's default when none is declared: the value the fit uses.
        fieldValue: !row.analysis ? "" : row.analysis.hasChiSquareTolerance ? row.analysis.chiSquareTolerance : row.analysis.defaultChiSquareTolerance
        label: qsTr("tolerance")
        objectName: "minimizer.chiSquareTolerance"
        width: row.fieldWidth

        onCommitted: text => row.analysis.chiSquareTolerance = Number(text)
    }
}
