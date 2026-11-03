// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0

TestCase {
    id: test
    name: "OnboardingCrash"
    when: windowShown
    property var app
    Component {
        id: application
        Main {}
    }
    function cleanup() {
        if (app)
            app.destroy();
        app = null;
        OnboardingProbe.finishHostLog();
    }
    function named(name) {
        const matches = Probe.objectsWithProperty(app, "objectName").filter(item => item.objectName === name);
        compare(matches.length, 1, "The crash report flow exposes its actual control " + name);
        return matches[0];
    }
    function test_popup_offers_the_actual_crashed_log() {
        verify(OnboardingProbe.prepareCrashLog().length > 0, "An independently exited process leaves a real crash marker and log before app startup");
        app = application.createObject(null);
        verify(app !== null && waitForRendering(app.contentItem), "Crash acceptance starts the production app after detecting the old run");
        const popup = named("crash.popup");
        verify(popup.visible, "The next application startup offers the crashed run's log");
        const form = named("feedback.form");
        form.endpoint = "https://feedback.example.invalid/feedback";
        form.transport = function () {
            fail("Crash-report acceptance never sends to a network endpoint");
        };
        mouseClick(named("crash.report"));
        verify(form.visible, "Reporting a crash opens the same Help and feedback form");
        compare(named("feedback.kind").currentValue, "problem", "The crash form starts with Report a problem selected");
        mouseClick(named("feedback.preview"));
        const payload = JSON.parse(named("feedback.payload").text);
        compare(payload.kind, "problem", "A crash preview uses the feedback service's problem kind");
        verify(payload.log.includes("retained-crash-sentinel"), "The crash form attaches the actual flushed log from the process that exited abruptly");
    }
}
