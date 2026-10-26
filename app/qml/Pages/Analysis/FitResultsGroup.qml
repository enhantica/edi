// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Whether a finished fit opens its results window (the owner, 2026-10-26): a setting of this user, not part of the
// project, so it is on the page's Settings tab beside the show-filters (edi ADR-0031 §2). Off, the status bar's fit
// status still opens the results.
EaElements.GroupBox {
    id: group

    readonly property string openKey: "Settings:fitResults"

    objectName: "group.fitResults"
    collapsed: !SideBarGroups.isOpen(openKey)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed)
    last: SideBarGroups.isLast(group)
    title: qsTr("Fit results")
    icon: "poll"

    EaElements.CheckBox {
        objectName: "analysis.showFitResults"
        width: EaStyle.Sizes.sideBarContentWidth
        leftPadding: 0
        text: qsTr("Show fit results after fitting")
        checked: Preferences.showFitResults
        onToggled: Preferences.showFitResults = checked
        ToolTip.text: qsTr("Open the results window when a fit ends; the fit status in the status bar opens it too")
    }
}
