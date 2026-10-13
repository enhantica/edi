// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Saving the report, the sidebar's top group (the owner, 2026-10-13): the interactive HTML with, beside it, whether it
// embeds plotly.js and three.js (online by default); below it the static PDF, on A4 with the preview's figures as
// images, and the CIF report (disabled until its writer exists).
EaElements.GroupBox {
    id: group

    property ReportViewModel report: null
    // The preview, whose figures the PDF shows.
    property ReportPreview preview: null

    // Grabs the preview's figures, then writes the PDF to `file` (the browser downloads it).
    function savePdf(file) {
        const report = group.report;
        group.preview.grabFigures(figures => report.savePdf(file, figures, EaStyle.Fonts.fontFamily));
    }

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
                enabled: group.report !== null
                fontIcon: "file-code"
                text: qsTr("Save interactive HTML")
                ToolTip.text: qsTr("Save the report as one HTML file with interactive charts")
                // The browser downloads the file; the desktop asks where to write it.
                onClicked: {
                    if (WebFiles.available) {
                        group.report.saveHtml("");
                        return;
                    }
                    // Offered in the project's folder, under the project's name.
                    if (Session.projectLocation !== "")
                        htmlDialog.currentFolder = Session.projectDirectoryUrl(Session.projectLocation);
                    htmlDialog.selectedFile = htmlDialog.currentFolder + "/" + group.report.htmlFileName();
                    htmlDialog.open();
                }
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
            enabled: group.report !== null && group.preview !== null
            fontIcon: "file-pdf"
            text: qsTr("Save static PDF")
            ToolTip.text: qsTr("Save the report as a PDF on A4 pages, its charts as images")
            onClicked: {
                if (WebFiles.available) {
                    group.savePdf("");
                    return;
                }
                if (Session.projectLocation !== "")
                    pdfDialog.currentFolder = Session.projectDirectoryUrl(Session.projectLocation);
                pdfDialog.selectedFile = pdfDialog.currentFolder + "/" + group.report.pdfFileName();
                pdfDialog.open();
            }
        }
        EaElements.SideBarButton {
            objectName: "report.saveCif"
            enabled: false
            fontIcon: "file-alt"
            text: qsTr("Save static CIF")
            ToolTip.text: qsTr("The CIF report is not available yet")
        }
    }

    FileDialog {
        id: pdfDialog
        title: qsTr("Save the report as PDF")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "pdf"
        nameFilters: [qsTr("PDF files (*.pdf)")]
        onAccepted: group.savePdf(selectedFile)
    }
    FileDialog {
        id: htmlDialog
        title: qsTr("Save the report as HTML")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "html"
        nameFilters: [qsTr("HTML files (*.html)")]
        onAccepted: group.report.saveHtml(selectedFile)
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
