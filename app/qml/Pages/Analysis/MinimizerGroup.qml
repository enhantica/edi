// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// `minimizer` (easydiffractionbeta's Minimization engine): the engine — crysta, the one edi supports —
// the descent flow over crysta's registry, the declared iteration bound, the stop rule with the value the fit uses
// (declared, or crysta's default), and for a magnetic structure whether moments are tried at exactly zero. Rows of
// two (the owner, 2026-10-06), so the descent list is wide enough for its names, and the stop rule's value beside its
// selector (the owner, 2026-11-04); spaced as ParameterGrid spaces the instrument's fields.
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
        uid: "minimizer.type"
        options: row.analysis ? row.analysis.minimizerTypeOptions : null
        token: row.analysis ? row.analysis.minimizerType : ""
    }
    SelectorField {
        objectName: "minimizer.descent"
        width: row.fieldWidth
        uid: "minimizer.descent"
        options: row.analysis ? row.analysis.descentOptions : null
        token: row.analysis ? row.analysis.descent : ""
        onSelected: token => row.analysis.descent = token
    }
    // What ends a fit as converged: the χ² change, Shift/s.u. (FullProf's criterion), or either; a project that
    // declares none takes both.
    SelectorField {
        objectName: "minimizer.stopRule"
        width: row.fieldWidth
        uid: "minimizer.stop_rules"
        options: row.analysis ? row.analysis.stopRuleOptions : null
        token: row.analysis ? row.analysis.stopRule : ""
        onSelected: token => row.analysis.stopRule = token
    }
    // Each selected rule's value beside the selector: the declared value, or crysta's default when none is declared.
    ValueField {
        objectName: "minimizer.chiSquareTolerance"
        visible: row.analysis !== null && row.analysis.stopRule.indexOf("chi_square_change") >= 0
        width: row.fieldWidth
        uid: "minimizer.chi_square_tolerance"
        fieldValue: !row.analysis ? "" : row.analysis.hasChiSquareTolerance ? row.analysis.chiSquareTolerance : row.analysis.defaultChiSquareTolerance
        accepts: "number"
        onCommitted: text => row.analysis.chiSquareTolerance = Number(text)
    }
    ValueField {
        objectName: "minimizer.shiftTolerance"
        visible: row.analysis !== null && row.analysis.stopRule.indexOf("shift_su") >= 0
        width: row.fieldWidth
        uid: "minimizer.shift_tolerance"
        fieldValue: !row.analysis ? "" : row.analysis.hasShiftTolerance ? row.analysis.shiftTolerance : row.analysis.defaultShiftTolerance
        accepts: "number"
        onCommitted: text => row.analysis.shiftTolerance = Number(text)
    }
    ValueField {
        objectName: "minimizer.maxIterations"
        width: row.fieldWidth
        uid: "minimizer.max_iterations"
        // The declared bound, or the fit's own when none is declared: the value the fit uses, as the
        // tolerance above it (edi ADR-0017 §5).
        fieldValue: !row.analysis ? "" : row.analysis.hasMaxIterations ? row.analysis.maxIterations : row.analysis.defaultMaxIterations
        accepts: "integer"
        onCommitted: text => row.analysis.maxIterations = Number(text)
    }
    // Whether a fit tries free magnetic moments at exactly zero (the owner, 2026-11-04): shown only for a magnetic
    // structure, the only one it applies to.
    SelectorField {
        objectName: "minimizer.momentsNearZero"
        visible: row.analysis !== null && row.analysis.magnetic
        width: row.fieldWidth
        uid: "minimizer.moments_near_zero"
        options: row.analysis ? row.analysis.momentsNearZeroOptions : null
        token: row.analysis ? row.analysis.momentsNearZero : ""
        onSelected: token => row.analysis.momentsNearZero = token
    }
}
