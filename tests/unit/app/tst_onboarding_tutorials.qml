// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import ReportAcceptance 1.0
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0
import "ExampleProjects.js" as Examples
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "OnboardingTutorials"
    when: windowShown
    property var app
    property var panel
    property var chooser
    property var launchButton
    SignalSpy {
        id: clickedSpy
        signalName: "clicked"
    }
    Component {
        id: application
        Main {}
    }
    function init() {
        Session.closeProject();
        app = application.createObject(null);
        verify(app !== null, "Tutorial acceptance opens the production window");
        AppState.open(AppState.Page.Home);
        verify(waitForRendering(app.contentItem), "Tutorial input starts on the rendered Home page");
        const named = Probe.objectsWithProperty(app, "objectName");
        const panels = named.filter(item => item.objectName === "tutorial");
        const choosers = named.filter(item => item.objectName === "tutorials");
        compare(panels.length, 1, "The window owns exactly one written tutorial panel");
        compare(choosers.length, 1, "The window owns exactly one Tutorials chooser");
        panel = panels[0];
        chooser = choosers[0];
        const buttons = Probe.objectsWithProperty(app, "text").filter(item => item.visible && item.text === "Tutorials" && typeof item.clicked === "function");
        compare(buttons.length, 1, "Home exposes the actual Tutorials action");
        launchButton = buttons[0];
    }
    function cleanup() {
        if (app && panel && panel.visible)
            panel.stop();
        clickedSpy.target = null;
        Session.closeProject();
        if (app)
            app.destroy();
        app = null;
        panel = null;
        chooser = null;
        launchButton = null;
    }
    function control(name) {
        if (name === "tutorial")
            return panel;
        if (name === "tutorials")
            return chooser;
        const root = name.startsWith("tutorial.") ? panel : chooser;
        const owned = Probe.objectsWithProperty(root, "objectName");
        const visual = Render.descendants(root.contentItem || root);
        const matches = owned.concat(visual.filter(item => !owned.includes(item))).filter(item => item.objectName === name);
        compare(matches.length, 1, "The tutorial exposes its actual control " + name);
        return matches[0];
    }
    function activate(item, name, localLayout = false) {
        tryVerify(() => item.visible && item.enabled && Ui.exposed(item), 2000, "The tutorial action is exposed and enabled before input: " + name);
        verify(waitForPolish(localLayout ? item : app), "The tutorial control and its required layout finish before input: " + name);
        app.update();
        const point = Ui.clickPoint(item);
        verify(point !== null, "The tutorial input point remains inside the exposed control: " + name);
        if (item.objectName.startsWith("tutorials.row.")) {
            mouseClick(item, point.x, point.y);
        } else {
            clickedSpy.target = item;
            clickedSpy.clear();
            verify(clickedSpy.valid, "The actual tutorial button exposes its clicked signal: " + name);
            mouseClick(item, point.x, point.y);
            compare(clickedSpy.count, 1, "The actual tutorial action is activated exactly once: " + name);
        }
    }
    function clickControl(name) {
        activate(control(name), name);
    }
    function startTutorial(id) {
        clickControl("tutorials.row." + id);
        tryCompare(control("tutorials"), "visible", false, 2000, "The Tutorials chooser closes before the written-step controls receive input");
        tryCompare(control("tutorial"), "opened", true, 2000, "The written tutorial panel finishes opening before its steps are used");
        if (id !== "interface") {
            compare(Session.project, null, "Scientific tutorials wait for the learner to create a project");
            const steps = JSON.parse(OnboardingProbe.sourceText("app/tutorials/manifest.json")).tutorials.find(entry => entry.id === id).steps;
            const createStep = steps.findIndex(step => step.target === "project.create");
            verify(createStep >= 0, "A scientific tutorial begins with the user's Create project action");
            compare(app.appBarCentralTabs.currentIndex, AppState.Page.Home, "The scientific lesson begins at Home Start");
            Ui.click(test, Probe, app, "home.start");
            tryCompare(panel, "step", createStep, 2000, "The learner's Start action advances to Project creation");
            Ui.click(test, Probe, app, "project.create");
            const dialog = SettingsProof.creationDialog(app);
            verify(dialog !== null, "The ownership witness uses the real Create project form");
            tryCompare(dialog, "opened", true, 2000, "The creation form opens before the learner enters its name");
            dialog.projectParentDirectory = String(SettingsProof.emptyDirectory());
            const field = findChild(dialog, "createProject.name");
            verify(field !== null && SettingsProof.type(field, "owned_" + id), "The ownership witness supplies a real learner-entered project name");
            activate(dialog.standardButton(Dialog.Ok), "Create learner project");
            tryVerify(() => Session.project !== null && Session.project.name === "owned_" + id, 3000, "The learner's project exists before its ownership is exercised");
        }
    }
    function nextStep(index, total) {
        clickControl("tutorial.next");
        tryCompare(control("tutorial.progress"), "text", "Step " + (index + 1) + " of " + total, 2000, "Next advances to the requested written step before another action");
    }
    function tutorials() {
        activate(launchButton, "Home Tutorials");
        tryCompare(control("tutorials"), "opened", true, 2000, "The Tutorials chooser finishes opening before a script is selected");
        const entries = JSON.parse(OnboardingProbe.sourceText("app/tutorials/manifest.json")).tutorials;
        for (const entry of entries) {
            if (!entry.steps && entry.tour) {
                const pages = JSON.parse(OnboardingProbe.sourceText("app/tutorials/" + entry.tour)).pages;
                entry.steps = pages.reduce((steps, page) => steps.concat(page.steps.map(step => Object.assign({}, step, {
                            page: page.page
                        }))), []);
            }
        }
        compare(entries.length, 3, "The Tutorials popup uses the three built-in written scripts");
        return entries;
    }
    function test_popup_lists_the_shared_scripts() {
        for (const entry of tutorials()) {
            const row = control("tutorials.row." + entry.id);
            verify(row.visible && row.enabled, "Each built-in script has an available Tutorials row");
            verify(Probe.objectsWithProperty(row, "text").some(item => item.text === entry.title) || row.text === entry.title, "The popup displays the title from the script it opens");
        }
    }
    function test_scientific_tutorial_does_not_modify_the_user_project_data() {
        return [
            {
                tag: "simulation",
                id: "simulation"
            },
            {
                tag: "fitting",
                id: "fitting"
            }
        ];
    }
    function test_scientific_tutorial_does_not_modify_the_user_project(data) {
        verify(Examples.bundled(test, Session, "pd-neut-cwl_cosio-d20"), "The isolation check retains an actual user project");
        const original = Session.project;
        original.description = "unsaved user description retained through tutorial";
        tutorials();
        startTutorial(data.id);
        verify(Session.project !== null && Session.project !== original, "The learner creates a separate temporary project after entering the scientific tutorial");
        compare(original.description, "unsaved user description retained through tutorial", "Starting a tutorial preserves unsaved edits on the user's own project");
        clickControl("tutorial.stop");
        tryCompare(control("tutorial"), "visible", false, 2000, "Stopping closes the written tutorial panel");
        compare(Session.project, original, "Stopping the written tutorial restores the exact user's project object");
        compare(Session.project.description, "unsaved user description retained through tutorial", "Stopping a tutorial preserves the user's unsaved edits");
    }
    function test_script_completion_offers_keep_and_discard_data() {
        return [
            {
                tag: "keep",
                keep: true
            },
            {
                tag: "discard",
                keep: false
            }
        ];
    }
    function test_script_completion_offers_keep_and_discard(data) {
        verify(Examples.bundled(test, Session, "pd-neut-cwl_cosio-d20"), "Completion choices retain a real user's project");
        const original = Session.project;
        const entries = tutorials();
        const entry = entries.find(item => item.id === "simulation");
        startTutorial("simulation");
        const temporary = Session.project;
        verify(temporary !== null && temporary !== original, "Completion choices refer to the tutorial's temporary project");
        // Scientific progression has its own actor; this case exercises the real
        // completion actions after the learner has created the owned project.
        panel.step = entry.steps.length - 1;
        panel.show();
        tryCompare(control("tutorial"), "atEnd", true, 2000, "The completion choices replace Next only at the final written step");
        const keep = control("tutorial.keep"), discard = control("tutorial.discard");
        compare(keep.text, "Keep working on " + temporary.name, "The keep choice names the actual tutorial project");
        compare(discard.text, "Return to my project", "The return choice describes restoring the prior user project");
        activate(data.keep ? keep : discard, data.keep ? "tutorial.keep" : "tutorial.discard");
        tryCompare(control("tutorial"), "visible", false, 2000, "The chosen completion action closes the written tutorial panel");
        compare(Session.project, data.keep ? temporary : original, "Keep retains the tutorial project and Discard restores the user's project");
    }
    function clickApp(name) {
        tryVerify(() => app.pagesBuilt === app.pagesWanted, 5000, "Workflow pages finish loading before the next tutorial accident input");
        tryVerify(() => Ui.control(Probe, app, name) !== null, 2000, "The requested app action is present before tutorial input: " + name);
        const item = Ui.control(Probe, app, name);
        activate(item, name, true);
        if (name.includes(".tab."))
            tryCompare(item, "checked", true, 2000, "The actual tutorial accident input selects its requested tab: " + name);
    }
    function userProject() {
        verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"))), "Tutorial accidents start with a real user's saved project");
        tryCompare(Session.project, "calculating", false, 5000, "The user's actual project finishes loading");
        Session.project.description = "user edit awaiting save before Tutorials";
        OnboardingProbe.rememberProject(Session.project);
        return {
            path: Session.project.path,
            location: Session.projectLocation,
            needsSaveAs: Session.needsSaveAs
        };
    }
    function rememberedIntact(before) {
        verify(OnboardingProbe.rememberedAlive(), "No tutorial action deletes the user's original project before consent");
        compare(OnboardingProbe.rememberedProperty("description"), "user edit awaiting save before Tutorials", "The original user's unsaved description survives accidental actions");
        compare(OnboardingProbe.rememberedProperty("path"), before.path, "The user's backing folder is not moved by a tutorial");
        verify(OnboardingProbe.rememberedProperty("modified"), "The user's original project remains unsaved until its own save");
    }
    function returnedIntact(before) {
        rememberedIntact(before);
        verify(OnboardingProbe.isRemembered(Session.project), "Stopping returns the exact original user project");
        compare(Session.projectLocation, before.location, "Stopping retains the original save destination");
        compare(Session.needsSaveAs, before.needsSaveAs, "Stopping retains the original Save versus Save as behavior");
    }
    function named(name) {
        const matches = Probe.objectsWithProperty(app, "objectName").filter(item => item.objectName === name);
        compare(matches.length, 1, "The real application owns one requested dialog: " + name);
        return matches[0];
    }
    function test_home_reentry_cannot_replace_the_user_project_data() {
        const rows = [];
        for (const first of ["simulation", "fitting"])
            for (const second of ["simulation", "fitting", "interface"])
                rows.push({
                    tag: first + "-then-" + second,
                    first: first,
                    second: second
                });
        return rows;
    }
    function test_home_reentry_cannot_replace_the_user_project(data) {
        // Accident: the panel is nonmodal, so the user returns Home and picks another tutorial.
        const before = userProject();
        tutorials();
        startTutorial(data.first);
        clickApp("appBar.tab.home");
        tutorials();
        const second = control("tutorials.row." + data.second);
        if (second.enabled)
            activate(second, "tutorials.row." + data.second);
        else
            keyClick(Qt.Key_Escape);
        // A disabled entry or a consent question may legitimately block reentry.
        // Cancel any such question through its real standard button; never consent to data loss.
        const questions = Probe.objectsWithProperty(app, "standardButtons").filter(item => item.visible && typeof item.standardButton === "function");
        for (const question of questions) {
            const cancel = question.standardButton(Dialog.Cancel);
            if (cancel && cancel.visible && cancel.enabled)
                activate(cancel, "Cancel accidental tutorial replacement");
        }
        verify(waitForPolish(app), "A second tutorial selection finishes its actual page layout");
        rememberedIntact(before);
        // Refusing reentry, asking first, or keeping the first owner are all valid policies.
        // No dialog receives Save/Discard consent from this gate.
        if (panel.visible) {
            if (panel.atEnd && !panel.temporary)
                clickControl("tutorial.close");
            else if (panel.atEnd && panel.temporary)
                clickControl("tutorial.discard");
            else
                clickControl("tutorial.stop");
        }
        returnedIntact(before);
    }
    function test_unsaved_set_aside_project_blocks_replacement_and_quit_data() {
        return [
            {
                tag: "quit",
                quit: true
            },
            {
                tag: "replace",
                quit: false
            }
        ];
    }
    function test_unsaved_set_aside_project_blocks_replacement_and_quit(data) {
        // Accident: Fitting is an unmodified example; Quit/Open checks only that active example.
        const before = userProject();
        tutorials();
        startTutorial("fitting");
        verify(!Session.project.modified, "The accident reaches an unmodified tutorial over a modified user project");
        let ran = false;
        if (data.quit)
            app.close();
        else
            AppState.afterChanges(() => ran = true);
        const question = named("unsavedChanges");
        tryVerify(() => question.visible || ran || !app.visible, 2000, "The real quit or replacement reaches its guard or continuation");
        verify(app.visible && !ran && question.visible, "Quit and project replacement require consent for the unsaved set-aside user project");
        activate(question.standardButton(Dialog.Cancel), "Cancel unsaved user changes");
        rememberedIntact(before);
        clickControl("tutorial.stop");
        returnedIntact(before);
    }
    function test_pending_text_edit_survives_home_and_tutorial_entry() {
        // Accident: a user types in Project Text, then selects a tutorial without Apply.
        const before = userProject();
        clickApp("appBar.tab.project");
        clickApp("sideBar.tab.text");
        Preferences.textShow = "editable";
        tryVerify(() => Ui.control(Probe, app, "text.view") !== null, 2000, "The actual Project Text editor finishes loading before keyboard input");
        const editor = Ui.control(Probe, app, "text.view");
        tryCompare(editor, "readOnly", false, 2000, "The accident reaches the actual editable Project Text tab");
        editor.forceActiveFocus();
        keyClick(Qt.Key_End, Qt.ControlModifier);
        keyClick(Qt.Key_Return);
        for (const character of "# pending-text-edit-must-survive")
            keyClick(character, Qt.NoModifier, 0);
        keyClick(Qt.Key_Return);
        tryVerify(() => AppState.textEdit !== null, 2000, "Real keyboard input creates an unapplied Text-tab edit");
        const pending = AppState.textEdit;
        const text = editor.text;
        verify(text.includes("pending-text-edit-must-survive"), "The pending edit belongs to the real text editor");
        clickApp("appBar.tab.home");
        const prompts = Probe.objectsWithProperty(app, "objectName").filter(item => item.objectName === "text.discard" && item.visible);
        if (prompts.length) {
            activate(prompts[0].standardButton(Dialog.Cancel), "Cancel unapplied Text edit");
            compare(AppState.textEdit, pending, "Cancel retains the owner of the pending Text edit");
            compare(editor.text, text, "Cancel retains every byte typed before tutorial entry");
            returnedIntact(before);
            return;
        }
        tutorials();
        clickControl("tutorials.row.fitting");
        verify(waitForPolish(app), "Tutorial entry finishes before pending edit ownership is inspected");
        verify(AppState.textEdit === pending && pending.dirty, "Tutorial entry cannot destroy or detach an unapplied Text edit without consent");
        compare(editor.text, text, "An unapplied Text edit survives tutorial entry byte for byte");
        rememberedIntact(before);
    }
}
