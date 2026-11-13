// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Components as EaComponents

import edi.app

// The Structure page (easydiffractionbeta Pages/Model): the Structures list and the current structure's `.edi`
// categories in the sidebar (packet §2b (ii), §15.6), with the structure view's Appearance group on Extras; the
// structure block's `.edi` in Text. The views are the window's one main view beside it (MainView).
WorkflowPage {
    id: page

    readonly property ProjectViewModel project: Session.project
    property StructureViewModel structure: null
    Binding {
        target: page
        property: "structure"
        value: page.project ? page.project.currentStructure : null
        when: page.current
        restoreMode: Binding.RestoreNone
    }

    // Each category's content, by `.edi` category id.
    readonly property var contents: ({
            "space_group": spaceGroupContent,
            "cell": cellContent,
            "atom_site": atomSitesContent,
            "atom_site_aniso": atomSiteAdpContent,
            "atom_site_moment": atomSiteMomentContent,
            "magnetic_form_factor": magneticFormFactorsContent,
            "space_group_magn": magneticSpaceGroupContent,
            "parent_propagation_vector": propagationVectorsContent,
            "scattering_length": scatteringLengthsContent
        })

    pageName: "structure"
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
                    textSource: page.structure ? page.structure.text : null
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
                    textSource: page.structure ? page.structure.text : null
                    shownTier: "Extras"
                    contents: page.contents
                }
            }
            AppearanceGroup {
                options: page.project ? page.project.structureViewOptions : null
                controller: AppState.mainView ? AppState.mainView.structureController : null
                structure: page.structure
            }
        }
    }
    textItem: Component {
        TextTab {
            source: page.structure ? page.structure.text : null
        }
    }
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
        id: magneticSpaceGroupContent
        MagneticSpaceGroupGroup {
            structure: page.structure
        }
    }
    Component {
        id: propagationVectorsContent
        PropagationVectorsGroup {
            structure: page.structure
        }
    }
    Component {
        id: atomSiteMomentContent
        AtomSiteMomentGroup {
            structure: page.structure
            options: page.project ? page.project.structureViewOptions : null
        }
    }
    Component {
        id: magneticFormFactorsContent
        MagneticFormFactorsGroup {
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
