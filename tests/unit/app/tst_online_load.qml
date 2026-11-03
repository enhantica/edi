// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui

TestCase {
    name: "OnlineLoad"
    when: windowShown
    property var app

    Component { id: application; Main {} }

    function init() {
        Session.closeProject();
        app = application.createObject(null, {width: 1300, height: 1000});
        verify(app !== null, "Online loading is exercised in the production window");
        verify(Session.createProject("load_menu", "", String(SettingsProof.emptyDirectory())),
               "The load menu starts from an isolated project");
        verify(Session.project.createStructure(), "The structure page starts with a selected structure");
        verify(Session.project.createExperiment(), "The experiment page starts with a selected experiment");
        verify(waitForRendering(app.contentItem), "The production window renders before input");
    }

    function cleanup() {
        Session.closeProject();
        if (app)
            app.destroy();
        app = null;
    }

    function pageControl(name) {
        const page = () => Ui.page(app);
        tryVerify(() => page() && Ui.find(page(), name, true) !== null, 3000,
                  "The current page exposes its production control " + name);
        return Ui.find(page(), name, true);
    }

    function click(item) {
        Ui.scrollIntoView(item);
        const point = Ui.clickPoint(item);
        verify(point !== null && item.enabled, "The production control accepts pointer input");
        mouseClick(item, point.x, point.y);
    }

    function menuLabels(label) {
        return Render.texts(Ui.windowRoot(app)).filter(item => item.text === label && Ui.rendered(item));
    }

    function label(text) {
        tryVerify(() => menuLabels(text).length > 0, 2000, "The real menu or dialog renders " + text);
        return menuLabels(text)[0];
    }

    function openPage(data) {
        AppState.open(data.page);
        tryCompare(app.appBarCentralTabs, "currentIndex", data.page, 3000,
                   "The named workflow page is selected");
        const group = pageControl("group." + data.group);
        if (group.collapsed)
            click(group.titleArea);
        return pageControl(data.group + ".load");
    }

    function test_new_experiment_wavelength() {
        const experiment = Session.project.currentExperiment;
        const wavelength = Probe.rows(experiment.instrument).find(
            row => row.parameter && row.parameter.name === "setup_wavelength");
        verify(wavelength !== undefined, "The new constant-wavelength experiment has a wavelength");
        compare(wavelength.parameter.value, 1, "A newly created experiment starts at one angstrom");
    }

    function test_actions_and_formats_data() {
        return [
            {tag: "structure", page: AppState.Page.Structure, group: "structures",
             titles: ["Structure"], hints: [".cif", ".edi", "COD", "EasyDiffraction"], web: 1},
            {tag: "experiment", page: AppState.Page.Experiment, group: "experiments",
             titles: ["Full experiment", "Measured data into"],
             hints: [".edi", ".cif", ".xye", ".xy", ".dat", ".txt", ".csv", "EasyDiffraction"], web: 2}
        ];
    }

    function test_actions_and_formats(data) {
        const load = openPage(data);
        const create = pageControl(data.group + ".create");
        const duplicate = pageControl(data.group + ".duplicate");
        const items = [load, create, duplicate];
        const positions = items.map(item => item.mapToItem(app.contentItem, 0, item.height / 2));
        verify(positions.every(point => Math.abs(point.y - positions[0].y) < 1),
               "Load, Create and Duplicate occupy one rendered row");
        verify(positions[0].x < positions[1].x && positions[1].x < positions[2].x,
               "The action row orders Load, Create and Duplicate from left to right");
        verify(/^Load(?:\s*[▾▼])?$/.test(load.text), "The first button is the Load menu");
        compare(create.text, "Create", "The second action is labelled Create");
        compare(duplicate.text, "Duplicate", "The third action is labelled Duplicate");
        if (data.group === "experiments") {
            compare(Ui.find(Ui.page(app), "experiments.loadData.0"), null,
                    "The experiment's Data file cell has no row-level Load data action");
            label("— no data yet");
        }

        click(load);
        label("From web…");
        const menu = Render.texts(Ui.windowRoot(app)).filter(item => Ui.rendered(item));
        for (const title of data.titles)
            verify(menu.some(item => item.text.startsWith(title)), "The Load menu shows its group " + title);
        compare(menuLabels("From web…").length, data.web, "Each menu group has a From web action");
        compare(menuLabels("From file…").length, data.web, "Each menu group has a From file action");
        for (const hint of data.hints) {
            verify(menu.some(item => String(item.color) === String(Style.Colors.themeForegroundMinor)
                              && item.text.split(/[^\w.]+/).includes(hint)),
                   "The Load menu renders a grey hint for " + hint);
        }
        verify(!menu.some(item => item.text.includes(".zip") &&
                            String(item.color) === String(Style.Colors.themeForegroundMinor)),
               "The structure and experiment menus reserve ZIP for the Project page");
    }

    function test_from_web_opens_source_selector_data() {
        return [
            {tag: "structure", page: AppState.Page.Structure, group: "structures", route: 0,
             sources: ["COD", "EasyDiffraction"], fields: ["ID", "Formula", "Elements", "Space group"]},
            {tag: "experiment", page: AppState.Page.Experiment, group: "experiments", route: 0,
             sources: ["EasyDiffraction"], fields: ["ID", "Name", "Radiation", "Technique", "Instrument"]},
            {tag: "measured", page: AppState.Page.Experiment, group: "experiments", route: 1,
             sources: ["EasyDiffraction"], fields: ["ID", "Name", "Radiation", "Technique", "Instrument"]}
        ];
    }

    function test_from_web_opens_source_selector(data) {
        click(openPage(data));
        label("From web…");
        const webActions = menuLabels("From web…").sort(
            (first, second) => first.mapToItem(Ui.windowRoot(app), 0, 0).y -
                              second.mapToItem(Ui.windowRoot(app), 0, 0).y);
        verify(data.route < webActions.length, "The selected Load group has a real From web action");
        click(webActions[data.route]);
        const root = Ui.windowRoot(app);
        label("Search");
        const selector = Render.descendants(root).find(item => Ui.rendered(item) &&
            typeof item.textAt === "function" && item.count === data.sources.length &&
            data.sources.every((source, index) => item.textAt(index) === source));
        verify(selector !== undefined, "From web shows the page's source selector");
        compare(selector.currentText, data.sources[0], "The source selector shows the default database");
        const fields = data.fields.map(text => label(text).mapToItem(root, 0, 0));
        verify(fields.slice(1).every(point => point.y > fields[0].y ||
                                      (point.y === fields[0].y && point.x > fields[0].x)),
               "ID is the first rendered search field for the selected database");
    }
}
