// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiOnlineHttpFixture 1.0
import ReportAcceptance 1.0
import OnboardingAcceptance 1.0
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

OnlineLoadSession {
    SignalSpy { id: readySpy; target: Session.onlineSearch; signalName: "fileReady" }

    function cleanup() {
        if (!loadGroupsOnly) {
            const panel = Probe.objectsWithProperty(app, "objectName").find(item => item.objectName === "tutorial");
            if (panel && panel.tutorial !== null) panel.stop();
            const chooser = Probe.objectsWithProperty(app, "objectName").find(item => item.objectName === "tutorials");
            if (chooser && chooser.visible) chooser.close();
        }
        cleanupOnlineControls();
    }

    function sourceDocument() {
        const file = SettingsProof.fileObservation(fixture({file: "easydiffraction/"}), "index.json");
        verify(file.exists, "Boundary cases start from the independent committed index");
        return JSON.parse(file.text);
    }
    function projectEntry(id) {
        const entry = sourceDocument().entries.find(row => row.kind === "project");
        entry.id = id;
        delete entry.files[0].sha256;
        delete entry.files[0].bytes;
        return entry;
    }
    function exampleSource(entries) {
        verify(OnlineHttpFixture.attachExamples(Session), "Only the example transport is replaced");
        OnlineHttpFixture.clearExamples();
        Session.onlineSources.add();
        Session.onlineSources.setKinds("new-source", ["project"]);
        OnlineHttpFixture.exampleText(200, JSON.stringify({schema:"edi-data-index/1", entries:entries}));
        Session.onlineSources.setUrl("new-source", "https://examples.invalid");
        tryVerify(() => OnlineHttpFixture.exampleKnown(Session, entries[0].id), 3000,
                  "The fixture index is adopted before a project download starts");
        settle();
    }
    function queuedArchive(deferred = true) {
        verify(OnlineHttpFixture.exampleFile(200, fixture({file:"easydiffraction/projects/lbco-hrpt.zip"}), deferred),
               "The delayed project is an independently saved archive");
    }
    function check_example_ownership_data() {
        return ["close", "create", "ordinary-open", "reverse", "old-error"].map(tag => ({tag:tag}));
    }
    function check_example_ownership(data) {
        resetProject();
        const original = Session.project;
        original.description = "edited owner before download";
        exampleSource([projectEntry("owned-a"), projectEntry("owned-b")]);
        if (data.tag === "old-error") OnlineHttpFixture.exampleText(503, "", true);
        else queuedArchive();
        verify(Session.openExample("owned-a"), "The first Open admits a controlled pending download");
        verify(Session.openingExample, "The first example has not completed before the replacement action");
        let owner;
        if (data.tag === "reverse") {
            queuedArchive();
            verify(Session.openExample("owned-b"), "A second user Open receives its own completion authority");
            verify(OnlineHttpFixture.releaseExample(1), "The newer reply is delivered before the older one");
            tryVerify(() => Session.project !== original, 3000, "The newer example is adopted first");
            owner = Session.project;
            owner.description = "newer download wins";
        } else if (data.tag === "close") {
            Session.closeProject();
            owner = null;
        } else if (data.tag === "ordinary-open") {
            verify(Session.openProject(fixture({file:"easydiffraction/projects/lbco-hrpt.zip"})), "The intervening ordinary archive open succeeds independently");
            owner = Session.project;
            owner.description = "ordinary open wins";
        } else {
            verify(Session.createProject("replacement", "", String(SettingsProof.emptyDirectory())), "The user creates a newer project while the old download is pending");
            owner = Session.project;
            owner.description = "created owner wins";
        }
        const beforeError = Session.lastError;
        const description = owner ? owner.description : "";
        verify(OnlineHttpFixture.releaseExample(0), "The stale reply is exercised even after cancellation or replacement");
        settle();
        compare(Session.project, owner, "An older download cannot replace the current project or undo Close");
        if (owner) compare(owner.description, description, "A stale example preserves the newer owner's edits");
        compare(Session.lastError, beforeError, "An older failure cannot publish an error into a newer session");
    }
    function check_integrity_data() {
        const rows = [];
        for (const route of ["structure", "experiment", "data", "project"])
            for (const claim of ["digest", "size", "absent"])
                rows.push({tag:route + "-" + claim, route:route, claim:claim});
        return rows;
    }
    function check_integrity(data) {
        resetProject();
        const owner = Session.project;
        owner.description = "content claim must precede adoption";
        const entry = sourceDocument().entries.find(row => row.kind === data.route);
        if (data.claim === "digest") entry.files[0].sha256 = "0".repeat(64);
        else if (data.claim === "size") entry.files[0].bytes = OnlineHttpFixture.fileBytes(fixture({file:"easydiffraction/" + entry.files[0].path})) + 1;
        else { delete entry.files[0].sha256; delete entry.files[0].bytes; }
        if (data.route === "project") {
            entry.id = "checked-project";
            exampleSource([entry]);
            queuedArchive(false);
            verify(Session.openExample("checked-project"), "The example dispatch uses the index's retained content claims");
            tryCompare(Session, "openingExample", false, 3000, "The checked example download completes");
            settle();
            if (data.claim === "absent") {
                verify(Session.project !== owner && Session.project.experiments.count > 0, "Absent optional claims preserve successful project loading");
            } else {
                compare(Session.project, owner, "A wrong archive digest or size cannot replace the project");
                verify(Session.lastError !== "", "A rejected archive reports its content mismatch");
            }
            return;
        }
        const search = Session.onlineSearch;
        verify(OnlineHttpFixture.attach(search), "Popup content checks use the shipped download callback");
        OnlineHttpFixture.clear();
        openOnline({page:data.route === "structure" ? AppState.Page.Structure : AppState.Page.Experiment,
                    group:data.route === "structure" ? "structures" : "experiments",
                    action:data.route === "structure" ? "web" : data.route === "experiment" ? "experimentWeb" : "dataWeb"});
        Session.onlineSources.add();
        Session.onlineSources.setKinds("new-source", [data.route]);
        Session.onlineSources.setUrl("new-source", "https://index.invalid/" + data.route + "/" + data.claim);
        search.sourceId = "new-source";
        settle();
        verify(waitForPolish(app), "The replacement source fields finish layout before popup input");
        app.update();
        OnlineHttpFixture.enqueue(200, JSON.stringify({schema:"edi-data-index/1", entries:[entry]}));
        search.setField("id", entry.id);
        search.search();
        tryCompare(search, "busy", false, 3000, "The injected index search finishes before loading its bytes");
        compare(search.results.count, 1, "The injected index exposes its requested kind: " + search.message + " kind=" + search.kind + " source=" + search.sourceId + " requests=" + OnlineHttpFixture.requests());
        readySpy.clear();
        verify(OnlineHttpFixture.enqueueFile(200, fixture({file:"easydiffraction/" + entry.files[0].path})), "The popup receives the independently saved file bytes");
        click(onlineControl("load.0"));
        tryCompare(search, "busy", false, 3000, "The content check finishes before publishing the loader input");
        if (data.claim === "absent") compare(readySpy.count, 1, "Absent optional claims preserve an ordinary download");
        else {
            compare(readySpy.count, 0, "A wrong digest or size must never reach the ordinary loader");
            verify(search.message !== "", "A mismatched popup file reports why it was refused");
            compare(Session.project, owner, "An integrity refusal preserves project ownership");
        }
    }
    function check_formula_seam_data() {
        return ["cod", "collection"].map(tag => ({tag:tag}));
    }
    function check_formula_seam(data) {
        resetProject();
        const search = Session.onlineSearch;
        verify(OnlineHttpFixture.attach(search), "Malformed formula search is checked before any network request");
        OnlineHttpFixture.clear();
        search.kind = "structure";
        search.sourceId = data.tag === "cod" ? "cod" : "easydiffraction";
        search.setField("formula", "C1.2.3");
        search.search();
        tryCompare(search, "busy", false, 3000, "Malformed count tokens are refused without a pending query");
        verify(search.message.toLowerCase().includes("formula"), "The popup must report the invalid chemical formula");
        compare(OnlineHttpFixture.requests().length, 0, "Malformed decimal counts must not be normalized into a COD or collection query");
    }
    function check_downloaded_working_copy() {
        resetProject();
        const source = fixture({file:"easydiffraction/projects/"});
        const before = SettingsProof.fileObservation(source, "lbco-hrpt.zip").base64;
        const previous = Session.project;
        verify(Session.openExample("lbco-hrpt-project"), "The writable-copy witness opens the downloaded archive");
        tryVerify(() => !Session.openingExample && Session.project !== previous, 3000,
                  "The downloaded example is adopted before its working copy is inspected");
        verify(OnlineHttpFixture.writableWorkingFiles(Session), "The downloaded project's metadata is owner-readable and writable");
        Session.project.description = "downloaded working-copy save witness";
        const target = SettingsProof.emptyDirectory();
        verify(Session.saveAs(target), "Save As uses the ordinary writer for the downloaded working project");
        verify(SettingsProof.fileObservation(target, "project.edi").text.includes("downloaded working-copy save witness"),
               "The chosen writable target contains the user's edited project");
        compare(SettingsProof.fileObservation(source, "lbco-hrpt.zip").base64, before,
                "Editing and saving a downloaded example never writes back into the source collection archive");
    }

    function check_initial_outage() {
        tryVerify(() => Session.examplesNotice !== "", 3000, "Failed startup discovery must explain why examples are unavailable");
    }
    function check_recovery_open() {
        const before = Session.project;
        verify(Session.openExample("pd-neut-cwl_lbco-hrpt"), "The next ordinary Open must rediscover a source restored after startup");
        tryVerify(() => Session.project !== before, 3000, "The recovered Open adopts the downloaded project without a Preferences mutation");
        compare(Session.examplesNotice, "", "Successful rediscovery retires the outage notice");
    }
    function check_empty_projects_notice() {
        tryVerify(() => Session.examplesNotice !== "", 3000, "An answering source with no project entries still explains that no examples can download");
    }
    function check_logical_source_data() {
        const rows = [{tag:"selector", stage:"selector", outcome:"primary"}];
        for (const stage of ["index", "file", "examples-index", "examples-file"])
            for (const outcome of ["primary", "fallback", "both-fail", "missing"])
                rows.push({tag:stage + "-" + outcome, stage:stage, outcome:outcome});
        return rows;
    }
    function check_logical_source(data) {
        resetProject();
        const search = Session.onlineSearch;
        const selector = openOnline({page:AppState.Page.Structure, group:"structures", action:"web"});
        if (data.stage === "selector") {
            compare(Array.from({length:selector.count}, (_, row) => selector.textAt(row)), ["COD", "EasyDiffraction"],
                    "The source selector exposes one EasyDiffraction row and no mirror row");
            return;
        }
        verify(OnlineHttpFixture.attach(search) && OnlineHttpFixture.attachExamples(Session),
               "Both production collection readers use socket-free injected locations");
        OnlineHttpFixture.clear();
        OnlineHttpFixture.clearExamples();
        const examples = data.stage.startsWith("examples-");
        const fileStage = data.stage.endsWith("file");
        const index = JSON.stringify(sourceDocument());
        const status = data.outcome === "missing" ? 404 : 503;
        // Source refresh exercises discovery too: give its own transport an independent index.
        if (!examples || fileStage) OnlineHttpFixture.exampleText(200, index);
        else {
            OnlineHttpFixture.exampleText(data.outcome === "primary" ? 200 : status, index);
            if (data.outcome === "fallback") OnlineHttpFixture.exampleText(200, index, true);
            if (data.outcome === "both-fail") OnlineHttpFixture.exampleText(status, "");
        }
        OnlineHttpFixture.useDefaultLocations(Session);
        settle();
        if (examples && !fileStage && data.outcome === "fallback") {
            tryVerify(() => OnlineHttpFixture.exampleRequests().length === 2, 3000, "Example discovery reaches the pending mirror reply");
            compare(Session.examplesNotice, "", "Examples do not announce an outage before the mirror has answered");
            verify(OnlineHttpFixture.releaseExample(0), "The responding mirror finishes example discovery");
        }
        if (examples) {
            if (fileStage) {
                tryVerify(() => OnlineHttpFixture.exampleKnown(Session, "lbco-hrpt-project"), 3000,
                          "The project index is available before exercising file-location fallback");
                if (data.outcome !== "primary") OnlineHttpFixture.exampleText(status, "");
                if (["primary", "fallback"].includes(data.outcome)) queuedArchive(false);
                if (data.outcome === "both-fail") OnlineHttpFixture.exampleText(status, "");
                const previous = Session.project;
                Session.openExample("lbco-hrpt-project");
                tryCompare(Session, "openingExample", false, 3000, "The example exhausts or completes its ordered locations");
                compare(Session.project !== previous, ["primary", "fallback"].includes(data.outcome),
                        "Examples adopt a project only after one ordered location succeeds");
            } else if (["primary", "fallback"].includes(data.outcome)) {
                tryVerify(() => OnlineHttpFixture.exampleKnown(Session, "lbco-hrpt-project"), 3000,
                          "Example discovery succeeds through the first responding location");
                compare(Session.examplesNotice, "", "A responding mirror suppresses the example outage notice");
            } else {
                tryVerify(() => Session.examplesNotice !== "", 3000,
                          "Examples explain exhausted locations or missing collection content");
            }
        } else {
            search.sourceId = "easydiffraction";
            if (fileStage || data.outcome === "primary") OnlineHttpFixture.enqueue(200, index);
            else {
                OnlineHttpFixture.enqueue(status, "");
                if (data.outcome === "fallback") OnlineHttpFixture.enqueue(200, index, true);
                if (data.outcome === "both-fail") OnlineHttpFixture.enqueue(status, "");
            }
            search.setField("id", "lbco");
            search.search();
            if (!fileStage && data.outcome === "fallback") {
                tryVerify(() => OnlineHttpFixture.requests().length === 2, 3000, "The popup reaches the pending mirror index reply");
                verify(search.busy && !search.unreachable, "The logical source stays pending rather than unavailable while its mirror can respond");
                verify(OnlineHttpFixture.release(0), "The responding mirror completes the index request");
            }
            tryCompare(search, "busy", false, 3000, "The popup finishes the ordered index attempt");
            if (fileStage) {
                compare(search.results.count, 1, "File fallback starts from the injected successful index");
                readySpy.clear();
                if (data.outcome !== "primary") OnlineHttpFixture.enqueue(status, "");
                if (["primary", "fallback"].includes(data.outcome))
                    verify(OnlineHttpFixture.enqueueFile(200, fixture({file:"easydiffraction/structures/lbco.cif"})),
                           "The responding location holds the independent CIF bytes");
                if (data.outcome === "both-fail") OnlineHttpFixture.enqueue(status, "");
                click(onlineControl("load.0"));
                tryCompare(search, "busy", false, 3000, "The popup finishes the ordered file attempt");
                compare(readySpy.count, ["primary", "fallback"].includes(data.outcome) ? 1 : 0,
                        "The popup publishes file bytes only after an ordered location succeeds");
            } else {
                compare(search.results.count, ["primary", "fallback"].includes(data.outcome) ? 1 : 0,
                        "The popup retains the same entry identity through location fallback");
            }
            if (["primary", "fallback"].includes(data.outcome))
                verify(!search.unreachable, "A healthy location suppresses the logical source's unavailable state");
            else compare(search.unreachable, data.outcome === "both-fail",
                         "Unavailable is reserved for exhausted locations, not a missing file");
        }
        const path = fileStage ? (examples ? "projects/lbco-hrpt.zip" : "structures/lbco.cif") : "index.json";
        const requests = (examples ? OnlineHttpFixture.exampleRequests() : OnlineHttpFixture.requests()).filter(url => url.endsWith("/" + path));
        const expected = ["https://raw.githubusercontent.com/enhantica/edi-data/main/" + path];
        if (["fallback", "both-fail"].includes(data.outcome)) expected.push("https://data.easydiffraction.org/" + path);
        compare(requests, expected, "The one logical collection attempts primary then mirror only for an outage");
    }
    function tutorialPanel() {
        const panels = Probe.objectsWithProperty(app, "objectName").filter(item => item.objectName === "tutorial");
        compare(panels.length, 1, "The production window owns the real tutorial panel");
        return panels[0];
    }
    function launchTutorial(id) {
        AppState.open(AppState.Page.Home);
        settle();
        const buttons = Probe.objectsWithProperty(app, "text").filter(item => item.visible && item.text === "Tutorials" && typeof item.clicked === "function");
        compare(buttons.length, 1, "Home exposes the actual Tutorials action");
        click(buttons[0]);
        const chooser = Probe.objectsWithProperty(app, "objectName").find(item => item.objectName === "tutorials");
        tryCompare(chooser, "opened", true, 3000, "The tutorial chooser finishes opening before selection");
        const name = "tutorials.row." + id;
        const row = Probe.objectsWithProperty(chooser, "objectName").concat(Render.descendants(chooser.contentItem)).find(item => item.objectName === name);
        verify(row !== undefined, "The chooser exposes the requested written tutorial");
        click(row);
        tryCompare(chooser, "visible", false, 3000, "Selecting a written tutorial closes the chooser");
    }
    function check_tour_download_preserves_owner() {
        resetProject();
        const owner = Session.project;
        owner.description = "unsaved project before Interface tour";
        const entry = projectEntry("pd-neut-cwl_lbco-hrpt");
        exampleSource([entry]);
        queuedArchive();
        launchTutorial("interface");
        compare(Session.project, owner, "The pending tour download cannot discard the edited user project");
        verify(OnlineHttpFixture.releaseExample(0), "The tour's asynchronous project reply is exercised");
        const panel = tutorialPanel();
        tryCompare(panel, "opened", true, 3000, "The Interface tour starts after its example is adopted");
        verify(Session.hasProjectSetAside, "The original project remains held for restoration across the download");
        verify(Session.project !== owner, "The tour uses a separate downloaded project");
        click(findChild(panel, "tutorial.stop"));
        tryCompare(Session, "project", owner, 3000, "Stopping the downloaded tour restores the exact original project");
        compare(owner.description, "unsaved project before Interface tour", "Tour restoration retains the user's unsaved edits");
    }
    function check_unavailable_tutorial_data() {
        return ["next", "save"].map(tag => ({tag:tag}));
    }
    function check_unavailable_tutorial(data) {
        resetProject();
        launchTutorial("fitting");
        const panel = tutorialPanel();
        tryCompare(panel, "opened", true, 3000, "The tutorial opens before an unavailable collection is exercised");
        if (data.tag === "save") {
            const folder = SettingsProof.emptyDirectory();
            panel.saveFiles(String(folder));
            settle();
            verify(!panel.filesSaved, "Unavailable tutorial files cannot be reported as saved");
            verify(!SettingsProof.fileObservation(folder, "lbco.cif").exists && !SettingsProof.fileObservation(folder, "hrpt.xye").exists,
                   "Save files must not substitute bundled resources when the collection is unavailable");
        } else {
            for (let attempt = 0; attempt < 14 && panel.current.check !== "files-saved"; ++attempt) {
                click(findChild(panel, "tutorial.next"));
                const dialog = SettingsProof.creationDialog(app);
                if (dialog && dialog.visible) dialog.projectParentDirectory = String(SettingsProof.emptyDirectory());
                settle();
            }
            compare(panel.current.check, "files-saved", "The actual Next flow reaches tutorial input staging");
            const step = panel.step;
            click(findChild(panel, "tutorial.next"));
            settle();
            verify(!panel.filesSaved, "Next must not substitute bundled inputs after collection failure");
            compare(panel.step, step, "A failed input stage cannot advance the written tutorial");
        }
        panel.stop();
    }

    function check_tutorial_files_data() {
        return ["next", "save"].map(tag => ({tag:tag}));
    }
    function check_tutorial_files(data) {
        resetProject();
        launchTutorial("fitting");
        const panel = tutorialPanel();
        tryCompare(panel, "opened", true, 3000, "The written fitting tutorial opens before its collection inputs are used");
        if (data.tag === "save") {
            const folder = SettingsProof.emptyDirectory();
            panel.saveFiles(String(folder));
            tryVerify(() => SettingsProof.fileObservation(folder, "lbco.cif").exists, 3000, "Save tutorial files completes from the injected collection");
            verify(SettingsProof.fileObservation(folder, "lbco.cif").text.includes("3.77"), "Saved CIF bytes come from the injected collection, not the bundled default");
            compare(SettingsProof.fileObservation(folder, "hrpt.xye").text, "21.5 117.25 0.75\n22.75 131.75 1.25\n25.125 123.5 1.5\n", "Save files preserves the independently authored injected pattern exactly");
            panel.stop();
            return;
        }
        let reachedData = false;
        for (let attempt = 0; attempt < 22 && !reachedData; ++attempt) {
            const check = panel.current ? panel.current.check : "";
            const next = findChild(panel, "tutorial.next");
            click(next);
            const dialog = SettingsProof.creationDialog(app);
            if (dialog && dialog.visible) dialog.projectParentDirectory = String(SettingsProof.emptyDirectory());
            settle();
            if (check === "structure:lbco")
                compare(Session.project.currentStructure.cell.lengthA.value, 3.77, "Next loads the collection CIF's independent cell value");
            if (check === "data") reachedData = true;
        }
        verify(reachedData, "Next reaches the measured-data step using the collection inputs");
        const experiment = Session.project.currentExperiment;
        compare(experiment.measuredPattern.count, 3, "The tutorial loads the injected three-point pattern");
        compare(Probe.rows(experiment.measuredPattern)[0].intensityMeas, 117.25, "Next uses the injected measured intensity rather than bundled HRPT data");
        panel.stop();
    }
}
