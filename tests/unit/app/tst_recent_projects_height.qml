// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "RecentProjectsHeight"
    when: windowShown
    property var app
    property var savedPaths
    Component {
        id: application
        Main {}
    }
    function init() {
        savedPaths = RecentProjects.settings.recent.slice();
        RecentProjects.settings.recent = Array.from({
            length: 40
        }, (_, i) => "/missing/onboarding/project-" + i);
        app = application.createObject(null);
        verify(app !== null, "Recent projects acceptance opens the production window");
        AppState.open(AppState.Page.Project);
    }
    function cleanup() {
        if (app)
            app.destroy();
        app = null;
        RecentProjects.settings.recent = savedPaths;
        RecentProjects.refresh();
    }
    function test_status_header_is_empty() {
        Ui.expandGroup(test, Probe, app, "group.recentProjects");
        const table = Ui.control(Probe, app, "recentProjects.list");
        verify(table !== null && waitForPolish(table), "The real Recent projects table completes layout");
        const headers = Render.cells(table.headerItem);
        compare(headers.length, 4, "Recent projects retains its four table columns");
        compare(headers[2].text, "", "The status icon column has no header");
        const status = Ui.control(Probe, app, "recentProjects.status.0");
        const remove = Ui.control(Probe, app, "recentProjects.remove.0");
        verify(status !== null && remove !== null, "Recent projects retains status and remove controls");
        verify(status.mapToItem(table, 0, 0).x < remove.mapToItem(table, 0, 0).x, "The status icon precedes the remove control");
        verify(status.toolTip.length > 0, "The headerless status remains explained by its tooltip");
    }
    function test_recent_table_grows_when_sidebar_grows() {
        Ui.expandGroup(test, Probe, app, "group.recentProjects");
        const table = Ui.control(Probe, app, "recentProjects.list");
        verify(table !== null, "The resize check reaches the actual Recent projects table");
        const heights = [];
        for (const size of [
            {
                width: 1100,
                height: 760
            },
            {
                width: 1480,
                height: 1080
            }
        ]) {
            app.width = size.width;
            app.height = size.height;
            verify(waitForRendering(app.contentItem) && waitForPolish(table), "Recent projects is measured after each real window resize");
            heights.push(table.height);
            verify(table.height > table.tableRowHeight * 2, "The populated Recent projects table uses room for more than two rows");
            const bottom = table.mapToItem(app.contentItem, 0, table.height).y;
            verify(bottom <= app.contentItem.height, "Recent projects remains within the visible application after resizing");
        }
        verify(heights[1] > heights[0], "Recent projects unfolds into additional sidebar height when the window grows");
    }
}
