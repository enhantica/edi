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
            "space_group_magn_symbols": magneticSymbolsContent,
            "parent_space_group": parentSpaceGroupContent,
            "parent_propagation_vector": propagationVectorsContent,
            "scattering_length": scatteringLengthsContent,
            "geom": geomContent
        })

    pageName: "structure"
    // Its own main view: Structure, and Pattern disabled until there is one (the owner, 2026-11-14 item 5).
    pageView: Component {
        MainView {
            shown: page.current
            defaultKey: "structure"
            pageKey: "structure"
            tabKeys: ["structure", "pattern"]
        }
    }
    onCurrentChanged: if (current && pageViewItem)
        AppState.mainView = pageViewItem
    onPageViewItemChanged: if (current && pageViewItem)
        AppState.mainView = pageViewItem
    extrasEnabled: structure !== null
    textEnabled: structure !== null
    basicItem: Component {
        EaComponents.SideBarColumn {
            StructuresGroup {
                project: page.project
            }
            Repeater {
                // One list following the current structure's categories, so a next structure keeps the groups
                // (ADR-0102 rule 2).
                model: CategoryListMirror {
                    source: page.structure ? page.structure.categories : null
                }
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
                // One list following the current structure's categories, so a next structure keeps the groups
                // (ADR-0102 rule 2).
                model: CategoryListMirror {
                    source: page.structure ? page.structure.categories : null
                }
                delegate: CategoryGroup {
                    textSource: page.structure ? page.structure.text : null
                    shownTier: "Extras"
                    contents: page.contents
                }
            }
            AppearanceGroup {
                options: page.project ? page.project.structureViewOptions : null
                controller: page.pageViewItem ? page.pageViewItem.structureController : null
                structure: page.structure
            }
            PolyhedraGroup {
                options: page.project ? page.project.structureViewOptions : null
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
        id: magneticSymbolsContent
        MagneticSymbolsGroup {
            structure: page.structure
        }
    }
    Component {
        id: parentSpaceGroupContent
        ParentSpaceGroupGroup {
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
        id: geomContent
        GeomGroup {
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
