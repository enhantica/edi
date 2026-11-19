// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A Magnetic structure's derived symbols on Extra (edi ADR-0078): the UNI symbol, the OG number and name and the
// point group (UNI symbol, Litvin number), read only and saved as the dictionary's `_space_group_magn` items.
Grid {
    id: group

    property StructureViewModel structure: null
    readonly property var magnetic: structure ? structure.magneticGroup : ({})
    readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.inputSpacing) / 3

    columns: 3
    columnSpacing: AppSizes.inputSpacing
    rowSpacing: AppSizes.inputSpacing

    ValueField {
        objectName: "magneticSymbols.nameUni"
        width: group.fieldWidth
        uid: "space_group_magn.name_uni"
        editable: false
        fieldValue: group.magnetic.name_uni ?? ""
    }
    ValueField {
        objectName: "magneticSymbols.numberOg"
        width: group.fieldWidth
        uid: "space_group_magn.number_og"
        editable: false
        fieldValue: group.magnetic.number_og ?? ""
    }
    ValueField {
        objectName: "magneticSymbols.nameOg"
        width: group.fieldWidth
        uid: "space_group_magn.name_og"
        editable: false
        fieldValue: group.magnetic.name_og ?? ""
    }
    ValueField {
        objectName: "magneticSymbols.pointGroupUni"
        width: group.fieldWidth
        uid: "space_group_magn.point_group_name_uni"
        editable: false
        fieldValue: group.magnetic.point_group_name_uni ?? ""
    }
    ValueField {
        objectName: "magneticSymbols.pointGroupLitvin"
        width: group.fieldWidth
        uid: "space_group_magn.point_group_number_litvin"
        editable: false
        fieldValue: group.magnetic.point_group_number_litvin ?? ""
    }
}
