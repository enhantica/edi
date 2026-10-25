// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// How a followed scan redraws the pattern while it runs (edi ADR-0029): a setting of this machine, not part of the
// project, so it is on the page's Settings tab (edi ADR-0031 §2).
EaElements.GroupBox {
    id: group

    readonly property string openKey: "Settings:patternUpdates"

    objectName: "group.patternUpdates"
    collapsed: !SideBarGroups.isOpen(openKey, group)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed)
    last: SideBarGroups.isLast(group)
    title: qsTr("Pattern updates during a scan")
    icon: "chart-line"

    EaElements.ComboBox {
        objectName: "analysis.patternUpdates"
        width: EaStyle.Sizes.sideBarContentWidth
        // The order is FitViewModel.patternUpdates's, so a saved 0, the earlier "Every pattern", is "fit waits", and the
        // newer choice comes last.
        model: [qsTr("Every pattern, fit waits for the display"), qsTr("About once a second"), qsTr("Adaptive"), qsTr("Only at the end"), qsTr("Every pattern, display catches up")]
        currentIndex: Preferences.scanPatternUpdates
        onActivated: index => Preferences.scanPatternUpdates = index
    }
}
