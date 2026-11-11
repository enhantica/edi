// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick

import EasyApplication.Gui.Style as EaStyle

// A thin strip of colours under a colour selector in Preferences, each colour an equal share of the width (edi
// ADR-0084): a palette's figure colours in their order, or the colours a moment arrows choice draws.
Item {
    id: strip

    property var colours: []

    implicitHeight: Math.round(EaStyle.Sizes.fontPixelSize * 0.4)

    // Each colour from its share's rounded left edge to the next one's, so neighbours meet without a seam.
    Repeater {
        model: strip.colours

        Rectangle {
            required property int index
            required property color modelData

            x: Math.round(index * strip.width / strip.colours.length)
            width: Math.round((index + 1) * strip.width / strip.colours.length) - x
            height: strip.height
            color: modelData
        }
    }
}
