// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Elements as EaElements

import edi.app

// The report's export (the owner's note 31): Save HTML report and Open in browser (the HTML report, next), Save CIF
// report (waits for the CIF report), and whether a saved report embeds plotly.js and three.js (online by default; the
// owner, 2026-10-12).
EaElements.GroupBox {
    id: group

    property ReportViewModel report: null

    objectName: "group.reportExport"
    title: qsTr("Export")
    icon: "download"
    collapsed: false
    last: SideBarGroups.isLast(group)

    Column {
        spacing: AppSizes.groupContentSpacing

        Grid {
            columns: 2
            spacing: AppSizes.inputSpacing

            EaElements.SideBarButton {
                objectName: "report.saveHtml"
                enabled: false
                fontIcon: "file-code"
                text: qsTr("Save HTML report")
                ToolTip.text: qsTr("Not available yet")
            }
            EaElements.SideBarButton {
                objectName: "report.openInBrowser"
                enabled: false
                fontIcon: "external-link-alt"
                text: qsTr("Open in browser")
                ToolTip.text: qsTr("Not available yet")
            }
            EaElements.SideBarButton {
                objectName: "report.saveCif"
                enabled: false
                fontIcon: "file-alt"
                text: qsTr("Save CIF report")
                ToolTip.text: qsTr("The CIF report is not available yet")
            }
        }
        EaElements.CheckBox {
            objectName: "report.embedLibraries"
            enabled: group.report !== null
            text: qsTr("Embed the chart libraries, to open the report offline")
            checked: group.report ? group.report.embedLibraries : false
            onToggled: group.report.embedLibraries = checked
        }
    }
}
