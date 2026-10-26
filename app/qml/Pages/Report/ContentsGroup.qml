// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// What the report holds besides what it always does (the owner, 2026-10-13): a box for each optional group, the
// charts, the correlations, the reflections, the data (left out by default) and, for a scan, the evolution. The
// correlation level and the x axis come from the Analysis page.
EaElements.GroupBox {
    id: group

    // Only the top group opens on first view, as on the other pages; each remembers its state.
    readonly property string openKey: "Main:reportContents"
    property ReportViewModel report: null
    // Whether the group is on screen; reading the model builds the report, so a hidden group reads nothing.
    property bool shown: true
    readonly property var items: report && shown && report.model.contents ? report.model.contents : []
    readonly property var hidden: report ? report.hidden : []

    objectName: "group.reportContents"
    title: qsTr("Contents")
    icon: "list"
    collapsed: !SideBarGroups.isOpen(openKey, group)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed, group)
    last: SideBarGroups.isLast(group)
    enabled: report !== null

    Column {
        spacing: AppSizes.groupContentSpacing

        // The list itself is the model, so a delegate holds its own item while a shorter list replaces it.
        Repeater {
            model: group.items
            delegate: EaElements.CheckBox {
                required property var modelData

                objectName: "report.contents." + modelData.key
                width: EaStyle.Sizes.sideBarContentWidth
                text: modelData.title
                checked: group.hidden.indexOf(modelData.key) < 0
                onToggled: group.report.setIncluded(modelData.key, checked)
            }
        }
    }
}
