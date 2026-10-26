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
    width: 1280
    height: 768
    Component { id: appFactory; Main { visible: true } }
    TestCase {
        id: test
        name: "StructureBackend"
        when: windowShown
        property var app: null
        function cleanup() {
            Session.closeProject();
            if (app) { app.close(); app.destroy(); }
            app = null;
        }
        function test_structure_capability() {
            Preferences.resetToDefaults();
            app = appFactory.createObject(null);
            verify(app !== null, "Structure capability uses the actual application window");
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "Structure page navigation reaches the active production window");
            ChartBackendProof.watch(app.contentItem);
            app.update();
            verify(waitForRendering(app.contentItem), "Qt initializes its actual rendering API before structure capability is checked");
            tryVerify(() => ChartBackendProof.facts(app.contentItem).api !== undefined, 2000, "The independent reference observes Qt's actual graphics API");
            const observed = ChartBackendProof.facts(app.contentItem);
            verify(observed.api !== "Unknown", "The Structure capability reference must identify the initialized Qt API");
            const supported = ["OpenGL", "Direct3D11", "Direct3D12", "Vulkan", "Metal"].includes(observed.api);
            verify(supported || observed.api === "Software", "The Structure capability pair uses a supported graphics API or Qt Quick Software");
            const location = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/scan_template/project"));
            verify(Session.openProject(location), "Structure capability opens a private saved crystal project");
            Ui.click(test, Probe, app, "appBar.tab.structure");
            const views = Render.descendants(app.contentItem).filter(item => item.objectName === "structure.view" && item.visible && item.shown);
            compare(views.length, 1, "The actual Structure page exposes one shown production view");
            const view = views[0];
            tryVerify(() => view.current && view.atomCount > 0, 8000, "The actual Structure view receives nonempty crystal geometry");
            app.update();
            verify(waitForPolish(view) && waitForRendering(view), "The Structure view completes layout and rendering on its actual backend");
            const unavailable = findChild(view, "structure.view.unavailable");
            verify(unavailable !== null, "The Structure view retains its named unsupported-backend message");
            if (supported) {
                tryVerify(() => view.view3d !== null && view.view3d.visible && view.view3d.width > 0 && view.view3d.height > 0, 2000, "A supported Qt graphics API activates the actual Structure View3D item");
                compare(unavailable.visible, false, "A supported Qt graphics API must not show the Structure unavailable message");
            } else {
                compare(view.view3d, null, "Qt Quick Software must not activate a Structure View3D item");
                compare(unavailable.visible, true, "Qt Quick Software shows the Structure unavailable message");
            }
        }
    }
}
