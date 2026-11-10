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

TestCase {
    id: test
    name: "UserActionLogging"
    when: windowShown
    property var app
    property var form
    property string endpoint
    property string level
    property bool logging: false
    property bool fitStarted: false
    Connections {
        target: Session.project ? Session.project.fit : null
        function onRunningChanged() {
            if (test.logging && Session.project.fit.running)
                test.fitStarted = true;
        }
    }
    property string secret: "NeverLogThisPrivateSentence8274"
    Component {
        id: application
        Main {}
    }
    function init() {
        Session.closeProject();
        endpoint = Preferences.feedbackEndpoint;
        level = Preferences.loggingLevel;
        Preferences.feedbackEndpoint = "https://stub.example.invalid/feedback";
        Preferences.loggingLevel = "Info";
        app = application.createObject(null, {
            width: 1300,
            height: 950
        });
        verify(app !== null, "Interaction logging runs in the real application host");
        OnboardingProbe.startClock();
        AppState.open(AppState.Page.Home);
        settle();
        form = named("feedback.form");
        form.transport = function (url, payload, completed) {
            completed(201);
        };
    }
    function cleanup() {
        if (logging)
            OnboardingProbe.finishHostLog();
        logging = false;
        const tour = named("tutorial");
        if (tour && tour.visible)
            tour.stop();
        Session.closeProject();
        if (app)
            app.destroy();
        app = null;
        OnboardingProbe.stopClock();
        Preferences.feedbackEndpoint = endpoint;
        Preferences.loggingLevel = level;
    }
    function named(name) {
        const owned = Probe.objectsWithProperty(app, "objectName");
        const popup = owned.find(item => item.objectName === "tutorials");
        const visual = popup ? Ui.itemsWithProperty(popup.contentItem, "objectName") : [];
        return owned.concat(visual).find(item => item.objectName === name) || null;
    }
    function settle() {
        for (let i = 0; i < 5; ++i) {
            OnboardingProbe.incubate(app);
            OnboardingProbe.advanceClock(200);
        }
        tryVerify(() => {
            for (let i = 0; i < 10 && app.pagesBuilt !== app.pagesWanted; ++i)
                OnboardingProbe.incubate(app);
            return app.pagesBuilt === app.pagesWanted;
        }, 5000, "The actual asynchronous pages exist before an interaction is attempted");
        verify(waitForPolish(app), "Real controls finish layout under the injected animation clock");
    }
    function press(item) {
        verify(item !== null && item.enabled, "The logging witness reaches an enabled actual control");
        Ui.scrollIntoView(item);
        settle();
        const point = Ui.clickPoint(item);
        verify(point !== null, "The logging witness clicks within the exposed actual control");
        mouseClick(item, point.x, point.y, Qt.LeftButton, Qt.NoModifier, 0);
        settle();
    }
    function click(name) {
        const found = Ui.control(Probe, app, name) || named(name);
        press(Ui.target(found));
    }
    function type(field, value) {
        verify(field && typeof field.selectAll === "function", "Committed-field logging is exercised through an editable real field");
        press(field);
        field.selectAll();
        keyClick(Qt.Key_Backspace);
        for (const character of value)
            keyClick(character);
        keyClick(Qt.Key_Tab);
        settle();
        if (Number.isFinite(Number(value)))
            compare(Number(field.text), Number(value), "The real numeric field commits the requested value");
        else
            compare(field.text.trim(), value, "The logging witness commits its actual keyboard input");
    }
    function openFeedback() {
        AppState.open(AppState.Page.Home);
        settle();
        const link = Probe.objectsWithProperty(app, "text").find(item => item.text === "Help and feedback" && typeof item.clicked === "function" && Ui.rendered(item));
        press(link);
        tryCompare(form, "opened", true, 2000, "The real Home link opens feedback before control input");
    }
    function fixture() {
        const path = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
        verify(Session.openProject(path), "A disposable measured project supplies real editable controls and a fit");
        settle();
        return path;
    }
    function begin() {
        verify(OnboardingProbe.startHostLog().length > 0, "Action receipts use the actual run logger with private app-data storage and fixed clock");
        logging = true;
        fitStarted = false;
        RunLog.level = "Info";
        OnboardingProbe.emitNativeMessage();
    }
    function end() {
        const text = OnboardingProbe.finishHostLog();
        logging = false;
        verify(text.includes("host-cpp-sentinel"), "A native Info control proves the real logger is enabled");
        verify(!text.includes(secret), "No typed free text reaches any level or field of the run log");
        verify(!text.includes(OnboardingProbe.homePath()) && !text.includes("SyntheticLogUser8274"), "No home path or user name reaches the run log");
        // Independent packet grammar, not an implementation-produced parser.
        return text.split(/\r?\n/).filter(line => /^\d{2}:\d{2}:\d{2}\.\d{3}  \+(\d\.\d{3}|\d{2}\.\d{2}|\d{3}\.\d|\d{5})  INFO      (app   |qml   |crysta)  .+  \S+$/.test(line));
    }
    function test_shared_control_has_one_private_info_receipt_data() {
        return ["button", "tab", "combobox", "checkbox", "numeric", "message", "subject", "name", "email", "affiliation", "project-title", "project-description"].map(kind => ({
                    tag: kind,
                    kind: kind
                }));
    }
    function test_shared_control_has_one_private_info_receipt(data) {
        // Class: missing, duplicate or privacy-leaking shared-control receipts.
        // Accident: an ordinary click, choice or focus-out commit is the only clue
        // before a later failure; neither nested handlers nor raw input may leak.
        let control, value = "", action = /\b(click|activate)\b/i;
        if (data.kind === "tab" || data.kind === "numeric" || data.kind.startsWith("project-")) {
            fixture();
            if (data.kind === "tab") {
                AppState.open(AppState.Page.Project);
                settle();
                control = named("appBar.tab.analysis");
            } else if (data.kind === "numeric") {
                AppState.open(AppState.Page.Structure);
                settle();
                const group = Ui.find(Ui.page(app), "group.cell", true);
                verify(group !== null, "The numeric witness locates its real cell group");
                if (group.collapsed)
                    press(group.titleArea);
                compare(group.collapsed, false, "The injected clock completes the cell group expansion");
                const wrapper = Ui.control(Probe, app, "cell.length_a");
                verify(wrapper !== null, "The numeric witness reaches the actual cell-length control");
                control = typeof wrapper.selectAll === "function" ? wrapper : Render.descendants(wrapper).find(item => typeof item.selectAll === "function");
                value = "4.125";
            } else {
                AppState.open(AppState.Page.Project);
                settle();
                control = named(data.kind === "project-title" ? "project.title" : "project.description");
                value = secret;
            }
        } else {
            openFeedback();
            if (data.kind === "button")
                control = named("feedback.preview");
            else if (data.kind === "combobox")
                control = named("feedback.kind");
            else if (data.kind === "checkbox")
                control = named("feedback.include");
            else if (data.kind === "message") {
                control = named("feedback.text");
                value = secret;
            } else if (data.kind === "subject") {
                control = named("feedback.subject");
                value = secret;
            } else {
                const labels = {
                    name: "Name (optional)",
                    email: "E-mail (optional)",
                    affiliation: "Affiliation (optional)"
                };
                control = Probe.objectsWithProperty(form, "placeholderText").find(item => item.placeholderText === labels[data.kind]);
                value = secret;
            }
        }
        verify(control !== null && control !== undefined, "Each required shared-control kind exists in the actual application");
        // A named titled wrapper is allowed; require the receipt's public control ID.
        let owner = control;
        while (owner && !owner.objectName)
            owner = owner.parent;
        verify(owner && owner.objectName.length > 0, "Each logged interaction has a stable objectName");
        const name = data.kind === "numeric" ? "cell.length_a" : owner.objectName;
        begin();
        if (data.kind === "combobox") {
            press(control);
            const index = (control.currentIndex + 1) % control.count;
            value = control.textAt(index);
            const option = Render.descendants(control.popup.contentItem).find(item => item.text === value && typeof item.clicked === "function" && Ui.rendered(item));
            press(option);
            compare(control.currentIndex, index, "The choice receipt follows a real changed combobox selection");
            value = String(control.currentValue === undefined ? control.currentText : control.currentValue);
            action = /\b(set|select|choose|change)\b/i;
        } else if (data.kind === "checkbox") {
            const before = control.checked;
            press(control);
            compare(control.checked, !before, "The checkbox receipt follows an actual state change");
            action = /\b(set|toggle|check|change)\b/i;
        } else if (value) {
            type(control, value);
            action = /\b(set|edit|commit|change)\b/i;
        } else
            press(control);
        const receipts = end().filter(line => line.includes(name) && action.test(line));
        compare(receipts.length, 1, "One user interaction writes exactly one Info receipt naming its objectName and action");
        if (data.kind === "numeric" || data.kind === "combobox")
            verify(receipts[0].includes(value), "Numeric and choice receipts include the committed public value");
    }
    function test_workflow_action_has_an_info_receipt_data() {
        return ["page", "tab", "project-create", "project-open", "project-save", "structure-add", "structure-remove", "experiment-add", "experiment-remove", "fit", "tutorial", "feedback"].map(kind => ({
                    tag: kind,
                    kind: kind
                }));
    }
    function test_workflow_action_has_an_info_receipt(data) {
        // Class: silent workflow boundaries. Each accident path performs the real
        // action before demanding its receipt; setup cannot supply a false match.
        let input = "";
        if (!["project-create", "tutorial", "feedback"].includes(data.kind))
            input = fixture();
        if (data.kind.startsWith("structure"))
            AppState.open(AppState.Page.Structure);
        if (data.kind.startsWith("experiment"))
            AppState.open(AppState.Page.Experiment);
        if (data.kind.startsWith("project") || data.kind === "page" || data.kind === "tab")
            AppState.open(AppState.Page.Project);
        if (data.kind === "fit") {
            AppState.open(AppState.Page.Analysis);
            const parameters = Probe.rows(Session.project.parameters).map(row => row.parameter).filter(item => item && item.fittable);
            verify(parameters.length > 0 && Session.project.setParametersFree(parameters, true), "The fit receipt witness has real measured free parameters");
            tryCompare(Session.project, "calculating", false, 10000, "The actual measured fixture is ready before fitting");
        }
        if (data.kind === "feedback") {
            openFeedback();
            type(named("feedback.text"), secret);
        }
        settle();
        begin();
        let required = [];
        if (data.kind === "page") {
            click("appBar.tab.analysis");
            required = [/analysis/i];
        } else if (data.kind === "tab") {
            click("sideBar.tab.text");
            required = [/\b(tab|select|click)\b.*text|text.*\b(tab|select|click)\b/i];
        } else if (data.kind === "project-create") {
            click("project.create");
            const dialog = SettingsProof.creationDialog(app);
            verify(dialog !== null, "The project receipt witness opens the real creation dialog");
            dialog.projectParentDirectory = OnboardingProbe.homePath();
            type(findChild(dialog, "createProject.name"), "logging-project");
            press(dialog.standardButton(Dialog.Ok));
            tryVerify(() => Session.project && Session.project.name === "logging-project", 3000, "Actual user creation makes the named private project");
            required = [/project.*creat|creat.*project/i];
        } else if (data.kind === "project-open") {
            Session.closeProject();
            settle();
            click("project.open");
            click("open.folder");
            press(named("open.choice").standardButton(Dialog.Ok));
            let dialogs = [];
            tryVerify(() => {
                dialogs = SettingsProof.projectFileDialogs(app, true);
                return dialogs.length === 1;
            }, 2000, "Open exposes its actual folder chooser");
            verify(SettingsProof.chooseProjectLocation(dialogs[0], input, true), "The injected chooser opens the disposable real project");
            tryVerify(() => Session.project !== null, 3000, "The selected project actually opens before the receipt is read");
            required = [/project.*open|open.*project/i];
        } else if (data.kind === "project-save") {
            click("project.saveAs");
            const choice = named("saveAs.choice");
            verify(choice !== null, "Save As presents its real format choice before the destination");
            press(choice.standardButton(Dialog.Ok));
            let dialogs = [];
            tryVerify(() => {
                dialogs = SettingsProof.projectFileDialogs(app, false);
                return dialogs.length === 1;
            }, 2000, "Save As exposes its actual destination chooser");
            const destination = SettingsProof.childUrl(SettingsProof.emptyDirectory(), "saved-project");
            verify(SettingsProof.chooseProjectLocation(dialogs[0], destination, false), "The injected chooser supplies a private save destination");
            verify(SettingsProof.text(destination, "project.edi").length > 0, "The real Save As writes the project before its receipt is read");
            required = [/project.*sav|sav.*project/i];
        } else if (/^(structure|experiment)-/.test(data.kind)) {
            const structure = data.kind.startsWith("structure"), add = data.kind.endsWith("add"), model = structure ? Session.project.structures : Session.project.experiments;
            const before = Probe.rows(model).length, stem = structure ? "structures" : "experiments";
            click(stem + (add ? ".create" : ".remove.0"));
            tryVerify(() => Probe.rows(model).length === before + (add ? 1 : -1), 2000, "The real list action changes its actual project model");
            required = [new RegExp((structure ? "structure" : "experiment") + ".*" + (add ? "(add|creat)" : "(remov|delet)") + "|" + (add ? "(add|creat)" : "(remov|delet)") + ".*" + (structure ? "structure" : "experiment"), "i")];
        } else if (data.kind === "fit") {
            click("statusBar.fit.button");
            tryVerify(() => fitStarted, 2000, "The real status-bar action starts fitting");
            tryCompare(Session.project.fit, "running", false, 15000, "The actual fit completes before its end receipt is inspected");
            required = [/fit.*start|start.*fit/i, /fit.*(end|finish|complet)|(?:end|finish|complet).*fit/i];
        } else if (data.kind === "tutorial") {
            const link = Probe.objectsWithProperty(app, "text").find(item => item.text === "Tutorials" && typeof item.clicked === "function" && Ui.rendered(item));
            press(link);
            press(named("tutorials.row.pd-neut-cwl_lbco_simulation"));
            const tour = named("tutorial");
            tryCompare(tour, "opened", true, 2000, "The real row starts the tutorial before its receipt is inspected");
            press(named("tutorial.next"));
            press(named("tutorial.stop"));
            required = [/tutorial.*start|start.*tutorial/i, /tutorial.*step|step.*tutorial/i, /tutorial.*stop|stop.*tutorial/i];
        } else {
            press(named("feedback.send"));
            required = [/feedback.*sent|sent.*feedback/i];
        }
        const receipts = end();
        for (const expression of required)
            verify(receipts.some(line => expression.test(line)), "The actual user action writes its own Info lifecycle receipt: " + data.kind + " / " + expression);
    }
}
