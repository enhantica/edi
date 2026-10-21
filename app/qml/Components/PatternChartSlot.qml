// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import edi.app

// A page's place for the app's one pattern chart (edi ADR-0017 §15): when the place is shown it takes the chart, which
// moves here with its selectors, view and toggles as they are. A place not shown holds nothing to draw.
Item {
    id: slot

    property bool shown: false
    readonly property bool holds: AppState.patternChartSlot === slot
    readonly property real toolbarRightInset: AppState.patternChart ? AppState.patternChart.toolbarRightInset : AppSizes.mainAreaMargin

    function take() {
        if (slot.shown)
            AppState.placePatternChart(slot);
    }

    onShownChanged: take()
    Component.onCompleted: take()
    Component.onDestruction: AppState.releasePatternChart(slot)
}
