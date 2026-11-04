// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiOnlineHttpFixture 1.0
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
                width: Style.Sizes.sideBarContentWidth + leftPadding + rightPadding
                visible: showStructures
                project: Session.project
            }
            ExperimentsGroup {
                id: experiments
                width: Style.Sizes.sideBarContentWidth + leftPadding + rightPadding
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
        app.requestActivate();
        resetProject();
        if (!loadGroupsOnly) {
            tryVerify(() => {
                settle();
                return app.pagesBuilt > 0 && app.pagesBuilt === app.pagesWanted;
            }, 5000, "The production workflow pages are ready in the shared window");
        }
        app.update();
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

    function cleanup() { cleanupOnlineControls(); }

    function cleanupOnlineControls() {
        Session.onlineSources.remove("new-source");
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
        if (loadGroupsOnly)
            for (const chooser of Probe.objectsWithProperty(app, "selectedFile"))
                if (chooser.visible)
                    chooser.reject();
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

    function menuAction(data) {
        click(openPage(data));
        const page = pageItem();
        const menu = findChild(page, data.group + ".load.menu");
        verify(menu !== null, "The workflow page owns the Load menu");
        tryCompare(menu, "opened", true, 3000, "The actual Load menu opens");
        const name = data.group + ".load." + data.action;
        const action = Array.from({length: menu.count}, (_, index) => menu.itemAt(index))
            .find(item => item.objectName === name);
        verify(action !== undefined, "The chosen Load group offers its requested action");
        return action;
    }

    function openOnline(data) {
        app.requestActivate();
        click(menuAction(data));
        onlineDialog = findChild(pageItem(), "onlineLoad");
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
        resetProject();
        const load = openPage(data);
        const create = pageControl(data.group + ".create");
        const duplicate = pageControl(data.group + ".duplicate");
        const items = [load, create, duplicate];
        tryVerify(() => {
            const [first, second, third] = items.map(item => item.mapToItem(app.contentItem, 0, item.height / 2));
            return first.x < second.x && second.x < third.x &&
                   Math.abs(second.y - first.y) < 1 && Math.abs(third.y - first.y) < 1;
        }, 3000, "Load, Create and Duplicate share one rendered row in that order");
        verify(/^Load(?:\s*[▾▼])?$/.test(load.text), "The first button reads Load with its menu caret");
        if (load.text.trim() === "Load")
            verify(Render.texts(load).some(item => Ui.rendered(item) &&
                       item.font.family === Style.Fonts.iconsFamily && item.text === "caret-down"),
                   "The rendered Load button includes its downward menu caret");
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
        const entity = data.group === "experiments" ? "experiment" : "structure";
        compare(create.text, "Create " + entity, "The second action names the entity it creates");
        compare(duplicate.text, "Duplicate " + entity, "The third action names the entity it duplicates");
    }

    function check_from_web_opens_source_selector_data() {
        return [
            {tag: "structure", page: AppState.Page.Structure, group: "structures", action: "web",
             sources: ["COD", "EasyDiffraction"], fields: ["ID", "Formula", "Elements", "Space group"]},
            {tag: "experiment", page: AppState.Page.Experiment, group: "experiments", action: "experimentWeb",
             sources: ["EasyDiffraction"], fields: ["ID", "Name", "Radiation", "Technique", "Instrument"]},
            {tag: "measured", page: AppState.Page.Experiment, group: "experiments", action: "dataWeb",
             sources: ["EasyDiffraction"], fields: ["ID", "Name", "Radiation", "Technique", "Instrument"]}
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
            ["easydiffraction", "EasyDiffraction", "structures, experiments, data"]
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

    function check_new_target_import_data() {
        return [
            {tag: "local-cancel", local: true, cancel: true},
            {tag: "local-corrupt", local: true, cancel: false},
            {tag: "local-valid", local: true, success: true},
            {tag: "web-valid", id: "valid-data", success: true},
            {tag: "web-corrupt", id: "corrupt-data"},
            {tag: "web-refused-probe", id: "unsupported-probe"}
        ];
    }

    function check_new_target_import(data) {
        resetProject(false);
        const project = Session.project;
        compare(project.experiments.count, 0, "The import begins with no selected experiment");
        verify(!project.canUndo, "The import begins with an empty Undo stack");
        const route = {page: AppState.Page.Experiment, group: "experiments",
                       action: data.local ? "dataFile" : "dataWeb"};
        if (data.local) {
            click(menuAction(route));
            let chooser;
            tryVerify(() => {
                chooser = Probe.objectsWithProperty(app, "selectedFile").find(
                    item => item.visible && /measured data/i.test(item.title));
                return chooser !== undefined;
            }, 3000, "From file opens the real measured-data chooser");
            if (data.cancel)
                chooser.reject();
            else {
                const file = fixture({file: data.success ? "three_points.xye" : "corrupt.xye"});
                chooser.reject();
                tryCompare(chooser, "visible", false, 3000, "The initial chooser closes before its starting file is set");
                chooser.currentFolder = fixture({file: ""});
                chooser.selectedFile = file;
                app.requestActivate();
                click(menuAction(route));
                tryCompare(chooser, "visible", true, 3000, "The real menu reopens the chooser with its initial selection");
                settle();
                compare(String(chooser.selectedFile), String(file), "The actual local chooser holds the requested fixture file");
                let acceptedFile;
                const observed = () => { acceptedFile = String(chooser.selectedFile); };
                chooser.accepted.connect(observed);
                chooser.accept();
                chooser.accepted.disconnect(observed);
                compare(acceptedFile, String(file), "The actual accepted signal carries the chosen local fixture");

            }
            tryCompare(chooser, "visible", false, 3000, "The local chooser settles after its answer");
        } else {
            openOnline(route);
            searchFor(data.id);
            result(data.id, "Data");
            click(onlineControl("load.0"));
            tryCompare(onlineDialog.search, "busy", false, 3000, "The downloaded file reaches the import boundary");
            tryCompare(onlineDialog, "visible", !data.success, 3000,
                       "The online popup closes on success and stays available on refusal");
        }
        if (data.success) {
            compare(project.experiments.count, 1, "A successful import commits one new experiment");
            const rows = Probe.rows(project.currentExperiment.pattern).map(
                row => [row.x, row.intensityMeas, row.intensityMeasSu]);
            compare(rows, [[21.5, 17.25, 0.75], [22.75, 31.75, 1.25], [25.125, 23.5, 1.5]],
                    "The new experiment contains every coordinate, count and uncertainty from the fixture");
            verify(project.canUndo, "The completed import can be undone");
            project.undo();
        }
        compare(project.experiments.count, 0, "Refusal or Undo of an import leaves no experiment");
        compare(project.currentExperiment, null, "Refusal or Undo leaves no selected experiment");
        verify(!project.canUndo, "Refusal or Undo leaves the original empty Undo stack");
        if (data.local && data.cancel) {
            verify(typeof project.setNewExperimentType === "function",
                   "A new-target type selection has a validation boundary before creation");
            verify(project.setNewExperimentType("sampleForm", "single crystal"),
                   "Single-crystal neutron data is a supported new-target selection");
            verify(!project.setNewExperimentType("radiationProbe", "xray"),
                   "The unsupported single-crystal X-ray probe change is refused");
            compare(project.newExperimentRadiationProbeToken, "neutron",
                    "A refused probe change retains the supported pending type");
            compare(project.experiments.count, 0, "A refused pending type change creates no experiment");
            verify(!project.canUndo, "A refused pending type change creates no Undo entry");
        }
    }

    function check_late_delivery_data() {
        return check_disk_parity_data().map(row => Object.assign({}, row, {remove: false}))
            .concat([Object.assign({}, check_disk_parity_data()[2], {tag: "removed-target", remove: true})]);
    }

    function check_late_delivery(data) {
        prepare(data);
        const selector = openOnline(data);
        if (data.kind === "Structure")
            selectSource(selector, "EasyDiffraction", Qt.Key_Down);
        searchFor(data.id);
        result(data.id, data.kind);
        const project = Session.project;
        const load = onlineControl("load.0");
        verify(load.enabled && Ui.exposed(load), "The real result action can start the download");
        // Invoke the shipped click signal in this frame. The fixture file reply
        // is queued for the next event-loop turn, after the owner change below.
        load.clicked();
        verify(onlineDialog.search.busy, "The selected file has an outstanding delivery");
        if (data.remove) {
            const target = project.currentExperiment;
            project.removeExperiment(project.currentExperimentIndex);
            verify(OnlineHttpFixture.finishRemoval(target),
                   "The removed target is actually destroyed before the queued file is delivered");
            compare(project.experiments.count, 1, "Only the other experiment survives the removal");
        } else {
            Session.closeProject();
            verify(Session.createProject("successor", "", String(SettingsProof.emptyDirectory())),
                   "A distinct project replaces the originating project before delivery");
            if (data.kind === "Experiment")
                verify(Session.project.loadStructure(fixture({file: "easydiffraction/structures/lbco.cif"})),
                       "The replacement project could accept the full experiment if delivery escaped");
        }
        const active = Session.project;
        const before = snapshot(data);
        tryCompare(onlineDialog.search, "busy", false, 3000, "The outstanding download settles");
        app.update();
        verify(waitForRendering(app.contentItem), "The replacement or surviving page processes the deferred file reply");
        compare(Session.project, active, "Late delivery cannot change the active project");
        compare(snapshot(data), before, "Late delivery changes neither the new project nor the surviving target");
    }

    function check_disabled_source_data() {
        return [{tag: "button", dispatch: false}, {tag: "stale-dispatch", dispatch: true}];
    }

    function check_disabled_source(data) {
        const route = {page: AppState.Page.Experiment, group: "experiments", action: "experimentWeb"};
        openOnline(route);
        const search = onlineDialog.search;
        const sources = Session.onlineSources;
        const disabled = Array.from({length: search.sources.count}, (_, index) => search.sources.keyAt(index));
        verify(disabled.includes("easydiffraction"), "The previously selected fixture source is initially enabled");
        onlineDialog.close();
        settle();
        try {
            for (const id of disabled)
                sources.setEnabled(id, false);
            const selector = openOnline(route);
            compare(selector.count, 0, "No source remains for the same kind after disabling them");
            if (data.dispatch) {
                search.sourceId = "easydiffraction";
                search.setField("id", "lbco-hrpt");
                search.search();
                verify(!search.busy, "Dispatch refuses a stale disabled id before starting work");
                compare(search.results.count, 0, "A disabled source cannot return its known matching entry");
            } else {
                verify(!onlineControl("search").enabled, "An empty source selector leaves Search disabled");
            }
        } finally {
            for (const id of disabled)
                sources.setEnabled(id, true);
        }
    }

    function check_cod_http_data() {
        return [
            {tag: "spacegroup", elements: "Ag Al Ba C Co H La O Zn", checkUrl: true},
            {tag: "extra-elements", elements: "Ag Al Ba C Co H La O Zn", checkUrl: false},
            {tag: "comma", elements: "Ag,Al,Ba,C,Co,H,La,O,Zn", checkUrl: false},
            {tag: "semicolon", elements: "Ag;Al;Ba;C;Co;H;La;O;Zn", checkUrl: false}
        ];
    }

    function check_cod_http(data) {
        resetProject();
        const search = Session.onlineSearch;
        verify(OnlineHttpFixture.attach(search), "The real search receives a socket-free COD transport");
        OnlineHttpFixture.clear();
        const body = SettingsProof.fileObservation(fixture({file: ""}), "cod_response.json");
        verify(body.exists, "The independent COD-shaped response is present");
        OnlineHttpFixture.enqueue(200, body.text);
        openOnline({page: AppState.Page.Structure, group: "structures", action: "web"});
        search.setField("space_group", "P 21/c");
        search.setField("elements", data.elements);
        search.search();
        tryCompare(search, "busy", false, 3000, "The injected COD answer settles in the production search");
        const requests = OnlineHttpFixture.requests();
        compare(requests.length, 1, "The entered element list reaches the COD request once");
        if (data.checkUrl) {
            const query = OnlineHttpFixture.query(requests[0]);
            compare(query.spacegroup, "P 21/c", "COD requests its documented spacegroup parameter");
            compare(query.sg, undefined, "COD's response field spelling is absent from the request");
        }
        result("9001003", "Structure");
    }

    function check_outage_class_data() {
        const rows = [];
        for (const route of ["search", "download", "index"]) {
            for (let status = 500; status <= 599; ++status)
                rows.push({tag: route + "-" + status, route: route, status: status, error: 0});
            for (const error of [401, 499, 102, 199])
                rows.push({tag: route + "-error-" + error, route: route, status: 0, error: error});
        }
        return rows;
    }

    function check_outage_class(data) {
        resetProject();
        const search = Session.onlineSearch;
        verify(OnlineHttpFixture.attach(search), "The outage gate replaces only the HTTP transport");
        OnlineHttpFixture.clear();
        const selector = openOnline({page: AppState.Page.Structure, group: "structures", action: "web"});
        if (data.route === "index") {
            addIndexSource();
        }
        if (data.route === "download") {
            const body = SettingsProof.fileObservation(fixture({file: ""}), "cod_response.json");
            const hit = JSON.parse(body.text).filter(row => String(row.file) === "9001003");
            OnlineHttpFixture.enqueue(200, JSON.stringify(hit));
            searchFor("9001003");
        }
        OnlineHttpFixture.enqueueError(data.status, data.error);
        if (data.route === "download") click(onlineControl("load.0"));
        else searchFor("");
        tryCompare(search, "busy", false, 3000, "The outage reaches the shipped callback");
        verify(search.unreachable, "Every server or proxy outage is classified as unavailable");
        verify(search.alternativeId !== "", "Every server or proxy outage offers an alternate source");
        verify(onlineControl("alternative").visible, "The alternate source is offered in the popup");
        if (data.route !== "index") {
            const field = onlineControl("field.id");
            field.forceActiveFocus();
            keyClick(Qt.Key_A, Qt.ControlModifier);
            keyClick(Qt.Key_Backspace);
            clickAlternative(onlineControl("alternative"));
            tryCompare(selector, "currentText", "EasyDiffraction", 3000, "The alternate source remains usable");
            result("lbco", "Structure");
        }
    }

    function addIndexSource() {
        Session.onlineSources.add();
        Session.onlineSources.setKinds("new-source", ["structure"]);
        Session.onlineSources.setUrl("new-source", "https://collection.invalid");
        Session.onlineSearch.sourceId = "new-source";
    }

    function check_malformed_index_data() {
        return ["bytes:1e30", "bytes:1e100", "bytes:9223372036854775808", "bytes:9007199254740994",
                "bytes:-1", "bytes:12.5", "schema", "kind", "duplicate", "absolute", "parent", "cell-short", "cell-type", "no-files"]
            .map(value => ({tag: value}));
    }

    function check_malformed_index(data) {
        resetProject();
        const search = Session.onlineSearch;
        verify(OnlineHttpFixture.attach(search), "Malformed indexes enter the shipped HTTP callback");
        OnlineHttpFixture.clear();
        const selector = openOnline({page: AppState.Page.Structure, group: "structures", action: "web"});
        addIndexSource();
        const body = SettingsProof.fileObservation(fixture({file: "easydiffraction/"}), "index.json");
        verify(body.exists, "Malformed documents start from the independent collection fixture");
        const doc = JSON.parse(body.text);
        const entry = doc.entries[0];
        const tag = data.tag;
        if (tag.startsWith("bytes:")) entry.files[0].bytes = Number(tag.substring(6));
        else if (tag === "schema") doc.schema = "edi-data-index/999";
        else if (tag === "kind") entry.kind = "unknown";
        else if (tag === "duplicate") doc.entries.push(entry);
        else if (tag === "absolute") entry.files[0].path = "/escaped.cif";
        else if (tag === "parent") entry.files[0].path = "../escaped.cif";
        else if (tag === "cell-short") entry.cell = [1, 2, 3];
        else if (tag === "cell-type") entry.cell = [1, 2, 3, 90, 90, "bad"];
        else if (tag === "no-files") entry.files = [];
        OnlineHttpFixture.enqueue(200, JSON.stringify(doc));
        searchFor("");
        tryCompare(search, "busy", false, 3000, "Malformed remote indexes finish without crashing");
        compare(search.results.count, 0, "A malformed index publishes no partial entries");
        verify(search.message !== "" && !search.unreachable, "A malformed index reports a parse failure, distinct from an outage");
    }

    function check_collection_entry_data() {
        return [{tag: "lbco", kind: "structure", name: "La0.5Ba0.5CoO3"},
                {tag: "lbco-hrpt", kind: "experiment", name: "La0.5Ba0.5CoO3 at HRPT"},
                {tag: "lbco-hrpt-xye", kind: "data", name: "La0.5Ba0.5CoO3 pattern from HRPT"}];
    }

    function check_collection_entry(data) {
        resetProject();
        const shape = {page: data.kind === "structure" ? AppState.Page.Structure : AppState.Page.Experiment,
                       group: data.kind === "structure" ? "structures" : "experiments",
                       action: data.kind === "structure" ? "web" : data.kind === "experiment" ? "experimentWeb" : "dataWeb"};
        const selector = openOnline(shape);
        if (data.kind === "structure") selectSource(selector, "EasyDiffraction", Qt.Key_Down);
        searchFor(data.tag);
        result(data.tag, data.kind === "structure" ? "Structure" : data.kind === "experiment" ? "Experiment" : "Data");
    }

    function check_collection_examples() {
        const model = Session.examples;
        model.filterProperty = "";
        model.filterValue = "";
        model.searchText = "";
        let row = -1;
        tryVerify(() => {
            for (let i = 0; i < model.count; ++i)
                if (model.text(i, "exampleId") === "lbco-hrpt-project") row = i;
            return row >= 0;
        }, 3000, "The Examples list includes the project from the collection fixture");
        compare(model.text(row, "origin"), "HRPT @ PSI", "The collection example retains its declared origin");
        verify(Session.openExample("lbco-hrpt-project"), "The collection example dispatches its ordinary archive loader");
        tryCompare(Session, "openingExample", false, 3000, "The fixture archive finishes opening");
        verify(Session.project !== null && Session.project.experiments.count > 0, "The collection archive opens a real populated project");
    }

    function check_unavailable_http_data() {
        return [
            {tag: "service-503", status: 503},
            {tag: "download-503", status: 503, download: true},
            {tag: "absent-file", status: 404, download: true},
            {tag: "missing-entry", status: 200}
        ];
    }

    function check_unavailable_http(data) {
        resetProject();
        const search = Session.onlineSearch;
        verify(OnlineHttpFixture.attach(search), "HTTP status comes from the socket-free fixture transport");
        OnlineHttpFixture.clear();
        const selector = openOnline({page: AppState.Page.Structure, group: "structures", action: "web"});
        if (data.download) {
            const body = SettingsProof.fileObservation(fixture({file: ""}), "cod_response.json");
            verify(body.exists, "The downloaded-file case starts from a known COD entry");
            const hit = JSON.parse(body.text).filter(row => String(row.file) === "9001003");
            OnlineHttpFixture.enqueue(200, JSON.stringify(hit));
            searchFor("9001003");
            compare(onlineControl("id.0").text, "9001003", "The known entry can be selected before its file fails");
            OnlineHttpFixture.enqueue(data.status, "");
            click(onlineControl("load.0"));
        } else {
            OnlineHttpFixture.enqueue(data.status, data.status === 200 ? "[]" : "");
            searchFor(data.status === 200 ? "9999999" : "");
        }
        tryCompare(search, "busy", false, 3000, "The controlled reply reaches the rendered result state");
        const message = onlineControl("message");
        if (data.status === 503) {
            verify(/COD.*cannot be reached/i.test(message.text), "A 503 identifies COD as unavailable");
            verify(search.detail.includes("503"), "The error detail retains the actual status code");
            if (data.download) {
                const field = onlineControl("field.id");
                field.forceActiveFocus();
                keyClick(Qt.Key_A, Qt.ControlModifier);
                keyClick(Qt.Key_Backspace);
                compare(field.text, "", "The alternate database search starts without the COD-specific id");
            }
            const alternative = onlineControl("alternative");
            clickAlternative(alternative);
            tryCompare(selector, "currentText", "EasyDiffraction", 3000, "The alternative selects EasyDiffraction");
            result("lbco", "Structure");
        } else {
            verify(!search.unreachable && search.alternativeId === "",
                   "An absent file or entry does not report a COD service outage");
            if (data.status === 404)
                verify(message.text.includes("404"), "An absent file reports its response code");
            else
                compare(message.text, "Nothing found", "A missing entry reports an empty search result");
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

    function clickAlternative(alternative) {
        verify(waitForPolish(onlineDialog.contentItem), "The newly offered fallback action completes layout");
        app.update();
        verify(waitForRendering(onlineDialog.contentItem), "The fallback action is rendered before clicking it");
        click(alternative);
    }

    function check_cod_fallback() {
        const selector = openOnline({page: AppState.Page.Structure, group: "structures", action: "web"});
        selectSource(selector, "COD", Qt.Key_Up);
        click(onlineControl("search"));
        verify(/COD.*cannot be reached/i.test(onlineControl("message").text),
               "The unreachable fixture reports the COD failure in the popup: " + onlineControl("message").text);
        const alternative = onlineControl("alternative");
        compare(alternative.text, "Search EasyDiffraction instead", "The popup offers the other collection");
        clickAlternative(alternative);
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
