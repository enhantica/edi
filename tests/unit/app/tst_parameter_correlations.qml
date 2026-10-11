import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "ParameterCorrelations"
    when: windowShown
    property var appWindow
    property int savedTheme
    Component {
        id: application
        Main {}
    }

    function initTestCase() {
        savedTheme = Style.Colors.theme;
        Style.Colors.theme = Style.Colors.LightTheme;
        appWindow = application.createObject(null);
        verify(appWindow !== null, "The production window must load for correlation and editing checks");
        verify(waitForRendering(appWindow.contentItem), "The production window must render before input");
    }
    function init() {
        Session.closeProject();
        AppState.reached = AppState.Page.Home;
    }
    function cleanupTestCase() {
        Session.closeProject();
        appWindow.destroy();
        Style.Colors.theme = savedTheme;
    }
    function click(name) {
        Ui.click(test, Probe, appWindow, name);
    }
    function control(name) {
        return Ui.control(Probe, appWindow, name);
    }
    function open(path) {
        verify(Session.openProject(Probe.repoUrl(path)), "The independently authored project must open");
    }
    function findBy(root, property, value) {
        if (root && (property === "model" ? JSON.stringify(root[property]) === JSON.stringify(value) : root[property] === value))
            return root;
        for (const child of root && root.children ? root.children : []) {
            const found = findBy(child, property, value);
            if (found)
                return found;
        }
        return null;
    }

    function test_creation_uses_a_normalized_chosen_directory() {
        AppState.reached = AppState.Page.Project;
        click("appBar.tab.project");
        click("project.create");
        const dialogs = Probe.visibleDialogs(appWindow).filter(item => typeof item.projectName === "string");
        compare(dialogs.length, 1, "Create project must expose exactly one project description dialog");
        const dialog = dialogs[0];
        verify(dialog !== null, "Create project must show its production dialog");
        dialog.projectParentDirectory = Probe.repoUrl("build/test-tmp/correlation-create/");
        dialog.projectName = "created";
        const location = findBy(dialog.contentItem, "placeholderText", "Enter project location here");
        verify(location !== null, "Create project must expose its location field");
        verify(!location.text.includes("//"), "The chosen native directory must not acquire doubled separators");
        dialog.projectName = "renamed";
        verify(!location.text.includes("//"), "Changing the project name must retain normalized separators");
        const chosen = location.text;
        dialog.accept();
        tryVerify(() => Session.hasProject, 2000, "Accepting the create dialog must create the project");
        compare(Session.projectLocation, chosen, "The created project must be saved in the chosen location");
        verify(Session.projectDirectoryExists(chosen), "The chosen location must contain the saved project directory");
    }

    function test_save_as_is_needed_once_then_save_stays_in_place() {
        verify(Session.createProject("unsaved", "Save lifecycle witness"), "A new unsaved project must be created");
        verify(Session.needsSaveAs, "The first save of an unsaved project must ask for its directory");
        verify(Session.saveAs(Probe.repoUrl("build/test-tmp/correlation-save")), "Save As must save at the chosen directory");
        verify(!Session.needsSaveAs, "A successful Save As must remove the need for another directory dialog");
        const location = Session.projectLocation;
        Session.project.name = "changed";
        verify(Session.save(), "The second save after an edit must save in place");
        compare(Session.projectLocation, location, "Saving an edited project must retain its chosen directory");
        verify(!Session.needsSaveAs, "The second save must not request Save As again");
    }

    function test_appended_atom_has_a_valid_position_and_no_text_error() {
        open("tests/fixtures/e04_t1/editable-project");
        const sites = Session.project.currentStructure.atomSites;
        const count = sites.count;
        sites.append();
        compare(sites.count, count + 1, "Appending must add exactly one atom site");
        const row = Probe.rows(sites)[count];
        verify(row.wyckoffLetter.length > 0, "An appended atom must receive a nonempty Wyckoff letter");
        click("appBar.tab.structure");
        click("sideBar.tab.text");
        verify(!Ui.text(Ui.windowRoot(appWindow)).includes("Wyckoff letter ''"), "The appended atom must not create a model error in Text");
    }

    function test_positions_show_multiplicity_letter_and_coordinates() {
        open("tests/fixtures/e04_t1/editable-project");
        click("appBar.tab.structure");
        Ui.expandGroup(test, Probe, appWindow, "group.atom_site");
        const position = control("atomSite.wyckoffLetter.0");
        verify(position !== null, "The atom-site WP control must be present");
        verify(typeof position.currentIndex === "number", "The WP field must offer a combobox choice");
        verify(/\d+[a-z]\s*\([^)]*\)/.test(position.currentText), "The WP choice must show multiplicity, letter and coordinates");
    }

    function test_removing_last_structure_disables_dependent_pages() {
        open("tests/fixtures/e04_t1/editable-project");
        while (Session.project.structures.count)
            Session.project.removeStructure(0);
        verify(!AppState.experimentPageEnabled, "Experiment must disable after the final structure is removed");
        verify(!AppState.analysisPageEnabled, "Analysis must disable after the final structure is removed");
        verify(!AppState.reportPageEnabled, "Summary must disable after the final structure is removed");
    }

    function test_removing_last_experiment_disables_analysis_and_summary() {
        open("tests/fixtures/e04_t1/editable-project");
        while (Session.project.experiments.count)
            Session.project.removeExperiment(0);
        verify(AppState.experimentPageEnabled, "Experiment must remain available while a structure exists");
        verify(!AppState.analysisPageEnabled, "Analysis must disable after the final experiment is removed");
        verify(!AppState.reportPageEnabled, "Summary must disable after the final experiment is removed");
    }

    function test_supported_only_choices_explain_their_disabled_state() {
        open("tests/fixtures/e04_t1/editable-project");
        click("appBar.tab.experiment");
        for (const name of ["sampleForm", "scatteringType"]) {
            const field = control("experimentType." + name);
            verify(field !== null && !field.enabled, "A supported-only type choice must be shown disabled");
            verify(Ui.text(field).length > 0, "The disabled choice must still display its supported value");
        }
    }

    function test_scan_correlations_data() {
        return [
            {
                tag: "sequential",
                mode: "sequential"
            },
            {
                tag: "independent",
                mode: "independent"
            }
        ];
    }

    function checkExperiment(reference, index) {
        Session.project.currentExperimentIndex = index;
        tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 3000, "Selecting an experiment must finish its own dataset projection");
        const chart = control("correlations");
        verify(chart !== null, "The selected experiment must have the production Correlations chart");
        compare(chart.count, 3, "Each completed experiment must retain all three correlated parameters");
        const truth = reference.cases[index];
        for (let row = 0; row < 3; ++row) {
            for (let column = 0; column < row; ++column) {
                const i = truth.names.indexOf(chart.labels[row]);
                const j = truth.names.indexOf(chart.labels[column]);
                verify(i >= 0 && j >= 0, "The selected experiment must show the independent parameter identities");
                verify(Math.abs(chart.valueAt(row * 3 + column) - truth.matrix[i][j]) < 2e-4, "Switching experiments must show that experiment's own independent covariance, including its sign");
            }
        }
    }

    function test_scan_correlations(data) {
        const reference = JSON.parse(Probe.readFile("tests/fixtures/correlations/scan-reference.json"));
        open("tests/fixtures/correlations/scan-" + data.mode);
        click("appBar.tab.analysis");
        click("mainArea.analysis.tab.correlations");
        tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 3000, "The scan witness must finish its initial experiment projection before fitting");
        Session.project.fit.start();
        tryCompare(Session.project.fit, "running", false, 5000, "The two independent polynomial experiment fits must complete");
        compare(Session.project.fit.scanFitted, 2, "The switching witness must really fit both experiments");
        for (const index of [0, 1, 0, 1])
            checkExperiment(reference, index);
        const saved = Probe.repoUrl("build/test-tmp/correlation-scan-" + data.mode);
        verify(Session.saveAs(saved), "The app must save every experiment's own correlations");
        Session.closeProject();
        verify(Session.openProject(saved), "The app must reopen persisted per-experiment correlations");
        click("appBar.tab.analysis");
        click("mainArea.analysis.tab.correlations");
        for (const index of [1, 0, 1, 0])
            checkExperiment(reference, index);
    }

    function test_data_file_header_button_and_free_width() {
        verify(Session.createProject("empty-experiment", "Data file layout witness"), "The data-file witness must create a project");
        verify(Session.project.createStructure(), "The data-file witness must create a structure");
        verify(Session.project.createExperiment(), "The data-file witness must create an experiment");
        click("appBar.tab.experiment");
        Ui.expandGroup(test, Probe, appWindow, "group.experiments");
        const list = control("experiments.list");
        verify(list !== null, "The Experiments table must show its production ListView");
        verify(Ui.text(list).includes("Data file"), "The free-width data column must have its Data file header");
        compare(list.columnWidths[4], -1, "Data file must own the table's free width");
        const load = control("experiments.loadData.0");
        verify(load !== null && load.text === "Load data…", "An experiment without data must offer a real Load data button");
        verify(load.width > 0 && load.enabled, "The Load data button must have a usable width and accept input");
    }

    function test_diagnostics_button_matches_logging_level_size() {
        click("appBar.button.preferences");
        const button = control("preferences.diagnostics");
        verify(button !== null && button.text === "Show", "Diagnostics must offer a real Show button");
        const dialog = Probe.visibleDialogs(appWindow).find(item => Ui.text(item).includes("Logging level"));
        verify(dialog !== undefined, "Preferences must expose the Logging level control beside Diagnostics");
        const logging = findBy(dialog.contentItem, "model", ["Debug", "Info", "Error", "Disabled"]);
        verify(logging !== null, "The Logging level combobox must be present for the size comparison");
        compare(button.width, logging.width, "Diagnostics Show must be the Logging level combobox's width");
        dialog.reject();
    }

    function test_correlation_scale_empty_state_and_fit_values() {
        open("tests/fixtures/correlations/polynomial-3");
        click("appBar.tab.analysis");
        click("mainArea.analysis.tab.correlations");
        const chart = control("correlations");
        verify(chart !== null, "The Correlations tab must show the production chart");
        compare(chart.count, 0, "A project before fitting must show an empty correlation view");
        compare(String(chart.cellColor(-1)), "#d73027", "Negative unit correlation must use the external red endpoint");
        compare(String(chart.cellColor(0)), "#ffffff", "Zero correlation on the light chart must be white");
        compare(String(chart.cellColor(1)), "#4575b4", "Positive unit correlation must use the external blue endpoint");
        const reference = JSON.parse(Probe.readFile("tests/fixtures/correlations/reference.json")).cases["3"];
        Session.project.fit.start();
        tryCompare(Session.project.fit, "running", false, 5000, "The small polynomial fit must complete");
        compare(chart.count, 3, "The many-parameter fit must show all three free parameter identities");
        const labels = chart.labels;
        for (let row = 0; row < 3; ++row) {
            for (let col = 0; col < row; ++col) {
                const i = reference.names.indexOf(labels[row]);
                const j = reference.names.indexOf(labels[col]);
                verify(i >= 0 && j >= 0, "Each heatmap label must identify an independently chosen free parameter");
                verify(Math.abs(chart.valueAt(row * 3 + col) - reference.matrix[i][j]) < 2e-4, "Each shown coefficient must match the external correlation matrix");
            }
        }
        Session.project.correlations.maxParameters = 2;
        compare(chart.count, 2, "The parameter-count control must keep exactly the two strongest-correlated parameters");
        Session.project.correlations.level = 1;
        compare(chart.count, 0, "The absolute-correlation control must hide every pair below the chosen level");
    }

    function test_background_coefficients_have_editing_parity() {
        open("tests/fixtures/correlations/polynomial-3");
        click("appBar.tab.experiment");
        Ui.expandGroup(test, Probe, appWindow, "group.background");
        const experiment = Session.project.currentExperiment;
        const terms = experiment.backgroundTerms;
        verify(control("background.terms") !== null, "Polynomial must show its term table");
        const count = terms.count;
        click("background.appendTerm");
        compare(terms.count, count + 1, "Append must add exactly one coefficient");
        compare(Probe.rows(terms)[count].order, 3, "Append must choose the lowest unused order");
        verify(!terms.setOrder(count, 0), "A duplicate coefficient order must be refused");
        verify(!terms.setOrder(count, 6), "Polynomial orders above five must be refused");
        verify(terms.setOrder(count, 5), "A unique supported order must be editable");
        const coefficient = control("background.coef.0");
        verify(coefficient !== null, "The coefficient value must have a visible editing control");
        coefficient.forceActiveFocus();
        keyClick(Qt.Key_A, Qt.ControlModifier);
        for (const key of [Qt.Key_6, Qt.Key_Period, Qt.Key_2, Qt.Key_5])
            keyClick(key);
        keyClick(Qt.Key_Return);
        compare(Probe.rows(terms)[0].coef.value, 6.25, "Typing a coefficient must update the production model");
        click("background.removeTerm." + count);
        compare(terms.count, count, "Remove must erase exactly the selected coefficient");
        const selector = control("background.type");
        verify(selector !== null, "Coefficient backgrounds must retain the type selector");
        selector.selected("chebyshev");
        const question = findChild(appWindow, "background.typeQuestion");
        verify(question !== null && question.visible, "Replacing rows must ask for confirmation");
        question.reject();
        compare(experiment.backgroundType, "polynomial", "Cancel must retain the existing background type");
        compare(terms.count, count, "Cancel must preserve every coefficient row");
        compare(Probe.rows(terms)[0].coef.value, 6.25, "Cancel must preserve edited coefficient values");
        selector.selected("chebyshev");
        question.accept();
        tryCompare(experiment, "backgroundType", "chebyshev", 2000, "Accept must apply the chosen type");
        compare(terms.count, 0, "A new background type must start with no retained terms");
        compare(experiment.background.count, 0, "A coefficient background must not retain hidden points");
        compare(experiment.backgroundXMin, 40, "Chebyshev must initialize its domain from measured minimum");
        compare(experiment.backgroundXMax, 72, "Chebyshev must initialize its domain from measured maximum");
        verify(control("background.terms") !== null, "Chebyshev must show its term table");
        click("background.appendTerm");
        compare(terms.count, 1, "Chebyshev must offer the same append operation");
        verify(terms.setOrder(0, 23), "Chebyshev must permit its highest supported order");
        verify(!terms.setOrder(0, 24), "Chebyshev must refuse orders beyond its supported range");
        click("background.removeTerm.0");
        compare(terms.count, 0, "Chebyshev must offer the same remove operation");
    }
}
