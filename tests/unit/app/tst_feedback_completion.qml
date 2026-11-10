// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0
import "NativeTurn.js" as Turn

TestCase {
    id: test
    name: "FeedbackCompletion"
    when: windowShown
    property var app
    property var form
    property var dialogComponent
    property var oldContact: null
    property string gateTurnSelector: ""
    property url dialogSource: Qt.resolvedUrl("../../../app/qml/Components/FeedbackDialog.qml")
    Component { id: application; Window { width: 1200; height: 900; visible: true } }
    Component {
        id: delayedExit
        Transition { NumberAnimation { target: test.form.contentItem; property: "opacity"; from: 1; to: 0; duration: 1000 } }
    }
    function initTestCase() {
        dialogComponent = Qt.createComponent(dialogSource);
        app = application.createObject(null);
        verify(OnboardingProbe.prepareCrashLog().length > 0, "ADR-0063 F1: an independent crashed process supplies the shared host's real retained log");
    }
    function init() {
        gateTurnSelector = Turn.begin(test, Probe, message => test.warn(message));
    }
    function cleanupTestCase() {
        OnboardingProbe.finishHostLog();
        if (app) app.destroy();
        app = null;
    }
    function one(name) {
        const found = Probe.objectsWithProperty(form, "objectName").filter(item => item.objectName === name);
        compare(found.length, 1, "ADR-0063 F1: the actual dialog exposes one named input: " + name);
        return found[0];
    }
    function openForm(attachment = "") {
        oldContact = [Preferences.feedbackName, Preferences.feedbackEmail, Preferences.feedbackAffiliation];
        app.update();
        verify(app !== null && waitForRendering(app.contentItem), "ADR-0063 F1: feedback completion uses a rendered real window");
        const component = dialogComponent;
        compare(component.status, Component.Ready, "ADR-0063 F1: the exact production FeedbackDialog source loads: " + component.errorString());
        form = component.createObject(app.contentItem, {roomWidth: 1200});
        verify(form !== null, "ADR-0063 F1: the real FeedbackDialog owns the pending request");
        form.enter = null;
        form.exit = null;
        form.endpoint = "https://feedback.example.invalid/feedback";
        form.transport = function () { fail("ADR-0063 F1: every request must use the controlled transport, never the network"); };
        form.openAs("problem", attachment);
        tryCompare(form, "opened", true, 2000, "ADR-0063 F1: the actual feedback form opens before composing");
        one("feedback.text").text = "Submitted message A";
        one("feedback.subject").text = "Submitted subject A";
        one("feedback.name").text = "Person A";
        one("feedback.email").text = "a@example.invalid";
        one("feedback.affiliation").text = "Institute A";
    }
    function cleanup() {
        if (form) form.destroy();
        form = null;
        if (oldContact) {
            Preferences.feedbackName = oldContact[0];
            Preferences.feedbackEmail = oldContact[1];
            Preferences.feedbackAffiliation = oldContact[2];
        }
        oldContact = null;
        Turn.end(gateTurnSelector, message => test.warn(message));
    }
    function dispatch() {
        const held = {body: null, done: null, calls: 0};
        form.transport = function (url, body, completed) {
            ++held.calls;
            compare(url, "https://feedback.example.invalid/feedback", "ADR-0063 F1: the request reaches only its injected endpoint");
            held.body = body;
            held.done = completed;
        };
        const send = one("feedback.send");
        verify(send.enabled && waitForPolish(send), "ADR-0063 F1: real Send is enabled for the composed request");
        mouseClick(send, send.width / 2, send.height / 2);
        compare(held.calls, 1, "ADR-0063 F1: actual Send dispatches one request before any later edit");
        compare(form.sending, true, "ADR-0063 F1: the request remains pending until the held callback completes");
        compare(held.body.text, "Submitted message A", "ADR-0063 F1: the wire payload contains the submitted message snapshot");
        compare(held.body.subject, "Submitted subject A", "ADR-0063 F1: the wire payload contains the submitted subject snapshot");
        compare(held.body.kind, "problem", "ADR-0063 F1: the wire kind belongs to the submitted request");
        return held;
    }
    function draft() {
        const kind = one("feedback.kind");
        return [one("feedback.text").text, one("feedback.subject").text,
            one("feedback.name").text, one("feedback.email").text, one("feedback.affiliation").text,
            kind.currentValue, one("feedback.include").checked, form.attachedLog];
    }
    function test_later_draft_data() {
        return ["message", "subject", "name", "email", "affiliation", "kind", "include", "close", "closing", "reopen", "reopen-identical", "attachment-added", "attachment-changed", "attachment-cleared"].map(change => ({tag: change, change}));
    }
    function test_later_draft(data) {
        const firstAttachment = ["attachment-changed", "attachment-cleared"].includes(data.change) ? "Submitted attachment A" : "";
        openForm(firstAttachment);
        if (data.change === "reopen-identical") one("feedback.include").checked = false;
        const held = dispatch();
        const serialized = JSON.stringify(held.body);
        const expected = ["Submitted message A", "Submitted subject A", "Person A", "a@example.invalid", "Institute A", "problem", data.change !== "reopen-identical", firstAttachment];
        const fields = ["message", "subject", "name", "email", "affiliation"];
        const index = fields.indexOf(data.change);
        const fieldAttempt = index >= 0 || data.change === "kind" || data.change === "include";
        let acceptedEdit = false;
        if (index >= 0) {
            const values = ["Later message B\nwith a correction", "Later subject B", "Person B", "b@example.invalid", "Institute B"];
            const key = index === 0 ? "text" : data.change;
            if (one("feedback." + key).enabled) {
                one("feedback." + key).text = values[index];
                expected[index] = values[index];
                acceptedEdit = true;
            }
        } else if (data.change === "kind") {
            const kind = one("feedback.kind");
            if (kind.enabled) {
                kind.currentIndex = kind.indexOfValue("idea");
                expected[5] = "idea";
                acceptedEdit = true;
            }
        } else if (data.change === "include") {
            if (one("feedback.include").enabled) {
                one("feedback.include").checked = false;
                expected[6] = false;
                acceptedEdit = true;
            }
        } else if (data.change.startsWith("attachment-")) {
            form.attachedLog = data.change === "attachment-cleared" ? "" : "Later attachment B";
            expected[7] = form.attachedLog;
        } else {
            if (data.change === "closing") form.exit = delayedExit.createObject(form);
            form.close();
            tryCompare(form, "opened", false, 2000, "ADR-0063 F1: closing the dialog ends the submitted form session");
            if (data.change === "closing")
                verify(form.visible, "ADR-0063 F1: a controlled exit keeps the real close transition pending at completion");
            else
                tryCompare(form, "visible", false, 2000, "ADR-0063 F1: the closed-form witness reaches the completed close boundary");
            expected[7] = "";
            if (data.change === "reopen" || data.change === "reopen-identical") {
                const identical = data.change === "reopen-identical";
                form.openAs(identical ? "problem" : "idea", identical ? "" : "Later attachment B");
                tryCompare(form, "opened", true, 2000, "ADR-0063 F1: reopening exposes a distinct form session");
                if (identical) {
                    compare(JSON.stringify(form.payload), serialized, "ADR-0063 F1: an identical wire payload still belongs to a newly opened form session");
                } else {
                    one("feedback.text").text = "Later message B\nwith a correction";
                    one("feedback.subject").text = "Later subject B";
                    expected[0] = "Later message B\nwith a correction";
                    expected[1] = "Later subject B";
                    expected[5] = "idea";
                    expected[7] = "Later attachment B";
                }
            }
        }
        compare(JSON.stringify(draft()), JSON.stringify(expected), "ADR-0063 F1: the later draft/context is actually present before completion");
        const status = form.lastStatus;
        held.done(201);
        wait(0);
        compare(JSON.stringify(held.body), serialized, "ADR-0063 F1: edits and completion never mutate the submitted wire snapshot");
        if (fieldAttempt) {
            const at = index >= 0 ? index : data.change === "kind" ? 5 : 6;
            compare(draft()[at], acceptedEdit ? expected[at] : at < 2 ? "" : expected[at], "ADR-0063 F1: later edits remain intact, or the disabled editor prevented the edit before ordinary success");
            if (!acceptedEdit) {
                compare(one("feedback.text").text, "", "ADR-0063 F1: a locked unchanged message keeps ordinary successful clearing");
                compare(one("feedback.subject").text, "", "ADR-0063 F1: a locked unchanged subject keeps ordinary successful clearing");
            }
            return;
        }
        compare(JSON.stringify(draft()), JSON.stringify(expected), "ADR-0063 F1: success for an older request preserves every unsubmitted field and attachment");
        compare(form.lastStatus, status, "ADR-0063 F1: old completion does not install success into a different draft or form session");
        compare(form.sent, false, "ADR-0063 F1: old success cannot hide the current draft behind its confirmation");
        if (data.change === "closing")
            compare(form.opened, false, "ADR-0063 F1: completion cannot reopen a form whose exit is pending");
        else
            compare(form.visible, data.change !== "close", "ADR-0063 F1: completion cannot reopen a closed form or dismiss its successor");
    }
    function test_ordinary_completion_data() {
        return ["201", "429", "0", "400", "no-address"].map(status => ({tag: status, status}));
    }
    function test_ordinary_completion(data) {
        openForm();
        if (data.status === "no-address") {
            form.endpoint = "";
            compare(one("feedback.send").enabled, false, "ADR-0063: missing address disables Send");
            form.send();
            compare(form.sending, false, "ADR-0063: missing address does not leave a pending request");
        } else {
            const held = dispatch();
            held.done(Number(data.status));
            compare(form.lastStatus, Number(data.status), "ADR-0063: an unchanged form keeps its ordinary transport outcome");
        }
        const expected = data.status === "201" ? "" : "Submitted message A";
        compare(one("feedback.text").text, expected, "ADR-0063: only ordinary successful completion clears the submitted message");
        compare(one("feedback.subject").text, data.status === "201" ? "" : "Submitted subject A", "ADR-0063: failure and no-address keep the submitted subject");
        compare(one("feedback.name").text, "Person A", "ADR-0063: all outcomes retain remembered contact details");
    }
    function test_a_unsent_crash_attachment() {
        openForm();
        const crash = RunLog.crashedLog;
        verify(crash.length > 0, "ADR-0063 F1: the pending crash belongs to the actual logger");
        const held = dispatch();
        verify(!held.body.log.includes("retained-crash-sentinel"), "ADR-0063 F1: the old request did not attach the retained crash report");
        form.attachedLog = RunLog.crashedLogText();
        verify(form.attachedLog.includes("retained-crash-sentinel"), "ADR-0063 F1: the later draft attaches the actual unsent crash log");
        const later = form.attachedLog;
        held.done(201);
        compare(RunLog.crashedLog, crash, "ADR-0063 F1: old success cannot dismiss a crash absent from its submitted request");
        compare(form.attachedLog, later, "ADR-0063 F1: old success retains the later crash attachment");
        compare(one("feedback.text").text, "Submitted message A", "ADR-0063 F1: a changed attachment makes the current draft distinct");
    }
    function test_submitted_kind_is_logged() {
        openForm();
        const offset = RunLog.logText().length;
        const held = dispatch();
        form.openAs("idea", "Later attachment B");
        held.done(201);
        const text = RunLog.logText().slice(offset);
        verify(text.includes("feedback sent: problem"), "ADR-0063 F1: completion logs the submitted kind even after the form is reused");
        verify(!text.includes("feedback sent: idea"), "ADR-0063 F1: completion cannot attribute the old request to the live form kind");
    }
    function test_successor_can_send_data() {
        const rows = [];
        for (const change of ["attachment-added", "attachment-changed", "attachment-cleared", "close", "cancel", "open-as"])
            for (const order of ["old-first", "new-first"])
                rows.push({tag: change+"-"+order, change, order});
        return rows;
    }
    function test_successor_can_send(data) {
        openForm(["attachment-changed", "attachment-cleared"].includes(data.change) ? "Submitted attachment A" : "");
        const old = dispatch();
        if (data.change.startsWith("attachment-")) {
            form.attachedLog = data.change === "attachment-cleared" ? "" : "Later attachment B";
        } else if (data.change === "open-as") {
            verify(form.opened, "ADR-0063 F1: in-place reuse begins with a dialog that is already open");
            form.openAs("idea", "Later attachment B");
        } else {
            form.exit = delayedExit.createObject(form);
            if (data.change === "cancel") {
                const cancel = one("feedback.cancel");
                mouseClick(cancel, cancel.width/2, cancel.height/2);
            } else form.close();
            compare(form.opened, false, "ADR-0063 F1: close and real Cancel begin the close boundary before completion");
            verify(form.visible, "ADR-0063 F1: the old request remains held while the close transition has not emitted onClosed");
            compare(form.sending, false, "ADR-0063 F1: the close boundary releases the old draft's pending state before onClosed");
            form.openAs("idea", "Later attachment B");
            tryCompare(form, "opened", true, 2000, "ADR-0063 F1: the successor opens while the old response is still pending");
        }
        compare(form.sending, false, "ADR-0063 F1: attachment changes and in-place openAs release stale pending state immediately");
        verify(one("feedback.text").enabled && one("feedback.subject").enabled && one("feedback.send").enabled, "ADR-0063 F1: the successor's editors and Send are usable before the old request finishes");
        one("feedback.text").text = "Successor message B";
        one("feedback.subject").text = "Successor subject B";
        const next = {calls: 0, done: null, body: null};
        form.transport = function(url, body, completed) { ++next.calls; next.body = body; next.done = completed; };
        const send = one("feedback.send");
        mouseClick(send, send.width/2, send.height/2);
        compare(next.calls, 1, "ADR-0063 F1: actual Send dispatches the usable successor while the older request is pending");
        compare(next.body.text, "Successor message B", "ADR-0063 F1: the successor request carries its own independently composed message");
        compare(form.sending, true, "ADR-0063 F1: the successor owns its new pending state");
        if (data.order === "old-first") {
            old.done(201);
            compare(form.sending, true, "ADR-0063 F1: old completion cannot unlock or replace the pending successor");
            compare(form.sent, false, "ADR-0063 F1: old success cannot confirm the successor request");
            next.done(429);
        } else {
            next.done(429);
            old.done(201);
        }
        compare(form.lastStatus, 429, "ADR-0063 F1: only the successor's response determines its status in either completion order");
        compare(one("feedback.text").text, "Successor message B", "ADR-0063 F1: either response ordering retains the successor's unsent retry text");
        compare(one("feedback.subject").text, "Successor subject B", "ADR-0063 F1: old success never clears the successor's retry subject");
        verify(!form.sending && !form.sent && one("feedback.send").enabled, "ADR-0063 F1: the latest failed request leaves Send usable for retry after both responses");
    }

}
