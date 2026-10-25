// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ChartBackendAcceptance 1.0
import ReportAcceptance 1.0
import "../../unit/app/RenderedTable.js" as Render
import "../../unit/app/UiInteraction.js" as Ui

Item {
    Component { id: appFactory; Main { visible: true; width: 1280; height: 800 } }
    TestCase {
        id: test
        name: "SidebarDefaults"
        when: windowShown
        property var app: null
        property int sidebarTabCount: 0
        function initTestCase() { ChartBackendProof.useStore(); }
        function cleanup() {
            Session.closeProject();
            if (app) { app.close(); app.destroy(); }
            app = null;
        }
        function page(name) {
            Ui.click(test, Probe, app, "appBar.tab." + name);
            tryVerify(() => Math.abs(Ui.page(app).mapToItem(app.contentItem, 0, 0).x) < 1, 2000, "The selected page reaches the actual viewport before sidebar inventory");
        }
        function tab(name) {
            const button = Ui.control(Probe, app, name);
            verify(button !== null && button.enabled, "The sidebar inventory revisits an actual enabled tab");
            if (!button.checked) Ui.click(test, Probe, app, name);
            tryVerify(() => !Ui.moving(app.contentItem), 2000, "The selected sidebar tab settles before group observations");
            verify(waitForPolish(app), "The selected sidebar tab completes its actual group layout");
            tryVerify(() => Render.descendants(Ui.page(app)).filter(item => item.interactive === false && item.count === sidebarTabCount && item.currentItem).every(item => Math.abs(item.currentItem.mapToItem(item, 0, 0).x) < 0.1), 2000, "The selected sidebar pane reaches its viewport before first-group observations");
        }
        function firstGroup() {
            const groups = Render.descendants(Ui.page(app)).filter(item => typeof item.collapsed === "boolean" && item.titleArea && Ui.inPane(item.titleArea));
            groups.sort((a, b) => a.titleArea.mapToItem(app.contentItem, 0, 0).y - b.titleArea.mapToItem(app.contentItem, 0, 0).y);
            return groups.length > 0 ? groups[0] : null;
        }
        function clickHeader(group) {
            Ui.scrollIntoView(group.titleArea);
            const point = Ui.clickPoint(group.titleArea);
            verify(point !== null, "The real first group's title is exposed for a user fold");
            mouseClick(group.titleArea, point.x, point.y);
        }
        function test_every_tab_data() { return ["home", "project", "structure", "experiment", "analysis", "report"].map(name => ({tag: name, page: name})); }
        function test_every_tab(data) {
            Preferences.resetToDefaults();
            const location = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/scan_template/project"));
            verify(Session.openProject(location), "Fresh sidebar acceptance opens a private nonempty saved project");
            app = appFactory.createObject(null);
            verify(app !== null, "Sidebar defaults are observed in the actual application");
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "Real sidebar folding reaches the active application window");
            page(data.page);
            if (data.page !== "home")
                tryVerify(() => Render.descendants(Ui.page(app)).some(item => String(item.objectName).startsWith("sideBar.tab.")), 5000, "The selected workflow page loads its actual sidebar before inventory");
            const allTabs = Render.descendants(Ui.page(app)).filter(item => String(item.objectName).startsWith("sideBar.tab."));
            sidebarTabCount = allTabs.length;
            const tabs = allTabs.filter(item => Ui.rendered(item) && item.enabled);
            if (data.page === "home") {
                compare(tabs.length, 0, "Home has no sidebar tab or foldable first group to default");
                return;
            }
            verify(tabs.length > 0, "Every workflow page exposes its actual enabled sidebar tabs");
            const entries = [], errors = [];
            for (const button of tabs) {
                tab(button.objectName);
                const first = firstGroup();
                entries.push({tab: button.objectName, name: first ? first.objectName : "", title: first ? first.title : "", foldable: first ? first.collapsible : false});
                if (first && first.collapsible && first.collapsed)
                    errors.push(data.page + "/" + button.objectName + "/" + first.title);
            }
            for (const entry of entries) {
                if (!entry.foldable) continue;
                tab(entry.tab);
                let first = firstGroup();
                verify(first !== null && first.objectName === entry.name && first.title === entry.title, "The remembered-state witness targets the same actual first group");
                if (first.collapsed) {
                    clickHeader(first);
                    tryCompare(first, "collapsed", false, 1500, "An initially folded first group is opened before an explicit remembered user fold");
                }
                clickHeader(first);
                tryCompare(first, "collapsed", true, 1500, "Actual pointer input folds the first group and records the user's choice");
                page("home");
                page(data.page);
                tab(entry.tab);
                first = firstGroup();
                verify(first !== null && first.objectName === entry.name && first.title === entry.title, "Returning to the tab restores the same first group");
                compare(first.collapsed, true, "A remembered user fold wins over the unfolded first-group default");
            }
            console.log("SIDEBAR_FIRST_GROUPS " + JSON.stringify({page: data.page, tabs: entries}));
            compare(errors.join("\n"), "", "Every enabled sidebar tab's first foldable group starts unfolded when no user state exists");
        }
    }
}
