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
        // The project directories, most recent first.
        property list<string> projectPaths: []
        onProjectPathsChanged: recent.refresh()
    }
    property Connections sessionConnection: Connections {
        target: Session
        function onProjectDirectoryUsed(path) {
            recent.remember(path);
        }
    }

    function paths(): list<string> {
        return recentSettings.projectPaths.filter(path => path.length > 0);
    }
    // Rows are updated in place, so a project that goes missing or comes back changes the cell already shown.
    function refresh() {
        const saved = paths();
        for (let index = 0; index < saved.length; ++index) {
            const row = {
                "path": saved[index],
                "available": Session.projectDirectoryExists(saved[index])
            };
            if (index < rows.count)
                rows.set(index, row);
            else
                rows.append(row);
        }
        if (rows.count > saved.length)
            rows.remove(saved.length, rows.count - saved.length);
    }
    function remember(path: string) {
        if (!path)
            return;
        const saved = paths().filter(item => item !== path);
        saved.unshift(path);
        recentSettings.projectPaths = saved;
        refresh();
    }
    function forget(index: int) {
        const saved = paths();
        if (index < 0 || index >= saved.length)
            return;
        saved.splice(index, 1);
        recentSettings.projectPaths = saved;
        refresh();
    }
    Component.onCompleted: {
        if (Session.project && !Session.needsSaveAs)
            remember(Session.projectLocation);
        else
            refresh();
    }
}
