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
        let item;
        tryVerify(() => {
            item = Ui.control(Probe, app, name);
            return item !== null && item.enabled && Ui.clickPoint(item) !== null && !Ui.moving(app.contentItem);
        }, 4000, "The actual project action is enabled in its settled viewport: " + name);
        verify(waitForPolish(item), "The actual project action finishes layout before pointer input");
        app.update();
        verify(waitForRendering(app.contentItem), "The actual application draws before project input");
        tryVerify(() => {
            item = Ui.control(Probe, app, name);
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
    readonly property var cases: ["sc-neut-tof_taurine_fit", "pd-neut-cwl_cosio-d20_scan-3f", "sc-neut-cwl_tb2ti2o7-heidi_basic"]
    function cleanup() {
        if (app) {
            app.close();
            app.destroy();
        }
        app = null;
        Session.closeProject();
    }
    function test_save_dialog_layout() {
        application();
        canonicalProject(cases[2]);
        clickControl("project.saveAs");
        const dialog = findChild(app, "saveAs.choice");
        verify(dialog !== null, "Save as geometry is observed on the real application dialog");
        tryCompare(dialog, "opened", true, 2000, "Save as geometry is measured after the real dialog opens");
        const folder = findChild(dialog.contentItem, "saveAs.folder"), zip = findChild(dialog.contentItem, "saveAs.zip"), copy = findChild(dialog.contentItem, "saveAs.copy");
        verify(folder && zip && copy, "The compact dialog exposes its actual format radios and separate copy checkbox");
        const folderEnd = folder.mapToItem(dialog.contentItem, 0, folder.height).y;
        const zipTop = zip.mapToItem(dialog.contentItem, 0, 0).y;
        const zipEnd = zip.mapToItem(dialog.contentItem, 0, zip.height).y;
        const copyTop = copy.mapToItem(dialog.contentItem, 0, 0).y;
        verify(zipTop >= folderEnd && copyTop - zipEnd > zipTop - folderEnd, "Folder and Zip archive form a tighter group than the separated Save a copy choice");
        const content = Math.max(folder.implicitWidth, zip.implicitWidth, copy.implicitWidth);
        const halfWidth = Math.round(AppSizes.messagesDialogContentWidth / 2);
        const expectedWidth = Math.max(content, halfWidth);
        verify(Math.abs(dialog.contentWidth - expectedWidth) <= 1, "Save as fits its widest choice with the recorded floor of about half the normal message width");
        verify(dialog.leftPadding > 0 && dialog.rightPadding > 0, "The compact format dialog retains the app's usual side margins");
        compare(dialog.width, dialog.contentWidth + dialog.leftPadding + dialog.rightPadding, "Dialog margins surround the compact content without clipping a choice");
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
        const actions = Render.descendants(group).filter(item => item.objectName.startsWith("project.") && typeof item.text === "string");
        const visible = actions.filter(item => item.visible);
        compare(visible.filter(item => /^Open project[.\u2026]/.test(item.text)).length, 1, "The Project page has one Open project action for records and ZIP archives");
        compare(visible.filter(item => /^Save project as[.\u2026]/.test(item.text)).length, 1, "The Project page has one Save project as action");
        compare(visible.filter(item => item.enabled).map(item => item.objectName).sort().join(","), ["project.create", "project.open", "project.saveAs"].sort().join(","), "Create, Open and Save as are the only working Get started actions");
        const url = visible.find(item => item.objectName === "project.openUrl");
        verify(url !== undefined && !url.enabled, "Open from URL stays present and disabled");
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
        verify(Session.openProject(Probe.repoUrl("docs/user/cli/sc-neut-tof_taurine_fit/project")), "The first opening starts on the real taurine project");
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
        verify(Session.openProject(Probe.repoUrl("docs/user/cli/sc-neut-tof_taurine_fit/project")), "Pending Save starts on the real taurine project");
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
    function chooseOpenFormat(zip) {
        const choice = findChild(app, "open.choice");
        verify(choice !== null, "Open first presents the same app format dialog on every platform");
        tryCompare(choice, "opened", true, 2000, "The Open format dialog is actually open before its system chooser");
        const format = findChild(choice.contentItem, zip ? "open.zip" : "open.folder");
        verify(format && format.enabled, "The selected Open format is supported on this platform");
        mouseClick(format, format.width / 2, format.height / 2);
        const ok = choice.standardButton(Dialog.Ok);
        mouseClick(ok, ok.width / 2, ok.height / 2);
    }
    function test_open_dialog(data) {
        application();
        const input = routeInput(data.projectName, data.route);
        clickControl("project.open");
        chooseOpenFormat(data.route === "zip");
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
            clickControl("project.open");
            chooseOpenFormat(true);
            let dialogs;
            tryVerify(() => {
                dialogs = SettingsProof.projectFileDialogs(app, false);
                return dialogs.length === 1;
            }, 2000, "The Get started Open project button exposes one real native file chooser");
            verify(SettingsProof.chooseProjectLocation(dialogs[0], input, false), "The native chooser accepts the actual browser-produced ZIP");
        } else {
            RecentProjects.remember(SettingsProof.localPath(input));
            RecentProjects.refresh();
            const group = Ui.control(Probe, app, "group.recentProjects");
            verify(group !== null, "Recent projects is present in the real Project page");
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
        const choice = findChild(app, "saveAs.choice");
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
        const choice = findChild(app, "saveAs.choice");
        verify(choice !== null, "The real Save-as format dialog precedes its chooser");
        tryCompare(choice, "opened", true, 2000, "The real Save-as dialog opens before format selection");
        const format = findChild(choice.contentItem, data.zip ? "saveAs.zip" : "saveAs.folder");
        const copy = findChild(choice.contentItem, "saveAs.copy");
        verify(format && copy, "The requested format and copy choices are actual controls");
        if (!format.checked)
            mouseClick(format, format.width / 2, format.height / 2);
        if (copy.checked !== data.copy)
            mouseClick(copy, copy.width / 2, copy.height / 2);
        const ok = choice.standardButton(Dialog.Ok);
        mouseClick(ok, ok.width / 2, ok.height / 2);
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
        const dialog = findChild(app, "saveAs.choice");
        verify(dialog !== null, "Save as first opens the application format-and-copy dialog");
        tryCompare(dialog, "opened", true, 2000, "The application Save as choice finishes opening");
        const folder = findChild(dialog.contentItem, "saveAs.folder"), archive = findChild(dialog.contentItem, "saveAs.zip"), checkbox = findChild(dialog.contentItem, "saveAs.copy");
        verify(folder && archive && checkbox, "Save as exposes Folder, Zip archive and Save a copy choices");
        verify(folder.checked && !archive.checked && !checkbox.checked, "Each Save as starts in Folder mode without Save a copy");
        const format = zip ? archive : folder;
        if (!format.checked) {
            verify(waitForPolish(format), "The chosen Save as format is laid out before input");
            mouseClick(format, format.width / 2, format.height / 2);
        }
        if (copy)
            mouseClick(checkbox, checkbox.width / 2, checkbox.height / 2);
        compare(format.checked, true, "Real input selects the required Save as format");
        compare(checkbox.checked, copy, "Real input selects whether Save as keeps the current location");
        const accept = dialog.standardButton(Dialog.Ok);
        verify(accept && accept.enabled, "The format choice has an actual enabled confirmation button");
        mouseClick(accept, accept.width / 2, accept.height / 2);
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
        saveChoice(data.zip, true, destination);
        compare(Session.projectLocation, location, "Save a copy leaves the current persistent location unchanged");
        compare(Session.project.path, path, "Save a copy leaves the open project's working location unchanged");
        compareFolder(SettingsProof.projectFolderBytes(folder), original);
        if (data.zip) {
            const archive = SettingsProof.projectArchiveBytes(destination);
            verify(archive.length > 0, "Save a copy as Zip archive writes a real nonempty archive");
            evidence({
                kind: "copy",
                original,
                archive
            });
        } else {
            compareFolder(SettingsProof.projectFolderBytes(destination), original);
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
        const before = data.example ? "" : SettingsProof.projectArchiveBytes(input);
        Session.project.name = "needs-new-location";
        verify(Session.needsSaveAs, "A bundled example or genuinely read-only ZIP requires a new destination");
        clickControl("appBar.button.save");
        const dialog = findChild(app, "saveAs.choice");
        verify(dialog !== null, "Ordinary Save routes an unwritable source to the actual Save as dialog");
        tryCompare(dialog, "opened", true, 2000, "Ordinary Save asks for a format and destination instead of a write error");
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
