// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The magnetic symmetry analysis of the current Crystal structure, on the Structure page's Tools tab (owner,
// 2026-11-28, sidebar tabs by role; edi ADR-0017 §2): a button that opens the symmetry popup for it, where the
// magnetic subgroups are found and chosen. A Magnetic structure is analysed from the Crystal structure it came from.
SideBarGroup {
    id: group

    property ProjectViewModel project: null
    property StructureViewModel structure: null
    // The popup this group opens (MagneticPopup), declared on the page.
    property Component popupComponent: null

    readonly property bool crystal: structure !== null && !structure.magnetic

    readonly property string openKey: "Tools:magnetic_analysis"
    pinKey: openKey
    objectName: "group.magnetic_analysis"
    collapsed: !SideBarGroups.isOpen(openKey, group)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed, group)
    last: SideBarGroups.isLast(group)
    title: qsTr("Magnetic symmetry analysis")
    icon: "magnet"

    Column {
        width: parent ? parent.width : 0
        spacing: AppSizes.groupContentSpacing

        EaElements.Label {
            width: parent.width
            wrapMode: Text.Wrap
            color: EaStyle.Colors.themeForegroundMinor
            text: group.crystal
                ? qsTr("The magnetic space groups of this structure for a propagation vector k, to add as magnetic structures.")
                : qsTr("Choose the Crystal structure a magnetic structure came from to analyse it.")
        }
        EaElements.SideBarButton {
            objectName: "spaceGroup.magneticAnalysis"
            wide: true  // the row to itself, as the sidebar's other single actions
            enabled: group.crystal && group.project !== null && group.popupComponent !== null
            fontIcon: "magnet"
            text: qsTr("Magnetic symmetry analysis…")
            onClicked: {
                const popup = group.popupComponent.createObject(Overlay.overlay, {
                    project: group.project,
                    structureIndex: group.project.currentStructureIndex,
                    structure: group.structure
                }) as MagneticPopup;
                popup.open();
            }
        }
    }
}
