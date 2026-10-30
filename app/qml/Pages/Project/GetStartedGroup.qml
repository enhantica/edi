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
            onClicked: ApplicationInfo.createProjectClicked()
        }

        EaElements.SideBarButton {
            objectName: "project.open"
            fontIcon: "upload"
            text: qsTr("Open project…")
            // A folder or a .zip, first, on every platform: a chooser picks files or a folder, never both (edi
            // ADR-0052 §3).
            onClicked: ApplicationInfo.askOpenProjectChoice()
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

    property var createLife: ({ alive: true })
    property var createIntent: null
    property var createOperation: null
    property var assistantCreate: null
    Component.onDestruction: createLife.alive = false
    function prepareAssistantCreate(id) { return ApplicationInfo.prepareAssistantCreate(id); }
    function assistantCreateDialog(id) { return ApplicationInfo.assistantCreateDialog(id); }
    function retireAssistantCreate(id, manual) { ApplicationInfo.retireAssistantCreate(id, manual); }
    // Native Create reuses this actual form's remembered parent/defaults. It does
    // not accept a dialog or synthesize a chooser selection.
    function nativeProjectNameError(name) { return ApplicationInfo.createProjectNameError(name); }
    function nativeCreateDefaults(name, description, title) { return ApplicationInfo.createProjectDefaults(name, description, title); }
    function chooseCreate() { ApplicationInfo.chooseCreateProject(); }

    EaComponents.ProjectDescriptionDialog {
        id: createDialog
        objectName: "createProject.dialog"
        readonly property string assistantIntentId: group.createIntent !== null && group.createIntent.assistant !== null ? group.createIntent.assistant.id : ""
        // The base's dialog (edi's copy joins the location cleanly), placed on whole pixels as AppDialog is.
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        visible: EaGlobals.Vars.showProjectDescriptionDialog
        onOpened: ApplicationInfo.createProjectDialogEvent(0)
        onRejected: ApplicationInfo.createProjectDialogEvent(1)
        onClosed: ApplicationInfo.createProjectDialogEvent(2)
        // A new project's folder is under the user's documents unless one was chosen before; it is saved there at
        // once (the owner, 2026-10-08). The browser has no folder to save into: Save As downloads it.
        defaultProjectParentDirectory: EaLogic.Utils.urlToLocalFile(String(StandardPaths.writableLocation(StandardPaths.DocumentsLocation)))
        // On the next turn: the new project replaces this page, dialog and all (AppState.afterChanges). The flag is
        // reset here, not only when the dialog has closed: this page goes before its closing ends, and the new page's
        // dialog would open again on a flag still set.
        onAccepted: ApplicationInfo.createProjectDialogEvent(3)
    }

    // Open project (edi ADR-0052 §3, §9; owner, 2026-10-25): the same small dialog on every platform, Folder or Zip
    // archive, then the matching chooser: a folder chooser for the project folder holding project.edi, or a file
    // chooser for a .zip. In the browser the browser's own chooser: Chrome and Edge open it on the disk, where Save
    // writes it back; other browsers copy it into the browser's storage.
    AppDialog {
        id: openChoice
        objectName: "open.choice"
        enterAccepts: true
        property bool zip: false
        parent: Overlay.overlay
        title: qsTr("Open project")
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentWidth: Math.max(openChoiceColumn.implicitWidth, Math.round(AppSizes.messagesDialogContentWidth / 2))
        contentHeight: openChoiceColumn.implicitHeight
        onAboutToShow: zip = false
        onAccepted: ApplicationInfo.openProjectChoice()

        Column {
            id: openChoiceColumn

            ChoiceRadioButton {
                objectName: "open.folder"
                text: qsTr("Folder")
                checked: !openChoice.zip
                onClicked: openChoice.zip = false
            }
            ChoiceRadioButton {
                objectName: "open.zip"
                text: qsTr("Zip archive")
                checked: openChoice.zip
                onClicked: openChoice.zip = true
            }
        }
    }

    // The system's choosers. On the next turn the opened project replaces this page, dialogs and all
    // (AppState.afterChanges).
    FolderDialog {
        id: openFolderDialog
        title: qsTr("Open an edi project folder")
        acceptLabel: qsTr("Open")
        onAccepted: Qt.callLater(Session.openProject, selectedFolder)
    }
    FileDialog {
        id: openZipDialog
        title: qsTr("Open an edi project archive")
        nameFilters: [qsTr("edi project archives (*.zip)")]
        onAccepted: Qt.callLater(Session.openProject, selectedFile)
    }
}
