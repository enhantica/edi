// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// One line of icons and text on one visual centre line (edi ADR-0017 §10): every place an icon precedes a name
// draws it through this, so icon and name cannot sit at different heights. The text pieces share the line's
// baseline; each icon is placed so the middle of its drawn glyph lies on the middle of a capital's height of
// the text — not on the icon font's own baseline or box, whose metrics differ from the text font's and draw
// the icon high. The line is one text line high whatever it holds, so an icon alone (a table's colour column)
// centred in a cell sits where the centred text of the next cell has its centre line.
Item {
    id: line

    // The pieces, in order: {icon: <Font Awesome name>, color} or {text, color, bold}; a piece without a colour
    // takes `textColor`.
    property var segments: []
    property real pixelSize: EaStyle.Sizes.fontPixelSize
    property color textColor: EaStyle.Colors.themeForeground
    property real spacing: pixelSize * 0.5

    // The centre line, from the line's top: the text baseline, less half a capital's height.
    readonly property real centreY: textMetrics.ascent + capital.tightBoundingRect.y + capital.tightBoundingRect.height / 2

    implicitWidth: row.implicitWidth
    implicitHeight: textMetrics.height

    FontMetrics {
        id: textMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: line.pixelSize
    }
    TextMetrics {
        id: capital
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: line.pixelSize
        text: "H"
    }

    Row {
        id: row
        spacing: line.spacing

        Repeater {
            model: line.segments
            delegate: EaElements.Label {
                id: piece

                required property var modelData
                readonly property bool isIcon: modelData.icon !== undefined
                // The drawn glyph's middle, from the piece's top (none measured: its baseline).
                readonly property real inkMiddle: ink.tightBoundingRect.height > 0 ? baselineOffset + ink.tightBoundingRect.y + ink.tightBoundingRect.height / 2 : baselineOffset

                // Bold by its own loader's family and its style, never by a weight (ADR-0015 §10).
                font.family: isIcon ? EaStyle.Fonts.iconsFamily : modelData.bold ? EaStyle.Fonts.ptSansBold.name : EaStyle.Fonts.fontFamily
                font.styleName: !isIcon && modelData.bold ? "Bold" : ""
                font.pixelSize: line.pixelSize
                color: modelData.color ?? line.textColor
                text: isIcon ? modelData.icon : modelData.text
                y: isIcon ? line.centreY - inkMiddle : textMetrics.ascent - baselineOffset

                TextMetrics {
                    id: ink
                    font: piece.font
                    text: piece.isIcon ? piece.text : ""
                }
            }
        }
    }
}
