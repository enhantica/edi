// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The pattern chart's options (edi ADR-0031 §2), one set for the one chart every page shows: the y scale, kept in the
// app's settings, and the x axis, the project's own (which the report follows too).
EaElements.GroupBox {
    id: group

    readonly property string openKey: "Settings:chart:pattern"
    readonly property var scaleTokens: ["linear", "sqrt", "log"]

    objectName: "group.chartSettings"
    collapsed: !SideBarGroups.isOpen(openKey)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed)
    last: SideBarGroups.isLast(group)
    title: qsTr("Pattern chart")
    icon: "chart-area"

    Column {
        spacing: AppSizes.groupContentSpacing

        EaElements.ComboBox {
            objectName: "settings.chart.yScale"
            width: EaStyle.Sizes.sideBarContentWidth
            model: [qsTr("y: linear"), qsTr("y: square root"), qsTr("y: log")]
            currentIndex: Math.max(0, group.scaleTokens.indexOf(Preferences.patternYScale))
            onActivated: index => Preferences.patternYScale = group.scaleTokens[index]
        }
        EaElements.ComboBox {
            objectName: "settings.chart.xAxis"
            enabled: Session.project !== null
            width: EaStyle.Sizes.sideBarContentWidth
            model: [qsTr("x: the experiment's own"), qsTr("x: d-spacing")]
            currentIndex: Session.project && Session.project.patternDSpacing ? 1 : 0
            onActivated: index => {
                if (Session.project)
                    Session.project.patternDSpacing = index === 1;
            }
        }
    }
}
