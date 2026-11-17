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

    objectName: "relations.aliases"
    property AnalysisViewModel analysis: null
    // For each offered parameter's coloured name (ParameterNames.pickerLine).
    property ProjectViewModel project: null
    readonly property AliasListModel aliases: analysis ? analysis.aliases : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table
        objectName: "aliases.list"
        defaultInfoText: qsTr("No aliases")
        sourceModel: group.aliases

        columns: [numberColumnWidth, -1, -1, AppSizes.iconColumnWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "alias.id"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "alias.parameter_unique_name"
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
                editMember: row
                editModel: group.aliases
                editIndex: row.index
                objectName: `alias.id.${row.index}`
                horizontalAlignment: Text.AlignLeft
                value: row.model.id
                onCommitted: text => group.aliases.setText(row.index, "id", text)
            }
            // The base's table combo box (TableViewComboBox), searchable: a project has many parameters. Each entry is the
            // parameter table's coloured name and the full name, and a search finds either (the owner, 2026-11-17).
            // The whole Parameter column, and a list as wide as its widest entry with its icons, within the window (the
            // owner, 2026-11-17).
            ComboCell {
                fills: true

                SearchableComboBox {
                    id: parameterBox

                    function itemOf(name) {
                        return group.project ? group.project.parameterNamed(name) : null;
                    }
                    readonly property var names: group.aliases ? group.aliases.parameterNames : []

                    inTable: true
                    horizontalAlignment: Text.AlignLeft
                    objectName: `alias.parameter.${row.index}`
                    anchors.verticalCenter: parent.verticalCenter
                    // Each entry as the search reads it, so the list is measured on what it shows.
                    model: parameterBox.names.map(name => ParameterNames.pickerText(parameterBox.itemOf(name), name))
                    popup.width: Math.min(Math.max(parameterBox.width, parameterBox.optionWidth + EaStyle.Sizes.fontPixelSize * 4), parameterBox.Window.width - popup.leftMargin - popup.rightMargin)
                    currentIndex: parameterBox.names.indexOf(row.model.parameter)
                    displayText: row.model.parameter
                    ToolTip.text: row.model.parameter
                    onActivated: index => group.aliases.setText(row.index, "parameter", parameterBox.names[index])

                    contentItem: Item {
                        clip: true

                        IconLine {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width
                            maximumWidth: Math.max(1, parent.width)
                            segments: ParameterNames.pickerLine(parameterBox.itemOf(row.model.parameter), row.model.parameter)
                        }
                    }
                    delegate: EaElements.MenuItem {
                        id: entry

                        required property int index
                        required property var modelData
                        readonly property string name: parameterBox.names[entry.index] ?? ""
                        readonly property var item: parameterBox.itemOf(entry.name)
                        readonly property bool matching: parameterBox.matches(text)

                        width: entry.parent !== null ? entry.parent.width : 0
                        height: matching ? EaStyle.Sizes.comboBoxHeight : 0
                        opacity: matching ? 1 : 0
                        topPadding: 0
                        bottomPadding: 0
                        highlighted: parameterBox.highlightedIndex === entry.index
                        hoverEnabled: parameterBox.hoverEnabled
                        // What the search reads: both names.
                        text: entry.modelData

                        contentItem: Item {
                            clip: true

                            IconLine {
                                anchors.verticalCenter: parent.verticalCenter
                                maximumWidth: Math.max(1, parent.width)
                                segments: ParameterNames.pickerLine(entry.item, entry.name)
                            }
                        }
                    }
                }
            }
            EaComponents.ListViewButton {
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
            enabled: group.aliases !== null && group.aliases.parameterNames.length > 0
            ToolTip.text: enabled ? qsTr("Append an alias for an offered parameter") : qsTr("No parameter is available for an alias")
            fontIcon: "plus-circle"
            text: qsTr("Append new alias")
            onClicked: group.aliases.append()
        }
        EaElements.SideBarButton {
            objectName: "aliases.duplicate"
            enabled: table.currentIndex >= 0 || (group.aliases && group.aliases.count > 0)
            fontIcon: "clone"
            text: qsTr("Duplicate selected alias")
            ToolTip.text: enabled ? "" : qsTr("Nothing to duplicate: add an alias first")
            onClicked: group.aliases.duplicate(Math.max(table.currentIndex, 0))
        }
    }
}
