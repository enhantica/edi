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

// Get started (easydiffractionbeta Pages/Project/SideBarBasic/GetStarted.qml): create a new project
// or open an existing one — an edi project is a directory — and save the open one as (edi ADR-0017 §13).
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
            onClicked: group.chooseCreate()
        }

        EaElements.SideBarButton {
            objectName: "project.open"
            fontIcon: "upload"
            text: qsTr("Open an existing project")
            // In the browser the chosen folder is copied into the page's memory first (edi ADR-0023).
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

    // The original Create dialog, with a one-shot original owner/operation.
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
        readonly property string assistantIntentId: group.createIntent !== null && group.createIntent.assistant !== null ? group.createIntent.assistant.id : ""
        // The base's dialog (edi's copy joins the location cleanly), placed on whole pixels as AppDialog is.
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        visible: EaGlobals.Vars.showProjectDescriptionDialog
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
        onAccepted: {
            const life = group.createLife;
            const original = group.createIntent;
            if (original === null || Session.project !== original.project ||
                (original.assistant !== null && original.assistant.cancelled)) return;
            group.createIntent = null;
            if (!life.alive || group.createIntent !== null || group.createOperation !== original || Session.project !== original.project) return;
            if (original.assistant !== null && group.assistantCreate === original.assistant) group.assistantCreate = null;
            if (!life.alive || group.createIntent !== null || group.createOperation !== original || Session.project !== original.project) return;
            const created = Session.createProjectWithOutcome(createDialog.projectName, createDialog.projectDescription, WebFiles.available ? "" : createDialog.projectLocation, Preferences.newProjectSuRule, createDialog.projectTitle, createDialog.projectAuthors, Preferences.newReportLibraries === "embedded", original.assistant !== null ? original.assistant.id : "");
            if (!life.alive || group.createIntent !== null || group.createOperation !== original) return;
            if (!created.success && created.current && Session.creationOutcomeCurrent(created)
                && created.error.length > 0 && original.assistant === null) {
                createError.ownerOperation = original;
                if (!life.alive || group.createOperation !== original || group.createIntent !== null) return;
                createError.ownerOutcome = created;
                if (!life.alive || group.createIntent !== null || group.createOperation !== original
                    || createError.ownerOutcome !== created || !Session.creationOutcomeCurrent(created)) return;
                createError.message = created.error;
                if (!life.alive || group.createIntent !== null || group.createOperation !== original
                    || createError.ownerOutcome !== created || !Session.creationOutcomeCurrent(created)) return;
                createError.open();
            }
        }
    }

    // A created project that could not be saved at its location stays open, unsaved; this says why.
    AppDialog {
        id: createError
        objectName: "create.error"
        property string message: ""
        property var ownerOutcome: null
        property var ownerOperation: null
        Connections {
            target: group
            function onCreateOperationChanged() {
                if (createError.visible && createError.ownerOperation !== group.createOperation)
                    createError.close();
            }
        }
        Connections {
            target: Session
            function onProjectChanged() {
                const original = createError.ownerOutcome;
                if (createError.visible && original !== null && !Session.creationOutcomeCurrent(original))
                    createError.close();
            }
        }
        parent: Overlay.overlay
        title: qsTr("The project was not saved")
        standardButtons: Dialog.Ok
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: createErrorText.implicitHeight

        EaElements.Label {
            id: createErrorText
            width: createError.contentWidth
            wrapMode: Text.Wrap
            text: createError.message
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

    FolderDialog {
        id: openProjectDialog
        title: qsTr("Open an edi project directory")
        onAccepted: Session.openProject(selectedFolder)
    }
}
