import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import PatternPolishAcceptance 1.0
import "UiInteraction.js" as Ui
import "E04Review.js" as View

TestCase {
    id: test
    name: "CalculationOnlyFitting"
    when: windowShown
    property var appWindow
    property var extraField
    property var source
    Component {
        id: application
        Main {}
    }
    Component {
        id: parameterField
        ParameterField {
            x: 25
            y: 80
            z: 10000
            width: 200
            height: 45
        }
    }
    SignalSpy {
        id: running
        target: Session.project ? Session.project.fit : null
        signalName: "runningChanged"
    }
    SignalSpy {
        id: recalculated
        target: Session.project
        signalName: "recalculated"
    }

    function init() {
        Session.closeProject();
        Preferences.analysisYScale = "linear";
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Calculation-only acceptance hosts the production application window");
        appWindow.width = 1300;
        // Keep the bottom fitting controls inside the headless screen for real pointer input.
        appWindow.height = 720;
        verify(waitForRendering(appWindow.contentItem), "The calculation-only window renders before input");
    }
    function cleanup() {
        if (extraField)
            extraField.destroy();
        extraField = null;
        Probe.clearWatches();
        Session.closeProject();
        appWindow.destroy();
        appWindow = null;
        Probe.releaseScratchProjects();
    }
    function ready() {
        tryVerify(() => !Session.project.calculating && !Session.project.currentExperiment.pattern.stale, 10000, "Every actual calculation publishes current pattern rows before inspection");
        compare(Session.project.currentExperiment.pattern.calculationError, "", "The authored calculation must finish without an engine error");
    }
    function open(measured) {
        source = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/excluded_display/cw"));
        let text = SettingsProof.text(source, "experiments/pattern.edi");
        verify(text.includes("phase 1\n"), "The independent cubic fixture supplies a known unit structure scale");
        text = text.replace("phase 1\n", "phase 1()\n");
        if (!measured) {
            verify(text.includes("loop_\n_data.two_theta\n"), "The authored measured loop is explicitly removed for the calculation-only control");
            text = text.split("loop_\n_data.two_theta\n")[0] + "_data_range.two_theta_min 10\n_data_range.two_theta_max 90\n_data_range.two_theta_step 0.5\n";
        }
        verify(SettingsProof.write(source, "experiments/pattern.edi", text), "The disposable project preserves the independent structure and instrument while declaring its measured-data state");
        verify(SettingsProof.write(source, "observed.xye", "10 100 2\n20 110 2\n30 120 2\n40 130 2\n50 140 2\n60 150 2\n70 160 2\n80 170 2\n90 180 2\n"), "The load-data control has independently authored positive observations and uncertainties");
        verify(Session.openProject(source), "The authored calculation-only or measured project loads through Session: " + Session.lastError);
        ready();
        compare(Session.project.currentExperiment.calculationOnly, !measured, "Measured-data presence follows the authored file rather than the project label or axis size");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1, 3000, "Analysis enters the real viewport before its fitting controls are used");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        Ui.expandGroup(test, Probe, appWindow, "group.parameters");
        verify(waitForPolish(appWindow.contentItem), "The real Analysis table finishes layout");
    }
    function control(name) {
        const item = name.startsWith("statusBar.") ? Ui.control(Probe, appWindow, name) : Ui.find(Ui.page(appWindow), name, true);
        verify(item !== null, "The actual Analysis page exposes " + name);
        return item;
    }
    function scale() {
        const item = Session.project.currentExperiment.scale;
        verify(item !== null && item.refinable, "The witness reaches the real editable structure-scale parameter");
        return item;
    }
    function scaleRow() {
        const table = control("parameters.list");
        table.sourceModel.nameFilter = "scale";
        tryCompare(table, "count", 1, 2000, "The real name filter isolates the single authored structure scale");
        table.positionViewAtIndex(0, ListView.Contain);
        table.forceLayout();
        tryVerify(() => Ui.find(table, "parameters.value.0", true) !== null, 2000, "The scale's actual row delegate is materialized before input");
        return table;
    }
    function input(item, button) {
        Ui.scrollIntoView(item);
        verify(waitForPolish(appWindow.contentItem), "Attempted fitting and free-control pointer targets finish their actual layout");
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "Attempted fitting and free-control pointer targets reach a settled frame");
        const point = Ui.clickPoint(item);
        verify(point !== null, "The attempted fitting route has a real pointer target");
        mouseClick(item, point.x, point.y, button === undefined ? Qt.LeftButton : button);
    }
    function flags() {
        return Probe.rows(Session.project.parameters).map(row => [String(row.path), row.parameter.free]);
    }
    function noFreeChange(action, reason) {
        const before = JSON.stringify(flags());
        const modified = Session.project.modified;
        const watch = Probe.watch(scale());
        action();
        verify(waitForPolish(appWindow.contentItem), "Attempted free edits settle through the production event loop");
        compare(JSON.stringify(flags()), before, "Without measured data every free flag stays unchanged: " + reason);
        compare((Probe.events(watch).freeChanged || []).length, 0, "Blocked free edits publish no parameter-free change");
        compare(Session.project.modified, modified, "Blocked free edits do not dirty the project");
    }
    function test_start_data() {
        return ["disabled", "tooltip", "hover-tooltip", "pointer", "keyboard", "invokable"].map(route => ({
                    tag: route,
                    route: route
                }));
    }
    function test_start(data) {
        open(false);
        const fit = Session.project.fit, button = control("statusBar.fit.button");
        if (data.route === "disabled") {
            verify(!button.clickable && !fit.available, "A project without measured data disables both Start fitting and its application command");
        } else if (data.route === "tooltip") {
            compare(button.ToolTip.text, "Fit the free parameters", "The disabled status Fit retains the exact owner tooltip");
            verify(/measur/i.test(fit.unavailableReason) && /data/i.test(fit.unavailableReason), "The unavailable model still explains the measured-data requirement");
        } else if (data.route === "hover-tooltip") {
            Ui.scrollIntoView(button);
            verify(waitForPolish(appWindow.contentItem), "The disabled fitting hover target completes its actual layout");
            appWindow.update();
            verify(waitForRendering(appWindow.contentItem), "The disabled fitting hover target reaches a settled frame");
            const point = Ui.clickPoint(button);
            verify(point !== null, "The disabled fitting button remains reachable for its explanatory hover");
            mouseMove(button, point.x, point.y);
            tryVerify(() => Probe.objectsWithProperty(button, "enterAnimationDuration").some(tip => tip.visible && tip.opened && tip.opacity >= 0.99 && View.textItems(tip.contentItem).some(item => item.text === "Fit the free parameters")), 3000, "Hovering disabled Start fitting displays the owner tooltip when preferences enable it");
        } else {
            running.clear();
            const status = fit.status;
            if (data.route === "invokable")
                fit.start();
            else {
                if (data.route === "keyboard") {
                    Ui.scrollIntoView(button);
                    appWindow.requestActivate();
                    button.forceActiveFocus();
                    tryVerify(() => !button.clickable || button.activeFocus, 1000, "An enabled fitting button receives focus before the independent keyboard attempt");
                    verify(SettingsProof.key(button, Qt.Key_Space), "The fitting keyboard attempt sends Space to the actual application window");
                } else
                    input(button);
            }
            verify(waitForRendering(appWindow.contentItem), "Attempted fitting input is delivered before its effect is checked");
            compare(running.count, 0, "No pointer, keyboard or direct application route starts a fit without measured data");
            compare(fit.status, status, "A blocked fit does not become a failed attempted fit");
        }
    }
    function test_free_controls_data() {
        return ["checkbox", "checkbox-keyboard", "header", "header-pointer", "value-menu", "field-menu", "value-signal", "field-signal"].map(route => ({
                    tag: route,
                    route: route
                }));
    }
    function test_free_controls(data) {
        open(false);
        scaleRow();
        if (data.route === "checkbox") {
            const box = control("parameters.free.0");
            verify(!box.enabled, "The visible free checkbox is disabled in a calculation-only project");
            noFreeChange(() => input(box), "A disabled free checkbox cannot change the saved free flag");
        } else if (data.route === "checkbox-keyboard") {
            const box = control("parameters.free.0");
            noFreeChange(() => {
                Ui.scrollIntoView(box);
                appWindow.requestActivate();
                box.forceActiveFocus();
                tryVerify(() => !box.enabled || box.activeFocus, 1000, "An enabled free checkbox receives focus before its keyboard attempt");
                verify(SettingsProof.key(box, Qt.Key_Space), "The free-checkbox keyboard attempt reaches the actual application window");
            }, "Keyboard input cannot toggle a free checkbox without measured data");
        } else if (data.route === "header" || data.route === "header-pointer") {
            const header = control("parameters.freeHeader");
            if (data.route === "header") {
                compare(header.interactionEnabled, false, "The exported header interaction state follows the disabled bulk pointer actor without measured data");
            } else {
                noFreeChange(() => input(header), "Clicking the disabled free header cannot change parameter flags");
                verify(!Probe.visiblePopups(appWindow).some(popup => findChild(popup, "parameters.freeHeader.free") !== null), "The disabled free header cannot open its bulk-free menu");
            }
        } else {
            let field = control("parameters.value.0");
            if (data.route.startsWith("field-")) {
                extraField = parameterField.createObject(appWindow.contentItem, {
                    item: scale()
                });
                verify(extraField !== null && extraField.enabled, "The production parameter field stays editable without measured data");
                field = extraField;
            }
            if (data.route.endsWith("signal")) {
                noFreeChange(() => field.fitToggled(!scale().free), "The parameter menu's free signal cannot bypass the no-measured-data rule");
            } else {
                input(field, Qt.RightButton);
                tryVerify(() => field.fitCheckBox !== null, 1000, "The real parameter context menu exposes its free-toggle control");
                verify(!field.fitCheckBox.visible || !field.fitCheckBox.enabled, "Value-cell and parameter-field menus cannot offer an active free toggle without measured data");
            }
        }
    }
    function test_free_commands_data() {
        const rows = [];
        for (const route of ["parameter", "bulk", "table-role"])
            for (const makeFree of [false, true])
                rows.push({
                    tag: route + "-" + makeFree,
                    route: route,
                    makeFree: makeFree
                });
        return rows;
    }
    function test_free_commands(data) {
        open(false);
        const rows = Probe.rows(Session.project.parameters);
        const uid = data.makeFree ? "cell.length_a" : "linked_structure.scale";
        const index = rows.findIndex(row => String(row.parameter.uid) === uid && row.parameter.free !== data.makeFree);
        verify(index >= 0, "The authored project reaches both fixed-to-free and free-to-fixed attempts");
        const parameter = rows[index].parameter;
        noFreeChange(() => {
            if (data.route === "parameter")
                parameter.free = data.makeFree;
            else if (data.route === "bulk")
                Session.project.setParametersFree([parameter], data.makeFree);
            else
                Probe.writeRole(Session.project.parameters, index, "free", data.makeFree);
        }, "Direct parameter, bulk-header and editable-role routes cannot toggle free without measured data");
    }
    function test_values_still_recalculate() {
        open(false);
        scaleRow();
        const cell = control("parameters.value.0");
        verify(cell.enabled && !cell.readOnly, "Calculation-only parameter values remain editable in the actual table");
        const before = Probe.rows(Session.project.currentExperiment.pattern);
        verify(before.length > 2 && before.some(row => row.intensityCalc > row.intensityBkg), "The physical scale control starts with a nonzero calculated peak contribution");
        const chart = View.find(Ui.page(appWindow), "chart");
        verify(chart !== null, "Analysis retains its real calculated-pattern chart");
        tryVerify(() => PatternProof.series(chart, "chart.series.calc").some(line => line.points.some(point => isFinite(point.y))), 3000, "The original calculated pattern reaches its actual chart series before the value edit");
        const drawnBefore = JSON.stringify(PatternProof.series(chart, "chart.series.calc"));
        recalculated.clear();
        input(cell);
        appWindow.requestActivate();
        cell.forceActiveFocus();
        tryCompare(cell, "activeFocus", true, 1000, "The real calculation-only value editor receives keyboard focus before typing");
        verify(SettingsProof.type(cell, "2"), "The actual scale value editor accepts real keyboard text");
        verify(SettingsProof.key(cell, Qt.Key_Return), "The actual scale editor commits through its ordinary Return handler");
        compare(scale().value, 2, "The requested nontrivial scale value is retained without enabling fitting");
        tryVerify(() => recalculated.count > 0 && !Session.project.calculating, 10000, "A calculation-only value edit publishes a real later calculation");
        ready();
        const after = Probe.rows(Session.project.currentExperiment.pattern);
        compare(after.length, before.length, "A scale edit preserves the independently declared calculation grid");
        let peaks = 0;
        for (let i = 0; i < before.length; ++i) {
            if (!isFinite(before[i].intensityCalc) || !isFinite(after[i].intensityCalc))
                continue;
            const background = 40 + (before[i].x - 10) / 2;
            fuzzyCompare(after[i].intensityBkg, background, 1e-8, "The authored linear background remains independent of the structure scale");
            const expected = background + 2 * (before[i].intensityCalc - background);
            fuzzyCompare(after[i].intensityCalc, expected, Math.max(1e-8, Math.abs(expected) * 1e-10), "Doubling structure scale doubles net calculated intensity at every included grid point");
            if (before[i].intensityCalc > background + 1e-5)
                peaks++;
        }
        verify(peaks > 0, "The scale invariant reaches real peaks rather than background-only identity points");
        tryVerify(() => JSON.stringify(PatternProof.series(chart, "chart.series.calc")) !== drawnBefore, 3000, "The edited calculation-only pattern replaces real chart coordinates instead of retaining the old drawing");
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "The changed calculation-only chart reaches an actual frame");
        const capture = PatternProof.capture(appWindow, "calculation-only-value-edit");
        verify(capture.openGL && capture.saved, "The editable calculation-only pattern retains a real OpenGL capture");
    }
    function measuredControls(edit) {
        verify(control("statusBar.fit.button").clickable && Session.project.fit.available, "At least one measured experiment enables Start fitting without a restart");
        scaleRow();
        verify(control("parameters.free.0").enabled && control("parameters.freeHeader").interactionEnabled === true, "Measured data enables both the free column and its bulk header");
        if (!edit)
            return;
        const before = scale().free;
        input(control("parameters.free.0"));
        compare(scale().free, !before, "Measured-data free checkboxes retain their ordinary edit behavior");
        scale().free = before;
        compare(scale().free, before, "Measured-data direct free assignment retains ordinary behavior");
        for (const makeFree of [false, true]) {
            input(control("parameters.freeHeader"));
            const name = "parameters.freeHeader." + (makeFree ? "free" : "fixed");
            tryVerify(() => Probe.visiblePopups(appWindow).some(popup => findChild(popup, name) !== null), 1000, "Measured data preserves the real bulk-free header menu");
            const popup = Probe.visiblePopups(appWindow).find(item => findChild(item, name) !== null);
            const choice = findChild(popup, name);
            verify(choice !== null && choice.enabled, "Measured-data bulk menu choices remain enabled");
            input(choice);
            compare(scale().free, makeFree, "Measured-data header actions still write the selected free or fixed state");
        }
    }
    function test_data_transitions_data() {
        return ["load", "undo-last-data", "remove-last-data"].map(flow => ({
                    tag: flow,
                    flow: flow
                }));
    }
    function test_data_transitions(data) {
        open(false);
        const project = Session.project;
        verify(project.loadDataInto(project.currentExperiment, Qt.resolvedUrl(source + "/observed.xye")), "The real plain-data loader replaces the calculation-only experiment with authored measurements");
        ready();
        compare(Session.project, project, "Loading measured data keeps the same open application project");
        verify(!project.currentExperiment.calculationOnly, "Loading measurements changes actual experiment data presence");
        measuredControls(false);
        if (data.flow === "undo-last-data") {
            project.undo();
            ready();
            verify(project.currentExperiment.calculationOnly, "Undoing the last measured-data load restores the original simulation");
        } else if (data.flow === "remove-last-data") {
            verify(project.createExperiment(), "The removal control keeps a real calculation-only experiment beside the measured one");
            project.removeExperiment(0);
            ready();
            verify(project.currentExperiment.calculationOnly, "Removing the last measured experiment leaves only a calculation-only experiment");
        } else
            return;
        verify(!control("statusBar.fit.button").clickable && !project.fit.available, "Removing the last measured data disables fitting again in the same application project");
        scaleRow();
        verify(!control("parameters.free.0").enabled && control("parameters.freeHeader").interactionEnabled === false, "Removing the last measured data disables free edits again without a restart");
    }
    function test_measured_and_mixed_projects() {
        open(true);
        measuredControls(true);
        verify(Session.project.createExperiment(), "The mixed control adds a real calculation-only experiment beside measured data");
        ready();
        verify(Session.project.currentExperiment.calculationOnly, "The mixed witness selects its calculation-only experiment");
        verify(control("statusBar.fit.button").clickable && Session.project.fit.available, "Measured data anywhere in the project enables fitting even when the selected experiment is calculation-only");
        Session.project.currentExperimentIndex = 0;
        ready();
        running.clear();
        Session.project.fit.start();
        verify(running.count > 0, "The unchanged measured-data application command really starts a fit");
        tryVerify(() => !Session.project.fit.running && Session.project.fit.canUndo, 10000, "The measured-data control completes an actual fit with an undoable result");
    }
}
