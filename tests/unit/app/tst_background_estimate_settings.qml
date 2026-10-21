import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "BackgroundEstimateSettings"
    when: windowShown
    property var appWindow
    property var sidebarPane
    property var enablementGroup
    Component { id: application; Main {} }
    Component { id: estimateGroup; BackgroundExtrasGroup { width: 320; z: 1000 } }
    Component { id: manualGroup; BackgroundGroup { width: 320; y: 75; z: 1000 } }
    function init() {
        Session.closeProject();
        sidebarPane = null;
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Saved estimation settings must use the production app window");
        verify(waitForRendering(appWindow.contentItem), "The settings window must render");
    }
    function cleanup() {
        if (enablementGroup) enablementGroup.destroy();
        enablementGroup = null;
        sidebarPane = null;
        Session.closeProject();
        appWindow.destroy();
        Probe.releaseScratchProjects();
    }
    function objects(root, property) {
        const items = Probe.objectsWithProperty(root, property).concat(Ui.itemsWithProperty(root, property));
        return items.filter((item, index) => items.indexOf(item) === index);
    }
    function points() {
        return Probe.rows(Session.project.currentExperiment.background).map(row => [row.position, row.intensity.value]);
    }
    function cases() {
        return JSON.parse(Probe.readFile("tests/fixtures/background_estimate/settings-cases.json"));
    }
    function openCase(name) {
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/" + name)),
               "The app must load the same saved auto-mode project as CLI and Python: " + name);
    }
    function awaitAutomatic(name) {
        const fixture = cases()[name];
        const reference = JSON.parse(Probe.readFile("tests/fixtures/background_estimate/reference.json"));
        const expected = reference.cases.hrpt.methods[fixture.method][fixture.variant].anchors;
        tryVerify(() => !Session.project.calculating && points().length === expected.length &&
                  points().some(point => point[1] !== 0), 2000,
                  "An auto-mode project must replace its stale zero points before publishing the app calculation");
        const actual = points();
        compare(actual.length, expected.length, "Automatic app calculation must retain the independent anchor count");
        actual.forEach((point, index) => {
            verify(Math.abs(point[0] - expected[index][0]) <= 1e-9,
                   "Automatic app calculation must select the independent reference samples");
            const atol = fixture.method === "snip" ? 1e-12 : 1e-9;
            const rtol = fixture.method === "snip" ? 1e-10 : 1e-6;
            verify(Math.abs(point[1] - expected[index][1]) <= atol + rtol * Math.abs(expected[index][1]),
                   "Automatic app calculation must meet the unchanged independent method tolerance");
        });
    }
    function savedSettings(destination) {
        const text = SettingsProof.text(destination, "experiments/bank.edi");
        const result = {width: null, smoothness: null, n_points: null, max_terms: null};
        text.split(/\r?\n/).forEach(line => {
            const match = line.match(/^_background_estimate\.([a-z_]+)\s+(\S+)/);
            if (!match) return;
            const name = match[1], value = match[2];
            result[name] = value === "." || value === "?" ? null :
                name === "use_model" ? (/^(true|yes|1)$/i.test(value) ? "subtract" :
                    /^(false|no|0)$/i.test(value) ? "ignore" : value) :
                ["width", "smoothness", "n_points", "max_terms", "tolerance"].indexOf(name) >= 0 ? Number(value) : value;
        });
        return result;
    }
    function pane(tier) {
        Ui.click(test, Probe, appWindow, "appBar.tab.experiment");
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1,
                  2000, "The Experiment page must enter the actual viewport before reading its sidebar");
        const label = tier === "basic" ? "Main" : "Extra";
        const tabItems = objects(Ui.page(appWindow), "text").filter(control =>
            ["Main", "Extra"].indexOf(String(control.text).trim()) >= 0);
        const tabs = tabItems.filter(control => String(control.text).trim() === label &&
            control.checked !== undefined && typeof control.clicked === "function");
        compare(tabs.length, 1, "The active Experiment sidebar must expose its " +
                label + " tab control; observed=" + JSON.stringify(tabItems.map(control => ({
                    objectName: control.objectName, text: String(control.text), checked: control.checked,
                    visible: control.visible, width: control.width, inPane: Ui.inPane(control)
                }))));
        if (!tabs[0].checked) pointer(tabs[0]);
        tryCompare(tabs[0], "checked", true, 1000, "Real input must select the requested estimate settings tab");
        let sidebar = tabs[0].parent;
        while (sidebar && sidebar.items === undefined) sidebar = sidebar.parent;
        const paneIndex = tier === "basic" ? 0 : 1;
        verify(sidebar !== null && sidebar.items.length > paneIndex,
               "The Main/Extra tab control must belong to a sidebar with the selected content pane");
        sidebarPane = sidebar.items[paneIndex];
        tryVerify(() => sidebarPane.SwipeView.isCurrentItem &&
                  Math.abs(sidebarPane.mapToItem(sidebarPane.SwipeView.view, 0, 0).x) < 1,
                  2000, "The selected " + label + " sidebar pane must enter its actual viewport before inspecting controls");
        tryVerify(() => !Ui.moving(appWindow.contentItem), 2000,
                  "The selected estimate settings pane must finish moving before reading controls");
        verify(waitForPolish(appWindow, 2000), "The selected estimate settings pane must finish layout");
        verify(waitForRendering(appWindow.contentItem), "The selected estimate settings pane must render");
        tryVerify(() => Ui.groupNames(Ui.page(appWindow)).some(name => name.indexOf("background") >= 0),
                  2000, "The selected Main or Extra pane must expose its background category header");
        Ui.groupNames(Ui.page(appWindow)).filter(name => name.indexOf("background") >= 0).forEach(name =>
            Ui.expandGroup(test, Probe, appWindow, "group." + name));
    }
    function optionTokens(control) {
        const model = control.options || control.model;
        if (!model) return [];
        const count = typeof model.count === "number" ? model.count : model.length;
        if (typeof count !== "number") return [];
        return Array.from({length: count}, (_, index) => {
            if (typeof model.tokenAt === "function") return model.tokenAt(index);
            const entry = model[index];
            return typeof entry === "string" ? entry : entry && entry.token !== undefined ? entry.token : "";
        });
    }
    function selectors(tokens) {
        return objects(sidebarPane, "model").filter(control => Ui.inPane(control) &&
            optionTokens(control).slice().sort().join("|") === tokens.slice().sort().join("|"));
    }
    function selectorIdentity() {
        return JSON.stringify(objects(sidebarPane, "model").filter(control =>
            control.currentIndex !== undefined && typeof control.activated === "function").map(control => ({
            objectName: String(control.objectName), label: String(control.label), token: String(control.token),
            tokens: optionTokens(control).map(token => String(token)),
            inPane: Ui.inPane(control), enabled: control.enabled
        })));
    }
    function estimateButtons() {
        return objects(sidebarPane, "text").filter(control => Ui.inPane(control) && control.enabled &&
            typeof control.clicked === "function" && String(control.text).replace(/&|\u2026/g, "").trim() === "Estimate");
    }
    function pointer(control) {
        Ui.scrollIntoView(control);
        verify(waitForPolish(appWindow, 2000), "The selected estimate control must finish layout before input");
        verify(waitForRendering(appWindow.contentItem), "The selected estimate control must render before pointer input");
        Ui.scrollIntoView(control);
        const point = Ui.clickPoint(control);
        verify(point !== null, "The selected estimate control must expose a real pointer target; identity=" +
               String(control.objectName) + " text=" + String(control.text) +
               " visible=" + control.visible + " width=" + control.width + " height=" + control.height);
        let delay = 0;
        for (let parent = control.parent; parent; parent = parent.parent)
            if (typeof parent.pressDelay === "number") delay = Math.max(delay, parent.pressDelay + 1);
        mouseClick(control, point.x, point.y, undefined, undefined, delay);
    }
    function choose(control, token) {
        pointer(control);
        tryVerify(() => control.popup && control.popup.visible, 1000,
                  "Real input must open the saved estimate setting's choices");
        const index = optionTokens(control).indexOf(token);
        verify(index >= 0, "The saved estimate choice must offer the requested public token");
        verify(SettingsProof.key(control, Qt.Key_Home), "The first option must receive real keyboard input");
        for (let step = 0; step < index; ++step)
            verify(SettingsProof.key(control, Qt.Key_Down), "The option list must receive actual navigation input");
        verify(SettingsProof.key(control, Qt.Key_Return), "Return must activate the actual saved estimate option");
    }
    function valueField(labels, identity) {
        const fields = objects(sidebarPane, "label").filter(control => Ui.inPane(control) &&
            (identity ? String(control.objectName) === identity :
             labels.indexOf(String(control.label).toLowerCase()) >= 0) && control.fieldValue !== undefined);
        compare(fields.length, 1, "Extra must expose one estimate override field labelled " + labels.join(" or ") +
                (identity ? "; objectName=" + identity : ""));
        return fields[0];
    }
    function type(field, text) {
        Ui.scrollIntoView(field);
        const editors = objects(field, "text").filter(item => typeof item.selectAll === "function" && item.enabled && !item.readOnly);
        compare(editors.length, 1, "An estimate override must expose one writable text input");
        editors[0].forceActiveFocus();
        verify(SettingsProof.type(editors[0], text), "The override must receive real keyboard text in its app window");
        verify(SettingsProof.key(editors[0], Qt.Key_Return), "Return must commit the actual override editor");
    }
    function modelChoice() {
        const controls = objects(sidebarPane, "model").filter(control => Ui.inPane(control) &&
            String(control.objectName) === "background_estimate.use_model" &&
            control.currentIndex !== undefined && typeof control.activated === "function");
        compare(controls.length, 1, "Extra must expose one enabled selector with objectName background_estimate.use_model, model/options and activated role");
        compare(optionTokens(controls[0]).slice().sort().join("|"), "auto|ignore|subtract",
                "The calculated-peaks selector must offer exactly auto, subtract and ignore");
        return controls[0];
    }
    function test_saved_auto_project_matches_reference_data() {
        return [{tag: "auto-derived"}, {tag: "auto-overrides"}];
    }
    function test_saved_auto_project_matches_reference(data) {
        openCase(data.tag);
        awaitAutomatic(data.tag);
        const before = points();
        const destination = Probe.scratchProjectUrl();
        verify(Session.saveAs(destination), "The automatic app calculation must save its settings and points");
        const settings = savedSettings(destination);
        const expected = cases()[data.tag].settings;
        Object.keys(expected).forEach(name => compare(settings[name], expected[name],
            "Automatic app saving must retain the stored estimate setting: " + name +
            "; null means blank or absent, kept derived rather than replaced by a number"));
        Session.closeProject();
        verify(Session.openProject(destination), "An automatic estimate project must reload in the app");
        awaitAutomatic(data.tag);
        compare(JSON.stringify(points()), JSON.stringify(before), "An unchanged saved auto estimate must reload exactly");
        console.log("BACKGROUND_SETTINGS_RECEIPT " + JSON.stringify({case: data.tag, points: points(), settings: settings}));
    }
    function test_main_choice_and_extra_overrides_are_real_saved_controls() {
        openCase("auto-overrides");
        pane("basic");
        const modes = selectors(["manual", "auto"]);
        compare(modes.length, 1, "Main must expose one visible background-estimate mode selector with " +
                "options/model tokens manual and auto (the existing background_estimate.mode selector qualifies); " +
                "observed=" + selectorIdentity());
        compare(estimateButtons().length, 0, "Auto mode must disable the Main Estimate action");
        compare(selectors(["auto", "arpls", "snip", "fabc"]).length, 0,
                "The advanced estimate method belongs in Extra rather than Main");
        choose(modes[0], "manual");
        pane("extras");
        compare(selectors(["manual", "auto"]).length, 0, "The manual/auto choice must remain on Main");
        compare(estimateButtons().length, 0, "The Estimate action must remain on Main");
        const methods = selectors(["auto", "arpls", "snip", "fabc"]);
        compare(methods.length, 1, "Extra must expose one method selector with options/model tokens " +
                "auto, arpls, snip and fabc; observed=" + selectorIdentity());
        choose(methods[0], "fabc");
        type(valueField([], "background_estimate.width"), "7.25");
        type(valueField([], "background_estimate.smoothness"), "2468.5");
        type(valueField([], "background_estimate.tolerance"), "0.75");
        type(valueField([], "background_estimate.n_points"), "9");
        // Before: a Boolean checkbox. After: the saved three-way selector.
        const modelControl = modelChoice();
        compare(String(modelControl.label).trim().toLowerCase(), "calculated peaks",
                "The three-way selector must use the public Calculated peaks label");
        choose(modelControl, "subtract");
        const destination = Probe.scratchProjectUrl();
        verify(Session.saveAs(destination), "Actual Main and Extra inputs must save to the project category");
        const expected = {mode: "manual", method: "fabc", width: 7.25, smoothness: 2468.5, n_points: 9, tolerance: 0.75, in_peaks: "drop", use_model: "subtract"};
        const actual = savedSettings(destination);
        Object.keys(expected).forEach(name => compare(actual[name], expected[name],
            "Real Main and Extra controls must write the stored setting: " + name));
        console.log("BACKGROUND_MODEL_CONTROL " + JSON.stringify({objectName: String(modelControl.objectName), label: String(modelControl.label), use_model: actual.use_model}));
        console.log("BACKGROUND_SETTINGS_UI " + JSON.stringify(actual));
    }
    function test_blank_defaults_and_derived_hint_survive_save_reload() {
        // Before: unconditional subtraction. After: automatic model selection;
        // the override remains blank, with a whole-number derived hint.
        const input = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/hrpt"));
        const original = SettingsProof.text(input, "experiments/bank.edi");
        verify(original.length > 0, "The blank-default control must copy the committed measured project");
        verify(SettingsProof.write(input, "experiments/bank.edi",
               original.split(/\r?\n/).filter(line => !line.startsWith("_background_estimate.")).join("\n")),
               "The default control must remove every explicitly authored estimator setting");
        verify(Session.openProject(input), "The app must load a project with no estimate category");
        for (let turn = 0; turn < 2; ++turn) {
            pane("extras");
            const tolerance = valueField([], "background_estimate.tolerance");
            compare(String(tolerance.fieldValue), "", "A blank tolerance must remain a derived override in Extra");
            compare(String(tolerance.placeholderText), "2", "Extra must show the twice-noise default as the whole-number hint 2");
            compare(String(modelChoice().token), "auto", "Blank projects must select automatic calculated-peak handling");
            const destination = Probe.scratchProjectUrl();
            verify(Session.saveAs(destination), "Blank estimate defaults must save through the actual app");
            const stored = savedSettings(destination);
            verify(stored.tolerance === undefined || stored.tolerance === null,
                   "Saving a blank tolerance must retain the blank override with effective default 2");
            // Absent default tokens retain their declared default on reload.
            verify(stored.use_model === undefined || stored.use_model === "auto",
                   "Saving a blank policy must preserve effective auto, either implicit or explicit");
            verify(stored.in_peaks === undefined || stored.in_peaks === "move",
                   "Saving blank peak handling must retain effective move, implicit or explicit");
            Session.closeProject();
            verify(Session.openProject(destination), "The blank-default project must reload through the actual app");
        }
        console.log("BACKGROUND_BLANK_DEFAULTS tolerance=2 use_model=auto in_peaks=move saves=2");
    }
    function modelPolicy(authored, expected, chosen) {
        const input = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/hrpt"));
        const original = SettingsProof.text(input, "experiments/bank.edi");
        const text = original.split(/\r?\n/).filter(line => !line.startsWith("_background_estimate.")).join("\n")
            .replace("phase 0\n", "phase 3.25\n") +
            "\n_background_estimate.mode manual\n_background_estimate.use_model " + authored + "\n";
        verify(SettingsProof.write(input, "experiments/bank.edi", text),
               "The app policy input must retain measured data and its authored canonical or legacy value");
        enablementGroup = estimateGroup.createObject(appWindow.contentItem);
        verify(enablementGroup !== null, "Three-way selection must use the production Background Extra group");
        verify(Session.openProject(input), "The app must load every canonical policy and old Boolean: " + Session.lastError);
        enablementGroup.experiment = Session.project.currentExperiment;
        sidebarPane = enablementGroup;
        compare(Session.project.currentExperiment.pattern.stale, true,
                "The initial selector must be inspected before the first worker publication");
        const control = modelChoice();
        compare(String(control.token), expected, "The selector must retain canonical policy or migrate true/false to subtract/ignore");
        verify(control.enabled, "All three saved policy choices must be available before a calculated pattern exists");
        if (expected === "auto") {
            // Before: reason text under Background. After: only the resolved
            // combo hint remains there; actual estimates report to Messages.
            const notes = objects(sidebarPane, "text").filter(item => item.visible &&
                String(item.objectName) === "background_estimate.model_reason" && String(item.text).trim());
            compare(notes.length, 0, "Background must have no visible reason label background_estimate.model_reason; Auto reasons belong in Messages");
            compare(String(control.resolved), "ignore", "Before a calculation the Auto combo must retain its resolved ignore hint");
        }
        tryVerify(() => !Session.project.calculating && !Session.project.currentExperiment.pattern.stale,
                  2000, "The policy workflow must use the real app calculation");
        choose(control, chosen);
        const destination = Probe.scratchProjectUrl();
        verify(Session.saveAs(destination), "An actual calculated-peaks selection must save");
        const stored = SettingsProof.text(destination, "experiments/bank.edi");
        const tokens = stored.match(/^_background_estimate\.use_model\s+(\S+)/gm) || [];
        compare(tokens.length, 1, "Every app save must write exactly one calculated-peaks policy");
        compare(tokens[0].trim().split(/\s+/)[1], chosen, "The app must write the chosen canonical token, never a Boolean");
        Session.closeProject();
        verify(Session.openProject(destination), "The selected policy must reload through the app");
        enablementGroup.experiment = Session.project.currentExperiment;
        compare(String(modelChoice().token), chosen, "The real selector must restore the saved policy on reload");
        console.log("BACKGROUND_MODEL_POLICY " + JSON.stringify({authored: authored, canonical: expected, chosen: chosen, reloaded: String(modelChoice().token)}));
    }
    function test_model_policy_auto() { modelPolicy("auto", "auto", "subtract"); }
    function test_model_policy_subtract() { modelPolicy("subtract", "subtract", "ignore"); }
    function test_model_policy_ignore() { modelPolicy("ignore", "ignore", "auto"); }
    function test_model_policy_legacy_true() { modelPolicy("true", "subtract", "ignore"); }
    function test_model_policy_legacy_false() { modelPolicy("false", "ignore", "subtract"); }
    function test_auto_reason_is_information_for_each_estimate() {
        const input = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/hrpt"));
        const original = SettingsProof.text(input, "experiments/bank.edi");
        const text = original.split(/\r?\n/).filter(line => !line.startsWith("_background_estimate.")).join("\n")
            .replace("phase 0\n", "phase 3.25\n") +
            "\n_background_estimate.mode manual\n_background_estimate.use_model auto\n";
        verify(SettingsProof.write(input, "experiments/bank.edi", text),
               "The Messages control must use measured data, Auto and a nonzero calculated model");
        verify(Session.openProject(input), "The Auto information control must open in the actual app");
        tryVerify(() => !Session.project.calculating && !Session.project.currentExperiment.pattern.stale,
                  2000, "The information control must calculate a real nonzero model before Estimate");
        enablementGroup = manualGroup.createObject(appWindow.contentItem);
        verify(enablementGroup !== null, "Information actions must use the production Main BackgroundGroup");
        enablementGroup.experiment = Session.project.currentExperiment;
        sidebarPane = enablementGroup;
        verify(waitForPolish(enablementGroup), "The actual Main Estimate control must finish layout");
        Session.loadWarnings.dismissAll();
        for (let attempt = 0; attempt < 2; ++attempt) {
            const actions = estimateButtons();
            compare(actions.length, 1, "Main must expose one enabled clickable Estimate action for the Auto Messages workflow");
            pointer(actions[0]);
            tryVerify(() => Probe.rows(Session.loadWarnings).filter(row => row.severity === "information").length === attempt + 1,
                      1000, "Every actual Auto estimate, including an identical repeat, must append one information entry to Session.loadWarnings");
            const messages = Probe.rows(Session.loadWarnings).filter(row => row.severity === "information");
            const message = String(messages[attempt].message);
            verify(/subtract|ignore/i.test(message), "The Auto information entry must name its resolved subtract or ignore action");
            verify(/\d+(?:\.\d+)?\s*%/.test(message) && /below/i.test(message) && /noise/i.test(message),
                   "The Auto information entry must explain the measured share of points below the noise threshold");
            verify(/(?:^|[^\d.])1(?:\.0+)?\s*%/.test(message),
                   "The Auto information entry must state the independently declared one-percent decision rule");
            verify(Session.project.currentExperiment.backgroundEstimateUseModel === "auto",
                   "Reporting the resolved action must retain the saved Auto policy");
        }
        enablementGroup.destroy();
        enablementGroup = estimateGroup.createObject(appWindow.contentItem);
        verify(enablementGroup !== null, "The information control must inspect the production Extra Background group");
        enablementGroup.experiment = Session.project.currentExperiment;
        sidebarPane = enablementGroup;
        verify(waitForPolish(enablementGroup), "The production Extra group must finish its reason-text layout");
        const reason = String(Session.project.currentExperiment.estimateModelReason);
        const labels = objects(sidebarPane, "text").filter(item => item.visible && String(item.text).trim() &&
            (String(item.objectName) === "background_estimate.model_reason" ||
             (reason.length > 0 && String(item.text).indexOf(reason) >= 0)));
        compare(labels.length, 0, "The Background Extra pane must not duplicate the Auto reason shown in Messages");
        console.log("BACKGROUND_AUTO_MESSAGES information=2 repeated=true sidebarReason=false");
    }
    function test_point_keyboard_edit_sets_manual() {
        const input = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/readonly-line-segment"));
        const source = SettingsProof.text(input, "experiments/bank.edi");
        verify(SettingsProof.write(input, "experiments/bank.edi", source.replace("_background_estimate.mode manual", "_background_estimate.mode auto")),
               "The keyboard control must start with an Auto table before any included-data estimate");
        verify(Session.openProject(input), "The keyboard actor must load the bounded Auto-row control");
        // The real Main BackgroundGroup is hosted directly, keeping this saved
        // keyboard workflow bounded. Separate cases retain Main/Extra placement
        // and the independent saved-auto estimator equality checks.
        enablementGroup = manualGroup.createObject(appWindow.contentItem);
        verify(enablementGroup !== null, "The Manual keyboard actor must use the production Main BackgroundGroup");
        enablementGroup.experiment = Session.project.currentExperiment;
        sidebarPane = enablementGroup;
        verify(waitForPolish(enablementGroup), "The actual Manual background editors must finish layout");
        // Before: a point edit implicitly selected Manual. After: select Manual first.
        const modes = selectors(["manual", "auto"]);
        compare(modes.length, 1, "The point edit requires the real estimation mode selector on Main");
        compare(String(modes[0].label).trim().toLowerCase(), "estimation mode",
                "Every background type must label the manual/auto box estimation mode");
        choose(modes[0], "manual");
        tryVerify(() => !Session.project.calculating, 1000,
                  "The real Manual calculation must settle before committing its point edit");
        const cell = Ui.find(enablementGroup, "background.intensity.0", true);
        verify(cell !== null, "The loaded Auto-row control must expose its real height editor on Main");
        Ui.scrollIntoView(cell);
        cell.forceActiveFocus();
        verify(SettingsProof.type(cell, "8.125"), "After selecting Manual the loaded point must receive a real height edit");
        verify(SettingsProof.key(cell, Qt.Key_Return), "Return must commit the manual background point edit");
        const destination = Probe.scratchProjectUrl();
        verify(Session.saveAs(destination), "The hand-edited automatic background must save");
        compare(savedSettings(destination).mode, "manual", "A real point edit must persist manual estimate mode");
        compare(points()[0][1], 8.125, "The Manual background must retain the committed keyboard height");
        Session.closeProject();
        verify(Session.openProject(destination), "The manual background must reload in the app");
        compare(points()[0][1], 8.125, "Reloading manual mode must retain the point edit exactly");
        console.log("BACKGROUND_SETTINGS_MANUAL true");
    }

    // Before: fields were discovered by their older wording and line-segment alone
    // exposed Estimate. After: identities survive two-word labels; all types share
    // one grid, with only their own count, and auto shows its resolved method.
    function namedField(identity) {
        const controls = objects(sidebarPane, "label").filter(control =>
            Ui.inPane(control) && String(control.objectName) === identity);
        compare(controls.length, 1, "Background Extra must expose exactly one visible field objectName=" + identity);
        return controls[0];
    }
    function savedTerms(destination) {
        const result = [];
        let tags = [], active = false;
        SettingsProof.text(destination, "experiments/bank.edi").split(/\r?\n/).forEach(line => {
            const words = line.trim().split(/\s+/);
            if (words[0] === "loop_") { tags = []; active = true; }
            else if (active && words[0].startsWith("_")) {
                if (words.length === 1) tags.push(words[0]); else active = false;
            } else if (active && words[0] !== "" && tags.indexOf("_background.order") >= 0) {
                result.push([Number(words[tags.indexOf("_background.order")]),
                             Number(words[tags.indexOf("_background.coef")].split("(")[0])]);
            }
        });
        return result;
    }
    function seriesLayout(kind) {
        const fixture = kind === "line-segment" ? "auto-overrides" : "series-" + kind;
        openCase(fixture);
        tryVerify(() => !Session.project.calculating, 1000, "The real app calculation must finish before checking each type's grid");
        enablementGroup = estimateGroup.createObject(appWindow.contentItem);
        verify(enablementGroup !== null, "Every type's layout must use the production BackgroundExtrasGroup");
        enablementGroup.experiment = Session.project.currentExperiment;
        sidebarPane = enablementGroup;
        verify(waitForPolish(enablementGroup), "The production Extra grid must settle before checking its rows");
        const own = kind === "line-segment" ? "n_points" : "max_terms";
        const ids = ["use_model", own, "method", "width", "smoothness", "tolerance"];
        const fields = ids.map(id => namedField("background_estimate." + id));
        const other = own === "n_points" ? "max_terms" : "n_points";
        compare(objects(sidebarPane, "label").filter(control => Ui.inPane(control) &&
                String(control.objectName) === "background_estimate." + other).length, 0,
                "Extra must show only the current background type's own count field");
        const labels = ["calculated peaks", kind === "line-segment" ? "anchor points" : "max terms",
                        "baseline method", "peak width", "curve smoothness", "noise tolerance"];
        fields.forEach((field, index) => {
            const label = String(field.label).toLowerCase().replace(/ \(points\)/, "").trim();
            compare(label, labels[index], "Stable background field identity must carry its approved two-word label: " + ids[index]);
        });
        const positions = fields.map(field => field.mapToItem(sidebarPane, 0, 0));
        for (let row = 0; row < 3; ++row) {
            verify(Math.abs(positions[2 * row].y - positions[2 * row + 1].y) <= 1,
                   "The approved Background grid pairs must share a row");
            verify(positions[2 * row].x < positions[2 * row + 1].x,
                   "The approved Background grid must put calculated peaks, method and smoothness on the left");
            if (row > 0) verify(positions[2 * row].y > positions[2 * row - 2].y,
                                "The Background grid must order calculated peaks, method and smoothness from top to bottom");
        }
        verify(Math.abs(fields[0].width - fields[2].width) <= 1,
               "Both Background selectors must have the same grid width");
        const method = fields[2], peaks = fields[0];
        [method, peaks].forEach(control => {
            for (let index = 0; index < optionTokens(control).length; ++index)
                compare(String(control.textAt(index)), String(control.textAt(index)).toLowerCase(),
                        "Every public Background combo value must display in lower case");
        });
        choose(method, "snip");
        verify(!namedField("background_estimate.smoothness").enabled,
               "SNIP must disable curve smoothness because it has no smoothing penalty");
        choose(method, "auto");
        verify(namedField("background_estimate.smoothness").enabled,
               "Auto resolving to arpls must enable curve smoothness again");
        compare(String(method.token), "auto", "The resolved baseline hint must retain the saved auto token");
        verify(/auto/.test(String(method.displayText)) && /·.*arpls/.test(String(method.displayText)),
               "The stable baseline-method selector must display auto followed by its resolved arpls choice");
        const destination = Probe.scratchProjectUrl();
        verify(Session.saveAs(destination), "All background types must save their shared and own estimate controls");
        if (kind !== "line-segment") {
            type(valueField([], "background_estimate.max_terms"), "2");
            verify(Session.saveAs(destination), "The real max_terms editor must save for either series type");
            compare(savedSettings(destination).max_terms, 2, "The actual app count override must remain two on save");
            Session.closeProject();
            verify(Session.openProject(destination), "The saved max_terms override must reload through the actual app");
            compare(Session.project.currentExperiment.backgroundEstimateMaxTerms, 2,
                    "The reloaded view model must retain the actual max_terms editor choice");
        }
        console.log("BACKGROUND_SERIES_LAYOUT " + JSON.stringify({type: kind, countField: own, method: "auto", resolved: "arpls"}));
    }
    function seriesAction(kind) {
        const input = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/series-" + kind));
        const text = SettingsProof.text(input, "experiments/bank.edi");
        verify(SettingsProof.write(input, "experiments/bank.edi",
               text.replace(/_background_estimate.max_terms 6/, "_background_estimate.max_terms 2")),
               "The series action control must start with an independently insufficient saved cap");
        verify(Session.openProject(input), "The app must load each declared series before testing its Main action");
        tryVerify(() => !Session.project.calculating, 2000, "The series action must wait for the real initial calculation");
        pane("basic");
        compare(estimateButtons().length, 1, "Main must expose one enabled clickable Estimate action for background type " + kind);
        const original = JSON.stringify(Probe.rows(Session.project.currentExperiment.backgroundTerms));
        pointer(estimateButtons()[0]);
        compare(Probe.rows(Session.project.currentExperiment.backgroundTerms).length, 2,
                "The actual Estimate action must stop a known cubic exactly at its two-term cap");
        const destination = Probe.scratchProjectUrl();
        verify(Session.saveAs(destination), "Estimated capped series must save through the actual app");
        compare(savedSettings(destination).max_terms, 2, "The app action must preserve the saved term cap");
        const coefficients = savedTerms(destination);
        const estimated = JSON.stringify(Probe.rows(Session.project.currentExperiment.backgroundTerms));
        Session.project.undo();
        compare(JSON.stringify(Probe.rows(Session.project.currentExperiment.backgroundTerms)), original,
                "One undo must restore the complete prior series after Estimate");
        Session.closeProject();
        verify(Session.openProject(destination), "The estimated series must reload through the actual app");
        compare(JSON.stringify(Probe.rows(Session.project.currentExperiment.backgroundTerms)), estimated,
                "The saved estimated coefficients must reload exactly");
        console.log("BACKGROUND_SERIES_ACTION " + JSON.stringify({type: kind, terms: coefficients}));
    }
    function test_series_action_polynomial() { seriesAction("polynomial"); }
    function test_series_action_chebyshev() { seriesAction("chebyshev"); }
    function test_series_layout_line_segment() { seriesLayout("line-segment"); }
    function test_series_layout_polynomial() { seriesLayout("polynomial"); }
    function test_series_layout_chebyshev() { seriesLayout("chebyshev"); }
}
