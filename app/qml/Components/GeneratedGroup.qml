// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The group the app makes for a category no designed group shows (edi ADR-0017 §3): from the dictionary and the
// block's text, with the shared components, a loop as the shared table and single items as labelled fields.
// Output categories are shown, never edited; an input value's edit is the block's text with it, applied as the Text
// tab applies an edit.
Column {
    id: group

    // The block's text, read while the group is open, and the category.
    property BlockText source: null
    property string categoryId: ""
    // Why the last edit was refused.
    property string refusal: ""

    function apply(row: int, name: string, value: string) {
        group.refusal = Session.project ? Session.project.applyText(group.source.file, category.editedText(row, name, value)) : "";
    }

    spacing: AppSizes.groupContentSpacing
    width: EaStyle.Sizes.sideBarContentWidth

    GeneratedCategory {
        id: category
        source: group.source
        categoryId: group.categoryId
    }

    // Single items: labelled fields, up to four a row.
    Grid {
        id: fields

        visible: !category.loop
        columns: Math.min(4, Math.max(1, category.names.length))
        columnSpacing: AppSizes.inputSpacing
        rowSpacing: AppSizes.groupContentSpacing

        // Each item in the control its dictionary type asks for: a selector, a check box, or a field taking a number
        // or a text.
        Repeater {
            model: category.loop ? [] : category.names
            delegate: Loader {
                id: field

                required property int index
                required property string modelData
                readonly property string kind: category.kinds[index] ?? "text"
                readonly property string value: category.rowCount > 0 ? category.value(0, index) : ""
                readonly property bool editable: !category.output && !category.setByProgram.includes(modelData) && group.source !== null && group.source.file !== ""

                width: (EaStyle.Sizes.sideBarContentWidth - (fields.columns - 1) * AppSizes.inputSpacing) / fields.columns
                sourceComponent: kind === "choice" ? choiceField : kind === "flag" ? flagField : valueField

                Component {
                    id: choiceField
                    SelectorField {
                        objectName: `generated.${group.categoryId}.${field.modelData}`
                        options: category.optionsAt(field.index)
                        uid: `${group.categoryId}.${field.modelData}`
                        token: field.value
                        writable: field.editable
                        onSelected: token => group.apply(0, field.modelData, token)
                    }
                }
                Component {
                    id: flagField
                    EaElements.CheckBox {
                        objectName: `generated.${group.categoryId}.${field.modelData}`
                        leftPadding: 0
                        text: category.labels[field.index] ?? field.modelData
                        checked: field.value === "true"
                        enabled: field.editable
                        onToggled: group.apply(0, field.modelData, checked ? "true" : "false")
                    }
                }
                Component {
                    id: valueField
                    ValueField {
                        objectName: `generated.${group.categoryId}.${field.modelData}`
                        label: category.labels[field.index] ?? field.modelData
                        unit: category.units[field.index] ?? ""
                        accepts: field.kind === "number" ? "number" : "text"
                        fieldValue: field.value
                        editable: field.editable
                        onCommitted: text => group.apply(0, field.modelData, text)
                    }
                }
            }
        }
    }

    // A loop: the shared table, made only for a loop, so no empty table stands for single items.
    Loader {
        active: category.loop
        width: parent.width
        sourceComponent: Component {
            DataTable {
                id: table

                objectName: `generated.${group.categoryId}.list`
                defaultInfoText: qsTr("No rows")
                sourceModel: category.loop ? category.rows : null
                // The cells a Repeater makes come before it, so the Repeater, declared last, takes the last width.
                columns: [numberColumnWidth].concat(category.names.map(() => -1)).concat([0.001])

                header: EaComponents.ListViewHeader {
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Repeater {
                        model: category.labels
                        delegate: EaComponents.ListViewLabel {
                            required property int index
                            required property string modelData
                            horizontalAlignment: Text.AlignHCenter
                            text: category.units[index] ? `${modelData} (${category.units[index]})` : modelData
                        }
                    }
                }

                delegate: TableRow {
                    id: row

                    required property list<string> values

                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        marksCurrentRow: true
                        text: row.index + 1
                    }
                    Repeater {
                        model: category.names
                        delegate: TextCell {
                            required property int index
                            required property string modelData
                            readonly property string cellText: row.values[index] ?? ""
                            // A number of a dictionary item is a number cell, aligned and written as the dictionary's.
                            readonly property bool isNumber: category.kinds[index] === "number" && cellText !== "" && isFinite(Number(cellText))

                            objectName: `generated.${group.categoryId}.${modelData}.${row.index}`
                            horizontalAlignment: Text.AlignHCenter
                            accepts: category.kinds[index] === "number" ? "number" : "text"
                            uid: isNumber ? `${group.categoryId}.${modelData}` : ""
                            value: isNumber ? Number(cellText) : cellText
                            readOnly: category.output || group.source === null || group.source.file === ""
                            onCommitted: text => group.apply(row.index, modelData, text)
                        }
                    }
                }
            }
        }
    }

    EaElements.Label {
        objectName: `generated.${group.categoryId}.refusal`
        width: parent.width
        visible: group.refusal !== ""
        wrapMode: Text.Wrap
        color: EaStyle.Colors.red
        text: group.refusal
    }
}
