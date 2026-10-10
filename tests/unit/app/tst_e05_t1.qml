import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiChartReference 1.0
import EdiFitReference 1.0
import EasyApplication.Gui.Style as Style
import EasyApplication.Gui.Elements as Elements
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui
import "E04Review.js" as Review

// : expectations are frozen CLI fits, model data, and complete stream invariants.
TestCase {
    id: test
    name: "E05T1Fitting"
    when: windowShown
    property int savedTheme
    property var appWindow
    Component {
        id: application
        Main {}
    }
    Component {
        id: rangeField
        ParameterField {
            width: 220
            label: ""
        }
    }
    Component {
        id: ordinaryTooltip
        Elements.ToolTip {
            text: "independent style reference"
        }
    }
    function rangeTooltip(input) {
        input.forceActiveFocus();
        let warning = null;
        tryVerify(() => {
            warning = Probe.visiblePopups(appWindow).find(popup => typeof popup.text === "string" && popup.text.toLowerCase().includes("outside"));
            return warning !== undefined;
        }, 3000, "Out-of-range values explain their actual range in a visible tooltip");
        const reference = createTemporaryObject(ordinaryTooltip, input);
        verify(reference !== null, "The normal app tooltip supplies the independently retained style reference");
        compare(warning.font.family, reference.font.family, "Range tooltips retain the ordinary app tooltip font");
        compare(warning.font.pixelSize, reference.font.pixelSize, "Range tooltips retain the ordinary app tooltip text size");
        compare(warning.leftPadding, reference.leftPadding, "Range tooltips retain the ordinary app tooltip padding");
        compare(warning.topPadding, reference.topPadding, "Range tooltips retain the ordinary app tooltip arrow spacing");
        const backgrounds = Render.descendants(warning.background).filter(item => item.visible && item.radius > 0 && item.color);
        verify(backgrounds.length > 0, "The actual range tooltip has the rounded app background");
        for (const background of backgrounds) {
            compare(background.radius, reference.borderRadius, "Range tooltips retain the ordinary rounded background geometry");
            verify(background.color.r >= reference.backgroundColor.r && background.color.g < reference.backgroundColor.g && background.color.b < reference.backgroundColor.b, "The actual tooltip background is tinted by the red warned text");
        }
        const shadows = Probe.objectsWithProperty(warning.background, "shadowColor");
        verify(shadows.length > 0, "The warning tooltip has its actual app border-shadow effect");
        verify(shadows.some(shadow => String(shadow.shadowColor) === String(input.color)), "The actual tooltip border-shadow uses the warned text colour");
        input.focus = false;
        warning.close();
    }
    property var animation
    Component {
        id: flightControl
        Rectangle {
            width: 2
            height: 2
            color: "transparent"
            NumberAnimation on x {
                from: 0
                to: 20
                duration: 200
                loops: Animation.Infinite
            }
        }
    }
    function init() {
        savedTheme = Style.Colors.theme;
        Style.Colors.theme = Style.Colors.Themes.LightTheme;
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, " gate 1 uses the production app window");
        animation = flightControl.createObject(appWindow.contentItem);
    }
    function cleanup() {
        FitOracle.disarm();
        animation.destroy();
        Session.closeProject();
        appWindow.destroy();
        Style.Colors.theme = savedTheme;
    }
    function open(path) {
        Session.openProject(Probe.repoUrl(path));
        verify(Session.hasProject, " gate 1 independently declared CLI input opens");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        tryVerify(() => Ui.control(Probe, appWindow, "fitting.start") !== null, 5000, " gate 1 real fitting button reaches the selected Analysis page");
        tryVerify(() => !Session.project.calculating, 10000, " gate 1 initial calculation completes before fitting begins");
    }
    function fitPopup(name) {
        // QObject ownership includes Popup objects outside the visual item tree.
        return Probe.visibleControl(appWindow, name);
    }
    function button() {
        return Ui.control(Probe, appWindow, "fitting.start");
    }
    function canonicalStatus(value) {
        const normal = String(value).toLowerCase().replace(/[_ ]/g, "");
        return normal === "success" ? "done" : normal === "maxiterations" ? "maxiter" : normal;
    }
    function near(actual, expected) {
        return Math.abs(actual - expected) <= Math.max(5e-10, 5e-9 * Math.abs(expected));
    }
    function test_cli_fit_and_atomic_consumers_data() {
        const rows = FitOracle.cases();
        verify(rows.length > 0 && rows.some(row => row.mode === "joint"), " gate 1 CLI oracle is nonempty and covers both single and joint");
        return rows;
    }
    function test_cli_fit_and_atomic_consumers(data) {
        const expected = FitOracle.expected(data.path);
        verify(FitOracle.inputsMatchCli(data.path), " gate 1 every input byte is tied to the frozen CLI reference");
        open(data.path);
        verify(button().enabled, " gate 1 Start fitting enables every registered single or joint project");
        const project = Session.project;
        const before = FitOracle.bytes(project);
        const undo = Ui.control(Probe, appWindow, "appBar.button.undo");
        verify(undo !== null && !undo.enabled, " gate 3 app-bar Undo arrow is disabled before the first fit");
        verify(FitOracle.observe(project.fit), " gate 2 observer reaches actual fit-iteration notifications");
        Ui.click(test, Probe, appWindow, "fitting.start");
        tryVerify(() => project.fit !== undefined && project.fit.status !== "" && !project.fit.running, 20000, " gate 1 clicking Start fitting produces a stop status");
        tryVerify(() => project.fit.running === false, 20000, " gate 2 final delivery clears fitting state");
        compare(canonicalStatus(project.fit.status), expected.status.replace(/[_ ]/g, ""), " gate 1 GUI stop reason equals the CLI fit of the same project");
        compare(Number(project.fit.iterations), Number(expected.iterations), " gate 1 GUI iteration count equals frozen CLI fit");
        verify(Math.abs(Number(project.fit.goodnessOfFit.split("→").pop()) - Number(expected.reduced_chi_square)) <= .005, " gate 1 GUI chi-square equals frozen CLI fit within existing parity tolerance");
        verify(FitOracle.tableEqualsCli(project, data.path), " gates 1 4 every shown value free flag and e.s.d. equals the CLI fitted model");
        verify(FitOracle.freshCalculated(project), " gate 4 every final calculated bank equals a fresh calculation at the fitted state");
        const progress = FitOracle.progress().filter(i => i > 0);
        compare(progress, Array.from({
            length: Number(expected.iterations)
        }, (_, i) => i + 1), " gate 2 all accepted iterations notify exactly once and in order");
        verify(FitOracle.ownerThread(), " gate 2 every GUI progress notification runs on the owner thread");
        const chi = Ui.control(Probe, appWindow, "statusBar.goodnessOfFit");
        verify(chi !== null && /→|->/.test(chi.valueText), " gate 4 status bar presents chi-square before to after");
        const chart = Review.find(Ui.page(appWindow), "chart");
        verify(chart !== null, " gate 4 final result reaches the visible production chart");
        const calc = ChartOracle.object(chart, "chart.series.calc");
        tryVerify(() => ChartOracle.points(calc).length > 0, 5000, " gate 4 final calculated curve is rendered");
        tryVerify(() => FitOracle.chartFresh(chart, project), 5000, " gate 4 every actually drawn calculated point equals a fresh fitted-state calculation");
        verify(FitOracle.bankDeliveryWork(data.path, "fit").length > 0, " gate 7 actual owner delivery work is measured and reported for the existing latency ratchet");
        checkResultsPopup(expected);
        const dialog = fitPopup("fit.results");
        const close = dialog ? dialog.standardButton(Dialog.Ok) : null;
        verify(close !== null, " scope 9 finished popup has an actual close control");
        mouseClick(close);
        verify(undo.enabled, " gate 3 completed fit enables the app-bar Undo arrow");
        Ui.click(test, Probe, appWindow, "appBar.button.undo");
        tryVerify(() => FitOracle.bytes(project) === before, 10000, " gate 3 app-bar Undo restores the whole pre-fit saved state");
        verify(!undo.enabled, " gate 3 single-level Undo is consumed after restoration");
    }
    function test_fit_result_save_reopen_data() {
        return FitOracle.cases();
    }
    function test_fit_result_save_reopen(data) {
        const expected = FitOracle.expected(data.path);
        open(data.path);
        verify(button().enabled, " valid CLI fixture enables the actual Start fitting control");
        Ui.click(test, Probe, appWindow, "fitting.start");
        tryVerify(() => Session.project.fit && !Session.project.fit.running && Session.project.fit.iterations !== "", 20000, " gate 8 actual app fit completes before save");
        const popup = fitPopup("fit.results");
        verify(popup !== null && popup.visible, " gate 8 save follows the final fit delivery");
        mouseClick(popup.standardButton(Dialog.Ok));
        const target = FitOracle.directory();
        verify(Session.saveAs(target), " gate 8 app save path writes its completed fit");
        const result = FitOracle.savedResult(target);
        compare(Number(result.iterations), Number(expected.iterations), " gate 8 app save stores CLI iteration count");
        verify(near(Number(result.reduced_chi_square), Number(expected.reduced_chi_square)) && near(Number(result.prof_wr_factor), Number(expected.rwp)), " gate 8 app saved chi-square and Rwp equal the independent CLI fixtures");
        verify(Number(result.fitting_time) > 0, " gate 8 app persists a positive fit duration in seconds");
        Session.closeProject();
        verify(Session.openProject(target), " gate 8 saved app fit reopens successfully: " + Session.lastError);
        compare(Number(Session.project.fit.iterations), Number(expected.iterations), " gate 8 reopening restores status-bar iterations");
        compare(canonicalStatus(Session.project.fit.status), canonicalStatus(expected.status), " gate 8 reopening restores the last-fit stop reason");
        verify(Math.abs(Number(Session.project.fit.goodnessOfFit.split("→").pop()) - Number(expected.reduced_chi_square)) <= .005, " gate 8 reopening restores final status-bar chi-square");
        verify(Probe.rows(Session.project.fit.results).length >= 6, " gate 8 reopening restores the last fit-results table");
        verify(Ui.control(Probe, appWindow, "appBar.button.undo").enabled, " gate 8 reopened fit keeps app-bar Undo available");
        Ui.click(test, Probe, appWindow, "appBar.button.undo");
        verify(Session.save(), " gate 8 Undo can be saved through the app path");
        compare(Object.keys(FitOracle.savedResult(target)).length, 0, " gate 8 app Undo clears the persisted fit-result category");
    }
    function checkResultsPopup(expected) {
        const dialog = fitPopup("fit.results");
        verify(dialog !== null && dialog.visible, " scope 9 completed fit opens the actual fit-finished pop-up");
        const table = Review.find(dialog.contentItem, "fit.results.list");
        verify(table !== null && table.model, " scope 9 pop-up renders the fit-results metric table");
        const rows = Probe.rows(table.model);
        function metric(name) {
            const row = rows.find(row => row.metric === name);
            verify(row !== undefined, " scope 9 pop-up contains the declared " + name + " metric");
            return row.value;
        }
        compare(metric("Minimizer"), expected.minimizer, " scope 9 minimizer equals the CLI project's declared minimizer");
        compare(canonicalStatus(metric("Overall status")), canonicalStatus(expected.status), " scope 9 status equals independent CLI final result");
        verify(Number(metric("Fitting time (seconds)")) > 0, " scope 9 fitting time is positive seconds, never a frozen duration expectation");
        compare(Number(metric("Iterations")), Number(expected.iterations), " scope 9 iterations equal independent CLI final result");
        verify(Math.abs(Number(metric("Goodness-of-fit (reduced χ²)")) - Number(expected.reduced_chi_square)) <= .005, " scope 9 reduced chi-square equals independent CLI final result");
        function checkRwp(rawName, reference) {
            const row = rows.find(row => row.metric === rawName || row.metric === rawName.replace("(Rwp)", "(Rwp, %)") || row.metric === rawName + " (%)");
            verify(row !== undefined, " scope 9 each global or bank Rwp is present with its declared units");
            const percent = String(row.metric).includes("%");
            const displayed = Number(reference) * (percent ? 100 : 1);
            verify(Math.abs(Number(row.value) - displayed) <= (percent ? .005 : .00005), " scope 9 displayed Rwp equals CLI fraction with the declared percent conversion at display precision");
        }
        checkRwp("Weighted profile R-factor (Rwp)", expected.rwp);
        const banks = Object.keys(expected).filter(key => /^bank\..+\.rwp$/.test(key));
        compare(rows.filter(row => /^Rwp, /.test(row.metric)).length, banks.length, " scope 9 per-bank rows exactly cover CLI joint banks");
        banks.forEach(key => checkRwp("Rwp, " + key.slice(5, -4), expected[key]));
    }
    function test_producing_minimizer_survives_reopen_data() {
        return [
            {
                tag: "completed",
                cancelled: false,
                path: "docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project"
            },
            {
                tag: "cancelled",
                cancelled: true,
                path: "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof/project"
            }
        ];
    }
    function test_producing_minimizer_survives_reopen(data) {
        const expected = FitOracle.expected(data.path);
        open(data.path);
        mouseClick(button(), button().width / 2, button().height / 2, Qt.LeftButton, Qt.NoModifier, 0);
        if (data.cancelled) {
            verify(Session.project.fit.running, " gate 8 cancelled provenance witness starts the actual fit");
            mouseClick(button(), button().width / 2, button().height / 2, Qt.LeftButton, Qt.NoModifier, 0);
        }
        tryVerify(() => Session.project.fit && !Session.project.fit.running && Session.project.fit.iterations !== "", 20000, " gate 8 historical provenance starts with a delivered terminal result");
        if (data.cancelled)
            compare(canonicalStatus(Session.project.fit.status), "cancelled", " gate 8 provenance exercises a cancelled partial result");
        const dialog = fitPopup("fit.results");
        verify(dialog !== null && dialog.visible, " gate 8 terminal result opens the real Popup QObject");
        const before = Probe.rows(Session.project.fit.results);
        compare(before.find(row => row.metric === "Minimizer").value, expected.minimizer, " gate 8 producing minimizer matches the independent CLI input and result");
        mouseClick(dialog.standardButton(Dialog.Ok));
        const changed = expected.minimizer.includes("(fast_descent)") ? "ladder" : "fast_descent";
        Session.project.analysis.descent = changed;
        compare(Session.project.analysis.descent, changed, " gate 8 setting change reaches the current Analysis model");
        const target = FitOracle.directory();
        verify(Session.saveAs(target), " gate 8 completed and cancelled results save after a minimizer edit");
        Session.closeProject();
        verify(Session.openProject(target), " gate 8 edited minimizer and historical result reopen together");
        compare(Session.project.analysis.descent, changed, " gate 8 reopened settings preserve the changed minimizer control");
        const after = Probe.rows(Session.project.fit.results);
        compare(after.find(row => row.metric === "Minimizer").value, expected.minimizer, " gate 8 reopened historical table names the producing CLI minimizer rather than current settings");
        before.forEach(row => {
            const retained = after.find(value => value.metric === row.metric);
            verify(retained !== undefined, " gate 8 reopening retains each named historical result row");
            compare(retained.value, row.value, " gate 8 editing current minimizer changes no completed or cancelled historical metric");
        });
    }
    function test_early_stop_reasons_data() {
        return FitOracle.stopCases();
    }
    function test_early_stop_reasons(data) {
        const expected = FitOracle.expected(data.path);
        verify(FitOracle.inputsMatchCli(data.path), " gate 1 stop-case inputs are tied to actual author-time CLI fits");
        open(data.path);
        verify(button().enabled, " valid CLI fixture enables the actual Start fitting control");
        Ui.click(test, Probe, appWindow, "fitting.start");
        tryVerify(() => Session.project.fit && !Session.project.fit.running && Session.project.fit.iterations !== "", 20000, " gate 2 early-stop fit reaches final delivery");
        compare(canonicalStatus(Session.project.fit.status), canonicalStatus(expected.status), " gate 1 MaxIter and NoStep equal independently committed CLI stop reasons");
        verify(FitOracle.tableEqualsCli(Session.project, data.path), " gate 4 early-stop parameter values and errors equal independent CLI values");
        const stop = Ui.control(Probe, appWindow, "statusBar.fitStatus");
        const chi = Ui.control(Probe, appWindow, "statusBar.goodnessOfFit");
        verify(stop !== null && chi !== null && /→|->/.test(chi.valueText), " gate 4 early-stop status accompanies chi-square before to after");
        compare(canonicalStatus(stop.valueText), canonicalStatus(expected.status), " gate 4 status bar names the actual MaxIter or NoStep stop reason");
        checkResultsPopup(expected);
    }
    function test_scan_modes_are_disabled_data() {
        return [
            {
                tag: "sequential",
                mode: "sequential"
            },
            {
                tag: "independent",
                mode: "independent"
            }
        ];
    }
    function test_scan_modes_are_disabled(data) {
        open("tests/fixtures/e04_t5/" + data.mode);
        verify(!button().enabled, " gate 5 scan modes keep Start fitting disabled");
        verify(String(button().ToolTip.text).includes(data.mode), " gate 5 disabled-button tooltip names its unsupported scan mode");
    }
    function test_cancel_and_blocked_edits() {
        open("docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof/project");
        const project = Session.project;
        const before = FitOracle.bytes(project);
        const parameter = Probe.rows(project.parameters).find(row => row.free).parameter;
        const value = parameter.value;
        // No time-based waits. Fitting state is set synchronously by the actual button action.
        mouseClick(button(), button().width / 2, button().height / 2, Qt.LeftButton, Qt.NoModifier, 0);
        verify(project.fit.running === true, " gate 3 fitting state is entered before processing its final queued delivery");
        compare(button().text, "Cancel fitting", " gate 3 active fit button becomes Cancel fitting");
        parameter.value = value * 1.13;
        compare(parameter.value, value, " gate 6 fitted-input writes through GUI models are blocked while fitting");
        mouseClick(button(), button().width / 2, button().height / 2, Qt.LeftButton, Qt.NoModifier, 0);
        tryVerify(() => project.fit.running === false, 20000, " gate 3 Cancel fitting reaches final delivery");
        compare(String(project.fit.status).toLowerCase(), "cancelled", " gate 3 partial result is labelled Cancelled");
        verify(FitOracle.freshCalculated(project), " gate 3 cancelled partial result and chart calculations agree");
        const chi = Ui.control(Probe, appWindow, "statusBar.goodnessOfFit");
        verify(chi !== null && /→|->/.test(chi.valueText) && /cancelled/i.test(Ui.control(Probe, appWindow, "statusBar.fitStatus").valueText), " gate 3 Cancelled stop reason appears beside chi-square before to after");
        const popup = fitPopup("fit.results");
        verify(popup !== null && popup.visible, " scope 9 a cancelled partial result opens the final results dialog");
        mouseClick(popup.standardButton(Dialog.Ok));
        verify(Ui.control(Probe, appWindow, "appBar.button.undo").enabled, " gate 3 cancelled fit enables the app-bar Undo arrow");
        Ui.click(test, Probe, appWindow, "appBar.button.undo");
        tryVerify(() => FitOracle.bytes(project) === before, 10000, " gate 3 Undo restores the pre-cancel project byte-for-byte");
    }
    function test_calculation_only_refusal_dialog() {
        open("app/examples/pd-xray-cwl_lif/project");
        const before = FitOracle.modelValues(Session.project);
        verify(button().enabled, " gate 5 calculation-only single mode reaches the fitting refusal");
        Ui.click(test, Probe, appWindow, "fitting.start");
        tryVerify(() => {
            const error = fitPopup("fit.error");
            return error !== null && error.visible && error.message.length > 0;
        }, 10000, " gate 5 actual message dialog displays the refused fit reason");
        compare(FitOracle.modelValues(Session.project), before, " gate 5 refusal preserves all saved model bytes");
        const results = fitPopup("fit.results");
        verify(results === null || !results.visible, " scope 9 refusal never opens a fit-finished pop-up");
        verify(!Ui.control(Probe, appWindow, "appBar.button.undo").enabled, " gate 5 refused fit creates no Undo state");
    }
    function test_failed_fit_dialog() {
        const reference = FitOracle.refusalCase();
        verify(reference.path !== undefined && reference.record.status === "error", " gate 5 failed-fit fixture is backed by an actual CLI error");
        open(reference.path);
        verify(button().enabled, " gate 5 a loaded measured single project reaches the actual fit attempt");
        const before = FitOracle.bytes(Session.project);
        Ui.click(test, Probe, appWindow, "fitting.start");
        tryVerify(() => {
            const error = fitPopup("fit.error");
            return error !== null && error.visible && error.message.length > 0;
        }, 10000, " gate 5 failed fit displays its reason in the actual message dialog");
        const error = fitPopup("fit.error");
        verify(String(error.message).includes(reference.reason), " gate 5 the dialog contains the independently recorded CLI failure reason");
        compare(FitOracle.bytes(Session.project), before, " gate 5 failed fit preserves all saved model bytes");
        const results = fitPopup("fit.results");
        verify(results === null || !results.visible, " scope 9 a failed fit never opens a successful fit-finished popup");
        verify(!Ui.control(Probe, appWindow, "appBar.button.undo").enabled, " gate 5 failed fit leaves no app-bar Undo entry");
    }
    function test_animated_zoom_matches_instant_data() {
        return [
            {
                tag: "rectangle",
                action: "rectangle"
            },
            {
                tag: "wheel",
                action: "wheel"
            },
            {
                tag: "reset",
                action: "reset"
            }
        ];
    }
    function test_animated_zoom_matches_instant(data) {
        open("docs/user/cli/pd-neut-cwl_lab6-echidna_fcj-asymmetry/project");
        const chart = Review.find(Ui.page(appWindow), "chart");
        const controller = FitOracle.controller(chart);
        verify(controller !== null, " scope 8 animated zoom exercises the production chart controller");
        const axis = ChartOracle.object(chart, "chart.axis.x");
        const left = axis.min, right = axis.max, span = right - left;
        const yAxis = ChartOracle.object(chart, "chart.axis.y");
        const bottom = yAxis.min, top = yAxis.max, ySpan = top - bottom;
        let targetBottom = top - (.85 * controller.plotHeight / controller.plotHeight) * ySpan;
        let targetTop = top - (.15 * controller.plotHeight / controller.plotHeight) * ySpan;
        let targetLeft = left + (.2 * controller.plotWidth / controller.plotWidth) * span, targetRight = left + (.8 * controller.plotWidth / controller.plotWidth) * span;
        if (data.action === "reset") {
            controller.zoomTo(.2 * controller.plotWidth, .8 * controller.plotWidth, .15 * controller.plotHeight, .85 * controller.plotHeight);
            tryVerify(() => axis.min === targetLeft && axis.max === targetRight, 5000, " scope 8 reset starts from the independently specified nontrivial zoom range");
            targetLeft = left;
            targetRight = right;
            targetBottom = bottom;
            targetTop = top;
        }
        const startLeft = axis.min, startRight = axis.max;
        verify(FitOracle.observePresentation(controller), " scope 8 animated frames are measured on the actual owner delivery path");
        if (data.action === "rectangle")
            controller.zoomTo(.2 * controller.plotWidth, .8 * controller.plotWidth, .15 * controller.plotHeight, .85 * controller.plotHeight);
        else if (data.action === "wheel") {
            // Prior instant wheel formula (ADR-0017): one notch scales the span by 0.8.
            const factor = Math.pow(.8, 120 / 120);
            const anchor = left + (.25 * controller.plotWidth / controller.plotWidth) * span;
            targetLeft = anchor - (anchor - left) * factor;
            targetRight = anchor + (right - anchor) * factor;
            const instantY = FitOracle.instantFittedY(Session.project, targetLeft, targetRight);
            targetBottom = instantY.min;
            targetTop = instantY.max;
            controller.wheelAt(.25 * controller.plotWidth, 120);
        } else
            mouseClick(ChartOracle.object(chart, "chart.toolbar.reset"));
        let intermediate = false, ended = false;
        for (let frame = 0; frame < 180 && !ended; ++frame) {
            verify(waitForRendering(appWindow.contentItem, 5000), " scope 8 zoom progress is observed in rendered frames without sleeping");
            const atStart = axis.min === startLeft && axis.max === startRight;
            ended = axis.min === targetLeft && axis.max === targetRight && yAxis.min === targetBottom && yAxis.max === targetTop;
            if (!atStart && !ended)
                intermediate = true;
        }
        verify(intermediate, " scope 8 zoom shows an intermediate frame instead of an instant range jump");
        verify(ended, " scope 8 animation ends at exactly the prior instant zoom ranges");
        verify(FitOracle.pointsEqualInstant(chart, Session.project, targetLeft, targetRight), " scope 8 regression against the instant path preserves every final decimated point exactly");
        verify(FitOracle.bankDeliveryWork("docs/user/cli/pd-neut-cwl_lab6-echidna_fcj-asymmetry/project", "zoom-" + data.action).length > 0, " scope 8 animated presentation work is reported for the  median ratchet");
    }
    function test_fitted_values_outside_range_are_red_data() {
        return FitOracle.cases();
    }
    function test_fitted_values_outside_range_are_red(data) {
        const expected = FitOracle.fittedRangeRows(data.path);
        verify(expected.length > 0, " scope 11 independent CLI fixtures include fitted rows with declared ranges");
        open(data.path);
        verify(button().enabled, " valid CLI fixture enables the actual Start fitting control");
        Ui.click(test, Probe, appWindow, "fitting.start");
        tryVerify(() => Session.project.fit && !Session.project.fit.running && Session.project.fit.iterations !== "", 20000, " scope 11 table coloring follows the final fit delivery");
        const popup = fitPopup("fit.results");
        verify(popup !== null && popup.visible, " scope 11 fitted table inspection follows the final popup");
        mouseClick(popup.standardButton(Dialog.Ok));
        const table = Ui.control(Probe, appWindow, "parameters.list");
        verify(table !== null, " scope 11 actual Analysis parameter table is rendered");
        Ui.scrollIntoView(table);
        verify(waitForPolish(appWindow, 2000), " scope 11 actual table layout settles before inspecting colors");
        const rows = Probe.rows(table.model);
        let outside = 0, inside = 0;
        expected.forEach(reference => {
            const actual = FitOracle.rawParameter(Session.project, reference.path);
            verify(actual.value !== undefined && near(actual.value, reference.value), " scope 11 every fitted CLI value remains intact, including symmetry followers");
            compare(actual.independent, reference.independent, " scope 11 actual parameter freedom equals the independent crysta symmetry map");
            const index = rows.findIndex(row => row.path === reference.path);
            if (!reference.independent) {
                compare(index, -1, " scope 11 ADR-0019 symmetry followers have no Analysis table row");
                return;
            }
            verify(index >= 0, " scope 11 every independent fitted CLI identity is present in the table");
            verify(near(rows[index].parameter.value, reference.value), " scope 11 out-of-range fitted values are retained at CLI precision");
            table.forceLayout();
            table.positionViewAtIndex(index, ListView.Center);
            tryVerify(() => Review.find(table, "parameters.value." + index) !== null, 2000, " scope 11 scrolling instantiates every actual fitted value cell");
            const cell = Review.find(table, "parameters.value." + index);
            tryVerify(() => (String(cell.color).toLowerCase() === String(Style.Colors.red).toLowerCase()) === reference.outside, 2000, " scope 11 value text is red exactly for fitted rows outside ParameterSpec.range");
            if (reference.outside) {
                rangeTooltip(cell);
                const field = createTemporaryObject(rangeField, appWindow.contentItem, {
                    item: rows[index].parameter,
                    x: 10,
                    y: 10
                });
                verify(field !== null, "The outside-range CLI parameter also reaches the standalone field");
                compare(field.color, Style.Colors.red, "Standalone and table consumers both colour retained outside-range values red");
                rangeTooltip(field);
                field.destroy();
                ++outside;
            } else
                ++inside;
        });
        verify(inside > 0, " scope 11 in-range fitted rows provide the non-red control");
        if (data.path.includes("cosio-d20_start-1"))
            verify(outside > 0 && expected.some(row => row.path.includes("Co1") && row.value < 0 && row.outside), " scope 11 negative CLI Co1 ADP is the nontrivial zero-to-ten range witness");
    }
    function test_hover_readout_data() {
        return [
            {
                tag: "data",
                pane: 0
            },
            {
                tag: "residual",
                pane: 2
            },
            {
                tag: "bragg",
                pane: 1
            }
        ];
    }
    function test_hover_readout(data) {
        open("docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project");
        const chart = Review.find(Ui.page(appWindow), "chart");
        verify(chart !== null, " gate 6 hover reaches the production pattern chart");
        const controller = FitOracle.controller(chart);
        verify(controller !== null, " gate 6 hover reaches actual chart controller");
        const r = FitOracle.hoverReference(controller, Session.project, data.pane);
        verify(r.x !== undefined, " gate 6 independent source row and signed Miller indices exist");
        const height = data.pane === 2 ? controller.residualPlotHeight : data.pane === 1 ? 100 : controller.plotHeight;
        const low = data.pane === 1 ? 0 : data.pane === 2 ? controller.residualMin : controller.yMin;
        const high = data.pane === 1 ? 1 : data.pane === 2 ? controller.residualMax : controller.yMax;
        const y = data.pane === 2 ? r.resid : r.y;
        const text = controller.hoverReadout((r.x - controller.xMin) / (controller.xMax - controller.xMin) * controller.plotWidth, (high - y) / (high - low) * height, data.pane, height);
        if (data.pane === 1) {
            verify(text.includes(r.name) && text.includes(r.hkl), " gate 6 Bragg read-out shows structure and independently loaded signed Miller tuple");
        } else {
            ["Imeas", "Ibkg", "Icalc"].forEach(label => verify(text.includes(label), " gate 6 data and residual hover show each required series quantity"));
            [r.x, r.meas, r.bkg, r.calc, r.resid].forEach(value => verify(Probe.plainText(text).includes(Number(value).toLocaleString("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                })), " gate 6 every displayed hover number equals its independent source row at read-out precision"));
            ["#03a9f4", "#f44336", "#607d8b", "#8bc34a"].forEach(color => verify(text.toLowerCase().includes(color), " gate 6 every read-out quantity uses its ADR-0017 light series colour"));
        }
    }
}
