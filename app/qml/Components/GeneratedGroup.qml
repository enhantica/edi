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

    function apply(row: int, name: string, value: string) { ApplicationInfo.applyGeneratedCategory(row, name, value); }

    spacing: AppSizes.groupContentSpacing
    width: EaStyle.Sizes.sideBarContentWidth

    GeneratedCategory {
        id: data
        source: group.source
        categoryId: group.categoryId
    }

    // Single items: labelled fields, up to four a row.
    Grid {
        id: fields

        visible: !data.loop
        columns: Math.min(4, Math.max(1, data.names.length))
        columnSpacing: AppSizes.inputSpacing
        rowSpacing: AppSizes.groupContentSpacing

        Repeater {
            model: data.loop ? [] : data.names
            delegate: ValueField {
                required property int index
                required property string modelData

                objectName: `generated.${group.categoryId}.${modelData}`
                width: (EaStyle.Sizes.sideBarContentWidth - (fields.columns - 1) * AppSizes.inputSpacing) / fields.columns
                label: data.labels[index] ?? modelData
                unit: data.units[index] ?? ""
                fieldValue: data.rows.length > 0 ? (data.rows[0][index] ?? "") : ""
                editable: !data.output && !data.setByProgram.includes(modelData) && group.source !== null && group.source.file !== ""
                onCommitted: text => group.apply(0, modelData, text)
            }
        }
    }

    // A loop: the shared table, made only for a loop, so no empty table stands for single items.
    Loader {
        active: data.loop
        width: parent.width
        sourceComponent: Component {
            DataTable {
                id: table

                objectName: `generated.${group.categoryId}.list`
                defaultInfoText: qsTr("No rows")
                sourceModel: data.loop ? data.rows : null
                // The cells a Repeater makes come before it, so the Repeater, declared last, takes the last width.
                columns: ApplicationInfo.nativeListProjection(0)

                header: EaComponents.ListViewHeader {
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Repeater {
                        model: data.labels
                        delegate: EaComponents.ListViewLabel {
                            required property int index
                            required property string modelData
                            horizontalAlignment: Text.AlignHCenter
                            text: data.units[index] ? `${modelData} (${data.units[index]})` : modelData
                        }
                    }
                }

                delegate: TableRow {
                    id: row

                    required property var modelData

                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        marksCurrentRow: true
                        text: row.index + 1
                    }
                    Repeater {
                        model: data.names
                        delegate: TextCell {
                            required property int index
                            required property string modelData

                            objectName: `generated.${group.categoryId}.${modelData}.${row.index}`
                            horizontalAlignment: Text.AlignHCenter
                            value: row.modelData[index] ?? ""
                            readOnly: data.output || group.source === null || group.source.file === ""
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
