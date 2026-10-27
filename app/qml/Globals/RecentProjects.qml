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
    function webRows(): list<var> {
        const kept = [];
        const saved = [];
        const places = WebStorage.places;
        for (let row = 0; row < places.count; ++row) {
            const key = places.key(row), name = places.name(row), inBrowser = places.kind(row) === "browser";
            if (places.recovery(row))
                kept.push({
                    "path": "kept:" + key,
                    "label": qsTr("Continue where you left off: %1").arg(name),
                    "inBrowser": false,
                    "available": true
                });
            if (places.saved(row))
                saved.push({
                    "path": "place:" + key,
                    "label": inBrowser ? qsTr("%1 · in this browser").arg(name) : qsTr("%1 · on this computer").arg(name),
                    "inBrowser": inBrowser,
                    "available": true
                });
        }
        return kept.concat(saved);
    }
    // A web row's place and whether it is the unsaved state kept for it.
    function webKey(path: string): string {
        return path.substring(path.indexOf(":") + 1);
    }
    function open(path: string) {
        if (WebFiles.available)
            Session.openStoredProject(webKey(path), path.startsWith("kept:"));
        else
            Session.openProject(Session.projectDirectoryUrl(path));
    }

    function paths(): list<string> {
        return recentSettings.recent.filter(path => path.length > 0);
    }
    // Rows are updated in place, so a project that goes missing or comes back changes the cell already shown.
    function refresh() {
        const saved = WebFiles.available ? webRows() : paths().map(path => ({
                    "path": path,
                    "label": path,
                    "inBrowser": false,
                    "available": Session.projectDirectoryExists(path)
                }));
        for (let index = 0; index < saved.length; ++index) {
            const row = saved[index];
            if (index < rows.count)
                rows.set(index, row);
            else
                rows.append(row);
        }
        if (rows.count > saved.length)
            rows.remove(saved.length, rows.count - saved.length);
    }
    function remember(path: string) {
        if (!path || WebFiles.available)
            return;
        const saved = paths().filter(item => item !== path);
        saved.unshift(path);
        recentSettings.recent = saved;
        recentSettings.last = path;
        refresh();
    }
    function forget(index: int) {
        if (WebFiles.available) {
            // A kept project is deleted from the browser with its row; unsaved changes kept for one are dropped.
            const path = index >= 0 && index < rows.count ? rows.get(index).path : "";
            if (path.startsWith("kept:"))
                WebStorage.dropRecovery(webKey(path));
            else if (path.startsWith("place:"))
                WebStorage.forget(webKey(path));
            return;
        }
        const saved = paths();
        if (index < 0 || index >= saved.length)
            return;
        saved.splice(index, 1);
        recentSettings.recent = saved;
        refresh();
    }
    Component.onCompleted: {
        if (Session.project && !Session.needsSaveAs && !WebFiles.available)
            remember(Session.projectLocation);
        else
            refresh();
    }
}
