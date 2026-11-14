// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Components as EaComponents

import edi.app

// The Analysis page (easydiffractionbeta Pages/Analysis): the parameter table and Fitting in Main; the analysis block's
// `.edi` categories in Extra (packet §2b (iv), §15.6); analysis.edi in Text. The views are the window's one main view
// beside it (MainView).
WorkflowPage {
    id: page

    readonly property ProjectViewModel project: Session.project
    readonly property AnalysisViewModel analysis: project ? project.analysis : null
    readonly property ExperimentViewModel experiment: project ? project.currentExperiment : null
    readonly property bool scanMode: project !== null && project.fit.scanMode
    // Some experiment holds measured data: without any there is nothing to fit, and what only a fit uses is hidden.
    readonly property bool measured: project !== null && project.fit.measured

    // Each category's content, by `.edi` category id.
    readonly property var contents: ({
            "minimizer": minimizerContent,
            "refine_ls": refinementContent,
            "fitting_mode": fittingModeContent,
            "alias": aliasesContent,
            "constraint": constraintsContent,
            "joint_fit": jointFitContent,
            "sequential_fit": sequentialFitContent,
            "sequential_fit_extract": sequentialExtractContent,
            "fit_parameter": fitStartContent
        })

    pageName: "analysis"
    extrasEnabled: analysis !== null
    textEnabled: analysis !== null
    basicItem: Component {
        EaComponents.SideBarColumn {
            id: analysisSidebar
            // The table fills the sidebar down to its value slider: fitting is run from the status bar (the owner,
            // 2026-10-26). The fitted inputs are not edited while a fit runs.
            ParametersGroup {
                tableViewportHeight: analysisSidebar.height
                project: page.project
                enabled: !(page.project && page.project.fit.running)
            }
        }
    }
    extrasItem: Component {
        EaComponents.SideBarColumn {
            Repeater {
                model: page.analysis ? page.analysis.categories : null
                delegate: CategoryGroup {
                    textSource: page.analysis ? page.analysis.text : null
                    shownTier: "Extras"
                    contents: page.contents
                    measured: page.measured
                }
            }
        }
    }
    // The page's view options (edi ADR-0031 §2): which rows the parameter table shows, how a followed scan redraws,
    // and, for a scan, how many of its files are fitted at once (read-only, a Preferences setting).
    // The chart's own choices are on the chart. Both are about fitting, so both are hidden while no experiment has
    // measured data (edi ADR-0046), as the table's free column is.
    settingsItem: Component {
        EaComponents.SideBarColumn {
            ShownParametersGroup {
                visible: page.measured
                project: page.project
            }
            PatternUpdatesGroup {
                visible: page.measured
            }
            PerformanceGroup {
                visible: page.measured && page.scanMode
                shows: "parallelFits"
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
    continueText: qsTr("Continue")
    onContinueClicked: AppState.open(AppState.Page.Report)

    Component {
        id: refinementContent
        RefinementGroup {
            analysis: page.analysis
        }
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
