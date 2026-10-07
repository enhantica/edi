// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `refln`: the reflections the loaded file carries — written by the calculation that saved it
// (diffraction-lib); edi does not model reflections, so they are shown read-only, as read, and a save
// does not write them ("loop in .edi — table in gui"): Miller indices, d-spacing, position and F²calc,
// at six significant digits.
EaComponents.TableView {
    id: table

    property ExperimentViewModel experiment: null
    readonly property bool timeOfFlight: experiment !== null && experiment.beamMode === ExperimentViewModel.TimeOfFlight

    function shown(value) {
        return value === undefined || isNaN(value) ? "" : String(Number(value.toPrecision(6)));
    }

    objectName: "reflections.list"
    defaultInfoText: qsTr("No reflections")
    model: experiment ? experiment.reflections : null

    header: EaComponents.TableViewHeader {
        EaComponents.TableViewLabel {
            width: AppSizes.dataIndexColumnWidth
        }
        EaComponents.TableViewLabel {
            flexibleWidth: true
            text: qsTr("h k l")
        }
        EaComponents.TableViewLabel {
            width: AppSizes.dataColumnWidth
            text: qsTr("d (Å)")
        }
        EaComponents.TableViewLabel {
            width: AppSizes.dataColumnWidth
            text: table.timeOfFlight ? qsTr("TOF (µs)") : qsTr("2θ (°)")
        }
        EaComponents.TableViewLabel {
            width: AppSizes.dataColumnWidth
            text: qsTr("F² calc")
        }
    }

    delegate: EaComponents.TableViewDelegate {
        id: row

        required property int index
        required property var model

        EaComponents.TableViewLabel {
            width: AppSizes.dataIndexColumnWidth
            color: EaStyle.Colors.themeForegroundMinor
            text: row.index + 1
        }
        EaComponents.TableViewLabel {
            width: table.headerLabelItems.length > 1 ? table.headerLabelItems[1].width : 0
            text: row.model.hkl
        }
        EaComponents.TableViewLabel {
            width: AppSizes.dataColumnWidth
            text: table.shown(row.model.dSpacing)
        }
        EaComponents.TableViewLabel {
            width: AppSizes.dataColumnWidth
            text: table.shown(row.model.position)
        }
        EaComponents.TableViewLabel {
            width: AppSizes.dataColumnWidth
            text: table.shown(row.model.fSquaredCalc)
        }
    }
}
