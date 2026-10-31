import QtQuick
import QtTest
import EasyApplication.Gui.Style as EaStyle
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "FilteredFreeHeader"
    when: windowShown
    property var appWindow
    property real filterRowHeight: 0
    Component {
        id: application
        Main {}
    }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "The free-header actor requires the production window");
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment")), "The free-header witness must open independently committed input");
        verify(waitForRendering(appWindow.contentItem), "The free-header window must render before input");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        Ui.expandGroup(test, Probe, appWindow, "group.parameters");
        const picker = Ui.control(Probe, appWindow, "parameters.category");
        verify(picker !== null, "The spacing witness requires the actual category filter");
        Ui.click(test, Probe, appWindow, "parameters.category");
        let listRow;
        tryVerify(() => {
            listRow = Ui.itemsWithProperty(picker.popup.contentItem, "modelData").find(item => item.modelData.title !== undefined && item.height > 0 && item.topPadding !== undefined);
            return listRow !== undefined;
        }, 2000, "The category dropdown must instantiate its actual padded list delegate");
        filterRowHeight = listRow.height;
        picker.popup.close();
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
    function popup(emptyController = false) {
        const header = Ui.control(Probe, appWindow, "parameters.freeHeader");
        verify(header !== null && Ui.exposed(header), "The free title must be a visible real left-click target");
        const point = Ui.clickPoint(header);
        mouseMove(header, point.x, point.y);
        tryCompare(header, "color", EaStyle.Colors.themeAccent, 2000, "Hover must accent the actual free header");
        if (emptyController) {
            // The empty model has no batch target. Check its actual menu state;
            // nonempty actors separately exercise the real header's mouse route.
            const declared = Probe.objectsWithProperty(appWindow, "shown").find(item => item.freeCount !== undefined && item.fixedCount !== undefined);
            verify(declared !== undefined, "The empty subset must retain its production radio-menu controller");
            declared.open();
        } else {
            mouseClick(header, point.x, point.y, Qt.LeftButton);
        }
        let menu;
        tryVerify(() => {
            menu = Probe.visiblePopups(appWindow).find(item => item.shown !== undefined);
            return menu !== undefined;
        }, 2000, "Left-clicking the free title must open the radio menu");
        tryVerify(() => {
            const centre = menu.parent.mapToItem(appWindow.contentItem, menu.x + menu.width / 2, menu.y + menu.height / 2);
            return Math.abs(centre.x - appWindow.contentItem.width / 2) <= 1 && Math.abs(centre.y - appWindow.contentItem.height / 2) <= 1;
        }, 2000, "The free-column menu opens at the centre of the app window in both axes");
        const text = Ui.text(menu.contentItem);
        verify(!text.includes("shown parameters") && !text.includes("Applies to"), "The lean popup must contain neither the retired title nor footer");
        const buttons = ["free", "fixed", "mixed"].map(state => radio(menu, state));
        const layout = buttons[0].parent;
        const margin = menu.rightPadding + layout.rightPadding;
        compare(menu.leftPadding + layout.leftPadding, margin, "The popup's left inner margin must equal its right margin");
        compare(menu.topPadding + layout.topPadding, margin, "The popup's top inner margin must equal its right margin");
        compare(menu.bottomPadding + layout.bottomPadding, margin, "The popup's bottom inner margin must equal its right margin");
        buttons.forEach((button, index) => {
            const expected = index === 2 ? "Mixed · " + menu.freeCount + " free · " + menu.fixedCount + " fixed" : (index === 0 ? "Free" : "Fixed") + " · all " + menu.shown.length;
            compare(button.text, expected, "Every popup radio row must render one exact state/count text with one space around each dot");
            if (index > 0) {
                const pitch = button.mapToItem(layout, 0, button.height / 2).y - buttons[index - 1].mapToItem(layout, 0, buttons[index - 1].height / 2).y;
                compare(pitch, filterRowHeight, "Popup row centres must retain the actual filter dropdown row pitch");
            }
        });
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
        appWindow.width = data.filter === "name" ? 1200 : 1430;
        appWindow.height = data.filter === "combined" ? 930 : 1000;
        verify(waitForPolish(appWindow.contentItem), "Window resizing settles before opening the centred free menu");
        const parameters = allParameters();
        const target = parameters.filter(parameter => parameter.category === "cell" && parameter.fittable && parameter.refinable);
        verify(target.length >= 2, "The independent cell fixture must reach several mutable rows");
        target.forEach((parameter, index) => parameter.free = index % 2 === 0);
        const sentinel = parameters.find(parameter => parameter.category !== "cell" && parameter.fittable && parameter.refinable);
        verify(sentinel !== undefined, "A hidden parameter must witness filter isolation");
        // An independent value edit makes a two-step undo detectable.
        const oldValue = sentinel.value;
        sentinel.value = oldValue + 0.125;
        const oldFree = sentinel.free;
        verify(Session.project.setParametersFree([sentinel], !oldFree), "The prior independent hidden-row batch must be undoable");
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
        // A scalar value edit need not be undoable; the prior explicit free batch is.
        // The next Undo reaches that independent record, detecting a duplicate batch record.
        Session.project.undo();
        compare(sentinel.free, oldFree, "The second Undo must reach the independent prior hidden-row batch");
        compare(sentinel.value, oldValue + 0.125, "Undoing free batches must preserve the independent prior value edit");
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
        const menu = popup(true);
        compare(menu.shown.length, 0, "An unmatched filter must produce exactly zero popup targets");
        ["free", "fixed", "mixed"].forEach(state => {
            const item = radio(menu, state);
            verify(!item.checked && !item.enabled, "An empty subset must disable and deselect every state radio");
        });
        compare(snapshot(allParameters()), before, "Opening an empty-subset popup must preserve the whole project");
        menu.close();
    }
}
