// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Dialogs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// Get started (easydiffractionbeta Pages/Project/SideBarBasic/GetStarted.qml): create a new project
// or open an existing one — an edi project is a directory — and save the open one as (edi ADR-0017 §13).
EaElements.GroupBox {
    id: group
    objectName: "group.getStarted"
    title: qsTr("Get started")
    icon: "rocket"
    // The one group that starts open: the first thing a new user needs (the owner, 2026-09-29; edi ADR-0017 §3).
    collapsed: false

    Grid {
        columns: 2
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            objectName: "project.create"
            fontIcon: "plus-circle"
            text: qsTr("Create a new project")
            onClicked: EaGlobals.Vars.showProjectDescriptionDialog = true
        }

        EaElements.SideBarButton {
            objectName: "project.open"
            fontIcon: "upload"
            text: qsTr("Open an existing project")
            // In the browser the chosen folder is copied into the page's memory first (edi ADR-0023).
            onClicked: {
                if (WebFiles.available) {
                    group.webRequestProject = Session.project;
                    group.webRequest = WebFiles.openProject();
                } else {
                    openProjectDialog.open();
                }
            }
        }

        EaElements.SideBarButton {
            objectName: "project.saveAs"
            enabled: Session.project !== null
            fontIcon: "file-export"
            text: qsTr("Save project as…")
            onClicked: AppState.saveAsRequested()
        }

        // Opening a project from a URL is not implemented: shown, disabled (edi ADR-0017 §4).
        EaElements.SideBarButton {
            objectName: "project.openUrl"
            enabled: false
            fontIcon: "link"
            text: qsTr("Open project from URL…")
        }
    }

    EaComponents.ProjectDescriptionDialog {
        id: createDialog
        // The base's own dialog, placed on whole pixels as AppDialog is.
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        visible: EaGlobals.Vars.showProjectDescriptionDialog
        onClosed: EaGlobals.Vars.showProjectDescriptionDialog = false
        onAccepted: Session.createProject(createDialog.projectName, createDialog.projectDescription)
    }

    // The folder request and the project open when it was made: a folder that arrives after another project was
    // opened meanwhile is not opened over it.
    property int webRequest: 0
    property var webRequestProject: null
    Connections {
        target: WebFiles
        function onProjectOpened(request, directory) {
            if (request !== group.webRequest)
                return;
            group.webRequest = 0;
            if (Session.project === group.webRequestProject)
                Session.openProject(directory);
        }
        function onFailed(request) {
            if (request === group.webRequest)
                group.webRequest = 0;
        }
        function onCancelled(request) {
            if (request === group.webRequest)
                group.webRequest = 0;
        }
    }

    FolderDialog {
        id: openProjectDialog
        title: qsTr("Open an edi project directory")
        onAccepted: Session.openProject(selectedFolder)
    }
}
