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

    function paths(): list<string> {
        return recentSettings.recent.filter(path => path.length > 0);
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
        recentSettings.recent = saved;
        recentSettings.last = path;
        refresh();
    }
    function forget(index: int) {
        const saved = paths();
        if (index < 0 || index >= saved.length)
            return;
        saved.splice(index, 1);
        recentSettings.recent = saved;
        refresh();
    }
    Component.onCompleted: {
        if (Session.project && !Session.needsSaveAs)
            remember(Session.projectLocation);
        else
            refresh();
    }
}
