// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Effects

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The intro at start (the owner, 2026-11-14), after the 2020 app's Home page (easyDiffraction 0.x, Home.qml): over a
// plain backdrop, "Making diffraction data analysis easy" fades in, every word but "easy" and "diffraction" fades out,
// and those two move to their places in the Home wordmark, "diffraction" turning SemiBold on the way. The round mark
// then rolls in from beyond the left edge, spinning fast and blurred by its speed, and stops with a hard brake. Last,
// the backdrop fades, so the rest of the window fades in around the landed wordmark. Skip jumps to the end; Disable
// also turns Preferences' Home page animations off.
Item {
    id: intro

    required property Wordmark wordmark
    property bool running: false

    // Each phase's progress, 0 to 1; the items below are bound to them.
    property real wordsIn: 0
    property real othersOut: 1
    property real bold: 0
    property real move: 0
    property real roll: 0
    property real reveal: 0

    // The mark coasts at one speed, then brakes at a steady rate over the last fifth of its time.
    readonly property real brakeStart: 0.8
    readonly property real rolled: {
        const p = roll, p0 = brakeStart, v = 2 / (1 + p0);
        return p < p0 ? v * p : v * p0 + v * (p - p0) - v * (p - p0) * (p - p0) / (2 * (1 - p0));
    }
    readonly property real speed: roll <= 0 || roll >= 1 ? 0 : roll < brakeStart ? 1 : (1 - roll) / (1 - brakeStart)

    readonly property real pixelSize: wordmark ? wordmark.namePixelSize : 40
    readonly property real lineBaseline: height / 2
    readonly property real lineWidth: making.implicitWidth + diffraction.implicitWidth + middle.implicitWidth + easy.implicitWidth
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

    component Word: EaElements.Label {
        font.family: EaStyle.Fonts.baloo2Regular.name
        font.styleName: "Regular"
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
        opacity: intro.wordsIn * (1 - intro.bold)
        text: ApplicationInfo.nameSuffixForLogo
    }
    Word {
        x: diffraction.x
        y: diffraction.y
        font.family: EaStyle.Fonts.baloo2SemiBold.name
        font.styleName: "SemiBold"
        opacity: intro.wordsIn * intro.bold
        text: ApplicationInfo.nameSuffixForLogo
    }
    Word {
        id: middle
        x: diffraction.startX + diffraction.implicitWidth
        y: intro.lineBaseline - baselineOffset
        opacity: intro.wordsIn * intro.othersOut
        text: qsTr(" data analysis ")
    }
    Word {
        id: easy
        readonly property real startX: middle.x + middle.implicitWidth
        x: startX + (intro.easyEnd.x - startX) * intro.move
        y: intro.lineBaseline - baselineOffset + (intro.easyEnd.y - intro.lineBaseline + baselineOffset) * intro.move
        opacity: intro.wordsIn
        text: ApplicationInfo.namePrefixForLogo
    }

    // The mark, rolling: its turn follows the distance it covers, six turns in all.
    Item {
        width: intro.markSize
        height: width
        x: -width * 1.2 + (intro.markEnd.x + width * 1.2) * intro.rolled
        y: intro.markEnd.y
        visible: intro.roll > 0

        Image {
            // App.svg's circle spans 1020 of its 1024 units, as in Wordmark.
            width: parent.width * 1024 / 1020
            height: width
            x: (parent.width - width) / 2
            y: x
            rotation: 360 * 6 * (intro.rolled - 1)
            source: Qt.resolvedUrl("../../resources/logo/App.svg")
            sourceSize: Qt.size(width, height)
            antialiasing: true
        }
        layer.enabled: intro.speed > 0
        layer.effect: MultiEffect {
            blurEnabled: true
            blurMax: 16
            blur: 0.7 * intro.speed
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
        ParallelAnimation {
            NumberAnimation {
                target: intro
                property: "move"
                to: 1
                duration: 1000
                easing.type: Easing.OutExpo
            }
            NumberAnimation {
                target: intro
                property: "bold"
                to: 1
                duration: 600
            }
        }
        NumberAnimation {
            target: intro
            property: "roll"
            to: 1
            duration: 1200
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
