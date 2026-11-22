import QtQuick
import QtQuick.Window
import QtTest
import "ExampleProjects.js" as Examples
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui

Item {
    id: surface
    width: 1400
    height: 1000
    Component {
        id: appFactory
        Main {
            width: 1400
            height: 1000
            visible: true
        }
    }
    TestCase {
        id: test
        name: "ScanAxisSync"
        when: windowShown
        property var pages: ({})
        property var appWindow
        property var preparedRoutes: ({})
        function initTestCase() {
            AppState.reset();
            appWindow = appFactory.createObject(null);
            verify(appWindow !== null && appWindow.visible, "Shared quantities use the actual application window and its workflow pages");
            appWindow.requestActivate();
            tryCompare(appWindow, "active", true, 2000, "Quantity input reaches the active application window");
            verify(Examples.fixture(Session, "pd-neut-cwl_cosio-d20_scan-3f"), "Shared quantities use the real three-temperature scan");
            tryCompare(Session.project, "calculating", false, 10000, "The shared-axis project finishes its real calculation");
            Ui.click(test, Probe, appWindow, "appBar.tab.structure");
            const items = Render.descendants(appWindow.contentItem);
            for (const name of ["structure", "experiment", "analysis"])
                pages[name] = items.find(item => item.pageName === name && item.pageViewItem !== undefined);
            verify(Object.values(pages).every(page => page !== undefined), "The actor resolves the application's actual three retained workflow pages");
        }
        function cleanupTestCase() {
            Session.closeProject();
            if (appWindow) {
                appWindow.close();
                appWindow.destroy();
            }
            appWindow = null;
            pages = ({});
        }
        function routes(quantity) {
            if (quantity === "rows")
                return ["analysis-Stacked", "analysis-Map", "analysis-Evolution"];
            return ["structure-Pattern", "experiment-Pattern", "analysis-Pattern", "analysis-Stacked", "analysis-Map"];
        }
        function show(route) {
            const [name, tabName] = route.split("-"), page = pages[name];
            Ui.click(test, Probe, appWindow, "appBar.tab." + name);
            verify(Ui.page(appWindow).item === page && page.current, "The actual app bar selects the owner of the requested quantity");
            const view = page.pageViewItem;
            verify(view !== null && Render.descendants(page.mainArea).includes(view), "The quantity selector belongs to this page's own main view");
            const tabs = Array.from(view.tabs), at = tabs.findIndex(tab => tab.text === tabName);
            verify(at >= 0 && tabs[at].visible && tabs[at].enabled, "The actual workflow main view exposes the requested quantity's tab");
            Ui.click(test, Probe, appWindow, "mainArea.tab." + tabName.toLowerCase());
            tryCompare(view, "currentKey", tabName.toLowerCase(), 1000, "The page-owned view selects the requested physical quantity's tab");
            tryVerify(() => !Ui.moving(page), 1500, "The selected real tab finishes layout before axis input");
            verify(waitForPolish(appWindow), "The real quantity selector completes layout before its requested frame");
            appWindow.update();
            verify(waitForRendering(appWindow.contentItem), "The real quantity selector has a completed visible frame");
            return page;
        }
        function control(route, quantity) {
            const [name, tab] = route.split("-"), page = pages[name];
            let objectName;
            if (tab === "Pattern")
                objectName = "chart.toolbar." + (quantity === "x" ? "xaxis" : "yscale");
            else if (tab === "Evolution")
                objectName = "evolution.toolbar.x";
            else
                objectName = "scanView." + tab.toLowerCase() + ".toolbar." + (quantity === "x" ? "xaxis" : quantity === "rows" ? "rows" : "yscale");
            const view = page.pageViewItem, content = Array.from(view.items)[view.tabOf(tab.toLowerCase())];
            const owner = tab === "Pattern" ? content.chart : content;
            verify(owner !== null && owner !== undefined, "The selector belongs to this tab's live content: " + route);
            if (tab === "Pattern")
                verify(owner.experiment === Session.project.currentExperiment && owner.report === null, "The quantity selector belongs to the current experiment's app chart");
            const items = Render.descendants(owner).filter(item => item.objectName === objectName);
            verify(items.length === 1 && items[0].count > 1, "Every actual selector for the same physical quantity is present once: " + route + " / " + quantity);
            return items[0];
        }
        function choose(item, index) {
            const original = item;
            let morePopup = null;
            if (item.x < -1000) {
                const row = item.parent, more = findChild(row, row.objectName + ".more");
                verify(more !== null && more.enabled && Ui.clickPoint(more) !== null, "The quantity's actual toolbar exposes its More entrance");
                const point = Ui.clickPoint(more);
                mouseClick(more, point.x, point.y);
                morePopup = findChild(row, row.objectName + ".more.popup");
                verify(morePopup !== null, "The More entrance owns its actual toolbar popup");
                tryCompare(morePopup, "opened", true, 1000, "Real pointer input opens the overflow quantity controls");
                tryVerify(() => {
                    item = Render.descendants(morePopup.contentItem).find(control => control.objectName === original.objectName + ".overflow" && control.visible && control.enabled);
                    return item !== undefined;
                }, 1000, "The actual More popup exposes the requested physical quantity's control");
            }
            let point;
            tryVerify(() => {
                point = Ui.clickPoint(item);
                return item.enabled && point !== null;
            }, 1500, "A real pointer reaches the visible quantity selector after its tab transition: " + original.objectName + " " + JSON.stringify({
                enabled: item.enabled,
                visible: item.visible,
                x: item.x,
                width: item.width,
                height: item.height,
                point: Ui.clickPoint(item)
            }));
            mouseClick(item, point.x, point.y);
            tryCompare(item.popup, "opened", true, 1000, "The real quantity popup opens before keyboard selection");
            mouseMove(appWindow.contentItem, appWindow.contentItem.width - 1, appWindow.contentItem.height - 1);
            verify(SettingsProof.key(item, Qt.Key_Home), "The real selector receives Home");
            for (let step = 0; step < index; ++step)
                verify(SettingsProof.key(item, Qt.Key_Down), "The real selector receives Down");
            verify(SettingsProof.key(item, Qt.Key_Return), "The real selector receives Return");
            tryCompare(item, "currentIndex", index, 1000, "The origin selector changes through actual user input");
            tryCompare(original, "currentIndex", index, 1000, "The actual quantity choice reaches its retained original control");
            tryCompare(item.popup, "visible", false, 1000, "The real quantity popup closes before the reverse choice");
            if (morePopup) {
                verify(SettingsProof.key(item, Qt.Key_Escape), "Real Escape closes More after choosing the quantity");
                tryCompare(morePopup, "visible", false, 1000, "The overflow popup closes before observing other quantity controls");
            }
        }
        function test_each_quantity_is_shared_both_directions_data() {
            const rows = [];
            for (const quantity of ["x", "intensity", "rows"])
                for (const origin of routes(quantity))
                    rows.push({
                        tag: quantity + "-" + origin,
                        quantity,
                        origin
                    });
            return rows;
        }
        function test_each_quantity_is_shared_both_directions(data) {
            // Each retained chart acquires its calculated axis columns on its
            // first visible frame. Prepare each route once in this actor, then
            // keep testing both directions on the same live selectors.
            for (const route of routes(data.quantity)) {
                if (!preparedRoutes[route]) {
                    show(route);
                    preparedRoutes[route] = true;
                }
            }
            for (const route of routes(data.quantity))
                control(route, data.quantity);
            show(data.origin);
            const origin = control(data.origin, data.quantity), before = origin.currentIndex;
            const after = before === 0 ? 1 : 0;
            choose(origin, after);
            for (const destination of routes(data.quantity))
                tryCompare(control(destination, data.quantity), "currentIndex", after, 1000, "Changing " + data.origin + " changes the same quantity on " + destination);
            choose(origin, before);
            for (const destination of routes(data.quantity))
                tryCompare(control(destination, data.quantity), "currentIndex", before, 1000, "The reverse choice propagates to every selector for that quantity");
        }
    }
}
