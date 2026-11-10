// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// What a page runs with, read-only, on its Settings tab: the count is this machine's Performance preference, never
// saved in a project, and the link opens Preferences on that tab (the owner, 2026-11-04). The Analysis page shows how
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

    // A plain Text, so the link runs the app's own action rather than going to the browser.
    Text {
        objectName: "performance.line"
        width: EaStyle.Sizes.sideBarContentWidth
        wrapMode: Text.WordWrap
        textFormat: Text.StyledText
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        color: EaStyle.Colors.themeForeground
        linkColor: EaStyle.Colors.themeAccent
        text: (group.shows === "parallelFits" ? qsTr("Parallel fits: %1").arg(Preferences.scanWorkersApplied) : qsTr("Threads per calculation: %1").arg(group.threads)) + ` (<a href="preferences">${qsTr("Preferences")}</a>)`
        onLinkActivated: Preferences.openPerformance()

        HoverHandler {
            cursorShape: parent.hoveredLink !== "" ? Qt.PointingHandCursor : Qt.ArrowCursor
        }
    }
}
