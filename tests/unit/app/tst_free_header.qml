import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "FilteredFreeHeader"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "The free-header actor requires the production window");
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "The free-header witness must open independently committed input");
        verify(waitForRendering(appWindow.contentItem), "The free-header window must render before input");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        Ui.expandGroup(test, Probe, appWindow, "group.parameters");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
    }
    function allParameters() {
        return Probe.rows(Session.project.parameters).map(row => row.parameter);
    }
    function snapshot(parameters) {
        return JSON.stringify(parameters.map(parameter => [parameter.path, parameter.free, parameter.value]));
    }
    function popup() {
        const header = Ui.control(Probe, appWindow, "parameters.freeHeader");
        verify(header !== null && Ui.exposed(header), "The free title must be a visible real right-click target");
        const point = Ui.clickPoint(header);
        mouseClick(header, point.x, point.y, Qt.RightButton);
        let menu;
        tryVerify(() => {
            menu = Probe.visiblePopups(appWindow).find(item => item.shown !== undefined);
            return menu !== undefined;
        }, 2000, "Right-clicking the free title must open the radio menu");
        const text = Ui.text(menu.contentItem);
        verify(text.includes("Free · " + menu.shown.length + " shown parameters"), "The popup title must name the exact shown parameter count");
        verify(text.includes("Applies to the rows the filters show. Undo with Ctrl+Z."), "The popup must explain its filter scope and undo action");
        verify(text.includes("all " + menu.shown.length), "Free and Fixed must show their complete target counts");
        return menu;
    }
    function radio(menu, suffix) {
        const item = Ui.find(menu.contentItem, "parameters.freeHeader." + suffix);
        verify(item !== null, "The popup must expose the requested state radio");
        return item;
    }
    function test_filtered_batch_data() {
        return [
            {
                tag: "name",
                filter: "name"
            },
            {
                tag: "category",
                filter: "category"
            },
            {
                tag: "combined",
                filter: "combined"
            }
        ];
    }
    function test_filtered_batch(data) {
        const parameters = allParameters();
        const target = parameters.filter(parameter => parameter.category === "cell" && parameter.fittable && parameter.refinable);
        verify(target.length >= 2, "The independent cell fixture must reach several mutable rows");
        target.forEach((parameter, index) => parameter.free = index % 2 === 0);
        const sentinel = parameters.find(parameter => parameter.category !== "cell" && parameter.fittable && parameter.refinable);
        verify(sentinel !== undefined, "A hidden parameter must witness filter isolation");
        // An independent value edit makes a two-step undo detectable.
        const oldValue = sentinel.value;
        sentinel.value = oldValue + 0.125;
        const before = snapshot(parameters);
        const list = Ui.control(Probe, appWindow, "parameters.list");
        verify(list !== null, "The real parameter table must expose its filter model");
        if (data.filter !== "category") {
            const field = Ui.control(Probe, appWindow, "parameters.nameFilter");
            verify(field !== null, "The real name filter must be exposed before typing");
            mouseClick(field);
            keyClick(Qt.Key_A, Qt.ControlModifier);
            for (const character of "length")
                keyClick(character.toUpperCase().charCodeAt(0));
        }
        if (data.filter !== "name")
            list.sourceModel.categoryFilter = "cell";
        const menu = popup();
        const shown = menu.shown.slice();
        verify(shown.length >= 2 && shown.length < parameters.length, "Each filter witness must show a proper multi-row subset");
        const free = shown.filter(parameter => parameter.free).length;
        const fixed = shown.length - free;
        verify(free > 0 && fixed > 0, "The initial shown subset must be mixed");
        verify(Ui.text(menu.contentItem).includes(free + " free · " + fixed + " fixed"), "Mixed must display both exact state counts");
        const mixed = radio(menu, "mixed");
        verify(mixed.checked && mixed.enabled && !mixed.checkable, "Mixed must be preselected and unselectable when both states occur");
        mouseClick(mixed);
        compare(snapshot(parameters), before, "Clicking Mixed must never mutate a shown or hidden parameter");
        const chooseFree = radio(menu, "free");
        verify(!chooseFree.checked && !radio(menu, "fixed").checked, "Only Mixed must be preselected for mixed rows");
        mouseClick(chooseFree);
        verify(shown.every(parameter => parameter.free), "Free must change every shown row in the batch");
        const hidden = parameters.filter(parameter => !shown.includes(parameter));
        const oldRows = JSON.parse(before);
        hidden.forEach(parameter => compare(parameter.free, oldRows.find(row => row[0] === parameter.path)[1], "The name and category filters must leave every hidden row untouched"));
        compare(sentinel.value, oldValue + 0.125, "A batch free edit must preserve earlier parameter values");
        Session.project.undo();
        compare(snapshot(parameters), before, "One Undo must restore every shown free flag and all hidden parameter state");
        // The next Undo must consume the sentinel, proving the batch used exactly one history record.
        Session.project.undo();
        compare(sentinel.value, oldValue, "The second Undo must restore the independent prior value edit");
        const hiddenBeforeFixed = snapshot(hidden);
        const again = popup();
        mouseClick(radio(again, "fixed"));
        verify(shown.every(parameter => !parameter.free), "Fixed must change every shown row in the batch");
        compare(snapshot(hidden), hiddenBeforeFixed, "Fixed must preserve every hidden row and value");
        const allFixed = popup();
        verify(radio(allFixed, "fixed").checked && !radio(allFixed, "mixed").enabled, "All-fixed rows must preselect Fixed and grey out Mixed");
        mouseClick(radio(allFixed, "free"));
        compare(snapshot(hidden), hiddenBeforeFixed, "Free from Fixed must preserve every hidden row and value");
        const allFree = popup();
        verify(radio(allFree, "free").checked && !radio(allFree, "mixed").enabled, "All-free rows must preselect Free and grey out Mixed");
        allFree.close();
        Session.project.undo();
        verify(shown.every(parameter => !parameter.free), "One Undo must restore the complete Fixed batch after Free");
    }
    function test_empty_filter_has_no_batch() {
        const field = Ui.control(Probe, appWindow, "parameters.nameFilter");
        verify(field !== null, "The empty-row witness requires the real name filter");
        mouseClick(field);
        for (const character of "zzzzmissing")
            keyClick(character.toUpperCase().charCodeAt(0));
        const before = snapshot(allParameters());
        const menu = popup();
        compare(menu.shown.length, 0, "An unmatched filter must produce exactly zero popup targets");
        ["free", "fixed", "mixed"].forEach(state => {
            const item = radio(menu, state);
            verify(!item.checked && !item.enabled, "An empty subset must disable and deselect every state radio");
        });
        compare(snapshot(allParameters()), before, "Opening an empty-subset popup must preserve the whole project");
        menu.close();
    }
}
