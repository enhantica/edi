// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import EasyApplication.Gui.Globals as EaGlobals
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
                tryCompare(dialog, "visible", false, 2000, "The previous form finishes closing before its window is destroyed");
            }
            tryVerify(() => !EaGlobals.Vars.showProjectDescriptionDialog, 2000, "Create cancellation releases its shared dialog flag before the fixture retires");
            Session.closeProject();
            app.destroy();
        }
        app = null;
        Turn.end(selected, message => test.warn(message));
    }
    function draft() {
        verify(Session.project === null, "Opening Project alone creates no project or work container");
        verify(!AppState.experimentPageEnabled, "Experiment remains disabled before any structure exists");
        Ui.click(test, Probe, app, "appBar.tab.structure");
        tryVerify(() => Session.project !== null, 2000, "Opening Structure supplies the invisible work container");
        verify(Session.needsSaveAs, "Untitled work has no owned saved destination");
        verify(Session.untitled, "Work remains unnamed until the Create form is accepted");
        compare(Session.project.title, "", "Work before Create has no default project title");
        compare(Session.project.path, "", "Work before Create owns no project folder");
        verify(!AppState.experimentPageEnabled, "Opening Structure without adding one does not enable Experiment");
        compare(findChild(app, "statusBar.project").valueText, "Undefined", "The status bar never presents the work container as a named project");
        return Session.project;
    }
    function work() {
        const p = draft();
        Ui.click(test, Probe, app, "structures.create");
        compare(p.structures.count, 1, "Structure is usable before a project is named");
        verify(AppState.experimentPageEnabled, "Adding a structure enables Experiment before Create");
        p.currentStructure.cell.lengthA.value = 7.125;
        Ui.click(test, Probe, app, "appBar.tab.experiment");
        Ui.click(test, Probe, app, "experiments.create");
        compare(p.experiments.count, 1, "An experiment can be added once the unnamed work contains a structure");
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
        const page = Ui.page(app).item;
        compare(page.defaultInfo, "No project yet", "The Project page hides the work container until Create");
        compare(findChild(app, "statusBar.project").valueText, "Undefined", "Returning to Project does not expose an invented project name");
        Ui.click(test, Probe, app, "appBar.button.reset");
        const question = findChild(app, "unsavedChanges");
        tryCompare(question, "opened", true, 2000, "Clear protects the actual unsaved scientific edit");
        press(question.standardButton(Dialog.Discard));
        tryVerify(() => Session.project === null, 2000, "Clear discards the unnamed work after confirmation");
        compare(app.appBarCentralTabs.currentIndex, AppState.Page.Home, "Clear returns to the Home page");
        verify(!AppState.structurePageEnabled, "Clear resets the Structure tab to its startup state");
    }
    function test_b_first_save_names_and_preserves_work() {
        work();
        Ui.click(test, Probe, app, "appBar.button.save");
        const dialog = creation(), folder = fill(dialog);
        press(dialog.standardButton(Dialog.Ok));
        tryVerify(() => Session.project && !Session.needsSaveAs && !Session.project.modified, 5000, "Create after first Save commits the existing untitled work");
        verify(SettingsProof.fileObservation(folder, "project.edi").exists, "First Save writes into the selected parent and short-name folder");
        verify(Session.openProject(folder), "The first saved project reopens through the real loader");
        compare(Session.project.name, "lbco_hrpt-7", "The short name becomes the saved project name");
        compare(findChild(app, "statusBar.project").valueText, "lbco_hrpt-7", "The status bar shows the project name only after creation");
        compare(Session.project.title, "Neutron work before Save", "First Save retains the entered title");
        compare(Session.project.authors, "Ada Example; Lin Example", "First Save retains separated authors");
        compare(Session.project.description, "Unsaved cobalt study", "First Save retains the description");
        compare(Session.project.structures.count, 1, "Naming an untitled project does not replace its structure");
        compare(Session.project.experiments.count, 1, "Naming an untitled project does not replace its experiment");
        compare(Session.project.currentStructure.cell.lengthA.value, 7.125, "First Save and reopen preserve the independent scientific edit");
        workAfterClearAndCreate();
    }
    function workAfterClearAndCreate() {
        Session.closeProject();
        AppState.reset();
        AppState.open(AppState.Page.Project);
        work();
        Ui.click(test, Probe, app, "appBar.tab.project");
        Ui.click(test, Probe, app, "project.create");
        const dialog = creation(), folder = fill(dialog);
        press(dialog.standardButton(Dialog.Ok));
        tryVerify(() => Session.project && !Session.untitled && !Session.project.modified, 5000, "Create itself adopts and saves existing work, as first Save does");
        verify(Session.openProject(folder), "Work named through Create reopens through the ordinary loader");
        compare(Session.project.structures.count, 1, "Create keeps the structure made before a project existed");
        compare(Session.project.experiments.count, 1, "Create keeps the experiment made before a project existed");
        compare(Session.project.currentStructure.cell.lengthA.value, 7.125, "Create preserves the independent scientific edit");
    }
    function test_c_cancel_first_save_keeps_work() {
        const p = work();
        Ui.click(test, Probe, app, "appBar.button.save");
        const dialog = creation();
        keyClick(Qt.Key_Escape);
        tryCompare(dialog, "visible", false, 2000, "Escape cancels first Save through the real dialog");
        verify(Session.project === p && p.modified && Session.needsSaveAs, "Cancelling first Save preserves dirty untitled work");
        compare(p.currentStructure.cell.lengthA.value, 7.125, "Cancelling naming loses no scientific edit");
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
        verify(app.visible, "Pending Quit waits for the first-save form to finish");
        press(dialog.standardButton(Dialog.Ok));
        tryCompare(app, "visible", false, 5000, "Successful first Save resumes the pending Quit");
        verify(SettingsProof.fileObservation(folder, "project.edi").exists, "Quit's Save writes the chosen named project before closing");
        verify(Session.openProject(folder), "The project saved while quitting reopens normally");
        compare(Session.project.currentStructure.cell.lengthA.value, 7.125, "Quit's Save preserves the nontrivial untitled scientific edit");
    }
    function test_e_dialog_labels() {
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
