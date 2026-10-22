import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiChartReference 1.0
import PatternPolishAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "UiInteraction.js" as Ui
import "E04Review.js" as Review
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "SingleCrystalViews"
    when: windowShown
    property var appWindow
    property var originalTheme
    Component {
        id: application
        Main {}
    }
    function init() {
        originalTheme = Style.Colors.theme;
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Single-crystal views must load the production Main window");
        appWindow.width = 1280;
        appWindow.height = 900;
        verify(waitForRendering(appWindow.contentItem), "The production window must render before input");
    }
    function cleanup() {
        Session.closeProject();
        Style.Colors.theme = originalTheme;
        if (appWindow)
            appWindow.destroy();
        appWindow = null;
    }
    function cellTexts(item) {
        return Render.cells(item).map(cell => Render.texts(cell).map(label => label.text).join(" ").trim());
    }
    function matchesDisplayed(raw, value) {
        if (typeof raw !== "string")
            return false;
        const match = raw.replace(/−/g, "-").match(/^([-+]?[0-9]+(?:\.[0-9]+)?)(?:[eE]([-+]?[0-9]+))?$/);
        if (!match)
            return false;
        const digits = (match[1].split(".")[1] || "").length;
        const rounding = 0.500001 * Math.pow(10, Number(match[2] || 0) - digits);
        return Math.abs(Number(raw.replace(/−/g, "-")) - value) <= rounding;
    }
    function test_chart_table_and_sidebar_data() {
        let cases = [];
        for (const name of ["sc-neut-cwl_pr2nio4_basic", "sc-neut-cwl_tbti_basic", "sc-neut-cwl_tbti_anisotropic-adp", "sc-neut-cwl_tbti_isotropic-extinction", "sc-neut-tof_taurine_basic"])
            for (const dark of [false, true])
                for (const page of ["experiment", "analysis"])
                    cases.push({
                        tag: name + "-" + (dark ? "dark" : "light") + "-" + page,
                        project: name,
                        dark: dark,
                        page: page
                    });
        return cases;
    }
    function test_chart_table_and_sidebar(data) {
        Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
        verify(Session.openProject(Probe.referenceUrl("projects/" + data.project)), "Each independent single-crystal project must open in the real app: " + Session.lastError);
        tryCompare(Session.project, "calculating", false, 10000, "The single-crystal project must finish its normal calculation");
        Ui.click(test, Probe, appWindow, "appBar.tab." + data.page);
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1, 3000, "The selected workflow page must be in the real viewport");
        verify(waitForPolish(appWindow.contentItem, 3000), "The single-crystal view must finish layout");
        const expected = Probe.rows(Session.project.currentExperiment.reflections);
        const inputs = JSON.parse(Probe.readReferenceFile("fullprof.json")).cases[data.project].input_rows;
        compare(expected.length, inputs.length, "The app model must retain all project reflections");
        for (let i = 0; i < expected.length; ++i) {
            compare(expected[i].hkl, inputs[i].slice(0, 3).join(" "), "The app reflection model must preserve signed hkl order");
            compare(expected[i].intensityMeas, inputs[i][3], "The app reflection model must expose measured F squared exactly");
            compare(expected[i].intensityMeasSu, inputs[i][4], "The app reflection model must expose each standard uncertainty exactly");
            verify(Number.isFinite(expected[i].intensityCalc), "The app reflection model must carry each computed F squared");
        }
        const chart = Review.find(Ui.page(appWindow), "chart");
        verify(chart !== null && chart.width > 0 && chart.height > 0, "Both single-crystal pages must display their real chart");
        verify(waitForRendering(chart), "The populated single-crystal chart must reach a rendered frame");
        const series = PatternProof.series(chart, "");
        verify(series.some(s => s.points.length === expected.length && s.points.every((p, i) => Math.abs(p.x - expected[i].intensityMeas) < 1e-7 && Math.abs(p.y - expected[i].intensityCalc) < 1e-7)), "The displayed scatter series must use measured F squared on x and computed F squared on y for every row");
        verify(series.some(s => s.points.length >= 2 && s.points[0].x !== s.points[s.points.length - 1].x && s.points.every(p => Math.abs(p.x - p.y) < 1e-9)), "The actual chart must draw the nonzero-length y equals x reference line");
        for (const index of [0, Math.floor(expected.length / 2), expected.length - 1]) {
            const row = expected[index];
            verify(series.some(line => line.points.some((left, i) => i + 1 < line.points.length && Math.abs(left.x - (row.intensityMeas - row.intensityMeasSu)) < 1e-7 && Math.abs(left.y - row.intensityCalc) < 1e-7 && Math.abs(line.points[i + 1].x - (row.intensityMeas + row.intensityMeasSu)) < 1e-7 && Math.abs(line.points[i + 1].y - row.intensityCalc) < 1e-7)), "The visible chart must draw each measured standard uncertainty horizontally about its own F squared point");
        }
        const xAxis = ChartOracle.object(chart, "chart.axis.x");
        const yAxis = ChartOracle.object(chart, "chart.axis.y");
        verify(xAxis !== null && yAxis !== null, "The single-crystal chart must expose its real numeric axes");
        const initial = [xAxis.min, xAxis.max, yAxis.min, yAxis.max];
        const pointer = Review.find(chart, "chart.pointer");
        const reset = Review.find(chart, "chart.toolbar.reset");
        verify(pointer !== null && reset !== null && Ui.exposed(reset), "The scatter chart must expose the shared zoom surface and reset control");
        mouseDrag(pointer, pointer.width * .2, pointer.height * .2, pointer.width * .3, pointer.height * .4);
        tryVerify(() => xAxis.max - xAxis.min < initial[1] - initial[0], 2000, "A real drag must zoom the single-crystal plot");
        mouseClick(reset, reset.width / 2, reset.height / 2);
        tryVerify(() => [xAxis.min, xAxis.max, yAxis.min, yAxis.max].every((value, i) => Math.abs(value - initial[i]) < 1e-7), 2000, "Reset must restore both single-crystal axes after zoom");
        const tables = Review.descendants(Ui.page(appWindow)).filter(item => item.visible && item.headerItem && typeof item.count === "number" && typeof item.itemAtIndex === "function");
        const table = tables.find(item => item.count === inputs.length && item.itemAtIndex(0));
        verify(table !== undefined, "Both pages must render a reflection table with the complete project row count");
        const headers = cellTexts(table.headerItem).map(text => text.toLowerCase().replace(/²/g, "2").replace(/[^a-z0-9]/g, ""));
        const columns = [headers.indexOf("h"), headers.indexOf("k"), headers.indexOf("l"), headers.findIndex(text => /f2.*meas/.test(text)), headers.findIndex(text => /^(su|sigma|uncertainty)$/.test(text)), headers.findIndex(text => /f2.*calc/.test(text)), headers.findIndex(text => /residual|diff.*sigma/.test(text))];
        verify(columns.every(index => index >= 0) && new Set(columns).size === 7, "The real reflection table must label its distinct h, k, l, measured, uncertainty, calculated and residual columns");
        for (const i of [0, Math.floor(expected.length / 2), expected.length - 1]) {
            table.positionViewAtIndex(i, ListView.Center);
            tryVerify(() => table.itemAtIndex(i) !== null, 2000, "Reflection table scrolling must instantiate the requested real row");
            const item = table.itemAtIndex(i);
            verify(waitForRendering(item), "The reflection row must be drawn before its text is checked");
            const cells = cellTexts(item);
            const values = inputs[i].slice(0, 5).concat([expected[i].intensityCalc, (inputs[i][3] - expected[i].intensityCalc) / inputs[i][4]]);
            for (let j = 0; j < values.length; ++j)
                verify(matchesDisplayed(cells[columns[j]], values[j]), "Every rendered reflection cell must match its own labelled quantity to its displayed precision");
        }
        const sortHeader = Render.cells(table.headerItem)[columns[3]];
        const endpoints = [Math.min(...inputs.map(row => row[3])), Math.max(...inputs.map(row => row[3]))];
        let firstOrder = null;
        for (let click = 0; click < 2; ++click) {
            mouseClick(sortHeader, sortHeader.width / 2, sortHeader.height / 2);
            table.positionViewAtIndex(0, ListView.Beginning);
            tryVerify(() => table.itemAtIndex(0) !== null, 2000, "Sorting must retain a rendered first reflection row");
            tryVerify(() => {
                const value = cellTexts(table.itemAtIndex(0))[columns[3]];
                return endpoints.some(endpoint => matchesDisplayed(value, endpoint));
            }, 2000, "Clicking the measured header must sort reflection values numerically");
            const first = cellTexts(table.itemAtIndex(0))[columns[3]];
            const ascending = matchesDisplayed(first, endpoints[0]);
            if (firstOrder !== null)
                verify(ascending !== firstOrder, "Clicking the same reflection header again must reverse the sort direction");
            firstOrder = ascending;
            table.positionViewAtIndex(expected.length - 1, ListView.End);
            tryVerify(() => table.itemAtIndex(expected.length - 1) !== null, 2000, "Sorting must retain the rendered final reflection row");
            verify(matchesDisplayed(cellTexts(table.itemAtIndex(expected.length - 1))[columns[3]], endpoints[ascending ? 1 : 0]), "The final sorted reflection must be the opposite numeric endpoint");
        }
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "Both themes must reach a populated production frame");
        const capture = PatternProof.capture(appWindow, "single-crystal-" + data.tag);
        verify(capture.openGL && capture.saved, "The actual single-crystal view must retain an OpenGL capture in each theme");
        if (data.page === "experiment") {
            for (const tier of ["basic", "extras"]) {
                Ui.click(test, Probe, appWindow, "sideBar.tab." + tier);
                const groups = Ui.groupNames(Ui.page(appWindow));
                for (const forbidden of ["background", "peak", "peak_profile", "excluded_regions"])
                    verify(!groups.includes(forbidden), "Single-crystal sidebars must omit every powder-only group");
            }
            Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
            const basic = Ui.groupNames(Ui.page(appWindow));
            Ui.click(test, Probe, appWindow, "sideBar.tab.extras");
            verify(basic.concat(Ui.groupNames(Ui.page(appWindow))).includes("extinction"), "The Experiment sidebar must expose the single-crystal extinction group");
        }
    }
    function test_powder_view_unchanged_data() {
        return [
            {
                tag: "light-experiment",
                dark: false,
                page: "experiment"
            },
            {
                tag: "dark-experiment",
                dark: true,
                page: "experiment"
            },
            {
                tag: "light-analysis",
                dark: false,
                page: "analysis"
            },
            {
                tag: "dark-analysis",
                dark: true,
                page: "analysis"
            }
        ];
    }
    function test_powder_view_unchanged(data) {
        Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
        verify(Session.openProject(Probe.referenceUrl("powder")), "The existing powder project must still open in the production app");
        tryCompare(Session.project, "calculating", false, 10000, "The powder control must finish its normal calculation");
        Ui.click(test, Probe, appWindow, "appBar.tab." + data.page);
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1, 3000, "The powder workflow page must reach the real viewport");
        const chart = Review.find(Ui.page(appWindow), "chart");
        verify(chart !== null && chart.visible, "Powder must retain its production pattern chart");
        const pin = JSON.parse(Probe.readReferenceFile("powder-regression.json")).intensity_calc;
        tryVerify(() => PatternProof.series(chart, "chart.series.calc").some(series => series.points.length === pin.length && series.points.every((point, i) => Math.abs(point.x - (20 + i * .8)) < 1e-7 && Math.abs(point.y - pin[i]) <= 1e-9 + Math.abs(pin[i]) * 1e-12)), 3000, "The actual powder curve must retain the pre-feature regression pin");
        if (data.page === "experiment") {
            let groups = [];
            for (const tier of ["basic", "extras"]) {
                Ui.click(test, Probe, appWindow, "sideBar.tab." + tier);
                groups = groups.concat(Ui.groupNames(Ui.page(appWindow)));
            }
            verify(groups.includes("background"), "The powder Experiment sidebar must retain its background group");
            verify(!groups.includes("extinction"), "Single-crystal extinction must not appear on the powder sidebar");
        }
        verify(waitForRendering(chart), "The unchanged powder curve must be rendered in both themes");
    }
}
