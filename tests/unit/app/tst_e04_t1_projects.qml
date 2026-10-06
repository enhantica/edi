import QtQuick
import "UiInteraction.js" as Ui
import QtTest
import edi.app
import EdiAcceptance 1.0
import "../../fixtures/e04_t1/oracle.js" as Oracle

TestCase {
    id: test
    name: "E04T1ExistingProjects"
    when: windowShown
    property var appWindow
    Component { id: application; Main {} }

    function initTestCase() {
        failOnWarning(/.*/);
        appWindow = application.createObject(null);
        verify(appWindow !== null, "I19: existing-project tests load production Main");
        verify(waitForRendering(appWindow.contentItem), "I19: the real window is ready for input");
    }
    function init() {
        // Qt Graphs probes a temporary GLES2 context once per process, even
        // with the software backend. Only this first Graphs user may lack GL.
        const firstGraphsUse = qtest_results.functionName
            === "test_arbitrary_directory_keeps_legacy_type_inference";
        failOnWarning(firstGraphsUse
            ? /\A(?!QRhiGles2: Failed to create (?:temporary context|context)\z)[\s\S]*\z/
            : /.*/);
        Session.closeProject();
        click("appBar.tab.home");
        click("home.start");
    }
    function cleanupTestCase() {
        Probe.clearWatches();
        Session.closeProject();
        verify(waitForRendering(appWindow.contentItem),
               "I10: pending page loads settle before the test window is destroyed");
        appWindow.destroy();
    }
    function visibleControl(name) { return Ui.control(Probe, appWindow, name); }
    function click(name) { Ui.click(test, Probe, appWindow, name); }
    function openExample(id) {
        click("examples.open." + id);
        // Rendering a frame does not prove that a deferred row press opened its
        // project. Observe the result, including identity, before reading it.
        tryVerify(() => (Session.hasProject && Session.openedExample === id)
                  || Session.lastError !== "", 2000,
                  "I19: the selected Example completes its open: " + id);
        verify(Session.hasProject && Session.openedExample === id,
               "I19: the selected Example opens without refusal: " + id + " " + Session.lastError);
    }

    function showMessages() {
        click("statusBar.warnings");
        const dialog = findChild(appWindow, "warnings");
        verify(dialog !== null, " idea 24: status click reaches the central Messages dialog");
        tryCompare(dialog, "opened", true, 2000, " idea 24: central dialog opens through real input");
        compare(Session.loadWarnings.unviewedCount, 0, " idea 24: showing the list marks messages viewed");
        return dialog;
    }

    function same(actual, expected, message) {
        compare(JSON.stringify(actual), JSON.stringify(expected), message);
    }
    function textVisible(fragment, message) {
        tryVerify(() => Ui.text(Ui.windowRoot(appWindow)).includes(fragment), 2000, message);
    }
    function populated(expected) {
        verify(Session.hasProject, "I19: selected project opens: " + expected.id + " " + Session.lastError);
        const project = Session.project;
        compare(project.name, expected.metadata["_metadata.name"], "I19: opened metadata belongs to the selected project");
        compare(project.title, expected.metadata["_metadata.title"] ?? "Untitled Project",
                "I19: title follows declared metadata or the UI default regression pin");
        same(Probe.rows(project.structures).map(r => r.name).sort(),
             expected.structures.map(r => r.name).sort(), "I19: every structure is loaded");
        same(Probe.rows(project.experiments).map(r => r.name).sort(),
             expected.experiments.slice().sort(), "I19: every experiment is loaded");
        click("appBar.tab.project");
        click("sideBar.tab.text");
        textVisible(expected.metadata["_metadata.name"], "I19: Project Text renders loaded metadata");
        click("appBar.tab.structure");
        const structures = Probe.rows(project.structures);
        for (let i = 0; i < structures.length; ++i) {
            project.currentStructureIndex = i;
            const structure = project.currentStructure;
            const frozen = expected.structures.find(s => s.name === structure.name);
            verify(frozen !== undefined, "I19: selected structure has an independent file oracle");
            compare(Probe.rows(structure.atomSites).length, frozen.atoms, "I19: Structure includes every committed atom");
            compare(structure.cell.lengthA.value, frozen.cellA, "I19: Structure contains the loaded cell");
            click("sideBar.tab.text");
            textVisible("_cell.length_a", "I19: Structure Text is populated by the loaded block");
        }
        const experiments = Probe.rows(project.experiments);
        for (let i = 0; i < experiments.length; ++i) {
            project.currentExperimentIndex = i;
            const experiment = project.currentExperiment;
            const frozen = Oracle.frozen.corpus.find(c => c.project === expected.path && c.experiment === experiment.name);
            verify(frozen !== undefined, "I19: selected experiment has an independent file oracle");
            compare(experiment.peakType, frozen.peakType, "I19: loaded profile is preserved");
            verify(experiment.measuredRange.points > 0, "I19: Experiment publishes the loaded measured data");
            click("appBar.tab.experiment");
            click("sideBar.tab.text");
            textVisible("_peak.type", "I19: Experiment Text is populated by the loaded block");
            click("sideBar.tab.basic");
            click("sideBar.tab.extras");
            click("appBar.tab.analysis");
            click("sideBar.tab.basic");
            verify(Probe.rows(project.parameters).length > 0, "I19: Analysis has loaded parameter rows");
            click("sideBar.tab.extras");
            click("sideBar.tab.text");
        }
        click("appBar.tab.report");
        tryVerify(() => visibleControl("report.text") !== null, 2000,
                  "owner final report record: the report finishes loading in the selected page");
        const report = visibleControl("report.text");
        verify(report !== null && Probe.nativeText(report),
               "owner final report record: report renders in a standard QML Text or TextArea");
        compare(report.textFormat, Text.RichText, "owner final report record: report uses Qt's rich-text subset");
        verify(!/<(?:script|img|iframe|canvas|svg|object|embed)\b|\bon\w+\s*=|javascript:/i.test(report.text),
               "owner final report record: simple report contains no JavaScript, web frame or plot");
        const text = Probe.plainText(report.text);
        ["Crystal data", "Data collection", "Fit"].forEach(heading =>
            verify(text.toLowerCase().includes(heading.toLowerCase()), "owner final report record: every report section is populated"));
        const numbers = (text.match(/[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?/g) || []).map(Number);
        expected.structures.forEach(s => {
            verify(text.includes(s.name) && text.includes(s.spaceGroup), "owner final report record: crystal identity comes from committed structure files");
            s.cell.forEach(value => verify(numbers.some(n => Math.abs(n - value) < 0.00005),
                                          "owner final report record: reported cell lengths and angles agree with committed structure input"));
        });
        expected.experiments.forEach(name => {
            verify(text.includes(name), "owner final report record: data collection names every loaded experiment");
            const frozen = Oracle.frozen.corpus.find(c => c.project === expected.path && c.experiment === name);
            frozen.range.forEach(value => verify(numbers.some(n => Math.abs(n - value) < 0.00005),
                                                 "owner final report record: measured range and point count come from committed experiment data"));
        });
        verify(text.includes("crysta"), "owner final report record: fit summary names the effective engine");
    }
    function test_examples_registry_is_complete() {
        same(Probe.rows(Session.examples).map(r => r.exampleId), Oracle.frozen.projects.map(p => p.id).concat(["pd-xray-cwl_lif"]),
             "I19/owner X-ray record: Examples follows the whole registry plus the independent LiF example");
    }
    function test_every_example_opens_through_its_page_row_data() {
        return Oracle.frozen.projects.map((p, index) => ({tag: p.id, expected: p, index: index}));
    }
    function test_every_example_opens_through_its_page_row(data) {
        compare(Probe.libraryLoadWarning(Probe.repoUrl(data.expected.path)), data.expected.loaderWarning,
                "review-4 F1: frozen warning expectation is observed on the library's actual cerr channel");
        click("appBar.tab.project");
        click("sideBar.tab.basic");
        Ui.expandGroup(test, Probe, appWindow, "group.examples");
        tryVerify(() => visibleControl("examples.list") !== null, 2000,
                  "I19: the Examples table is exposed after expansion");
        const list = visibleControl("examples.list");
        verify(list !== null, "I19: Project Examples exposes the base TableView");
        compare(list.count, Oracle.frozen.projects.length + 1, "I19/owner X-ray record: every registry entry and LiF reach the visible list");
        list.positionViewAtIndex(data.index, ListView.Center);
        tryVerify(() => list.itemAtIndex(data.index) !== null, 2000,
                  "I19: positioning instantiates the requested Example row");
        Ui.scrollIntoView(list.itemAtIndex(data.index));
        tryVerify(() => visibleControl("examples.open." + data.expected.id) !== null,
                  2000, "I19: scrolling materializes each selectable example row");
        openExample(data.expected.id);
        // The CLI adds its "Warning: " envelope; the typed sink carries the
        // diagnostic body specified by plan 15.1. Keep both channel checks exact.
        const diagnostics = data.expected.loaderWarning ? data.expected.loaderWarning.split("\n").map(line => line.replace(/^Warning: /, "")) : [];
        same(Probe.rows(Session.loadWarnings).map(row => row.message), diagnostics, "I10/I19: the app warning list equals the file-derived diagnostic bodies");
        if (data.expected.loaderWarning) {
            const dialog = showMessages();
            diagnostics.forEach((diagnostic, index) => {
                tryVerify(() => { const message = visibleControl("warnings.message." + index);
                    return message !== null && message.text === diagnostic; }, 2000, " ideas 24/26: each file-derived loader warning is shown in the central list");
            });
            compare(Session.project.analysis.minimizerType, "crysta", "review-4 F1: the GUI displays the effective supported minimizer");
            click("warnings.dismissAll");
            compare(Session.loadWarnings.count, 0, " idea 24: real Dismiss all input clears the central list");
            dialog.close();
            tryCompare(dialog, "opened", false, 2000, " idea 24: central dialog finishes closing before workflow input");
        }
        populated(data.expected);
    }
    function test_directory_warning_is_forwarded_without_special_casing_data() {
        return [
            {tag: "committed-scan", url: Probe.repoUrl("docs/user/cli/pd-neut-cwl_cosio-d20_scan-3f/project"), token: "crysta (lm)"},
            {tag: "different-legacy-token", url: Probe.repoUrl("tests/fixtures/e04_t1/warning-project"), token: "legacy-e04-warning-witness"}
        ];
    }
    function test_directory_warning_is_forwarded_without_special_casing(data) {
        const expected = 'unsupported _minimizer.type "' + data.token + '" - using crysta';
        compare(Probe.libraryLoadWarning(data.url), "Warning: " + expected,
                "review-4 F1: independent core load observes the specific legacy warning on cerr");
        Session.openProject(data.url);
        verify(Session.hasProject, "review-4 F1: warning does not become a project-open refusal");
        const dialog = showMessages();
        tryVerify(() => { const message = visibleControl("warnings.message.0");
            return message !== null && message.text === expected; }, 2000, " idea 24: directory loading displays the current diagnostic in the central list");
        compare(Session.project.analysis.minimizerType, "crysta",
                "review-4 F1: legacy minimizer maps to the sole supported GUI choice");
        verify(Session.project.analysis.text.text.includes(data.token),
               "review-4 F1: displaying the effective minimizer preserves the legacy persisted token");
        dialog.close();
    }
    function test_bundled_xray_example_opens_by_real_input() {
        click("appBar.tab.project");
        click("sideBar.tab.basic");
        Ui.expandGroup(test, Probe, appWindow, "group.examples");
        tryVerify(() => visibleControl("examples.list") !== null, 2000,
                  "owner X-ray record: the Examples table is exposed after expansion");
        const list = visibleControl("examples.list");
        verify(list !== null, "owner X-ray record: the bundled X-ray example is user-reachable");
        list.positionViewAtIndex(Oracle.frozen.projects.length, ListView.Center);
        tryVerify(() => list.itemAtIndex(Oracle.frozen.projects.length) !== null, 2000,
                  "owner X-ray record: positioning instantiates the final Example row");
        Ui.scrollIntoView(list.itemAtIndex(Oracle.frozen.projects.length));
        openExample("pd-xray-cwl_lif");
        verify(Session.hasProject, "owner X-ray record: selecting the bundled LiF example opens it");
        const s = Session.project.currentStructure, e = Session.project.currentExperiment;
        compare(s.spaceGroup.nameHM, "F m -3 m", "owner X-ray record: bundled structure is the committed LiF reference");
        fuzzyCompare(s.cell.lengthA.value, 4.0267, 1e-8, "owner X-ray record: LiF cell comes from ");
        compare(e.radiationProbeToken, "xray", "owner X-ray record: bundled example reaches the X-ray page path");
        click("appBar.tab.experiment");
        click("sideBar.tab.extras");
        Ui.expandGroup(test, Probe, appWindow, "group.scattering_source");
        ["xray_form_factor", "xray_dispersion"].forEach(name => {
            tryVerify(() => visibleControl("scatteringSource." + name) !== null, 2000,
                      "owner X-ray record: each bundled selector is exposed after expansion");
            const combo = visibleControl("scatteringSource." + name);
            verify(combo !== null && combo.enabled, "owner X-ray record: the bundled calculation-only project exposes both selectors");
            same(Probe.rows(combo.model).map(r => r.token),
                 name === "xray_form_factor" ? ["wk1995", "it1992"] : ["cromer-liberman", "sasaki1989", "it1992", "none"],
                 "owner X-ray record: bundled selector choices equal the library's independently declared sets");
        });
    }
    function test_arbitrary_directory_keeps_legacy_type_inference() {
        const expected = Oracle.frozen.projects.find(p => p.id === "pd-neut-tof_diamond-dream_basic");
        verify(!Probe.readFile(expected.path + "/experiments/dream.edi").includes("_experiment_type."),
               "I19: legacy witness genuinely declares no type axes");
        Session.openProject(Probe.referenceUrl("unlisted legacy project/project"));
        populated(expected);
        compare(Session.project.currentExperiment.beamModeToken, "time-of-flight",
                "I19: arbitrary project directories retain the loader-derived TOF type");
    }
}
