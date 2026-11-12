// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import Qt.labs.qmlmodels

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

    // The block's text, read while the group is open, and the categoryData.
    property BlockText source: null
    property string categoryId: ""
    // Why the last edit was refused.
    property string refusal: ""

    function apply(row: int, name: string, value: string) {
        ApplicationInfo.applyGeneratedCategory(row, name, value);
    }

    spacing: AppSizes.groupContentSpacing
    width: EaStyle.Sizes.sideBarContentWidth

    GeneratedCategory {
        id: categoryData
        source: group.source
        categoryId: group.categoryId
    }

    // Single items: labelled fields, up to four a row.
    Grid {
        id: fields

        visible: !categoryData.loop
        columns: Math.min(4, Math.max(1, categoryData.names.length))
        columnSpacing: AppSizes.inputSpacing
        rowSpacing: AppSizes.groupContentSpacing

        // Each item in the control its dictionary type asks for: a selector, a check box, or a field taking a number
        // or a text.
        Repeater {
            model: categoryData.loop ? [] : categoryData.names
            delegate: Loader {
                id: field

                required property int index
                required property string modelData
                readonly property string kind: categoryData.kinds[index] ?? "text"
                readonly property string value: categoryData.rowCount > 0 ? categoryData.value(0, index) : ""
                readonly property bool editable: !categoryData.output && !categoryData.setByProgram.includes(modelData) && group.source !== null && group.source.file !== ""

                width: (EaStyle.Sizes.sideBarContentWidth - (fields.columns - 1) * AppSizes.inputSpacing) / fields.columns
                sourceComponent: kind === "choice" ? choiceField : kind === "flag" ? flagField : valueField

                Component {
                    id: choiceField
                    SelectorField {
                        objectName: `generated.${group.categoryId}.${field.modelData}`
                        options: categoryData.options[field.index] ?? null
                        uid: `${group.categoryId}.${field.modelData}`
                        token: field.value
                        writable: field.editable
                        onSelected: token => group.apply(0, field.modelData, token)
                    }
                }
                Component {
                    id: flagField
                    FlagField {
                        objectName: `generated.${group.categoryId}.${field.modelData}`
                        label: categoryData.labels[field.index] ?? field.modelData
                        checked: field.value === "true"
                        editable: field.editable
                        ToolTip.text: field.editable ? "" : categoryData.output ? qsTr("Calculated by the program, so shown, not edited") : categoryData.setByProgram.includes(field.modelData) ? qsTr("Set by the program, so shown, not edited") : qsTr("This block is written to no project file, so shown, not edited")
                        onToggled: group.apply(0, field.modelData, checked ? "true" : "false")
                    }
                }
                Component {
                    id: valueField
                    ValueField {
                        objectName: `generated.${group.categoryId}.${field.modelData}`
                        label: categoryData.labels[field.index] ?? field.modelData
                        unit: categoryData.units[field.index] ?? ""
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
        active: categoryData.loop
        width: parent.width
        sourceComponent: Component {
            DataTable {
                id: table

                objectName: `generated.${group.categoryId}.list`
                defaultInfoText: qsTr("No rows")
                sourceModel: categoryData.loop ? categoryData.rows : null
                // The cells a Repeater makes come before it, so the Repeater, declared last, takes the last width.
                columns: ApplicationInfo.nativeListProjection(0)

                header: EaComponents.ListViewHeader {
                    EaComponents.ListViewLabel {
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Repeater {
                        model: categoryData.labels
                        delegate: EaComponents.ListViewLabel {
                            elide: Text.ElideRight
                            required property int index
                            required property string modelData
                            readonly property string units: categoryData.units[index] ?? ""
                            readonly property string description: categoryData.descriptions[index] ?? ""
                            horizontalAlignment: Text.AlignHCenter
                            // The label alone, as every table header; its units and what it holds are its tooltip.
                            text: modelData
                            ToolTip.text: [description, units !== "" ? qsTr("Units: %1").arg(units) : ""].filter(t => t !== "").join(" ")
                        }
                    }
                }

                delegate: TableRow {
                    id: row

                    required property list<string> values

                    // A calculated or unsaved table is shown, not edited: no hover tint, as nothing in it is chosen.
                    highlightsHover: !categoryData.output && group.source !== null && group.source.file !== ""

                    EaComponents.ListViewLabel {
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignHCenter
                        marksCurrentRow: true
                        text: row.index + 1
                    }
                    // Each item in the cell its dictionary type asks for: a selector with the dictionary's labels, or
                    // a text cell, a number of a dictionary item a number cell, aligned and written as the dictionary's.
                    Repeater {
                        model: categoryData.cells
                        delegate: DelegateChooser {
                            role: "kind"
                            DelegateChoice {
                                roleValue: "choice"
                                ComboCell {
                                    id: choice

                                    required property var modelData
                                    readonly property bool editable: !categoryData.output && group.source !== null && group.source.file !== ""

                                    SearchableComboBox {
                                        readonly property OptionListModel options: categoryData.options[choice.modelData.column] ?? null

                                        objectName: `generated.${group.categoryId}.${choice.modelData.name}.${row.index}`
                                        inTable: true
                                        horizontalAlignment: Text.AlignLeft
                                        anchors.verticalCenter: parent.verticalCenter
                                        enabled: choice.editable
                                        ToolTip.text: choice.editable ? "" : categoryData.output ? qsTr("Calculated by the program, so shown, not edited") : qsTr("This block is written to no project file, so shown, not edited")
                                        model: options
                                        textRole: "label"
                                        valueRole: "token"
                                        currentIndex: options ? options.indexOf(row.values[choice.modelData.column] ?? "") : -1
                                        displayText: currentIndex >= 0 ? currentText : (row.values[choice.modelData.column] ?? "")
                                        onActivated: index => group.apply(row.index, choice.modelData.name, currentValue)
                                    }
                                }
                            }
                            // A calculated cell naming a parameter shows it as the Analysis parameter table does,
                            // with its `.edi` name in the tooltip, and the name itself if no parameter has it now.
                            DelegateChoice {
                                roleValue: "parameter"
                                Item {
                                    id: reference

                                    required property var modelData
                                    readonly property string name: row.values[modelData.column] ?? ""
                                    readonly property ParameterItem parameter: Session.project !== null && name !== "" ? Session.project.parameterNamed(name) : null
                                    property int horizontalAlignment: Text.AlignLeft

                                    objectName: `generated.${group.categoryId}.${modelData.name}.${row.index}`
                                    implicitWidth: referenceLine.implicitWidth
                                    height: parent ? parent.height : EaStyle.Sizes.tableRowHeight
                                    clip: true

                                    IconLine {
                                        id: referenceLine
                                        anchors.verticalCenter: parent.verticalCenter
                                        textColor: EaStyle.Colors.themeForegroundMinor
                                        segments: reference.parameter !== null ? ParameterNames.segments(reference.parameter) : [
                                            {
                                                "text": reference.name
                                            }
                                        ]
                                    }
                                    HoverHandler {
                                        id: referenceHover
                                    }
                                    EaElements.ToolTip {
                                        text: reference.name
                                        requested: referenceHover.hovered
                                    }
                                }
                            }
                            DelegateChoice {
                                TextCell {
                                    required property var modelData
                                    readonly property string cellText: row.values[modelData.column] ?? ""
                                    readonly property bool isNumber: modelData.kind === "number" && cellText !== "" && isFinite(Number(cellText))

                                    objectName: `generated.${group.categoryId}.${modelData.name}.${row.index}`
                                    horizontalAlignment: Text.AlignHCenter
                                    accepts: modelData.kind === "number" ? "number" : "text"
                                    uid: isNumber ? `${group.categoryId}.${modelData.name}` : ""
                                    displayed: categoryData.output
                                    value: isNumber ? Number(cellText) : cellText
                                    readOnly: categoryData.output || group.source === null || group.source.file === ""
                                    onCommitted: text => group.apply(row.index, modelData.name, text)
                                }
                            }
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
