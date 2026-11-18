// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtCore

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Globals as EaGlobals

import edi.app

import "../../feedback/Likes.js" as Likes

// The survey invitation (owner, 2026-11-17): a bar like the likes bar, after useful work in a session (a project
// loaded or a fit finished) once the app has been idle about a minute, rarely (Likes.surveyEligible). Take the survey
// and Don't ask again end it for good; Not now and the close cross ask again 30 days and 2 sessions later.
Rectangle {
    id: bar

    // The likes bar, whose session counts it shares and which goes first when both qualify.
    property var likes: null
    property var fit: null
    property bool tutorialRunning: false
    property bool shownThisSession: false
    // A project was loaded or a fit finished in this session; start-up alone is never a pause after work.
    property bool usefulWork: false
    // When the user last moved, clicked, scrolled or typed (ApplicationInfo.userInput).
    property real lastInput: now()
    property alias store: settings
    readonly property string surveyUrl: ApplicationInfo.docsUrl + "about/survey/"
    readonly property real gap: EaStyle.Sizes.fontPixelSize * 1.5

    function now() {
        return Date.now();
    }
    function surveyState(time) {
        const counts = likes ? likes.store : null;
        return {
            "sessions": counts ? counts.sessions : 0,
            "firstSession": counts && counts.firstSession > 0 ? counts.firstSession : null,
            "disabled": !Preferences.surveyInvitation,
            "stopped": settings.stopped,
            "lastShown": settings.lastShown > 0 ? settings.lastShown : null,
            "sessionsAtShown": settings.sessionsAtShown,
            "usefulWork": usefulWork,
            "idle": time - lastInput,
            "fitting": fit ? fit.running : false,
            "tutorial": tutorialRunning,
            // The likes bar goes first: while it shows (it shows as a fit succeeds), the invitation waits.
            "likesDue": likes ? likes.stage !== "" : false,
            "barShown": shownThisSession || (likes !== null && likes.shownThisSession),
            "otherShown": counts && counts.lastPrompt > 0 ? counts.lastPrompt : null
        };
    }
    // Checked again just before showing.
    function offer() {
        const time = now();
        if (visible || !Likes.surveyEligible(surveyState(time), time))
            return;
        settings.lastShown = time;
        settings.sessionsAtShown = likes ? likes.store.sessions : 0;
        settings.sync();
        shownThisSession = true;
        visible = true;
    }
    function close() {
        visible = false;
    }
    function stop() {
        settings.stopped = true;
        settings.sync();
        close();
    }

    visible: false
    height: visible ? 32 + EaStyle.Sizes.fontPixelSize * 0.5 : 0
    color: EaStyle.Colors.themeBackground
    objectName: "survey.bar"

    Connections {
        target: ApplicationInfo
        function onUserInput() {
            bar.lastInput = bar.now();
        }
    }
    Connections {
        target: bar.fit
        function onFinished() {
            bar.usefulWork = true;
        }
        function onRunningChanged() {
            if (bar.fit.running)
                bar.close();
        }
    }
    Connections {
        target: Session
        function onHasProjectChanged() {
            if (Session.hasProject)
                bar.usefulWork = true;
        }
    }
    onTutorialRunningChanged: {
        if (tutorialRunning)
            close();
    }
    // Every few seconds once there was useful work, until it has shown in this session.
    Timer {
        interval: 5000
        repeat: true
        running: bar.usefulWork && !bar.shownThisSession
        onTriggered: bar.offer()
    }

    Settings {
        id: settings

        property real lastShown: 0
        property int sessionsAtShown: 0
        property bool stopped: false

        location: EaGlobals.Vars.settingsFile
        category: "Survey"
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
            objectName: "survey.text"
            anchors.verticalCenter: parent.verticalCenter
            font.pixelSize: 14
            text: qsTr("Help shape %1: a 10–15 min anonymous survey on how you work and what you need.").arg(ApplicationInfo.name)
        }
        BarButton {
            objectName: "survey.take"
            fontIcon: "external-link-alt"
            text: qsTr("Take the survey")
            onClicked: {
                Qt.openUrlExternally(bar.surveyUrl);
                bar.stop();
            }
        }
        BarButton {
            objectName: "survey.later"
            text: qsTr("Not now")
            onClicked: bar.close()
        }
    }
    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: EaStyle.Sizes.fontPixelSize
        spacing: EaStyle.Sizes.fontPixelSize

        BarButton {
            objectName: "survey.never"
            text: qsTr("Don't ask again")
            onClicked: bar.stop()
        }
        BarButton {
            objectName: "survey.close"
            fontIcon: "times"
            text: ""
            ToolTip.text: qsTr("Close")
            onClicked: bar.close()
        }
    }
}
