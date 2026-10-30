// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// How the project writes and shows every value with a standard uncertainty: the IUCr recommendation, or always
// two digits. A setting of the project, saved with it, so whoever opens the project calculates from the same
// numbers; the application preference only sets it for new projects.
EaElements.GroupBox {
    id: group

    property ProjectViewModel project: null
    readonly property string openKey: "Extras:standardUncertainties"
    readonly property var rules: ["iucr_19", "iucr_99"]

    objectName: "group.su_format"
    collapsed: !SideBarGroups.isOpen(openKey, group)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed, group)
    last: SideBarGroups.isLast(group)
    title: Session.categoryTitle("su_format")
    icon: "ruler-horizontal"

    EaElements.ComboBox {
        objectName: "project.suRule"
        width: EaStyle.Sizes.sideBarContentWidth
        enabled: group.project !== null
        // The order is `rules`, each by its dictionary name.
        model: ApplicationInfo.nativeListProjection(3)
        currentIndex: group.project ? group.rules.indexOf(group.project.suRule) : 0
        onActivated: index => group.project.suRule = group.rules[index]
    }
}
