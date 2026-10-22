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
    property var originalPointer
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
        originalPointer = Preferences.chartPointerMode;
        if (originalPointer !== undefined)
            Preferences.chartPointerMode = "zoom";
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
        if (originalPointer !== undefined)
            Preferences.chartPointerMode = originalPointer;
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
        const reset = toolbarControl(chart, "reset");
        verify(pointer !== undefined && reset !== null && Ui.exposed(reset), "The scatter chart must expose the shared zoom surface and reset control");
        verify(waitForPolish(chart), "The chart pointer geometry must finish layout before a real drag");
        verify(Ui.exposed(pointer), "The actual chart pointer must be exposed before a zoom drag");
        mouseDrag(pointer, pointer.width * .2, pointer.height * .2, pointer.width * .3, pointer.height * .4, Qt.LeftButton, Qt.NoModifier, 20);
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
        tryVerify(() => Ui.groupNames(Ui.page(appWindow)).includes("refln"), 2000, "The Experiment Extra tab must expose its dedicated reflection group after its lazy content has entered the viewport");
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
        if (Preferences.chartPointerMode !== undefined)
            compare(Preferences.chartPointerMode, "zoom", "Fresh chart preferences must initially enable box zoom");
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
        const combo = toolbarControl(chart, "quantity");
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
        const combo = toolbarControl(chart, "quantity");
        const reset = toolbarControl(chart, "reset");
        const hover = toolbarControl(chart, "hover");
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
        compare(toolbarControl(other, "quantity").currentIndex, 1, "The selected quantity must be shared by both chart pages");
        Session.closeProject();
        const reopened = openSingle(data);
        compare(toolbarControl(reopened, "quantity").currentIndex, 1, "Closing and reopening the project must retain the remembered F selection");
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
        const oracle = JSON.parse(Probe.readReferenceFile("hover.json"));
        compare(Session.project.suRule, oracle.rule, "The independent tooltip oracle must match the project's declared IUCr display rule");
        const model = Session.project.currentExperiment.singleCrystalReflections;
        const layer = Review.find(chart, "singleCrystal.points");
        const pointer = Review.descendants(chart).find(item => typeof item.pressX === "number");
        verify(pointer !== undefined, "Hover acceptance must use the chart's actual pointer surface");
        const toggle = toolbarControl(chart, "hover");
        verify(toggle !== null && toggle.checked, "Single-crystal tooltips must share the initially enabled chart setting");
        for (const amplitude of [false, true]) {
            selectQuantity(chart, amplitude ? 1 : 0);
            const points = SettingsProof.points(layer);
            const index = oracle.index;
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
            const shown = oracle.quantities[amplitude ? "f" : "f_squared"];
            compare(Number(meas[1]), shown.shown, "The tooltip's measured F squared or F must follow independent Decimal conversion and the project's IUCr rounding rule");
            compare(Number(meas[2]), shown.shown_su, "The tooltip's F squared or propagated F uncertainty must follow the independent IUCr display value");
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
        if (Preferences.chartPointerMode !== undefined)
            compare(Preferences.chartPointerMode, "zoom", "Fresh chart preferences must initially enable box zoom");
        compare(Preferences.chartHoverShown, true, "The powder tooltip button must update the same remembered setting");
        const restored = openSingle(data);
        compare(toolbarControl(restored, "hover").checked, true, "Reopening single crystal must retain the tooltip choice made on the pattern chart");
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
        verify(SettingsProof.write(location, "experiments/experiment.edi", source.replace("structure 3.653\n", "structure 3.653()\n")), "The disposable fit witness must declare only scale free at the actual FullProf page starting value");
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
    function toolbarControl(chart, name) {
        return Review.find(chart, "singleCrystal.toolbar." + name) || Review.find(chart, "chart.toolbar." + name);
    }
    function test_zoom_selection_and_shared_pointer_modes_data() {
        return pageCases();
    }
    function test_zoom_selection_and_shared_pointer_modes(data) {
        const chart = openSingle(data);
        const pan = toolbarControl(chart, "pan"), zoom = toolbarControl(chart, "zoom"), reset = toolbarControl(chart, "reset");
        verify(pan !== null && zoom !== null && reset !== null && Ui.exposed(pan) && Ui.exposed(zoom), "The single-crystal chart must expose working move, box zoom and reset buttons as the pattern chart does");
        compare(Preferences.chartPointerMode, "zoom", "The single-crystal chart must expose the shared remembered pointer setting");
        verify(zoom.checked && !pan.checked, "The shared initial chart pointer mode must enable box zoom and exclude move");
        const layer = Review.find(chart, "singleCrystal.points");
        const pointer = Review.find(chart, "singleCrystal.pointer") || Review.descendants(chart).find(item => typeof item.pressX === "number");
        verify(pointer !== undefined && pointer !== null && Ui.exposed(pointer), "The zoom and move acceptance must reach the actual exposed chart pointer surface");
        verify(waitForPolish(chart), "The chart's pointer and axis geometry must settle before a box gesture");
        const initial = [layer.xMin, layer.xMax, layer.yMin, layer.yMax];
        const x0 = Math.round(pointer.width * .17), x1 = Math.round(pointer.width * .61);
        const y0 = Math.round(pointer.height * .23), y1 = Math.round(pointer.height * .77);
        const edgeY = (y0 + y1) / 2;
        const before = PatternProof.pixel(appWindow, pointer, x0, edgeY);
        let box = null;
        mousePress(pointer, x0, y0, Qt.LeftButton, Qt.NoModifier, 20);
        try {
            verify(pointer.pressed, "A real left press must grab the single-crystal box-zoom surface");
            mouseMove(pointer, x1, y1, 20);
            box = Review.find(chart, "singleCrystal.zoom.box") || Review.find(chart, "chart.zoom.box");
            verify(box !== null && Ui.rendered(box), "A box-zoom drag must display a real selection rectangle before release");
            const corner = box.mapToItem(pointer, 0, 0);
            verify(Math.abs(corner.x - x0) <= 1 && Math.abs(corner.y - y0) <= 1 && Math.abs(box.width - (x1 - x0)) <= 1 && Math.abs(box.height - (y1 - y0)) <= 1, "The visible selection rectangle must follow the actual pointer endpoints in both dimensions");
            verify(box.border.width > 0 && box.opacity > 0 && box.border.color.a > 0, "The selection rectangle must have a visible border as the pattern chart does");
            appWindow.update();
            verify(waitForRendering(chart), "The held selection rectangle must reach a rendered frame before release");
            const after = PatternProof.pixel(appWindow, pointer, x0, edgeY);
            verify(Math.abs(after.r - before.r) + Math.abs(after.g - before.g) + Math.abs(after.b - before.b) > .02, "The box border must change actual rendered pixels while the pointer is held down");
            const capture = PatternProof.capture(appWindow, "single-crystal-selection-" + data.tag);
            verify(capture.openGL && capture.saved, "The visible zoom selection must retain a real OpenGL capture in each theme and page");
        } finally {
            mouseRelease(pointer, x1, y1, Qt.LeftButton, Qt.NoModifier, 20);
        }
        tryVerify(() => !box.visible, 2000, "Releasing a box zoom must hide its selection rectangle");
        const expected = [initial[0] + x0 / pointer.width * (initial[1] - initial[0]), initial[0] + x1 / pointer.width * (initial[1] - initial[0]), initial[3] - y1 / pointer.height * (initial[3] - initial[2]), initial[3] - y0 / pointer.height * (initial[3] - initial[2])];
        tryVerify(() => [layer.xMin, layer.xMax, layer.yMin, layer.yMax].every((value, i) => Math.abs(value - expected[i]) < 1e-6 * Math.max(1, Math.abs(expected[i]))), 2000, "Box zoom must use both independently mapped coordinate intervals as the pattern chart does");
        mouseClick(pan, pan.width / 2, pan.height / 2);
        tryVerify(() => pan.checked && !zoom.checked, 2000, "Selecting move must enable pan and turn box zoom off");
        compare(Preferences.chartPointerMode, "pan", "The single-crystal move button must write the shared remembered chart pointer mode");
        const span = layer.xMax - layer.xMin;
        const left = layer.xMin, bottom = layer.yMin, top = layer.yMax;
        const from = Math.round(pointer.width * .45), to = Math.round(pointer.width * .58);
        mousePress(pointer, from, pointer.height / 2, Qt.LeftButton, Qt.NoModifier, 20);
        try {
            mouseMove(pointer, to, pointer.height / 2, 20);
            verify(!box.visible, "Moving the plot must not display the box-zoom selection rectangle");
        } finally {
            mouseRelease(pointer, to, pointer.height / 2, Qt.LeftButton, Qt.NoModifier, 20);
        }
        const shift = (to - from) / pointer.width * span;
        tryVerify(() => Math.abs(layer.xMin - (left - shift)) < 1e-6 * Math.max(1, span) && Math.abs((layer.xMax - layer.xMin) - span) < 1e-6 * Math.max(1, span), 2000, "A rightward move must translate the x interval left by its independent pointer-distance conversion without zooming");
        verify(Math.abs(layer.yMin - bottom) < 1e-6 && Math.abs(layer.yMax - top) < 1e-6, "A horizontal move must retain the selected y interval as on the pattern chart");
        mouseClick(reset, reset.width / 2, reset.height / 2);
        tryVerify(() => [layer.xMin, layer.xMax, layer.yMin, layer.yMax].every((value, i) => Math.abs(value - initial[i]) < 1e-6), 2000, "Reset must restore the full single-crystal axes after box zoom and move");
        verify(Session.openProject(Probe.referenceUrl("powder")), "The pointer-mode parity control must open the unchanged powder project");
        Ui.click(test, Probe, appWindow, "appBar.tab." + data.page);
        const pattern = Review.find(Ui.page(appWindow), "chart");
        const patternPan = Review.find(pattern, "chart.toolbar.pan"), patternZoom = Review.find(pattern, "chart.toolbar.zoom");
        verify(patternPan !== null && patternZoom !== null && patternPan.checked && !patternZoom.checked, "The pattern chart must restore the move mode selected on the single-crystal chart");
        mouseClick(patternZoom, patternZoom.width / 2, patternZoom.height / 2);
        compare(Preferences.chartPointerMode, "zoom", "The pattern chart's zoom button must update the same saved pointer setting");
        const reopened = openSingle(data);
        verify(toolbarControl(reopened, "zoom").checked && !toolbarControl(reopened, "pan").checked, "Reopening single crystal must restore the box-zoom mode selected on the pattern chart");
    }
    function exampleRows(compound) {
        Session.examples.searchText = "";
        Session.examples.filterValue = "";
        return Probe.rows(Session.examples).filter(row => row.exampleId.toLowerCase().includes(compound));
    }
    function openCompoundExample(compound) {
        Ui.click(test, Probe, appWindow, "appBar.tab.home");
        Ui.click(test, Probe, appWindow, "home.start");
        Ui.click(test, Probe, appWindow, "appBar.tab.project");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        expand("group.examples");
        const rows = exampleRows(compound);
        compare(rows.length, 1, "The app example catalogue must offer exactly one fitting exercise per single-crystal compound");
        const expected = compound === "tb2ti2o7" ? "HEiDi @ MLZ (FRM II)" : "5C2 @ LLB";
        compare(rows[0].origin, expected, "The compound's app example must display the owner-selected instrument and facility label");
        const all = Probe.rows(Session.examples);
        const index = all.findIndex(row => row.exampleId === rows[0].exampleId);
        const list = Review.find(Ui.page(appWindow), "examples.list");
        verify(list !== null, "The actual example catalogue must expose its rendered list");
        list.positionViewAtIndex(index, ListView.Contain);
        list.forceLayout();
        tryVerify(() => list.itemAtIndex(index) !== null, 2000, "The selected compound example must materialize its own real row");
        Ui.scrollIntoView(list.itemAtIndex(index));
        Ui.click(test, Probe, appWindow, "examples.open." + rows[0].exampleId);
        tryVerify(() => Session.hasProject && Session.openedExample === rows[0].exampleId, 3000, "Clicking the compound's real example row must open that fitting exercise");
        tryVerify(() => !Session.project.calculating && Session.project.currentExperiment.singleCrystalReflections.calculatedShown, 10000, "The compound fitting exercise must calculate automatically after it opens");
        return Session.project;
    }
    function test_two_compound_fitting_examples_data() {
        let cases = [];
        for (const compound of ["tb2ti2o7", "pr2nio4"])
            for (const dark of [false, true])
                cases.push({
                    tag: compound + "-" + (dark ? "dark" : "light"),
                    compound: compound,
                    dark: dark
                });
        return cases;
    }
    function test_two_compound_fitting_examples(data) {
        Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
        const project = openCompoundExample(data.compound);
        const experiment = project.currentExperiment;
        const oracle = JSON.parse(Probe.readReferenceFile("example-fits.json")).cases[data.compound];
        verify(data.compound !== "pr2nio4" || ["5c2", "llb_5c2"].includes(experiment.name), "The Pr2NiO4 experiment datablock must be named for its 5C2 instrument");
        const tensors = Probe.rows(project.currentStructure.atomSiteAdps);
        verify(tensors.length > 0 && tensors.every(row => ["beta", "Uani", "Bani"].includes(row.adpType)), "Each single-crystal fitting exercise must start with anisotropic ADPs on its atom sites");
        for (const tensor of tensors) {
            const cell = project.currentStructure.cell;
            verify([cell.angleAlpha.value, cell.angleBeta.value, cell.angleGamma.value].every(value => Math.abs(value - 90) < 1e-10), "The orthogonal FullProf example cells must retain the metric used by the independent beta-to-U conversion");
            const lengths = [cell.lengthA.value, cell.lengthB.value, cell.lengthC.value];
            const u = ["11", "22", "33", "12", "13", "23"].map((component, i) => {
                const value = tensor["ani" + component].value;
                const a = Number(component[0]) - 1, b = Number(component[1]) - 1;
                return tensor.adpType === "Uani" ? value : tensor.adpType === "Bani" ? value / (8 * Math.PI * Math.PI) : value * lengths[a] * lengths[b] / (2 * Math.PI * Math.PI);
            });
            verify(u.slice(0, 3).every(value => Number.isFinite(value) && value > 0), "Initial anisotropic tensors must represent positive isotropic-equivalent displacements");
            const fittedDiagonal = oracle.parameters.filter(item => item.atom === tensor.label && item.kind === "beta" && ["11", "22", "33"].includes(item.component));
            verify(fittedDiagonal.every(item => {
                const axis = Number(item.component[0]) - 1;
                return u[axis] < item.value * lengths[axis] * lengths[axis] / (2 * Math.PI * Math.PI);
            }), "Initial isotropic-equivalent displacements must be smaller than the independent FullProf fitted diagonals");
            verify(Math.max(...u.slice(0, 3)) - Math.min(...u.slice(0, 3)) < 1e-10 && u.slice(3).every(value => Math.abs(value) < 1e-12), "Initial anisotropic tensors must be isotropic-equivalent in Cartesian U, including non-cubic cells");
        }
        const extinction = Probe.rows(experiment.extinction).map(row => row.parameter);
        verify(extinction.length === 2 && extinction.some(item => item.value === 0) && extinction.some(item => item.free), "The fitting exercise must start one extinction parameter at zero and leave an extinction parameter free");
        const parameters = Probe.rows(project.parameters);
        verify(parameters.some(row => row.category === "atom_site_aniso" && row.free) && parameters.some(row => row.category === "atom_site" && row.name.startsWith("fract_") && row.free), "The compound exercise must leave independent displacement and coordinate parameters free");
        verify(oracle.parameters.some(item => item.kind === "coordinate") && oracle.parameters.some(item => item.kind === "beta"), "The independent FullProf oracle must include fitted coordinates and anisotropic tensors with uncertainties");
        const atoms = Probe.rows(project.currentStructure.atomSites);
        verify(oracle.parameters.filter(item => item.kind === "coordinate").some(item => Math.abs(atoms.find(atom => atom.label === item.atom)["fract" + item.component.toUpperCase()].value - item.value) > item.su), "The app example's initial coordinates must be perturbed beyond the independent FullProf uncertainty");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        const start = Ui.find(Ui.page(appWindow), "fitting.start", true);
        verify(start !== null && start.enabled, "The loaded compound exercise must enable the real Start fitting action");
        Ui.scrollIntoView(start);
        verify(waitForPolish(appWindow.contentItem), "The compound fit action must finish layout before input");
        const point = Ui.clickPoint(start);
        verify(point !== null, "The compound's real fit action must be in the visible sidebar");
        mouseClick(start, point.x, point.y);
        const dialog = findChild(appWindow, "fit.results");
        tryVerify(() => dialog !== null && dialog.opened && !project.fit.running, 30000, "The compound's normal app fit must finish and display results");
        const fittedAtoms = Probe.rows(project.currentStructure.atomSites);
        const fittedTensors = Probe.rows(project.currentStructure.atomSiteAdps);
        for (const target of oracle.parameters) {
            let value;
            if (target.kind === "scale")
                value = experiment.scale.value;
            else if (target.kind === "coordinate")
                value = fittedAtoms.find(atom => atom.label === target.atom)["fract" + target.component.toUpperCase()].value;
            else {
                const tensor = fittedTensors.find(row => row.label === target.atom);
                value = tensor["ani" + target.component].value;
                const cell = project.currentStructure.cell;
                const lengths = [cell.lengthA.value, cell.lengthB.value, cell.lengthC.value];
                const a = Number(target.component[0]) - 1, b = Number(target.component[1]) - 1;
                if (tensor.adpType === "Uani")
                    value *= 2 * Math.PI * Math.PI / (lengths[a] * lengths[b]);
                else if (tensor.adpType === "Bani")
                    value /= 4 * lengths[a] * lengths[b];
            }
            verify(Number.isFinite(value) && Math.abs(value - target.value) <= target.su + (target.kind === "coordinate" ? 5e-6 : target.kind === "beta" ? 5e-6 : 5e-7 * oracle.scale_factor), "The compound app fit must reach each independent FullProf coordinate, ADP and scale value within its printed uncertainty; atom=" + (target.atom || "scale") + ", component=" + (target.component || "") + ", actual=" + value + ", expected=" + target.value + ", su=" + target.su);
        }
    }
    function chooseTypeToken(name, token) {
        const box = Ui.find(Ui.page(appWindow), name, true);
        verify(box !== null && box.enabled, "An experiment without loaded data must expose an enabled type selector");
        Ui.scrollIntoView(box);
        verify(waitForPolish(appWindow.contentItem), "The type selector must finish layout before real input");
        const index = box.permittedValues.indexOf(token);
        verify(index >= 0, "The type selector must offer the requested supported token");
        mouseClick(box, box.width / 2, box.height / 2);
        tryCompare(box.popup, "opened", true, 2000, "A real pointer click must open the experiment type choices");
        const list = box.popup.contentItem;
        list.positionViewAtIndex(index, ListView.Contain);
        const item = list.itemAtIndex(index);
        verify(item !== null && item.enabled, "The actual popup must render the requested experiment type choice");
        mouseClick(item, item.width / 2, item.height / 2);
    }
    function test_create_single_crystal_then_load_reflections_data() {
        let cases = [];
        for (const extension of ["int", "dat"])
            for (const dark of [false, true])
                cases.push({
                    tag: extension + "-" + (dark ? "dark" : "light"),
                    extension: extension,
                    dark: dark,
                    page: "experiment"
                });
        return cases;
    }
    function test_create_single_crystal_then_load_reflections(data) {
        // Existing TOF view gates still require that path independently; this witness selects only working modes.
        const tofOpened = Session.openProject(Probe.referenceUrl("projects/sc-neut-tof_taurine_basic"));
        if (tofOpened)
            tryCompare(Session.project, "calculating", false, 10000, "The TOF capability witness must finish before choosing available beam modes");
        const tofAvailable = tofOpened && Session.project.currentExperiment.singleCrystalReflections.calculatedShown && Session.project.currentExperiment.singleCrystalReflections.count > 0;
        openSingle(data);
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        expand("group.experiments");
        const count = Session.project.experiments.count;
        const create = Ui.find(Ui.page(appWindow), "experiments.create", true);
        verify(create !== null && create.enabled, "The actual Experiment sidebar must expose Create experiment");
        Ui.scrollIntoView(create);
        Ui.click(test, Probe, appWindow, "experiments.create");
        tryCompare(Session.project.experiments, "count", count + 1, 2000, "Clicking Create experiment must add a real empty experiment");
        const form = Ui.find(Ui.page(appWindow), "experimentType.sampleForm", true);
        verify(form !== null && form.enabled, "A newly created experiment must allow powder or single crystal before its data are loaded");
        compare(JSON.stringify(Array.from(form.permittedValues).sort()), JSON.stringify(["powder", "single crystal"]), "The pre-data sample-form selector must offer both implemented sample forms");
        chooseTypeToken("experimentType.sampleForm", "single crystal");
        tryCompare(Session.project.currentExperiment, "sampleFormToken", "single crystal", 2000, "Choosing single crystal through the real popup must replace the created experiment's type");
        let groups = [];
        for (const tab of ["basic", "extras"]) {
            Ui.click(test, Probe, appWindow, "sideBar.tab." + tab);
            tryVerify(() => Ui.groupNames(Ui.page(appWindow)).length > 0, 2000, "The selected sidebar tier must finish loading its type-specific groups");
            groups = groups.concat(Ui.groupNames(Ui.page(appWindow)));
        }
        verify(groups.includes("extinction") && groups.includes("refln"), "Choosing single crystal before data must expose extinction and reflection categories");
        verify(["background", "peak", "peak_profile", "excluded_region", "excluded_regions"].every(name => !groups.includes(name)), "A created single crystal must omit all powder-only categories before data loading");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        const probe = Ui.find(Ui.page(appWindow), "experimentType.radiationProbe", true);
        const beam = Ui.find(Ui.page(appWindow), "experimentType.beamMode", true);
        verify(probe !== null && !probe.enabled && probe.value === "neutron", "Single crystal must fix the probe to neutron and disable the unavailable X-ray choice");
        const expectedModes = tofAvailable ? ["constant wavelength", "time-of-flight"] : ["constant wavelength"];
        compare(JSON.stringify(Array.from(beam.permittedValues)), JSON.stringify(expectedModes), "The single-crystal beam selector must offer only independently working beam modes");
        compare(beam.enabled, expectedModes.length > 1, "The beam selector must be disabled exactly while only one single-crystal mode works");
        Ui.scrollIntoView(probe.parent);
        mouseMove(probe.parent, probe.parent.width / 2, probe.parent.height / 2);
        tryVerify(() => Probe.objectsWithProperty(probe.parent, "enterAnimationDuration").some(tip => tip.visible && /neutron|single crystal/i.test(tip.text)), 3000, "Hovering the unavailable single-crystal probe must explain its supported choice");
        if (!tofAvailable) {
            Ui.scrollIntoView(beam.parent);
            mouseMove(beam.parent, beam.parent.width / 2, beam.parent.height / 2);
            tryVerify(() => Probe.objectsWithProperty(beam.parent, "enterAnimationDuration").some(tip => tip.visible && /constant wavelength|not.*implement/i.test(tip.text)), 3000, "An unavailable beam-mode choice must explain why it is fixed");
        }
        chooseTypeToken("experimentType.sampleForm", "powder");
        tryCompare(Session.project.currentExperiment, "sampleFormToken", "powder", 2000, "The created experiment must switch back to powder while still empty");
        chooseTypeToken("experimentType.sampleForm", "single crystal");
        tryCompare(Session.project.currentExperiment, "sampleFormToken", "single crystal", 2000, "The final pre-data choice must again be single crystal");
        const index = Session.project.currentExperimentIndex;
        const load = Ui.find(Ui.page(appWindow), "experiments.loadData." + index, true);
        verify(load !== null && load.enabled, "The created single crystal must expose its real Load data action");
        Ui.scrollIntoView(load);
        Ui.click(test, Probe, appWindow, "experiments.loadData." + index);
        const dialog = Probe.objectsWithProperty(appWindow, "selectedFile").find(item => item.visible && /reflection/i.test(item.title));
        verify(dialog !== undefined, "The real Load data action must open the reflection-file chooser");
        verify(dialog.nameFilters.some(filter => filter.includes("*.int") && filter.includes("*.dat")), "The reflection chooser must offer FullProf int and plain reflection dat files");
        dialog.selectedFile = Probe.referenceUrl("fullprof/sc-neut-cwl_tbti_basic/tbti." + data.extension);
        dialog.accept();
        const expected = JSON.parse(Probe.readReferenceFile("fullprof.json")).cases["sc-neut-cwl_tbti_basic"].input_rows;
        tryVerify(() => Session.project.currentExperiment.singleCrystalReflections.count === expected.length, 5000, "Completing the real chooser must load every reflection into the created single crystal");
        const rows = Probe.rows(Session.project.currentExperiment.singleCrystalReflections);
        verify(rows.every((row, i) => row.h === expected[i][0] && row.k === expected[i][1] && row.l === expected[i][2] && row.intensityMeas === expected[i][3] && row.intensityMeasSu === expected[i][4]), "Both reflection file formats must preserve the independent signed indices, measured values and uncertainties");
        const fixedForm = Ui.find(Ui.page(appWindow), "experimentType.sampleForm", true);
        verify(fixedForm !== null && !fixedForm.enabled && fixedForm.value === "single crystal", "Loading reflections must fix the created experiment's sample form");
        verify(!Ui.find(Ui.page(appWindow), "experimentType.radiationProbe", true).enabled && !Ui.find(Ui.page(appWindow), "experimentType.beamMode", true).enabled, "Loaded reflection data must fix the experiment type axes");
    }
    function fittedReport(data) {
        const location = SettingsProof.copyProject(Probe.referenceUrl("projects/sc-neut-cwl_tbti_isotropic-extinction"));
        openSingle({
            dark: data.dark,
            page: "analysis"
        }, location);
        const project = Session.project;
        project.currentExperiment.scale.free = true;
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        const start = Ui.find(Ui.page(appWindow), "fitting.start", true);
        verify(start !== null && start.enabled, "The report witness must fit actual single-crystal reflections through Start fitting");
        Ui.scrollIntoView(start);
        verify(waitForPolish(appWindow.contentItem), "The report witness's fit action must settle before input");
        const point = Ui.clickPoint(start);
        verify(point !== null, "The report witness's fitting button must be in its sidebar viewport");
        mouseClick(start, point.x, point.y);
        const dialog = findChild(appWindow, "fit.results");
        tryVerify(() => dialog !== null && dialog.opened && !project.fit.running, 15000, "The report witness must complete a normal fit before inspecting agreement factors");
        dialog.close();
        Ui.click(test, Probe, appWindow, "appBar.tab.report");
        const preview = Review.find(Ui.page(appWindow), "report.preview");
        verify(preview !== null, "The actual Report workflow must expose its live production preview");
        tryVerify(() => preview.model.experiments && preview.model.experiments.length === 1, 5000, "The report model must contain its fitted single-crystal experiment");
        return {
            location: location,
            project: project,
            preview: preview
        };
    }
    function reportChartValues(model, expected) {
        const experiment = model.experiments[0];
        const crystal = experiment.single_crystal;
        verify(crystal !== undefined && crystal !== null, "The report model must carry a populated single-crystal chart rather than an empty pattern chart");
        compare(crystal.calc.length, expected.length, "The report must carry every calculated reflection point");
        for (let i = 0; i < expected.length; ++i) {
            compare(JSON.stringify([crystal.h[i], crystal.k[i], crystal.l[i]]), JSON.stringify([expected[i].h, expected[i].k, expected[i].l]), "The report chart must preserve each reflection's signed identity");
            compare(crystal.meas[i], expected[i].intensityMeas, "The report chart must use the project's measured reflection values");
            compare(crystal.su[i], expected[i].intensityMeasSu, "The report chart's bars must use the project's own reflection uncertainties");
            compare(crystal.calc[i], expected[i].intensityCalc, "The report chart must use the project's current calculated reflection values");
        }
        verify(!experiment.pattern || experiment.pattern.series.length === 0, "A single-crystal report must not retain an empty powder-series substitute");
        return crystal;
    }
    function savedReportFiles(witness) {
        const report = witness.project.report;
        report.embedLibraries = true;
        report.writesHtml = true;
        report.writesPdf = true;
        report.setIncluded("charts", true);
        const action = Ui.find(Ui.page(appWindow), "report.save", true);
        verify(action !== null && action.enabled, "The report workflow must expose its actual Save report action");
        Ui.scrollIntoView(action);
        Ui.click(test, Probe, appWindow, "report.save");
        tryVerify(() => report.savedReports.some(row => row.format === "html" && row.state === "current") && report.savedReports.some(row => row.format === "pdf" && row.state === "current"), 30000, "The actual export action must publish both HTML and PDF for the fitted single crystal");
        return {
            html: SettingsProof.childUrl(witness.location, "reports/" + report.savedReports.find(row => row.format === "html").name),
            pdf: SettingsProof.childUrl(witness.location, "reports/" + report.savedReports.find(row => row.format === "pdf").name)
        };
    }
    function reportReflectionTable(model, expected) {
        const category = model.experiments[0].categories.find(category => category.id === "refln");
        verify(category !== undefined, "The single-crystal report must include a reflections category after its chart");
        const table = category.table;
        compare(JSON.stringify(table.columns.slice(0, 3)), JSON.stringify(["h", "k", "l"]), "The report reflection table must keep the three signed indices in separate columns");
        verify(table.columns.length === 7 && /F².*meas/.test(table.columns[3]) && /s.u./.test(table.columns[4]) && /F².*calc/.test(table.columns[5]) && /meas.*calc.*s.u./.test(table.columns[6]), "The report reflection columns must contain measured F-squared, uncertainty, calculated F-squared and normalised residual");
        compare(table.rows.length, expected.length, "The report reflection table must have exactly one row for every project reflection");
        for (let i = 0; i < expected.length; ++i) {
            const row = table.rows[i], reflection = expected[i];
            compare(JSON.stringify(row.slice(0, 3).map(Number)), JSON.stringify([reflection.h, reflection.k, reflection.l]), "The report table must retain the signed reflection identity and input order");
            const numbers = [reflection.intensityMeas, reflection.intensityMeasSu, reflection.intensityCalc];
            for (let j = 0; j < numbers.length; ++j) {
                const sixDigits = Number(numbers[j].toPrecision(6));
                verify(Math.abs(Number(row[j + 3]) - sixDigits) <= Math.max(1e-12, Math.abs(sixDigits) * 1e-12), "Report reflection values must follow the app's six-significant-digit number rule independently of the report formatter");
            }
            compare(row[6], ((reflection.intensityMeas - reflection.intensityCalc) / reflection.intensityMeasSu).toFixed(2), "The report's normalised residual must use an independent measured-minus-calculated-over-uncertainty formula");
        }
        return table;
    }
    function test_single_crystal_report_reflection_list_data() {
        return test_single_crystal_report_chart_and_outputs_data();
    }
    function test_single_crystal_report_reflection_list(data) {
        const witness = fittedReport(data);
        const expected = Probe.rows(witness.project.currentExperiment.singleCrystalReflections);
        const table = reportReflectionTable(witness.preview.model, expected);
        verify(expected.length > 100, "The reflection-list witness must exercise a long table rather than a one-page list");
        const actual = Probe.objectsWithProperty(witness.preview, "columns").find(item => item.columns && item.columns.length === 7 && item.columns[0] === "h" && item.rows && item.rows.length === expected.length);
        verify(actual !== undefined, "The live Report page must render the reflection model with its production report table");
        Ui.scrollIntoView(actual);
        verify(waitForPolish(actual) && waitForRendering(actual), "The reflection report table must settle in the live viewport");
        const list = Render.descendants(actual).find(item => typeof item.positionViewAtIndex === "function" && item.count === expected.length);
        verify(list !== undefined, "A long report reflection table must expose its real scrolling row view");
        for (const index of [0, Math.floor(expected.length / 2), expected.length - 1]) {
            list.positionViewAtIndex(index, ListView.Contain);
            tryVerify(() => list.itemAtIndex(index) !== null, 2000, "Scrolling the report must instantiate each sampled reflection row including the last");
            const item = list.itemAtIndex(index);
            const labels = Render.texts(item).map(label => label.text).join("").replace(/\s/g, "");
            compare(labels, table.rows[index].join("").replace(/\s/g, ""), "The first, middle and last report rows must render all seven complete reflection values");
        }
        const chart = Review.find(witness.preview, "report.singleCrystal");
        verify(chart !== null && actual.mapToItem(witness.preview, 0, 0).y > chart.mapToItem(witness.preview, 0, chart.height).y, "The rendered report reflection table must follow its single-crystal chart");
        witness.project.report.setIncluded("reflections", true);
        const files = savedReportFiles(witness);
        const savedTable = reportReflectionTable(SettingsProof.htmlModel(files.html), expected);
        const html = SettingsProof.htmlEvolutionFacts(files.html);
        verify(!html.error && html.wide.ready && html.narrow.ready, "The reflection-list HTML must render in the actual browser at both viewports");
        for (const view of [html.wide, html.narrow]) {
            const rendered = view.tables.find(candidate => candidate.columns.length === 7 && candidate.columns[0] === "h" && candidate.columns[1] === "k");
            verify(rendered !== undefined, "The actual saved HTML DOM must contain the seven-column reflection table");
            compare(JSON.stringify(rendered.columns), JSON.stringify(savedTable.columns), "The saved HTML must render every reflection column header");
            compare(JSON.stringify(rendered.rows), JSON.stringify(savedTable.rows), "The actual saved HTML must render every reflection row without truncation or omission");
        }
        const pdf = SettingsProof.pdfFacts(files.pdf);
        verify(!pdf.error && pdf.pages.length > 1, "The reflection report must export a parseable multi-page PDF");
        const compact = text => text.replace(/\s/g, "").replace(/−/g, "-");
        const header = compact(table.columns.join(""));
        const rowTexts = table.rows.map(row => compact(row.join("")));
        const seen = Array(expected.length).fill(0);
        let reflectionPages = 0;
        for (const page of pdf.pages) {
            const lines = page.lines.map(line => ({
                        text: compact(line.text),
                        y: line.y
                    }));
            const rows = lines.filter(line => rowTexts.includes(line.text));
            if (rows.length === 0)
                continue;
            ++reflectionPages;
            const heading = lines.find(line => line.text === header);
            verify(heading !== undefined && rows.every(row => row.y > heading.y), "Every PDF page carrying reflection rows must repeat the complete header above them");
            for (const row of rows)
                ++seen[rowTexts.indexOf(row.text)];
        }
        verify(reflectionPages >= 2, "The long single-crystal reflection list must continue across multiple PDF pages");
        verify(seen.every(count => count === 1), "The exported PDF must render every complete reflection row exactly once across its pages");
    }
    function test_single_crystal_report_chart_and_outputs_data() {
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
    function test_single_crystal_report_chart_and_outputs(data) {
        const witness = fittedReport(data);
        const expected = Probe.rows(witness.project.currentExperiment.singleCrystalReflections);
        const model = witness.preview.model;
        const crystal = reportChartValues(model, expected);
        const categories = model.experiments[0].categories;
        const rows = categories.reduce((all, category) => all.concat(category.rows || []), []);
        verify(rows.some(row => /wavelength|λ/i.test(row.label)), "The single-crystal report must list its wavelength");
        verify(rows.some(row => /extinction|model/i.test(row.label) && /gauss|lorentz|becker/i.test(row.text)), "The single-crystal report must list its extinction model");
        verify(rows.some(row => /radius/i.test(row.label)) && rows.some(row => /mosaicity/i.test(row.label)), "The single-crystal report must list the descriptive extinction values");
        verify(rows.some(row => /reflection/i.test(row.label) && Number(row.text) === expected.length), "The single-crystal report must state the actual reflection count");
        const fitRows = model.analysis_categories.reduce((all, category) => all.concat(category.rows || []), []);
        const rRow = fitRows.find(row => /R\(F²\)/.test(row.label) && !/wR\(F²\)/.test(row.label));
        const wrRow = fitRows.find(row => /wR\(F²\)/.test(row.label));
        verify(rRow !== undefined && wrRow !== undefined && !fitRows.some(row => /Rwp|profile R/i.test(row.label)), "The report must label single-crystal R-F-squared and weighted-R-F-squared agreement factors");
        const r = 100 * expected.reduce((sum, row) => sum + Math.abs(row.intensityMeas - row.intensityCalc), 0) / expected.reduce((sum, row) => sum + Math.abs(row.intensityMeas), 0);
        const wr = 100 * Math.sqrt(expected.reduce((sum, row) => sum + Math.pow((row.intensityMeas - row.intensityCalc) / row.intensityMeasSu, 2), 0) / expected.reduce((sum, row) => sum + Math.pow(row.intensityMeas / row.intensityMeasSu, 2), 0));
        verify(matchesDisplayed(rRow.text, r) && matchesDisplayed(wrRow.text, wr), "The report's agreement percentages must match independent residual formulas");
        const chart = Review.find(witness.preview, "report.singleCrystal");
        verify(chart !== null, "The live Report page must draw its single-crystal chart");
        Ui.scrollIntoView(chart);
        verify(waitForPolish(chart) && waitForRendering(chart), "The report's single-crystal chart must reach a visible rendered frame");
        const layer = Review.find(chart, "singleCrystal.points");
        const points = SettingsProof.points(layer);
        verify(points.length === expected.length && points.every((point, i) => point.x === crystal.calc[i] && point.y === crystal.meas[i]), "The actual report preview must plot every calculated/measured reflection pair");
        const graph = ChartOracle.graph(chart);
        verify(graph !== null && Array.from(graph.seriesList).some(series => {
            const values = ChartOracle.points(series);
            return values.length >= 2 && values[0].x !== values[values.length - 1].x && values.every(point => point.x === point.y);
        }), "The actual report chart must draw a nonzero-length equality diagonal");
        checkErrorBar(chart, layer, JSON.parse(Probe.readReferenceFile("fullprof.json")).cases["sc-neut-cwl_tbti_isotropic-extinction"].input_rows, false);
        const files = savedReportFiles(witness);
        reportChartValues(SettingsProof.htmlModel(files.html), expected);
        const html = SettingsProof.htmlEvolutionFacts(files.html);
        verify(!html.error && html.wide.ready && html.narrow.ready, "The saved single-crystal HTML must render in the actual browser at both viewports");
        for (const view of [html.wide, html.narrow]) {
            verify(view.patterns.length === 1 && view.patterns[0].svgCount > 0, "The saved HTML must draw one populated single-crystal SVG or canvas chart");
            const plot = view.patterns[0];
            const trace = plot.traces.find(trace => trace.mode === "markers" && trace.x.length === expected.length);
            verify(trace !== undefined && trace.x.every((value, i) => value === expected[i].intensityCalc) && trace.y.every((value, i) => value === expected[i].intensityMeas), "Actual HTML plot traces must contain the project's own reflection coordinates");
            verify(trace.error_y && trace.error_y.visible && trace.error_y.array.every((value, i) => value === expected[i].intensityMeasSu), "The saved HTML's rendered plot must carry every measured uncertainty bar");
            verify(plot.traces.some(trace => trace.mode === "lines" && trace.x.length >= 2 && trace.x[0] !== trace.x[trace.x.length - 1] && trace.x.every((value, i) => value === trace.y[i])), "The actual HTML chart must draw the equality diagonal");
            verify(/F².*calc/.test(plot.xTitle) && /F².*meas/.test(plot.yTitle), "The saved HTML chart must label its calculated and measured F-squared axes");
        }
        const pdf = SettingsProof.pdfFacts(files.pdf);
        verify(!pdf.error && pdf.pages.length > 0, "The actual exported PDF must be parseable and contain pages");
        verify(/R\(F²\)/.test(pdf.text) && /wR\(F²\)/.test(pdf.text) && /wavelength|λ/i.test(pdf.text) && /mosaicity|radius/i.test(pdf.text), "The exported PDF must carry the single-crystal fields and agreement factors");
        const colour = model.pattern_styles.find(style => style.key === "meas.0").light;
        const ink = SettingsProof.pdfImageColours(files.pdf, [colour]);
        verify(!ink.error && ink.images >= model.structures.length + 1 && ink.counts[colour] > expected.length, "The PDF must contain a populated reflection figure in addition to its structure figures");
        verify(ink.maxVerticalRun && ink.maxVerticalRun[colour] > Math.ceil(layer.markerSize * 2) + 2, "The PDF reflection image must draw uncertainty bars longer than its doubled-size point markers");
    }
}
