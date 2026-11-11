// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// What a page runs with, read-only, on its Settings tab: the count is this machine's Performance preference, never
// saved in a project, and the link at its right opens Preferences on that tab (the owner, 2026-11-04, 2026-11-10). The Analysis page shows how
// many scan files are fitted at once, the Experiment page how many threads a calculation runs on.
SideBarGroup {
    id: group

    // "parallelFits" or "threads".
    property string shows: "threads"
    readonly property string openKey: "Settings:performance"
    readonly property string threads: !ApplicationInfo.engineThreadsSelectable ? "1" : Preferences.engineThreads > 0 ? String(Preferences.engineThreads) : qsTr("Auto")

    objectName: "group.performance"
    collapsed: !SideBarGroups.isOpen(openKey, group)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed, group)
    last: SideBarGroups.isLast(group)
    title: qsTr("Performance")
    icon: "tachometer-alt"

    // The value on the left and, at the right end, a light link with the Preferences icon that opens that tab (the
    // owner, 2026-11-10: better than a link inside the sentence).
    Item {
        width: EaStyle.Sizes.sideBarContentWidth
        height: Math.max(line.implicitHeight, link.implicitHeight)

        EaElements.Label {
            id: line

            objectName: "performance.line"
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - link.width - EaStyle.Sizes.fontPixelSize
            elide: Text.ElideRight
            text: group.shows === "parallelFits" ? qsTr("Parallel fits: %1").arg(Preferences.scanWorkersApplied) : qsTr("Threads per calculation: %1").arg(group.threads)
        }
        IconLink {
            id: link

            objectName: "performance.preferences"
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            fontIcon: "cog"
            text: qsTr("Preferences")
            onClicked: Preferences.openPerformance()
            ToolTip.text: qsTr("Change it on the Performance tab of Preferences, for this computer")
        }
    }
}
