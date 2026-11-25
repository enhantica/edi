// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `space_group_magn` (edi ADR-0078): a Magnetic structure's group in place of Space group, built like it. Crystal
// system is read only and not saved (the magnetic CIF dictionary has no item for it). Number BNS and Name BNS are two
// linked, searchable fields over crysta's table of the 1651 groups: choosing either replaces the structure's operators
// when crysta admits them, else nothing changes and the refusal says why. Setting is the transform to the BNS
// standard, chosen from the tabulated settings of the group's own space group, `a,b,c;0,0,0` first. The derived symbols and the parent group are on Extra. A refused
// choice shows in the app's error popup and the Messages center; the fields keep their values.
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
            // "System" where the whole title does not fit its field: a title is never cut (N1).
            label: crystalTitle.advanceWidth + EaStyle.Sizes.fontPixelSize <= width ? qsTr("Crystal system") : qsTr("System")
            TextMetrics {
                id: crystalTitle
                font.family: EaStyle.Fonts.fontFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize
                text: qsTr("Crystal system")
            }
            editable: false
            fieldValue: group.structure && group.structure.spaceGroup ? group.structure.spaceGroup.crystalSystem : ""
        }
        SearchableComboBox {
            objectName: "magneticSpaceGroup.numberBns"
            // The dictionary item it edits, as the designed fields name theirs.
            property string uid: "space_group_magn.number_bns"
            width: group.fieldWidth
            // The names the owner gave the two fields (decision of 2026-11-18), not the dictionary's labels.
            title: qsTr("Number BNS")
            searchThreshold: 0
            model: group.structure ? group.structure.magneticGroupNumbersBns : []
            currentIndex: group.index
            displayText: group.magnetic.number_bns ?? ""
            onActivated: index => {
                if (group.structure && !group.structure.setMagneticGroup(index))
                    Session.reportRefusal(group.structure.magneticGroupRefusal);
                currentIndex = Qt.binding(() => group.index);
            }
        }
        SearchableComboBox {
            objectName: "magneticSpaceGroup.nameBns"
            property string uid: "space_group_magn.name_bns"
            width: group.fieldWidth
            title: qsTr("Name BNS")
            searchThreshold: 0
            model: group.structure ? group.structure.magneticGroupNamesBns : []
            currentIndex: group.index
            displayText: group.magnetic.name_bns ?? ""
            onActivated: index => {
                if (group.structure && !group.structure.setMagneticGroup(index))
                    Session.reportRefusal(group.structure.magneticGroupRefusal);
                currentIndex = Qt.binding(() => group.index);
            }
        }
        // A searchable list, as the space group's Code (the owner, 2026-11-19): the tabulated settings of the group's
        // own space group, each as its transform from the BNS standard. A file's other setting shows as written,
        // marked operators only, with the tabulated ones still selectable.
        SearchableComboBox {
            objectName: "magneticSpaceGroup.setting"
            property string uid: "space_group_magn_transforms.pp_abc"
            readonly property string current: group.magnetic.setting ?? ""
            width: group.fieldWidth
            title: qsTr("Setting")
            searchThreshold: 0
            model: group.structure ? group.structure.magneticSettings : []
            currentIndex: model.indexOf(current)
            displayText: group.structure && !group.structure.magneticSettingTabulated && current !== "" ? qsTr("%1 (operators only)").arg(current) : current
            onActivated: index => {
                if (group.structure && !group.structure.chooseMagneticSetting(index))
                    Session.reportRefusal(group.structure.magneticGroupRefusal);
                currentIndex = Qt.binding(() => model.indexOf(current));
            }
        }
    }
}
