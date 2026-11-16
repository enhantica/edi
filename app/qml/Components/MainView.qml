// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A workflow page's own main view (edi ADR-0017 §2; the owner, 2026-11-14 item 5): each of the Structure, Experiment
// and Analysis pages holds one, in its main area, and it moves with the page. Its tabs are the page's set (`tabKeys`)
// out of Structure, Pattern, Correlations, Stacked, Map and Evolution: a tab that will become available is shown
// disabled, one that is irrelevant (Stacked and Map with one dataset, Evolution without a scan) is hidden. The page's
// first tab opens with each project; after that the shown tab stays. The block selector above the views lists the
// structures on the Structure tab and the experiments on the others.
EaComponents.MainContent {
    id: view

    // On screen: its page is shown.
    property bool shown: false
    // The page's tabs, by key, its own first: the others are hidden.
    property var tabKeys: ["structure", "pattern", "correlations", "stacked", "map", "evolution"]
    readonly property var allKeys: ["structure", "pattern", "correlations", "stacked", "map", "evolution"]
    function shows(key) {
        return tabKeys.indexOf(key) >= 0;
    }
    readonly property int ownTab: Math.max(0, allKeys.indexOf(tabKeys[0]))

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
            showMainTab(ownTab);
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
    // The page's own tab opens the first time the page is shown with a project, even with nothing to show yet; after
    // that the tab the user is on stays until they pick another, and the view never switches by itself (the owner,
    // 2026-11-11; edi ADR-0017 §2).
    property bool ownTabOpened: false
    function openOwnTabOnFirstVisit() {
        if (!bar || !shown || ownTabOpened)
            return;
        ownTabOpened = true;
        showMainTab(ownTab);
    }
    onProjectChanged: {
        ownTabOpened = false;
        openOwnTabOnFirstVisit();
    }
    onShownChanged: {
        openOwnTabOnFirstVisit();
        Qt.callLater(showCurrentPage);
    }
    onBarChanged: openOwnTabOnFirstVisit()
    onTabIndexChanged: Qt.callLater(showCurrentPage)
    // The pages' list keeps its old position when the tab changes while the view is hidden (a scan project opened
    // straight onto Analysis showed the previous project's structure under the Pattern tab): put it on the current
    // tab's page whenever the view shows or the tab changes.
    function showCurrentPage() {
        const pages = view.children.length > 1 ? view.children[1] : null;
        if (pages && pages.contentItem && pages.contentItem.positionViewAtIndex !== undefined && pages.currentIndex >= 0)
            pages.contentItem.positionViewAtIndex(pages.currentIndex, ListView.Beginning);
    }

    Connections {
        target: AppState
        function onEvolutionRequested() {
            if (view.shows("evolution"))
                view.showMainTab(5);
        }
    }

    // A hidden tab takes no width, so the tab bar keeps no gap for it.
    tabs: [
        IconTabButton {
            id: structureTab

            objectName: "mainArea.tab.structure"
            text: qsTr("Structure")
            visible: view.shows("structure")
            width: visible ? Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitContentWidth + leftPadding + rightPadding) : 0
            enabled: view.hasStructures
        },
        IconTabButton {
            objectName: "mainArea.tab.pattern"
            text: qsTr("Pattern")
            visible: view.shows("pattern")
            width: visible ? Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitContentWidth + leftPadding + rightPadding) : 0
            enabled: view.hasExperiments
        },
        // The last fit's parameter correlations for the shown experiment.
        IconTabButton {
            objectName: "mainArea.tab.correlations"
            text: qsTr("Correlations")
            visible: view.shows("correlations")
            width: visible ? Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitContentWidth + leftPadding + rightPadding) : 0
            enabled: view.correlationsShown
        },
        // A scan's or a joint fit's patterns, stacked and as a map (edi ADR-0041): only with several datasets.
        IconTabButton {
            objectName: "mainArea.tab.stacked"
            text: qsTr("Stacked")
            visible: view.shows("stacked") && (view.patternViews || view.singleCrystals)
            width: visible ? Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitContentWidth + leftPadding + rightPadding) : 0
        },
        IconTabButton {
            objectName: "mainArea.tab.map"
            text: qsTr("Map")
            visible: view.shows("map") && view.patternViews && !view.singleCrystals
            width: visible ? Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitContentWidth + leftPadding + rightPadding) : 0
        },
        // A fitted parameter across a scan's datasets (edi ADR-0017 §19), in a scan project (edi ADR-0046).
        IconTabButton {
            objectName: "mainArea.tab.evolution"
            text: qsTr("Evolution")
            visible: view.shows("evolution") && view.project !== null && view.project.scan
            width: visible ? Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitContentWidth + leftPadding + rightPadding) : 0
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
        text: view.tabIndex === 0 ? qsTr("No structure yet") : qsTr("No pattern yet")
    }
}
