import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ProjectTextAcceptance 1.0
import EasyApplication.Gui.Globals as Globals
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "MeasuredDataControls"
    when: windowShown
    property var appWindow
    property bool oldToolTips
    property int oldTheme
    ProjectTextProof {
        id: reference
    }
    Component {
        id: application
        Main {}
    }

    function init() {
        oldToolTips = Globals.Vars.showToolTips;
        oldTheme = Style.Colors.theme;
        Globals.Vars.showToolTips = true;
        Session.closeProject();
        appWindow = application.createObject(null, {
            width: 1300,
            height: 720,
            visible: true
        });
        verify(appWindow !== null, "Measured-data availability uses the production application window");
        verify(Session.openExample("pd-neut-cwl_lbco_simulation"), "The real bundled LBCO simulation opens: " + Session.lastError);
        ready();
        verify(Session.project.currentExperiment.calculationOnly, "The initial example has no measured observations");
        verify(!Session.project.fit.measured, "The simulation has no measured experiment anywhere in its project");
        Session.project.currentExperiment.backgroundEstimateMode = "manual";
        ready();
    }
    function cleanup() {
        Session.closeProject();
        if (appWindow)
            appWindow.destroy();
        appWindow = null;
        Globals.Vars.showToolTips = oldToolTips;
        Style.Colors.theme = oldTheme;
    }
    function ready() {
        tryVerify(() => Session.project && !Session.project.calculating && !Session.project.currentExperiment.pattern.stale, 10000, "The real project finishes its current calculation before controls are inspected");
        compare(Session.project.currentExperiment.pattern.calculationError, "", "The availability witness has a valid calculated pattern");
    }
    function click(name) {
        Ui.click(test, Probe, appWindow, name);
    }
    function page(name, tier) {
        click("appBar.tab." + name);
        const current = Ui.page(appWindow);
        if (tier) {
            let tab;
            tryVerify(() => (tab = Ui.find(current, "sideBar.tab." + tier)) !== null, 2000, "The selected page finishes sliding into view before its sidebar tab is inspected: " + tier);
            if (!tab.enabled)
                return null;
            click("sideBar.tab." + tier);
        }
        return current;
    }
    function active(root, predicate) {
        return Render.descendants(root).filter(item => predicate(item) && Ui.inPane(Ui.target(item)));
    }
    function groups(root, id) {
        return active(root, item => item.titleArea && (item.categoryId === id || item.objectName === "group." + id));
    }
    function exposed(item) {
        Ui.scrollIntoView(Ui.target(item));
        verify(waitForPolish(appWindow.contentItem) && waitForRendering(appWindow.contentItem), "The inspected control completes layout and a real frame");
        verify(Ui.exposed(Ui.target(item)), "The inspected control can be reached in the current sidebar");
    }
    function expand(group) {
        exposed(group);
        if (group.collapsed)
            Ui.expandGroup(test, Probe, appWindow, group.objectName);
    }
    function loadMeasurements() {
        const original = Session.project;
        verify(original.loadDataInto(original.currentExperiment, Probe.repoUrl("tests/fixtures/background_estimate/meas-lbco-hrpt.xye")), "The production data loader adds independent measured LBCO observations: " + original.lastError);
        ready();
        compare(Session.project, original, "Loading data keeps the same application project open");
        verify(!original.currentExperiment.calculationOnly && original.fit.measured, "Loaded observations change actual experiment and project data presence");
        original.currentExperiment.backgroundEstimateMode = "manual";
        ready();
    }
    function tooltipNeedsMeasurements(button) {
        exposed(button);
        mouseMove(button, button.width / 2, button.height / 2);
        tryVerify(() => {
            // Qt's shared attached tooltip need not be a QObject child of the window.
            const popups = Probe.visiblePopups(appWindow).concat([button.ToolTip.toolTip]);
            const text = popups.filter(popup => popup && popup.visible && popup.opened).map(popup => Ui.text(popup.contentItem ?? popup)).join(" ");
            return /measur|observ/i.test(text) && /data|pattern/i.test(text) && /need|require|load|without|first|available/i.test(text);
        }, 2500, "Hovering disabled Estimate displays a tooltip explaining that measured data must be loaded");
        mouseMove(appWindow.contentItem, 1, 1);
    }
    function experimentControls(measured, projectMeasured) {
        if (projectMeasured === undefined)
            projectMeasured = measured;
        const basic = page("experiment", "basic");
        const background = groups(basic, "background");
        compare(background.length, 1, "A simulation retains its main Background points group");
        expand(background[0]);
        const estimates = active(background[0], item => item.objectName === "background.estimate");
        compare(estimates.length, 1, "The actual background table exposes its Estimate action");
        exposed(estimates[0]);
        compare(estimates[0].enabled, measured, "Estimate is available exactly when this manual-background experiment holds measured data");
        if (!measured)
            tooltipNeedsMeasurements(estimates[0]);
        let exclusions = groups(basic, "excluded_region").length;
        const extras = page("experiment", "extras");
        verify(extras !== null, "A simulation keeps its Extras tab for calculation settings");
        const settings = groups(extras, "background").concat(groups(extras, "background_estimate"));
        compare(settings.length > 0, measured, "Background estimation settings are hidden without measurements and return after loading data");
        exclusions += groups(extras, "excluded_region").length;
        compare(exclusions > 0, measured, "Excluded regions are hidden without measurements and return after loading data");
        const cutoff = active(extras, item => item.titleArea && (item.categoryId === "peak" || item.objectName === "group.peak" || Render.descendants(item).some(child => child.objectName === "peak.cutoff_fwhm")));
        compare(cutoff.length, 1, "The peak cutoff group remains available with and without measured data");
        exposed(cutoff[0]);
        verify(cutoff[0].title.trim().length > 0 && cutoff[0].title.trim().toLowerCase() !== "peak profile", "The cutoff group has its own name instead of appearing as a second Peak profile group");
        expand(cutoff[0]);
        const cutoffField = active(cutoff[0], item => item.objectName === "peak.cutoff_fwhm");
        compare(cutoffField.length, 1, "The retained group contains the real peak-cutoff editor");
        verify(cutoffField[0].enabled, "Peak cutoff remains a usable calculation setting without measured data");
        const analysis = page("analysis", "basic");
        const correlations = active(analysis, item => item.objectName === "mainArea.analysis.tab.correlations");
        compare(correlations.length, 1, "The real Analysis page retains its Correlations tab");
        compare(correlations[0].enabled, projectMeasured, "Correlations depends on measured data anywhere in the project rather than only the selected experiment");
    }
    function listingControls(root) {
        return active(root, item => /^(?:parameters\.(?:datablock|category|variability|nameFilter|clearFilters|shown|listing)|group\.(?:shownParameters|shown_parameters))$/.test(item.objectName) || String(item).startsWith("ShownParametersGroup"));
    }
    function freeMenuOpen() {
        return Probe.visiblePopups(appWindow).some(popup => Render.descendants(popup.contentItem ?? popup).some(item => /^parameters\.freeHeader\.(free|fixed|mixed)$/.test(item.objectName)));
    }
    function analysisControls(measured, relationsApply) {
        const basic = page("analysis", "basic");
        const parameters = groups(basic, "parameters");
        compare(parameters.length, 1, "The Analysis parameter values remain available for a calculation");
        expand(parameters[0]);
        const table = active(parameters[0], item => item.objectName === "parameters.list")[0];
        verify(table !== undefined && table.count > 0, "The retained Analysis table contains actual parameter rows");
        table.forceLayout();
        const first = table.itemAtIndex(0);
        verify(first !== null, "The retained table creates a real value row");
        const values = active(first, item => /^parameters\.value\./.test(item.objectName));
        verify(values.length > 0, "The simulation's parameter values are rendered rather than an empty table shell");
        const titles = Render.texts(table.headerItem).map(item => item.text.toLowerCase());
        for (const title of ["value", "min", "max"])
            verify(titles.includes(title), "Values and their limits stay in Analysis without measured data");
        const row = Probe.rows(table.sourceModel)[0];
        verify(typeof row.units === "string", "The retained parameter row still carries its units");
        if (row.units !== "")
            verify(Render.texts(first).some(item => item.text === row.units), "The retained parameter row actually displays its units");
        const header = active(table.headerItem, item => item.objectName === "parameters.freeHeader");
        const free = active(table, item => /^parameters\.free\.\d+$/.test(item.objectName));
        compare(header.length > 0, measured, "The free-column header is hidden without measured data and restored afterwards");
        compare(free.length > 0, measured, "Free checkboxes are hidden without measured data and restored afterwards");
        compare(listingControls(basic).length > 0, measured, "The parameter listing filters are hidden without measured data and restored afterwards");
        if (measured) {
            exposed(header[0]);
            click("parameters.freeHeader");
            tryVerify(freeMenuOpen, 1000, "Measured data restores the real free-header menu");
            keyClick(Qt.Key_Escape);
            tryVerify(() => !freeMenuOpen(), 1000, "The measured-data free menu closes before navigation");
        } else {
            exposed(table.headerItem);
            mouseClick(table.headerItem, table.headerItem.width - 2, table.headerItem.height / 2);
            verify(!freeMenuOpen(), "A reparented or hidden header input area cannot expose the free menu without data");
        }
        const fit = active(basic, item => item.objectName === "fitting.start");
        compare(fit.length, 1, "The Analysis fit action remains discoverable in a simulation");
        if (!measured)
            verify(!fit[0].enabled, "The simulation cannot start a fit without measured data");
        const dictionary = reference.dictionary();
        verify(dictionary.categories && dictionary.categories.length > 0, "Fit-only category identities come from the selected SDK dictionary");
        const reflectionSelection = dictionary.categories.find(item => item.title === "Fitted reflections");
        verify(reflectionSelection !== undefined, "The dictionary declares the single-crystal fitted-reflection selection category");
        const hidden = ["minimizer", "fitting_mode", reflectionSelection.id, "joint_fit", "fit_parameter", "sequential_fit", "sequential_fit_extract"];
        if (!measured) {
            for (const category of hidden.concat(["patternUpdates"]))
                compare(groups(basic, category).length, 0, "Fit-only groups cannot escape the no-data rule by living in Basic");
        }
        const extras = page("analysis", "extras");
        if (!measured) {
            if (extras) {
                for (const category of hidden)
                    compare(groups(extras, category).length, 0, "Fit-only Analysis groups are hidden when no experiment has measured data");
                compare(groups(extras, "patternUpdates").length, 0, "Pattern updates cannot escape the no-data rule by living in Extras");
                compare(listingControls(extras).length, 0, "The listing group cannot escape the no-data rule by living in Extras");
            }
        } else {
            verify(extras !== null, "Measured data restores the Analysis fit-settings pane");
            const carried = Session.project.analysis.text.text;
            for (const category of hidden) {
                if (["minimizer", "fitting_mode"].includes(category) || new RegExp("^_" + category + "\\.", "m").test(carried))
                    verify(groups(extras, category).length > 0, "Measured data restores every applicable declared fit-settings category");
            }
        }
        for (const category of ["alias", "constraint"])
            compare(extras ? groups(extras, category).length > 0 : false, measured || relationsApply, "Aliases and constraints stay available when they affect a calculation without measurements");
        const settings = page("analysis", "settings");
        compare(settings ? groups(settings, "patternUpdates").length > 0 : false, measured, "Pattern updates is hidden without measurements and restored after loading data");
        if (!measured && settings) {
            compare(listingControls(settings).length, 0, "The listing group cannot escape the no-data rule by living in Settings");
            for (const category of hidden)
                compare(groups(settings, category).length, 0, "Fit-only groups cannot escape the no-data rule by living in Settings");
        }
    }
    function test_experiment_and_correlations_transition_data() {
        return [
            {
                tag: "light",
                theme: Style.Colors.LightTheme
            },
            {
                tag: "dark",
                theme: Style.Colors.DarkTheme
            }
        ];
    }
    function test_experiment_and_correlations_transition(data) {
        Style.Colors.theme = data.theme;
        experimentControls(false);
        loadMeasurements();
        experimentControls(true);
    }
    function test_analysis_transition() {
        analysisControls(false, false);
        loadMeasurements();
        analysisControls(true, false);
    }
    function test_project_wide_correlations_keep_data_from_other_experiments() {
        loadMeasurements();
        verify(Session.project.createExperiment(), "The measured project can create another calculation-only experiment");
        ready();
        verify(Session.project.currentExperiment.calculationOnly, "The mixed-project witness selects its unmeasured experiment");
        verify(Session.project.fit.measured, "The mixed project retains measurements in its original experiment");
        Session.project.currentExperiment.backgroundEstimateMode = "manual";
        ready();
        experimentControls(false, true);
    }
    function test_calculation_constraints_remain_available() {
        const project = Session.project;
        project.analysis.aliases.append();
        verify(project.analysis.aliases.setText(0, "id", "edge"), "The calculation witness declares a named cubic-cell edge alias");
        verify(project.analysis.aliases.setText(0, "parameter", "lbco.cell.length_a"), "The alias targets the cubic simulation's independent a parameter; symmetry ties b and c to a");
        project.analysis.constraints.append();
        verify(project.analysis.constraints.setText(0, "expression", "edge = 4.125"), "A nontrivial independent cell-edge constraint is applied through the real project editor");
        ready();
        compare(project.currentStructure.cell.lengthA.value, 4.125, "A calculation without observations actually adopts the declared constraint value");
        analysisControls(false, true);
        loadMeasurements();
        analysisControls(true, true);
        compare(project.currentStructure.cell.lengthA.value, 4.125, "Loading measurements preserves the calculation's applied constraint");
    }
}
