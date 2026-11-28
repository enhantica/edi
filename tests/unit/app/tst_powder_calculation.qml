// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "PowderCalculation"
    when: windowShown
    property var app

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
        verify(app && waitForRendering(app.contentItem), "The Calculation tests use the rendered production application");
    }

    function cleanup() {
        Session.closeProject();
        Probe.releaseScratchProjects();
    }

    function cleanupTestCase() {
        if (app)
            app.destroy();
    }

    function page(name) {
        Ui.click(test, Probe, app, "appBar.tab." + name);
        Ui.click(test, Probe, app, "sideBar.tab.basic");
        return Ui.page(app);
    }

    function openProject(path, methods = {}) {
        const copy = SettingsProof.copyProject(Probe.repoUrl(path));
        for (const phase of Object.keys(methods)) {
            const file = "structures/" + phase + ".edi";
            const structure = SettingsProof.text(copy, file);
            verify(structure.includes("data_" + phase), "The authored method is set on the intended structure block");
            const tag = phase === "beta" ? "_edi_structure.calc_method" : "_structure.calc_method";
            verify(SettingsProof.write(copy, file, structure + "\n" + tag + " " + methods[phase] + "\n"), "The disposable input declares each requested method through its structure item");
        }
        if (Object.values(methods).includes("pawley"))
            seedPawleyRows(copy);
        verify(Session.openProject(copy), "The real app opens the hand-authored powder project: " + Session.lastError);
        tryVerify(() => app.pagesWanted > 0 && app.pagesWanted === app.pagesBuilt, 10000, "The app instantiates the production workflow pages");
        tryCompare(Session.project, "calculating", false, 10000, "The loaded powder fixture finishes calculating before pointer input");
        return copy;
    }

    function seedPawleyRows(copy) {
        const fields = ["structure_id", "index_h", "index_k", "index_l", "f_squared"];
        for (const bank of ["first", "second"]) {
            const file = "experiments/" + bank + ".edi";
            const source = SettingsProof.text(copy, file);
            const category = bank === "first" ? "_extracted_intensity." : "_edi_extracted_intensity.";
            const loop = fields.map(field => category + field).join("\n");
            verify(SettingsProof.write(copy, file, source + "\nloop_\n" + loop + "\nalpha 1 0 0 7.5()\nbeta 1 0 0 4.25()\n"), "Each measured bank starts with an authored free hkl for each Pawley structure");
        }
    }

    function press(item) {
        verify(item !== null && item !== undefined && item.enabled, "The actual visible acceptance control is available for pointer input");
        Ui.scrollIntoView(Ui.target(item));
        verify(waitForPolish(app.contentItem) && waitForRendering(app.contentItem), "The scrolled control reaches a real rendered frame");
        const at = Ui.clickPoint(Ui.target(item));
        verify(at !== null, "The acceptance control has an exposed pointer target");
        let delay = 0;
        for (let parent = item.parent; parent; parent = parent.parent) {
            if (typeof parent.pressDelay === "number")
                delay = Math.max(delay, parent.pressDelay + 1);
        }
        mouseClick(Ui.target(item), at.x, at.y, Qt.LeftButton, Qt.NoModifier, delay);
    }

    function rowAt(table, index) {
        table.positionViewAtIndex(index, ListView.Contain);
        table.forceLayout();
        tryVerify(() => table.itemAtIndex(index) !== null, 2000, "The actual table renders the requested data row");
        return table.itemAtIndex(index);
    }

    function calculation(index) {
        const table = findChild(Ui.page(app), "structures.list");
        verify(table !== null, "The Structure page uses its real Structures table");
        const row = rowAt(table, index);
        const matches = Render.descendants(row).filter(item => item.visible && typeof item.textAt === "function" && item.count === 3 && item.textAt(0) === "Rietveld" && item.textAt(1) === "Le Bail" && item.textAt(2) === "Pawley");
        compare(matches.length, 1, "Each Structure row offers one Calculation selector with the three specified methods");
        return matches[0];
    }

    function choose(index, method) {
        const selector = calculation(index);
        const option = ["Rietveld", "Le Bail", "Pawley"].indexOf(method);
        press(selector);
        tryCompare(selector.popup, "opened", true, 2000, "The Calculation options open on pointer input");
        press(rowAt(selector.popup.contentItem, option));
        tryCompare(selector, "currentText", method, 2000, "The clicked method becomes the selected Calculation");
        tryCompare(Session.project, "calculating", false, 10000, "The real method edit completes its update");
    }

    function atomGroups() {
        const visible = Render.descendants(Ui.page(app)).filter(item => item.visible && item.shown !== false);
        return ["atom_site", "atom_site_aniso", "atom_site_moment"].filter(id => visible.some(item => item.objectName === "group." + id));
    }

    function test_calculation_column_and_magnetic_atom_content() {
        const location = openProject("tests/fixtures/magnetic_stall/frame");
        const structureFile = "structures/cosio.edi";
        const structurePage = page("structure");
        const groups = ["atom_site", "atom_site_aniso", "atom_site_moment"];
        compare(atomGroups(), groups, "Magnetic Rietveld shows atoms, ADPs and moments");
        const table = findChild(structurePage, "structures.list");
        verify(table && table.headerItem, "The Structures table and header are rendered");
        const headers = Render.descendants(table.headerItem).filter(item => item.visible);
        const header = name => headers.find(item => item.text === name);
        const typeHeading = header("Type");
        const structureHeading = header("Structure");
        const calculationHeading = header("Calculation");
        verify(typeHeading && structureHeading && calculationHeading, "The Structures table visibly labels Type, Structure and Calculation");
        const x = item => item.mapToItem(table.headerItem, 0, 0).x;
        verify(x(typeHeading) < x(structureHeading) && x(structureHeading) < x(calculationHeading), "Calculation follows Structure and Type in the rendered column order");
        compare(calculation(0).currentText, "Rietveld", "A saved structure with no method defaults to Rietveld");
        verify(Session.save(), "The original Rietveld project saves through the app");
        const before = SettingsProof.text(location, structureFile);
        verify(before.includes("_atom_site.id") && before.includes("_atom_site_moment."), "The saved byte control contains the authored atoms and moments");
        for (const method of ["Le Bail", "Pawley"]) {
            choose(0, method);
            tryVerify(() => atomGroups().length === 0, 2000, "Profile matching hides the atom-site, ADP and moment groups");
            verify(Session.save(), "The selected profile-matching method saves through the app");
            const token = method.toLowerCase().replace(" ", "_");
            const saved = SettingsProof.text(location, structureFile);
            verify(new RegExp("^_structure\\.calc_method\\s+" + token + "\\s*$", "m").test(saved), "The chosen method is saved under the canonical native structure item");
            choose(0, "Rietveld");
            tryVerify(() => JSON.stringify(atomGroups()) === JSON.stringify(groups), 2000, "Switching back returns the three rendered atom groups");
            verify(Session.save(), "The restored Rietveld method saves through the app");
            compare(SettingsProof.text(location, structureFile), before, "Switching back preserves the saved Rietveld structure, including every atom, ADP and moment");
        }
    }

    function linkedTable() {
        const experimentPage = page("experiment");
        Ui.expandGroup(test, Probe, app, "group.linked_structure");
        const table = findChild(experimentPage, "linkedStructure.list");
        verify(table && table.count === 2, "The experiment displays both independently linked phases");
        return table;
    }

    function test_rietveld_powder_project_keeps_editable_scales() {
        openProject("tests/fixtures/powder_calculation/two_banks");
        const table = linkedTable();
        for (let index = 0; index < table.count; ++index) {
            const scale = findChild(rowAt(table, index), "linkedStructure.scale." + index);
            verify(scale && scale.visible && scale.enabled && scale.item.fittable, "A phase in the ordinary Rietveld project retains its editable scale");
        }
    }

    function test_experiment_scale_and_weight_fraction() {
        openProject("tests/fixtures/powder_calculation/two_banks", {
            "alpha": "le_bail"
        });
        const table = linkedTable();
        const scale = findChild(rowAt(table, 0), "linkedStructure.scale.0");
        const control = findChild(rowAt(table, 1), "linkedStructure.scale.1");
        verify(scale && scale.visible && scale.enabled, "The Le Bail phase still displays its held scale value");
        verify(!scale.item.fittable, "The Le Bail scale is ineligible for fitting");
        verify(/Le Bail|profile match|intensit/i.test(String(scale.item.fitReason)), "The disabled Free control names intensity extraction in its reason");
        const popup = Ui.parameterPopup(test, scale, Qt.LeftButton);
        const toggle = Ui.parameterPopupItem(test, scale, popup, "free");
        verify(toggle && !toggle.enabled, "The real Le Bail scale Free checkbox is disabled");
        keyClick(Qt.Key_Escape);
        tryCompare(popup, "opened", false, 2000, "The linked scale editor closes before comparing rows");
        verify(control && control.visible && control.enabled && control.item.fittable, "The other phase in the same experiment keeps its normal Rietveld scale");
        for (let index = 0; index < table.count; ++index) {
            const fraction = findChild(rowAt(table, index), "linkedStructure.weightFraction." + index);
            compare(fraction.shownValue, "—", "The experiment with a Le Bail link has no displayed weight fractions");
        }
    }

    function test_one_pawley_free_row_per_structure_and_experiment() {
        openProject("tests/fixtures/powder_calculation/two_banks", {
            "alpha": "pawley",
            "beta": "pawley"
        });
        const analysis = page("analysis");
        const table = findChild(analysis, "parameters.list");
        verify(table, "Analysis displays the actual Parameters table");
        const model = table.sourceModel;
        model.nameFilter = "Pawley intensities";
        tryCompare(table, "count", 4, 2000, "Two Pawley structures linked to two experiments give one row for each pair");
        const names = Probe.rows(model).map(row => row.parameter.fullName);
        for (const phase of ["alpha", "beta"]) {
            for (const bank of ["first", "second"]) {
                compare(names.filter(name => name.includes(phase) && name.includes(bank)).length, 1, "Every Pawley row identifies its unique structure and experiment");
            }
        }
        for (let index = 0; index < table.count; ++index) {
            const row = rowAt(table, index);
            const label = Render.descendants(row).find(item => /Pawley intensities \(1\)/.test(item.text || ""));
            verify(label, "Each grouped label displays the count from the independent one-line Bragg window");
            const boxes = Render.descendants(row).filter(item => item.visible && /^parameters\.free\./.test(item.objectName));
            compare(boxes.length, 1, "Each grouped Pawley row exposes exactly one Free checkbox");
            const box = boxes[0];
            const initial = box.checked;
            const expected = Probe.rows(model).map(row => row.parameter.free);
            expected[index] = !initial;
            press(box);
            tryCompare(box, "checked", !initial, 2000, "The grouped Pawley Free checkbox changes the selected pair");
            compare(Probe.rows(model).map(row => row.parameter.free), expected, "Toggling one Pawley pair preserves the other experiment and structure Free flags");
        }
    }
}
