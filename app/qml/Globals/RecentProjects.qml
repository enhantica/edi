// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton
import QtQuick
import QtCore

import EasyApplication.Gui.Globals as EaGlobals

import edi.app

QtObject {
    id: recent

    readonly property ListModel rows: ListModel {}
    property Settings settings: Settings {
        id: recentSettings
        location: EaGlobals.Vars.settingsFile
        category: "Edi.RecentProjects"
        property string paths: "[]"
        onPathsChanged: recent.refresh()
    }
    property Connections sessionConnection: Connections {
        target: Session
        function onProjectDirectoryUsed(path) {
            recent.remember(path);
        }
    }

    function paths(): list<string> {
        try {
            const saved = JSON.parse(recentSettings.paths);
            return Array.isArray(saved) ? saved.filter(path => typeof path === "string" && path.length > 0) : [];
        } catch (error) {
            return [];
        }
    }
    function refresh() {
        rows.clear();
        for (const path of paths())
            rows.append({
                "path": path,
                "available": Session.projectDirectoryExists(path)
            });
    }
    function remember(path: string) {
        if (!path)
            return;
        const saved = paths().filter(item => item !== path);
        saved.unshift(path);
        recentSettings.paths = JSON.stringify(saved);
        refresh();
    }
    function forget(index: int) {
        const saved = paths();
        if (index < 0 || index >= saved.length)
            return;
        saved.splice(index, 1);
        recentSettings.paths = JSON.stringify(saved);
        refresh();
    }
    Component.onCompleted: {
        if (Session.project && !Session.needsSaveAs)
            remember(Session.projectLocation);
        else
            refresh();
    }
}
