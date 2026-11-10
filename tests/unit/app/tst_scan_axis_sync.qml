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
        id: structureFactory
        StructurePage {
            width: 1400
            height: 1000
            current: false
            visible: false
        }
    }
    Component {
        id: experimentFactory
        ExperimentPage {
            width: 1400
            height: 1000
            current: false
            visible: false
        }
    }
    Component {
        id: analysisFactory
        AnalysisPage {
            width: 1400
            height: 1000
            current: false
            visible: false
        }
    }
    TestCase {
        id: test
        name: "ScanAxisSync"
        when: windowShown
        property var pages: ({})
        function initTestCase() {
            verify(Examples.fixture(Session, "pd-neut-cwl_cosio-d20_scan-3f"), "Shared quantities use the real three-temperature scan");
            tryCompare(Session.project, "calculating", false, 10000, "The shared-axis project finishes its real calculation");
            pages = {
                structure: structureFactory.createObject(surface),
                experiment: experimentFactory.createObject(surface),
                analysis: analysisFactory.createObject(surface)
            };
            verify(Object.values(pages).every(page => page !== null), "The actor instantiates the actual three workflow pages once");
        }
        function cleanupTestCase() {
            for (const page of Object.values(pages))
                page.destroy();
            Session.closeProject();
        }
        function routes(quantity) {
            if (quantity === "rows")
                return ["analysis-Stacked", "analysis-Map", "analysis-Evolution"];
            return ["structure-Pattern", "experiment-Pattern", "analysis-Pattern", "analysis-Stacked", "analysis-Map"];
        }
        function show(route) {
            const [name, tabName] = route.split("-"), page = pages[name];
            for (const candidate of Object.values(pages)) {
                candidate.visible = candidate === page;
                candidate.current = candidate === page;
            }
            const tabs = Array.from(page.mainTabs), at = tabs.findIndex(tab => tab.text === tabName);
            verify(at >= 0 && tabs[at].enabled, "The actual workflow page exposes the requested quantity's tab");
            page.showMainTab(at);
            tryVerify(() => !Ui.moving(page), 1500, "The selected real tab finishes layout before axis input");
            surface.Window.window.update();
            verify(waitForPolish(page) && waitForRendering(page), "The real quantity selector has a completed visible frame");
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
            const item = findChild(page, objectName);
            verify(item !== null && item.count > 1, "Every actual selector for the same physical quantity is present: " + route + " / " + quantity);
            return item;
        }
        function choose(item, index) {
            let point;
            tryVerify(() => {
                point = Ui.clickPoint(item);
                return item.enabled && point !== null;
            }, 1500, "A real pointer reaches the visible quantity selector after its tab transition");
            mouseClick(item, point.x, point.y);
            tryCompare(item.popup, "opened", true, 1000, "The real quantity popup opens before keyboard selection");
            verify(SettingsProof.key(item, Qt.Key_Home), "The real selector receives Home");
            for (let step = 0; step < index; ++step)
                verify(SettingsProof.key(item, Qt.Key_Down), "The real selector receives Down");
            verify(SettingsProof.key(item, Qt.Key_Return), "The real selector receives Return");
            tryCompare(item, "currentIndex", index, 1000, "The origin selector changes through actual user input");
            tryCompare(item.popup, "visible", false, 1000, "The real quantity popup closes before the reverse choice");
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
            // Materialise the real tabs before testing retained selectors; navigation
            // is setup, while every axis change uses the production input control.
            for (const route of routes(data.quantity))
                control(route, data.quantity);
            for (const route of routes(data.quantity))
                show(route);
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
