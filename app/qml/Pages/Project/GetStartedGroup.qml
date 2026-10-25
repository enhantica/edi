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

    // The browser's Open (edi ADR-0052 §9): a project folder or a .zip, then the browser's own chooser. Chrome and Edge
    // open it on the disk, where Save writes it back; other browsers copy it into the browser's storage.
    AppDialog {
        id: openChoice
        objectName: "open.choice"
        property bool zip: false
        parent: Overlay.overlay
        title: qsTr("Open project")
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentWidth: openChoiceColumn.implicitWidth
        contentHeight: openChoiceColumn.implicitHeight
        onAboutToShow: zip = false
        onAccepted: Session.openWebProject(zip ? "zip" : "folder")

        Column {
            id: openChoiceColumn

            EaElements.Label {
                text: qsTr("Format")
                bottomPadding: EaStyle.Sizes.fontPixelSize * 0.25
            }
            EaElements.RadioButton {
                objectName: "open.folder"
                verticalPadding: 0
                text: qsTr("Folder")
                checked: !openChoice.zip
                onClicked: openChoice.zip = false
            }
            EaElements.RadioButton {
                objectName: "open.zip"
                verticalPadding: 0
                text: qsTr("Zip archive")
                checked: openChoice.zip
                onClicked: openChoice.zip = true
            }
        }
    }

    // The system's file dialog: a project.edi opens its folder, a .zip is unpacked (edi ADR-0052).
    FileDialog {
        id: openProjectDialog
        title: qsTr("Open an edi project")
        nameFilters: [qsTr("edi projects (project.edi *.zip)")]
        onAccepted: Session.openProject(selectedFile)
    }
}
