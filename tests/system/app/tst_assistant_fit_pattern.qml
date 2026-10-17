// PRIVATE draft: production Session/FitViewModel and actual pattern components.
// No golden optimum, replacement optimizer, synthetic fit result or repaint call.
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0

TestCase {
    name: "AssistantFitPatternPublication"
    when: windowShown
    property var window
    property var finishedFacts: null
    property int completedCount: 0
    property var scene
    property string oldExperimentAxis
    Component {
        id: application
        ApplicationWindow { width: 1600; height: 900; visible: true }
    }
    Component {
        id: pattern
        PatternChart { width: 780; height: 850; shown: true }
    }
    Component {
        id: geometry
        StructureViewController { active: true; viewportWidth: 400; viewportHeight: 400 }
    }
    Connections {
        target: Session.project ? Session.project.fit : null
        function onFinished() {
            ++completedCount;
            const experiment = Session.project.currentExperiment;
            finishedFacts = {computed: Probe.computedCurrent(experiment), stale: experiment.pattern.stale,
                             error: experiment.pattern.calculationError};
        }
    }
    function initTestCase() {
        oldExperimentAxis = Preferences.experimentXAxis;
        window = application.createObject(null);
        verify(window !== null, "FIT-DISPLAY1: actual component window hosts real Session chart consumers");
    }
    function cleanup() { Session.closeProject(); }
    function cleanupTestCase() { Preferences.experimentXAxis = oldExperimentAxis; window.destroy(); }
    function controller(chart) {
        const matches = Probe.objectsWithProperty(chart, "hasResidual");
        compare(matches.length, 1, "FIT-DISPLAY1: actual chart has one public pattern controller");
        return matches[0];
    }
    function series(chart, kind) {
        const value = findChild(chart, "chart.series." + kind);
        verify(value !== null, "FIT-DISPLAY1: actual chart owns its applicable " + kind + " series");
        return value;
    }
    function allLayers(chart) {
        return ["calc", "bkg", "resid", "bragg.0"].every(kind => series(chart, kind).count > 0);
    }
    function observedInput(experiment) {
        return JSON.stringify({
            measured: Probe.rows(experiment.pattern).map(row => [row.x, row.intensityMeas, row.intensityMeasSu]),
            excluded: Probe.rows(experiment.excludedRegions),
            phases: Probe.rows(experiment.linkedStructures).map(row => [row.structureId, row.enabled]),
            weight: experiment.datasetWeight
        });
    }
    function test_real_adopted_fit_retains_current_chart_sources_data() {
        return [{tag: "aliased", aliased: true}, {tag: "alias-free", aliased: false}];
    }
    function test_real_adopted_fit_retains_current_chart_sources(data) {
        finishedFacts = null;
        completedCount = 0;
        verify(Session.openProject(Probe.repoUrl("docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project")), "FIT-DISPLAY1 SETUP: genuine committed complete CoSiO measured project opens read-only");
        const project = Session.project;
        const experiment = project.currentExperiment;
        verify(experiment !== null && project.currentStructure !== null, "FIT-DISPLAY1 SETUP: actual measured experiment and linked structure exist");
        const parameters = Probe.rows(project.parameters);
        const target = parameters.filter(row => row.blockName === "cosio" && row.category === "cell" && row.name === "length_a");
        compare(target.length, 1, "FIT-DISPLAY1 SETUP: independent CoSiO cell-length parameter is uniquely identified by public metadata");
        for (const row of parameters)
            row.parameter.free = false;
        target[0].parameter.free = true;
        experiment.scale.free = true;
        project.analysis.maxIterations = 8; // Finite exercise budget, no convergence oracle.
        compare(project.analysis.aliases.count, 0, "FIT-DISPLAY1 SETUP: original fixture is independently alias-free");
        if (data.aliased) {
            const aliases = project.analysis.aliases;
            const names = aliases.parameterNames.filter(name => name === "cosio.cell.length_a");
            compare(names.length, 1, "FIT-DISPLAY1 SETUP: public alias catalogue exposes the real changing cell parameter");
            aliases.append();
            compare(aliases.count, 1, "FIT-DISPLAY1 SETUP: genuine public relation edit admits one alias");
            verify(aliases.setText(0, "id", "changing_cell"), "FIT-DISPLAY1 SETUP: public alias edit names the original independent parameter");
            verify(aliases.setText(0, "parameter", names[0]), "FIT-DISPLAY1 SETUP: alias genuinely binds the free fitted scalar");
        }
        tryVerify(() => !project.calculating && Probe.computedCurrent(experiment), 10000, "FIT-DISPLAY1 SETUP: original calculation and real relation/free edits settle before fitting");
        const originalInputs = observedInput(experiment);
        const originalAliases = JSON.stringify(Probe.rows(project.analysis.aliases));
        const beforeValue = target[0].parameter.value;
        const experimentChart = createTemporaryObject(pattern, window.contentItem, {experiment: experiment, settingsPage: "experiment", x: 0});
        const analysisChart = createTemporaryObject(pattern, window.contentItem, {experiment: experiment, axisProject: project, settingsPage: "analysis", x: 800});
        scene = createTemporaryObject(geometry, window.contentItem, {structure: project.currentStructure});
        verify(experimentChart !== null && analysisChart !== null && scene !== null, "FIT-DISPLAY1 SETUP: real pattern/geometry consumers are constructed without a fake model");
        // Actual Experiment native axis and actual Analysis d-spacing setting.
        Preferences.experimentXAxis = "native";
        project.patternDSpacing = true;
        tryVerify(() => controller(experimentChart).current && controller(analysisChart).current && scene.current, 10000, "FIT-DISPLAY1 SETUP: both original pattern axes and structure geometry are current before the fit");
        tryVerify(() => allLayers(experimentChart) && allLayers(analysisChart), 10000, "FIT-DISPLAY1 SETUP: fixture has real calculated/background/residual/reflection layers before fitting");
        const beforeScene = scene.revision;
        project.fit.start();
        verify(project.fit.running, "FIT-DISPLAY1 SETUP: real worker fitting is admitted and remains cancellable");
        tryCompare(project.fit, "running", false, 10000, "FIT-DISPLAY1: bounded genuine optimizer returns through owner delivery");
        compare(completedCount, 1, "FIT-DISPLAY1: one real retained fit completion reaches the normal Session controller");
        verify(project.fit.canUndo && ["success", "maxIterations"].includes(project.fit.outcome), "FIT-DISPLAY1 SETUP: real fit is adopted, not an unavailable/error/cancel/no-step substitute");
        verify(target[0].parameter.value !== beforeValue, "FIT-DISPLAY1 SETUP: the actually aliased scalar genuinely changes in the adopted fit");
        verify(finishedFacts !== null && finishedFacts.computed && !finishedFacts.stale && finishedFacts.error === "", "FIT-DISPLAY1: current computation is already published at normal retained completion without manual edits");
        compare(observedInput(experiment), originalInputs, "FIT-DISPLAY1: fitting preserves original measured values, uncertainties, exclusions, phase links and weights");
        compare(JSON.stringify(Probe.rows(project.analysis.aliases)), originalAliases, "FIT-DISPLAY1: the actual alias declaration is not removed to hide a publication defect");
        tryVerify(() => controller(experimentChart).current && controller(analysisChart).current && scene.current && scene.revision > beforeScene, 10000, "FIT-DISPLAY1: post-fit chart and geometry publications describe the adopted model");
        tryVerify(() => allLayers(experimentChart) && allLayers(analysisChart), 10000, "FIT-DISPLAY1: both actual axes retain applicable calculated/background/residual/reflection layers after real fit");
        // Equal public writes still invalidate old computation synchronously.
        // This is a separate postcondition, never the action repairing the fit.
        const adopted = target[0].parameter.value;
        target[0].parameter.value = adopted;
        verify(!Probe.computedCurrent(experiment), "FIT-DISPLAY1: currentness remains strict after a later ordinary model write");
    }
}
