// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import edi.app

import EasyApplication.Gui.Style as EaStyle

// A value whose digits each sit centred in a cell as wide as the font's widest digit, as tabular digits do (the app's
// font has none), so a live counter keeps its width (the owner, 2026-10-13). An arrow between two values ("1.28→1.27")
// is drawn in Encode Sans, which has one, its middle level with the digits' middle.
Row {
    id: value

    property string text: ""
    property color color: EaStyle.Colors.themeForeground
    property font font: Qt.font({
        "family": EaStyle.Fonts.fontFamily,
        "pixelSize": EaStyle.Sizes.fontPixelSize
    })
    // The widest digit, rounded up.
    readonly property real cell: ApplicationInfo.digitCellWidth()
    // The text as runs: each digit alone, each arrow alone, anything else whole.
    readonly property var runs: ApplicationInfo.digitTextRuns()

    height: metrics.height
    // The runs are plain Text items, which accessibility does not expose, so the value is read as one text.
    Accessible.role: Accessible.StaticText
    Accessible.name: value.text

    FontMetrics {
        id: metrics
        font: value.font
    }
    TextMetrics {
        id: digitInk
        font: value.font
        text: "0"
    }
    TextMetrics {
        id: arrowInk
        font.family: EaStyle.Fonts.encodeSansRegular.name
        font.pixelSize: value.font.pixelSize
        text: "→"
    }

    Repeater {
        model: value.runs
        delegate: Text {
            id: run

            required property string modelData
            readonly property bool digit: ApplicationInfo.digitRunIsDigit(modelData)
            readonly property bool arrow: modelData === "→"

            width: digit ? value.cell : implicitWidth
            // On the row's baseline; an arrow with its ink's middle on the digits' ink middle.
            y: arrow ? metrics.ascent + digitInk.tightBoundingRect.y + digitInk.tightBoundingRect.height / 2 - (baselineOffset + arrowInk.tightBoundingRect.y + arrowInk.tightBoundingRect.height / 2) : metrics.ascent - baselineOffset
            horizontalAlignment: Text.AlignHCenter
            font.family: arrow ? EaStyle.Fonts.encodeSansRegular.name : value.font.family
            font.pixelSize: value.font.pixelSize
            color: value.color
            textFormat: Text.PlainText
            text: modelData
        }
    }
}
