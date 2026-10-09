// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `refln`: the reflections the loaded file carries — written by the calculation that saved it
// (diffraction-lib); edi does not model reflections, so they are shown read-only, as read, and a save
// does not write them ("loop in .edi — table in gui"): Miller indices, d-spacing, position and F²calc,
// with the same numeric-column sizing as the measured-data table (ADR-0028).
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
    model: experiment ? experiment.reflections : null

    columnWidths: [numberColumnWidth, -1, -1, -1, -1]

    header: EaComponents.ListViewHeader {
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("id")
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("h k l")
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("d (Å)")
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: table.timeOfFlight ? qsTr("TOF (µs)") : qsTr("2θ (°)")
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("F² calc")
        }
    }

    delegate: EaComponents.ListViewDelegate {
        id: row

        required property int index
        required property var model

        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            color: EaStyle.Colors.themeForegroundMinor
            text: row.index + 1
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: row.model.hkl
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: table.shown(row.model.dSpacing)
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: table.shown(row.model.position)
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: table.shown(row.model.fSquaredCalc)
        }
    }
}
