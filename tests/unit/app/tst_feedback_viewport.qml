// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "FeedbackViewport"
    when: windowShown
    property var app
    property var form
    property string previousEndpoint
    property bool sampleOpening: false
    property var frames: []
    property var fontReference
    FontMetrics {
        id: metrics
        font: test.fontReference || Qt.font({
            pixelSize: 14
        })
    }
    Component {
        id: application
        Main {}
    }
    Connections {
        target: test.app
        enabled: test.sampleOpening
        function onAfterAnimating() {
            test.recordFrame();
        }
    }
    function init() {
        previousEndpoint = Preferences.feedbackEndpoint;
        Preferences.feedbackEndpoint = "https://feedback.example.invalid/feedback";
        app = application.createObject(null);
        verify(app !== null, "Feedback viewport checks use the actual application window");
        app.width = 1200;
        app.height = 1000;
        form = one(app, "feedback.form");
        form.transport = function () {
            fail("Viewport checks cannot use a network transport");
        };
        AppState.open(AppState.Page.Home);
        verify(waitForRendering(app.contentItem), "The Home entry is rendered before opening the form");
        OnboardingProbe.startClock();
        frames = [];
    }
    function cleanup() {
        sampleOpening = false;
        OnboardingProbe.stopClock();
        if (app)
            app.destroy();
        app = null;
        form = null;
        Preferences.feedbackEndpoint = previousEndpoint;
    }
    function one(root, name) {
        const found = Probe.objectsWithProperty(root, "objectName").filter(item => item.objectName === name);
        compare(found.length, 1, "The real feedback flow exposes exactly one control: " + name);
        return found[0];
    }
    function press(item) {
        verify(waitForPolish(item), "The actual form action finishes layout before input");
        const point = Ui.clickPoint(item);
        verify(item.enabled && point !== null, "The actual form action is enabled and exposed");
        mouseClick(item, point.x, point.y, Qt.LeftButton, Qt.NoModifier, 0);
    }
    function open(settle = true) {
        const link = Probe.objectsWithProperty(app, "text").find(item => item.text === "Help and feedback" && Ui.rendered(item) && typeof item.clicked === "function");
        verify(link !== undefined, "Viewport acceptance opens feedback through its actual Home action");
        press(link);
        if (settle) {
            OnboardingProbe.advanceClock(1000);
            tryCompare(form, "opened", true, 2000, "The actual form finishes opening on the injected animation clock");
            verify(waitForPolish(app), "The form finishes its actual layout before measurement");
        }
    }
    function textArea(name) {
        const root = one(form, name);
        const candidates = Render.descendants(root).filter(item => typeof item.positionToRectangle === "function" && typeof item.cursorPosition === "number");
        compare(candidates.length, 1, "The named text box contains one actual text-edit surface: " + name);
        return candidates[0];
    }
    function flickable(item) {
        for (let parent = item.parent; parent; parent = parent.parent)
            if (typeof parent.contentY === "number" && typeof parent.contentHeight === "number")
                return parent;
        fail("The real text box has an observable scrolling viewport");
        return null;
    }
    function body() {
        return flickable(one(form, "feedback.kind"));
    }
    function showPreview() {
        form.attachedLog = Array.from({
            length: 40
        }, (_, n) => "diagnostic line " + n).join("\n");
        const toggle = one(form, "feedback.preview");
        press(toggle);
        OnboardingProbe.advanceClock(1000);
        verify(waitForPolish(app), "The expanded preview and body finish layout before measurement");
        return textArea("feedback.payload");
    }
    function bars() {
        return Probe.objectsWithProperty(form, "orientation").filter(item => item.orientation === Qt.Vertical && (OnboardingProbe.inheritsType(item, "QQuickScrollBar") || OnboardingProbe.inheritsType(item, "QQuickScrollIndicator")));
    }
    function painted(item) {
        if (!Ui.rendered(item))
            return false;
        let opacity = 1;
        for (let parent = item; parent; parent = parent.parent)
            opacity *= parent.opacity;
        return opacity > 0.001;
    }
    function visibleBars() {
        return bars().filter(painted);
    }
    function recordFrame() {
        if (!form || !form.visible)
            return;
        frames.push({
            height: form.height,
            bars: visibleBars().length
        });
    }
    function lineHeight(area) {
        fontReference = area.font;
        return metrics.lineSpacing;
    }
    function visibleLines(area) {
        const viewport = flickable(area);
        return (viewport.height - area.topPadding - area.bottomPadding) / lineHeight(area);
    }
    function wheel(viewport) {
        const point = Ui.clickPoint(viewport);
        verify(point !== null, "The active scroll viewport is exposed for actual wheel input");
        mouseWheel(viewport, point.x, point.y, 0, -120, Qt.NoButton, Qt.NoModifier, 0);
        OnboardingProbe.advanceClock(16);
        verify(waitForRendering(app.contentItem), "The real scroll input is rendered before checking its indicator");
    }
    function test_preview_uses_six_readable_monospaced_lines_data() {
        const rows = [];
        for (const theme of ["light", "dark"])
            for (const part of ["height-and-scroll", "monospace", "normal-colour"])
                rows.push({
                    tag: theme + "-" + part,
                    theme: theme,
                    part: part
                });
        return rows;
    }
    function test_preview_uses_six_readable_monospaced_lines(data) {
        const original = Style.Colors.theme;
        try {
            Style.Colors.theme = data.theme === "dark" ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            open();
            const area = showPreview();
            verify(area.readOnly && area.enabled, "The preview is read-only without disabling its readable text");
            if (data.part === "height-and-scroll") {
                verify(Math.abs(visibleLines(area) - 6) * lineHeight(area) <= 2, "At normal height the preview displays six lines plus its field padding");
                const viewport = flickable(area), before = viewport.contentY;
                verify(viewport.contentHeight > viewport.height, "Long preview JSON exceeds the six-line viewport");
                wheel(viewport);
                verify(viewport.contentY > before, "An actual wheel scroll exposes more of the complete preview");
            } else if (data.part === "monospace") {
                fontReference = area.font;
                verify(Math.abs(metrics.advanceWidth("iiiiiiii") - metrics.advanceWidth("WWWWWWWW")) <= 0.1, "The preview's actual font assigns equal advances to narrow and wide glyphs");
            } else {
                compare(String(area.color), String(Style.Colors.themeForeground), "Read-only preview text retains the normal foreground colour in both themes");
            }
        } finally {
            Style.Colors.theme = original;
        }
    }
    function test_message_box_shows_five_lines() {
        open();
        const area = textArea("feedback.text");
        verify(Math.abs(visibleLines(area) - 5) * lineHeight(area) <= 2, "The message field opens five lines tall plus its padding");
    }
    function test_opening_starts_at_top_with_message_focus_data() {
        return [
            {
                tag: "normal",
                height: 1000
            },
            {
                tag: "small",
                height: 640
            }
        ];
    }
    function test_opening_starts_at_top_with_message_focus(data) {
        app.height = data.height;
        open();
        const viewport = body(), area = textArea("feedback.text");
        compare(viewport.contentY, viewport.originY, "The feedback body opens at its first row rather than scrolled down");
        verify(area.activeFocus, "The newly opened form places the text cursor in the message field");
        const lines = Render.texts(form.contentItem).filter(item => item.text === "We'd love to hear from you to make EasyDiffraction better.");
        compare(lines.length, 1, "The opening line remains visible at the top of the newly opened form");
    }
    function test_privacy_note_wraps_to_two_lines_at_default_font() {
        open();
        const note = one(form, "feedback.note");
        verify(Ui.rendered(note), "The wide-window privacy note is actually rendered");
        compare(note.lineCount, 2, "At the default font and sufficient app width the privacy note wraps to exactly two lines");
    }
    function controlsInsideWindow() {
        const margin = Math.max(1, form.margins, form.topMargin, form.bottomMargin);
        verify(form.height <= app.contentItem.height - 2 * margin, "The feedback window height respects a nonzero margin inside the app window");
        const bounds = form.background.mapToItem(app.contentItem, 0, 0, form.background.width, form.background.height);
        verify(bounds.y >= margin && bounds.y + bounds.height <= app.contentItem.height - margin, "The form's top and bottom borders remain inside the app's visible area");
        const title = Render.texts(form.header).find(item => item.text === "Help and feedback");
        verify(title !== undefined, "The feedback window has a visible title above its scrolling body");
        for (const item of [title, one(form, "feedback.cancel"), one(form, "feedback.send")]) {
            const r = item.mapToItem(app.contentItem, 0, 0, item.width, item.height);
            verify(Ui.rendered(item) && r.x >= 0 && r.y >= 0 && r.x + r.width <= app.contentItem.width && r.y + r.height <= app.contentItem.height, "Title, Cancel and Send stay fully visible at small app heights");
        }
    }
    function test_small_window_keeps_title_and_actions_visible_data() {
        return [
            {
                tag: "minimum",
                height: 640
            },
            {
                tag: "short",
                height: 720
            }
        ];
    }
    function test_small_window_keeps_title_and_actions_visible(data) {
        app.height = data.height;
        open();
        showPreview();
        controlsInsideWindow();
        const viewport = body();
        if (data.tag === "minimum")
            verify(viewport.contentHeight > viewport.height, "At the minimum window the form exceeds its capped body and must scroll");
        if (viewport.contentHeight > viewport.height)
            viewport.contentY = viewport.originY + viewport.contentHeight - viewport.height;
        else {
            const preview = flickable(textArea("feedback.payload"));
            verify(preview.contentHeight > preview.height, "When the complete form fits a short window, the six-line preview owns scrolling instead");
        }
        verify(waitForPolish(app), "The body finishes scrolling before its fixed title and actions are rechecked");
        controlsInsideWindow();
    }
    function test_only_the_correct_viewport_scrolls_data() {
        return [
            {
                tag: "normal",
                height: 1000
            },
            {
                tag: "small",
                height: 640
            }
        ];
    }
    function test_only_the_correct_viewport_scrolls(data) {
        app.height = data.height;
        open();
        const preview = showPreview(), previewView = flickable(preview), bodyView = body();
        verify(visibleBars().length <= 1, "The form never shows two scroll bars after preview expansion");
        const active = data.tag === "normal" ? previewView : bodyView;
        const inactive = data.tag === "normal" ? bodyView : previewView;
        verify(active.contentHeight > active.height, "The expected viewport owns overflow at this window height");
        verify(inactive.contentHeight <= inactive.height + 1, "The other viewport expands to its content instead of introducing nested scrolling");
        if (data.tag === "small")
            verify(preview.height >= preview.contentHeight, "At a small height the preview exposes all JSON lines to the body scroller");
        const before = active.contentY;
        wheel(active);
        verify(active.contentY > before, "The actual wheel moves the expected single scroll viewport");
        compare(visibleBars().length, 1, "Scrolling overflow exposes exactly one scroll indicator");
    }
    function test_fitting_content_has_no_indicator_on_any_opening_frame() {
        sampleOpening = true;
        open(false);
        recordFrame();
        // The production animation driver advances each frame, without sleeping.
        for (let elapsed = 0; elapsed < 1000; elapsed += 16) {
            OnboardingProbe.advanceClock(16);
            app.update();
            verify(waitForRendering(app.contentItem), "Every opening-frame sample accompanies a rendered real window");
        }
        sampleOpening = false;
        verify(form.opened && frames.length > 2, "The frame observer spans the actual opening through its settled state");
        const viewport = body();
        verify(viewport.contentHeight <= viewport.height + 1, "The opening-flash control has content that fits without body scrolling");
        verify(frames.every(frame => frame.bars === 0), "No rendered opening frame flashes a scroll indicator when content fits");
    }
}
