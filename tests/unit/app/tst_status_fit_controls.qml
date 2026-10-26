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
    function rightmostFitAction() {
        verify(waitForPolish(appWindow.contentItem), "The status bar finishes layout before the Fit action's position is checked");
        const group = area(), button = shortcut();
        const left = button.mapToItem(group, 0, 0).x;
        for (const item of group.children) {
            if (item === button || !item.visible || item.width <= 0)
                continue;
            verify(item.mapToItem(group, item.width, 0).x <= left, "The Fit action follows every visible fit indicator, statistic and progress bar: " + item.objectName);
        }
        fuzzyCompare(button.mapToItem(group, button.width, 0).x, group.width, 1, "The Fit action is the last item at the status bar's right end");
    }
    function fitState(shortText) {
        compare(caption(shortcut()), shortText, "The status Fit control names the actual idle, continuing or running state");
        compare(icon(shortcut()), shortText === "Stop" ? "stop-circle" : "play-circle", "Start and Continue use play, and the running action uses stop");
    }
    function sidebarFitActions() {
        return View.descendants(Ui.page(appWindow)).filter(item => ["fitting.start", "fitting.reset", "fitting.follow"].includes(item.objectName) || (typeof item.clicked === "function" && /^(Start fitting|Continue fitting|Stop fitting|Follow|Reset fits)$/.test(item.text)));
    }
    function scanControl(name, optional = false) {
        const item = findChild(appWindow, "statusBar.fit." + name);
        verify(optional || item !== null, "The status bar owns the scan " + name + " control");
        return item;
    }
    function actionable(item) {
        return item !== null && item.enabled && (typeof item.clickable !== "boolean" || item.clickable);
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
        const button = shortcut();
        verify(button.visible && !actionable(button), "The status Fit button remains shown but disabled when the model reports an unavailable fit");
        runningSpy.clear();
        click(button);
        compare(runningSpy.count, 0, "Clicking an unavailable status shortcut cannot start a worker");
    }
    function test_status_start() {
        open("single");
        fitState("Fit");
        const button = shortcut();
        verify(actionable(button) && Session.project.fit.available, "An idle status action follows the model availability");
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
        verify(Session.project.fit.continuable, "The physical resume witness reaches the real resumable state");
        fitState("Continue");
        verify(actionable(shortcut()), "The resumable scan enables the status Continue action");
        click(shortcut());
        finish();
        compare(Session.project.fit.scanFitted, 2, "Status Fit continues the partial scan through the newly added measured dataset");
        fitState("Fit");
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
        if (data.tag === "status")
            AppState.open(AppState.Page.Structure);
        const button = shortcut();
        fitState("Fit");
        Session.project.fit.start();
        verify(Session.project.fit.running, "The actual worker enters its running state synchronously before stop input");
        fitState("Stop");
        const progress = findChild(appWindow, "statusBar.fit.progress");
        verify(progress !== null && progress.visible, "The running position witness includes the actual fit progress bar");
        rightmostFitAction();
        verify(actionable(button), "The running status action stays available to stop the worker on either page");
        click(button);
        finish();
        compare(Session.project.fit.outcome, "stopped", "The status action stops the actual fit worker from Analysis and other pages");
        fitState(Session.project.fit.continuable ? "Continue" : "Fit");
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
    function paintedColor(fill) {
        const image = grabImage(appWindow.contentItem);
        const point = fill.mapToItem(appWindow.contentItem, fill.width / 2, 2);
        const scale = image.width / appWindow.contentItem.width;
        return image.pixel(Math.round(point.x * scale), Math.round(point.y * scale));
    }
    function paintedLuminance(fill) {
        return luminance(paintedColor(fill));
    }
    function paintedGrayMatches(fill, channel) {
        const color = paintedColor(fill);
        return Math.abs(color.r - channel) <= 1 / 255 && Math.abs(color.g - channel) <= 1 / 255 && Math.abs(color.b - channel) <= 1 / 255;
    }
    function colorsMatch(a, b) {
        return Math.abs(a.r - b.r) <= 1 / 255 && Math.abs(a.g - b.g) <= 1 / 255 && Math.abs(a.b - b.b) <= 1 / 255 && Math.abs(a.a - b.a) <= 1 / 255;
    }
    function normalButtonStyle(item, light, canHover) {
        mouseMove(appWindow.contentItem, 1, 1, 0);
        const fill = rectangle(item);
        if (light)
            tryVerify(() => paintedGrayMatches(fill, 1), 1500, "Secondary status buttons have a rendered white background in light mode");
        else
            tryVerify(() => paintedLuminance(fill) > luminance(EaStyle.Colors.statusBarBackground), 1500, "Secondary status buttons are slightly lighter than the dark status bar");
        compare(fill.border.width, 1, "Secondary status buttons have a one-pixel border");
        tryVerify(() => colorsMatch(fill.border.color, EaStyle.Colors.appBarBorder), 1500, "Secondary button borders match the status bar's own border line");
        if (light)
            verify(luminance(fill.border.color) < luminance(EaStyle.Colors.statusBarBackground), "The light secondary border is darker than the status bar background");
        if (!canHover)
            return;
        verify(actionable(item), "The secondary hover witness has a real available action");
        const label = View.textItems(item).find(text => text.text === caption(item));
        verify(label !== undefined, "The secondary status action renders its actual caption");
        const oldInk = label.color, oldIcon = item.iconColor;
        mouseMove(item, item.width / 2, item.height / 2, 0);
        tryVerify(() => colorsMatch(label.color, EaStyle.Colors.themeAccent) && colorsMatch(item.iconColor, EaStyle.Colors.themeAccent), 1500, "Hovering an available secondary status action turns its caption and icon accent blue");
        if (light)
            verify(paintedGrayMatches(fill, 1), "Secondary hover retains its white background while only the ink turns blue");
        mouseMove(appWindow.contentItem, 1, 1, 0);
        tryVerify(() => colorsMatch(label.color, oldInk) && colorsMatch(item.iconColor, oldIcon), 1500, "Leaving a secondary status action restores its normal caption and icon colours");
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
        const idleChannel = data.tag === "light" ? 0 : 1;
        tryVerify(() => paintedGrayMatches(fill, idleChannel), 1500, "The enabled status Fit background is pure black in light mode and pure white in dark mode");
        tryVerify(() => data.tag === "light" ? paintedLuminance(outcome) > paintedLuminance(fill) : paintedLuminance(outcome) < paintedLuminance(fill), 1500, "The drawn outcome button has a lighter light-mode background and an inverse dark-mode hierarchy after overlay compositing");
        fuzzyCompare(fill.height, outcome.height, 1, "Fit and outcome buttons have the same background height");
        fuzzyCompare(fill.radius, outcome.radius, .5, "Fit and outcome buttons have the same rounded corners");
        verify(fill.radius > 0, "The status Fit button has rounded corners");
        const label = View.textItems(button).filter(item => item.text === "Fit");
        compare(label.length, 1, "The status shortcut renders the white or inverse Fit caption");
        const ink = data.tag === "light" ? Qt.rgba(1, 1, 1, 1) : Qt.rgba(0, 0, 0, 1);
        tryVerify(() => colorsMatch(label[0].color, ink), 1500, "The enabled Fit caption is pure white in light mode and pure black in dark mode");
        const glyphs = View.textItems(button).filter(item => item.text !== "Fit");
        verify(glyphs.length > 0 && glyphs.some(item => colorsMatch(item.color, ink)), "The status Fit icon uses the same pure white or black ink as its caption");
        mouseMove(button, button.width / 2, button.height / 2, 0);
        tryVerify(() => colorsMatch(paintedColor(fill), EaStyle.Colors.themeAccent), 1500, "Hovering enabled Fit changes its rendered background to the app accent blue");
        compare(label[0].color, ink, "Fit keeps its inverted caption ink on the blue hover background");
        verify(glyphs.some(item => colorsMatch(item.color, ink)), "Fit keeps its inverted icon ink on the blue hover background");
        mouseMove(appWindow.contentItem, 1, 1, 0);
        tryVerify(() => paintedGrayMatches(fill, idleChannel), 1500, "Leaving Fit restores its pure black or white background");
        normalButtonStyle(status, data.tag === "light", true);
        rightmostFitAction();
    }
    function test_scan_controls_data() {
        return ["single", "joint", "scan", "independent", "scan-single"].map(kind => ({
                    tag: kind
                }));
    }
    function test_scan_controls(data) {
        const isScan = data.tag === "scan" || data.tag === "independent";
        open(data.tag === "single" || data.tag === "joint" ? "single" : "scan");
        if (data.tag === "joint") {
            verify(Session.project.duplicateExperiment(), "A second real experiment creates the joint witness");
            Session.project.analysis.fittingMode = "joint";
        } else if (data.tag === "independent")
            Session.project.analysis.fittingMode = "independent";
        else if (data.tag === "scan-single")
            Session.project.analysis.fittingMode = "single";
        verify(waitForPolish(appWindow.contentItem), "The selected fitting mode settles before scan action checks");
        const reset = scanControl("reset", !isScan), follow = scanControl("follow", !isScan), button = shortcut();
        compare(reset !== null && reset.visible, isScan, "Reset is shown only for sequential and independent scans");
        compare(follow !== null && follow.visible, isScan, "Follow is shown only for sequential and independent scans");
        verify(!actionable(follow), "Follow cannot be activated before a scan runs");
        if (!isScan)
            return;
        verify(reset.mapToItem(area(), reset.width, 0).x <= follow.mapToItem(area(), 0, 0).x && follow.mapToItem(area(), follow.width, 0).x <= button.mapToItem(area(), 0, 0).x, "The scan actions are ordered Reset, Follow, Fit at the right end");
        for (const item of [reset, follow]) {
            const fill = rectangle(item), fitFill = rectangle(button);
            fuzzyCompare(fill.height, fitFill.height, 1, "Scan actions have Fit's framed height");
            fuzzyCompare(fill.radius, fitFill.radius, .5, "Scan actions have Fit's corner radius");
            fuzzyCompare(item.leftPadding, button.leftPadding, .5, "Scan actions have Fit's left padding");
            fuzzyCompare(item.rightPadding, button.rightPadding, .5, "Scan actions have Fit's right padding");
        }
        let compact = false;
        for (const width of [1000, 800, 640, 500]) {
            appWindow.width = width;
            verify(waitForPolish(appWindow.contentItem), "Narrow-window layout settles before checking action captions");
            const hasCaption = item => View.textItems(item).some(label => label.text === caption(item));
            if (!hasCaption(reset) && !hasCaption(follow) && hasCaption(button)) {
                compact = true;
                break;
            }
        }
        verify(compact, "Reset and Follow drop their captions before Fit on a narrow status bar");
        appWindow.width = 1300;
        verify(waitForPolish(appWindow.contentItem), "The wide status controls are restored before worker input");
        Session.project.fit.start();
        verify(Session.project.fit.scanning && actionable(follow), "Follow becomes available while the actual scan runs");
        const previous = Session.project.fit.following;
        click(follow);
        compare(Session.project.fit.following, !previous, "Actual status Follow input toggles the running scan's model");
        click(follow);
        compare(Session.project.fit.following, previous, "A second Follow click restores the real following state");
        click(button);
        finish();
        dialogs().forEach(dialog => dialog.close());
        verify(!actionable(follow), "Follow becomes unavailable when the scan stops");
        if (!Session.project.fit.canReset) {
            Session.project.fit.start();
            finish();
            dialogs().forEach(dialog => dialog.close());
        }
        verify(Session.project.fit.canReset && actionable(reset), "Retained real scan results enable Reset");
        click(reset);
        compare(Session.project.fit.scanFitted, 0, "Actual status Reset input clears the scan's fitted datasets");
        verify(!Session.project.fit.canReset && !actionable(reset), "Reset becomes unavailable after its own results are cleared");
    }
    function test_disabled_style_data() {
        return [
            {
                tag: "light"
            },
            {
                tag: "dark"
            }
        ];
    }
    function test_disabled_style(data) {
        open("scan");
        Session.project.fit.start();
        finish();
        dialogs().forEach(dialog => dialog.close());
        EaStyle.Colors.theme = data.tag === "light" ? EaStyle.Colors.Themes.LightTheme : EaStyle.Colors.Themes.DarkTheme;
        const button = shortcut(), follow = scanControl("follow");
        verify(!Session.project.fit.available && !actionable(button) && !actionable(follow), "A completed scan disables Fit and Follow for the muted-style witness");
        mouseMove(appWindow.contentItem, 1, 1);
        const fill = rectangle(button), other = rectangle(follow);
        tryVerify(() => {
            const a = paintedColor(fill), b = paintedColor(other);
            return Math.abs(a.r - b.r) <= 1 / 255 && Math.abs(a.g - b.g) <= 1 / 255 && Math.abs(a.b - b.b) <= 1 / 255;
        }, 1500, "Disabled Fit has the same rendered background as disabled Follow in each theme");
        const label = View.textItems(button).find(item => item.text === caption(button));
        const peer = View.textItems(follow).find(item => item.text === caption(follow));
        verify(label !== undefined && peer !== undefined, "Both disabled controls render their captions");
        tryCompare(label, "color", peer.color, 1500, "Disabled Fit uses Follow's normal caption colour");
        tryCompare(button, "iconColor", follow.iconColor, 1500, "Disabled Fit uses Follow's normal icon colour");
        normalButtonStyle(button, data.tag === "light", false);
        normalButtonStyle(follow, data.tag === "light", false);
        normalButtonStyle(scanControl("reset"), data.tag === "light", true);
    }
    function test_fit_tooltip_data() {
        return [
            {
                tag: "on",
                enabled: true
            },
            {
                tag: "off",
                enabled: false
            }
        ];
    }
    function test_fit_tooltip(data) {
        open("single");
        Preferences.toolTips = data.enabled;
        const button = shortcut();
        compare(button.ToolTip.text, "Fit the free parameters", "The Fit tooltip uses the owner's exact text");
        mouseMove(appWindow.contentItem, 1, 1);
        const point = Ui.clickPoint(button);
        verify(point !== null, "The status Fit tooltip has a visible hover target");
        mouseMove(button, point.x, point.y);
        const tips = () => Probe.objectsWithProperty(button, "enterAnimationDuration").filter(tip => tip.text === "Fit the free parameters");
        tryVerify(() => tips().length > 0, 1000, "The actual Fit control owns its tooltip popup");
        if (data.enabled)
            tryVerify(() => tips().some(tip => tip.visible && tip.opened && tip.opacity >= .99), 3000, "Hovering Fit displays its exact tooltip when app tooltips are enabled");
        else {
            verify(tips().every(tip => !tip.visible && !tip.opened), "Hovering Fit keeps its tooltip closed when app tooltips are disabled");
            Preferences.toolTips = true;
            tryVerify(() => tips().some(tip => tip.visible && tip.opened && tip.opacity >= .99), 3000, "The same held hover opens the real tooltip after enabling it");
            Preferences.toolTips = false;
            tryVerify(() => tips().every(tip => !tip.visible && !tip.opened), 1000, "Disabling tooltips closes the actual open Fit popup");
        }
    }
    function test_sidebar_table_uses_available_height() {
        open("single");
        verify(sidebarFitActions().length === 0, "The sidebar has no Start, Stop, Continue, Follow or Reset controls");
        const table = findChild(Ui.page(appWindow), "parameters.list"), slider = findChild(Ui.page(appWindow), "parameters.slider");
        verify(table !== null && slider !== null && Ui.exposed(slider), "The expanded parameter table retains its visible value slider");
        const initial = table.height;
        appWindow.height += 160;
        verify(waitForPolish(appWindow.contentItem), "Sidebar resizing finishes before checking table growth");
        verify(table.height > initial + 100, "The table consumes the new sidebar height instead of leaving the old fit-button space");
        verify(slider.mapToItem(appWindow.contentItem, 0, slider.height).y <= appWindow.contentItem.height, "The value slider remains within the resized application viewport");
        const rows = View.descendants(table).filter(item => /^parameters.row.[0-9]+$/.test(item.objectName));
        verify(rows.length > 2, "The table-height witness contains enough independently authored parameters for clipping");
        const fractional = rows.some(row => {
            let top = row.mapToItem(table, 0, 0).y, bottom = top + row.height;
            return top >= 0 && top < table.height && bottom > table.height && (table.height - top) / row.height >= .3 && (table.height - top) / row.height <= .7;
        });
        verify(fractional, "About half of the next parameter row remains visible at the table's lower edge");
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
        verify(sidebarFitActions().length === 0, "Analysis has no sidebar fitting controls");
        click(shortcut());
        verify(runningSpy.count > 0, "The status Fit action starts the real worker while Analysis is selected");
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
