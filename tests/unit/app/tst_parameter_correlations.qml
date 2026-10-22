import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
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
        const input = SettingsProof.copyProject(Probe.repoUrl(path));
        verify(Session.openProject(input), "The independently authored project opens from a disposable copy without changing later cases' input: " + path);
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

    function test_appended_atom_is_random_general_and_has_no_text_error() {
        open("tests/fixtures/e04_t1/editable-project");
        const sites = Session.project.currentStructure.atomSites;
        const count = sites.count;
        const existing = Probe.rows(sites).map(site => site.typeSymbol);
        sites.append();
        compare(sites.count, count + 1, "Appending must add exactly one atom site");
        const row = Probe.rows(sites)[count];
        const supported = JSON.parse(Probe.readFile("tests/fixtures/correlations/atom-reference.json")).supported;
        verify(supported.includes(row.typeSymbol), "The random atom must be supported by the engine’s neutron and X-ray tables");
        verify(!existing.includes(row.typeSymbol), "A new atom must prefer an element absent from this structure");
        compare(row.wyckoffLetter, "n", "The cctbx Pm-3m catalogue requires a new atom on general position 48n");
        verify(/^[A-Z][a-z]?\d+$/.test(row.label), "A new atom label must be its element and a free number");
        compare(row.label.replace(/\d+$/, ""), row.typeSymbol, "The new atom label must use its selected element");
        for (const coordinate of [row.fractX.value, row.fractY.value, row.fractZ.value]) {
            verify(coordinate >= 0 && coordinate < 1, "New atom coordinates must lie in the fractional unit cell");
            verify(Math.abs(coordinate * 1000 - Math.round(coordinate * 1000)) < 1e-8, "New atom coordinates must have three decimal places");
        }
        const symmetry = JSON.parse(Probe.readFile("tests/fixtures/c34_t25_fullprof/wyckoff.json")).groups["Pm-3m"];
        const xyz = [row.fractX.value, row.fractY.value, row.fractZ.value];
        const orbit = new Set(symmetry.operations.map(op => [0, 1, 2].map(axis => {
                const image = op.t[axis] + op.r[3 * axis] * xyz[0] + op.r[3 * axis + 1] * xyz[1] + op.r[3 * axis + 2] * xyz[2];
                return Math.round(((image % 1 + 1) % 1) * 1e9) / 1e9;
            }).join(",")));
        compare(orbit.size, symmetry.general, "The new atom must have the independent general-position orbit rather than a special-position orbit");
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
        verify(/^\d+[a-z]: /.test(position.currentText), "Open-list Wyckoff entries must show multiplicity, letter, colon and coordinates");
        verify(/^\d+[a-z]$/.test(position.displayText), "The closed Wyckoff box must show only multiplicity and letter");
        verify(position.model.includes("24m: ½x+½y, ½x+½y, z"), "The Pm-3m catalogue’s 24m entry must use fraction glyphs");
        verify(position.model.includes("12i: 0, ½y+½z, ½y+½z"), "The Pm-3m catalogue’s 12i entry must retain its coordinates");
        const catalogue = JSON.parse(Probe.readFile("tests/fixtures/c34_t25_fullprof/wyckoff.json")).groups;
        const fractions = {
            "1/2": "½",
            "1/3": "⅓",
            "2/3": "⅔",
            "1/4": "¼",
            "3/4": "¾",
            "1/6": "⅙",
            "5/6": "⅚",
            "1/8": "⅛",
            "3/8": "⅜",
            "5/8": "⅝",
            "7/8": "⅞"
        };
        for (const group of ["Pm-3m", "Pnma"]) {
            Session.project.currentStructure.spaceGroup.nameHM = group;
            const expected = catalogue[group].wyckoff.map(wp => wp.multiplicity + wp.letter + ": " + wp.special_op.replace(/\d+\/\d+/g, value => fractions[value] || value).replace(/\*/g, "").replace(/-/g, "−").replace(/,/g, ", "));
            compare(JSON.stringify(Array.from(position.model).sort()), JSON.stringify(expected.sort()), "Every displayed WP choice must match the independent catalogue with fraction and minus glyphs");
            verify(/^\d+[a-z]$/.test(position.displayText), "Changing the space group must retain a WP-only closed display");
        }
        const glyphs = /[½⅓⅔¼¾⅙⅚⅛⅜⅝⅞−]/;
        verify(Session.saveAs(Probe.repoUrl("build/test-tmp/wyckoff-display")), "The displayed Wyckoff choices must permit saving the project");
        const saved = Probe.readFile("build/test-tmp/wyckoff-display/structures/lbco.edi");
        verify(saved.includes("_atom_site.wyckoff_letter"), "The saved structure must retain its ASCII Wyckoff field");
        verify(!glyphs.test(saved), "Unicode Wyckoff display must not change saved .edi text");
        click("sideBar.tab.text");
        verify(!glyphs.test(Ui.text(Ui.windowRoot(appWindow))), "The structure Text tab must retain ASCII data");
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
        Ui.expandGroup(test, Probe, appWindow, "group.experiments");
        for (const name of ["sampleForm", "scatteringType"]) {
            const field = control("experimentType." + name);
            verify(field !== null && !field.enabled, "The visible supported-only type choice is disabled; objectName=experimentType." + name + "; actual found=" + (field !== null) + "; enabled=" + (field ? field.enabled : "absent"));
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

    function checkExperiment(reference, index, readPoint) {
        Session.project.currentExperimentIndex = index;
        tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 3000, "Selecting an experiment must finish its own dataset projection");
        Session.project.correlations.level = 0;
        Session.project.correlations.maxParameters = 3;
        const chart = control("correlations");
        verify(chart !== null, "The selected experiment must have the production Correlations chart");
        compare(chart.count, 3, "Each completed experiment retains three independently correlated parameters at " + readPoint + "; dataset=" + index + "; actual count=" + chart.count);
        const truth = reference.cases[index];
        for (let row = 0; row < 3; ++row) {
            for (let column = 0; column < row; ++column) {
                const i = truth.names.indexOf(chart.labels[row]);
                const j = truth.names.indexOf(chart.labels[column]);
                verify(i >= 0 && j >= 0, "The selected experiment must show the independent parameter identities");
                const raw = truth.matrix[i][j];
                const stored = readPoint.includes("reopened");
                const expected = stored ? Number(raw.toPrecision(Math.abs(raw) >= 0.95 ? 3 : 2)) : raw;
                verify(Math.abs(chart.valueAt(row * 3 + column) - expected) < (stored ? 1e-14 : 2e-4), "Dataset selection retains its signed external covariance, IUCr-rounded only after persistence; read point=" + readPoint + " actual=" + chart.valueAt(row * 3 + column) + " expected=" + expected);
            }
        }
    }

    function test_scan_correlations(data) {
        const reference = JSON.parse(Probe.readFile("tests/fixtures/correlations/scan-reference.json"));
        const input = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/correlations/scan-" + data.mode));
        verify(Session.openProject(input), "The scan fits a disposable copy without changing its committed independent fixture");
        click("appBar.tab.analysis");
        click("mainArea.analysis.tab.correlations");
        tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 3000, "The scan witness must finish its initial experiment projection before fitting");
        Session.project.fit.start();
        tryCompare(Session.project.fit, "running", false, 5000, "The two independent polynomial experiment fits must complete");
        compare(Session.project.fit.scanFitted, 2, "The switching witness must really fit both experiments");
        for (const index of [0, 1, 0, 1])
            checkExperiment(reference, index, "live before save");
        const saved = Probe.repoUrl("build/test-tmp/correlation-scan-" + data.mode);
        verify(Session.saveAs(saved), "The app saves only the effective first dataset matrix while retaining all live matrices");
        Session.closeProject();
        verify(Session.openProject(saved), "The app must reopen persisted per-experiment correlations");
        click("appBar.tab.analysis");
        click("mainArea.analysis.tab.correlations");
        // Before: all reloaded datasets had matrices. After: only the effective first template does.
        for (const index of [1, 0, 1, 0]) {
            if (index === 0) {
                checkExperiment(reference, index, "reopened effective template");
            } else {
                Session.project.currentExperimentIndex = index;
                tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 3000, "The non-template dataset completes its actual reopened projection");
                compare(control("correlations").count, 0, "Only the effective first template matrix persists; other live dataset matrices remain memory-only");
                verify(Session.project.correlations.emptyText.toLowerCase().includes("template"), "The reopened non-template dataset explains the template-only persistence rule");
            }
        }
    }

    function test_data_file_header_link_and_free_width() {
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
        verify(load !== null && load.text === "Load data…", "An experiment without data must offer a Load data text link");
        verify(load.width > 0 && load.enabled, "The Load data link must have a usable width and accept input");
        compare(load.horizontalAlignment, Text.AlignLeft, "The data-file link must be left aligned");
        compare(String(load.color), String(Style.Colors.themeAccent), "An empty data-file link must use accent blue");
        open("tests/fixtures/e04_t1/editable-project");
        click("appBar.tab.experiment");
        Ui.expandGroup(test, Probe, appWindow, "group.experiments");
        const loaded = control("experiments.loadData.0");
        verify(loaded !== null && loaded.text.length > 0, "An experiment loaded from disk must retain its data-file link");
        const point = Ui.clickPoint(loaded);
        verify(point !== null, "The loaded filename must expose a pointer target");
        mouseMove(loaded, point.x, point.y);
        tryCompare(loaded, "color", Style.Colors.themeAccent, 1000, "Hovering the loaded filename must turn it accent blue");
        verify(Session.saveAs(Probe.repoUrl("build/test-tmp/data-link-reload")), "The linked experiment must save for reload");
        open("build/test-tmp/data-link-reload");
        click("appBar.tab.experiment");
        Ui.expandGroup(test, Probe, appWindow, "group.experiments");
        verify(control("experiments.loadData.0") !== null, "The data-file link must remain available after a save and reload");
    }

    function test_diagnostics_button_matches_the_preferences_control_column() {
        click("appBar.button.preferences");
        const dialogs = Probe.visibleDialogs(appWindow);
        const dialog = dialogs.find(item => findChild(item, "preferences.tab.develop") !== null);
        verify(dialog !== undefined, "The actual Preferences dialog exposes its Develop tab; actual dialogs=" + dialogs.length);
        const appearance = findChild(dialog, "preferences.tab.appearance");
        mouseClick(appearance, appearance.width / 2, appearance.height / 2);
        tryCompare(appearance, "checked", true, 1000, "Appearance opens before taking the actual combo control width");
        tryVerify(() => findChild(dialog, "preferences.colourScheme") !== null && findChild(dialog, "preferences.colourScheme").width > 0, 2000, "The real Appearance combo is laid out before its width is read");
        const column = findChild(dialog, "preferences.colourScheme").width;
        const tab = findChild(dialog, "preferences.tab.develop");
        mouseClick(tab, tab.width / 2, tab.height / 2);
        tryCompare(tab, "checked", true, 1000, "The actual Develop tab opens before Diagnostics geometry is read");
        const button = findChild(dialog, "preferences.diagnostics");
        verify(button !== null && button.text === "Show", "The visible Develop tab exposes its actual Diagnostics Show button");
        tryVerify(() => button.visible && button.width > 0, 2000, "The actual Diagnostics control finishes its Preferences slide before measuring");
        fuzzyCompare(button.width, column, 1, "Diagnostics Show shares the actual Appearance combo control column, independent of a private layout property; actual button=" + button.width + "; actual colour-scheme combo width=" + column);
        dialog.reject();
    }

    function test_correlation_scale_empty_state_and_fit_values() {
        open("tests/fixtures/correlations/polynomial-3");
        click("appBar.tab.analysis");
        click("mainArea.analysis.tab.correlations");
        const chart = findChild(appWindow.contentItem, "correlations");
        verify(chart !== null, "The selected mainArea.analysis.tab.correlations exposes its actual correlations chart; actual tab=" + control("mainArea.analysis.tab.correlations").checked);
        compare(chart.count, 0, "A project before fitting must show an empty correlation view");
        compare(String(chart.cellColor(-1)), "#d73027", "Negative unit correlation must use the external red endpoint");
        compare(String(chart.cellColor(0)), "#ffffff", "Zero correlation on the light chart must be white");
        compare(String(chart.cellColor(1)), "#4575b4", "Positive unit correlation must use the external blue endpoint");
        const reference = JSON.parse(Probe.readFile("tests/fixtures/correlations/reference.json")).cases["3"];
        Session.project.fit.start();
        tryCompare(Session.project.fit, "running", false, 5000, "The small polynomial fit must complete");
        Session.project.correlations.level = 0;
        Session.project.correlations.maxParameters = 3;
        compare(chart.count, 3, "The actual completed fit shows all three independently free parameter identities at explicit level zero; actual count=" + chart.count + "; labels=" + JSON.stringify(chart.labels));
        const labels = chart.labels;
        for (let row = 0; row < 3; ++row) {
            for (let col = 0; col < row; ++col) {
                const i = reference.names.indexOf(labels[row]);
                const j = reference.names.indexOf(labels[col]);
                verify(i >= 0 && j >= 0, "Each heatmap label must identify an independently chosen free parameter");
                verify(Math.abs(chart.valueAt(row * 3 + col) - reference.matrix[i][j]) < 2e-4, "Each shown coefficient must match the external correlation matrix");
            }
        }
        Session.project.correlations.level = 0.8;
        compare(chart.count, 3, "The level chooses three parameters through their strongest pairs");
        const row = chart.labels.indexOf(reference.names[2]);
        const column = chart.labels.indexOf(reference.names[0]);
        const cells = findChild(chart, "correlations.cells");
        verify(cells !== null, "The chart must expose its actual cell delegates");
        const weak = cells.itemAt(row * 3 + column);
        verify(Math.abs(weak.value - reference.matrix[2][0]) < 2e-4, "A below-level pair between shown parameters must keep its independent coefficient");
        compare(String(weak.color), String(chart.cellColor(weak.value)), "The below-level pair must retain its diverging colour");
        const pointer = control("correlations.pointer");
        mouseMove(pointer, (column + 0.5) * pointer.width / 3, (row + 0.5) * pointer.height / 3);
        const popup = findChild(chart, "correlations.toolTip");
        verify(popup !== null, "A shown weak pair must retain its coefficient popup");
        tryVerify(() => popup.visible, 2000, "Hovering a below-level finite pair must show its popup");
        verify(popup.text.includes(reference.matrix[2][0].toFixed(2)), "The weak pair's popup must name its independent coefficient");
        Session.project.correlations.maxParameters = 2;
        compare(chart.count, 2, "The parameter-count control must keep exactly the two strongest-correlated parameters");
        Session.project.correlations.level = 1;
        compare(chart.count, 0, "A level above every finite pair must select no parameters");
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
        verify(SettingsProof.type(coefficient, "6.25"), "The keyboard observer sends real text to the coefficient's own app window and active input, rather than the Quick Test runner window; actual text=" + coefficient.text);
        verify(SettingsProof.key(coefficient, Qt.Key_Return), "Return reaches the actual coefficient editor's own app window to commit its typed value");
        compare(Probe.rows(terms)[0].coef.value, 6.25, "Actual keyboard input plus Return commits the independently entered background coefficient; actual first term=" + JSON.stringify(Probe.rows(terms)[0]));
        click("background.removeTerm." + count);
        compare(terms.count, count, "Remove must erase exactly the selected coefficient");
        const selector = control("background.type");
        verify(selector !== null, "Coefficient backgrounds must retain the type selector");
        selector.selected("chebyshev");
        const background = control("group.background");
        const question = findChild(background, "background.typeQuestion") || findChild(appWindow.contentItem, "background.typeQuestion");
        verify(question !== null, "The actual background group retains its type confirmation popup; actual group=" + (background ? background.objectName : "absent"));
        tryCompare(question, "visible", true, 2000, "Changing an existing background opens the actual confirmation popup owned by its group, including its real overlay transition; actual type=" + experiment.backgroundType);
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
    // Owner name contract, tested on the ORIGINAL source component and real focused native input.
    // This observes text/path state, never duplicates the production validator/regular expression.
    function project454_nameState(dialog, field, location, expected, directory) {
        compare(field.text, expected, "NAME454: genuine original native input retains the exact independent name spelling");
        compare(dialog.projectName, expected, "NAME454: original name alias follows actual typed field, not assigned test data");
        verify(field.acceptableInput === true, "NAME454: letters/digits/spaces/Unicode are acceptable to the actual native validator");
        verify(location.text.endsWith(expected), "NAME454: actual location preview retains the COMPLETE exact user name");
        const base = SettingsProof.localPath(directory);
        const prefix = location.text.slice(0, location.text.length - expected.length);
        compare(prefix.slice(0, -1), base, "NAME454: location preview stays inside the independent chosen owned directory");
        verify(prefix.endsWith("/") || prefix.endsWith("\\"), "NAME454: one actual platform path separator joins directory and name");
    }
    function test_project454_original_name_accepts_native_text_and_refuses_path_controls() {
        // Load the real source URL rather than relabeling old compiled resources as a new dialog.
        // The existing unit's separate Main Create/save assertions remain unchanged.
        const component = Qt.createComponent(Probe.repoUrl("app/qml/Base/Gui/Components/ProjectDescriptionDialog.qml"));
        tryCompare(component, "status", Component.Ready, 2000,
            "NAME454: original ProjectDescriptionDialog source loads in the existing registered native engine: " + component.errorString());
        const dialog = createTemporaryObject(component, appWindow.contentItem);
        verify(dialog !== null && dialog.objectName === "createProject.dialog", "NAME454: test hosts the original named production dialog, no copied form");
        const previousParent = dialog.projectParentDirectory;
        const directory = SettingsProof.emptyDirectory();
        verify(SettingsProof.localPath(directory).length > 0, "NAME454 SETUP: existing helper supplies a fresh owned location, not a fabricated picker acceptance");
        dialog.projectParentDirectory = String(directory); // Existing original directory setup only; all NAME input is native.
        const dialogWatch = Probe.watch(dialog);
        let field = null, fieldWatch = -1, accepted = 0, acceptedLocation = "", edited = [];
        function observedText() { edited.push(field.text); }
        function observedAccepted() { ++accepted; acceptedLocation = dialog.projectLocation; }
        let connectedText = false, connectedAccept = false;
        try {
            dialog.open();
            tryCompare(dialog, "opened", true, 2000, "NAME454: actual original dialog finishes native entry before input");
            verify(waitForPolish(dialog.contentItem) && waitForRendering(appWindow.contentItem), "NAME454: original native field layout renders before real pointer/key input");
            field = findChild(dialog, "createProject.name");
            const location = findChild(dialog, "createProject.location");
            verify(field !== null && location !== null && field.visible && field.enabled && Ui.exposed(field),
                "NAME454: exact original name/location controls exist and the genuine input receiver is exposed");
            fieldWatch = Probe.watch(field);
            verify(dialogWatch >= 0 && fieldWatch >= 0 && Probe.watchedAlive(dialogWatch) && Probe.watchedAlive(fieldWatch),
                "NAME454: original dialog and field have actual native lifetime receipts");
            field.textEdited.connect(observedText); connectedText = true;
            dialog.accepted.connect(observedAccepted); connectedAccept = true;
            mouseClick(field, field.width / 2, field.height / 2);
            verify(field.activeFocus && appWindow.activeFocusItem === field,
                "NAME454: real pointer selects the exact current native name receiver");
            keyClick(Qt.Key_A, Qt.ControlModifier); keyClick(Qt.Key_Backspace);
            compare(field.text, "", "NAME454: actual key input clears any persisted name before the independent witness");
            // ASCII keyboard witnesses cover ordinary letters, a digit run and an internal space.
            for (const character of "Project 42") {
                const upper = character >= "A" && character <= "Z";
                keyClick(character, upper ? Qt.ShiftModifier : Qt.NoModifier);
            }
            project454_nameState(dialog, field, location, "Project 42", directory);
            verify(edited.includes("Project 42"), "NAME454: actual textEdited signal proves ordinary native key input reached its final spelling");
            // Existing bounded genuine QInputMethodEvent supports non-Latin Unicode and NUL
            // on the same focused receiver; no text/property/accepted signal is assigned.
            const unicode = Probe.focusedInputMethod233(appWindow, field, "", " Åβ");
            verify(unicode.delivered === true && unicode.targetAlive === true && unicode.focusMatchesAfter === true
                && unicode.eventKind === "InputMethod" && unicode.commit === " Åβ",
                "NAME454: original focused Qt input method really receives the independent Unicode commit");
            project454_nameState(dialog, field, location, "Project 42 Åβ", directory);
            verify(edited.includes("Project 42 Åβ"), "NAME454: Unicode is adopted by the original native input path, not a regex-only example");
            const expected = "Project 42 Åβ", preview = location.text;
            for (const key of [Qt.Key_Slash, Qt.Key_Backslash]) {
                verify(Probe.watchedAlive(fieldWatch) && field.activeFocus && appWindow.activeFocusItem === field,
                    "NAME454: each forbidden key still targets the same original current native field");
                keyClick(Qt.Key_End); const before = edited.length;
                keyClick(key);
                project454_nameState(dialog, field, location, expected, directory);
                compare(location.text, preview, "NAME454: slash/backslash rejection cannot redirect or alter the original location");
                compare(edited.length, before, "NAME454: forbidden separator is refused before any accepted name edit");
                verify(field.activeFocus && appWindow.activeFocusItem === field,
                    "NAME454: rejected separator cannot transfer input authority to another receiver");
                compare(accepted, 0, "NAME454: rejected name input cannot trigger original Create acceptance");
            }
            const beforeNul = edited.length, nul = String.fromCharCode(0);
            const rejected = Probe.focusedInputMethod233(appWindow, field, "", nul);
            verify(rejected.delivered === true && rejected.targetAlive === true && rejected.focusMatchesAfter === true
                && rejected.eventKind === "InputMethod" && rejected.commit.length === 1 && rejected.commit.charCodeAt(0) === 0,
                "NAME454: exact bounded NUL commit reaches the original focused native input event, never a setter or ignored shortcut");
            project454_nameState(dialog, field, location, expected, directory);
            compare(location.text, preview, "NAME454: NUL cannot enter the location preview");
            compare(edited.length, beforeNul, "NAME454: NUL is refused before an accepted text edit");
            compare(accepted, 0, "NAME454: no rejected key/IME input creates a project or acceptance");
            keyClick(Qt.Key_Return);
            tryCompare(dialog, "visible", false, 2000, "NAME454: genuine Return preserves original native accept/close behavior");
            compare(accepted, 1, "NAME454: the original final Return accepts exactly ONCE, no synthetic accepted/duplicate tail");
            compare(acceptedLocation, preview, "NAME454: original accepted handler publishes the exact preview location");
            compare(dialog.projectLocation, preview, "NAME454: selected name/location semantics stay unchanged after native acceptance");
            compare(Session.project, null, "NAME454: isolated original source dialog does not substitute a direct native Create/save call");
            console.log("NAME454_INPUT", JSON.stringify({typed: edited, unicode: unicode, nul: rejected,
                name: expected, preview: preview, accepted: accepted, acceptedLocation: acceptedLocation,
                componentSource: String(Probe.repoUrl("app/qml/Base/Gui/Components/ProjectDescriptionDialog.qml"))}));
        } finally {
            if (connectedText && Probe.watchedAlive(fieldWatch)) field.textEdited.disconnect(observedText);
            if (connectedAccept && Probe.watchedAlive(dialogWatch)) dialog.accepted.disconnect(observedAccepted);
            if (Probe.watchedAlive(dialogWatch)) {
                dialog.projectParentDirectory = previousParent;
                dialog.close();
            }
        }
    }
}
