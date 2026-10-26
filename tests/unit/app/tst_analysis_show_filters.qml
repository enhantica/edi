import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui
import "E04Review.js" as View
import "AnalysisShowFilters.js" as Show

TestCase {
    id: test
    name: "AnalysisShowFilters"
    when: windowShown
    property var appWindow
    property var filter
    property var savedStates
    Component {
        id: application
        ApplicationWindow {
            width: 1300
            height: 1000
            visible: true
            property alias analysisPage: analysisPage
            AnalysisPage {
                id: analysisPage
                anchors.fill: parent
                current: true
            }
        }
    }
    function init() {
        Session.closeProject();
        savedStates = null;
        filter = null;
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Analysis show-filters are exercised in the production application");
        appWindow.width = 1300;
        appWindow.height = 1000;
        verify(waitForRendering(appWindow.contentItem), "The actual application renders before show-filter input");
    }
    function cleanup() {
        if (savedStates) {
            tab("settings");
            Show.choose(test, appWindow.analysisPage, savedStates);
        }
        Session.closeProject();
        appWindow.destroy();
        appWindow = null;
        Probe.releaseScratchProjects();
    }
    function tab(name) {
        const control = Ui.find(appWindow.analysisPage, "sideBar.tab." + name, true);
        verify(control !== null && control.enabled, "Analysis exposes the actual " + name + " sidebar tab");
        const hit = Ui.clickPoint(control);
        verify(hit !== null, "The Analysis sidebar tab accepts actual pointer input");
        mouseClick(control, hit.x, hit.y);
        tryCompare(control, "checked", true, 1000, "Pointer input selects the requested actual Analysis tab");
        verify(waitForPolish(appWindow.contentItem), "The selected actual Analysis tab finishes layout");
        verify(waitForRendering(appWindow.contentItem), "The selected actual Analysis tab reaches a rendered frame");
        tryVerify(() => !Ui.moving(appWindow.analysisPage), 1000, "The Analysis sidebar finishes its tab movement before further pointer input");
        if (name === "basic")
            tryVerify(() => Ui.find(appWindow.analysisPage, "parameters.list", true) !== null, 2000, "The production parameter table finishes sliding into the Main sidebar viewport");
    }
    function open(name) {
        verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/fittability/projects/" + name))), "The independent show-filter fixture loads through the actual app");
        tab("basic");
        const table = Ui.find(appWindow.analysisPage, "parameters.list", true);
        verify(table !== null, "The Analysis page owns the actual parameter filter model");
        filter = table.sourceModel;
        tab("settings");
    }
    function boxes() {
        const result = Show.controls(test, appWindow.analysisPage);
        if (!savedStates)
            savedStates = result.map(box => box.checked);
        return result;
    }
    function set(states) {
        boxes();
        Show.choose(test, appWindow.analysisPage, states);
        verify(waitForPolish(appWindow.contentItem), "The show-filter change finishes actual layout");
    }
    function ids(model) {
        return Probe.rows(model).map(Show.key).sort();
    }
    function exact(expected, states, freeIds) {
        compare(ids(filter), Show.shown(expected, states, freeIds), "The view model selects exactly the independent requested reason groups and all fittable or free-marked inputs");
        compare(ids(Session.project.parameters), expected.map(row => row.id).sort(), "View filtering preserves every numerical input in the unfiltered project model");
    }
    function counts(expected, freeIds) {
        const controls = boxes();
        Show.expand(test, controls);
        controls.forEach((box, group) => {
            const match = String(box.text).match(/\((\d+)\)$/);
            verify(match !== null, "Every show-checkbox label ends with the number of rows it adds");
            const wanted = expected.filter(row => row.group === group && !(freeIds || []).includes(row.id)).length;
            compare(Number(match[1]), wanted, "Show-group counts come from the independent blockers and exclude rows already kept by their free flags");
        });
    }
    function test_defaults_and_grid() {
        open("cubic-constrained");
        const controls = boxes();
        compare(controls.map(box => box.checked), Show.defaults, "Not measured and Fixed settings default on; symmetry and constraint default off");
        const actual = View.descendants(appWindow.analysisPage).filter(item => typeof item.text === "string" && typeof item.checked === "boolean" && /^(Can be fitted|Not measured in this fit|Fixed by symmetry|Set by a constraint|Fixed settings)(\s|$)/.test(item.text));
        compare(actual.length, 4, "The always-included fittable group has no fifth checkbox");
        const at = controls.map(box => box.mapToItem(appWindow.contentItem, 0, 0));
        fuzzyCompare(at[0].y, at[1].y, 0.5, "The first two show-checkboxes share the first grid row");
        fuzzyCompare(at[2].y, at[3].y, 0.5, "The last two show-checkboxes share the second grid row");
        verify(at[2].y > at[0].y && at[0].x < at[1].x, "The show groups form the requested row-major 2 by 2 grid");
        fuzzyCompare(at[0].x, at[2].x, 0.5, "Both first-column cells share the same left edge");
        fuzzyCompare(at[1].x, at[3].x, 0.5, "Both second-column cells share the same left edge");
        controls.forEach(box => fuzzyCompare(box.width, controls[0].width, 0.5, "Every show-filter cell has equal width"));
        const expected = Show.inventory(true, true);
        exact(expected, Show.defaults);
        counts(expected);
    }
    function test_every_combination_data() {
        const fixtures = [
            {
                tag: "triclinic",
                project: "single",
                cubic: false,
                constrained: false
            },
            {
                tag: "cubic-constraint",
                project: "cubic-constrained",
                cubic: true,
                constrained: true
            }
        ];
        const cases = [];
        for (const fixture of fixtures)
            for (const first of [0, 4, 8, 12])
                cases.push(Object.assign({}, fixture, {
                    tag: fixture.tag + "-" + first,
                    first: first
                }));
        return cases;
    }
    function test_every_combination(data) {
        open(data.project);
        const expected = Show.inventory(data.cubic, data.constrained);
        for (let mask = data.first; mask < data.first + 4; ++mask) {
            const states = [0, 1, 2, 3].map(bit => !!(mask & (1 << bit)));
            set(states);
            exact(expected, states);
            counts(expected);
        }
    }
    function test_view_model_intersections_and_reset() {
        open("cubic-constrained");
        const expected = Show.inventory(true, true);
        set([false, true, false, false]);
        filter.datablockFilter = "structure:phase";
        filter.categoryFilter = "cell";
        filter.nameFilter = "length";
        compare(ids(filter), ["phase.cell.length_b", "phase.cell.length_c"], "The reason selection intersects datablock, category and name filters in the actual proxy");
        compare(filter.parameterAt(0), Probe.rows(filter)[0].parameter, "The proxy maps a shown blocked input back to its real project parameter");
        filter.variability = ParameterFilterModel.NotFittable;
        compare(ids(filter), ["phase.cell.length_b", "phase.cell.length_c"], "Not fittable keeps only the blocked rows admitted by the show groups");
        filter.clearFilters();
        exact(expected, [false, true, false, false]);
        compare(boxes().map(box => box.checked), [false, true, false, false], "Clearing table search filters preserves the user's saved show-group choices");
        compare(Array.from(filter.variabilityCounts), [11, 0, 3, 8], "The variability counts partition the admitted fittable and symmetry-held rows");
    }
    function test_labels_follow_context_and_free_override() {
        open("mixed");
        const cell = Probe.rows(Session.project.parameters).find(row => Show.key(row) === "phase.cell.length_a").parameter;
        cell.free = true;
        compare(cell.free, true, "The powder experiment initially permits the shared independent cubic length to be free");
        set([false, false, false, false]);
        const powder = Probe.rows(Session.project.experiments).findIndex(row => row.name === "powder");
        verify(powder >= 0, "The context-change witness contains its authored powder experiment");
        Session.project.removeExperiment(powder);
        const expected = Show.inventory(true, false);
        exact(expected, [false, false, false, false], ["phase.cell.length_a"]);
        counts(expected, ["phase.cell.length_a"]);
        compare(cell.fittable, false, "Removing powder recomputes the rule's data blocker without clearing the free flag");
        tab("basic");
        const table = Ui.find(appWindow.analysisPage, "parameters.list", true);
        const index = ids(filter).indexOf("phase.cell.length_a");
        const rows = Probe.rows(filter);
        const shownIndex = rows.findIndex(row => Show.key(row) === "phase.cell.length_a");
        verify(index >= 0 && shownIndex >= 0, "A blocked free-marked value remains available with every show group off");
        table.positionViewAtIndex(shownIndex, ListView.Contain);
        verify(waitForPolish(table), "The surviving free-marked row gets an actual delegate");
        const checkbox = Ui.find(appWindow.analysisPage, "parameters.free." + shownIndex, true);
        verify(checkbox !== null && checkbox.checked && checkbox.enabled, "A blocked free-marked row exposes an enabled Free control so it can be cleared");
        Ui.scrollIntoView(checkbox);
        const hit = Ui.clickPoint(checkbox);
        verify(hit !== null, "The surviving free flag can be cleared through actual pointer input");
        mouseClick(checkbox, hit.x, hit.y);
        tryVerify(() => !cell.free && !ids(filter).includes("phase.cell.length_a"), 1000, "Clearing the stale free flag removes the now-unselected data-blocked row");
        tab("settings");
        counts(expected);
        set([true, false, false, false]);
        exact(expected, [true, false, false, false]);
    }
    function test_preferences_survive_a_fresh_engine_and_another_project() {
        open("cubic-constrained");
        const wanted = [false, true, true, false];
        set(wanted);
        const code = 'import QtQuick; import edi.app; QtObject { property string states: JSON.stringify([' + 'Preferences.analysisShowNotMeasured, Preferences.analysisShowBySymmetry, ' + 'Preferences.analysisShowByConstraint, Preferences.analysisShowFixedSettings]); }';
        let restored;
        tryVerify(() => {
            restored = SettingsProof.restart(code);
            return !restored.error && restored.states === JSON.stringify(wanted);
        }, 1000, "A fresh production QML engine reads all four user's show-group choices from the app settings");
        open("single");
        compare(boxes().map(box => box.checked), wanted, "Opening another project keeps the same per-user view choices");
        exact(Show.inventory(false, false), wanted);
    }
    function test_view_choices_preserve_project_bytes_and_flags() {
        open("cubic-constrained");
        const beforePath = Probe.scratchProjectUrl();
        verify(Session.saveAs(beforePath), "The byte witness first saves the actual unedited project");
        const modified = Session.project.modified;
        const before = Probe.rows(Session.project.parameters).map(row => [Show.key(row), row.value, row.free]);
        set([true, true, true, true]);
        set([false, false, false, false]);
        compare(Session.project.modified, modified, "Show-checkbox input never marks the project modified");
        compare(Probe.rows(Session.project.parameters).map(row => [Show.key(row), row.value, row.free]), before, "View choices preserve every input value and free flag");
        const afterPath = Probe.scratchProjectUrl();
        verify(Session.saveAs(afterPath), "The actual project still saves after changing every view choice");
        const first = SettingsProof.projectBytes(beforePath), second = SettingsProof.projectBytes(afterPath);
        verify(!first.error && !second.error && Object.keys(first).length > 0, "The byte observer reads the entire saved project tree");
        compare(JSON.stringify(second), JSON.stringify(first), "Show preferences add no project file, tag or changed byte; only project wall-clock metadata is normalized");
    }
}
