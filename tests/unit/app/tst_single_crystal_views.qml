import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiChartReference 1.0
import PatternPolishAcceptance 1.0
import ReportAcceptance 1.0
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
    property var originalQuantity
    property var originalHover
    SignalSpy {
        id: recalculated
        signalName: "recalculated"
    }
    Component {
        id: application
        Main {}
    }
    function init() {
        originalTheme = Style.Colors.theme;
        originalQuantity = Preferences.singleCrystalQuantity;
        originalHover = Preferences.chartHoverShown;
        Preferences.singleCrystalQuantity = "f_squared";
        Preferences.chartHoverShown = true;
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Single-crystal views must load the production Main window");
        appWindow.width = 1280;
        appWindow.height = 720;
        verify(waitForRendering(appWindow.contentItem), "The production window must render before input");
    }
    function cleanup() {
        recalculated.target = null;
        Session.closeProject();
        Probe.releaseScratchProjects();
        Preferences.singleCrystalQuantity = originalQuantity;
        Preferences.chartHoverShown = originalHover;
        Style.Colors.theme = originalTheme;
        if (appWindow)
            appWindow.destroy();
        appWindow = null;
    }
    function cellTexts(item) {
        return Render.cells(item).map(cell => Render.texts(cell).map(label => label.text).join(" ").trim());
    }
    function matchesDisplayed(raw, value, tolerance) {
        if (typeof raw !== "string")
            return false;
        const match = raw.replace(/−/g, "-").match(/^([-+]?[0-9]+(?:\.[0-9]+)?)(?:[eE]([-+]?[0-9]+))?$/);
        if (!match)
            return false;
        const digits = (match[1].split(".")[1] || "").length;
        const rounding = 0.500001 * Math.pow(10, Number(match[2] || 0) - digits);
        return Math.abs(Number(raw.replace(/−/g, "-")) - value) <= rounding + (tolerance || 0);
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
        const expected = Probe.rows(Session.project.currentExperiment.singleCrystalReflections);
        const inputs = JSON.parse(Probe.readReferenceFile("fullprof.json")).cases[data.project].input_rows;
        compare(expected.length, inputs.length, "The app model must retain all project reflections");
        for (let i = 0; i < expected.length; ++i) {
            compare([expected[i].h, expected[i].k, expected[i].l].join(" "), inputs[i].slice(0, 3).join(" "), "The app reflection model must preserve signed hkl order");
            compare(expected[i].intensityMeas, inputs[i][3], "The app reflection model must expose measured F squared exactly");
            compare(expected[i].intensityMeasSu, inputs[i][4], "The app reflection model must expose each standard uncertainty exactly");
            verify(Number.isFinite(expected[i].intensityCalc), "The app reflection model must carry each computed F squared");
        }
        const chart = Review.find(Ui.page(appWindow), "singleCrystal.chart");
        verify(chart !== null && chart.width > 0 && chart.height > 0, "Both single-crystal pages must display their real chart");
        verify(waitForRendering(chart), "The populated single-crystal chart must reach a rendered frame");
        const layer = Review.find(chart, "singleCrystal.points");
        verify(layer !== null, "The single-crystal chart must contain its rendered measured layer");
        const points = SettingsProof.points(layer);
        compare(points.length, expected.length, "Calculation on load must populate every reflection in the actual chart");
        for (let i = 0; i < points.length; ++i) {
            verify(Math.abs(points[i].x - expected[i].intensityCalc) < 1e-7 && Math.abs(points[i].y - inputs[i][3]) < 1e-7, "The labelled calculated and measured axes must place each reflection at its own values");
        }
        const graph = ChartOracle.graph(chart);
        verify(graph !== null, "The chart must expose its real Qt Graphs view");
        const series = Array.from(graph.seriesList).map(item => ({
                    points: ChartOracle.points(item)
                }));
        verify(series.some(s => s.points.length >= 2 && s.points[0].x !== s.points[s.points.length - 1].x && s.points.every(p => Math.abs(p.x - p.y) < 1e-9)), "The actual chart must draw the nonzero-length y equals x reference line");
        verify(/F² calc/.test(Ui.text(chart)) && /F² meas/.test(Ui.text(chart)), "The chart must label both axes with their plotted quantities");
        verify(!Ui.text(chart).includes("Not calculated yet"), "A complete single-crystal project must already be calculated on load");
        const initial = [layer.xMin, layer.xMax, layer.yMin, layer.yMax];
        const pointer = Review.descendants(chart).find(item => typeof item.pressX === "number" && typeof item.pressY === "number");
        const reset = Review.find(chart, "singleCrystal.toolbar.reset");
        verify(pointer !== undefined && reset !== null && Ui.exposed(reset), "The scatter chart must expose the shared zoom surface and reset control");
        mouseDrag(pointer, pointer.width * .2, pointer.height * .2, pointer.width * .3, pointer.height * .4);
        tryVerify(() => layer.xMax - layer.xMin < initial[1] - initial[0], 2000, "A real drag must zoom the single-crystal plot");
        mouseClick(reset, reset.width / 2, reset.height / 2);
        tryVerify(() => [layer.xMin, layer.xMax, layer.yMin, layer.yMax].every((value, i) => Math.abs(value - initial[i]) < 1e-7), 2000, "Reset must restore both single-crystal axes after zoom");
        verify(Review.find(chart.parent.parent, "singleCrystal.reflections") === null, "The main chart area must leave the reflection table to the Experiment Extra sidebar");
        appWindow.update();
        verify(waitForRendering(chart), "Both themes and workflow pages must draw the single-crystal chart");
        const frame = PatternProof.capture(appWindow, "single-crystal-chart-" + data.tag);
        verify(frame.openGL && frame.saved, "The actual single-crystal chart must retain an OpenGL capture in each page and theme");
        if (data.page === "analysis")
            return;
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        verify(!Ui.groupNames(Ui.page(appWindow)).includes("refln"), "The reflection group must not occupy the Basic tab");
        Ui.click(test, Probe, appWindow, "sideBar.tab.extras");
        verify(Ui.groupNames(Ui.page(appWindow)).includes("refln"), "The Experiment Extra tab must expose its dedicated reflection group; visible groups=" + JSON.stringify(Ui.groupNames(Ui.page(appWindow))));
        expand("group.refln");
        const reflectionGroup = Review.findGroup(Ui.page(appWindow), "group.refln");
        verify(reflectionGroup !== null, "The expanded reflection group must remain in the live Extra tab");
        const tables = Review.descendants(reflectionGroup).filter(item => item.visible && item.headerItem && typeof item.count === "number" && typeof item.itemAtIndex === "function");
        const table = tables.find(item => item.count === inputs.length && item.itemAtIndex(0));
        verify(table !== undefined, "The Extra reflection group must render the complete project row count");
        const headers = cellTexts(table.headerItem).map(text => text.toLowerCase().replace(/²/g, "2").replace(/θ/g, "theta").replace(/λ/g, "lambda").replace(/Å/gi, "a").replace(/[^a-z0-9]/g, ""));
        const columns = [headers.indexOf("h"), headers.indexOf("k"), headers.indexOf("l"), headers.findIndex(text => /f2.*meas/.test(text)), headers.findIndex(text => /^(su|sigma|uncertainty)$/.test(text)), headers.findIndex(text => /f2.*calc/.test(text)), headers.findIndex((text, index) => /residual|diff.*sigma/.test(text) || (text === "su" && index > headers.findIndex(t => /^(su|sigma|uncertainty)$/.test(t))))];
        verify(columns.every(index => index >= 0) && new Set(columns).size === 7, "The real reflection table must label its distinct h, k, l, measured, uncertainty, calculated and residual columns");
        const dColumn = headers.findIndex(text => text === "d" || text === "da");
        const wavelengthColumn = headers.findIndex(text => /wavelength|lambda/.test(text) && !text.includes("sin"));
        if (data.project.includes("tof"))
            verify(wavelengthColumn >= 0, "The TOF reflection table must include its per-reflection wavelength column");
        const sinColumn = headers.findIndex(text => /sin.*lambda|sinθ|sin/.test(text));
        verify(dColumn >= 0 && sinColumn >= 0, "The Extra table must include the reflection category's d-spacing and sin-theta-over-wavelength columns");
        for (const i of [0, Math.floor(expected.length / 2), expected.length - 1]) {
            table.positionViewAtIndex(i, ListView.Center);
            tryVerify(() => table.itemAtIndex(i) !== null, 2000, "Reflection table scrolling must instantiate the requested real row");
            const item = table.itemAtIndex(i);
            Ui.scrollIntoView(item);
            verify(waitForRendering(item), "The reflection row must be drawn before its text is checked");
            const cells = cellTexts(item);
            if (data.project.includes("tof"))
                verify(matchesDisplayed(cells[wavelengthColumn], inputs[i][5]), "The TOF reflection wavelength cell must retain the independent input value");
            verify(Number.isFinite(expected[i].dSpacing) && expected[i].dSpacing > 0, "Calculation on load must populate finite positive reflection d spacings");
            verify(matchesDisplayed(cells[dColumn], expected[i].dSpacing), "The rendered d-spacing column must show the calculated reflection value");
            verify(matchesDisplayed(cells[sinColumn], 1 / (2 * expected[i].dSpacing)), "The reflection columns must satisfy the independent Bragg relation sin-theta-over-wavelength equals one over two d");
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
    function initTestCase() {
        compare(Preferences.singleCrystalQuantity, "f_squared", "Fresh chart preferences must default to F squared before a test writes them");
        compare(Preferences.chartHoverShown, true, "Fresh chart preferences must default to showing reflection tooltips");
    }
    function expand(name) {
        const group = Review.findGroup(Ui.page(appWindow), name);
        verify(group !== null, "The selected sidebar tab must own the requested category group");
        tryVerify(() => {
            Ui.scrollIntoView(group.titleArea);
            return Ui.exposed(group.titleArea);
        }, 2000, "The real category header must enter the sidebar viewport before expansion");
        verify(waitForPolish(appWindow.contentItem), "The scrolled category header must finish layout before input");
        if (group.collapsed) {
            const point = Ui.clickPoint(group.titleArea);
            mouseClick(group.titleArea, point.x, point.y);
        }
        tryCompare(group, "collapsed", false, 2000, "A real header click must expand the selected category");
        tryVerify(() => Math.abs(group.height - (group.titleArea.height + group.spacing + group.contentHeight + group.bottomPadding)) < .01, 2000, "The category must finish expanding before inspecting its contents");
        Ui.scrollIntoView(group.contentItem);
        verify(waitForPolish(appWindow.contentItem), "The expanded category content must finish layout before observation");
        return group;
    }
    function pageCases() {
        let cases = [];
        for (const theme of ["light", "dark"])
            for (const page of ["experiment", "analysis"])
                cases.push({
                    tag: theme + "-" + page,
                    dark: theme === "dark",
                    page: page
                });
        return cases;
    }
    function openSingle(data, location) {
        Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
        verify(Session.openProject(location || Probe.referenceUrl("projects/sc-neut-cwl_tbti_basic")), "The independent single-crystal witness must open through the normal app loader: " + Session.lastError);
        tryVerify(() => !Session.project.calculating && Session.project.currentExperiment.singleCrystalReflections.calculatedShown, 10000, "Opening a complete single-crystal project must calculate before any user calculation request");
        Ui.click(test, Probe, appWindow, "appBar.tab." + data.page);
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1, 3000, "The requested chart page must enter the real viewport");
        const chart = Review.find(Ui.page(appWindow), "singleCrystal.chart");
        verify(chart !== null && Ui.rendered(chart), "The selected workflow page must render its single-crystal chart");
        verify(waitForRendering(chart), "The populated single-crystal witness must reach a rendered frame");
        return chart;
    }
    function selectQuantity(chart, index) {
        const combo = Review.find(chart, "singleCrystal.toolbar.quantity");
        verify(combo !== null && Ui.exposed(combo), "The chart toolbar must expose the F squared or F selector");
        if (combo.currentIndex === index)
            return;
        mouseClick(combo, combo.width / 2, combo.height / 2);
        tryCompare(combo.popup, "opened", true, 2000, "A real pointer click must open the quantity choices");
        const list = combo.popup.contentItem;
        list.positionViewAtIndex(index, ListView.Contain);
        const delegate = list.itemAtIndex(index);
        verify(delegate !== null && delegate.enabled, "Both plotted quantities must be selectable through the actual popup");
        mouseClick(delegate, delegate.width / 2, delegate.height / 2);
        tryCompare(combo, "currentIndex", index, 2000, "Selecting the real popup row must change the plotted quantity");
        verify(waitForRendering(chart), "The quantity change must reach a rendered chart");
    }
    function test_toolbar_quantity_and_memory_data() {
        return pageCases();
    }
    function test_toolbar_quantity_and_memory(data) {
        const chart = openSingle(data);
        const combo = Review.find(chart, "singleCrystal.toolbar.quantity");
        const reset = Review.find(chart, "singleCrystal.toolbar.reset");
        const hover = Review.find(chart, "singleCrystal.toolbar.hover");
        verify(combo !== null && reset !== null && hover !== null, "The chart toolbar must offer quantity, tooltip and reset controls together");
        compare(combo.currentIndex, 0, "The single-crystal chart's initial quantity must be F squared");
        verify(/axes?:\s*F²/.test(combo.displayText), "The closed quantity selector must use the shared axis-colon-value form");
        const left = combo.mapToItem(chart, 0, 0), right = reset.mapToItem(chart, reset.width, 0);
        verify(Math.abs((left.x + right.x) / 2 - chart.width / 2) <= 1, "The complete second toolbar line must be centred in the chart");
        verify(Math.abs(left.y - right.y) <= 1, "The selector and buttons must share the centred second line");
        selectQuantity(chart, 1);
        const model = Session.project.currentExperiment.singleCrystalReflections;
        const rows = JSON.parse(Probe.readReferenceFile("fullprof.json")).cases["sc-neut-cwl_tbti_basic"].input_rows;
        const layer = Review.find(chart, "singleCrystal.points");
        const points = SettingsProof.points(layer);
        compare(points.length, rows.length, "Switching to F must retain every positive measured reflection");
        for (let i = 0; i < rows.length; ++i) {
            const f = Math.sqrt(rows[i][3]), sigma = rows[i][4] / (2 * f);
            verify(Math.abs(points[i].y - f) < 1e-10, "The plotted measured F must equal the independent square root of the frozen measured F squared");
            verify(Math.abs(model.measuredFSu[i] - sigma) < 1e-10, "The F uncertainty must follow independent first-order propagation sigma-F equals sigma-F-squared over twice F");
            verify(Math.abs(points[i].x * points[i].x - model.calculated[i]) < 1e-7, "The plotted calculated F squared must recover the calculated F squared reflection value");
        }
        verify(/F calc/.test(Ui.text(chart)) && /F meas/.test(Ui.text(chart)), "Both axis titles must change to F with the selector");
        checkErrorBar(chart, layer, rows, true);
        Ui.click(test, Probe, appWindow, "appBar.tab." + (data.page === "experiment" ? "analysis" : "experiment"));
        const other = Review.find(Ui.page(appWindow), "singleCrystal.chart");
        verify(other !== null, "The other workflow page must expose its single-crystal chart");
        compare(Review.find(other, "singleCrystal.toolbar.quantity").currentIndex, 1, "The selected quantity must be shared by both chart pages");
        Session.closeProject();
        const reopened = openSingle(data);
        compare(Review.find(reopened, "singleCrystal.toolbar.quantity").currentIndex, 1, "Closing and reopening the project must retain the remembered F selection");
        selectQuantity(reopened, 0);
        verify(/F² calc/.test(Ui.text(reopened)), "Choosing F squared again must restore its chart labels");
        const restored = SettingsProof.points(Review.find(reopened, "singleCrystal.points"));
        verify(restored.every((point, i) => Math.abs(point.y - rows[i][3]) < 1e-7), "Choosing F squared again must restore every original measured value");
        checkErrorBar(reopened, Review.find(reopened, "singleCrystal.points"), rows, false);
    }
    function checkErrorBar(chart, layer, rows, amplitude) {
        // A large, isolated uncertainty in the frozen Tb data makes its bar observable in pixels.
        const index = rows.findIndex(row => row[0] === 17 && row[1] === 3 && row[2] === 3);
        verify(index >= 0, "The independent Tb input must retain the wide uncertainty reflection");
        const point = SettingsProof.points(layer)[index];
        const sigma = amplitude ? rows[index][4] / (2 * Math.sqrt(rows[index][3])) : rows[index][4];
        const x = (point.x - layer.xMin) / (layer.xMax - layer.xMin) * layer.width;
        const at = value => (1 - (value - layer.yMin) / (layer.yMax - layer.yMin)) * layer.height;
        const colour = layer.color;
        function ink(y) {
            for (let dx = -2; dx <= 2; ++dx) {
                const pixel = PatternProof.pixel(appWindow, layer, x + dx, y);
                if (Math.abs(pixel.r - colour.r) + Math.abs(pixel.g - colour.g) + Math.abs(pixel.b - colour.b) < 0.2)
                    return true;
            }
            return false;
        }
        verify(sigma / (layer.yMax - layer.yMin) * layer.height > 5, "The uncertainty witness must span enough pixels to distinguish a bar from a marker");
        verify(ink(at(point.y - sigma * 0.85)) && ink(at(point.y + sigma * 0.85)), "The rendered measured bar must extend in both directions by its independently propagated uncertainty");
        verify(!ink(at(point.y + sigma * 1.2)), "The rendered uncertainty bar must stop at its independent length");
    }
    function test_reflection_hover_and_shared_toggle_data() {
        return pageCases();
    }
    function test_reflection_hover_and_shared_toggle(data) {
        const chart = openSingle(data);
        const reference = JSON.parse(Probe.readReferenceFile("fullprof.json")).cases["sc-neut-cwl_tbti_basic"];
        const inputs = reference.input_rows;
        const model = Session.project.currentExperiment.singleCrystalReflections;
        const layer = Review.find(chart, "singleCrystal.points");
        const pointer = Review.descendants(chart).find(item => typeof item.pressX === "number");
        verify(pointer !== undefined, "Hover acceptance must use the chart's actual pointer surface");
        const toggle = Review.find(chart, "singleCrystal.toolbar.hover");
        verify(toggle !== null && toggle.checked, "Single-crystal tooltips must share the initially enabled chart setting");
        for (const amplitude of [false, true]) {
            selectQuantity(chart, amplitude ? 1 : 0);
            const points = SettingsProof.points(layer);
            const index = 4;
            const point = points[index], input = inputs[index];
            mouseMove(pointer, 1, 1);
            mouseMove(pointer, (point.x - layer.xMin) / (layer.xMax - layer.xMin) * pointer.width, (1 - (point.y - layer.yMin) / (layer.yMax - layer.yMin)) * pointer.height);
            const tooltip = Review.find(chart, "singleCrystal.hover");
            tryVerify(() => tooltip !== null && tooltip.visible, 2000, "Hovering an actual reflection must show its value tooltip");
            const text = Ui.text(tooltip).replace(/<br\s*\/?\s*>/g, "\n").replace(/<[^>]*>/g, "").replace(/−/g, "-");
            verify(text.includes(input.slice(0, 3).join(" ")), "The reflection tooltip must identify its own signed h k l");
            const meas = text.match(/meas:\s*([-+\d.eE]+)\s*±\s*([-+\d.eE]+)/);
            const calc = text.match(/calc:\s*([-+\d.eE]+)/);
            verify(meas !== null && calc !== null, "A reflection hover must show measured value plus-or-minus uncertainty and calculated value");
            const expectedMeas = amplitude ? Math.sqrt(input[3]) : input[3];
            const expectedSu = amplitude ? input[4] / (2 * Math.sqrt(input[3])) : input[4];
            verify(matchesDisplayed(meas[1], expectedMeas) && matchesDisplayed(meas[2], expectedSu), "The tooltip's measured value and uncertainty must independently follow the plotted F squared or F quantity");
            const independentCalc = reference.calculated_rows[index].f2_calc;
            const calcValue = amplitude ? Math.sqrt(independentCalc) : independentCalc;
            const printBudget = independentCalc * 1e-4 + 5.1e-5;
            verify(matchesDisplayed(calc[1], calcValue, amplitude ? printBudget / (2 * calcValue) : printBudget), "The tooltip's calculated value must belong to the hovered reflection in the selected quantity");
            verify(text.includes(amplitude ? "F meas:" : "F² meas:"), "The tooltip must name the currently selected quantity");
        }
        mouseClick(toggle, toggle.width / 2, toggle.height / 2);
        compare(Preferences.chartHoverShown, false, "The single-crystal tooltip button must update the shared remembered chart setting");
        mouseMove(pointer, 1, 1);
        tryVerify(() => Review.find(chart, "singleCrystal.hover") === null, 2000, "Disabling tooltips must suppress reflection hover content");
        verify(Session.openProject(Probe.referenceUrl("powder")), "The shared-setting witness must open its powder control");
        Ui.click(test, Probe, appWindow, "appBar.tab." + data.page);
        const patternToggle = Review.find(Ui.page(appWindow), "chart.toolbar.hover");
        verify(patternToggle !== null && !patternToggle.checked, "The powder chart's tooltip button must observe the same saved disabled setting");
        mouseClick(patternToggle, patternToggle.width / 2, patternToggle.height / 2);
        compare(Preferences.chartHoverShown, true, "The powder tooltip button must update the same remembered setting");
        const restored = openSingle(data);
        compare(Review.find(restored, "singleCrystal.toolbar.hover").checked, true, "Reopening single crystal must retain the tooltip choice made on the pattern chart");
    }
    function test_calculation_after_edits_and_extinction_labels_data() {
        return [
            {
                tag: "light",
                dark: false,
                page: "experiment"
            },
            {
                tag: "dark",
                dark: true,
                page: "experiment"
            }
        ];
    }
    function test_calculation_after_edits_and_extinction_labels(data) {
        const chart = openSingle(data, Probe.referenceUrl("projects/sc-neut-cwl_tbti_isotropic-extinction"));
        const model = Session.project.currentExperiment.singleCrystalReflections;
        const before = Array.from(model.calculated);
        const scale = Session.project.currentExperiment.scale;
        recalculated.target = Session.project;
        recalculated.clear();
        scale.value *= 1.37;
        tryVerify(() => recalculated.count > 0 && !Session.project.calculating, 10000, "Editing a single-crystal parameter must automatically complete a new calculation");
        verify(model.calculated.every((value, i) => Math.abs(value - before[i] * 1.37) <= 1e-8 + Math.abs(value) * 1e-10), "Automatic recalculation after a scale edit must obey the independent linear-scale invariant");
        const plotted = SettingsProof.points(Review.find(chart, "singleCrystal.points"));
        verify(plotted.every((point, i) => Math.abs(point.x - model.calculated[i]) < 1e-7), "The real chart must display the new calculated values after an edit");
        Ui.click(test, Probe, appWindow, "sideBar.tab.extras");
        if (!Ui.groupNames(Ui.page(appWindow)).includes("extinction"))
            Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        const group = expand("group.extinction");
        verify(group !== null, "The expanded extinction group must remain in the live sidebar");
        const radius = Review.find(group, "extinction.radius"), mosaic = Review.find(group, "extinction.mosaicity");
        verify(radius !== null && mosaic !== null, "The extinction group must display its two actual parameter fields");
        verify(/crystal radius/i.test(radius.label) && /mosaicity/i.test(mosaic.label), "Extinction inputs must use descriptive crystal radius and mosaicity labels instead of isolated symbols");
        verify(/µm|μm/.test(radius.parameter.units) && /arcmin|′/.test(mosaic.parameter.units), "Extinction inputs must show crystal radius in micrometres and mosaicity in arcminutes");
    }
    function test_fit_lowers_objective_and_reports_single_crystal_factors_data() {
        return [
            {
                tag: "light",
                dark: false,
                page: "analysis"
            },
            {
                tag: "dark",
                dark: true,
                page: "analysis"
            }
        ];
    }
    function test_fit_lowers_objective_and_reports_single_crystal_factors(data) {
        const location = SettingsProof.copyProject(Probe.referenceUrl("projects/sc-neut-cwl_tbti_basic"));
        const source = SettingsProof.text(location, "experiments/experiment.edi");
        verify(source.includes("structure 3.653\n"), "The weighted fit witness must preserve the frozen FullProf input scale");
        verify(SettingsProof.write(location, "experiments/experiment.edi", source.replace("structure 3.653\n", "structure 2.59363()\n")), "The disposable fit witness must declare only scale free at seventy-one per cent of the FullProf starting value");
        openSingle(data, location);
        const reference = JSON.parse(Probe.readReferenceFile("fullprof.json")).cases["sc-neut-cwl_tbti_basic"];
        const rows = reference.input_rows;
        const basis = reference.calculated_rows.map(row => row.f2_calc / 3.653);
        const expectedScale = rows.reduce((sum, row, i) => sum + basis[i] * row[3] / (row[4] * row[4]), 0) / rows.reduce((sum, row, i) => sum + Math.pow(basis[i] / row[4], 2), 0);
        const expectedChi = rows.reduce((sum, row, i) => sum + Math.pow((row[3] - expectedScale * basis[i]) / row[4], 2), 0) / (rows.length - 1);
        const model = Session.project.currentExperiment.singleCrystalReflections;
        const before = rows.reduce((sum, row, i) => sum + Math.pow((row[3] - model.calculated[i]) / row[4], 2), 0) / (rows.length - 1);
        const scale = Session.project.currentExperiment.scale;
        verify(scale.free, "The normal app fit must see the authored free scale parameter");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        const start = Ui.find(Ui.page(appWindow), "fitting.start", true);
        verify(start !== null && start.enabled, "A measured single-crystal project with a free parameter must enable Start fitting");
        Ui.scrollIntoView(start);
        verify(waitForPolish(appWindow.contentItem), "The real Start fitting action must finish layout before input");
        const target = Ui.clickPoint(start);
        verify(target !== null, "The real fitting button must be reachable through the sidebar viewport");
        mouseClick(start, target.x, target.y);
        const dialog = findChild(appWindow, "fit.results");
        tryVerify(() => dialog !== null && dialog.opened && !Session.project.fit.running, 15000, "Start fitting must finish and open its real result dialog");
        const chi = rows.reduce((sum, row, i) => sum + Math.pow((row[3] - model.calculated[i]) / row[4], 2), 0) / (rows.length - 1);
        verify(chi < before, "The app fit must lower the independently calculated reflection objective");
        const columns = dialog.factorColumns.map(column => column.factor.replace(/<[^>]*>/g, ""));
        compare(JSON.stringify(columns), JSON.stringify(["R(F²)", "wR(F²)"]), "A single-crystal fit result must name its two single-crystal agreement factors");
        const table = Review.find(dialog.contentItem, "fit.results.agreement");
        verify(table !== null && table.count === 1 && table.itemAtIndex(0) !== null, "The actual agreement table must render the fitted single-crystal dataset row");
        const values = cellTexts(table.itemAtIndex(0)).slice(-2);
        const calc = Array.from(model.calculated);
        const r = 100 * rows.reduce((sum, row, i) => sum + Math.abs(row[3] - calc[i]), 0) / rows.reduce((sum, row) => sum + Math.abs(row[3]), 0);
        const wr = 100 * Math.sqrt(rows.reduce((sum, row, i) => sum + Math.pow((row[3] - calc[i]) / row[4], 2), 0) / rows.reduce((sum, row) => sum + Math.pow(row[3] / row[4], 2), 0));
        verify(matchesDisplayed(values[0], r) && matchesDisplayed(values[1], wr), "Rendered R-F-squared and weighted-R-F-squared percentages must match independent residual formulas");
        for (const label of Render.texts(dialog.contentItem))
            verify(label.truncated !== true && !label.text.includes("…"), "The real fit-results dialog must show complete names without truncation");
        verify(matchesDisplayed(Session.project.fit.results.text(3, "value"), chi), "The actual fit result summary must report the independently calculated reduced chi square");
        verify(Math.abs(scale.value - expectedScale) <= Math.abs(expectedScale) * 2e-4 + 2e-5, "The app's fit must reach the independent FullProf-based weighted scale optimum; actual=" + scale.value + ", expected=" + expectedScale);
        verify(chi < before && Math.abs(chi - expectedChi) <= expectedChi * 3e-4 + .002, "The app fit must lower reduced chi square to the independent all-reflection optimum");
    }

    function test_result_structure_names_are_complete_data() {
        return [
            {
                tag: "light",
                dark: false
            },
            {
                tag: "dark",
                dark: true
            }
        ];
    }
    function test_result_structure_names_are_complete(data) {
        Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
        const location = SettingsProof.copyProject(Probe.referenceUrl("../fit_tables/five"));
        const longName = "Tb2Ti2O7_oxygen_displacement_structure";
        const original = SettingsProof.text(location, "structures/ncaf.edi");
        verify(original.startsWith("data_ncaf\n"), "The saved powder fit must carry its independent structure block name");
        verify(SettingsProof.write(location, "structures/ncaf.edi", original.replace("data_ncaf\n", "data_" + longName + "\n")), "The disposable saved result must supply an unambiguously long structure name");
        // Update the link tokens in every frozen dataset without changing any measured or calculated number.
        for (const file of ["wish_1_10.edi", "wish_2_9.edi", "wish_3_8.edi", "wish_4_7.edi", "wish_5_6.edi"]) {
            const text = SettingsProof.text(location, "experiments/" + file);
            verify(text.includes("ncaf "), "Every frozen dataset must carry its declared structure link");
            verify(SettingsProof.write(location, "experiments/" + file, text.replace(/\bncaf /g, longName + " ")), "Each saved result dataset must retain its link to the authored long structure name");
        }
        const analysis = SettingsProof.text(location, "analysis/analysis.edi");
        verify(analysis.includes(" ncaf "), "The frozen saved fit must retain its structure-specific agreement rows");
        verify(SettingsProof.write(location, "analysis/analysis.edi", analysis.replace(/ ncaf /g, " " + longName + " ")), "The saved agreement rows must use the authored structure name while retaining all factor values");
        verify(Session.openProject(location), "The saved fit with a long structure name must open normally: " + Session.lastError);
        tryCompare(Session.project, "calculating", false, 10000, "The saved-name witness must finish loading before result inspection");
        const dialog = findChild(appWindow, "fit.results");
        verify(dialog !== null, "The real fit result dialog must exist for a saved fit");
        dialog.open();
        tryCompare(dialog, "opened", true, 3000, "The actual saved fit result dialog must open");
        verify(waitForPolish(dialog.contentItem), "Long-name result headers must finish layout before measuring truncation");
        const names = Render.texts(dialog.contentItem).filter(label => label.objectName.startsWith("fit.results.agreement.structure."));
        verify(names.length >= 2, "The saved fit must render both structure-specific agreement factor names");
        for (const label of names) {
            compare(label.text, longName, "Every structure header must retain the complete authored name");
            verify(label.truncated !== true && label.contentWidth <= label.width + 1, "The complete structure name must fit in its rendered result header without truncation");
            verify(Ui.rendered(label), "The untruncated structure name must remain inside the actual dialog viewport");
        }
    }
}
