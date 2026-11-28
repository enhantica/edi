// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `refln`: the reflections the loaded file carries — written by the calculation that saved it
// (diffraction-lib); edi does not model reflections, so they are shown read-only, as read, and a save
// does not write them ("loop in .edi — table in gui"): Miller indices, d-spacing, position and F²calc,
// with the same numeric-column sizing as the measured-data table (ADR-0029). A magnetic structure's reflections show
// |M⊥|² and their total F² + |M⊥|², as the calculation gives them, beside F²calc, so a purely magnetic reflection
// (F²calc 0) shows its intensity (edi ADR-0078); they are the last columns, hidden for a structure without moments.
// A Le Bail or Pawley structure's rows have no calculated F²: they show the F² extracted from the pattern and, for
// Pawley, its s.u., in columns after those (edi ADR-0109). A table of such rows alone shows neither F² calc nor the
// magnetic columns.
DataTable {
    id: table

    property ExperimentViewModel experiment: null
    readonly property bool timeOfFlight: experiment !== null && experiment.beamMode === ExperimentViewModel.TimeOfFlight

    // A reflection's position on the experiment's axis.
    readonly property string positionItem: timeOfFlight ? "refln.time_of_flight" : "refln.two_theta"

    // A reflection's values, each in its item's display format.
    function shown(uid, value) {
        return ApplicationInfo.formShownValue(uid, value, true);
    }

    objectName: "reflections.list"
    readOnly: true
    defaultInfoText: qsTr("No reflections yet")
    sourceModel: experiment ? experiment.reflections : null

    readonly property ReflectionListModel reflections: experiment ? experiment.reflections : null
    readonly property bool extracted: reflections !== null && reflections.extracted
    readonly property bool extractedSu: reflections !== null && reflections.extractedSu
    // Some row has F² calc: every table without extracted rows, and one mixing them with a Rietveld structure's.
    readonly property bool calculated: !extracted || (reflections !== null && reflections.calculated)
    readonly property bool magnetic: calculated && reflections !== null && reflections.magnetic

    // Its columns by kind (the shared column model, DataTable.columnKinds; ADR-0103 decision 4). With extracted rows
    // the columns of F² calc and |M⊥|² stay in place, without width where no row has them (a hidden middle column
    // left the header a cell short of its rows).
    columnKinds: !extracted ? (magnetic ? ["index", "text", "number", "number", "number", "number", "number"] : ["index", "text", "number", "number", "number"]) : ["index", "text", "number", "number", calculated ? "number" : 0.001, magnetic ? "number" : 0.001, magnetic ? "number" : 0.001, "number"].concat(extractedSu ? ["number"] : [])
    columnTexts: ["", "hkl"]
    // Widths from column types, not rows (ADR-0103 rule 4): the Miller indices a short column (three small integers),
    // then values; a text column made them half the table (the owner, 2026-11-21).
    // The values share the spare width, so the table spans its panel evenly rather than one last column taking it all.

    // Aligned as the column model aligns them: the Miller indices at the left, the numbers at the right (the
    // owner's sweep, 2026-11-23: centred cells under right-aligned titles).
    header: EaComponents.ListViewHeader {
        EaComponents.ListViewLabel {
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
        }
        EaComponents.ListViewLabel {
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignLeft
            text: qsTr("h k l")
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignRight
            uid: "refln.d_spacing"
            withUnits: true
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignRight
            uid: table.positionItem
            withUnits: true
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignRight
            visible: table.calculated
            uid: "refln.f_squared_calc"
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignRight
            visible: table.magnetic
            uid: "refln.f_m_perp_squared_calc"
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignRight
            visible: table.magnetic
            uid: "refln.f_squared_total_calc"
            toolTipText: qsTr("F² + |F_M⊥|²: nuclear plus magnetic, unpolarised neutrons")
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignRight
            visible: table.extracted
            uid: "refln.f_squared_meas"
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignRight
            visible: table.extractedSu
            uid: "refln.f_squared_meas_su"
        }
    }

    delegate: TableRow {
        id: row

        required property var model

        EaComponents.ListViewLabel {
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
            marksCurrentRow: true
            text: row.index + 1
        }
        CellLabel {
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignLeft
            text: row.model.hkl
        }
        NumberLabel {
            horizontalAlignment: Text.AlignRight
            number: table.shown("refln.d_spacing", row.model.dSpacing)
            full: NumberText.plainFull(row.model.dSpacing)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignRight
            number: table.shown(table.positionItem, row.model.position)
            full: NumberText.plainFull(row.model.position)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignRight
            visible: table.calculated
            number: table.shown("refln.f_squared_calc", row.model.fSquaredCalc)
            full: NumberText.plainFull(row.model.fSquaredCalc)
        }
        NumberLabel {
            objectName: `reflection.fMPerpSquared.${row.index}`
            horizontalAlignment: Text.AlignRight
            visible: table.magnetic
            number: table.shown("refln.f_m_perp_squared_calc", row.model.fMPerpSquaredCalc)
            full: NumberText.plainFull(row.model.fMPerpSquaredCalc)
        }
        NumberLabel {
            objectName: `reflection.fSquaredTotal.${row.index}`
            horizontalAlignment: Text.AlignRight
            visible: table.magnetic
            number: table.shown("refln.f_squared_total_calc", row.model.fSquaredTotalCalc)
            full: NumberText.plainFull(row.model.fSquaredTotalCalc)
        }
        NumberLabel {
            objectName: `reflection.fSquaredMeas.${row.index}`
            horizontalAlignment: Text.AlignRight
            visible: table.extracted
            number: table.shown("refln.f_squared_meas", row.model.fSquaredMeas)
            full: NumberText.plainFull(row.model.fSquaredMeas)
        }
        NumberLabel {
            objectName: `reflection.fSquaredMeasSu.${row.index}`
            horizontalAlignment: Text.AlignRight
            visible: table.extractedSu
            number: table.shown("refln.f_squared_meas_su", row.model.fSquaredMeasSu)
            full: NumberText.plainFull(row.model.fSquaredMeasSu)
        }
    }
}
