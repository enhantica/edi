// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0
import "NativeTurn.js" as Turn
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "StabilityFeedback"
    when: windowShown
    property var app
    property var form
    property var savedContact
    property string gateTurnSelector: ""
    Component {
        id: application
        Main {}
    }
    function named(name) {
        const found = Probe.objectsWithProperty(app, "objectName").filter(item => item.objectName === name);
        compare(found.length, 1, "ADR-0063: the production feedback flow exposes its named control " + name);
        return found[0];
    }
    function textControl(label) {
        const found = Probe.objectsWithProperty(app, "text").filter(item => item.text === label && Ui.rendered(item) && typeof item.clicked === "function");
        compare(found.length, 1, "ADR-0062: one visible action is labelled " + label);
        return found[0];
    }
    function press(item) {
        verify(item.enabled && waitForPolish(item), "ADR-0062: the real action is enabled and laid out");
        verify(waitForRendering(item), "ADR-0062: the current popup layout is rendered before pointer input");
        const point = Ui.clickPoint(item);
        verify(point !== null, "ADR-0062: the real action is exposed for pointer input");
        mouseClick(item, point.x, point.y);
    }
    function initTestCase() {
        verify(OnboardingProbe.prepareCrashLog().length > 0, "ADR-0062: native feedback starts a real run header and retains an independently crashed run before QML singleton use");
    }
    function init() {
        gateTurnSelector = Turn.begin(test, Probe, message => test.warn(message));
        if (test.qtest_results.functionName === "test_a_previous_crash_has_send_and_ok")
            verify(RunLog.crashedLog.length > 0, "ADR-0062: a separate abruptly exited process supplies a real retained log");
        else
            RunLog.dismissCrash();
        savedContact = [Preferences.feedbackName, Preferences.feedbackEmail, Preferences.feedbackAffiliation];
        Preferences.feedbackName = "Zoë Example";
        Preferences.feedbackEmail = "zoe@example.invalid";
        Preferences.feedbackAffiliation = "Example Institute";
        app = application.createObject(null);
        verify(app !== null && waitForRendering(app.contentItem), "ADR-0062: stability actions run in the rendered production application");
        form = named("feedback.form");
        form.endpoint = "https://feedback.example.invalid/feedback";
        form.transport = function () {
            fail("ADR-0063: popup acceptance never uses the network");
        };
    }
    function cleanupTestCase() {
        OnboardingProbe.finishHostLog();
    }
    function cleanup() {
        Session.closeProject();
        if (app)
            app.destroy();
        app = null;
        form = null;
        RunLog.dismissCrash();
        Preferences.feedbackName = savedContact[0];
        Preferences.feedbackEmail = savedContact[1];
        Preferences.feedbackAffiliation = savedContact[2];
        Turn.end(gateTurnSelector, message => test.warn(message));
    }
    function checkSendAndOk(message, filename) {
        tryVerify(() => Probe.objectsWithProperty(app, "text").filter(item => item.text === "Send to developers" && Ui.rendered(item) && typeof item.clicked === "function").length === 1, 2000, "ADR-0062: the queued production error popup opens before its actions are used");
        compare(Probe.objectsWithProperty(app, "text").filter(item => item.text === "Copy error message" && Ui.rendered(item) && typeof item.clicked === "function").length, 0, "2026-11-17 owner decision: error and crash popups have no Copy error message action");
        verify(textControl("OK").enabled, "2026-11-17 owner decision: every error popup can be dismissed with OK");
        verify(Probe.objectsWithProperty(app, "text").some(item => typeof item.text === "string" && Ui.rendered(item) && (message === "" ? /crash|unexpected/i.test(item.text) : item.text.includes(message))), "ADR-0062: the popup displays its diagnostic before Send is pressed");
        press(textControl("Send to developers"));
        tryCompare(form, "opened", true, 2000, "ADR-0062: Send opens the existing feedback form");
        compare(form.payload.kind, "feedback", "A reported error uses the shared feedback route");
        verify(message === "" ? named("feedback.text").text.length > 0 : named("feedback.text").text.includes(message), "ADR-0062: the actual diagnostic pre-fills the problem text");
        compare(Preferences.feedbackName, "Zoë Example", "ADR-0063: sending an error retains the saved name");
        compare(Preferences.feedbackEmail, "zoe@example.invalid", "ADR-0063: sending an error retains the saved email");
        compare(Preferences.feedbackAffiliation, "Example Institute", "ADR-0063: sending an error retains the saved affiliation");
        verify(named("feedback.include").checked, "2026-11-17 owner decision: Include app version, system and log is checked after Send");
        const payload = form.payload;
        verify(typeof payload.log === "string" && payload.log.length > 0, "ADR-0062: the report includes the diagnostic run log");
        if (filename !== "") {
            verify(Array.isArray(payload.attachments) && payload.attachments.some(file => file.name === filename), "ADR-0063: Send attaches the unreadable file with its original name");
            const wire = JSON.stringify(payload.attachments);
            verify(RunLog.homePath === "" || !wire.includes(RunLog.homePath), "ADR-0063: attachment metadata never exposes the home folder");
        }
    }
    function test_a_previous_crash_has_send_and_ok() {
        const popup = named("crash.popup");
        tryCompare(popup, "visible", true, 2000, "ADR-0062: the next start offers the real previous crash");
        checkSendAndOk("", "");
        verify(form.payload.log.includes("retained-crash-sentinel"), "ADR-0062: a previous crash report carries the independently flushed log");
    }
    function test_b_caught_event_error_shows_diagnostic_actions() {
        const message = "injected event error at item 17";
        RunLog.errorCaught(message);
        checkSendAndOk(message, "");
        verify(app.visible, "ADR-0062: a caught error leaves the rendered application open");
    }
    function test_b_failed_project_open_shows_diagnostic_actions() {
        verify(!Session.openProject(Probe.repoUrl("tests/fixtures/stability_inputs/absent-project")), "ADR-0062: a controlled project-open failure reaches the production error path");
        verify(Session.lastError.length > 0, "ADR-0062: the refusal supplies a diagnostic");
        checkSendAndOk(Session.lastError, "");
    }
    function test_c_unreadable_input_shows_location_and_attaches_file_data() {
        return [
            {
                tag: "structure",
                file: "unreadable.cif"
            },
            {
                tag: "experiment",
                file: "unreadable.edi"
            },
            {
                tag: "data",
                file: "unreadable.xye"
            }
        ];
    }
    function test_c_unreadable_input_shows_location_and_attaches_file(data) {
        verify(Session.createProject("Failure witness", ""), "ADR-0062: unreadable-file checks use a fresh real project");
        const project = Session.project;
        const url = Probe.repoUrl("tests/fixtures/stability_inputs/" + data.file);
        let accepted;
        if (data.tag === "structure")
            accepted = project.loadStructure(url);
        else if (data.tag === "experiment")
            accepted = project.loadExperiments([url]);
        else {
            verify(project.createExperiment(), "ADR-0062: unreadable data is loaded into a real experiment");
            accepted = project.loadData(0, url);
        }
        verify(!accepted, "ADR-0062: the independent malformed input must be refused");
        const message = project.lastError || Session.lastError;
        verify(message.length > 0 && /line|item|row|_atom_site|NOT_A_NUMBER/i.test(message), "ADR-0062: an unreadable file identifies a line, row or item");
        checkSendAndOk(message, data.file);
    }
    function test_d_non_ascii_datablock_survives_load_save_and_reopen() {
        verify(Session.createProject("Unicode witness", ""), "ADR-0062: the Unicode witness uses a fresh real project");
        verify(Session.project.loadStructure(Probe.repoUrl("tests/fixtures/stability_inputs/non-ascii.cif")), "ADR-0062: a valid non-ASCII datablock loads without a silent close");
        compare(Session.project.currentStructure.cell.lengthA.value, 5.123, "ADR-0062: the independently written Unicode CIF retains its lattice value");
        compare(Probe.rows(Session.project.currentStructure.atomSites).length, 1, "ADR-0062: the Unicode datablock retains its independently specified atom");
        const location = Probe.scratchProjectUrl();
        verify(Session.saveAs(location), "ADR-0062: a structure with a non-ASCII datablock saves without an identifier refusal");
        Session.closeProject();
        verify(Session.openProject(location), "ADR-0062: the saved Unicode structure reopens through the real session");
        compare(Session.project.currentStructure.cell.lengthA.value, 5.123, "ADR-0062: save and reopen preserve the independent cell value");
        verify(app.visible, "ADR-0062: the application stays open throughout the Unicode round trip");
    }
    function test_e_survey_is_permanently_available() {
        AppState.open(AppState.Page.Home);
        const home = named("home.survey");
        tryVerify(() => Ui.rendered(home), 1000, "ADR-0063: Home exposes its permanent survey action");
        verify(home.enabled && home.text === "Take the user survey", "2026-11-17 Home ruling: the survey retains its approved Home label");
        verify(/^(external-link(?:-alt)?|arrow-up-right-from-square|square-arrow-up-right|up-right-from-square)$/.test(home.fontIcon), "2026-11-17 Home ruling: the survey carries the external-link icon");
        compare(home.ToolTip.text, "About 10–15 minutes", "2026-11-17 Home ruling: the survey names its duration in the tooltip");
        const column = named("home.contact");
        const links = Probe.objectsWithProperty(column, "text").filter(item => typeof item.clicked === "function" && Ui.rendered(item)).sort((left, right) => left.mapToItem(app.contentItem, 0, 0).y - right.mapToItem(app.contentItem, 0, 0).y);
        compare(links.map(item => item.text), ["Help and feedback", "Enjoying EasyDiffraction?", "Take the user survey", "About EasyDiffraction"], "2026-11-17 Home ruling: the survey is third in the four-row developer column");
        form.openAs("feedback", "");
        tryCompare(form, "opened", true, 1000, "2026-11-17 Home ruling: feedback opens before its survey-link absence is observed");
        compare(Probe.objectsWithProperty(form, "text").filter(item => item.text === "Take the user survey" && typeof item.clicked === "function" && Ui.rendered(item)).length, 0, "2026-11-17 Home ruling: the feedback form has no survey action");
    }
    function test_e_user_can_open_likes_from_home_despite_timing() {
        AppState.open(AppState.Page.Home);
        const trigger = textControl("Enjoying EasyDiffraction?");
        compare(trigger.fontIcon, "heart", "2026-11-17 Home ruling: the on-demand likes action uses a heart icon");
        const bar = named("likes.bar");
        const stores = Probe.objectsWithProperty(bar, "category").filter(item => item.category === "Likes");
        compare(stores.length, 1, "ADR-0063: on-demand likes is exercised against the real persisted timing settings");
        const history = stores[0];
        const previous = {
            sessions: history.sessions,
            firstSession: history.firstSession,
            lastPrompt: history.lastPrompt
        };
        const endpoint = Preferences.feedbackEndpoint;
        const asked = Preferences.askLikes;
        OnboardingProbe.interceptUrls();
        try {
            Preferences.feedbackEndpoint = "offline-feedback://fixture";
            bar.transport = function () {
                fail("2026-11-17 Home ruling: opening the likes question never submits feedback");
            };
            history.sessions = 1;
            history.firstSession = Date.now();
            history.lastPrompt = Date.now();
            Preferences.askLikes = false;
            bar.stage = "";
            tryCompare(bar, "visible", false, 1000, "ADR-0063: this persisted history is ineligible for an automatic prompt");
            press(trigger);
            tryCompare(bar, "visible", true, 1000, "2026-11-17 Home ruling: the Home action opens likes despite age, session, cooldown and opt-out limits");
            compare(OnboardingProbe.urls().length, 0, "2026-11-17 Home ruling: opening likes is an internal action with no external URL dispatch");
            verify(Probe.objectsWithProperty(bar, "text").some(item => item.text === "Enjoying EasyDiffraction?" && Ui.rendered(item)), "2026-11-17 Home ruling: the manual action opens the actual likes question");
        } finally {
            OnboardingProbe.releaseUrls();
            Preferences.feedbackEndpoint = endpoint;
            Preferences.askLikes = asked;
            for (const key of Object.keys(previous))
                history[key] = previous[key];
        }
    }
    function copyReportLinks() {
        return Probe.objectsWithProperty(app, "text").filter(item => item.text === "Copy report" && Ui.rendered(item) && typeof item.clicked === "function");
    }
    function test_f_failed_send_offers_a_plain_text_report_data() {
        return [
            {
                tag: "no-answer",
                status: 0
            },
            {
                tag: "rate-limit",
                status: 429
            },
            {
                tag: "server",
                status: 503
            },
            {
                tag: "other-success-code",
                status: 200
            }
        ];
    }
    function test_f_failed_send_offers_a_plain_text_report(data) {
        const message = "Unreadable sample at line 17";
        const log = "copied-report-log-sentinel";
        const attachment = {
            name: "scientific-input.cif",
            type: "text/plain",
            size: 19,
            data: "c2NpZW50aWZpYy13aXRuZXNzCg=="
        };
        form.openAs("problem", log, message, [attachment]);
        tryCompare(form, "opened", true, 1000, "2026-11-17 owner decision: the report-copy witness uses the real feedback form");
        compare(copyReportLinks().length, 0, "2026-11-17 owner decision: Copy report is absent before a send");
        const payload = form.payload;
        form.transport = function (url, sent, done) {
            done(data.status, "injected offline refusal");
        };
        press(named("feedback.send"));
        tryCompare(form, "lastStatus", data.status, 1000, "2026-11-17 owner decision: the injected failed send reaches the actual form response");
        tryVerify(() => copyReportLinks().length === 1, 1000, "2026-11-17 owner decision: every non-201 response exposes one Copy report link");
        ApplicationInfo.copyText("stale-report-clipboard");
        press(copyReportLinks()[0]);
        const copied = OnboardingProbe.clipboard();
        verify(copied !== "stale-report-clipboard", "2026-11-17 owner decision: pressing Copy report replaces the actual clipboard");
        const expected = {
            message: message,
            log: log,
            file: attachment.name,
            name: "Zoë Example",
            email: "zoe@example.invalid",
            affiliation: "Example Institute",
            version: payload.app.version,
            system: payload.app.os
        };
        for (const field of Object.keys(expected))
            verify(expected[field] !== "" && copied.includes(expected[field]), "2026-11-17 owner decision: the copied plain-text report retains its preview field " + field + "=" + JSON.stringify(expected[field]));
        verify(!copied.includes(attachment.data), "2026-11-17 owner decision: copied attachments are listed by name instead of base64 file bodies");
        form.transport = function (url, sent, done) {
            done(201, "");
        };
        press(named("feedback.send"));
        tryCompare(form, "lastStatus", 201, 1000, "2026-11-17 owner decision: a successful retry reaches the real confirmation");
        compare(copyReportLinks().length, 0, "2026-11-17 owner decision: Copy report disappears after a successful send");
    }
}
