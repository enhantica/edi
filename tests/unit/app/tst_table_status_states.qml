// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import EasyApplication.Gui.Style as Style
import edi.app
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

Item {
    id: surface
    width: 1100
    height: 900
    ListModel {
        id: supplied
        dynamicRoles: true
        property bool stale: false
        property string calculationError: ""
    }
    Component {
        id: experimentGroup
        ExperimentsGroup {
            width: 950
            collapsed: false
        }
    }
    Component {
        id: measuredGroup
        MeasuredRangeGroup {
            width: 950
        }
    }
    Component {
        id: recentGroup
        RecentProjectsGroup {
            width: 950
        }
    }
    TestCase {
        name: "TableStatusStates"
        when: windowShown
        function init() {
            failOnWarning(/.*/);
            Session.closeProject();
            supplied.clear();
            supplied.stale = false;
            supplied.calculationError = "";
            verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), "The independently named measured example opens");
        }
        function cleanup() {
            Session.closeProject();
        }
        function status(cell, glyph, colour, word, ring) {
            verify(cell !== null, "The state reaches an actual rendered status cell");
            compare(cell.icon, glyph, "The rendered status uses the independently specified state glyph");
            compare(cell.ring, ring === true, "Only the independently declared unfitted state uses a hollow circle");
            compare(String(cell.iconColor).toLowerCase(), String(colour).toLowerCase(), "The status colour changes with its input state");
            verify(String(cell.toolTip).toLowerCase().includes(word.toLowerCase()), "The status tooltip retains the state word");
            const visible = Render.texts(cell);
            verify(!visible.some(item => item.text.toLowerCase().includes(word.toLowerCase())), "Status words stay in tooltips rather than the status column");
            if (glyph !== "") {
                const ink = visible.find(item => item.text === glyph);
                verify(ink !== undefined, "The requested glyph is actually drawn by the cell");
                compare(ink.color, colour, "The actual glyph ink has the state colour");
            } else {
                const circle = Render.descendants(cell).find(item => item.visible && item.radius > 0 && item.border && item.border.width > 0);
                verify(circle !== undefined, "The unfitted hollow circle is actually drawn");
                compare(circle.border.color, colour, "The hollow circle has the neutral status colour");
            }
        }
        function test_fit_outcomes_update_the_existing_cell() {
            supplied.append({
                experiment: Session.project.currentExperiment,
                name: "bank",
                file: "pattern.dat",
                extracted: [],
                isTemplate: false,
                fitOutcome: ""
            });
            const group = createTemporaryObject(experimentGroup, surface, {
                project: Session.project
            });
            const table = Ui.find(group, "experiments.list");
            verify(table !== null, "The real Experiments table consumes the supplied fit states");
            table.sourceModel = supplied;
            verify(waitForPolish(table), "The fit status delegate completes actual layout");
            const cell = Ui.find(group, "experiments.fit.0");
            // ADR-0017's state family predates this task. Do not ask FitOutcomes for expectations.
            const cases = [["", "", Style.Colors.themeForegroundMinor, "Not fitted", true], ["success", "check-circle", Style.Colors.green, "Success", false], ["maxIterations", "exclamation-circle", Style.Colors.orange, "Max iterations", false], ["noStep", "exclamation-circle", Style.Colors.orange, "No step", false], ["notConverged", "exclamation-circle", Style.Colors.orange, "Not converged", false], ["stopped", "stop-circle", Style.Colors.themeForegroundMinor, "Stopped", false], ["superseded", "minus-circle", Style.Colors.themeForegroundMinor, "Superseded", false], ["skipped", "minus-circle", Style.Colors.themeForegroundMinor, "Skipped", false], ["failed", "times-circle", Style.Colors.red, "Failed", false], ["refused", "times-circle", Style.Colors.red, "Refused", false], ["success", "check-circle", Style.Colors.green, "Success", false]];
            for (const expected of cases) {
                supplied.setProperty(0, "fitOutcome", expected[0]);
                verify(waitForPolish(table), "A changed outcome completes status layout");
                compare(Ui.find(group, "experiments.fit.0"), cell, "Fit transitions update the same live cell without recreating the table");
                status(cell, expected[1], expected[2], expected[3], expected[4]);
            }
        }
        function test_calculation_states_update_the_existing_cell() {
            supplied.append({
                x: 12,
                intensityMeas: 8,
                intensityMeasSu: 2,
                intensityCalc: 7,
                dSpacing: 3.4,
                excluded: false,
                calcStatus: "incl"
            });
            const group = createTemporaryObject(measuredGroup, surface, {
                experiment: Session.project.currentExperiment
            });
            const table = Ui.find(group, "data.list");
            verify(table !== null, "The real measured-data table consumes the independent calculation input");
            table.sourceModel = supplied;
            verify(waitForPolish(table), "The measured status delegate completes actual layout");
            const delegate = table.itemAtIndex(0);
            const cells = Render.cells(delegate);
            compare(cells.length, 9, "The measured-data row retains its status column");
            const cell = cells[8];
            const states = [
                {
                    stale: true,
                    error: "",
                    key: "incl",
                    word: "pending",
                    colour: null,
                    glyph: /clock|hourglass|spinner|exclamation|question/
                },
                {
                    stale: false,
                    error: "supplied calculation failure",
                    key: "incl",
                    word: "failed",
                    colour: Style.Colors.red,
                    glyph: /times|exclamation/
                },
                {
                    stale: false,
                    error: "",
                    key: "incl",
                    word: "incl",
                    colour: Style.Colors.green,
                    glyph: /check/
                },
                {
                    stale: false,
                    error: "",
                    key: "excl",
                    word: "excl",
                    colour: Style.Colors.themeForegroundMinor,
                    glyph: /minus|ban/
                },
                {
                    stale: true,
                    error: "",
                    key: "incl",
                    word: "pending",
                    colour: null,
                    glyph: /clock|hourglass|spinner|exclamation|question/
                }
            ];
            for (const state of states) {
                supplied.stale = state.stale;
                supplied.calculationError = state.error;
                supplied.setProperty(0, "calcStatus", state.key);
                verify(waitForPolish(table), "A calculation-state transition completes actual layout");
                compare(Render.cells(table.itemAtIndex(0))[8], cell, "Pending, failed, included and excluded states update the same cell");
                verify(typeof cell.icon === "string" && (state.glyph.test(cell.icon) || (state.word === "pending" && cell.ring)), "Calculation states draw a meaningful nonconstant status glyph");
                if (state.colour !== null)
                    compare(String(cell.iconColor), String(state.colour), "Calculation states have the independently required colour");
                else
                    verify([String(Style.Colors.orange), String(Style.Colors.themeForegroundMinor)].includes(String(cell.iconColor)), "Pending calculation stays neutral or amber rather than masquerading as success or failure");
                verify(String(cell.toolTip).toLowerCase().includes(state.word), "Calculation tooltips retain their corresponding state word");
                const ink = Render.texts(cell).find(item => item.text === cell.icon);
                if (cell.ring) {
                    const circle = Render.descendants(cell).find(item => item.visible && item.radius > 0 && item.border && item.border.width > 0);
                    verify(circle !== undefined, "The pending calculation circle is actually visible");
                    compare(String(circle.border.color), String(cell.iconColor), "The pending ring has the actual neutral status ink");
                } else {
                    verify(ink !== undefined, "The calculation glyph is actually visible");
                    compare(String(ink.color), String(cell.iconColor), "Calculation ink follows the state instead of remaining successful green");
                }
            }
        }
        function test_recent_availability_updates_the_existing_cell() {
            supplied.append({
                name: "supplied project",
                path: "/independent/project",
                available: true
            });
            const group = createTemporaryObject(recentGroup, surface);
            const table = Ui.find(group, "recentProjects.list");
            verify(table !== null, "The real Recent projects table consumes independent availability states");
            table.sourceModel = supplied;
            verify(waitForPolish(table), "The Recent projects delegate completes actual layout");
            const cell = Ui.find(group, "recentProjects.status.0");
            for (const available of [true, false, true]) {
                supplied.setProperty(0, "available", available);
                verify(waitForPolish(table), "Availability changes complete actual layout");
                compare(Ui.find(group, "recentProjects.status.0"), cell, "Availability changes update the existing Recent projects status cell");
                verify(available ? /check/.test(cell.icon) : /exclamation/.test(cell.icon), "Found draws a check and Missing draws a warning");
                verify(String(cell.toolTip).includes(available ? "Found" : "Missing"), "Availability remains named by the corresponding tooltip");
                const colour = available ? Style.Colors.green : Style.Colors.red;
                verify(available ? String(cell.iconColor) === String(colour) : [String(colour), String(Style.Colors.orange)].includes(String(cell.iconColor)), "Found is green and Missing is red or amber");
                const ink = Render.texts(cell).find(item => item.text === cell.icon);
                verify(ink !== undefined, "The availability glyph is actually rendered");
                compare(String(ink.color), String(cell.iconColor), "The actual availability ink uses the specified state colour");
            }
        }
    }
}
