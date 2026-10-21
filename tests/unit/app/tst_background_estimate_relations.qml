import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0

TestCase {
    id: test
    name: "BackgroundEstimateRelations"
    when: windowShown
    function init() { Session.closeProject(); }
    function cleanup() { Session.closeProject(); Probe.releaseScratchProjects(); }
    function points() {
        return Probe.rows(Session.project.currentExperiment.background).map(row => [row.position, row.intensity.value]);
    }
    function input(cell, normalized, mode) {
        const project = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/lifecycle-model"));
        let experiment = SettingsProof.text(project, "experiments/hrpt.edi");
        experiment = experiment.replace(/^_background_estimate\..*\n/gm, "");
        experiment = experiment.replace(/(_linked_structure.scale\n\S+)\s+\S+/, "$1 " + (!cell && normalized ? "2.5" : "10"));
        experiment += "\n_background_estimate.mode " + mode + "\n_background_estimate.method snip\n_background_estimate.width 7.25\n_background_estimate.n_points 9\n_background_estimate.use_model true\n";
        verify(SettingsProof.write(project, "experiments/hrpt.edi", experiment), "The app input must declare a due guided estimate");
        if (cell && normalized) {
            const structure = SettingsProof.text(project, "structures/lbco.edi").replace(/^(_cell.length_[abc]) .*$/gm, "$1 3.9375");
            verify(SettingsProof.write(project, "structures/lbco.edi", structure), "The control must explicitly complete cubic cell relations");
        }
        const target = cell ? "lbco.cell.length_a" : "hrpt.linked_structure.lbco.scale";
        const value = cell ? "3.9375" : "2.5";
        verify(SettingsProof.write(project, "analysis/analysis.edi", "_edi.schema_version 3\n_fitting_mode.type single\nloop_\n_alias.id\n_alias.parameter_unique_name\ntarget " + target + "\nloop_\n_constraint.expression\n\"target = " + value + "\"\n"),
               "The app must load a valid value-changing declared relation");
        return project;
    }
    function open(project) {
        verify(Session.openProject(project), "The app must accept the related nonzero-model project");
        tryVerify(() => !Session.project.calculating && !Session.project.currentExperiment.pattern.stale,
                  2000, "The related-model automatic preview must complete");
        verify(Probe.rows(Session.project.currentExperiment.pattern).some(row =>
               row.calcStatus === "incl" && Math.abs(row.intensityCalc - row.intensityBkg) > 1e-8),
               "Relation-order parity must retain nonzero model peaks");
    }
    function comparePoints(expected, reason) {
        const actual = points();
        compare(actual.length, expected.length, reason + ": anchor count");
        for (let index = 0; index < expected.length; ++index) {
            compare(actual[index][0], expected[index][0], reason + ": positions");
            verify(Math.abs(actual[index][1] - expected[index][1]) <= 1e-9 + 2e-12 * Math.abs(expected[index][1]),
                   reason + ": heights must use the relation-applied model");
        }
    }
    function relation(cell) {
        open(input(cell, true, "auto"));
        const expected = points();
        Session.closeProject();
        open(input(cell, false, "auto"));
        comparePoints(expected, "Opening an automatic project must evaluate declared and symmetry relations before subtracting model peaks");
    }
    function test_open_applies_scale_relation_before_guided_estimate() { relation(false); }
    function test_open_completes_symmetry_before_guided_estimate() { relation(true); }
    function test_auto_setting_edit_applies_changed_relation_before_guided_estimate() {
        const control = input(false, true, "auto");
        verify(SettingsProof.write(control, "analysis/analysis.edi", SettingsProof.text(control, "analysis/analysis.edi").replace("target = 2.5", "target = 1.25")),
               "The edit control must declare the same changed relation");
        verify(SettingsProof.write(control, "experiments/hrpt.edi", SettingsProof.text(control, "experiments/hrpt.edi").replace(/(_linked_structure.scale\n\S+)\s+\S+/, "$1 1.25")),
               "The edit control must carry the explicitly applied target value");
        open(control);
        const expected = points();
        Session.closeProject();
        open(input(false, true, "manual"));
        verify(Session.project.analysis.constraints.setText(0, "expression", "target = 1.25"),
               "The public app relation edit must be admitted");
        Session.project.currentExperiment.backgroundEstimateMode = "auto";
        tryVerify(() => !Session.project.calculating && !Session.project.currentExperiment.pattern.stale,
                  2000, "The relation and auto-setting edit must publish a completed preview");
        comparePoints(expected, "Auto-setting changes must use the newly applied relation before refreshing");
    }
}
