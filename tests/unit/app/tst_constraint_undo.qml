import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import RelationUndoReference 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "ConstraintUndo"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Undo must be exercised in the production controller");
        Session.openProject(Probe.repoUrl("tests/fixtures/constraint_expressions/project"));
        verify(Session.hasProject, "The independent declaration fixture must open");
        tryVerify(() => !Session.project.calculating, 10000, "The initial implied values must settle before editing");
        verify(RelationUndoObserver.seedPriorUncertainty(Session.project), "The undo witness needs prior uncertainties that serialization omits");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
    }
    function test_each_relation_edit_data() {
        return ["alias-append", "alias-duplicate", "alias-remove", "alias-rename", "alias-retarget", "constraint-append", "constraint-duplicate", "constraint-remove", "constraint-rename", "expression", "enabled"].map(action => ({
                    tag: action,
                    action: action
                }));
    }
    function test_each_relation_edit(data) {
        const project = Session.project;
        const before = RelationUndoObserver.state(project);
        const aliases = project.analysis.aliases;
        const constraints = project.analysis.constraints;
        switch (data.action) {
        case "alias-append":
            aliases.append();
            break;
        case "alias-duplicate":
            aliases.duplicate(0);
            break;
        case "alias-remove":
            aliases.remove(0);
            break;
        case "alias-rename":
            verify(aliases.setText(0, "id", "renamed"), "The alias rename must be admitted");
            break;
        case "alias-retarget":
            verify(aliases.setText(0, "parameter", "phase.cell.length_a"), "The alias retarget must be admitted");
            break;
        case "constraint-append":
            constraints.append();
            break;
        case "constraint-duplicate":
            constraints.duplicate(1);
            break;
        case "constraint-remove":
            constraints.remove(1);
            break;
        case "constraint-rename":
            verify(constraints.setText(1, "id", "renamed"), "The constraint rename must be admitted");
            break;
        case "expression":
            verify(constraints.setText(1, "expression", "b = 3*a + 1"), "Expression replacement must be admitted");
            break;
        case "enabled":
            verify(constraints.setEnabled(1, false), "The enabled toggle must be admitted");
            break;
        }
        tryVerify(() => !project.calculating, 10000, "The edited project must settle before the Undo action");
        verify(RelationUndoObserver.state(project) !== before, "Every undo witness must first change real controller state");
        const undo = Ui.control(Probe, appWindow, "appBar.button.undo");
        verify(undo !== null && undo.enabled, "Every admitted relation edit must enable user Undo without a prior fit");
        Ui.click(test, Probe, appWindow, "appBar.button.undo");
        tryVerify(() => !project.calculating, 10000, "Undo must finish restoring implied values");
        compare(RelationUndoObserver.state(project), before, "Controller Undo must restore declaration text ids enabled state dependence free marks values and prior uncertainty");
    }

    function test_refused_restore_preserves_record_data() {
        return [
            {
                tag: "removed",
                route: "remove"
            },
            {
                tag: "renamed",
                route: "rename"
            }
        ];
    }
    function test_refused_restore_preserves_record(data) {
        const project = Session.project;
        const before = RelationUndoObserver.state(project);
        verify(project.analysis.constraints.setText(1, "expression", "b = 3*a + 1"), "The history witness must admit a value-changing relation edit");
        tryVerify(() => !project.calculating, 10000, "The relation edit must settle");
        verify(RelationUndoObserver.blockRestore(project, data.route, true), "The target must become unavailable to restoration");
        project.undo();
        const kept = project.canUndo;
        verify(RelationUndoObserver.blockRestore(project, data.route, false), "The same target must be available for retry");
        project.undo();
        tryVerify(() => !project.calculating, 10000, "A retried restoration must settle");
        verify(kept, "A refused restore must preserve its history record");
        compare(RelationUndoObserver.state(project), before, "Retry must restore the same record after its parameter becomes available");
    }
    function test_running_fit_cannot_consume_relation_history() {
        const project = Session.project;
        verify(RelationUndoObserver.prepareFit(project), "The witness must have an independent fit parameter");
        const before = RelationUndoObserver.state(project);
        verify(project.analysis.constraints.setText(0, "expression", "b = 3*a + 1"), "The interleaving witness must create a relation history record");
        tryVerify(() => !project.calculating, 10000, "The edit must settle before starting the fit");
        verify(RelationUndoObserver.refuseNextFit(project, true), "The worker refusal must leave existing history available");
        project.fit.start();
        verify(project.fit.running, "The undo attempt must happen while the real fit controller is running");
        project.undo();
        tryVerify(() => !project.fit.running, 10000, "The refused fit must finish delivery");
        verify(RelationUndoObserver.refuseNextFit(project, false), "The invalid declaration must be repaired before retrying Undo");
        verify(project.canUndo, "Running or refused fitting must preserve earlier relation history");
        project.undo();
        tryVerify(() => !project.calculating, 10000, "The preserved relation Undo must settle");
        compare(RelationUndoObserver.state(project), before, "Undo after a refused fit must restore the original relation state");
    }
    function test_refused_fit_keeps_previous_fit_record() {
        const project = Session.project;
        verify(RelationUndoObserver.prepareFit(project), "The fit history control needs an independent parameter");
        const before = RelationUndoObserver.state(project);
        project.fit.start();
        verify(project.fit.running, "The first fit must actually start");
        tryVerify(() => !project.fit.running, 10000, "The first fit must finish before the refusal witness");
        verify(project.fit.canUndo && project.canUndo, "A successful first fit must have a real undo record");
        verify(RelationUndoObserver.refuseNextFit(project, true), "The second worker must encounter an invalid declaration");
        project.fit.start();
        verify(project.fit.running && !project.fit.canUndo, "The witness must cross temporary fit Undo unavailability");
        tryVerify(() => !project.fit.running, 10000, "The refused second fit must finish");
        verify(RelationUndoObserver.refuseNextFit(project, false), "Undo must be retried with valid declarations");
        verify(project.canUndo, "A transient canUndo change must not delete the previous fit history");
        project.undo();
        tryVerify(() => !project.calculating, 10000, "The previous fit Undo must settle");
        compare(RelationUndoObserver.state(project), before, "Undo must restore the state preceding the first fit");
    }
}
