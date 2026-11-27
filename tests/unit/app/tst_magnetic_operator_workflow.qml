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
        const found = Render.descendants(popup().contentItem).find(item => item.objectName === name);
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
        tryVerify(() => !popup().busy && popup().found !== null, 3000, "The selected k produces its bounded magnetic graph");
    }
    function shownNodes() {
        return Render.descendants(popup().contentItem).filter(item => /^magnetic\.node\./.test(item.objectName));
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
        const nodes = shownNodes();
        compare(nodes.length, expected.length, "The rendered graph includes every independently enumerated class");
        const actual = nodes.map(item => {
            const text = Ui.text(item);
            const identity = text.match(/(\d+\.\d+)#(\d+)/);
            verify(identity !== null, "Every rendered node carries its BNS and embedding identity");
            return {
                bns: identity[1],
                embedding: Number(identity[2]),
                fm: /\bFM\b/.test(text),
                y: item.y
            };
        });
        const heights = Array.from(new Set(actual.map(node => node.y))).sort((a, b) => a - b);
        const actualRows = actual.map(node => [node.bns, heights.indexOf(node.y) + 1, node.fm].join("|")).sort();
        const expectedRows = expected.map(node => [node.bns, node.row, node.fm].join("|")).sort();
        compare(actualRows.join(";"), expectedRows.join(";"), "Rendered rows and FM marks equal the independent signed census");
        verify(/1[′']/.test(Ui.text(popup().contentItem)), "The rendered graph has its unselectable parent grey-group header");
        const edges = Render.descendants(popup().contentItem).filter(item => /^magnetic\.edge\./.test(item.objectName));
        const count = expected.reduce((sum, node) => sum + node.parents.length, 0);
        compare(edges.length, count, "Rendered covering edges expose endpoint object-name pairs for the independent graph");
        for (const edge of edges)
            verify(actual.some(node => edge.objectName.includes(node.bns + "#" + node.embedding)), "Every edge endpoint names a rendered candidate identity");
        verify(nodes.some(node => /Co1/.test(Ui.text(node)) && /M[x-z]|m[x-z]/.test(Ui.text(node))), "The actual graph renders the per-split-site moment components");
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
    function test_calculate_does_not_enable_find_k() {
        openPopup();
        const button = Render.descendants(popup().contentItem).find(item => /Find k from data/i.test(String(item.text)));
        verify(button !== undefined, "The popup exposes Find k from data beside its Data list");
        if (button.enabled)
            press(button);
        verify(!pcontrol("magnetic.searchK").enabled, "A fresh Calculate without an adopted fit does not make a bank eligible");
        verify(/fit.*keep|keep.*fit/i.test(Ui.text(popup().contentItem)), "The ineligible Data list explains that an adopted fit is required");
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
    function test_k_field_refusal_is_atomic() {
        openInput("type-iv", false);
        const structure = Session.project.currentStructure;
        const before = snapshot();
        verify(!structure.propagationVectors.setVector(0, "0,0,1/3"), "A k requiring another magnetic cell is refused in the existing structure");
        verify(/popup|candidate|Magnetic/i.test(structure.propagationVectors.refusal), "The k refusal directs the user to magnetic candidates");
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
        verify(/popup|candidate|Magnetic/i.test(structure.magneticGroupRefusal), "The BNS refusal directs the user to magnetic candidates");
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

    function keptSearchFit() {
        openPopup("find-k");
        popup().close();
        const project = Session.project;
        project.currentExperimentIndex = project.experimentIndex("first");
        project.analysis.fittingMode = "single";
        verify(Probe.rows(project.currentStructure.atomSites).every(row => !row.fractX.free && !row.fractY.free && !row.fractZ.free), "The eligibility witness keeps the whole nuclear parent fixed");
        verify(project.fit.available, "The synthetic observed bank permits its real constant-background fit");
        project.fit.start();
        tryVerify(() => !project.fit.running && project.fit.canUndo, 3000, "The real fitted background is adopted before search eligibility is tested");
        tryCompare(project, "calculating", false, 1000, "The kept fit publishes its current calculated pattern");
        choose(typeChoice(), "Magnetic");
        tryVerify(() => !!popup(), 1000, "The kept-fit parent opens the same candidate popup");
    }
    function dataChoice(name) {
        const choices = Session.project.magneticDataChoices(Session.project.structureIndex("parent"));
        const found = choices.find(row => row.name === name);
        verify(found !== undefined, "The Data list contains the linked bank " + name);
        return found;
    }
    function runSearch() {
        const button = pcontrol("magnetic.findK");
        if (!button.checked)
            press(button);
        const data = pcontrol("magnetic.data");
        const text = Array.from({
            length: data.count
        }, (_, i) => data.textAt(i)).find(value => value === "first");
        verify(text !== undefined, "The kept first bank is visibly eligible in the Data list");
        choose(data, text);
        const ticks = Render.descendants(popup().contentItem).filter(item => /^magnetic\.peak\./.test(item.objectName));
        verify(ticks.length >= 12 && ticks.every(item => item.checked), "The independently separated observed maxima appear as ticked search peaks");
        press(pcontrol("magnetic.searchK"));
        tryVerify(() => !popup().searching, 3000, "The bounded search finishes before a result can be chosen");
        const list = pcontrol("magnetic.kRows");
        verify(list.count > 0, "The independent half-period satellites yield a real ranked list");
        list.forceLayout();
        return list;
    }
    function test_find_k_fixed_parent_is_eligible() {
        keptSearchFit();
        verify(dataChoice("first").eligible, "An adopted fit is eligible even when the nuclear parent itself was fixed");
        verify(!dataChoice("second").eligible, "A different bank has no adoption merely because the first bank was fitted");
    }
    function staleSearchEdit(kind) {
        keptSearchFit();
        verify(dataChoice("first").eligible, "The stale-stamp witness starts from a genuinely adopted fit");
        const project = Session.project, bank = project.currentExperiment;
        if (kind === "coordinate")
            Probe.rows(project.currentStructure.atomSites)[0].fractX.value = .173;
        else if (kind === "zero") {
            const zero = Probe.rows(bank.instrument).find(row => row.parameter && row.parameter.name === "calib_twotheta_offset");
            verify(zero !== undefined, "The calibration-only witness reaches the real CW zero parameter");
            zero.parameter.value = .1;
        } else if (kind === "mask") {
            bank.excludedRegions.append();
            const n = Probe.rows(bank.excludedRegions).length - 1;
            verify(bank.excludedRegions.setStart(n, 20) && bank.excludedRegions.setEnd(n, 21), "The mask witness changes a real observed-data inclusion interval");
        } else if (kind === "disabled")
            verify(bank.linkedStructures.setEnabled(0, false), "The parent link can be disabled through the normal recorded action");
        else
            Probe.rows(bank.peak)[2].parameter.value = .09;
        tryCompare(project, "calculating", false, 1000, "The edit's subsequent Calculate completes");
        verify(project.fit.canUndo, "The earlier fit record remains available while its adoption is stale");
        verify(!dataChoice("first").eligible, "Editing and calculating cannot refresh the kept-fit adoption stamp");
        compare(project.magneticPeaks(project.structureIndex("parent"), project.experimentIndex("first")).length, 0, "A stale or disabled parent refuses peak extraction");
    }
    function test_find_k_coordinate_edit_stales_fit() {
        staleSearchEdit("coordinate");
    }
    function test_find_k_calibration_edit_stales_fit() {
        staleSearchEdit("zero");
    }
    function test_find_k_mask_edit_stales_fit() {
        staleSearchEdit("mask");
    }
    function test_find_k_disabled_parent_refuses() {
        staleSearchEdit("disabled");
    }
    function test_find_k_profile_edit_stales_fit() {
        staleSearchEdit("profile");
    }
    function test_find_k_data_ticks_and_choice_reach_graph() {
        keptSearchFit();
        const list = runSearch();
        const top = list.itemAtIndex(0);
        verify(top && top.enabled, "The synthetic half-period best row is buildable");
        verify(/1\/2,0,0/.test(Ui.text(top)), "The real result row shows the independently known half-period vector");
        press(top);
        tryVerify(() => !popup().busy && popup().found !== null, 3000, "Choosing the ranked k computes its subgroup graph");
        compare(popup().k, "1/2,0,0", "Choosing a search result sets the graph's exact k");
        verify(shownNodes().length > 0, "The selected search result reaches the rendered magnetic candidate graph");
    }
    function test_find_k_unticking_changes_search_snapshot() {
        keptSearchFit();
        runSearch();
        const tick = pcontrol("magnetic.peak.0");
        press(tick);
        verify(!tick.checked, "The actual unexplained peak tick changes by pointer input");
        verify(!Session.project.propagationSearchCurrent(Session.project.experimentIndex("first")), "Changing a peak tick invalidates the previous search snapshot");
        compare(pcontrol("magnetic.kRows").count, 0, "Stale result rows disappear after peak selection changes");
    }
    function test_find_k_late_choice_after_calibration_edit_refuses() {
        keptSearchFit();
        const list = runSearch();
        const top = list.itemAtIndex(0), before = popup().k;
        const zero = Probe.rows(Session.project.currentExperiment.instrument).find(row => row.parameter && row.parameter.name === "calib_twotheta_offset");
        verify(zero !== undefined, "The late-choice witness addresses the real calibration parameter");
        zero.parameter.value = .1;
        tryCompare(Session.project, "calculating", false, 1000, "Calculate after the late calibration edit completes");
        press(top);
        compare(popup().k, before, "A late row choice cannot change k after its data stamp expires");
        verify(/changed.*search again/i.test(Ui.text(popup().contentItem)), "The stale result refusal visibly asks the user to search again");
    }
    function noteNodes(name, forms) {
        openPopup(name);
        wave("0,0,0");
        const nodes = shownNodes();
        const selected = [];
        for (const form of forms) {
            const node = nodes.find(item => form.test(Ui.text(item).replace(/\s/g, "")));
            verify(node !== undefined, "The independent point-group moment form is selectable");
            selected.push(node);
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
        const node = shownNodes().find(item => /62\.452/.test(Ui.text(item)));
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
        verify(/popup|Crystal.*Magnetic|candidate/i.test(structure.magneticGroupRefusal), "Either BNS field directs a cell-changing edit to the popup");
        verify(/62\.452/.test(value(number)), "A refused BNS name edit leaves the linked BNS number unchanged");
    }
    function test_rendered_bns_number_refusal() {
        renderedBnsRefusal(false);
    }
    function test_rendered_bns_name_refusal() {
        renderedBnsRefusal(true);
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
        verify(/popup|candidate|Crystal.*Magnetic/i.test(structure.magneticGroupRefusal), "The grey BNS refusal also points to the parent popup");
        verify(before.length > 0, "The legacy grey control observes a serialized model before attempted edits");
    }
}
