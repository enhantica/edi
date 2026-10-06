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

    // The pieces, in order: {icon: <Font Awesome name>, color, slot, ring} or {text, color, bold}; a piece without
    // a colour takes `textColor`, an icon with `slot` is one icon wide, drawn or not (a fit-outcome column), and
    // one with `ring` is drawn as a hollow circle of the icons' size (FitOutcomes' "Not fitted").
    property var segments: []
    property real pixelSize: EaStyle.Sizes.fontPixelSize
    property color textColor: EaStyle.Colors.themeForeground
    property real spacing: pixelSize * 0.5
    // A width the line must not exceed (0: none): its last text piece is then elided, by `elide`.
    property real maximumWidth: 0
    property int elide: Text.ElideRight

    // The width of every piece before the last, with their spacing: what the last piece leaves room for.
    readonly property real leadingWidth: {
        let width = 0;
        for (let i = 0; i < pieces.count - 1; ++i) {
            const piece = pieces.itemAt(i);
            width += piece ? piece.width + spacing : 0;
        }
        return width;
    }

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
            id: pieces
            model: line.segments
            delegate: EaElements.Label {
                id: piece

                required property int index
                required property var modelData
                readonly property bool elided: line.maximumWidth > 0 && !isIcon && index === line.segments.length - 1
                readonly property bool isIcon: modelData.icon !== undefined
                // The drawn glyph's middle, from the piece's top (none measured: its baseline).
                readonly property real inkMiddle: ink.tightBoundingRect.height > 0 ? baselineOffset + ink.tightBoundingRect.y + ink.tightBoundingRect.height / 2 : baselineOffset

                // Bold by its own loader's family and its style, never by a weight (ADR-0015 §10).
                font.family: isIcon ? EaStyle.Fonts.iconsFamily : modelData.bold ? EaStyle.Fonts.ptSansBold.name : EaStyle.Fonts.fontFamily
                font.styleName: !isIcon && modelData.bold ? "Bold" : ""
                font.pixelSize: line.pixelSize
                color: modelData.color ?? line.textColor
                text: isIcon ? modelData.icon : modelData.text
                width: elided ? Math.max(0, Math.min(implicitWidth, line.maximumWidth - line.leadingWidth)) : modelData.slot ? line.pixelSize * 1.15 : implicitWidth
                elide: elided ? line.elide : Text.ElideNone
                y: isIcon ? line.centreY - inkMiddle : textMetrics.ascent - baselineOffset

                Rectangle {
                    readonly property real diameter: line.pixelSize * 0.85

                    visible: piece.modelData.ring === true
                    x: (piece.width - diameter) / 2
                    y: line.centreY - piece.y - diameter / 2
                    width: diameter
                    height: diameter
                    radius: diameter / 2
                    color: "transparent"
                    border.color: piece.color
                    border.width: Math.max(1, diameter / 8)
                }

                TextMetrics {
                    id: ink
                    font: piece.font
                    text: piece.isIcon ? piece.text : ""
                }
            }
        }
    }
}
