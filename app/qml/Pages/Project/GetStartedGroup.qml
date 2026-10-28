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
            onClicked: AppState.afterChanges(() => group.chooseCreate())
        }

        EaElements.SideBarButton {
            objectName: "project.open"
            fontIcon: "upload"
            text: qsTr("Open project…")
            // A folder or a .zip, first, on every platform: a chooser picks files or a folder, never both (edi
            // ADR-0052 §3).
            onClicked: AppState.afterChanges(() => openChoice.open())
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
    function prepareAssistantCreate(id) {
        if (id.length === 0 || Session.project !== null || createIntent !== null || assistantCreate !== null || createDialog.visible) return false;
        assistantCreate = { id: id, cancelled: false };
        return assistantCreate !== null && assistantCreate.id === id && Session.project === null;
    }
    function assistantCreateDialog(id) {
        return assistantCreate !== null && assistantCreate.id === id ? createDialog : null;
    }
    function retireAssistantCreate(id, manual) {
        const original = assistantCreate;
        if (original === null || original.id !== id) return;
        original.cancelled = true;
        const pending = createIntent;
        if (manual && pending !== null && pending.assistant === original) pending.assistant = null;
        if (assistantCreate === original) assistantCreate = null;
        if (!manual && createIntent === pending && pending !== null && pending.assistant === original)
            createDialog.close(); // Terminal original-dialog callback; may admit B.
    }
    // Native Create reuses this actual form's remembered parent/defaults. It does
    // not accept a dialog or synthesize a chooser selection.
    function nativeProjectNameError(name) {
        return createDialog.acceptsProjectName(name) ? "" : qsTr("Project Name must contain 2–31 characters: start with an ASCII letter, then use letters, digits, underscore, hyphen or period. Put human-readable text in Title. The supplied Name was not changed.");
    }
    function nativeCreateDefaults(name, description, title) {
        if (Session.project !== null || createIntent !== null || createDialog.visible) return ({});
        const actualName = name.length > 0 ? name : "project";
        const nameError = nativeProjectNameError(actualName);
        if (nameError.length > 0)
            return ({error: nameError, target: "createProject.name"});
        const actualTitle = title === undefined || title === null ? createDialog.projectTitle : title;
        if (!createDialog.acceptsProjectTitle(actualTitle))
            return ({error: qsTr("Project Title must fit the original single-line field (%1 UTF-16 units), without NUL, newline, carriage-return or tab. The supplied Title was not changed.").arg(createDialog.projectTitleMaximumLength), target: "createProject.title"});
        const parent = createDialog.projectParentDirectory
            ? EaLogic.Utils.urlToLocalFile(createDialog.projectParentDirectory) : createDialog.defaultProjectParentDirectory;
        return ({name: actualName, description: description, title: actualTitle,
            authors: createDialog.projectAuthors, location: WebFiles.available ? "" : createDialog.joinedPath(parent, actualName),
            suRule: Preferences.newProjectSuRule, reportLibraries: Preferences.newReportLibraries === "embedded"});
    }
    function chooseCreate() {
        if (createIntent !== null || createDialog.visible) return;
        const life = createLife;
        const original = { project: Session.project, assistant: assistantCreate };
        createOperation = original;
        if (!life.alive || createOperation !== original) return;
        createIntent = original;
        if (!life.alive || createIntent !== original || Session.project !== original.project) return;
        EaGlobals.Vars.showProjectDescriptionDialog = true;
    }

    EaComponents.ProjectDescriptionDialog {
        id: createDialog
        objectName: "createProject.dialog"
        readonly property string assistantIntentId: group.createIntent !== null && group.createIntent.assistant !== null ? group.createIntent.assistant.id : ""
        // The base's dialog (edi's copy joins the location cleanly), placed on whole pixels as AppDialog is.
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        visible: EaGlobals.Vars.showProjectDescriptionDialog
        onOpened: {
            const original = group.createIntent;
            if (original !== null && original.assistant !== null)
                Session.assistant.observeCreateDialog(createDialog, original.assistant.id, "opened");
        }
        onRejected: {
            const original = group.createIntent;
            if (original !== null && original.assistant !== null)
                Session.assistant.observeCreateDialog(createDialog, original.assistant.id, "rejected");
        }
        onClosed: {
            const life = group.createLife;
            const original = group.createIntent;
            // Qt's same close/accepted signal tail retains this original token
            // until accepted can consume it. Never clear a newer dialog intent.
            Qt.callLater(() => {
                if (!life.alive || group.createIntent !== original || createDialog.visible) return;
                if (original !== null && original.assistant !== null && group.assistantCreate === original.assistant)
                    group.assistantCreate = null;
                if (!life.alive || group.createIntent !== original || createDialog.visible) return;
                group.createIntent = null;
                if (!life.alive || group.createIntent !== null || createDialog.visible) return;
                EaGlobals.Vars.showProjectDescriptionDialog = false;
            });
        }
        // A new project's folder is under the user's documents unless one was chosen before; it is saved there at
        // once (the owner, 2026-10-08). The browser has no folder to save into: Save As downloads it.
        defaultProjectParentDirectory: EaLogic.Utils.urlToLocalFile(String(StandardPaths.writableLocation(StandardPaths.DocumentsLocation)))
        // On the next turn: the new project replaces this page, dialog and all (AppState.afterChanges). The flag is
        // reset here, not only when the dialog has closed: this page goes before its closing ends, and the new page's
        // dialog would open again on a flag still set.
        onAccepted: {
            const life = group.createLife, original = group.createIntent;
            if (original === null || Session.project !== original.project || (original.assistant !== null && original.assistant.cancelled)) return;
            if (original.assistant !== null && !Session.assistant.observeCreateDialog(createDialog, original.assistant.id, "accepted")) return;
            group.createIntent = null;
            if (!life.alive || group.createOperation !== original || Session.project !== original.project) return;
            if (original.assistant !== null && group.assistantCreate === original.assistant) group.assistantCreate = null;
            const name = createDialog.projectName, description = createDialog.projectDescription;
            const location = WebFiles.available ? "" : createDialog.projectLocation;
            const title = createDialog.projectTitle, authors = createDialog.projectAuthors;
            EaGlobals.Vars.showProjectDescriptionDialog = false;
            Qt.callLater(() => {
                if (!life.alive || group.createOperation !== original || Session.project !== original.project || (original.assistant !== null && original.assistant.cancelled)) return;
                const outcome = Session.createProjectWithOutcome(name, description, location, Preferences.newProjectSuRule, title, authors, Preferences.newReportLibraries === "embedded", original.assistant !== null ? original.assistant.id : "");
                if (!outcome.success && outcome.current && Session.creationOutcomeCurrent(outcome) && outcome.error.length > 0 && original.assistant === null)
                    AppState.createFailed();
            });
        }
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
        onAccepted: {
            if (WebFiles.available)
                Session.openWebProject(zip ? "file" : "folder");
            else if (zip)
                openZipDialog.open();
            else
                openFolderDialog.open();
        }

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
