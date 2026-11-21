// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `_parent_space_group` on Extra, always present for a Magnetic structure (edi ADR-0078): its name, IT number and
// the transform to it, read only. A file without one gets the magnetic group's own space group.
EaElements.GroupRow {
    id: group

    property StructureViewModel structure: null
    readonly property var parent_: structure ? structure.parentGroup : ({})
    readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.inputSpacing) / 3

    spacing: AppSizes.inputSpacing

    ValueField {
        objectName: "parentSpaceGroup.name"
        width: group.fieldWidth
        uid: "parent_space_group.name_h_m_alt"
        editable: false
        fieldValue: group.parent_.name_h_m_alt ?? ""
    }
    ValueField {
        objectName: "parentSpaceGroup.number"
        width: group.fieldWidth
        uid: "parent_space_group.it_number"
        editable: false
        fieldValue: group.parent_.it_number ?? ""
    }
    ValueField {
        objectName: "parentSpaceGroup.transform"
        width: group.fieldWidth
        uid: "parent_space_group.transform_pp_abc"
        editable: false
        fieldValue: group.parent_.transform_pp_abc ?? ""
    }
}
