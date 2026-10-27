// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Saving the report, the sidebar's top group (edi ADR-0036 §7): one row per format, its box and its report's path, the
// interactive HTML with whether it embeds plotly.js and three.js (online by default) on its own row under it, then the
// static PDF (A4, the preview's figures as images) and the CIF report (every item under its official CIF name); one
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
        const report = group.report;
        // A project that cannot be written back (an example, a read-only .zip) asks where to keep it first, as Save
        // does; its report is saved once it has a place (the owner, 2026-10-27).
        if (!group.inBrowser && Session.needsSaveAs) {
            group.afterSaveAs = true;
            AppState.saveAsRequested();
            return;
        }
        if (report.calculating) {
            group.savePending = true;
            return;
        }
        // First, so the report is rebuilt from the calculation's outcome and the preview drawn before its figures
        // are grabbed; a save that waited may run after its page was left.
        group.saving = true;
        group.savePending = false;
        const write = () => {
            try {
                report.saveReport(EaStyle.Fonts.fontFamily);
                const refusal = Session.writeBackReports();
                if (refusal !== "") {
                    saveError.message = refusal;
                    saveError.open();
                }
            } finally {
                group.saving = false;
            }
        };
        if (report.writesPdf)
            group.preview.grabFigures(figures => {
                for (const name in figures)
                    report.setFigure(name, figures[name]);
                write();
            });
        else
            write();
    }

    // In the browser Save report also downloads the files, and a saved file lasts until the page is reloaded.
    readonly property bool inBrowser: WebFiles.available

    // The format boxes share one width, so the path fields line up.
    readonly property real boxWidth: Math.max(htmlBox.implicitWidth, pdfBox.implicitWidth, cifBox.implicitWidth)

    // The row of savedReports for the file Save report would write in a format now, by its name, or null when that
    // file has not been saved (before the first save, or after the project is renamed). Rows of other names keep
    // their files.
    function savedRow(format) {
        if (!group.report || !group.shown)
            return null;
        const name = group.report.fileStem + "." + format;
        for (const row of group.report.savedReports) {
            if (row.name === name && row.format === format)
                return row;
        }
        return null;
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
        width: EaStyle.Sizes.sideBarContentWidth - group.boxWidth - EaStyle.Sizes.fontPixelSize
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
        }
        // Whether the HTML carries its chart libraries, on its own row under HTML.
        EaElements.CheckBox {
            objectName: "report.embedLibraries"
            width: EaStyle.Sizes.sideBarContentWidth
            leftPadding: 0
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
            if (group.afterSaveAs && !Session.needsSaveAs) {
                group.afterSaveAs = false;
                group.saveReport();
            }
        }
        function onProjectChanged() {
            group.afterSaveAs = false;
        }
    }
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
