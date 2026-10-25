// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtCore

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents
import EasyApplication.Gui.Logic as EaLogic

import edi.app

// Get started (easydiffractionbeta Pages/Project/SideBarBasic/GetStarted.qml): create a new project, open one from its
// project.edi or a .zip, or save the open one as a folder or a .zip, or a copy of it (edi ADR-0017 §13, ADR-0052).
EaElements.GroupBox {
    id: group
    objectName: "group.getStarted"
    title: qsTr("Get started")
    icon: "rocket"
    // The one group that starts open: the first thing a new user needs (the owner, 2026-09-29; edi ADR-0017 §3).
    collapsed: false

    Grid {
        columns: 2
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            objectName: "project.create"
            fontIcon: "plus-circle"
            text: qsTr("Create a new project")
            onClicked: AppState.afterChanges(() => EaGlobals.Vars.showProjectDescriptionDialog = true)
        }

        EaElements.SideBarButton {
            objectName: "project.open"
            fontIcon: "upload"
            text: qsTr("Open project…")
            // In the browser a folder or a .zip is chosen through the browser (edi ADR-0052 §9): which, first.
            onClicked: AppState.afterChanges(() => WebFiles.available ? openChoice.open() : openProjectDialog.open())
        }

        EaElements.SideBarButton {
            objectName: "project.saveAs"
            enabled: Session.project !== null
            fontIcon: "file-export"
            text: qsTr("Save project as…")
            onClicked: AppState.saveAsRequested()
        }

        // Opening a project from a URL is not implemented: shown, disabled (edi ADR-0017 §4).
        EaElements.SideBarButton {
            objectName: "project.openUrl"
            enabled: false
            fontIcon: "link"
            text: qsTr("Open project from URL…")
        }
    }

    EaComponents.ProjectDescriptionDialog {
        id: createDialog
        // The base's dialog (edi's copy joins the location cleanly), placed on whole pixels as AppDialog is.
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        visible: EaGlobals.Vars.showProjectDescriptionDialog
        onClosed: EaGlobals.Vars.showProjectDescriptionDialog = false
        // A new project's folder is under the user's documents unless one was chosen before; it is saved there at
        // once (the owner, 2026-10-08). The browser has no folder to save into: Save As downloads it.
        defaultProjectParentDirectory: EaLogic.Utils.urlToLocalFile(String(StandardPaths.writableLocation(StandardPaths.DocumentsLocation)))
        // On the next turn: the new project replaces this page, dialog and all (AppState.afterChanges).
        onAccepted: {
            const name = createDialog.projectName, description = createDialog.projectDescription;
            const location = WebFiles.available ? "" : createDialog.projectLocation;
            const title = createDialog.projectTitle, authors = createDialog.projectAuthors;
            Qt.callLater(() => {
                if (!Session.createProject(name, description, location, Preferences.newProjectSuRule, title, authors, Preferences.newReportLibraries === "embedded"))
                    AppState.createFailed();
            });
        }
    }

    // The browser's Open (edi ADR-0052 §9): a project folder or a .zip, then the browser's own chooser. Chrome and Edge
    // open it on the disk, where Save writes it back; other browsers copy it into the browser's storage.
    AppDialog {
        id: openChoice
        objectName: "open.choice"
        property bool zip: false
        parent: Overlay.overlay
        title: qsTr("Open project")
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentWidth: Math.max(openChoiceColumn.implicitWidth, Math.round(AppSizes.messagesDialogContentWidth / 2))
        contentHeight: openChoiceColumn.implicitHeight
        onAboutToShow: zip = false
        onAccepted: Session.openWebProject(zip ? "file" : "folder")

        Column {
            id: openChoiceColumn

            EaElements.RadioButton {
                objectName: "open.folder"
                verticalPadding: AppSizes.choiceRowPadding
                text: qsTr("Folder")
                checked: !openChoice.zip
                onClicked: openChoice.zip = false
            }
            EaElements.RadioButton {
                objectName: "open.zip"
                verticalPadding: AppSizes.choiceRowPadding
                // Chrome and Edge open a project.edi too, from its folder on the disk.
                text: WebStorage.diskAccess ? qsTr("project.edi or zip archive") : qsTr("Zip archive")
                checked: openChoice.zip
                onClicked: openChoice.zip = true
            }
        }
    }

    // A project.edi picked in Chrome or Edge opens its folder, which the browser lets the page use only once the user
    // picks it too, with a click of its own.
    Connections {
        target: Session
        function onWebFolderNeeded(name) {
            recordFolder.name = name;
            recordFolder.open();
        }
    }
    AppDialog {
        id: recordFolder
        objectName: "open.recordFolder"
        property string name
        parent: Overlay.overlay
        title: qsTr("Open project")
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: recordFolderText.implicitHeight
        onAccepted: Session.openWebRecordFolder()

        EaElements.Label {
            id: recordFolderText
            width: recordFolder.contentWidth
            wrapMode: Text.Wrap
            text: qsTr("To open %1, choose the folder that holds it.").arg(recordFolder.name)
        }
    }

    // The system's file dialog: a project.edi opens its folder, a .zip is unpacked (edi ADR-0052).
    FileDialog {
        id: openProjectDialog
        title: qsTr("Open an edi project")
        nameFilters: [qsTr("edi projects (project.edi *.zip)")]
        // On the next turn: the opened project replaces this page, dialog and all (AppState.afterChanges).
        onAccepted: Qt.callLater(Session.openProject, selectedFile)
    }
}
