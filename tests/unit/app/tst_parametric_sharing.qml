import QtQuick
import QtQuick.Controls
import QtTest
import EasyApplication.Gui.Style as Style
import "NativeTurn.js" as Turn
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0

TestCase {
    id: test
    property string gateTurnSelector: ""
    name: "ParametricSharing"
    when: windowShown
    property var window
    property var table
    property bool showConstraints
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
        gateTurnSelector = Turn.begin(test, Probe);
        showConstraints = Preferences.analysisShowByConstraint;
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
        Preferences.analysisShowByConstraint = showConstraints;
        Session.closeProject();
        if (window)
            window.destroy();
        window = null;
        Probe.releaseScratchProjects();
        Turn.end(gateTurnSelector);
    }
    function members() {
        const rows = Probe.rows(Session.project.parameters);
        const result = ["zeta", "alpha", "third"].map(bank => rows.find(row => row.parameter.blockName === bank && row.parameter.uid === "peak.broad_gauss_w"));
        verify(result.every(row => row !== undefined), "All three independent experiments expose the same eligible profile parameter");
        return result.map(row => row.parameter);
    }
    function rowIndex(bank, uid, label = "") {
        const list = findChild(table, "parameters.list");
        list.sourceModel.nameFilter = uid.split(".").pop();
        const index = Probe.rows(list.sourceModel).findIndex(row =>
            row.parameter.blockName === bank && row.parameter.uid === uid &&
            (label === "" || row.parameter.rowLabel === label));
        verify(index >= 0, "The Analysis table contains the authored parameter " + bank + "." + uid);
        list.positionViewAtIndex(index, ListView.Contain);
        verify(waitForPolish(list), "The target Analysis row is laid out before interaction");
        return index;
    }
    function shownGroup() {
        const visibleRows = findChild(table, "parameters.list").sourceModel;
        return Probe.rows(visibleRows).filter(row => row.parameter.uid === "peak.broad_gauss_w")
            .map(row => row.parameter.blockName).sort();
    }
    function test_group_edits_and_undo() {
        let parameters = members();
        parameters.forEach((parameter, index) => {
            parameter.free = false;
            parameter.value = 0.3 + index;
        });
        compare(shownGroup(), ["alpha", "third", "zeta"], "The Analysis table initially includes all distinct copies");
        const uid = "peak.broad_gauss_w";
        const alpha = rowIndex("alpha", uid);
        const sharedBox = findChild(table, "parameters.shared." + alpha);
        verify(sharedBox && sharedBox.enabled, "The selected member has a usable Shared checkbox");
        mouseClick(sharedBox, sharedBox.width / 2, sharedBox.height / 2);
        tryVerify(() => JSON.stringify(shownGroup()) === JSON.stringify(["alpha"]), 2000,
            "Only the clicked member remains on the Analysis page");
        const survivor = rowIndex("alpha", uid);
        const sharedValue = findChild(table, "parameters.value." + survivor);
        verify(sharedValue !== null, "The surviving member has a rendered value cell");
        tryVerify(() => String(sharedValue.color) === String(AppColors.shared), 1000,
            "The retained row uses the Shared value colour");
        parameters.forEach(parameter => {
            compare(parameter.shared, true, "Shared includes the unassigned third experiment");
            compare(parameter.free, false, "Checking Shared preserves a fixed group");
            compare(parameter.value, 1.3, "The clicked member supplies the common value");
        });
        Session.project.undo();
        tryVerify(() => shownGroup().length === 3, 2000, "Undo restores the three separate Analysis rows");
        parameters = members();
        parameters.forEach((parameter, index) => {
            compare(parameter.shared, false, "One undo restores every member sharing flag");
            compare(parameter.value, 0.3 + index, "One undo restores the distinct member values");
        });
        parameters[2].shared = true;
        parameters[1].free = true;
        parameters.forEach(parameter => compare(parameter.free, true, "The Free edit updates the whole shared group"));
        Session.project.undo();
        parameters = members();
        parameters.forEach(parameter => {
            compare(parameter.free, false, "One undo restores the whole group Free flag");
            compare(parameter.shared, true, "Undoing Free retains Shared");
        });
    }
    function test_click_shared_uses_any_free_and_the_clicked_value() {
        const parameters = members();
        parameters.forEach((parameter, index) => {
            parameter.free = index === 0;
            parameter.value = 0.3 + index;
        });
        const row = rowIndex("alpha", "peak.broad_gauss_w");
        const box = findChild(table, "parameters.shared." + row);
        verify(box && box.enabled, "The fixed middle copy has an actionable Shared checkbox");
        mouseClick(box, box.width / 2, box.height / 2);
        tryVerify(() => parameters.every(parameter => parameter.shared), 2000,
            "Pointer input shares all three eligible copies");
        parameters.forEach(parameter => {
            compare(parameter.free, true, "A free copy makes the newly shared group free");
            compare(parameter.value, 1.3, "The clicked fixed copy still supplies the common value");
        });
        compare(shownGroup(), ["alpha"], "The clicked row remains as the visible group owner");
        Session.project.undo();
        const restored = members();
        compare(restored.map(parameter => parameter.free), [true, false, false],
            "Undo restores each copy's original Free state");
        compare(restored.map(parameter => parameter.value), [0.3, 1.3, 2.3],
            "Undo restores each original value");
    }
    function test_bulk_shared_is_one_undo() {
        const parameters = members();
        verify(Session.project.setParametersShared([parameters[1], parameters[2]], true), "The bulk operation accepts eligible visible members");
        parameters.forEach(parameter => compare(parameter.shared, true, "Bulk sharing includes every member of the selected group"));
        Session.project.undo();
        members().forEach(parameter => compare(parameter.shared, false, "Bulk sharing is one undo step even with duplicate group members"));
    }
    function test_unshareable_rows_explain_why() {
        const root = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/parametric_series/project"));
        const analysis = SettingsProof.text(root, "analysis/analysis.edi");
        verify(SettingsProof.write(root, "analysis/analysis.edi", analysis +
            '\nloop_\n_alias.id\n_alias.parameter_unique_name\n' +
            'dependent zeta.peak.broad_gauss_w\nsource alpha.peak.broad_gauss_w\n' +
            'loop_\n_constraint.id\n_constraint.expression\nwidth_tie "dependent = source * 2"\n'),
            "The private project declares a named constraint on the first member");
        const experiment = SettingsProof.text(root, "experiments/2_third.edi");
        const missing = experiment.replace(/^1 12 2$/m, "9 12 2");
        verify(missing !== experiment && SettingsProof.write(root, "experiments/2_third.edi", missing),
            "The third experiment has no background coefficient with the paired id");
        table.project = null;
        verify(Session.openProject(root), "The app opens the private constraint and incomplete-group witness");
        table.project = Session.project;

        Preferences.analysisShowByConstraint = false;
        verify(!shownGroup().includes("zeta"), "Analysis initially hides the user-dependent copy");
        Preferences.analysisShowByConstraint = true;
        const dependent = rowIndex("zeta", "peak.broad_gauss_w");
        const value = findChild(table, "parameters.value." + dependent);
        verify(value !== null, "The shown dependent row has a real value cell");
        tryVerify(() => value.color.r > value.color.g && value.color.b > value.color.g,
            1000, "A displayed constrained value uses magenta");
        for (const bank of ["zeta", "alpha", "third"]) {
            const index = rowIndex(bank, "peak.broad_gauss_w");
            const box = findChild(table, "parameters.shared." + index);
            verify(box && !box.enabled, "A dependent copy disables Shared for the whole group");
            verify(box.ToolTip.text.includes("width_tie"), "The disabled checkbox names the actual user constraint");
        }
        const orphan = rowIndex("zeta", "background.intensity", "1");
        const box = findChild(table, "parameters.shared." + orphan);
        verify(box && !box.enabled, "An incomplete group has a disabled Shared checkbox");
        verify(/not in every experiment/i.test(box.ToolTip.text), "The incomplete group tooltip explains its missing counterpart");
    }
    function test_column_follows_fitting_mode() {
        compare(table.sharedShown, true, "Joint mode shows the Shared column");
        const shared = findChild(table, "parameters.sharedHeader");
        const free = findChild(table, "parameters.freeHeader");
        verify(shared && free && shared.visible && free.visible, "The real table lays out both visible headers");
        verify(shared.mapToItem(table, shared.width, 0).x <= free.mapToItem(table, 0, 0).x,
            "Shared is to the left of Free");
        const freeBox = findChild(table, "parameters.free.0");
        const sharedBox = findChild(table, "parameters.shared.0");
        verify(freeBox && sharedBox, "A materialized parameter row exposes both checkboxes");
        compare(String(freeBox.color), String(Style.Colors.green), "The Free checkbox uses the free-value green");
        compare(String(sharedBox.color), String(AppColors.shared), "The Shared checkbox uses its own colour");
        verify(String(sharedBox.color) !== String(freeBox.color), "Shared and Free are visually distinct");
        Session.project.analysis.fittingMode = "independent";
        compare(table.sharedShown, false, "Independent mode hides the Shared column");
        Session.project.analysis.fittingMode = "joint";
        compare(table.sharedShown, true, "Returning to Joint restores the Shared column");
    }
}
