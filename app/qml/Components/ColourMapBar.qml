// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick

import edi.app

// A colour map drawn as a short bar from its low values on the left to its high values on the right, in the theme and
// the direction it is drawn in (ApplicationInfo.scanColourStops): the swatch beside a map's name (edi ADR-0041).
Item {
    id: bar

    // A name of ApplicationInfo.scanColourMaps.
    property string map: ""
    property bool dark: false
    property bool inverted: false
    property real barWidth: 40
    property real barHeight: 10
    readonly property var stops: ApplicationInfo.scanColourStops(map, dark, inverted, 24)

    width: barWidth
    height: barHeight
    clip: true

    // Whole-pixel pieces, a little wider than their share, so no seam shows between them.
    Row {
        Repeater {
            model: bar.stops

            Rectangle {
                required property color modelData

                width: Math.ceil(bar.barWidth / bar.stops.length)
                height: bar.barHeight
                color: modelData
            }
        }
    }
}
