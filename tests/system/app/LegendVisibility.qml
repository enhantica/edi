// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiChartReference 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style
import EasyApplication.Gui.Globals as Globals
import "../../unit/app/RenderedTable.js" as Render
import "../../unit/app/UiInteraction.js" as Ui

Item {
    Component { id: application; Main { visible: true; width: 1500; height: 900 } }
    TestCase {
        id: test
        name: "LegendVisibility"
        when: windowShown
        property var app: null
        property var chart: null
        property var axis: null
        SignalSpy { id: lowChanges; target: test.axis; signalName: "minChanged" }
        SignalSpy { id: highChanges; target: test.axis; signalName: "maxChanged" }
        function cleanup() {
            chart = null;
            axis = null;
            Session.closeProject();
            if (app) { app.close(); app.destroy(); }
            app = null;
            Preferences.resetToDefaults();
        }
        function frame() {
            tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 15000, "The legend witness waits for the real saved project calculation");
            app.update();
            verify(waitForPolish(chart) && waitForRendering(chart), "Legend visibility is observed after the actual chart's rendered frame");
        }
        function bounds() { return [axis.min, axis.max]; }
        function same(a, b) { return Math.abs(a[0] - b[0]) < 1e-7 && Math.abs(a[1] - b[1]) < 1e-7; }
        function select(page, single) {
            Ui.click(test, Probe, app, "appBar.tab." + page);
            const body = Ui.page(app);
            const patternTab = Array.from(body.mainTabs || []).find(item => item.text === "Pattern");
            if (patternTab && !patternTab.checked) Ui.click(test, Probe, app, patternTab.objectName);
            tryVerify(() => {
                chart = Render.descendants(Ui.page(app)).find(item => item.objectName === (single ? "singleCrystal.chart" : "chart") && item.visible && item.shown);
                return chart !== undefined && Math.abs(Ui.page(app).mapToItem(app.contentItem, 0, 0).x) < 1;
            }, 4000, "Legend input reaches the actual selected page and chart");
            frame();
            const graph = single ? ChartOracle.graph(chart) : ChartOracle.object(chart, "chart.view.main");
            axis = graph.axisY;
            verify(axis !== null && axis.max > axis.min, "The legend range contract reads actual Qt Graphs axis endpoints");
        }
        function legend(single) {
            const item = findChild(chart, single ? "singleCrystal.legend" : "chart.legend");
            verify(item !== null && item.visible, "Every requested chart exposes its actual visible legend");
            return item;
        }
        function entries(single) { return Render.descendants(legend(single)).filter(item => item.objectName === "chart.legend.entry"); }
        function entry(single, key) {
            const item = entries(single).find(item => item.key === key);
            verify(item !== undefined, "Every original curve retains an actionable legend entry while hidden");
            return item;
        }
        function click(single, key, symbol) {
            const item = entry(single, key);
            let previous = "", stable = 0;
            tryVerify(() => {
                const point = item.mapToItem(app.contentItem, 0, 0);
                const current = JSON.stringify([point.x, point.y, item.width, item.height].map(value => Math.round(value * 10)));
                stable = current === previous ? stable + 1 : 0;
                previous = current;
                return stable >= 3;
            }, 2500, "Legend input waits for the entry's enabled-or-disabled layout to settle");
            const mark = Render.descendants(item).find(child => typeof child.thickness === "number" && child.visible);
            verify(mark !== undefined, "The legend symbol is actual drawn geometry and accepts the same toggle as its name");
            const texts = Render.texts(item), label = texts[texts.length - 1];
            verify(label !== undefined, "The legend name is actual drawn text before pointer input");
            const at = symbol ? mark.mapToItem(item, mark.width / 2, mark.height / 2) : label.mapToItem(item, label.width / 2, label.height / 2);
            // Separate ordinary clicks; consecutive symbol clicks otherwise become one platform double click.
            console.log("LEGEND_INPUT " + JSON.stringify({key: key, symbol: symbol, hidden: item.hidden, at: [at.x, at.y]}));
            mouseClick(item, at.x, at.y, Qt.LeftButton, Qt.NoModifier, 500);
            frame();
        }
        function tooltip(single, key, hidden) {
            const item = entry(single, key);
            mouseMove(item, item.width - 3, item.height / 2);
            let tip;
            tryVerify(() => {
                tip = Array.from(Probe.objectsWithProperty(item, "backgroundColor")).find(object => object.visible && object.text === (hidden ? "Click to show" : "Click to hide"));
                return tip !== undefined;
            }, 2500, "A real legend hover shows the exact hide-or-show instruction");
            tryCompare(tip, "opacity", 1, 2000, "The actual legend tooltip finishes its shared entry transition");
            compare(tip.backgroundColor, Style.Colors.toolTipBackground, "Legend tooltips retain the app tooltip background");
            compare(tip.textColor, Style.Colors.themeForeground, "Legend tooltips retain the app tooltip text colour");
            compare(tip.borderColor, Style.Colors.toolTipBorder, "Legend tooltips retain the app tooltip border");
            verify(Render.texts(tip.contentItem).some(text => text.text === tip.text && text.font.family === Style.Fonts.fontFamily), "The real legend instruction is drawn in the app's tooltip font");
        }
        function signatures() {
            const result = {};
            for (const series of Render.series(chart)) {
                if (series.objectName && series.objectName.startsWith("chart.series."))
                    result[series.objectName] = ChartOracle.points(series).filter(point => Number.isFinite(point.x) && Number.isFinite(point.y));
            }
            return result;
        }
        function test_curves_data() {
            let cases = [];
            for (const page of ["experiment", "analysis"])
                for (const single of [false, true])
                    for (const range of ["keep", "fit"])
                        cases.push({tag: page + "-" + (single ? "single" : "powder") + "-" + range, page, single, range});
            return cases;
        }
        function test_curves(data) {
            Preferences.resetToDefaults();
            compare(Preferences.chartHiddenRange, "keep", "Keeping the y range is the declared fresh preference default");
            Preferences.chartHiddenRange = data.range;
            Preferences.patternLegendShown = true;
            Preferences.patternMeasuredStyle = "line";
            Preferences.structureCurves = true;
            const source = data.single ? Probe.repoUrl("docs/user/cli/sc-neut-cwl_pr2nio4-5c2_basic/project") : Probe.repoUrl("docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project");
            const location = SettingsProof.copyProject(source);
            verify(Session.openProject(location), "The legend gate uses an independent saved powder or single-crystal project");
            app = application.createObject(null);
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "Legend clicks reach the active actual application window");
            select(data.page, data.single);
            if (!data.single) {
                Session.project.currentExperiment.scale.value *= 1000;
                frame();
            }
            const original = bounds(), keys = entries(data.single).map(item => item.key);
            verify(keys.length > 0, "Every requested chart has actual curve legend entries");
            if (!data.single) verify(["meas", "calc", "bkg", "resid"].every(key => keys.includes(key)) && keys.some(key => key.startsWith("bragg/")), "The powder witness exercises measured, calculated, background, residual and structure entries");
            for (const key of keys) {
                const before = signatures();
                tooltip(data.single, key, false);
                lowChanges.clear(); highChanges.clear();
                click(data.single, key, false);
                tryCompare(entry(data.single, key), "hidden", true, 2000, "Clicking a legend name marks its curve hidden");
                const hidden = entry(data.single, key), disabled = legend(data.single).colors.themeForegroundDisabled;
                compare(hidden.textColor, disabled, "A hidden curve's legend name uses the disabled colour");
                verify(hidden.segments.length >= 2 && hidden.segments.every(piece => String(piece.color) === String(disabled)), "A hidden curve's name and symbol both use the disabled style");
                verify(Render.texts(hidden).some(text => String(text.color) === String(disabled)), "The hidden legend label actually paints its disabled text");
                if (data.single) {
                    compare(findChild(chart, "singleCrystal.points").visible, false, "A single-crystal legend click removes the actual reflection layer from the scene");
                } else {
                    const after = signatures();
                    const expected = key.startsWith("bragg/") ? Object.keys(before).filter(name => name.startsWith("chart.series.bragg.") || name.startsWith("chart.series.structure.outline.")) : ["chart.series." + key];
                    verify(expected.some(name => before[name] && before[name].length > 0), "Each legend entry controls an independently observed nonempty curve");
                    verify(expected.every(name => !after[name] || after[name].length === 0), "The corresponding actual curve has no drawable points after its legend entry is hidden");
                }
                if (data.range === "keep") {
                    verify(same(bounds(), original), "Hiding any curve keeps both y range endpoints exactly under the default preference");
                    compare(lowChanges.count + highChanges.count, 0, "Keeping the y range emits no axis endpoint changes on hide");
                } else verify(lowChanges.count <= 1 && highChanges.count <= 1, "Hiding a curve fits each actual y endpoint at most once");
                tooltip(data.single, key, true);
                click(data.single, key, true);
                tryCompare(entry(data.single, key), "hidden", false, 2000, "Clicking the legend symbol restores its curve and enabled entry");
                if (data.single) compare(findChild(chart, "singleCrystal.points").visible, true, "Showing a single-crystal curve restores the actual reflection layer");
                else {
                    const restored = signatures();
                    verify(Object.keys(before).every(name => JSON.stringify(restored[name]) === JSON.stringify(before[name])), "Showing a powder curve restores every original series point");
                }
                verify(same(bounds(), original), "Showing every curve restores the original full-data range without drift");
                click(data.single, key, true);
                tryCompare(entry(data.single, key), "hidden", true, 2000, "The symbol can hide a curve independently of name input");
                click(data.single, key, false);
                tryCompare(entry(data.single, key), "hidden", false, 2000, "The name can restore a curve independently of symbol input");
            }
            const reset = Render.descendants(chart).find(item => item.objectName.endsWith("toolbar.reset"));
            verify(reset !== undefined, "The later-range-fit gate uses the actual chart reset control");
            const hiddenKeys = data.single ? keys : keys.filter(key => key !== "meas");
            for (const key of hiddenKeys) click(data.single, key, false);
            const hiddenRange = bounds();
            mouseClick(reset, reset.width / 2, reset.height / 2);
            frame();
            if (data.range === "keep") verify(same(bounds(), original), "A later range fit still counts hidden curves when Keep the y range is selected");
            else {
                verify(same(bounds(), hiddenRange), "A later range fit continues to count only the visible curves");
                verify(!same(bounds(), original), "The visible-only range witness excludes real hidden data rather than passing an unchanged range");
            }
            const remembered = hiddenKeys[0], other = data.page === "analysis" ? "experiment" : "analysis";
            select(other, data.single);
            compare(entry(data.single, remembered).hidden, false, "Legend visibility belongs to each chart independently");
            select(data.page, data.single);
            compare(entry(data.single, remembered).hidden, true, "A chart retains its hidden curves while navigating elsewhere in the running app");
            const another = SettingsProof.copyProject(source);
            verify(String(another) !== String(location) && Session.openProject(another), "A genuinely different project opens in the same running application");
            select(data.page, data.single);
            verify(entries(data.single).every(item => !item.hidden), "Opening another project resets all runtime legend visibility");
        }
        function test_preference() {
            Preferences.resetToDefaults();
            compare(Preferences.chartHiddenRange, "keep", "A fresh preferences store defaults to Keep the y range");
            app = application.createObject(null);
            app.requestActivate();
            Ui.click(test, Probe, app, "appBar.button.preferences");
            const dialog = findChild(app, "preferences");
            tryCompare(dialog, "opened", true, 1500, "The real app preferences dialog opens through the app bar");
            const tab = findChild(dialog, "preferences.tab.appearance");
            mouseClick(tab, tab.width / 2, tab.height / 2);
            const box = findChild(dialog, "preferences.hiddenRange");
            verify(box !== null, "Appearance exposes the actual When a curve is hidden preference selector");
            compare(JSON.stringify(Array.from(box.model)), JSON.stringify(["Keep the y range", "Fit the range to visible curves"]), "The actual preference lists the two exact owner-requested choices");
            for (const index of [1, 0]) {
                app.requestActivate();
                tryCompare(app, "active", true, 2000, "Preference input regains focus after a fresh-engine settings read");
                Ui.scrollIntoView(box);
                mouseClick(box, box.width / 2, box.height / 2);
                tryCompare(box.popup, "opened", true, 1500, "The real range preference dropdown opens for keyboard selection");
                verify(SettingsProof.key(box, Qt.Key_Home), "The real range preference receives Home input");
                if (index) verify(SettingsProof.key(box, Qt.Key_Down), "The real range preference receives Down input");
                verify(SettingsProof.key(box, Qt.Key_Return), "Return commits the selected range preference");
                tryCompare(box.popup, "visible", false, 1500, "The preference popup closes before settings are read in another engine");
                const expected = index ? "fit" : "keep";
                compare(Preferences.chartHiddenRange, expected, "The preference maps the displayed label to its stored value");
                tryVerify(() => SettingsProof.value(Globals.Vars.settingsFile, "Charts", "hiddenRange") === expected, 2500, "The production settings object flushes the changed machine preference before restart");
                const fresh = SettingsProof.restart('import QtQuick; import edi.app; QtObject { property string savedRange: Preferences.chartHiddenRange }');
                verify(fresh.error === undefined, "A fresh actual engine reads the machine range preference");
                compare(fresh.savedRange, expected, "Both range choices persist in machine preferences across an actual engine restart");
            }
        }
    }
}
