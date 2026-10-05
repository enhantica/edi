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

    EaComponents.TableView {
        id: table

        objectName: "linkedStructure.list"
        defaultInfoText: qsTr("No linked structure")
        model: group.rows

        header: EaComponents.TableViewHeader {
            EaComponents.TableViewLabel {
                width: AppSizes.indexColumnWidth
                text: qsTr("No.")
            }
            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.tableRowHeight
            }
            EaComponents.TableViewLabel {
                flexibleWidth: true
                horizontalAlignment: Text.AlignLeft
                text: qsTr("structure")
            }
            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 8
                text: qsTr("scale")
            }
            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 2.5
                text: qsTr("use")
            }
            EaComponents.TableViewLabel {
                width: AppSizes.iconColumnWidth
            }
        }

        delegate: EaComponents.TableViewDelegate {
            id: row

            required property int index
            required property string structureId
            required property int colorIndex
            // `scale` and `enabled` are Item properties, so these two roles are read through the model.
            required property var model

            EaComponents.TableViewLabel {
                width: AppSizes.indexColumnWidth
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            IconCell {
                objectName: `linkedStructure.color.${row.index}`
                icon: "layer-group"
                iconColor: AppColors.structure(row.colorIndex)
                toolTip: qsTr("Calculated pattern color")
            }
            EaElements.ComboBox {
                objectName: `linkedStructure.structureId.${row.index}`
                width: table.headerLabelItems.length > 2 ? table.headerLabelItems[2].width : 0
                height: EaStyle.Sizes.tableRowHeight
                model: group.rows ? group.rows.structureNames : []
                currentIndex: group.rows ? group.rows.structureNames.indexOf(row.structureId) : -1
                displayText: row.structureId
                onActivated: index => {
                    group.rows.setStructureId(row.index, group.rows.structureNames[index]);
                    currentIndex = Qt.binding(() => group.rows ? group.rows.structureNames.indexOf(row.structureId) : -1);
                }
            }
            ParameterCell {
                objectName: `linkedStructure.scale.${row.index}`
                width: EaStyle.Sizes.fontPixelSize * 8
                item: row.model.scale
            }
            EaComponents.TableViewCheckBox {
                objectName: `linkedStructure.enabled.${row.index}`
                width: EaStyle.Sizes.fontPixelSize * 2.5
                checked: row.model.enabled
                ToolTip.text: qsTr("Use this structure in the calculation and the fit")
                onToggled: group.rows.setEnabled(row.index, checked)
            }
            EaComponents.TableViewButton {
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
