// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `constraint`: each constraint as declared, `<alias> = <expression>`, editable as text; a disabled one
// stays in the project, is not applied, and shows its id and expression disabled. Enable or disable, then remove, at the row's end; append and
// duplicate below, as the aliases. A loop in `.edi`, so a table.
Column {
    id: group
    objectName: "relations.constraints"

    property AnalysisViewModel analysis: null
    readonly property ConstraintListModel constraints: analysis ? analysis.constraints : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table
        objectName: "constraints.list"
        defaultInfoText: qsTr("No constraints")
        sourceModel: group.constraints

        // Its columns by kind (the shared column model, DataTable.columnKinds; ADR-0103 decision 4).
        columnKinds: ["index", "name", "name", "control", "control"]
        columnTexts: ["",
            {
                "role": "id",
                "edited": true
            },
            {
                "role": "expression",
                "edited": true
            }
        ]
        // Widths from column types, not rows (ADR-0103 rule 4): the constrained parameter, then its expression.

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "constraint.id"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "constraint.expression"
            }
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: TableRow {
            id: row

            // The roles by the model: `id` cannot be a property name.
            required property var model

            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            TextCell {
                objectName: `constraint.id.${row.index}`
                horizontalAlignment: Text.AlignLeft
                // A disabled constraint's id and expression cells are both disabled.
                enabled: row.model.enabled
                color: row.model.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundMinor
                value: row.model.id
                onCommitted: text => group.constraints.setText(row.index, "id", text)
            }
            TextCell {
                objectName: `constraint.expression.${row.index}`
                horizontalAlignment: Text.AlignLeft
                enabled: row.model.enabled
                color: row.model.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundMinor
                value: row.model.expression
                onCommitted: text => group.constraints.setText(row.index, "expression", text)
            }
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `constraint.enabled.${row.index}`
                fontIcon: row.model.enabled ? "toggle-on" : "toggle-off"
                ToolTip.text: row.model.enabled ? qsTr("Disable this constraint") : qsTr("Enable this constraint")
                onClicked: group.constraints.setEnabled(row.index, !row.model.enabled)
            }
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `constraint.remove.${row.index}`
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this constraint")
                onClicked: group.constraints.remove(row.index)
            }
        }
    }

    Row {
        id: buttons

        // Whole labels where the longer fits beside its icon, else the short ones, the same on both buttons (no label
        // runs out of its button).
        readonly property bool wholeLabels: labelMetrics.advanceWidth + EaStyle.Sizes.fontPixelSize * 4 <= appendButton.width
        TextMetrics {
            id: labelMetrics
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
            text: qsTr("Duplicate selected constraint")
        }

        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            id: appendButton
            objectName: "constraints.append"
            fontIcon: "plus-circle"
            text: buttons.wholeLabels ? qsTr("Append new constraint") : qsTr("Append")
            onClicked: group.constraints.append()
        }
        EaElements.SideBarButton {
            objectName: "constraints.duplicate"
            enabled: table.currentIndex >= 0 || (group.constraints && group.constraints.count > 0)
            fontIcon: "clone"
            text: buttons.wholeLabels ? qsTr("Duplicate selected constraint") : qsTr("Duplicate")
            ToolTip.text: enabled ? "" : qsTr("Nothing to duplicate: add a constraint first")
            onClicked: group.constraints.duplicate(Math.max(table.currentIndex, 0))
        }
    }
}
