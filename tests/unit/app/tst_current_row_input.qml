// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "../../fixtures/current_row_style/reference.js" as RowStyle
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui

Item {
    id: surface
    width: 1200
    height: 1000
    ListModel {
        id: authored
        dynamicRoles: true
    }
    Component {
        id: makeStructuresGroup
        StructuresGroup {}
    }
    Component {
        id: makeAtomSitesGroup
        AtomSitesGroup {}
    }
    Component {
        id: makeAtomSiteAdpGroup
        AtomSiteAdpGroup {}
    }
    Component {
        id: makeScatteringLengthsGroup
        ScatteringLengthsGroup {}
    }
    Component {
        id: makeExperimentsGroup
        ExperimentsGroup {}
    }
    Component {
        id: makeLinkedStructureGroup
        LinkedStructureGroup {}
    }
    Component {
        id: makePreferredOrientationGroup
        PreferredOrientationGroup {}
    }
    Component {
        id: makeBackgroundGroup
        BackgroundGroup {}
    }
    Component {
        id: makeExcludedRegionsGroup
        ExcludedRegionsGroup {}
    }
    Component {
        id: makeMeasuredRangeGroup
        MeasuredRangeGroup {}
    }
    Component {
        id: makeReflectionsGroup
        ReflectionsGroup {}
    }
    Component {
        id: makeParametersGroup
        ParametersGroup {}
    }
    Component {
        id: makeJointFitGroup
        JointFitGroup {}
    }
    Component {
        id: makeAliasesGroup
        AliasesGroup {}
    }
    Component {
        id: makeConstraintsGroup
        ConstraintsGroup {}
    }
    Component {
        id: makeFitStartGroup
        FitStartGroup {}
    }
    Component {
        id: makeSequentialExtractGroup
        SequentialExtractGroup {}
    }
    Component {
        id: makeExamplesGroup
        ExamplesGroup {}
    }
    Component {
        id: makeRecentProjectsGroup
        RecentProjectsGroup {}
    }
    Component {
        id: makeAboutDialog
        AboutDialog {}
    }
    Component {
        id: makeWarningsDialog
        WarningsDialog {}
    }
    Component {
        id: makeFitResultsDialog
        FitResultsDialog {}
    }
    Component {
        id: makeReportTable
        ReportTable {}
    }
    TestCase {
        id: test
        name: "CurrentRowInput"
        when: windowShown
        property var group
        property var table
        property int savedTheme
        property var savedHistory
        function initTestCase() {
            savedTheme = Style.Colors.theme;
            savedHistory = RecentProjects.settings.recent.slice();
            surface.Window.window.width = 1200;
            surface.Window.window.height = 1000;
        }
        function cleanup() {
            if (group) {
                if (typeof group.close === "function")
                    group.close();
                group.destroy();
            }
            group = null;
            table = null;
            Session.closeProject();
            RecentProjects.settings.recent = savedHistory;
            RecentProjects.refresh();
            Style.Colors.theme = savedTheme;
        }
        function definitions() {
            return JSON.parse(SettingsProof.text(Qt.resolvedUrl("../../fixtures/current_row_input/"), "catalogue.json"));
        }
        function factory(type) {
            const factories = ({
                    StructuresGroup: makeStructuresGroup,
                    AtomSitesGroup: makeAtomSitesGroup,
                    AtomSiteAdpGroup: makeAtomSiteAdpGroup,
                    ScatteringLengthsGroup: makeScatteringLengthsGroup,
                    ExperimentsGroup: makeExperimentsGroup,
                    LinkedStructureGroup: makeLinkedStructureGroup,
                    PreferredOrientationGroup: makePreferredOrientationGroup,
                    BackgroundGroup: makeBackgroundGroup,
                    ExcludedRegionsGroup: makeExcludedRegionsGroup,
                    MeasuredRangeGroup: makeMeasuredRangeGroup,
                    ReflectionsGroup: makeReflectionsGroup,
                    ParametersGroup: makeParametersGroup,
                    JointFitGroup: makeJointFitGroup,
                    AliasesGroup: makeAliasesGroup,
                    ConstraintsGroup: makeConstraintsGroup,
                    FitStartGroup: makeFitStartGroup,
                    SequentialExtractGroup: makeSequentialExtractGroup,
                    ExamplesGroup: makeExamplesGroup,
                    RecentProjectsGroup: makeRecentProjectsGroup,
                    AboutDialog: makeAboutDialog,
                    WarningsDialog: makeWarningsDialog,
                    FitResultsDialog: makeFitResultsDialog,
                    ReportTable: makeReportTable
                });
            return factories[type];
        }
        function prepare(data) {
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), "Real input uses a loaded scientific project");
            const project = Session.project, structure = project.currentStructure, experiment = project.currentExperiment;
            if (data.table === "structures.list" || data.table === "linkedStructure.list")
                verify(project.duplicateStructure(), "Selection has distinct real structure identities");
            if (data.table === "experiments.list" || data.table === "jointFit.list")
                verify(project.duplicateExperiment(), "Selection has distinct real experiment identities");
            const seed = data.table === "scatteringLengths.list" ? structure.scatteringLengths : data.table === "excludedRegions.list" ? experiment.excludedRegions : data.table === "aliases.list" ? project.analysis.aliases : data.table === "constraints.list" ? project.analysis.constraints : data.table === "linkedStructure.list" ? experiment.linkedStructures : data.table === "preferredOrientation.list" ? experiment.preferredOrientation : null;
            if (seed) {
                if (data.table === "preferredOrientation.list") {
                    if (!seed.count)
                        seed.append();
                } else
                    for (let i = 0; seed.count < 2 && i < 2; ++i)
                        seed.append();
            }
            if (data.table === "background.terms") {
                experiment.backgroundType = "polynomial";
                experiment.backgroundTerms.append();
                experiment.backgroundTerms.append();
            }
            if (data.table === "recentProjects.list") {
                RecentProjects.settings.recent = ["/missing/selection-first", "/missing/selection-second"];
                RecentProjects.refresh();
            }
            const props = {
                width: 1100
            };
            if (data.owner)
                props[data.owner] = data.owner === "project" ? project : data.owner === "structure" ? structure : data.owner === "experiment" ? experiment : project.analysis;
            if (data.type === "ParametersGroup")
                props.tableViewportHeight = 700;
            if (data.type === "ReportTable") {
                props.height = 240;
                props.columns = ["Name", "Value"];
                props.rows = [["First", "1.25"], ["Second", "7.5"]];
            }
            group = factory(data.type).createObject(surface, props);
            verify(group !== null, "The inventory instantiates each actual production table owner");
            if (typeof group.collapsed === "boolean")
                group.collapsed = false;
            if (typeof group.open === "function")
                group.open();
            if (data.type === "AboutDialog")
                findChild(group, "about.thirdPartyPopup").open();
            verify(waitForPolish(surface), "Every real table completes layout before input");
            table = group.objectName === data.table ? group : findChild(group, data.table);
            if (data.type === "AboutDialog" && !table)
                table = Render.descendants(group.contentItem).find(item => item.sourceModel !== undefined && item.count > 1);
            if (data.type === "ReportTable")
                table = Render.descendants(group).find(item => typeof item.itemAtIndex === "function" && item.count > 1);
            verify(table !== null && table !== undefined, "The closed table inventory reaches its real ListView");
            authored.clear();
            if (["reflections.list", "fitStart.list", "sequentialExtract.list", "warnings.list"].includes(data.table)) {
                // Independently authored read-only rows exercise production delegates and input.
                for (let i = 0; i < 2; ++i)
                    authored.append({
                        id: "row" + i,
                        hkl: "(" + (i + 1) + " 0 1)",
                        fSquaredCalc: 100 + i,
                        indexH: i + 1,
                        indexK: 0,
                        indexL: 1,
                        dSpacing: 2.5 + i,
                        position: 20 + i,
                        intensity: 100 + i,
                        fSquared: 100 + i,
                        startValue: 3.25 + i,
                        startUncertainty: 0.01,
                        target: "diffrn.ambient_temperature",
                        pattern: "TEMP ([0-9.]+)",
                        required: true,
                        text: "Selection warning " + i,
                        message: "Selection warning " + i,
                        kind: "warning",
                        severity: "warning"
                    });
                table.sourceModel = authored;
            }
            if (data.type === "FitResultsDialog") {
                group.close();
                group.destroy();
                group = null;
                const location = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/fit_tables/five"));
                verify(Session.openProject(location), "Passive result rows come from an independent saved fit");
                group = makeFitResultsDialog.createObject(surface);
                group.open();
                verify(waitForPolish(surface), "The saved fit tables lay out before passive input");
                table = findChild(group, data.table);
            }
            verify(table.count > 0, "Each table has actual visible rows; an empty inventory is not evidence");
            table.positionViewAtIndex(0, ListView.Beginning);
            if (typeof group.collapsed === "boolean" && group.titleArea)
                tryVerify(() => Math.abs(group.height - (group.titleArea.height + group.spacing + group.contentHeight + group.bottomPadding)) < 0.5, 1500, "A collapsed production group fully expands before its table receives input");
            table.forceLayout();
            verify(waitForPolish(table), "The first production delegates materialize before the click");
        }
        function click(cell, passive) {
            verify(cell && (cell.enabled || passive), "The real input cell exists and accepts pointer events");
            Ui.scrollIntoView(cell);
            const point = Ui.clickPoint(cell);
            verify(point !== null, "Input stays inside the actual clipped table viewport");
            let delay = 0;
            for (let p = cell.parent; p; p = p.parent)
                if (typeof p.pressDelay === "number")
                    delay = Math.max(delay, p.pressDelay + 1);
            mouseClick(cell, point.x, point.y, Qt.LeftButton, Qt.NoModifier, delay);
        }
        function bars() {
            return Render.descendants(table).filter(item => item.objectName === "currentRowBar" && item.visible && item.opacity > 0);
        }
        function marked(index) {
            tryCompare(table, "markerRow", index, 1500, "Any clicked cell or keyboard move makes exactly its row current");
            table.forceLayout();
            surface.Window.window.update();
            verify(waitForRendering(surface), "Selection is observed after a real rendered frame");
            tryVerify(() => {
                const number = Render.descendants(table.itemAtIndex(index)).find(item => item.marksCurrentRow === true);
                return number && number.font && number.font.bold && String(number.color) === String(Style.Colors.themeAccent);
            }, 1500, "The current row number finishes its colour transition to the exact bold accent");
            for (let i = 0; i < Math.min(table.count, 2); ++i) {
                const row = table.itemAtIndex(i);
                verify(row !== null, "Both independent row witnesses stay materialized");
                const number = Render.descendants(row).find(item => item.marksCurrentRow === true);
                verify(number && number.font, "The actual production row number is observable");
                compare(number.font.bold, i === index, "Exactly the current row number is bold");
                compare(String(number.color) === String(Style.Colors.themeAccent), i === index, "Exactly the current row number uses the accent colour");
            }
            tryVerify(() => bars().length === 1 && Math.abs(bars()[0].mapToItem(table, 0, 0).y - table.itemAtIndex(index).mapToItem(table, 0, 0).y) < 0.5, 1500, "Exactly one visible marker follows the same current row as its bold accent number");
        }
        function rowPixel(index) {
            surface.Window.window.update();
            const row = table.itemAtIndex(index);
            const cells = Render.cells(row);
            const left = cells[0].mapToItem(surface, cells[0].width, 4);
            const right = cells[1].mapToItem(surface, 0, 4);
            const at = {
                x: (left.x + right.x) / 2,
                y: left.y
            };
            return String(grabImage(surface).pixel(Math.round(at.x), Math.round(at.y))).toLowerCase();
        }
        function ordinary(index, data) {
            const theme = data.dark ? "dark" : "light";
            return (index % 2 ? RowStyle.reference.even : RowStyle.reference.odd)[theme];
        }
        function leaveRows() {
            mouseMove(surface, surface.width - 2, surface.height - 2);
            surface.Window.window.update();
            verify(waitForRendering(surface), "The mouse leaves the actual table before its background is observed");
        }
        function noFill(data) {
            leaveRows();
            console.log("ROW_BACKGROUND " + JSON.stringify({
                table: data.table,
                mode: data.mode,
                dark: data.dark,
                rows: [0, Math.min(1, table.count - 1)].map(index => ({
                            index: index,
                            pixel: rowPixel(index),
                            expected: ordinary(index, data),
                            base: String(table.itemAtIndex(index).color)
                        }))
            }));
            for (let index = 0; index < Math.min(2, table.count); ++index)
                tryVerify(() => rowPixel(index) === ordinary(index, data), 1500, "Current, previous and editing rows draw only their independent alternating background when the pointer leaves");
        }
        function test_input_data() {
            const result = [];
            for (const row of definitions()) {
                const modes = row.passive ? ["passive"] : ["readonly", "keyboard", "background", "hover"].concat(row.editable.map(column => "editable" + column)).concat(row.textColumn === null ? [] : ["cursor"]);
                for (const dark of [false, true])
                    for (const mode of modes)
                        result.push(Object.assign({}, row, {
                            tag: row.table + "-" + mode + (dark ? "-dark" : "-light"),
                            dark: dark,
                            mode: mode
                        }));
            }
            return result;
        }
        function test_input(data) {
            prepare(data);
            if (data.passive) {
                for (const index of [0, 1]) {
                    const row = table.itemAtIndex(index);
                    verify(row !== null, "Passive tables expose more than an empty placeholder");
                    const cells = Render.cells(row);
                    const target = data.type === "ReportTable" ? row : cells[0] || Render.texts(row)[0];
                    verify(target !== undefined, "A passive production row exposes real cells");
                    click(target, true);
                    table.forceActiveFocus();
                    keyClick(Qt.Key_Down);
                    compare(table.markerRow === undefined ? -1 : table.markerRow, -1, "A passive table remains without a current row after pointer and keyboard input");
                    compare(bars().length, 0, "A passive table draws no current-row marker");
                    verify(!cells.some(cell => cell.marksCurrentRow && cell.font.bold), "Passive rows acquire no bold current-row number");
                }
                return;
            }
            const target = table.count > 1 ? 1 : 0;
            if (data.mode === "cursor" || data.mode === "background") {
                const column = data.textColumn === null ? 0 : data.textColumn;
                const cell = Render.cells(table.itemAtIndex(target))[column];
                click(cell);
                if (data.mode === "cursor") {
                    tryVerify(() => Render.descendants(cell).some(item => item.activeFocus && item.readOnly === false && item.cursorVisible === true && item.cursorRectangle && item.cursorRectangle.width > 0 && item.cursorRectangle.height > 0), 500, "A mouse click enables the active text cursor in the actual editable cell without a Tab press");
                } else {
                    noFill(data);
                }
                return;
            }
            if (data.mode === "hover") {
                noFill(data);
                const row = table.itemAtIndex(target);
                mouseMove(row, 4, 4);
                const theme = data.dark ? "dark" : "light";
                tryVerify(() => rowPixel(target) === RowStyle.reference.hover[theme], 1500, "Only the row under the pointer receives the independent hover background");
                if (target)
                    tryVerify(() => rowPixel(0) === ordinary(0, data), 1500, "The row outside the mouse keeps its ordinary background after its colour transition");
                noFill(data);
                return;
            }
            if (data.mode === "keyboard") {
                click(Render.cells(table.itemAtIndex(0))[0]);
                if (target) {
                    table.forceActiveFocus();
                    keyClick(Qt.Key_Down);
                    marked(1);
                    keyClick(Qt.Key_Up);
                    marked(0);
                } else {
                    table.forceActiveFocus();
                    keyClick(Qt.Key_Down);
                    keyClick(Qt.Key_Up);
                    marked(0);
                }
                return;
            }
            const columns = data.mode.startsWith("editable") ? [Number(data.mode.slice(8))] : [0];
            for (const column of columns) {
                if (target)
                    click(Render.cells(table.itemAtIndex(0))[0]);
                const container = Render.cells(table.itemAtIndex(target))[column];
                const cell = Render.descendants(container).find(item => item.popup && item.enabled) || container;
                click(cell);
                if (data.mode.startsWith("editable")) {
                    verify(Render.descendants(cell).some(item => item.activeFocus) || (cell.popup && cell.popup.visible), "The same click also begins editing or opens the real choice popup");
                    if (cell.popup && cell.popup.visible)
                        keyClick(Qt.Key_Escape);
                }
                compare(table.markerRow, target, "Mouse input moves the logical current-row line immediately without Tab or another input");
                marked(target);
                keyClick(Qt.Key_Escape);
            }
        }
    }
}
