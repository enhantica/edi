// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// How the project writes and shows every value with a standard uncertainty: the IUCr recommendation, or always
// two digits. A setting of the project, saved with it, so whoever opens the project calculates from the same
// numbers; the application preference only sets it for new projects.
SideBarGroup {
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
        id: ruleBox
        objectName: "project.suRule"
        width: AppSizes.loneControlWidth
        enabled: group.project !== null
        ToolTip.text: enabled ? "" : qsTr("Open or create a project first")
        // The order is `rules`, each by its dictionary name.
        model: ApplicationInfo.nativeListProjection(3)
        currentIndex: group.project ? group.rules.indexOf(group.project.suRule) : 0
        onActivated: index => group.project.suRule = group.rules[index]
    }

    // The open list goes as another project's replacement starts, before it shows (AppState.retirePopup): a choice from
    // it would otherwise land on the next project.
    Connections {
        target: Session
        function onProjectReplacing() {
            AppState.retirePopup(ruleBox.popup);
        }
    }
}
