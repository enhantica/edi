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
// folder, its project.edi or a .zip of the folder, save the open one as, or export it as a .zip (edi ADR-0017 §13,
// ADR-0052).
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
            onClicked: EaGlobals.Vars.showProjectDescriptionDialog = true
        }

        EaElements.SideBarButton {
            objectName: "project.open"
            fontIcon: "upload"
            text: qsTr("Open an existing project")
            // In the browser the chosen folder or archive is copied into the page's memory first (edi ADR-0023).
            onClicked: {
                if (WebFiles.available) {
                    group.webRequestProject = Session.project;
                    group.webRequest = WebFiles.openProject();
                } else {
                    openProjectDialog.open();
                }
            }
        }

        EaElements.SideBarButton {
            objectName: "project.openFolder"
            visible: !WebFiles.available
            fontIcon: "folder-open"
            text: qsTr("Open a project folder…")
            onClicked: openFolderDialog.open()
        }

        EaElements.SideBarButton {
            objectName: "project.saveAs"
            enabled: Session.project !== null
            fontIcon: "file-export"
            text: qsTr("Save project as…")
            onClicked: AppState.saveAsRequested()
        }

        EaElements.SideBarButton {
            objectName: "project.export"
            enabled: Session.project !== null
            fontIcon: "file-archive"
            text: qsTr("Export project…")
            // The browser downloads the archive; the desktop asks where to write it.
            onClicked: {
                if (!WebFiles.available) {
                    exportDialog.open();
                } else if (!WebFiles.downloadProject(Session.exportFolder())) {
                    exportError.open();
                }
            }
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
        onAccepted: {
            if (!Session.createProject(createDialog.projectName, createDialog.projectDescription, WebFiles.available ? "" : createDialog.projectLocation, Preferences.newProjectSuRule, createDialog.projectTitle, createDialog.projectAuthors, Preferences.newReportLibraries === "embedded"))
                createError.open();
        }
    }

    // A created project that could not be saved at its location stays open, unsaved; this says why.
    AppDialog {
        id: createError
        objectName: "create.error"
        parent: Overlay.overlay
        title: qsTr("The project was not saved")
        standardButtons: Dialog.Ok
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: createErrorText.implicitHeight

        EaElements.Label {
            id: createErrorText
            width: createError.contentWidth
            wrapMode: Text.Wrap
            text: Session.lastError
        }
    }

    // The folder request and the project open when it was made: a folder that arrives after another project was
    // opened meanwhile is not opened over it.
    property int webRequest: 0
    property var webRequestProject: null
    Connections {
        target: WebFiles
        function onProjectOpened(request, directory) {
            if (request !== group.webRequest)
                return;
            group.webRequest = 0;
            if (Session.project === group.webRequestProject)
                Session.openProject(directory);
        }
        function onFailed(request) {
            if (request === group.webRequest)
                group.webRequest = 0;
        }
        function onCancelled(request) {
            if (request === group.webRequest)
                group.webRequest = 0;
        }
    }

    FileDialog {
        id: openProjectDialog
        title: qsTr("Open an edi project")
        nameFilters: [qsTr("edi projects (project.edi *.zip)")]
        onAccepted: Session.openProject(selectedFile)
    }

    FolderDialog {
        id: openFolderDialog
        title: qsTr("Open an edi project folder")
        onAccepted: Session.openProject(selectedFolder)
    }

    FileDialog {
        id: exportDialog
        title: qsTr("Export the project as a .zip")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "zip"
        nameFilters: [qsTr("Zip archives (*.zip)")]
        onAccepted: {
            if (!Session.exportProject(selectedFile))
                exportError.open();
        }
    }

    AppDialog {
        id: exportError
        objectName: "export.error"
        parent: Overlay.overlay
        title: qsTr("The project was not exported")
        standardButtons: Dialog.Ok
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: exportErrorText.implicitHeight

        EaElements.Label {
            id: exportErrorText
            width: exportError.contentWidth
            wrapMode: Text.Wrap
            text: Session.lastError
        }
    }
}
