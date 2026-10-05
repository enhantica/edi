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
}
