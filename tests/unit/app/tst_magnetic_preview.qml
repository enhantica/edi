import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render
import "E04Review.js" as Review

TestCase {
    id: test
    name: "MagneticPreview"
    when: windowShown
    property var appWindow
    property var scratch
    Component { id: application; Main {} }
    Component { id: pattern; PatternChart { width: 1200; height: 800 } }
    function init() {
        scratch = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/magnetic_pnma/app-project"));
        verify(Session.openProject(scratch), "The magnetic preview opens the independent cobalt input");
        appWindow = application.createObject(null, { width: 1400, height: 1000, visible: true });
        verify(appWindow !== null, "Magnetic display checks use the production application window");
        tryVerify(() => appWindow.pagesBuilt > 0 && appWindow.pagesBuilt === appWindow.pagesWanted, 10000, "The magnetic project builds its real pages");
        tryCompare(Session.project, "calculating", false, 15000, "The initial magnetic calculation finishes");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
    }
    function click(name) { Ui.click(test, Probe, appWindow, name); }
    function groups(page, tier) {
        click("appBar.tab." + page);
        click("sideBar.tab." + tier);
        verify(waitForPolish(appWindow.contentItem), "Magnetic page groups finish layout");
        return Render.descendants(Ui.page(appWindow)).filter(item => typeof item.title === "string" && typeof item.collapsed === "boolean" && (item.shown === true || (item.categoryId === undefined && item.visible)));
    }
    function group(id, page, tier) {
        const found = groups(page || "structure", tier || "basic").filter(item => item.categoryId === id);
        compare(found.length, 1, "Each magnetic category has one displayed group: " + id);
        found[0].collapsed = false;
        Ui.scrollIntoView(found[0]);
        verify(waitForPolish(found[0]), "The opened magnetic category completes layout");
        return found[0];
    }
    function test_extra_groups_are_single_ordered_and_human_readable() {
        const shown = groups("structure", "extras");
        const appearances = shown.filter(item => /^Appearance/.test(item.title));
        compare(appearances.length, 1, "The two preview Appearance groups are merged into one");
        verify(!shown.some(item => item.categoryId === "parent_space_group"), "The crystal parent has no duplicate Extra group");
        verify(!shown.some(item => item.categoryId === "magnetic_form_factor"), "The ion selector belongs to moment rows, not a separate group");
        const ids = shown.map(item => item.categoryId);
        for (const id of ["space_group_symop_magn_operation", "space_group_symop_magn_centering", "expanded_atom_site_moment"])
            verify(ids.includes(id), "Extra retains the signed operators and moments in the cell: " + id);
        const magnetic = shown.filter(item => /magn|moment/.test(item.categoryId));
        verify(magnetic.length > 0, "Extra exposes actual magnetic groups");
        const crystal = shown.filter(item => ["cell", "atom_site", "atom_site_aniso", "space_group_symop"].includes(item.categoryId));
        verify(crystal.every(c => magnetic.every(m => shown.indexOf(c) < shown.indexOf(m))), "Extra magnetic groups follow the existing crystal groups");
        const labels = Render.descendants(Ui.page(appWindow)).filter(item => typeof item.label === "string").map(item => item.label);
        verify(!labels.some(label => /number_BNS|name_BNS|name_UNI/.test(label)), "GUI labels use readable BNS and UNI titles instead of CIF item names");
    }
    function test_main_order_all_sites_ids_ions_and_symmetry_form() {
        const shown = groups("structure", "basic");
        const ids = shown.map(item => item.categoryId);
        const firstMagnetic = ids.findIndex(id => id === "space_group_magn");
        verify(firstMagnetic >= 0, "Main exposes the magnetic space group");
        for (const id of ["space_group", "cell", "atom_site", "atom_site_aniso"])
            verify(ids.indexOf(id) >= 0 && ids.indexOf(id) < firstMagnetic, "Magnetic Main groups follow each crystal group: " + id);
        const moments = group("atom_site_moment");
        const table = Render.descendants(moments).find(item => item.sourceModel !== undefined && typeof item.itemAtIndex === "function");
        verify(table !== undefined, "Moments uses the shared row table");
        compare(table.count, 6, "Moments lists all six atom sites, including sites without a moment");
        verify(/\(6\)/.test(moments.title), "The moments header reports its actual row count");
        const headers = Render.cells(table.headerItem).filter(item => item.visible && item.width > 1);
        verify(headers.some(item => String(item.text).toLowerCase() === "id"), "The first identity column is id, as in Atomic displacement");
        verify(!headers.some(item => String(item.text).toLowerCase() === "label"), "The preview label heading is replaced by id");
        verify(headers.some(item => /ion|form factor/i.test(String(item.text))), "Every moment row exposes its magnetic ion choice");
        verify(!headers.some(item => /[μµ]B|Bohr/.test(String(item.text))), "Moment units follow shared field tooltips rather than custom column headings");
        const forms = Render.descendants(moments).filter(item => /symmform|symmetry.?form/i.test(item.objectName || ""));
        verify(forms.length > 0, "The derived symmetry form is displayed");
        verify(forms.every(item => !("readOnly" in item) || item.readOnly || !item.enabled), "Symmetry form is read-only in every displayed editor");
        const displacement = group("atom_site_aniso");
        verify(/\(6\)/.test(displacement.title), "Atomic displacement reports all six site rows instead of zero");
    }
    function test_magnetic_selector_and_scale_use_one_editing_surface() {
        const magnetic = group("space_group_magn");
        const selectors = Render.descendants(magnetic).filter(item => typeof item.textAt === "function" && item.editable === true);
        compare(selectors.length, 1, "The magnetic name fields share one searchable selector");
        const appearances = groups("structure", "extras").filter(item => /^Appearance/.test(item.title));
        compare(appearances.length, 1, "Magnetic scale is edited in the single Appearance group");
        appearances[0].collapsed = false;
        const fields = Render.descendants(appearances[0]).filter(item => typeof item.label === "string");
        const atom = fields.find(item => item.label === "Atom scale");
        const moment = fields.find(item => item.label === "Moment scale");
        verify(atom !== undefined && moment !== undefined, "Appearance places Moment scale alongside Atom scale");
        compare(Session.project.structureViewOptions.momentScale, .75, "Default moment length is 1.5 times the preview length");
        Session.project.structureViewOptions.momentScale = 1.125;
        verify(Session.save(), "The selected appearance scale saves through the real project");
        Session.closeProject();
        verify(Session.openProject(scratch), "The saved magnetic appearance reopens");
        compare(Session.project.structureViewOptions.momentScale, 1.125, "Moment scale survives project save and reload");
    }
    function test_visibility_keeps_camera_and_independent_moments() {
        click("appBar.tab.structure");
        const view = Review.find(Ui.page(appWindow), "structure.view");
        verify(view !== null, "The magnetic case reaches the real structure view");
        tryVerify(() => view.current, 10000, "The magnetic scene is current before visibility edits");
        const controller = view.controller;
        controller.viewAnimationDuration = 0;
        const state = () => JSON.stringify({position: controller.cameraPosition, rotation: controller.cameraRotation, projection: controller.cameraProjection, zoom: controller.magnification});
        const before = state();
        const options = Session.project.structureViewOptions;
        for (const change of [["atoms", "none"], ["bonds", false], ["showMoments", false], ["showMoments", true], ["cell", false]]) {
            options[change[0]] = change[1];
            verify(waitForRendering(view), "A visibility edit reaches a rendered frame");
            compare(state(), before, "Showing or hiding structure features preserves camera position, projection and zoom");
        }
        verify(options.showMoments && controller.hasMoments, "Moments remain enabled and present with atoms hidden");
    }
    function test_analysis_contains_only_independent_magnetic_components() {
        click("appBar.tab.analysis");
        const rows = Probe.rows(Session.project.parameters).filter(row => row.category === "atom_site_moment");
        compare(rows.length, 6, "Analysis exposes the six components of the two magnetic sites");
        compare(rows.filter(row => row.fittable).length, 4, "Analysis allows exactly four symmetry-independent cobalt components");
        const filters = Probe.objectsWithProperty(Ui.page(appWindow), "categoryGroups");
        verify(filters.some(filter => filter.categoryGroups.some(row => row.key === "atom_site_moment" && /Magnetic moments/.test(row.title))), "The Analysis category uses the readable Magnetic moments title");
    }
    function test_nuclear_and_magnetic_tick_rows_cover_the_independent_reflections() {
        const chart = pattern.createObject(appWindow.contentItem, {experiment: Session.project.currentExperiment});
        verify(chart !== null && waitForPolish(chart), "The magnetic chart reaches the actual shared controller");
        tryVerify(() => Probe.objectsWithProperty(chart, "braggLabels").length === 1, 5000, "The pattern uses one presentation controller");
        const controller = Probe.objectsWithProperty(chart, "braggLabels")[0];
        tryCompare(controller, "braggRows", 2, 5000, "A magnetic phase has separate nuclear and magnetic tick rows");
        const labels = controller.braggLabels;
        const magnetic = labels.find(row => /magnetic/i.test(row.text));
        const nuclear = labels.find(row => /nuclear/i.test(row.text));
        verify(magnetic !== undefined && nuclear !== undefined, "Both reflection row labels state their scattering contribution");
        verify(String(magnetic.color) !== String(nuclear.color), "The two reflection rows use distinct fill colours");
        const series = Render.series(chart).filter(item => String(item.objectName).startsWith("chart.series.bragg.") && item.at !== undefined);
        const magneticRows = series.filter(row => row.count > 0 && Math.abs(row.at(0).y - magnetic.centre) < .5);
        compare(magneticRows.length, 1, "The magnetic label belongs to one actual tick series");
        const actual = [];
        for (let i = 0; i < magneticRows[0].count; ++i) actual.push(magneticRows[0].at(i).x);
        const expected = JSON.parse(SettingsProof.text(Probe.repoUrl("tests/fixtures/magnetic_pnma"), "magnetic-ticks.json"));
        for (const angle of expected)
            verify(actual.some(x => Math.abs(x - angle) < .0001), "Every independent allowed magnetic reflection has its tick, including nuclear-forbidden peaks");
        chart.destroy();
    }
    function test_k_editor_refuses_without_changing_the_saved_model() {
        const propagation = group("parent_propagation_vector");
        const editors = Render.descendants(propagation).filter(item => typeof item.text === "string" && "readOnly" in item && !item.readOnly && item.enabled);
        verify(editors.length > 0, "Propagation rows expose the validated editable k input");
        verify(Session.save(), "The valid propagation model saves before the refused edit");
        const before = SettingsProof.text(scratch, "structures/cosio.edi");
        const editor = editors[editors.length - 1];
        const old = editor.text;
        editor.forceActiveFocus();
        keyClick(Qt.Key_A, Qt.ControlModifier);
        editor.text = "1/3,0,0";
        keyClick(Qt.Key_Return);
        tryCompare(editor, "text", old, 2000, "The primitive third-order k is refused and the editor restores the old row");
        verify(Session.save(), "A refused k edit leaves a saveable consistent model");
        compare(SettingsProof.text(scratch, "structures/cosio.edi"), before, "A refused GUI propagation edit writes no change to the model");
    }
    function test_catalogue_count_and_selector_operator_replacement() {
        const magnetic = group("space_group_magn");
        const selectors = Render.descendants(magnetic).filter(item => typeof item.textAt === "function" && item.editable === true);
        compare(selectors.length, 1, "The vendored groups reach one searchable magnetic selector");
        const selector = selectors[0];
        compare(selector.count, 1651, "The selector contains every independently counted BNS group");
        function choice(number) {
            for (let i = 0; i < selector.count; ++i)
                if (selector.textAt(i).includes(number)) return i;
            return -1;
        }
        const grey = choice("62.442");
        verify(grey >= 0, "The independent grey Pnma identity is searchable by BNS number");
        selector.currentIndex = grey;
        selector.activated(grey);
        tryCompare(Session.project, "calculating", false, 15000, "The accepted group selection recalculates through the core");
        const moments = Probe.rows(Session.project.parameters).filter(row => row.category === "atom_site_moment");
        verify(moments.length >= 6 && moments.every(row => Number(row.value) === 0), "Selecting grey Pnma replaces signed operators and fixes every moment at zero");
        verify(Session.save(), "The selected grey group saves through the native writer");
        const before = SettingsProof.text(scratch, "structures/cosio.edi");
        verify(before.includes("62.442") && /x,y,z,-1/.test(before.replace(/\s+/g, "")), "The saved BNS identity and negative-time identity agree after selection");
        const incompatible = choice("1.3");
        verify(incompatible >= 0, "The type-IV control is present in the same catalogue");
        selector.currentIndex = incompatible;
        selector.activated(incompatible);
        verify(Session.save(), "A refused incompatible selector choice leaves a saveable prior model");
        compare(SettingsProof.text(scratch, "structures/cosio.edi"), before, "The selector cannot replace operators with a group incompatible with the current propagation");
        verify(Probe.rows(Session.loadWarnings).some(row => /propagation|translation|lattice|magnetic/i.test(row.message)), "A refused magnetic selection gives its acceptance-rule reason");
    }
    function test_propagation_rows_add_remove_and_refuse_duplicates_data() {
        return [{tag: "fraction-first", first: "1/2", duplicate: "0.5"},
                {tag: "decimal-first", first: "0.5", duplicate: "1/2"}];
    }
    function test_propagation_rows_add_remove_and_refuse_duplicates(data) {
        const location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/magnetic_pnma/propagation-project"));
        const original = SettingsProof.text(location, "structures/cosio.edi");
        verify(SettingsProof.write(location, "structures/cosio.edi", original.replace("1/2,0,0", data.first + ",0,0")), "The duplicate control independently chooses its exact starting spelling");
        verify(Session.openProject(location), "The period-22 edit control opens with one valid half-order row");
        const vectors = group("parent_propagation_vector");
        const objects = () => Render.descendants(vectors);
        const table = objects().find(item => item.sourceModel !== undefined && typeof item.itemAtIndex === "function");
        verify(table !== undefined && table.count === 1, "The propagation control starts with exactly one row");
        const removes = () => objects().filter(item => typeof item.clicked === "function" && /remove|delete/i.test((item.objectName || "") + " " + (item.toolTip || "")));
        verify(removes().length === 1 && !removes()[0].enabled, "The final propagation row cannot be removed");
        verify(!objects().some(item => /enable|active/i.test(item.objectName || "") && "checked" in item), "Propagation rows have no enable toggle");
        const add = objects().find(item => typeof item.clicked === "function" && item.text === "Add vector");
        verify(add !== undefined && add.width > vectors.width * .6, "A wide Add vector button sits below the propagation table");
        mouseClick(add);
        tryCompare(table, "count", 2, 2000, "Add vector creates a second compatible distinct row");
        verify(Session.save(), "The two accepted propagation rows save");
        const before = SettingsProof.text(location, "structures/cosio.edi");
        const editors = objects().filter(item => typeof item.text === "string" && "readOnly" in item && !item.readOnly && item.enabled);
        verify(editors.length >= 2, "Both propagation rows have real editable k fields");
        const editor = editors[editors.length - 1];
        const old = editor.text;
        for (const value of [data.duplicate + ",0,0", "1/3,0,0"]) {
            editor.forceActiveFocus();
            editor.text = value;
            keyClick(Qt.Key_Return);
            tryCompare(editor, "text", old, 2000, "An exact duplicate or incompatible k restores the previous row");
            verify(Session.save(), "A refused propagation edit keeps a valid saveable row set");
            compare(SettingsProof.text(location, "structures/cosio.edi"), before, "Duplicate and incompatible edits preserve every prior propagation row");
            verify(Probe.rows(Session.loadWarnings).some(row => /duplicate|propagation|translation|commensurate/i.test(row.message)), "Each refused row edit explains the acceptance-rule failure");
        }
        verify(removes().length === 2 && removes().every(item => item.enabled), "Every row can be removed while another remains");
        mouseClick(removes()[1]);
        tryCompare(table, "count", 1, 2000, "Removing a propagation row leaves its peer intact");
        verify(removes().length === 1 && !removes()[0].enabled, "Removal disables again at the last remaining row");
    }
    function test_named_magcif_import_uses_the_app_loader_data() {
        return [{tag: "isodistort", file: "isodistort.mcif"}, {tag: "fullprof", file: "cosio1.mcif"}];
    }
    function test_named_magcif_import_uses_the_app_loader(data) {
        const before = Probe.rows(Session.project.structures).length;
        verify(Session.project.loadStructure(Probe.repoUrl("tests/fixtures/magnetic_pnma/cosio/" + data.file)), "The app imports each independently supplied magnetic CIF");
        compare(Probe.rows(Session.project.structures).length, before + 1, "MagCIF import adds one structure through the core loader");
        if (data.tag === "isodistort")
            verify(Probe.rows(Session.loadWarnings).some(row => /mode/i.test(row.message) && /not.*fit|later|component/i.test(row.message)), "Import explains that retained mode definitions are not yet fittable amplitudes");
        verify(Probe.rows(Session.project.currentStructure.categories).some(row => row.categoryId === "atom_site_moment"), "The imported magnetic category reaches the actual app model");
    }
}
