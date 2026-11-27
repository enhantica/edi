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
            verify(SettingsProof.write(copy, file, structure + "\n_edi_structure.calc_method " + methods[phase] + "\n"), "The disposable input declares each requested method through its structure item");
        }
        verify(Session.openProject(copy), "The real app opens the hand-authored powder project");
        tryVerify(() => app.pagesWanted > 0 && app.pagesWanted === app.pagesBuilt, 10000, "The app instantiates the production workflow pages");
        tryCompare(Session.project, "calculating", false, 10000, "The loaded powder fixture finishes calculating before pointer input");
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
        openProject("tests/fixtures/magnetic_stall/frame");
        const structurePage = page("structure");
        const groups = ["atom_site", "atom_site_aniso", "atom_site_moment"];
        compare(atomGroups(), groups, "Magnetic Rietveld shows atoms, ADPs and moments");
        const table = findChild(structurePage, "structures.list");
        const headers = Render.descendants(table.headerItem).filter(item => item.visible);
        const header = name => headers.find(item => item.text === name);
        const typeHeading = header("Type");
        const structureHeading = header("Structure");
        const calculationHeading = header("Calculation");
        verify(typeHeading && structureHeading && calculationHeading, "The Structures table visibly labels Type, Structure and Calculation");
        const x = item => item.mapToItem(table.headerItem, 0, 0).x;
        verify(x(typeHeading) < x(structureHeading) && x(structureHeading) < x(calculationHeading), "Calculation follows Structure and Type in the rendered column order");
        compare(calculation(0).currentText, "Rietveld", "A saved structure with no method defaults to Rietveld");
        const before = Session.project.currentStructure.text.text;
        for (const method of ["Le Bail", "Pawley"]) {
            choose(0, method);
            tryVerify(() => atomGroups().length === 0, 2000, "Profile matching hides the atom-site, ADP and moment groups");
            choose(0, "Rietveld");
            tryVerify(() => JSON.stringify(atomGroups()) === JSON.stringify(groups), 2000, "Switching back returns the three rendered atom groups");
            compare(Session.project.currentStructure.text.text, before, "Switching back preserves every atom, ADP and magnetic moment declaration");
        }
    }

    function test_experiment_scale_and_weight_fraction() {
        openProject("tests/fixtures/powder_calculation/two_banks", {
            "alpha": "le_bail"
        });
        const experimentPage = page("experiment");
        Ui.expandGroup(test, Probe, app, "group.linked_structure");
        const table = findChild(experimentPage, "linkedStructure.list");
        verify(table && table.count === 2, "The experiment displays both independently linked phases");
        const scale = findChild(rowAt(table, 0), "linkedStructure.scale.0");
        const control = findChild(rowAt(table, 1), "linkedStructure.scale.1");
        verify(scale && scale.visible && !scale.enabled && !scale.item.fittable, "The Le Bail phase's scale is visible and disabled for fitting");
        verify(/Le Bail|profile match|intensit/i.test(String(scale.item.fitReason)), "The disabled scale names the active intensity extraction in its reason");
        verify(control && control.visible && control.enabled && control.item.fittable, "The other phase in the same experiment keeps its normal Rietveld scale");
        const fraction = findChild(experimentPage, "linkedStructure.weightFraction.0");
        compare(fraction.shownValue, "—", "The linked Le Bail phase has no displayed weight fraction");
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
            press(box);
            tryCompare(box, "checked", !initial, 2000, "The grouped Pawley Free checkbox changes the selected pair");
        }
    }
}
