// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// How a followed scan redraws the pattern while it runs (edi ADR-0029). A preference of this machine, not part of
// the project, so it comes after the project's own groups.
EaElements.GroupBox {
    id: group

    readonly property string openKey: "Extras:patternUpdates"

    objectName: "group.patternUpdates"
    collapsed: !SideBarGroups.isOpen(openKey)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed)
    last: SideBarGroups.isLast(group)
    title: qsTr("Pattern updates during a scan")
    icon: "chart-line"

    EaElements.ComboBox {
        objectName: "analysis.patternUpdates"
        width: EaStyle.Sizes.sideBarContentWidth
        // The order is FitViewModel.patternUpdates's.
        model: [qsTr("Every pattern"), qsTr("About once a second"), qsTr("Adaptive"), qsTr("Only at the end")]
        currentIndex: Preferences.scanPatternUpdates
        onActivated: index => Preferences.scanPatternUpdates = index
    }
}
