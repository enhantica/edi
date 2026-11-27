// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
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
        return Render.descendants(popup().contentItem).filter(item => item.visible && /^magnetic\.node\./.test(item.objectName));
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
        const zero = pcontrol("magnetic.zeroMoment");
        if (!zero.checked)
            press(zero);
        wave(vector);
        const expected = Oracle.expected[kind].nodes;
        const maximal = pcontrol("magnetic.maximalOnly");
        verify(maximal.checked, "The graph opens with Maximal only selected");
        compare(shownNodes().length, expected.filter(node => node.row === 1).length, "Only the independent maximal classes are initially visible");
        const renderedEdges = () => Render.descendants(popup().contentItem).filter(item => item.visible && item.to !== undefined && item.to.x !== undefined);
        compare(renderedEdges().length, 0, "Maximal-only cards render without subgroup edges");
        const footer = pcontrol("magnetic.add");
        const footerY = footer.mapToItem(popup().contentItem, 0, 0).y;
        verify(popup().height <= app.height * .91 && popup().width <= app.width * .91, "The dialog fits within the window with an outer margin");
        press(maximal);
        const nodes = shownNodes();
        compare(nodes.length, expected.length, "Expanding levels retains every independently enumerated class");
        const headers = Render.descendants(popup().contentItem).filter(item => item.visible && /^magnetic\.level\./.test(item.objectName));
        compare(headers.length, Math.max(...expected.map(node => node.row)), "Every independent subgroup level has a selection header");
        for (let i = 0; i < headers.length; ++i) {
            const count = expected.filter(node => node.row === i + 1).length;
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
        const withChildren = expected.findIndex((node, i) => expected.some(child => child.parents.includes(i)) && expected.filter(peer => peer.bns === node.bns).length === 1);
        verify(withChildren >= 0, "The independent graph has an unambiguous parent with covering edges");
        const firstCard = nodes.find(node => node.data_.bns === expected[withChildren].bns);
        verify(firstCard, "The graph renders that independent parent");
        Ui.scrollIntoView(firstCard);
        const point = Ui.clickPoint(firstCard);
        verify(point !== null, "A maximal card is reachable by pointer");
        mouseMove(firstCard, point.x, point.y);
        tryVerify(() => /Co1.*[Mm][xyz]/.test(pcontrol("magnetic.details").text), 2000, "Pointing at a card moves the split-site moment components to the details strip");
        const outgoing = expected.filter(child => child.parents.includes(withChildren));
        const targets = renderedEdges().map(edge => {
            const target = nodes.find(node => node.x === edge.to.x && node.y === edge.to.y);
            verify(target, "A rendered edge terminates at a card");
            return target.data_.bns;
        }).sort();
        compare(targets.join("|"), outgoing.map(node => node.bns).sort().join("|"), "Only the pointed card's independently known covering endpoints are visible");
        const header = headers[0];
        press(header);
        verify(header.checked && popup().selected.length > 0, "The maximal-level checkbox selects its selectable cards");
        const selected = popup().selected.length;
        verify(selected <= expected.filter(node => node.row === 1).length, "Selecting a level never selects lower-level cards");
        verify(footer.text.includes(String(selected)), "The fixed Add button shows the selected count");
        compare(footer.mapToItem(popup().contentItem, 0, 0).y, footerY, "Expanding and selecting levels keeps the footer fixed");
        press(pcontrol("magnetic.clear"));
        compare(popup().selected.length, 0, "The footer Clear resets level selection");
        press(pcontrol("magnetic.listView"));
        const list = pcontrol("magnetic.list");
        compare(list.count, expected.length, "The list retains every class shown by the expanded graph");
        verify(/Co1/.test(Ui.text(popup().contentItem)), "The list has per-site moment columns");
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
        const starts = pcontrol("magnetic.startMoments");
        if (starts.checked)
            press(starts);
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
        tryVerify(() => !popup(), 1000, "Successful Add closes the popup");
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
        group("space_group");
        const action = findChild(page, "spaceGroup.magneticAnalysis");
        verify(action && action.visible, "The Crystal Space group exposes Magnetic symmetry analysis");
        press(action);
        tryVerify(() => !!popup(), 2000, "The Space group button independently opens magnetic symmetry analysis");
        compare(Ui.page(app), page, "The Structure analysis opens over the current page");
        verify(pcontrol("magnetic.k").visible, "The popup keeps its preset and typed k control");
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
        tryVerify(() => !popup(), 1000, "The candidate batch is added before saving");
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
    function startMarking() {
        if (!Ui.find(Ui.page(app), "group.k_search", true))
            Ui.click(test, Probe, app, "sideBar.tab.basic");
        Ui.expandGroup(test, Probe, app, "group.k_search");
        const sidebar = Ui.find(Ui.page(app), "group.k_search", true);
        verify(/^Propagation vector \(k\) search(?: \(\d+\))?$/.test(sidebar.title), "The Experiment sidebar names the propagation vector search group");
        const toggle = chartControl("chart.toolbar.findK");
        verify(toggle.checkable && !toggle.checked, "The chart toolbar offers a Mark peaks toggle initially off");
        pressChart(toggle);
        tryCompare(toggle, "checked", true, 2000, "The chart toolbar toggle turns peak marking on");
        return sidebar;
    }
    function sidebarControl(name) {
        const control = Ui.find(Ui.page(app), "kSearch." + name, true);
        verify(control, "The active Experiment sidebar exposes the k search " + name + " control");
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
    function clickPeak(x) {
        const layer = chartControl("chart.peaks");
        const point = layer.px(x);
        verify(point > 0 && point < layer.width, "The reference peak falls on the visible native chart axis");
        mouseClick(layer, point, layer.height / 2);
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
        startMarking();
        const peaks = markedPeaks(chart);
        const satellite = 13.285477100052015;
        const index = peaks.findIndex(peak => Math.abs(peak.x - satellite) < .051);
        verify(index >= 0, "The independently calculated half-period satellite is pre-marked from measured data");
        const table = sidebarControl("list");
        compare(table.count, peaks.length, "Every chart pre-mark has one sidebar row");
        Ui.scrollIntoView(table.headerItem);
        const headings = Render.texts(table.headerItem).filter(Ui.rendered).map(label => label.text);
        compare(headings, ["2θ (°)", "d (Å)", "Role"], "The table identifies the observed angle, spacing and indexing role");
        const searchControls = Render.descendants(chart.imageToolbar).filter(item => item.visible && (/findK|kSearch/i.test(item.objectName) || ["Find k", "Clear"].includes(item.text)));
        compare(searchControls.map(item => item.objectName), ["chart.toolbar.findK"], "Only Mark peaks sits in the chart toolbar");
        const x = peaks[index].x;
        const rowIndex = peaks.filter(peak => peak.x < x).length;
        const row = sidebarPeak(table, rowIndex, satellite, "pre-marked");
        const remove = findChild(row, "kSearch.remove." + rowIndex);
        verify(remove, "The pre-marked peak row offers its own remove button");
        press(remove);
        compare(table.count, peaks.length - 1, "Removing the suggested row drops exactly one sidebar entry");
        verify(!markedPeaks(chart).some(peak => peak.x === x), "Removing the suggested row unmarks that exact peak on the chart");
        clickPeak(x);
        compare(table.count, peaks.length, "Clicking the observed peak adds its sidebar row again");
        sidebarPeak(table, rowIndex, satellite, "pre-marked");
        clickPeak(x);
        compare(table.count, peaks.length - 1, "Clicking a marked peak drops its row from the sidebar");
        clickPeak(x);
        const clear = sidebarControl("clear");
        compare(clear.text, "Clear", "The Experiment group has a Clear button");
        press(clear);
        compare(table.count, 0, "Clear empties the sidebar table");
        compare(markedPeaks(chart).length, 0, "Clear removes all chart marks");
        compare(snapshot(), before, "Transient marking changes neither the saved model nor Undo history");
        verify(!sidebarControl("findK").enabled && !clear.enabled, "An empty sidebar disables Find k and Clear");
    }
    function test_find_k_mask_excludes_observed_peak() {
        const chart = openPattern();
        const mask = Session.project.currentExperiment.excludedRegions;
        mask.append();
        const row = Probe.rows(mask).length - 1;
        verify(mask.setStart(row, 13) && mask.setEnd(row, 13.6), "The mask covers the independent first satellite");
        startMarking();
        const peaks = markedPeaks(chart);
        verify(peaks.length > 0, "Other unmasked peaks still reach the chart");
        verify(peaks.every(peak => peak.x < 13 || peak.x > 13.6), "An excluded strong peak is not pre-marked");
    }
    function test_find_k_disabled_parent_refuses() {
        const chart = openPattern();
        verify(Session.project.currentExperiment.linkedStructures.setEnabled(0, false), "The real edit disables the sole Crystal link");
        const sidebar = startMarking();
        compare(markedPeaks(chart).length, 0, "A disabled parent produces no chart marks");
        Ui.scrollIntoView(sidebarControl("list"));
        verify(/link.*enable.*crystal/i.test(Ui.text(sidebar)), "The sidebar explains that an enabled Crystal link is required");
    }
    function test_find_k_multiple_crystal_links_refuse() {
        const chart = openPattern("popup");
        const links = Probe.rows(Session.project.currentExperiment.linkedStructures);
        verify(links.some(link => link.structureId === "parent" && link.enabled) && links.some(link => link.structureId === "unrelated" && link.enabled), "The measured experiment has two enabled Crystal phases");
        const before = snapshot();
        const sidebar = startMarking();
        compare(markedPeaks(chart).length, 0, "Link order cannot choose a Crystal target when both links are enabled");
        Ui.scrollIntoView(sidebarControl("list"));
        verify(/several.*crystal/i.test(Ui.text(sidebar)), "The sidebar identifies the ambiguous Crystal target");
        verify(!sidebarControl("findK").enabled, "The ambiguous target cannot start indexing");
        compare(snapshot(), before, "Refusing an ambiguous target leaves both links unchanged");
    }
    function test_find_k_gamma_labels_forbidden_and_allowed_marks() {
        const chart = openPattern("find-k-gamma");
        startMarking();
        const bragg = d => 360 / Math.PI * Math.asin(1.54 / (2 * d));
        const peaks = markedPeaks(chart);
        compare(peaks.length, 1, "Only the Pnma glide absence is pre-marked");
        verify(Math.abs(peaks[0].x - bragg(8)) <= .051, "The pre-mark is the independently positioned forbidden 001");
        const allowedPosition = bragg(1 / Math.hypot(1 / 6, 1 / 8));
        clickPeak(allowedPosition);
        const allowed = markedPeaks(chart).find(peak => Math.abs(peak.x - allowedPosition) <= .051);
        verify(allowed, "Clicking the observed allowed 101 adds it manually");
        const table = sidebarControl("list");
        compare(table.count, 2, "The sidebar shows the forbidden suggestion and the manually added allowed peak");
        sidebarPeak(table, 1, allowedPosition, "added by hand");
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
        const text = Ui.text(findChild(results.contentItem, "chart.kVectorRoles"));
        verify(text.includes(peaks[0].x.toFixed(2) + "° forbidden reflection"), "The vector dialog pairs 001 with the forbidden role");
        verify(text.includes(allowed.x.toFixed(2) + "° allowed reflection"), "The vector dialog pairs 101 with the allowed role");
        pressChart(findChild(results.footer, "chart.kVectorPopup.cancel"));
        tryVerify(() => !openedVectors(), 2000, "Closing the vector dialog reveals the updated sidebar");
        sidebarPeak(table, 0, bragg(8), "forbidden reflection");
        sidebarPeak(table, 1, allowedPosition, "allowed reflection");
    }
    function test_find_k_table_analyse_add_stays_on_pattern() {
        const chart = openPattern();
        const project = Session.project;
        const bank = project.currentExperiment;
        const page = Ui.page(app);
        startMarking();
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
        pressChart(row);
        const roles = Ui.text(findChild(results.contentItem, "chart.kVectorRoles"));
        verify(roles.includes(peaks[satelliteIndex].x.toFixed(2) + "° satellite"), "The vector dialog identifies the isolated peak as a satellite of the selected vector");
        pressChart(findChild(results.footer, "chart.kVectorPopup.analyse"));
        tryVerify(() => !!popup() && !popup().busy && popup().found !== null, 5000, "Analyse closes the k table and builds the graph over the chart");
        verify(!openedVectors(), "The k table closes on Analyse");
        compare(popup().k, "1/2,0,0", "The chart hands off the exact selected k");
        compare(Ui.page(app), page, "The analysis overlays Experiment Pattern");
        const starts = pcontrol("magnetic.startMoments");
        if (starts.checked)
            press(starts);
        const node = shownNodes().find(item => item.data_.type === 4 && item.data_.momentAllowed && item.data_.bns);
        verify(node, "The half-period graph offers a selectable type IV candidate");
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
        tryVerify(() => /1 magnetic structure added.*no magnetic intensity at.*13\.[23]\d°/i.test(Ui.text(Ui.control(Probe, app, "chart.findK.added"))), 5000, "The post-Add chart notice reports the marked satellite with no magnetic intensity");
        verify(Ui.text(chartControl("chart.findK.openStructure")).includes("Open in Structure page"), "The chart offers an explicit way to open Structure");
        verify(markedPeaks(chart).length > 0, "After Add the original marks remain available on the recalculated chart");
        pressChart(chartControl("chart.findK.openStructure"));
        tryVerify(() => Ui.page(app) !== page && chartControl("appBar.tab.structure").checked, 2000, "The explicit Open in Structure action opens the Structure page");
    }
    function staleRowChoice(kind) {
        openPattern();
        startMarking();
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
        press(pcontrol("magnetic.maximalOnly"));
        const nodes = shownNodes();
        for (const form of forms) {
            const node = nodes.find(item => form.test(String(item.data_.moments).replace(/\s/g, "")));
            verify(node !== undefined, "The independent point-group moment form is selectable");
            press(node);
        }
        verify(pcontrol("magnetic.startMoments").checked, "Nonzero starting moments are on by default");
        press(pcontrol("magnetic.add"));
        tryVerify(() => !popup(), 1000, "The note witness is added through the live popup");
        tryCompare(Session.project, "calculating", false, 3000, "The note witness completes its observed reflection calculation");
        return Probe.rows(Session.loadWarnings).map(row => row.message).join("\n") + Ui.text(app.contentItem);
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
        press(pcontrol("magnetic.maximalOnly"));
        const node = shownNodes().find(item => item.data_.bns === "62.452");
        verify(node !== undefined, "The MAGNDATA Mn3O4 signed group is offered at the published propagation vector");
        press(node);
        verify(pcontrol("magnetic.startMoments").checked, "The published positive-intensity witness uses nonzero starting moments");
        press(pcontrol("magnetic.add"));
        tryVerify(() => !popup(), 1000, "The published candidate is added through the live popup");
        tryCompare(Session.project, "calculating", false, 3000, "The Mn3O4 candidate finishes the linked powder calculation");
        const children = Probe.rows(Session.project.structures).filter(row => row.name !== "parent");
        compare(children.length, 1, "The published witness has exactly one added child");
        const moments = Probe.rows(children[0].structure.atomSiteMoments);
        verify(moments.some(row => ["mx", "my", "mz"].some(axis => Math.abs(row[axis].value) > 0)), "Mn3O4 retains a nonzero seeded magnetic moment");
        const bank = Probe.rows(Session.project.experiments)[0].experiment;
        const started = bank.measCalcPoints().calc.slice();
        verify(started.length > 0 && started.every(Number.isFinite), "The linked Mn3O4 starting state has a calculable powder pattern");
        const text = Probe.rows(Session.loadWarnings).map(row => row.message).join("\n") + Ui.text(app.contentItem);
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
        tryVerify(() => !popup(), 1000, "The normal candidate toggle starts from a committed Add");
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
