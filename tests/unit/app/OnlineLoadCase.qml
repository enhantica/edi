// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import OnboardingAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui

TestCase {
    when: windowShown
    property var app
    property var onlineDialog
    property bool loadGroupsOnly: false

    Component { id: application; Main {} }

    Component {
        id: loadGroupsWindow
        ApplicationWindow {
            visible: true
            property bool showStructures: true
            readonly property Item activeGroup: showStructures ? structures : experiments
            StructuresGroup {
                id: structures
                width: 460
                visible: showStructures
                project: Session.project
            }
            ExperimentsGroup {
                id: experiments
                width: 460
                visible: !showStructures
                project: Session.project
            }
        }
    }

    function initTestCase() {
        Session.closeProject();
        OnboardingProbe.startClock();
        const factory = loadGroupsOnly ? loadGroupsWindow : application;
        app = factory.createObject(null, {width: 1300, height: 1000});
        verify(app !== null, "Online loading is exercised in the production window");
        resetProject();
        if (!loadGroupsOnly) {
            tryVerify(() => {
                settle();
                return app.pagesBuilt > 0 && app.pagesBuilt === app.pagesWanted;
            }, 5000, "The production workflow pages are ready in the shared window");
        }
        verify(waitForRendering(app.contentItem), "The production window renders before input");
    }

    function settle() {
        OnboardingProbe.incubate(app);
        OnboardingProbe.advanceClock(1000);
    }

    function resetProject(withControls = true) {
        Session.closeProject();
        verify(Session.createProject("load_menu", "", String(SettingsProof.emptyDirectory())),
               "The load menu starts from an isolated project");
        if (withControls) {
            verify(Session.project.createStructure(), "The structure page starts with a selected structure");
            verify(Session.project.createExperiment(), "The experiment page starts with a selected experiment");
            settle();
        }
    }

    function cleanup() {
        const page = pageItem();
        if (page) {
            for (const name of ["structures.load.menu", "experiments.load.menu", "onlineLoad"]) {
                const popup = findChild(page, name);
                if (popup && popup.visible)
                    popup.close();
                if (popup && name === "onlineLoad")
                    popup.lastSource = {};
            }
        }
        const preferences = findChild(app, "preferences");
        if (preferences && preferences.visible)
            preferences.close();
        onlineDialog = null;
        settle();
    }

    function cleanupTestCase() {
        OnboardingProbe.stopClock();
        if (app) {
            app.destroy();
            tryVerify(() => !app, 2000, "The shared window is destroyed before closing its project");
        }
        Session.closeProject();
    }

    function pageItem() {
        return loadGroupsOnly ? app.activeGroup : Ui.page(app);
    }

    function pageControl(name) {
        const page = () => pageItem();
        tryVerify(() => page() && Ui.find(page(), name, true) !== null, 3000,
                  "The current page exposes its production control " + name);
        return Ui.find(page(), name, true);
    }

    function click(item) {
        Ui.scrollIntoView(item);
        tryVerify(() => Ui.exposed(item) && item.enabled, 3000,
                  "The production control accepts pointer input: " + item.objectName);
        const point = Ui.clickPoint(item);
        let delay = 0;
        for (let parent = item.parent; parent; parent = parent.parent)
            if (typeof parent.pressDelay === "number")
                delay = Math.max(delay, parent.pressDelay + 1);
        mouseClick(item, point.x, point.y, Qt.LeftButton, Qt.NoModifier, delay);
        settle();
    }

    function openPage(data) {
        if (loadGroupsOnly) {
            app.showStructures = data.group === "structures";
            settle();
        } else {
            AppState.open(data.page);
            settle();
            tryCompare(app.appBarCentralTabs, "currentIndex", data.page, 3000,
                       "The named workflow page is selected");
            tryVerify(() => !Ui.moving(app.contentItem), 3000,
                      "The workflow page finishes its slide before input");
        }
        const group = pageControl("group." + data.group);
        if (group.collapsed)
            click(group.titleArea);
        verify(!group.collapsed, "The actual load group is expanded before interacting with it");
        return pageControl(data.group + ".load");
    }

    function onlineControl(name) {
        const find = () => Ui.find(onlineDialog.contentItem, "onlineLoad." + name);
        tryVerify(() => {
            if (find() !== null)
                return true;
            settle();
            return find() !== null;
        }, 3000, "The open dialog renders " + name);
        return find();
    }

    function openOnline(data) {
        click(openPage(data));
        const page = pageItem();
        const menu = findChild(page, data.group + ".load.menu");
        verify(menu !== null, "The workflow page owns the Load menu");
        tryCompare(menu, "opened", true, 3000, "The actual Load menu opens");
        const name = data.group + ".load." + data.action;
        const action = Array.from({length: menu.count}, (_, index) => menu.itemAt(index))
            .find(item => item.objectName === name);
        verify(action !== undefined, "The chosen Load group offers its From web action");
        click(action);
        onlineDialog = findChild(page, "onlineLoad");
        verify(onlineDialog !== null, "The workflow page owns the online dialog");
        tryVerify(() => {
            settle();
            return onlineDialog.opened;
        }, 3000, "The online dialog opens before its controls receive input");
        return onlineControl("source");
    }

    function check_new_experiment_wavelength() {
        const experiment = Session.project.currentExperiment;
        const wavelength = Probe.rows(experiment.instrument).find(
            row => row.parameter && row.parameter.name === "setup_wavelength");
        verify(wavelength !== undefined, "The new constant-wavelength experiment has a wavelength");
        compare(wavelength.parameter.value, 1, "A newly created experiment starts at one angstrom");
    }

    function check_actions_and_formats_data() {
        return [
            {tag: "structure", page: AppState.Page.Structure, group: "structures",
             groups: [["Structure", ".cif .edi", "COD · EasyDiffraction"]]},
            {tag: "experiment", page: AppState.Page.Experiment, group: "experiments",
             groups: [["Full experiment", ".edi .cif", "EasyDiffraction"],
                      ["Measured data into", ".xye .xy .dat .txt .csv · .int .hkl", "EasyDiffraction"]]}
        ];
    }

    function check_actions_and_formats(data) {
        const load = openPage(data);
        const create = pageControl(data.group + ".create");
        const duplicate = pageControl(data.group + ".duplicate");
        const items = [load, create, duplicate];
        tryVerify(() => {
            const [first, second, third] = items.map(item => item.mapToItem(app.contentItem, 0, item.height / 2));
            return first.x < second.x && second.x < third.x &&
                   Math.abs(second.y - first.y) < 1 && Math.abs(third.y - first.y) < 1;
        }, 3000, "Load, Create and Duplicate share one rendered row in that order");
        verify(/^Load(?:\s*[▾▼])?$/.test(load.text), "The first button is the Load menu");
        if (data.group === "experiments") {
            compare(Ui.find(pageItem(), "experiments.loadData.0"), null,
                    "The experiment's Data file cell has no row-level Load data action");
            compare(pageControl("experiments.file.0").text, "— no data yet",
                    "The data file cell describes an empty experiment");
        }

        click(load);
        const menu = findChild(pageItem(), data.group + ".load.menu");
        verify(menu !== null, "The current page owns a Load menu");
        tryCompare(menu, "opened", true, 3000, "The Load menu opens over the current page");
        compare(menu.count, 3 * data.groups.length, "Only the declared headers and actions occupy the menu");
        for (const [index, group] of data.groups.entries()) {
            const header = menu.itemAt(3 * index);
            const title = data.group === "experiments" && index === 1
                ? group[0] + " " + Session.project.currentExperiment.name : group[0];
            compare(header.text, title, "The menu names the group and its selected target");
            verify(!header.enabled, "Group headings are labels");
            for (const [offset, labelText] of [[1, "From file…"], [2, "From web…"]]) {
                const action = menu.itemAt(3 * index + offset);
                compare(action.text, labelText, "The group presents file and web actions in order");
                const labels = Render.texts(action.contentItem).filter(
                    item => Ui.rendered(item) && item.font.family !== Style.Fonts.iconsFamily);
                compare(labels.map(item => item.text), [labelText, group[offset]],
                        "The action displays only its name and its own formats or sources");
                compare(String(labels[1].color), String(Style.Colors.themeForegroundMinor),
                        "The format or source hint uses the secondary text colour");
            }
        }
        compare(create.text, "Create", "The second action is labelled Create");
        compare(duplicate.text, "Duplicate", "The third action is labelled Duplicate");
    }

    function check_from_web_opens_source_selector_data() {
        return [
            {tag: "structure", page: AppState.Page.Structure, group: "structures", action: "web",
             sources: ["COD", "EasyDiffraction", "EasyDiffraction mirror"], fields: ["ID", "Formula", "Elements", "Space group"]},
            {tag: "experiment", page: AppState.Page.Experiment, group: "experiments", action: "experimentWeb",
             sources: ["EasyDiffraction", "EasyDiffraction mirror"], fields: ["ID", "Name", "Radiation", "Technique", "Instrument"]},
            {tag: "measured", page: AppState.Page.Experiment, group: "experiments", action: "dataWeb",
             sources: ["EasyDiffraction", "EasyDiffraction mirror"], fields: ["ID", "Name", "Radiation", "Technique", "Instrument"]}
        ];
    }

    function check_from_web_opens_source_selector(data) {
        const selector = openOnline(data);
        compare(Array.from({length: selector.count}, (_, index) => selector.textAt(index)),
                data.sources, "From web shows the enabled sources for the page");
        compare(selector.currentText, data.sources[0], "The source selector shows the default database");
        const fields = Render.descendants(onlineDialog.contentItem).filter(
            item => item.objectName.startsWith("onlineLoad.field.") && Ui.rendered(item));
        const row = field => field.mapToItem(onlineDialog.contentItem, 0, 0).y;
        fields.sort((left, right) => row(left) - row(right));
        compare(fields.map(field => Render.texts(field.parent).find(item => item.text.endsWith(":")).text),
                data.fields.map(name => name + ":"), "The source renders its declared search fields in order with ID first");
        if (data.group === "structures")
            checkPreferences(onlineDialog);
    }

    function checkPreferences(dialog) {
        dialog.close();
        settle();
        tryCompare(dialog, "visible", false, 3000, "The search dialog closes before opening Preferences");
        const button = Ui.find(Ui.windowRoot(app), "appBar.button.preferences");
        verify(button !== null, "The production app bar exposes the Preferences action");
        click(button);
        const preferences = findChild(app, "preferences");
        verify(preferences !== null, "The application opens its production Preferences dialog");
        const projects = findChild(preferences, "preferences.tab.projects");
        verify(projects !== null, "Preferences has the Projects tab for online sources");
        click(projects);
        const table = findChild(preferences, "preferences.online.sources");
        tryVerify(() => table !== null && table.visible, 3000, "The Projects tab shows its online sources table");
        Ui.scrollIntoView(table);
        for (const [id, name, kinds] of [
            ["cod", "COD", "structures"],
            ["easydiffraction", "EasyDiffraction", "structures, experiments, data"],
            ["easydiffraction-mirror", "EasyDiffraction mirror", "structures, experiments, data"]
        ]) {
            const row = "preferences.online.source.";
            const cell = () => Render.descendants(table).find(item => item.objectName === row + "name." + id);
            tryVerify(() => cell() !== undefined, 3000, "Preferences lists " + name + " as an online source");
            compare(cell().value, name, "The source has the same name in Preferences and the search selector");
            compare(Render.descendants(table).find(item => item.objectName === row + "kinds." + id).text, kinds,
                    "Preferences lists the entry types provided by this source");
        }
    }

    function fixture(data) {
        return Qt.resolvedUrl("../../fixtures/online_sources/" + data.file);
    }

    function snapshot(data) {
        const project = Session.project;
        const structure = data.kind === "Structure";
        const block = structure ? project.currentStructure : project.currentExperiment;
        return {
            structures: project.structures.count,
            experiments: project.experiments.count,
            inputs: block ? block.text.inputText : "",
            pattern: !structure && block && !block.calculationOnly ? Probe.rows(block.pattern).map(
                row => [row.x, row.intensityMeas, row.intensityMeasSu]) : []
        };
    }

    function loadFromDisk(data) {
        const project = Session.project;
        const file = fixture(data);
        if (data.kind === "Structure")
            return project.loadStructure(file);
        if (data.kind === "Experiment")
            return project.loadExperiments([file]);
        return project.loadDataInto(project.currentExperiment, file);
    }

    function searchFor(id) {
        const field = onlineControl("field.id");
        field.forceActiveFocus();
        tryCompare(field, "activeFocus", true, 2000, "The open search field accepts keyboard input");
        for (const character of id)
            keyClick(character);
        compare(field.text, id, "The search ID is entered through the dialog field");
        click(onlineControl("search"));
    }

    function result(id, kind) {
        compare(onlineControl("id.0").text, id, "The result displays the independent fixture ID");
        compare(onlineControl("kind.0").text, kind, "The Kind column identifies what will load");
        compare(Ui.find(onlineDialog.contentItem, "onlineLoad.row.1"), null,
                "The selected route returns only its requested fixture entry");
    }

    function check_disk_parity_data() {
        return [
            {tag: "structure", page: AppState.Page.Structure, group: "structures", action: "web",
             id: "lbco", kind: "Structure", file: "easydiffraction/structures/lbco.cif"},
            {tag: "experiment", page: AppState.Page.Experiment, group: "experiments", action: "experimentWeb",
             id: "lbco-hrpt", kind: "Experiment", file: "easydiffraction/experiments/lbco_hrpt.edi"},
            {tag: "measured", page: AppState.Page.Experiment, group: "experiments", action: "dataWeb",
             id: "lbco-hrpt-xye", kind: "Data", file: "easydiffraction/data/lbco_hrpt.xye"}
        ];
    }

    function prepare(data) {
        resetProject(false);
        if (data.kind === "Structure")
            verify(Session.project.createStructure(), "Structure loading starts with an existing structure");
        if (data.kind === "Experiment")
            verify(Session.project.loadStructure(fixture({file: "easydiffraction/structures/lbco.cif"})),
                   "The full experiment has its independently authored linked structure");
        if (data.kind === "Data") {
            verify(Session.project.createExperiment(), "The measured project has a separate first experiment");
            verify(Session.project.createExperiment(), "Measured loading targets a second experiment");
        }
    }

    function check_disk_parity(data) {
        prepare(data);
        const before = snapshot(data);
        verify(loadFromDisk(data), "The ordinary local loader opens the committed fixture: " + Session.project.lastError);
        const expected = snapshot(data);
        verify(expected.inputs !== before.inputs, "The fixture changes the selected structure or experiment");
        if (data.kind === "Data")
            verify(expected.pattern.length > 0 && expected.pattern[0][1] !== undefined,
                   "The disk reference exposes the measured intensities");
        Session.project.undo();
        compare(snapshot(data), before, "Undo restores the identical starting state for the web load");

        const selectedIndex = Session.project.currentExperimentIndex;
        const selector = openOnline(data);
        if (data.kind === "Structure")
            selectSource(selector, "EasyDiffraction", Qt.Key_Down);
        searchFor(data.id);
        result(data.id, data.kind);
        click(onlineControl("load.0"));
        tryVerify(() => {
            settle();
            return !onlineDialog.visible;
        }, 3000, "A successful load closes the real dialog");
        const actual = snapshot(data);
        compare(actual.structures, expected.structures, "The two routes create the same number of structures");
        compare(actual.experiments, expected.experiments, "The two routes create the same number of experiments");
        compare(actual.inputs, expected.inputs, "The selected block has the same input values as its disk counterpart");
        compare(actual.pattern, expected.pattern, "Every measured coordinate, intensity and uncertainty matches disk");

        if (data.kind === "Data") {
            compare(Session.project.currentExperimentIndex, selectedIndex,
                    "Measurements go into the selected experiment");
            const first = Probe.rows(Session.project.experiments)[0].experiment;
            verify(first !== null && first.calculationOnly,
                   "Loading into the second experiment leaves the first without observations");
        }
    }

    function selectSource(selector, name, direction) {
        if (selector.currentText !== name) {
            click(selector);
            verify(SettingsProof.key(selector, direction), "The real source selector receives a navigation key");
            verify(SettingsProof.key(selector, Qt.Key_Return), "The real source selector commits the selected row");
            settle();
        }
        tryCompare(selector, "currentText", name, 2000, "The real search uses the requested database");
    }

    function check_cod_fallback() {
        const selector = openOnline({page: AppState.Page.Structure, group: "structures", action: "web"});
        selectSource(selector, "COD", Qt.Key_Up);
        click(onlineControl("search"));
        verify(/COD.*cannot be reached/i.test(onlineControl("message").text),
               "The unreachable fixture reports the COD failure in the popup: " + onlineControl("message").text);
        const alternative = onlineControl("alternative");
        compare(alternative.text, "Search EasyDiffraction instead", "The popup offers the other collection");
        verify(waitForPolish(onlineDialog.contentItem), "The newly offered fallback action completes layout");
        app.update();
        verify(waitForRendering(onlineDialog.contentItem), "The fallback action is rendered before clicking it");
        click(alternative);
        tryCompare(selector, "currentText", "EasyDiffraction", 2000, "The search uses the selected fallback source");
        result("lbco", "Structure");
        onlineControl("field.name");
        const id = onlineControl("field.id");
        const formula = onlineControl("field.formula");
        verify(id.mapToItem(formula, 0, 0).y < 0, "ID stays first after switching to EasyDiffraction");
        compare(Ui.find(onlineDialog.contentItem, "onlineLoad.message"), null,
                "A successful fallback clears the unreachable message");
    }
}
