// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The Experiment page (easydiffractionbeta Pages/Experiment): the Experiments list and the current experiment's `.edi`
// categories in the sidebar, their content following the experiment's type (packet §2b (iii), §15.5, §15.6); its
// `.edi` in Text. The views are the window's one main view beside it (MainView).
WorkflowPage {
    id: page

    readonly property ProjectViewModel project: Session.project
    readonly property ExperimentViewModel experiment: project ? project.currentExperiment : null
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
        "background_estimate": backgroundExtrasContent
    })

    pageName: "experiment"
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
                    textSource: page.experiment ? page.experiment.text : null
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
                    textSource: page.experiment ? page.experiment.text : null
                    shownTier: "Extras"
                    contents: page.extrasContents
                    measured: page.measured
                }
            }
        }
    }
    // How the page runs (edi ADR-0031 §2): the threads a calculation runs on, read-only, a Preferences setting.
    settingsItem: Component {
        EaComponents.SideBarColumn {
            PerformanceGroup {
                shows: "threads"
            }
        }
    }
    textItem: Component {
        TextTab {
            source: page.experiment ? page.experiment.text : null
        }
    }
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
                    ApplicationInfo.placeReflectionTable();
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
