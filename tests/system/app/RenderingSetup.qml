// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ChartBackendAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Globals as Globals
import "../../unit/app/RenderedTable.js" as Render
import "../../unit/app/UiInteraction.js" as Ui
import "RendererPath.js" as RendererPath

Item {
    id: surface
    width: 1280
    height: 768
    Component { id: appFactory; Main { visible: true } }
    Component { id: chartFactory; ScanViewChart { width: 1100; height: 650; shown: true; mode: "stacked" } }
    TestCase {
        id: test
        name: "RenderingSetup"
        when: windowShown
        property var app: null
        property var chart: null
        function initTestCase() {
            ChartBackendProof.useStore();
            if (String(ChartBackendProof.store()) !== "")
                compare(String(Globals.Vars.settingsFile), String(ChartBackendProof.store()), "The restart witness uses the actual host's private settings-path seam");
        }
        function cleanup() {
            if (chart) chart.destroy();
            chart = null;
            if (app) { app.close(); app.destroy(); }
            app = null;
            Session.closeProject();
        }
        function window() {
            app = appFactory.createObject(null);
            verify(app !== null, "Rendering setup uses the production application window");
            app.width = 1280;
            app.height = 768;
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "The renderer controls receive real input on the active app window");
            ChartBackendProof.watch(app.contentItem);
            app.update();
            verify(waitForRendering(app.contentItem), "Qt renders the app before its backend is observed");
            tryVerify(() => ChartBackendProof.facts(app.contentItem).api !== undefined, 2000, "The independent observer reads Qt's actual rendering API");
            return app;
        }
        function reference() {
            const observed = ChartBackendProof.facts(app.contentItem);
            verify(observed.api !== "Unknown", "The renderer reference identifies an initialized Qt backend");
            if (observed.api === "OpenGL")
                verify(observed.renderer.length > 0, "The renderer reference reads GL_RENDERER from the current Qt OpenGL context");
            return observed;
        }
        function software(observed) {
            return RendererPath.software(observed);
        }
        function click(item) {
            verify(item !== null && item.visible && item.enabled, "The renderer preference control is visible and enabled");
            const point = Ui.clickPoint(item);
            verify(point !== null, "The actual renderer preference is inside its visible viewport");
            mouseClick(item, point.x, point.y);
            app.update();
            verify(waitForRendering(app.contentItem), "A real renderer-preference click reaches the next rendered frame");
        }
        function develop() {
            Ui.click(test, Probe, app, "appBar.button.preferences");
            const dialog = findChild(app, "preferences");
            verify(dialog !== null, "The app retains its actual Preferences dialog");
            tryCompare(dialog, "opened", true, 1000, "Preferences opens through the app-bar button");
            const tab = findChild(dialog, "preferences.tab.develop");
            click(tab);
            tryCompare(tab, "checked", true, 1000, "The real Develop tab is selected before inspecting rendering setup");
            return dialog;
        }
        function options(box) {
            return Array.from({length: box.count}, (_, index) => box.textAt(index));
        }
        function overrideControl(dialog) {
            const candidates = Render.descendants(dialog.contentItem).filter(item => {
                if (!Ui.rendered(item) || typeof item.textAt !== "function") return false;
                const values = options(item);
                return values.some(text => /gpu/i.test(text)) && values.some(text => /software|painter|cpu/i.test(text));
            });
            compare(candidates.length, 1, "Develop offers one scan-renderer selector with GPU and software choices");
            return candidates[0];
        }
        function scan() {
            const location = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/scan_template/project"));
            verify(Session.openProject(location), "The renderer witness opens a private independent scan project");
            chart = chartFactory.createObject(app.contentItem, {project: Session.project});
            verify(chart !== null, "The renderer witness uses the production Stacked view");
            tryCompare(chart.scan, "loaded", 3, 8000, "The renderer witness loads all saved input files");
            settled();
            const layer = findChild(chart, "scanView.stacked.layer");
            verify(layer !== null, "The actual Stacked plot exposes its existing line item");
            return layer;
        }
        function settled() {
            app.update();
            verify(waitForPolish(chart) && waitForRendering(chart), "The active renderer is observed after the loaded scan reaches a completed frame");
        }
        function test_qt_reference() {
            window();
            reference();
        }
        function test_develop_reports_detection() {
            window();
            const observed = reference(), dialog = develop();
            const text = Render.texts(dialog.contentItem).filter(item => Ui.rendered(item)).map(item => item.text).join("\n");
            verify(text.toLowerCase().includes(observed.api.toLowerCase()), "Develop displays the graphics backend independently reported by Qt");
            if (observed.api === "OpenGL")
                verify(text.includes(observed.renderer), "Develop displays Qt's actual OpenGL renderer string");
            if (software(observed))
                verify(/no\s*gpu|software renderer|software rendering/i.test(text), "Develop classifies Qt's software renderer as no GPU");
        }
        function test_default_uses_detected_renderer() {
            window();
            const observed = reference(), dialog = develop(), box = overrideControl(dialog);
            verify(/auto/i.test(box.currentText) || (software(observed) ? /software|painter|cpu/i.test(box.currentText) : /gpu/i.test(box.currentText)), "A fresh app's renderer choice agrees with the detected hardware or automatic mode");
            dialog.close();
            RendererPath.check(test, ChartBackendProof, scan(), RendererPath.effectiveGpu(observed, "auto"), settled);
        }
        function test_override_roundtrip() {
            window();
            const observed = reference();
            const dialog = develop(), box = overrideControl(dialog), wanted = ChartBackendProof.choice();
            const values = options(box);
            const index = values.findIndex(text => wanted === "gpu" ? /gpu/i.test(text) && !/auto/i.test(text) : /software|painter|cpu/i.test(text) && !/auto/i.test(text));
            verify(index >= 0, "The user can explicitly choose either scan-rendering path");
            if (ChartBackendProof.phase() === "write") {
                click(box);
                tryCompare(box.popup, "opened", true, 1000, "The renderer override popup opens through real pointer input");
                mouseMove(app.contentItem, app.width - 1, app.height - 1);
                verify(SettingsProof.key(box, Qt.Key_Home), "The actual renderer selector receives its first-option key");
                for (let i = 0; i < index; ++i)
                    verify(SettingsProof.key(box, Qt.Key_Down), "The actual renderer selector receives each navigation key");
                verify(SettingsProof.key(box, Qt.Key_Return), "The renderer override commits through real keyboard input");
            }
            compare(box.currentText, values[index], "The explicit renderer choice survives a complete host restart on the same machine store");
            dialog.close();
            RendererPath.check(test, ChartBackendProof, scan(), RendererPath.effectiveGpu(observed, wanted), settled);
        }
    }
}
