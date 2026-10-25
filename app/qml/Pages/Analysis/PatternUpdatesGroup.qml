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
        // The order the owner chose (2026-10-24); `values` holds each entry's FitViewModel.patternUpdates, so saved
        // choices keep their meaning: a saved 0, the earlier "Every pattern", is "fit waits".
        readonly property list<int> values: [2, 1, 0, 4, 3]
        model: [qsTr("Adaptive"), qsTr("About once a second"), qsTr("Every pattern, fit waits for the display"), qsTr("Every pattern, display catches up"), qsTr("Only at the end")]
        currentIndex: values.indexOf(Preferences.scanPatternUpdates)
        onActivated: index => Preferences.scanPatternUpdates = values[index]
    }
}
