// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `alias`: the short names constraints use, each with the parameter it stands for, chosen from the
// project's refinable parameters; append, duplicate and remove as the atom sites do. A loop in `.edi`, so a
// table.
Column {
    id: group

    readonly property AliasListModel aliases: analysis ? analysis.aliases : null
    property AnalysisViewModel analysis: null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table

        columnWidths: [numberColumnWidth, EaStyle.Sizes.fontPixelSize * 7, -1, AppSizes.iconColumnWidth]
        defaultInfoText: qsTr("No aliases")
        model: group.aliases
        objectName: "aliases.list"

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
                horizontalAlignment: Text.AlignLeft
                objectName: `alias.id.${row.index}`
                value: row.model.id

                onCommitted: text => group.aliases.setText(row.index, "id", text)
            }
            // The base's table combo box (TableViewComboBox), searchable: a project has many parameters.
            SearchableComboBox {
                ToolTip.text: row.model.parameter
                anchors.verticalCenter: parent.verticalCenter
                backgroundColor: "transparent"
                borderColor: "transparent"
                currentIndex: group.aliases ? group.aliases.parameterNames.indexOf(row.model.parameter) : -1
                displayText: row.model.parameter
                model: group.aliases ? group.aliases.parameterNames : []
                objectName: `alias.parameter.${row.index}`

                onActivated: index => group.aliases.setText(row.index, "parameter", group.aliases.parameterNames[index])
            }
            EaComponents.TableViewButton {
                ToolTip.text: qsTr("Remove this alias")
                fontIcon: "minus-circle"
                objectName: `alias.remove.${row.index}`

                onClicked: group.aliases.remove(row.index)
            }
        }
        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("alias")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("parameter")
            }
            EaComponents.TableViewLabel {
            }
        }
    }
    Row {
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            fontIcon: "plus-circle"
            objectName: "aliases.append"
            text: qsTr("Append new alias")

            onClicked: group.aliases.append()
        }
        EaElements.SideBarButton {
            enabled: table.currentIndex >= 0 || (group.aliases && group.aliases.count > 0)
            fontIcon: "clone"
            objectName: "aliases.duplicate"
            text: qsTr("Duplicate selected alias")

            onClicked: group.aliases.duplicate(Math.max(table.currentIndex, 0))
        }
    }
}
