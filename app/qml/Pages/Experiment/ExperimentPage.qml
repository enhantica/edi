// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Components as EaComponents

import edi.app

// The Experiment page (easydiffractionbeta Pages/Experiment): the chart's place in the main area; the
// Experiments list and the current experiment's `.edi` categories in the sidebar, their content
// following the experiment's type (packet §2b (iii), §15.5, §15.6); its `.edi` in Text.
WorkflowPage {
    id: page

    readonly property ProjectViewModel project: Session.project
    readonly property ExperimentViewModel experiment: project ? project.currentExperiment : null

    // Each category's content, by `.edi` category id.
    readonly property var contents: ({
            "data": rangeContent,
            "data_range": rangeContent,
            "instrument": instrumentContent,
            "peak": peakContent,
            "background": backgroundContent,
            "linked_structure": linkedStructureContent,
            "excluded_region": excludedRegionsContent,
            "absorption": absorptionContent,
            "preferred_orientation": preferredOrientationContent,
            "scattering_source": scatteringSourceContent,
            "refln": reflectionsContent
        })
    // Extras shows the same categories, and the Extras part of those that have one.
    readonly property var extrasContents: Object.assign({}, contents, {
        "peak": peakExtrasContent
    })

    pageName: "experiment"
    defaultInfo: experiment ? "" : qsTr("No experiments defined")
    mainTabs: [
        IconTabButton {
            objectName: "mainArea.experiment.tab.chart"
            // The experiment's icon in its colour, and its name; the word alone with no experiment (edi
            // ADR-0017 §2).
            fontIcon: page.experiment ? "microscope" : ""
            iconColor: AppColors.experiment(page.project ? page.project.currentExperimentIndex : -1)
            text: page.experiment ? page.experiment.name : qsTr("Experiment")
        }
    ]
    mainItems: [
        PatternChart {
            experiment: page.experiment
            shown: page.current && SwipeView.isCurrentItem
        }
    ]
    extrasEnabled: experiment !== null
    textEnabled: experiment !== null
    basicItem: Component {
        EaComponents.SideBarColumn {
            ExperimentsGroup {
                project: page.project
            }
            Repeater {
                model: page.experiment ? page.experiment.categories : null
                delegate: CategoryGroup {
                    shownTier: "Basic"
                    contents: page.contents
                }
            }
        }
    }
    extrasItem: Component {
        EaComponents.SideBarColumn {
            Repeater {
                model: page.experiment ? page.experiment.categories : null
                delegate: CategoryGroup {
                    shownTier: "Extras"
                    contents: page.extrasContents
                }
            }
        }
    }
    textItem: Component {
        TextTab {
            source: page.experiment ? page.experiment.text : null
        }
    }
    // One block selector in the main view's tab bar (edi ADR-0017 §7).
    blockSelectorShown: true
    blocks: project ? project.experiments : null
    blocksTextRole: "name"
    blockKind: "experiment"
    blockIndex: project ? project.currentExperimentIndex : -1
    onBlockActivated: index => page.project.currentExperimentIndex = index
    continueText: qsTr("Continue")
    onContinueClicked: AppState.open(AppState.Page.Analysis)

    Component {
        id: rangeContent
        MeasuredRangeGroup {
            experiment: page.experiment
        }
    }
    Component {
        id: instrumentContent
        InstrumentGroup {
            experiment: page.experiment
        }
    }
    Component {
        id: peakContent
        PeakGroup {
            experiment: page.experiment
        }
    }
    Component {
        id: reflectionsContent
        ReflectionsGroup {
            experiment: page.experiment
        }
    }
    Component {
        id: peakExtrasContent
        PeakExtrasGroup {
            experiment: page.experiment
        }
    }
    Component {
        id: backgroundContent
        BackgroundGroup {
            experiment: page.experiment
        }
    }
    Component {
        id: linkedStructureContent
        LinkedStructureGroup {
            experiment: page.experiment
            project: page.project
        }
    }
    Component {
        id: excludedRegionsContent
        ExcludedRegionsGroup {
            experiment: page.experiment
        }
    }
    Component {
        id: absorptionContent
        AbsorptionGroup {
            experiment: page.experiment
        }
    }
    Component {
        id: preferredOrientationContent
        PreferredOrientationGroup {
            experiment: page.experiment
        }
    }
    Component {
        id: scatteringSourceContent
        ScatteringSourceGroup {
            experiment: page.experiment
        }
    }
}
