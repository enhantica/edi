// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Which of a single crystal's reflections the fit uses: how equivalents are merged and whether systematic absences
// are left out, each blank until set (none and include by default), then the counts and agreement crysta's admission
// gives (Rint over merged groups of two or more, shown as n/a when undefined).
Column {
    id: row

    property ExperimentViewModel experiment: null
    readonly property var admission: experiment ? experiment.reflectionAdmission : null
    readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - grid.columnSpacing) / 2

    function ratio(value) {
        return isNaN(value) ? qsTr("n/a") : Number(value).toFixed(3);
    }

    spacing: AppSizes.groupContentSpacing

    Grid {
        id: grid

        columns: 2
        columnSpacing: AppSizes.inputSpacing
        rowSpacing: AppSizes.groupContentSpacing

        SelectorField {
            objectName: "reflns.merge"
            width: row.fieldWidth
            uid: "reflns.merge"
            enabled: row.experiment !== null && row.experiment.beamMode !== ExperimentViewModel.TimeOfFlight
            options: row.experiment ? row.experiment.reflnsMergeOptions : null
            token: row.experiment ? (row.experiment.reflnsMerge || "none") : ""
            onSelected: token => row.experiment.reflnsMerge = token
        }
        SelectorField {
            objectName: "reflns.absences"
            width: row.fieldWidth
            uid: "reflns.absences"
            options: row.experiment ? row.experiment.reflnsAbsencesOptions : null
            token: row.experiment ? (row.experiment.reflnsAbsences || "include") : ""
            onSelected: token => row.experiment.reflnsAbsences = token
        }
    }
    EaElements.Label {
        objectName: "reflns.admissionSummary"
        visible: row.admission !== null && row.admission.available
        width: EaStyle.Sizes.sideBarContentWidth
        wrapMode: Text.WordWrap
        text: row.admission === null ? "" : qsTr("Measured %1, unique %2, used %3, excluded %4, absent %5; Rint %6, R-sigma %7").arg(row.admission.measured).arg(row.admission.unique).arg(row.admission.used).arg(row.admission.excluded).arg(row.admission.absent).arg(row.ratio(row.admission.rInt)).arg(row.ratio(row.admission.rSigma))
    }
    EaElements.Label {
        objectName: "reflns.absencesWarning"
        visible: row.admission !== null && row.admission.absent > 0 && row.admission.absentMeanIOverSigma > 3
        width: EaStyle.Sizes.sideBarContentWidth
        wrapMode: Text.WordWrap
        color: EaStyle.Colors.red
        text: row.admission === null ? "" : qsTr("Systematic absences: %1 with mean I/su %2; the space group may be wrong").arg(row.admission.absent).arg(Number(row.admission.absentMeanIOverSigma).toFixed(1))
    }
}
