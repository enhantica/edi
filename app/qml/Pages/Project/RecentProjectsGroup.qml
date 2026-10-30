// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

EaElements.GroupBox {
    objectName: "group.recentProjects"
    title: qsTr("Recent projects")
    icon: "archive"
    onVisibleChanged: ApplicationInfo.finishUiEvent(13, undefined)
    onCollapsedChanged: ApplicationInfo.finishUiEvent(14, undefined)

    Column {
        DataTable {
            id: table
            objectName: "recentProjects.list"
            defaultInfoText: qsTr("No recent projects")
            sourceModel: RecentProjects.rows
            // The status is icons only, so it sits by the remove buttons (the owner, 2026-10-27).
            columns: [numberColumnWidth, -1, AppSizes.iconOnlyColumnWidth, AppSizes.iconColumnWidth]
            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    text: WebFiles.available ? qsTr("Project") : qsTr("Project directory")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("Status")
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
