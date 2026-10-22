// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `refln` of a single crystal, in the Extra tab: the Miller indices, d, sinθ/λ, the measured F² and its su,
// the calculated F² and the normalised residual (F²meas - F²calc) / su, with the app's one rule for numbers; in time of
// flight each reflection's wavelength last.
DataTable {
    id: table

    property ExperimentViewModel experiment: null
    readonly property bool timeOfFlight: experiment !== null && experiment.beamMode === ExperimentViewModel.TimeOfFlight
    // The height the table may take: its own and the room the sidebar leaves under it. Its rows fill it, with half
    // a row as a scroll cue; without it the table keeps the default number of rows.
    property real spareHeight: 0

    // Each column with a fixed number of decimals, so no value is cut: d and sinθ/λ to 4, F² and its su to 3.
    function fixed(value, decimals) {
        return value === undefined || isNaN(value) ? "" : value.toFixed(decimals);
    }

    objectName: "singleCrystal.reflections"
    maxRowCountShow: spareHeight > 0 ? Math.max(5, Math.floor((spareHeight - (headerItem ? headerItem.height : 0) - AppSizes.groupContentSpacing) / tableRowHeight - 0.5)) : EaStyle.Sizes.tableMaxRowCountShow
    defaultInfoText: qsTr("No reflections")
    sourceModel: experiment ? experiment.singleCrystalReflections : null

    columnWidths: timeOfFlight ? [numberColumnWidth, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1] : [numberColumnWidth, -1, -1, -1, -1, -1, -1, -1, -1, -1]

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
            text: qsTr("d (Å)")
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("sinθ/λ")
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
            text: qsTr("Δ / s.u.")
        }
        EaComponents.TableViewLabel {
            visible: table.timeOfFlight
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("λ (Å)")
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
    }
}
