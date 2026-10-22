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
            "extinction": extinctionContent,
            "preferred_orientation": preferredOrientationContent,
            "scattering_source": scatteringSourceContent,
            "refln": page.experiment && page.experiment.sampleForm === ExperimentViewModel.SingleCrystal
                     ? singleCrystalReflectionsContent : reflectionsContent
        })
    // The Extras column's height and the height of its content, so a single crystal's reflection table can take
    // the room left under the groups above it.
    property real extrasViewportHeight: 0
    property real extrasContentHeight: 0
    // Extras shows the same categories, and the Extras part of those that have one.
    readonly property var extrasContents: Object.assign({}, contents, {
        "peak": peakExtrasContent,
        "background": backgroundExtrasContent
    })

    pageName: "experiment"
    defaultInfo: experiment ? "" : qsTr("No experiments defined")
    mainTabs: [
        IconTabButton {
            objectName: "mainArea.experiment.tab.chart"
            // The view's name, text only (edi ADR-0017 §2).
            text: qsTr("Pattern")
        }
    ]
    mainItems: [
        ProjectPatternChart {
            id: chartView
            experiment: page.experiment
            settingsPage: "experiment"
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
            id: extrasColumn
            Binding {
                target: page
                property: "extrasViewportHeight"
                value: extrasColumn.height
            }
            Binding {
                target: page
                property: "extrasContentHeight"
                value: extrasColumn.contentHeight
            }
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
        id: singleCrystalReflectionsContent
        SingleCrystalTable {
            id: reflectionTable

            // Set after the column has laid out, not bound: the content's height follows the table's own.
            function place() {
                spareHeight = page.extrasViewportHeight - (page.extrasContentHeight - height);
            }

            experiment: page.experiment
            Component.onCompleted: Qt.callLater(place)
            Connections {
                target: page
                function onExtrasViewportHeightChanged() {
                    Qt.callLater(reflectionTable.place);
                }
                function onExtrasContentHeightChanged() {
                    Qt.callLater(reflectionTable.place);
                }
            }
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
        id: backgroundExtrasContent
        BackgroundExtrasGroup {
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
        id: extinctionContent
        ExtinctionGroup {
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
