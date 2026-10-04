// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

// Export summary (easydiffractionbeta Pages/Summary/SideBarBasic/ExportReportGroup.qml): disabled until
// export arrives with the report task.
EaElements.GroupBox {
    objectName: "group.exportSummary"
    title: qsTr("Export summary")
    icon: "download"
    collapsible: false
    enabled: false

    EaElements.SideBarButton {
        objectName: "report.export"
        wide: true
        fontIcon: "download"
        text: qsTr("Export")
    }
}
