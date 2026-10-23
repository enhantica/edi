// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Components as EaComponents

import edi.app

// The Analysis page (easydiffractionbeta Pages/Analysis): the chart's place in the main area, with the
// experiment selector in its tab bar; the parameter table and Fitting in Main; the analysis block's `.edi`
// categories in Extra (packet §2b (iv), §15.6); analysis.edi in Text.
WorkflowPage {
    id: page

    readonly property ProjectViewModel project: Session.project
    readonly property AnalysisViewModel analysis: project ? project.analysis : null
    readonly property ExperimentViewModel experiment: project ? project.currentExperiment : null
    // The Stacked and Map tabs: a scan, or a joint fit of several experiments.
    readonly property bool patternViews: project !== null && (project.scan || project.scanViews.joint)
    // A project of several single crystals: the Stacked tab draws all of them on one F²calc-against-F²meas chart, and
    // there is no Map.
    readonly property bool singleCrystals: project !== null && project.singleCrystalExperiments.length > 1
    readonly property bool scanMode: project !== null && project.fit.scanMode
    // Leaving the scan modes hides Evolution: a page showing it goes back to the pattern.
    onScanModeChanged: {
        if (!scanMode)
            page.showMainTab(0);
    }

    // Each category's content, by `.edi` category id.
    readonly property var contents: ({
            "minimizer": minimizerContent,
            "fitting_mode": fittingModeContent,
            "alias": aliasesContent,
            "constraint": constraintsContent,
            "joint_fit": jointFitContent,
            "sequential_fit": sequentialFitContent,
            "sequential_fit_extract": sequentialExtractContent,
            "fit_parameter": fitStartContent
        })

    pageName: "analysis"
    defaultInfo: project ? "" : qsTr("No analysis done")
    mainTabs: [
        IconTabButton {
            objectName: "mainArea.analysis.tab.fitting"
            // The view's name, text only (edi ADR-0017 §2).
            text: qsTr("Pattern")
        },
        // The last fit's parameter correlations for the shown experiment (diffraction-lib's correlation heatmap),
        // before Evolution: every fit has them (owner, 2026-10-11).
        IconTabButton {
            objectName: "mainArea.analysis.tab.correlations"
            text: qsTr("Correlations")
        },
        // A fitted parameter across a scan's datasets (edi ADR-0017 §19). Shown only in the sequential and
        // independent fitting modes, and enabled in a scan project (edi ADR-0046).
        IconTabButton {
            objectName: "mainArea.analysis.tab.evolution"
            text: qsTr("Evolution")
            visible: page.scanMode
            // The base tab's own width, and none while hidden, so the tab bar keeps no gap for it.
            width: visible ? Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitContentWidth + leftPadding + rightPadding) : 0
            enabled: page.project !== null && page.project.scan
        },
        // Every pattern of a scan, or every experiment of a joint fit, one above another, and the same as a 2D map
        // (edi ADR-0041; the joint fit's, the owner, 2026-10-22).
        IconTabButton {
            objectName: "mainArea.analysis.tab.stacked"
            text: qsTr("Stacked")
            enabled: page.patternViews || page.singleCrystals
        },
        IconTabButton {
            objectName: "mainArea.analysis.tab.map"
            text: qsTr("Map")
            enabled: page.patternViews && !page.singleCrystals
        }
    ]
    mainItems: [
        ProjectPatternChart {
            id: chartView
            experiment: page.project ? page.project.currentExperiment : null
            axisProject: page.project
            settingsPage: "pattern"
            shown: page.current && SwipeView.isCurrentItem
        },
        CorrelationChart {
            project: page.project
            shown: page.current && SwipeView.isCurrentItem
        },
        EvolutionChart {
            id: evolutionChart
            project: page.project
            shown: page.current && SwipeView.isCurrentItem
        },
        Item {
            id: stackedTab

            readonly property bool shown: page.current && SwipeView.isCurrentItem

            ScanViewChart {
                anchors.fill: parent
                visible: !page.singleCrystals
                project: page.project
                mode: "stacked"
                shown: stackedTab.shown && !page.singleCrystals
            }
            SingleCrystalChart {
                objectName: "singleCrystal.stacked"
                anchors.fill: parent
                visible: page.singleCrystals
                stackedExperiments: page.singleCrystals ? page.project.singleCrystalExperiments : []
                shown: stackedTab.shown && page.singleCrystals
            }
        },
        ScanViewChart {
            project: page.project
            mode: "map"
            shown: page.current && SwipeView.isCurrentItem
        }
    ]
    extrasEnabled: analysis !== null
    textEnabled: analysis !== null
    basicItem: Component {
        EaComponents.SideBarColumn {
            id: analysisSidebar
            // The fitted inputs are not edited while a fit runs.
            ParametersGroup {
                tableViewportHeight: analysisSidebar.height - fitting.height
                project: page.project
                enabled: !(page.project && page.project.fit.running)
            }
            FittingGroup {
                id: fitting
            }
        }
    }
    extrasItem: Component {
        EaComponents.SideBarColumn {
            Repeater {
                model: page.analysis ? page.analysis.categories : null
                delegate: CategoryGroup {
                    shownTier: "Extras"
                    contents: page.contents
                }
            }
        }
    }
    // The page's view options (edi ADR-0031 §2): how a followed scan redraws. The chart's own choices are on the chart.
    settingsItem: Component {
        EaComponents.SideBarColumn {
            PatternUpdatesGroup {}
        }
    }
    textItem: Component {
        TextTab {
            source: page.analysis ? page.analysis.text : null
        }
    }
    // The same selector as the Experiment page's, over the one current experiment the project holds, so
    // choosing here or there is one choice (edi ADR-0017 §7).
    blockSelectorShown: true
    blockSelectorRightInset: chartView.toolbarRightInset
    blocks: project ? project.experiments : null
    blocksTextRole: "label"
    blockKind: "experiment"
    blockOutcomeRole: "fitOutcome"
    blockCurrentOutcome: experiment ? experiment.fitOutcome : ""
    blockTemplateRole: project !== null && project.scan ? "isTemplate" : ""
    blockCurrentTemplate: project !== null && project.scan && project.currentExperimentIndex === project.templateIndex
    blockIndex: project ? project.currentExperimentIndex : -1
    onBlockActivated: index => page.project.currentExperimentIndex = index
    Connections {
        target: AppState
        function onEvolutionRequested() {
            page.showMainTab(2);
        }
    }
    continueText: qsTr("Continue")
    onContinueClicked: AppState.open(AppState.Page.Report)

    Component {
        id: minimizerContent
        MinimizerGroup {
            analysis: page.analysis
        }
    }
    Component {
        id: fittingModeContent
        FittingModeGroup {
            analysis: page.analysis
        }
    }
    Component {
        id: aliasesContent
        AliasesGroup {
            analysis: page.analysis
        }
    }
    Component {
        id: constraintsContent
        ConstraintsGroup {
            analysis: page.analysis
        }
    }
    Component {
        id: jointFitContent
        JointFitGroup {
            project: page.project
        }
    }
    Component {
        id: sequentialExtractContent
        SequentialExtractGroup {
            analysis: page.analysis
        }
    }
    Component {
        id: fitStartContent
        FitStartGroup {
            analysis: page.analysis
        }
    }
    Component {
        id: sequentialFitContent
        SequentialFitGroup {
            analysis: page.analysis
        }
    }
}
