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
    readonly property ExperimentViewModel experiment: project ? project.currentExperiment : null
    // Extras shows the same categories, and the Extras part of those that have one.
    readonly property var extrasContents: Object.assign({}, contents, {
        "peak": peakExtrasContent
    })
    readonly property ProjectViewModel project: Session.project

    blockCurrentOutcome: experiment ? experiment.fitOutcome : ""
    blockCurrentTemplate: project !== null && project.scan && project.currentExperimentIndex === project.templateIndex
    blockIndex: project ? project.currentExperimentIndex : -1
    blockKind: "experiment"
    blockOneColour: project !== null && project.scan
    blockOutcomeRole: "fitOutcome"
    blockSelectorRightInset: chartView.toolbarRightInset
    // One block selector in the main view's tab bar (edi ADR-0017 §7).
    blockSelectorShown: true
    blockTemplateRole: project !== null && project.scan ? "isTemplate" : ""
    blocks: project ? project.experiments : null
    blocksTextRole: "label"
    continueText: qsTr("Continue")
    defaultInfo: experiment ? "" : qsTr("No experiments defined")
    extrasEnabled: experiment !== null
    pageName: "experiment"
    textEnabled: experiment !== null

    basicItem: Component {
        EaComponents.SideBarColumn {
            ExperimentsGroup {
                project: page.project
            }
            Repeater {
                model: page.experiment ? page.experiment.categories : null

                delegate: CategoryGroup {
                    contents: page.contents
                    shownTier: "Basic"
                }
            }
        }
    }
    extrasItem: Component {
        EaComponents.SideBarColumn {
            Repeater {
                model: page.experiment ? page.experiment.categories : null

                delegate: CategoryGroup {
                    contents: page.extrasContents
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
        }
    ]
    mainTabs: [
        IconTabButton {
            objectName: "mainArea.experiment.tab.chart"
            // The view's name, text only (edi ADR-0017 §2).
            text: qsTr("Pattern")
        }
    ]
    textItem: Component {
        TextTab {
            source: page.experiment ? page.experiment.text : null
        }
    }

    onBlockActivated: index => page.project.currentExperimentIndex = index
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
