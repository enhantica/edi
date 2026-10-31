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
    // Up to 24 samples, each at least about two pixels wide, so both ends of the map always show.
    readonly property int samples: Math.max(2, Math.min(24, Math.floor(barWidth / 2)))
    readonly property var stops: ApplicationInfo.scanColourStops(map, dark, inverted, samples)

    width: barWidth
    height: barHeight
    clip: true

    // Each sample from its share's rounded left edge to the next one's, so neighbours meet without a seam and the
    // last ends at the bar's right edge whatever its width.
    Repeater {
        model: bar.stops

        Rectangle {
            required property int index
            required property color modelData

            x: Math.round(index * bar.barWidth / bar.stops.length)
            width: Math.round((index + 1) * bar.barWidth / bar.stops.length) - x
            height: bar.barHeight
            color: modelData
        }
    }
}
