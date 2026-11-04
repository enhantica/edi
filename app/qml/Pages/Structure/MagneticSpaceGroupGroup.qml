// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `space_group_magn` (edi ADR-0070; the owner, 2026-11-03): the magnetic space group as the file names it, its BNS
// number, BNS symbol and UNI symbol in one row, read only until the group can be chosen from crysta's table. Under
// it the parent group, read only, when it is not the space group itself (a supercell or a lower family group).
Column {
    id: group

    property StructureViewModel structure: null
    readonly property var magnetic: structure ? structure.magneticGroup : ({})
    readonly property var parent_: structure ? structure.parentGroup : ({})

    spacing: AppSizes.inputSpacing

    EaElements.GroupRow {
        spacing: AppSizes.inputSpacing

        ValueField {
            objectName: "magneticSpaceGroup.numberBns"
            uid: "space_group_magn.number_bns"
            editable: false
            fieldValue: group.magnetic.number_bns ?? ""
        }
        ValueField {
            objectName: "magneticSpaceGroup.nameBns"
            uid: "space_group_magn.name_bns"
            editable: false
            fieldValue: group.magnetic.name_bns ?? ""
        }
        ValueField {
            objectName: "magneticSpaceGroup.nameUni"
            uid: "space_group_magn.name_uni"
            editable: false
            fieldValue: group.magnetic.name_uni ?? ""
        }
    }
    EaElements.GroupRow {
        visible: group.parent_.differs === true
        spacing: AppSizes.inputSpacing

        ValueField {
            objectName: "magneticSpaceGroup.parentName"
            uid: "parent_space_group.name_h_m_alt"
            editable: false
            fieldValue: group.parent_.name_h_m_alt ?? ""
        }
        ValueField {
            objectName: "magneticSpaceGroup.parentNumber"
            uid: "parent_space_group.it_number"
            editable: false
            fieldValue: group.parent_.it_number ?? ""
        }
        ValueField {
            objectName: "magneticSpaceGroup.parentTransform"
            uid: "parent_space_group.transform_pp_abc"
            editable: false
            fieldValue: group.parent_.transform_pp_abc ?? ""
        }
    }
}
