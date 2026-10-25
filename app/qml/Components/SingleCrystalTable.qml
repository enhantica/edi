// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `refln` of a single crystal, in the Extra tab: the Miller indices, d, sinθ/λ, the measured F² and its su,
// the calculated F² and the normalised residual (F²meas - F²calc) / su, with the app's one rule for numbers; in time of
// flight each reflection's wavelength; last, whether the fit uses the reflection (the fit's cutoff, F² > n su(F²), or
// every one without), as an icon with the reason in its tooltip, as the measured data's status column. A click on a
// column title sorts the rows by that column.
DataTable {
    id: table

    property ExperimentViewModel experiment: null
    readonly property bool timeOfFlight: experiment !== null && experiment.beamMode === ExperimentViewModel.TimeOfFlight
    // The height the table may take: its own and the room the sidebar leaves under it. Its rows fill it, with half
    // a row as a scroll cue; without it the table keeps the default number of rows.
    property real spareHeight: 0

    // A column title that sorts the rows by its column on a click, again in reverse on a second, and marks the
    // sorted column with its direction.
    component SortTitle: EaComponents.ListViewLabel {
        id: title

        required property string role
        property string label

        objectName: "singleCrystal.reflections.sort." + role
        horizontalAlignment: Text.AlignHCenter
        // The header lays a mouse area over its row of titles, which would take the click: the row goes above it.
        Component.onCompleted: {
            if (parent)
                parent.z = 1;
        }
        text: label + (table.sourceModel && table.sourceModel.sortRole === role ? (table.sourceModel.sortAscending ? " ˄" : " ˅") : "")

        TapHandler {
            onTapped: {
                if (table.sourceModel)
                    table.sourceModel.sortBy(title.role);
            }
        }
    }

    // Each column with a fixed number of decimals, so no value is cut: d and sinθ/λ to 4, F² and its su to 3.
    function fixed(value, decimals) {
        return value === undefined || isNaN(value) ? "" : value.toFixed(decimals);
    }

    objectName: "singleCrystal.reflections"
    maxRowCountShow: spareHeight > 0 ? Math.max(5, Math.floor((spareHeight - (headerItem ? headerItem.height : 0) - AppSizes.groupContentSpacing) / tableRowHeight - 0.5)) : EaStyle.Sizes.tableMaxRowCountShow
    defaultInfoText: qsTr("No reflections")
    sourceModel: experiment ? experiment.singleCrystalReflections : null

    // The Miller indices are short integers, so their columns are narrow and the numbers keep their room.
    readonly property real indexColumnWidth: EaStyle.Sizes.fontPixelSize * 2.5
    columnWidths: [numberColumnWidth, indexColumnWidth, indexColumnWidth, indexColumnWidth, -1, -1, -1, -1, -1, -1].concat(timeOfFlight ? [-1] : []).concat([AppSizes.iconOnlyColumnWidth])

    header: EaComponents.ListViewHeader {
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
        }
        SortTitle {
            role: "h"
            label: "h"
        }
        SortTitle {
            role: "k"
            label: "k"
        }
        SortTitle {
            role: "l"
            label: "l"
        }
        SortTitle {
            role: "dSpacing"
            label: qsTr("d (Å)")
        }
        SortTitle {
            role: "sinThetaOverLambda"
            label: qsTr("sinθ/λ")
        }
        SortTitle {
            role: "intensityMeas"
            label: qsTr("F² meas")
        }
        SortTitle {
            role: "intensityMeasSu"
            label: qsTr("s.u.")
        }
        SortTitle {
            role: "intensityCalc"
            label: qsTr("F² calc")
        }
        SortTitle {
            role: "residual"
            label: qsTr("Δ / s.u.")
        }
        SortTitle {
            visible: table.timeOfFlight
            role: "wavelength"
            label: qsTr("λ (Å)")
        }
        SortTitle {
            role: "fitUse"
            label: qsTr("fit")
        }
    }

    delegate: TableRow {
        id: row

        required property var model

        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
            marksCurrentRow: true
            text: row.index + 1
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: row.model.h
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: row.model.k
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: row.model.l
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.fixed(row.model.dSpacing, 4)
            full: NumberText.plainFull(row.model.dSpacing)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.fixed(row.model.sinThetaOverLambda, 4)
            full: NumberText.plainFull(row.model.sinThetaOverLambda)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.fixed(row.model.intensityMeas, 3)
            full: NumberText.plainFull(row.model.intensityMeas)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.fixed(row.model.intensityMeasSu, 3)
            full: NumberText.plainFull(row.model.intensityMeasSu)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.fixed(row.model.intensityCalc, 3)
            full: NumberText.plainFull(row.model.intensityCalc)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.fixed(row.model.residual, 2)
            full: NumberText.plainFull(row.model.residual)
        }
        NumberLabel {
            visible: table.timeOfFlight
            horizontalAlignment: Text.AlignHCenter
            number: table.fixed(row.model.wavelength, 4)
            full: NumberText.plainFull(row.model.wavelength)
        }
        IconCell {
            readonly property bool used: row.model.fitUse === 1
            readonly property real cutoff: table.sourceModel ? table.sourceModel.fitCutoff : NaN

            horizontalAlignment: Text.AlignHCenter
            objectName: `singleCrystal.reflections.fitUse.${row.index}`
            icon: used ? FitOutcomes.icon("success") : "minus-circle"
            iconColor: String(used ? EaStyle.Colors.green : EaStyle.Colors.themeForegroundMinor)
            toolTip: used ? (isNaN(cutoff) ? qsTr("Used by the fit (no cutoff: every reflection)") : qsTr("Used by the fit: F² > %1 s.u.").arg(cutoff)) : qsTr("Left out of the fit: F² at most %1 s.u.").arg(cutoff)
        }
    }
}
