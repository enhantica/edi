// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The Experiment page (easydiffractionbeta Pages/Experiment): the chart's place in the main area; the
// Experiments list and the current experiment's `.edi` categories in the sidebar, their content
// following the experiment's type (packet §2b (iii), §15.5, §15.6); its `.edi` in Text.
WorkflowPage {
    id: page

    readonly property ProjectViewModel project: Session.project
    readonly property ExperimentViewModel experiment: project ? project.currentExperiment : null
    // The Stacked and Map tabs: a scan, or a joint fit of several experiments.
    readonly property bool patternViews: project !== null && (project.scan || project.scanViews.joint)
    // A project of several single crystals: the Stacked tab draws all of them on one F²calc-against-F²meas chart, and
    // there is no Map.
    readonly property bool singleCrystals: project !== null && project.singleCrystalExperiments.length > 1
    // Whether the shown experiment holds measured data: what only works on it is hidden or disabled without.
    readonly property bool measured: experiment !== null && !experiment.calculationOnly

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
            "refln": page.experiment && page.experiment.sampleForm === ExperimentViewModel.SingleCrystal ? singleCrystalReflectionsContent : reflectionsContent
        })
    // The Extras column, so a single crystal's reflection table can take the room left under the groups above it.
    property Flickable extrasColumn: null
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
        },
        // A scan's or a joint fit's patterns, stacked and as a map, as on the Analysis page and with its settings, so
        // the data can be looked at before any fit (edi ADR-0041; the owner, 2026-10-22).
        IconTabButton {
            objectName: "mainArea.experiment.tab.stacked"
            text: qsTr("Stacked")
            enabled: page.patternViews || page.singleCrystals
        },
        IconTabButton {
            objectName: "mainArea.experiment.tab.map"
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
        Item {
            id: stackedTab

            readonly property bool shown: page.current && SwipeView.isCurrentItem

            ScanViewChart {
                id: stackedChart
                anchors.fill: parent
                visible: !page.singleCrystals
                project: page.project
                mode: "stacked"
                shown: stackedTab.shown && !page.singleCrystals
            }
            SingleCrystalChart {
                id: stackedCrystals
                objectName: "singleCrystal.stacked"
                anchors.fill: parent
                visible: page.singleCrystals
                stackedExperiments: page.singleCrystals ? page.project.singleCrystalExperiments : []
                project: page.project
                shown: stackedTab.shown && page.singleCrystals
            }
        },
        ScanViewChart {
            id: mapChart
            project: page.project
            mode: "map"
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
                    measured: page.measured
                }
            }
        }
    }
    extrasItem: Component {
        EaComponents.SideBarColumn {
            id: extrasColumn
            Binding {
                target: page
                property: "extrasColumn"
                value: extrasColumn
            }
            Repeater {
                model: page.experiment ? page.experiment.categories : null
                delegate: CategoryGroup {
                    shownTier: "Extras"
                    contents: page.extrasContents
                    measured: page.measured
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
    // The row ends where the shown chart's toolbar does, so the two share one centre.
    blockSelectorRightInset: stackedTab.SwipeView.isCurrentItem ? (page.singleCrystals ? stackedCrystals.toolbarRightInset : stackedChart.toolbarRightInset) : mapChart.SwipeView.isCurrentItem ? mapChart.toolbarRightInset : chartView.toolbarRightInset
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
        // The observed threshold above the reflection table (edi ADR-0050).
        Column {
            spacing: AppSizes.groupContentSpacing
            ObservedThresholdRow {
                experiment: page.experiment
            }
            SingleCrystalTable {
                id: reflectionTable

                // From the column's height and where the table starts in it, never from the table's own height, so a
                // new row count cannot move the room it was taken from (a half-pixel rounding made it flicker).
                // Set after the column has laid out: the table's place is read, not bound.
                function place() {
                    const column = page.extrasColumn;
                    if (!column || !column.contentItem)
                        return;
                    const top = mapToItem(column.contentItem, 0, 0).y;
                    spareHeight = Math.floor(column.height - top - EaStyle.Sizes.fontPixelSize);
                }

                experiment: page.experiment
                Component.onCompleted: Qt.callLater(place)
                Connections {
                    target: page.extrasColumn
                    function onHeightChanged() {
                        Qt.callLater(reflectionTable.place);
                    }
                    function onContentHeightChanged() {
                        Qt.callLater(reflectionTable.place);
                    }
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
