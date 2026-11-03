// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render
import "ExampleProjects.js" as Examples

TestCase {
    id: test
    name: "OnboardingExtraTables"
    when: windowShown
    property var app
    property var restoreWidths: []
    FontMetrics {
        id: metrics
    }
    Component {
        id: application
        Main {}
    }
    function initTestCase() {
        Session.closeProject();
        app = application.createObject(null);
        verify(app !== null, "Extra-table acceptance uses the real app at its default window size");
        verify(Examples.bundled(test, Session, "pd-neut-cwl_lbco-hrpt"), "The independently bundled LBCO example supplies all table content");
        tryVerify(() => {
            for (let n = 0; n < 10 && app.pagesBuilt !== app.pagesWanted; ++n)
                OnboardingProbe.incubate(app);
            return app.pagesBuilt === app.pagesWanted;
        }, 5000, "All real workflow pages are ready for the live Extra-table census");
    }
    function cleanup() {
        for (const entry of restoreWidths)
            if (entry.table)
                entry.table.width = entry.width;
        restoreWidths = [];
    }
    function cleanupTestCase() {
        Session.closeProject();
        if (app)
            app.destroy();
        app = null;
    }
    function tables(pageIndex, inspect) {
        if (pageIndex === AppState.Page.Structure)
            tryCompare(Session.project, "calculating", false, 15000, "LBCO derived structure content is ready before the Extra-table census");
        Ui.click(test, Probe, app, "appBar.tab." + ["home", "project", "structure", "experiment", "analysis", "report"][pageIndex]);
        verify(waitForPolish(app), "The selected workflow page finishes layout before its Extra tab is found");
        const page = Ui.page(app);
        const matches = Probe.objectsWithProperty(page, "objectName").filter(item => item.objectName === "sideBar.tab.extras");
        const tab = matches.length === 1 ? matches[0] : null;
        verify(tab !== null, "Each workflow page has an actual Extra tab to census");
        if (!tab.enabled)
            return [];
        Ui.click(test, Probe, app, "sideBar.tab.extras");
        const groups = Render.descendants(page).filter(item => item.objectName.startsWith("group.") && Ui.inPane(Ui.target(item)));
        // The owner accident starts in Atoms in the cell; all other live groups
        // follow, so this class cannot escape through a new generated table.
        groups.sort((a, b) => Number(b.objectName === "group.expanded_atom_site") - Number(a.objectName === "group.expanded_atom_site"));
        const found = [];
        for (const group of groups) {
            Ui.expandGroup(test, Probe, app, group.objectName);
            Ui.scrollIntoView(group.contentItem);
            tryVerify(() => {
                OnboardingProbe.incubate(app);
                const loaders = Probe.objectsWithProperty(group, "status").filter(item => OnboardingProbe.inheritsType(item, "QQuickLoader") && item.active);
                return loaders.every(item => item.status !== Loader.Loading);
            }, 5000, "On-screen groups finish loading their computed content before the table census");
            verify(waitForPolish(group), "An expanded group's lazy content finishes layout before its tables are enumerated");
            app.update();
            verify(waitForRendering(app.contentItem), "The expanded group is rendered before its live table census");
            for (const item of Render.descendants(group)) {
                if (typeof item.itemAtIndex !== "function" || item.columnWidths === undefined || found.includes(item.objectName))
                    continue;
                Ui.scrollIntoView(item);
                item.forceLayout();
                tryVerify(() => item.headerItem !== null, 2000, "Each on-screen table creates its header before the live census measures it: " + item.objectName);
                // Computed content is released when another group becomes
                // active. Measure now, retaining only its stable name afterwards.
                found.push(item.objectName);
                inspect(item);
            }
        }
        return found;
    }
    function rowCells(table, index) {
        table.positionViewAtIndex(index, ListView.Contain);
        table.forceLayout();
        tryVerify(() => table.itemAtIndex(index) !== null, 2000, "Every data row is materialised before its full cells are measured");
        return Render.cells(table.itemAtIndex(index));
    }
    function natural(cell) {
        const labels = Render.descendants(cell).filter(item => typeof item.text === "string" && item.font && item.color !== undefined);
        let need = 0;
        for (const label of labels) {
            const full = typeof label.written === "string" ? label.written : typeof label.fullText === "string" ? label.fullText : label.text;
            metrics.font = label.font;
            need = Math.max(need, metrics.advanceWidth(full));
            verify(label.truncated !== true && !/…|\.\.\./.test(label.text), "Every Extra-table header and cell shows its complete label without elision");
            verify(label.width - (label.leftPadding || 0) - (label.rightPadding || 0) + 1 >= metrics.advanceWidth(full), "The full header or value fits its painted text viewport");
        }
        return need;
    }
    function test_every_extra_table_sizes_columns_from_content_data() {
        return ["structure", "project", "experiment", "analysis", "report"].map(page => ({
                    tag: page,
                    page: page
                }));
    }
    function test_every_extra_table_sizes_columns_from_content(data) {
        const pageIndex = {
            project: AppState.Page.Project,
            structure: AppState.Page.Structure,
            experiment: AppState.Page.Experiment,
            analysis: AppState.Page.Analysis,
            report: AppState.Page.Report
        }[data.page];
        const found = tables(pageIndex, table => {
            Ui.scrollIntoView(table);
            verify(waitForPolish(table), "Default-width Extra tables finish layout before column measurements");
            const headers = Render.cells(table.headerItem), needs = headers.map(natural);
            verify(headers.length > 0, "Each live table exposes real header cells for independent font measurement");
            let cells = headers;
            for (let row = 0; row < table.count; ++row) {
                cells = rowCells(table, row);
                for (let column = 0; column < cells.length; ++column)
                    needs[column] = Math.max(needs[column] || 0, natural(cells[column]));
            }
            const widths = cells.map(cell => cell.width);
            for (let column = 0; column < widths.length; ++column)
                verify(widths[column] + 1 >= (needs[column] || 0), "Each column fits the larger of its independently measured header and widest cell: " + table.objectName + ":" + column);
            verify(typeof table.fillerIndex === "number" && table.fillerIndex >= 0, "Extra tables declare the filler column that takes spare width");
            const original = table.width, filler = table.fillerIndex;
            restoreWidths.push({
                table: table,
                width: original
            });
            table.width = original + 120;
            verify(waitForPolish(table), "The spare-width witness applies a wider available table viewport");
            const after = table.count ? rowCells(table, table.count - 1) : Render.cells(table.headerItem);
            for (let column = 0; column < widths.length; ++column)
                fuzzyCompare(after[column].width - widths[column], column === filler ? 120 : 0, 1, "All spare width goes to the filler, never to the widest content columns");
            table.width = original;
        });
        if (data.page === "structure")
            verify(found.includes("generated.expanded_atom_site.list"), "The class census reaches the actual Atoms in the cell table");
    }
    function test_numeric_cells_follow_atom_sites_and_cartesian_zero() {
        let numbers = 0, cartesianZeros = 0;
        tables(AppState.Page.Structure, table => {
            for (let row = 0; row < table.count; ++row) {
                for (const root of rowCells(table, row)) {
                    for (const cell of Render.descendants(root)) {
                        if (typeof cell.value !== "number" || typeof cell.text !== "string" || !isFinite(cell.value))
                            continue;
                        ++numbers;
                        // The owner names Atom sites' formatter as the cross-widget
                        // reference. It is not the generated-table formatter under test.
                        const reference = NumberText.parameter(cell.value, 0, 6);
                        if (!/[eE][+-]?\d/.test(reference))
                            verify(!/[eE][+-]?\d/.test(cell.text), "An Extra-table value stays fixed when the Atom sites formatter uses fixed notation");
                        if (/cartn|cartesian/i.test(cell.uid || cell.objectName) && Math.abs(cell.value) < 1e-10) {
                            ++cartesianZeros;
                            compare(cell.text, "0", "Cartesian values within the independent 1e-10 zero tolerance display as 0");
                        }
                    }
                }
            }
        });
        verify(numbers > 0 && cartesianZeros > 0, "LBCO exercises numeric Extra cells and near-zero Cartesian coordinates: numbers=" + numbers + " zeros=" + cartesianZeros);
    }
    function test_scattering_lengths_explains_standard_values_without_overrides() {
        // The saved LBCO example declares no custom overrides. Standard element
        // values must not be materialised as rows in this category.
        Ui.click(test, Probe, app, "appBar.tab.structure");
        Ui.click(test, Probe, app, "sideBar.tab.extras");
        const group = Ui.find(Ui.page(app), "group.scattering_length", true);
        verify(group !== null, "LBCO exposes its custom scattering-length overrides group");
        Ui.expandGroup(test, Probe, app, group.objectName);
        verify(waitForPolish(group), "The expanded overrides group finishes laying out its empty state");
        const lists = Render.descendants(group).filter(item => typeof item.itemAtIndex === "function" && item.count !== undefined);
        for (const list of lists)
            compare(list.count, 0, "A standard-values LBCO project has no custom scattering-length rows");
        const expected = "No custom scattering lengths: the standard values are used.";
        const labels = Render.texts(group).filter(item => item.text === expected);
        compare(labels.length, 1, "The empty custom-overrides group explains standard values with the exact agreed text");
        Ui.scrollIntoView(labels[0]);
        verify(waitForRendering(labels[0]) && Ui.rendered(labels[0]), "The expanded group's standard-values explanation is visibly rendered");
    }
}
