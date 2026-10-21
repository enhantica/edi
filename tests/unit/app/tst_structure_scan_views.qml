// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Globals as Globals
import "RenderedTable.js" as Render

Item {
    id: surface

    height: 1000
    width: 1400

    Component {
        id: pageFactory

        AnalysisPage {
        }
    }
    Component {
        id: emptyChartFactory

        PatternChart {
            settingsPage: "analysis"
        }
    }
    TestCase {
        property var page

        function cleanup() {
            if (page) {
                const toggle = structureToggle(page);
                if (toggle && toggle.visible && toggle.checked)
                    mouseClick(toggle, toggle.width / 2, toggle.height / 2);
                page.destroy();
            }
            page = null;
            Session.closeProject();
        }
        function freshToolbarState() {
            const label = JSON.stringify("Show each structure's curve");
            return SettingsProof.restart('import QtQuick; import QtQuick.Window; import edi.app; QtObject {' + ' property Window sourceWindow: Window { width: 1400; height: 1000; visible: true;' + ' AnalysisPage { id: analysis; anchors.fill: parent; current: true }' + ' Component.onCompleted: Session.openExample("pd-neut-tof_ferrite-austenite-beer_joint"); }' + ' property bool acceptanceReady: Session.project !== null && !Session.project.calculating;' + ' property var savedCurveToggle: {' + ' const walk = item => { let all = [item]; for (const child of item.children || []) all = all.concat(walk(child)); return all; };' + ' const found = walk(analysis).filter(item => item.toolTip === ' + label + ' && typeof item.checked === "boolean" && item.visible);' + ' return {count: found.length, checked: found.length === 1 ? found[0].checked : null}; } }');
        }
        function openAnalysis() {
            verify(Session.openExample("pd-neut-tof_ferrite-austenite-beer_joint"), "The Analysis actor uses the two-structure BEER project");
            tryCompare(Session.project, "calculating", false, 10000, "The real two-structure calculation completes");
            compare(Session.project.structures.count, 2, "The BEER vehicle retains both independently named structures");
            page = pageFactory.createObject(surface, {
                width: surface.width,
                height: surface.height,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The actual Analysis page lays out its chart and controls");
        }
        function settingsText() {
            const url = String(Globals.Vars.settingsFile);
            return SettingsProof.text(url.slice(0, url.lastIndexOf("/") + 1), SettingsProof.fileName(Globals.Vars.settingsFile));
        }
        function structureToggle(root) {
            return Render.descendants(root).find(item => item.toolTip === "Show each structure's curve" && typeof item.checked === "boolean");
        }
        function test_fresh_engine_observer_loads_the_actual_calculated_page() {
            const ordinary = SettingsProof.restart('import QtQuick; QtObject { property bool marker: true }');
            compare(ordinary.marker, true, "The ordinary settings snapshot remains usable without a page readiness property");
            const actual = freshToolbarState();
            verify(!actual.error && actual.acceptanceReady, "The fresh-engine observer waits for the actual BEER calculation before reading controls: " + actual.error);
            verify(actual.savedCurveToggle.count === 0 || actual.savedCurveToggle.count === 1, "The observer reaches a real calculated toolbar, whether the new button is still missing or implemented");
        }
        function test_scan_tabs() {
            openAnalysis();
            const tabs = Render.texts(page).filter(item => /stack|map/i.test(item.text));
            verify(tabs.some(item => /stack/i.test(item.text)) && tabs.some(item => /map/i.test(item.text)), "Analysis offers both stacked patterns and the 2D intensity map beside its existing views");
        }
        function test_structure_toolbar_toggle_and_saved_state(data) {
            const empty = createTemporaryObject(emptyChartFactory, surface, {
                width: surface.width,
                height: surface.height
            });
            verify(empty !== null, "The default visibility check instantiates a real empty pattern chart");
            const emptyToggle = structureToggle(empty);
            verify(!emptyToggle || !emptyToggle.visible, "The structure-curve toggle stays hidden without a calculated pattern");
            empty.destroy();
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
            compare(toggle.checked, false, "Each structure's curve is off by default in a fresh app settings store");
            compare(visibleFills().length, 0, "Structure fills are absent while their toolbar toggle is off");
            const modified = Session.project.modified;
            const before = settingsText();
            mouseClick(toggle, toggle.width / 2, toggle.height / 2);
            tryCompare(toggle, "checked", true, 1000, "Real pointer input enables each structure's curve");
            verify(waitForRendering(page), "The enabled structure curves complete a rendered frame");
            tryVerify(() => visibleFills().length === Session.project.structures.count, 2000, "The chart draws one visible area series for each structure");
            let background = null;
            for (const item of Render.descendants(page))
                if (item.seriesList !== undefined)
                    for (const series of item.seriesList)
                        if (series.objectName === "chart.series.bkg")
                            background = series;
            verify(background !== null && background.count > 0, "The fill baseline is the chart's actual nonempty background curve");
            for (const fill of visibleFills()) {
                verify(fill.lowerSeries !== null && fill.upperSeries !== null, "Every unstacked structure fill retains its own curve over a background baseline");
                compare(fill.lowerSeries.count, background.count, "Each structure fill spans the same grid as the background");
                for (let index = 0; index < background.count; ++index) {
                    const actual = fill.lowerSeries.at(index);
                    const expected = background.at(index);
                    verify(actual.x === expected.x && actual.y === expected.y, "Every structure fill starts at the background rather than stacking on another structure");
                }
                verify(fill.color.a > 0 && fill.color.a * fill.opacity < 1 && fill.borderColor.a > fill.color.a && fill.borderWidth > 0, "Each structure has a soft fill and a visible outline");
            }
            tryVerify(() => settingsText() !== before, 2000, "Turning the toolbar toggle on writes the actual app settings file");
            compare(Session.project.modified, modified, "Showing structure curves is an app setting and does not modify the project");
            const savedOn = settingsText();
            if (!data.enabled) {
                mouseClick(toggle, toggle.width / 2, toggle.height / 2);
                tryCompare(toggle, "checked", false, 1000, "Real pointer input hides each structure's curve again");
                tryVerify(() => visibleFills().length === 0, 2000, "Turning the toggle off removes every visible structure fill");
                tryVerify(() => settingsText() !== savedOn, 2000, "Turning the toolbar toggle off also writes the actual app settings file");
            }
            compare(Session.project.modified, modified, "Hiding structure curves also leaves the scientific project unchanged");
            const restored = freshToolbarState();
            verify(!restored.error, "A fresh production chart and Preferences engine reload the actual app store");
            compare(restored.savedCurveToggle.count, 1, "The reloaded calculated chart contains its one structure-curve control");
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

        name: "StructureScanViews"
        when: windowShown
    }
}
