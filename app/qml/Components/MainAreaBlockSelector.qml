// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// The page's block selector in the main view's tab bar (edi ADR-0017 §7): right-aligned, half the main area
// wide, on the chart background. Below `AppSizes.mainAreaSelectorBreak` it moves under the tab bar, as wide as
// the main area. Placed by the main area (WorkflowPage), which keeps its tabs clear of it: `reservedWidth`
// is what the tabs must leave free in the tab bar's row, `reservedHeight` what the tabs' view starts below.
Item {
    id: placement

    property alias blocks: selector.blocks
    property alias blocksTextRole: selector.blocksTextRole
    property alias blockKind: selector.blockKind
    property alias blockIndex: selector.blockIndex
    signal blockActivated(int index)

    // The main area's width and its tab bar's height.
    property real areaWidth: 0
    property real tabBarHeight: EaStyle.Sizes.tabBarHeight

    readonly property bool under: areaWidth < AppSizes.mainAreaSelectorBreak
    readonly property real margin: EaStyle.Sizes.fontPixelSize * 0.5
    readonly property real reservedWidth: visible && !under ? width + 2 * margin : 0
    readonly property real reservedHeight: visible && under ? height + 2 * margin : 0

    x: under ? margin : areaWidth / 2
    y: under ? tabBarHeight + margin : (tabBarHeight - height) / 2
    width: under ? areaWidth - 2 * margin : areaWidth / 2 - margin
    height: selector.height

    BlockSelector {
        id: selector
        objectName: "mainArea.blocks"
        width: placement.width
        backgroundColor: EaStyle.Colors.chartBackground
        onBlockActivated: index => placement.blockActivated(index)
    }
}
