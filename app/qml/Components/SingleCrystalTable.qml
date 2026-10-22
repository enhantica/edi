// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `refln` of a single crystal, in the Extra tab: the Miller indices, d, sinθ/λ, the measured F² and its su,
// the calculated F² and the normalised residual (F²meas - F²calc) / su, with the app's one rule for numbers.
DataTable {
    id: table

    property ExperimentViewModel experiment: null

    function shown(value) {
        return value === undefined || isNaN(value) ? "" : NumberText.plain(value, 10);
    }
    // A column whose values share one scale, with a fixed number of decimals, so none is cut.
    function fixed(value, decimals) {
        return value === undefined || isNaN(value) ? "" : value.toFixed(decimals);
    }

    objectName: "singleCrystal.reflections"
    defaultInfoText: qsTr("No reflections")
    sourceModel: experiment ? experiment.singleCrystalReflections : null

    columnWidths: [numberColumnWidth, -1, -1, -1, -1, -1, -1, -1, -1, -1]

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
            number: table.shown(row.model.dSpacing)
            full: NumberText.plainFull(row.model.dSpacing)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.fixed(row.model.sinThetaOverLambda, 4)
            full: NumberText.plainFull(row.model.sinThetaOverLambda)
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
            number: table.fixed(row.model.residual, 2)
            full: NumberText.plainFull(row.model.residual)
        }
    }
}
