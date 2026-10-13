// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Saving the report, the sidebar's top group (the owner, 2026-10-13): the interactive HTML with, beside it, whether it
// embeds plotly.js and three.js (online by default); below it the static PDF and the CIF report (waits for the CIF
// report task). Each is disabled until its writer exists.
EaElements.GroupBox {
    id: group

    property ReportViewModel report: null

    objectName: "group.reportExport"
    title: qsTr("Export")
    icon: "download"
    collapsed: false
    last: SideBarGroups.isLast(group)

    // One column of buttons at the sidebar buttons' own size and spacing, as the Project page's Get started has them
    // (the owner, 2026-10-13), the Embed checkbox beside the first.
    Column {
        spacing: EaStyle.Sizes.fontPixelSize

        Row {
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.SideBarButton {
                id: saveHtml
                objectName: "report.saveHtml"
                enabled: false
                fontIcon: "file-code"
                text: qsTr("Save interactive HTML")
                ToolTip.text: qsTr("Not available yet")
            }
            EaElements.CheckBox {
                objectName: "report.embedLibraries"
                anchors.verticalCenter: saveHtml.verticalCenter
                enabled: group.report !== null
                text: qsTr("Embed the chart libraries")
                checked: group.report ? group.report.embedLibraries : false
                onToggled: group.report.embedLibraries = checked
                ToolTip.text: qsTr("Include plotly.js and three.js in the file, so the report opens offline")
            }
        }
        EaElements.SideBarButton {
            objectName: "report.savePdf"
            enabled: false
            fontIcon: "file-pdf"
            text: qsTr("Save static PDF")
            ToolTip.text: qsTr("Not available yet")
        }
        EaElements.SideBarButton {
            objectName: "report.saveCif"
            enabled: false
            fontIcon: "file-alt"
            text: qsTr("Save static CIF")
            ToolTip.text: qsTr("The CIF report is not available yet")
        }
    }
}
