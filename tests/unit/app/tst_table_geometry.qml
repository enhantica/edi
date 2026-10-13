// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import EasyApplication.Gui.Style as EaStyle
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render
import "TableBoundary.js" as Boundary

Item {
    id: surface
    width: 1200
    height: 1100
    ListModel {
        id: rows
        dynamicRoles: true
    }
    TextMetrics {
        id: ink
    }
    Component {
        id: atoms
        AtomSitesGroup {}
    }
    Component {
        id: experiments
        ExperimentsGroup {
            collapsed: false
        }
    }
    Component {
        id: background
        BackgroundGroup {}
    }
    Component {
        id: exclusions
        ExcludedRegionsGroup {}
    }
    Component {
        id: orientation
        PreferredOrientationGroup {}
    }
    Component {
        id: reflections
        ReflectionsGroup {}
    }
    Component {
        id: canvas
        Rectangle {
            width: 190
            height: 100
            color: "#18334a"
        }
    }
    Component {
        id: cell
        ParameterCell {
            x: 20
            y: 25
            height: 40
        }
    }
    Component {
        id: field
        ParameterField {
            x: 20
            y: 25
            height: 40
            label: ""
        }
    }
    TestCase {
        id: test
        name: "RenderedTableGeometry"
        when: windowShown
        function init() {
            failOnWarning(/.*/);
            Session.closeProject();
            rows.clear();
            verify(Session.openProject(Qt.resolvedUrl("../../fixtures/table_display")), "The independently supplied geometry input opens");
        }
        function cleanup() {
            Session.closeProject();
        }
        function parameter() {
            const supplied = Probe.rows(Session.project.parameters);
            const found = supplied.find(row => row.parameter && row.parameter.name === "intensity");
            verify(found !== undefined, "The independent fixture has its intensity parameter");
            return found.parameter;
        }
        function assertCellInkFits(cell) {
            const drawn = Render.texts(cell);
            const rings = Render.descendants(cell).filter(item => item.visible && item.radius > 0 && item.border && item.border.width > 0);
            verify(drawn.length + rings.length > 0, "Every fixed column retains actual text, glyph or ring ink");
            for (const item of drawn) {
                ink.font = Qt.font({
                    family: item.font.family === EaStyle.Fonts.iconsFamily ? EaStyle.Fonts.iconsFamily : EaStyle.Fonts.fontFamily,
                    pixelSize: EaStyle.Sizes.fontPixelSize
                });
                ink.text = item.text;
                const needed = Math.ceil(ink.advanceWidth);
                verify(item.width + 0.6 >= needed, "The actual fixed-column text or glyph viewport fits its independently measured ink");
                const left = item.mapToItem(cell, 0, 0).x;
                verify(left >= -0.6 && left + needed <= cell.width + 0.6, "Fixed-column ink remains within its actual cell boundary");
            }
            for (const ring of rings) {
                verify(ring.width >= EaStyle.Sizes.fontPixelSize * 0.85, "A status ring retains the independently declared icon ink size");
                const left = ring.mapToItem(cell, 0, 0).x;
                verify(left >= -0.6 && left + ring.width <= cell.width + 0.6, "A fixed status column fits the whole independently drawn ring");
            }
        }
        function assertSuppliedTextFits(cell, supplied, title) {
            ink.font = Qt.font({
                family: EaStyle.Fonts.fontFamily,
                pixelSize: EaStyle.Sizes.fontPixelSize
            });
            ink.text = supplied;
            const bodyNeed = Math.ceil(ink.advanceWidth);
            ink.text = title;
            const headingNeed = Math.ceil(ink.advanceWidth);
            verify(cell.width >= Math.max(bodyNeed, headingNeed), "A compact fixed column fits both its independently supplied content and heading");
            assertCellInkFits(cell);
        }
        function test_actual_column_geometry_data() {
            const kinds = [
                {
                    tag: "atoms",
                    component: atoms,
                    table: "atomSites.list",
                    count: 9,
                    flex: [3, 4, 5, 7],
                    idColumn: 1,
                    icons: [8]
                },
                {
                    tag: "experiments",
                    component: experiments,
                    table: "experiments.list",
                    count: 7,
                    flex: [4],
                    idColumn: 3,
                    icons: [1, 2, 6]
                },
                {
                    tag: "background",
                    component: background,
                    table: "background.list",
                    count: 5,
                    flex: [2, 3],
                    idColumn: 1,
                    icons: [4]
                },
                {
                    tag: "exclusions",
                    component: exclusions,
                    table: "excludedRegions.list",
                    count: 5,
                    flex: [2, 3],
                    idColumn: 1,
                    icons: [4]
                },
                {
                    tag: "orientation",
                    component: orientation,
                    table: "preferredOrientation.list",
                    count: 8,
                    flex: [2, 3, 4, 5, 6],
                    idColumn: 1,
                    icons: [7]
                },
                {
                    tag: "reflections",
                    component: reflections,
                    table: "reflections.list",
                    count: 5,
                    flex: [1, 2, 3, 4],
                    idColumn: -1,
                    icons: []
                }
            ];
            const result = [];
            for (const kind of kinds)
                for (const count of [12, 112])
                    result.push(Object.assign({}, kind, {
                        tag: kind.tag + "-" + count,
                        rows: count
                    }));
            return result;
        }
        function test_actual_column_geometry(data) {
            const p = parameter();
            const seed = {
                id: "row",
                label: "row",
                typeSymbol: "Si",
                wyckoffLetter: "a",
                fractX: p,
                fractY: p,
                fractZ: p,
                occupancy: p,
                name: "bank",
                experiment: Session.project.currentExperiment,
                fitOutcome: "",
                file: "pattern.dat",
                extracted: [],
                isTemplate: false,
                position: 12,
                intensity: p,
                start: 10,
                end: 20,
                structureId: "phase",
                indexH: 1,
                indexK: 0,
                indexL: 0,
                marchR: p,
                marchRandomFract: p,
                hkl: "1 0 0",
                dSpacing: 3.4,
                fSquaredCalc: 123.4
            };
            for (let i = 0; i < data.rows; ++i)
                rows.append(Object.assign({}, seed, {
                    id: "r" + i,
                    label: "r" + i,
                    name: "r" + i,
                    structureId: "r" + i
                }));
            const group = createTemporaryObject(data.component, surface, {
                width: 610
            });
            verify(group !== null, "Every owner-named table is the production component");
            if (data.tag.startsWith("atoms"))
                group.structure = Session.project.currentStructure;
            else if (data.tag.startsWith("experiments"))
                group.project = Session.project;
            else
                group.experiment = Session.project.currentExperiment;
            const table = group.objectName === data.table ? group : Ui.find(group, data.table);
            verify(table !== null, "The production table consumer is discoverable");
            table.sourceModel = rows;
            table.maxRowCountShow = 4;
            tryCompare(table, "count", data.rows, 2000, "The supplied numbering-length input reaches the delegate model");
            const widths = [];
            for (const width of [610, 930]) {
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
                    verify(Math.abs(body[i].mapToItem(table, 0, 0).x - head[i].mapToItem(table, 0, 0).x) < 0.6, "Actual header and row column boundaries align");
                }
                ink.font = Qt.font({
                    family: EaStyle.Fonts.fontFamily,
                    pixelSize: EaStyle.Sizes.fontPixelSize
                });
                ink.text = String(data.rows);
                const needed = Math.ceil(ink.advanceWidth);
                verify(body[0].width >= needed && body[0].width <= needed + body[0].font.pixelSize + 1, "Numbering fits the independently measured longest supplied number with at most one em padding");
                for (const column of data.flex)
                    verify(Math.abs(body[column].width - body[data.flex[0]].width) < 0.6, "The actual main scientific columns share the remaining width equally");
                for (const column of data.icons) {
                    assertCellInkFits(body[column]);
                    verify(body[column].width <= EaStyle.Sizes.fontPixelSize * 2.5, "Rendered icon and action columns remain compact at each sidebar width");
                }
                if (data.tag.startsWith("atoms")) {
                    ink.font = Qt.font({
                        family: EaStyle.Fonts.fontFamily,
                        pixelSize: EaStyle.Sizes.fontPixelSize
                    });
                    ink.text = "Si";
                    verify(body[2].width >= Math.ceil(ink.advanceWidth) + ink.font.pixelSize * 1.5, "The type column fits the independently supplied silicon symbol, an atom icon and their spacing");
                    assertCellInkFits(head[2]);
                    assertCellInkFits(body[2]);
                    assertSuppliedTextFits(body[6], "a", "WL");
                    assertCellInkFits(head[6]);
                    verify(body[2].width <= EaStyle.Sizes.fontPixelSize * 4.5 + 1, "The atom type column remains compact while fitting its icon and supplied symbol");
                    verify(body[6].width <= EaStyle.Sizes.fontPixelSize * 2.5 + 1, "The Wyckoff column remains compact while fitting its supplied letter and heading");
                }
                if (data.idColumn >= 0) {
                    assertCellInkFits(head[data.idColumn]);
                    assertSuppliedTextFits(body[data.idColumn], "r" + (data.rows - 1), data.tag.startsWith("experiments") ? "Datablock" : "id");
                    verify(body[data.idColumn].width <= table.width * 0.25 + 1, "Identifiers leave scientific columns the remaining space");
                    ink.font = Qt.font({
                        family: EaStyle.Fonts.fontFamily,
                        pixelSize: EaStyle.Sizes.fontPixelSize
                    });
                    ink.text = data.tag.startsWith("experiments") ? "Datablock" : "r111";
                    verify(body[data.idColumn].width <= Math.ceil(ink.advanceWidth) + ink.font.pixelSize + 2, "Short names and IDs use measured content width rather than a fixed wide share");
                    compare(body[data.idColumn].horizontalAlignment, Text.AlignLeft, "Identifiers align left across the loop tables");
                }
                if (data.tag.startsWith("background") || data.tag.startsWith("exclusions") || data.tag.startsWith("orientation"))
                    compare(head[1].text.toLowerCase(), "id", "Stored loop identities have their visible ID column");
                for (const column of data.flex)
                    if (!data.tag.startsWith("experiments"))
                        compare(body[column].horizontalAlignment, Text.AlignHCenter, "The actual loop and reflection scientific columns align consistently across tables");
                widths.push(body.map(item => item.width));
                const last = body[body.length - 1].mapToItem(table, body[body.length - 1].width, 0).x;
                verify(last <= table.width + 0.6 && table.width - last <= EaStyle.Sizes.fontPixelSize * 2, "Rendered cells fill the available table width without overflow or unused right-side space");
                const next = table.itemAtIndex(4);
                verify(next !== null, "Each page consumer instantiates its next scrolling row");
                Boundary.check(test, table, next, surface);
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
                const longWidth = longCells[data.idColumn].width;
                verify(Math.abs(longCells[data.idColumn].width - table.width * 0.25) <= 1, "Long independently supplied IDs expand to the permitted quarter-table cap");
                verify(longCells[data.idColumn].width > widths[1][data.idColumn], "Long supplied IDs expand the actual ID column beyond its short-content width");
                verify(longCells[data.idColumn].width <= table.width * 0.25 + 1, "Long IDs cannot consume more than one quarter of the rendered table");
                for (const column of data.flex)
                    verify(longCells[column].width > 0, "Long IDs leave every real scientific cell usable");
                for (const column of data.icons)
                    assertCellInkFits(longCells[column]);
                for (let i = 0; i < rows.count; ++i)
                    for (const role of ["id", "label", "name", "structureId"])
                        rows.setProperty(i, role, "r" + i);
                verify(waitForPolish(table), "Returning to short supplied IDs completes rendered layout");
                table.forceLayout();
                const shortCells = Render.cells(table.itemAtIndex(0));
                verify(shortCells[data.idColumn].width < longWidth, "The long-to-short resize restores compact actual ID width");
                compare(shortCells[data.idColumn].width, widths[1][data.idColumn], "The ID column returns to its original independently supplied short-content width");
                assertSuppliedTextFits(shortCells[data.idColumn], "r" + (data.rows - 1), data.tag.startsWith("experiments") ? "Datablock" : "id");
            }
            verify(widths[1][data.flex[0]] > widths[0][data.flex[0]], "Rendered main columns receive the extra sidebar width");
            verify(Math.abs(widths[1][0] - widths[0][0]) < 0.6, "Numbering remains content-sized as the sidebar grows");
        }
        function test_loop_table_boundaries_align_for_identical_identifiers() {
            const p = parameter();
            for (let i = 0; i < 12; ++i)
                rows.append({
                    id: "phase",
                    position: 12,
                    intensity: p,
                    start: 10,
                    end: 20,
                    structureId: "phase",
                    indexH: 1,
                    indexK: 0,
                    indexL: 0,
                    marchR: p,
                    marchRandomFract: p
                });
            const boundaries = [];
            for (const component of [background, exclusions, orientation]) {
                const group = createTemporaryObject(component, surface, {
                    width: 800,
                    experiment: Session.project.currentExperiment
                });
                verify(group !== null, "The loop-alignment witness uses each real production group");
                const table = Render.descendants(group).find(item => typeof item.sourceModel !== "undefined" && typeof item.itemAtIndex === "function");
                verify(table !== undefined, "Each actual loop table is discoverable");
                table.width = 800;
                table.sourceModel = rows;
                verify(waitForPolish(table), "Independent equal-length loop IDs complete rendered layout");
                table.forceLayout();
                const body = Render.cells(table.itemAtIndex(0));
                assertSuppliedTextFits(body[1], "phase", "id");
                compare(body[1].text, "phase", "The first visible ID retains the independently supplied stored key");
                boundaries.push([body[0].mapToItem(table, 0, 0).x, body[1].mapToItem(table, 0, 0).x, body[2].mapToItem(table, 0, 0).x]);
            }
            for (const current of boundaries.slice(1))
                for (let i = 0; i < current.length; ++i)
                    verify(Math.abs(current[i] - boundaries[0][i]) < 0.6, "Numbering, ID and scientific column starts align across the loop tables for identical inputs");
        }
        function test_real_overflow_clips_without_ellipsis_data() {
            return [
                {
                    tag: "table-cell",
                    component: cell,
                    width: 35
                },
                {
                    tag: "standalone-field",
                    component: field,
                    width: 80
                }
            ];
        }
        function test_real_overflow_clips_without_ellipsis(data) {
            const parent = createTemporaryObject(canvas, surface);
            const input = createTemporaryObject(data.component, parent, {
                width: data.width,
                item: parameter()
            });
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
                    compare(image.pixel(x, y), parent.color, "Numerical glyphs cannot paint beyond the real narrow input boundary");
            input.forceActiveFocus();
            tryCompare(input, "text", "22900000", 2000, "Editing the clipped cell or field exposes the complete supplied value");
        }
    }
}
