// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Whether a save copies a scan's linked files into the project, keeps them linked, or asks each time (edi ADR-0069,
// the owner, 2026-11-04). Kept by the app for this project's folder; until chosen, all data up to 20 files and 50 MB,
// linked above.
SideBarGroup {
    id: group

    property ProjectViewModel project: null
    readonly property string openKey: "Extras:saveData"
    readonly property var modes: ["all", "linked", "ask"]

    objectName: "group.save_data"
    collapsed: !SideBarGroups.isOpen(openKey, group)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed, group)
    last: SideBarGroups.isLast(group)
    title: qsTr("Data on save")
    icon: "database"

    EaElements.ComboBox {
        objectName: "project.includeDataOnSave"
        width: EaStyle.Sizes.sideBarContentWidth
        enabled: group.project !== null
        model: [qsTr("Include all data"), qsTr("Keep linked data linked"), qsTr("Ask on every save")]
        currentIndex: group.project ? group.modes.indexOf(group.project.includeDataOnSave) : 0
        onActivated: index => group.project.includeDataOnSave = group.modes[index]
        ToolTip.text: qsTr("What a save does with data files the project reads from outside its folder")
        ToolTip.visible: hovered && EaGlobals.Vars.showToolTips
    }
}
