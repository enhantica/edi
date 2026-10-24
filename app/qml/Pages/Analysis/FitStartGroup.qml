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

    // A start value or error in its item's display format; the model keeps it whole.
    function shown(uid, value) {
        return value === undefined ? "" : Session.display(uid, value);
    }

    objectName: "fitStart.list"
    defaultInfoText: qsTr("No fit start state")
    sourceModel: analysis ? analysis.fitStart : null

    columnWidths: [numberColumnWidth, textColumnWidth("id", Session.label("fit_parameter.id")), -1, -1]

    header: EaComponents.ListViewHeader {
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignLeft
            uid: "fit_parameter.id"
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignHCenter
            uid: "fit_parameter.start_value"
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignHCenter
            uid: "fit_parameter.start_uncertainty"
        }
    }

    delegate: EaComponents.ListViewDelegate {
        id: row

        required property int index
        // The roles by the model: `id` cannot be a property name.
        required property var model

        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            color: EaStyle.Colors.themeForegroundMinor
            text: row.index + 1
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideMiddle
            text: row.model.id
            ToolTip.text: row.model.id
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.shown("fit_parameter.start_value", row.model.startValue)
            full: NumberText.plainFull(row.model.startValue)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignHCenter
            number: table.shown("fit_parameter.start_uncertainty", row.model.startUncertainty)
            full: NumberText.plainFull(row.model.startUncertainty)
        }
    }
}
