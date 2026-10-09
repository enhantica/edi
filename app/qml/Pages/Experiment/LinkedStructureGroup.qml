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

        objectName: "linkedStructure.list"
        defaultInfoText: qsTr("No linked structure")
        sourceModel: group.rows

        columnWidths: [numberColumnWidth, EaStyle.Sizes.tableRowHeight, -1, EaStyle.Sizes.fontPixelSize * 8, AppSizes.iconColumnWidth, AppSizes.iconColumnWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("structure")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: qsTr("scale")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property int index
            required property string structureId
            required property int colorIndex
            // `scale` and `enabled` are Item properties, so these two roles are read through the model.
            required property var model

            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            IconCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `linkedStructure.color.${row.index}`
                icon: "layer-group"
                iconColor: AppColors.structure(row.colorIndex)
                toolTip: qsTr("Calculated pattern color")
            }
            // The structure, picked from the project's structures as the aliases table picks a parameter.
            Item {
                property int horizontalAlignment: Text.AlignLeft
                height: parent.height
                SearchableComboBox {
                    width: Math.min(parent.width, implicitWidth)
                    x: parent.horizontalAlignment === Text.AlignRight ? parent.width - width : parent.horizontalAlignment === Text.AlignLeft ? 0 : (parent.width - width) / 2
                    inTable: true
                    horizontalAlignment: Text.AlignLeft
                    anchors.verticalCenter: parent.verticalCenter
                    objectName: `linkedStructure.structureId.${row.index}`
                    enabled: row.model.enabled
                    model: group.rows ? group.rows.structureNames : []
                    currentIndex: group.rows ? group.rows.structureNames.indexOf(row.structureId) : -1
                    displayText: row.structureId
                    ToolTip.text: row.structureId
                    onActivated: index => {
                        group.rows.setStructureId(row.index, group.rows.structureNames[index]);
                        currentIndex = Qt.binding(() => group.rows ? group.rows.structureNames.indexOf(row.structureId) : -1);
                    }
                }
            }
            ParameterCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `linkedStructure.scale.${row.index}`
                enabled: row.model.enabled
                item: row.model.scale
            }
            // Disabled as a constraint is: kept and saved, but neither calculated nor fitted.
            EaComponents.TableViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `linkedStructure.enabled.${row.index}`
                fontIcon: row.model.enabled ? "toggle-on" : "toggle-off"
                ToolTip.text: row.model.enabled ? qsTr("Disable this linked structure") : qsTr("Enable this linked structure")
                onClicked: group.rows.setEnabled(row.index, !row.model.enabled)
            }
            EaComponents.TableViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `linkedStructure.remove.${row.index}`
                enabled: group.rows !== null && group.rows.canRemove
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this linked structure")
                onClicked: group.rows.remove(row.index)
            }
        }
    }

    EaElements.SideBarButton {
        objectName: "linkedStructure.append"
        wide: true
        enabled: group.rows !== null && group.rows.canAppend
        fontIcon: "plus-circle"
        text: qsTr("Add linked structure")
        onClicked: group.rows.append()
    }
}
