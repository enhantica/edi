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
    function appProjects() {
        // Frozen file purposes and the owner's catalogue rule select the expected set.
        return Oracle.frozen.projects.filter(p => p.metadata["_metadata.purpose"] !== "verification");
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
        Session.examples.searchText = "";
        Session.examples.filterValue = "";
        Session.examples.filterProperty = "purpose";
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
        click("appBar.tab.project");
        click("sideBar.tab.basic");
        Ui.expandGroup(test, Probe, appWindow, "group.examples");
        tryVerify(() => visibleControl("examples.list") !== null, 2000,
                  "The unfiltered catalogue is exposed after group expansion");
        const list = visibleControl("examples.list");
        compare(list.count, appProjects().length + 1,
                "Every app example and the independent LiF example reach the catalogue");
        const index = Probe.rows(Session.examples).map(row => row.exampleId).indexOf(id);
        verify(index >= 0, "The requested example retains its own catalogue identity: " + id);
        list.positionViewAtIndex(index, ListView.Contain);
        list.forceLayout();
        tryVerify(() => list.itemAtIndex(index) !== null, 2000,
                  "Positioning materializes the row with the requested identity: " + id);
        const row = list.itemAtIndex(index);
        compare(row.exampleId, id, "The materialized catalogue row belongs to the requested example");
        Ui.scrollIntoView(row);
        tryVerify(() => visibleControl("examples.open." + id) !== null, 2000,
                  "The requested example's own row is visible for real input: " + id);
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
        const datasets = expected.datasets || [];
        if (datasets.length) {
            verify(project.scan, "Scan examples expose their dataset catalogue");
            same(Probe.rows(project.experiments).map(r => r.file), datasets.map(d => d.file),
                 "Every independently inventoried scan filename appears once in scan order");
            same(Probe.rows(project.experiments).map(r => r.name),
                 datasets.map(() => expected.experiments[0]),
                 "Every scan dataset retains its declared template experiment identity");
        } else {
            same(Probe.rows(project.experiments).map(r => r.name).sort(),
                 expected.experiments.slice().sort(), "I19: every experiment is loaded");
        }
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
        const selected = datasets.length
            ? [...new Set([0, Math.floor(datasets.length / 2), datasets.length - 1])]
            : experiments.map((_, index) => index);
        for (const i of selected) {
            project.currentExperimentIndex = i;
            tryCompare(project, "calculating", false, 5000,
                       "A selected dataset finishes its lazy read and projection");
            const experiment = project.currentExperiment;
            const frozen = Oracle.frozen.corpus.find(c => c.project === expected.path && c.experiment === experiment.name);
            verify(frozen !== undefined, "I19: selected experiment has an independent file oracle");
            compare(experiment.peakType, frozen.peakType, "I19: loaded profile is preserved");
            const range = datasets.length ? datasets[i].range : frozen.range;
            tryCompare(experiment.measuredRange, "points", range[3], 5000,
                       "The selected experiment publishes its independently measured point count");
            fuzzyCompare(experiment.measuredRange.minimum, range[0], 1e-10,
                         "The selected dataset displays the independent ASCII axis minimum");
            fuzzyCompare(experiment.measuredRange.maximum, range[1], 1e-10,
                         "The selected dataset displays the independent ASCII axis maximum");
            if (datasets.length) {
                const samples = datasets[i].samples;
                tryVerify(() => {
                    const rows = Probe.rows(experiment.pattern);
                    return samples.every(sample => {
                        const row = rows[sample.index];
                        return row !== undefined
                            && Math.abs(row.x - sample.values[0]) < 1e-9
                            && Math.abs(row.intensityMeas - sample.values[1]) < 1e-9
                            && Math.abs(row.intensityMeasSu - sample.values[2]) < 1e-9;
                    });
                }, 5000, "Selected datasets publish their own independent measured values and uncertainties");
            }
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
            const reportRange = datasets.length ? datasets[selected[selected.length - 1]].range : frozen.range;
            reportRange.forEach(value => verify(numbers.some(n => Math.abs(n - value) < 0.00005),
                                                 "owner final report record: measured range and point count come from committed experiment data"));
        });
        verify(text.includes("crysta"), "owner final report record: fit summary names the effective engine");
    }
    function test_examples_registry_is_complete() {
        same(Probe.rows(Session.examples).map(r => r.exampleId), appProjects().map(p => p.id).concat(["pd-xray-cwl_lif"]),
             "The catalogue contains exactly the app examples and independent LiF, excluding verification projects");
    }
    function test_every_example_opens_through_its_page_row_data() {
        return appProjects().map(p => ({tag: p.id, expected: p}));
    }
    function test_every_example_opens_through_its_page_row(data) {
        compare(Probe.libraryLoadWarning(Probe.repoUrl(data.expected.path)), data.expected.loaderWarning,
                "review-4 F1: frozen warning expectation is observed on the library's actual cerr channel");
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
    function test_verification_directories_keep_their_independent_project_population_data() {
        return Oracle.frozen.projects.filter(p => p.metadata["_metadata.purpose"] === "verification")
            .map(p => ({tag: p.id, expected: p}));
    }
    function test_verification_directories_keep_their_independent_project_population(data) {
        verify(!Probe.rows(Session.examples).some(row => row.exampleId === data.expected.id),
               "A verification project remains outside the app catalogue");
        Session.openProject(Probe.repoUrl(data.expected.path));
        verify(Session.hasProject, "The retained verification directory remains loadable");
        compare(Session.openedExample, "", "A directory load cannot claim an example row selection");
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
        const legacy = Probe.readReferenceFile("unlisted legacy project/project/experiments/dream.edi");
        verify(!legacy.includes("_experiment_type.") && !legacy.includes("_type."),
               "I19: legacy witness genuinely declares no type axes");
        const source = Probe.readReferenceFile("unlisted legacy project/project/project.edi");
        const title = source.match(/^_metadata\.title[ \t]+"([^"\n]+)"[ \t]*$/m);
        verify(title !== null, "The archived directory declares its independent quoted title");
        const legacyExpected = JSON.parse(JSON.stringify(expected));
        legacyExpected.metadata["_metadata.title"] = title[1];
        Session.openProject(Probe.referenceUrl("unlisted legacy project/project"));
        populated(legacyExpected);
        compare(Session.project.currentExperiment.beamModeToken, "time-of-flight",
                "I19: arbitrary project directories retain the loader-derived TOF type");
    }
}
