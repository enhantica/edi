import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import "UiInteraction.js" as Ui
import "E04Review.js" as View

TestCase {
    id: test
    name: "StatusFitControls"
    when: windowShown
    property var appWindow
    property var savedBooleans
    property int oldTheme
    Component {
        id: application
        Main {}
    }
    SignalSpy {
        id: runningSpy
        target: Session.project ? Session.project.fit : null
        signalName: "runningChanged"
    }
    function init() {
        Session.closeProject();
        savedBooleans = {};
        Object.keys(Preferences).forEach(key => {
            if (typeof Preferences[key] === "boolean")
                savedBooleans[key] = Preferences[key];
        });
        AppState.reset();
        oldTheme = EaStyle.Colors.theme;
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Fit controls use the actual production Main window");
        appWindow.width = 1300;
        appWindow.height = 720;
        verify(waitForRendering(appWindow.contentItem), "The fit-control window renders before pointer input");
    }
    function cleanup() {
        if (Session.project && Session.project.fit.running) {
            Session.project.fit.cancel();
            tryVerify(() => !Session.project.fit.running, 10000, "The real worker stops before its application window is destroyed");
        }
        Session.closeProject();
        Preferences.dialogShown = false;
        Object.keys(savedBooleans).forEach(key => {
            if (Preferences[key] !== savedBooleans[key])
                Preferences[key] = savedBooleans[key];
        });
        EaStyle.Colors.theme = oldTheme;
        appWindow.close();
        appWindow.destroy();
        appWindow = null;
        Probe.releaseScratchProjects();
    }
    function click(item) {
        verify(item !== null && item !== undefined, "The requested production fit control exists before pointer input");
        Ui.scrollIntoView(item);
        const point = Ui.clickPoint(item);
        verify(point !== null, "The actual fit control has an exposed pointer target");
        mouseClick(item, point.x, point.y, Qt.LeftButton, Qt.NoModifier, 0);
    }
    function open(kind) {
        const path = kind === "scan" ? "tests/fixtures/correlations/scan-sequential" : "tests/fixtures/excluded_display/cw";
        const copy = SettingsProof.copyProject(Probe.repoUrl(path));
        if (kind !== "scan") {
            let text = SettingsProof.text(copy, "experiments/pattern.edi");
            verify(text.includes("phase 1\n"), "The independent single-fit fixture declares its known structure scale");
            text = text.replace("phase 1\n", "phase 1()\n");
            if (kind === "calculation")
                text = text.split("loop_\n_data.two_theta\n")[0] + "_data_range.two_theta_min 10\n_data_range.two_theta_max 90\n_data_range.two_theta_step 0.5\n";
            verify(SettingsProof.write(copy, "experiments/pattern.edi", text), "The disposable fixture declares the intended free scale and measured-data state");
        }
        verify(Session.openProject(copy), "The independently authored fit-control project loads: " + Session.lastError);
        tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 10000, "The actual project publishes its initial dataset before fit input");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        tryVerify(() => !Ui.moving(appWindow.contentItem), 2000, "Analysis finishes navigation before its fit control is inspected");
        verify(waitForPolish(appWindow.contentItem), "Analysis fitting controls finish layout before input");
    }
    function area() {
        const item = findChild(appWindow, "statusBar.fit");
        verify(item !== null, "The production status bar retains its fit-results group");
        return item;
    }
    function shortcut() {
        const candidates = View.descendants(area()).filter(item => item.objectName === "statusBar.fit.button" && typeof item.clicked === "function");
        compare(candidates.length, 1, "The fit-results group contains exactly one stateful Fit shortcut");
        return candidates[0];
    }
    function caption(item) {
        return typeof item.valueText === "string" ? item.valueText : item.text;
    }
    function fitState(shortText, sidebarText) {
        compare(caption(shortcut()), shortText, "The status Fit shortcut names the actual idle, continuing or running state");
        compare(analysisButton().text, sidebarText, "The Analysis button names the same actual fitting state");
        compare(icon(shortcut()), icon(analysisButton()), "The status shortcut uses the sidebar icon for its actual fitting state");
        verify(icon(shortcut()) !== "", "Each fitting state renders its sidebar action icon");
    }
    function analysisButton() {
        const item = findChild(Ui.page(appWindow), "fitting.start");
        verify(item !== null, "The production Analysis fitting button supplies the action-parity control");
        return item;
    }
    function icon(item) {
        if (typeof item.fontIcon === "string")
            return item.fontIcon;
        if (typeof item.keyIcon === "string")
            return item.keyIcon;
        return item.icon ? String(item.icon.name) : "";
    }
    function dialogs() {
        return Probe.visibleDialogs(appWindow).filter(dialog => dialog.objectName === "fit.results" || dialog.objectName === "statusBar.fitResults");
    }
    function finish() {
        tryVerify(() => !Session.project.fit.running && Session.project.fit.outcome !== "", 12000, "The real worker publishes its completed fit before result-window checks");
        verify(Session.project.fit.outcome !== "failed", "The physical witness completes a fit rather than a refusal: " + Session.project.fit.status);
        verify(Session.project.fit.results.count > 0, "A finished fit retains actual results independently of automatic window display");
        verify(waitForRendering(appWindow.contentItem), "Completion handlers and popup layout reach a frame before visibility is checked");
    }
    function preference() {
        Ui.click(test, Probe, appWindow, "appBar.button.preferences");
        const dialog = findChild(appWindow, "preferences");
        verify(dialog !== null, "The real application owns its Preferences dialog");
        tryCompare(dialog, "opened", true, 1000, "Preferences finishes opening before its fit-results choice is inspected");
        const label = View.descendants(dialog.contentItem).find(item => typeof item.text === "string" && item.text.replace(/:$/, "").trim() === "Show fit results after fitting");
        verify(label !== undefined, "App preferences expose Show fit results after fitting with the owner's label");
        let box = label;
        if (typeof box.checked !== "boolean") {
            const siblings = label.parent.children;
            box = siblings.slice(siblings.indexOf(label) + 1).find(item => typeof item.checked === "boolean");
        }
        verify(box !== undefined && typeof box.toggled === "function", "The fit-results preference is an actual user-toggleable checkbox");
        const tabs = View.descendants(dialog.contentItem).filter(item => item.objectName.startsWith("preferences.tab."));
        for (const tab of tabs) {
            if (Ui.exposed(box))
                break;
            click(tab);
            verify(waitForPolish(dialog.contentItem), "The selected Preferences tab lays out its actual fit-results checkbox");
        }
        verify(Ui.exposed(box), "The fit-results preference is reachable on a visible Preferences tab");
        return {
            dialog: dialog,
            box: box
        };
    }
    function chooseResults(enabled) {
        const control = preference();
        compare(control.box.checked, true, "A fresh app defaults to showing fit results after fitting");
        const modified = Session.project.modified;
        if (control.box.checked !== enabled)
            click(control.box);
        tryCompare(control.box, "checked", enabled, 1000, "Actual checkbox input selects the user's automatic results-window choice");
        compare(Session.project.modified, modified, "The app preference never modifies the scientific project");
        control.dialog.close();
        tryCompare(control.dialog, "visible", false, 1000, "Preferences closes before the actual fit starts");
    }
    function test_visibility_tracks_analysis_on_every_page() {
        const empty = View.descendants(area()).filter(item => typeof item.clicked === "function" && item.text === "Fit");
        verify(empty.every(item => !item.visible), "Without an enabled Analysis page the status Fit shortcut is hidden");
        open("single");
        compare(Session.project.fit.outcome, "", "The initial visibility witness has no previous fit result");
        for (const page of [0, 1, 2, 3, 4, 5]) {
            AppState.open(page);
            verify(waitForPolish(appWindow.contentItem), "Page navigation settles before status shortcut visibility is inspected");
            verify(AppState.analysisPageEnabled && shortcut().visible, "The status Fit shortcut remains visible on every page whenever Analysis is enabled, even before the first fit");
        }
        Session.closeProject();
        const remaining = View.descendants(area()).filter(item => typeof item.clicked === "function" && (item.text === "Fit" || item.keyText === "Fit" || item.valueText === "Fit"));
        verify(remaining.every(item => !item.visible), "Closing the project hides the status Fit shortcut when Analysis becomes disabled");
    }
    function test_unavailable_action_matches_analysis() {
        open("calculation");
        verify(AppState.analysisPageEnabled && !Session.project.fit.available, "Calculation-only data enable Analysis while making a fit unavailable");
        const button = shortcut(), analysis = analysisButton();
        verify(button.visible && !button.enabled && !analysis.enabled, "The status Fit button remains shown but disabled exactly like Analysis for an unavailable fit");
        runningSpy.clear();
        click(button);
        compare(runningSpy.count, 0, "Clicking an unavailable status shortcut cannot start a worker");
    }
    function test_status_start() {
        open("single");
        fitState("Fit", "Start fitting");
        const button = shortcut();
        compare(button.enabled, analysisButton().enabled, "An idle status shortcut follows Analysis availability");
        compare(icon(button), icon(analysisButton()), "The idle status shortcut shows the Analysis start icon");
        AppState.open(AppState.Page.Structure);
        runningSpy.clear();
        click(button);
        verify(runningSpy.count > 0, "The status shortcut starts the actual worker while another page is selected");
        finish();
    }
    function test_continue_matches_analysis() {
        open("scan");
        const copy = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/correlations/scan-sequential"));
        verify(SettingsProof.remove(copy, "experiments/scan/02.xy"), "The resume witness initially declares one independently stored dataset");
        verify(Session.openProject(copy), "The one-dataset scan opens through the real loader");
        tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 10000, "The resume witness publishes its only initial dataset");
        Session.project.fit.start();
        finish();
        dialogs().forEach(dialog => dialog.close());
        const second = SettingsProof.text(Probe.repoUrl("tests/fixtures/correlations/scan-sequential"), "experiments/scan/02.xy");
        verify(SettingsProof.write(copy, "experiments/scan/02.xy", second), "A second independently authored dataset extends the saved real scan");
        verify(Session.save(), "The partial scan saves its completed dataset and real result index");
        Session.closeProject();
        verify(Session.openProject(copy), "The partial scan restores its result index alongside the newly added dataset");
        tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 10000, "The restored partial scan publishes its selected dataset");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        verify(Session.project.fit.continuable && /Continue/.test(analysisButton().text), "The physical resume witness reaches Analysis Continue fitting");
        fitState("Continue", "Continue fitting");
        compare(shortcut().enabled, analysisButton().enabled, "The status shortcut follows Continue fitting availability");
        compare(icon(shortcut()), icon(analysisButton()), "The status shortcut follows Continue fitting's icon");
        click(shortcut());
        finish();
        compare(Session.project.fit.scanFitted, 2, "Status Fit continues the partial scan through the newly added measured dataset");
        fitState("Fit", "Start fitting");
    }
    function test_running_action_data() {
        return [
            {
                tag: "status"
            },
            {
                tag: "analysis"
            }
        ];
    }
    function test_running_action(data) {
        open("scan");
        const button = data.tag === "status" ? shortcut() : analysisButton();
        fitState("Fit", "Start fitting");
        Session.project.fit.start();
        verify(Session.project.fit.running, "The actual worker enters its running state synchronously before stop input");
        fitState("Stop", "Stop fitting");
        if (data.tag === "status") {
            compare(button.enabled, analysisButton().enabled, "While running the status shortcut remains enabled exactly like Analysis");
            compare(icon(button), icon(analysisButton()), "While running the status shortcut changes to the actual Analysis stop icon");
            verify(icon(button) !== "" && /Stop/.test(analysisButton().text), "Running-state parity is checked at Stop, not at the idle start icon");
        }
        click(button);
        finish();
        compare(Session.project.fit.outcome, "stopped", "The running status and Analysis actions both stop the actual fit worker");
        fitState(Session.project.fit.continuable ? "Continue" : "Fit", Session.project.fit.continuable ? "Continue fitting" : "Start fitting");
    }
    function test_button_style_data() {
        return [
            {
                tag: "light"
            },
            {
                tag: "dark"
            }
        ];
    }
    function rectangle(control) {
        const found = View.descendants(control.background).filter(item => item.visible && typeof item.radius === "number" && item.color && item.color.a > 0 && item.opacity > 0 && item.width >= control.width - 1);
        verify(found.length > 0, "The fit button has a visible filled background even without hovering");
        return found[0];
    }
    function luminance(color) {
        return .2126 * color.r + .7152 * color.g + .0722 * color.b;
    }
    function test_button_style(data) {
        open("single");
        Session.project.fit.start();
        finish();
        dialogs().forEach(dialog => dialog.close());
        EaStyle.Colors.theme = data.tag === "light" ? EaStyle.Colors.Themes.LightTheme : EaStyle.Colors.Themes.DarkTheme;
        const button = shortcut(), status = findChild(appWindow, "statusBar.fit.outcome");
        verify(status !== null && status.visible, "A real fit provides its outcome button beside the status Fit shortcut");
        mouseMove(appWindow.contentItem, 1, 1);
        const fill = rectangle(button), outcome = rectangle(status);
        tryVerify(() => data.tag === "light" ? luminance(fill.color) < .25 : luminance(fill.color) > .75, 1500, "Fit has a near-black light-mode background and the inverse in dark mode");
        verify(data.tag === "light" ? luminance(outcome.color) > luminance(fill.color) : luminance(outcome.color) < luminance(fill.color), "The outcome button has a visibly lighter light-mode background and an inverse dark-mode hierarchy");
        fuzzyCompare(fill.height, outcome.height, 1, "Fit and outcome buttons have the same background height");
        fuzzyCompare(fill.radius, outcome.radius, .5, "Fit and outcome buttons have the same rounded corners");
        verify(fill.radius > 0, "The status Fit button has rounded corners");
        const label = View.textItems(button).filter(item => item.text === "Fit");
        compare(label.length, 1, "The status shortcut renders the white or inverse Fit caption");
        tryVerify(() => data.tag === "light" ? luminance(label[0].color) > .9 : luminance(label[0].color) < .1, 1500, "Fit caption ink is white in light mode and inverted in dark mode");
        const glyphs = View.textItems(button).filter(item => item.text !== "Fit");
        verify(glyphs.length > 0 && glyphs.some(item => data.tag === "light" ? luminance(item.color) > .9 : luminance(item.color) < .1), "The status Fit icon has the same white or inverse ink as its caption");
        const sidebar = analysisButton(), sidebarFill = rectangle(sidebar);
        tryVerify(() => data.tag === "light" ? luminance(sidebarFill.color) < .25 : luminance(sidebarFill.color) > .75, 1500, "The Analysis fit button shares the status shortcut's dark primary fill and its dark-mode inverse");
        const sidebarLabel = View.textItems(sidebar).filter(item => item.text === sidebar.text);
        compare(sidebarLabel.length, 1, "The primary Analysis fit button renders its state caption");
        tryVerify(() => data.tag === "light" ? luminance(sidebarLabel[0].color) > .9 : luminance(sidebarLabel[0].color) < .1, 1500, "The primary Analysis fit caption shares the status shortcut's white or inverse ink");
        const sidebarGlyphs = View.textItems(sidebar).filter(item => item.text === icon(sidebar));
        verify(sidebarGlyphs.length > 0 && sidebarGlyphs.some(item => data.tag === "light" ? luminance(item.color) > .9 : luminance(item.color) < .1), "The primary Analysis fit icon shares the status shortcut's white or inverse ink");
        verify(button.mapToItem(area(), 0, 0).x < status.mapToItem(area(), 0, 0).x, "The Fit shortcut sits at the left of the fit-results controls");
    }
    function test_preference_default_and_user_store() {
        open("single");
        const control = preference();
        compare(control.box.checked, true, "Show fit results after fitting is on in a fresh user store");
        const before = {};
        Object.keys(Preferences).forEach(key => {
            if (typeof Preferences[key] === "boolean")
                before[key] = Preferences[key];
        });
        click(control.box);
        compare(control.box.checked, false, "The actual preference checkbox accepts the user's off choice");
        const changed = Object.keys(before).filter(key => before[key] === true && Preferences[key] === false);
        compare(changed.length, 1, "The preference checkbox changes one actual application preference");
        const source = 'import QtQuick; import edi.app; QtObject { property bool saved: Preferences[' + JSON.stringify(changed[0]) + '] }';
        tryVerify(() => {
            const restored = SettingsProof.restart(source);
            return !restored.error && restored.saved === false;
        }, 1500, "A fresh app engine restores the user's off choice from settings");
        Preferences.resetToDefaults();
        tryCompare(control.box, "checked", true, 1000, "Resetting app preferences restores automatic results display to on");
    }
    function test_results_preference_data() {
        const rows = [];
        for (const kind of ["single", "scan"])
            for (const enabled of [true, false])
                rows.push({
                    tag: kind + "-" + (enabled ? "on" : "off"),
                    kind: kind,
                    enabled: enabled
                });
        return rows;
    }
    function test_results_preference(data) {
        open(data.kind);
        chooseResults(data.enabled);
        Session.project.fit.start();
        finish();
        compare(dialogs().length, data.enabled ? 1 : 0, "A real single or scan completion opens results exactly when the user's preference is on");
        dialogs().forEach(dialog => dialog.close());
        const status = findChild(appWindow, "statusBar.fit.outcome");
        verify(status !== null && status.visible && status.clickable, "Finished results remain reachable from the actual outcome button with either preference choice");
        click(status);
        tryVerify(() => dialogs().length === 1, 1000, "Clicking the outcome button still opens the retained fit results when automatic opening is off");
    }
    function test_existing_analysis_start() {
        open("single");
        runningSpy.clear();
        click(analysisButton());
        verify(runningSpy.count > 0, "The unchanged Analysis button starts the real fit worker as the shortcut's control");
        finish();
    }
    function test_existing_completion_data() {
        return [
            {
                tag: "single"
            },
            {
                tag: "scan"
            }
        ];
    }
    function test_existing_completion(data) {
        open(data.tag);
        Session.project.fit.start();
        finish();
        compare(dialogs().length, 1, "The existing default completion route opens the actual results window for single and scan fits");
    }
}
