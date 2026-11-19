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

TestCase {
    id: test
    name: "MagneticStructureType"
    when: windowShown
    property var app
    property string selector: ""
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
    function openInput(name) {
        verify(Session.openProject(SettingsProof.copyProject(Probe.referenceUrl(name))), "The app opens the independently authored " + name + " input");
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
    function test_a_create_defaults_to_crystal() {
        openInput("crystal");
        Ui.click(test, Probe, app, "structures.create");
        compare(typeChoice().currentText, "Crystal", "Create makes a Crystal structure");
        const ids = groups("basic").map(item => item.categoryId).concat(groups("extras").map(item => item.categoryId));
        verify(ids.includes("space_group"), "Crystal exposes its ordinary space group");
        verify(!ids.some(id => /magn|moment|parent_space_group|propagation/.test(id)), "Crystal exposes no magnetic groups, including moments");
    }
    function test_b_magnetic_cif_selects_magnetic() {
        openInput("magnetic");
        compare(typeChoice().currentText, "Magnetic", "A magnetic CIF opens as Magnetic even before a moment edit");
        const ids = groups("basic").map(item => item.categoryId);
        verify(ids.includes("space_group_magn") && !ids.includes("space_group"), "Magnetic space group replaces Space group on Main");
    }
    function test_c_switch_to_magnetic_uses_the_grey_group() {
        openInput("crystal");
        choose(typeChoice(), "Magnetic");
        const structure = Session.project.currentStructure;
        compare(structure.magneticGroup.number_bns, "62.442", "Switching Pnma to Magnetic chooses its grey group BNS 62.442");
        compare(String(structure.magneticGroup.name_bns).replace(/[\s′]/g, c => c === "′" ? "'" : ""), "Pnma1'", "The grey group is Pnma with pure time reversal");
        const table = Render.descendants(group("atom_site_moment")).find(item => item.sourceModel !== undefined && typeof item.itemAtIndex === "function");
        verify(table && table.count > 0, "The grey group's moment constraints are visible for actual sites");
        table.positionViewAtIndex(0, ListView.Contain);
        table.forceLayout();
        const ion = findChild(table.itemAtIndex(0), "atomSiteMoment.ion.0");
        verify(ion, "The first cobalt site exposes its actual magnetic-ion selector");
        choose(ion, "Co2+");
        let checked = 0;
        for (let i = 0; i < table.count; ++i) {
            table.positionViewAtIndex(i, ListView.Contain);
            table.forceLayout();
            const row = table.itemAtIndex(i);
            verify(row, "Every grey-group site row is instantiated");
            const components = Render.descendants(row).filter(item => item.item && /^atomSiteMoment\.m[xyz]\./.test(item.objectName));
            for (const component of components) {
                compare(Number(component.item.value), 0, "Pure time reversal fixes every moment component to zero");
                verify(!component.item.fittable, "Grey-group moments cannot be fitted against symmetry");
                ++checked;
            }
        }
        verify(checked >= 3, "The zero-moment check reaches all components of a real cobalt moment");
    }
    function confirmation() {
        let dialog;
        tryVerify(() => {
            dialog = Probe.objectsWithProperty(app, "opened").find(item => item.opened && typeof item.standardButton === "function" && /moment|magnetic/i.test(item.title + " " + Ui.text(item.contentItem)));
            return !!dialog;
        }, 2000, "Dropping magnetic moments requires a visible confirmation");
        return dialog;
    }
    function test_d_return_to_crystal_requires_confirmation() {
        openInput("magnetic");
        const before = Session.project.currentStructure.text.text;
        choose(typeChoice(), "Crystal");
        let dialog = confirmation();
        press(dialog.standardButton(Dialog.Cancel) ?? dialog.standardButton(Dialog.No));
        compare(typeChoice().currentText, "Magnetic", "Cancelling keeps the magnetic structure type");
        compare(Session.project.currentStructure.text.text, before, "Cancelling retains the nonzero moments and every scientific declaration");
        choose(typeChoice(), "Crystal");
        dialog = confirmation();
        press(dialog.standardButton(Dialog.Ok) ?? dialog.standardButton(Dialog.Yes) ?? dialog.standardButton(Dialog.Discard));
        compare(typeChoice().currentText, "Crystal", "Confirming returns the structure to Crystal");
        compare(Session.project.currentStructure.spaceGroup.itNumber, 62, "Ignoring time reversal returns the magnetic group's own Pnma space group");
        verify(!/_atom_site_moment\.|_space_group_magn\./i.test(Session.project.currentStructure.text.text), "Returning to Crystal drops the magnetic moments and magnetic symmetry from the file");
    }
    function test_e_bns_fields_are_linked_and_searchable() {
        openInput("magnetic");
        const owner = group("space_group_magn");
        const number = field(owner, ".number_bns", "Number BNS");
        const name = field(owner, ".name_bns", "Name BNS");
        for (const control of [number, name]) {
            verify(typeof control.textAt === "function" && control.searchThreshold === 0, "Both linked BNS fields expose the searchable selector used by Space group");
        }
        const target = Array.from({
            length: number.count
        }, (_, i) => number.textAt(i)).find(text => /62\.442/.test(text));
        verify(target, "The BNS number selector contains Pnma's grey group");
        choose(number, target);
        verify(/Pnma.*1/.test(value(name)), "Choosing the grey BNS number updates the linked BNS name");
        const ordinary = Array.from({
            length: name.count
        }, (_, i) => name.textAt(i)).find(text => text.replace(/\s/g, "") === "Pnma");
        verify(ordinary, "The BNS name selector offers the ordinary Pnma magnetic subgroup");
        choose(name, ordinary);
        verify(/62\.441/.test(value(number)), "Choosing Pnma by name updates the linked BNS number");
    }
    function test_f_setting_shows_the_nontrivial_transform() {
        openInput("shifted");
        const setting = field(group("space_group_magn"), ".pp_abc", "Setting");
        compare(value(setting), "a,b,c;1/4,0,0", "Setting shows the supplied quarter-cell transform to standard BNS");
    }
    function test_g_crystal_system_is_read_only() {
        openInput("magnetic");
        const system = field(group("space_group_magn"), ".crystal_system", "Crystal system");
        compare(value(system).toLowerCase(), "orthorhombic", "The magnetic group's derived crystal system is displayed");
        readOnly(system);
        verify(!/crystal_system/i.test(Session.project.currentStructure.text.text), "The displayed crystal system is never saved as an invented dictionary item");
    }
    function test_h_derived_symbols_are_read_only_on_extra() {
        openInput("magnetic");
        const main = group("space_group_magn");
        const fields = [[".name_uni", "Name UNI", "Pnma.1"], [".number_og", "Number OG", "62.1.502"], [".name_og", "Name OG", "Pnma"], [".point_group_name_uni", "Point group name UNI", "mmm.1"], [".point_group_number_litvin", "Point group number Litvin", "8.1.24"]];
        verify(!Render.descendants(main).some(item => item.visible && fields.some(row => identifies(item, row[0]))), "Derived symbols have no duplicate fields under the Main BNS selector");
        const extra = groups("extras");
        for (const owner of extra)
            owner.collapsed = false;
        verify(waitForPolish(app.contentItem), "Extra builds every derived-symbol field before discovery");
        const owners = [];
        for (const row of fields) {
            const matching = extra.filter(owner => Render.descendants(owner).some(item => item.visible && identifies(item, row[0])));
            compare(matching.length, 1, "Extra displays each derived magnetic symbol once");
            owners.push(matching[0]);
            matching[0].collapsed = false;
            Ui.scrollIntoView(matching[0]);
            const control = field(matching[0], row[0], row[1]);
            compare(value(control), row[2], "Derived symbols agree with the independently authored ISODISTORT file");
            readOnly(control);
        }
        verify(owners.every(owner => owner === owners[0]) && owners[0].categoryId !== "parent_space_group", "Derived magnetic symbols share their own Extra group");
    }
    function test_i_parent_is_always_on_extra() {
        openInput("magnetic");
        const main = group("space_group_magn");
        verify(!Render.descendants(main).some(item => item.visible && String(item.uid || "").startsWith("parent_space_group.")), "Main has no duplicate parent row below the BNS selector");
        const parent = group("parent_space_group", "extras");
        compare(value(field(parent, ".it_number", "IT number")), "62", "An absent parent defaults to the magnetic group's own space group even when both groups agree");
        verify(/P\s*n\s*m\s*a/.test(value(field(parent, ".name_h_m_alt", "Name H-M alt"))), "The always-present Extra parent heading shows Pnma");
    }
    function test_j_sites_show_the_published_wyckoff_positions_and_fit_freedom() {
        openInput("magnetic");
        const expected = [["Co1_1", "4a", [false, false, false]], ["Co2_1", "4c", [true, false, true]], ["Si_1", "4c", [true, false, true]], ["O1_1", "4c", [true, false, true]], ["O2_1", "4c", [true, false, true]], ["O3_1", "8d", [true, true, true]]];
        const table = findChild(group("atom_site"), "atomSites.list");
        verify(table && table.count === expected.length, "The app renders all independently published CoSiO sites");
        for (let index = 0; index < expected.length; ++index) {
            table.positionViewAtIndex(index, ListView.Contain);
            table.forceLayout();
            const row = table.itemAtIndex(index);
            verify(row, "Each independently published site row is reachable");
            compare(findChild(row, "atomSite.label." + index).value, expected[index][0], "The displayed site identity matches ISODISTORT");
            const wyckoff = findChild(row, "atomSite.wyckoffLetter." + index);
            verify(wyckoff && wyckoff.displayText.replace(/\s/g, "") === expected[index][1], "The visible Wyckoff field shows the ISODISTORT multiplicity and letter");
            for (let axis = 0; axis < 3; ++axis) {
                const cell = findChild(row, "atomSite.fract" + "XYZ"[axis] + "." + index);
                verify(cell && cell.item, "Every displayed coordinate refers to its real parameter");
                compare(cell.item.fittable, expected[index][2][axis], "The magnetic table leaves exactly the published positional degrees of freedom fittable");
            }
        }
    }
}
