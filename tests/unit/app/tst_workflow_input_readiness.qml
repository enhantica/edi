// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "WorkflowInputReadiness"
    when: windowShown
    property var app: null
    readonly property var workflowNames: ["project", "structure", "experiment", "analysis", "report"]
    Component {
        id: application
        Main {}
    }
    Component {
        id: unrelatedPreparingItem
        Item {
            objectName: "appBar.tab.unrelated"
            readonly property bool preparing: true
            width: 1
            height: 1
        }
    }

    function init() {
        failOnWarning(Probe.softwareOffscreenWithoutGl() ? /\A(?!(?:QRhiGles2: Failed to create (?:temporary context|context)|window doesn\x27t exist\.)\z)[\s\S]*\z/ : /.*/);
        Session.closeProject();
        app = application.createObject(null, {width: 1280, height: 800, visible: true});
        verify(app !== null, "Startup input uses the actual production Main window");
        app.requestActivate();
        tryCompare(app, "active", true, 2000, "The normal actor owns real pointer input");
        app.update();
        verify(waitForRendering(app.contentItem), "The initial no-project application renders before opening");
        Ui.click(test, Probe, app, "appBar.tab.home");
        Ui.click(test, Probe, app, "home.start");
        const loader = app.contentArea[AppState.Page.Project];
        tryVerify(() => AppState.projectPageEnabled && loader.status === Loader.Ready && loader.item !== null,
                  10000, "The established real Home Start admission loads the no-project Project page");
        Ui.click(test, Probe, app, "appBar.tab.project");
        compare(Ui.page(app), loader, "The real Project viewport is admitted before opening");
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

    function actualTabs() {
        // Independent observation of the five declared real controls, not Ui's
        // new preparing-population discovery or a manufactured loader state.
        return workflowNames.map(name => {
            const tab = findChild(app, "appBar.tab." + name);
            verify(tab !== null && tab.page !== null, "The real window declares its " + name + " loader tab");
            return tab;
        });
    }

    function snapshot(tabs) {
        return tabs.map(tab => ({name: tab.objectName, wanted: tab.pageWanted,
                                preparing: tab.preparing, status: tab.page.status,
                                enabled: tab.enabled}));
    }

    function test_real_opening_before_original_input_pipeline_data() {
        return ["appBar.tab.project", "appBar.tab.analysis", "sideBar.tab.basic"].map(name => ({tag: name, name}));
    }

    function test_real_opening_before_original_input_pipeline(data) {
        const tabs = actualTabs();
        const source = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/sc-neut-tof_taurine-senju/project"));
        verify(Session.openProject(source), "The unchanged readiness fixture opens through the original real owner");
        const project = Session.project;
        const before = snapshot(tabs);
        console.log("WORKFLOW_INPUT_BEFORE " + JSON.stringify(before));
        verify(before.every(tab => tab.wanted), "The real complete project requests every workflow page");
        verify(before.some(tab => tab.preparing), "The witness actually enters declared asynchronous page preparation");
        // No extra wait, forced loader/selection/enablement or fake TestCase.
        // Project is the early page; the sidebar target has no preparing flag.
        Ui.click(test, Probe, app, data.name);
        const after = snapshot(tabs);
        console.log("WORKFLOW_INPUT_AFTER " + JSON.stringify(after));
        verify(after.every(tab => !tab.preparing && tab.status === Loader.Ready),
               "Whole-window settling starts only after every actual requested page finishes preparation");
        compare(Session.project, project, "Preparation never replaces or synthesizes the actual project");
        const target = Ui.control(Probe, app, data.name);
        verify(target !== null && target.enabled && Ui.exposed(target), "The original target is genuinely exposed and enabled");
        compare(target.checked, true, "The original real pointer/selection path still selects the requested tab");
    }

    function test_missing_disabled_and_unrelated_flags_are_not_startup() {
        const tabs = actualTabs();
        compare(Session.hasProject, false, "This control has no project opening underway");
        verify(tabs.every(tab => !tab.preparing), "The public phase distinguishes no project from preparation");
        const analysis = findChild(app, "appBar.tab.analysis");
        compare(analysis.enabled, false, "The actual no-project Analysis tab is disabled for its original reason");
        compare(Ui.preparingWorkflowTabs(app).length, 0, "A disabled nonpreparing control gets no startup allowance");
        compare(Ui.control(Probe, app, "appBar.tab.missing"), null, "A genuinely missing input remains missing");

        const host = tabs[0].contentItem;
        verify(host !== null, "The actual tab exposes its real visual content owner");
        const item = unrelatedPreparingItem.createObject(host, {parent: host});
        verify(item !== null, "A real unrelated Qt Item supplies the adversarial property");
        try {
            verify(Render.descendants(app.appBarCentralTabs).includes(item), "The phase discovery actually reaches the unrelated object");
            compare(item.preparing, true, "The unrelated flag is really armed");
            compare(Ui.preparingWorkflowTabs(app).length, 0,
                    "Only the declared real workflow-tab population may delay normal layout/input checks");
        } finally {
            item.destroy();
        }
    }
}
