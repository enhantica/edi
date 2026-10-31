// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Components as EaComponents

import edi.app

// The Project page (easydiffractionbeta Pages/Project): the project's description in the main area;
// Get started, Examples and Recent projects in the sidebar; how standard uncertainties are written in Extra;
// the project block's `.edi` in Text.
WorkflowPage {
    id: page

    readonly property ProjectViewModel project: Session.project

    pageName: "project"
    defaultInfo: project ? "" : qsTr("No project defined")
    mainTabs: [
        IconTabButton {
            objectName: "mainArea.project.tab.description"
            // The view's name, text only (edi ADR-0017 §2).
            text: qsTr("Project")
        }
    ]
    mainItems: [
        DescriptionTab {
            project: page.project
        }
    ]
    textEnabled: project !== null
    extrasEnabled: project !== null
    basicItem: Component {
        EaComponents.SideBarColumn {
            GetStartedGroup {}
            ExamplesGroup {}
            RecentProjectsGroup {}
        }
    }
    extrasItem: Component {
        EaComponents.SideBarColumn {
            StandardUncertaintiesGroup {
                project: page.project
            }
            // The rest of `project.edi`, each category in a group made from the dictionary; the standard
            // uncertainties have theirs above, the report's settings theirs on the Report page.
            Repeater {
                model: page.project ? page.project.categories : null
                delegate: CategoryGroup {
                    shownTier: "Extras"
                    textSource: page.project ? page.project.metadataText : null
                    visible: shown && categoryId !== "su_format" && categoryId !== "report"
                }
            }
        }
    }
    textItem: Component {
        TextTab {
            source: page.project ? page.project.metadataText : null
        }
    }
    continueText: project ? qsTr("Continue") : qsTr("Continue without project")
    onContinueClicked: AppState.open(AppState.Page.Structure)
}
