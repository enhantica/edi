// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A figure palette's colour order beside its choice in Preferences (edi ADR-0038; the owner's variant D, 2026-10-26):
// positions 1 to 11 in the palette's colours, a position the open project uses showing its block's icon (experiment
// or structure) in that colour and a free one a plain square, then the calculated curve's colour as the calculator
// icon labelled "calc", and one line saying how new blocks take colours. It follows the open project live.
Column {
    id: strip

    // The palette's token (ApplicationInfo.colourSchemes).
    property string scheme: Preferences.colourScheme
    readonly property bool dark: EaStyle.Colors.isDarkPalette
    readonly property real cell: EaStyle.Sizes.fontPixelSize * 1.25
    // Each position's block kind in the open project: "experiment", "structure" or "" when free.
    readonly property var used: ApplicationInfo.palettePositions()

    spacing: EaStyle.Sizes.fontPixelSize * 0.5

    Row {
        id: cells

        spacing: EaStyle.Sizes.fontPixelSize * 0.25

        Repeater {
            objectName: "preferences.paletteStrip"
            model: ApplicationInfo.paletteColourCount

            Item {
                id: position

                required property int index
                readonly property string kind: strip.used[index] ?? ""
                readonly property color colour: ApplicationInfo.figureColour(strip.scheme, index, ApplicationInfo.paletteColourCount, strip.dark)

                objectName: "preferences.paletteStrip." + index
                width: strip.cell
                height: strip.cell

                Rectangle {
                    visible: position.kind === ""
                    anchors.centerIn: parent
                    width: strip.cell * 0.8
                    height: width
                    radius: EaStyle.Sizes.fontPixelSize * 0.15
                    color: position.colour
                }
                EaElements.Label {
                    visible: position.kind !== ""
                    anchors.centerIn: parent
                    font.family: EaStyle.Fonts.iconsFamily
                    font.pixelSize: strip.cell * 0.9
                    color: position.colour
                    text: position.kind === "structure" ? "layer-group" : "microscope"
                }
            }
        }
        // Set apart: the calculated curve's colour, the same in every palette.
        Item {
            width: strip.cell * 0.75
            height: strip.cell
        }
        EaElements.Label {
            objectName: "preferences.paletteStrip.calc"
            height: strip.cell
            verticalAlignment: Text.AlignVCenter
            font.family: EaStyle.Fonts.iconsFamily
            font.pixelSize: strip.cell * 0.9
            color: ApplicationInfo.calculationColour(strip.scheme, strip.dark)
            text: "calculator"
        }
        EaElements.Label {
            height: strip.cell
            verticalAlignment: Text.AlignVCenter
            color: EaStyle.Colors.themeForegroundMinor
            text: qsTr("calc")
        }
    }
    // As wide as the colours, on as many lines as it needs.
    EaElements.Label {
        width: cells.width
        wrapMode: Text.WordWrap
        color: EaStyle.Colors.themeForegroundMinor
        text: qsTr("Each new experiment or structure takes the next free colour.")
    }
}
