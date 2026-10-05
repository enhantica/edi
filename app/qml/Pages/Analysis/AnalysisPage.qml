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
            text: qsTr("Fitting")
        }
    ]
    mainItems: [
        PatternChart {
            experiment: page.experiment
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
    blocks: project ? project.experiments : null
    blocksTextRole: "label"
    blockKind: "experiment"
    blockIndex: project ? project.currentExperimentIndex : -1
    onBlockActivated: index => page.project.currentExperimentIndex = index
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
