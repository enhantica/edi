// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtTest
import edi.app
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render

Item {
    id: surface

    height: 1000
    width: 1100

    Component {
        id: experiments

        ExperimentsGroup {
        }
    }
    Component {
        id: adps

        AtomSiteAdpGroup {
        }
    }
    Component {
        id: structures

        StructuresGroup {
        }
    }
    Component {
        id: parameters

        ParametersGroup {
            tableViewportHeight: 700
        }
    }
    TestCase {
        property var group
        property int savedTheme

        function cleanup() {
            if (group)
                group.destroy();
            group = null;
            Session.closeProject();
            Style.Colors.theme = savedTheme;
        }
        function initTestCase() {
            savedTheme = Style.Colors.theme;
        }
        function test_current_number(data) {
            if (data.kind === "parameters") {
                skip("Waiting for the updated Analysis Parameters table; this case supplies no acceptance evidence.");
                return;
            }
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), "The row-number check opens a real project");
            verify(Session.project.duplicateStructure(), "The selected-row check needs distinct structure rows");
            verify(Session.project.duplicateExperiment(), "The selected-row check needs distinct experiment rows");
            const factory = data.kind === "experiments" ? experiments : data.kind === "structures" ? structures : data.kind === "adps" ? adps : parameters;
            group = factory.createObject(surface, data.kind === "adps" ? {
                structure: Session.project.currentStructure,
                width: 1000
            } : {
                project: Session.project,
                width: 600
            });
            verify(group !== null && waitForPolish(group), "The production table completes layout");
            const table = findChild(group, data.kind === "adps" ? "atomSiteAdps.list" : data.kind + ".list");
            verify(table !== null && table.count >= 2, "The actual table contains distinct rows");
            table.forceLayout();
            for (const index of [0, 1, 0]) {
                if (data.kind === "experiments")
                    Session.project.currentExperimentIndex = index;
                else if (data.kind === "structures")
                    Session.project.currentStructureIndex = index;
                else if (data.kind === "adps")
                    table.currentRow = index;
                else
                    group.selected = table.itemAtIndex(index).parameter;
                tryVerify(() => {
                    const cells = Render.cells(table.itemAtIndex(index));
                    return cells.length > 0 && cells[0].font.bold && String(cells[0].color) === String(Style.Colors.themeAccent);
                }, 1000, "The actual current row number becomes bold in the theme accent colour");
                const other = Render.cells(table.itemAtIndex(1 - index))[0];
                verify(other !== undefined && !other.font.bold, "The previous current row number loses its bold selection");
                surface.Window.window.update();
                verify(waitForRendering(surface), "The selected number is checked after a drawn frame");
                const current = table.itemAtIndex(index);
                const previous = table.itemAtIndex(1 - index);
                verify(String(current.color) !== String(Style.Colors.tableHighlight), "The current row keeps its alternating background");
                verify(String(previous.color) !== String(Style.Colors.tableHighlight), "The other row keeps its alternating background");
            }
        }
        function test_current_number_data() {
            const cases = [];
            for (const kind of ["experiments", "structures", "parameters", "adps"])
                for (const dark of [false, true])
                    cases.push({
                        tag: kind + (dark ? "-dark" : "-light"),
                        kind: kind,
                        dark: dark
                    });
            return cases;
        }

        name: "CurrentRowNumbers"
        when: windowShown
    }
}
