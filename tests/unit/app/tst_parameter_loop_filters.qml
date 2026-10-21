import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "ParameterLoopFilters"
    when: windowShown
    property var appWindow
    property var group
    Component { id: application; ApplicationWindow { width: 900; height: 700; visible: true } }
    Component { id: parameters; ParametersGroup { width: 720; y: 75; z: 1000; tableViewportHeight: 500 } }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Category-filter acceptance must host the production Analysis component in a real Qt window");
        verify(waitForRendering(appWindow.contentItem), "The category-filter window must render");
    }
    function cleanup() {
        if (group) group.destroy();group = null;
        Session.closeProject();appWindow.destroy();Probe.releaseScratchProjects();
    }
    function matches(row, key) {
        // The public field UID starts with its declared category, before any
        // row id. Do not trust the table category role the broken filter consumes.
        const category = String(row.parameter.uid).split(".")[0], leaf = String(row.name);
        if (!key) return true;
        if (key === "@structure" || key === "@experiment") return row.blockKind === key.slice(1);
        if (key === "@atoms") return category === "atom_site" || category === "atom_site_aniso";
        if (key === "@coordinates") return category === "atom_site" && leaf.startsWith("fract_");
        if (key === "@occupancies") return category === "atom_site" && leaf === "occupancy";
        if (key === "@displacement") return category === "atom_site_aniso" || category === "atom_site" && leaf.startsWith("adp_");
        if (key === "@peakBroadening") return category === "peak" && leaf.startsWith("broad_");
        if (key === "@peakMixing") return category === "peak" && leaf.startsWith("mixing_");
        if (key === "@peakAsymmetry") return category === "peak" && /^(asym_|rise_|decay_)/.test(leaf);
        verify(!key.startsWith("@"), "Every offered hierarchical category must have an explicit semantic expectation: " + key);
        return category === key;
    }
    function chooseCategory(picker, index) {
        Ui.scrollIntoView(picker);
        const point = Ui.clickPoint(picker);
        verify(point !== null, "The production category picker must accept actual pointer input");
        mouseClick(picker, point.x, point.y);
        tryVerify(() => picker.popup && picker.popup.visible, 500, "The real category menu must open");
        const list = picker.popup.contentItem;
        verify(typeof list.positionViewAtIndex === "function", "The actual category popup must expose its option list");
        list.positionViewAtIndex(index, ListView.Contain);
        verify(waitForPolish(list), "The requested real category delegate must finish layout");
        const entry = list.itemAtIndex(index);
        verify(entry !== null && String(entry.modelData.key) === String(picker.model[index].key),
               "The pointer target must be the actual requested category delegate, identified by its model key");
        const hit = Ui.clickPoint(entry);
        verify(hit !== null, "The requested real category entry must expose a clipped pointer target");
        mouseClick(entry, hit.x, hit.y);
        tryVerify(() => !picker.popup.visible, 500, "The real category selection must close its popup");
    }
    function exercise(kind, numeric, chunk) {
        const source = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/readonly-" + kind));
        if (numeric) {
            const text = SettingsProof.text(source, "experiments/bank.edi");
            verify(SettingsProof.write(source, "experiments/bank.edi", text.replace(/^r(\d+) /gm, (_, index) => String(Number(index) + 1) + " ")),
                   "The numeric-id control must change only authored background row identifiers");
        }
        verify(Session.openProject(source),
               "The category control must load actual typed parameter rows: " + kind);
        group = parameters.createObject(appWindow.contentItem, {project: Session.project});
        verify(group !== null, "The filter must be the actual Analysis Main ParametersGroup");
        verify(waitForPolish(group), "The actual Analysis category picker must finish layout");
        const table = Ui.find(group, "parameters.list", true);
        verify(table !== null && table.sourceModel !== null, "The Analysis table must expose its production filtered model");
        const filter = table.sourceModel, all = Probe.rows(Session.project.parameters);
        const picker = Ui.find(group, "parameters.category", true);
        verify(picker !== null, "Analysis Main must expose the actual parameters.category picker");
        verify(new Set(all.map(row => String(row.path))).size === all.length,
               "Unfiltered parameter paths must distinguish every actual row identity");
        const groups = filter.categoryGroups.slice();
        const background = all.filter(row => matches(row, "background"));
        const expectedCount = kind === "line-segment" ? 12 : kind === "polynomial" ? 6 : 8;
        compare(background.length, expectedCount, "The independent authored fixture must expose every background height or coefficient in All categories");
        verify(background.some(row => row.free) && background.some(row => !row.free),
               "The loop-category control must include both free and fixed parameters");
        verify(groups.some(item => item.key === "background"), "The actual category menu must offer its Background family");
        ["linked_structure", "preferred_orientation", "@atoms", "@displacement"].forEach(key =>
            verify(groups.some(item => item.key === key), "The class gate must reach actual links, texture, sites and anisotropic tensor parameters: " + key));
        const tensors = all.filter(row => matches(row, "atom_site_aniso"));
        verify(tensors.length >= 12, "The class gate must retain multiple real anisotropic tensor rows, not one synthetic scalar");
        const loopKeys = ["background", "linked_structure", "preferred_orientation", "scattering_length", "atom_site", "atom_site_aniso"];
        verify(groups.filter(item => loopKeys.indexOf(item.key) >= 0).length >= 3,
               "The class gate must reach background, links and at least one other real loop family");
        let visited = 0;
        groups.forEach((item, index) => {
            if (index % 3 !== chunk) return;
            visited++;
            const expected = all.filter(row => matches(row, item.key));
            compare(item.count, expected.length, "The offered category count must equal its full unfiltered parameter membership: " + item.key);
            chooseCategory(picker, index);
            compare(String(filter.categoryFilter), String(item.key),
                    "Activating each displayed category must select that exact public model key: " + item.key);
            [ParameterFilterModel.All, ParameterFilterModel.Free, ParameterFilterModel.Fixed].forEach(variability => {
                filter.variability = variability;
                const wanted = expected.filter(row => variability === ParameterFilterModel.All ||
                    (variability === ParameterFilterModel.Free ? row.free : !row.free));
                const observed = Probe.rows(filter);
                compare(JSON.stringify(observed.map(row => String(row.path)).sort()),
                        JSON.stringify(wanted.map(row => String(row.path)).sort()),
                        "Each category/variability filter must retain exactly the unfiltered row identities, without omissions or duplicates: " + item.key + "/" + variability);
            });
            filter.variability = ParameterFilterModel.All;
        });
        compare(visited, Math.floor((groups.length + 2 - chunk) / 3),
                "The three bounded cases must partition every offered category exactly once");
        verify(visited > 0, "Every bounded category case must exercise actual offered groups");
        chooseCategory(picker, 0);
        compare(Probe.rows(filter).length, all.length, "Returning to All categories must restore every public parameter row");
        console.log("PARAMETER_LOOP_FILTERS " + kind + " groups=" + groups.length + " background=" + expectedCount + " variability=all,free,fixed ids=" + (numeric ? "numeric" : "named") + " chunk=" + chunk + " checked=" + visited);
    }
    function hot(kind, example, automatic) {
        verify(Session.openExample(example), "The hot category control must load the actual published measured-data example: " + example);
        tryVerify(() => !Session.project.calculating, 1000,
                  "The actual example calculation must settle before replacing background rows");
        Session.project.currentExperiment.backgroundEstimateMode = "manual";
        group = parameters.createObject(appWindow.contentItem, {project: Session.project});
        verify(group !== null && waitForPolish(group), "The actual Analysis filter must exist before Estimate replaces its rows");
        const table = Ui.find(group, "parameters.list", true), picker = Ui.find(group, "parameters.category", true);
        verify(table !== null && picker !== null, "The pre-existing Analysis table and category picker must be real production controls");
        const filter = table.sourceModel;
        const experiment = Session.project.currentExperiment;
        const model = kind === "line-segment" ? experiment.background : experiment.backgroundTerms;
        function values() { return JSON.stringify(Probe.rows(model).map(row => kind === "line-segment" ?
            [row.id, row.position, row.intensity.value] : [row.id, row.order, row.coef.value])); }
        if (automatic) {
            const before = values();
            experiment.backgroundEstimateTolerance = 0.75;
            experiment.backgroundEstimateMode = "auto";
            tryVerify(() => !Session.project.calculating && !experiment.pattern.stale && values() !== before,
                      2000, "The real Auto worker must publish changed estimated rows into the already-open Analysis table");
        } else {
            verify(Session.project.estimateBackground(), "The real manual Estimate operation must replace the background in the published example");
        }
        const rows = Probe.rows(model);
        verify(rows.length >= 2, "The replacement witness must have multiple estimated heights or coefficients");
        if (!automatic) {
            const first = kind === "line-segment" ? rows[0].intensity : rows[0].coef;
            first.free = true;
            verify(first.free, "The Manual replacement control must expose a real free parameter alongside fixed estimated rows");
        }
        const all = Probe.rows(Session.project.parameters);
        const expected = all.filter(row => matches(row, "background"));
        compare(expected.length, rows.length, "All categories must contain every current estimated background parameter exactly once");
        const groups = filter.categoryGroups, index = groups.findIndex(item => item.key === "background");
        verify(index >= 0, "The pre-existing category picker must retain Background after row replacement");
        compare(groups[index].count, expected.length, "The refreshed Background menu count must match the actual replaced rows");
        chooseCategory(picker, index);
        [ParameterFilterModel.All, ParameterFilterModel.Free, ParameterFilterModel.Fixed].forEach(variability => {
            filter.variability = variability;
            const wanted = expected.filter(row => variability === ParameterFilterModel.All ||
                (variability === ParameterFilterModel.Free ? row.free : !row.free));
            compare(JSON.stringify(Probe.rows(filter).map(row => String(row.path)).sort()),
                    JSON.stringify(wanted.map(row => String(row.path)).sort()),
                    "After a real Estimate the already-open Background filter must retain every current all/free/fixed parameter identity");
        });
        console.log("PARAMETER_HOT_FILTER " + kind + " count=" + expected.length + " variability=all,free,fixed route=" + (automatic ? "auto" : "manual"));
    }
    function test_hot_points() { hot("line-segment", "pd-neut-cwl_cosio-d20_start-1"); }
    function test_hot_polynomial() { hot("polynomial", "pd-neut-tof_ceo2-pearl_polynomial"); }
    function test_hot_chebyshev() { hot("chebyshev", "pd-neut-tof_cecoal-polaris_chebyshev"); }
    function test_auto_points() { hot("line-segment", "pd-neut-cwl_cosio-d20_start-1", true); }
    function test_auto_polynomial() { hot("polynomial", "pd-neut-tof_ceo2-pearl_polynomial", true); }
    function test_auto_chebyshev() { hot("chebyshev", "pd-neut-tof_cecoal-polaris_chebyshev", true); }
    function test_points_0() { exercise("line-segment", false, 0); }
    function test_points_1() { exercise("line-segment", false, 1); }
    function test_points_2() { exercise("line-segment", false, 2); }
    function test_points_numeric_0() { exercise("line-segment", true, 0); }
    function test_points_numeric_1() { exercise("line-segment", true, 1); }
    function test_points_numeric_2() { exercise("line-segment", true, 2); }
    function test_polynomial_0() { exercise("polynomial", false, 0); }
    function test_polynomial_1() { exercise("polynomial", false, 1); }
    function test_polynomial_2() { exercise("polynomial", false, 2); }
    function test_polynomial_numeric_0() { exercise("polynomial", true, 0); }
    function test_polynomial_numeric_1() { exercise("polynomial", true, 1); }
    function test_polynomial_numeric_2() { exercise("polynomial", true, 2); }
    function test_chebyshev_0() { exercise("chebyshev", false, 0); }
    function test_chebyshev_1() { exercise("chebyshev", false, 1); }
    function test_chebyshev_2() { exercise("chebyshev", false, 2); }
    function test_chebyshev_numeric_0() { exercise("chebyshev", true, 0); }
    function test_chebyshev_numeric_1() { exercise("chebyshev", true, 1); }
    function test_chebyshev_numeric_2() { exercise("chebyshev", true, 2); }
}
