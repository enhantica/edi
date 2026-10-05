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
    readonly property EvolutionViewModel evolution: project ? project.evolution : null
    // The Evolution tab is the one shown: the selector row then chooses the parameter it draws.
    readonly property bool evolutionShown: evolutionChart.SwipeView.isCurrentItem

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
        // A fitted parameter across a scan's datasets (edi ADR-0017 §19); a scan project's only.
        IconTabButton {
            objectName: "mainArea.analysis.tab.evolution"
            text: qsTr("Evolution")
            enabled: page.project !== null && page.project.scan
        }
    ]
    mainItems: [
        PatternChart {
            id: chartView
            experiment: page.experiment
            shown: page.current && SwipeView.isCurrentItem
        },
        EvolutionChart {
            id: evolutionChart
            project: page.project
            shown: page.current && SwipeView.isCurrentItem
        }
    ]
    extrasEnabled: analysis !== null
    textEnabled: analysis !== null
    basicItem: Component {
        EaComponents.SideBarColumn {
            // The fitted inputs are not edited while a fit runs.
            ParametersGroup {
                project: page.project
                enabled: !(page.project && page.project.fit.running)
            }
            FittingGroup {}
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
    textItem: Component {
        TextTab {
            source: page.analysis ? page.analysis.text : null
        }
    }
    // The same selector as the Experiment page's, over the one current experiment the project holds, so
    // choosing here or there is one choice (edi ADR-0017 §7).
    blockSelectorShown: true
    blockSelectorRightInset: evolutionShown ? evolutionChart.toolbarRightInset : chartView.toolbarRightInset
    blocks: evolutionShown ? (evolution ? evolution.parameters : null) : project ? project.experiments : null
    blocksTextRole: "label"
    blockKind: evolutionShown ? "parameter" : "experiment"
    blockOutcomeRole: evolutionShown ? "" : "fitOutcome"
    blockCurrentOutcome: experiment && !evolutionShown ? experiment.fitOutcome : ""
    blockOneColour: project !== null && project.scan
    blockIndex: evolutionShown ? (evolution ? evolution.currentParameter : -1) : project ? project.currentExperimentIndex : -1
    onBlockActivated: index => {
        if (page.evolutionShown)
            page.evolution.currentParameter = index;
        else
            page.project.currentExperimentIndex = index;
    }
    Connections {
        target: AppState
        function onEvolutionRequested() {
            page.showMainTab(1);
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
