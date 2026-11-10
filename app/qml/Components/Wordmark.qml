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
// About set it below, centred (WordmarkWithVersion). The name stays live text, for the Home page's animation to
// come.
Item {
    id: wordmark

    required property real markDiameter
    property string link: ""  // opened by a click on the mark, when set

    readonly property real nameX: markDiameter * 1.1094  // the mark, then the gap before the name
    readonly property real namePixelSize: markDiameter * 0.4309

    implicitWidth: nameX + Math.max(prefix.implicitWidth, suffix.implicitWidth)
    implicitHeight: markDiameter

    Image {
        // App.svg's circle spans 1020 of its 1024 units, so the image is that much larger than the mark.
        width: wordmark.markDiameter * 1024 / 1020
        height: width
        x: (wordmark.markDiameter - width) / 2
        y: x
        source: Qt.resolvedUrl("../../resources/logo/App.svg")
        sourceSize: Qt.size(width, height)
        fillMode: Image.PreserveAspectFit
        antialiasing: true

        MouseArea {
            anchors.fill: parent
            enabled: wordmark.link !== ""
            cursorShape: Qt.PointingHandCursor
            onClicked: Qt.openUrlExternally(wordmark.link)
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
}
