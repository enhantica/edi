// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A page's pattern chart options (edi ADR-0031 §2), kept in the app's settings under the page's name: the y scale and,
// on the Experiment page, the x axis (the Analysis chart's x axis is the project's own, on its chart's toolbar).
EaElements.GroupBox {
    id: group

    // "analysis" or "experiment".
    property string page: ""
    readonly property string openKey: "Settings:chart:" + page
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
            currentIndex: Math.max(0, group.scaleTokens.indexOf(group.page === "analysis" ? Preferences.analysisYScale : Preferences.experimentYScale))
            onActivated: index => {
                if (group.page === "analysis")
                    Preferences.analysisYScale = group.scaleTokens[index];
                else
                    Preferences.experimentYScale = group.scaleTokens[index];
            }
        }
        EaElements.ComboBox {
            objectName: "settings.chart.xAxis"
            visible: group.page === "experiment"
            width: EaStyle.Sizes.sideBarContentWidth
            model: [qsTr("x: the experiment's own"), qsTr("x: d-spacing")]
            currentIndex: Preferences.experimentXAxis === "d_spacing" ? 1 : 0
            onActivated: index => Preferences.experimentXAxis = index === 1 ? "d_spacing" : "native"
        }
    }
}
