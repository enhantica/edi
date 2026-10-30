// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton
import QtQuick
import QtCore

import EasyApplication.Gui.Globals as EaGlobals

import edi.app

QtObject {
    id: recentProjects

    readonly property ListModel rows: ListModel {}
    property Settings settings: Settings {
        id: recentSettings
        location: EaGlobals.Vars.settingsFile
        category: "Projects"
        // The project directories, most recent first, and the last one open (ADR-0031: the store's Projects group).
        property list<string> recent: []
        property string last: ""
        onRecentChanged: recentProjects.refresh()
    }
    property Connections sessionConnection: Connections {
        target: Session
        function onProjectDirectoryUsed(path) {
            recentProjects.remember(path);
        }
    }
    // The web app lists the places the browser keeps (edi ADR-0052 §9): first the unsaved changes kept for a project,
    // to continue where they were left off, then the projects, each in the browser or on the disk.
    property Connections storageConnection: Connections {
        target: WebStorage
        function onPlacesChanged() {
            recentProjects.refresh();
        }
    }
    function webRows(): list<var> { return ApplicationInfo.recentWebRows(); }
    // A web row's place and whether it is the unsaved state kept for it.
    function webKey(path: string): string { return ApplicationInfo.recentWebKey(path); }
    function open(path: string) { ApplicationInfo.recentOpen(path); }

    function paths(): list<string> { return ApplicationInfo.recentPaths(); }
    // Rows are updated in place, so a project that goes missing or comes back changes the cell already shown.
    function refresh() { ApplicationInfo.recentRefresh(); }
    function remember(path: string) { ApplicationInfo.recentRemember(path); }
    function forget(index: int) { ApplicationInfo.recentForget(index); }
    Component.onCompleted: ApplicationInfo.recentCompleted()
}
