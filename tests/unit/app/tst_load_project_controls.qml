import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "LoadProjectControls"
    when: windowShown
    property var app: null
    Component {
        id: application
        Main {}
    }

    function normalized(text) {
        return text.replace(/(?:…|\.\.\.)$/, "");
    }

    function init() {
        failOnWarning(Probe.softwareOffscreenWithoutGl() ? /\A(?!(?:QRhiGles2: Failed to create (?:temporary context|context)|window doesn\x27t exist\.)\z)[\s\S]*\z/ : /.*/);
        Session.closeProject();
        app = application.createObject(null, {
            width: 1280,
            height: 800,
            visible: true
        });
        verify(app !== null, "The project entry controls run in the production Main window");
        app.requestActivate();
        tryCompare(app, "active", true, 2000, "Real input belongs to the active production window");
        Ui.click(test, Probe, app, "appBar.tab.home");
        Ui.click(test, Probe, app, "home.start");
        Ui.click(test, Probe, app, "appBar.tab.project");
    }

    function cleanup() {
        Probe.clearWatches();
        Session.closeProject();
        if (app) {
            app.close();
            app.destroy();
        }
        app = null;
    }

    function group() {
        const groups = Render.descendants(Ui.page(app)).filter(item => item.objectName === "group.getStarted");
        compare(groups.length, 1, "The actual Project page owns one Get started group");
        return groups[0];
    }

    function projectButtons() {
        return Render.descendants(group()).filter(item => String(item).includes("SideBarButton") && typeof item.text === "string" && item.visible);
    }

    function states() {
        return [
            {
                tag: "empty",
                loaded: false
            },
            {
                tag: "loaded",
                loaded: true
            }
        ];
    }

    function menuFrame(name) {
        const menu = findChild(app, name);
        verify(menu !== null, "The project popup exists before its geometry is read");
        tryCompare(menu, "opened", true, 2000, "The project popup finishes opening before its rows are ordered");
        verify(waitForPolish(menu.contentItem), "Registry-created menu rows finish layout before their positions are compared");
        app.update();
        verify(waitForRendering(app.contentItem), "The menu order is observed after an actual application frame");
    }

    function prepareState(data) {
        if (data.loaded) {
            verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"))), "The loaded-state check starts from an ordinary open project");
            Ui.click(test, Probe, app, "appBar.tab.project");
        }
    }

    function test_three_project_buttons_data() {
        return states();
    }

    function test_three_project_buttons(data) {
        prepareState(data);
        const buttons = projectButtons();
        compare(JSON.stringify(buttons.map(item => normalized(item.text))), JSON.stringify(["Create a new project", "Load project", "Save project as"]), "Get started shows the three requested actions, without the old import or URL buttons");
        for (const button of buttons) {
            Ui.scrollIntoView(button);
            verify(Ui.rendered(button), "Each project entry button is visibly available in its real sidebar");
        }
    }

    function test_load_project_opens_the_ordered_choices_data() {
        return states();
    }

    function test_load_project_opens_the_ordered_choices(data) {
        prepareState(data);
        const load = projectButtons().filter(item => normalized(item.text) === "Load project");
        compare(load.length, 1, "Get started has one actual Load project button");
        Ui.scrollIntoView(load[0]);
        verify(Ui.rendered(load[0]) && load[0].enabled, "Load project accepts real input before a project exists");
        const point = Ui.clickPoint(load[0]);
        mouseClick(load[0], point.x, point.y);
        const expected = ["Open project folder", "Open project zip", "Open project from URL", "Import cryspy", "Import FullProf", "Import GSAS-II"];
        function choices() {
            return Render.descendants(Ui.windowRoot(app)).filter(item => typeof item.text === "string" && typeof item.clicked === "function" && expected.includes(normalized(item.text)) && Ui.rendered(item));
        }
        tryVerify(() => choices().length === 6, 2000, "Clicking Load project exposes all six real project and program choices");
        menuFrame("project.load.menu");
        const ordered = choices().sort((left, right) => left.mapToItem(null, 0, 0).y - right.mapToItem(null, 0, 0).y);
        compare(JSON.stringify(ordered.map(item => normalized(item.text))), JSON.stringify(expected), "The rendered popup lists folder, zip, URL, cryspy, FullProf and GSAS-II in order");
        keyClick(Qt.Key_Escape);
    }

    function test_save_copy_belongs_to_native_choices() {
        verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"))), "The copy-checkbox check starts from an ordinary open native project");
        Ui.click(test, Probe, app, "appBar.tab.project");
        Ui.click(test, Probe, app, "project.saveAs");
        const expected = ["As project folder", "As project zip", "Save a copy", "As cryspy", "As FullProf", "As GSAS-II"];
        function controls() {
            return Render.descendants(Ui.windowRoot(app)).filter(item => typeof item.text === "string" && typeof item.clicked === "function" && expected.includes(normalized(item.text)) && Ui.rendered(item));
        }
        tryVerify(() => controls().length === 6, 2000, "Save project as has one copy checkbox beside its five real choices");
        menuFrame("project.saveAs.menu");
        const ordered = controls().sort((left, right) => left.mapToItem(null, 0, 0).y - right.mapToItem(null, 0, 0).y);
        compare(JSON.stringify(ordered.map(item => normalized(item.text))), JSON.stringify(expected), "Save a copy belongs under the two EasyDiffraction choices and above the export section");
        const copy = ordered[2];
        verify(typeof copy.toggled === "function", "The native copy option is an actual checkbox");
        const before = copy.checked;
        const point = Ui.clickPoint(copy);
        mouseClick(copy, point.x, point.y);
        tryCompare(copy, "checked", !before, 1000, "The actual native copy checkbox responds to pointer input");
        keyClick(Qt.Key_Escape);
    }

    function test_save_project_as_opens_the_ordered_choices() {
        verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"))), "Save project as starts with an ordinary open native project");
        Ui.click(test, Probe, app, "appBar.tab.project");
        Ui.click(test, Probe, app, "project.saveAs");
        const expected = ["As project folder", "As project zip", "As cryspy", "As FullProf", "As GSAS-II"];
        function choices() {
            return Render.descendants(Ui.windowRoot(app)).filter(item => typeof item.text === "string" && typeof item.clicked === "function" && expected.includes(normalized(item.text)) && Ui.rendered(item));
        }
        tryVerify(() => choices().length === 5, 2000, "Clicking Save project as exposes all five real destination choices");
        menuFrame("project.saveAs.menu");
        const ordered = choices().sort((left, right) => left.mapToItem(null, 0, 0).y - right.mapToItem(null, 0, 0).y);
        compare(JSON.stringify(ordered.map(item => normalized(item.text))), JSON.stringify(expected), "The Save popup lists EasyDiffraction folder, Zip, cryspy, FullProf and GSAS-II in order");
        keyClick(Qt.Key_Escape);
    }
}
