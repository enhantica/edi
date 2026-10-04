// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `linked_structure` (easydiffractionbeta's Associated phases; edi's singular category, packet
// D-g): the structure this experiment calculates and its scale. A loop in `.edi`, so a table ("loop in
// .edi — table in gui"), with its one row while edi calculates one structure per
// experiment (multiphase is not implemented). As easydiffractionbeta's Associated phases, each row shows the
// linked structure's icon in that structure's colour before its label (edi ADR-0017 §8), and a remove button,
// disabled: an experiment keeps its one linked structure.
EaComponents.TableView {
    id: table

    property ExperimentViewModel experiment: null
    property ProjectViewModel project: null
    // The linked structure's place in the project (its colour); the count re-reads it as structures come and go.
    readonly property int structureIndex: table.project && table.experiment && table.project.structures.count >= 0 ? table.project.structureIndex(table.experiment.linkedStructureId) : -1

    objectName: "linkedStructure.list"
    defaultInfoText: qsTr("No linked structure")
    model: experiment ? 1 : 0

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
            width: AppSizes.iconColumnWidth
        }
    }

    delegate: EaComponents.TableViewDelegate {
        id: row

        required property int index

        EaComponents.TableViewLabel {
            width: AppSizes.indexColumnWidth
            color: EaStyle.Colors.themeForegroundMinor
            text: row.index + 1
        }
        IconCell {
            objectName: `linkedStructure.color.${row.index}`
            icon: "layer-group"
            iconColor: AppColors.structure(table.structureIndex)
            toolTip: qsTr("Calculated pattern color")
        }
        TextCell {
            objectName: "linkedStructure.structureId"
            width: table.headerLabelItems.length > 2 ? table.headerLabelItems[2].width : 0
            horizontalAlignment: Text.AlignLeft
            value: table.experiment ? table.experiment.linkedStructureId : ""
            onCommitted: text => table.experiment.linkedStructureId = text
        }
        ParameterCell {
            objectName: "linked_structure.scale"
            width: EaStyle.Sizes.fontPixelSize * 8
            item: table.experiment ? table.experiment.scale : null
        }
        EaComponents.TableViewButton {
            objectName: `linkedStructure.remove.${row.index}`
            enabled: false
            fontIcon: "minus-circle"
            ToolTip.text: qsTr("Remove this linked structure")
        }
    }
}
