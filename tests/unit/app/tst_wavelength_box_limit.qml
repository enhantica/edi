// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "WavelengthBoxLimit"
    when: windowShown
    property var app
    Component { id: windowFactory; Main {} }

    function cleanup() {
        Session.closeProject();
        if (app)
            app.destroy();
        app = null;
    }

    function enter(field, text) {
        Ui.scrollIntoView(field);
        const point = Ui.clickPoint(field);
        verify(point !== null, "The instrument wavelength field must be reachable");
        field.forceActiveFocus();
        tryCompare(field, "activeFocus", true, 2000, "The wavelength editor receives the actual window input");
        verify(SettingsProof.type(field, text) && SettingsProof.key(field, Qt.Key_Return),
               "A real wavelength draft is submitted through the normal value box");
    }

    function openProject(root) {
        app = windowFactory.createObject(null);
        verify(app !== null, "The wavelength witness uses the running production window");
        app.requestActivate();
        tryCompare(app, "active", true, 2000, "The wavelength window is active before real keyboard input");
        verify(Session.openProject(root), "The private wavelength project opens");
    }

    function wavelengthField() {
        Ui.click(test, Probe, app, "appBar.tab.experiment");
        Ui.click(test, Probe, app, "sideBar.tab.basic");
        Ui.expandGroup(test, Probe, app, "group.instrument");
        const field = Ui.find(Ui.page(app), "instrument.setup_wavelength", true);
        verify(field !== null && field.enabled && field.item !== null,
               "The real primary wavelength is editable in the Instrument group");
        return field;
    }

    function test_wavelength_is_refused_when_the_linked_cell_exceeds_the_reflection_budget() {
        const root = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project"));
        const path = "structures/lbco.edi";
        const original = SettingsProof.text(root, path);
        const edge = 6.7;
        const requested = 0.1;
        // The fixture ends at 164.85 degrees two-theta. Bragg's law and the
        // orthogonal cell exceed the calculation's candidate budget at 0.1 Å,
        // without submitting any smaller wavelength.
        const d = requested / (2 * Math.sin(164.85 * Math.PI / 360));
        const side = 2 * (Math.floor(edge / d) + 1) + 1;
        verify(side ** 3 > 18000000, "The proposed physical wavelength crosses the documented candidate limit");
        // Use the normal neutron table so this fixture can calculate before the rejected edit.
        const customScattering = original.indexOf("\nloop_\n_scattering_length.type_symbol");
        verify(customScattering > 0, "The source fixture's incomplete scattering override can be removed");
        const enlarged = original.slice(0, customScattering).replace(/^_cell\.length_([abc]) .*$/gm,
                                                                     "_cell.length_$1 " + edge);
        verify(enlarged !== original && SettingsProof.write(root, path, enlarged),
               "The private project links an enlarged orthogonal cell to the saved measurement range");

        openProject(root);
        const field = wavelengthField();
        compare(field.item.value, 1.494, "The original fixture starts at its recorded wavelength");
        enter(field, "1.6");
        tryCompare(field.item, "value", 1.6, 2000, "A wavelength safely inside the reflection budget is accepted");
        const pattern = Session.project.currentExperiment.pattern;
        tryCompare(Session.project, "calculating", false, 5000,
                   "The preceding valid wavelength has finished calculating before the next edit");
        compare(pattern.calculationError, "", "The valid wavelength leaves a usable calculation");
        enter(field, String(requested));
        tryVerify(() => /reflection|candidate|d_min/i.test(field.warningText), 5000,
                  "The wavelength field reports the calculation's reason for refusing the reflection list"
                  + "; value=" + field.item.value + "; preview=" + pattern.calculationError
                  + "; field=" + field.warningText);
        compare(field.item.value, 1.6,
                "The wavelength value box must retain the last usable value when the reflection budget is exceeded");
    }

    function test_relation_can_make_another_banks_reflection_list_too_large() {
        const root = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project"));
        const experiment = SettingsProof.text(root, "experiments/hrpt.edi");
        const structure = SettingsProof.text(root, "structures/lbco.edi");
        const scattering = structure.indexOf("\nloop_\n_scattering_length.type_symbol");
        verify(scattering > 0 && SettingsProof.write(root, "structures/lbco.edi", structure.slice(0, scattering)),
               "Both banks use the complete default neutron scattering table");
        const shortWavelength = 0.15;
        verify(SettingsProof.write(root, "experiments/short.edi",
                                   experiment.replace("data_hrpt", "data_short")
                                             .replace("_instrument.setup_wavelength 1.494",
                                                      "_instrument.setup_wavelength " + shortWavelength)),
               "The second bank has the same measured range and an independently fixed shorter wavelength");
        const analysisFile = "analysis/analysis.edi";
        const analysis = SettingsProof.text(root, analysisFile).replace("_fitting_mode.type single",
                                                                        "_fitting_mode.type joint");
        verify(SettingsProof.write(root, analysisFile, analysis + `

loop_
_alias.id
_alias.parameter_unique_name
primary hrpt.instrument.setup_wavelength
edge lbco.cell.length_a

loop_
_constraint.id
_constraint.expression
edge "edge = 3.88 + 80 * (primary - 1.494)"
`), "The first bank's wavelength moves the linked cubic cell shared by both banks");

        openProject(root);
        const project = Session.project;
        const cell = project.currentStructure.cell;
        compare(project.experiments.count, 2, "The joint project opens both powder banks");
        project.currentExperimentIndex = 1;
        compare(project.currentExperiment.name, "short", "The second bank has its own wavelength");
        const secondPattern = project.currentExperiment.pattern;
        const secondWavelength = Probe.rows(project.currentExperiment.instrument).find(
            row => row.parameter && row.parameter.name === "setup_wavelength")?.parameter;
        verify(secondWavelength, "The second bank exposes its primary wavelength");
        compare(secondWavelength.value, shortWavelength, "The second bank loads its shorter wavelength");
        project.currentExperimentIndex = 0;
        compare(project.currentExperiment.name, "hrpt", "Only the first bank's wavelength is edited");
        const firstPattern = project.currentExperiment.pattern;
        const field = wavelengthField();
        compare(field.item.value, 1.494, "The first bank starts at its recorded wavelength");

        enter(field, "1.52");
        tryCompare(field.item, "value", 1.52, 2000, "A linked edit within both banks' budgets is accepted");
        tryCompare(project, "calculating", false, 5000, "Both banks finish the accepted calculation");
        for (const axis of [cell.lengthA, cell.lengthB, cell.lengthC])
            fuzzyCompare(axis.value, 5.96, 1e-7, "The accepted input moves the three cubic lengths through the relation");
        compare(firstPattern.calculationError, "", "The first bank starts with a usable calculation");
        compare(secondPattern.calculationError, "", "The second bank starts with a usable calculation");

        // At the proposed 12.36 Å edge, only the short bank exceeds the
        // documented reflection budget for the measured two-theta range.
        const proposed = 1.6;
        const dMin = wavelength => wavelength / (2 * Math.sin(164.85 * Math.PI / 360));
        const count = wavelength => (2 * (Math.floor(12.36 / dMin(wavelength)) + 1) + 1) ** 3;
        verify(count(proposed) < 18000000 && count(shortWavelength) > 18000000,
               "The proposed cell exceeds the reflection budget only at the unchanged second wavelength");
        enter(field, String(proposed));
        compare(field.item.value, 1.52, "The first bank's wavelength is preserved when the second would be refused");
        tryVerify(() => /reflection|candidate|d_min/i.test(field.warningText), 5000,
                  "The real wavelength field explains the unchanged second bank's refusal");
        fuzzyCompare(cell.lengthA.value, 5.96, 1e-7, "The shared cell is preserved by the refusal");
        compare(secondWavelength.value, shortWavelength, "The refusal preserves the second bank's own wavelength");
        compare(secondPattern.calculationError, "", "The other bank keeps its usable calculation");
    }
}
