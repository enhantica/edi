// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `space_group_magn` (edi ADR-0078): a Magnetic structure's group in place of Space group, built like it. Crystal
// system is read only and not saved (the magnetic CIF dictionary has no item for it). Number BNS and Name BNS are two
// linked, searchable fields over crysta's table of the 1651 groups: choosing either replaces the structure's operators
// when crysta admits them, else nothing changes and the refusal says why. Setting is the transform to the BNS
// standard, `a,b,c;0,0,0` for the standard itself. The derived symbols and the parent group are on Extra.
Column {
    id: group

    property StructureViewModel structure: null
    readonly property var magnetic: structure ? structure.magneticGroup : ({})
    readonly property int index: structure && magnetic.number_bns ? structure.magneticGroupNumbersBns.indexOf(magnetic.number_bns) : -1
    readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - 3 * AppSizes.inputSpacing) / 4

    spacing: AppSizes.inputSpacing

    EaElements.GroupRow {
        spacing: AppSizes.inputSpacing

        ValueField {
            objectName: "magneticSpaceGroup.crystalSystem"
            width: group.fieldWidth
            label: qsTr("Crystal system")
            editable: false
            fieldValue: group.structure && group.structure.spaceGroup ? group.structure.spaceGroup.crystalSystem : ""
        }
        SearchableComboBox {
            objectName: "magneticSpaceGroup.numberBns"
            width: group.fieldWidth
            // The names the owner gave the two fields (decision of 2026-11-18), not the dictionary's labels.
            title: qsTr("Number BNS")
            searchThreshold: 0
            model: group.structure ? group.structure.magneticGroupNumbersBns : []
            currentIndex: group.index
            displayText: group.magnetic.number_bns ?? ""
            onActivated: index => {
                if (group.structure)
                    group.structure.setMagneticGroup(index);
                currentIndex = Qt.binding(() => group.index);
            }
        }
        SearchableComboBox {
            objectName: "magneticSpaceGroup.nameBns"
            width: group.fieldWidth
            title: qsTr("Name BNS")
            searchThreshold: 0
            model: group.structure ? group.structure.magneticGroupNamesBns : []
            currentIndex: group.index
            displayText: group.magnetic.name_bns ?? ""
            onActivated: index => {
                if (group.structure)
                    group.structure.setMagneticGroup(index);
                currentIndex = Qt.binding(() => group.index);
            }
        }
        ValueField {
            objectName: "magneticSpaceGroup.setting"
            width: group.fieldWidth
            label: qsTr("Setting")
            fieldValue: group.magnetic.setting ?? ""
            onCommitted: text => {
                if (group.structure)
                    group.structure.setMagneticSetting(text);
            }
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
}
