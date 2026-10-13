// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The report's charts (the owner's note 31): which experiments are drawn, the x axis (2θ or TOF, or d), the residual
// and the Bragg ticks.
EaElements.GroupBox {
    id: group

    // Only the top group opens on first view, as on the other pages; each remembers its state.
    readonly property string openKey: "Main:reportCharts"
    property ReportViewModel report: null
    readonly property var ids: report && report.model.experiment_ids ? report.model.experiment_ids : []

    function toggle(id, on) {
        // An empty choice means every experiment.
        let chosen = group.report.experiments.length > 0 ? group.report.experiments.slice() : group.ids.slice();
        chosen = chosen.filter(shown => shown !== id);
        if (on)
            chosen.push(id);
        group.report.experiments = chosen.length === group.ids.length ? [] : chosen;
    }

    objectName: "group.reportCharts"
    title: qsTr("Charts")
    icon: "chart-line"
    collapsed: !SideBarGroups.isOpen(openKey)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed)
    last: SideBarGroups.isLast(group)
    enabled: report !== null

    Column {
        spacing: AppSizes.groupContentSpacing

        Grid {
            columns: 2
            columnSpacing: EaStyle.Sizes.fontPixelSize
            rowSpacing: 0
            Repeater {
                model: group.ids.length
                delegate: EaElements.CheckBox {
                    required property int index
                    objectName: "report.chart.experiment." + index
                    width: (EaStyle.Sizes.sideBarContentWidth - EaStyle.Sizes.fontPixelSize) / 2
                    text: group.ids[index]
                    checked: group.report ? group.report.experiments.length === 0 || group.report.experiments.indexOf(group.ids[index]) >= 0 : true
                    onToggled: group.toggle(group.ids[index], checked)
                }
            }
        }
        EaElements.GroupRow {
            spacing: AppSizes.inputSpacing
            EaElements.ComboBox {
                objectName: "report.xAxis"
                width: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.inputSpacing) / 3
                model: [qsTr("x: 2θ or TOF"), qsTr("x: d-spacing")]
                currentIndex: group.report && group.report.dSpacing ? 1 : 0
                onActivated: index => group.report.dSpacing = index === 1
            }
            EaElements.CheckBox {
                objectName: "report.residual"
                width: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.inputSpacing) / 3
                text: qsTr("Residual")
                checked: group.report ? group.report.residual : true
                onToggled: group.report.residual = checked
            }
            EaElements.CheckBox {
                objectName: "report.braggTicks"
                width: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.inputSpacing) / 3
                text: qsTr("Bragg ticks")
                checked: group.report ? group.report.braggTicks : true
                onToggled: group.report.braggTicks = checked
            }
        }
    }
}
