// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// What the report holds besides what it always does (the owner, 2026-10-13): a box for each optional group, the
// charts, the correlations, the reflections, the measured data and, for a scan, the evolution. The correlation level
// and the x axis come from the Analysis page.
EaElements.GroupBox {
    id: group

    // Only the top group opens on first view, as on the other pages; each remembers its state.
    readonly property string openKey: "Main:reportContents"
    property ReportViewModel report: null
    readonly property var items: report && report.model.contents ? report.model.contents : []
    readonly property var hidden: report ? report.hidden : []

    objectName: "group.reportContents"
    title: qsTr("Contents")
    icon: "list"
    collapsed: !SideBarGroups.isOpen(openKey)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed)
    last: SideBarGroups.isLast(group)
    enabled: report !== null

    Column {
        spacing: AppSizes.groupContentSpacing

        Repeater {
            model: group.items.length
            delegate: EaElements.CheckBox {
                required property int index
                readonly property var item: group.items[index]

                objectName: "report.contents." + item.key
                width: EaStyle.Sizes.sideBarContentWidth
                text: item.title
                checked: group.hidden.indexOf(item.key) < 0
                onToggled: group.report.setIncluded(item.key, checked)
            }
        }
    }
}
