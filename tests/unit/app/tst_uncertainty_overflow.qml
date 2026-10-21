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
    Component {
        id: application
        Main {}
    }
    TextMetrics {
        id: metrics
    }

    function init() {
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
        appWindow.destroy();
        appWindow = null;
        Probe.releaseScratchProjects();
    }
    function open(rule) {
        location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/fit_tables/five"));
        verify(Session.openProject(location), "The saved NCAF five-bank project opens through the actual application loader");
        Session.project.suRule = rule;
        compare(Session.project.suRule, rule, "The live project selects the independently specified standard-uncertainty rule");
        tryCompare(Session.project, "calculating", false, 15000, "The real NCAF calculation settles before numeric cells are observed");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1, 3000, "Analysis reaches the real viewport before inspecting numeric columns");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        table = Ui.find(Ui.page(appWindow), "parameters.list", true);
        verify(table !== null && table.sourceModel !== null, "The real Analysis table exposes its production parameter filter");
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
        compare(parameter.hasUncertainty, found.su !== null, "The numeric reference independently distinguishes present and absent uncertainties");
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
        values[2] = kind === "wide" ? 130 : 55;
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
        open(data.rule);
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
        open(data.rule);
        widths("narrow");
        const rows = Probe.rows(table.sourceModel);
        const index = rows.findIndex(row => row.parameter.blockName === "wish_5_6" && row.parameter.uid === "peak.decay_beta_0");
        verify(index >= 0, "The full-hover control reaches the real fifth-bank beta-zero parameter");
        const ref = reference(rows[index].parameter, data.rule);
        const cell = cellAt(index, data.column);
        verify(ordinaryWidth(cell, ref[data.column + "_text"]) > room(cell), "The hover witness starts with a number whose ordinary text exceeds its column");
        Ui.scrollIntoView(cell);
        const point = Ui.clickPoint(cell);
        verify(point !== null, "The actual narrow numeric cell exposes a real hover target");
        mouseMove(cell, point.x, point.y);
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
}
