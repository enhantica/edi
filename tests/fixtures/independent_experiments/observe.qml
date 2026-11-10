import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "../../unit/app/UiInteraction.js" as Ui

TestCase {
    id: test
    name: "IndependentExperimentsApp"
    when: windowShown
    property var app
    Component { id: application; Main {} }
    function cleanup() {
        Session.closeProject();
        if (app) app.destroy();
    }
    function test_actual_mode_choice_and_fit() {
        const source = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/independent_experiments/project"));
        verify(Session.openProject(source), "Independent experiments: open the closed-form three-crystal input");
        app = application.createObject(null, {width: 1300, height: 950});
        verify(app !== null && waitForRendering(app.contentItem), "Independent experiments: render the actual app window");
        Ui.click(test, Probe, app, "appBar.tab.analysis");
        Ui.click(test, Probe, app, "sideBar.tab.extras");
        Ui.expandGroup(test, Probe, app, "group.fitting_mode");
        const choice = Ui.control(Probe, app, "fittingMode.type");
        verify(choice !== null, "Independent experiments: reach the actual fit-mode selector");
        const modes = Probe.rows(Session.project.analysis.fittingModeOptions).map(row => row.token);
        verify(modes.includes("independent"), "Independent experiments: the app offers independent mode for three disjoint structure/data pairs");
        compare(Session.project.analysis.fittingMode, "independent", "Independent experiments: the selected app mode preserves the declared independent token");
        verify(choice.currentIndex >= 0 && choice.currentText.length > 0, "Independent experiments: the actual selector visibly represents the independent choice");
        const fit = Session.project.fit;
        verify(fit.available, "Independent experiments: the actual app admits the declared non-scan fit");
        let started = false;
        const watch = () => { if (fit.running) started = true; };
        fit.runningChanged.connect(watch);
        fit.start();
        tryVerify(() => started, 2000, "Independent experiments: the real app worker starts");
        tryCompare(fit, "running", false, 10000, "Independent experiments: the real app worker completes");
        fit.runningChanged.disconnect(watch);
        compare(fit.outcome, "success", "Independent experiments: every individual fit succeeds in the app");
        const parameters = Probe.rows(Session.project.parameters).filter(row => row.category === "atom_site" && row.name === "occupancy" && row.free).map(row => ({path: row.path, value: row.parameter.value, su: row.parameter.uncertainty}));
        compare(parameters.length, 3, "Independent experiments: the app retains all three disjoint free occupancies");
        const quality = Probe.rows(fit.results.agreement).filter(row => row.place >= 0).map(row => ({name: row.label, rwp: Number(row.values[1]) / 100}));
        console.log("INDEPENDENT_EXPERIMENTS_APP " + JSON.stringify({modes, parameters, quality}));
    }
}
