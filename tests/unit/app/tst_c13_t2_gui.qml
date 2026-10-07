import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "C13T2Gui"
    when: windowShown
    property var appWindow
    Component { id: application; Main {} }
    function initTestCase() {
        failOnWarning(/.*/);
        appWindow = application.createObject(null);
        verify(appWindow !== null, "C13-T2 GUI: production Main loads");
        verify(waitForRendering(appWindow.contentItem), "C13-T2 GUI: production window renders");
    }
    function init() {
        // Offscreen software has no GL context; changing a tensor also refreshes the 3D scene.
        // Keep all other warnings fatal, including every warning in cases without a scene refresh.
        const refreshesScene = ["test_adp_view_uses_probability_in_atom_scale_position",
            "test_each_declared_adp_type_has_the_required_editor_state"].includes(qtest_results.functionName);
        failOnWarning(refreshesScene
            ? /\A(?!QRhiGles2: Failed to create (?:temporary context|context)\z)[\s\S]*\z/ : /.*/);
        Session.closeProject();
        Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project"));
        verify(Session.hasProject, "C13-T2 GUI: committed editable project opens");
    }
    function cleanupTestCase() {
        Session.closeProject();
        verify(waitForRendering(appWindow.contentItem), "C13-T2 GUI: page teardown settles");
        appWindow.destroy();
    }
    function click(name) { Ui.click(test, Probe, appWindow, name); }
    function control(name) { return Ui.control(Probe, appWindow, name); }
    function discover(root, name) {
        if (!root || !root.visible) return null;
        if (root.objectName === name && Ui.inPane(Ui.target(root))) return root;
        for (const child of root.children || []) {
            const found = discover(child, name);
            if (found) return found;
        }
        return null;
    }
    function reveal(page, tier, group, name) {
        click("appBar.tab." + page);
        click("sideBar.tab." + tier);
        let header = null;
        tryVerify(() => { header = discover(Ui.page(appWindow), "group." + group); return header !== null; },
                  2000, "C13-T2 GUI: declared category belongs to the selected pane: " + group);
        Ui.scrollIntoView(Ui.target(header));
        Ui.expandGroup(test, Probe, appWindow, "group." + group);
        tryVerify(() => control(name) !== null, 2000, "C13-T2 GUI: category exposes its control: " + name);
        return control(name);
    }
    function search(combo, text) {
        Ui.scrollIntoView(combo);
        const point = Ui.clickPoint(combo);
        verify(point !== null, "C13-T2 GUI: combo is exposed for real input");
        mouseClick(combo, point.x, point.y);
        tryCompare(combo.popup, "opened", true, 2000, "C13-T2 GUI: real click opens the popup");
        const field = Ui.find(combo.popup.contentItem.headerItem, "comboBox.search");
        verify(field !== null, "C13-T2 GUI: filter field is visible at the top of the popup");
        filterText(field, text);
        return field;
    }
    function filterText(field, text) {
        field.forceActiveFocus();
        keyClick(Qt.Key_A, Qt.ControlModifier);
        for (const character of text) {
            keyClick(character === " " ? Qt.Key_Space : character.toUpperCase().charCodeAt(0));
        }
    }
    function expectRed(field) {
        tryVerify(() => field.color.r > field.color.g + 0.15 && field.color.r > field.color.b + 0.15,
                  1000, "owner 2026-10-06: rejected text actually renders red after the colour transition");
    }
    function textInput(field, keys) {
        field.forceActiveFocus();
        keyClick(Qt.Key_A, Qt.ControlModifier);
        for (const key of keys) keyClick(key);
        keyClick(Qt.Key_Return);
    }
    function headers(table) { return Array.from(table.headerLabelItems).map(item => item.text); }
    function test_separate_adp_table_and_isotropic_controls() {
        const atoms = reveal("structure", "basic", "atom_site", "atomSites.list");
        compare(JSON.stringify(headers(atoms)), JSON.stringify(["", "label", "type", "x", "y", "z", "WL", "occ", ""]),
                "owner 2026-10-06: Atom sites has an unlabelled index, WL, and no ADP columns");
        const picker = control("atomSite.typeSymbol.0");
        const icon = control("atomSite.icon.0");
        verify(picker !== null && icon !== null && icon.parent === picker.contentItem,
               "owner 2026-10-06: atom icon sits inside the type picker without a separate column");
        verify(atoms.headerLabelItems[2].width < atoms.headerLabelItems[3].width,
               "owner 2026-10-06: atom type column is compact beside coordinates");
        const table = reveal("structure", "basic", "atom_site_aniso", "atomSiteAdps.list");
        compare(JSON.stringify(headers(table)), JSON.stringify(["", "label", "type", "iso", "ani11", "ani22", "ani33", "ani12", "ani13", "ani23"]),
                "owner 2026-10-06: Atomic displacement owns the complete scalar and tensor table");
        const sites = Probe.rows(Session.project.currentStructure.atomSites);
        const adps = Probe.rows(Session.project.currentStructure.atomSiteAdps);
        compare(JSON.stringify(adps.map(row => row.label)), JSON.stringify(sites.map(row => row.label)),
                "owner 2026-10-06: ADP labels copy Atom sites in exactly the same order");
        verify(!control("atomSiteAdp.label.0").enabled, "owner 2026-10-06: copied ADP label is disabled");
        verify(control("atomSiteAdp.iso.0").enabled, "owner 2026-10-06: Biso scalar is editable");
        for (const component of ["11", "22", "33", "12", "13", "23"]) {
            const field = control("atomSiteAdp.ani" + component + ".0");
            verify(field !== null && !field.enabled && field.text === "",
                   "owner 2026-10-06: isotropic sites leave all tensor fields empty and disabled");
        }
    }
    function test_each_declared_adp_type_has_the_required_editor_state() {
        const picker = reveal("structure", "basic", "atom_site_aniso", "atomSiteAdp.type.0");
        compare(JSON.stringify(Array.from(picker.model)), JSON.stringify(["Biso", "Uiso", "Bani", "Uani", "beta"]),
                "C13-T2: all five declared ADP types are selectable");
        for (const type of ["Uiso", "Bani", "Uani", "beta", "Biso"]) {
            Ui.scrollIntoView(picker);
            click("atomSiteAdp.type.0");
            tryCompare(picker.popup, "opened", true, 2000, "C13-T2: ADP list opens through input");
            const index = Array.from(picker.model).indexOf(type);
            keyClick(Qt.Key_Home);
            for (let i = 0; i < index; ++i) keyClick(Qt.Key_Down);
            keyClick(Qt.Key_Return);
            tryCompare(picker.popup, "visible", false, 2000, "C13-T2: selection finishes closing the ADP popup");
            tryVerify(() => Probe.rows(Session.project.currentStructure.atomSiteAdps)[0].adpType === type,
                      2000, "C13-T2: real ADP selection reaches the row model: " + type);
            const anisotropic = ["Bani", "Uani", "beta"].includes(type);
            // Before: non-Biso selected a retired preview object. After: the same
            // iso cell edits both scalar types and displays the tensor equivalent.
            tryVerify(() => {
                const iso = control("atomSiteAdp.iso.0");
                return iso !== null && iso.enabled === !anisotropic;
            }, 2000, "owner 2026-10-06: equivalent iso is disabled only for anisotropic types");
            // La at the Pm-3m origin: cubic rotations equate all diagonals and
            // mirrors fix off-diagonals to zero; only ani11 is independent.
            for (const component of ["11", "22", "33", "12", "13", "23"])
                tryVerify(() => {
                    const field = control("atomSiteAdp.ani" + component + ".0");
                    return field !== null && field.enabled === (anisotropic && component === "11");
                }, 2000, "cubic site symmetry: only the independent tensor component is editable");
        }
    }
    function test_atom_filter_recovers_from_red_and_commits_element() {
        const picker = reveal("structure", "basic", "atom_site", "atomSite.typeSymbol.0");
        let field = search(picker, "zzzz");
        verify(field.warned && !picker.anyMatch, "owner 2026-10-06: unmatched atom filter is red");
        expectRed(field);
        const before = Probe.rows(Session.project.currentStructure.atomSites)[0].typeSymbol;
        keyClick(Qt.Key_Return);
        compare(Probe.rows(Session.project.currentStructure.atomSites)[0].typeSymbol, before,
                "owner 2026-10-06: invalid filter never commits an atom type");
        field.forceActiveFocus();
        keyClick(Qt.Key_A, Qt.ControlModifier);
        keyClick(Qt.Key_C); keyClick(Qt.Key_E);
        verify(!field.warned && picker.anyMatch, "owner 2026-10-06: valid atom text clears red");
        keyClick(Qt.Key_Return);
        tryVerify(() => Probe.rows(Session.project.currentStructure.atomSites)[0].typeSymbol === "Ce", 2000,
                  "owner 2026-10-06: Enter chooses the exact valid element through the filter");
    }
    function test_space_group_name_and_number_choose_new_default() {
        const name = reveal("structure", "basic", "space_group", "spaceGroup.nameHM");
        const group = Session.project.currentStructure.spaceGroup;
        group.nameHM = "F d -3 m"; group.coordSystemCode = "1";
        const field = search(name, "nosuchgroup");
        verify(field.warned && !name.anyMatch, "owner 2026-10-06: unmatched space-group names warn");
        expectRed(field);
        keyClick(Qt.Key_Return);
        compare(group.itNumber, 227, "owner 2026-10-06: invalid name leaves group identity intact");
        filterText(field, "p n m a");
        verify(!field.warned, "owner 2026-10-06: filtering ignores case and spaces");
        keyClick(Qt.Key_Return);
        tryCompare(group, "itNumber", 62, 2000, "owner 2026-10-06: name edit resolves IT number");
        compare(group.coordSystemCode, "abc", "International Tables: Pnma has the abc default setting");
        const number = control("spaceGroup.itNumber");
        textInput(number, [Qt.Key_2, Qt.Key_2, Qt.Key_5]);
        compare(group.nameHM, "F m -3 m", "owner 2026-10-06: number edit resolves the group name");
        compare(group.coordSystemCode, "1", "owner example: Fm-3m resolves its default code 1");
        group.nameHM = "F d -3 m"; group.coordSystemCode = "2";
        const code = control("spaceGroup.coordSystemCode");
        const codeField = search(code, "nosuchcode");
        verify(codeField.warned && !code.anyMatch, "owner 2026-10-06: unmatched setting codes warn");
        expectRed(codeField);
        keyClick(Qt.Key_Return);
        compare(group.coordSystemCode, "2", "owner 2026-10-06: invalid code leaves setting intact");
        filterText(codeField, "1");
        verify(!codeField.warned, "owner 2026-10-06: setting code is filterable");
        keyClick(Qt.Key_Return);
        compare(group.coordSystemCode, "1", "owner 2026-10-06: selected setting remains editable");
        compare(group.itNumber, 227, "owner 2026-10-06: setting edit retains group identity");
    }
    function test_invalid_number_is_red_and_unapplied() {
        const field = reveal("structure", "basic", "space_group", "spaceGroup.itNumber");
        const before = Session.project.currentStructure.spaceGroup.itNumber;
        for (const keys of [[Qt.Key_0], [Qt.Key_2, Qt.Key_3, Qt.Key_1], [Qt.Key_6, Qt.Key_2, Qt.Key_Period, Qt.Key_5]]) {
            textInput(field, keys);
            verify(field.warned, "owner 2026-10-06: only whole IT numbers in 1..230 are admitted");
            expectRed(field);
            compare(Session.project.currentStructure.spaceGroup.itNumber, before,
                    "owner 2026-10-06: invalid IT number leaves space-group identity intact");
        }
        textInput(field, [Qt.Key_6, Qt.Key_2]);
        verify(!field.warned, "owner 2026-10-06: valid IT number clears red");
        compare(Session.project.currentStructure.spaceGroup.itNumber, 62, "owner 2026-10-06: valid IT number commits");
    }
    function nativeAtomGlyph(root) {
        if (!root || !root.visible) return null;
        if (root.isIcon && root.modelData.icon === "atom" && Probe.nativeText(root) && Ui.rendered(root)) return root;
        for (const child of root.children || []) {
            const found = nativeAtomGlyph(child);
            if (found) return found;
        }
        return null;
    }
    function test_atom_icon_colours_follow_structure_palette_in_both_tables() {
        const colours = [{scheme: "jmol", value: "#70d4ff"}, {scheme: "vesta", value: "#5ac449"}];
        for (const palette of colours) {
            Session.project.structureViewOptions.colorScheme = palette.scheme;
            const picker = reveal("structure", "basic", "atom_site", "atomSite.typeSymbol.0");
            const glyph = nativeAtomGlyph(control("atomSite.icon.0"));
            verify(glyph !== null, "owner 2026-10-06: Atom sites draws its coloured atom glyph beside the type");
            tryCompare(glyph, "color", palette.value, 2000,
                       "published-elements.tsv: La icon follows its independent Jmol/VESTA colour");
            click("appBar.tab.analysis"); click("sideBar.tab.basic");
            const rows = Probe.rows(Session.project.parameters);
            const index = rows.findIndex(row => row.parameter && row.parameter.rowLabel === "La" && row.parameter.name === "occupancy");
            verify(index >= 0, "owner 2026-10-06: Analysis contains the same La occupancy row");
            let table = null;
            tryVerify(() => { table = discover(Ui.page(appWindow), "parameters.list"); return table !== null; },
                      2000, "owner 2026-10-06: Analysis parameter table belongs to the selected pane");
            table.positionViewAtIndex(index, ListView.Center);
            tryVerify(() => control("parameters.name." + index) !== null, 2000,
                      "owner 2026-10-06: the selected Analysis name is exposed");
            const line = control("parameters.name." + index);
            const atom = nativeAtomGlyph(line);
            verify(atom !== null, "owner 2026-10-06: Analysis draws its atom glyph");
            tryCompare(atom, "color", palette.value, 2000,
                       "owner 2026-10-06: Analysis and Atom sites draw the same independent palette colour");
        }
    }
    function test_adp_view_uses_probability_in_atom_scale_position() {
        const scale = reveal("structure", "extras", "appearance", "structure.appearance.atomScale");
        const location = scale.mapToItem(appWindow.contentItem, 0, 0);
        Session.project.structureViewOptions.atomView = "adp";
        tryVerify(() => control("structure.appearance.adpProbability") !== null, 2000,
                  "owner 2026-10-06: ADP atom view exposes ellipsoid probability");
        const probability = control("structure.appearance.adpProbability");
        compare(Number(probability.text), 0.99, "diffraction-lib v0.21.1: ellipsoid probability defaults to 0.99");
        verify(control("structure.appearance.atomScale") === null,
               "owner 2026-10-06: ADP view replaces the ball atom scale field");
        verify(waitForPolish(appWindow, 2000), "owner 2026-10-06: replacement field finishes layout");
        tryVerify(() => probability.mapToItem(appWindow.contentItem, 0, 0).x === location.x, 2000,
                  "owner 2026-10-06: probability occupies the atom scale column");
        tryVerify(() => probability.mapToItem(appWindow.contentItem, 0, 0).y === location.y, 2000,
                  "owner 2026-10-06: probability occupies the atom scale row");
    }
    function test_minimizer_is_two_rows_of_two() {
        const type = reveal("analysis", "extras", "minimizer", "minimizer.type");
        const descent = control("minimizer.descent");
        const iterations = control("minimizer.maxIterations");
        const tolerance = control("minimizer.chiSquareTolerance");
        const positions = [type, descent, iterations, tolerance].map(item => item.mapToItem(appWindow.contentItem, 0, 0));
        compare(positions[0].y, positions[1].y, "owner 2026-10-06: minimizer and descent share the first row");
        compare(positions[2].y, positions[3].y, "owner 2026-10-06: iteration bound and tolerance share the second row");
        verify(positions[2].y > positions[0].y && positions[1].x > positions[0].x,
               "owner 2026-10-06: minimizer uses two rows and two columns");
        verify(descent.width >= type.width && descent.width >= iterations.width,
               "owner 2026-10-06: descent names have a full half-row");
    }
}
