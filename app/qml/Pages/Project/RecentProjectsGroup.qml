// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

// Recent projects (easydiffractionbeta Pages/Project/SideBarBasic/Recent.qml): shown empty until the
// settings façade exists (ADR-0006 pt 2, E06).
EaElements.GroupBox {
    objectName: "group.recentProjects"
    title: qsTr("Recent projects")
    icon: "archive"

    // A Column gives the group its content height (a ListView has no implicit height).
    Column {
        EaComponents.TableView {
            showHeader: false
            defaultInfoText: qsTr("No recent projects")
            model: 0

            header: EaComponents.TableViewHeader {
                EaComponents.TableViewLabel {
                    flexibleWidth: true
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("path")
                }
            }
        }
    }
}
