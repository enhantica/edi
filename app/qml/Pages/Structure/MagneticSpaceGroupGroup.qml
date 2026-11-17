// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `space_group_magn` (edi ADR-0078; the owner, 2026-11-03): the magnetic space group, chosen from crysta's table of
// the 1651 groups by BNS number and symbol, beside its UNI symbol. A choice replaces the structure's operators when
// crysta admits them with the cell and the propagation vectors; a refused one leaves the structure as it was and says
// why. Under it the parent group, read only, when it is not the space group itself (a supercell or a lower family
// group).
Column {
    id: group

    property StructureViewModel structure: null
    readonly property var magnetic: structure ? structure.magneticGroup : ({})
    readonly property var parent_: structure ? structure.parentGroup : ({})

    spacing: AppSizes.inputSpacing
    // The BNS and UNI symbols in two equal columns, as Bond settings and Appearance pair their fields (the owner,
    // 2026-11-17); the parent group's three fields in equal thirds.
    readonly property real halfWidth: (EaStyle.Sizes.sideBarContentWidth - AppSizes.inputSpacing) / 2
    readonly property real thirdWidth: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.inputSpacing) / 3

    Grid {
        columns: 2
        columnSpacing: AppSizes.inputSpacing

        // Searchable like the space group's name (the owner, 2026-11-03).
        SearchableComboBox {
            id: selector
            objectName: "magneticSpaceGroup.selector"
            width: group.halfWidth
            title: Session.label("space_group_magn.name_bns")
            searchThreshold: 0
            model: group.structure ? group.structure.magneticGroupNames : []
            readonly property string current: (group.magnetic.number_bns ?? "") + "  " + (group.magnetic.name_bns ?? "")
            currentIndex: model.indexOf(current)
            displayText: group.magnetic.number_bns ? current : ""
            // The choice goes to the model; the box then follows the model's group again.
            onActivated: index => {
                if (group.structure) {
                    group.structure.setMagneticGroup(index);
                }
                currentIndex = Qt.binding(() => model.indexOf(current));
            }
        }
        ValueField {
            objectName: "magneticSpaceGroup.nameUni"
            width: group.halfWidth
            uid: "space_group_magn.name_uni"
            editable: false
            fieldValue: group.magnetic.name_uni ?? ""
        }
    }
    EaElements.Label {
        objectName: "magneticSpaceGroup.refusal"
        visible: text !== ""
        width: EaStyle.Sizes.sideBarContentWidth
        wrapMode: Text.WordWrap
        color: EaStyle.Colors.red
        text: group.structure ? group.structure.magneticGroupRefusal : ""
    }
    EaElements.GroupRow {
        visible: group.parent_.differs === true
        spacing: AppSizes.inputSpacing

        ValueField {
            objectName: "magneticSpaceGroup.parentName"
            width: group.thirdWidth
            uid: "parent_space_group.name_h_m_alt"
            editable: false
            fieldValue: group.parent_.name_h_m_alt ?? ""
        }
        ValueField {
            objectName: "magneticSpaceGroup.parentNumber"
            width: group.thirdWidth
            uid: "parent_space_group.it_number"
            editable: false
            fieldValue: group.parent_.it_number ?? ""
        }
        ValueField {
            objectName: "magneticSpaceGroup.parentTransform"
            width: group.thirdWidth
            uid: "parent_space_group.transform_pp_abc"
            editable: false
            fieldValue: group.parent_.transform_pp_abc ?? ""
        }
    }
}
