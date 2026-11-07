// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import OnboardingAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

CollectionBoundarySession {
    property bool keepCreationQuestion: false
    property var retainedFormValues

    function cleanup() {
        cleanupOnlineControls();
        if (keepCreationQuestion) return;
        for (let pass = 0; pass < 3; ++pass) {
            const dialogs = Probe.objectsWithProperty(app, "title").filter(item => item !== app && item.visible && typeof item.reject === "function");
            for (const dialog of dialogs) dialog.reject();
            settle();
        }
    }
    function creationInput() {
        const data = SettingsProof.fileObservation(mailbox, "creation-inputs.json");
        verify(data.exists, "Creation cases receive their independent temporary-folder inputs");
        return JSON.parse(data.text);
    }
    function visibleButton(text) {
        const all = Probe.objectsWithProperty(app, "text").concat(Render.descendants(Ui.windowRoot(app)));
        const button = all.find(item => item.text === text && typeof item.clicked === "function" && Ui.exposed(item));
        return button === undefined ? null : button;
    }
    function requireButton(text) {
        let button;
        tryVerify(() => { button = visibleButton(text); return button !== null; }, 3000,
                  "The actual confirmation exposes its requested user action " + text);
        return button;
    }
    function formValues(dialog) {
        return {name:dialog.projectName, title:dialog.projectTitle, authors:dialog.projectAuthors,
                description:dialog.projectDescription, parent:dialog.projectParentDirectory};
    }
    function openCreation() {
        keepCreationQuestion = false;
        Session.closeProject();
        AppState.open(AppState.Page.Project);
        settle();
        Ui.click(this, Probe, app, "project.create");
        const dialog = Probe.objectsWithProperty(app, "projectName").find(item => item.visible && item.objectName === "createProject.dialog");
        verify(dialog !== undefined, "Project creation uses the visible production form");
        tryVerify(() => { settle(); return dialog.opened; }, 3000, "The production create form finishes opening before its inputs are set");
        const data = creationInput();
        dialog.projectName = data.name;
        dialog.projectTitle = data.title;
        dialog.projectAuthors = data.authors;
        dialog.projectDescription = data.description;
        dialog.projectParentDirectory = data.parent;
        settle();
        retainedFormValues = formValues(dialog);
        compare(retainedFormValues.name, data.name, "The actual form holds the requested name");
        compare(retainedFormValues.description, data.description, "The actual form holds the requested description");
        const accept = Probe.objectsWithProperty(app, "objectName").find(item => item.objectName === "createProject.accept" && Ui.exposed(item));
        verify(accept !== undefined, "The visible create form exposes its real acceptance button");
        click(accept);
        return dialog;
    }
    function expectQuestion() {
        const data = creationInput();
        const replace = requireButton("Replace");
        requireButton("Cancel");
        const texts = Render.descendants(Ui.windowRoot(app)).filter(item => typeof item.text === "string" && Ui.exposed(item)).map(item => item.text.replace(/<[^>]*>/g, ""));
        verify(texts.some(text => text.includes("A project named") && text.includes(data.name) && text.includes(data.nativeParent) && text.includes("Replace it?")),
               "The overwrite question identifies the existing project and its chosen folder");
        return replace;
    }
    function proveNewProject() {
        const data = creationInput();
        tryVerify(() => Session.hasProject, 3000, "Successful creation adopts the newly saved project");
        compare(Session.project.name, data.name, "The saved project has the form's requested name");
        compare(Session.project.title, data.title, "The saved project has the form's requested title");
        compare(Session.project.authors, data.authors, "The saved project has the form's requested authors");
        compare(Session.project.description, data.description, "The saved project has the form's requested description");
        compare(Session.project.structures.count, 0, "Replacing a project starts with the same empty structure set as fresh creation");
        compare(Session.project.experiments.count, 0, "Replacing a project starts with the same empty experiment set as fresh creation");
        verify(!Session.needsSaveAs, "Successful creation saves into the chosen ordinary location");
    }
    function check_creation_fresh() {
        openCreation();
        proveNewProject();
    }
    function check_creation_cancel() {
        const dialog = openCreation();
        expectQuestion();
        click(requireButton("Cancel"));
        tryCompare(dialog, "visible", true, 3000, "Cancel returns to the actual create form");
        compare(formValues(dialog), retainedFormValues, "Cancel preserves every entered create-form value");
    }
    function check_creation_replace() {
        openCreation();
        click(expectQuestion());
        proveNewProject();
    }
    function check_creation_prepare_failure() {
        openCreation();
        expectQuestion();
        keepCreationQuestion = true;
    }
    function check_creation_confirm_failure() {
        keepCreationQuestion = false;
        click(requireButton("Replace"));
        tryVerify(() => Session.lastError !== "", 3000, "A failing ordinary replacement reports its factual failure");
        const reason = Session.lastError;
        verify(/permission|denied|read.only|writ|not allowed|cannot create|failed to create|could not create|could not be moved aside|access/i.test(reason),
               "The replacement failure names the actual unwritable-destination reason: " + reason);
        const texts = () => Render.descendants(Ui.windowRoot(app)).filter(item => typeof item.text === "string" && Ui.exposed(item)).map(item => item.text.replace(/<[^>]*>/g, "")).join("\n");
        tryVerify(() => texts().includes(reason), 3000, "The user-visible failure contains the backend's factual reason");
    }
}
