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

    property AnalysisViewModel analysis: null
    readonly property AliasListModel aliases: analysis ? analysis.aliases : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table
        objectName: "aliases.list"
        defaultInfoText: qsTr("No aliases")
        sourceModel: group.aliases

        columnWidths: [numberColumnWidth, EaStyle.Sizes.fontPixelSize * 7, -1, AppSizes.iconColumnWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
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
                horizontalAlignment: Text.AlignHCenter
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
            TextCell {
                objectName: `alias.id.${row.index}`
                horizontalAlignment: Text.AlignLeft
                value: row.model.id
                onCommitted: text => group.aliases.setText(row.index, "id", text)
            }
            // The base's table combo box (TableViewComboBox), searchable: a project has many parameters.
            SearchableComboBox {
                horizontalAlignment: Text.AlignLeft
                objectName: `alias.parameter.${row.index}`
                anchors.verticalCenter: parent.verticalCenter
                borderColor: "transparent"
                backgroundColor: "transparent"
                model: group.aliases ? group.aliases.parameterNames : []
                currentIndex: group.aliases ? group.aliases.parameterNames.indexOf(row.model.parameter) : -1
                displayText: row.model.parameter
                ToolTip.text: row.model.parameter
                onActivated: index => group.aliases.setText(row.index, "parameter", group.aliases.parameterNames[index])
            }
            EaComponents.TableViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `alias.remove.${row.index}`
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this alias")
                onClicked: group.aliases.remove(row.index)
            }
        }
    }

    Row {
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            objectName: "aliases.append"
            fontIcon: "plus-circle"
            text: qsTr("Append new alias")
            onClicked: group.aliases.append()
        }
        EaElements.SideBarButton {
            objectName: "aliases.duplicate"
            enabled: table.currentIndex >= 0 || (group.aliases && group.aliases.count > 0)
            fontIcon: "clone"
            text: qsTr("Duplicate selected alias")
            onClicked: group.aliases.duplicate(Math.max(table.currentIndex, 0))
        }
    }
}
