// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Globals as Globals
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui

Item {
    id: surface

    height: 1000
    width: 1400

    Component {
        id: appFactory
        Main {
            width: 1400
            height: 1000
            visible: true
        }
    }
    TestCase {
        id: test
        property var appWindow
        property var page

        function cleanup() {
            Session.closeProject();
            if (appWindow) {
                appWindow.close();
                appWindow.destroy();
            }
            appWindow = null;
            page = null;
        }
        function openWindow() {
            AppState.reset();
            appWindow = appFactory.createObject(null);
            verify(appWindow !== null && appWindow.visible, "The toolbar gate opens the actual application window");
            appWindow.requestActivate();
            tryCompare(appWindow, "active", true, 2000, "Actual toolbar input reaches the active application window");
        }
        function showPage(name) {
            Ui.click(test, Probe, appWindow, "appBar.tab." + name);
            page = Render.descendants(appWindow.contentItem).find(item => item.pageName === name && item.current);
            verify(page !== undefined && page.Window.window === appWindow, "The actual current page belongs to the application window");
            const charts = Render.descendants(page).filter(item => item.objectName === "chart" && item.report === null && item.visible && item.shown);
            compare(charts.length, 1, "The current page holds its one app-owned pattern chart");
            verify(charts[0].Window.window === appWindow, "The reparented chart has the actual application window before input");
        }
        function clickToggle(toggle) {
            tryVerify(() => !Ui.moving(appWindow.contentItem), 2000, "The chart finishes moving before its toolbar receives input");
            verify(waitForPolish(appWindow), "The actual application completes toolbar layout");
            appWindow.update();
            verify(waitForRendering(appWindow.contentItem), "The actual chart toolbar renders before input");
            const point = Ui.clickPoint(toggle);
            verify(toggle.enabled && point !== null, "The real pointer targets the exposed portion of the app-owned chart toggle");
            mouseClick(toggle, point.x, point.y);
            appWindow.update();
            verify(waitForRendering(appWindow.contentItem), "The app-owned chart completes a frame after actual pointer input");
        }
        function freshToolbarState(requireControl) {
            const label = JSON.stringify("Show each structure's curve");
            return SettingsProof.restart('import QtQuick; import edi.app; QtObject {' + ' property Item toolbar: ChartToolbar {}' + ' property bool acceptanceReady: ' + (requireControl ? 'savedCurveToggle.count === 1' : 'true') + ';' + ' property var savedCurveToggle: {' + ' const walk = item => { let all = [item]; for (const child of item.children || []) all = all.concat(walk(child)); return all; };' + ' const found = walk(toolbar).filter(item => item.toolTip === ' + label + ' && typeof item.checked === "boolean");' + ' return {count: found.length, checked: found.length === 1 ? found[0].checked : null}; } }');
        }
        function hasClearOutline(fill) {
            const sameHue = colour => colour.r === fill.color.r && colour.g === fill.color.g && colour.b === fill.color.b;
            if (fill.borderWidth > 0 && fill.borderColor.a > fill.color.a && sameHue(fill.borderColor))
                return true;
            const chart = Render.descendants(page).find(item => item.objectName === "chart" && item.report === null);
            const rows = Probe.rows(Session.project.currentExperiment.pattern);
            const expected = new Map(rows.map(row => [chart.xAxis === "dSpacing" ? row.dSpacing : row.x, row.componentIntensities.map(net => row.intensityBkg + net)]));
            for (const item of Render.descendants(page)) {
                if (!item.visible || item.seriesList === undefined)
                    continue;
                for (const series of item.seriesList) {
                    if (series.upperSeries !== undefined || !series.visible || !(series.width > 0) || !(series.opacity > 0) || !sameHue(series.color) || series.color.a * series.opacity <= fill.color.a * fill.opacity)
                        continue;
                    // Area polygons may add gap-closing vertices and a subpixel
                    // separation at the baseline. The outline represents the
                    // physical curve, not the area's triangulation vertices.
                    for (let column = 0; column < Session.project.structures.count; ++column) {
                        let finite = 0, matches = true;
                        for (let index = 0; index < series.count; ++index) {
                            const point = series.at(index);
                            if (!Number.isFinite(point.x) || !Number.isFinite(point.y))
                                continue;
                            ++finite;
                            if (!expected.has(point.x) || point.y !== expected.get(point.x)[column]) {
                                matches = false;
                                break;
                            }
                        }
                        if (matches && finite >= 2)
                            return true;
                    }
                }
            }
            return false;
        }
        function openAnalysis() {
            if (!appWindow)
                openWindow();
            verify(Session.openExample("pd-neut-tof_ferrite-austenite-beer_joint"), "The Analysis actor uses the two-structure BEER project");
            tryCompare(Session.project, "calculating", false, 10000, "The real two-structure calculation completes");
            compare(Session.project.structures.count, 2, "The BEER vehicle retains both independently named structures");
            showPage("analysis");
        }
        function settingsText() {
            const url = String(Globals.Vars.settingsFile);
            return SettingsProof.text(url.slice(0, url.lastIndexOf("/") + 1), SettingsProof.fileName(Globals.Vars.settingsFile));
        }
        function structureToggle(root) {
            return Render.descendants(root).find(item => item.toolTip === "Show each structure's curve" && typeof item.checked === "boolean");
        }
        function test_fresh_toolbar_observer_loads_actual_control() {
            const ordinary = SettingsProof.restart('import QtQuick; QtObject { property bool marker: true }');
            compare(ordinary.marker, true, "The ordinary settings snapshot remains usable without a page readiness property");
            const actual = freshToolbarState();
            verify(!actual.error && actual.acceptanceReady, "The fresh-engine observer creates the actual production toolbar before reading its saved control: " + actual.error);
            verify(actual.savedCurveToggle.count === 0 || actual.savedCurveToggle.count === 1, "The observer reaches the real toolbar component, whether its curve button is still missing or implemented");
        }
        function test_scan_tabs() {
            openAnalysis();
            const tabs = Render.texts(page).filter(item => /stack|map/i.test(item.text));
            verify(tabs.some(item => /stack/i.test(item.text)) && tabs.some(item => /map/i.test(item.text)), "Analysis offers both stacked patterns and the 2D intensity map beside its existing views");
        }
        function test_structure_toolbar_toggle_and_saved_state(data) {
            // Data rows share the process's test-owned store and Preferences singleton.
            // Remove only the saved choice, then ask a fresh production engine for
            // its default before normalising the old engine for the pointer exercise.
            SettingsProof.erase(Globals.Vars.settingsFile, "PatternChart", "structureCurves");
            compare(SettingsProof.value(Globals.Vars.settingsFile, "PatternChart", "structureCurves"), undefined, "The fresh-default witness has no saved structure-curve choice");
            const fresh = freshToolbarState(true);
            verify(!fresh.error && fresh.savedCurveToggle.count === 1, "The default witness loads the actual production toolbar in a fresh engine");
            compare(fresh.savedCurveToggle.checked, true, "The actual toolbar defaults to showing each structure when no choice is saved");
            Preferences.structureCurves = fresh.savedCurveToggle.checked;
            openWindow();
            verify(Session.createProject("Empty pattern", "Toolbar visibility witness"), "The empty-chart witness creates a real unsaved project");
            verify(Session.project.createStructure(), "The real Experiment page is available before any experiment is created");
            compare(Session.project.experiments.count, 0, "The no-calculated-pattern witness has no experiment");
            showPage("experiment");
            const emptyToggle = structureToggle(page);
            verify(emptyToggle !== undefined && !emptyToggle.visible, "The app-owned structure-curve toggle stays hidden without a calculated pattern");
            openAnalysis();
            let toggle;
            tryVerify(() => {
                toggle = structureToggle(page);
                return toggle !== undefined && toggle.visible && toggle.enabled;
            }, 2000, "A calculated Analysis pattern exposes the structure-curve toggle in its toolbar");
            compare(toggle.fontIcon, "layer-group", "The curve toggle uses the existing structure icon");
            const legend = findChild(page, "chart.toolbar.legend");
            const hover = findChild(page, "chart.toolbar.hover");
            verify(legend && hover && toggle.parent === legend.parent && toggle.parent === hover.parent, "The structure toggle shares the legend and coordinates-tooltip toolbar group");
            const siblings = Array.from(toggle.parent.children);
            const members = [legend, hover, toggle];
            const positions = members.map(item => siblings.indexOf(item));
            verify(siblings.slice(Math.min(...positions), Math.max(...positions) + 1).every(item => members.includes(item)), "No spacer separates the structure toggle from its legend and tooltip group");
            compare(toggle.checked, true, "Each structure's curve is on by default when the fresh app store has no saved choice");
            tryVerify(() => visibleFills().length === Session.project.structures.count, 2000, "The fresh default draws every structure before a choice is saved");
            const defaultSettings = settingsText();
            clickToggle(toggle);
            tryCompare(toggle, "checked", false, 1000, "Real pointer input can turn the default structure fills off");
            tryVerify(() => visibleFills().length === 0, 2000, "No finite painted structure area remains while the toolbar toggle is off");
            tryVerify(() => settingsText() !== defaultSettings, 2000, "Turning the fresh default off must persist the actual user override before another choice is tested");
            const modified = Session.project.modified;
            const before = settingsText();
            clickToggle(toggle);
            tryCompare(toggle, "checked", true, 1000, "Real pointer input enables each structure's curve");
            verify(waitForPolish(appWindow), "The enabled app-owned structure curves complete layout after their rendered frame");
            tryVerify(() => visibleFills().length === Session.project.structures.count, 2000, "The chart draws one visible area series for each structure");
            let background = null;
            for (const item of Render.descendants(page))
                if (item.visible && item.seriesList !== undefined)
                    for (const series of item.seriesList)
                        if (series.objectName === "chart.series.bkg")
                            background = series;
            verify(background !== null && background.count > 0, "The fill baseline is the chart's actual nonempty background curve");
            tryVerify(() => visibleFills().length === 2 && visibleFills().every(fill => fill.lowerSeries && fill.upperSeries && fill.lowerSeries.count > 0 && fill.upperSeries.count === fill.lowerSeries.count), 2000, "Every visible structure's real data finishes loading before its baseline is compared");
            // Each plotted line is decimated separately. The exact full background is the engine's
            // calculated pattern data, not another independently sampled presentation's array index.
            const chart = Render.descendants(page).find(item => item.objectName === "chart" && item.report === null);
            const rows = Probe.rows(Session.project.currentExperiment.pattern);
            const backgroundByX = new Map(rows.map(row => [chart.xAxis === "dSpacing" ? row.dSpacing : row.x, row.intensityBkg]));
            verify(rows.length > 0 && backgroundByX.size === rows.length, "The exact calculated background has a nonempty unique x grid");
            for (let index = 0; index < background.count; ++index) {
                const point = background.at(index);
                verify(backgroundByX.has(point.x) && point.y === backgroundByX.get(point.x), "The chart's sampled background retains the exact full calculated background values");
            }
            for (const fill of visibleFills()) {
                verify(fill.lowerSeries !== null && fill.upperSeries !== null, "Every unstacked structure fill retains its own curve over a background baseline");
                compare(fill.lowerSeries.count, fill.upperSeries.count, "Each structure's upper and lower curves share their own nonempty sample grid");
                compare(fill.lowerSeries.at(0).x, background.at(0).x, "Every structure fill starts at the full background domain boundary");
                compare(fill.lowerSeries.at(fill.lowerSeries.count - 1).x, background.at(background.count - 1).x, "Every structure fill ends at the full background domain boundary");
                for (let index = 0; index < fill.lowerSeries.count; ++index) {
                    const actual = fill.lowerSeries.at(index);
                    verify(backgroundByX.has(actual.x) && actual.y === backgroundByX.get(actual.x), "Every structure fill starts at the background rather than stacking on another structure");
                    compare(fill.upperSeries.at(index).x, actual.x, "A structure's upper and lower curves use the same physical x coordinate");
                }
                verify(fill.color.a > 0 && fill.color.a * fill.opacity < 1 && hasClearOutline(fill), "Each structure has a soft fill and a visible outline");
            }
            tryVerify(() => settingsText() !== before, 2000, "Turning the toolbar toggle on writes the actual app settings file");
            compare(Session.project.modified, modified, "Showing structure curves is an app setting and does not modify the project");
            const savedOn = settingsText();
            if (!data.enabled) {
                clickToggle(toggle);
                tryCompare(toggle, "checked", false, 1000, "Real pointer input hides each structure's curve again");
                tryVerify(() => visibleFills().length === 0, 2000, "Turning the toggle off leaves no finite painted structure area");
                tryVerify(() => settingsText() !== savedOn, 2000, "Turning the toolbar toggle off also writes the actual app settings file");
            }
            compare(Session.project.modified, modified, "Hiding structure curves also leaves the scientific project unchanged");
            // Restart after the original app window closes, rather than overlapping two full sessions.
            Session.closeProject();
            appWindow.close();
            appWindow.destroy();
            appWindow = null;
            page = null;
            wait(0);
            console.info("Toolbar gate reached the fresh production toolbar after exact fill and settings checks");
            const restored = freshToolbarState(true);
            console.info("Toolbar gate completed the fresh production toolbar snapshot");
            verify(!restored.error, "A fresh production toolbar and Preferences engine reload the actual app store");
            compare(restored.savedCurveToggle.count, 1, "The actual reloaded toolbar contains its one structure-curve control");
            compare(restored.savedCurveToggle.checked, data.enabled, "A fresh engine restores the selected on or off curve setting from disk");
        }
        function test_structure_toolbar_toggle_and_saved_state_data() {
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
        function drawableArea(series) {
            if (!series || !series.visible || series.opacity <= 0 || !series.color || series.color.a <= 0 || !series.upperSeries || !series.lowerSeries)
                return false;
            const upper = series.upperSeries, lower = series.lowerSeries;
            for (let i = 1; i < Math.min(upper.count, lower.count); ++i) {
                const a = upper.at(i - 1), b = upper.at(i), c = lower.at(i - 1), d = lower.at(i);
                if ([a.x, a.y, b.x, b.y, c.x, c.y, d.x, d.y].every(Number.isFinite) && a.x === c.x && b.x === d.x && a.x !== b.x && (a.y !== c.y || b.y !== d.y))
                    return true;
            }
            return false;
        }
        function test_drawable_area_observer() {
            const line = points => ({
                        count: points.length,
                        at: i => points[i]
                    });
            const area = (upper, lower, alpha) => ({
                        visible: true,
                        opacity: 1,
                        color: {
                            a: alpha
                        },
                        upperSeries: line(upper),
                        lowerSeries: line(lower)
                    });
            const upper = [
                {
                    x: 0,
                    y: 1
                },
                {
                    x: 1,
                    y: 2
                }
            ], lower = [
                {
                    x: 0,
                    y: 0
                },
                {
                    x: 1,
                    y: 0
                }
            ];
            verify(drawableArea(area(upper, lower, 0.2)), "The area observer accepts finite painted geometry");
            verify(!drawableArea(area([
                {
                    x: NaN,
                    y: NaN
                }
            ], [
                {
                    x: NaN,
                    y: NaN
                }
            ], 0.2)), "Retained one-point NaN placeholders cannot draw an area");
            verify(!drawableArea(area(upper, lower, 0)), "Transparent retained geometry cannot draw a fill");
            verify(!drawableArea(area(upper, upper, 0.2)), "A zero-height outline cannot count as a painted interior");
            verify(!drawableArea(area([], [], 0.2)), "Empty series cannot count as drawn fills");
            verify(!drawableArea(area([upper[0]], [lower[0]], 0.2)), "A single finite point cannot enclose a painted area");
            const hidden = area(upper, lower, 0.2);
            hidden.visible = false;
            verify(!drawableArea(hidden), "A hidden retained series cannot count as a drawn fill");
            hidden.visible = true;
            hidden.opacity = 0;
            verify(!drawableArea(hidden), "Zero effective opacity cannot count as a drawn fill");
        }
        function visibleFills() {
            const fills = [];
            for (const item of Render.descendants(page)) {
                if (!item.visible || item.seriesList === undefined)
                    continue;
                for (const series of item.seriesList)
                    if (drawableArea(series))
                        fills.push(series);
            }
            return fills;
        }

        name: "StructureScanViews"
        when: windowShown
    }
}
