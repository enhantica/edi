// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The easydiffraction wordmark as the official logo lays it out (easyscience/assets-branding,
// easydiffraction/source/EasyDiffraction-logo_lightmode_wfont.svg): the logo mark, and beside it "easy" over
// "diffraction" in Baloo 2. Every measure follows the mark's visible diameter by that SVG's proportions. The
// SVG asks "easy" for weight 300, which Baloo 2 does not have (its weights start at 400), so "easy" draws in
// Regular, as the SVG itself does, and "diffraction" in SemiBold. The version is not part of it: Home and
// About set it below, centred (WordmarkWithVersion). The name stays live text, which the Home page's intro moves into
// place (HomeIntro).
Item {
    id: wordmark

    required property real markDiameter
    property string link: ""  // opened by a click on the mark, when set

    readonly property real nameX: markDiameter * 1.1094  // the mark, then the gap before the name
    readonly property real namePixelSize: markDiameter * 0.4309
    // Where the intro lands its words and the mark.
    readonly property Item markItem: mark
    readonly property Item prefixItem: prefix
    readonly property Item suffixItem: suffix

    // The Home page's idle spin (the owner, 2026-11-14): two fast spins back to back, each coasting for a second at
    // just under one turn per 24 fps film frame, then braking (quartic) to rest where it started, 27 turns in all.
    // The mark is shown at the film's frame times, so while it coasts its dots seem to drift slowly backwards, and a
    // light rotational blur keeps the forward speed visible. The web page's loader runs the same motion (index.html).
    readonly property real spinRate: (360 - 15) * 24  // degrees per second while coasting
    readonly property real spinCoast: 1.0  // s
    readonly property real spinBrake: (360 * 27 - spinRate * spinCoast) / (spinRate / 4)  // s
    property real spinTime: 0  // s into the current spin
    readonly property bool spinning: idleSpin.running
    function spinAngle(time) {
        if (time <= spinCoast)
            return spinRate * time;
        const u = Math.min(1, (time - spinCoast) / spinBrake);
        return spinRate * spinCoast + spinRate * spinBrake * (1 - Math.pow(1 - u, 4)) / 4;
    }
    function spinSpeed(time) {  // a share of the coasting speed
        return time <= spinCoast ? 1 : Math.pow(1 - Math.min(1, (time - spinCoast) / spinBrake), 3);
    }
    readonly property real filmAngle: spinning ? spinAngle(Math.floor(spinTime * 24) / 24) % 360 : 0
    readonly property real spinTrail: spinning ? 12 * spinSpeed(spinTime) : 0
    function spin() {
        idleSpin.restart();
    }

    implicitWidth: nameX + Math.max(prefix.implicitWidth, suffix.implicitWidth)
    implicitHeight: markDiameter

    Image {
        id: mark
        // App.svg's circle spans 1020 of its 1024 units, so the image is that much larger than the mark.
        width: wordmark.markDiameter * 1024 / 1020
        height: width
        x: (wordmark.markDiameter - width) / 2
        y: x
        source: Qt.resolvedUrl("../../resources/logo/App.svg")
        sourceSize: Qt.size(width, height)
        fillMode: Image.PreserveAspectFit
        antialiasing: true
        rotation: wordmark.filmAngle

        MouseArea {
            anchors.fill: parent
            enabled: wordmark.link !== ""
            cursorShape: Qt.PointingHandCursor
            onClicked: Qt.openUrlExternally(wordmark.link)
        }
    }

    // The spin's rotational blur: three faint copies trailing the mark by up to 12 degrees while it is fast.
    Repeater {
        model: wordmark.spinTrail > 0.5 ? 3 : 0
        Image {
            required property int index
            width: mark.width
            height: mark.height
            x: mark.x
            y: mark.y
            rotation: wordmark.filmAngle - wordmark.spinTrail * (index + 1) / 3
            opacity: 0.25
            source: mark.source
            sourceSize: mark.sourceSize
            antialiasing: true
        }
    }

    EaElements.Label {
        id: prefix
        x: wordmark.nameX
        y: wordmark.markDiameter * 0.3859 - baselineOffset  // the baseline, as in the SVG
        // Each face by the family its own loader registered and by its style (ADR-0015 §10).
        font.family: EaStyle.Fonts.baloo2Regular.name
        font.styleName: "Regular"
        font.pixelSize: wordmark.namePixelSize
        text: ApplicationInfo.namePrefixForLogo
    }

    EaElements.Label {
        id: suffix
        x: wordmark.nameX
        y: wordmark.markDiameter * 0.8198 - baselineOffset
        font.family: EaStyle.Fonts.baloo2SemiBold.name
        font.styleName: "SemiBold"
        font.pixelSize: wordmark.namePixelSize
        text: ApplicationInfo.nameSuffixForLogo
    }

    NumberAnimation {
        id: idleSpin
        target: wordmark
        property: "spinTime"
        from: 0
        to: wordmark.spinCoast + wordmark.spinBrake
        duration: (wordmark.spinCoast + wordmark.spinBrake) * 1000
        loops: 2
    }
}
