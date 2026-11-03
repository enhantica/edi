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
                tag: "feedback-kind",
                kind: "feedback",
                labels: ["Share feedback", "Ask a question", "Report a problem", "Suggest an idea"],
                values: ["feedback", "question", "problem", "idea"]
            },
            {
                tag: "logging-level",
                kind: "logging",
                labels: ["Debug", "Info", "Error", "Disabled"],
                values: ["Debug", "Info", "Error", "Disabled"]
            }
        ];
    }
    function test_opened_choices_are_visible_and_selectable(data) {
        let combo;
        if (data.kind === "feedback") {
            named("feedback.form").endpoint = "https://feedback.example.invalid/feedback";
            named("feedback.form").transport = function () {
                fail("Choosing a feedback kind never makes a network request");
            };
            const link = Probe.objectsWithProperty(app, "text").find(item => item.visible && item.text === "Help and feedback" && typeof item.clicked === "function");
            verify(link !== undefined, "The feedback choice is entered through the real Home link");
            press(link);
            tryCompare(named("feedback.form"), "opened", true, 2000, "The feedback form finishes opening before choosing its kind");
            combo = named("feedback.kind");
        } else {
            press(named("appBar.button.preferences"));
            tryCompare(named("preferences"), "opened", true, 2000, "Preferences finishes opening before choosing logging");
            press(named("preferences.tab.develop"));
            combo = named("preferences.loggingLevel");
        }
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
            compare(data.kind === "feedback" ? named("feedback.form").kind : Preferences.loggingLevel, data.values[index], "The chosen value reaches the feedback payload or logging preference");
        }
    }
}
