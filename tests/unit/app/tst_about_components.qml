// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtTest
import edi.app
import EdiAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render

Item {
    id: surface
    width: 1200
    height: 1000

    Component {
        id: factory
        AboutDialog {}
    }
    FontMetrics {
        id: metrics
        font.family: Style.Fonts.fontFamily
        font.pixelSize: Style.Sizes.fontPixelSize
    }
    TestCase {
        name: "AboutComponents"
        when: windowShown
        property var dialog
        property int savedTheme

        function initTestCase() {
            savedTheme = Style.Colors.theme;
        }
        function cleanup() {
            if (dialog)
                dialog.destroy();
            dialog = null;
            Style.Colors.theme = savedTheme;
        }
        function openTable(dark) {
            Style.Colors.theme = dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            dialog = factory.createObject(surface);
            verify(dialog !== null, "The production About dialog must be created");
            dialog.open();
            tryCompare(dialog, "opened", true, 1000, "The About dialog must finish opening");
            const link = findChild(dialog.contentItem, "about.thirdParty");
            verify(link !== null, "The visible third-party licence link must exist");
            mouseClick(link, link.width / 2, link.height / 2);
            const popup = findChild(dialog, "about.thirdPartyPopup");
            verify(popup !== null, "The link must open the real third-party popup");
            tryCompare(popup, "opened", true, 1000, "The third-party popup must finish opening");
            const table = findChild(dialog, "about.components");
            verify(table !== null && table.visible && table.count > 0, "The popup must contain its actual populated table");
            verify(waitForPolish(table), "The actual dependency table must complete layout");
            table.forceLayout();
            return table;
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
        function test_component_list_excludes_development_sources() {
            const table = openTable(false);
            const fixture = JSON.parse(Probe.readFile("tests/fixtures/distribution_licences/production_components.json"));
            const allowed = [];
            for (const group of fixture.groups)
                for (const name of group.components)
                    allowed.push(name.toLowerCase());
            verify(allowed.length > 0, "The independent inclusion witness must not be empty");
            for (let i = 0; i < table.count; ++i) {
                const name = table.sourceModel.get(i).component;
                verify(allowed.indexOf(name.toLowerCase()) >= 0, "The actual app list excludes development tools and design or porting sources: " + name);
            }
        }
        function test_columns_fit_content_data() {
            return themes();
        }
        function test_columns_fit_content(data) {
            const table = openTable(data.dark);
            const header = Render.cells(table.headerItem);
            compare(header.length, 3, "The popup must contain exactly its three stated columns");
            const roles = ["component", "version", "licence"];
            // Independent text metrics, all rows (including virtualised ones), and
            // the shared table padding contract; never table.textColumnWidth().
            const widths = header.map((cell, column) => {
                let widest = metrics.advanceWidth(cell.text);
                for (let i = 0; i < table.count; ++i)
                    widest = Math.max(widest, metrics.advanceWidth(table.sourceModel.get(i)[roles[column]]));
                return Math.ceil(widest) + 2 * AppSizes.fieldSpacing;
            });
            const expected = widths.reduce((sum, width) => sum + width, 0) + 2 * Style.Sizes.tableColumnSpacing + 2 * Style.Sizes.tableColumnSpacing + 2 * Style.Sizes.borderThickness;
            console.info("Measured dependency table", table.width, "content budget", expected, "columns", JSON.stringify(widths));
            verify(Math.abs(table.width - expected) <= 1, "The dependency table width must fit its measured columns and standard padding, without a fixed-width surplus or clipped text");
            for (let i = 0; i < 3; ++i)
                verify(Math.abs(header[i].width - widths[i]) <= 1, "Each dependency column must fit its longest header or value with standard cell margins");
        }
        function test_cells_have_standard_margins_data() {
            return themes();
        }
        function test_cells_have_standard_margins(data) {
            const table = openTable(data.dark);
            const header = Render.cells(table.headerItem);
            compare(header.length, 3, "Margin checks must reach all three actual header cells");
            verify(AppSizes.fieldSpacing > 0, "The shared table-column padding must be positive");
            const violations = [];
            // Scroll through every real delegate instead of examining only row zero.
            for (let i = 0; i < table.count; ++i) {
                table.positionViewAtIndex(i, ListView.Contain);
                table.forceLayout();
                tryVerify(() => table.itemAtIndex(i) !== null, 1000, "Every dependency row must be instantiated for its margin check");
                const row = table.itemAtIndex(i);
                const cells = Render.cells(row);
                compare(cells.length, 3, "Every dependency row must expose all three actual cells");
                for (const cell of header.concat(cells)) {
                    if (cell.leftPadding !== AppSizes.fieldSpacing || cell.rightPadding !== AppSizes.fieldSpacing)
                        violations.push({
                            row: i,
                            text: cell.text,
                            left: cell.leftPadding,
                            right: cell.rightPadding
                        });
                }
            }
            console.info("Checked dependency margins on", table.count, "rows; examples", JSON.stringify(violations.slice(0, 6)));
            compare(violations.length, 0, "Every dependency header and row cell must have both positive insets of the shared table-column padding");
        }
    }
}
