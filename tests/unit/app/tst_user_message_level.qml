// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import OnboardingAcceptance 1.0

Item {
    id: surface

    height: 950
    width: 1200

    Component {
        id: preferencesFactory

        AppPreferencesDialog {
        }
    }
    TestCase {
        property string previous

        function cleanup() {
            if (Session.project && Session.project.fit.running) {
                Session.project.fit.cancel();
                tryCompare(Session.project.fit, "running", false, 10000, "The diagnostic fit settles before its project closes");
            }
            Session.closeProject();
            Preferences.dialogShown = false;
            Preferences.loggingLevel = previous;
        }
        function init() {
            previous = Preferences.loggingLevel;
        }
        function test_default_is_warning() {
            compare(Preferences.loggingLevel.toLowerCase(), "warning", "A fresh app preference starts at Warning");
            compare(RunLog.level.toLowerCase(), "warning", "The actual app message sink shares the default Warning level");
        }
        function test_selector_changes_the_actual_message_sink() {
            const dialog = createTemporaryObject(preferencesFactory, surface);
            verify(dialog !== null, "Message levels are selected in the real Preferences dialog");
            Preferences.dialogShown = true;
            tryCompare(dialog, "opened", true, 1000, "The actual Preferences dialog finishes opening");
            const tab = findChild(dialog, "preferences.tab.develop");
            verify(tab !== null, "The logging control retains its actual Develop tab");
            mouseClick(tab, tab.width / 2, tab.height / 2);
            verify(waitForPolish(dialog.contentItem), "The real level selector completes its layout");
            const choice = findChild(dialog, "preferences.loggingLevel");
            verify(choice !== null && choice.visible && choice.enabled, "The real app exposes an enabled message-level selector");
            const names = [];
            for (let index = 0; index < choice.count; ++index)
                names.push(choice.textAt(index).toLowerCase());
            compare(JSON.stringify(names.slice().sort()), JSON.stringify(["debug", "error", "info", "warning"]), "The app offers exactly the four owner-selected levels, with no Disabled level");
            for (let index = 0; index < names.length; ++index) {
                const path = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/message_levels/project"));
                verify(Session.openProject(path), "The app loads the independent h00 longitudinal-moment fixture");
                tryCompare(Session.project, "calculating", false, 10000, "The actual measured fixture is ready before fitting");
                mouseClick(choice, choice.width / 2, choice.height / 2);
                keyClick(Qt.Key_Home);
                for (let step = 0; step < index; ++step)
                    keyClick(Qt.Key_Down);
                keyClick(Qt.Key_Return);
                tryCompare(choice, "currentIndex", index, 1000, "Keyboard selection activates the actual menu item");
                compare(Preferences.loggingLevel.toLowerCase(), names[index], "The actual selector updates the shared app preference");
                compare(RunLog.level.toLowerCase(), names[index], "The actual message sink reads the same user-selected level");
                const fit = Session.project.fit;
                let started = false;
                const watch = () => {
                    if (fit.running)
                        started = true;
                };
                fit.runningChanged.connect(watch);
                fit.start();
                tryVerify(() => started, 2000, "The actual app worker starts the independent diagnostic fit");
                tryCompare(fit, "running", false, 10000, "The actual app diagnostic fit settles");
                fit.runningChanged.disconnect(watch);
                verify(["success", "noStep", "maxIterations"].includes(fit.outcome), "The covariance witness produces a real fit result rather than a reader or worker error");
                verify(waitForRendering(surface), "The actual message surface settles after the completed worker");
                // The app presents diagnostics in Messages; its native run log is a separate view.
                // The independent h00 / longitudinal-moment fixture has an exactly null column.
                const diagnostic = Probe.rows(Session.loadWarnings).some(row =>
                    /data do not determine/.test(row.message) && /s\.u\. is undefined/.test(row.message));
                compare(diagnostic, ["info", "debug"].includes(names[index]), "The chosen app level filters the real undefined-covariance diagnostic in the user-visible Messages model");
                Session.closeProject();
            }
        }

        name: "UserMessageLevel"
        when: windowShown
    }
}
