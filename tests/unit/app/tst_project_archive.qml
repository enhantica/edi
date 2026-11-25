import QtQuick
import QtTest
import QtQuick.Controls
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0

TestCase {
    id: test
    name: "ProjectArchive"
    when: windowShown
    property var app
    Component {
        id: appFactory
        Main {}
    }
    function application() {
        app = appFactory.createObject(null, {
            width: Math.min(1280, SettingsProof.screen().width),
            height: Math.min(720, SettingsProof.screen().height - 60),
            visible: true
        });
        verify(app !== null, "Project file actions use the actual application window");
        app.requestActivate();
        tryCompare(app, "active", true, 2000, "The project action window receives real input");
        if (Ui.control(Probe, app, "home.start"))
            clickControl("home.start");
        clickControl("appBar.tab.project");
        clickControl("sideBar.tab.basic");
        return app;
    }
    function clickControl(name) {
        if (["project.create", "project.load", "project.saveAs"].includes(name))
            Ui.expandGroup(test, Probe, app, "group.getStarted");
        let item;
        tryVerify(() => {
            item = Ui.control(Probe, app, name) || Ui.find(Ui.windowRoot(app), name);
            return item !== null && item.enabled && Ui.clickPoint(item) !== null && !Ui.moving(app.contentItem);
        }, 4000, "The actual project action is enabled in its settled viewport: " + name);
        verify(waitForPolish(item), "The actual project action finishes layout before pointer input");
        app.update();
        verify(waitForRendering(app.contentItem), "The actual application draws before project input");
        tryVerify(() => {
            item = Ui.control(Probe, app, name) || Ui.find(Ui.windowRoot(app), name);
            return item !== null && item.enabled && Ui.clickPoint(item) !== null && !Ui.moving(app.contentItem);
        }, 4000, "The rebuilt page retains an exposed action at the actual input frame: " + name);
        const point = Ui.clickPoint(item);
        mouseClick(item, point.x, point.y);
        app.update();
        verify(waitForRendering(app.contentItem), "Project pointer input reaches a real application frame");
        if (name.includes(".tab."))
            tryCompare(item, "checked", true, 2000, "Real project input selects the requested tab");
        tryVerify(() => !Ui.moving(app.contentItem), 2000, "The selected project viewport finishes moving");
        return item;
    }
    readonly property var cases: ["sc-neut-tof_taurine-senju", "pd-neut-cwl_cosio-d20_scan-3f", "sc-neut-cwl_tb2ti2o7-heidi_basic"]
    function cleanup() {
        if (app) {
            app.close();
            app.destroy();
        }
        app = null;
        Session.closeProject();
    }
    property int completedDialogTurn: 0
    function completedProjectStaysOpen(name) {
        tryVerify(() => {
            const creates = Probe.objectsWithProperty(app, "projectName").filter(dialog => dialog.projectParentDirectory !== undefined);
            const opens = Probe.objectsWithProperty(app, "opened").filter(dialog => dialog.objectName === "project.load.menu");
            return creates.length > 0 && opens.length > 0 && creates.concat(opens).every(dialog => !dialog.visible && !dialog.opened);
        }, 2000, "Accepted Create and Open dialogs finish closing on the actual replacement page");
        for (let turn = 0; turn < 12; ++turn) {
            completedDialogTurn = 0;
            Qt.callLater(() => completedDialogTurn = 1);
            tryCompare(test, "completedDialogTurn", 1, 1000, "The completed project action reaches each following event-loop turn");
            app.update();
            verify(waitForRendering(app.contentItem), "The completed project action is checked after each actual application frame");
            verify(Session.hasProject && Session.project.name === name, "The created or opened project remains open on every following turn");
            const creates = Probe.objectsWithProperty(app, "projectName").filter(dialog => dialog.projectParentDirectory !== undefined);
            const opens = Probe.objectsWithProperty(app, "opened").filter(dialog => dialog.objectName === "project.load.menu");
            console.log("PROJECT_DIALOG_COMPLETION " + JSON.stringify({
                turn,
                name: Session.project.name,
                create: creates.map(dialog => ({
                            visible: dialog.visible,
                            opened: dialog.opened
                        })),
                open: opens.map(dialog => ({
                            visible: dialog.visible,
                            opened: dialog.opened
                        }))
            }));
            verify(creates.length > 0, "The current real Project page retains its Create dialog for inspection");
            verify(creates.every(dialog => !dialog.visible && !dialog.opened), "An accepted project action never reopens any empty Create dialog on a following turn");
            verify(opens.length > 0 && opens.every(dialog => !dialog.visible && !dialog.opened), "An accepted project action keeps every Load project menu closed on following turns");
        }
    }
    function test_create_completion_data() {
        return [
            {
                tag: "enter",
                enter: true
            },
            {
                tag: "ok",
                enter: false
            }
        ];
    }
    function test_create_completion(data) {
        application();
        verify(!Session.hasProject, "Create completion starts on the Project page without an existing project");
        clickControl("project.create");
        const dialog = SettingsProof.creationDialog(app);
        verify(dialog !== null, "The Project page Create action opens its actual production dialog");
        tryCompare(dialog, "opened", true, 2000, "Name input follows the Create dialog's opening transition");
        dialog.projectParentDirectory = String(SettingsProof.emptyDirectory());
        const name = "completed_" + data.tag;
        const field = findChild(dialog, "createProject.name");
        verify(field !== null, "Create completion types into the real project name field");
        mouseClick(field, field.width / 2, field.height / 2);
        verify(SettingsProof.type(field, name), "The focused real project name field receives actual keyboard text events");
        compare(field.text, name, "Real name-field keyboard input supplies the requested project name");
        if (data.enter)
            keyClick(Qt.Key_Return);
        else {
            const ok = dialog.standardButton(Dialog.Ok);
            verify(ok !== null && ok.enabled, "Create completion uses the enabled actual OK control");
            mouseClick(ok, ok.width / 2, ok.height / 2);
        }
        tryVerify(() => Session.hasProject && Session.project.name === name, 4000, "Enter and OK create and open the named project through the actual Project page");
        completedProjectStaysOpen(name);
    }
    function test_open_choice_completion_data() {
        return [
            {
                tag: "enter",
                enter: true
            },
            {
                tag: "ok",
                enter: false
            }
        ];
    }
    function test_open_choice_completion(data) {
        application();
        const input = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
        const metadata = SettingsProof.text(input, "project.edi");
        const name = metadata.match(/_metadata.name\s+(?:"([^"]+)"|(\S+))/).slice(1).find(value => value !== undefined);
        clickControl("project.load");
        const choice = findChild(app, "project.load.menu");
        verify(choice !== null, "Open completion uses the actual Load project menu");
        tryCompare(choice, "opened", true, 2000, "The actual Load menu receives keyboard or pointer input only after opening");
        if (data.enter) {
            keyClick(Qt.Key_Down);
            tryVerify(() => choice.currentItem && choice.currentItem.objectName === "project.load.folder", 2000, "Keyboard navigation selects the first enabled native folder entry");
            keyClick(Qt.Key_Return);
        } else {
            clickControl("project.load.folder");
        }
        let dialogs;
        tryVerify(() => {
            dialogs = SettingsProof.projectFileDialogs(app, true);
            return dialogs.length === 1;
        }, 2000, "Accepted Open choice reaches exactly one real folder chooser");
        verify(SettingsProof.chooseProjectLocation(dialogs[0], input, true), "The real system chooser accepts the independent project folder");
        tryVerify(() => Session.hasProject && Session.project.name === name, 4000, "Enter and OK Open choices finish opening their selected project");
        completedProjectStaysOpen(name);
    }
    function test_save_dialog_layout() {
        application();
        canonicalProject(cases[2]);
        clickControl("project.saveAs");
        const dialog = findChild(app, "project.saveAs.menu");
        verify(dialog !== null, "Save geometry is observed on the actual Save project as menu");
        tryCompare(dialog, "opened", true, 2000, "Save geometry is measured after the real menu opens");
        const folder = Ui.find(Ui.windowRoot(app), "project.saveAs.folder"), zip = Ui.find(Ui.windowRoot(app), "project.saveAs.zip"), copy = Ui.find(Ui.windowRoot(app), "project.saveAs.copy");
        verify(folder && zip && copy, "The menu exposes both native destinations and the separate copy checkbox");
        const folderEnd = folder.mapToItem(dialog.contentItem, 0, folder.height).y;
        const zipTop = zip.mapToItem(dialog.contentItem, 0, 0).y;
        const zipEnd = zip.mapToItem(dialog.contentItem, 0, zip.height).y;
        const copyTop = copy.mapToItem(dialog.contentItem, 0, 0).y;
        verify(zipTop >= folderEnd && copyTop >= zipEnd, "The copy checkbox follows both native destinations without overlap");
        const exportItem = Ui.find(Ui.windowRoot(app), "project.export.fullProf");
        verify(exportItem !== null && exportItem.mapToItem(dialog.contentItem, 0, 0).y >= copyTop + copy.height, "The always-copy exports follow the native copy option");
        for (const item of [folder, zip, copy, exportItem])
            verify(item.width >= item.implicitWidth && Ui.rendered(item), "The fitted menu renders each destination and its complete label and hint");
        for (const item of [folder, zip, exportItem])
            verify(item.leftPadding > 0 && item.rightPadding === item.leftPadding, "Each destination row retains equal positive left and right margins");
        compare(dialog.width, dialog.contentWidth + dialog.leftPadding + dialog.rightPadding, "Menu margins surround its content without an unused dialog column");
        dialog.close();
    }
    function test_project_actions() {
        application();
        verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"))), "The Project page action inventory starts with a real open project");
        let group;
        tryVerify(() => {
            group = Ui.control(Probe, app, "group.getStarted");
            return group !== null;
        }, 4000, "The working project exposes its actual Get started group");
        Ui.expandGroup(test, Probe, app, "group.getStarted");
        const actions = Render.descendants(group).filter(item => item.objectName.startsWith("project.") && typeof item.text === "string");
        const visible = actions.filter(item => item.visible);
        compare(visible.filter(item => item.objectName === "project.load").length, 1, "The Project page has one Load project action for native projects and imports");
        compare(visible.filter(item => item.objectName === "project.saveAs").length, 1, "The Project page has one Save project as action");
        compare(visible.filter(item => item.enabled).map(item => item.objectName).sort().join(","), ["project.create", "project.load", "project.saveAs"].sort().join(","), "Create, Load and Save as are the three working Get started actions");
        clickControl("project.load");
        const url = Ui.find(Ui.windowRoot(app), "project.load.url");
        verify(url !== null && !url.enabled, "Open from URL stays present and disabled inside Load project");
        keyClick(Qt.Key_Escape);
    }
    function test_open_data() {
        let rows = [];
        for (const name of cases)
            for (const route of ["folder", "record", "zip"])
                rows.push({
                    tag: name + "-" + route,
                    projectName: name,
                    route: route
                });
        return rows;
    }
    function test_open(data) {
        if (data.route === "zip")
            application();
        const folder = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/" + data.projectName + "/project"));
        verify(Session.openProject(folder), "The folder route loads the independently committed project");
        const expected = Session.project.name;
        const cell = Session.project.currentStructure.cell.lengthA.value;
        Session.closeProject();
        const input = data.route === "zip" ? SettingsProof.copyProjectArchive(Probe.repoUrl("tests/fixtures/project_archive/" + data.projectName + ".zip")) : data.route === "record" ? folder.toString() + "/project.edi" : folder;
        verify(Session.openProject(input), "The app opens folders, project records and interoperable ZIP archives: " + Session.lastError);
        compare(Session.project.name, expected, "Every app open route retains the project identity");
        compare(Session.project.currentStructure.cell.lengthA.value, cell, "Archive opening retains the independently loaded cell value exactly");
        if (data.route === "zip") {
            compare(Session.projectLocation, SettingsProof.localPath(input), "An opened ZIP keeps that same ZIP as its persistent location");
            verify(!Session.needsSaveAs, "A writable opened ZIP supports ordinary Save without asking for a new destination");
            const first = SettingsProof.projectArchiveBytes(input);
            Session.project.name = "zip-open-edited";
            clickControl("appBar.button.save");
            compare(Session.lastError, "", "The actual Save button writes the opened ZIP without a refusal");
            const choice = findChild(app, "saveAs.choice");
            verify(choice !== null && !choice.visible, "Ordinary Save of a writable opened ZIP does not ask for a new destination");
            const archive = SettingsProof.projectArchiveBytes(input);
            verify(archive !== first, "Saving an edit actually replaces the same opened ZIP bytes");
            verify(!Session.project.modified && !Session.project.canUndo, "ZIP Save leaves the adopted model clean without an Undo step");
            evidence({
                kind: "opened-rewrite",
                original: SettingsProof.projectFolderBytes(Session.projectDirectoryUrl(Session.project.path)),
                archive,
                name: "zip-open-edited"
            });
            Session.closeProject();
            verify(Session.openProject(input), "The same rewritten ZIP is immediately readable");
            compare(Session.project.name, "zip-open-edited", "Reopening the same ZIP retains the saved edit exactly");
        }
    }
    function test_escape() {
        verify(!Session.openProject(Probe.repoUrl("tests/fixtures/project_archive/escape.zip")), "The app refuses an archive member outside its project folder");
        verify(Session.lastError.length > 0, "The rejected archive reports its containment error");
    }
    function test_cancel() {
        verify(Session.openProject(Probe.repoUrl("docs/user/cli/sc-neut-tof_taurine-senju/project")), "The first opening starts on the real taurine project");
        verify(Session.project.calculating, "Opening publishes a usable model while its first calculation is pending");
        const second = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
        verify(Session.openProject(second), "A second project replaces an opening project with work pending");
        const active = Session.project;
        tryCompare(active, "calculating", false, 15000, "The second project's own calculation completes");
        compare(Session.project, active, "The first project's result never replaces the second project");
        compare(active.name, "relations", "Cancellation retains the independently named second project");
        compare(active.currentStructure.cell.lengthA.value, 4.1, "Cancellation retains the second project's independent cell value");
        const rows = Probe.rows(active.currentExperiment.pattern);
        verify(rows.length === 9 && rows[0].intensityMeas === 5.0484848484848488, "No taurine reflection result reaches the second project's measured pattern");
    }
    function test_save_pending() {
        verify(Session.openProject(Probe.repoUrl("docs/user/cli/sc-neut-tof_taurine-senju/project")), "Pending Save starts on the real taurine project");
        verify(Session.project.calculating, "Save is exercised during actual pending opening work");
        const destination = SettingsProof.emptyDirectory();
        verify(Session.saveAs(destination), "Save waits for coherent rounded results before publishing");
        const before = JSON.stringify(Probe.rows(Session.project.currentExperiment.pattern));
        verify(!Session.project.modified && !Session.project.canUndo, "Pending Save finishes clean and adds no Undo step");
        Session.closeProject();
        verify(Session.openProject(destination), "A project saved during opening is immediately readable");
        tryCompare(Session.project, "calculating", false, 15000, "Reopened results settle before exact comparison");
        compare(JSON.stringify(Probe.rows(Session.project.currentExperiment.pattern)), before, "Pending Save writes the exact rounded-model pattern that a reopen calculates");
    }
    function routeInput(projectName, route) {
        const folder = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/" + projectName + "/project"));
        return route === "zip" ? Probe.repoUrl("tests/fixtures/project_archive/" + projectName + ".zip") : route === "record" ? folder.toString() + "/project.edi" : folder;
    }
    function test_open_dialog_data() {
        const rows = [];
        for (const projectName of cases)
            for (const route of ["folder", "zip"])
                rows.push({
                    tag: projectName + "-" + route,
                    projectName,
                    route
                });
        return rows;
    }
    function chooseOpenFormat(kind) {
        const choice = findChild(app, "project.load.menu");
        verify(choice !== null, "Load project presents the same menu on every platform");
        tryCompare(choice, "opened", true, 2000, "The Load project menu is open before choosing a native destination or importer");
        clickControl(kind === "fullProf" ? "project.import.fullProf" : "project.load." + kind);
    }
    function test_open_dialog(data) {
        application();
        const input = routeInput(data.projectName, data.route);
        clickControl("project.load");
        chooseOpenFormat(data.route);
        let dialogs;
        tryVerify(() => {
            dialogs = SettingsProof.projectFileDialogs(app, data.route === "folder");
            return dialogs.length === 1;
        }, 2000, "One Open project action opens one actual system file dialog");
        const facts = SettingsProof.projectDialogFacts(dialogs[0]);
        verify(data.route === "folder" ? !facts.systemFile : facts.systemFile, "Open uses the matching folder or ZIP system chooser");
        verify(SettingsProof.chooseProjectLocation(dialogs[0], input, data.route === "folder"), "The actual Open dialog accepts the selected folder or ZIP");
        tryVerify(() => Session.hasProject && Session.lastError === "", 4000, "The deferred Open handler loads the selected project after its signal returns");
        const metadata = SettingsProof.text(Probe.repoUrl("docs/user/cli/" + data.projectName + "/project"), "project.edi");
        const name = metadata.match(/_metadata.name\s+(?:"([^"]+)"|(\S+))/).slice(1).find(value => value !== undefined);
        compare(Session.project.name, name, "Unified Open retains the input project's declared name");
    }
    function test_open_fullprof_project() {
        application();
        clickControl("project.load");
        chooseOpenFormat("fullProf");
        let dialogs;
        tryVerify(() => {
            dialogs = SettingsProof.projectFileDialogs(app, false);
            return dialogs.length === 1;
        }, 2000, "The FullProf choice opens a real file chooser");
        const input = Probe.repoUrl("knowledge/verification/fullprof/pd-neut-cwl_pbso4_basic/pbso4.pcr");
        verify(SettingsProof.chooseProjectLocation(dialogs[0], input, false), "The native chooser accepts the PCR file");
        tryVerify(() => Session.hasProject || Session.lastError !== "", 8000, "The deferred Open action finishes");
        compare(Session.lastError, "", "Opening the selected FullProf control file");
        verify(Session.hasProject, "Open imports the selected data and structure");
        compare(Session.project.name, "pbso4");
        verify(Session.needsSaveAs, "The imported project has its own native save destination");
        const imported = Session.project;
        clickControl("project.saveAs");
        clickControl("project.export.fullProf");
        tryVerify(() => {
            dialogs = SettingsProof.projectFileDialogs(app, true);
            return dialogs.length === 1;
        }, 2000, "FullProf export chooses a parent folder");
        const parent = SettingsProof.emptyDirectory();
        verify(SettingsProof.chooseProjectLocation(dialogs[0], parent, true));
        const folder = parent.toString() + "/pbso4-fullprof";
        tryVerify(() => SettingsProof.text(folder, "project.pcr").includes("NPATT"), 4000);
        verify(SettingsProof.text(folder, "pattern_1.dat").startsWith("XYDATA"));
        compare(Session.project, imported, "Export keeps the imported project open");
    }
    function test_web_zip_lifecycle_data() {
        const rows = [];
        for (const route of ["open", "recent"])
            for (const state of ["empty", "replace"])
                rows.push({
                    tag: route + "-" + state,
                    route,
                    state
                });
        return rows;
    }
    function test_web_zip_lifecycle(data) {
        application();
        const input = SettingsProof.copyProjectArchive(Probe.repoUrl("tests/fixtures/project_archive/browser-saved-project.zip"));
        verify(input.toString().endsWith(".zip"), "The desktop route uses a writable copy of the actual web download");
        const expected = JSON.parse(SettingsProof.repoText("tests/fixtures/project_archive/browser-saved-project.json"));
        if (data.state === "replace") {
            verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"))), "Reopening starts with a different real project already open");
            tryCompare(Session.project, "calculating", false, 15000, "The replaced project is usable before the next real control action");
            compare(Session.project.name, "relations", "The pre-existing project differs from the downloaded project");
        } else {
            verify(!Session.hasProject, "The empty-window route starts without an open project");
        }
        if (data.route === "open") {
            clickControl("project.load");
            chooseOpenFormat("zip");
            let dialogs;
            tryVerify(() => {
                dialogs = SettingsProof.projectFileDialogs(app, false);
                return dialogs.length === 1;
            }, 2000, "The Get started Open project button exposes one real native file chooser");
            verify(SettingsProof.chooseProjectLocation(dialogs[0], input, false), "The native chooser accepts the actual browser-produced ZIP");
        } else {
            RecentProjects.remember(SettingsProof.localPath(input));
            RecentProjects.refresh();
            clickControl("appBar.tab.project");
            let group;
            tryVerify(() => {
                group = Ui.control(Probe, app, "group.recentProjects");
                return group !== null;
            }, 4000, "Recent projects is present after the replaced project's real page finishes loading");
            if (group.collapsed)
                mouseClick(group.titleArea, group.titleArea.width / 2, group.titleArea.height / 2);
            let index = -1;
            for (let i = 0; i < RecentProjects.rows.count; ++i)
                if (RecentProjects.rows.get(i).path === SettingsProof.localPath(input))
                    index = i;
            verify(index >= 0, "The exact downloaded ZIP appears in Recent projects");
            clickControl("recentProjects.path." + index);
        }
        tryVerify(() => Session.hasProject && Session.project.name === expected.name, 4000, "The real control finishes loading the name recorded in the downloaded ZIP");
        tryCompare(Session.project, "calculating", false, 15000, "The downloaded project's own calculation settles after opening");
        compare(Session.lastError, "", "The downloaded project opens without a reported error");
        clickControl("project.saveAs");
        const choice = findChild(app, "project.saveAs.menu");
        verify(choice !== null, "The project remains interactive after the opening signal handler returns");
        tryCompare(choice, "opened", true, 2000, "A second real action works after ZIP opening");
        choice.close();
    }
    function test_save_chooser_defaults_data() {
        const rows = [];
        for (const input of ["folder", "zip"])
            for (const zip of [false, true])
                for (const copy of [false, true])
                    rows.push({
                        tag: input + "-" + (zip ? "zip" : "folder") + (copy ? "-copy" : "-move"),
                        input,
                        zip,
                        copy
                    });
        return rows;
    }
    function test_save_chooser_defaults(data) {
        application();
        const input = data.input === "zip" ? SettingsProof.copyProjectArchive(Probe.repoUrl("tests/fixtures/project_archive/browser-saved-project.zip")) : SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
        verify(Session.openProject(input), "Chooser defaults start at an actual project location");
        tryCompare(Session.project, "calculating", false, 15000, "Chooser defaults are inspected on a usable project");
        Session.project.name = "Named choice alpha 19";
        const source = SettingsProof.localPath(input);
        const directory = data.input === "zip" ? source.substring(0, source.lastIndexOf("/")) : source;
        clickControl("project.saveAs");
        const choice = findChild(app, "project.saveAs.menu");
        verify(choice !== null, "The real Save project as menu precedes its chooser");
        tryCompare(choice, "opened", true, 2000, "The real Save menu opens before destination selection");
        const copy = Ui.find(Ui.windowRoot(app), "project.saveAs.copy");
        verify(copy !== null && !copy.checked, "Native Save as starts with copy optional and unchecked");
        if (copy.checked !== data.copy)
            clickControl("project.saveAs.copy");
        compare(copy.checked, data.copy, "Real input selects copy retention before choosing the destination");
        clickControl(data.zip ? "project.saveAs.zip" : "project.saveAs.folder");
        let dialogs;
        tryVerify(() => {
            dialogs = SettingsProof.projectFileDialogs(app, false).concat(SettingsProof.projectFileDialogs(app, true));
            return dialogs.length === 1;
        }, 2000, "The chosen Save-as route opens exactly one real native chooser");
        const dialog = dialogs[0];
        const selected = typeof dialog.selectedFile !== "undefined" ? dialog.selectedFile : dialog.selectedFolder;
        const expectedName = Session.project.name + (data.zip ? ".zip" : "");
        const target = SettingsProof.localPath(selected);
        const facts = {
            name: target.substring(target.lastIndexOf("/") + 1),
            expectedName,
            folder: SettingsProof.localPath(dialog.currentFolder),
            expectedFolder: directory
        };
        console.log("SAVE_CHOOSER_DEFAULTS " + JSON.stringify(facts));
        verify(facts.name === expectedName && facts.folder === directory, "Every native chooser receives the project name and its current folder: " + JSON.stringify(facts));
        dialog.close();
    }
    function test_drop_data() {
        const rows = [];
        for (const projectName of cases)
            for (const route of ["folder", "record", "zip"])
                rows.push({
                    tag: projectName + "-" + route,
                    projectName,
                    route
                });
        return rows;
    }
    function test_drop(data) {
        application();
        const input = routeInput(data.projectName, data.route);
        verify(SettingsProof.dropProject(app, input), "The real window accepts a URL drag and drop for folders, records and ZIPs");
        tryVerify(() => Session.hasProject && Session.lastError === "", 4000, "The accepted drop opens the actual project after its queued signal handler returns");
        const name = Session.project.name;
        const cell = Session.project.currentStructure.cell.lengthA.value;
        Session.closeProject();
        verify(Session.openProject(input), "The dropped project's same input remains readable");
        compare(Session.project.name, name, "Drag and drop preserves exactly the same project identity as Open");
        compare(Session.project.currentStructure.cell.lengthA.value, cell, "Drag and drop preserves the exact independently loaded model value");
    }
    function saveChoice(zip, copy, target) {
        clickControl("project.saveAs");
        const dialog = findChild(app, "project.saveAs.menu");
        verify(dialog !== null, "Save as first opens the application destination menu");
        tryCompare(dialog, "opened", true, 2000, "The application Save project as menu finishes opening");
        const folder = Ui.find(Ui.windowRoot(app), "project.saveAs.folder"), archive = Ui.find(Ui.windowRoot(app), "project.saveAs.zip"), checkbox = Ui.find(Ui.windowRoot(app), "project.saveAs.copy");
        verify(folder && archive && checkbox, "Save as exposes native folder, zip and copy destinations");
        verify(folder.enabled && archive.enabled && !checkbox.checked, "Each native Save as enables both formats with copy initially unchecked");
        if (copy)
            clickControl("project.saveAs.copy");
        compare(checkbox.checked, copy, "Real input selects whether Save as keeps the current location");
        clickControl(zip ? "project.saveAs.zip" : "project.saveAs.folder");
        let dialogs;
        tryVerify(() => {
            dialogs = SettingsProof.projectFileDialogs(app, false);
            return dialogs.length === 1;
        }, 2000, "Confirming Save as opens exactly one system destination dialog");
        const facts = SettingsProof.projectDialogFacts(dialogs[0]);
        verify(facts.systemFile, "Both ZIP and new-folder destinations use the actual save FileDialog so the name can be entered: " + JSON.stringify(facts));
        verify(/^Save$/i.test(facts.acceptLabel), "Both destination formats confirm the entered name with Save");
        verify(SettingsProof.chooseProjectLocation(dialogs[0], target, false), "The system dialog supplies the chosen persistent destination");
        compare(Session.lastError, "", "The selected Save as operation completes without a refusal");
    }
    function canonicalProject(projectName) {
        const source = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/" + projectName + "/project"));
        verify(SettingsProof.write(source, "reports/opaque.html", "<p>Independent carried report</p>\n"), "The cross-surface archive fixture contains an independent report");
        verify(Session.openProject(source), "The save operation starts on the independently committed real project");
        const folder = SettingsProof.emptyDirectory();
        verify(Session.saveAs(folder), "A canonical saved folder supplies the independent archive member bytes");
        return folder;
    }
    function evidence(value) {
        console.log("PROJECT_ARCHIVE_EVIDENCE " + JSON.stringify(value));
    }
    function compareFolder(actual, expected) {
        compare(Object.keys(actual).sort().join("\n"), Object.keys(expected).sort().join("\n"), "A folder copy retains exactly the source member names");
        for (const name of Object.keys(expected))
            compare(actual[name], expected[name], "A folder copy retains the exact independently saved member bytes: " + name);
    }
    function structureInput(value) {
        const lines = Qt.atob(value).split("\n"), entries = [];
        const derived = ["_atom_sites_cartn_transform", "_space_group_symop", "_expanded_atom_site", "_geom_bond"];
        let head = [], body = [], key = "", quoted = false, loopKeys = false;
        function finish() {
            if (!key)
                return;
            while (body.length && !body[body.length - 1].trim())
                body.pop();
            const category = key.replace(/^loop:/, "").split(".")[0];
            if (!derived.includes(category))
                entries.push([key, body.join("\n").replace(/^_edi.schema_version [34]$/m, "_edi.schema_version <3-or-4>")]);
        }
        for (const line of lines) {
            const start = !quoted && (line.trim() === "loop_" || (line.startsWith("_") && !(loopKeys && line.trim().split(/\s+/).length === 1)));
            if (start) {
                finish();
                body = [];
                key = line.trim() === "loop_" ? "loop" : line.split(/\s+/)[0];
                loopKeys = key === "loop";
            } else if (key === "loop" && loopKeys && line.startsWith("_")) {
                key = "loop:" + line.split(".")[0];
            } else if (loopKeys && line.trim() && !line.startsWith("_")) {
                loopKeys = false;
            }
            if (!key)
                head.push(line);
            else
                body.push(line);
            if (line.startsWith(";"))
                quoted = !quoted;
        }
        finish();
        return JSON.stringify([head, entries.sort((a, b) => a[0].localeCompare(b[0]))]);
    }
    function saveStamp(text) {
        const rows = text.match(/^_metadata\.last_modified[^\n]*$/gm) || [];
        compare(rows.length, 1, "A copied project retains exactly one declared last-save timestamp");
        const stamp = rows[0].match(/"(\d{2}) ([A-Za-z]{3}) (\d{4}) (\d{2}):(\d{2}):(\d{2})"$/);
        verify(stamp !== null, "The last-save value retains the declared STAR UTC timestamp format");
        const month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].indexOf(stamp[2]);
        verify(month >= 0, "The saved UTC timestamp names a real calendar month");
        return {
            row: rows[0],
            seconds: Date.UTC(Number(stamp[3]), month, Number(stamp[1]), Number(stamp[4]), Number(stamp[5]), Number(stamp[6])) / 1000
        };
    }
    function compareRecalculatedCopy(actual, expected, started, finished) {
        compare(Object.keys(actual).sort().join("\n"), Object.keys(expected).sort().join("\n"), "A recalculated copy retains every member name");
        for (const name of Object.keys(expected)) {
            if (name.startsWith("structures/") && name.endsWith(".edi")) {
                compare(structureInput(actual[name]), structureInput(expected[name]), "A recalculated copy retains every non-derived structure byte: " + name);
            } else if (name.startsWith("experiments/") && name.endsWith(".edi") && /^_experiment_type.sample_form[ \t]+"single crystal"$/m.test(Qt.atob(expected[name]))) {
                verify(Qt.atob(actual[name]).includes("\n_refln.intensity_calc\n"), "A recalculated single-crystal copy writes its reflection results: " + name);
            } else if (name === "project.edi") {
                const before = Qt.atob(expected[name]), after = Qt.atob(actual[name]);
                const oldStamp = saveStamp(before), newStamp = saveStamp(after);
                verify(newStamp.seconds >= Math.max(Math.floor(started / 1000), oldStamp.seconds + 1) && newStamp.seconds <= Math.max(Math.floor(finished / 1000), oldStamp.seconds + 1), "A newly saved folder copy advances its save timestamp within the independently observed save interval");
                compare(after.replace(newStamp.row, "<last-save-time>"), before.replace(oldStamp.row, "<last-save-time>"), "A folder copy retains every project byte except its independently checked last-save timestamp");
            } else {
                compare(actual[name], expected[name], "A recalculated copy retains unrelated member bytes: " + name);
            }
        }
    }
    function test_save_copy_data() {
        const rows = [];
        for (const projectName of cases)
            for (const zip of [false, true])
                rows.push({
                    tag: projectName + (zip ? "-zip" : "-folder"),
                    projectName,
                    zip
                });
        return rows;
    }
    function test_save_copy(data) {
        application();
        const folder = canonicalProject(data.projectName);
        const original = SettingsProof.projectFolderBytes(folder), location = Session.projectLocation, path = Session.project.path;
        const destination = data.zip ? SettingsProof.childUrl(SettingsProof.emptyDirectory(), "copy.zip") : SettingsProof.emptyDirectory();
        const started = Date.now();
        saveChoice(data.zip, true, destination);
        const finished = Date.now();
        compare(Session.projectLocation, location, "Save a copy leaves the current persistent location unchanged");
        compare(Session.project.path, path, "Save a copy leaves the open project's working location unchanged");
        compareFolder(SettingsProof.projectFolderBytes(folder), original);
        if (data.zip) {
            const archive = SettingsProof.projectArchiveBytes(destination);
            verify(archive.length > 0, "Save a copy as Zip archive writes a real nonempty archive");
            evidence({
                kind: "copy",
                started,
                finished,
                original,
                archive
            });
        } else {
            const saved = SettingsProof.projectFolderBytes(destination);
            compareRecalculatedCopy(saved, original, started, finished);
            evidence({
                kind: "copy",
                started,
                finished,
                original,
                saved
            });
        }
    }
    function test_save_zip_data() {
        return cases.map(projectName => ({
                    tag: projectName,
                    projectName
                }));
    }
    function test_save_zip(data) {
        application();
        canonicalProject(data.projectName);
        const archive = SettingsProof.childUrl(SettingsProof.emptyDirectory(), "current.zip");
        saveChoice(true, false, archive);
        compare(Session.projectLocation, SettingsProof.localPath(archive), "Save as Zip archive makes the chosen ZIP the current persistent location");
        verify(!Session.needsSaveAs, "A ZIP-saved project has a persistent destination for its next Save");
        const first = SettingsProof.projectArchiveBytes(archive);
        verify(first.length > 0, "Save as Zip archive publishes its first real archive");
        Session.project.name = "zip-next-save";
        verify(Session.project.modified, "The next ZIP Save exercises a real model edit");
        verify(Session.save(), "The next Save rewrites the current ZIP successfully");
        const second = SettingsProof.projectArchiveBytes(archive);
        verify(second.length > 0 && second !== first, "The next Save actually replaces the ZIP bytes");
        compare(Session.projectLocation, SettingsProof.localPath(archive), "Repeated Save keeps the same ZIP location");
        const folder = Session.project.path;
        evidence({
            kind: "rewrite",
            original: SettingsProof.projectFolderBytes(Session.projectDirectoryUrl(folder)),
            archive: second,
            name: "zip-next-save"
        });
        Session.closeProject();
        verify(Session.openProject(archive), "The rewritten ZIP reopens through the ordinary application route");
        compare(Session.project.name, "zip-next-save", "The rewritten ZIP contains the edited scientific project's current state");
    }
    function test_browser_warning_save_as_requires_confirmation() {
        application();
        canonicalProject(cases[2]);
        const warning = findChild(app, "webStorageWarning");
        const choice = findChild(app, "saveAs.choice");
        verify(warning !== null && choice !== null, "The real application retains its browser warning and delegated Save-as dialog");
        // Open the actual warning on the native host to inspect its unchanged action;
        // browser storage and download behavior remain in the Chromium consumer.
        warning.open();
        tryCompare(warning, "opened", true, 2000, "The warning finishes opening before real action input");
        const saveAs = warning.standardButton(Dialog.Apply);
        verify(saveAs !== null && saveAs.enabled && /Save project as/.test(saveAs.text), "The actual warning exposes its enabled Save-as action");
        verify(waitForPolish(saveAs), "The warning action completes layout before pointer input");
        mouseClick(saveAs, saveAs.width / 2, saveAs.height / 2);
        tryCompare(choice, "opened", true, 2000, "Warning Save-as opens the surviving confirmation dialog");
        let renderedChoice;
        tryVerify(() => {
            renderedChoice = Ui.find(Ui.windowRoot(app), "project.saveChoice");
            return renderedChoice !== null;
        }, 2000, "The browser confirmation observer targets the actual named column in the visual tree");
        verify(renderedChoice instanceof Item, "The observed confirmation column is a visual Item supported by the browser hook");
        verify(waitForPolish(renderedChoice), "The observed confirmation column completes its real layout");
        verify(renderedChoice.width > 0 && renderedChoice.height > 0, "The browser confirmation target has a positive rendered extent");
        compare(SettingsProof.projectFileDialogs(app, false).concat(SettingsProof.projectFileDialogs(app, true)).length, 0, "The warning route cannot reach a chooser before its dialog is confirmed");
        const ok = choice.standardButton(Dialog.Ok);
        verify(ok !== null && ok.enabled, "The surviving Save-as dialog exposes its actual confirmation control");
        verify(waitForPolish(ok), "The surviving confirmation completes layout before pointer input");
        mouseClick(ok, ok.width / 2, ok.height / 2);
        let dialogs;
        tryVerify(() => {
            dialogs = SettingsProof.projectFileDialogs(app, false).concat(SettingsProof.projectFileDialogs(app, true));
            return dialogs.length === 1;
        }, 2000, "Confirming warning Save-as reaches exactly one real system chooser");
        tryCompare(choice, "opened", false, 2000, "Confirmation closes the actual Save-as choice dialog");
        tryCompare(renderedChoice, "visible", false, 2000, "The same visual confirmation target becomes hidden after real acceptance");
        dialogs[0].close();
    }
    function test_save_unwritable_data() {
        return [
            {
                tag: "read-only-zip",
                example: false
            },
            {
                tag: "bundled-example",
                example: true
            }
        ];
    }
    function test_save_unwritable(data) {
        application();
        let input;
        if (data.example) {
            verify(Session.openExample(cases[0]), "The no-write-back route opens a real bundled example");
        } else {
            input = SettingsProof.copyProjectArchive(Probe.repoUrl("tests/fixtures/project_archive/" + cases[0] + ".zip"), true);
            verify(input.toString().length > 0 && !SettingsProof.archiveLocationWritable(input), "The read-only ZIP fixture prevents both file writes and replacement through its parent directory");
            verify(Session.openProject(input), "The no-write-back route opens the actual read-only ZIP");
        }
        tryVerify(() => Session.hasProject, 4000, "The example or read-only archive finishes opening before its save route is exercised");
        const before = data.example ? "" : SettingsProof.projectArchiveBytes(input);
        Session.project.name = "needs-new-location";
        verify(Session.needsSaveAs, "A bundled example or genuinely read-only ZIP requires a new destination");
        clickControl("appBar.button.save");
        const dialog = findChild(app, "saveAs.choice");
        verify(dialog !== null, "Ordinary Save keeps its fallback format dialog for an unwritable source");
        tryCompare(dialog, "opened", true, 2000, "Ordinary Save asks for a destination instead of a write error");
        if (!data.example)
            compare(SettingsProof.projectArchiveBytes(input), before, "Asking for another destination leaves every read-only input ZIP byte intact");
        dialog.close();
    }
    function test_save_folder_choice() {
        application();
        canonicalProject(cases[2]);
        const destination = SettingsProof.emptyDirectory();
        saveChoice(false, false, destination);
        compare(Session.projectLocation, SettingsProof.localPath(destination), "Folder Save as makes the selected folder the persistent project location");
        verify(!Session.needsSaveAs, "A folder chosen with Choose or Save supports ordinary later Saves");
    }
}
