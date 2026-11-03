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
    // Set: the chart's x axis is this project's (the Analysis page's, which the report follows).
    property ProjectViewModel axisProject: null
    // "pattern" for a page's chart, which follows the app's one pattern view (edi ADR-0017 §15).
    property string settingsPage: ""
    property bool shown: true
    property PatternChart chart: null
    // A single crystal has reflections, not a pattern: its F²calc-vs-F²meas chart shows instead.
    readonly property bool singleCrystal: experiment !== null && experiment.sampleForm === ExperimentViewModel.SingleCrystal
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
            visible: !holder.singleCrystal
            experiment: holder.experiment
            axisProject: holder.axisProject
            settingsPage: holder.settingsPage
            shown: holder.shown && visible
        }
    }

    Connections {
        target: Session
        function onProjectChanged() {
            holder.renew();
        }
    }

    Item {
        anchors.fill: parent
        visible: holder.singleCrystal
        z: 1

        SingleCrystalChart {
            anchors.fill: parent
            experiment: holder.singleCrystal ? holder.experiment : null
            // The project too: another one shows the curves its legend hid.
            project: holder.axisProject
            shown: holder.shown && holder.singleCrystal
        }
    }
}
