// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `fit_parameter`: the persisted pre-fit start state — each fitted parameter's value and uncertainty
// before the last fit, which undo restores — read-only (a fit writes it). A loop in `.edi`, so a
// table.
DataTable {
    id: table

    property AnalysisViewModel analysis: null

    // A start value by the app's one rule for numbers in cells (NumberText); the model keeps it whole.
    function shown(value) {
        return value === undefined ? "" : NumberText.plain(value, 8);
    }

    objectName: "fitStart.list"
    defaultInfoText: qsTr("No fit start state")
    model: analysis ? analysis.fitStart : null

    columnWidths: [numberColumnWidth, textColumnWidth("id", qsTr("parameter")), -1, -1]

    header: EaComponents.ListViewHeader {
        EaComponents.TableViewLabel {}
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignLeft
            text: qsTr("parameter")
        }
        EaComponents.TableViewLabel {
            text: qsTr("start value")
        }
        EaComponents.TableViewLabel {
            text: qsTr("start error")
        }
    }

    delegate: EaComponents.ListViewDelegate {
        id: row

        required property int index
        // The roles by the model: `id` cannot be a property name.
        required property var model

        EaComponents.TableViewLabel {
            color: EaStyle.Colors.themeForegroundMinor
            text: row.index + 1
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideMiddle
            text: row.model.id
            ToolTip.text: row.model.id
        }
        EaComponents.TableViewLabel {
            text: table.shown(row.model.startValue)
        }
        EaComponents.TableViewLabel {
            text: table.shown(row.model.startUncertainty)
        }
    }
}
