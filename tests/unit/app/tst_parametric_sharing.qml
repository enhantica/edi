import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0

TestCase {
    id: test
    name: "ParametricSharing"
    when: windowShown
    property var window
    property var table
    Component {
        id: host
        ApplicationWindow {
            width: 1000
            height: 800
            visible: true
        }
    }
    Component {
        id: group
        ParametersGroup {
            width: 900
            tableViewportHeight: 600
        }
    }
    function init() {
        window = host.createObject(null);
        verify(window !== null, "The sharing controls need their real Qt window");
        const source = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/parametric_series/project"));
        verify(Session.openProject(source), "The sharing actor loads its handwritten joint project");
        table = group.createObject(window.contentItem, {
            project: Session.project
        });
        verify(table !== null, "The actor instantiates the production Parameters table");
    }
    function cleanup() {
        if (table)
            table.destroy();
        table = null;
        Session.closeProject();
        if (window)
            window.destroy();
        window = null;
        Probe.releaseScratchProjects();
    }
    function members() {
        const rows = Probe.rows(Session.project.parameters);
        const result = ["zeta", "alpha", "third"].map(bank => rows.find(row => row.parameter.blockName === bank && row.parameter.uid === "peak.broad_gauss_w"));
        verify(result.every(row => row !== undefined), "All three independent experiments expose the same eligible profile parameter");
        return result.map(row => row.parameter);
    }
    function test_group_edits_and_undo() {
        const parameters = members();
        parameters.forEach((parameter, index) => {
            parameter.free = false;
            parameter.value = 0.3 + index;
        });
        parameters[1].shared = true;
        parameters.forEach(parameter => {
            compare(parameter.shared, true, "Shared includes the unassigned third experiment");
            compare(parameter.free, false, "Checking Shared preserves a fixed group");
            compare(parameter.value, 1.3, "The clicked member supplies the common value");
        });
        Session.project.undo();
        parameters.forEach((parameter, index) => {
            compare(parameter.shared, false, "One undo restores every member sharing flag");
            compare(parameter.value, 0.3 + index, "One undo restores the distinct member values");
        });
        parameters[2].shared = true;
        parameters[1].free = true;
        parameters.forEach(parameter => compare(parameter.free, true, "The Free edit updates the whole shared group"));
        Session.project.undo();
        parameters.forEach(parameter => {
            compare(parameter.free, false, "One undo restores the whole group Free flag");
            compare(parameter.shared, true, "Undoing Free retains Shared");
        });
    }
    function test_bulk_shared_is_one_undo() {
        const parameters = members();
        verify(Session.project.setParametersShared([parameters[1], parameters[2]], true), "The bulk operation accepts eligible visible members");
        parameters.forEach(parameter => compare(parameter.shared, true, "Bulk sharing includes every member of the selected group"));
        Session.project.undo();
        parameters.forEach(parameter => compare(parameter.shared, false, "Bulk sharing is one undo step even with duplicate group members"));
    }
    function test_column_follows_fitting_mode() {
        compare(table.sharedShown, true, "Joint mode shows the Shared column");
        Session.project.analysis.fittingMode = "independent";
        compare(table.sharedShown, false, "Independent mode hides the Shared column");
        Session.project.analysis.fittingMode = "joint";
        compare(table.sharedShown, true, "Returning to Joint restores the Shared column");
    }
}
