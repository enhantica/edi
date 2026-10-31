// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The Map's colour-map drop-down (edi ADR-0041; the owner, 2026-10-26): each map's name with its colour bar beside it,
// in the list and for the current choice, each bar drawn in the theme and in the direction the Map would draw that map.
ToolbarComboBox {
    id: box

    // Names of ApplicationInfo.scanColourMaps, and the Map's direction and background, which the bars follow.
    property var maps: []
    property string direction: "auto"
    property color chartBackground: "white"
    property bool dark: false
    readonly property real barWidth: EaStyle.Sizes.fontPixelSize * 2.5
    readonly property real barHeight: EaStyle.Sizes.fontPixelSize * 0.7
    readonly property real barGap: EaStyle.Sizes.fontPixelSize * 0.5

    function inverted(map) {
        return ApplicationInfo.scanMapInverted(map, box.direction, box.chartBackground, box.dark);
    }

    model: maps.map(map => ApplicationInfo.scanColourTitle(map))
    // Room for the bar before the name, in the closed box (its label's padding, which its width counts) and in the
    // list.
    readonly property real leadingSpace: barWidth + barGap
    Binding {
        target: box.contentItemLabel
        property: "leftPadding"
        value: EaStyle.Sizes.fontPixelSize * 0.75 + box.leadingSpace
    }
    ColourMapBar {
        objectName: box.objectName + ".bar"
        x: box.leftPadding + EaStyle.Sizes.fontPixelSize * 0.75
        anchors.verticalCenter: parent.verticalCenter
        map: box.maps[box.currentIndex] ?? ""
        dark: box.dark
        inverted: box.inverted(map)
        barWidth: box.barWidth
        barHeight: box.barHeight
    }

    delegate: EaElements.MenuItem {
        id: entry

        required property int index
        required property var modelData

        width: parent !== null ? parent.width : 0
        height: EaStyle.Sizes.comboBoxHeight
        leftPadding: EaStyle.Sizes.fontPixelSize * 0.75 + box.leadingSpace
        font.family: box.font.family
        text: entry.modelData
        highlighted: box.highlightedIndex === entry.index
        hoverEnabled: box.hoverEnabled

        ColourMapBar {
            x: EaStyle.Sizes.fontPixelSize * 0.75
            anchors.verticalCenter: parent.verticalCenter
            map: box.maps[entry.index] ?? ""
            dark: box.dark
            inverted: box.inverted(map)
            barWidth: box.barWidth
            barHeight: box.barHeight
        }
    }
}
