// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtTest
import EasyApplication.Gui.Style as EaStyle
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
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
    FontMetrics {
        id: nameMetrics
    }
    Component {
        id: fractionalViewport
        Text {
            text: "Independent natural viewport"
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
            width: implicitWidth
        }
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
        function fixedInkViewportFits(width, advance) {
            return width + 0.6 >= advance;
        }
        function test_fixed_ink_qreal_domain_rejects_an_actual_undersized_viewport() {
            const item = createTemporaryObject(fractionalViewport, surface);
            verify(item !== null, "The ink negative uses a genuine natural-width Qt text item");
            ink.font = item.font;
            ink.text = item.text;
            const actual = ink.advanceWidth;
            verify(actual > 2 * 0.6, "The independent literal arms a positive undersizing contrast");
            compare(item.width, item.implicitWidth, "The positive preserves its natural qreal viewport");
            verify(fixedInkViewportFits(item.width, actual),
                "Natural unrounded text and its qreal logical advance share the same measurement domain");
            item.width = actual / 2;
            verify(item.width > 0 && !fixedInkViewportFits(item.width, actual),
                "The same ink predicate rejects a genuinely positive but undersized real viewport");
        }
        function rememberShownIdentifiers(data, table, seen) {
            for (let index = 0; index < data.rows; ++index) {
                const row = table.itemAtIndex(index);
                if (!row || !row.visible || row.height <= 0)
                    continue;
                const top = row.mapToItem(table, 0, 0).y;
                if (top < table.height && top + row.height > 0) {
                    const authored = "r" + index;
                    if (!seen.includes(authored))
                        seen.push(authored);
                }
            }
            verify(seen.length > 0, "Generic ID needs come only from actual shown authored rows");
        }
        function identifierInputs(data, seen) {
            // Atom ID columns explicitly use the all-model text-width helper.
            // Generic auto-fitted columns retain only shown/visited identities.
            return data.expectedPolicy === "equal" ? ["r" + (data.rows - 1)] : seen;
        }
        function suppliedIdentifierNeed(inputs, font) {
            let widest = 0;
            for (const text of inputs)
                widest = Math.max(widest, advance(text, font));
            return widest;
        }
        function assertCellInkFits(cell) {
            const drawn = Render.texts(cell);
            const rings = Render.descendants(cell).filter(item => item.visible && item.radius > 0 && item.border && item.border.width > 0);
            verify(drawn.length + rings.length > 0, "Every fixed column retains actual text, glyph or ring ink");
            for (const item of drawn) {
                ink.font = item.font;
                ink.text = item.text;
                const needed = ink.advanceWidth;
                verify(fixedInkViewportFits(item.width, needed), "The actual fixed-column text or glyph viewport fits its independently measured ink");
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
        function geometrySettled(table, expandedOwner = null) {
            const tableReady = table.columnFitLife !== null && table.columnFitLife.alive
                && !table.columnFitLife.queued && !table.refitting
                && !isPolishScheduled(surface.Window.window);
            if (!tableReady || expandedOwner === null)
                return tableReady;
            const finalHeight = expandedOwner.titleArea.height + expandedOwner.spacing
                + expandedOwner.contentHeight + expandedOwner.bottomPadding;
            return expandedOwner.visible && !expandedOwner.collapsed
                && expandedOwner.height === finalHeight
                && expandedOwner.implicitHeight === finalHeight;
        }
        function settleGeometry(table, expandedOwner = null) {
            tryVerify(() => geometrySettled(table, expandedOwner), 2000,
                "The actual live table and declared containing GroupBox expansion settle within the same geometry clock");
            verify(geometrySettled(table, expandedOwner), "Geometry capture cannot admit queued fit, unpolished layout or incomplete declared owner expansion");
        }
        function advance(text, font) {
            ink.font = font;
            ink.text = String(text);
            return Math.ceil(ink.advanceWidth);
        }
        function naturalInk(cell) {
            let needed = 0;
            if (cell.font && typeof cell.number === "number")
                needed = advance(cell.number, cell.font);
            for (const item of Render.texts(cell))
                needed = Math.max(needed, advance(Probe.plainText(item.text), item.font));
            return needed;
        }
        function paddingObservation(cell) {
            if (!("leftPadding" in cell) || !("rightPadding" in cell))
                return null;
            return {left: cell.leftPadding, right: cell.rightPadding};
        }
        function declaredChrome(data, column, owner) {
            const kind = data.kinds[column];
            if (owner === "body" && kind === "held-text")
                return 0; // Experiments' file Item and its nested Labels have no base padding.
            return kind === "text" || kind === "held-text" || kind === "number"
                ? EaStyle.Sizes.tableColumnSpacing : 0;
        }
        function naturalCellNeed(data, column, body, head) {
            return Math.max(naturalInk(body) + declaredChrome(data, column, "body"),
                naturalInk(head) + declaredChrome(data, column, "head"));
        }
        function identityTitle(data) {
            if (data.tag.startsWith("experiments"))
                return "Datablock";
            const uid = data.tag.startsWith("atoms") ? "atom_site.id"
                : data.tag.startsWith("orientation") ? "preferred_orientation.structure_id"
                : data.tag.startsWith("background") ? "background.id" : "excluded_region.id";
            return Session.label(uid);
        }
        function sourceAlignment(kind) {
            return kind === "number" ? Text.AlignRight
                : kind === "text" || kind === "held-text" ? Text.AlignLeft : Text.AlignHCenter;
        }
        function chromeErrors(data, record) {
            const errors = [];
            const gap = EaStyle.Sizes.tableColumnSpacing;
            for (let column = 1; column < data.count; ++column) {
                const kind = data.kinds[column];
                if (kind !== "text" && kind !== "held-text" && kind !== "number")
                    continue; // Fixed icons/actions, selector Items and the hidden slot are separate declarations.
                for (const owner of ["body", "head"]) {
                    const cell = record[owner][column];
                    if (cell.alignment !== sourceAlignment(kind))
                        errors.push("source-kind alignment");
                    if (kind === "held-text" && owner === "body") {
                        if (cell.padding !== null || cell.nestedPadding.length === 0
                                || cell.nestedPadding.some(pad => !Number.isFinite(pad.left)
                                    || !Number.isFinite(pad.right) || Math.abs(pad.left) >= 0.6
                                    || Math.abs(pad.right) >= 0.6))
                            errors.push("source-owned cell chrome");
                        continue;
                    }
                    const left = kind === "number" ? 0 : gap;
                    const right = kind === "number" ? gap : 0;
                    if (cell.padding === null || !Number.isFinite(cell.padding.left)
                            || !Number.isFinite(cell.padding.right)
                            || Math.abs(cell.padding.left - left) >= 0.6
                            || Math.abs(cell.padding.right - right) >= 0.6)
                        errors.push("source-owned cell chrome");
                }
            }
            return errors;
        }
        function loopStartErrors(records) {
            const errors = [];
            const first = records[0];
            for (const record of records) {
                for (const column of [0, 1])
                    if (Math.abs(record.starts[column] - first.starts[column]) >= 0.6)
                        errors.push("common numbering/ID start");
                if (record.width + 0.6 < record.need
                        || Math.abs(record.starts[2] - record.starts[1] - record.width
                            - EaStyle.Sizes.tableColumnSpacing) >= 0.6)
                    errors.push("per-heading ID boundary");
            }
            return errors;
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
            const positionFont = Qt.font({family: EaStyle.Fonts.fontFamily,
                pixelSize: EaStyle.Sizes.fontPixelSize});
            for (let i = 0; i < symbols.length; ++i) {
                compare(type.textAt(i), symbols[i], "Every measured type option is the actual public catalogue entry");
                widestType = Math.max(widestType, advance(symbols[i], type.font));
            }
            for (const name of names)
                widestPosition = Math.max(widestPosition, advance(name, positionFont));
            const pieces = Render.texts(type.contentItem).filter(item => item.font.family === EaStyle.Fonts.iconsFamily);
            verify(pieces.length === 1, "The type selector has its genuine single atom-category glyph");
            const glyph = advance(pieces[0].text, pieces[0].font);
            const result = [];
            for (const selector of [type, wyckoff]) {
                verify(selector.indicator !== null && selector.indicator.visible, "The actual selector retains its declared arrow");
                compare(selector.indicator.text, "\uf0d7", "The pinned base selector's arrow is the declared caret glyph");
                compare(selector.indicator.font.family, EaStyle.Fonts.iconsFamily,
                    "The selector arrow uses its declared icon face");
                const arrow = advance("\uf0d7", selector.indicator.font);
                verify(Math.abs(selector.indicator.width - arrow) < 1,
                    "The arrow's own width fits exactly its independently measured glyph");
                compare(selector.padding, 0, "The pinned template selector has no unspecified base padding");
                compare(selector.spacing, 0, "The pinned template selector has no unspecified extra spacing");
                verify(!selector.mirrored, "This authored left-to-right fixture retains its declared layout direction");
                compare(selector.leftPadding, 0, "The genuine selector has its source-declared left padding");
                verify(Math.abs(selector.rightPadding - arrow) < 1,
                    "The genuine selector reserves only its declared arrow on the right");
                const isType = selector === type;
                // IconLine's half-em gap plus the type content's extra half-em;
                // the pinned ComboBox supplies its own padding, spacing and arrow.
                const text = isType ? widestType + glyph + EaStyle.Sizes.fontPixelSize : widestPosition;
                const natural = text + arrow; // Pinned base padding/spacing are independently required to be zero.
                const minimum = Math.max(naturalInk(head[isType ? 2 : 6]), natural,
                    isType ? EaStyle.Sizes.fontPixelSize * 4.5 : 0);
                // Preserve the type vocabulary/chrome ceiling. WP instead has
                // its FIRST group's explicit widest-name/header plus 2.5-em width.
                const maximum = isType ? minimum + EaStyle.Sizes.tableColumnSpacing * 6 + arrow
                    : Math.max(widestPosition, advance("WP", positionFont)) + EaStyle.Sizes.fontPixelSize * 2.5;
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
        function policyRecord(table, body, head, fixed, selectors) {
            const capture = cell => ({width: cell.width, x: cell.mapToItem(table, 0, 0).x,
                alignment: cell.horizontalAlignment, ink: inkBounds(cell, table),
                padding: paddingObservation(cell),
                nestedPadding: Render.texts(cell).map(paddingObservation).filter(pad => pad !== null)});
            return {width: table.width,
                body: body.map(capture), head: head.map(capture), fixed, selectors};
        }
        function policyErrors(data, record) {
            const errors = [];
            if (record.body.length !== data.count || record.head.length !== data.count)
                return ["column population"];
            for (const cell of record.body.concat(record.head))
                if (!Number.isFinite(cell.width) || !Number.isFinite(cell.x) || cell.width < 0)
                    return ["invalid measured geometry"];
            errors.push(...chromeErrors(data, record));
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
            for (const column of data.flex)
                if (record.body[column].alignment !== record.head[column].alignment)
                    errors.push("scientific header/body alignment");
            for (const action of data.actions) {
                const cell = record.body[action];
                if (cell.x + cell.width > record.width + 0.6
                        || record.width - cell.x - cell.width > EaStyle.Sizes.tableColumnSpacing + 0.6)
                    errors.push("trailing action leaves the right edge");
            }
            return errors;
        }
        function transitionErrors(data, first, second) {
            const errors = policyErrors(data, first).concat(policyErrors(data, second));
            if (errors.includes("column population") || errors.includes("invalid measured geometry"))
                return errors;
            if (first.roomy && second.roomy) {
                for (let column = 0; column < data.count; ++column)
                    if (column !== data.elasticColumn
                            && Math.abs(first.body[column].width - second.body[column].width) >= 0.6)
                        errors.push("known column absorbs spare width");
                if (data.elasticColumn >= 0
                        && Math.abs(second.body[data.elasticColumn].width - first.body[data.elasticColumn].width
                                    - (second.width - first.width)) >= 0.6)
                    errors.push("name column does not receive spare width");
            }
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
            broken = copy();
            for (let column = 1; column < data.count; ++column) {
                const kind = data.kinds[column];
                if (kind !== "text" && kind !== "number")
                    continue;
                broken = copy();
                for (const owner of ["body", "head"])
                    broken[owner][column].alignment = sourceAlignment(kind) === Text.AlignLeft ? Text.AlignRight : Text.AlignLeft;
                verify(policyErrors(data, broken).includes("source-kind alignment"),
                    "Matching wrong header/body alignment cannot defeat the independent declared kind");
                broken = copy();
                for (const owner of ["body", "head"]) {
                    const side = kind === "text" ? "left" : "right";
                    broken[owner][column].padding[side] += EaStyle.Sizes.tableColumnSpacing;
                    broken[owner][column].width += EaStyle.Sizes.tableColumnSpacing;
                }
                verify(policyErrors(data, broken).includes("source-owned cell chrome"),
                    "A cell cannot grow both padding and width to manufacture its expected budget");
            }
            if (first.roomy && second.roomy) {
                const fixedData = data.flex.find(column => column !== data.elasticColumn) ?? data.idColumn;
                verify(fixedData >= 0, "The spare-width control addresses a known-width data column");
                broken = copy();
                broken.body[fixedData].width += 2;
                broken.head[fixedData].width += 2;
                verify(transitionErrors(data, first, broken).includes("known column absorbs spare width"),
                       "Matching headers cannot conceal spare width added to fixed scientific data");
            }
            for (const action of data.actions) {
                broken = copy();
                broken.body[action].x -= 3 * EaStyle.Sizes.tableColumnSpacing + 2;
                broken.head[action].x = broken.body[action].x;
                verify(policyErrors(data, broken).includes("trailing action leaves the right edge"),
                       "A synchronized action and header cannot hide a real trailing gap");
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
                    kinds: ["numbering", "text", "selector", "number", "number", "number", "selector", "number", "icon"],
                    expectedPolicy: "equal",
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
                    expandedGroupBoxOwner: true,
                    kinds: ["numbering", "icon", "icon", "text", "held-text", "hidden", "icon"],
                    expectedPolicy: "content",
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
                    kinds: ["numbering", "text", "number", "number", "icon"],
                    expectedPolicy: "content",
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
                    kinds: ["numbering", "text", "number", "number", "icon"],
                    expectedPolicy: "content",
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
                    kinds: ["numbering", "text", "text", "text", "text", "number", "number", "icon"],
                    expectedPolicy: "content",
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
                    kinds: ["numbering", "text", "number", "number", "number"],
                    expectedPolicy: "content",
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
                        elasticColumn: kind.tag === "experiments" ? 4 : kind.idColumn,
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
            const widths = [], records = [], seenIdentifiers = [];
            for (const width of [610, 930]) {
                group.width = width;
                table.width = width;
                table.forceLayout();
                settleGeometry(table, data.expandedGroupBoxOwner ? group : null);
                const delegate = table.itemAtIndex(0);
                verify(delegate !== null, "The actual first delegate exists");
                const body = Render.cells(delegate), head = Render.cells(table.headerItem);
                if (data.idColumn >= 0 && data.expectedPolicy !== "equal")
                    rememberShownIdentifiers(data, table, seenIdentifiers);
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
                const margin = 3 * EaStyle.Sizes.tableColumnSpacing;
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
                        let natural = naturalCellNeed(data, column, body[column], head[column]);
                        if (column === data.idColumn)
                            natural = Math.max(natural, suppliedIdentifierNeed(identifierInputs(data, seenIdentifiers), body[column].font)
                                + declaredChrome(data, column, "body"));
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
                        verify(body[column].width + 0.6 >= naturalInkNeeds[column], "Roomy columns retain independent complete header/content ink and source-owned chrome");
                    }
                }
                const record = policyRecord(table, body, head, fixed, selectors);
                record.roomy = roomy;
                record.needs = needs;
                console.log("TABLE_POLICY " + JSON.stringify({tag: data.tag, consumer: data.table, record}));
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
                    assertSuppliedTextFits(body[6], "a", "WP");
                    assertCellInkFits(head[6]);
                }
                if (data.idColumn >= 0) {
                    assertCellInkFits(head[data.idColumn]);
                    for (const authored of identifierInputs(data, seenIdentifiers))
                        assertSuppliedTextFits(body[data.idColumn], authored, identityTitle(data));
                    compare(body[data.idColumn].horizontalAlignment, Text.AlignLeft, "Identifiers align left across the loop tables");
                }
                if (data.tag.startsWith("background") || data.tag.startsWith("exclusions") || data.tag.startsWith("orientation")) {
                    const uid = data.tag.startsWith("background") ? "background.id"
                        : data.tag.startsWith("exclusions") ? "excluded_region.id" : "preferred_orientation.structure_id";
                    compare(head[1].uid, uid, "Each stored identity keeps its actual source-declared semantic header");
                    compare(head[1].text, Session.label(uid), "The declared ID or Structure heading remains visible");
                }
                for (const column of data.flex) {
                    const alignment = sourceAlignment(data.kinds[column]);
                    compare(body[column].horizontalAlignment, alignment, "Scientific columns retain their declared numeric or text alignment");
                    compare(head[column].horizontalAlignment, alignment, "Scientific headers retain the corresponding independently declared alignment");
                }
                widths.push(body.map(item => item.width));
                const last = body[body.length - 1].mapToItem(table, body[body.length - 1].width, 0).x;
                verify(last <= table.width + 0.6, "Rendered columns stay inside the table without clipping its right edge");
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
                settleGeometry(table, data.expandedGroupBoxOwner ? group : null);
                const longCells = Render.cells(table.itemAtIndex(0));
                const longWidth = longCells[data.idColumn].width;
                const longHead = Render.cells(table.headerItem);
                compare(policyErrors(data, policyRecord(table, longCells, longHead, fixedColumns(data, longHead), data.expectedPolicy === "equal" ? selectorBounds(group, longCells, longHead) : [])).length, 0, "Long identifiers preserve all fixed, selector and header/body boundaries");
                compare(longWidth, widths[1][data.idColumn], "A long user identifier cannot move its allocated column");
                for (let column = 0; column < longCells.length; ++column)
                    compare(longCells[column].width, widths[1][column], "Changing user text leaves all other column widths fixed");
                for (const column of data.flex)
                    verify(longCells[column].width > 0, "Long IDs leave every real scientific cell usable");
                for (const column of data.icons)
                    assertCellInkFits(longCells[column]);
                for (let i = 0; i < rows.count; ++i)
                    for (const role of ["id", "label", "name", "structureId"])
                        rows.setProperty(i, role, "r" + i);
                table.forceLayout();
                settleGeometry(table, data.expandedGroupBoxOwner ? group : null);
                const shortCells = Render.cells(table.itemAtIndex(0));
                const shortHead = Render.cells(table.headerItem);
                compare(policyErrors(data, policyRecord(table, shortCells, shortHead, fixedColumns(data, shortHead), data.expectedPolicy === "equal" ? selectorBounds(group, shortCells, shortHead) : [])).length, 0, "Returning short identifiers preserve every original fixed and header/body boundary");
                compare(shortCells[data.idColumn].width, widths[1][data.idColumn], "The ID column returns to its original independently supplied short-content width");
                for (const authored of identifierInputs(data, seenIdentifiers))
                    assertSuppliedTextFits(shortCells[data.idColumn], authored, identityTitle(data));
            }
            compare(transitionErrors(data, records[0], records[1]).length, 0, "A wider roomy viewport gives spare room to the user name alone");
            armPolicyEscapes(data, records[0], records[1]);
            verify(Math.abs(widths[1][0] - widths[0][0]) < 0.6, "Numbering remains content-sized as the sidebar grows");
        }
        function test_datablock_names_fit_until_the_table_reaches_its_minimum_data() {
            return [{tag: "ordinary", scan: false}, {tag: "scan-with-extracts", scan: true}];
        }
        function openDatablockScan(name) {
            const location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/correlations/scan-sequential"));
            const file = "analysis/analysis.edi";
            const analysis = SettingsProof.text(location, file);
            const rules = [
                ["temperature", "diffrn.ambient_temperature", "^# TEMP ([0-9.]+)", true],
                ["pressure", "diffrn.ambient_pressure", "^# PRESS ([0-9.]+)", false],
                ["field", "diffrn.ambient_field", "^# FIELD ([0-9.]+)", false]
            ];
            const columns = ["id", "target", "pattern", "required"];
            const extractLoop = ["loop_", ...columns.map(column => "_sequential_fit_extract." + column),
                ...rules.map(([id, target, pattern, required]) => `${id} ${target} "${pattern}" ${required}`)].join("\n");
            verify(analysis.length > 0 && SettingsProof.write(location, file, analysis.trim() + "\n\n" + extractLoop + "\n"),
                "The scratch analysis gets the complete temperature, pressure and field extract loop");
            const bankFile = "experiments/bank.edi";
            const bank = SettingsProof.text(location, bankFile);
            verify(bank.startsWith("data_bank") && SettingsProof.write(location, bankFile, bank.replace("data_bank", "data_" + name)),
                "The scan's saved datablock has the independently authored long name");
            for (const dataset of ["01.xy", "02.xy"]) {
                const path = "experiments/scan/" + dataset;
                const points = SettingsProof.text(location, path);
                verify(points.length > 0 && SettingsProof.write(location, path, "# TEMP 295\n# PRESS 12.5\n# FIELD 3.7\n" + points),
                    "Each real scan file carries its independently supplied extract values");
            }
            Session.closeProject();
            verify(Session.openProject(location), "The scratch project opens as an Experiments scan: " + Session.lastError);
            const loadedRules = Probe.rows(Session.project.analysis.sequentialExtract)
                .map(rule => columns.map(column => rule[column]));
            compare(JSON.stringify(loadedRules), JSON.stringify(rules),
                "The loaded scratch project retains each extract rule's id, target, pattern and required flag in order");
        }
        function assertDatablockRowFits(table, row, header) {
            const cells = Render.cells(row).filter(cell => cell.visible);
            verify(cells.length > 0, "The minimum-width observation finds the actual " + header + " cells");
            let last = 0;
            for (const cell of cells) {
                const left = cell.mapToItem(table, 0, 0).x;
                const right = cell.mapToItem(table, cell.width, 0).x;
                verify(cell.width > 0 && left >= last - 0.6 && right <= table.width + 0.6,
                    "Every visible " + header + " cell fits, in order, inside the minimum-width table");
                last = right;
            }
        }
        function assertExtractCells(table, parent, entries) {
            const texts = Render.texts(parent);
            for (const entry of entries) {
                const cell = texts.find(item => item.text === entry);
                verify(cell !== undefined && !cell.truncated,
                    "The real scan list displays the complete extract heading or supplied value " + entry);
                verify(cell.mapToItem(table, 0, 0).x >= -0.6
                    && cell.mapToItem(table, cell.width, 0).x <= table.width + 0.6,
                    "The scan extract cell stays inside the visible table: " + entry);
            }
        }
        function assertDatablockHover(cell, name) {
            const level = Preferences.toolTipLevel;
            try {
                Preferences.toolTipLevel = "All";
                const point = Ui.clickPoint(cell);
                verify(point !== null, "The shortened Datablock cell has a reachable hover point");
                mouseMove(cell, point.x, point.y);
                tryVerify(() => SettingsProof.tooltipObjects(cell).some(tip =>
                    SettingsProof.tooltipOwnedBy(tip, cell) && tip.opened && tip.visible
                    && tip.text === name && tip.contentItem && tip.contentItem.width > 0), 3000,
                    "Hovering the shortened Datablock opens its own visible tooltip with the full unelided name");
            } finally {
                mouseMove(surface, surface.width - 1, surface.height - 1);
                Preferences.toolTipLevel = level;
            }
        }
        function test_datablock_names_fit_until_the_table_reaches_its_minimum(data) {
            const longName = "experimentLongCalibrationNameForTheWarmDetectorAndDownstreamMonitor2026";
            const names = [data.scan ? longName : "experiment1", longName];
            const headings = ["Temperature", "Pressure", "Field"];
            const values = ["295 K", "12.5", "3.7"];
            if (data.scan)
                openDatablockScan(longName);
            else
                for (const name of names)
                    rows.append({name, experiment: Session.project.currentExperiment,
                        fitOutcome: "", file: "pattern.dat", extracted: [], isTemplate: false});
            compare(Session.project.scan, data.scan, "The Datablock actor uses the requested real project mode");
            const widths = data.scan ? [1150, AppSizes.minimumAppWidth] : [930, 1150, AppSizes.minimumAppWidth];
            for (const width of widths) {
                const group = createTemporaryObject(experiments, surface, {width, project: Session.project, pageShown: true});
                verify(group !== null, "The names appear in the actual Experiments group");
                const table = Ui.find(group, "experiments.list");
                verify(table !== null, "The expanded group exposes the production experiments table");
                compare(Array.from(group.scanColumns), data.scan ? headings : [],
                    "The production table receives the configured extract columns in order");
                if (!data.scan)
                    table.sourceModel = rows;
                table.width = width;
                table.maxRowCountShow = names.length;
                table.forceLayout();
                tryCompare(table, "count", names.length, 2000, "Both independently supplied names reach the table");
                if (data.scan)
                    tryVerify(() => Probe.rows(table.sourceModel).every(row =>
                        JSON.stringify(row.extracted) === JSON.stringify(values)), 3000,
                        "The actual visible scan rows have loaded all three independently supplied extracts");
                settleGeometry(table, group);

                const atMinimum = width === AppSizes.minimumAppWidth;
                verify(atMinimum ? table.fillerWidth <= 1 : table.fillerWidth > 1,
                    "The sampled widths distinguish the minimum table from those with actual spare room");
                if (atMinimum)
                    assertDatablockRowFits(table, table.headerItem, "header");
                if (data.scan)
                    assertExtractCells(table, table.headerItem, headings);
                for (let index = 0; index < names.length; ++index) {
                    const name = names[index];
                    const row = table.itemAtIndex(index);
                    verify(row !== null && row.visible, "Each Datablock has a real visible experiment row");
                    if (atMinimum)
                        assertDatablockRowFits(table, row, "row");
                    if (data.scan)
                        assertExtractCells(table, row, values);
                    const cell = Ui.find(row, "experiments.name." + index);
                    verify(cell !== null && cell.visible, "The real Datablock name cell is displayed");
                    verify(cell.mapToItem(table, cell.width, 0).x <= table.width + 0.6,
                        "The Datablock cell must fit inside the table even at its minimum width");
                    if (!atMinimum || (!data.scan && index === 0)) {
                        compare(cell.text, name, "The full name remains in the Datablock cell while it fits");
                        verify(cell.color.a > 0
                            && cell.width - cell.leftPadding - cell.rightPadding + 0.6 >= advance(name, cell.font),
                            "A full Datablock name has visible ink and enough room for both ends");
                        continue;
                    }
                    const renderer = Render.texts(cell).find(item => item.truncated === true && item.color.a > 0);
                    verify(renderer !== undefined, "The long name visibly elides at the minimum width");
                    compare(renderer.text, name, "The elider receives the complete authored Datablock name");
                    compare(renderer.elide, Text.ElideMiddle, "The name elides in the middle");
                    nameMetrics.font = renderer.font;
                    const room = renderer.width - renderer.leftPadding - renderer.rightPadding;
                    const drawn = nameMetrics.elidedText(name, renderer.elide, room);
                    const ends = drawn.split("…");
                    verify(ends.length === 2 && ends.every(part => part.length > 0)
                        && name.startsWith(ends[0]) && name.endsWith(ends[1])
                        && ends[0].length + ends[1].length >= 10,
                        "The middle ellipsis preserves both ends and at least ten name characters");
                    if (index === names.length - 1)
                        assertDatablockHover(cell, name);
                }
                group.destroy();
            }
        }
        function test_generic_id_width_stays_fixed_when_rows_scroll_or_change() {
            const p = parameter(), last = 111, wideText = "model.identifier.111";
            for (let index = 0; index <= last; ++index)
                rows.append({id: index === last ? wideText : "r" + index,
                    position: 12, intensity: p});
            const group = createTemporaryObject(background, surface, {
                width: 930, experiment: Session.project.currentExperiment});
            verify(group !== null, "The whole-model ID witness uses the genuine production background owner");
            const table = Ui.find(group, "background.list");
            verify(table !== null, "The actual generic auto-fitted table is present");
            table.sourceModel = rows;
            table.width = 930;
            table.maxRowCountShow = 4;
            table.forceLayout();
            settleGeometry(table);
            compare(table.count, last + 1, "The whole independently authored model remains populated");
            compare(table.itemAtIndex(last), null, "The later wider ID is genuinely unseen initially");
            const before = Render.cells(table.itemAtIndex(0))[1].width;
            table.positionViewAtIndex(last, ListView.Contain);
            table.forceLayout();
            tryVerify(() => table.itemAtIndex(last) !== null && geometrySettled(table), 2000,
                "Ordinary actual scrolling instantiates the wider authored row within the original clock");
            const shown = table.itemAtIndex(last), shownCell = Render.cells(shown)[1];
            const top = shown.mapToItem(table, 0, 0).y;
            verify(shown.visible && top >= 0 && top + shown.height <= table.height + 0.6,
                "The later identifier really reaches the current viewport, not a hidden cache entry");
            assertSuppliedTextFits(shownCell, wideText, Session.label("background.id"));
            const visited = shownCell.width;
            compare(visited, before, "Scrolling cannot change the width declared by the column type");
            table.positionViewAtIndex(0, ListView.Contain);
            table.forceLayout();
            tryVerify(() => table.itemAtIndex(0) !== null && table.itemAtIndex(last) === null
                && geometrySettled(table), 2000,
                "Returning to the first real row releases the later delegate under the same clock");
            compare(Render.cells(table.itemAtIndex(0))[1].width, before,
                "Releasing the wider delegate leaves the whole-model width unchanged");
            rows.setProperty(last, "id", "r" + last);
            table.forceLayout();
            settleGeometry(table);
            compare(Render.cells(table.itemAtIndex(0))[1].width, before,
                "Changing unseen model content leaves the declared width unchanged");
            compare(rows.get(last).id, "r" + last, "Measurement preserves the independently changed source ID");
            compare(table.count, last + 1, "Fixed column sizing preserves unseen model rows");
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
            const sources = [
                {component: background, uid: "background.id"},
                {component: exclusions, uid: "excluded_region.id"},
                {component: orientation, uid: "preferred_orientation.structure_id"}
            ];
            for (const source of sources) {
                const group = createTemporaryObject(source.component, surface, {
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
                const head = Render.cells(table.headerItem);
                compare(head[1].uid, source.uid, "Each table keeps its own declared semantic heading");
                const title = Session.label(source.uid);
                compare(head[1].text, title, "The ID or Structure title comes from its declared dictionary item");
                assertSuppliedTextFits(body[1], "phase", title);
                compare(body[1].text, "phase", "The first visible ID retains the independently supplied stored key");
                boundaries.push({
                    starts: [body[0].mapToItem(table, 0, 0).x, body[1].mapToItem(table, 0, 0).x,
                        body[2].mapToItem(table, 0, 0).x], width: body[1].width,
                    need: Math.max(advance("phase", body[1].font), advance(title, head[1].font))
                        + EaStyle.Sizes.tableColumnSpacing + 3 * EaStyle.Sizes.tableColumnSpacing});
            }
            compare(loopStartErrors(boundaries).length, 0,
                "Common numbering/ID starts agree; each next start fits its own declared heading, chrome and margin");
            verify(Math.abs(boundaries[2].need - boundaries[0].need) > 1,
                "The source-declared Structure and ID headings independently distinguish this boundary exercise");
            const broken = JSON.parse(JSON.stringify(boundaries));
            broken[2].starts[2] += 2;
            verify(loopStartErrors(broken).includes("per-heading ID boundary"),
                "An offset from the declared Structure column cannot satisfy the observed boundary");
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
            const widthOf = text => {
                ink.text = text;
                return ink.advanceWidth;
            };
            const plain = "22900000";
            const scientific = ["2.290×10⁷", "2.29×10⁷", "2.3×10⁷"];
            const box = widthOf(scientific[1]) + 0.5;
            const isCell = data.tag === "table-cell";
            input.width = (isCell ? box : Math.ceil(widthOf(plain) / 2)) + input.leftPadding + input.rightPadding;
            verify(waitForPolish(input), "The production narrow number finishes real layout");
            compare(Ui.numericText(input.item.fileValue), 22900000, "The supplied IUCr99 pair retains its canonical written value");
            compare(Ui.numericText(input.item.fileSu), 100000, "The supplied pair retains its written uncertainty");
            const room = input.width - input.leftPadding - input.rightPadding;
            verify(widthOf(plain) > room, "The allocated width cannot show the complete ordinary token");
            if (isCell) {
                const expected = scientific.find(text => widthOf(text) <= room);
                verify(expected !== undefined, "The table column has room for at least two significant digits in scientific notation");
                tryCompare(input, "text", expected, 2000, "The table displays the most authored digits that fit without clipping");
                verify(input.contentWidth <= room + 0.5, "The entire compact number fits the native cell");
            } else {
                compare(input.cursorPosition, 0, "The narrow standalone field retains its leading digit");
            }
            verify(!String(input.text).includes("…"), "Numeric text does not substitute an ellipsis");
            const ownerWindow = parent.Window.window;
            verify(ownerWindow !== null && ownerWindow === surface.Window.window
                && ownerWindow === test.Window.window && windowShown && ownerWindow.visible
                && ownerWindow.visibility !== Window.Hidden && ownerWindow.visibility !== Window.Minimized,
                "The overflow item belongs to the same exposed QuickTest viewing window");
            ownerWindow.update();
            verify(waitForRendering(parent), "The actual overflow frame is rendered before pixel inspection");
            const image = grabImage(parent);
            for (let x = Math.ceil(input.x + input.width + 2); x < parent.width - 2; ++x)
                for (let y = Math.ceil(input.y + 8); y < input.y + input.height - 8; ++y)
                    compare(image.pixel(x, y), parent.color, "Numerical glyphs cannot paint beyond the real narrow input boundary");
            const popup = Ui.parameterPopup(test, input);
            const editor = Ui.parameterValue(test, input, popup);
            Ui.focusParameter(test, editor);
            tryCompare(editor, "text", input.item.fileEditValue, 2000, "The full editing route takes the canonical value");
            compare(Ui.numericText(editor.text), 22900000, "The full editing route exposes the complete supplied value");
            popup.close();
        }
    }
}
