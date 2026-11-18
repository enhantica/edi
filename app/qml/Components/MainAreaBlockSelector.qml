// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// The page's block selector as a row of its own at the top of the main area, under the tab bar (edi ADR-0017 §7):
// the combo box filling the width, then the previous and next buttons, ending where the chart toolbar below ends
// (`rightInset`), on the chart background, with the chart toolbar's margin above it and no line under it: the chart
// keeps its own margin above its toolbar, so one margin separates the two (owner, 2026-10-05). Placed by the main
// area (WorkflowPage), whose tabs' view starts `reservedHeight` lower so the charts give up that height.
Item {
    id: placement

    property alias blocks: selector.blocks
    property alias blocksTextRole: selector.blocksTextRole
    property alias blockKind: selector.blockKind
    property alias blockIndex: selector.blockIndex
    property alias outcomeRole: selector.outcomeRole
    property alias currentOutcome: selector.currentOutcome
    property alias templateRole: selector.templateRole
    property alias currentTemplate: selector.currentTemplate
    signal blockActivated(int index)

    // The main area's width and its tab bar's height.
    property real areaWidth: 0
    property real tabBarHeight: EaStyle.Sizes.tabBarHeight
    property real rightInset: margin
    // Where the row starts, from the main area's left edge: the shown view's toolbar's left edge (the owner, 2026-11-16).
    property real leftInset: leftMargin

    // The chart's own margin above its toolbar, here also above the row (PatternChart.topMargin); on the left the
    // main area's margin (owner, 2026-10-05).
    readonly property real margin: EaStyle.Sizes.fontPixelSize
    readonly property real leftMargin: AppSizes.mainAreaMargin
    // The margin above the row and the row; the chart's own margin above its toolbar is the one below it.
    readonly property real reservedHeight: visible ? margin + height : 0

    x: leftInset
    y: tabBarHeight + margin
    width: areaWidth - leftInset - rightInset
    height: selector.height

    // The row's band, across the main area, in the chart's background.
    Rectangle {
        x: -placement.leftInset
        y: -placement.margin
        width: placement.areaWidth
        height: placement.height + 2 * placement.margin
        color: EaStyle.Colors.chartBackground
    }

    // A series of joint fits chooses a point and a bank in place of an experiment (SeriesSelectors).
    readonly property bool series: blockKind === "experiment" && Session.project !== null && Session.project.series

    BlockSelector {
        id: selector
        objectName: "mainArea.blocks"
        visible: !placement.series
        width: placement.width
        backgroundColor: EaStyle.Colors.chartBackground
        onBlockActivated: index => placement.blockActivated(index)
    }
    SeriesSelectors {
        objectName: "mainArea.series"
        visible: placement.series
        width: placement.width
        project: placement.series ? Session.project : null
        viewKey: AppState.mainView?.currentKey ?? ""
    }
}
