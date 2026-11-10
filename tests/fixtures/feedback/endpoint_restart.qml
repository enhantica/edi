// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Globals as Globals
import "__UI_HELPER__" as Ui

TestCase {
    name: "FeedbackEndpointUpgrade"
    when: windowShown
    property string phase: "__PHASE__"
    property url snapshot: "__SNAPSHOT__"
    readonly property string service: "https://edi-feedback.savanna-animas-0g.workers.dev/feedback"
    property var app
    property var form
    Component {
        id: application
        Main {}
    }
    function one(name) {
        const matches = Probe.objectsWithProperty(app, "objectName").filter(item => item.objectName === name);
        compare(matches.length, 1, "The actual endpoint-upgrade flow exposes one control: " + name);
        return matches[0];
    }
    function location() {
        const file = String(Globals.Vars.settingsFile), slash = file.lastIndexOf("/");
        return {
            folder: file.slice(0, slash + 1),
            name: file.slice(slash + 1)
        };
    }
    function init() {
        // The old key is an independent persisted input, before Preferences exists.
        if (phase === "legacy")
            SettingsProof.seed(Globals.Vars.settingsFile, "develop", "feedbackEndpoint", "");
        if (phase === "read") {
            const file = location(), bytes = SettingsProof.text(snapshot, "settings.ini");
            verify(bytes.length > 0, "Restart receives only the settings bytes written by the first app");
            verify(SettingsProof.write(file.folder, file.name, bytes), "The isolated settings are restored before Preferences is created");
        }
        if (phase === "clear")
            Preferences.feedbackEndpoint = service;
        app = application.createObject(null);
        verify(app !== null, "The upgrade gate creates the real application against private settings");
        form = one("feedback.form");
        form.transport = function () {
            fail("Endpoint upgrade tests never reach a network transport");
        };
        AppState.open(AppState.Page.Home);
        verify(waitForRendering(app.contentItem), "The real Home entry is ready before endpoint input");
        OnboardingProbe.startClock();
    }
    function cleanup() {
        OnboardingProbe.stopClock();
        if (app)
            app.destroy();
        app = null;
        form = null;
    }
    function press(item) {
        verify(item !== null && typeof item.mapToItem === "function", "Endpoint input addresses a real visual control");
        verify(waitForPolish(item), "Endpoint input follows actual control layout");
        const p = Ui.clickPoint(item);
        verify(item.enabled && p !== null, "Endpoint input uses a visible enabled actual control");
        mouseClick(item, p.x, p.y, Qt.LeftButton, Qt.NoModifier, 0);
        OnboardingProbe.advanceClock(1000);
    }
    function openFeedback() {
        const link = Probe.objectsWithProperty(app, "text").find(item => item.text === "Help and feedback" && Ui.rendered(item) && typeof item.clicked === "function");
        verify(link !== undefined, "The upgrade flow enters feedback through the real Home link");
        press(link);
        tryCompare(form, "opened", true, 2000, "The configured feedback form opens");
        one("feedback.text").text = "A message ready to send";
    }
    function test_endpoint_upgrade_and_user_clear() {
        if (phase === "clear") {
            press(one("appBar.button.preferences"));
            tryCompare(one("preferences"), "opened", true, 2000, "Preferences finishes opening before its settings are edited");
            press(one("preferences.tab.develop"));
            const field = one("preferences.feedbackEndpoint");
            compare(field.text, service, "The real Preferences field starts with the injected working address");
            press(field);
            field.selectAll();
            keyClick(Qt.Key_Backspace, Qt.NoModifier, 0);
            keyClick(Qt.Key_Tab, Qt.NoModifier, 0);
            compare(Preferences.feedbackEndpoint, "", "Clearing the actual Preferences field disables the configured destination");
            press(one("preferences").standardButton(Dialog.Ok));
        }
        openFeedback();
        if (phase === "legacy") {
            compare(Preferences.feedbackEndpoint, service, "A legacy empty develop/feedbackEndpoint does not override the new deployed default");
            compare(form.endpoint, service, "The migrated default reaches the actual feedback form");
            compare(one("feedback.send").enabled, true, "Users upgrading from an old empty setting can send a composed message");
        } else {
            compare(Preferences.feedbackEndpoint, "", "An explicit user-cleared address remains empty, including after restarting");
            compare(one("feedback.send").enabled, false, "An explicit clear keeps Send off even when the message is nonempty");
        }
        if (phase === "clear") {
            press(one("feedback.cancel"));
            const stores = Probe.objectsWithProperty(Preferences, "location").concat(Probe.objectsWithProperty(Preferences, "fileName"));
            for (const store of stores) {
                if (typeof store.sync !== "function")
                    continue;
                // Changing storage location flushes Qt's buffered properties,
                // as shutdown does, without waiting for a wall-clock timer.
                if (typeof store.location !== "undefined")
                    store.location = String(store.location) + ".closed";
                store.sync();
            }
            const file = location(), bytes = SettingsProof.text(file.folder, file.name);
            verify(bytes.length > 0, "The user clear produces a real settings file");
            verify(SettingsProof.write(snapshot, "settings.ini", bytes), "The restart fixture copies the actual cleared-setting bytes without inventing a new key");
        }
    }
}
