import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "BulkFilterMembership"
    when: windowShown
    property var appWindow
    property var expected
    property bool savedSetup
    property var directory
    Component {
        id: application
        Main {}
    }
    function init() {
        Session.closeProject();
        savedSetup = Preferences.analysisShowFixedSettings;
        Preferences.analysisShowFixedSettings = false;
        expected = JSON.parse(Probe.readFile("tests/fixtures/analysis_filters/expected.json"));
        directory = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/analysis_filters/project"));
        verify(Session.openProject(directory), "The bulk membership oracle loads the authored two-structure two-experiment project");
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Bulk membership checks host the actual application window");
        appWindow.width = 1300;
        appWindow.height = 1000;
        verify(waitForRendering(appWindow.contentItem), "The bulk membership window renders before user selections");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1, 3000, "Analysis reaches the visible viewport before bulk actions");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        const observed = parameters();
        compare(observed.map(key).sort(), expected.map(key).sort(), "The authored project independently accounts for the complete mutable parameter inventory");
        verify(observed.every(parameter => parameter.fittable === !expected.find(row => key(row) === key(parameter)).blocked), "The P1 fixture admits every independent fit parameter and blocks each saved setup value");
    }
    function cleanup() {
        Session.closeProject();
        Preferences.analysisShowFixedSettings = savedSetup;
        appWindow.destroy();
        appWindow = null;
        Probe.releaseScratchProjects();
    }
    function control(name) {
        const item = Ui.find(Ui.page(appWindow), name, true);
        verify(item !== null, "Bulk membership input reaches the actual " + name + " control");
        return item;
    }
    function key(row) {
        if (row.uid !== undefined) {
            const parts = String(row.uid).split(".");
            return [row.blockKind, row.blockName, parts[0], row.rowLabel, parts[1]].join("/");
        }
        return [row.kind, row.block, row.category, row.label, row.name].join("/");
    }
    function parameters() {
        return Probe.rows(Session.project.parameters).map(row => row.parameter);
    }
    function snapshot() {
        const result = {};
        for (const item of parameters())
            result[key(item)] = {
                free: item.free,
                value: item.value
            };
        return result;
    }
    function same(actual, wanted) {
        return JSON.stringify(Object.keys(actual).sort().map(id => [id, actual[id].free, actual[id].value])) === JSON.stringify(Object.keys(wanted).sort().map(id => [id, wanted[id].free, wanted[id].value]));
    }
    function choose(name, caption) {
        const picker = control(name);
        let index = -1;
        for (let i = 0; i < picker.count; ++i) {
            const title = typeof picker.model[i] === "string" ? picker.model[i] : picker.model[i].title;
            if (String(title).replace(/\s*\(\d+\)$/, "") === caption)
                index = i;
        }
        verify(index >= 0, "The user's independent filter choice exists in the real selector");
        Ui.scrollIntoView(picker);
        verify(waitForPolish(appWindow.contentItem), "Filter pointer geometry settles before opening its menu");
        const point = Ui.clickPoint(picker);
        verify(point !== null, "The filter selector has an exposed pointer target");
        mouseClick(picker, point.x, point.y);
        tryVerify(() => picker.popup.visible, 1000, "A real pointer click opens the selected filter menu");
        const list = picker.popup.contentItem;
        list.positionViewAtIndex(index, ListView.Contain);
        verify(waitForPolish(list), "The selected filter entry finishes actual layout");
        const entry = list.itemAtIndex(index);
        verify(entry !== null, "The selected filter has an instantiated menu delegate");
        mouseClick(entry, entry.width / 2, entry.height / 2);
        tryVerify(() => !picker.popup.visible, 1000, "A real filter choice closes its menu before the next action");
        compare(picker.currentIndex, index, "The selected filter reaches the actual production selector");
    }
    function popup() {
        const header = control("parameters.freeHeader");
        Ui.scrollIntoView(header);
        verify(waitForPolish(appWindow.contentItem), "The bulk header finishes layout before pointer input");
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "The real bulk header reaches a rendered frame");
        const point = Ui.clickPoint(header);
        verify(point !== null, "The bulk header remains an exposed pointer target");
        mouseClick(header, point.x, point.y);
        let menu = null;
        tryVerify(() => {
            menu = Probe.objectsWithProperty(header, "shown").find(item => item.visible && item.contentItem !== undefined);
            return menu !== undefined;
        }, 1000, "The actual header interaction opens its own production bulk menu");
        verify(waitForPolish(menu.contentItem), "The actual bulk menu finishes binding and layout before inspecting its state");
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "The opened bulk menu reaches a settled rendered frame before its captions are checked");
        return menu;
    }
    function radio(menu, state) {
        const item = Ui.find(menu.contentItem, "parameters.freeHeader." + state, true);
        verify(item !== null, "The bulk popup exposes the independently requested state action");
        return item;
    }
    function targets(state) {
        return expected.filter(row => !row.blocked && (!state.block || row.block === state.block) && (!state.peak || row.category === "peak") && (!state.query || row.name.startsWith("broad_gauss"))).map(key).sort();
    }
    function test_membership_data() {
        const cases = [];
        for (const transition of ["all-east", "east-all", "east-west", "west-east", "clear-all", "replace-same-free-count"])
            for (const makeFree of [true, false])
                cases.push({
                    tag: transition + "-" + (makeFree ? "Free" : "Fixed"),
                    transition,
                    makeFree
                });
        return cases;
    }
    function test_membership(data) {
        const project = Session.project;
        const original = parameters();
        verify(project.setParametersFree(original.filter(item => item.fittable), !data.makeFree), "The authored target state supplies a genuine opposite-state bulk transition");
        if (data.transition === "east-west" || data.transition === "west-east") {
            const first = data.transition === "east-west" ? "east" : "west";
            verify(project.setParametersFree(original.filter(item => item.blockName === first && item.category === "peak"), data.makeFree), "Equal-size banks start in opposite free states before a datablock-only switch");
        }
        if (data.transition === "replace-same-free-count") {
            verify(project.setParametersFree(original.filter(item => item.blockName === "west"), false), "The replaced bank starts fixed so its removal does not change the project's free count");
        }
        choose("parameters.category", data.transition === "replace-same-free-count" ? "All categories" : "Peak profile");
        const state = {
            block: "",
            peak: data.transition !== "replace-same-free-count",
            query: ""
        };
        if (["east-all", "east-west", "clear-all"].includes(data.transition))
            state.block = "east";
        else if (data.transition === "west-east")
            state.block = "west";
        if (state.block)
            choose("parameters.datablock", state.block);
        if (data.transition === "clear-all") {
            choose("parameters.variability", data.makeFree ? "Fixed parameters" : "Free parameters");
            const name = control("parameters.nameFilter");
            Ui.scrollIntoView(name);
            const namePoint = Ui.clickPoint(name);
            verify(namePoint !== null, "The reset witness exposes the real name editor before typing");
            mouseClick(name, namePoint.x, namePoint.y);
            appWindow.requestActivate();
            name.forceActiveFocus();
            tryCompare(name, "activeFocus", true, 2000, "The reset witness focuses the actual name editor before sending text");
            verify(SettingsProof.type(name, "broad_gauss"), "The reset witness enters the fourth filter through the actual name editor");
            state.query = "broad_gauss";
        }
        const beforePrime = snapshot();
        const primed = popup();
        primed.close();
        compare(same(snapshot(), beforePrime), true, "Priming and closing the old menu preserves every parameter before the filter transition");
        const originalCategory = control("parameters.list").sourceModel.categoryFilter;
        if (data.transition === "all-east" || data.transition === "west-east") {
            state.block = "east";
            choose("parameters.datablock", "east");
        } else if (data.transition === "east-all") {
            state.block = "";
            choose("parameters.datablock", "All datablocks");
        } else if (data.transition === "east-west") {
            state.block = "west";
            choose("parameters.datablock", "west");
        } else if (data.transition === "clear-all") {
            Ui.click(test, Probe, appWindow, "parameters.clearFilters");
            state.block = "";
            state.peak = false;
            state.query = "";
            compare(control("parameters.datablock").currentIndex, 0, "Clearing all filters restores every authored datablock");
            compare(control("parameters.category").currentIndex, 0, "Clearing all filters restores every authored category");
            compare(control("parameters.variability").currentIndex, 0, "Clearing all filters restores both parameter states");
            compare(control("parameters.nameFilter").text, "", "Clearing all filters removes the actual name query");
        } else {
            const freeCount = project.parameters.freeCount;
            const west = SettingsProof.text(directory, "experiments/west.edi");
            const north = west.replace("data_west", "data_north").replace(/\([^)]*\)/g, "");
            verify(SettingsProof.write(directory, "north.edi", north), "The replacement bank is an authored fixed copy with a new independent identity");
            const index = Probe.rows(project.experiments).findIndex(row => row.name === "west");
            verify(index >= 0, "The structural replacement addresses the independently named west bank");
            project.removeExperiment(index);
            compare(project.parameters.freeCount, freeCount, "Removing a fixed bank leaves the project's free count unchanged");
            verify(project.loadExperiments([Qt.resolvedUrl(directory + "/north.edi")]), "The public loader installs the independently authored replacement bank");
            compare(project.parameters.freeCount, freeCount, "Replacing bank membership leaves the project's total free count unchanged");
            expected = expected.map(row => row.block === "west" ? Object.assign({}, row, {
                    block: "north",
                    free: false
                }) : row);
            compare(parameters().map(key).sort(), expected.map(key).sort(), "Replacement retains the authored inventory with only the intended bank identity changed");
        }
        if (data.transition !== "clear-all")
            compare(control("parameters.list").sourceModel.categoryFilter, originalCategory, "The membership transition leaves the category unchanged instead of refreshing through another filter");
        if (data.transition !== "replace-same-free-count")
            compare(same(snapshot(), beforePrime), true, "Changing only user filters preserves every free flag and value before applying the bulk action");
        const wanted = targets(state);
        const shown = Probe.rows(control("parameters.list").sourceModel).map(row => key(row.parameter)).sort();
        compare(shown, wanted, "The user's selections independently predict every visible parameter identity");
        verify(wanted.length > 0, "The independent current selection supplies a nonempty bulk target set");
        if (data.transition === "east-west" || data.transition === "west-east")
            compare(wanted.length, expected.filter(row => !row.blocked && row.block === (state.block === "east" ? "west" : "east") && row.category === "peak").length, "The bank-switch control replaces identities while retaining exactly the same target count");
        const before = snapshot();
        const after = JSON.parse(JSON.stringify(before));
        wanted.forEach(id => after[id].free = data.makeFree);
        verify(!same(before, after), "The chosen bulk action must change at least one independently predicted target");
        const failures = [];
        const menu = popup();
        const free = wanted.filter(id => before[id].free).length;
        const fixed = wanted.length - free;
        const freeAction = radio(menu, "free"), fixedAction = radio(menu, "fixed"), mixed = radio(menu, "mixed");
        if (freeAction.text !== "Free · all " + wanted.length || fixedAction.text !== "Fixed · all " + wanted.length || mixed.text !== "Mixed · " + free + " free · " + fixed + " fixed")
            failures.push("menu state describes stale membership: " + [freeAction.text, fixedAction.text, mixed.text].join(" / ") + " expected " + wanted.length + " targets, " + free + " free, " + fixed + " fixed");
        const isMixed = free > 0 && fixed > 0;
        if (freeAction.checked !== (fixed === 0) || fixedAction.checked !== (free === 0) || mixed.checked !== isMixed || mixed.enabled !== isMixed || mixed.checkable)
            failures.push("menu selected state describes stale filter members");
        const action = data.makeFree ? freeAction : fixedAction;
        mouseClick(action, action.width / 2, action.height / 2);
        verify(waitForPolish(appWindow.contentItem), "The actual bulk menu action finishes its ordinary publication");
        if (!same(snapshot(), after))
            failures.push("bulk action changes the wrong flags or hidden values");
        if (menu.visible)
            menu.close();
        Ui.click(test, Probe, appWindow, "appBar.button.undo");
        if (!same(snapshot(), before))
            failures.push("one Undo fails to restore every target and hidden parameter");
        compare(failures, [], "Menu state, Free or Fixed and one Undo follow only the independent current filter membership: " + failures.join("; "));
    }
}
