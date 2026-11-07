import "TooltipSettings.js" as TooltipSettings
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import StatusAccessibilityAcceptance 1.0
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
    SignalSpy {
        id: clickedSpy
        signalName: "clicked"
    }
    function accessibleAction(item, expected) {
        compare(item.focusPolicy, Qt.StrongFocus, "An available status action retains main's keyboard focus policy");
        compare(item.Accessible.role, Accessible.Button, "The actual clickable status consumer declares Button");
        const facts = StatusAccessibilityProof.observe(item);
        verify(facts.valid && facts.button && facts.press && facts.focusable && !facts.disabled && !facts.invisible, "The actual current status consumer advertises a live native Press action");
        compare(facts.name, expected, "Its native accessible name is the exact current caption");
        compare(facts.description, item.ToolTip.text, "Its native description is the actual current tooltip");
        return facts.id;
    }
    function pressAction(item) {
        const id = accessibleAction(item, caption(item));
        clickedSpy.target = item;
        verify(clickedSpy.valid, "The accessible route observes the original actual clicked signal");
        clickedSpy.clear();
        const attempt = StatusAccessibilityProof.press(id);
        verify(attempt.valid && attempt.attempted, "Assistive activation reaches the actual Qt action interface");
        compare(clickedSpy.count, 1, "One accessible activation invokes the original clicked handler exactly once");
    }
    function passiveAction(item) {
        compare(item.Accessible.role, Accessible.NoRole, "Unavailable status consumers retain ordinary Control semantics");
        verify(item.enabled, "Unavailability does not disable the original hover/tooltip Control");
        compare(item.Accessible.focusable, false, "Unavailable roots retire Button's sticky focusable metadata");
        const facts = StatusAccessibilityProof.observe(item);
        verify(facts.valid && !facts.button && !facts.press && !facts.focusable, "An unavailable root advertises no Press, including through Qt's connected-signal discovery");
        clickedSpy.target = item;
        verify(clickedSpy.valid, "The unavailable-door witness observes actual clicked publication");
        clickedSpy.clear();
        const attempt = StatusAccessibilityProof.press(facts.id);
        verify(attempt.valid && attempt.attempted, "The negative attempts the real cached Qt action despite no advertisement");
        compare(clickedSpy.count, 0, "The unavailable consumer cannot dispatch its original business action");
    }
    SignalSpy {
        id: keyboardSpy
        signalName: "clicked"
    }
    function keyAction(item, key, available) {
        verify(item !== null, "Keyboard input reaches an existing production status action");
        appWindow.requestActivate();
        item.forceActiveFocus(Qt.TabFocusReason);
        if (available)
            verify(item.activeFocus, "An available status action accepts keyboard focus");
        keyboardSpy.target = item;
        verify(keyboardSpy.valid, "Every real status action exposes its pointer activation signal to the keyboard observer");
        keyboardSpy.clear();
        verify(SettingsProof.key(item, key), "The activation key is delivered to the real application window");
        compare(keyboardSpy.count, available ? 1 : 0, "Space and Enter use the status action's same clicked signal as pointer input and respect availability");
        keyboardSpy.target = null;
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
    function resizeWindow(width, height) {
        appWindow.width = width;
        appWindow.height = height;
        tryCompare(appWindow.contentItem, "width", width, 2000, "The real window resize reaches its content width before layout observations");
        tryCompare(appWindow.contentItem, "height", height, 2000, "The real window resize reaches its content height before layout observations");
        verify(waitForRendering(appWindow.contentItem), "The resized application renders a frame before its captions and table are inspected");
        verify(waitForPolish(appWindow.contentItem), "The resized content finishes its pending layout before observations");
    }
    function cleanup() {
        SettingsProof.releaseScanStop();
        clickedSpy.target = null;
        if (Session.project && Session.project.fit.running) {
            Session.project.fit.cancel();
            tryVerify(() => !Session.project.fit.running, 10000, "The real worker stops before its application window is destroyed");
        }
        const scanStopCleared = SettingsProof.clearScanStop();
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
        verify(scanStopCleared, "The test-owned scan hold exits without expiry before owner teardown");
    }
    function click(item) {
        verify(item !== null && item !== undefined, "The requested production fit control exists before pointer input");
        Ui.scrollIntoView(item);
        const point = Ui.clickPoint(item);
        verify(point !== null, "The actual fit control has an exposed pointer target");
        mouseClick(item, point.x, point.y, Qt.LeftButton, Qt.NoModifier, 0);
    }
    function pagesReady() {
        tryVerify(() => appWindow.pagesWanted > 0 && appWindow.pagesBuilt === appWindow.pagesWanted, 10000, "The opened project's workflow pages finish loading before navigation or fit input");
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
        pagesReady();
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
    function windowLayoutReady(requestedHeight) {
        const group = area();
        const bar = group.parent, container = bar ? bar.parent : null;
        const host = container ? container.parent : null;
        if (!host || host.parent !== appWindow.contentItem)
            return false;
        // FIRST ApplicationWindow appContainer fills the padded Window content;
        // its statusBarContainer is bottom-anchored. Sidebar/page height is not
        // equated to the full Window: the app/status bars remain their owners.
        return appWindow.height === requestedHeight && appWindow.header === null && appWindow.footer === null && appWindow.menuBar === null && appWindow.contentItem.height === Math.max(0, requestedHeight - appWindow.topPadding - appWindow.bottomPadding) && host.height === appWindow.contentItem.height && container.y + container.height === host.height && bar.height === container.height && group.width === group.implicitWidth && !isPolishScheduled(appWindow);
    }
    function rightmostFitAction(requireScanHold = false) {
        const requestedHeight = appWindow.height, requestedWidth = appWindow.width;
        // QtTest's existing waitForPolish default is 5000ms. One combined
        // owning-Window/Row boundary replaces that same budget, not a new wait.
        tryVerify(() => footerGeometryReady(requestedWidth) && windowLayoutReady(requestedHeight) && (!requireScanHold || SettingsProof.scanStopReady(Session.project)), 5000, "The actual Window, footer host and fit Row settle before the unchanged Fit ordering checks");
        verify(!windowLayoutReady(requestedHeight + 1), "A polished Window cannot satisfy a different requested resize");
        const group = area(), button = shortcut();
        const left = button.mapToItem(group, 0, 0).x;
        for (const item of group.children) {
            if (item === button || View.descendants(item).includes(button) || !item.visible || item.width <= 0)
                continue;
            verify(item.mapToItem(group, item.width, 0).x <= left, "The Fit action follows every visible fit indicator, statistic and progress bar: " + item.objectName);
        }
        fuzzyCompare(button.mapToItem(group, button.width, 0).x, group.width, 1, "The Fit action is the last item at the status bar's right end");
    }
    function fitState(shortText) {
        compare(caption(shortcut()), shortText, "The status Fit control names the actual idle, continuing or running state");
        compare(icon(shortcut()), shortText === "Stop" ? "stop-circle" : "play-circle", "Start and Continue use play, and the running action uses stop");
        if (shortcut().clickable)
            accessibleAction(shortcut(), shortText);
        else
            passiveAction(shortcut());
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
        const prompts = findChild(dialog.contentItem, "preferences.tab.prompts");
        verify(prompts !== null, "Fit results preferences live on the actual Prompts tab");
        click(prompts);
        verify(waitForPolish(dialog.contentItem), "Prompts lays out its fit-results and tool-tip choices");
        const label = View.descendants(dialog.contentItem).find(item => typeof item.text === "string" && item.text.replace(/:$/, "").trim() === "Show fit results after fitting");
        verify(label !== undefined, "App preferences expose Show fit results after fitting with the owner's label");
        let box = label;
        if (typeof box.checked !== "boolean") {
            const siblings = label.parent.children;
            box = siblings.slice(siblings.indexOf(label) + 1).find(item => typeof item.checked === "boolean");
        }
        verify(box !== undefined && typeof box.toggled === "function", "The fit-results preference is an actual user-toggleable checkbox");
        const toolTips = View.descendants(dialog.contentItem).find(item => typeof item.textAt === "function" && item.count === 3 && ["All", "Important", "Off"].every(text => {
                for (let i = 0; i < item.count; ++i)
                    if (item.textAt(i) === text)
                        return true;
                return false;
            }));
        verify(toolTips !== undefined && Ui.exposed(toolTips) && Ui.exposed(box), "Prompts shows fit results beside the tooltip level chooser");
        compare(box.parent, toolTips.parent, "Both prompt choices belong to the same preferences grid");
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
        const bar = appWindow.statusBar;
        verify(bar !== null && !bar.assistantStatusNeeded, "The actual Home-hidden contrast has no independent assistant status demand");
        AppState.open(0);
        verify(waitForPolish(appWindow.contentItem), "Page navigation settles before status shortcut visibility is inspected");
        verify(AppState.analysisPageEnabled && !bar.visible && !shortcut().visible, "Home retains its declared hidden footer despite an available Analysis page");
        for (const page of [1, 2, 3, 4, 5]) {
            AppState.open(page);
            verify(waitForPolish(appWindow.contentItem), "Page navigation settles before status shortcut visibility is inspected");
            verify(AppState.analysisPageEnabled && shortcut().visible, "After opening an unfitted project and navigating to page " + page + ", Fit must remain visible whenever Analysis is enabled; observed Analysis enabled=" + AppState.analysisPageEnabled + ", Fit visible=" + shortcut().visible);
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
        passiveAction(button);
        compare(runningSpy.count, 0, "The actual unavailable accessible route also cannot start the worker");
        keyAction(button, Qt.Key_Space, false);
        keyAction(button, Qt.Key_Return, false);
        compare(runningSpy.count, 0, "Keyboard input on unavailable Fit cannot start a worker");
    }
    function test_status_start() {
        open("single");
        fitState("Fit");
        const button = shortcut();
        verify(actionable(button) && Session.project.fit.available, "An idle status action follows the model availability");
        AppState.open(AppState.Page.Structure);
        runningSpy.clear();
        keyAction(button, Qt.Key_Space, true);
        verify(runningSpy.count > 0, "The focused status shortcut starts the same actual worker from another page");
        finish();
    }
    function test_continue_matches_analysis() {
        open("scan");
        const copy = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/correlations/scan-sequential"));
        verify(SettingsProof.remove(copy, "experiments/scan/02.xy"), "The resume witness initially declares one independently stored dataset");
        verify(Session.openProject(copy), "The one-dataset scan opens through the real loader");
        pagesReady();
        tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 10000, "The resume witness publishes its only initial dataset");
        Session.project.fit.start();
        finish();
        dialogs().forEach(dialog => dialog.close());
        const second = SettingsProof.text(Probe.repoUrl("tests/fixtures/correlations/scan-sequential"), "experiments/scan/02.xy");
        verify(SettingsProof.write(copy, "experiments/scan/02.xy", second), "A second independently authored dataset extends the saved real scan");
        verify(Session.save(), "The partial scan saves its completed dataset and real result index");
        Session.closeProject();
        verify(Session.openProject(copy), "The partial scan restores its result index alongside the newly added dataset");
        pagesReady();
        tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 10000, "The restored partial scan publishes its selected dataset");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        verify(Session.project.fit.continuable, "The physical resume witness reaches the real resumable state");
        fitState("Continue");
        verify(actionable(shortcut()), "The resumable scan enables the status Continue action");
        keyAction(shortcut(), Qt.Key_Return, true);
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
            },
            {
                tag: "pointer-status"
            },
            {
                tag: "pointer-analysis"
            }
        ];
    }
    function test_running_action(data) {
        open("scan");
        if (data.tag.endsWith("status"))
            AppState.open(AppState.Page.Structure);
        const button = shortcut();
        fitState("Fit");
        verify(!SettingsProof.armScanStop(null) && !SettingsProof.armScanStop(button), "Only the actual current scan project can own the worker hold");
        verify(SettingsProof.armScanStop(Session.project), "The genuine next scan-file hook is owned before the unchanged fit start");
        verify(!SettingsProof.armScanStop(Session.project), "A second arm cannot replace the first generation");
        try {
            Session.project.fit.start();
            verify(Session.project.fit.running, "The actual worker enters its running state synchronously before stop input");
            fitState("Stop");
            const progress = findChild(appWindow, "statusBar.fit.progress");
            verify(progress !== null && progress.visible, "The running position witness includes the actual fit progress bar");
            rightmostFitAction(true);
            verify(actionable(button), "The running status action stays available to stop the worker on either page");
            verify(!SettingsProof.scanStopReady(null) && !SettingsProof.scanStopReady(button), "A different or absent owner cannot borrow this live worker admission");
            verify(!SettingsProof.clearScanStop(), "Clearing a live held callback refuses without releasing it");
            const held = SettingsProof.scanStopFacts(Session.project);
            console.info("E11_SCAN_STOP_BEFORE", JSON.stringify(held));
            verify(held.ready, "The same real worker is still held and cancellable immediately before physical Stop");
            clickedSpy.target = button;
            verify(clickedSpy.valid, "The original physical Stop observes the actual clicked publication");
            clickedSpy.clear();
            try {
                if (data.tag.startsWith("pointer-"))
                    click(button);
                else
                    keyAction(button, data.tag === "status" ? Qt.Key_Space : Qt.Key_Return, true);
            } finally {
                SettingsProof.releaseScanStop();
            }
            compare(clickedSpy.count, 1, "Exactly one original physical Stop dispatches while the real worker is held");
            SettingsProof.releaseScanStop();
            verify(!SettingsProof.scanStopReady(Session.project), "Repeated release is idempotent and cannot retain running admission");
            finish();
            const ended = SettingsProof.scanStopFacts(Session.project);
            console.info("E11_SCAN_STOP_AFTER", JSON.stringify(ended));
            compare(Session.project.fit.outcome, "stopped", "The status action stops the actual fit worker from Analysis and other pages");
            verify(ended.owner_current && !ended.native_running && ended.entered === 1 && ended.exited === 1 && !ended.blocked && ended.released && !ended.expired && ended.distinct_thread && ended.file_owned && ended.starts.length > 0, "The single actual callback exited without watchdog expiry after the real worker finished");
            verify(ended.run_identity_matches && !ended.run_invalid && ended.run_error === "" && ended.run_outcome === "stopped", "The actual current persisted run records the uniquely core-CANCELLED-derived stopped outcome");
            fitState(Session.project.fit.continuable ? "Continue" : "Fit");
        } finally {
            SettingsProof.releaseScanStop();
        }
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
    function bodyFrame(control, outline) {
        const fill = rectangle(control);
        compare(fill.border.width, outline, "The declared outer outline is separate from the two-font-size body");
        fuzzyCompare(fill.height, 2 * control.font.pixelSize + 2 * outline, 1, "The status body is two font sizes with the explicit outline outside it");
        fuzzyCompare(fill.radius, fill.height / 2, .5, "The complete framed pill retains its declared rounded corners");
        return fill;
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
            tryVerify(() => paintedGrayMatches(fill, 0), 1500, "Secondary status buttons have the declared rendered black background in dark mode");
        compare(fill.border.width, 1, "Secondary status buttons have a one-pixel border");
        tryVerify(() => colorsMatch(fill.border.color, AppColors.statusButtonBorder), 1500, "Secondary button borders follow the declared status-button palette in each theme");
        if (light) {
            verify(colorsMatch(fill.border.color, EaStyle.Colors.appBarBorder), "The light secondary border retains the status bar's own border line");
            verify(luminance(fill.border.color) < luminance(EaStyle.Colors.statusBarBackground), "The light secondary border is darker than the status bar background");
        }
        if (!canHover)
            return;
        verify(actionable(item), "The secondary hover witness has a real available action");
        const label = View.textItems(item).find(text => text.text === caption(item));
        const glyphs = View.textItems(item).filter(text => text.text === icon(item));
        verify(glyphs.length > 0, "The secondary status action renders its icon even when its caption is compacted");
        const oldInk = item.valueColor, oldIcon = item.iconColor;
        mouseMove(item, item.width / 2, item.height / 2, 0);
        tryVerify(() => colorsMatch(item.valueColor, oldInk) && colorsMatch(item.iconColor, oldIcon) && glyphs.some(glyph => colorsMatch(glyph.color, EaStyle.Colors.themeAccent)), 1500, "Hovering an available secondary action tints its actual drawn icon while preserving its base palette");
        if (label !== undefined)
            tryVerify(() => colorsMatch(label.color, EaStyle.Colors.themeAccent), 1500, "An expanded secondary caption visibly turns accent blue on hover");
        if (light)
            verify(paintedGrayMatches(fill, 1), "Secondary hover retains its white background while only the ink turns blue");
        mouseMove(appWindow.contentItem, 1, 1, 0);
        tryVerify(() => (label === undefined || colorsMatch(label.color, oldInk)) && glyphs.some(glyph => colorsMatch(glyph.color, oldIcon)), 1500, "Leaving a secondary status action restores its normal caption and visible icon colours");
    }
    function test_button_style(data) {
        const originalToolTips = TooltipSettings.level(Preferences);
        TooltipSettings.setLevel(Preferences, "Off");
        try {
            open("single");
            Session.project.fit.start();
            finish();
            dialogs().forEach(dialog => dialog.close());
            EaStyle.Colors.theme = data.tag === "light" ? EaStyle.Colors.Themes.LightTheme : EaStyle.Colors.Themes.DarkTheme;
            const button = shortcut(), status = findChild(appWindow, "statusBar.fit.outcome");
            verify(status !== null && status.visible, "A real fit provides its outcome button beside the status Fit shortcut");
            mouseMove(appWindow.contentItem, 1, 1);
            const fill = bodyFrame(button, 0), outcome = bodyFrame(status, 1);
            const idleChannel = data.tag === "light" ? 0 : 1;
            tryVerify(() => paintedGrayMatches(fill, idleChannel), 1500, "The enabled status Fit background is pure black in light mode and pure white in dark mode");
            tryVerify(() => data.tag === "light" ? paintedLuminance(outcome) > paintedLuminance(fill) : paintedLuminance(outcome) < paintedLuminance(fill), 1500, "The drawn outcome button has a lighter light-mode background and an inverse dark-mode hierarchy after overlay compositing");
            fuzzyCompare(fill.height, outcome.height - 2, 1, "Fit and outcome buttons have equal bodies after the explicit outer outline");
            fuzzyCompare(fill.radius, outcome.radius - 1, .5, "Fit and outcome buttons have equal body rounding inside the explicit outer outline");
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
        } finally {
            TooltipSettings.setLevel(Preferences, originalToolTips);
        }
    }
    function footerGeometryReady(requestedWidth) {
        const group = findChild(appWindow, "statusBar.fit");
        if (!group || !group.parent || !group.parent.parent || !group.parent.parent.parent)
            return false;
        // FIRST StatusBar fitArea is parented directly to bar; bar fills the
        // statusBarContainer, which spans the appContainer's anchored width.
        const bar = group.parent, container = bar.parent, host = container.parent;
        return host.parent === appWindow.contentItem && appWindow.width === requestedWidth && appWindow.contentItem.width === Math.max(0, appWindow.width - appWindow.leftPadding - appWindow.rightPadding) && host.width === appWindow.contentItem.width && container.width === host.width && bar.width === container.width && bar.mapToItem(appWindow.contentItem, 0, 0).x === 0 && !isPolishScheduled(appWindow);
    }
    function resultsPresentationReady() {
        const candidates = dialogs();
        if (candidates.length !== 1)
            return false;
        const dialog = candidates[0], content = dialog.contentItem;
        if (!dialog.visible || !dialog.opened || dialog.opacity !== 1 || !content || content.width <= 0 || content.height <= 0 || isPolishScheduled(appWindow))
            return false;
        const table = findChild(content, "fit.results.list");
        const expected = Session.project.fit.results.count;
        if (!table || !table.visible || table.width <= 0 || table.height <= 0 || table.count !== expected || expected <= 0 || !table.headerItem || table.headerItem.width <= 0 || table.headerItem.height <= 0)
            return false;
        let bottom = 0;
        for (let index = 0; index < expected; ++index) {
            const row = table.itemAtIndex(index);
            if (!row || !row.visible || row.width <= 0 || row.height <= 0)
                return false;
            const top = row.mapToItem(table.contentItem, 0, 0).y;
            if (top < bottom)
                return false;
            bottom = top + row.height;
            const metric = findChild(row, "fit.results.metric." + index);
            const value = findChild(row, "fit.results.value." + index);
            if (!metric || !value || !metric.visible || !value.visible || metric.width <= 0 || value.width <= 0 || metric.height <= 0 || value.height <= 0)
                return false;
        }
        return true;
    }
    function test_scan_controls_data() {
        return ["single", "joint", "scan", "independent", "scan-single"].map(kind => ({
                    tag: kind
                }));
    }
    function test_scan_controls(data, viaAccessibility = false) {
        const activate = viaAccessibility ? pressAction : click;
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
        if (isScan) {
            const before = Session.project.fit.following;
            keyAction(follow, Qt.Key_Space, false);
            keyAction(follow, Qt.Key_Return, false);
            compare(Session.project.fit.following, before, "Unavailable Follow ignores activation keys");
        }
        if (!isScan)
            return;
        Session.project.fit.start();
        verify(Session.project.fit.scanning && actionable(follow), "The keyboard witness reaches an available real Follow action");
        const keyboardFollowing = Session.project.fit.following;
        keyAction(follow, data.tag === "scan" ? Qt.Key_Space : Qt.Key_Return, true);
        compare(Session.project.fit.following, !keyboardFollowing, "Keyboard Follow toggles the same real model state as pointer input");
        click(follow);
        tryVerify(() => Session.project.fit.scanFitted > 0, 10000, "The reset witness publishes a real scan result before cancellation");
        Session.project.fit.cancel();
        finish();
        dialogs().forEach(dialog => dialog.close());
        verify(Session.project.fit.canReset, "The stopped real scan retains a resettable result");
        keyAction(reset, data.tag === "scan" ? Qt.Key_Return : Qt.Key_Space, true);
        compare(Session.project.fit.scanFitted, 0, "Keyboard Reset clears the real result set before the style witness restarts");
        verify(reset.mapToItem(area(), reset.width, 0).x <= follow.mapToItem(area(), 0, 0).x && follow.mapToItem(area(), follow.width, 0).x <= button.mapToItem(area(), 0, 0).x, "The scan actions are ordered Reset, Follow, Fit at the right end");
        for (const item of [reset, follow]) {
            const fill = bodyFrame(item, 1), fitFill = bodyFrame(button, 0);
            fuzzyCompare(fill.height - 2, fitFill.height, 1, "Scan actions have Fit's body height inside their explicit outer outline");
            fuzzyCompare(fill.radius - 1, fitFill.radius, .5, "Scan actions have Fit's body corner radius inside their explicit outer outline");
            fuzzyCompare(item.leftPadding, button.leftPadding, .5, "Scan actions have Fit's left padding");
            fuzzyCompare(item.rightPadding, button.rightPadding, .5, "Scan actions have Fit's right padding");
        }
        let compact = false;
        const captionStates = [];
        for (const width of [1000, 800, 640, 500]) {
            resizeWindow(width, appWindow.height);
            const hasCaption = item => View.textItems(item).some(label => label.text === caption(item));
            console.log("RESIZE AFTER", width, appWindow.width, appWindow.contentItem.width, hasCaption(reset), hasCaption(follow), hasCaption(button));
            captionStates.push("width=" + width + ": Reset=" + hasCaption(reset) + ", Follow=" + hasCaption(follow) + ", Fit=" + hasCaption(button));
            if (!hasCaption(reset) && !hasCaption(follow) && hasCaption(button)) {
                compact = true;
                break;
            }
        }
        verify(compact, "After a scan is stopped and reset, narrowing the window must show icon-only Reset and Follow while Fit keeps its caption at some width; observed " + captionStates.join("; "));
        resizeWindow(1300, appWindow.height);
        Session.project.fit.start();
        verify(Session.project.fit.scanning && actionable(follow), "Follow becomes available while the actual scan runs");
        const previous = Session.project.fit.following;
        keyAction(follow, data.tag === "scan" ? Qt.Key_Space : Qt.Key_Return, true);
        compare(Session.project.fit.following, !previous, "Actual status Follow input toggles the running scan's model");
        activate(follow);
        compare(Session.project.fit.following, previous, "A second Follow click restores the real following state");
        activate(button);
        finish();
        dialogs().forEach(dialog => dialog.close());
        verify(!actionable(follow), "Follow becomes unavailable when the scan stops");
        if (viaAccessibility)
            passiveAction(follow);
        if (!Session.project.fit.canReset) {
            Session.project.fit.start();
            finish();
            dialogs().forEach(dialog => dialog.close());
        }
        verify(Session.project.fit.canReset && actionable(reset), "Retained real scan results enable Reset");
        if (viaAccessibility) {
            const outcome = findChild(appWindow, "statusBar.fit.outcome");
            verify(outcome !== null && outcome.visible && outcome.clickable, "Real retained scan results expose the shared outcome action");
            pressAction(outcome);
            tryVerify(() => dialogs().length === 1, 1000, "Accessible outcome activation opens the same retained results window");
            dialogs().forEach(dialog => dialog.close());
        }
        if (viaAccessibility)
            pressAction(reset);
        else
            keyAction(reset, data.tag === "scan" ? Qt.Key_Return : Qt.Key_Space, true);
        compare(Session.project.fit.scanFitted, 0, "Actual status Reset input clears the scan's fitted datasets");
        verify(!Session.project.fit.canReset && !actionable(reset), "Reset becomes unavailable after its own results are cleared");
        keyAction(reset, Qt.Key_Space, false);
        keyAction(reset, Qt.Key_Return, false);
        compare(Session.project.fit.scanFitted, 0, "Unavailable Reset cannot change the cleared result set");
        if (viaAccessibility) {
            passiveAction(reset);
            compare(Session.project.fit.scanFitted, 0, "Unavailable Reset Press leaves the cleared real result population unchanged");
        }
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
        const keyboardReset = scanControl("reset");
        verify(Session.project.fit.canReset && actionable(keyboardReset), "Completed real scan results enable Reset for keyboard input");
        keyAction(keyboardReset, data.tag === "light" ? Qt.Key_Return : Qt.Key_Space, true);
        compare(Session.project.fit.scanFitted, 0, "Keyboard Reset clears the same completed scan results as pointer input");
        keyAction(keyboardReset, Qt.Key_Space, false);
        keyAction(keyboardReset, Qt.Key_Return, false);
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
        verify(label !== undefined, "Disabled Fit retains its caption while secondary controls may compact to icons");
        tryCompare(label, "color", follow.valueColor, 1500, "Disabled Fit uses Follow's normal caption colour");
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
        TooltipSettings.setLevel(Preferences, data.enabled ? "All" : "Off");
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
            TooltipSettings.setLevel(Preferences, "All");
            tryVerify(() => tips().some(tip => tip.visible && tip.opened && tip.opacity >= .99), 3000, "The same held hover opens the real tooltip after enabling it");
            TooltipSettings.setLevel(Preferences, "Off");
            tryVerify(() => tips().every(tip => !tip.visible && !tip.opened), 1000, "Disabling tooltips closes the actual open Fit popup");
        }
    }
    function test_sidebar_table_uses_available_height() {
        open("single");
        verify(sidebarFitActions().length === 0, "The sidebar has no Start, Stop, Continue, Follow or Reset controls");
        const table = findChild(Ui.page(appWindow), "parameters.list"), slider = findChild(Ui.page(appWindow), "parameters.slider");
        verify(table !== null && slider !== null && Ui.exposed(slider), "The expanded parameter table retains its visible value slider");
        compare(EaStyle.Sizes.statusBarHeight, EaStyle.Sizes.tabBarHeight, "The status bar takes the tab bars' height while retaining the button body height");
        const initial = table.height;
        resizeWindow(appWindow.width, appWindow.height + 160);
        console.log("HEIGHT AFTER", appWindow.height, appWindow.contentItem.height, initial, table.height);
        verify(table.height > initial + 100, "On Analysis, increasing window height from 720 to 880 must grow the parameter table by more than 100 pixels; observed table height " + initial + " -> " + table.height);
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
        Ui.click(test, Probe, appWindow, "sideBar.tab.settings");
        const relocated = View.descendants(Ui.page(appWindow)).filter(item => typeof item.text === "string" && item.text.replace(/:$/, "").trim() === "Show fit results after fitting");
        compare(relocated.length, 0, "Analysis Settings no longer duplicates the application-wide fit-results preference");
        const control = preference();
        compare(control.box.checked, true, "Show fit results after fitting is on in a fresh user store");
        const before = {};
        Object.keys(Preferences).forEach(key => {
            if (typeof Preferences[key] === "boolean")
                before[key] = Preferences[key];
        });
        const modified = Session.project.modified;
        click(control.box);
        compare(control.box.checked, false, "The actual preference checkbox accepts the user's off choice");
        compare(Session.project.modified, modified, "The app Preferences choice leaves the scientific project unchanged");
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
    function outdatedModes() {
        return [
            {
                tag: "sequential"
            },
            {
                tag: "independent"
            }
        ];
    }
    function resultFileProblems(bytes, facts) {
        const errors = [], names = ["results.csv", "results-provenance.csv", "scan-run.json", "scan-notes.csv"];
        if (bytes.length !== names.length || facts.length !== names.length)
            return ["All four original result slots are required"];
        const notesAbsent = facts[3].exists === false;
        for (let i = 0; i < names.length; ++i) {
            const f = facts[i];
            if (i === 3 && notesAbsent) {
                if (f.regular !== false || f.readable !== false || bytes[i] !== "")
                    errors.push("Absent notes require precise supported-root absence");
            } else if (f.exists !== true || f.regular !== true || f.readable !== true || !(f.bytes > 0) || bytes[i].length === 0) {
                errors.push(names[i] + " requires actual nonempty regular readable bytes");
            }
        }
        const csv = (index, prefix, completeHeader) => {
            const lines = bytes[index].split(/\r?\n/);
            if (lines[lines.length - 1] === "")
                lines.pop();
            const header = (lines.shift() ?? "").split(",");
            if (JSON.stringify(header.slice(0, prefix.length)) !== JSON.stringify(prefix) || (completeHeader && header.length !== prefix.length))
                errors.push(names[index] + " does not carry its declared header");
            const rows = lines.map(line => line.split(","));
            if (rows.some(row => row.length !== header.length))
                errors.push(names[index] + " contains an incomplete record");
            return rows;
        };
        const results = csv(0, ["file_path", "fit_result.reduced_chi_square", "fit_result.success", "fit_result.iterations"], false);
        const provenance = csv(1, ["file_path", "descent", "chi_square_tolerance", "max_iterations", "termination"], true);
        const paths = ["experiments/scan/01.xy", "experiments/scan/02.xy"];
        for (const rows of [results, provenance])
            if (JSON.stringify(rows.map(row => row[0]).sort()) !== JSON.stringify(paths))
                errors.push("The independently declared scan requires both unique result identities");
        if (notesAbsent && provenance.some(row => row[4] === "refused"))
            errors.push("A refused fit requires its declared notes record");
        let notes = [];
        if (!notesAbsent) {
            notes = csv(3, ["file_path", "negative_points", "skipped_dataset", "refusal"], true);
            const seen = [];
            for (const row of notes) {
                if (!paths.includes(row[0]) || seen.includes(row[0]) || !/^\d{1,12}$/.test(row[1]) || !["True", "False"].includes(row[2]))
                    errors.push("Notes retain their declared unique four-cell domain");
                seen.push(row[0]);
            }
        }
        for (const row of provenance)
            if (row[4] === "refused" && !notes.some(note => note[0] === row[0] && note[2] === "False"))
                errors.push("Each refused dataset requires its own non-skipped note");
        try {
            const run = JSON.parse(bytes[2]);
            if (!run || Array.isArray(run) || typeof run.template !== "string" || !run.template || run.last !== "scan" || typeof run.mixed !== "boolean" || !["", "success", "maxIterations", "noStep", "notConverged", "stopped", "failed"].includes(run.outcome) || (run.seconds !== undefined && (typeof run.seconds !== "number" || !isFinite(run.seconds) || run.seconds < 0)))
                errors.push("The run record retains its declared scan identity and field types");
        } catch (error) {
            errors.push("The run record must be actual JSON");
        }
        return errors;
    }
    function resultBytes() {
        const directory = Session.projectDirectoryUrl(Session.project.path);
        verify(String(directory).startsWith("file:"), "Result observations use the current project's converted local directory URL");
        const observations = ["results.csv", "results-provenance.csv", "scan-run.json", "scan-notes.csv"].map(name => {
            const relative = "analysis/" + name;
            const observed = SettingsProof.fileObservation(directory, relative);
            verify(!observed.error, "The saved scan file must be readable: " + relative + ": " + observed.error);
            compare(observed.path, Session.project.path + "/" + relative, "Scan bytes come from the opened project's analysis directory");
            if (name !== "scan-notes.csv") {
                verify(observed.exists, "Every completed scan stores its required result and provenance file: " + relative);
                verify(observed.base64.length > 0, "Required scan result and provenance observations contain real bytes: " + relative);
            }
            return observed.exists ? {
                exists: true,
                bytes: observed.base64
            } : {
                exists: false
            };
        });
        resultSemanticBytes();
        return observations;
    }
    function resultSemanticBytes() {
        const path = Session.projectDirectoryUrl(Session.project.path);
        const names = ["results.csv", "results-provenance.csv", "scan-run.json", "scan-notes.csv"];
        const facts = names.map(name => SettingsProof.fileFacts(path, "analysis/" + name));
        const bytes = names.map((name, index) => facts[index].exists && facts[index].readable ? SettingsProof.text(path, "analysis/" + name) : "");
        const problems = resultFileProblems(bytes, facts);
        compare(problems.length, 0, "Concrete result/provenance identities precede byte comparison: " + JSON.stringify({
            problems,
            facts
        }));
        return bytes;
    }
    function test_result_file_admission_guards() {
        const bytes = ["file_path,fit_result.reduced_chi_square,fit_result.success,fit_result.iterations\nexperiments/scan/01.xy,1,True,1\nexperiments/scan/02.xy,1,True,1\n", "file_path,descent,chi_square_tolerance,max_iterations,termination\nexperiments/scan/01.xy,qr,0,1,chi_converged\nexperiments/scan/02.xy,qr,0,1,chi_converged\n", '{"template":"independent-control","last":"scan","mixed":false,"outcome":"success"}', ""];
        const facts = bytes.map(text => text ? {
                exists: true,
                regular: true,
                readable: true,
                bytes: text.length
            } : {
                exists: false,
                regular: false,
                readable: false
            });
        compare(resultFileProblems(bytes, facts).length, 0, "Notes may genuinely be absent for this independently positive-input scan");
        const present = bytes.slice(), presentFacts = facts.slice();
        present[3] = "file_path,negative_points,skipped_dataset,refusal\nexperiments/scan/01.xy,1,False,\n";
        presentFacts[3] = {
            exists: true,
            regular: true,
            readable: true,
            bytes: present[3].length
        };
        compare(resultFileProblems(present, presentFacts).length, 0, "Present notes retain a concrete valid schema");
        const refused = present.slice(), refusedFacts = presentFacts.map(item => Object.assign({}, item));
        refused[1] = refused[1].replace("chi_converged", "refused");
        refused[3] = "file_path,negative_points,skipped_dataset,refusal\nexperiments/scan/01.xy,0,False,independent-refusal\n";
        refusedFacts[3].bytes = refused[3].length;
        compare(resultFileProblems(refused, refusedFacts).length, 0, "A refused dataset is admitted only with its own declared non-skipped note");
        for (const kind of ["header-only-refusal-note", "other-dataset-refusal-note", "refusal-note-marked-skipped"]) {
            const b = refused.slice(), f = refusedFacts.map(item => Object.assign({}, item));
            if (kind === "header-only-refusal-note")
                b[3] = b[3].split("\n")[0] + "\n";
            if (kind === "other-dataset-refusal-note")
                b[3] = b[3].replace("01.xy", "02.xy");
            if (kind === "refusal-note-marked-skipped")
                b[3] = b[3].replace(",False,", ",True,");
            f[3].bytes = b[3].length;
            verify(resultFileProblems(b, f).includes("Each refused dataset requires its own non-skipped note"), "The actual missing relation is reached and refused: " + kind);
        }
        for (const kind of ["missing-result", "unreadable-notes", "directory", "wrong-header", "malformed-run", "duplicate-path", "refusal-without-notes"]) {
            const b = bytes.slice(), f = facts.map(item => Object.assign({}, item));
            if (kind === "missing-result") {
                b[0] = "";
                f[0] = {
                    exists: false,
                    regular: false,
                    readable: false
                };
            }
            if (kind === "unreadable-notes")
                f[3] = {
                    exists: true,
                    regular: true,
                    readable: false
                };
            if (kind === "directory")
                f[0].regular = false;
            if (kind === "wrong-header")
                b[1] = b[1].replace("termination", "unknown");
            if (kind === "malformed-run")
                b[2] = "{";
            if (kind === "duplicate-path")
                b[0] = b[0].replace("02.xy", "01.xy");
            if (kind === "refusal-without-notes")
                b[1] = b[1].replace("chi_converged", "refused");
            verify(resultFileProblems(b, f).length > 0, "The concrete admission escape is armed and refused: " + kind);
        }
    }
    function checkFileObserver() {
        const directory = SettingsProof.emptyDirectory();
        verify(SettingsProof.write(directory, "empty", ""), "The observer witness stores an independently authored empty file");
        const empty = SettingsProof.fileObservation(directory, "empty");
        verify(!empty.error && empty.exists && empty.base64 === "", "An empty readable file is present with zero bytes");
        const absent = SettingsProof.fileObservation(directory, "absent");
        verify(!absent.error && absent.exists === false && absent.base64 === undefined, "An absent optional file differs from an empty readable file");
        verify(!!SettingsProof.fileObservation(directory, ".").error, "Reading a directory as a file is an observation error");
        verify(!!SettingsProof.fileObservation(Session.project.path, "project.edi").error, "A plain path is refused before any cwd-relative observation");
        verify(!!SettingsProof.projectBytes(Session.project.path).error, "A plain path cannot observe the unrelated working directory as project bytes");
        verify(!SettingsProof.write(Session.project.path, "observer-escape", "bad"), "A plain path cannot write relative to the working directory");
        verify(!SettingsProof.remove(Session.project.path, "project.edi"), "A plain path cannot remove a file relative to the working directory");
        let refused = false;
        try {
            SettingsProof.text(Session.project.path, "project.edi");
        } catch (error) {
            refused = true;
        }
        verify(refused, "The text convenience reader raises an error for an unconverted path");
        refused = false;
        try {
            SettingsProof.text(directory, "absent");
        } catch (error) {
            refused = true;
        }
        verify(refused, "The text convenience reader raises an error for a missing required file");
        compare(SettingsProof.text(directory, "empty"), "", "A valid local URL reads the empty file without an error");
    }

    function resultRows() {
        const table = Session.project.fit.results, rows = [];
        for (let i = 0; i < table.count; ++i)
            rows.push(["metric", "value", "outcome"].map(column => table.text(i, column)));
        return JSON.stringify(rows);
    }
    function outdatedScan(mode) {
        open("scan");
        Session.project.analysis.fittingMode = mode;
        Preferences.showFitResults = false;
        Session.project.fit.start();
        finish();
        tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 10000, "The followed final dataset settles before editing the scan template");
        compare(Session.project.fit.scanFitted, 2, "Both independently authored scan files have results before the template edit");
        verify(!Session.project.fit.outOfDate, "A freshly completed scan is current before its template changes");
        dialogs().forEach(dialog => dialog.close());
        const before = {
            bytes: resultBytes(),
            rows: resultRows(),
            outcome: Session.project.fit.outcome
        };
        const parameters = Session.project.parameters;
        let cell = null;
        for (let i = 0; i < parameters.count; ++i)
            if (parameters.item(i, "parameter").uid === "cell.length_a" && parameters.item(i, "parameter").blockName === "phase")
                cell = parameters.item(i, "parameter");
        verify(cell !== null, "The independent scan fixture exposes its template cell length");
        before.edited = cell.value + .03125;
        cell.value = before.edited;
        compare(cell.lastError, "", "The template edit has no silent model refusal");
        compare(cell.value, before.edited, "The template cell edit is admitted without changing its requested value");
        tryCompare(Session.project.fit, "outOfDate", true, 2000, "A nontrivial template cell edit marks the retained scan results outdated");
        compare(JSON.stringify(resultBytes()), JSON.stringify(before.bytes), "Editing the template preserves all previous result and provenance bytes");
        compare(resultRows(), before.rows, "Editing the template preserves the previous results model");
        return before;
    }
    function test_outdated_outcome_data() {
        return outdatedModes();
    }
    function test_outdated_outcome(data) {
        const before = outdatedScan(data.tag);
        const outcome = findChild(appWindow, "statusBar.fit.outcome");
        verify(outcome !== null && outcome.visible && actionable(outcome), "Outdated scan results remain accessible from the outcome button");
        compare(caption(outcome), "Outdated", "The outcome button replaces its previous outcome with Outdated");
        compare(icon(outcome), "history", "The Outdated outcome uses the history icon");
        compare(outcome.iconColor, EaStyle.Colors.orange, "The Outdated history icon is amber");
        const separate = findChild(appWindow, "statusBar.fit.outOfDate");
        verify(separate === null || !separate.visible, "The status bar has no separate out of date label");
    }
    function test_outdated_results_banner_data() {
        return outdatedModes();
    }
    function test_outdated_results_banner(data) {
        const before = outdatedScan(data.tag);
        const outcome = findChild(appWindow, "statusBar.fit.outcome");
        verify(outcome !== null && outcome.visible && actionable(outcome), "Previous outdated results retain their real window-opening action");
        keyAction(outcome, data.tag === "sequential" ? Qt.Key_Space : Qt.Key_Return, true);
        tryVerify(() => dialogs().length === 1, 1000, "The Outdated outcome opens the retained results window");
        tryVerify(() => resultsPresentationReady(), 1000, "The retained result rows are rendered after keyboard activation");
        const dialog = dialogs()[0];
        const banner = View.textItems(dialog.contentItem).find(item => item.visible && item.text === "These results are from before your parameter changes. Fit again to update them.");
        verify(banner !== undefined && Ui.exposed(banner), "Previous results display the owner's exact visible warning banner");
        const table = findChild(dialog.contentItem, "fit.results.list");
        let amber = colorsMatch(banner.color, EaStyle.Colors.orange);
        for (let item = banner.parent; item && item !== dialog.contentItem && !View.descendants(item).includes(table); item = item.parent)
            amber = amber || View.descendants(item).some(child => child.visible && child.color && colorsMatch(child.color, EaStyle.Colors.orange));
        verify(amber, "The stale-results warning banner itself has a visible amber treatment");
        verify(table !== null && banner.mapToItem(dialog.contentItem, 0, banner.height).y <= table.mapToItem(dialog.contentItem, 0, 0).y, "The warning banner sits above the retained result table");
        verify(View.textItems(dialog.contentItem).some(item => item.visible && item.text === FitOutcomes.word(before.outcome)), "The original outcome remains visible inside the outdated results window");
        compare(resultRows(), before.rows, "Opening outdated results leaves the previous scientific result rows unchanged");
    }
    function test_refit_and_undo_data() {
        return outdatedModes();
    }
    function test_refit_and_undo(data) {
        const before = outdatedScan(data.tag);
        checkFileObserver();
        fitState("Refit");
        verify(Session.project.fit.available && actionable(shortcut()), "Outdated completed scans enable Refit without Reset");
        runningSpy.clear();
        keyAction(shortcut(), data.tag === "sequential" ? Qt.Key_Space : Qt.Key_Return, true);
        verify(runningSpy.count > 0, "Actual Refit key input starts the same worker as pointer input");
        finish();
        compare(Session.project.fit.scanFitted, 2, "Refit processes every scan file again rather than continuing after the last result");
        verify(!Session.project.fit.outOfDate, "A full Refit clears the outdated state");
        verify(JSON.stringify(resultBytes()) !== JSON.stringify(before.bytes), "After a " + data.tag + " scan completes, editing the template cell length by 0.03125 and activating Refit must replace the saved result generation; observed all four saved result/provenance files byte-identical to before the edit (scanFitted=" + Session.project.fit.scanFitted + ", outOfDate=" + Session.project.fit.outOfDate + ")");
        verify(Session.project.canUndo, "Refit retains a single reversible result replacement");
        Session.project.undo();
        tryVerify(() => !Session.project.calculating && Session.project.fit.outOfDate, 10000, "One Undo restores the previous outdated result generation");
        compare(JSON.stringify(resultBytes()), JSON.stringify(before.bytes), "One Undo restores every previous result and provenance byte");
        compare(resultRows(), before.rows, "One Undo restores the old scientific result rows");
        compare(Session.project.fit.outcome, before.outcome, "One Undo restores the original recorded outcome");
        fitState("Refit");
        verify(actionable(shortcut()), "Undo leaves the restored outdated results available for another Refit");
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
    function test_accessible_status_start() {
        open("single");
        fitState("Fit");
        verify(Session.project.fit.available, "The real independently measured project admits fitting");
        runningSpy.clear();
        pressAction(shortcut());
        verify(runningSpy.count > 0, "Accessible Fit starts the same actual worker through clicked");
        finish();
    }
    function test_accessible_scan_controls_data() {
        return [
            {
                tag: "scan"
            },
            {
                tag: "independent"
            }
        ];
    }
    function test_accessible_scan_controls(data) {
        test_scan_controls(data, true);
    }
}
