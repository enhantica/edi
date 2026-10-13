// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Saving the report, the sidebar's top group (edi ADR-0035 §7): two boxes per row, the interactive HTML and whether it
// embeds plotly.js and three.js (online by default), then the static PDF (A4, the preview's figures as images) and the
// CIF report (disabled until its writer exists); one Save report button, which writes the ticked formats into the
// project's reports/ folder; and the reports saved so far, each marked when the project has changed since.
EaElements.GroupBox {
    id: group

    property ReportViewModel report: null
    // The preview, whose figures the PDF shows.
    property ReportPreview preview: null

    // Writes the ticked formats; with the PDF ticked, once the preview's figures are grabbed.
    function saveReport() {
        const report = group.report;
        if (report.writesPdf)
            group.preview.grabFigures(figures => report.saveReport(figures, EaStyle.Fonts.fontFamily));
        else
            report.saveReport({}, EaStyle.Fonts.fontFamily);
    }

    objectName: "group.reportExport"
    title: qsTr("Export")
    icon: "download"
    collapsed: false
    last: SideBarGroups.isLast(group)

    Column {
        spacing: AppSizes.groupContentSpacing

        Grid {
            columns: 2
            columnSpacing: EaStyle.Sizes.fontPixelSize
            rowSpacing: AppSizes.groupContentSpacing

            EaElements.CheckBox {
                objectName: "report.writesHtml"
                enabled: group.report !== null
                text: qsTr("HTML")
                checked: group.report ? group.report.writesHtml : false
                onToggled: group.report.writesHtml = checked
                ToolTip.text: qsTr("Save the report as one HTML file with interactive charts")
            }
            EaElements.CheckBox {
                objectName: "report.embedLibraries"
                enabled: group.report !== null && group.report.writesHtml
                text: qsTr("Embed the chart libraries")
                checked: group.report ? group.report.embedLibraries : false
                onToggled: group.report.embedLibraries = checked
                ToolTip.text: qsTr("Include plotly.js and three.js in the file, so the report opens offline")
            }
            EaElements.CheckBox {
                objectName: "report.writesPdf"
                enabled: group.report !== null && group.preview !== null
                text: qsTr("PDF")
                checked: group.report ? group.report.writesPdf : false
                onToggled: group.report.writesPdf = checked
                ToolTip.text: qsTr("Save the report as a PDF on A4 pages, its charts as images")
            }
            EaElements.CheckBox {
                objectName: "report.writesCif"
                enabled: false
                text: qsTr("CIF")
                checked: group.report ? group.report.writesCif : false
                ToolTip.text: qsTr("The CIF report is not available yet")
            }
        }

        EaElements.SideBarButton {
            objectName: "report.save"
            enabled: group.report !== null && (group.report.writesHtml || group.report.writesPdf)
            fontIcon: "download"
            text: qsTr("Save report")
            ToolTip.text: qsTr("Write the ticked formats into the project's reports folder")
            onClicked: group.saveReport()
        }

        // The reports saved so far, each with when it was written and whether the project has changed since.
        Repeater {
            model: group.report ? group.report.savedReports : []
            delegate: EaElements.Label {
                required property var modelData

                objectName: "report.saved." + modelData.name
                width: EaStyle.Sizes.sideBarContentWidth
                elide: Text.ElideMiddle
                color: modelData.state === "current" ? EaStyle.Colors.themeForeground : EaStyle.Colors.orange
                text: modelData.state === "current" ? qsTr("%1 · %2").arg(modelData.name).arg(modelData.saved) : qsTr("%1 · %2 · %3").arg(modelData.name).arg(modelData.saved).arg(modelData.state === "missing" ? qsTr("missing") : qsTr("out of date"))
            }
        }
    }

    // A report that could not be saved says why, as a project that could not.
    Connections {
        target: group.report
        function onSaveFailed(message) {
            saveError.message = message;
            saveError.open();
        }
    }
    AppDialog {
        id: saveError
        objectName: "report.saveError"
        property string message: ""
        title: qsTr("The report was not saved")
        standardButtons: Dialog.Ok
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: saveErrorText.implicitHeight

        EaElements.Label {
            id: saveErrorText
            width: saveError.contentWidth
            wrapMode: Text.Wrap
            text: saveError.message
        }
    }
}
