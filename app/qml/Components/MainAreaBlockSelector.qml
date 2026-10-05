// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// The page's block selector as a row of its own at the top of the main area, under the tab bar (edi ADR-0017 §7):
// the combo box filling the width, then the previous and next buttons, ending where the chart toolbar below ends
// (`rightInset`), on the chart background, with the chart toolbar's margin above it and a separating line a margin
// below it. Placed by the main area (WorkflowPage), whose tabs' view starts `reservedHeight` lower so the charts give
// up that height.
Item {
    id: placement

    property alias blocks: selector.blocks
    property alias blocksTextRole: selector.blocksTextRole
    property alias blockKind: selector.blockKind
    property alias blockIndex: selector.blockIndex
    property alias outcomeRole: selector.outcomeRole
    property alias currentOutcome: selector.currentOutcome
    signal blockActivated(int index)

    // The main area's width and its tab bar's height.
    property real areaWidth: 0
    property real tabBarHeight: EaStyle.Sizes.tabBarHeight
    property real rightInset: margin

    // The chart's own margin above its toolbar, here also above and beside the row (PatternChart.toolbarGap).
    readonly property real margin: EaStyle.Sizes.fontPixelSize
    // The margin above the row, the row, the margin down to its line, and the line: the chart below keeps its own
    // margin above its toolbar, so the line has the same margin under it as over it.
    readonly property real reservedHeight: visible ? 2 * margin + height + EaStyle.Sizes.borderThickness : 0

    x: margin
    y: tabBarHeight + margin
    width: areaWidth - margin - rightInset
    height: selector.height

    // The row's band, across the main area, in the chart's background.
    Rectangle {
        x: -placement.margin
        y: -placement.margin
        width: placement.areaWidth
        height: placement.height + 2 * placement.margin
        color: EaStyle.Colors.chartBackground
    }
    // The line between the row and the chart, across the main area, a margin under the row.
    Rectangle {
        x: -placement.margin
        y: placement.height + placement.margin
        width: placement.areaWidth
        height: EaStyle.Sizes.borderThickness
        // The legend box's border colour.
        color: EaStyle.Colors.chartGridLine
    }

    BlockSelector {
        id: selector
        objectName: "mainArea.blocks"
        width: placement.width
        backgroundColor: EaStyle.Colors.chartBackground
        onBlockActivated: index => placement.blockActivated(index)
    }
}
