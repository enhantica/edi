// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The one main view of the Structure, Experiment and Analysis pages (the owner, 2026-11-10; edi ADR-0017 §2): it stays
// where it is while the app bar's pages change only the sidebar beside it. Its tabs are every view those pages had,
// once: Structure, Pattern, Correlations, Stacked, Map and Evolution. A page's first visit opens its own tab; later the
// shown tab stays. The block selector above the views lists the structures on the Structure tab and the experiments on
// the others.
EaComponents.MainContent {
    id: view

    // On screen: one of the three pages is shown.
    property bool shown: false
    // The page whose sidebar is shown, an AppState.Page value: its first visit opens its own tab.
    property int page: -1

    readonly property ProjectViewModel project: Session.project
    readonly property bool hasStructures: project !== null && project.structures.count > 0
    readonly property bool hasExperiments: project !== null && project.experiments.count > 0
    // The Stacked and Map tabs: a scan, or a joint fit of several experiments.
    readonly property bool patternViews: project !== null && (project.scan || project.scanViews.joint)
    // A project of several single crystals: the Stacked tab draws all of them on one F²calc-against-F²meas chart, and
    // there is no Map.
    readonly property bool singleCrystals: project !== null && project.singleCrystalExperiments.length > 1
    readonly property bool scanMode: project !== null && project.fit.scanMode
    readonly property bool measured: project !== null && project.fit.measured
    // The Correlations tab: enabled once a fit has produced correlations to show, as Stacked and Map are only with
    // something to show (owner record 2026-11-11, item 4). Off again after Undo or in a new project, when the view
    // goes back to the pattern.
    readonly property bool correlationsShown: measured && correlationChart.available
    onCorrelationsShownChanged: {
        if (!correlationsShown && tabIndex === 2)
            showMainTab(hasExperiments ? 1 : 0);
    }

    // The tab bar, reached from its first tab (the base names it nowhere).
    readonly property var bar: structureTab.TabBar.tabBar
    readonly property int tabIndex: bar ? bar.currentIndex : 0
    readonly property bool structureShown: tabIndex === 0
    // The structure view's controller, for the Structure page's Appearance group.
    readonly property var structureController: structureView.controller

    function showMainTab(index) {
        if (bar)
            bar.currentIndex = index;
    }
    // The first visit to a page in a project selects the page's own tab, Structure on the Structure page and Pattern on
    // the others, even with nothing to show yet; after that the tab the user is on stays across page switches until
    // they pick another, and the view never switches by itself (the owner, 2026-11-11; edi ADR-0017 §2).
    property var visitedPages: ({})
    function openOwnTabOnFirstVisit() {
        if (!bar || !shown || page < 0 || visitedPages[page])
            return;
        visitedPages[page] = true;
        showMainTab(page === AppState.Page.Structure ? 0 : 1);
    }
    onProjectChanged: {
        visitedPages = {};
        openOwnTabOnFirstVisit();
    }
    onPageChanged: openOwnTabOnFirstVisit()
    onShownChanged: openOwnTabOnFirstVisit()
    onBarChanged: openOwnTabOnFirstVisit()

    Connections {
        target: AppState
        function onEvolutionRequested() {
            view.showMainTab(5);
        }
    }

    tabs: [
        IconTabButton {
            id: structureTab

            objectName: "mainArea.tab.structure"
            text: qsTr("Structure")
            enabled: view.hasStructures
        },
        IconTabButton {
            objectName: "mainArea.tab.pattern"
            text: qsTr("Pattern")
            enabled: view.hasExperiments
        },
        // The last fit's parameter correlations for the shown experiment.
        IconTabButton {
            objectName: "mainArea.tab.correlations"
            text: qsTr("Correlations")
            enabled: view.correlationsShown
        },
        // A scan's or a joint fit's patterns, stacked and as a map (edi ADR-0041).
        IconTabButton {
            objectName: "mainArea.tab.stacked"
            text: qsTr("Stacked")
            enabled: view.patternViews || view.singleCrystals
        },
        IconTabButton {
            objectName: "mainArea.tab.map"
            text: qsTr("Map")
            enabled: view.patternViews && !view.singleCrystals
        },
        // A fitted parameter across a scan's datasets (edi ADR-0017 §19): shown in the sequential and independent
        // fitting modes, enabled in a scan project (edi ADR-0046).
        IconTabButton {
            objectName: "mainArea.tab.evolution"
            text: qsTr("Evolution")
            visible: view.scanMode
            // The base tab's own width, and none while hidden, so the tab bar keeps no gap for it.
            width: visible ? Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitContentWidth + leftPadding + rightPadding) : 0
            enabled: view.project !== null && view.project.scan
        }
    ]
    items: [
        StructureView {
            id: structureView

            structure: view.project ? view.project.currentStructure : null
            options: view.project ? view.project.structureViewOptions : null
            // With no structure the tab shows only its empty state, no view and no toolbar.
            visible: view.hasStructures
            shown: view.shown && SwipeView.isCurrentItem
        },
        ProjectPatternChart {
            id: chartView

            experiment: view.project ? view.project.currentExperiment : null
            axisProject: view.project
            settingsPage: "pattern"
            visible: view.hasExperiments
            shown: view.shown && SwipeView.isCurrentItem
        },
        CorrelationChart {
            id: correlationChart

            project: view.project
            shown: view.shown && SwipeView.isCurrentItem
        },
        Item {
            id: stackedTab

            readonly property bool shown: view.shown && SwipeView.isCurrentItem

            ScanViewChart {
                id: stackedChart

                anchors.fill: parent
                visible: !view.singleCrystals
                project: view.project
                mode: "stacked"
                shown: stackedTab.shown && !view.singleCrystals
            }
            SingleCrystalChart {
                id: stackedCrystals

                objectName: "singleCrystal.stacked"
                anchors.fill: parent
                visible: view.singleCrystals
                stackedExperiments: view.singleCrystals ? view.project.singleCrystalExperiments : []
                project: view.project
                shown: stackedTab.shown && view.singleCrystals
            }
        },
        ScanViewChart {
            id: mapChart

            project: view.project
            mode: "map"
            shown: view.shown && SwipeView.isCurrentItem
        },
        EvolutionChart {
            project: view.project
            shown: view.shown && SwipeView.isCurrentItem
        }
    ]

    // The structures on the Structure tab, the experiments on the others (edi ADR-0017 §7).
    MainAreaBlockSelector {
        id: blockSelector

        readonly property bool experiments: !view.structureShown

        visible: blocks !== null && blocks.count > 0
        areaWidth: view.width
        // Where the shown view's toolbar ends, so the selector and the toolbar share one right edge.
        rightInset: [structureView.toolbarRightInset, chartView.toolbarRightInset, correlationChart.toolbarRightInset, view.singleCrystals ? stackedCrystals.toolbarRightInset : stackedChart.toolbarRightInset, mapChart.toolbarRightInset, chartView.toolbarRightInset][view.tabIndex] ?? EaStyle.Sizes.fontPixelSize
        blocks: view.project ? (experiments ? view.project.experiments : view.project.structures) : null
        blocksTextRole: "label"
        blockKind: experiments ? "experiment" : "structure"
        outcomeRole: experiments ? "fitOutcome" : ""
        currentOutcome: experiments && view.project && view.project.currentExperiment ? view.project.currentExperiment.fitOutcome : ""
        templateRole: experiments && view.project !== null && view.project.scan ? "isTemplate" : ""
        currentTemplate: experiments && view.project !== null && view.project.scan && view.project.currentExperimentIndex === view.project.templateIndex
        blockIndex: view.project ? (experiments ? view.project.currentExperimentIndex : view.project.currentStructureIndex) : -1
        onBlockActivated: index => {
            if (experiments)
                view.project.currentExperimentIndex = index;
            else
                view.project.currentStructureIndex = index;
        }
    }

    // The tabs' view (the base's SwipeView, the main area's second child, anchored under the tab bar) starts below the
    // selector.
    Binding {
        target: view.children.length > 1 ? view.children[1].anchors : null
        property: "topMargin"
        value: blockSelector.reservedHeight
    }

    // The Structure and Pattern tabs' empty states, as the pages had them: on the shown tab, when it has nothing to draw.
    EmptyStateLabel {
        objectName: "mainArea.emptyState"
        anchors.centerIn: parent
        visible: (view.tabIndex === 0 && !view.hasStructures) || (view.tabIndex === 1 && !view.hasExperiments)
        text: view.tabIndex === 0 ? qsTr("No structure") : qsTr("No pattern")
    }
}
