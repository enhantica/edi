// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A workflow page's own main view (edi ADR-0017 §2; the owner, 2026-11-14 item 5): each of the Structure, Experiment
// and Analysis pages holds one, in its main area, and it moves with the page. Its tabs are the page's set (`tabKeys`)
// out of Structure, Pattern, Meas vs calc, Evolution, Stacked, Map and Correlations, in the page's order: a tab that will
// become available is shown disabled, one that is irrelevant (Stacked and Map with one dataset, Evolution without a
// scan) is hidden. The page's first tab opens with each project; after that the shown tab stays. The block selector
// above the views lists the structures on the Structure tab and the experiments on the others.
EaComponents.MainContent {
    id: view

    // On screen: its page is shown.
    property bool shown: false
    // The page's tabs, by key, in the page's order with its own first: the others are hidden.
    property var tabKeys: ["structure", "pattern", "meascalc", "evolution", "stacked", "map", "correlations"]
    // Every tab, in the order the tabs and views below are declared: an order every page's set keeps (each page's
    // tabs are a part of it, in its own order). Structure has two places, first (the Structure page) and after Meas vs
    // calc (the Analysis page), with the one structure view in the place the page uses. Tabs cannot be moved after
    // they are made: the bar put them back in this order.
    readonly property var allKeys: ["structure", "pattern", "meascalc", "structureLate", "evolution", "stacked", "map", "correlations"]
    function shows(key) {
        return tabKeys.indexOf(key) >= 0;
    }
    readonly property bool structureLate: shows("structure") && shows("pattern") && tabKeys.indexOf("structure") > tabKeys.indexOf("pattern")
    function tabOf(key) {
        return Math.max(0, allKeys.indexOf(key === "structure" && structureLate ? "structureLate" : key));
    }
    readonly property int ownTab: tabOf(tabKeys[0])
    readonly property string currentKey: (allKeys[tabIndex] ?? "").replace("structureLate", "structure")

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
        if (!correlationsShown && currentKey === "correlations")
            showMainTab(ownTab);
    }

    // The tab bar, reached from its first tab (the base names it nowhere).
    readonly property var bar: structureTab.TabBar.tabBar
    readonly property int tabIndex: bar ? bar.currentIndex : 0
    readonly property bool structureShown: currentKey === "structure"
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
                view.showMainTab(view.tabOf("evolution"));
        }
    }

    // A hidden tab takes no width, so the tab bar keeps no gap for it.
    tabs: [
        IconTabButton {
            id: structureTab

            objectName: "mainArea.tab.structure"
            text: qsTr("Structure")
            visible: view.shows("structure") && !view.structureLate
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
        // Measured against calculated values, with the y = x line, apart from Pattern and with its own settings (the
        // owner, 2026-11-16): enabled once the shown experiment has both.
        IconTabButton {
            objectName: "mainArea.tab.measCalc"
            text: qsTr("Meas vs calc")
            visible: view.shows("meascalc")
            width: visible ? Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitContentWidth + leftPadding + rightPadding) : 0
            enabled: measCalcTab.available
        },
        // Structure in the Analysis page's place, after Meas vs calc.
        IconTabButton {
            objectName: "mainArea.tab.structure"
            text: qsTr("Structure")
            visible: view.shows("structure") && view.structureLate
            width: visible ? Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitContentWidth + leftPadding + rightPadding) : 0
            enabled: view.hasStructures
        },
        // A fitted parameter across a scan's datasets (edi ADR-0017 §19), in a scan project (edi ADR-0046).
        IconTabButton {
            objectName: "mainArea.tab.evolution"
            text: qsTr("Evolution")
            visible: view.shows("evolution") && view.project !== null && view.project.scan
            width: visible ? Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitContentWidth + leftPadding + rightPadding) : 0
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
        // The last fit's parameter correlations for the shown experiment.
        IconTabButton {
            objectName: "mainArea.tab.correlations"
            text: qsTr("Correlations")
            visible: view.shows("correlations")
            width: visible ? Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitContentWidth + leftPadding + rightPadding) : 0
            enabled: view.correlationsShown
        }
    ]
    items: [
        // The Structure tab's view, in the first place or, on the Analysis page, after Meas vs calc (structureLate).
        Item {
            id: structureFirst

            StructureView {
                id: structureView

                parent: view.structureLate ? structureLater : structureFirst
                anchors.fill: parent
                structure: view.project ? view.project.currentStructure : null
                options: view.project ? view.project.structureViewOptions : null
                // With no structure the tab shows only its empty state, no view and no toolbar.
                visible: view.hasStructures
                shown: view.shown && (view.structureLate ? structureLater : structureFirst).SwipeView.isCurrentItem
            }
        },
        ProjectPatternChart {
            id: chartView

            experiment: view.project ? view.project.currentExperiment : null
            axisProject: view.project
            settingsPage: "pattern"
            visible: view.hasExperiments
            shown: view.shown && SwipeView.isCurrentItem
        },
        Item {
            id: measCalcTab

            readonly property bool shown: view.shown && SwipeView.isCurrentItem
            readonly property ExperimentViewModel experiment: view.project ? view.project.currentExperiment : null
            readonly property bool singleCrystal: experiment !== null && experiment.sampleForm === ExperimentViewModel.SingleCrystal
            readonly property var reflections: singleCrystal ? experiment.singleCrystalReflections : null
            readonly property bool available: experiment !== null && (singleCrystal ? reflections !== null && !reflections.simulated && reflections.calculated.length > 0 : !experiment.calculationOnly)
            readonly property real toolbarRightInset: singleCrystal ? measCalcCrystal.toolbarRightInset : measCalcPowder.toolbarRightInset

            SingleCrystalChart {
                id: measCalcCrystal

                objectName: "singleCrystal.measCalc"
                anchors.fill: parent
                visible: measCalcTab.singleCrystal
                comparison: true
                experiment: measCalcTab.singleCrystal ? measCalcTab.experiment : null
                project: view.project
                shown: measCalcTab.shown && measCalcTab.singleCrystal
            }
            MeasCalcChart {
                id: measCalcPowder

                anchors.fill: parent
                visible: !measCalcTab.singleCrystal
                experiment: measCalcTab.singleCrystal ? null : measCalcTab.experiment
                shown: measCalcTab.shown && !measCalcTab.singleCrystal && measCalcTab.available
            }
        },
        Item {
            id: structureLater
        },
        EvolutionChart {
            id: evolutionChart

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
        CorrelationChart {
            id: correlationChart

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
        // The selector row fills the main view's width with the standard margin on every chart view (the owner,
        // 2026-11-16); the structure view's row ends where its toolbar does.
        rightInset: view.currentKey === "structure" ? structureView.toolbarRightInset : AppSizes.mainAreaMargin
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

    // Save image for the shown tab, in the main view's bottom-left corner, inset as the toolbar buttons are spaced (the
    // owner, 2026-11-16). Each tab's view names what it saves (imageItem, imageToolbar, imageName, imageCropsToolbar).
    SaveImageButton {
        id: saveImage

        readonly property Item source: ({
                "structure": view.hasStructures ? structureView.imageItem : null,
                "pattern": view.hasExperiments ? chartView.imageItem : null,
                "meascalc": measCalcTab.available ? (measCalcTab.singleCrystal ? measCalcCrystal.imageItem : measCalcPowder.imageItem) : null,
                "evolution": evolutionChart.imageItem,
                "stacked": view.singleCrystals ? stackedCrystals.imageItem : stackedChart.imageItem,
                "map": mapChart.imageItem,
                "correlations": correlationChart.imageItem
            })[view.currentKey] ?? null

        objectName: "mainArea.saveImage"
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.leftMargin: AppSizes.toolbarSpacing
        anchors.bottomMargin: AppSizes.toolbarSpacing
        z: 2
        visible: source !== null
        target: source
        toolbar: source ? source.imageToolbar : null
        fileName: source ? source.imageName : "image"
        cropToolbar: source ? source.imageCropsToolbar : true
    }

    // The Structure and Pattern tabs' empty states, as the pages had them: on the shown tab, when it has nothing to draw.
    EmptyStateLabel {
        objectName: "mainArea.emptyState"
        anchors.centerIn: parent
        visible: (view.currentKey === "structure" && !view.hasStructures) || (view.currentKey === "pattern" && !view.hasExperiments)
        text: view.currentKey === "structure" ? qsTr("No structure yet") : qsTr("No pattern yet")
    }
}
