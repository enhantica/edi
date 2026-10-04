// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Components as EaComponents

import edi.app

// The Project page (easydiffractionbeta Pages/Project): the project's description in the main area;
// Get started, Examples and Recent projects in the sidebar; the project block's `.edi` in Text.
WorkflowPage {
    id: page

    readonly property ProjectViewModel project: Session.project

    pageName: "project"
    defaultInfo: project ? "" : qsTr("No project defined")
    mainTabs: [
        IconTabButton {
            objectName: "mainArea.project.tab.description"
            // The project's icon, in the tab's own colour, and name; the word alone with no project (edi
            // ADR-0017 §2).
            fontIcon: page.project ? "archive" : ""
            text: page.project ? page.project.name : qsTr("Project")
        }
    ]
    mainItems: [
        DescriptionTab {
            project: page.project
        }
    ]
    textEnabled: project !== null
    basicItem: Component {
        EaComponents.SideBarColumn {
            GetStartedGroup {}
            ExamplesGroup {}
            RecentProjectsGroup {}
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
