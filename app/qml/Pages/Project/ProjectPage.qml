// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Components as EaComponents

import edi.app

// The Project page (easydiffractionbeta Pages/Project): the project's description in the main area;
// Get started, Examples and Recent projects on the sidebar's Tools tab; how standard uncertainties are written in
// Extra; the project block's `.edi` in Text.
WorkflowPage {
    id: page

    // The page stays when another project replaces the open one (edi ADR-0052): it lets go of a project before that one
    // is retired, and shows the next as a page made for it would.
    property bool letGo: false
    readonly property ProjectViewModel project: letGo ? null : Session.project
    // Untitled work is not a project yet: the page looks as it does with none until it is created (edi ADR-0017 §13).
    readonly property bool created: project !== null && !Session.untitled

    Connections {
        target: Session
        function onProjectAboutToChange() {
            page.letGo = true;
        }
        function onProjectChanged() {
            page.letGo = false;
            page.textDirty = false;
            page.showStartTab();
            page.startedOver();
        }
    }
    // Another project is shown: what a page made for it would start with.
    signal startedOver
    // With no project the page opens on Tools, where a project is started or opened; once one exists, on Main.
    function showStartTab() {
        selectSidebarTab(created ? "basic" : "tools");
    }
    onCreatedChanged: showStartTab()
    Component.onCompleted: showStartTab()

    pageName: "project"
    defaultInfo: created ? "" : qsTr("No project yet")
    mainTabs: [
        IconTabButton {
            objectName: "mainArea.project.tab.description"
            // The view's name, text only (edi ADR-0017 §2).
            text: qsTr("Project")
        }
    ]
    mainItems: [
        DescriptionTab {
            project: page.created ? page.project : null
        }
    ]
    textEnabled: created
    extrasEnabled: created
    // Get started, Examples and Recent projects open or create a project and edit no `.edi` category: tools (owner,
    // 2026-11-28, sidebar tabs by role; edi ADR-0017 §2). The page shows them while no project exists.
    toolsItem: Component {
        EaComponents.SideBarColumn {
            id: basicColumn

            GetStartedGroup {
                id: getStarted
            }
            ExamplesGroup {
                id: examples
            }
            RecentProjectsGroup {
                id: recentProjects
            }
            Connections {
                target: page
                function onStartedOver() {
                    getStarted.rest(false);
                    examples.rest(true);
                    recentProjects.rest(true);
                    basicColumn.contentY = 0;
                }
            }
        }
    }
    // Main: the project's common categories, as Extra holds its rare ones (owner, 2026-11-28).
    basicItem: Component {
        EaComponents.SideBarColumn {
            Repeater {
                model: page.project ? page.project.categories : null
                delegate: CategoryGroup {
                    shownTier: "Basic"
                    textSource: page.project ? page.project.metadataText : null
                    admitted: categoryId !== "su_format" && categoryId !== "report"
                }
            }
        }
    }
    extrasItem: Component {
        EaComponents.SideBarColumn {
            StandardUncertaintiesGroup {
                project: page.project
            }
            SaveDataGroup {
                project: page.project
            }
            // The rest of `project.edi`, each category in a group made from the dictionary; the standard
            // uncertainties have theirs above, the report's settings theirs on the Report page.
            Repeater {
                model: page.project ? page.project.categories : null
                delegate: CategoryGroup {
                    shownTier: "Extras"
                    textSource: page.project ? page.project.metadataText : null
                    admitted: categoryId !== "su_format" && categoryId !== "report"
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
