// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0

ExperimentWorkflowSession {
    function cleanup() {
        const panels = Probe.objectsWithProperty(app, "objectName").filter(item => item.objectName === "tutorial");
        if (panels.length === 1 && panels[0].opened) panels[0].stop();
        cleanupOnlineControls();
    }
    function beginContinuationTutorial(id) {
        resetProject(false);
        launchTutorial(id);
        const panel = tutorialPanel();
        tryCompare(panel, "opened", true, 3000, "The actual written tutorial opens before its request is held");
        if (Session.project === null)
            verify(Session.createProject("request_tutorial", "Continuation owner", String(SettingsProof.emptyDirectory())),
                   "The file-staging witness creates its temporary tutorial owner through the ordinary Create route");
        tryVerify(() => Session.project !== null && !Session.project.calculating && Probe.datasetReady(Session.project), 5000,
                  "The tutorial owner is ready before creating a deferred request");
        return panel;
    }
    function pendingStaging(panel, check) {
        panel.stagedFolder = "";
        panel.filesSaved = false;
        panel.perform("files-saved");
        const waiting = panel.afterStaging;
        verify(waiting !== null && waiting.request !== undefined && waiting.request !== null,
               "Every pending tutorial continuation carries its actual returned request identity");
        waiting.check = check;
        return waiting;
    }
    function deliverTutorial(kind, request, folder) {
        if (kind === "success") Session.tutorialFilesStaged(request, folder);
        else Session.tutorialFilesFailed(request, "Independent earlier-request failure");
    }
    function check_tutorial_request_ownership_data() {
        const rows = [];
        for (const accident of ["repeat", "back", "stop-new", "new-tutorial", "project-replace", "source-change", "save-files"])
            for (const order of ["old-success", "old-failure", "new-before-old-success", "new-before-old-failure"])
                rows.push({tag:accident + "-" + order, accident:accident, order:order});
        return rows;
    }
    function check_tutorial_request_ownership(data) {
        let panel = beginContinuationTutorial(data.accident === "repeat" ? "pd-neut-cwl_lbco-hrpt" : "pd-neut-cwl_lbco_simulation");
        let old = pendingStaging(panel, "structures:2");
        if (data.accident === "back") {
            panel.step = Math.min(1, panel.steps.length - 1);
            panel.back();
        } else if (data.accident === "stop-new" || data.accident === "new-tutorial") {
            panel.stop();
            launchTutorial(data.accident === "new-tutorial" ? "pd-neut-cwl_lbco-hrpt" : "pd-neut-cwl_lbco_simulation");
            panel = tutorialPanel();
            tryCompare(panel, "opened", true, 3000, "A successor tutorial starts before the earlier reply is delivered");
        } else if (data.accident === "project-replace") {
            Session.closeProject();
            verify(Session.createProject("successor", "New request owner", String(SettingsProof.emptyDirectory())),
                   "A new project replaces the earlier continuation owner");
        } else if (data.accident === "source-change") {
            Session.onlineSources.add();
            Session.onlineSources.setKinds("new-source", ["structure", "data"]);
            const local = String(Qt.resolvedUrl("../../fixtures/online_sources/easydiffraction/"));
            Session.onlineSources.setUrl("new-source", local);
            compare(Session.onlineSources.urlOf("new-source"), local, "The source change uses a second local collection without a network transport");
        } else if (data.accident === "repeat") {
            // File-staging is a controller capability, not a promised step in any case recipe.
            const fixture = Object.assign({}, panel.tutorial, {steps: [
                {title: "Stage files", text: "Controlled staging input", target: "workflow.project.mainContent", check: "files-saved"},
                {title: "Done", text: "Staging complete", target: "workflow.project.mainContent"}
            ]});
            panel.tutorial = fixture;
            panel.step = 0;
            panel.filesSaved = false;
            panel.next();
            panel.next();
            old = panel.afterStaging;
            verify(old !== null, "Repeated Next retains its actual pending file request");
            old.check = "structures:2";
        }
        if (!panel.opened) {
            launchTutorial("pd-neut-cwl_lbco_simulation");
            panel = tutorialPanel();
            tryCompare(panel, "opened", true, 3000, "A closed predecessor is followed by a new admitted tutorial");
        }
        if (Session.project === null)
            verify(Session.createProject("request_successor", "Successor continuation owner", String(SettingsProof.emptyDirectory())),
                   "The successor tutorial creates its own ordinary project before requesting files");
        tryVerify(() => Session.project !== null && !Session.project.calculating && Probe.datasetReady(Session.project), 5000,
                  "The successor owner is ready before its independent pending request");
        const project = Session.project;
        const before = project.structures.count;
        const current = pendingStaging(panel, "structures:" + (before + 1));
        verify(current.request !== old.request, "Different accepted tutorial requests have distinct identities");
        const folder = Qt.resolvedUrl("../../fixtures/online_sources/easydiffraction/");
        if (data.accident === "save-files") {
            const saved = Session.saveTutorialFiles(SettingsProof.emptyDirectory());
            verify(saved !== undefined && saved !== null && saved !== current.request, "Save files owns a separate request identity");
            panel.savingRequest = saved;
            Session.tutorialFilesFailed(saved, "Independent Save files refusal");
            compare(panel.afterStaging, current, "A Save files failure never clears an unrelated staging continuation");
            Session.tutorialFilesSaved(saved);
            compare(panel.afterStaging, current, "A Save files completion never consumes a staging continuation");
        }
        const oldKind = data.order.endsWith("success") ? "success" : "failure";
        if (data.order.startsWith("new-before")) {
            deliverTutorial("success", current.request, folder);
            compare(panel.afterStaging, null, "The matching current reply consumes only its own continuation");
            compare(project.structures.count, before + 1, "The current continuation executes its actual action once");
            const acceptedFolder = panel.stagedFolder;
            deliverTutorial(oldKind, old.request, Qt.resolvedUrl("../../fixtures/experiment_workflow/"));
            compare(panel.stagedFolder, acceptedFolder, "An older reply cannot replace the already accepted folder");
            compare(project.structures.count, before + 1, "An older reply cannot replay a completed action");
        } else {
            deliverTutorial(oldKind, old.request, Qt.resolvedUrl("../../fixtures/experiment_workflow/"));
            compare(panel.afterStaging, current, "An earlier success or failure preserves the successor request's pending action");
            compare(project.structures.count, before, "The earlier reply cannot execute the successor action early");
            compare(panel.stagedFolder, "", "An earlier reply never publishes its folder under a successor request");
            deliverTutorial("success", current.request, folder);
            compare(panel.afterStaging, null, "The matching successor reply still completes after rejecting the earlier reply");
            compare(project.structures.count, before + 1, "The successor continuation executes its real action exactly once");
        }
    }
    function check_tutorial_producer_tags_each_terminal_reply() {
        beginContinuationTutorial("pd-neut-cwl_lbco_simulation");
        const replies = [];
        const staged = function(request, folder) { replies.push({request:request, kind:"staged"}); };
        const failed = function(request, reason) { replies.push({request:request, kind:"failed"}); };
        const saved = function(request) { replies.push({request:request, kind:"saved"}); };
        verify(typeof Session.tutorialFilesSaved === "function", "Save files has its own tagged terminal signal");
        Session.tutorialFilesStaged.connect(staged);
        Session.tutorialFilesFailed.connect(failed);
        Session.tutorialFilesSaved.connect(saved);
        try {
            const first = Session.stageTutorialFiles();
            const second = Session.saveTutorialFiles(SettingsProof.emptyDirectory());
            verify(first !== undefined && second !== undefined && first !== second,
                   "Each actual staging and Save files request returns its own identity");
            tryVerify(() => replies.some(row => row.request === first) && replies.some(row => row.request === second), 5000, "Both requested identities receive their own actual terminal outcomes");
            compare(replies.filter(row => row.request === first).length, 1, "The stage receiver carries its originating identity through exactly one terminal reply");
            compare(replies.filter(row => row.request === second).length, 1, "The Save files receiver carries its originating identity through exactly one terminal reply");
        } finally {
            Session.tutorialFilesStaged.disconnect(staged);
            Session.tutorialFilesFailed.disconnect(failed);
            Session.tutorialFilesSaved.disconnect(saved);
        }
    }
}
