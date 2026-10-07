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

    EaComponents.TableView {
        id: table
        objectName: "constraints.list"
        defaultInfoText: qsTr("No constraints")
        model: group.constraints

        header: EaComponents.TableViewHeader {
            EaComponents.TableViewLabel {
                width: AppSizes.indexColumnWidth
            }
            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 7
                horizontalAlignment: Text.AlignLeft
                text: qsTr("id")
            }
            EaComponents.TableViewLabel {
                flexibleWidth: true
                horizontalAlignment: Text.AlignLeft
                text: qsTr("expression")
            }
            EaComponents.TableViewLabel {
                width: AppSizes.iconColumnWidth
            }
            EaComponents.TableViewLabel {
                width: AppSizes.iconColumnWidth
            }
        }

        delegate: EaComponents.TableViewDelegate {
            id: row

            required property int index
            // The roles by the model: `id` cannot be a property name.
            required property var model

            EaComponents.TableViewLabel {
                width: AppSizes.indexColumnWidth
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                objectName: `constraint.id.${row.index}`
                width: EaStyle.Sizes.fontPixelSize * 7
                horizontalAlignment: Text.AlignLeft
                // A disabled constraint's id and expression cells are both disabled.
                enabled: row.model.enabled
                color: row.model.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundMinor
                value: row.model.id
                onCommitted: text => group.constraints.setText(row.index, "id", text)
            }
            TextCell {
                objectName: `constraint.expression.${row.index}`
                width: table.headerLabelItems.length > 2 ? table.headerLabelItems[2].width : 0
                horizontalAlignment: Text.AlignLeft
                enabled: row.model.enabled
                color: row.model.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundMinor
                value: row.model.expression
                onCommitted: text => group.constraints.setText(row.index, "expression", text)
            }
            EaComponents.TableViewButton {
                objectName: `constraint.enabled.${row.index}`
                fontIcon: row.model.enabled ? "toggle-on" : "toggle-off"
                ToolTip.text: row.model.enabled ? qsTr("Disable this constraint") : qsTr("Enable this constraint")
                onClicked: group.constraints.setEnabled(row.index, !row.model.enabled)
            }
            EaComponents.TableViewButton {
                objectName: `constraint.remove.${row.index}`
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this constraint")
                onClicked: group.constraints.remove(row.index)
            }
        }
    }

    Row {
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            objectName: "constraints.append"
            fontIcon: "plus-circle"
            text: qsTr("Append new constraint")
            onClicked: group.constraints.append()
        }
        EaElements.SideBarButton {
            objectName: "constraints.duplicate"
            enabled: table.currentIndex >= 0 || (group.constraints && group.constraints.count > 0)
            fontIcon: "clone"
            text: qsTr("Duplicate selected constraint")
            onClicked: group.constraints.duplicate(Math.max(table.currentIndex, 0))
        }
    }
}
