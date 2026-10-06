// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import edi.app

// The pattern chart a page shows, made anew for each project the session opens: Qt Graphs kept drawing the
// previous project's calculated line beside the new one, at its old place, and only a new chart drops it. The old
// chart is hidden and then destroyed where it is: taken out of the window first, as a Loader does, its views
// handled their pending updates without a window and logged a critical message each.
Item {
    id: holder

    property ExperimentViewModel experiment: null
    property bool shown: true
    property PatternChart chart: null
    readonly property real toolbarRightInset: holder.chart ? holder.chart.toolbarRightInset : AppSizes.mainAreaMargin

    function renew() {
        const old = holder.chart;
        holder.chart = chartComponent.createObject(holder) as PatternChart;
        if (old) {
            old.visible = false;
            old.destroy();
        }
    }

    Component.onCompleted: holder.renew()

    Component {
        id: chartComponent

        PatternChart {
            anchors.fill: parent
            experiment: holder.experiment
            shown: holder.shown && visible
        }
    }

    Connections {
        target: Session
        function onProjectChanged() {
            holder.renew();
        }
    }
}
