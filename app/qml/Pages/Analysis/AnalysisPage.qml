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

    readonly property AnalysisViewModel analysis: project ? project.analysis : null

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
    readonly property ExperimentViewModel experiment: project ? project.currentExperiment : null
    readonly property ProjectViewModel project: Session.project

    blockCurrentOutcome: experiment ? experiment.fitOutcome : ""
    blockCurrentTemplate: project !== null && project.scan && project.currentExperimentIndex === project.templateIndex
    blockIndex: project ? project.currentExperimentIndex : -1
    blockKind: "experiment"
    blockOneColour: project !== null && project.scan
    blockOutcomeRole: "fitOutcome"
    blockSelectorRightInset: chartView.toolbarRightInset
    // The same selector as the Experiment page's, over the one current experiment the project holds, so
    // choosing here or there is one choice (edi ADR-0017 §7).
    blockSelectorShown: true
    blockTemplateRole: project !== null && project.scan ? "isTemplate" : ""
    blocks: project ? project.experiments : null
    blocksTextRole: "label"
    continueText: qsTr("Continue")
    defaultInfo: project ? "" : qsTr("No analysis done")
    extrasEnabled: analysis !== null
    pageName: "analysis"
    textEnabled: analysis !== null

    basicItem: Component {
        EaComponents.SideBarColumn {
            id: analysisSidebar

            // The fitted inputs are not edited while a fit runs.
            ParametersGroup {
                availableHeight: analysisSidebar.height - fitting.height
                enabled: !(page.project && page.project.fit.running)
                project: page.project
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
                    contents: page.contents
                    shownTier: "Extras"
                }
            }
        }
    }
    mainItems: [
        ProjectPatternChart {
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
    mainTabs: [
        IconTabButton {
            objectName: "mainArea.analysis.tab.fitting"
            // The view's name, text only (edi ADR-0017 §2).
            text: qsTr("Pattern")
        },
        // A fitted parameter across a scan's datasets (edi ADR-0017 §19); a scan project's only.
        IconTabButton {
            enabled: page.project !== null && page.project.scan
            objectName: "mainArea.analysis.tab.evolution"
            text: qsTr("Evolution")
        }
    ]
    textItem: Component {
        TextTab {
            source: page.analysis ? page.analysis.text : null
        }
    }

    onBlockActivated: index => page.project.currentExperimentIndex = index
    onContinueClicked: AppState.open(AppState.Page.Report)

    Connections {
        function onEvolutionRequested() {
            page.showMainTab(1);
        }

        target: AppState
    }
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
