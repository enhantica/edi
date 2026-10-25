// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiChartReference 1.0
import ReportAcceptance 1.0
import "../../unit/app/RenderedTable.js" as Render
import "../../unit/app/UiInteraction.js" as Ui

Item {
    Component { id: appFactory; Main { visible: true; width: 1280; height: 900 } }
    Component { id: fieldFactory; ParameterField { x: 20; y: 55; width: 180; z: 10000 } }
    TestCase {
        id: test
        name: "PatternRange"
        when: windowShown
        property var app: null
        property var chart: null
        property var field: null
        property var axis: null
        property var pressedSlider: null
        SignalSpy { id: maximumChanges; target: test.axis; signalName: "maxChanged" }
        SignalSpy { id: minimumChanges; target: test.axis; signalName: "minChanged" }
        function cleanup() {
            if (pressedSlider) mouseRelease(pressedSlider, pressedSlider.width / 2, pressedSlider.height / 2);
            pressedSlider = null;
            if (field) field.destroy();
            field = null;
            axis = null;
            Session.closeProject();
            if (app) { app.close(); app.destroy(); }
            app = null;
        }
        function object(name) {
            const result = ChartOracle.object(chart, name);
            verify(result !== null, "The live Pattern chart exposes its actual " + name + " observation");
            return result;
        }
        function settled() {
            tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 15000, "Actual scientific calculation completes before the Pattern range is read");
            app.update();
            verify(waitForPolish(chart) && waitForRendering(chart), "The actual Pattern chart renders its calculated curve before range checks");
        }
        function bounds() { return {low: axis.min, high: axis.max}; }
        function curve() {
            const values = ChartOracle.points(object("chart.series.calc")).map(point => point.y).filter(Number.isFinite);
            verify(values.length > 0, "The range gate observes a nonempty actual calculated curve");
            return {low: Math.min(...values), high: Math.max(...values)};
        }
        function same(actual, expected) { return Math.abs(actual.low - expected.low) < 1e-7 && Math.abs(actual.high - expected.high) < 1e-7; }
        function edit(value) {
            field.forceActiveFocus();
            verify(SettingsProof.type(field, String(value)), "The production field receives an actual typed scale value");
            verify(SettingsProof.key(field, Qt.Key_Return), "Return commits the actual typed parameter value");
            app.contentItem.forceActiveFocus();
            verify(Math.abs(field.item.value - value) < Math.max(1e-8, Math.abs(value) * 1e-12), "The actual field commits the independently requested scale");
            settled();
        }
        function fitMatchesReset(expected) {
            const points = SettingsProof.points(object("chart.measured")).map(point => point.y).filter(Number.isFinite);
            const calculated = curve();
            verify(points.length > 0, "The refit reference contains the actual measured pattern as well as the calculation");
            verify(expected.low <= Math.min(...points, calculated.low) && expected.high >= Math.max(...points, calculated.high), "The committed range contains both measured and calculated curves");
            const reset = object("chart.toolbar.reset");
            mouseClick(reset, reset.width / 2, reset.height / 2);
            settled();
            tryVerify(() => same(bounds(), expected), 2000, "The range fitted on commit matches the existing user's fit-to-data zoom reset");
        }
        function open(path) {
            if (field) field.destroy();
            field = null;
            const location = SettingsProof.copyProject(Probe.repoUrl(path));
            verify(Session.openProject(location), "The range gate opens a private saved diffraction project");
            if (!app) app = appFactory.createObject(null);
            verify(app !== null, "The range gate uses the actual application and its shared Pattern chart");
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "Parameter input reaches the active actual window");
            Ui.click(test, Probe, app, "appBar.tab.analysis");
            Ui.click(test, Probe, app, "mainArea.analysis.tab.fitting");
            Ui.click(test, Probe, app, "sideBar.tab.basic");
            chart = Render.descendants(Ui.page(app)).find(item => item.objectName === "chart" && item.visible && item.shown && item.experiment === Session.project.currentExperiment);
            verify(chart !== undefined, "The actual selected dataset owns the shown Pattern chart");
            axis = object("chart.axis.y");
            verify(maximumChanges.valid && minimumChanges.valid, "Range commit counts observe actual Qt axis endpoint signals");
            settled();
            const parameter = Session.project.currentExperiment.scale;
            verify(parameter !== null && parameter.value > 0, "The saved project supplies a real positive editable scale parameter");
            field = fieldFactory.createObject(app.contentItem, {item: parameter});
            verify(field !== null && field.enabled, "A production typed field is bound to the saved experiment's scale");
            return parameter;
        }
        function sliderFor(parameter) {
            const group = Render.descendants(Ui.page(app)).find(item => item.objectName === "group.parameters" && item.visible);
            verify(group !== undefined, "The actual Analysis sidebar exposes its production parameter group");
            const table = findChild(group, "parameters.list");
            verify(table !== null, "The production parameter group owns its actual parameter table");
            table.sourceModel.variability = ParameterFilterModel.All;
            group.selected = parameter;
            tryVerify(() => group.selected === parameter && group.selectedRow >= 0, 2000, "The actual slider selects the real scale parameter in the displayed table");
            const slider = findChild(group, "parameters.slider");
            verify(slider !== null && slider.enabled, "The production scale slider is enabled for real pointer input");
            Ui.scrollIntoView(slider);
            verify(waitForPolish(app), "The actual scale slider reaches its viewport before dragging");
            verify(Ui.clickPoint(slider) !== null, "The actual scale slider has an exposed pointer target");
            return slider;
        }
        function sliderX(slider, fraction) {
            const handle = slider.handle ? slider.handle.width : 0;
            return Math.round(slider.leftPadding + handle / 2 + fraction * (slider.availableWidth - handle));
        }
        function test_drag_holds_and_commits_refit() {
            Preferences.resetToDefaults();
            const parameter = open("docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project");
            const original = parameter.value, initial = bounds();
            edit(original * 1000);
            verify(curve().high > initial.high, "The independently excessive scale makes the calculated curve far higher than the initial data range");
            const slider = sliderFor(parameter), y = slider.height / 2;
            settled();
            tryVerify(() => bounds().high >= curve().high, 2000, "The high-scale fitted range settles before the actual drag starts");
            const high = bounds();
            mousePress(slider, sliderX(slider, slider.visualPosition), y);
            pressedSlider = slider;
            verify(slider.pressed, "The actual scale slider stays pressed throughout the holding checks");
            compare(Session.project.adjusting, true, "The real pressed slider marks the actual project as adjusting");
            mouseMove(slider, sliderX(slider, 0.25), y);
            settled();
            verify(curve().high < high.high && curve().low >= high.low, "Dragging the excessive scale down keeps the actual curve inside the existing range");
            verify(same(bounds(), high), "While the slider is pressed an interior curve keeps both y-axis endpoints unchanged; actual=" + JSON.stringify(bounds()) + "; held=" + JSON.stringify(high) + "; adjusting=" + Session.project.adjusting + "; pressed=" + slider.pressed);
            mouseMove(slider, sliderX(slider, 0.95), y);
            settled();
            const widened = bounds(), outside = curve();
            verify(outside.high > high.high && widened.high >= outside.high, "A curve leaving the held upper boundary widens the range to contain it");
            verify(widened.low <= high.low, "Widening the upper boundary does not shrink the opposite edge");
            const lowerX = sliderX(slider, 0.05);
            mouseMove(slider, lowerX, y);
            settled();
            verify(curve().high < outside.high, "The real pressed slider reduces the excessive calculated peak before release");
            verify(same(bounds(), widened), "The reduced curve keeps the enlarged range while the slider is still pressed");
            maximumChanges.clear(); minimumChanges.clear();
            mouseRelease(slider, lowerX, y);
            pressedSlider = null;
            tryCompare(slider, "pressed", false, 1000, "The actual pointer release ends the scale adjustment");
            settled();
            tryVerify(() => bounds().high < widened.high && bounds().high - bounds().low < widened.high - widened.low, 2000, "Releasing a dragged-down excessive scale shrinks the range to fit the current data");
            compare(maximumChanges.count, 1, "Slider release changes the fitted upper endpoint once");
            verify(minimumChanges.count <= 1, "Slider release fits the lower endpoint at most once");
            fitMatchesReset(bounds());
            maximumChanges.clear(); minimumChanges.clear();
            edit(original);
            tryVerify(() => same(bounds(), initial), 2000, "A typed value refits immediately and can shrink back to the original measured/calculated range");
            verify(maximumChanges.count <= 1 && minimumChanges.count <= 1, "A typed commit fits each endpoint at most once");
            fitMatchesReset(bounds());
            maximumChanges.clear(); minimumChanges.clear();
            parameter.value = original * 500;
            settled();
            verify(bounds().high > initial.high && bounds().high < high.high, "A discrete parameter step refits directly instead of retaining an earlier enlarged range");
            verify(maximumChanges.count <= 1 && minimumChanges.count <= 1, "A discrete parameter step fits each endpoint at most once");
            fitMatchesReset(bounds());
            const bankScale = open("docs/user/cli/pd-neut-tof_ncaf-wish-2bank_start-3/project");
            edit(bankScale.value * 1000);
            const beforeDataset = bounds();
            Session.project.currentExperimentIndex = 1;
            settled();
            verify(bounds().high - bounds().low < beforeDataset.high - beforeDataset.low, "Selecting another dataset recomputes its range instead of inheriting the previous expanded bounds");
            const replacement = Session.project.currentExperiment.scale;
            field.destroy();
            field = fieldFactory.createObject(app.contentItem, {item: replacement});
            edit(replacement.value * 1000);
            const beforeModel = bounds();
            open("docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project");
            verify(bounds().high - bounds().low < beforeModel.high - beforeModel.low, "Opening another model recomputes its range instead of retaining the previous model's expanded bounds");
            fitMatchesReset(bounds());
        }
    }
}
