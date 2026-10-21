// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtTest
import edi.app
import EdiAcceptance 1.0
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui
import ReportAcceptance 1.0

Item {
    id: surface
    width: 1500
    height: 1000
    Component {
        id: appFactory
        Main {
            width: 1500
            height: 1000
            visible: true
        }
    }
    Component {
        id: spyFactory
        SignalSpy {
            signalName: "pointsReplaced"
        }
    }
    TestCase {
        id: test
        name: "SharedPatternChart"
        when: windowShown
        property var app
        function init() {
            AppState.reset();
            app = appFactory.createObject(null);
            verify(app !== null && app.visible, "The chart gate opens the actual application window");
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "Actual input reaches the active application window");
        }
        function cleanup() {
            if (app) {
                app.close();
                app.destroy();
            }
            app = null;
            Session.closeProject();
        }
        function openExample() {
            verify(Session.openExample("pd-neut-tof_ferrite-austenite-beer_joint"), "The shared-view vehicle is the committed two-experiment BEER project");
            tryCompare(Session.project, "calculating", false, 10000, "The actual project calculation completes before chart interaction");
            compare(Session.project.experiments.count, 2, "The selector witness has two distinct experiments");
        }
        function page(name) {
            return Render.descendants(app.contentItem).find(item => item.pageName === name);
        }
        function showPage(name, pattern = true) {
            Ui.click(test, Probe, app, "appBar.tab." + name);
            tryVerify(() => page(name) && page(name).current, 2000, "Navigation reaches the actual " + name + " page");
            const current = page(name);
            tryVerify(() => !Ui.moving(app.contentItem), 2000, "Page navigation finishes moving before chart input");
            verify(waitForPolish(app), "The application completes layout before observing its chart");
            if (pattern) {
                const tab = Array.from(current.mainTabs).find(item => item.text === "Pattern");
                verify(tab !== undefined && tab.enabled, "Each page offers an enabled Pattern tab while an experiment exists");
                if (!tab.checked)
                    click(tab);
                tryCompare(tab, "checked", true, 1000, "Real input selects the Pattern main-area tab");
                tryVerify(() => !Ui.moving(app.contentItem), 2000, "The Pattern pane finishes moving before chart input");
                app.update();
                verify(waitForRendering(app.contentItem), "The selected Pattern tab completes an explicitly requested application frame");
            }
            return current;
        }
        function charts(root) {
            return Render.descendants(root).filter(item => item.objectName === "chart" && item.report === null && item.experiment !== undefined);
        }
        function shownChart(name) {
            const current = showPage(name);
            let found;
            tryVerify(() => {
                found = charts(current).filter(item => item.visible && item.shown);
                return found.length === 1;
            }, 2000, "The shown page holds exactly one visible live pattern chart");
            return found[0];
        }
        function named(root, name) {
            const found = findChild(root, name);
            verify(found !== null, "The actual chart retains its observable " + name + " control or series");
            return found;
        }
        function click(item) {
            tryVerify(() => !Ui.moving(app.contentItem), 2000, "Viewports finish moving before the next real input");
            verify(waitForPolish(app), "Real input follows completed application layout");
            app.update();
            verify(waitForRendering(app.contentItem), "The settled input target has a rendered frame");
            const point = Ui.clickPoint(item);
            verify(item.enabled && point !== null, "Real input targets the exposed portion of an enabled control: " + item.objectName);
            mouseClick(item, point.x, point.y);
            app.update();
            verify(waitForRendering(app.contentItem), "Real pointer input is followed by a rendered frame");
        }
        function select(combo, index) {
            verify(combo.count > index, "The actual selector contains the non-default witness option");
            combo.forceActiveFocus();
            click(combo);
            verify(SettingsProof.key(combo, Qt.Key_Home), "Home reaches the real selector window");
            for (let row = 0; row < index; ++row)
                verify(SettingsProof.key(combo, Qt.Key_Down), "Down reaches the real selector window");
            verify(SettingsProof.key(combo, Qt.Key_Return), "Return reaches the real selector window");
            tryCompare(combo, "currentIndex", index, 1000, "Keyboard input changes the real selector");
        }
        function viewState(chart) {
            const x = named(chart, "chart.axis.x");
            const y = named(chart, "chart.axis.y");
            const toggles = Render.descendants(chart).filter(item => String(item.objectName).startsWith("chart.toolbar.") && typeof item.checked === "boolean" && item.visible).map(item => [item.objectName, item.checked]);
            toggles.sort((left, right) => left[0].localeCompare(right[0]));
            return {
                experiment: chart.experiment,
                xAxis: named(chart, "chart.toolbar.xaxis").currentIndex,
                yScale: named(chart, "chart.toolbar.yscale").currentIndex,
                xMin: x.min,
                xMax: x.max,
                yMin: y.min,
                yMax: y.max,
                toggles: JSON.stringify(toggles)
            };
        }
        function sameState(chart, expected) {
            const actual = viewState(chart);
            verify(actual.experiment === expected.experiment, "The chart retains the selected experiment across pages");
            compare(actual.xAxis, expected.xAxis, "The x-axis choice is shared by every page");
            compare(actual.yScale, expected.yScale, "The y-scale choice is shared by every page");
            compare(actual.toggles, expected.toggles, "Every visible toolbar toggle retains its state across pages");
            for (const key of ["xMin", "xMax", "yMin", "yMax"])
                verify(Math.abs(actual[key] - expected[key]) <= Math.max(1, Math.abs(expected[key])) * 1e-9, "The zoomed and panned " + key + " stays unchanged after navigation");
        }
        function test_actual_chart_observers_and_input() {
            openExample();
            const chart = shownChart("experiment");
            const legend = named(chart, "chart.toolbar.legend");
            const original = legend.checked;
            click(legend);
            tryCompare(legend, "checked", !original, 1000, "The real-window input control changes the actual legend toggle");
            click(legend);
            tryCompare(legend, "checked", original, 1000, "The real-window input control restores the actual legend toggle");
            const scale = named(chart, "chart.toolbar.yscale");
            const next = (scale.currentIndex + 1) % scale.count;
            const measured = named(chart, "chart.measured");
            const line = named(chart, "chart.series.calc");
            verify(measured.count > 0 && line.count > 0, "The drawing observer control sees real measured and calculated data");
            const spy = spyFactory.createObject(surface, {
                target: line
            });
            verify(spy.valid, "The observer control connects to the actual Qt-series replacement signal");
            const revision = measured.revision;
            select(scale, next);
            tryVerify(() => measured.revision > revision && spy.count > 0, 1500, "Visible actual input reaches both measured and Qt-series drawing observers");
            verify(charts(app.contentItem).includes(chart), "The whole-window census includes its actual visible chart");
            spy.destroy();
        }
        function test_structure_pattern_requires_experiment() {
            openExample();
            while (Session.project.experiments.count)
                Session.project.removeExperiment(0);
            compare(Session.project.experiments.count, 0, "The disabled-tab witness really has no experiment");
            const current = showPage("structure", false);
            const tabs = Array.from(current.mainTabs);
            compare(tabs.length, 2, "Structure and Pattern are the Structure page's two main-area tabs");
            compare(tabs[0].text, "Structure", "The existing Structure view remains the first tab");
            compare(tabs[1].text, "Pattern", "Pattern is the second Structure main-area tab");
            compare(tabs[1].enabled, false, "The Pattern tab is disabled without an experiment");
            verify(Session.project.createExperiment(), "Adding a real experiment changes the disabled-tab precondition");
            tryCompare(tabs[1], "enabled", true, 1000, "The same Pattern tab enables when an experiment is created");
            Session.project.removeExperiment(0);
            tryCompare(tabs[1], "enabled", false, 1000, "Removing the last experiment disables Pattern again");
        }
        function test_one_object_survives_page_changes() {
            openExample();
            const original = shownChart("experiment");
            for (const name of ["analysis", "structure", "experiment", "analysis", "structure"]) {
                verify(shownChart(name) === original, "One actual pattern-chart object moves between all three pages");
                compare(charts(app.contentItem).length, 1, "Loaded hidden pages cannot retain duplicate non-report charts");
                for (const hidden of ["structure", "experiment", "analysis"].filter(value => value !== name))
                    compare(charts(page(hidden)).length, 0, "A hidden page owns no pattern chart that can draw");
            }
        }
        function test_view_change_follows_every_page_data() {
            return [
                {
                    tag: "experiment",
                    origin: "experiment"
                },
                {
                    tag: "analysis",
                    origin: "analysis"
                },
                {
                    tag: "structure",
                    origin: "structure"
                }
            ];
        }
        function test_view_change_follows_every_page(data) {
            openExample();
            const chart = shownChart(data.origin);
            const before = viewState(chart);
            click(named(chart, "chart.toolbar.legend"));
            click(named(chart, "chart.toolbar.hover"));
            click(named(chart, "chart.toolbar.pan"));
            select(named(chart, "chart.toolbar.yscale"), 1);
            select(named(chart, "chart.toolbar.xaxis"), 1);
            const actualSelector = Render.descendants(page(data.origin)).find(item => item.model === Session.project.experiments && typeof item.currentIndex === "number" && item.visible);
            verify(actualSelector !== undefined, "Every Pattern page offers a real experiment selector over the current project");
            select(actualSelector, actualSelector.currentIndex === 0 ? 1 : 0);
            tryVerify(() => chart.experiment === Session.project.currentExperiment, 1000, "The chart follows the new experiment selected through its real control");
            const pointer = named(chart, "chart.pointer");
            verify(pointer.width > 100 && pointer.height > 50, "The zoom witness has a real nonempty chart plot");
            click(named(chart, "chart.toolbar.zoom"));
            const wide = viewState(chart);
            mouseDrag(pointer, pointer.width * 0.2, pointer.height * 0.2, pointer.width * 0.5, pointer.height * 0.5);
            wait(350);
            const zoomed = viewState(chart);
            verify(zoomed.xMax - zoomed.xMin < wide.xMax - wide.xMin, "Box input actually narrows the x range before navigation");
            click(named(chart, "chart.toolbar.pan"));
            mouseDrag(pointer, pointer.width * 0.5, pointer.height * 0.5, pointer.width * 0.1, 0);
            wait(350);
            const expected = viewState(chart);
            verify(expected.xMin !== zoomed.xMin, "Pan input actually moves the zoomed range before navigation");
            verify(expected.toggles !== before.toggles && expected.xAxis !== before.xAxis && expected.yScale !== before.yScale && expected.experiment !== before.experiment, "The witness changes real toggles, both axes and the selected experiment instead of comparing defaults");
            for (const destination of ["experiment", "analysis", "structure", data.origin])
                sameState(shownChart(destination), expected);
        }
        function test_toolbar_toggles_follow_every_page_data() {
            return test_view_change_follows_every_page_data();
        }
        function test_toolbar_toggles_follow_every_page(data) {
            openExample();
            const chart = shownChart(data.origin);
            const buttons = Render.descendants(chart).filter(item => String(item.objectName).startsWith("chart.toolbar.") && typeof item.checked === "boolean" && item.visible && item.objectName !== "chart.toolbar.reset");
            verify(buttons.length >= 4, "The toggle witness includes the real legend, tooltip and pointer-mode controls");
            for (const button of buttons) {
                // The exclusive pointer-mode button already selected is not a changed-state witness.
                if (["chart.toolbar.pan", "chart.toolbar.zoom"].includes(button.objectName) && button.checked)
                    continue;
                const old = button.checked;
                click(button);
                tryCompare(button, "checked", !old, 1000, "The actual toolbar toggle changes before its cross-page comparison: " + button.objectName);
                const expected = viewState(chart);
                for (const destination of ["experiment", "analysis", "structure", data.origin])
                    sameState(shownChart(destination), expected);
            }
        }
        function test_hidden_pages_do_no_chart_work() {
            openExample();
            const chart = shownChart("experiment");
            shownChart("analysis");
            showPage("structure", false);
            shownChart("experiment");
            for (const name of ["structure", "analysis"])
                compare(charts(page(name)).length, 0, "Every loaded hidden page is empty of live chart objects");
            const measured = named(chart, "chart.measured");
            const line = named(chart, "chart.series.calc");
            verify(measured.count > 0 && line.count > 0, "The hidden-work witness starts with real measured and calculated drawing data");
            const spy = spyFactory.createObject(surface, {
                target: line
            });
            verify(spy.valid, "The drawing observer is connected to the actual Qt series upload signal");
            const visibleRevision = measured.revision;
            select(named(chart, "chart.toolbar.yscale"), 1);
            tryVerify(() => measured.revision > visibleRevision && spy.count > 0, 1500, "Visible input really causes measured and Qt-series drawing uploads");
            AppState.open(AppState.Page.Project);
            tryVerify(() => !page("experiment").current && !page("analysis").current && !page("structure").current, 1000, "All pattern-chart pages are hidden for the idle-work witness");
            wait(350);
            verify(!chart.visible || chart.Window.window === null, "A chart with no visible Pattern host has no visible scene-graph item in any window");
            spy.clear();
            const hiddenRevision = measured.revision;
            // A different real experiment invalidates the presentation without touching an invisible control.
            Session.project.currentExperimentIndex = Session.project.currentExperimentIndex === 0 ? 1 : 0;
            tryCompare(Session.project, "calculating", false, 10000, "The hidden-page stimulus finishes its real project update");
            app.width += 31;
            wait(350);
            compare(measured.revision, hiddenRevision, "Hidden pattern pages perform no measured drawing uploads after data and geometry change");
            compare(spy.count, 0, "Hidden pattern pages perform no Qt-series drawing uploads after invalidation");
            for (const name of ["structure", "experiment", "analysis"])
                compare(charts(page(name)).length, 0, "No hidden page holds a chart capable of drawing while another page is shown");
            const restored = shownChart("experiment");
            verify(restored === chart, "The paused shared chart survives its hidden interval");
            tryVerify(() => measured.revision > hiddenRevision && spy.count > 0, 1500, "Showing the chart consumes the deferred drawing update rather than losing it");
            verify(restored.experiment === Session.project.currentExperiment, "The shown chart catches up to the newest experiment");
            spy.destroy();
        }
    }
}
