// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
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
                ink.font = item.font;
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
        function geometrySettled(table) {
            return table.columnFitLife !== null && table.columnFitLife.alive
                && !table.columnFitLife.queued && !table.refitting
                && !isPolishScheduled(surface.Window.window);
        }
        function settleGeometry(table) {
            tryVerify(() => geometrySettled(table), 2000,
                "The actual live table completes its queued fit and whole-window polish before geometry is observed");
            verify(geometrySettled(table), "Geometry capture cannot admit a queued, refitting, retired or unpolished owner");
        }
        function advance(text, font) {
            ink.font = font;
            ink.text = String(text);
            return Math.ceil(ink.advanceWidth);
        }
        function naturalInk(cell) {
            let needed = 0;
            if (cell.font) {
                if (typeof cell.editText === "string")
                    needed = Math.max(needed, advance(cell.editText, cell.font));
                if (typeof cell.number === "string" || typeof cell.number === "number")
                    needed = Math.max(needed, advance(cell.number, cell.font));
                if (typeof cell.value === "string" || typeof cell.value === "number")
                    needed = Math.max(needed, advance(cell.value, cell.font));
            }
            for (const item of Render.texts(cell))
                needed = Math.max(needed, advance(Probe.plainText(item.text), item.font));
            return needed;
        }
        function selectorBounds(group, body, head) {
            const type = Ui.find(group, "atomSite.typeSymbol.0");
            const wyckoff = Ui.find(group, "atomSite.wyckoffLetter.0");
            verify(type !== null && wyckoff !== null, "Both real atom selectors are present in the measured row");
            const names = group.sites.wyckoffNames;
            verify(names.length > 0, "The genuine current space group supplies its closed-selector position names");
            const symbols = ApplicationInfo.elementSymbols;
            compare(type.count, symbols.length, "The type selector exposes the declared element vocabulary");
            let widestType = 0, widestPosition = 0;
            for (let i = 0; i < symbols.length; ++i) {
                compare(type.textAt(i), symbols[i], "Every measured type option is the actual public catalogue entry");
                widestType = Math.max(widestType, advance(symbols[i], type.font));
            }
            for (const name of names)
                widestPosition = Math.max(widestPosition, advance(name, wyckoff.font));
            const pieces = Render.texts(type.contentItem).filter(item => item.font.family === EaStyle.Fonts.iconsFamily);
            verify(pieces.length === 1, "The type selector has its genuine single atom-category glyph");
            const glyph = advance(pieces[0].text, pieces[0].font);
            const result = [];
            for (const selector of [type, wyckoff]) {
                verify(selector.indicator !== null && selector.indicator.visible, "The actual selector retains its declared arrow");
                compare(selector.indicator.text, "\uf0d7", "The pinned base selector's arrow is the declared caret glyph");
                const arrow = advance("\uf0d7", selector.indicator.font);
                const isType = selector === type;
                // IconLine's half-em gap plus the type content's extra half-em;
                // the pinned ComboBox supplies its own padding, spacing and arrow.
                const text = isType ? widestType + glyph + EaStyle.Sizes.fontPixelSize : widestPosition;
                const natural = text + arrow + selector.spacing + 2 * selector.padding;
                const minimum = Math.max(naturalInk(head[isType ? 2 : 6]), natural,
                    isType ? EaStyle.Sizes.fontPixelSize * 4.5 : 0);
                // The public table declaration reserves at most one cell margin;
                // type's declaration additionally reserves half that margin.
                const maximum = minimum + EaStyle.Sizes.tableColumnSpacing * (isType ? 6 : 4)
                    + selector.leftPadding + selector.rightPadding;
                result.push({column: isType ? 2 : 6, minimum, maximum});
            }
            return result;
        }
        function fixedColumns(data, head) {
            const fixed = [];
            for (const column of data.actions)
                fixed.push({column, width: AppSizes.iconColumnWidth});
            if (data.tag.startsWith("experiments")) {
                fixed.push({column: 1, width: AppSizes.iconOnlyColumnWidth});
                const fit = Math.ceil(Math.max(advance("Fit", Qt.font({family: EaStyle.Fonts.fontFamily, pixelSize: EaStyle.Sizes.fontPixelSize})), EaStyle.Sizes.fontPixelSize * 1.15)) + EaStyle.Sizes.tableColumnSpacing;
                fixed.push({column: 2, width: fit});
            }
            return fixed;
        }
        function inkBounds(cell, table) {
            let left = Infinity, right = -Infinity;
            for (const item of Render.texts(cell)) {
                const needed = advance(Probe.plainText(item.text), item.font);
                const room = item.width - item.leftPadding - item.rightPadding;
                const spare = Math.max(0, room - needed);
                const inset = item.horizontalAlignment === Text.AlignRight ? spare
                    : item.horizontalAlignment === Text.AlignHCenter ? spare / 2 : 0;
                const start = item.mapToItem(table, 0, 0).x + item.leftPadding + inset;
                left = Math.min(left, start);
                right = Math.max(right, start + needed);
            }
            return left < Infinity ? {left, right} : null;
        }
        function policyRecord(data, table, body, head, fixed, selectors) {
            return {width: table.width,
                body: body.map(cell => ({width: cell.width, x: cell.mapToItem(table, 0, 0).x,
                    alignment: cell.horizontalAlignment, ink: inkBounds(cell, table)})),
                head: head.map(cell => ({width: cell.width, x: cell.mapToItem(table, 0, 0).x,
                    alignment: cell.horizontalAlignment, ink: inkBounds(cell, table)})), fixed, selectors};
        }
        function policyErrors(data, record) {
            const errors = [];
            if (record.body.length !== data.count || record.head.length !== data.count)
                return ["column population"];
            for (const cell of record.body.concat(record.head))
                if (!Number.isFinite(cell.width) || !Number.isFinite(cell.x) || cell.width < 0)
                    return ["invalid measured geometry"];
            for (let column = 0; column < data.count; ++column) {
                if (Math.abs(record.body[column].width - record.head[column].width) >= 0.6
                        || Math.abs(record.body[column].x - record.head[column].x) >= 0.6)
                    errors.push("header/body boundary");
            }
            for (const fixed of record.fixed)
                if (Math.abs(record.body[fixed.column].width - fixed.width) >= 0.6)
                    errors.push("declared fixed size");
            for (const selector of record.selectors)
                if (!Number.isFinite(selector.minimum) || !Number.isFinite(selector.maximum)
                        || selector.minimum < 0 || selector.maximum < selector.minimum
                        || record.body[selector.column].width + 0.6 < selector.minimum
                        || record.body[selector.column].width > selector.maximum + 0.6)
                    errors.push("measured selector compactness");
            if (data.expectedPolicy === "equal") {
                for (const column of data.flex)
                    if (Math.abs(record.body[column].width - record.body[data.flex[0]].width) >= 0.6)
                        errors.push("equal atom scientific columns");
            } else {
                for (const owner of ["body", "head"]) {
                    const ink = record[owner][data.filler].ink;
                    if (ink === null || !Number.isFinite(ink.left) || !Number.isFinite(ink.right) || ink.right < ink.left)
                        errors.push("last-data ink witness");
                }
                for (const column of data.flex)
                    if (record.body[column].alignment !== record.head[column].alignment)
                        errors.push("scientific header/body alignment");
                for (const action of data.actions)
                    if (record.body[data.filler].x + record.body[data.filler].width > record.body[action].x + 0.6)
                        errors.push("filler/button overlap");
            }
            return errors;
        }
        function transitionErrors(data, first, second) {
            const errors = policyErrors(data, first).concat(policyErrors(data, second));
            if (errors.includes("column population") || errors.includes("invalid measured geometry"))
                return errors;
            if (data.expectedPolicy === "content") {
                for (let column = 0; column < data.count; ++column)
                    if (column !== data.filler && ((first.roomy && second.roomy
                            && Math.abs(first.body[column].width - second.body[column].width) >= 0.6)
                            || second.body[column].width > second.needs[column] + 1))
                        errors.push("spare width before last data column");
                if (first.roomy && second.roomy
                        && Math.abs(second.body[data.filler].width - first.body[data.filler].width - (second.width - first.width)) >= 0.6)
                    errors.push("last-data spare width");
                for (const owner of first.roomy && second.roomy ? ["body", "head"] : []) {
                    const before = first[owner][data.filler].ink;
                    const after = second[owner][data.filler].ink;
                    if (before === null || after === null || Math.abs(after.left - before.left) >= 0.6
                            || Math.abs(after.right - before.right) >= 0.6)
                        errors.push("last-data ink shifted by spare width");
                }
            } else if (second.body[data.flex[0]].width <= first.body[data.flex[0]].width)
                errors.push("equal columns receive wider viewport");
            return errors;
        }
        function armPolicyEscapes(data, first, second) {
            const copy = () => JSON.parse(JSON.stringify(second));
            let broken = copy();
            broken.body[0].width = NaN;
            verify(policyErrors(data, broken).includes("invalid measured geometry"), "Non-finite observation data cannot silently satisfy numeric geometry comparisons");
            broken = copy();
            broken.head[0].x += 1;
            verify(policyErrors(data, broken).includes("header/body boundary"), "A real observation with a shifted header cannot satisfy the geometry observer");
            broken = copy();
            const removed = data.tag.startsWith("experiments") ? 5 : data.count - 1;
            broken.body.splice(removed, 1);
            broken.head.splice(removed, 1);
            verify(policyErrors(data, broken).includes("column population"), "Removing even a hidden placeholder cannot satisfy the complete column observer");
            for (const fixed of second.fixed) {
                broken = copy();
                broken.body[fixed.column].width *= 2;
                broken.head[fixed.column].width *= 2;
                verify(policyErrors(data, broken).includes("declared fixed size"), "An enlarged action, display icon or Fit slot cannot pass the independent declared-size check");
            }
            for (const selector of second.selectors) {
                broken = copy();
                broken.body[selector.column].width = selector.minimum - 2;
                broken.head[selector.column].width = selector.minimum - 2;
                verify(policyErrors(data, broken).includes("measured selector compactness"), "A selector that loses its independently measured option, icon or arrow room is refused");
                broken = copy();
                broken.body[selector.column].width = selector.maximum + 2;
                broken.head[selector.column].width = selector.maximum + 2;
                verify(policyErrors(data, broken).includes("measured selector compactness"), "A selector wider than its independently measured vocabulary and chrome is refused");
            }
            if (data.expectedPolicy === "equal") {
                broken = copy();
                broken.body[data.flex[0]].width += 2;
                broken.head[data.flex[0]].width += 2;
                verify(policyErrors(data, broken).includes("equal atom scientific columns"), "An unequal atom scientific column cannot pass merely because its header agrees");
            } else {
                broken = copy();
                const early = data.flex.find(column => column !== data.filler);
                // Experiments has only one old scientific flex entry; its ID is earlier data.
                const column = early === undefined ? data.idColumn : early;
                verify(column >= 0, "Every ordinary policy escape addresses a genuine earlier data column");
                const growth = second.needs[column] + 2 - second.body[column].width;
                broken.body[column].width += growth;
                broken.head[column].width += growth;
                broken.body[data.filler].width -= growth;
                broken.head[data.filler].width -= growth;
                verify(transitionErrors(data, first, broken).includes("spare width before last data column"), "Equal spreading or early spare width cannot satisfy the last-data-only policy");
                if (first.roomy && second.roomy) {
                    broken = copy();
                    for (const owner of ["body", "head"]) {
                        broken[owner][data.filler].ink.left += 10;
                        broken[owner][data.filler].ink.right += 10;
                    }
                    verify(transitionErrors(data, first, broken).includes("last-data ink shifted by spare width"), "Centred or trailing filler content cannot move into the newly supplied spare width");
                }
            }
        }
        function test_actual_pending_fit_is_not_settled_geometry() {
            const p = parameter();
            rows.append({id: "queued", position: 12, intensity: p});
            const group = createTemporaryObject(background, surface, {
                width: 800, experiment: Session.project.currentExperiment});
            verify(group !== null, "The queue exercise uses the actual loaded background component");
            const table = Ui.find(group, "background.list");
            verify(table !== null, "The queue exercise reaches its genuine table owner");
            table.width = 800;
            table.sourceModel = rows;
            table.forceLayout();
            settleGeometry(table);
            verify(!table.columnFitLife.queued, "The genuine table is quiet before the explicit public scheduling request");
            table.scheduleFitColumns();
            console.log("TABLE_POLICY_PENDING " + JSON.stringify({alive: table.columnFitLife.alive,
                queued: table.columnFitLife.queued, refitting: table.refitting}));
            verify(table.columnFitLife.queued, "The actual public scheduling door really arms a pending callback");
            verify(!geometrySettled(table), "The geometry readiness observer refuses that genuine pending callback");
            settleGeometry(table);
            verify(!table.columnFitLife.queued && !table.refitting, "The ordinary callback returns to truthful settled geometry under the same bound");
        }
        function test_actual_column_geometry_data() {
            const kinds = [
                {
                    tag: "atoms",
                    expectedPolicy: "equal",
                    filler: -1,
                    actions: [8],
                    component: atoms,
                    table: "atomSites.list",
                    count: 9,
                    flex: [3, 4, 5, 7],
                    idColumn: 1,
                    icons: [8]
                },
                {
                    tag: "experiments",
                    expectedPolicy: "content",
                    filler: 4,
                    actions: [6],
                    component: experiments,
                    table: "experiments.list",
                    count: 7,
                    flex: [4],
                    idColumn: 3,
                    icons: [1, 2, 6]
                },
                {
                    tag: "background",
                    expectedPolicy: "content",
                    filler: 3,
                    actions: [4],
                    component: background,
                    table: "background.list",
                    count: 5,
                    flex: [2, 3],
                    idColumn: 1,
                    icons: [4]
                },
                {
                    tag: "exclusions",
                    expectedPolicy: "content",
                    filler: 3,
                    actions: [4],
                    component: exclusions,
                    table: "excludedRegions.list",
                    count: 5,
                    flex: [2, 3],
                    idColumn: 1,
                    icons: [4]
                },
                {
                    tag: "orientation",
                    expectedPolicy: "content",
                    filler: 6,
                    actions: [7],
                    component: orientation,
                    table: "preferredOrientation.list",
                    count: 8,
                    flex: [2, 3, 4, 5, 6],
                    idColumn: 1,
                    icons: [7]
                },
                {
                    tag: "reflections",
                    expectedPolicy: "content",
                    filler: 4,
                    actions: [],
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
            const widths = [], records = [];
            for (const width of [610, 930]) {
                group.width = width;
                table.width = width;
                table.forceLayout();
                settleGeometry(table);
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
                const fixed = fixedColumns(data, head);
                const selectors = data.expectedPolicy === "equal" ? selectorBounds(group, body, head) : [];
                const margin = 4 * EaStyle.Sizes.tableColumnSpacing;
                let naturalTotal = 0;
                const needs = [], naturalInkNeeds = [];
                const rowSpacing = body[0].parent.spacing;
                verify(typeof rowSpacing === "number" && rowSpacing >= 0, "The actual row supplies its declared nonnegative layout spacing");
                for (let column = 0; column < body.length; ++column) {
                    const fixedColumn = fixed.find(item => item.column === column);
                    const selector = selectors.find(item => item.column === column);
                    if (fixedColumn) {
                        needs[column] = fixedColumn.width;
                        naturalTotal += needs[column];
                    } else if (selector) {
                        needs[column] = selector.minimum + margin;
                        naturalTotal += needs[column];
                    } else if (column === 0) {
                        needs[column] = needed + 2 * AppSizes.fieldSpacing;
                        naturalTotal += needs[column];
                    } else if (data.tag.startsWith("experiments") && column === 5) {
                        needs[column] = 0;
                        compare(body[column].visible, false, "The ordinary experiment keeps the declared hidden scan placeholder");
                        compare(head[column].visible, false, "The header preserves the same hidden scan slot");
                    } else {
                        let natural = Math.max(naturalInk(body[column]), naturalInk(head[column]));
                        if (column === data.idColumn)
                            natural = Math.max(natural, advance("r" + (data.rows - 1), body[column].font));
                        needs[column] = natural + margin;
                        naturalInkNeeds[column] = natural;
                        naturalTotal += needs[column];
                    }
                }
                const roomy = naturalTotal + rowSpacing * (data.count - 1) <= width;
                console.log("TABLE_POLICY_NATURAL " + JSON.stringify({tag: data.tag, width, naturalTotal, rowSpacing, roomy, needs, fixed, selectors}));
                verify(width !== 930 || roomy, "The authored wide viewport genuinely has room for independent natural content, declared chrome and margins");
                for (let column = 0; column < body.length; ++column) {
                    if (roomy && naturalInkNeeds[column] !== undefined) {
                        verify(body[column].width + 0.6 >= naturalInkNeeds[column], "Roomy columns retain independently measured complete header and supplied content ink");
                        if (data.expectedPolicy === "content" && column !== data.filler)
                            verify(body[column].width <= needs[column] + 1, "Earlier ordinary data columns stay compact instead of consuming spare row width");
                    }
                }
                const record = policyRecord(data, table, body, head, fixed, selectors);
                record.roomy = roomy;
                record.needs = needs;
                console.log("TABLE_POLICY " + JSON.stringify({tag: data.tag, expectedPolicy: data.expectedPolicy, filler: data.filler, record}));
                compare(policyErrors(data, record).length, 0, "The actual geometry follows the independently declared per-kind policy");
                records.push(record);
                for (const column of data.icons) {
                    assertCellInkFits(body[column]);
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
                for (const column of data.flex) {
                    const alignment = data.expectedPolicy === "equal" ? Text.AlignHCenter
                        : (data.tag.startsWith("experiments") || (data.tag.startsWith("reflections") && column === 1)) ? Text.AlignLeft : Text.AlignRight;
                    compare(body[column].horizontalAlignment, alignment, "Scientific alignment follows the authored equal/numeric/text/last-data policy");
                    compare(head[column].horizontalAlignment, alignment, "Scientific headers retain the corresponding independently declared alignment");
                }
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
                table.forceLayout();
                settleGeometry(table);
                const longCells = Render.cells(table.itemAtIndex(0));
                const longWidth = longCells[data.idColumn].width;
                const longHead = Render.cells(table.headerItem);
                compare(policyErrors(data, policyRecord(data, table, longCells, longHead, fixedColumns(data, longHead), data.expectedPolicy === "equal" ? selectorBounds(group, longCells, longHead) : [])).length, 0, "Long identifiers preserve all fixed, selector and header/body boundaries");
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
                table.forceLayout();
                settleGeometry(table);
                const shortCells = Render.cells(table.itemAtIndex(0));
                const shortHead = Render.cells(table.headerItem);
                compare(policyErrors(data, policyRecord(data, table, shortCells, shortHead, fixedColumns(data, shortHead), data.expectedPolicy === "equal" ? selectorBounds(group, shortCells, shortHead) : [])).length, 0, "Returning short identifiers preserve every original fixed and header/body boundary");
                verify(shortCells[data.idColumn].width < longWidth, "The long-to-short resize restores compact actual ID width");
                compare(shortCells[data.idColumn].width, widths[1][data.idColumn], "The ID column returns to its original independently supplied short-content width");
                assertSuppliedTextFits(shortCells[data.idColumn], "r" + (data.rows - 1), data.tag.startsWith("experiments") ? "Datablock" : "id");
            }
            compare(transitionErrors(data, records[0], records[1]).length, 0, "A wider viewport follows the declared equal-atom or last-data-only spare-width rule");
            armPolicyEscapes(data, records[0], records[1]);
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
                table.forceLayout();
                settleGeometry(table);
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
            ink.font = input.font;
            ink.text = "2.290e7";
            input.width = Math.min(data.width, Math.ceil(ink.advanceWidth / 2) + input.leftPadding + input.rightPadding);
            verify(waitForPolish(input), "The compact token also reaches a genuinely over-room rendered viewport");
            compare(input.item.fileValue, "22900000", "The supplied IUCr99 pair retains its canonical written value");
            compare(input.item.fileSu, "100000", "The supplied pair retains its written uncertainty");
            tryCompare(input, "text", "2.290e7", 2000, "The actual narrow display retains the last place required by SU 1.0e5");
            verify(input.contentWidth > input.width - input.leftPadding - input.rightPadding, "The test creates actual text overflow");
            compare(input.cursorPosition, 0, "Inactive overflow starts at the first digit");
            compare(input.horizontalAlignment, Text.AlignLeft, "A long number clips its end while retaining its beginning");
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
