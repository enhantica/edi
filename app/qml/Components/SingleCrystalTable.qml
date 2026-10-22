// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A single crystal's reflections under its chart: the Miller indices, the measured F² and its su, the
// calculated F² and the normalised residual (F²meas - F²calc) / su, with the app's one rule for numbers.
DataTable {
    id: table

    property ExperimentViewModel experiment: null

    function shown(value) {
        return value === undefined || isNaN(value) ? "" : NumberText.plain(value, 10);
    }

    objectName: "singleCrystal.reflections"
    defaultInfoText: qsTr("No reflections")
    sourceModel: experiment ? experiment.singleCrystalReflections : null

    columnWidths: [numberColumnWidth, -1, -1, -1, -1, -1, -1, -1]

    header: EaComponents.ListViewHeader {
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: "h"
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: "k"
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: "l"
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("F² meas")
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("s.u.")
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("F² calc")
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("(meas − calc)/s.u.")
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
            text: row.model.h
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: row.model.k
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: row.model.l
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.shown(row.model.intensityMeas)
            full: NumberText.plainFull(row.model.intensityMeas)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.shown(row.model.intensityMeasSu)
            full: NumberText.plainFull(row.model.intensityMeasSu)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.shown(row.model.intensityCalc)
            full: NumberText.plainFull(row.model.intensityCalc)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.shown(row.model.residual)
            full: NumberText.plainFull(row.model.residual)
        }
    }
}
