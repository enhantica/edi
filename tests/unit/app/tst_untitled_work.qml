// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "NativeTurn.js" as Turn
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "UntitledWork"
    when: windowShown
    property var app
    property string selected: ""
    Component {
        id: application
        Main {}
    }
    function initTestCase() {
        RunLog.dismissCrash();
    }
    function init() {
        selected = Turn.begin(test, Probe, message => test.warn(message));
        Session.closeProject();
        AppState.reset();
        app = application.createObject(null, {
            width: 1280,
            height: 900,
            visible: true
        });
        verify(app && waitForRendering(app.contentItem), "Untitled work uses the rendered production window");
        app.requestActivate();
        if (Ui.control(Probe, app, "home.start"))
            Ui.click(test, Probe, app, "home.start");
        Ui.click(test, Probe, app, "appBar.tab.project");
    }
    function cleanup() {
        if (app) {
            const dialogs = Probe.objectsWithProperty(app, "opened").filter(item => item.opened && typeof item.reject === "function");
            for (const dialog of dialogs) {
                dialog.reject();
                tryCompare(dialog, "visible", false, 2000, "The rejected form closes before its window is destroyed");
            }
            Session.closeProject();
            app.destroy();
        }
        app = null;
        Turn.end(selected, message => test.warn(message));
    }
    function draft() {
        verify(Session.project === null, "Opening Project alone creates no work container");
        AppState.open(AppState.Page.Structure);
        tryVerify(() => Session.project !== null, 2000, "Opening Structure supplies the unnamed work");
        verify(Session.untitled && Session.needsSaveAs, "Untitled work has no owned saved destination");
        verify(AppState.structurePageEnabled && !AppState.experimentPageEnabled, "Experiment waits for the first structure");
        return Session.project;
    }
    function work() {
        const p = draft();
        Ui.click(test, Probe, app, "appBar.tab.structure");
        Ui.click(test, Probe, app, "structures.create");
        compare(p.structures.count, 1, "Structure is usable before a project is named");
        p.currentStructure.cell.lengthA.value = 7.125;
        verify(AppState.experimentPageEnabled, "Adding a structure enables Experiment before naming the project");
        Ui.click(test, Probe, app, "appBar.tab.experiment");
        Ui.click(test, Probe, app, "experiments.create");
        compare(p.experiments.count, 1, "Experiment is usable before a project is named");
        verify(p.modified, "Actual untitled edits enable ordinary Save and unsaved-work protection");
        return p;
    }
    function creation() {
        let dialog;
        tryVerify(() => {
            dialog = Probe.objectsWithProperty(app, "projectName").find(item => item.objectName === "createProject.dialog" && item.opened);
            return !!dialog;
        }, 3000, "The first Save opens the real Create project dialog");
        return dialog;
    }
    function press(item) {
        Ui.scrollIntoView(item);
        app.update();
        verify(waitForRendering(app.contentItem), "The dialog control is rendered before real input");
        const point = Ui.clickPoint(item);
        verify(point && item.enabled, "The real dialog control receives pointer input");
        mouseClick(item, point.x, point.y);
    }
    function fill(dialog) {
        const parent = SettingsProof.emptyDirectory();
        dialog.projectParentDirectory = String(parent);
        for (const row of [["name", "lbco_hrpt-7"], ["title", "Neutron work before Save"], ["authors", "Ada Example; Lin Example"], ["description", "Unsaved cobalt study"]]) {
            const field = findChild(dialog, "createProject." + row[0]);
            verify(field !== null, "Create exposes the actual " + row[0] + " editor");
            press(field);
            keyClick(Qt.Key_A, Qt.ControlModifier);
            verify(SettingsProof.type(field, row[1]), "Real keyboard input supplies the requested " + row[0]);
            compare(field.text, row[1], "The dialog retains the literal entered " + row[0]);
        }
        return SettingsProof.childUrl(parent, "lbco_hrpt-7");
    }
    function test_a_structure_and_experiment_before_create() {
        const p = work();
        Ui.click(test, Probe, app, "appBar.tab.project");
        verify(Session.project === p && Session.needsSaveAs, "Navigating all usable tabs keeps the same untitled work");
        compare(p.currentStructure.cell.lengthA.value, 7.125, "Navigation retains the nontrivial scientific edit");
        const destination = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/report_evolution/project"));
        const naming = Session.beginUntitled("save");
        let callbackCount = 0;
        let opened = false;
        const settle = (operation, state) => {
            if (operation === naming && state === "superseded") {
                ++callbackCount;
                opened = Session.openProject(destination);
            }
        };
        Session.untitledSettled.connect(settle);
        try {
            Session.closeProject();
        } finally {
            Session.untitledSettled.disconnect(settle);
        }
        compare(callbackCount, 1, "Replacing the original owner settles its naming operation once");
        verify(opened, "A newer replacement is accepted synchronously from the settlement notification");
        verify(Session.project !== null && Session.project !== p && !Session.untitled,
               "The older close cannot retire the project a newer replacement just opened");
    }
    function test_b_first_save_names_and_preserves_work() {
        work();
        Ui.click(test, Probe, app, "appBar.button.save");
        const dialog = creation(), folder = fill(dialog);
        const id = Session.untitledOperationId;
        verify(id > 0, "The real Save starts a naming operation");
        compare(dialog.untitledId, id, "First Save opens Create with the same operation");
        const settlements = [];
        const settled = (operation, state) => settlements.push({
            operation, state, written: SettingsProof.fileObservation(folder, "project.edi").exists
        });
        Session.untitledSettled.connect(settled);
        try {
            compare(Session.beginUntitled("save"), id, "A repeated Save while asking reuses the operation");
            compare(settlements.length, 0, "Repeated Save does not settle the form that is still asking");
            verify(!SettingsProof.fileObservation(folder, "project.edi").exists,
                   "Filling the form does not publish a project early");
            press(dialog.standardButton(Dialog.Ok));
            tryVerify(() => Session.project && !Session.needsSaveAs && !Session.project.modified, 5000,
                      "Create after first Save commits the existing untitled work");
            Session.rejectUntitled(id);
            compare(settlements, [{operation: id, state: "saved", written: true}],
                    "First Save settles once and only after the project files exist");
        } finally {
            Session.untitledSettled.disconnect(settled);
        }
        const owner = Session.project;
        const stale = SettingsProof.childUrl(SettingsProof.emptyDirectory(), "stale-create");
        const outcome = Session.createProjectWithOutcome("stale-create", "", SettingsProof.localPath(stale),
                                                         "", "", "", false, "", false, id);
        verify(!outcome.saved, "A delayed Create answer cannot save after its naming operation settles");
        verify(Session.project === owner && Session.project.name === "lbco_hrpt-7",
               "The settled request may neither replace nor rename the adopted project");
        verify(!SettingsProof.fileObservation(stale, "project.edi").exists,
               "A delayed naming answer writes nothing at its obsolete destination");
        verify(Session.openProject(folder), "The first saved project reopens through the real loader");
        compare(Session.project.name, "lbco_hrpt-7", "The short name becomes the saved project name");
        compare(Session.project.title, "Neutron work before Save", "First Save retains the entered title");
        compare(Session.project.authors, "Ada Example; Lin Example", "First Save retains separated authors");
        compare(Session.project.description, "Unsaved cobalt study", "First Save retains the description");
        compare(Session.project.structures.count, 1, "Naming an untitled project does not replace its structure");
        compare(Session.project.experiments.count, 1, "Naming an untitled project does not replace its experiment");
        compare(Session.project.currentStructure.cell.lengthA.value, 7.125, "First Save and reopen preserve the independent scientific edit");
    }
    function test_c_cancel_first_save_keeps_work() {
        const p = work();
        Ui.click(test, Probe, app, "appBar.button.save");
        const dialog = creation();
        const first = dialog.untitledId;
        const settlements = [];
        const settled = (operation, state) => settlements.push([operation, state]);
        Session.untitledSettled.connect(settled);
        try {
            compare(first, Session.untitledOperationId, "The form carries the current Save operation");
            keyClick(Qt.Key_Escape);
            tryCompare(dialog, "visible", false, 2000, "Escape cancels first Save through the real dialog");
            compare(settlements, [[first, "rejected"]], "Escape settles the original Save exactly once");
            Ui.click(test, Probe, app, "appBar.button.save");
            const second = creation().untitledId;
            verify(second > 0 && second !== first, "Retry opens a new operation");
            const successor = Session.beginUntitled("manual-create");
            verify(successor > 0 && successor !== second, "A different Create origin supersedes the pending Save");
            const location = String(SettingsProof.emptyDirectory());
            verify(!Session.acceptUntitled(second, "stale-save", "", location, "", "", false),
                   "The replaced Save's late acceptance cannot publish");
            Session.rejectUntitled(second);
            compare(Session.untitledOperationId, successor, "A stale close cannot dismiss the successor");
            Session.rejectUntitled(successor);
            compare(settlements, [[first, "rejected"], [second, "superseded"], [successor, "rejected"]],
                    "Rejection and supersession settle only their own operation once");
        } finally {
            Session.untitledSettled.disconnect(settled);
        }
        verify(Session.project === p && p.modified && Session.needsSaveAs, "Cancelling first Save preserves dirty untitled work");
        compare(p.currentStructure.cell.lengthA.value, 7.125, "Cancelling naming loses no scientific edit");
        linkedPolicy(p);
    }
    function linkedPolicy(p) {
        const file = Probe.repoUrl("tests/fixtures/report_evolution/project/scan/point1.dat");
        verify(p.loadDatasets(p.currentExperiment, [file], false, false, []),
               "The original project admits a measured file that remains linked outside it");
        tryCompare(p, "calculating", false, 5000, "The linked data finishes loading before the Save question");
        p.includeDataOnSave = "ask";
        const parent = SettingsProof.emptyDirectory();
        const folder = SettingsProof.childUrl(parent, "linked-naming");
        const path = SettingsProof.localPath(folder);
        const formerName = p.name;
        const settlements = [];
        const settled = (operation, state) => settlements.push([operation, state]);
        const questions = [];
        let answerImmediately = false;
        const asked = (request, bytes, files, large, linked) => {
            questions.push({request, bytes, files, large, linked, operation: Session.untitledOperationId});
            if (answerImmediately)
                Session.answerSaveData(request, "linked");
        };
        Session.untitledSettled.connect(settled);
        Session.saveDataChoiceNeeded.connect(asked);
        try {
            const cancelled = Session.beginUntitled("save");
            verify(Session.acceptUntitled(cancelled, "linked-naming", "", path, "", "", false),
                   "First Save accepts a form for the linked-data question");
            compare(questions.length, 1, "The owning Save asks exactly one linked-data question");
            verify(questions[0].linked && questions[0].operation === cancelled,
                   "The question belongs to the original linked operation");
            verify(Session.project === p && p.name === formerName && Session.untitled,
                   "The question leaves the open project untitled");
            Session.answerSaveData(questions[0].request, "cancel");
            compare(settlements, [[cancelled, "rejected"]], "Cancelling the question rejects its operation once");
            verify(!SettingsProof.fileObservation(folder, "project.edi").exists,
                   "Cancelling the question leaves the destination unwritten");

            const stale = Session.beginUntitled("save");
            verify(Session.acceptUntitled(stale, "linked-naming", "", path, "", "", false),
                   "Retry installs its own data question");
            compare(questions.length, 2, "Retry reaches a distinct data question");
            const current = Session.beginUntitled("manual-create");
            const error = Session.lastError;
            Session.answerSaveData(questions[1].request, "copy");
            compare(Session.untitledOperationId, current, "The obsolete data answer leaves the successor asking");
            compare(Session.lastError, error, "The obsolete data answer leaves the successor's error state alone");
            verify(!SettingsProof.fileObservation(folder, "project.edi").exists,
                   "An obsolete data answer cannot create a project");
            const occupied = SettingsProof.childUrl(parent, "late-occupant");
            verify(Session.acceptUntitled(current, "late-occupant", "", SettingsProof.localPath(occupied), "", "", false),
                   "A new destination can still be empty when the naming operation asks about its data");
            compare(questions.length, 3, "The pending destination reaches its real linked-data question");
            const occupant = "Another process owns these files";
            verify(SettingsProof.write(parent, "late-occupant/sentinel.txt", occupant),
                   "A separate writer occupies the previously empty destination while the question is open");
            Session.answerSaveData(questions[2].request, "linked");
            compare(settlements, [[cancelled, "rejected"], [stale, "superseded"], [current, "refused"]],
                    "The attempted write refuses the late occupant and settles its own operation once");
            compare(SettingsProof.text(occupied, "sentinel.txt"), occupant, "The refusal preserves the new occupant");
            verify(!SettingsProof.fileObservation(occupied, "project.edi").exists,
                   "The refusal publishes no project over the late occupant");
            verify(Session.project === p && Session.untitled && p.name === formerName,
                   "The refused write leaves the original project and name intact");

            const retry = Session.beginUntitled("save");
            answerImmediately = true;
            verify(Session.acceptUntitled(retry, "linked-naming", "", path, "", "", false),
                   "A synchronous Link answer completes the owning naming request, error: " + Session.lastError);
            compare(questions.length, 4, "The succeeded naming has a single linked-data question of its own");
            compare(settlements, [[cancelled, "rejected"], [stale, "superseded"], [current, "refused"], [retry, "saved"]],
                    "A reentrant Link answer leaves exactly one terminal result for each operation");
            verify(SettingsProof.fileObservation(folder, "project.edi").exists,
                   "The reentrant Link answer writes a complete named project");
        } finally {
            Session.saveDataChoiceNeeded.disconnect(asked);
            Session.untitledSettled.disconnect(settled);
        }
    }
    function test_d_quit_cancel_and_discard() {
        const p = work();
        app.close();
        const question = findChild(app, "unsavedChanges");
        tryCompare(question, "opened", true, 2000, "Quitting with untitled edits asks the ordinary unsaved-work question");
        for (const button of [Dialog.Save, Dialog.Discard, Dialog.Cancel])
            verify(question.standardButton(button), "Untitled work retains Save, Discard and Cancel choices");
        press(question.standardButton(Dialog.Cancel));
        tryCompare(question, "visible", false, 2000, "Cancel closes the unsaved-work question");
        verify(app.visible && Session.project === p && p.modified, "Cancel leaves the window and untitled work intact");
        app.close();
        tryCompare(question, "opened", true, 2000, "A second quit still protects the unchanged dirty work");
        press(question.standardButton(Dialog.Discard));
        tryCompare(app, "visible", false, 2000, "Explicit Discard permits the ordinary window close");
    }
    function test_d2_quit_save_names_and_closes() {
        work();
        app.close();
        const question = findChild(app, "unsavedChanges");
        tryCompare(question, "opened", true, 2000, "Quit with untitled edits offers its ordinary Save choice");
        press(question.standardButton(Dialog.Save));
        const dialog = creation(), folder = fill(dialog);
        const id = Session.untitledOperationId;
        verify(id > 0, "The Quit guard starts a naming operation");
        compare(dialog.untitledId, id, "Quit's Save names the work through the same Create form");
        const settlements = [];
        const settled = (operation, state) => settlements.push([operation, state, app.visible]);
        Session.untitledSettled.connect(settled);
        try {
            press(dialog.standardButton(Dialog.Ok));
            tryCompare(app, "visible", false, 5000, "The original Quit resumes automatically after naming saves");
            compare(settlements, [[id, "saved", true]], "The project settles once before its owning Quit closes");
        } finally {
            Session.untitledSettled.disconnect(settled);
        }
        verify(SettingsProof.fileObservation(folder, "project.edi").exists, "Quit's Save writes the chosen project folder");
        verify(Session.openProject(folder), "The project saved while quitting reopens normally");
        compare(Session.project.currentStructure.cell.lengthA.value, 7.125, "Quit's Save preserves the nontrivial untitled scientific edit");
    }
    function test_e_dialog_labels() {
        Ui.expandGroup(test, Probe, app, "group.getStarted");
        Ui.click(test, Probe, app, "project.create");
        const dialog = creation();
        const labels = Render.descendants(dialog.contentItem).filter(item => typeof item.text === "string").map(item => item.text);
        for (const title of ["Short name · Folder", "Title", "Authors", "Description", "Location"])
            verify(labels.includes(title), "Create names the field by its actual purpose: " + title);
        verify(!labels.some(label => /directory/i.test(label)), "Project creation uses Folder rather than Directory");
    }
    function test_f_dialog_hints_data() {
        return [
            {
                tag: "name",
                purpose: "folder"
            },
            {
                tag: "title",
                purpose: "report"
            },
            {
                tag: "authors",
                purpose: "report"
            },
            {
                tag: "description",
                purpose: "report"
            },
            {
                tag: "location",
                purpose: "folder"
            }
        ].sort((a, b) => a.tag < b.tag ? -1 : 1);
    }
    function test_f_dialog_hints(data) {
        Ui.expandGroup(test, Probe, app, "group.getStarted");
        Ui.click(test, Probe, app, "project.create");
        const dialog = creation(), field = findChild(dialog, "createProject." + data.tag);
        verify(field !== null, "The create form exposes its " + data.tag + " field");
        const hint = String(field.placeholderText || "");
        verify(new RegExp(data.purpose, "i").test(hint), "The " + data.tag + " placeholder explains its actual " + data.purpose + " use");
        verify(!/directory/i.test(hint), "The create placeholder calls its destination a Folder");
        if (data.tag === "authors")
            verify(/;/.test(hint), "The Authors placeholder explains semicolon separation");
    }
}
