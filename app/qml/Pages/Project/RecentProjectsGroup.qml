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
    onVisibleChanged: if (visible)
        RecentProjects.refresh()
    onCollapsedChanged: if (!collapsed)
        RecentProjects.refresh()

    Column {
        DataTable {
            objectName: "recentProjects.list"
            defaultInfoText: qsTr("No recent projects")
            sourceModel: RecentProjects.rows
            columnWidths: [numberColumnWidth, -1, EaStyle.Sizes.fontPixelSize * 4.5, AppSizes.iconColumnWidth]
            header: EaComponents.ListViewHeader {
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.TableViewLabel {
                    text: qsTr("Project directory")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("Status")
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
            }
            delegate: EaComponents.ListViewDelegate {
                id: row
                required property int index
                required property string path
                required property bool available

                TapHandler {
                    onTapped: {
                        if (row.available)
                            Session.openProject(Session.projectDirectoryUrl(row.path));
                    }
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: row.index + 1
                    color: EaStyle.Colors.themeForegroundMinor
                }
                EaComponents.TableViewLabel {
                    objectName: `recentProjects.path.${row.index}`
                    text: row.path
                    horizontalAlignment: Text.AlignLeft
                    ToolTip.text: row.path
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `recentProjects.status.${row.index}`
                    text: row.available ? qsTr("Found") : qsTr("Missing")
                    color: row.available ? EaStyle.Colors.themeForegroundMinor : EaStyle.Colors.red
                }
                EaComponents.TableViewButton {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `recentProjects.remove.${row.index}`
                    fontIcon: "minus-circle"
                    ToolTip.text: qsTr("Remove from recent projects")
                    onClicked: RecentProjects.forget(row.index)
                }
            }
        }
    }
}
