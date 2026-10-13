// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// What the report holds, as its tree (the owner, 2026-10-13): the sections; under Analysis its categories; under
// Structures and Experiments each block and its categories; then Correlations and, for a scan, Evolution. Each box
// leaves its item out of the report with everything under it; a box under one left out is disabled. The correlation
// level and the x axis come from the Analysis page.
EaElements.GroupBox {
    id: group

    // Only the top group opens on first view, as on the other pages; each remembers its state.
    readonly property string openKey: "Main:reportContents"
    property ReportViewModel report: null
    readonly property var items: report && report.model.contents ? report.model.contents : []
    readonly property var hidden: report ? report.hidden : []

    // Whether the item above `index` (the last one before it a level up) is in the report.
    function parentIncluded(index: int): bool {
        const depth = items[index].depth;
        for (let i = index - 1; i >= 0; --i) {
            if (items[i].depth < depth)
                return items[i].included;
        }
        return true;
    }

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
                leftPadding: padding + item.depth * EaStyle.Sizes.fontPixelSize * 1.5
                width: EaStyle.Sizes.sideBarContentWidth
                enabled: group.parentIncluded(index)
                text: item.title
                checked: group.hidden.indexOf(item.key) < 0
                onToggled: group.report.setIncluded(item.key, checked)
            }
        }
    }
}
