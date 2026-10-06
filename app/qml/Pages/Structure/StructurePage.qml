// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Components as EaComponents

import edi.app

// The Structure page (easydiffractionbeta Pages/Model): the structure view in the main area; the Structures
// list and the current structure's `.edi` categories in the sidebar (packet §2b (ii), §15.6), with the
// view's Appearance group on Extras; the structure block's `.edi` in Text.
WorkflowPage {
    id: page

    readonly property ProjectViewModel project: Session.project
    readonly property StructureViewModel structure: project ? project.currentStructure : null

    // Each category's content, by `.edi` category id.
    readonly property var contents: ({
            "space_group": spaceGroupContent,
            "cell": cellContent,
            "atom_site": atomSitesContent,
            "atom_site_aniso": atomSiteAdpContent,
            "scattering_length": scatteringLengthsContent
        })

    pageName: "structure"
    defaultInfo: structure ? "" : qsTr("No structures defined")
    mainTabs: [
        IconTabButton {
            objectName: "mainArea.structure.tab.view"
            // The view's name, text only (edi ADR-0017 §2).
            text: qsTr("Structure")
        }
    ]
    mainItems: [
        StructureView {
            id: structureView

            structure: page.structure
            options: page.project ? page.project.structureViewOptions : null
            shown: page.current && SwipeView.isCurrentItem
        }
    ]
    extrasEnabled: structure !== null
    textEnabled: structure !== null
    basicItem: Component {
        EaComponents.SideBarColumn {
            StructuresGroup {
                project: page.project
            }
            Repeater {
                model: page.structure ? page.structure.categories : null
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
                model: page.structure ? page.structure.categories : null
                delegate: CategoryGroup {
                    shownTier: "Extras"
                    contents: page.contents
                }
            }
            AppearanceGroup {
                options: page.project ? page.project.structureViewOptions : null
                controller: structureView.controller
            }
        }
    }
    textItem: Component {
        TextTab {
            source: page.structure ? page.structure.text : null
        }
    }
    // One block selector for Basic, Extras and Text (edi ADR-0017 §7).
    blockSelectorShown: true
    blockSelectorRightInset: structureView.toolbarRightInset
    blocks: project ? project.structures : null
    blocksTextRole: "label"
    blockKind: "structure"
    blockIndex: project ? project.currentStructureIndex : -1
    onBlockActivated: index => page.project.currentStructureIndex = index
    continueText: qsTr("Continue")
    onContinueClicked: AppState.open(AppState.Page.Experiment)

    Component {
        id: spaceGroupContent
        SpaceGroupGroup {
            structure: page.structure
        }
    }
    Component {
        id: cellContent
        CellGroup {
            structure: page.structure
        }
    }
    Component {
        id: atomSitesContent
        AtomSitesGroup {
            structure: page.structure
        }
    }
    Component {
        id: atomSiteAdpContent
        AtomSiteAdpGroup {
            structure: page.structure
        }
    }
    Component {
        id: scatteringLengthsContent
        ScatteringLengthsGroup {
            structure: page.structure
        }
    }
}
