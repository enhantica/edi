// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The intro at start (the owner, 2026-11-14), after the 2020 app's Home page (easyDiffraction 0.x, Home.qml): over a
// plain backdrop, "Making diffraction data analysis easy" fades in, every word but "easy" and "diffraction" fades out,
// and those two move to their places in the Home wordmark, "easy" cross-fading to its logo face on the way. The
// round mark then rolls in from beyond the left edge, very fast at first and braking hard like a sports car, its inner circles
// shown as a 24 fps film shows a wheel, so they seem to turn backwards while it clearly rolls forwards. Last,
// the backdrop fades, so the rest of the window fades in around the landed wordmark. Skip jumps to the end; Disable
// also turns Preferences' Home page animations off.
Item {
    id: intro

    required property Wordmark wordmark
    property bool running: false

    // Each phase's progress, 0 to 1; the items below are bound to them.
    property real wordsIn: 0
    property real othersOut: 1
    property real move: 0
    property real roll: 0
    property real reveal: 0

    // The mark's entry (the owner, 2026-11-14): an ease-out (quartic) over the roll's time, so it starts very fast and
    // brakes hard, and it rolls without slipping, its angle the distance travelled over its radius.
    readonly property real rollTime: 1.2  // s, the roll animation's duration
    readonly property real rolled: 1 - Math.pow(1 - roll, 4)
    readonly property real speed: Math.pow(1 - roll, 3)  // the speed as a share of the first speed
    // The film look: the six circles around the centre repeat every 60 degrees, so a turn of just under a multiple of
    // 60 degrees per 24 fps frame looks like a slow turn backwards. The first speed is chosen so, with the start far
    // enough left to begin beyond the window's edge; braking then passes through still and slowly forwards.
    readonly property real filmRate: 24
    readonly property real frameTurn: {
        const radius = markSize / 2;
        const needed = markEnd.x + markSize * 1.2;  // from beyond the left edge
        const perPeriod = (60 - 3) * Math.PI / 180 * filmRate * radius * rollTime / 4;
        return (60 * Math.max(1, Math.ceil(needed / perPeriod)) - 3) * Math.PI / 180;  // rad per frame at the start
    }
    readonly property real distance: frameTurn * filmRate * (markSize / 2) * rollTime / 4
    // The inner circles' angle, in degrees, sampled at the film's frame times; the position stays smooth.
    function turnAt(progress) {
        return (distance * (1 - Math.pow(1 - progress, 4)) - distance) / (markSize / 2) * 180 / Math.PI;
    }
    readonly property real filmTurn: turnAt(Math.floor(roll * rollTime * filmRate) / (rollTime * filmRate))

    readonly property real pixelSize: wordmark ? wordmark.namePixelSize : 40
    readonly property real lineBaseline: height / 2
    // The line is laid out with "easy" in SemiBold, so nothing shifts when it turns Regular during the move.
    readonly property real lineWidth: making.implicitWidth + diffraction.implicitWidth + middle.implicitWidth + boldEasy.advanceWidth
    TextMetrics {
        id: boldEasy
        font.family: EaStyle.Fonts.baloo2SemiBold.name
        font.styleName: "SemiBold"
        font.pixelSize: intro.pixelSize
        text: easy.text
    }
    readonly property real lineX: (width - lineWidth) / 2

    // Where the words and the mark land, read from the Home wordmark just before they move.
    property point easyEnd
    property point diffractionEnd
    property point markEnd
    property real markSize: wordmark ? wordmark.markItem.width : 100

    function place() {
        easyEnd = wordmark.prefixItem.mapToItem(intro, 0, 0);
        diffractionEnd = wordmark.suffixItem.mapToItem(intro, 0, 0);
        markEnd = wordmark.markItem.mapToItem(intro, 0, 0);
        markSize = wordmark.markItem.width;
    }
    function start() {
        running = true;
        wordmark.opacity = 0;
        play.start();
    }
    function finish() {
        running = false;
        wordmark.opacity = 1;
    }
    function skip() {
        play.stop();
        finish();
    }

    visible: running
    z: 10000

    Rectangle {
        anchors.fill: parent
        color: EaStyle.Colors.contentBackground
        opacity: 1 - intro.reveal
    }
    // The window under the intro takes no input until it ends.
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.AllButtons
        onWheel: wheel => wheel.accepted = true
    }

    // "easy" and "diffraction" in Baloo 2 SemiBold, the other words Regular, the very faces the Home logo uses
    // (Wordmark), so every frame and the hand-over match it on every platform. Nothing changes while the other words
    // fade; during the move "easy" cross-fades from SemiBold to the logo's Regular, "diffraction" staying SemiBold
    // (the owner, 2026-11-14).
    component Word: EaElements.Label {
        property bool bold: false

        font.family: bold ? EaStyle.Fonts.baloo2SemiBold.name : EaStyle.Fonts.baloo2Regular.name
        font.styleName: bold ? "SemiBold" : "Regular"
        font.pixelSize: intro.pixelSize
    }

    Word {
        id: making
        x: intro.lineX
        y: intro.lineBaseline - baselineOffset
        opacity: intro.wordsIn * intro.othersOut
        text: qsTr("Making ")
    }
    Word {
        id: diffraction
        readonly property real startX: intro.lineX + making.implicitWidth
        x: startX + (intro.diffractionEnd.x - startX) * intro.move
        y: intro.lineBaseline - baselineOffset + (intro.diffractionEnd.y - intro.lineBaseline + baselineOffset) * intro.move
        opacity: intro.wordsIn
        bold: true
        text: ApplicationInfo.nameSuffixForLogo
    }
    Word {
        id: middle
        x: diffraction.startX + diffraction.implicitWidth
        y: intro.lineBaseline - baselineOffset
        opacity: intro.wordsIn * intro.othersOut
        text: qsTr(" data analysis ")
    }
    // "easy" twice, overlaid and left-aligned: SemiBold fading out and Regular fading in over the middle of the move.
    readonly property real easyLight: Math.min(1, Math.max(0, (move - 0.2) / 0.6))
    Word {
        id: easy
        readonly property real startX: middle.x + middle.implicitWidth
        x: startX + (intro.easyEnd.x - startX) * intro.move
        y: intro.lineBaseline - baselineOffset + (intro.easyEnd.y - intro.lineBaseline + baselineOffset) * intro.move
        opacity: intro.wordsIn * (1 - intro.easyLight)
        bold: true
        text: ApplicationInfo.namePrefixForLogo
    }
    Word {
        x: easy.x
        y: intro.lineBaseline - baselineOffset + (intro.easyEnd.y - intro.lineBaseline + baselineOffset) * intro.move
        opacity: intro.wordsIn * intro.easyLight
        text: ApplicationInfo.namePrefixForLogo
    }

    // The mark, rolling. A light rotational blur trails the circles by part of one frame's turn while it is fast.
    Item {
        id: rollingMark

        readonly property real trail: Math.min(12, intro.frameTurn * 180 / Math.PI * intro.speed) * (intro.speed > 0.05 ? 1 : 0)

        width: intro.markSize
        height: width
        x: intro.markEnd.x - intro.distance * (1 - intro.rolled)
        y: intro.markEnd.y
        visible: intro.roll > 0

        Repeater {
            model: 4
            Image {
                required property int index
                // App.svg's circle spans 1020 of its 1024 units, as in Wordmark.
                width: rollingMark.width * 1024 / 1020
                height: width
                x: (rollingMark.width - width) / 2
                y: x
                rotation: intro.filmTurn - rollingMark.trail * index / 3
                opacity: index === 0 ? 1 : rollingMark.trail > 0 ? 0.25 : 0
                z: index
                source: Qt.resolvedUrl("../../resources/logo/App.svg")
                sourceSize: Qt.size(width, height)
                antialiasing: true
            }
        }
    }

    // A text button without a background, as in the 2020 app.
    component TextButton: EaElements.Label {
        signal clicked

        opacity: hover.hovered ? 1 : 0.6

        HoverHandler {
            id: hover
            cursorShape: Qt.PointingHandCursor
        }
        TapHandler {
            onTapped: parent.clicked()
        }
    }

    // Skip and Disable, at the bottom.
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: EaStyle.Sizes.fontPixelSize * 2
        spacing: EaStyle.Sizes.fontPixelSize * 2
        opacity: 1 - intro.reveal

        TextButton {
            objectName: "home.intro.skip"
            text: qsTr("Skip")
            onClicked: intro.skip()
        }
        TextButton {
            objectName: "home.intro.disable"
            text: qsTr("Disable")
            onClicked: {
                Preferences.homeAnimations = false;
                intro.skip();
            }
        }
    }

    // The 2020 app's timing: a 1 s pause, the line fading in over 4 s, the other words fading out over 2 s, and the
    // move over 1 s; then the mark's 1.2 s roll and the 1 s fade of the rest.
    SequentialAnimation {
        id: play

        PauseAnimation {
            duration: 1000
        }
        NumberAnimation {
            target: intro
            property: "wordsIn"
            to: 1
            duration: 4000
        }
        NumberAnimation {
            target: intro
            property: "othersOut"
            to: 0
            duration: 2000
        }
        ScriptAction {
            script: intro.place()
        }
        NumberAnimation {
            target: intro
            property: "move"
            to: 1
            duration: 1000
            easing.type: Easing.OutExpo
        }
        NumberAnimation {
            target: intro
            property: "roll"
            to: 1
            duration: intro.rollTime * 1000
        }
        NumberAnimation {
            target: intro
            property: "reveal"
            to: 1
            duration: 1000
            easing.type: Easing.OutExpo
        }
        ScriptAction {
            script: intro.finish()
        }
    }
}
