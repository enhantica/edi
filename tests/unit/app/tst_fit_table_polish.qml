import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import PatternPolishAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "E04Review.js" as Review
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "FitTablePolish"
    when: windowShown
    property var appWindow
    property var originalTheme
    Component {
        id: application
        Main {}
    }
    Component {
        id: measure
        FontMetrics {}
    }
    SignalSpy {
        id: currentChanges
        signalName: "currentIndexChanged"
    }
    function init() {
        originalTheme = Style.Colors.theme;
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Fit table acceptance opens the real application window");
        appWindow.width = 1280;
        appWindow.height = 768;
        verify(waitForRendering(appWindow.contentItem), "The real fit-results host renders before input");
    }
    function cleanup() {
        currentChanges.target = null;
        Session.closeProject();
        Style.Colors.theme = originalTheme;
        if (appWindow)
            appWindow.destroy();
        appWindow = null;
    }
    function themes() {
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
    function open(data) {
        Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
        const location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/fit_tables/five"));
        verify(Session.openProject(location), "The independent saved five-bank fit opens: " + Session.lastError);
        tryCompare(Session.project, "calculating", false, 10000, "The saved fit finishes calculating before inspection");
        const dialog = findChild(appWindow, "fit.results");
        verify(dialog !== null, "The production fit-results dialog is present");
        dialog.open();
        tryCompare(dialog, "opened", true, 3000, "The real result dialog opens before inspection");
        verify(waitForPolish(dialog.contentItem), "The fit-result tables finish layout before measuring");
        return dialog;
    }
    function table(dialog, name) {
        const view = Review.find(dialog.contentItem, "fit.results." + name);
        verify(view !== null, "Each requested fit-result table has its rendered production view");
        verify(view.count > 1 && view.itemAtIndex(1) !== null, "The independent fixture materializes distinct rows for pointer and column checks");
        return view;
    }
    function frame() {
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "Each pointer observation reaches a real rendered frame");
    }
    function capture(name) {
        frame();
        const result = PatternProof.capture(appWindow, "fit-polish-" + name);
        verify(result.openGL && result.saved, "Fit-table look checks retain an actual OpenGL capture");
    }
    function test_summary_width_data() {
        return themes();
    }
    function test_summary_width(data) {
        const summary = table(open(data), "list");
        const rows = [summary.headerItem];
        for (let i = 0; i < summary.count; ++i)
            rows.push(summary.itemAtIndex(i));
        const widths = [0, AppSizes.iconOnlyColumnWidth, 0, 0];
        for (const row of rows) {
            const cells = Render.cells(row);
            compare(cells.length, 4, "The compact summary keeps its number, icon, metric and value columns");
            for (const column of [0, 2, 3]) {
                const cell = cells[column];
                const metrics = measure.createObject(test, {
                    font: cell.font
                });
                const text = String(cell.text || "").replace(/<[^>]*>/g, "");
                widths[column] = Math.max(widths[column], Math.ceil(metrics.advanceWidth(text)) + AppSizes.fieldSpacing * 2 + (column === 3 ? Style.Sizes.fontPixelSize : 0));
                metrics.destroy();
                verify(!cell.truncated, "Content-width summary cells keep every metric and value readable");
            }
        }
        const required = widths.reduce((a, b) => a + b, 0) + Style.Sizes.tableColumnSpacing * 3 + summary.rowPadding * 2 + Style.Sizes.borderThickness * 2;
        verify(summary.width <= required + 2, "The summary is no wider than its measured text, icon and ordinary table padding require; actual=" + summary.width + ", required=" + required);
        capture("summary-width-" + data.tag);
    }
    function test_structure_colours_data() {
        return themes();
    }
    function test_structure_colours(data) {
        const agreement = table(open(data), "agreement");
        const colour = String(AppColors.structure(0));
        for (const column of [5, 6]) {
            const label = Review.find(agreement.headerItem, "fit.results.agreement.structure." + column);
            verify(label !== null && label.text === "ncaf", "Both phase-factor columns name their linked structure below the factor");
            const icon = Render.descendants(label.parent).find(item => item.icon === "layer-group");
            verify(icon !== undefined, "Both phase-factor names have the real structure icon beside them");
            compare(String(icon.iconColor), colour, "Each phase-factor icon uses the same structure colour as the chart");
            compare(String(label.color), colour, "Each phase-factor structure name uses the same structure colour as its chart and icon");
        }
        capture("structure-colours-" + data.tag);
    }
    function test_global_columns_data() {
        return themes();
    }
    function test_global_columns(data) {
        const agreement = table(open(data), "agreement");
        compare(agreement.count, 6, "The five-bank witness includes the global row before every dataset row");
        for (let column = 0; column < 7; ++column) {
            const header = Review.find(agreement.headerItem, "fit.results.agreement.header." + column);
            verify(header !== null, "Every agreement factor has its real rendered column header");
            const global = Review.find(agreement.itemAtIndex(0), "fit.results.agreement.value.0." + column);
            verify(global !== null, "The All datasets row retains every factor cell including empty phase cells");
            for (let row = 1; row < agreement.count; ++row) {
                const cell = Review.find(agreement.itemAtIndex(row), "fit.results.agreement.value." + row + "." + column);
                verify(cell !== null, "Every dataset row retains its own cell in each factor column");
                verify(Math.abs(global.mapToItem(agreement, 0, 0).x - cell.mapToItem(agreement, 0, 0).x) <= 1, "All datasets and every dataset share each factor column's left edge");
                verify(Math.abs(global.width - cell.width) <= 1, "All datasets and dataset factor cells share the same column width");
                verify(Math.abs(header.mapToItem(agreement, header.width / 2, 0).x - cell.mapToItem(agreement, cell.width / 2, 0).x) <= 1, "Each dataset factor stays centred below its real column header");
            }
        }
        capture("global-columns-" + data.tag);
    }
    function test_passive_tables_data() {
        const cases = [];
        for (const theme of themes())
            for (const name of ["list", "agreement"])
                for (const action of ["hover", "selection", "click"])
                    cases.push({
                        tag: theme.tag + "-" + name + "-" + action,
                        dark: theme.dark,
                        table: name,
                        action: action
                    });
        return cases;
    }
    function test_passive_tables(data) {
        const dialog = open(data), view = table(dialog, data.table), row = view.itemAtIndex(1);
        mouseMove(appWindow.contentItem, 2, 2);
        frame();
        frame();
        const beforePixel = PatternProof.pixel(appWindow, row, row.width - 7, row.height / 2);
        const beforeRows = JSON.stringify(Probe.rows(view.model));
        const beforeIndex = view.currentIndex;
        currentChanges.target = view;
        verify(currentChanges.valid, "The click witness observes the actual table current-row signal");
        currentChanges.clear();
        if (data.action === "hover") {
            mouseMove(row, row.width / 2, row.height / 2);
            frame();
            frame();
            compare(PatternProof.pixel(appWindow, row, row.width - 7, row.height / 2), beforePixel, "Moving over a read-only fit-result row does not tint or highlight it");
        } else if (data.action === "selection") {
            mouseClick(row, row.width / 2, row.height / 2, Qt.LeftButton, Qt.ControlModifier);
            frame();
            compare(view.selectedIndexes.length, 0, "Pointer selection leaves both read-only fit-result tables unselected");
            compare(PatternProof.pixel(appWindow, row, row.width - 7, row.height / 2), beforePixel, "Selecting a fit-result row never draws a selected-row background");
        } else {
            mouseClick(row, row.width / 2, row.height / 2);
            frame();
            compare(view.currentIndex, beforeIndex, "Clicking a fit-result row does not change its current row");
            compare(currentChanges.count, 0, "Clicking either fit-result table emits no current-row change");
        }
        compare(JSON.stringify(Probe.rows(view.model)), beforeRows, "Hover, selection and clicks preserve every displayed fit-result value");
        verify(dialog.opened, "Table pointer input does not dismiss or activate the fit-results dialog");
        capture(data.tag);
    }
}
