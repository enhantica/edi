// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A chart's toolbar (edi ADR-0041 §7; the owner, 2026-10-24), the one rule for the Pattern, Stacked and Map toolbars:
// every control on one line when they all fit; otherwise every combobox on the lines above, as many as fit on each,
// and every button on the last line. Each line is centred between `leftEdge` and `rightEdge`, the span of the block
// selector row above the chart, so the selector and every toolbar line share one centre (the owner, 2026-10-25). A child
// with `closedTexts` (ToolbarComboBox) is a combobox; any other visible child is a button, or a row of them kept
// whole. Comboboxes with a different `toolbarGroup` (a string, "" when not set) are a group's spacing apart, as the
// comboboxes are from the buttons: the axes, the Stacked spacing and the Map's colours each a group (the owner,
// 2026-10-26).
Item {
    id: lines

    // The room the lines may take, in this item's coordinates, and its middle, where each line is centred.
    property real leftEdge: 0
    property real rightEdge: width
    readonly property real centre: (leftEdge + rightEdge) / 2
    readonly property real spacing: AppSizes.toolbarSpacing
    // Between the comboboxes and the buttons on one line.
    readonly property real groupSpacing: EaStyle.Sizes.fontPixelSize * 0.5 + 2 * AppSizes.toolbarSpacing
    // The controls shown, and every width the layout depends on.
    readonly property var units: ApplicationInfo.toolbarUnits()
    readonly property string measure: ApplicationInfo.toolbarMeasure()
    // How many lines the controls take.
    property int lineCount: 0

    function isComboBox(unit) {
        return ApplicationInfo.toolbarIsComboBox(unit);
    }
    function groupOf(unit) {
        return ApplicationInfo.toolbarGroupOf(unit);
    }
    // The gap before a combobox that follows `before` on a line.
    function boxGap(before, unit) {
        return ApplicationInfo.toolbarBoxGap(before, unit);
    }
    function widthOf(row, gap) {
        return ApplicationInfo.toolbarRowWidth(row, gap, false);
    }
    function boxesWidth(row) {
        return ApplicationInfo.toolbarRowWidth(row, undefined, true);
    }
    function layout() {
        ApplicationInfo.toolbarLayout();
    }

    onMeasureChanged: Qt.callLater(layout)
    Component.onCompleted: layout()
}
