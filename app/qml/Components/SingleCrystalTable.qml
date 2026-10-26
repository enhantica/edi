// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
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
    // sorted column with its direction. A column of a `.edi` item is titled by the item's dictionary label and units
    // (edi ADR-0051), with the label and the `.edi` name as its tooltip, as HeaderLabel titles one.
    component SortTitle: EaComponents.ListViewLabel {
        id: title

        required property string role
        property string uid: ""
        readonly property string units: uid !== "" ? Session.units(uid) : ""
        property string label: uid === "" ? "" : units !== "" ? `${Session.label(uid)} (${units})` : Session.label(uid)

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
        EaElements.ToolTip {
            text: title.uid !== "" ? Session.tooltip(title.uid) : ""
            visible: title.uid !== "" && title.hovered && EaGlobals.Vars.showToolTips
        }
    }

    // A reflection's values, each in its item's display format (edi ADR-0051); the normalised residual, no item's
    // value, to two decimals.
    function shown(uid, value) {
        return value === undefined || isNaN(value) ? "" : Session.display(uid, value);
    }
    function residual(value) {
        return value === undefined || isNaN(value) ? "" : value.toFixed(2);
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
            uid: "refln.index_h"
        }
        SortTitle {
            role: "k"
            uid: "refln.index_k"
        }
        SortTitle {
            role: "l"
            uid: "refln.index_l"
        }
        SortTitle {
            role: "dSpacing"
            uid: "refln.d_spacing"
        }
        SortTitle {
            role: "sinThetaOverLambda"
            uid: "refln.sin_theta_over_lambda"
        }
        SortTitle {
            role: "intensityMeas"
            uid: "refln.intensity_meas"
        }
        SortTitle {
            role: "intensityMeasSu"
            uid: "refln.intensity_meas_su"
        }
        SortTitle {
            role: "intensityCalc"
            uid: "refln.intensity_calc"
        }
        SortTitle {
            role: "residual"
            label: qsTr("Δ / s.u.")
        }
        SortTitle {
            visible: table.timeOfFlight
            role: "wavelength"
            uid: "refln.wavelength"
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
            number: table.shown("refln.d_spacing", row.model.dSpacing)
            full: NumberText.plainFull(row.model.dSpacing)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.shown("refln.sin_theta_over_lambda", row.model.sinThetaOverLambda)
            full: NumberText.plainFull(row.model.sinThetaOverLambda)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.shown("refln.intensity_meas", row.model.intensityMeas)
            full: NumberText.plainFull(row.model.intensityMeas)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.shown("refln.intensity_meas_su", row.model.intensityMeasSu)
            full: NumberText.plainFull(row.model.intensityMeasSu)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.shown("refln.intensity_calc", row.model.intensityCalc)
            full: NumberText.plainFull(row.model.intensityCalc)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.residual(row.model.residual)
            full: NumberText.plainFull(row.model.residual)
        }
        NumberLabel {
            visible: table.timeOfFlight
            horizontalAlignment: Text.AlignHCenter
            number: table.shown("refln.wavelength", row.model.wavelength)
            full: NumberText.plainFull(row.model.wavelength)
        }
        IconCell {
            readonly property bool used: row.model.fitUse === 1
            readonly property real cutoff: table.sourceModel ? table.sourceModel.fitCutoff : NaN

            horizontalAlignment: Text.AlignHCenter
            objectName: `singleCrystal.reflections.fitUse.${row.index}`
            icon: used ? FitOutcomes.icon("success") : "minus-circle"
            iconColor: String(used ? EaStyle.Colors.green : EaStyle.Colors.themeForegroundMinor)
            toolTip: used ? (isNaN(cutoff) ? qsTr("Used by the fit (no cutoff: every reflection)") : qsTr("Used by the fit: F² > %1 s.u.").arg(Session.display("refine_ls.threshold_sigma", cutoff))) : qsTr("Left out of the fit: F² at most %1 s.u.").arg(Session.display("refine_ls.threshold_sigma", cutoff))
        }
    }
}
