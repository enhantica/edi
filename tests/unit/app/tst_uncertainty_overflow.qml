import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import PatternPolishAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "AnalysisNumericOverflow"
    when: windowShown
    property var appWindow
    property var expected
    property var location
    property var table
    property var originalTheme
    Component {
        id: application
        Main {}
    }
    TextMetrics {
        id: metrics
    }

    function init() {
        originalTheme = Style.Colors.theme;
        Session.closeProject();
        expected = JSON.parse(Probe.readFile("tests/fixtures/uncertainty_display/expected.json"));
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Numeric overflow acceptance hosts the actual application window");
        appWindow.width = 1300;
        appWindow.height = 1000;
        verify(waitForRendering(appWindow.contentItem), "The numeric table window renders before interaction");
    }
    function cleanup() {
        table = null;
        Session.closeProject();
        Style.Colors.theme = originalTheme;
        appWindow.destroy();
        appWindow = null;
        Probe.releaseScratchProjects();
    }
    function showAnalysis() {
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1, 3000, "Analysis reaches the real viewport before inspecting numeric columns");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        table = Ui.find(Ui.page(appWindow), "parameters.list", true);
        verify(table !== null && table.sourceModel !== null, "The real Analysis table exposes its production parameter filter");
    }
    function open(rule, narrowValue = false) {
        location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/fit_tables/five"));
        if (narrowValue) {
            const ref = expected.rules[rule][0];
            const file = "experiments/" + ref.block + ".edi";
            const text = SettingsProof.text(location, file);
            const pattern = new RegExp("^_peak\\." + ref.name + "\\s+\\S+", "m");
            verify(pattern.test(text), "The constructed value seam addresses an existing saved asymmetry parameter");
            verify(SettingsProof.write(location, file, text.replace(pattern, "_peak." + ref.name + " " + expected.narrow_value.token)), "The disposable project receives a decimal whose scientific spelling is shorter");
            expected.rules[rule][0] = Object.assign({}, ref, expected.narrow_value);
        }
        verify(Session.openProject(location), "The saved NCAF five-bank project opens through the actual application loader");
        Session.project.suRule = rule;
        compare(Session.project.suRule, rule, "The live project selects the independently specified standard-uncertainty rule");
        tryCompare(Session.project, "calculating", false, 15000, "The real NCAF calculation settles before numeric cells are observed");
        showAnalysis();
        const picker = Ui.find(Ui.page(appWindow), "parameters.category", true);
        verify(picker !== null, "The actual category selector exposes Peak asymmetry");
        let index = -1;
        for (let i = 0; i < picker.count; ++i)
            if (picker.model[i].key === "@peakAsymmetry")
                index = i;
        verify(index >= 0, "The category menu contains the real Peak asymmetry option");
        Ui.scrollIntoView(picker);
        const point = Ui.clickPoint(picker);
        verify(point !== null, "The Peak asymmetry selector has an actual pointer target");
        mouseClick(picker, point.x, point.y);
        tryVerify(() => picker.popup.visible, 1000, "The real category selector opens its menu");
        const list = picker.popup.contentItem;
        list.positionViewAtIndex(index, ListView.Contain);
        verify(waitForPolish(list), "The Peak asymmetry menu entry finishes layout");
        const entry = list.itemAtIndex(index);
        verify(entry !== null, "The actual Peak asymmetry menu delegate is instantiated");
        mouseClick(entry, entry.width / 2, entry.height / 2);
        tryCompare(table, "count", expected.rules[rule].length, 2000, "All four TOF asymmetry rows from every independently inventoried bank are present");
        compare(table.sourceModel.categoryFilter, "@peakAsymmetry", "Pointer selection applies the actual Peak asymmetry filter");
        verify(waitForPolish(table), "The filtered NCAF table finishes layout before numeric checks");
    }
    function reference(parameter, rule) {
        const found = expected.rules[rule].find(row => row.block === parameter.blockName && "peak." + row.name === parameter.uid);
        verify(found !== undefined, "Every shown TOF asymmetry parameter has an independent saved-decimal reference");
        compare(parameter.value, found.value, "The numeric reference addresses the actual saved parameter value");
        compare(parameter.hasUncertainty && parameter.uncertainty > 0, found.su !== null, "The numeric reference independently distinguishes positive uncertainties from blank uncertainty cells");
        if (found.su !== null)
            fuzzyCompare(parameter.uncertainty, found.su, Math.abs(found.su) * 1e-12, "The observed uncertainty agrees with the independently decoded saved bracket");
        return found;
    }
    function cellAt(index, column) {
        table.positionViewAtIndex(index, ListView.Contain);
        table.forceLayout();
        tryVerify(() => table.itemAtIndex(index) !== null, 2000, "Scrolling materializes the actual requested numeric row");
        const row = table.itemAtIndex(index);
        const cells = Render.cells(row);
        verify(cells.length >= 8, "The actual parameter delegate retains its eight scientific columns");
        const cell = cells[column === "value" ? 2 : 4];
        verify(cell !== null && typeof cell.text === "string", "The requested value or uncertainty column is an actual rendered numeric cell");
        return cell;
    }
    function room(cell) {
        return cell.width - (cell.leftPadding || 0) - (cell.rightPadding || 0);
    }
    function ordinaryWidth(cell, text) {
        metrics.font = cell.font;
        metrics.font.pixelSize = Style.Sizes.fontPixelSize;
        metrics.text = text;
        return metrics.advanceWidth;
    }
    function widths(kind) {
        const values = table.columnWidths.slice();
        // The original saved values can have longer scientific forms. This constructed
        // decimal fits in scientific notation here without sacrificing any digits.
        values[2] = kind === "wide" ? 130 : 4.5 * Style.Sizes.fontPixelSize;
        values[4] = kind === "wide" ? 100 : 42;
        table.columnWidths = values;
        verify(waitForPolish(table), "A real live column-width edit finishes the table layout");
    }
    function checkCells(rule, column, requireOverflow) {
        const rows = Probe.rows(table.sourceModel);
        const failures = [];
        let overflow = 0, fitting = 0;
        rows.forEach((row, index) => {
            const ref = reference(row.parameter, rule);
            const cell = cellAt(index, column);
            const plain = ref[column + "_text"];
            const exceeds = ordinaryWidth(cell, plain) > room(cell) + 0.5;
            if (exceeds)
                overflow++;
            else if (plain !== "")
                fitting++;
            const wanted = exceeds ? ref[column + "_scientific"] : plain;
            if (String(cell.text).replace(/e\+/, "e") !== wanted)
                failures.push(ref.block + "/" + ref.name + ": " + cell.text + " expected " + wanted);
            if (cell.truncated === true || /…|\.\./.test(cell.text) || cell.contentWidth > room(cell) + 0.5)
                failures.push(ref.block + "/" + ref.name + ": numeric glyphs exceed their actual column");
        });
        if (requireOverflow)
            verify(overflow > 0, "The narrow-column control reaches actual ordinary-text overflow rather than an identity layout");
        compare(failures.length, 0, "Every numeric cell fits without elision, preserving all independent rule digits and keeping fitting text unchanged: " + failures.join("; "));
        return {
            overflow: overflow,
            fitting: fitting
        };
    }
    function test_cells_data() {
        const cases = [];
        for (const rule of ["iucr_19", "iucr_99"])
            for (const column of ["value", "su"])
                for (const layout of ["default", "wide", "narrow", "resize"])
                    cases.push({
                        tag: [rule, column, layout].join("-"),
                        rule,
                        column,
                        layout
                    });
        return cases;
    }
    function test_cells(data) {
        open(data.rule, data.column === "value" && (data.layout === "narrow" || data.layout === "resize"));
        if (data.layout === "wide" || data.layout === "resize")
            widths("wide");
        if (data.layout === "resize") {
            const before = cellAt(0, data.column).width;
            const initial = checkCells(data.rule, data.column, false);
            compare(initial.overflow, 0, "The wider initial column displays every ordinary rule text unchanged");
            widths("narrow");
            verify(cellAt(0, data.column).width < before, "The same live numeric column genuinely becomes narrower without rebuilding the project");
        } else if (data.layout === "narrow")
            widths("narrow");
        const result = checkCells(data.rule, data.column, data.layout === "narrow" || data.layout === "resize");
        if (data.layout === "wide") {
            compare(result.overflow, 0, "Ordinary value and uncertainty text is retained whenever the complete text fits");
            verify(result.fitting > 0, "The fit-preserving control includes real nonempty numeric cells");
        }
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "The numeric column reaches a real rendered frame");
        const capture = PatternProof.capture(appWindow, "uncertainty-" + data.tag);
        verify(capture.openGL && capture.saved, "Numeric-column witnesses retain actual OpenGL captures");
    }
    function test_full_hover_data() {
        const cases = [];
        for (const rule of ["iucr_19", "iucr_99"])
            for (const column of ["value", "su"])
                cases.push({
                    tag: rule + "-" + column,
                    rule,
                    column
                });
        return cases;
    }
    function test_full_hover(data) {
        open(data.rule, data.column === "value");
        widths("narrow");
        const rows = Probe.rows(table.sourceModel);
        let cell = null, ref = null;
        for (let index = 0; index < rows.length; ++index) {
            const candidate = reference(rows[index].parameter, data.rule);
            const rendered = cellAt(index, data.column);
            if (candidate[data.column + "_text"] !== "" && ordinaryWidth(rendered, candidate[data.column + "_text"]) > room(rendered)) {
                cell = rendered;
                ref = candidate;
                break;
            }
        }
        verify(cell !== null && ref !== null, "The full-hover witness reaches an actual overflowing saved NCAF number under the current font metrics");
        Ui.scrollIntoView(cell);
        verify(waitForPolish(appWindow.contentItem), "The scrolled numeric hover target completes its actual layout");
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "The numeric hover target reaches a settled rendered frame");
        const point = Ui.clickPoint(cell);
        verify(point !== null, "The actual narrow numeric cell exposes a real hover target");
        mouseMove(cell, point.x, point.y);
        tryCompare(cell, "hovered", true, 2000, "Real pointer input reaches the numeric cell before observing its tooltip");
        const whole = ref[data.column + "_text"];
        const raw = String(data.column === "value" ? ref.value : ref.su);
        tryVerify(() => Probe.visiblePopups(appWindow).some(popup => popup.visible && (popup.text === whole || popup.text === raw)), 3000, "Hovering a compact numeric cell actually shows its complete plain value or standard uncertainty");
    }
    function reportTexts(rule) {
        const actual = Session.project.report.model.parameters;
        verify(actual !== undefined && actual.length > 0, "The actual Report model exposes its scientific parameter text");
        const texts = [];
        for (const ref of expected.rules[rule]) {
            const found = actual.filter(row => row.unique_name.includes(ref.block) && row.unique_name.endsWith("peak." + ref.name));
            compare(found.length, 1, "Each independent bank and asymmetry identity addresses exactly one Report parameter");
            compare(found[0].text, ref.saved, "The Report retains the independent standard-uncertainty rule text without column-dependent notation");
            texts.push(found[0].text);
        }
        return texts;
    }
    function savedTexts(rule) {
        for (const ref of expected.rules[rule]) {
            const text = SettingsProof.text(location, "experiments/" + ref.block + ".edi");
            const token = text.match(new RegExp("^_peak\\." + ref.name + "\\s+(\\S+)", "m"));
            verify(token !== null, "The saved project retains every independently inventoried asymmetry parameter");
            compare(token[1], ref.saved, "Saving retains the s.u. rule's complete decimal text without display-only scientific conversion");
        }
    }
    function test_persisted_and_report_data() {
        return ["iucr_19", "iucr_99"].map(rule => ({
                    tag: rule,
                    rule
                }));
    }
    function test_persisted_and_report(data) {
        open(data.rule);
        verify(Session.save(), "The ordinary NCAF project saves through the actual application writer");
        savedTexts(data.rule);
        const before = reportTexts(data.rule);
        const parameters = JSON.stringify(Probe.rows(table.sourceModel).map(row => [row.parameter.value, row.parameter.uncertainty, row.parameter.free]));
        widths("narrow");
        cellAt(table.count - 1, "su");
        compare(JSON.stringify(Probe.rows(table.sourceModel).map(row => [row.parameter.value, row.parameter.uncertainty, row.parameter.free])), parameters, "Narrowing display columns preserves every stored value, uncertainty and free flag");
        compare(Session.project.modified, false, "A display-only column-width edit does not dirty the saved scientific project");
        compare(reportTexts(data.rule), before, "The Report retains identical rule text after a live numeric-column resize");
        verify(Session.save(), "A project with narrow numeric columns remains saveable through the real application writer");
        savedTexts(data.rule);
    }
    function openLatp(rule) {
        location = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/pd-xray-cwl_latp_scan-4f/project"));
        let text = SettingsProof.text(location, "experiments/latp.edi");
        for (const ref of expected.latp[rule]) {
            const pattern = new RegExp("^" + ref.phase + " (\\S+)$", "m");
            verify(pattern.test(text), "The actual LATP scan declares each of the three linked-structure scales");
            text = text.replace(pattern, ref.phase + " " + ref.token);
        }
        verify(SettingsProof.write(location, "experiments/latp.edi", text), "The LATP scan receives the owner's three value magnitudes and independently authored uncertainty seams");
        verify(Session.openProject(location), "The actual LATP scan with authored scale uncertainties loads through Session");
        Session.project.suRule = rule;
        tryCompare(Session.project, "calculating", false, 15000, "The LATP scan finishes its real initial calculation");
        showAnalysis();
        table.sourceModel.nameFilter = "scale";
        tryCompare(table, "count", expected.latp[rule].length, 2000, "The actual Analysis filter retains exactly the three LATP phase scales");
    }
    function latpReference(parameter, rule) {
        compare(parameter.uid, "linked_structure.scale", "The LATP witness addresses actual linked-structure scale parameters");
        const found = expected.latp[rule].find(ref => ref.phase === parameter.rowLabel);
        verify(found !== undefined, "Every shown LATP scale belongs to its independently named structure");
        fuzzyCompare(parameter.value, found.value, found.value * 1e-12, "The actual LATP scale has the owner-supplied value magnitude");
        fuzzyCompare(parameter.uncertainty, found.su, found.su * 1e-12, "The LATP uncertainty is the authored rounding seam rather than a fitted-output pin");
        return found;
    }
    function test_latp_own_exponent_data() {
        const cases = [];
        for (const rule of ["iucr_19", "iucr_99"])
            for (const layout of ["default", "narrow"])
                cases.push({
                    tag: rule + "-" + layout,
                    rule,
                    layout
                });
        return cases;
    }
    function test_latp_own_exponent(data) {
        openLatp(data.rule);
        if (data.layout === "narrow") {
            const columns = table.columnWidths.slice();
            columns[4] = 42;
            table.columnWidths = columns;
            verify(waitForPolish(table), "The actual LATP uncertainty column finishes its narrower live layout");
        }
        const rows = Probe.rows(table.sourceModel), failures = [];
        let compact = 0;
        rows.forEach((row, index) => {
            const ref = latpReference(row.parameter, data.rule);
            const cell = cellAt(index, "su");
            const exceeds = ordinaryWidth(cell, ref.legacy_su) > room(cell) + 0.5;
            if (exceeds)
                compact++;
            const wanted = exceeds ? ref.su_scientific : ref.legacy_su;
            if (String(cell.text).replace(/e\+/, "e") !== wanted)
                failures.push(ref.phase + ": " + cell.text + " expected " + wanted);
            const value = cellAt(index, "value");
            if (value.text !== ref.value_display)
                failures.push(ref.phase + ": value lost its retained four-digit magnitude notation");
            for (const number of [cell, value])
                if (number.truncated === true || /…|\.\./.test(number.text) || number.contentWidth > room(number) + 0.5)
                    failures.push(ref.phase + ": LATP numeric glyphs exceed their actual column");
        });
        if (data.layout === "narrow")
            verify(compact > 0, "The forced-narrow LATP witness reaches shared-exponent overflow rather than an identity layout");
        compare(failures.length, 0, "Every overflowing LATP uncertainty uses its own shortest exponent with the rule's independent significant digits and no elision: " + failures.join("; "));
    }
    function test_latp_full_hover_data() {
        return ["iucr_19", "iucr_99"].map(rule => ({
                    tag: rule,
                    rule
                }));
    }
    function test_latp_full_hover(data) {
        openLatp(data.rule);
        const rows = Probe.rows(table.sourceModel);
        for (let index = 0; index < rows.length; ++index) {
            const ref = latpReference(rows[index].parameter, data.rule);
            const cell = cellAt(index, "su");
            Ui.scrollIntoView(cell);
            const point = Ui.clickPoint(cell);
            verify(point !== null, "Every actual LATP uncertainty exposes a real hover target");
            mouseMove(cell, point.x, point.y);
            tryVerify(() => Probe.visiblePopups(appWindow).some(popup => popup.visible && (popup.text === ref.full_su || popup.text === String(ref.su))), 3000, "Hovering compact LATP uncertainties exposes their full authored values beyond the rule-rounded mantissa");
            mouseMove(appWindow.contentItem, 1, 1);
        }
    }
    function sidebarContainer() {
        const workflow = Render.descendants(Ui.page(appWindow)).find(item => typeof item.pageName === "string" && typeof item.placeSideBar === "function");
        verify(workflow !== undefined, "The active page contains its real production workflow component");
        const contents = workflow.sideBar;
        verify(contents !== undefined, "Every tested workflow page exposes its actual sidebar content");
        for (let index = 0; index < contents.length; ++index)
            if (contents[index].continueButton !== undefined && contents[index].parent)
                return contents[index].parent;
        fail("Every workflow sidebar has its actual rendered container");
    }
    function alignedSidebar() {
        const sidebar = sidebarContainer();
        const experiment = Ui.control(Probe, appWindow, "appBar.tab.experiment");
        verify(experiment !== null && experiment.visible, "The top bar exposes the actual Experiment button as the sidebar alignment reference");
        const left = sidebar.mapToItem(appWindow.contentItem, 0, 0).x;
        const centre = experiment.mapToItem(appWindow.contentItem, experiment.width / 2, 0).x;
        verify(Math.abs(left - centre) <= 1, "The rendered sidebar left edge coincides with the rendered Experiment button centre within one pixel: " + left + " versus " + centre);
    }
    function test_sidebar_alignment_data() {
        return ["project", "structure", "experiment", "analysis", "report"].map(page => ({
                    tag: page,
                    page
                }));
    }
    function test_sidebar_alignment(data) {
        open("iucr_19");
        Ui.click(test, Probe, appWindow, "appBar.tab." + data.page);
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1, 3000, "Each workflow page enters the real viewport before measuring its sidebar");
        verify(waitForPolish(appWindow.contentItem), "The workflow page completes actual layout before alignment measurement");
        alignedSidebar();
        appWindow.width = 1500;
        verify(waitForPolish(appWindow.contentItem), "A real window resize updates both the top bar and the page layout");
        alignedSidebar();
    }
    function test_free_success_colour_data() {
        return ["Light", "Dark"].map(theme => ({
                    tag: theme,
                    theme
                }));
    }
    function test_free_success_colour(data) {
        Style.Colors.theme = data.theme === "Light" ? Style.Colors.LightTheme : Style.Colors.DarkTheme;
        open("iucr_19");
        verify(SettingsProof.publishScanSummary(Session.project), "An authored successful scan summary reaches the real status bar with a nonzero successful-file count");
        const rows = Probe.rows(table.sourceModel);
        const index = rows.findIndex(row => row.parameter.free && row.parameter.refinable && !row.parameter.outsideRange);
        verify(index >= 0, "The real Analysis table contains a free parameter whose value is not a warning");
        const cell = cellAt(index, "value");
        const outcome = findChild(appWindow, "statusBar.fit.outcome");
        verify(outcome !== null && outcome.visible, "The actual status bar displays its successful outcome");
        const success = Render.texts(outcome).find(item => item.text === "Success");
        const tick = outcome.contentItem.children[0];
        verify(success !== undefined && tick.visible && typeof tick.text === "string", "The Success word and its tick are actual visible rendered text items");
        const values = findChild(appWindow, "statusBar.fit.values");
        verify(values !== null, "The real status bar exposes the scan's rendered counts");
        const ok = Render.descendants(values).find(item => item.visible && item.keyText === "OK");
        verify(ok !== undefined && Number(ok.valueText) > 0, "The successful-file count really displays a nonzero supplied result");
        const check = ok.contentItem.children[0];
        const digits = Render.texts(ok).filter(item => /^\d$/.test(item.text));
        verify(check.visible && digits.length > 0, "The successful-file check and count digits are actually drawn");
        verify(cell.font.bold, "A real free parameter retains its bold value style in each theme");
        const ink = item => String(item.color).toLowerCase();
        const rendered = [tick, success, check].concat(digits);
        tryVerify(() => rendered.every(item => ink(item) === ink(success)), 2000, "The actual Success tick, label and successful-file count settle to the same rendered green");
        tryVerify(() => rendered.every(item => ink(item) === ink(cell)), 2000, "The bold free value shares the rendered Success tick, label and successful-file count colour in " + data.theme + ": free=" + ink(cell) + " status=" + rendered.map(ink).join(","));
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "The shared-green witness reaches a real completed frame");
        const capture = PatternProof.capture(appWindow, "free-success-green-" + data.theme);
        verify(capture.openGL && capture.saved, "Both shared-green themes retain actual OpenGL captures");
    }
}
