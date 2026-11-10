import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "../../unit/app/UiInteraction.js" as Ui

Item {
    id: surface
    width: 1300
    height: 950
    Component { id: parameters; ParametersGroup { width: 1200; tableViewportHeight: 800 } }
    TestCase {
        name: "ParameterNotationObserver"
        when: windowShown
        function observe(value, su, rule) {
            const path = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
            const source = SettingsProof.text(path, "experiments/bank.edi");
            verify(/^pA 10\.011 4\(\)$/m.test(source), "Parameter notation: the authored real background row is present before changing its input pair");
            const number = value.toFixed(20), uncertainty = su.toFixed(20);
            compare(Number(number), value, "Parameter notation: the accepted decimal token preserves the exact authored value");
            compare(Number(uncertainty), su, "Parameter notation: the accepted decimal token preserves the exact authored s.u.");
            verify(SettingsProof.write(path, "experiments/bank.edi", source.replace(/^pA 10\.011 4\(\)$/m, "pA 10.011 " + number + "(" + uncertainty + ")")), "Parameter notation: write only the declared background value and s.u.");
            const metadata = SettingsProof.text(path, "project.edi");
            verify(!metadata.includes("_su_format.rule"), "Parameter notation: the real source has no hidden uncertainty-rule override");
            verify(SettingsProof.write(path, "project.edi", metadata + "\n_su_format.rule " + rule + "\n"), "Parameter notation: explicitly select the actual project's saved-value rule");
            verify(Session.openProject(path), "Parameter notation: the app loads the authored input without an intermediate save: " + JSON.stringify({value, su, rule}) + " / " + Session.lastError);
            compare(Session.project.suRule, rule, "Parameter notation: the loaded app project owns the requested s.u. rule");
            const group = parameters.createObject(surface, {project: Session.project});
            verify(group !== null, "Parameter notation: instantiate the production Analysis ParametersGroup");
            const table = Ui.find(group, "parameters.list", true);
            verify(table !== null, "Parameter notation: reach the actual Analysis parameter table");
            table.sourceModel.categoryFilter = "background";
            table.sourceModel.variability = ParameterFilterModel.All;
            for (let reason = 1; reason <= 4; ++reason)
                table.sourceModel.setShownGroup(reason, true);
            const rows = Probe.rows(table.sourceModel);
            const index = rows.findIndex(row => row.rowLabel === "pA" && row.name === "intensity");
            verify(index >= 0, "Parameter notation: find the authored pA intensity by its independent row and parameter identity");
            table.positionViewAtIndex(index, ListView.Contain);
            tryVerify(() => table.itemAtIndex(index) !== null, 1000, "Parameter notation: the real value row is instantiated");
            const row = table.itemAtIndex(index);
            const cell = Ui.find(row, "parameters.value." + index, true);
            const error = Ui.find(row, "parameters.su." + index, true);
            verify(cell && error && waitForPolish(group), "Parameter notation: the actual value and s.u. cells finish layout");
            verify(!cell.activeFocus, "Parameter notation: observe display text before the user enters its full-precision editor");
            const result = {value, su, rule, shown: cell.text, error: error.text, editor: cell.editText};
            group.destroy();
            Session.closeProject();
            return result;
        }
        function test_observe_real_value_and_su_pairs() {
            const values = [0.000999, 0.001, 999.9, 1000, -0.000999, -0.001, -999.9, -1000];
            const plain = [0, ...values, 0.000000000186515, 7453675696].map(value => observe(value, 0, "iucr_19").shown);
            const pairs = [];
            for (const rule of ["iucr_19", "iucr_99"])
                for (const value of values)
                    pairs.push(observe(value, Math.abs(value) < 1 ? 0.00000201 : 0.00201, rule));
            console.log("PARAMETER_NOTATION_PAIRS " + JSON.stringify({plain, pairs}));
        }
    }
}
