// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `refln`: the reflections the loaded file carries — written by the calculation that saved it
// (diffraction-lib); edi does not model reflections, so they are shown read-only, as read, and a save
// does not write them ("loop in .edi — table in gui"): Miller indices, d-spacing, position and F²calc,
// with the same numeric-column sizing as the measured-data table (ADR-0029).
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
    defaultInfoText: qsTr("No reflections")
    sourceModel: experiment ? experiment.reflections : null

    columns: [numberColumnWidth, -1, -1, -1, -1]

    header: EaComponents.ListViewHeader {
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("h k l")
        }
        HeaderLabel {
            uid: "refln.d_spacing"
            withUnits: true
        }
        HeaderLabel {
            uid: table.positionItem
            withUnits: true
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignHCenter
            uid: "refln.f_squared_calc"
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
            text: row.model.hkl
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.shown("refln.d_spacing", row.model.dSpacing)
            full: NumberText.plainFull(row.model.dSpacing)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.shown(table.positionItem, row.model.position)
            full: NumberText.plainFull(row.model.position)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.shown("refln.f_squared_calc", row.model.fSquaredCalc)
            full: NumberText.plainFull(row.model.fSquaredCalc)
        }
    }
}
