// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Saving the report, the sidebar's top group (edi ADR-0036 §7): one row per format in the sidebar's left half, its box
// and its report's path, the interactive HTML with whether it embeds plotly.js and three.js (online by default) in the
// right half of its row (the owner, 2026-10-27), then the static PDF (A4, the preview's figures as images) and the CIF report (every item under its official CIF name); one
// Save report button below, which writes the ticked formats into the project's reports/ folder (in the browser it also
// downloads them, one file or one zip).
EaElements.GroupBox {
    id: group

    property ReportViewModel report: null
    // The preview, whose figures the PDF shows.
    property ReportPreview preview: null
    // Whether the group is on screen; the saved reports' states build the report, so a hidden group reads none.
    property bool shown: true

    // A save asked for while the project calculates, made when the calculation ends.
    property bool savePending: false
    // A save under way, from its start until its files are written or refused. The page keeps the report built and
    // the preview's figures drawn meanwhile, even when another page is shown: a PDF takes those figures.
    property bool saving: false
    // A save asked for before the project had a place of its own, made once Save as gives it one.
    property bool afterSaveAs: false

    // Writes the ticked formats; with the PDF ticked, once the preview's figures are grabbed. While the project
    // calculates, the report is not yet its outcome, so the save waits for it.
    function saveReport() {
        ApplicationInfo.saveReportPreview();
    }

    // In the browser Save report also downloads the files, and a saved file lasts until the page is reloaded.
    readonly property bool inBrowser: WebFiles.available

    // The format rows take the sidebar's left half; the embed option the right half of the HTML row.
    readonly property real halfWidth: (EaStyle.Sizes.sideBarContentWidth - EaStyle.Sizes.fontPixelSize) / 2
    // The format boxes share one width, so the path fields line up.
    readonly property real boxWidth: Math.max(htmlBox.implicitWidth, pdfBox.implicitWidth, cifBox.implicitWidth)

    // The row of savedReports for the file Save report would write in a format now, by its name, or null when that
    // file has not been saved (before the first save, or after the project is renamed). Rows of other names keep
    // their files.
    function savedRow(format) {
        return ApplicationInfo.savedReportRow(format);
    }

    // A format's report path, read-only: normal when the saved file is current, red when the project changed since
    // or the file is gone, "not saved yet" before the first save; the saved time as its tooltip; dimmed while its
    // format is unticked, and disabled with its box. In the browser it is the file's name alone, as downloaded, and a
    // file is gone only after a reload, and reads as not saved then.
    component ReportPath: EaElements.TextField {
        id: path

        required property string format
        required property EaElements.CheckBox box
        readonly property var saved: group.savedRow(format)
        readonly property bool shown: saved !== null && !(group.inBrowser && saved.state === "missing")

        objectName: "report.path." + format
        width: group.halfWidth - group.boxWidth - EaStyle.Sizes.fontPixelSize
        readOnly: true
        horizontalAlignment: TextInput.AlignLeft
        enabled: box.enabled
        opacity: box.checked ? 1 : 0.5
        text: shown ? (group.inBrowser ? saved.name : "reports/" + saved.name) : ""
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
                leftPadding: 0
                objectName: "report.writesHtml"
                width: group.boxWidth
                enabled: group.report !== null
                text: Session.label("report.html")
                checked: group.report ? group.report.writesHtml : false
                onToggled: group.report.writesHtml = checked
                ToolTip.text: qsTr("Save the report as one HTML file with interactive charts")
            }
            ReportPath {
                format: "html"
                box: htmlBox
            }
            // Whether the HTML carries its chart libraries, on one line: shortened, never wrapped, where the half
            // is too narrow for the whole label.
            EaElements.CheckBox {
                id: embedBox

                readonly property string longText: qsTr("Embed the chart libraries (works offline)")

                anchors.verticalCenter: parent.verticalCenter
                objectName: "report.embedLibraries"
                width: group.halfWidth
                leftPadding: 0
                enabled: group.report !== null && group.report.writesHtml
                text: embedMetrics.advanceWidth(longText) + embedBox.indicator.width + embedBox.spacing <= width ? longText : qsTr("Embed chart libraries (offline)")
                checked: group.report ? group.report.embedLibraries : false
                onToggled: group.report.embedLibraries = checked
                ToolTip.text: qsTr("Include plotly.js and three.js in the HTML file, so the report opens offline")

                FontMetrics {
                    id: embedMetrics
                    font: embedBox.font
                }
            }
        }
        Row {
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.CheckBox {
                id: pdfBox

                anchors.verticalCenter: parent.verticalCenter
                leftPadding: 0
                objectName: "report.writesPdf"
                width: group.boxWidth
                enabled: group.report !== null && group.preview !== null
                text: Session.label("report.pdf")
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
                leftPadding: 0
                objectName: "report.writesCif"
                width: group.boxWidth
                enabled: group.report !== null
                text: Session.label("report.cif")
                checked: group.report ? group.report.writesCif : false
                onToggled: group.report.writesCif = checked
                ToolTip.text: qsTr("Save the report as a CIF, every item under its official CIF name")
            }
            ReportPath {
                format: "cif"
                box: cifBox
            }
        }

        // As wide as the sidebar, the boxes above starting at its left edge (the owner, 2026-10-14).
        EaElements.SideBarButton {
            objectName: "report.save"
            wide: true
            enabled: group.report !== null && !group.savePending && !group.saving && (group.report.writesHtml || group.report.writesPdf || group.report.writesCif)
            fontIcon: "download"
            text: qsTr("Save report")
            ToolTip.text: group.inBrowser ? qsTr("Download the ticked formats, one file or one zip of them") : qsTr("Write the ticked formats into the project's reports folder, inside its .zip when it is one")
            onClicked: group.saveReport()
        }
    }

    // A report that could not be saved says why, as a project that could not.
    Connections {
        target: Session
        function onNeedsSaveAsChanged() {
            ApplicationInfo.reportExportChanged(0);
        }
        function onProjectChanged() {
            ApplicationInfo.reportExportChanged(1);
        }
    }
    Connections {
        target: group.report
        function onCalculatingChanged() {
            ApplicationInfo.reportExportChanged(2);
        }
        function onSaveFailed(message) {
            ApplicationInfo.reportExportFailure(message);
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
