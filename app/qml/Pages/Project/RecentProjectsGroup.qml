// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// Recent projects (easydiffractionbeta Pages/Project/SideBarBasic/Recent.qml): shown empty until the
// settings façade exists (ADR-0006 pt 2, E06).
EaElements.GroupBox {
    icon: "archive"
    objectName: "group.recentProjects"
    title: qsTr("Recent projects")

    // A Column gives the group its content height (a ListView has no implicit height).
    Column {
        DataTable {
            columnWidths: [-1]
            defaultInfoText: qsTr("No recent projects")
            model: 0

            header: EaComponents.ListViewHeader {
                implicitHeight: 0
                visible: false

                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("path")
                }
            }
        }
    }
}
