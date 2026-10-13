// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls as Controls
import QtTest
import edi.app
import EasyApplication.Gui.Style as Style
import EasyApplication.Gui.Elements as Elements
import "RenderedTable.js" as Render
import "../../fixtures/current_row_style/reference.js" as RowStyle

Item {
    id: surface
    width: 1000
    height: 1000
    Component {
        id: experiments
        ExperimentsGroup {}
    }
    Component {
        id: structures
        StructuresGroup {}
    }
    Component {
        id: parameters
        ParametersGroup {
            tableViewportHeight: 700
        }
    }
    Component {
        id: tabReference
        Elements.TabBar {
            width: 240
            Controls.TabButton {
                width: 120
                text: "First"
            }
            Controls.TabButton {
                width: 120
                text: "Second"
            }
        }
    }
    TestCase {
        id: test
        name: "CurrentRowAccent"
        when: windowShown
        property int savedTheme
        property var styleReference: RowStyle.reference
        property string themeKey: "light"
        property var group
        property var table
        function initTestCase() {
            savedTheme = Style.Colors.theme;
        }
        function cleanup() {
            if (group)
                group.destroy();
            group = null;
            table = null;
            Session.closeProject();
            Style.Colors.theme = savedTheme;
        }
        function cases() {
            const rows = [];
            for (const kind of ["experiments", "structures", "parameters"])
                for (const dark of [false, true])
                    rows.push({
                        tag: kind + (dark ? "-dark" : "-light"),
                        kind: kind,
                        dark: dark
                    });
            return rows;
        }
        function prepare(data) {
            themeKey = data.dark ? "dark" : "light";
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), "An independent olivine example supplies real row models");
            verify(Session.project.duplicateStructure(), "The current-row witness supplies multiple structure rows");
            verify(Session.project.duplicateExperiment(), "The current-row witness supplies multiple experiment rows");
            const factory = data.kind === "experiments" ? experiments : data.kind === "structures" ? structures : parameters;
            group = factory.createObject(surface, {
                project: Session.project,
                x: 10,
                y: 10
            });
            verify(group !== null, "The current-row gate instantiates the production sidebar group");
            verify(waitForPolish(group), "The production table completes layout before observing selection");
            table = findChild(group, data.kind + ".list");
            verify(table !== null && table.count >= 2, "Every current-row consumer exposes multiple real rows");
            table.forceLayout();
            select(data.kind, 0);
            mouseMove(surface, surface.width - 5, surface.height - 5);
            verify(waitForRendering(table), "Selection is observed only after a drawn frame");
        }
        function select(kind, index) {
            if (kind === "experiments")
                Session.project.currentExperimentIndex = index;
            else if (kind === "structures")
                Session.project.currentStructureIndex = index;
            else
                group.selected = table.itemAtIndex(index).parameter;
        }
        function bars() {
            return Render.descendants(table).filter(item => item.visible && item.opacity > 0 && item.color && String(item.color) === String(Style.Colors.themeAccent) && item.width === styleReference.width && item.height >= table.tableRowHeight - 0.5);
        }
        function settled(index) {
            const row = table.itemAtIndex(index);
            verify(row !== null, "The selected row exists in the actual table viewport");
            tryVerify(() => bars().length === 1 && Math.abs(bars()[0].mapToItem(table, 0, 0).y - row.mapToItem(table, 0, 0).y) < 0.5, 1500, "Exactly one accent bar follows the current row inside the drawn table");
            const bar = bars()[0];
            const at = bar.mapToItem(row, 0, 0);
            verify(Math.abs(at.x) < 0.5 && Math.abs(at.y) < 0.5, "The accent starts at the selected row's left edge");
            compare(bar.height, row.height, "The accent covers the full logical row height");
            const inTable = bar.mapToItem(table, 0, 0);
            verify(inTable.x >= 0 && inTable.x + bar.width <= table.width, "The accent remains inside the table frame");
            verify(waitForRendering(table), "The settled accent is drawn before its pixels are sampled");
            const image = grabImage(table);
            compare(String(image.pixel(Math.floor(inTable.x + 1), Math.floor(inTable.y + row.height / 2))).toLowerCase(), styleReference.accent[themeKey], "The drawn bar has the theme accent colour, without an obscuring row layer");
        }
        function test_selection_background_and_hover_data() {
            return cases();
        }
        function test_selection_background_and_hover(data) {
            prepare(data);
            for (const index of [0, 1, 0]) {
                select(data.kind, index);
                settled(index);
                for (let i = 0; i < 2; ++i)
                    tryVerify(() => String(table.itemAtIndex(i).color).toLowerCase() === (i % 2 ? styleReference.even[themeKey] : styleReference.odd[themeKey]), 1000, "Current and non-current rows retain the ordinary alternating background");
            }
            const row = table.itemAtIndex(1);
            mouseMove(row, row.width / 2, row.height / 2);
            verify(waitForRendering(table), "The non-current row receives real hover input");
            tryVerify(() => Render.descendants(row).some(item => item.color && String(item.color).toLowerCase() === styleReference.hover[themeKey] && item.width === row.width && item.height === row.height && item.opacity > 0.99), 1500, "The actual non-current row retains the pinned base hover background");
            settled(0);
            compare(data.kind === "parameters" ? group.selected : data.kind === "structures" ? Session.project.currentStructureIndex : Session.project.currentExperimentIndex, data.kind === "parameters" ? table.itemAtIndex(0).parameter : 0, "Hover alone does not change the current row");
            mouseClick(row, 8, row.height / 2, Qt.LeftButton, Qt.NoModifier, table.pressDelay + 1);
            settled(1);
        }
        function test_move_matches_tab_animation_data() {
            return cases();
        }
        function test_move_matches_tab_animation(data) {
            prepare(data);
            settled(0);
            const tabs = createTemporaryObject(tabReference, surface, {
                x: 650,
                y: 10
            });
            verify(tabs !== null && waitForRendering(tabs), "The pinned tab bar supplies the independent animation reference");
            const reference = tabs.contentItem;
            compare(reference.highlightMoveDuration, styleReference.move_duration, "The tab reference uses its declared 250 ms move duration");
            const startY = bars()[0].mapToItem(table, 0, 0).y;
            const distance = table.itemAtIndex(1).mapToItem(table, 0, 0).y - startY;
            const startX = reference.highlightItem.x;
            tabs.currentIndex = 1;
            select(data.kind, 1);
            let intermediate = 0;
            const begun = Date.now();
            while (Date.now() - begun < 450) {
                verify(waitForRendering(table), "Animation comparisons use actual rendered frames");
                verify(bars().length === 1, "The moving accent remains a single visible bar");
                const x = (reference.highlightItem.x - startX) / 120;
                const y = (bars()[0].mapToItem(table, 0, 0).y - startY) / distance;
                if (x > 0.1 && x < 0.9) {
                    verify(Math.abs(x - y) < 0.12, "The row accent follows the tab underline's duration and easing at intermediate frames");
                    intermediate++;
                }
                if (x >= 0.999 && y >= 0.999)
                    break;
            }
            verify(intermediate > 0, "The animation gate reaches movement between the endpoints");
            settled(1);
        }
    }
}
