import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiSymmetryReference 1.0
import "E04Review.js" as Review
import "UiInteraction.js" as Ui

//  gates 3–5: live crysta API for every CLI project, file-declared model
// identities for fitting-mode filtering. No app output supplies symmetry expectations.
TestCase {
    id: test
    name: "E04T5Symmetry"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }
    Component {
        id: fields
        CellGroup {}
    }
    Component {
        id: sites
        AtomSitesGroup {}
    }
    Component {
        id: listing
        ParametersGroup {}
    }
    property var widgets: []

    function init() {
        Session.closeProject();
        widgets = [];
        appWindow = application.createObject(null);
        verify(appWindow !== null, " gate 3 production app window exists");
    }
    function cleanup() {
        Probe.clearWatches();
        widgets.forEach(item => item.destroy());
        Session.closeProject();
        appWindow.destroy();
    }
    function open(path) {
        Session.openProject(Probe.repoUrl(path));
        verify(Session.hasProject, " gate 3 CLI project opens: " + Session.lastError);
    }
    function cases() {
        const result = SymmetryOracle.projects();
        verify(result.length > 0, " gate 3 CLI reference inventory is nonempty");
        return result;
    }
    function key(row) {
        return row.category + "/" + row.row + "/" + row.name;
    }
    function observed() {
        const structure = Session.project.currentStructure;
        const cell = structure.cell;
        const output = {};
        ["lengthA", "lengthB", "lengthC", "angleAlpha", "angleBeta", "angleGamma"].forEach(member => {
            const item = cell[member];
            verify(item !== null, " gate 3 tied cell fields remain present");
            output["cell//" + item.name] = item;
        });
        Probe.rows(structure.atomSites).forEach(row => {
            ["fractX", "fractY", "fractZ"].forEach(member => {
                const item = row[member];
                verify(item !== null, " gate 3 tied atom fields remain present");
                output["atom_site/" + row.label + "/" + item.name] = item;
            });
        });
        return output;
    }
    function test_reference_is_total_data() {
        const result = cases();
        verify(result.some(data => SymmetryOracle.structure(data.path).some(row => row.category === "atom_site" && !row.independent)), " gate 3 reference corpus requires dependent positional controls");
        return result;
    }
    function test_reference_is_total(data) {
        const oracle = SymmetryOracle.structure(data.path);
        verify(oracle.length >= 6, " gate 3 crysta supplies cell and positional freedom");
        verify(oracle.some(row => row.independent), " gate 3 independent reference is nonvacuous");
    }
    function test_app_freedom_and_implied_values_data() {
        return cases();
    }
    function test_app_freedom_and_implied_values(data) {
        open(data.path);
        const oracle = SymmetryOracle.structure(data.path);
        verify(oracle.length >= 6, " gate 3 independent symmetry oracle resolves");
        const items = observed();
        compare(Object.keys(items).length, oracle.length, " gate 3 app exposes every cell and coordinate field");
        oracle.forEach(row => {
            const item = items[key(row)];
            verify(item !== undefined, " gate 3 reference field exists in app");
            compare(item.refinable, row.independent, " gate 3 eligibility role equals crysta independent basis: " + key(row));
            verify(Math.abs(item.value - row.value) < 1e-10, " gate 3 tied field shows crysta-implied value: " + key(row));
        });
        const cellFields = fields.createObject(appWindow.contentItem, {
            structure: Session.project.currentStructure,
            width: appWindow.contentItem.width
        });
        const atomFields = sites.createObject(appWindow.contentItem, {
            structure: Session.project.currentStructure,
            width: appWindow.contentItem.width
        });
        widgets.push(cellFields, atomFields);
        verify(waitForPolish(appWindow, 2000), " gate 3 production field delegates settle");
        const reached = [];
        function checkField(field, row) {
            verify(field !== undefined && field.item && field.parameter, " gate 3 every independent-reference identity reaches a production control: " + key(row));
            compare(key({
                category: field.item.category,
                row: field.item.rowLabel,
                name: field.item.name
            }), key(row), " gate 3 rendered field belongs to its expected reference identity");
            verify(field.visible && field.width > 0 && field.height > 0, " gate 3 expected cell or coordinate control has visible geometry");
            compare(field.parameter.enabled, row.independent, " gate 3 dependent value control is disabled");
            compare(field.parameter.fittable, row.independent, " gate 3 dependent vary control is disabled");
            compare(field.enabled, row.independent, " gate 3 production field interaction follows the independent basis");
            verify(Math.abs(field.parameter.value - row.value) < 1e-10, " gate 3 rendered field displays the crysta-implied value");
            reached.push(key(row));
        }
        oracle.filter(row => row.category === "cell").forEach(row => {
            const field = Review.descendants(cellFields).find(field => field.item && field.item.name === row.name);
            checkField(field, row);
        });
        const table = Review.descendants(atomFields).find(item => item.objectName === "atomSites.list");
        verify(table !== undefined, " gate 3 production coordinate table must be instantiated");
        const labels = [...new Set(oracle.filter(row => row.category === "atom_site").map(row => row.row))];
        verify(labels.length > 0, " gate 3 reference requires positional controls, not only cell controls");
        compare(table.count, labels.length, " gate 3 production coordinate table contains every reference site");
        labels.forEach((label, index) => {
            table.positionViewAtIndex(index, ListView.Center);
            tryVerify(() => table.itemAtIndex(index) !== null, 2000, " gate 3 production table materializes each required positional row");
            verify(waitForPolish(appWindow, 2000), " gate 3 positioned coordinate row settles");
            const delegate = table.itemAtIndex(index);
            oracle.filter(row => row.category === "atom_site" && row.row === label).forEach(row => {
                const field = Review.descendants(delegate).find(field => field.item && field.item.name === row.name);
                checkField(field, row);
            });
        });
        compare(reached.sort(), oracle.map(key).sort(), " gate 3 rendered cell and coordinate identities exactly equal the independent inventory");
    }
    function test_analysis_contains_exact_independent_set_data() {
        return cases();
    }
    function test_analysis_contains_exact_independent_set(data) {
        open(data.path);
        const oracle = SymmetryOracle.structure(data.path);
        verify(oracle.length >= 6, " gate 4 independent symmetry oracle resolves");
        const expected = oracle.filter(row => row.independent).map(key).sort();
        const table = listing.createObject(appWindow.contentItem, {
            project: Session.project
        });
        widgets.push(table);
        verify(waitForPolish(appWindow, 2000), " gate 4 Analysis production table settles");
        const view = Review.descendants(table).find(item => item.objectName === "parameters.list");
        verify(view !== undefined, " gate 4 production Analysis table exists");
        function structureKeys(model) {
            return Probe.rows(model).filter(row => row.blockKind === "structure" && (row.category === "cell" || (row.category === "atom_site" && row.name.startsWith("fract_")))).map(row => key({
                    category: row.category,
                    row: row.rowLabel,
                    name: row.name
                })).sort();
        }
        compare(structureKeys(Session.project.parameters), expected, " gate 4 source table contains all and only independent symmetry fields");
        compare(structureKeys(view.model), expected, " gate 4 rendered Analysis table contains no tied or symmetry-fixed field");
    }
    function test_analysis_mode_follows_selector_data() {
        return [
            {
                tag: "joint",
                mode: "joint"
            },
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
    function test_analysis_mode_follows_selector(data) {
        open("tests/fixtures/e04_t5/" + data.mode);
        const project = Session.project;
        compare(project.analysis.fittingMode, data.mode, " gate 5 fitting mode is loaded from the project file");
        project.analysis.fittingMode = "joint";
        compare(project.analysis.fittingMode, "joint", " gate 5 mode changes through project model");
        // Round-trip filtering invariant: the joint universe must be restored.
        // Experiment identities come from the independent fixture declaration.
        const allRows = Probe.rows(project.parameters);
        const names = ["hrpt", "second"];
        compare(Probe.rows(project.experiments).map(row => row.name), names, " gate 5 model retains independently declared experiment identities");
        compare(names.length, 2, " gate 5 independent fixture carries two distinct experiments");
        names.forEach(name => verify(allRows.some(row => row.blockKind === "experiment" && row.blockName === name), " gate 5 joint table carries every experiment"));
        const table = listing.createObject(appWindow.contentItem, {
            project: project
        });
        widgets.push(table);
        verify(waitForPolish(appWindow, 2000), " gate 5 production table settles");
        const view = Review.descendants(table).find(item => item.objectName === "parameters.list");
        verify(view !== undefined, " gate 5 rendered Analysis table exists");
        project.analysis.fittingMode = data.mode;
        compare(project.analysis.fittingMode, data.mode, " gate 5 table uses project fitting mode");
        [0, 1, 0].forEach(index => {
            project.currentExperimentIndex = index;
            const expected = allRows.filter(row => data.mode === "joint" || row.blockKind === "structure" || row.blockName === names[index]).map(row => row.path).sort();
            const actual = () => Probe.rows(view.model).map(row => row.path).sort();
            tryVerify(() => JSON.stringify(actual()) === JSON.stringify(expected), 2000, " gate 5 table follows selector and retains shared structure in " + data.mode);
        });
        project.analysis.fittingMode = "joint";
        tryVerify(() => Probe.rows(view.model).length === allRows.length, 2000, " gate 5 switching back to joint restores all experiment rows");
    }
    function test_count_consumers_follow_selection_data() {
        const result = [];
        ["joint", "sequential", "independent"].forEach(mode => {
            [0, 1].forEach(start => result.push({
                    tag: mode + "-from-" + start,
                    mode: mode,
                    start: start
                }));
        });
        return result;
    }
    function test_count_consumers_follow_selection(data) {
        const directory = "tests/fixtures/e04_t5/" + data.mode;
        const input = JSON.parse(Probe.readFile("tests/fixtures/e04_t5/counts.json"));
        compare(SymmetryOracle.sourceHash(directory + "/structures/lbco.edi"), input.structure.sha256, " F3 count oracle names the exact structure input");
        const freedom = SymmetryOracle.structure(directory);
        verify(freedom.length >= 6, " F3 independent crysta symmetry inventory is nonempty");
        const excluded = freedom.filter(row => !row.independent).map(key);
        const shared = input.structure.parameters.filter(row => !excluded.includes(key(row)));
        const names = ["hrpt", "second"];
        names.forEach(name => compare(SymmetryOracle.sourceHash(directory + "/experiments/" + name + ".edi"), input.experiments[name].sha256, " F3 count oracle names exact experiment input"));
        function counts(index) {
            let rows = shared.slice();
            names.forEach((name, bank) => {
                if (data.mode === "joint" || index === bank)
                    rows = rows.concat(input.experiments[name].parameters);
            });
            const free = rows.filter(row => row.free).length;
            return {
                total: rows.length,
                free: free,
                fixed: rows.length - free
            };
        }
        const first = input.experiments.hrpt.parameters;
        const second = input.experiments.second.parameters;
        verify(first.length !== second.length, " F3 fixtures require unequal inventories");
        verify(first.filter(row => row.free).length !== second.filter(row => row.free).length, " F3 fixtures require unequal free counts");
        Ui.click(test, Probe, appWindow, "appBar.tab.home");
        Ui.click(test, Probe, appWindow, "home.start");
        open(directory);
        const project = Session.project;
        project.analysis.fittingMode = "joint";
        project.currentExperimentIndex = data.start;
        project.analysis.fittingMode = data.mode;
        // Initial setup may edit the mode. From here on only selection and page
        // navigation occur; no edit, save or recalculation can repair the cache.
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        tryVerify(() => Ui.control(Probe, appWindow, "parameters.list") !== null, 2000, " F3 count check reaches the Analysis page consumer");
        const view = Ui.control(Probe, appWindow, "parameters.list");
        Ui.click(test, Probe, appWindow, "appBar.tab.report");
        tryVerify(() => Ui.control(Probe, appWindow, "report.text") !== null, 2000, " F3 rendered Report exists");
        const report = Ui.control(Probe, appWindow, "report.text");
        const status = Ui.control(Probe, appWindow, "statusBar.parameters");
        verify(status !== null, " F3 status parameter count consumer exists");
        verify(waitForRendering(appWindow.contentItem), " F3 setup finishes rendering before selection-only checks");
        const calculationWatch = Probe.watch(project);
        [data.start, 1 - data.start, data.start].forEach(index => {
            project.currentExperimentIndex = index;
            const expected = counts(index);
            const reason = " F3 " + data.mode + " selector " + index;
            const actual = () => Probe.rows(view.model);
            tryCompare(project.parameters, "count", expected.total, 2000, reason + " source total is declared inventory");
            compare(project.parameters.freeCount, expected.free, reason + " source free count is declared free flags");
            compare(project.parameters.fixedCount, expected.fixed, reason + " source fixed count is the complement");
            tryVerify(() => actual().length === expected.total, 2000, reason + " Analysis proxy total follows selection");
            compare(actual().filter(row => row.free).length, expected.free, reason + " Analysis proxy free count follows selection");
            const statusText = expected.total + " (" + expected.free + " free, " + expected.fixed + " fixed)";
            tryCompare(status, "valueText", statusText, 2000, reason + " rendered status counts follow selection");
            const reportText = expected.total + " (free " + expected.free + ", fixed " + expected.fixed + ")";
            tryVerify(() => Probe.plainText(project.report.richText).includes(reportText), 2000, reason + " cached Report counts follow selection");
            tryVerify(() => Probe.plainText(report.text).includes(reportText), 2000, reason + " rendered Report counts follow selection");
        });
        const events = Probe.events(calculationWatch);
        verify(!events.recalculated || events.recalculated.length === 0, " F3 selection counts refresh without an intervening recalculation");
    }
}
