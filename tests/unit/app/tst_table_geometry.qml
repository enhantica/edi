// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import EasyApplication.Gui.Style as EaStyle
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

Item {
    id: surface
    width: 1200
    height: 1100
    ListModel { id: rows; dynamicRoles: true }
    TextMetrics { id: ink }
    Component { id: atoms; AtomSitesGroup {} }
    Component { id: experiments; ExperimentsGroup { collapsed: false } }
    Component { id: background; BackgroundGroup {} }
    Component { id: exclusions; ExcludedRegionsGroup {} }
    Component { id: orientation; PreferredOrientationGroup {} }
    Component { id: reflections; ReflectionsGroup {} }
    Component { id: canvas; Rectangle { width: 190; height: 100; color: "#18334a" } }
    Component { id: cell; ParameterCell { x: 20; y: 25; height: 40 } }
    Component { id: field; ParameterField { x: 20; y: 25; height: 40; label: "" } }
    TestCase {
        name: "RenderedTableGeometry"
        when: windowShown
        function init() {
            failOnWarning(/.*/);
            Session.closeProject();
            rows.clear();
            verify(Session.openProject(Qt.resolvedUrl("../../fixtures/table_display")), "The independently supplied geometry input opens");
        }
        function cleanup() { Session.closeProject(); }
        function parameter() {
            const supplied = Probe.rows(Session.project.parameters);
            const found = supplied.find(row => row.parameter && row.parameter.name === "intensity");
            verify(found !== undefined, "The independent fixture has its intensity parameter");
            return found.parameter;
        }
        function test_actual_column_geometry_data() {
            const kinds = [
                {tag: "atoms", component: atoms, table: "atomSites.list", count: 9, flex: [3,4,5,7], idColumn: 1, icons: [8]},
                {tag: "experiments", component: experiments, table: "experiments.list", count: 7, flex: [4], idColumn: 3, icons: [1,2,6]},
                {tag: "background", component: background, table: "background.list", count: 5, flex: [2,3], idColumn: 1, icons: [4]},
                {tag: "exclusions", component: exclusions, table: "excludedRegions.list", count: 5, flex: [2,3], idColumn: 1, icons: [4]},
                {tag: "orientation", component: orientation, table: "preferredOrientation.list", count: 8, flex: [2,3,4,5,6], idColumn: 1, icons: [7]},
                {tag: "reflections", component: reflections, table: "reflections.list", count: 5, flex: [1,2,3,4], idColumn: -1, icons: []}
            ];
            const result = [];
            for (const kind of kinds) for (const count of [12,112])
                result.push(Object.assign({}, kind, {tag: kind.tag + "-" + count, rows: count}));
            return result;
        }
        function test_actual_column_geometry(data) {
            const p = parameter();
            const seed = {id: "row", label: "row", typeSymbol: "Si", wyckoffLetter: "a", fractX: p, fractY: p, fractZ: p, occupancy: p,
                name: "bank", experiment: Session.project.currentExperiment, fitOutcome: "", file: "pattern.dat", extracted: [], isTemplate: false,
                position: 12, intensity: p, start: 10, end: 20, structureId: "phase", indexH: 1, indexK: 0, indexL: 0, marchR: p, marchRandomFract: p,
                hkl: "1 0 0", dSpacing: 3.4, fSquaredCalc: 123.4};
            for (let i = 0; i < data.rows; ++i) rows.append(Object.assign({}, seed, {id: "r" + i, label: "r" + i}));
            const group = createTemporaryObject(data.component, surface, {width: 610});
            verify(group !== null, "Every owner-named table is the production component");
            if (data.tag.startsWith("atoms")) group.structure = Session.project.currentStructure;
            else if (data.tag.startsWith("experiments")) group.project = Session.project;
            else group.experiment = Session.project.currentExperiment;
            const table = group.objectName === data.table ? group : Ui.find(group, data.table);
            verify(table !== null, "The production table consumer is discoverable");
            table.sourceModel = rows;
            table.maxRowCountShow = 4;
            tryCompare(table, "count", data.rows, 2000, "The supplied numbering-length input reaches the delegate model");
            const widths = [];
            for (const width of [610,930]) {
                group.width = width;
                table.width = width;
                verify(waitForPolish(group), "Each changed sidebar width completes rendered layout");
                table.forceLayout();
                const delegate = table.itemAtIndex(0);
                verify(delegate !== null, "The actual first delegate exists");
                const body = Render.cells(delegate), head = Render.cells(table.headerItem);
                compare(body.length, data.count, "The rendered row has every declared column");
                compare(head.length, data.count, "The rendered header has every declared column");
                for (let i = 0; i < body.length; ++i) {
                    verify(Math.abs(body[i].width - head[i].width) < 0.6, "Header and delegate receive the same actual width");
                    verify(Math.abs(body[i].mapToItem(table,0,0).x - head[i].mapToItem(table,0,0).x) < 0.6, "Actual header and row column boundaries align");
                }
                ink.font = body[0].font;
                ink.text = String(data.rows);
                const needed = Math.ceil(ink.advanceWidth);
                verify(body[0].width >= needed && body[0].width <= needed + body[0].font.pixelSize + 1,
                    "Numbering fits the independently measured longest supplied number with at most one em padding");
                for (const column of data.flex) verify(Math.abs(body[column].width - body[data.flex[0]].width) < 0.6,
                    "The actual main scientific columns share the remaining width equally");
                for (const column of data.icons) verify(body[column].width > 0 && body[column].width <= EaStyle.Sizes.fontPixelSize * 2.5,
                    "Rendered icon and action columns remain compact at each sidebar width");
                if (data.idColumn >= 0) {
                    verify(body[data.idColumn].width <= table.width * 0.25 + 1, "Identifiers leave scientific columns the remaining space");
                    ink.font = head[data.idColumn].font;
                    ink.text = data.tag.startsWith("experiments") ? "Datablock" : "r111";
                    verify(body[data.idColumn].width <= Math.ceil(ink.advanceWidth) + ink.font.pixelSize + 2,
                        "Short names and IDs use measured content width rather than a fixed wide share");
                    compare(body[data.idColumn].horizontalAlignment, Text.AlignLeft, "Identifiers align left across the loop tables");
                }
                if (data.tag.startsWith("background") || data.tag.startsWith("exclusions"))
                    compare(head[1].text.toLowerCase(), "id", "Stored loop identities have their visible ID column");
                widths.push(body.map(item => item.width));
                const last = body[body.length-1].mapToItem(table,body[body.length-1].width,0).x;
                verify(last <= table.width + 0.6 && table.width - last <= EaStyle.Sizes.fontPixelSize * 2,
                    "Rendered cells fill the available table width without overflow or unused right-side space");
                const next = table.itemAtIndex(4);
                verify(next !== null, "Each page consumer instantiates its next scrolling row");
                const fraction = (table.height - next.mapToItem(table,0,0).y) / next.height;
                verify(Math.abs(fraction - 0.5) < 0.06, "Every actual table shows half the next delegate as its scrolling cue");
            }
            if (data.idColumn >= 0) {
                for (let i = 0; i < rows.count; ++i) {
                    rows.setProperty(i, "id", "long.identifier.".repeat(100));
                    rows.setProperty(i, "label", "long.identifier.".repeat(100));
                    rows.setProperty(i, "name", "long.identifier.".repeat(100));
                    rows.setProperty(i, "structureId", "long.identifier.".repeat(100));
                }
                verify(waitForPolish(table), "Long supplied identifiers complete actual cell layout");
                table.forceLayout();
                const longCells = Render.cells(table.itemAtIndex(0));
                verify(longCells[data.idColumn].width <= table.width * 0.25 + 1,
                    "Long IDs cannot consume more than one quarter of the rendered table");
                for (const column of data.flex) verify(longCells[column].width > 0,
                    "Long IDs leave every real scientific cell usable");
                for (const column of data.icons) verify(longCells[column].width > 0,
                    "Long IDs leave every actual row action visible");
            }
            verify(widths[1][data.flex[0]] > widths[0][data.flex[0]], "Rendered main columns receive the extra sidebar width");
            verify(Math.abs(widths[1][0] - widths[0][0]) < 0.6, "Numbering remains content-sized as the sidebar grows");
        }
        function test_real_overflow_clips_without_ellipsis_data() {
            return [{tag: "table-cell", component: cell, width: 35}, {tag: "standalone-field", component: field, width: 80}];
        }
        function test_real_overflow_clips_without_ellipsis(data) {
            const parent = createTemporaryObject(canvas, surface);
            const input = createTemporaryObject(data.component, parent, {width: data.width, item: parameter()});
            verify(input !== null && waitForPolish(input), "Both actual parameter consumers complete the narrow layout");
            input.focus = false;
            compare(input.value, "2.290e7", "Narrow rendering retains the independently specified scientific string");
            verify(input.contentWidth > input.width - input.leftPadding - input.rightPadding, "The test creates actual text overflow");
            compare(input.cursorPosition, 0, "Inactive overflow starts at the first digit");
            const first = input.positionToRectangle(0);
            verify(first.x >= 0 && first.x < input.width, "The first digit is inside the inactive text viewport");
            verify(!String(input.text).includes("…"), "Inactive numbers are clipped without substituting an ellipsis");
            verify(waitForRendering(parent), "The actual overflow frame is rendered before pixel inspection");
            const image = grabImage(parent);
            for (let x = Math.ceil(input.x + input.width + 2); x < parent.width - 2; ++x)
                for (let y = Math.ceil(input.y + 8); y < input.y + input.height - 8; ++y)
                    compare(image.pixel(x,y), parent.color, "Numerical glyphs cannot paint beyond the real narrow input boundary");
            input.forceActiveFocus();
            tryCompare(input, "text", "22900000", 2000, "Editing the clipped cell or field exposes the complete supplied value");
        }
    }
}
