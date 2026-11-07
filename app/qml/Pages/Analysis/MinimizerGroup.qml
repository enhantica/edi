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
    // What ends a fit as converged (the owner, 2026-11-04): the χ² change, the rule of a project that declares
    // none, or Shift/s.u., FullProf's criterion.
    SelectorField {
        objectName: "minimizer.stopRule"
        width: row.fieldWidth
        uid: "minimizer.stop_rule"
        options: row.analysis ? row.analysis.stopRuleOptions : null
        token: row.analysis ? row.analysis.stopRule : ""
        onSelected: token => row.analysis.stopRule = token
    }
    // The stop rule's value beside its selector (the owner, 2026-11-04): the χ² change's tolerance or the Shift/s.u.
    // value, whichever rule is chosen.
    ValueField {
        readonly property bool shift: row.analysis !== null && row.analysis.stopRule === "shift_su"

        objectName: "minimizer.chiSquareTolerance"
        width: row.fieldWidth
        uid: shift ? "minimizer.shift_tolerance" : "minimizer.chi_square_tolerance"
        // The declared value of the chosen rule, or crysta's default when none is declared: the value the fit uses.
        fieldValue: !row.analysis ? "" : shift ? (row.analysis.hasShiftTolerance ? row.analysis.shiftTolerance : row.analysis.defaultShiftTolerance)
                                                : (row.analysis.hasChiSquareTolerance ? row.analysis.chiSquareTolerance : row.analysis.defaultChiSquareTolerance)
        accepts: "number"
        onCommitted: text => {
            if (shift)
                row.analysis.shiftTolerance = Number(text);
            else
                row.analysis.chiSquareTolerance = Number(text);
        }
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
