// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtCore

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Globals as EaGlobals

import edi.app

import "../../feedback/Likes.js" as Likes
import "../../feedback/Payload.js" as Payload

// "Enjoying EasyDiffraction?": a slim bar above the status bar after a successful fit, rarely (Likes.eligible, edi
// ADR-0063; owner, 2026-11-17). Every answer goes to the feedback service at once under its likes label, then opens
// Help and feedback: Yes as Share feedback, Not really as a problem, Not sure as a question. Don't ask again ends it.
Rectangle {
    id: bar

    // The fit whose successful end may show the bar, and whether a tutorial runs.
    property var fit: null
    property bool tutorialRunning: false
    // The survey invitation bar (SurveyBar.qml), for the rules between the two; null when there is none.
    property var survey: null
    // The feedback service's address, as Help and feedback's.
    property string endpoint: Preferences.feedbackEndpoint
    // transport(url, payload, completed): tests inject one; null sends natively on the desktop, over HTTPS in a browser.
    property var transport: null
    // "ask" while it shows; hidden otherwise.
    property string stage: ""
    // Whether it showed in this session, which keeps the survey invitation away until the next one.
    property bool shownThisSession: false
    readonly property real controlHeight: 32
    readonly property int textSize: 14
    // The one gap between any two items of the bar (owner, 2026-11-17); the buttons have no side padding of their
    // own, so the gap between what is seen is this.
    readonly property real gap: EaStyle.Sizes.fontPixelSize * 1.5
    // The stored counts and choices (the settings file's Likes group).
    property alias store: settings

    function now() {
        return Date.now();
    }
    function promptState(fitSucceeded) {
        return {
            "sessions": settings.sessions,
            "firstSession": settings.firstSession > 0 ? settings.firstSession : null,
            "lastPrompt": settings.lastPrompt > 0 ? settings.lastPrompt : null,
            "fitSucceeded": fitSucceeded,
            "fitting": fit ? fit.running : false,
            "tutorial": tutorialRunning,
            "disabled": !Preferences.askLikes,
            "barShown": shownThisSession || (survey !== null && survey.shownThisSession),
            "otherShown": survey !== null && survey.store.lastShown > 0 ? survey.store.lastShown : null
        };
    }
    function offer() {
        const time = now();
        // Only a fit that ended with outcome "success": a stopped or unconverged one is not a success.
        const succeeded = fit !== null && fit.outcome === "success";
        if (stage !== "" || !Likes.eligible(promptState(succeeded), time))
            return;
        settings.lastPrompt = time;
        settings.sync();
        show();
    }
    // Shown on its own: the survey invitation, if showing, makes way (one bar at a time in the strip).
    function show() {
        if (survey !== null)
            survey.close();
        shownThisSession = true;
        stage = "ask";
    }
    // One answer to the feedback service: "yes", "no" or "unsure". How it went is only logged: the form that opens
    // carries anything more.
    function send(answer) {
        const report = RunLog.reportInfo();
        // The same app lines as Help and feedback's (FeedbackDialog.appDetails).
        const app = {
            "version": report.version,
            "commit": report.commit,
            "crysta": report.crysta,
            "qt": report.qt,
            "os": report.os,
            "graphics": report.graphics
        };
        const payload = Payload.likesPayload(answer, "", RunLog.homePath, RunLog.userName, app);
        const transport = bar.transport ?? (Qt.platform.os === "wasm" ? Payload.httpTransport : (url, body, completed) => ApplicationInfo.postFeedback(url, Payload.wireText(body, false), completed));
        Payload.submit(bar.endpoint, payload, transport, (status, detail) => {
            RunLog.note(`likes sent: ${answer}, status ${status}${detail ? ", " + detail : ""}`);
        });
    }
    function close() {
        stage = "";
    }
    function answer(choice) {
        send(choice);
        close();
        AppState.feedbackRequested(choice === "yes" ? "feedback" : choice === "no" ? "problem" : "question", "");
    }

    visible: stage !== ""
    height: visible ? controlHeight + EaStyle.Sizes.fontPixelSize * 0.5 : 0
    color: EaStyle.Colors.themeBackground
    objectName: "likes.bar"

    // A fit ending with its result, never while a tutorial runs; the outcome is read once the fit has settled.
    Connections {
        target: bar.fit
        function onFinished() {
            Qt.callLater(bar.offer);
        }
        // A fit starting while the bar shows puts it away.
        function onRunningChanged() {
            if (bar.fit.running)
                bar.close();
        }
    }
    // Asked for from Home: shown at once, without the timing rule and without counting as a prompt.
    Connections {
        target: AppState
        function onLikesRequested() {
            bar.show();
        }
    }
    onTutorialRunningChanged: {
        if (tutorialRunning)
            close();
    }
    // A new session counts once, from the bar's creation with the window.
    Component.onCompleted: {
        settings.sessions += 1;
        if (!(settings.firstSession > 0))
            settings.firstSession = now();
        settings.sync();
    }

    Settings {
        id: settings

        property int sessions: 0
        property real firstSession: 0
        property real lastPrompt: 0
        property bool disabled: false

        location: EaGlobals.Vars.settingsFile
        category: "Likes"
    }
    Rectangle {
        width: parent.width
        height: EaStyle.Sizes.borderThickness
        color: EaStyle.Colors.appBorder
    }

    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: EaStyle.Sizes.fontPixelSize
        spacing: bar.gap

        EaElements.Label {
            objectName: "likes.question"
            anchors.verticalCenter: parent.verticalCenter
            font.pixelSize: bar.textSize
            text: qsTr("Enjoying %1?").arg(ApplicationInfo.name)
        }
        BarButton {
            objectName: "likes.yes"
            fontIcon: "thumbs-up"
            iconColor: EaStyle.Colors.green
            text: qsTr("Yes")
            onClicked: bar.answer("yes")
        }
        BarButton {
            objectName: "likes.no"
            fontIcon: "thumbs-down"
            iconColor: EaStyle.Colors.red
            text: qsTr("Not really")
            onClicked: bar.answer("no")
        }
        BarButton {
            objectName: "likes.unsure"
            fontIcon: "question"
            iconColor: EaStyle.Colors.orange
            text: qsTr("Not sure")
            onClicked: bar.answer("unsure")
        }
    }
    // Don't ask again and the close cross, set a little apart on the right.
    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: EaStyle.Sizes.fontPixelSize
        spacing: EaStyle.Sizes.fontPixelSize

        BarButton {
            objectName: "likes.never"
            text: qsTr("Don't ask again")
            onClicked: {
                Preferences.askLikes = false;  // Preferences turns it back on
                bar.close();
            }
        }
        BarButton {
            objectName: "likes.close"
            fontIcon: "times"
            text: ""
            ToolTip.text: qsTr("Close")
            onClicked: bar.close()
        }
    }
}
