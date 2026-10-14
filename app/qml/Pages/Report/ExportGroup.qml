// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Saving the report, the sidebar's top group (edi ADR-0036 §7): one row per format, its box and its report's path, the
// interactive HTML with whether it embeds plotly.js and three.js (online by default) on its own row under it, then the
// static PDF (A4, the preview's figures as images) and the CIF report (disabled until its writer exists); one Save
// report button below, which writes the ticked formats into the project's reports/ folder (in the browser it also
// downloads them, one file or one zip).
EaElements.GroupBox {
    id: group

    property ReportViewModel report: null
    // The preview, whose figures the PDF shows.
    property ReportPreview preview: null

    // A save asked for while the project calculates, made when the calculation ends.
    property bool savePending: false

    // Writes the ticked formats; with the PDF ticked, once the preview's figures are grabbed. While the project
    // calculates, the report is not yet its outcome, so the save waits for it.
    function saveReport() {
        const report = group.report;
        if (report.calculating) {
            group.savePending = true;
            return;
        }
        group.savePending = false;
        if (report.writesPdf)
            group.preview.grabFigures(figures => report.saveReport(figures, EaStyle.Fonts.fontFamily));
        else
            report.saveReport({}, EaStyle.Fonts.fontFamily);
    }

    // In the browser Save report also downloads the files, and a saved file lasts until the page is reloaded.
    readonly property bool inBrowser: WebFiles.available

    // The format boxes share one width, so the path fields line up.
    readonly property real boxWidth: Math.max(htmlBox.implicitWidth, pdfBox.implicitWidth, cifBox.implicitWidth)

    // A format's saved report, its row of savedReports, or null before the first save.
    function savedRow(format) {
        const rows = group.report ? group.report.savedReports : [];
        for (const row of rows) {
            if (row.format === format)
                return row;
        }
        return null;
    }

    // A format's report path, read-only: normal when the saved file is current, red when the project changed since
    // or the file is gone, "not saved yet" before the first save; the saved time as its tooltip; dimmed while its
    // format is unticked, and disabled with its box. In the browser a file is gone only after a reload, and reads as
    // not saved then.
    component ReportPath: EaElements.TextField {
        id: path

        required property string format
        required property EaElements.CheckBox box
        readonly property var saved: group.savedRow(format)
        readonly property bool shown: saved !== null && !(group.inBrowser && saved.state === "missing")

        objectName: "report.path." + format
        width: EaStyle.Sizes.sideBarContentWidth - group.boxWidth - EaStyle.Sizes.fontPixelSize
        readOnly: true
        horizontalAlignment: TextInput.AlignLeft
        enabled: box.enabled
        opacity: box.checked ? 1 : 0.5
        text: shown ? "reports/" + saved.name : ""
        placeholderText: qsTr("not saved yet")
        color: shown && saved.state !== "current" ? EaStyle.Colors.red : EaStyle.Colors.themeForeground
        ToolTip.text: shown ? (group.inBrowser ? qsTr("Downloaded at %1") : qsTr("Saved %1")).arg(saved.saved) : ""
    }

    objectName: "group.reportExport"
    title: qsTr("Export")
    icon: "download"
    collapsed: false
    last: SideBarGroups.isLast(group)

    Column {
        spacing: AppSizes.groupContentSpacing

        // One row per format: its box, then the report's path in the project folder (the owner, 2026-10-14).
        Row {
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.CheckBox {
                id: htmlBox

                anchors.verticalCenter: parent.verticalCenter
                objectName: "report.writesHtml"
                width: group.boxWidth
                enabled: group.report !== null
                text: qsTr("HTML")
                checked: group.report ? group.report.writesHtml : false
                onToggled: group.report.writesHtml = checked
                ToolTip.text: qsTr("Save the report as one HTML file with interactive charts")
            }
            ReportPath {
                format: "html"
                box: htmlBox
            }
        }
        // Whether the HTML carries its chart libraries, on its own row under HTML.
        EaElements.CheckBox {
            objectName: "report.embedLibraries"
            width: EaStyle.Sizes.sideBarContentWidth
            enabled: group.report !== null && group.report.writesHtml
            text: qsTr("Embed the chart libraries in the HTML (works offline)")
            checked: group.report ? group.report.embedLibraries : false
            onToggled: group.report.embedLibraries = checked
            ToolTip.text: qsTr("Include plotly.js and three.js in the HTML file, so the report opens offline")
        }
        Row {
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.CheckBox {
                id: pdfBox

                anchors.verticalCenter: parent.verticalCenter
                objectName: "report.writesPdf"
                width: group.boxWidth
                enabled: group.report !== null && group.preview !== null
                text: qsTr("PDF")
                checked: group.report ? group.report.writesPdf : false
                onToggled: group.report.writesPdf = checked
                ToolTip.text: qsTr("Save the report as a PDF on A4 pages, its charts as images")
            }
            ReportPath {
                format: "pdf"
                box: pdfBox
            }
        }
        Row {
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.CheckBox {
                id: cifBox

                anchors.verticalCenter: parent.verticalCenter
                objectName: "report.writesCif"
                width: group.boxWidth
                enabled: false
                text: qsTr("CIF")
                checked: group.report ? group.report.writesCif : false
                ToolTip.text: qsTr("The CIF report is not available yet")
            }
            ReportPath {
                format: "cif"
                box: cifBox
            }
        }

        EaElements.SideBarButton {
            objectName: "report.save"
            enabled: group.report !== null && !group.savePending && (group.report.writesHtml || group.report.writesPdf)
            fontIcon: "download"
            text: qsTr("Save report")
            ToolTip.text: group.inBrowser ? qsTr("Download the ticked formats, one file or one zip of them") : qsTr("Write the ticked formats into the project's reports folder")
            onClicked: group.saveReport()
        }
    }

    // A report that could not be saved says why, as a project that could not.
    Connections {
        target: group.report
        function onCalculatingChanged() {
            if (group.savePending && !group.report.calculating)
                group.saveReport();
        }
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
