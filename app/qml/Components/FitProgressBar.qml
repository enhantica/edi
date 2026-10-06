// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Animations as EaAnimations

// The status bar's fit progress (edi ADR-0017 §17): a rounded bar with its text inside. A scan fills it by
// file count (`fraction`); a single fit, whose length is not known, fills it with moving stripes
// (`indeterminate`). The text is drawn twice, in the bar's ink over the track and in the accent's
// contrast colour over the fill, so it reads on both.
Item {
    id: bar

    property real fraction: 0
    property bool indeterminate: false
    property string text: ""
    property string fontFamily: EaStyle.Fonts.fontFamily
    property real pixelSize: EaStyle.Sizes.fontPixelSize * 0.85

    readonly property real fillWidth: indeterminate ? width : width * Math.max(0, Math.min(1, fraction))
    readonly property color accent: EaStyle.Colors.themeAccent
    readonly property color stripe: Qt.tint(EaStyle.Colors.themeAccent, Qt.rgba(1, 1, 1, 0.38))

    implicitHeight: Math.round(EaStyle.Sizes.fontPixelSize * 1.3)

    // The track.
    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: Qt.rgba(bar.accent.r, bar.accent.g, bar.accent.b, 0.17)
        Behavior on color {
            EaAnimations.ThemeChange {}
        }
    }

    // The fill: a plain pill for a scan, stripes for a single fit, clipped to the pill on a canvas.
    Canvas {
        id: fill

        property real offset: 0

        width: bar.fillWidth
        height: bar.height
        visible: width > 0

        onOffsetChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onVisibleChanged: requestPaint()

        onPaint: {
            const context = getContext("2d");
            context.reset();
            const r = height / 2;
            context.beginPath();
            context.moveTo(r, 0);
            context.lineTo(width - r, 0);
            context.arc(width - r, r, r, -Math.PI / 2, Math.PI / 2, false);
            context.lineTo(r, height);
            context.arc(r, r, r, Math.PI / 2, 3 * Math.PI / 2, false);
            context.closePath();
            context.fillStyle = bar.accent;
            context.fill();
            if (!bar.indeterminate)
                return;
            context.clip();
            context.fillStyle = bar.stripe;
            const period = height * 1.25;
            for (let x = -2 * height + offset; x < width + height; x += period) {
                context.beginPath();
                context.moveTo(x, height);
                context.lineTo(x + height, 0);
                context.lineTo(x + height + period / 2, 0);
                context.lineTo(x + period / 2, height);
                context.closePath();
                context.fill();
            }
        }

        NumberAnimation on offset {
            running: bar.indeterminate && bar.visible
            loops: Animation.Infinite
            from: 0
            to: bar.height * 1.25
            duration: 600
        }
    }

    Text {
        anchors.centerIn: parent
        font.family: bar.fontFamily
        font.pixelSize: bar.pixelSize
        color: EaStyle.Colors.themeForeground
        text: bar.text
    }
    Item {
        width: bar.fillWidth
        height: bar.height
        clip: true

        Text {
            x: (bar.width - width) / 2
            anchors.verticalCenter: parent.verticalCenter
            font.family: bar.fontFamily
            font.pixelSize: bar.pixelSize
            color: EaStyle.Colors.mainContentBackground
            text: bar.text
        }
    }
}
