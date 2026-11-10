// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0

TestCase {
    id: test
    name: "OnboardingPayload"
    when: windowShown
    property var app
    property string previousLevel
    property string previousEndpoint
    readonly property string deployedEndpoint: "https://edi-feedback.savanna-animas-0g.workers.dev/feedback"
    Component {
        id: application
        Main {}
    }
    function init() {
        previousLevel = Preferences.loggingLevel;
        previousEndpoint = Preferences.feedbackEndpoint;
        Preferences.feedbackEndpoint = "https://feedback.example.invalid/feedback";
        app = application.createObject(null);
        verify(app !== null, "Feedback acceptance opens the real application");
        named(app, "feedback.form").transport = function () {
            fail("Every feedback gate must intercept submission; no network transport is allowed");
        };
        AppState.open(AppState.Page.Home);
        verify(waitForRendering(app.contentItem), "The feedback entry is rendered before input");
    }
    function cleanup() {
        if (app)
            app.destroy();
        app = null;
        Preferences.feedbackEndpoint = previousEndpoint;
        Preferences.loggingLevel = previousLevel;
    }
    function named(root, name) {
        const matches = Probe.objectsWithProperty(root, "objectName").filter(item => item.objectName === name);
        compare(matches.length, 1, "The production feedback form exposes its control " + name);
        return matches[0];
    }
    function openForm() {
        const links = Probe.objectsWithProperty(app, "text").filter(item => item.visible && item.text === "Help and feedback" && typeof item.clicked === "function");
        compare(links.length, 1, "The real Home feedback action is available");
        mouseClick(links[0]);
        const form = named(app, "feedback.form");
        verify("transport" in form && "endpoint" in form, "Feedback has an injectable endpoint and transport before Send can be exercised");
        return form;
    }
    function preview(form) {
        mouseClick(named(form, "feedback.preview"));
        return JSON.parse(named(app, "feedback.payload").text);
    }
    function unavailableNotes(form) {
        return Probe.objectsWithProperty(form, "text").filter(item => item.visible && /not.*configured|not.*deployed|unavailable|not.*available/i.test(item.text));
    }
    function test_default_endpoint_enables_send_without_an_unavailable_note() {
        // The shipped declaration has its own source gate. Inject that address
        // here while intercepting the entire transport before any form is opened.
        Preferences.feedbackEndpoint = deployedEndpoint;
        const form = openForm();
        named(form, "feedback.text").text = "A question about the application";
        compare(form.endpoint, deployedEndpoint, "The actual form follows the injected default preference");
        compare(named(form, "feedback.send").enabled, true, "The deployed default enables Send for a nonempty message");
        compare(unavailableNotes(form).length, 0, "The default destination shows no not-available note");
        const sent = [];
        form.transport = function (url, payload, done) {
            sent.push(String(url));
            done(400);
        };
        mouseClick(named(form, "feedback.send"));
        compare(sent.length, 1, "Enabled Send reaches exactly one injected transport call");
        compare(sent[0], deployedEndpoint, "The configured default is used only by the injected transport");
    }
    function test_clearing_endpoint_disables_send() {
        // Accident: a user clears the destination after filling in the message.
        Preferences.feedbackEndpoint = deployedEndpoint;
        const form = openForm();
        named(form, "feedback.text").text = "An already composed question";
        const send = named(form, "feedback.send");
        compare(send.enabled, true, "The populated form starts with sending enabled");
        Preferences.feedbackEndpoint = "";
        compare(form.endpoint, "", "Clearing the preference reaches the open form without reopening it");
        compare(send.enabled, false, "Clearing the address disables Send even with a nonempty message");
    }
    function test_preview_is_exactly_the_injected_submission_data() {
        return [
            {
                tag: "created",
                status: 201
            },
            {
                tag: "invalid",
                status: 400
            },
            {
                tag: "limited",
                status: 429
            }
        ];
    }
    function test_preview_is_exactly_the_injected_submission(data) {
        const form = openForm();
        const sent = [];
        form.transport = function (url, payload, done) {
            sent.push({
                url: String(url),
                payload: payload
            });
            done(data.status);
        };
        form.endpoint = "https://feedback.example.invalid/feedback";
        const home = OnboardingProbe.homePath(), user = OnboardingProbe.userName();
        verify(home.length > 1 && user.length > 0, "The privacy gate uses the actual test account's home and user name");
        named(form, "feedback.text").text = "Problem under " + home + "/project for " + user;
        const payload = preview(form);
        const encoded = JSON.stringify(payload);
        verify(!encoded.includes(home) && !encoded.includes(user), "The preview redacts home and user name before any transport sees it");
        mouseClick(named(form, "feedback.send"));
        compare(sent.length, 1, "The actual Send action invokes the injected transport exactly once");
        compare(sent[0].url, form.endpoint, "The actual Send action uses the configured endpoint");
        compare(JSON.stringify(sent[0].payload), JSON.stringify(payload), "Show what will be sent displays exactly the object passed to the transport");
        if (data.status !== 201)
            verify(form.visible, "Rejected or rate-limited feedback remains available for correction");
    }
    function test_unticked_attachment_changes_the_preview() {
        const form = openForm();
        form.transport = function () {
            fail("Preview must not invoke the submission transport");
        };
        named(form, "feedback.text").text = "Only my written question";
        named(form, "feedback.include").checked = false;
        const payload = preview(form);
        verify(!payload.app && !payload.log, "Unticking diagnostics removes app, system and log from the actual preview");
        compare(payload.text, "Only my written question", "The form retains the user's message when diagnostics are excluded");
    }
    function test_real_host_log_header_and_aligned_sources() {
        Preferences.loggingLevel = "Info";
        const header = OnboardingProbe.actualLogHeader();
        for (const key of ["date", "app", "crysta", "Qt", "OS", "graphics", "preferences"])
            verify(typeof header[key] === "string" && header[key].length > 0, "The actual run header includes nonempty " + key);
        verify(/commit\s+\S+/.test(header.app), "The actual app header contains its build commit");
        verify(/commit\s+\S+/.test(header.crysta), "The actual engine header contains its build identity");
        verify(OnboardingProbe.startHostLog().length > 0, "The host installs the production logger on an injected temporary folder");
        OnboardingProbe.emitNativeMessage();
        console.info("host-qml-sentinel");
        const content = OnboardingProbe.finishHostLog();
        verify(/  INFO      app     host-cpp-sentinel/.test(content), "A real native message reaches the host log with the padded app source");
        verify(/  INFO      qml     host-qml-sentinel/.test(content), "A real QML message reaches the same host log with the padded qml source");
    }
}
