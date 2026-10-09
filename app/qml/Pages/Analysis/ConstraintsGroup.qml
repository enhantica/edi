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

    property AnalysisViewModel analysis: null
    readonly property ConstraintListModel constraints: analysis ? analysis.constraints : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table

        columnWidths: [numberColumnWidth, EaStyle.Sizes.fontPixelSize * 7, -1, AppSizes.iconColumnWidth, AppSizes.iconColumnWidth]
        defaultInfoText: qsTr("No constraints")
        model: group.constraints
        objectName: "constraints.list"

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property int index
            // The roles by the model: `id` cannot be a property name.
            required property var model

            EaComponents.TableViewLabel {
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                color: row.model.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundMinor
                // A disabled constraint's id and expression cells are both disabled.
                enabled: row.model.enabled
                horizontalAlignment: Text.AlignLeft
                objectName: `constraint.id.${row.index}`
                value: row.model.id

                onCommitted: text => group.constraints.setText(row.index, "id", text)
            }
            TextCell {
                color: row.model.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundMinor
                enabled: row.model.enabled
                horizontalAlignment: Text.AlignLeft
                objectName: `constraint.expression.${row.index}`
                value: row.model.expression

                onCommitted: text => group.constraints.setText(row.index, "expression", text)
            }
            EaComponents.TableViewButton {
                ToolTip.text: row.model.enabled ? qsTr("Disable this constraint") : qsTr("Enable this constraint")
                fontIcon: row.model.enabled ? "toggle-on" : "toggle-off"
                objectName: `constraint.enabled.${row.index}`

                onClicked: group.constraints.setEnabled(row.index, !row.model.enabled)
            }
            EaComponents.TableViewButton {
                ToolTip.text: qsTr("Remove this constraint")
                fontIcon: "minus-circle"
                objectName: `constraint.remove.${row.index}`

                onClicked: group.constraints.remove(row.index)
            }
        }
        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("id")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("expression")
            }
            EaComponents.TableViewLabel {
            }
            EaComponents.TableViewLabel {
            }
        }
    }
    Row {
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            fontIcon: "plus-circle"
            objectName: "constraints.append"
            text: qsTr("Append new constraint")

            onClicked: group.constraints.append()
        }
        EaElements.SideBarButton {
            enabled: table.currentIndex >= 0 || (group.constraints && group.constraints.count > 0)
            fontIcon: "clone"
            objectName: "constraints.duplicate"
            text: qsTr("Duplicate selected constraint")

            onClicked: group.constraints.duplicate(Math.max(table.currentIndex, 0))
        }
    }
}
