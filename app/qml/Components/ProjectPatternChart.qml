// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import edi.app

// The pattern chart a page shows, made anew for each project the session opens: Qt Graphs kept drawing the
// previous project's calculated line beside the new one, at its old place, and only a new chart drops it.
Loader {
    id: loader

    property ExperimentViewModel experiment: null
    property bool shown: true
    readonly property real toolbarRightInset: loader.item ? (loader.item as PatternChart).toolbarRightInset : AppSizes.mainAreaMargin

    sourceComponent: PatternChart {
        experiment: loader.experiment
        shown: loader.shown
    }

    Connections {
        target: Session
        function onProjectChanged() {
            loader.active = false;
            loader.active = true;
        }
    }
}
