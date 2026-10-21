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

    // A reflection's values by the app's one rule for numbers (NumberText).
    function shown(value) {
        return value === undefined || isNaN(value) ? "" : NumberText.plain(value, 10);
    }

    objectName: "reflections.list"
    defaultInfoText: qsTr("No reflections")
    sourceModel: experiment ? experiment.reflections : null

    columnWidths: [numberColumnWidth, -1, -1, -1, -1]

    header: EaComponents.ListViewHeader {
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("h k l")
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("d (Å)")
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: table.timeOfFlight ? qsTr("TOF (µs)") : qsTr("2θ (deg)")
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("F² calc")
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
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: table.shown(row.model.dSpacing)
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: table.shown(row.model.position)
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: table.shown(row.model.fSquaredCalc)
        }
    }
}
