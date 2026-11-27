// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `sequential_fit_extract`: the scan's extraction rules, each a pattern read from a scan file into a results column,
// editable as text. Required or not, then remove, at the row's end; append and duplicate below, as the constraints. A
// pattern that cannot be read, or a target another column has, is refused in its cell. A loop in `.edi`, so a table.
Column {
    id: group

    property AnalysisViewModel analysis: null
    readonly property SequentialExtractListModel rules: analysis ? analysis.sequentialExtract : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table
        objectName: "sequentialExtract.list"
        defaultInfoText: qsTr("No extraction rules")
        sourceModel: group.rules

        // Its columns by kind (the shared column model, DataTable.columnKinds; ADR-0103 decision 4).
        columnKinds: ["index", "name", "name", "name", "control", "control"]
        columnTexts: ["",
            {
                "role": "id",
                "edited": true
            },
            {
                "role": "target",
                "edited": true
            },
            {
                "role": "pattern",
                "edited": true
            }
        ]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "sequential_fit_extract.id"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "sequential_fit_extract.target"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "sequential_fit_extract.pattern"
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

            // The roles by the model: `id` and `required` cannot be property names.
            required property var model

            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            TextCell {
                editMember: row
                editModel: group.rules
                editIndex: row.index
                objectName: `sequentialExtract.id.${row.index}`
                horizontalAlignment: Text.AlignLeft
                value: row.model.id
                onCommitted: text => group.rules.setText(row.index, "id", text)
            }
            TextCell {
                editMember: row
                editModel: group.rules
                editIndex: row.index
                objectName: `sequentialExtract.target.${row.index}`
                horizontalAlignment: Text.AlignLeft
                value: row.model.target
                onCommitted: text => group.rules.setText(row.index, "target", text)
            }
            TextCell {
                editMember: row
                editModel: group.rules
                editIndex: row.index
                objectName: `sequentialExtract.pattern.${row.index}`
                horizontalAlignment: Text.AlignLeft
                value: row.model.pattern
                onCommitted: text => group.rules.setText(row.index, "pattern", text)
            }
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `sequentialExtract.required.${row.index}`
                fontIcon: row.model.required ? "toggle-on" : "toggle-off"
                ToolTip.text: row.model.required ? qsTr("Required: a dataset whose file has no match for this pattern fails") : qsTr("Not required: a dataset whose file has no match leaves this column empty")
                onClicked: group.rules.setRequired(row.index, !row.model.required)
            }
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `sequentialExtract.remove.${row.index}`
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this rule")
                onClicked: group.rules.remove(row.index)
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
            text: qsTr("Duplicate selected rule")
        }

        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            id: appendButton
            objectName: "sequentialExtract.append"
            fontIcon: "plus-circle"
            text: buttons.wholeLabels ? qsTr("Append new rule") : qsTr("Append")
            onClicked: group.rules.append()
        }
        EaElements.SideBarButton {
            objectName: "sequentialExtract.duplicate"
            enabled: table.currentIndex >= 0 || (group.rules && group.rules.count > 0)
            fontIcon: "clone"
            text: buttons.wholeLabels ? qsTr("Duplicate selected rule") : qsTr("Duplicate")
            ToolTip.text: enabled ? "" : qsTr("Nothing to duplicate: add a rule first")
            onClicked: group.rules.duplicate(Math.max(table.currentIndex, 0))
        }
    }
}
