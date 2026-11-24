// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "OnboardingChoices"
    when: windowShown
    property var app
    Component {
        id: application
        Main {}
    }
    function init() {
        app = application.createObject(null);
        verify(app !== null, "Choice acceptance opens the actual app");
        AppState.open(AppState.Page.Home);
        verify(waitForRendering(app.contentItem), "The actual Home page renders before choice input");
    }
    function cleanup() {
        Preferences.dialogShown = false;
        Preferences.loggingLevel = "Info";
        if (app)
            app.destroy();
        app = null;
    }
    function named(name) {
        const items = Probe.objectsWithProperty(app, "objectName").filter(item => item.objectName === name);
        compare(items.length, 1, "The actual app exposes the requested choice control: " + name);
        return items[0];
    }
    function press(item) {
        tryVerify(() => item.visible && item.enabled && Ui.exposed(item), 2000, "Choice input uses an exposed actual control");
        verify(waitForPolish(item), "Choice input follows actual control layout");
        const point = Ui.clickPoint(item);
        verify(point !== null, "The selected choice has a real visible click point");
        mouseClick(item, point.x, point.y);
    }
    function test_opened_choices_are_visible_and_selectable_data() {
        return [
            {
                tag: "logging-level",
                labels: ["Debug", "Info", "Warning", "Error"],
                values: ["Debug", "Info", "Warning", "Error"]
            }
        ];
    }
    function test_opened_choices_are_visible_and_selectable(data) {
        press(named("appBar.button.preferences"));
        tryCompare(named("preferences"), "opened", true, 2000, "Preferences finishes opening before choosing logging");
        press(named("preferences.tab.advanced"));
        const combo = named("preferences.loggingLevel");
        for (let index = 0; index < data.labels.length; ++index) {
            press(combo);
            tryCompare(combo.popup, "opened", true, 2000, "The combo opens its actual popup before inspecting choices");
            const labels = Render.texts(combo.popup.contentItem).filter(item => Ui.rendered(item)).map(item => item.text);
            compare(Array.from(new Set(labels)).sort(), data.labels.slice().sort(), "The opened choice popup paints every exact label, with no empty or missing delegate");
            const delegates = Render.descendants(combo.popup.contentItem).filter(item => item.text === data.labels[index] && typeof item.clicked === "function" && Ui.rendered(item));
            compare(delegates.length, 1, "Each visible popup label belongs to one selectable delegate");
            press(delegates[0]);
            tryCompare(combo.popup, "visible", false, 2000, "Choosing a rendered row closes the popup");
            compare(combo.currentValue, data.values[index], "The selected painted row sets the corresponding actual value");
            compare(Preferences.loggingLevel, data.values[index], "The chosen value reaches the logging preference");
        }
    }
}
