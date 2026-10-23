import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiChartReference 1.0
import ReportAcceptance 1.0
import PatternPolishAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "UiInteraction.js" as Ui
import "E04Review.js" as Review
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "PatternPolish"
    when: windowShown
    property var appWindow
    property var chart
    property var reference
    property var originalTheme
    Component {
        id: application
        Main {}
    }
    TextMetrics {
        id: axisText
    }
    function init() {
        originalTheme = Style.Colors.theme;
        Preferences.experimentXAxis = "native";
        Preferences.experimentYScale = "linear";
        Preferences.analysisYScale = "linear";
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Pattern acceptance opens the actual application window");
        appWindow.width = 1280;
        appWindow.height = 768;
        verify(waitForRendering(appWindow.contentItem), "The real app renders before interaction");
    }
    function cleanup() {
        chart = null;
        Session.closeProject();
        Style.Colors.theme = originalTheme;
        if (appWindow)
            appWindow.destroy();
        appWindow = null;
    }
    function open(path) {
        Session.closeProject();
        const location = SettingsProof.copyProject(Probe.repoUrl(path));
        verify(Session.openProject(location), "The independent project opens through the application loader: " + Session.lastError);
        tryCompare(Session.project, "calculating", false, 10000, "The project finishes calculating before its drawing is inspected");
    }
    function page(name) {
        Ui.click(test, Probe, appWindow, "appBar.tab." + name);
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1, 3000, "The selected workflow page reaches the real viewport");
        verify(waitForPolish(appWindow.contentItem, 3000), "The selected page finishes layout before inspection");
    }
    function pattern(kind, name) {
        reference = JSON.parse(Probe.readFile("tests/fixtures/excluded_display/" + (kind === "cw-scan" ? "cw" : kind) + ".json"));
        open("tests/fixtures/excluded_display/" + kind);
        page(name);
        chart = Review.find(Ui.page(appWindow), "chart");
        verify(chart !== null, "Every selected pattern page contains its real chart");
        tryVerify(() => PatternProof.series(chart, "chart.series.calc").some(row => row.points.length > 1), 10000, "The chart publishes a nonempty calculated curve before testing exclusions");
        verify(waitForRendering(chart), "The populated chart reaches a rendered frame");
        capture("initial-" + kind + "-" + name);
    }
    function capture(name) {
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "Look checks wait for the actual rendered frame");
        const result = PatternProof.capture(appWindow, name);
        verify(result.openGL === true, "Look checks must use the real OpenGL renderer rather than the offscreen software path");
        verify(result.saved && result.width > 0 && result.height > 0, "Look checks retain a nonempty OpenGL capture");
    }
    function includedButton() {
        const button = Review.descendants(chart).find(item => item.toolTip === "Show only the included range" && typeof item.checked === "boolean");
        verify(button !== undefined && Ui.exposed(button), "The chart toolbar exposes the included-range toggle with its stated tooltip");
        return button;
    }
    function setIncluded(value) {
        const button = includedButton();
        if (button.checked !== value)
            mouseClick(button, button.width / 2, button.height / 2);
        tryCompare(button, "checked", value, 2000, "Real pointer input changes the included-range toggle");
        verify(waitForRendering(chart), "The chart renders the changed range before inspection");
        return button;
    }
    function inRegion(x) {
        return reference.regions.some(region => x >= region[0] && x <= region[1]);
    }
    function curvesHaveGaps() {
        for (const kind of ["calc", "bkg", "resid"]) {
            const lines = PatternProof.series(chart, "chart.series." + kind);
            verify(lines.length > 0, "Calculated, background and difference series all remain present");
            let finite = 0;
            for (const line of lines) {
                let previous = null;
                for (const point of line.points) {
                    if (!isFinite(point.x) || !isFinite(point.y)) {
                        previous = null;
                        continue;
                    }
                    ++finite;
                    verify(!inRegion(point.x), "Derived curves have no point inside any excluded region");
                    if (previous) {
                        const low = Math.min(previous.x, point.x), high = Math.max(previous.x, point.x);
                        verify(!reference.regions.some(region => Math.max(low, region[0]) < Math.min(high, region[1])), "No finite curve segment bridges an excluded region");
                    }
                    previous = point;
                }
            }
            compare(finite, reference.included.filter(Boolean).length, "Every included derived point is retained while excluded values create genuine gaps");
        }
    }
    function test_curve_gaps_data() {
        const cases = [];
        for (const kind of ["cw", "tof", "cw-scan"])
            for (const name of ["experiment", "analysis"])
                cases.push({
                    tag: kind + "-" + name,
                    kind: kind,
                    page: name
                });
        return cases;
    }
    function test_curve_gaps(data) {
        pattern(data.kind, data.page);
        // This case also runs before the new toggle exists, proving current gaps independently.
        const button = Review.descendants(chart).find(item => item.toolTip === "Show only the included range");
        if (button && button.checked)
            setIncluded(false);
        const axis = ChartOracle.object(chart, "chart.axis.x");
        compare(axis.min, reference.full[0], "Toggle off preserves the first measured point on the x axis");
        compare(axis.max, reference.full[1], "Toggle off preserves the last measured point on the x axis");
        const measured = PatternProof.measured(chart).filter(p => isFinite(p.x) && isFinite(p.y));
        compare(measured.length, reference.x.length, "Toggle off retains every measured point inside and outside exclusions");
        curvesHaveGaps();
        capture("curves-" + data.tag);
    }
    function test_included_range_data() {
        return test_curve_gaps_data();
    }
    function reflectionPoints() {
        const points = [];
        for (const row of PatternProof.series(chart, "chart.series.bragg"))
            for (const point of row.points)
                if (isFinite(point.x) && isFinite(point.y))
                    points.push({
                        x: point.x,
                        y: point.y
                    });
        return points;
    }
    function test_included_range(data) {
        pattern(data.kind, data.page);
        setIncluded(false);
        const originalTicks = reflectionPoints();
        const gapReflection = data.kind === "tof" ? 37 + 5000 * 2 + 2.5 * 4 : 2 * Math.asin(1.54 * Math.sqrt(3) / 8) * 180 / Math.PI + .29;
        verify(inRegion(gapReflection), "The cubic fixture has a closed-form Bragg reflection inside an excluded region");
        verify(originalTicks.length > 0, "Toggle off retains genuine included Bragg ticks");
        verify(originalTicks.every(p => !inRegion(p.x)), "Toggle off hides every reflection tick inside an excluded region");
        const includedReflection = data.kind === "tof" ? 37 + 5000 * Math.sqrt(8) + 2.5 * 8 : 2 * Math.asin(1.54 / 8) * 180 / Math.PI + .29;
        verify(!inRegion(includedReflection), "The independent cubic reflection witness lies in the included range");
        verify(originalTicks.some(p => Math.abs(p.x - includedReflection) < 1e-6), "Toggle off retains the independently predicted included reflection");
        const fullMeasured = PatternProof.measured(chart).filter(p => isFinite(p.x) && isFinite(p.y));
        compare(fullMeasured.length, reference.x.length, "Hiding excluded ticks with toggle off retains every measured point");
        verify(fullMeasured.some(p => inRegion(p.x)), "Measured observations inside exclusions remain visible with toggle off");
        const button = setIncluded(true);
        compare(button.fontIcon, "eraser", "The included-range button uses the Excluded regions eraser icon");
        const legend = Review.find(chart, "chart.toolbar.legend"), hover = Review.find(chart, "chart.toolbar.hover");
        verify(button.parent === legend.parent && button.parent === hover.parent, "The range toggle belongs to the legend and tooltip toolbar group");
        const axis = ChartOracle.object(chart, "chart.axis.x");
        tryCompare(axis, "min", reference.included_range[0], 3000, "Toggle on starts exactly at the independently computed first included point");
        compare(axis.max, reference.included_range[1], "Toggle on ends exactly at the independently computed last included point");
        const measured = PatternProof.measured(chart).filter(p => isFinite(p.x) && isFinite(p.y));
        compare(measured.length, reference.included.filter(Boolean).length, "Toggle on retains every included measured point and removes all excluded ones");
        verify(measured.every(p => !inRegion(p.x)), "Interior excluded regions contain no measured point with the toggle on");
        curvesHaveGaps();
        const ticks = reflectionPoints();
        verify(ticks.length > 0, "Reflection filtering retains genuine included Bragg ticks");
        verify(ticks.every(p => !inRegion(p.x)), "Toggle on hides reflection ticks inside excluded regions");
        compare(ticks.map(p => p.x).sort().join(","), originalTicks.map(p => p.x).sort().join(","), "Both toggle states retain exactly the same included reflection ticks");
        const pointer = Review.find(chart, "chart.pointer");
        mouseDrag(pointer, pointer.width * .2, pointer.height * .2, pointer.width * .3, pointer.height * .4);
        const reset = Review.find(chart, "chart.toolbar.reset");
        mouseClick(reset, reset.width / 2, reset.height / 2);
        tryCompare(axis, "min", reference.included_range[0], 3000, "Reset restores the first included point after a real zoom gesture");
        compare(axis.max, reference.included_range[1], "Reset restores the last included point after a real zoom gesture");
        capture("included-" + data.tag);
    }
    function test_range_setting_survives_a_new_engine() {
        pattern("cw", "experiment");
        setIncluded(true);
        // The actual preference singleton is re-created in a separate QML engine.
        const source = 'import QtQuick; import edi.app; QtObject { property PatternChart chart: PatternChart { width: 900; height: 500; settingsPage: "experiment"; function choice(root) { if (root.toolTip === "Show only the included range") return root.checked; for (const child of root.children || []) { const found = choice(child); if (found !== undefined) return found; } return undefined; } } property var included: chart.choice(chart) }';
        const restarted = SettingsProof.restart(source);
        verify(!restarted.error, "A new app engine can read the persisted included-range preference");
        compare(restarted.included, true, "The included-range choice is remembered across application engines");
        setIncluded(false);
        compare(SettingsProof.restart(source).included, false, "Both toggle states persist rather than only the default or a sticky true value");
    }
    function test_axis_selectors_data() {
        return [
            {
                tag: "cw-experiment",
                kind: "cw",
                page: "experiment"
            },
            {
                tag: "cw-analysis",
                kind: "cw",
                page: "analysis"
            },
            {
                tag: "tof-experiment",
                kind: "tof",
                page: "experiment"
            },
            {
                tag: "tof-analysis",
                kind: "tof",
                page: "analysis"
            }
        ];
    }
    function checkAxisWidth(box, choices, closed) {
        compare(Array.from(box.model), choices, "The axis list retains every independently authored scientific choice");
        axisText.font = box.font;
        let widest = 0;
        for (const text of choices.concat(closed)) {
            axisText.text = text;
            widest = Math.max(widest, axisText.advanceWidth);
        }
        const padding = box.leftPadding + box.rightPadding + box.contentItemLabel.leftPadding + box.contentItemLabel.rightPadding;
        const expected = Math.ceil(widest) + padding;
        verify(Math.abs(box.width - expected) < 0.6, "Each pattern selector fits its own longest authored item with only its padding and arrow");
        verify(box.indicator.visible && box.indicator.width > 0, "The independently sized selector retains its actual dropdown arrow");
        verify(box.rightPadding >= box.indicator.width, "The selector reserves room for its arrow beside the complete text");
    }
    function test_axis_selectors(data) {
        pattern(data.kind, data.page);
        const x = Review.find(chart, "chart.toolbar.xaxis"), y = Review.find(chart, "chart.toolbar.yscale");
        verify(x !== null && y !== null, "Both axis selectors are visible on the selected pattern chart");
        const native = data.kind === "tof" ? "time-of-flight" : "2θ";
        const xChoices = [native, "d-spacing"];
        const xClosed = [data.kind === "tof" ? "x: TOF" : "x: 2θ", "x: d-spacing"];
        const yChoices = ["linear", "square root", "log"];
        const yClosed = ["y: linear", "y: square root", "y: log"];
        checkAxisWidth(x, xChoices, xClosed);
        checkAxisWidth(y, yChoices, yClosed);
        mouseClick(x, x.width / 2, x.height / 2);
        tryCompare(x.popup, "opened", true, 2000, "Real input opens the x-axis selector");
        const option = x.popup.contentItem.itemAtIndex(1);
        verify(option !== null, "The d-spacing menu choice has a real delegate");
        mouseClick(option, option.width / 2, option.height / 2);
        tryCompare(x, "currentIndex", 1, 2000, "The actual menu action selects d-spacing");
        verify(Render.texts(x).some(item => item.text === "x: d-spacing"), "The native closed selector renderer reads x: d-spacing");
        checkAxisWidth(x, xChoices, xClosed);
        checkAxisWidth(y, yChoices, yClosed);
        capture("axes-" + data.tag);
    }
    function test_excluded_tint_data() {
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
    function test_excluded_tint(data) {
        Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
        pattern("cw", "experiment");
        const normal = PatternProof.stripe(appWindow, chart, 36.5);
        const excluded = PatternProof.stripe(appWindow, chart, 40.5);
        const distance = Math.max(Math.abs(normal.r - excluded.r), Math.abs(normal.g - excluded.g), Math.abs(normal.b - excluded.b));
        verify(distance > 1 / 255 && distance < .20, "An excluded region is faintly tinted just off the actual chart background in each theme");
        capture("tint-" + data.tag);
    }
    function dialogFor(count) {
        open("tests/fixtures/fit_tables/" + (count === 1 ? "one" : "five"));
        const dialog = findChild(appWindow, "fit.results");
        verify(dialog !== null, "The real fit-results dialog belongs to the application window");
        dialog.open();
        tryCompare(dialog, "opened", true, 3000, "The saved fit record opens the actual result dialog");
        verify(waitForPolish(dialog.contentItem), "Both result tables finish layout before their cells are read");
        capture("initial-fit-" + count);
        return dialog;
    }
    function tables(dialog) {
        return Render.descendants(dialog.contentItem).filter(item => item.visible && item.headerItem && typeof item.count === "number" && typeof item.itemAtIndex === "function");
    }
    function test_global_only_saved_fit_keeps_dataset_data() {
        return [
            {
                tag: "correlated",
                path: "report_options/nontrivial"
            },
            {
                tag: "signed",
                path: "report_storage/signed"
            }
        ];
    }
    function test_global_only_saved_fit_keeps_dataset(data) {
        const fixture = "tests/fixtures/" + data.path;
        verify(!Probe.readFile(fixture + "/analysis/analysis.edi").includes("_fit_result_bank."), "The historical result witness has global fit factors and no bank loop");
        open(fixture);
        const dialog = findChild(appWindow, "fit.results");
        dialog.open();
        tryCompare(dialog, "opened", true, 3000, "The historical global-only result opens the real fit dialog");
        const table = Review.find(dialog.contentItem, "fit.results.agreement");
        verify(table !== null, "The historical result is presented in the agreement table");
        const rows = Probe.rows(table.model);
        compare(rows.length, 1, "A single historical fit retains exactly its dataset row without a duplicate global row");
        compare(rows[0].label, "bank", "A saved fit without bank shares still names its fitted dataset");
        compare(rows[0].place, 0, "The historical dataset retains its experiment icon identity");
        compare(rows[0].values[1], "10.00", "The named historical dataset displays its saved global Rwp as a percentage");
        for (let column = 0; column < rows[0].values.length; ++column)
            if (column !== 1)
                compare(rows[0].values[column], "", "Missing historical profile and phase factors remain empty rather than invented");
        capture("global-only-" + data.tag);
    }
    function test_fit_summary() {
        const dialog = dialogFor(5), views = tables(dialog);
        compare(views.length, 2, "Fit results split the summary and agreement factors into two real tables");
        const summary = views[0];
        compare(summary.count, 4, "The summary contains status, fitting time, iterations and reduced chi-square only");
        const text = Render.texts(summary).map(item => item.text);
        verify(!text.some(value => /minimizer/i.test(value)), "The minimizer is omitted from the fit summary");
        verify(text.includes("Fitting time") && text.includes("1.3 s"), "The fitting time has its stated label and a unit beside the value");
        const last = Render.texts(summary.itemAtIndex(3)).map(item => item.text).join(" ");
        verify(/χ/.test(last), "The summary ends with global reduced chi-square");
        capture("fit-summary");
    }
    function test_fit_agreement_data() {
        return [
            {
                tag: "single",
                count: 1
            },
            {
                tag: "five",
                count: 5
            }
        ];
    }
    function test_fit_agreement(data) {
        const dialog = dialogFor(data.count), views = tables(dialog);
        compare(views.length, 2, "Agreement factors have a separate table below the fit summary");
        const table = views[1];
        const expected = JSON.parse(Probe.readFile("tests/fixtures/fit_tables/reference.json"));
        const rows = data.count === 1 ? expected.banks.slice(0, 1) : [
            {
                name: "All datasets",
                values: expected.global_values
            }
        ].concat(expected.banks);
        compare(table.count, rows.length, "Agreement rows put the global result first and omit its duplicate for a single dataset");
        const headers = Render.texts(table.headerItem).map(item => item.text).filter(text => /^(c?R)/.test(text));
        const factors = ["R<sub>p</sub>", "R<sub>wp</sub>", "R<sub>exp</sub>", "cR<sub>p</sub>", "cR<sub>wp</sub>", "R<sub>Bragg</sub>", "R<sub>F</sub>"];
        compare(headers.join("|"), factors.join("|"), "Agreement columns use the specified factor order and Qt rich-text subscripts");
        verify(!Render.texts(table.headerItem).some(item => /[%χ]/.test(item.text)), "Agreement headers carry neither percent units nor chi-square");
        verify(Render.texts(dialog.contentItem).some(item => /all.*R.*%/i.test(item.text)), "A short line below the agreement table states that all R values are percentages");
        for (let i = 0; i < rows.length; ++i) {
            table.positionViewAtIndex(i, ListView.Contain);
            verify(waitForPolish(table), "Scrolling materializes each actual agreement row");
            const delegate = table.itemAtIndex(i);
            verify(delegate !== null, "Every expected dataset has a materialized agreement row");
            const cells = Render.cells(delegate);
            const nameCell = cells.findIndex(cell => Render.texts(cell).some(text => text.text === rows[i].name) || cell.text === rows[i].name);
            verify(nameCell >= 0, "Each agreement row displays the correct dataset identity");
            const numbers = cells.slice(nameCell + 1).map(cell => {
                const leaf = Render.texts(cell).find(item => /^[-+]?\d/.test(item.text));
                return leaf ? leaf.text : (cell.text || "");
            });
            for (let column = 0; column < 5; ++column)
                compare(numbers[column], (rows[i].values[column] * 100).toFixed(2), "Each profile-factor cell equals the textbook factor independently computed from the saved curves");
            if (rows[i].name === "All datasets")
                verify(numbers.slice(5).every(value => value === ""), "Global phase factors over several datasets are empty rather than invented averages");
            else {
                const bank = expected.banks.findIndex(row => row.name === rows[i].name);
                compare(numbers[5], ((.02 + bank * .01) * 100).toFixed(2), "Each Bragg factor belongs to its own linked structure and experiment record");
                compare(numbers[6], ((.01 + bank * .005) * 100).toFixed(2), "Each structure-amplitude factor belongs to its own linked structure and experiment record");
                verify(Render.descendants(delegate).some(item => item.iconColor && item.icon && String(item.iconColor) === String(AppColors.experiment(bank))), "Each dataset name has its coloured experiment icon");
            }
        }
        verify(Render.texts(table.headerItem).some(item => item.text === "ncaf"), "Phase columns name their linked structure under the factor headers");
        verify(Render.descendants(table.headerItem).some(item => item.iconColor && item.icon && String(item.iconColor) === String(AppColors.structure(0))), "The phase header has its coloured structure icon");
        const popupItem = dialog.contentItem.parent;
        compare(popupItem.height, dialog.height, "The geometry check covers the entire dialog including its header and footer");
        const top = popupItem.mapToItem(appWindow.contentItem, 0, 0);
        verify(top.y >= 0 && top.y + dialog.height <= appWindow.contentItem.height, "The five-dataset dialog stays within the visible application window");
        verify(table.clip, "The agreement table clips its scrolling rows inside the dialog");
        capture("fit-agreement-" + data.tag);
    }
    function test_long_agreement_list_scrolls() {
        const location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/fit_tables/one"));
        const experiment = SettingsProof.text(location, "experiments/wish_1_10.edi");
        const names = ["wish_1_10"];
        for (let i = 1; i < 10; ++i) {
            const name = "extra_bank_" + i;
            names.push(name);
            verify(SettingsProof.write(location, "experiments/" + name + ".edi", experiment.replace(/wish_1_10/g, name)), "The long-list fixture copies a real saved experiment under a distinct identity");
        }
        let analysis = SettingsProof.text(location, "analysis/analysis.edi").replace("_fitting_mode.type single", "_fitting_mode.type joint");
        analysis = analysis.replace(/^wish_1_10 .+$/gm, row => names.map(name => row.replace("wish_1_10", name)).join("\n"));
        analysis += "\nloop_\n_joint_fit.experiment_id\n_joint_fit.weight\n" + names.map(name => name + " 1.0").join("\n") + "\n";
        verify(SettingsProof.write(location, "analysis/analysis.edi", analysis), "The long-list fixture retains each copied bank's saved result and joint-fit membership");
        verify(Session.openProject(location), "The long-list fixture opens through the real project loader: " + Session.lastError);
        tryCompare(Session.project, "calculating", false, 10000, "The long-list project finishes calculating before the dialog is inspected");
        const dialog = findChild(appWindow, "fit.results");
        dialog.open();
        tryCompare(dialog, "opened", true, 3000, "The long-list result dialog opens before scrolling");
        const views = tables(dialog);
        compare(views.length, 2, "Long dataset lists retain both the summary and agreement tables");
        const table = views[1];
        tryCompare(table, "count", names.length + 1, 3000, "Every saved dataset and the global result populate the long agreement table");
        verify(waitForPolish(table), "The long agreement table finishes layout before overflow is measured");
        verify(table.contentHeight > table.height, "The long-list fixture actually overflows the agreement viewport");
        verify(table.clip && table.interactive, "Long dataset lists scroll inside the agreement table");
        table.positionViewAtBeginning();
        const before = table.contentY;
        mouseDrag(table, table.width / 2, table.height * .8, 0, -table.height * .6);
        tryVerify(() => table.contentY > before, 3000, "Real pointer input scrolls the overflowing agreement rows");
        table.positionViewAtIndex(names.length, ListView.Contain);
        verify(waitForPolish(table), "Scrolling to the final dataset materializes its agreement row");
        verify(table.itemAtIndex(names.length) !== null, "The final dataset remains reachable inside the scrolling agreement table");
        capture("fit-agreement-long-list");
    }
    function test_factor_subscripts_in_chart_and_report() {
        open("tests/fixtures/fit_tables/five");
        page("analysis");
        verify(Render.texts(Ui.page(appWindow)).some(item => /R<sub>wp<\/sub>/.test(item.text)), "The dataset line above the chart renders the Rwp subscript through Qt rich text");
        page("report");
        const texts = Render.texts(Ui.page(appWindow));
        verify(texts.some(item => /R<sub>wp<\/sub>/.test(item.text)), "The Report page renders its Rwp label through Qt rich text");
        verify(!texts.some(item => /\b(c?Rwp|c?Rp|R_Bragg|R_F)\b/.test(item.text)), "Report R-factor labels do not retain plain-text factor spellings");
        capture("factor-subscripts");
    }
    function test_report_background_data() {
        return test_excluded_tint_data();
    }
    function test_report_background(data) {
        Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
        open("tests/fixtures/excluded_display/cw");
        page("report");
        const preview = Review.find(Ui.page(appWindow), "report.preview");
        verify(preview !== null, "The Report page exposes its actual main preview");
        Ui.click(test, Probe, appWindow, "sideBar.tab.text");
        tryVerify(() => Review.find(Ui.page(appWindow), "text.view") !== null, 3000, "The actual Text tab opens beside the Report view");
        verify(waitForRendering(appWindow.contentItem), "Both background surfaces reach a rendered OpenGL frame");
        const text = Review.find(Ui.page(appWindow), "text.view");
        tryVerify(() => String(PatternProof.pixel(appWindow, text.parent, text.parent.width - 10, text.parent.height - 20)) === String(Style.Colors.textViewBackground), 3000, "The actual Text tab reaches its final theme background before the look comparison");
        const mainPixel = PatternProof.pixel(appWindow, preview, 8, 8);
        const textPixel = PatternProof.pixel(appWindow, text.parent, text.parent.width - 10, text.parent.height - 20);
        capture("report-background-before-check-" + data.tag);
        compare(mainPixel, textPixel, "The rendered Report main view and Text tab share the same background colour in each theme");
        capture("report-background-" + data.tag);
    }
}
