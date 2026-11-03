// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

SideBarGroup {
    id: group
    objectName: "group.recentProjects"
    title: qsTr("Recent projects")
    icon: "archive"
    onVisibleChanged: ApplicationInfo.finishUiEvent(13, undefined)
    onCollapsedChanged: ApplicationInfo.finishUiEvent(14, undefined)

    // The sidebar column the group sits in, found from its parents: the table takes the room left under the groups
    // above it, as the Examples table fills the sidebar, and the column scrolls past that.
    property Flickable column: null
    function findColumn() {
        for (let item = parent; item; item = item.parent)
            if (item instanceof Flickable)
                return item;
        return null;
    }
    onParentChanged: column = findColumn()
    Component.onCompleted: column = findColumn()

    Column {
        DataTable {
            id: table

            property real spareHeight: 0

            // From the column's height and where the table starts in it, never from the table's own height, so a
            // new row count cannot move the room it was taken from (as the single-crystal reflection table).
            function place() {
                if (!group.column || !group.column.contentItem || group.collapsed)
                    return;
                const top = mapToItem(group.column.contentItem, 0, 0).y;
                spareHeight = Math.floor(group.column.height - top - group.bottomPadding - EaStyle.Sizes.fontPixelSize);
            }

            objectName: "recentProjects.list"
            maxRowCountShow: spareHeight > 0 ? Math.max(3, Math.floor((spareHeight - (headerItem ? headerItem.height : 0)) / tableRowHeight - 0.5)) : EaStyle.Sizes.tableMaxRowCountShow
            Component.onCompleted: Qt.callLater(place)
            Connections {
                target: group.column
                function onHeightChanged() {
                    table.place();
                }
                function onContentHeightChanged() {
                    Qt.callLater(table.place);
                }
            }
            Connections {
                target: group
                function onCollapsedChanged() {
                    Qt.callLater(table.place);
                }
            }
            defaultInfoText: qsTr("No recent projects")
            sourceModel: RecentProjects.rows
            // The status is icons only, so it sits by the remove buttons (the owner, 2026-10-27).
            columns: [numberColumnWidth, -1, AppSizes.iconOnlyColumnWidth, AppSizes.iconColumnWidth]
            // The path takes all the width between the number and the status, so it is cut only when it does not fit
            // the row, whatever its first measure (the owner, 2026-11-02).
            spreadColumns: [1]
            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    text: WebFiles.available ? qsTr("Project") : qsTr("Project directory")
                    horizontalAlignment: Text.AlignLeft
                }
                // No title: the icons say found or missing in their tooltips.
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
            }
            delegate: TableRow {
                id: row
                required property string path
                required property string label
                required property bool inBrowser
                required property bool available

                MouseArea {
                    parent: row
                    height: row.height
                    width: row.width - AppSizes.iconColumnWidth - table.rowPadding - EaStyle.Sizes.tableColumnSpacing
                    cursorShape: row.available ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: ApplicationInfo.openProjectRow(true, true)
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    marksCurrentRow: true
                    text: row.index + 1
                }
                EaComponents.ListViewLabel {
                    objectName: `recentProjects.path.${row.index}`
                    text: row.label
                    horizontalAlignment: Text.AlignLeft
                    // Cut at the start, so the project's own folder at the end stays readable; the tooltip has it all.
                    elide: Text.ElideLeft
                    ToolTip.text: row.label
                }
                // Found or missing on disk as an icon, the word in its tooltip, as the experiments' fit column.
                IconCell {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `recentProjects.status.${row.index}`
                    icon: row.available ? FitOutcomes.icon("success") : "exclamation-triangle"
                    iconColor: String(row.available ? EaStyle.Colors.green : EaStyle.Colors.red)
                    toolTip: row.available ? qsTr("Found") : qsTr("Missing")
                }
                EaComponents.ListViewButton {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `recentProjects.remove.${row.index}`
                    fontIcon: "minus-circle"
                    ToolTip.text: row.inBrowser ? qsTr("Delete from this browser") : qsTr("Remove from recent projects")
                    onClicked: RecentProjects.forget(row.index)
                }
            }
        }
    }
}
