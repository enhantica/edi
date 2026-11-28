// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "NativeTurn.js" as Turn
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render
import "../../fixtures/magnetic_type_iv/graph_oracle.js" as Oracle
import "../../fixtures/magnetic_type_iv/source_text.js" as Source

TestCase {
    id: test
    name: "MagneticOperatorWorkflow"
    when: windowShown
    property var app
    property string selector: ""
    property url inputUrl
    Component {
        id: application
        Main {}
    }
    Component {
        id: markingSpy
        SignalSpy {}
    }

    function initTestCase() {
        RunLog.dismissCrash();
        AppState.reset();
        app = application.createObject(null, {
            width: 1400,
            height: 1000,
            visible: true
        });
        verify(app && waitForRendering(app.contentItem), "Magnetic type checks use the rendered production application");
    }
    function init() {
        selector = Turn.begin(test, Probe, message => test.warn(message));
    }
    function cleanup() {
        const dialogs = Probe.objectsWithProperty(app, "opened").filter(item => item.opened && typeof item.close === "function");
        for (const dialog of dialogs)
            dialog.close();
        Session.closeProject();
        Turn.end(selector, message => test.warn(message));
    }
    function cleanupTestCase() {
        if (app)
            app.destroy();
    }
    function openInput(name, controls = true) {
        inputUrl = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/magnetic_type_iv/gui/" + name));
        verify(Session.openProject(inputUrl), "The app opens the independently authored " + name + " input");
        if (!controls)
            return;
        tryVerify(() => app.pagesWanted > 0 && app.pagesBuilt === app.pagesWanted, 10000, "The magnetic input's real workflow pages finish preparing");
        tryCompare(Session.project, "calculating", false, 15000, "The magnetic input calculation finishes before editing");
        Ui.click(test, Probe, app, "appBar.tab.structure");
        Ui.click(test, Probe, app, "sideBar.tab.basic");
    }
    function groups(tier) {
        Ui.click(test, Probe, app, "sideBar.tab." + tier);
        verify(waitForPolish(app.contentItem), "The selected sidebar completes its category layout");
        return Render.descendants(Ui.page(app)).filter(item => item.categoryId !== undefined && item.shown && Ui.inPane(Ui.target(item)));
    }
    function group(id, tier = "basic") {
        const found = groups(tier).filter(item => item.categoryId === id);
        compare(found.length, 1, "The selected sidebar contains exactly one " + id + " group");
        Ui.expandGroup(test, Probe, app, "group." + id);
        return found[0];
    }
    function press(item) {
        Ui.scrollIntoView(item);
        app.update();
        verify(waitForRendering(app.contentItem), "The pointer target finishes its rendered layout");
        const point = Ui.clickPoint(item);
        verify(point && item.enabled, "A real visible enabled control receives the pointer");
        let inputDelay = 0;
        for (let parent = item.parent; parent; parent = parent.parent)
            if (typeof parent.pressDelay === "number")
                inputDelay = Math.max(inputDelay, parent.pressDelay + 1);
        mouseClick(item, point.x, point.y, undefined, undefined, inputDelay);
        app.update();
        verify(waitForRendering(app.contentItem), "The real pointer action produces its rendered result");
    }
    function typeChoice() {
        const table = findChild(Ui.page(app), "structures.list");
        verify(table && table.count > 0, "The Structures table has a real current row");
        table.positionViewAtIndex(Session.project.currentStructureIndex, ListView.Contain);
        table.forceLayout();
        const row = table.itemAtIndex(Session.project.currentStructureIndex);
        const choices = Render.descendants(row).filter(item => item.visible && typeof item.textAt === "function" && Array.from({
                length: item.count
            }, (_, i) => item.textAt(i)).includes("Crystal") && Array.from({
                length: item.count
            }, (_, i) => item.textAt(i)).includes("Magnetic"));
        compare(choices.length, 1, "An atom-based structure offers one Crystal or Magnetic choice");
        const oldType = Render.descendants(row).find(item => item.value === "Atom-based");
        verify(oldType, "The original atom-based Type column remains visible");
        verify(choices[0].mapToItem(row, 0, 0).x > oldType.mapToItem(row, 0, 0).x, "The Crystal or Magnetic column follows the original Type column");
        return choices[0];
    }
    function choose(combo, label) {
        const index = Array.from({
            length: combo.count
        }, (_, i) => combo.textAt(i)).indexOf(label);
        verify(index >= 0, "The real selector contains the requested choice " + label);
        press(combo);
        tryCompare(combo.popup, "opened", true, 2000, "Pointer input opens the selector");
        const list = combo.popup.contentItem;
        list.positionViewAtIndex(index, ListView.Contain);
        list.forceLayout();
        tryVerify(() => list.itemAtIndex(index) && Ui.exposed(list.itemAtIndex(index)), 2000, "The requested choice is visibly instantiated");
        press(list.itemAtIndex(index));
        tryCompare(combo.popup, "opened", false, 2000, "The selector closes after pointer selection");
        tryCompare(combo.popup, "visible", false, 2000, "The closed selector releases its popup pointer surface");
    }
    function identifies(item, suffix) {
        return String(item.uid || "").toLowerCase().replace(/-/g, "_").endsWith(suffix) || String(item.objectName || "").toLowerCase().startsWith("generated.") && String(item.objectName).toLowerCase().replace(/-/g, "_").endsWith(suffix);
    }
    function field(owner, suffix, title) {
        const found = Render.descendants(owner).filter(item => item.visible && (identifies(item, suffix) || item.title === title || item.label === title));
        verify(found.length > 0, "The category visibly exposes " + title);
        return found[0];
    }
    function value(item) {
        return String(item.fieldValue ?? item.displayText ?? item.text ?? "");
    }
    function readOnly(item) {
        verify(item.readOnly === true || item.editable === false || !item.enabled, "The derived dictionary field is read-only: " + item.objectName);
    }
    function popup() {
        return Probe.objectsWithProperty(app, "opened").find(item => item.opened && item.objectName === "structures.magneticPopup");
    }
    function openPopup(name = "popup") {
        openInput(name);
        Session.project.currentStructureIndex = Session.project.structureIndex("parent");
        choose(typeChoice(), "Magnetic");
        tryVerify(() => !!popup(), 1000, "Choosing Magnetic opens the parent-to-child popup");
        compare(Session.project.currentStructure.magnetic, false, "Opening the popup keeps the nuclear parent intact");
        return popup();
    }
    function pcontrol(name) {
        const found = Render.descendants(popup().contentItem).concat(Render.descendants(popup().footer)).find(item => item.objectName === name);
        verify(found !== undefined, "The popup exposes its actual " + name + " control");
        return found;
    }
    function wave(vector) {
        const combo = pcontrol("magnetic.k");
        tryCompare(combo, "enabled", true, 5000, "The initial graph finishes before choosing another k");
        const label = Array.from({
            length: combo.count
        }, (_, i) => combo.textAt(i)).find(text => text.replace(/\s/g, "").includes("(" + vector + ")"));
        if (label !== undefined)
            choose(combo, label);
        else {
            choose(combo, "Other…");
            const fields = Render.descendants(popup().contentItem).filter(item => ["k₁", "k₂", "k₃"].includes(item.placeholderText));
            compare(fields.length, 3, "Typed k has three visible reciprocal-basis components");
            fields.sort((a, b) => a.placeholderText.localeCompare(b.placeholderText));
            vector.split(",").forEach((value, i) => {
                if (fields[i].text === value)
                    return;
                tryCompare(fields[i], "enabled", true, 5000, "The typed k field becomes ready after the preceding entry");
                press(fields[i]);
                keyClick(Qt.Key_A, Qt.ControlModifier);
                for (const character of value)
                    keyClick(character.charCodeAt(0));
                keyClick(Qt.Key_Return);
            });
        }
        tryVerify(() => !popup().busy, 5000, "The bounded magnetic graph computation finishes");
        verify(popup().found !== null, "The selected k produces its magnetic graph: " + popup().refusal);
    }
    function shownNodes() {
        return Render.descendants(popup().contentItem).filter(item => item.visible && /^magnetic\.node\.\d+$/.test(item.objectName));
    }
    function snapshot() {
        return JSON.stringify({
            structures: Probe.rows(Session.project.structures).map(row => [row.name, row.structure.text.text]),
            experiments: Probe.rows(Session.project.experiments).map(row => [row.name, row.experiment.text.text]),
            undo: Session.project.canUndo
        });
    }
    function test_f_cubic_presets() {
        openPopup("f-cubic");
        const combo = pcontrol("magnetic.k");
        const texts = Array.from({
            length: combo.count
        }, (_, i) => combo.textAt(i).replace(/\s/g, ""));
        for (const expected of ["(0,0,0)", "X(0,1,0)", "L(1/2,1/2,1/2)", "W(1/2,1,0)", "K(3/4,3/4,0)"])
            verify(texts.some(text => text.includes(expected)), "The rendered F-centred presets use the independent reciprocal-lattice convention: " + expected);
    }
    function test_a_setting_presets() {
        openPopup("a-setting");
        const combo = pcontrol("magnetic.k");
        const texts = Array.from({
            length: combo.count
        }, (_, i) => combo.textAt(i).replace(/\s/g, ""));
        verify(texts.some(text => text.includes("Y(0,0,1)")), "The A-setting Y point follows the independent axis permutation");
    }
    function graph(kind, vector) {
        openPopup();
        wave(vector);
        const expected = Oracle.expected[kind].nodes;
        const levels = pcontrol("magnetic.levels");
        compare(levels.currentText, "Maximal only", "The graph opens with Maximal only selected");
        compare(shownNodes().length, expected.filter(node => node.row === 1).length, "Only the independent maximal classes are initially visible");
        const renderedEdges = () => Render.descendants(popup().contentItem).filter(item => item.visible && item.corners !== undefined && item.corners.length >= 2);
        compare(renderedEdges().length, 0, "Maximal-only cards render without subgroup edges");
        const footer = pcontrol("magnetic.add");
        const footerY = footer.mapToItem(popup().contentItem, 0, 0).y;
        verify(popup().height <= app.height * .91 && popup().width <= app.width * .91, "The dialog fits within the window with an outer margin");
        choose(levels, "All");
        const nodes = shownNodes();
        compare(nodes.length, expected.length, "Expanding levels retains every independently enumerated class");
        const headers = Render.descendants(popup().contentItem).filter(item => item.visible && /^magnetic\.level\./.test(item.objectName));
        compare(headers.length, Math.max(...expected.map(node => node.row)), "Every independent subgroup level has a title");
        for (let i = 0; i < headers.length; ++i) {
            const count = expected.filter(node => node.row === i + 1).length;
            verify(headers[i].font.bold && !Render.descendants(headers[i].parent).some(item => item.checked !== undefined), "The level title is bold and has no level-selection checkbox");
            verify(headers[i].text.includes(count + (count === 1 ? " group" : " groups")), "Each level header displays its independent group count");
        }
        const actualRows = nodes.map(item => {
            const text = Render.texts(item).map(label => label.text).join(" ");
            const identity = text.match(/(\d+\.\d+)(?:\s*#(\d+))?/);
            verify(identity !== null && /type (I|II|III|IV)\b/.test(text), "Each compact card displays BNS identity and magnetic type");
            const level = headers.filter(header => header.mapToItem(popup().contentItem, 0, 0).y < item.mapToItem(popup().contentItem, 0, 0).y).length;
            return [identity[1], level, /\bFM\b/.test(text)].join("|");
        }).sort();
        const expectedRows = expected.map(node => [node.bns, node.row, node.fm].join("|")).sort();
        compare(actualRows.join(";"), expectedRows.join(";"), "Rendered levels and FM marks equal the independent signed census");
        const withChildren = expected.findIndex((node, i) => node.parents.length > 0 && expected.some(child => child.parents.includes(i)) && expected.filter(peer => peer.bns === node.bns).length === 1);
        verify(withChildren >= 0, "The independent graph has an unambiguous interior group with ancestors and descendants");
        const card = nodes.find(node => node.data_.bns === expected[withChildren].bns);
        verify(card, "The graph renders the independently identified interior group");
        const labels = Render.texts(card).filter(item => item.visible && item.text !== "thumbtack");
        compare(labels.length, 2, "A card displays its symbol and identity in two lines");
        verify(labels.every(item => item.horizontalAlignment === Text.AlignLeft) && !labels[0].font.bold, "Both card labels align left and the group symbol uses normal weight");
        compare(String(card.color), String(Style.Colors.chartBackground), "An unselected card uses the chart background");
        verify(!Render.descendants(card).some(item => item.checked !== undefined), "A group card has no checkbox");
        verify(!findChild(popup().contentItem, "magnetic.details"), "The popup has no card details strip");

        Ui.scrollIntoView(card);
        const point = Ui.clickPoint(card);
        verify(point, "The interior card is reachable by pointer");
        mouseMove(card, point.x, point.y);
        const tip = findChild(card, card.objectName + ".tooltip");
        tryVerify(() => tip && tip.visible && /Co1.*[Mm][xyz]/.test(tip.text), 3000, "Hover reveals the chosen site's signed moment form in the card tooltip");
        const walk = next => {
            const reached = new Set([withChildren]);
            for (const i of reached)
                for (const j of next(i))
                    reached.add(j);
            return reached;
        };
        const ancestors = walk(i => expected[i].parents);
        const descendants = walk(i => expected.map((node, j) => node.parents.includes(i) ? j : -1).filter(j => j >= 0));
        const lineage = [];
        for (const [i, node] of expected.entries()) {
            for (const parent of node.parents) {
                if (ancestors.has(i) && ancestors.has(parent) || descendants.has(i) && descendants.has(parent))
                    lineage.push(expected[parent].bns + ">" + node.bns);
            }
        }
        const edges = () => renderedEdges().map(edge => {
            const first = edge.corners[0], last = edge.corners[edge.corners.length - 1];
            const source = nodes.find(node => node.x + node.width / 2 === first.x && node.y + node.height === first.y);
            const target = nodes.find(node => node.x === last.x && node.y + node.height / 2 === last.y);
            verify(source && target, "Every visible lineage edge terminates at two actual cards");
            return source.data_.bns + ">" + target.data_.bns;
        }).sort();
        compare(edges(), lineage.sort(), "The hovered interior card shows exactly the independent ancestor and descendant edges");
        const pin = findChild(card, card.objectName + ".pin");
        verify(pin && pin.visible, "A hovered card exposes its pin");
        press(pin);
        mouseMove(levels, levels.width / 2, levels.height / 2);
        compare(edges(), lineage, "Moving the pointer keeps the pinned lineage");
        const net = pcontrol("magnetic.netMoment");
        choose(net, expected[withChildren].fm ? "Zero" : "Ferromagnetic");
        tryVerify(() => !card.visible && !pin.on, 2000, "A net filter that hides a pinned card also drops its pin");
        choose(net, "Any");

        press(card);
        compare(popup().selected.length, 1, "A click selects exactly the clicked card");
        compare(String(card.color), String(Style.Colors.themeAccent), "The selected card uses the app accent fill");
        verify(labels.every(item => String(item.color) === String(Qt.rgba(1, 1, 1, 1))), "A selected card draws white text");
        verify(footer.text.includes("1"), "The fixed Add button shows the selected count");
        compare(footer.mapToItem(popup().contentItem, 0, 0).y, footerY, "Changing levels and selecting a card keeps the footer fixed");
        press(card);
        compare(popup().selected.length, 0, "Clicking the selected card again clears it");
        press(pcontrol("magnetic.listView"));
        const list = pcontrol("magnetic.list");
        compare(list.count, expected.length, "The list retains every class shown by the expanded graph");
        verify(/Co1/.test(Ui.text(popup().contentItem)), "The list has per-site moment columns");
        for (const [label, predicate] of [["Ferromagnetic", node => node.fm], ["Zero", node => !node.fm], ["Any", () => true]]) {
            choose(net, label);
            const filtered = expected.filter(predicate).map(node => node.bns).sort();
            compare(list.count, filtered.length, "List uses the independent class count for " + label);
            press(pcontrol("magnetic.graphView"));
            compare(shownNodes().map(item => item.data_.bns).sort(), filtered, "Graph uses the same independently classified identities for " + label);
            press(pcontrol("magnetic.listView"));
        }
        press(pcontrol("magnetic.graphView"));
        Ui.scrollIntoView(card);
        const finalPoint = Ui.clickPoint(card);
        verify(finalPoint, "The interior card is still reachable after the view switches");
        mouseMove(card, finalPoint.x, finalPoint.y);
        tryVerify(() => pin.visible, 2000, "The real pointer restores the card pin");
        press(pin);
        tryVerify(() => pin.on, 2000, "The card is pinned before pressing Escape");
        keyClick(Qt.Key_Escape);
        tryVerify(() => !!popup() && !pin.on, 2000, "Escape unpins the lineage while leaving the popup open");
    }
    function test_half_graph() {
        graph("half", "1/2,0,0");
    }
    function test_third_graph() {
        graph("third", "1/3,0,0");
    }
    function selectTwo() {
        wave("1/2,0,0");
        const nodes = shownNodes().filter(item => item.opacity > .9);
        verify(nodes.length >= 2, "The synthetic parent offers multiple selectable candidates");
        press(nodes[0]);
        press(nodes[1]);
        choose(pcontrol("magnetic.startMoments"), "Zero");
    }
    function test_add_links_and_undo() {
        openPopup();
        const before = snapshot();
        const originalBank = Probe.rows(Session.project.experiments).find(row => row.name === "first").experiment;
        const originalProfile = originalBank.measCalcPoints().calc.slice();
        const originalWeight = Probe.rows(originalBank.linkedStructures).find(row => row.structureId === "parent").weightFraction.value;
        verify(originalProfile.length > 0, "The nuclear control has a calculated profile before Add");
        selectTwo();
        press(pcontrol("magnetic.add"));
        tryVerify(() => !popup(), 1000, "Successful Add closes the popup: " + (popup()?.refusal ?? ""));
        tryCompare(Session.project, "calculating", false, 3000, "Added candidates publish their live calculations");
        const structures = Probe.rows(Session.project.structures);
        compare(structures.length, 4, "Two children are added beside the parent and unrelated phase");
        const children = structures.filter(row => row.name.startsWith("parent_"));
        compare(children.length, 2, "Each selected candidate receives its parent and BNS based name");
        for (const bank of Probe.rows(Session.project.experiments)) {
            const links = Probe.rows(bank.experiment.linkedStructures);
            compare(links.length, 4, "Every existing parent link gains both candidates");
            compare(links.find(row => row.structureId === "parent").enabled, false, "The parent remains linked and disabled");
            compare(links.find(row => row.structureId === "unrelated").enabled, true, "An unrelated enabled phase stays enabled");
            const added = links.filter(row => row.structureId.startsWith("parent_"));
            compare(added.filter(row => row.enabled).length, 1, "Only the first added candidate is enabled in each linked bank");
            for (const row of added)
                compare(row.scale.value, bank.name === "first" ? .9 : 2.1, "Each two-cell candidate uses the independently required S divided by four");
            const textures = Probe.rows(bank.experiment.preferredOrientation).filter(row => row.structureId.startsWith("parent_"));
            compare(textures.length, 2, "Both added candidates retain their texture rows");
            for (const row of textures) {
                compare([row.indexH, row.indexK, row.indexL].join(","), "2,1,0", "The child texture axis is D transpose times the parent axis");
                compare(row.marchR.value, .7, "The child's texture value is inherited");
                verify(row.marchR.free, "The carried texture parameter remains in the free set");
            }
        }
        const changedBank = Probe.rows(Session.project.experiments).find(row => row.name === "first").experiment;
        const active = Probe.rows(changedBank.linkedStructures).find(row => row.enabled && row.structureId.startsWith("parent_"));
        compareProfile(changedBank.measCalcPoints().calc, originalProfile);
        verify(Math.abs(active.weightFraction.value - originalWeight) < 1e-10, "S divided by N squared also preserves the parent weight fraction");
        for (const child of children)
            for (const row of Probe.rows(child.structure.atomSiteMoments))
                for (const axis of ["mx", "my", "mz"])
                    compare(row[axis].value, 0, "Moments Off writes zero to every added child component");
        Ui.click(test, Probe, app, "appBar.button.undo");
        tryCompare(Session.project, "calculating", false, 3000, "Undo restores the live project calculation");
        compare(snapshot(), before, "Undo restores all saved structures, links, texture rows and prior history");
    }
    function test_add_unlinked() {
        openPopup("unlinked");
        selectTwo();
        press(pcontrol("magnetic.add"));
        tryVerify(() => !popup(), 1000, "An unlinked parent can add candidates");
        compare(Probe.rows(Session.project.experiments).length, 0, "Add invents no experiment or link for an unlinked parent");
    }
    function test_texture_overflow_is_atomic() {
        openPopup("overflow");
        const before = snapshot();
        selectTwo();
        press(pcontrol("magnetic.add"));
        verify(!!popup(), "An invalid mapped texture axis keeps the popup open");
        verify(/1002/.test(Ui.text(popup().contentItem)) && /1000/.test(Ui.text(popup().contentItem)), "The refusal names the mapped texture axis and its bound");
        compare(snapshot(), before, "A failed candidate batch changes neither the project nor Undo history");
    }
    function test_structure_analysis_entry_keeps_k_in_popup() {
        openInput("find-k");
        const page = Ui.page(app);
        verify(!Probe.objectsWithProperty(page, "categoryId").some(item => item.shown && item.categoryId === "propagation_vectors"), "A Crystal structure has no Propagation vectors group");
        const atomGroup = group("atom_site");
        const atomTable = findChild(atomGroup, "atomSites.list");
        verify(atomTable && atomTable.headerItem && atomTable.count === 1, "The original Atom sites table supplies the one cobalt row");
        const headerUids = table => Render.descendants(table.headerItem).filter(item => item.uid && item.uid.startsWith("atom_site.")).map(item => item.uid);
        const sourceHeaders = headerUids(atomTable);
        group("space_group");
        const action = findChild(page, "spaceGroup.magneticAnalysis");
        verify(action && action.visible, "The Crystal Space group exposes Magnetic symmetry analysis");
        press(action);
        tryVerify(() => !!popup(), 2000, "The Space group button independently opens magnetic symmetry analysis");
        compare(Ui.page(app), page, "The Structure analysis opens over the current page");
        const toolbar = pcontrol("magnetic.toolbar");
        const names = ["k", "sites", "levels", "netMoment", "startMoments", "graphView", "listView"];
        const controls = names.map(name => pcontrol("magnetic." + name));
        verify(controls.every(item => item.visible && item.parent === toolbar), "Every symmetry control is in the same toolbar");
        const bounds = controls.map(item => item.mapToItem(toolbar, 0, item.height / 2));
        verify(bounds.every(point => Math.abs(point.y - bounds[0].y) < 1), "The controls align in one horizontal row");
        const gaps = bounds.slice(1).map((point, i) => point.x - bounds[i].x - controls[i].width);
        verify(gaps.every(gap => gap > 0) && [1, 3, 4].every(i => gaps[i] > Math.max(gaps[0], gaps[2], gaps[5])), "The toolbar orders k and sites, levels and net moment, start, then Graph and List");
        verify(/^k:.*\(0,0,0\)·a,b,c$/.test(controls[0].displayText.replace(/\s/g, "")), "The closed k choice shows the independent Gamma cell a,b,c: " + controls[0].displayText);
        verify(!findChild(toolbar, "magnetic.zeroMoment"), "Zero-only groups have no header toggle");
        const sites = controls[1];
        tryCompare(sites, "enabled", true, 5000, "The initial graph completes before opening the sites toolbar control");
        press(sites);
        tryCompare(sites.popup, "opened", true, 2000, "The actual sites toolbar button opens the Atom sites dropdown");
        const table = sites.popup.contentItem;
        compare(headerUids(table), sourceHeaders, "The dropdown renders the Atom sites headers in their original order");
        compare(table.columnKinds, atomTable.columnKinds, "The site table keeps the Atom sites column layout, including the trailing control slot");
        let cobalt;
        tryVerify(() => {
            table.forceLayout();
            cobalt = table.itemAtIndex(0);
            return !!cobalt;
        }, 2000, "The selectable cobalt row reaches the dropdown");
        const choice = findChild(cobalt, "magnetic.site.0");
        verify(choice && choice.checked && !choice.enabled, "The sole chosen cobalt site stays checked");
        const cells = Render.descendants(cobalt).filter(item => item.visible);
        const locked = cells.filter(item => item.locked === true && item.item);
        const number = cells.find(item => item.marksCurrentRow && String(item.text) === "1");
        const label = cells.find(item => item.text === "Co1");
        const x = item => item.mapToItem(cobalt, 0, 0).x;
        verify(number && label && x(number) < x(label), "The dropdown leads with the grey-style row number and the actual site name");
        compare(locked.length, 4, "The dropdown renders the coordinates and occupancy as read-only Atom sites cells");
        verify(locked.every(cell => x(cell) < x(choice)) && x(label) < x(choice), "The selection checkbox follows the last scientific value column");
        sites.popup.close();
        verify(!/Find k from data/i.test(Ui.text(popup().contentItem)), "Peak search is available from the experiment pattern");
    }
    function test_type_iv_letters_and_coordinate_edit() {
        openInput("type-iv");
        const owner = group("atom_site");
        const structure = Session.project.currentStructure;
        let row = Probe.rows(structure.atomSites)[0];
        compare(row.wyckoffLetter, "d", "The displayed type IV letter is the independent P_c nma mirror letter");
        compare(row.fractY.value, .25, "The mirror coordinate is exactly one quarter");
        verify(row.fractX.fittable && !row.fractY.fittable && row.fractZ.fittable, "Only the independent mirror coordinates can be fitted");
        const cell = Render.descendants(owner).find(item => item.objectName === "atomSite.fractX.0");
        verify(cell !== undefined, "The actual coordinate editor is rendered");
        const dialog = Ui.parameterPopup(test, cell);
        const editor = Ui.parameterValue(test, cell, dialog);
        Ui.focusParameter(test, editor);
        keyClick(Qt.Key_A, Qt.ControlModifier);
        for (const character of "0.173")
            keyClick(character.charCodeAt(0));
        keyClick(Qt.Key_Return);
        dialog.close();
        tryVerify(() => Math.abs(Probe.rows(structure.atomSites)[0].fractX.value - .173) < 1e-10, 1000, "The legal coordinate edit reaches the live type IV site");
        row = Probe.rows(structure.atomSites)[0];
        compare(row.fractY.value, .25, "A legal coordinate edit preserves the exact mirror tie");
        compare(row.wyckoffLetter, "d", "A coordinate edit on the orbit preserves its derived letter");
        verify(structure.text.text.includes("0.173"), "The saved structure text publishes the accepted coordinate");
    }
    function test_unverified_letter_is_retracted() {
        openInput("unverified");
        const owner = group("atom_site");
        const row = Probe.rows(Session.project.currentStructure.atomSites)[0];
        compare(row.wyckoffLetter, ".", "A wrong BNS identity retracts the stale magnetic letter");
        const letter = Render.descendants(owner).find(item => item.objectName === "atomSite.wyckoffLetter.0");
        verify(letter !== undefined, "The unknown letter remains visibly represented");
        verify(letter.readOnly === true || letter.editable === false || !letter.enabled, "An unverified operator-defined letter cannot be edited as an ordinary table letter");
    }
    function checkA10Refusal(message) {
        verify(/Crystal structure it came from/i.test(message) && /Structure page.*Space group.*Magnetic symmetry analysis/i.test(message) && /Experiment.*Pattern.*Mark peaks for k/i.test(message), "The refusal identifies both analysis routes and describes the original Crystal structure by role");
    }
    function test_k_field_refusal_is_atomic() {
        openInput("type-iv", false);
        const structure = Session.project.currentStructure;
        const before = snapshot();
        verify(!structure.propagationVectors.setVector(0, "0,0,1/3"), "A k requiring another magnetic cell is refused in the existing structure");
        checkA10Refusal(structure.propagationVectors.refusal);
        compare(snapshot(), before, "A refused k edit preserves fields, operators, cell, links and Undo history");
        verify(structure.propagationVectors.setVector(0, "0,0,1/2"), "The admitted same-cell propagation vector remains editable");
    }
    function test_bns_field_refusal_is_atomic() {
        openInput("type-iv", false);
        const structure = Session.project.currentStructure;
        const before = snapshot();
        const index = structure.magneticGroupNumbersBns.indexOf("62.442");
        verify(index >= 0, "The independent grey-group BNS number is offered");
        verify(!structure.setMagneticGroup(index), "The BNS control cannot silently change the existing nonzero-k cell contract");
        checkA10Refusal(structure.magneticGroupRefusal);
        compare(snapshot(), before, "A refused BNS edit preserves the complete project and Undo history");
    }
    function compareProfile(actual, expected) {
        compare(actual.length, expected.length, "The child and parent profiles share the observed grid");
        let norm = 0, error = 0;
        for (let i = 0; i < expected.length; ++i) {
            norm += expected[i] * expected[i];
            error += (actual[i] - expected[i]) * (actual[i] - expected[i]);
        }
        verify(norm > 0, "The nuclear profile control observes nonzero intensity");
        verify(Math.sqrt(error / norm) < 1e-8, "Moments Off with S divided by N squared and the mapped texture preserves the nuclear profile");
    }
    function mixed(name) {
        openPopup(name);
        const before = snapshot();
        selectTwo();
        press(pcontrol("magnetic.add"));
        verify(!!popup(), "A linked single-crystal experiment refuses the whole candidate Add");
        verify(/single.crystal/i.test(Ui.text(popup().contentItem)), "The refusal names the parent-indexed single-crystal reflections");
        compare(snapshot(), before, "A mixed-project refusal preserves structures, links, texture and Undo history");
    }
    function test_single_crystal_enabled_refuses() {
        mixed("mixed-enabled");
    }
    function test_single_crystal_disabled_refuses() {
        mixed("mixed-disabled");
    }
    function test_added_children_reopen() {
        openPopup();
        selectTwo();
        press(pcontrol("magnetic.add"));
        tryVerify(() => !popup(), 1000, "The candidate batch is added before saving: " + (popup()?.refusal ?? ""));
        tryCompare(Session.project, "calculating", false, 3000, "The added children finish their live calculation");
        const bank = Probe.rows(Session.project.experiments).find(row => row.name === "first").experiment;
        const profile = bank.measCalcPoints().calc.slice();
        const before = Probe.rows(Session.project.experiments).map(row => row.experiment.text.text).join("\n");
        verify(Session.save(), "The normal Save persists the added candidates and links");
        Session.closeProject();
        verify(Session.openProject(inputUrl), "The saved candidate project reopens through the normal loader");
        tryCompare(Session.project, "calculating", false, 3000, "Reopened candidates publish a current calculation");
        compare(Probe.rows(Session.project.experiments).map(row => row.experiment.text.text).join("\n"), before, "Reopen preserves all candidate links, scales and texture rows");
        compareProfile(Probe.rows(Session.project.experiments).find(row => row.name === "first").experiment.measCalcPoints().calc, profile);
    }

    function chartControl(name) {
        let item;
        tryVerify(() => {
            item = Ui.control(Probe, app, name);
            return item !== null && item !== undefined;
        }, 2000, "Experiment Pattern exposes " + name);
        return item;
    }
    function pressChart(item) {
        const at = Ui.clickPoint(item);
        verify(at && item.enabled, "The chart action reaches an exposed enabled control");
        mouseClick(item, at.x, at.y);
    }
    function openedVectors() {
        return Probe.objectsWithProperty(app, "opened").find(item => item.opened && item.objectName === "chart.kVectorPopup");
    }
    function openPattern(name = "find-k") {
        openInput(name, false);
        const first = Probe.rows(Session.project.experiments).findIndex(row => row.name === "first");
        verify(first >= 0, "The measured fixture contains the first powder experiment");
        Session.project.currentExperimentIndex = first;
        AppState.open(AppState.Page.Experiment);
        let owner;
        tryVerify(() => {
            owner = Render.descendants(Ui.page(app)).find(item => item.pageName === "experiment" && item.current);
            return !!owner;
        }, 3000, "The active loader exposes the Experiment page");
        let tab;
        tryVerify(() => {
            tab = owner.pageViewItem ? Array.from(owner.pageViewItem.tabs).find(item => item.objectName === "mainArea.tab.pattern") : null;
            return tab && tab.enabled && Ui.rendered(tab);
        }, 3000, "The Experiment page renders its Pattern tab");
        if (!tab.checked)
            pressChart(tab);
        tryCompare(tab, "checked", true, 2000, "The experiment's Pattern tab is active");
        const view = owner.pageViewItem;
        let chart;
        tryVerify(() => {
            chart = Render.descendants(view).find(item => item.objectName === "chart" && item.shown && Ui.rendered(item) && item.axisProject === Session.project && !item.report);
            return !!chart;
        }, 2000, "The current experiment owns the visible live powder chart");
        return chart;
    }
    function startMarking(chart) {
        Ui.click(test, Probe, app, "sideBar.tab.extras");
        Ui.expandGroup(test, Probe, app, "group.k_search");
        const sidebar = Ui.find(Ui.page(app), "group.k_search", true);
        compare(sidebar.title, "k-vector search", "Experiment Extra names the search group");
        const tools = Render.descendants(chart.imageToolbar).filter(item => item.visible && (/findK|kSearch/i.test(item.objectName) || ["Find k", "Clear", "Mark peaks"].includes(item.text)));
        compare(tools.length, 0, "The chart toolbar has no propagation-vector search controls");
        const toggle = sidebarControl("mark");
        const table = sidebarControl("list");
        const find = sidebarControl("findK");
        verify(toggle.checkable && toggle.enabled && !toggle.checked, "The search starts with marking off");
        compare(toggle.text, "Mark peaks", "The inactive button offers Mark peaks");
        compare(table.count, 0, "The search table starts empty");
        verify(!table.enabled && !find.enabled, "The visible empty table and Find k start disabled");
        press(toggle);
        tryCompare(toggle, "checked", true, 2000, "The Extra group starts chart marking");
        compare(toggle.text, "Stop marking", "The active button offers Stop marking");
        compare(find.text, "Find k", "The search uses its visible Find k label");
        return sidebar;
    }
    function sidebarControl(name) {
        const sidebar = Ui.find(Ui.page(app), "group.k_search", true);
        verify(sidebar, "The Experiment sidebar owns the propagation vector search group");
        const control = findChild(sidebar, "kSearch." + name);
        verify(control && control.visible, "The active search group exposes its " + name + " control");
        return control;
    }
    function sidebarPeak(table, index, angle, role) {
        table.positionViewAtIndex(index, ListView.Contain);
        let row;
        tryVerify(() => {
            table.forceLayout();
            row = table.itemAtIndex(index);
            return !!row;
        }, 2000, "The marked peak is instantiated in the sidebar table");
        Ui.scrollIntoView(row);
        const cells = Render.texts(row).filter(Ui.rendered).map(label => label.text);
        const x = Number(cells[1]);
        const d = 1.54 / (2 * Math.sin(x * Math.PI / 360));
        verify(Math.abs(x - angle) <= .056, "The peak row displays the independently positioned 2θ in degrees");
        verify(Math.abs(Number(cells[2]) - d) < .005, "The same peak row displays the Bragg d-spacing in angstroms");
        compare(cells[3], role, "The same peak row displays its expected indexing role");
        return row;
    }
    function markedPeaks(chart) {
        return Array.from(chart.peakMarks, index => chart.peakCandidates[index]);
    }
    function chartAxis(chart) {
        const axis = findChild(chart, "chart.axis.x");
        verify(axis && axis.max > axis.min, "The real rendered chart has a usable horizontal axis");
        return axis;
    }
    function clickPeak(chart, x) {
        const layer = chartControl("chart.peaks");
        const point = Math.round(layer.px(x));
        verify(point > 0 && point < layer.width, "The reference position falls on the visible native chart axis");
        const axis = chartAxis(chart);
        const clicked = axis.min + point / layer.width * (axis.max - axis.min);
        mouseClick(layer, point, layer.height / 2);
        return clicked;
    }
    function checkMarkingNavigation(chart) {
        const layer = chartControl("chart.peaks");
        const axis = chartAxis(chart);
        const full = [axis.min, axis.max];
        const marks = () => JSON.stringify(markedPeaks(chart).map(peak => peak.x));
        const before = marks();
        const changes = markingSpy.createObject(test, {
            target: chart.axisProject,
            signalName: "kSearchChanged"
        });
        verify(changes.valid, "The gesture control observes mark changes from the real project");
        mouseWheel(layer, layer.width * .4, layer.height * .55, 0, 120);
        tryVerify(() => axis.max - axis.min < .85 * (full[1] - full[0]), 2000, "The wheel zooms the real chart while marking");
        compare(marks(), before, "Wheel zoom changes no marks");
        pressChart(chartControl("chart.toolbar.zoom"));
        const wheelSpan = axis.max - axis.min;
        mouseDrag(layer, layer.width * .2, layer.height * .2, layer.width * .55, layer.height * .55, Qt.LeftButton);
        tryVerify(() => axis.max - axis.min < .65 * wheelSpan, 2000, "Dragging a zoom box still narrows the chart while marking");
        compare(marks(), before, "A zoom drag does not add a mark");
        pressChart(chartControl("chart.toolbar.pan"));
        const zoomed = axis.min;
        mouseDrag(layer, layer.width * .5, layer.height * .55, layer.width * .12, 0, Qt.LeftButton);
        tryVerify(() => axis.min < zoomed - .1, 2000, "Dragging in pan mode moves the zoomed range while marking");
        compare(marks(), before, "A pan drag does not add a mark");
        mouseDoubleClickSequence(layer, layer.width * .55, layer.height * .55, Qt.LeftButton);
        verify(waitForRendering(app.contentItem), "The chart remains rendered after a double-click with marking on");
        compare(marks(), before, "A double-click is not treated as a single marking tap");
        mouseClick(layer, layer.width * .5, layer.height * .55, Qt.RightButton);
        tryVerify(() => Math.abs(axis.min - full[0]) < .01 && Math.abs(axis.max - full[1]) < .01, 2000, "The normal chart reset restores the initial range with marking enabled");
        compare(marks(), before, "Reset leaves the same marks at their measured angles");
        compare(changes.count, 0, "Viewport gestures never emit even a transient change to the marks");
        changes.destroy();
    }
    function runSearch() {
        const findK = sidebarControl("findK");
        compare(findK.text, "Find k", "The Experiment group has a Find k button");
        press(findK);
        tryVerify(() => !!openedVectors() && !openedVectors().searching, 8000, "Find k opens and completes a bounded ranked table");
        const results = openedVectors();
        verify(results.rows.length > 0 && results.rows.length <= 10, "The table offers a short list of matching vectors");
        verify(results.rows.every(row => row.parentCells >= 1 && row.parentCells <= 24), "Every offered vector has a buildable magnetic cell");
        const firstOther = results.rows.findIndex(row => row.stage !== 1);
        verify(firstOther < 0 || results.rows.slice(firstOther).every(row => row.stage !== 1), "Special points precede general k rows");
        return results;
    }
    function test_find_k_marks_without_kept_fit() {
        const chart = openPattern();
        verify(!Session.project.fit.canUndo, "No fit has been kept for this measured bank");
        const before = snapshot();
        startMarking(chart);
        const peaks = markedPeaks(chart);
        const satellite = 13.285477100052015;
        const index = peaks.findIndex(peak => Math.abs(peak.x - satellite) < .051);
        verify(index >= 0, "The independently calculated half-period satellite is pre-marked from measured data");
        const table = sidebarControl("list");
        compare(table.count, peaks.length, "Every chart pre-mark has one sidebar row");
        Ui.scrollIntoView(table.headerItem);
        const headings = Render.texts(table.headerItem).filter(Ui.rendered).map(label => label.text);
        compare(headings, ["2θ (°)", "d (Å)", "Role", "minus-circle"], "The table shows angle, spacing and role, with remove-all in the final header");
        checkMarkingNavigation(chart);
        const x = peaks[index].x;
        const peakLayer = chartControl("chart.peaks");
        const mark = findChild(peakLayer, "chart.peak." + chart.peakMarks[index]);
        verify(mark && mark.visible, "The observed satellite has a visible line and pin");
        const bars = Array.from(mark.children).filter(item => item.visible && item.color !== undefined);
        compare(bars.length, 2, "Each chart mark draws a line and a pin");
        const widths = bars.map(item => item.width);
        const colors = bars.map(item => String(item.color));
        mouseMove(peakLayer, peakLayer.px(x), peakLayer.height * .75);
        tryVerify(() => bars.every(item => String(item.color) === String(Style.Colors.themeForegroundMinor)), 2000, "Hovering low on the line greys both the mark line and its pin");
        verify(colors.some(color => color !== String(Style.Colors.themeForegroundMinor)), "Hover changes the actual mark color");
        compare(bars.map(item => item.width), widths, "Hovering leaves the drawn line and pin widths unchanged");
        verify(!/click to remove/i.test(Ui.text(peakLayer)), "A hovered line offers no removal tooltip");
        const rowIndex = peaks.filter(peak => peak.x < x).length;
        const row = sidebarPeak(table, rowIndex, satellite, "forbidden reflection");
        const remove = findChild(row, "kSearch.remove." + rowIndex);
        verify(remove, "The suggested row offers its own remove button");
        press(remove);
        compare(table.count, peaks.length - 1, "Removing the suggested row drops exactly one sidebar entry");
        verify(!markedPeaks(chart).some(peak => peak.x === x), "Removing the suggested row unmarks that exact peak on the chart");

        const layer = chartControl("chart.peaks");
        const axis = chartAxis(chart);
        mouseWheel(layer, layer.px(x), layer.height * .55, 0, 960);
        tryVerify(() => (axis.max - axis.min) / layer.width < .035, 2000, "Zoom resolves the offset tap from the measured maximum");
        const offset = clickPeak(chart, x + .07);
        verify(Math.abs(offset - x) > .04 && Math.abs(offset - x) < .1, "The tap falls beside the maximum within the fixture's known half width");
        tryCompare(table, "count", peaks.length, 2000, "An offset tap restores the observed peak to the sidebar");
        verify(markedPeaks(chart).some(peak => Math.abs(peak.x - x) < 1e-8), "The offset tap lands at the measured maximum");

        const blank = 16.2;
        const clicked = clickPeak(chart, blank);
        tryCompare(table, "count", peaks.length + 1, 2000, "A click on a flat interval still creates a mark");
        const free = markedPeaks(chart).findIndex(peak => Math.abs(peak.x - clicked) < .02);
        verify(free >= 0, "With no maximum nearby the chart keeps the clicked angle");
        sidebarPeak(table, free, blank, "added by hand");
        mouseClick(layer, Math.round(layer.px(x)), layer.height * .85);
        tryCompare(table, "count", peaks.length, 2000, "Clicking down the line drops the snapped sidebar row");
        verify(!markedPeaks(chart).some(peak => Math.abs(peak.x - x) < 1e-8), "The click drops only the snapped maximum");
        clickPeak(chart, clicked);
        tryCompare(table, "count", peaks.length - 1, 2000, "Clicking the new free mark removes it");
        const toggle = sidebarControl("mark");
        const kept = JSON.stringify(markedPeaks(chart));
        const occupiedHeight = table.height;
        press(toggle);
        tryCompare(toggle, "checked", false, 2000, "Stop marking turns off marking mode");
        verify(table.visible && chartControl("chart.peaks").visible, "Stopping leaves the table and plotted marks visible");
        compare(JSON.stringify(markedPeaks(chart)), kept, "Stopping keeps the exact current marks");
        press(toggle);
        tryCompare(toggle, "checked", true, 2000, "Mark peaks resumes marking mode");
        compare(JSON.stringify(markedPeaks(chart)), kept, "Resuming an occupied table does not resuggest a removed peak");
        const clear = sidebarControl("clear");
        compare(clear.fontIcon, "minus-circle", "Clear is the remove-all icon in the table heading");
        press(clear);
        compare(table.count, 0, "Clear empties the sidebar table");
        compare(markedPeaks(chart).length, 0, "Clear removes all chart marks");
        compare(snapshot(), before, "Transient marking changes neither the saved model nor Undo history");
        verify(!sidebarControl("findK").enabled && !clear.enabled, "An empty sidebar disables Find k and Clear");
        tryVerify(() => table.height < occupiedHeight, 2000, "Clearing a populated table retracts its row-driven height");
        press(toggle);
        press(toggle);
        tryVerify(() => markedPeaks(chart).some(peak => Math.abs(peak.x - x) < .051), 2000, "Restarting on the empty table suggests the independently known satellite again");
    }
    function test_find_k_mask_excludes_observed_peak() {
        const chart = openPattern();
        const mask = Session.project.currentExperiment.excludedRegions;
        mask.append();
        const row = Probe.rows(mask).length - 1;
        verify(mask.setStart(row, 13) && mask.setEnd(row, 13.6), "The mask covers the independent first satellite");
        startMarking(chart);
        const peaks = markedPeaks(chart);
        verify(peaks.length > 0, "Other unmasked peaks still reach the chart");
        verify(peaks.every(peak => peak.x < 13 || peak.x > 13.6), "An excluded strong peak is not pre-marked");
        clickPeak(chart, 13.285477100052015);
        verify(waitForRendering(app.contentItem), "The chart processes a tap within the excluded interval");
        compare(markedPeaks(chart).map(peak => peak.x), peaks.map(peak => peak.x), "A real click inside the mask adds no mark");
    }
    function test_find_k_disabled_parent_refuses() {
        const chart = openPattern();
        verify(Session.project.currentExperiment.linkedStructures.setEnabled(0, false), "The real edit disables the sole Crystal link");
        const sidebar = startMarking(chart);
        compare(markedPeaks(chart).length, 0, "A disabled parent produces no chart marks");
        Ui.scrollIntoView(sidebarControl("list"));
        verify(/link.*enable.*crystal/i.test(Ui.text(sidebar)), "The sidebar explains that an enabled Crystal link is required");
    }
    function test_find_k_multiple_crystal_links_refuse() {
        const chart = openPattern("popup");
        const links = Probe.rows(Session.project.currentExperiment.linkedStructures);
        verify(links.some(link => link.structureId === "parent" && link.enabled) && links.some(link => link.structureId === "unrelated" && link.enabled), "The measured experiment has two enabled Crystal phases");
        const before = snapshot();
        const sidebar = startMarking(chart);
        compare(markedPeaks(chart).length, 0, "Link order cannot choose a Crystal target when both links are enabled");
        Ui.scrollIntoView(sidebarControl("list"));
        verify(/several.*crystal/i.test(Ui.text(sidebar)), "The sidebar identifies the ambiguous Crystal target");
        verify(!sidebarControl("findK").enabled, "The ambiguous target cannot start indexing");
        compare(snapshot(), before, "Refusing an ambiguous target leaves both links unchanged");
    }
    function indexedTooltip(results, row, index, expected) {
        verify(!findChild(results.contentItem, "chart.kVectorRoles"), "The k dialog has no role details strip");
        const cell = findChild(row, "chart.kVector." + index + ".indexedCell");
        verify(cell && Ui.exposed(cell), "The selected row exposes its actual Indexed cell");
        mouseMove(cell, cell.width / 2, cell.height / 2);
        const tip = findChild(cell, "chart.kVector." + index + ".indexed");
        tryVerify(() => tip && tip.visible, 2500, "Hovering Indexed opens the application's data tooltip");
        const roles = Array.from(tip.contentItem.children).filter(item => item.modelData !== undefined);
        compare(roles.length, results.markedPeaks.length, "The tooltip displays one status for every marked reflection");
        for (const [position, role, indexed] of expected) {
            const text = position.toFixed(2) + "° " + role;
            const match = roles.find(item => Ui.text(item).includes(text));
            verify(match, "The rendered Indexed tooltip lists " + text);
            verify(Render.descendants(match).some(item => item.icon === (indexed ? "check-circle" : "times-circle")), "The row carries the matching app status icon for " + text);
        }
    }
    function test_find_k_gamma_labels_forbidden_and_allowed_marks() {
        const chart = openPattern("find-k-gamma");
        const bank = Session.project.currentExperiment;
        tryVerify(() => !Session.project.calculating && bank.measCalcPoints().calc.some(value => Number.isFinite(value) && value > 0), 3000, "The two-label control uses a current calculated curve");
        startMarking(chart);
        const bragg = d => 360 / Math.PI * Math.asin(1.54 / (2 * d));
        const peaks = markedPeaks(chart).sort((a, b) => a.x - b.x);
        const allowedPosition = bragg(1 / Math.hypot(1 / 6, 1 / 8));
        const table = sidebarControl("list");
        compare(table.count, 2, "The isolated forbidden 001 and allowed 101 excess are both suggested");
        sidebarPeak(table, 0, bragg(8), "forbidden reflection");
        sidebarPeak(table, 1, allowedPosition, "excess on an allowed reflection");
        const allowed = peaks[1];
        const free = clickPeak(chart, 16.2);
        tryCompare(table, "count", 3, 2000, "An off-reflection click adds a third mark to the Gamma coverage witness");
        const results = runSearch();
        const index = results.rows.findIndex(row => row.k === "0,0,0");
        verify(index >= 0, "Gamma indexes both Pnma lattice peaks");
        const list = findChild(results.contentItem, "chart.kVectors");
        list.positionViewAtIndex(index, ListView.Contain);
        let row;
        tryVerify(() => {
            list.forceLayout();
            row = list.itemAtIndex(index);
            return !!row && Ui.exposed(row);
        }, 2000, "The selected k row is instantiated in the visible table");
        verify(row, "The Gamma result is visibly available");
        pressChart(row);
        compare(results.current, index, "A pointer click chooses the actual Gamma row");
        indexedTooltip(results, row, index, [[peaks[0].x, "forbidden reflection", true], [allowed.x, "allowed reflection", true], [free, "not indexed", false]]);
        pressChart(findChild(results.footer, "chart.kVectorPopup.cancel"));
        tryVerify(() => !openedVectors(), 2000, "Closing the vector dialog reveals the updated sidebar");
        sidebarPeak(table, 0, bragg(8), "forbidden reflection");
        const sorted = markedPeaks(chart).map(peak => peak.x).sort((a, b) => a - b);
        const allowedRow = sorted.findIndex(x => Math.abs(x - allowed.x) < 1e-8);
        verify(allowedRow >= 0, "The allowed reflection stays in the marked sidebar");
        sidebarPeak(table, allowedRow, allowedPosition, "allowed reflection");
    }
    function test_find_k_table_analyse_add_stays_on_pattern() {
        const chart = openPattern();
        const project = Session.project;
        const bank = project.currentExperiment;
        const page = Ui.page(app);
        const before = snapshot();
        startMarking(chart);
        const table = sidebarControl("list");
        const peaks = markedPeaks(chart).sort((a, b) => a.x - b.x);
        const satellite = 13.285477100052015;
        const satelliteIndex = peaks.findIndex(peak => Math.abs(peak.x - satellite) < .051);
        verify(satelliteIndex >= 0, "The observed half-period satellite has a marked sidebar row");
        const results = runSearch();
        sidebarPeak(table, satelliteIndex, satellite, "satellite");
        const index = results.rows.findIndex(row => row.k === "1/2,0,0");
        verify(index >= 0, "The independently known half-period vector is offered");
        const list = findChild(results.contentItem, "chart.kVectors");
        list.positionViewAtIndex(index, ListView.Contain);
        let row;
        tryVerify(() => {
            list.forceLayout();
            row = list.itemAtIndex(index);
            return !!row && Ui.exposed(row);
        }, 2000, "The selected k row is instantiated in the visible table");
        verify(row && /1\/2,0,0/.test(Ui.text(row)), "The ranked table renders the non-default half-period vector");
        const cells = Render.texts(row).map(label => label.text);
        verify(cells.includes("2 parent cells") && cells.some(text => /^\d+\.\d{2}$/.test(text)), "The same row renders cell size and numeric misfit");
        verify(results.rows.length > 1, "The ranked fixture supplies an independent row to select before the pointer click");
        if (results.current === index) {
            const other = index === 0 ? 1 : index - 1;
            keyClick(index === 0 ? Qt.Key_Down : Qt.Key_Up);
            tryCompare(results, "current", other, 2000, "The keyboard selects a different row before the pointer check");
        }
        verify(results.current !== index, "The intended half-period row starts unselected");
        pressChart(row);
        tryCompare(results, "current", index, 2000, "A pointer click chooses the previously unselected half-period row");
        indexedTooltip(results, row, index, [[peaks[satelliteIndex].x, "satellite", true]]);
        verify(results.rows.length > 1, "The ranked fixture supplies a second row for keyboard navigation");
        const adjacent = index === 0 ? 1 : index - 1;
        keyClick(index === 0 ? Qt.Key_Down : Qt.Key_Up);
        tryCompare(results, "current", adjacent, 2000, "A keyboard arrow moves the actual ranked table selection");
        keyClick(index === 0 ? Qt.Key_Up : Qt.Key_Down);
        tryCompare(results, "current", index, 2000, "Reversing the arrow restores the selected half-period result");
        pressChart(findChild(results.footer, "chart.kVectorPopup.analyse"));
        tryVerify(() => !!popup() && !popup().busy && popup().found !== null, 5000, "Analyse closes the k table and builds the graph over the chart");
        verify(!openedVectors(), "The k table closes on Analyse");
        compare(popup().k, "1/2,0,0", "The chart hands off the exact selected k");
        compare(Ui.page(app), page, "The analysis overlays Experiment Pattern");
        choose(pcontrol("magnetic.startMoments"), "Zero");
        const node = shownNodes().find(item => item.data_.type === 4 && item.data_.momentAllowed && item.data_.bns);
        verify(node, "The half-period graph offers a selectable type IV candidate");
        const expectedBns = node.data_.bns;
        const expectedSymbol = node.data_.name + " " + expectedBns;
        press(node);
        press(pcontrol("magnetic.add"));
        tryVerify(() => !popup(), 2000, "Add closes magnetic analysis");
        tryCompare(project, "calculating", false, 5000, "The first added candidate gets a current powder calculation");
        compare(project.currentExperiment, bank, "Add retains the chart experiment selection");
        compare(Ui.page(app), page, "Add retains Experiment Pattern");
        const links = Probe.rows(bank.linkedStructures);
        verify(links.some(link => link.structureId === "parent" && !link.enabled), "The original Crystal link remains and is disabled");
        const active = links.filter(link => link.enabled);
        compare(active.length, 1, "Only the first magnetic candidate is enabled");
        const child = project.structureAt(project.structureIndex(active[0].structureId));
        verify(child.magnetic, "The active replacement is magnetic");
        verify(bank.measCalcPoints().calc.some(value => Number.isFinite(value) && value > 0), "A populated calculated powder profile remains on the experiment");
        const vector = Probe.rows(child.propagationVectors)[0];
        verify(vector && /^(?:1\/2|0\.5),\s*0,\s*0$/.test(String(vector.vector)), "The active child publishes the chosen non-default propagation vector");
        let added;
        tryVerify(() => {
            added = Probe.objectsWithProperty(app, "opened").find(item => item.opened && item.objectName === "chart.findK.addedDialog");
            return !!added;
        }, 5000, "Chart Add opens the Magnetic structures added dialog");
        compare(added.title, "Magnetic structures added", "The after-Add report has its own dialog title");
        const entry = findChild(added.contentItem, "chart.findK.added.0");
        verify(entry, "The dialog renders a row for the enabled child");
        compare(child.magneticGroup.number_bns, expectedBns, "The added child has the selected card's BNS number");
        compare(entry.text, child.name + " · " + expectedSymbol, "The after-Add row contains exactly the added name and BNS symbol");
        compare(Render.descendants(added.contentItem).filter(item => /^chart\.findK\.added\.\d+$/.test(item.objectName)).length, 1, "The after-Add report lists exactly the one added structure");
        verify(!/no magnetic intensity|not indexed|allowed reflection/i.test(Ui.text(added.contentItem)), "The removed marked-peak intensity check leaves no notice in the dialog");
        verify(!Ui.find(page, "chart.findK.added", true), "Add leaves no status strip above the chart");
        verify(markedPeaks(chart).length > 0, "After Add the original marks remain available on the recalculated chart");
        const close = findChild(added.footer, "chart.findK.addedDialog.close");
        verify(close && close.enabled && close.text === "Close", "The dialog offers Close");
        const open = findChild(added.footer, "chart.findK.openStructure");
        verify(open && open.text === "Open in Structure page", "The dialog offers an explicit way to open Structure");
        pressChart(open);
        tryVerify(() => Ui.page(app) !== page && chartControl("appBar.tab.structure").checked, 2000, "The explicit Open in Structure action opens the Structure page");
        compare(project.currentStructure, child, "Structure opens the first added magnetic child");
        Ui.click(test, Probe, app, "appBar.button.undo");
        tryCompare(project, "calculating", false, 5000, "Undo republishes the original chart bank");
        compare(snapshot(), before, "Undo from the chart-Add route restores every original scientific record");
    }
    function staleRowChoice(kind) {
        const chart = openPattern();
        startMarking(chart);
        const results = runSearch();
        const project = Session.project;
        const bank = project.currentExperiment;
        if (kind === "zero") {
            const zero = Probe.rows(bank.instrument).find(row => row.parameter && row.parameter.name === "calib_twotheta_offset");
            verify(zero, "The stale-row witness reaches the CW zero parameter");
            zero.parameter.value = .1;
        } else if (kind === "link") {
            verify(bank.linkedStructures.setEnabled(0, false), "The stale-row witness edits the enabled link");
        } else {
            bank.excludedRegions.append();
            const row = Probe.rows(bank.excludedRegions).length - 1;
            verify(bank.excludedRegions.setStart(row, 13) && bank.excludedRegions.setEnd(row, 13.6), "The stale-row witness edits the mask");
        }
        pressChart(findChild(results.footer, "chart.kVectorPopup.analyse"));
        verify(!popup(), "An outdated chart snapshot cannot open analysis");
        verify(/changed.*mark the peaks again/i.test(Ui.text(results.contentItem)), "A stale row tells the user to mark the peaks again");
    }
    function test_find_k_late_choice_after_calibration_edit_refuses() {
        staleRowChoice("zero");
    }
    function test_find_k_late_choice_after_link_edit_refuses() {
        staleRowChoice("link");
    }
    function test_find_k_late_choice_after_mask_edit_refuses() {
        staleRowChoice("mask");
    }
    function noteNodes(name, forms) {
        openPopup(name);
        wave("0,0,0");
        choose(pcontrol("magnetic.levels"), "All");
        const nodes = shownNodes();
        if (name === "note-longitudinal") {
            const expected = Oracle.expected.pmmmOrigin;
            verify(expected.forbidden.length > 0, "The independent Pmmm origin has groups with no allowed axial component");
            compare(nodes.map(node => node.data_.bns).sort(), expected.allowed, "Groups with zero local moment are excluded before showing All");
        }
        for (const form of forms) {
            const node = nodes.find(item => form.test(String(item.data_.moments).replace(/\s/g, "")));
            verify(node !== undefined, "The independent point-group moment form is selectable");
            press(node);
        }
        compare(pcontrol("magnetic.startMoments").currentText, "Non-zero", "Nonzero starting moments are selected by default");
        press(pcontrol("magnetic.add"));
        tryVerify(() => !popup(), 1000, "The note witness is added through the live popup");
        tryCompare(Session.project, "calculating", false, 3000, "The note witness completes its observed reflection calculation");
        return Probe.rows(Session.loadWarnings).map(row => row.message).join("\n");
    }
    function test_start_longitudinal_note() {
        const text = noteNodes("note-longitudinal", [/0,0,[Mm]z/]);
        verify(/no magnetic intensity/i.test(text), "A moment parallel to the sole 001 scattering vector shows the zero-intensity note");
    }
    function test_start_uniform_dilution_has_no_note() {
        const text = noteNodes("note-diluted", [/[Mm]x,0,0/]);
        verify(!/no magnetic intensity/i.test(text), "Uniform dilution leaves the transverse intensity-to-bound ratio equal to one");
    }
    function test_start_below_cancellation_cutoff() {
        const text = noteNodes("note-below", [/[Mm]x,[Mm]y,[Mm]z/]);
        verify(/no magnetic intensity/i.test(text), "The independently constructed ratio below one trillionth shows the note");
    }
    function test_start_above_cancellation_cutoff() {
        const text = noteNodes("note-above", [/[Mm]x,[Mm]y,[Mm]z/]);
        verify(!/no magnetic intensity/i.test(text), "The independently constructed ratio above one trillionth retains its positive signal");
    }
    function test_start_mn3o4_has_no_note() {
        openPopup("note-mn3o4");
        wave("1/2,0,0");
        choose(pcontrol("magnetic.levels"), "All");
        const node = shownNodes().find(item => item.data_.bns === "62.452");
        verify(node !== undefined, "The MAGNDATA Mn3O4 signed group is offered at the published propagation vector");
        press(node);
        compare(pcontrol("magnetic.startMoments").currentText, "Non-zero", "The published positive-intensity witness uses nonzero starting moments");
        press(pcontrol("magnetic.add"));
        tryVerify(() => !popup(), 1000, "The published candidate is added through the live popup");
        tryCompare(Session.project, "calculating", false, 3000, "The Mn3O4 candidate finishes the linked powder calculation");
        const children = Probe.rows(Session.project.structures).filter(row => row.name !== "parent");
        compare(children.length, 1, "The published witness has exactly one added child");
        const moments = Probe.rows(children[0].structure.atomSiteMoments).filter(row => row.ion !== "none");
        verify(moments.length > 0 && moments.every(row => ["mx", "my", "mz"].every(axis => row[axis])), "The added Mn3O4 child exposes the real magnetic rows and their three components");
        verify(moments.some(row => ["mx", "my", "mz"].some(axis => Math.abs(row[axis].value) > 0)), "Mn3O4 retains a nonzero seeded magnetic moment");
        const bank = Probe.rows(Session.project.experiments)[0].experiment;
        const started = bank.measCalcPoints().calc.slice();
        verify(started.length > 0 && started.every(Number.isFinite), "The linked Mn3O4 starting state has a calculable powder pattern");
        const text = Probe.rows(Session.loadWarnings).map(row => row.message).join("\n");
        verify(!/no magnetic intensity/i.test(text), "The linked Mn3O4 positive-signal witness does not show the zero-intensity note");
        for (const row of moments)
            for (const axis of ["mx", "my", "mz"])
                row[axis].value = 0;
        tryCompare(Session.project, "calculating", false, 3000, "The zero-moment control completes its own forward calculation");
        const nuclear = bank.measCalcPoints().calc;
        compare(nuclear.length, started.length, "The positive-intensity control compares the identical observed powder grid");
        verify(started.some((value, i) => value - nuclear[i] > 1e-8), "The starting Mn3O4 moments produce an observed magnetic contribution above the zero-moment control");
    }
    function test_start_unlinked_has_no_note() {
        const text = noteNodes("note-unlinked", [/[Mm]x,[Mm]y,[Mm]z/]);
        verify(!/no magnetic intensity/i.test(text), "An unlinked parent supplies no experiment on which to claim zero magnetic intensity");
    }
    function test_start_batch_notes_are_per_candidate() {
        const text = noteNodes("note-longitudinal", [/0,0,[Mm]z/, /[Mm]x,0,0/]);
        const warnings = Probe.rows(Session.loadWarnings).filter(row => /no magnetic intensity/i.test(row.message));
        compare(warnings.length, 1, "A mixed longitudinal and transverse batch reports only the candidate with zero perpendicular intensity");
        verify(/set.*moments.*hand/i.test(text), "The zero-intensity note tells the user how to supply the starting moments");
    }
    function test_candidate_toggle_preserves_profile_and_free_set() {
        openPopup();
        const bank = Probe.rows(Session.project.experiments).find(row => row.name === "first").experiment;
        const profile = bank.measCalcPoints().calc.slice();
        selectTwo();
        press(pcontrol("magnetic.add"));
        tryVerify(() => !popup(), 1000, "The normal candidate toggle starts from a committed Add: " + (popup()?.refusal ?? ""));
        tryCompare(Session.project, "calculating", false, 3000, "The candidate Add completes its calculation");
        const links = Probe.rows(bank.linkedStructures);
        const candidates = links.map((row, index) => ({
                    row: row,
                    index: index
                })).filter(item => item.row.structureId.startsWith("parent_"));
        compare(candidates.length, 2, "Both added links are present before a normal candidate switch");
        verify(bank.linkedStructures.setEnabled(candidates[0].index, false), "The normal linked-structure edit disables the first candidate");
        verify(bank.linkedStructures.setEnabled(candidates[1].index, true), "The normal linked-structure edit enables the second candidate");
        tryCompare(Session.project, "calculating", false, 3000, "The normal candidate switch publishes its own calculation");
        compareProfile(bank.measCalcPoints().calc, profile);
        const texture = Probe.rows(bank.preferredOrientation).find(row => row.structureId === candidates[1].row.structureId);
        verify(texture.marchR.fittable && texture.marchR.free, "The enabled candidate's inherited March parameter remains eligible and free");
        const inactive = Probe.rows(bank.preferredOrientation).find(row => row.structureId === candidates[0].row.structureId);
        verify(!inactive.marchR.fittable, "The disabled candidate's texture does not enter the live fit vector");
        const free = Probe.rows(Session.project.parameters).filter(row => row.parameter.free && row.parameter.fittable);
        verify(free.some(row => row.parameter === texture.marchR), "The Analysis free set contains the enabled texture parameter");
        verify(!free.some(row => row.parameter === inactive.marchR), "The Analysis free set excludes the disabled texture parameter");
        verify(Session.save(), "The switched candidate state saves normally");
        Session.closeProject();
        verify(Session.openProject(inputUrl), "The switched candidate state reopens normally");
        tryCompare(Session.project, "calculating", false, 3000, "The switched state recalculates after reopen");
        const reopened = Probe.rows(Session.project.experiments).find(row => row.name === "first").experiment;
        compareProfile(reopened.measCalcPoints().calc, profile);
        compare(Probe.rows(reopened.linkedStructures).find(row => row.enabled && row.structureId.startsWith("parent_")).structureId, candidates[1].row.structureId, "Reopen retains the normally selected second candidate");
    }
    function test_three_candidate_texture_failure_is_atomic() {
        openPopup("overflow");
        const before = snapshot();
        wave("1/2,0,0");
        const nodes = shownNodes().filter(item => item.opacity > .9);
        verify(nodes.length >= 3, "The whole-change witness selects three identified candidates");
        for (const node of nodes.slice(0, 3))
            press(node);
        press(pcontrol("magnetic.add"));
        verify(!!popup(), "An invalid disabled member refuses the three-candidate batch");
        compare(snapshot(), before, "Validation of every disabled candidate precedes every live mutation");
    }
    function test_type_iv_adp_cell_and_new_atom_edits_complete() {
        openInput("type-iv");
        const structure = Session.project.currentStructure;
        structure.atomSiteAdps.setType(0, "Uani");
        tryCompare(Session.project, "calculating", false, 3000, "The type IV ADP edit publishes its calculation");
        compare(Probe.rows(structure.atomSiteAdps)[0].adpType, "Uani", "A type IV site admits anisotropic displacement through the live edit path");
        compare(Probe.rows(structure.atomSites)[0].wyckoffLetter, "d", "Changing ADP type preserves the independently known mirror letter");
        structure.cell.lengthA.value = 6.3;
        tryCompare(Session.project, "calculating", false, 3000, "A legal cell edit completes before inspecting its site");
        compare(structure.cell.lengthA.value, 6.3, "The type IV orthorhombic a length stays independently editable");
        compare(Probe.rows(structure.atomSites)[0].fractY.value, .25, "Cell editing retains the completed site mirror");
        structure.atomSites.append();
        compare(Probe.rows(structure.atomSites).length, 2, "The normal new-atom action adds one completed type IV site");
        const added = Probe.rows(structure.atomSites)[1];
        verify(/[abcde]/.test(added.wyckoffLetter), "A new type IV atom receives a derived magnetic-table letter");
        verify(Session.save(), "The edited type IV structure saves normally");
        Session.closeProject();
        verify(Session.openProject(inputUrl), "The edited type IV structure reopens normally");
        compare(Probe.rows(Session.project.currentStructure.atomSites)[0].wyckoffLetter, "d", "Reopen retains the completed original mirror letter");
    }
    function renderedBnsRefusal(byName) {
        openInput("type-iv");
        const owner = group("space_group_magn");
        const number = field(owner, ".number_bns", "Number BNS");
        const name = field(owner, ".name_bns", "Name BNS");
        const control = byName ? name : number;
        const structure = Session.project.currentStructure;
        const index = structure.magneticGroupNumbersBns.indexOf("62.442");
        verify(index >= 0, "The real linked BNS controls include the independent grey Pnma entry");
        const before = snapshot();
        choose(control, control.textAt(index));
        compare(snapshot(), before, "Either rendered BNS field refuses a different translation character without changing the project");
        checkA10Refusal(structure.magneticGroupRefusal);
        verify(/62\.452/.test(value(number)), "A refused BNS name edit leaves the linked BNS number unchanged");
    }
    function test_rendered_bns_number_refusal() {
        renderedBnsRefusal(false);
    }
    function test_rendered_bns_name_refusal() {
        renderedBnsRefusal(true);
    }
    function test_a10_refusal_ignores_renamed_and_reused_parent_name() {
        openInput("refusal-reuse", false);
        const project = Session.project;
        const child = project.structureAt(project.structureIndex("parent_62_452"));
        verify(child && child.magnetic, "The fixture retains the magnetic child's original parent-based name");
        project.structureAt(project.structureIndex("parent")).name = "renamed_origin";
        project.structureAt(project.structureIndex("unrelated")).name = "parent";
        verify(project.structureIndex("renamed_origin") >= 0 && project.structureIndex("parent") >= 0, "The original name is reused by another Crystal structure");
        const before = snapshot();
        const index = child.magneticGroupNumbersBns.indexOf("62.442");
        verify(index >= 0 && !child.setMagneticGroup(index), "A different translation character is still refused");
        checkA10Refusal(child.magneticGroupRefusal);
        verify(!/\b(?:parent|unrelated|renamed_origin)\b/.test(child.magneticGroupRefusal), "Neither the renamed origin nor the structure reusing its old name is named in the refusal");
        compare(snapshot(), before, "The refusal preserves the entire project after the renames");
    }
    function test_equivalent_signed_rows_retain_derived_identity() {
        openInput("type-iv");
        const structure = Session.project.currentStructure;
        const before = Source.typeIv;
        const changed = before.replace(/\bx\s*,\s*y\s*,\s*z\s*,\s*\+?1\b/, "x+1,y,z,+1");
        verify(changed !== before, "The equivalent signed-row edit actually changes an identity representative by an integral translation");
        compare(Session.project.applyText(structure.text.file, changed), "", "The live Text edit accepts an equivalent signed decomposition");
        const after = Session.project.currentStructure;
        compare(after.magneticGroup.number_bns, "62.452", "A verified type IV equivalent signed-row edit retains its BNS identity");
        compare(Probe.rows(after.atomSites)[0].wyckoffLetter, "d", "The equivalent signed-row edit republishes the independent mirror letter");
        compare(Probe.rows(after.atomSites)[0].fractY.value, .25, "The equivalent signed-row edit completes the same exact mirror");
        verify(Session.save(), "The equivalent signed representation saves through the normal writer");
        Session.closeProject();
        verify(Session.openProject(inputUrl), "The equivalent signed representation reopens through the normal loader");
        compare(Session.project.currentStructure.magneticGroup.number_bns, "62.452", "Reopen verifies the signed set instead of comparing operator spellings");
    }
    function test_legacy_grey_fields_obey_current_cell_admission() {
        openInput("unlinked");
        const structure = Session.project.currentStructure;
        verify(structure.setMagnetic(true), "The legacy core kind-switch route constructs the parent's grey group");
        compare(structure.magneticGroup.number_bns, "62.442", "The legacy Pnma grey group retains its established BNS identity");
        const before = snapshot();
        structure.propagationVectors.append();
        const afterAppend = snapshot();
        verify(!structure.propagationVectors.setVector(0, "0,0,1/2"), "A legacy grey structure cannot acquire a half-period k in its existing cell");
        compare(snapshot(), afterAppend, "The grey k refusal preserves the model and its existing Undo history");
        const idx = structure.magneticGroupNumbersBns.indexOf("62.452");
        verify(!structure.setMagneticGroup(idx), "The legacy grey structure cannot gain a doubled magnetic atom set from its BNS field");
        checkA10Refusal(structure.magneticGroupRefusal);
        verify(before.length > 0, "The legacy grey control observes a serialized model before attempted edits");
    }
}
