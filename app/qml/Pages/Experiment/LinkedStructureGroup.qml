// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `linked_structure` (easydiffractionbeta's Associated phases): the structures (phases) this experiment's
// pattern sums, each with its scale. A loop in `.edi`, so a table. As easydiffractionbeta's Associated phases,
// each row shows the structure's icon in that structure's colour before its name (edi ADR-0017 §8). The name
// is picked from the project's structures; a row can be added for a structure not yet linked, removed while
// another remains, and switched off: a disabled row is kept and saved but neither calculated nor fitted.
Column {
    id: group

    property ExperimentViewModel experiment: null
    property ProjectViewModel project: null
    readonly property LinkedStructureListModel rows: experiment ? experiment.linkedStructures : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table

        columnWidths: [numberColumnWidth, EaStyle.Sizes.tableRowHeight, -1, EaStyle.Sizes.fontPixelSize * 8, AppSizes.iconColumnWidth, AppSizes.iconColumnWidth]
        defaultInfoText: qsTr("No linked structure")
        model: group.rows
        objectName: "linkedStructure.list"

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property int colorIndex
            required property int index
            // `scale` and `enabled` are Item properties, so these two roles are read through the model.
            required property var model
            required property string structureId

            EaComponents.TableViewLabel {
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            IconCell {
                icon: "layer-group"
                iconColor: AppColors.structure(row.colorIndex)
                objectName: `linkedStructure.color.${row.index}`
                toolTip: qsTr("Calculated pattern color")
            }
            // The structure, picked from the project's structures as the aliases table picks a parameter.
            EaComponents.TableViewComboBox {
                ToolTip.text: row.structureId
                currentIndex: group.rows ? group.rows.structureNames.indexOf(row.structureId) : -1
                displayText: row.structureId
                enabled: row.model.enabled
                model: group.rows ? group.rows.structureNames : []
                objectName: `linkedStructure.structureId.${row.index}`

                onActivated: index => {
                    group.rows.setStructureId(row.index, group.rows.structureNames[index]);
                    currentIndex = Qt.binding(() => group.rows ? group.rows.structureNames.indexOf(row.structureId) : -1);
                }
            }
            ParameterCell {
                enabled: row.model.enabled
                item: row.model.scale
                objectName: `linkedStructure.scale.${row.index}`
            }
            // Disabled as a constraint is: kept and saved, but neither calculated nor fitted.
            EaComponents.TableViewButton {
                ToolTip.text: row.model.enabled ? qsTr("Disable this linked structure") : qsTr("Enable this linked structure")
                fontIcon: row.model.enabled ? "toggle-on" : "toggle-off"
                objectName: `linkedStructure.enabled.${row.index}`

                onClicked: group.rows.setEnabled(row.index, !row.model.enabled)
            }
            EaComponents.TableViewButton {
                ToolTip.text: qsTr("Remove this linked structure")
                enabled: group.rows !== null && group.rows.canRemove
                fontIcon: "minus-circle"
                objectName: `linkedStructure.remove.${row.index}`

                onClicked: group.rows.remove(row.index)
            }
        }
        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
            }
            EaComponents.TableViewLabel {
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("structure")
            }
            EaComponents.TableViewLabel {
                text: qsTr("scale")
            }
            EaComponents.TableViewLabel {
            }
            EaComponents.TableViewLabel {
            }
        }
    }
    EaElements.SideBarButton {
        enabled: group.rows !== null && group.rows.canAppend
        fontIcon: "plus-circle"
        objectName: "linkedStructure.append"
        text: qsTr("Add linked structure")
        wide: true

        onClicked: group.rows.append()
    }
}
