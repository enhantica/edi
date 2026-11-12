// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `fit_parameter`: the persisted pre-fit start state — each fitted parameter's value and uncertainty
// before the last fit, which undo restores — read-only (a fit writes it). A loop in `.edi`, so a
// table, shown as a read-only one: grey text and no hover tint. Each parameter is named by icons as the Analysis
// parameter table names it, with its `.edi` id in a tooltip.
DataTable {
    id: table

    property AnalysisViewModel analysis: null

    // A start value or error in its item's display format; the model keeps it whole.
    function shown(uid, value) {
        return ApplicationInfo.formShownValue(uid, value, false);
    }

    objectName: "fitStart.list"
    defaultInfoText: qsTr("No fit start state")
    sourceModel: analysis ? analysis.fitStart : null

    columns: [numberColumnWidth, -1, -1, -1]

    header: EaComponents.ListViewHeader {
        EaComponents.ListViewLabel {
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignLeft
            uid: "fit_parameter.id"
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignRight
            uid: "fit_parameter.start_value"
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignRight
            uid: "fit_parameter.start_uncertainty"
        }
    }

    delegate: TableRow {
        id: row

        // The roles by the model: `id` cannot be a property name.
        required property var model
        // A row's parameter, null for a start row no current parameter has.
        readonly property ParameterItem parameter: row.model.parameter ?? null

        highlightsHover: false

        EaComponents.ListViewLabel {
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
            marksCurrentRow: true
            text: row.index + 1
        }
        Item {
            property int horizontalAlignment: Text.AlignLeft
            objectName: `fitStart.name.${row.index}`
            // As wide as its icons and text, which the table fits the column to; a narrower column ends the name
            // with an ellipsis, its full name in the tooltip.
            implicitWidth: nameLine.fullWidth
            height: parent.height
            clip: true

            IconLine {
                id: nameLine
                anchors.verticalCenter: parent.verticalCenter
                maximumWidth: Math.max(1, parent.width)
                minimumTextWidth: EaStyle.Sizes.fontPixelSize * 3
                textColor: EaStyle.Colors.themeForegroundMinor
                segments: row.parameter !== null ? ParameterNames.segments(row.parameter) : [
                    {
                        "text": row.model.id
                    }
                ]
            }
            HoverHandler {
                id: nameHover
            }
            EaElements.ToolTip {
                text: row.model.id
                requested: nameHover.hovered
            }
        }
        NumberLabel {
            horizontalAlignment: Text.AlignRight
            color: EaStyle.Colors.themeForegroundMinor
            number: table.shown("fit_parameter.start_value", row.model.startValue)
            full: NumberText.plainFull(row.model.startValue)
        }
        NumberLabel {
            horizontalAlignment: Text.AlignRight
            color: EaStyle.Colors.themeForegroundMinor
            number: table.shown("fit_parameter.start_uncertainty", row.model.startUncertainty)
            full: NumberText.plainFull(row.model.startUncertainty)
        }
    }
}
