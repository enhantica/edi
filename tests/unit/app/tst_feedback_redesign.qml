// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Globals as Globals
import EasyApplication.Gui.Style as Style
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "FeedbackRedesign"
    when: windowShown
    property var app
    property var form
    property string originalEndpoint
    property string restartPhase: ""
    property url restartSnapshot: ""
    readonly property var placeholders: ["Name (optional)", "E-mail (optional)", "Affiliation (optional)"]
    readonly property var keys: ["name", "email", "affiliation"]
    readonly property var remembered: ["Lin Example", "lin@example.invalid", "Example Institute"]
    Component {
        id: application
        Main {}
    }
    function one(root, name) {
        const found = Probe.objectsWithProperty(root, "objectName").filter(item => item.objectName === name);
        compare(found.length, 1, "The real feedback form exposes exactly one control: " + name);
        return found[0];
    }
    function settingLocation() {
        const path = String(Globals.Vars.settingsFile), slash = path.lastIndexOf("/");
        return {
            folder: path.slice(0, slash + 1),
            name: path.slice(slash + 1)
        };
    }
    function init() {
        // In the read process restore only bytes written by the preceding app.
        // Do this before creating its Preferences singleton or any application UI.
        if (restartPhase === "read") {
            const file = settingLocation();
            const saved = SettingsProof.text(restartSnapshot, "preferences.ini");
            verify(saved.length > 0, "The second application receives the first application's persisted settings bytes");
            verify(SettingsProof.write(file.folder, file.name, saved), "The restart injects private settings before Preferences is instantiated");
        }
        originalEndpoint = Preferences.feedbackEndpoint;
        Preferences.feedbackEndpoint = "https://feedback.example.invalid/feedback";
        app = application.createObject(null);
        verify(app !== null, "Feedback redesign is exercised in the real application");
        app.width = 1200;
        app.height = 900;
        form = one(app, "feedback.form");
        form.transport = function () {
            fail("Feedback acceptance must intercept every submission without network access");
        };
        AppState.open(AppState.Page.Home);
        verify(waitForRendering(app.contentItem), "The Home feedback entry is painted before user input");
        const links = Probe.objectsWithProperty(app, "text").filter(item => Ui.rendered(item) && item.text === "Help and feedback" && typeof item.clicked === "function");
        compare(links.length, 1, "Home exposes one real Help and feedback action");
        OnboardingProbe.startClock();
        press(links[0]);
        OnboardingProbe.advanceClock(1000);
        tryCompare(form, "opened", true, 2000, "The real feedback form opens before inspection");
    }
    function cleanup() {
        OnboardingProbe.stopClock();
        if (app)
            app.destroy();
        app = null;
        form = null;
        Preferences.feedbackEndpoint = originalEndpoint;
    }
    function press(item) {
        verify(waitForPolish(item), "The feedback control finishes layout before input");
        const point = Ui.clickPoint(item);
        verify(item.enabled && point !== null, "The feedback control is enabled and exposed for real input");
        mouseClick(item, point.x, point.y);
    }
    function contacts() {
        return placeholders.map(label => {
            const fields = Probe.objectsWithProperty(form, "placeholderText").filter(item => item.placeholderText === label && typeof item.selectAll === "function");
            compare(fields.length, 1, "The feedback form has one optional single-line field: " + label);
            verify(typeof fields[0].echoMode === "number", "Optional contact details use single-line text fields");
            return fields[0];
        });
    }
    function fill(field, text) {
        press(field);
        field.selectAll();
        keyClick(Qt.Key_Backspace);
        for (const character of text)
            keyClick(character);
        keyClick(Qt.Key_Tab);
        compare(field.text.trim(), text.trim(), "Actual keyboard input populates the optional field");
    }
    function payloadPreview() {
        const toggle = one(form, "feedback.preview");
        if (/^Show/.test(toggle.text))
            press(toggle);
        const box = one(app, "feedback.payload");
        verify(waitForPolish(box), "The actual payload preview finishes layout");
        verify(Ui.rendered(box), "Show what will be sent exposes its actual JSON text");
        return JSON.parse(box.text);
    }
    function subjectField() {
        const field = one(form, "feedback.subject");
        verify(typeof field.selectAll === "function" && typeof field.echoMode === "number", "The optional subject is a real single-line field");
        return field;
    }
    function test_opening_line_is_between_the_title_and_kind() {
        const expected = "We'd love to hear from you to make EasyDiffraction better.";
        const lines = Render.texts(form.contentItem).filter(item => item.text === expected);
        compare(lines.length, 1, "The form paints the exact agreed opening line once");
        const titles = Render.texts(form.header).filter(item => item.text === "Help and feedback");
        compare(titles.length, 1, "The actual form title anchors the opening-line placement");
        const line = lines[0], title = titles[0], kind = one(form, "feedback.kind");
        compare(line.lineCount, 1, "The revised opening text occupies exactly one line");
        const y = line.mapToItem(app.contentItem, 0, 0).y;
        verify(y >= title.mapToItem(app.contentItem, 0, title.height).y && y + line.height <= kind.mapToItem(app.contentItem, 0, 0).y, "The opening line sits below the title and above the kind combobox");
        compare(String(line.color), String(Style.Colors.themeForeground), "The opening line uses normal text colour, not the muted privacy-note colour");
    }
    function test_general_feedback_is_first_and_default() {
        const combo = one(form, "feedback.kind");
        compare(combo.indexOfValue("feedback"), 0, "Share feedback is the first kind in the actual chooser");
        compare(combo.currentIndex, 0, "A newly opened form selects the first kind by default");
        compare(combo.currentValue, "feedback", "A newly opened form defaults to general feedback");
        compare(combo.currentText, "Share feedback", "The default kind displays Share feedback verbatim");
        compare(form.kind, "feedback", "The default form's wire discriminant is feedback");
    }
    function test_subject_and_message_placeholders_follow_the_kind_data() {
        return [
            {
                tag: "question",
                subject: "Your question in a few words (optional)",
                message: "What would you like to know, and what have you tried?"
            },
            {
                tag: "problem",
                subject: "What went wrong, in a few words (optional)",
                message: "What did you do, what happened, and what did you expect?"
            },
            {
                tag: "idea",
                subject: "Your idea in a few words (optional)",
                message: "What would you like the app to do, and how would it help?"
            },
            {
                tag: "feedback",
                subject: "Your feedback in a few words (optional)",
                message: "What works well for you, and what could be better?"
            }
        ];
    }
    function test_subject_and_message_placeholders_follow_the_kind(data) {
        const kind = one(form, "feedback.kind");
        const index = kind.indexOfValue(data.tag);
        verify(index >= 0, "The actual chooser contains each supported feedback kind: " + data.tag);
        kind.currentIndex = index;
        compare(form.kind, data.tag, "Changing the actual chooser selects its declared wire kind");
        compare(subjectField().placeholderText, data.subject, "The optional subject shows the kind's exact agreed placeholder");
        compare(one(form, "feedback.text").placeholderText, data.message, "The message shows the kind's exact agreed placeholder");
    }
    function test_optional_subject_is_trimmed_and_shown_in_the_payload_data() {
        return [
            {
                tag: "empty",
                text: ""
            },
            {
                tag: "whitespace",
                text: "   "
            },
            {
                tag: "filled",
                text: "  A short useful title  "
            }
        ];
    }
    function test_optional_subject_is_trimmed_and_shown_in_the_payload(data) {
        fill(subjectField(), data.text);
        one(form, "feedback.text").text = "A complete message with an optional subject";
        const payload = payloadPreview();
        if (data.text.trim() === "")
            verify(!Object.prototype.hasOwnProperty.call(payload, "subject"), "An empty or whitespace-only subject is absent from the actual preview payload");
        else
            compare(payload.subject, data.text.trim(), "The preview includes the trimmed optional subject");
        let sent = null;
        form.transport = function (url, body, done) {
            sent = JSON.stringify(body);
            done(400);
        };
        press(one(form, "feedback.send"));
        compare(sent, JSON.stringify(payload), "The actual submission includes exactly the optional subject shown in the preview");
    }
    function test_kind_has_no_redundant_question_label() {
        const labels = Render.texts(form.contentItem).map(item => item.text);
        verify(!labels.some(text => /what is this about/i.test(text)), "The kind combobox needs no What is this about question label");
    }
    function test_contact_fields_follow_the_kind_before_the_message() {
        const fields = contacts(), kind = one(form, "feedback.kind"), subject = subjectField(), message = one(form, "feedback.text");
        function rect(item) {
            return item.mapToItem(app.contentItem, 0, 0, item.width, item.height);
        }
        const kindBox = rect(kind), subjectBox = rect(subject), messageBox = rect(message);
        const rowY = rect(fields[0]).y;
        let right = kindBox.x;
        for (const field of fields) {
            verify(Ui.rendered(field), "Every optional contact field is visible in the shared row");
            const box = rect(field);
            verify(Math.abs(box.y - rowY) <= 1, "Name, E-mail and Affiliation share one horizontal row");
            verify(box.x >= right && box.y >= kindBox.y + kindBox.height, "Contact fields remain ordered and do not overlap each other or the kind row");
            verify(box.y + box.height <= subjectBox.y, "The optional subject sits below the shared contact row");
            right = box.x + box.width;
        }
        verify(Math.abs(rect(fields[0]).x - kindBox.x) <= 1 && Math.abs(subjectBox.x - kindBox.x) <= 1, "Contact row and subject align with the combobox's left edge");
        verify(subjectBox.y + subjectBox.height <= messageBox.y, "The optional subject remains directly above the message field");
    }
    function test_contact_payload_has_only_filled_trimmed_keys_data() {
        const rows = Array.from({
            length: 8
        }, (_, mask) => ({
                    tag: String(mask),
                    mask: mask
                }));
        rows.push({
            tag: "without-diagnostics",
            mask: 7
        });
        return rows;
    }
    function test_contact_payload_has_only_filled_trimmed_keys(data) {
        const fields = contacts(), expected = {};
        one(form, "feedback.include").checked = data.tag !== "without-diagnostics";
        for (let n = 0; n < fields.length; ++n) {
            const value = data.mask & (1 << n) ? "  " + remembered[n] + "  " : "   ";
            fill(fields[n], value);
            if (data.mask & (1 << n))
                expected[keys[n]] = remembered[n];
        }
        one(form, "feedback.text").text = "A question with optional contact details";
        const payload = payloadPreview();
        if (data.mask === 0) {
            verify(!Object.prototype.hasOwnProperty.call(payload, "contact"), "All-empty or whitespace-only optional inputs omit contact entirely");
        } else {
            verify(payload.contact !== null && typeof payload.contact === "object", "Filled contact details appear in the actual JSON preview");
            compare(Object.keys(payload.contact).sort().join("|"), Object.keys(expected).sort().join("|"), "Contact has exactly the filled keys, with no empty optional fields");
            for (const key of Object.keys(expected))
                compare(payload.contact[key], expected[key], "Contact values are trimmed without changing the user's supplied identity");
        }
        const sent = [];
        form.transport = function (url, body, done) {
            sent.push({
                url: String(url),
                body: JSON.stringify(body)
            });
            done(400);
        };
        press(one(form, "feedback.send"));
        compare(sent.length, 1, "Contact submission reaches the injected transport once");
        compare(sent[0].url, "https://feedback.example.invalid/feedback", "The contact gate can only reach its injected endpoint");
        compare(sent[0].body, JSON.stringify(payload), "The preview shows the exact optional contact object submitted");
    }
    function border(item) {
        // The text content may be taller than the scrolled field. Its border
        // encloses the clipped viewport, not every off-screen line of content.
        let viewport = item;
        for (let parent = item.parent; parent; parent = parent.parent) {
            if (typeof parent.contentY === "number") {
                viewport = parent;
                break;
            }
        }
        const candidates = [];
        for (const control of Render.descendants(item)) {
            for (const surface of Render.descendants(control.background)) {
                if (surface.border !== undefined && surface.border.width > 0 && surface.width >= viewport.width - 2 && surface.height >= viewport.height - 2 && !candidates.includes(surface))
                    candidates.push(surface);
            }
        }
        verify(candidates.length > 0, "Each text box has its own full-size visible field border, not a containing dialog border");
        return candidates[0];
    }
    function test_preview_and_message_share_the_field_border_data() {
        return ["light", "dark"].map(theme => ({
                    tag: theme,
                    theme: theme
                }));
    }
    function test_preview_and_message_share_the_field_border(data) {
        const original = Style.Colors.theme;
        try {
            Style.Colors.theme = data.theme === "dark" ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            payloadPreview();
            const message = one(form, "feedback.text"), preview = one(form, "feedback.payload");
            one(form, "feedback.kind").forceActiveFocus();
            mouseMove(app.contentItem, 1, 1);
            OnboardingProbe.advanceClock(1000);
            const a = border(message), b = border(preview);
            compare(b.border.width, a.border.width, "Preview and message use the same field border width");
            compare(String(b.border.color), String(a.border.color), "Preview and message use the same field border colour in each theme");
            compare(b.radius, a.radius, "Preview and message use the same field border corners");
            verify(b.border.color.a > 0 && a.border.color.a > 0, "Both actual text-box borders are painted rather than transparent");
        } finally {
            Style.Colors.theme = original;
        }
    }
    function test_checkbox_indicator_aligns_with_kind() {
        const check = one(form, "feedback.include"), combo = one(form, "feedback.kind");
        verify(check.indicator !== null && Ui.rendered(check.indicator), "The diagnostics checkbox has a painted indicator");
        const indicatorX = check.indicator.mapToItem(app.contentItem, 0, 0).x;
        const comboX = combo.mapToItem(app.contentItem, 0, 0).x;
        verify(Math.abs(indicatorX - comboX) <= 1, "The checkbox indicator, not its padded wrapper, shares the combobox's left edge");
    }
    function test_empty_message_disables_send_data() {
        return [
            {
                tag: "empty",
                value: ""
            },
            {
                tag: "whitespace",
                value: " \n\t "
            }
        ];
    }
    function test_empty_message_disables_send(data) {
        const message = one(form, "feedback.text"), send = one(form, "feedback.send");
        message.text = "A composed message";
        compare(send.enabled, true, "The injected destination and a real message enable Send");
        message.text = data.value;
        compare(send.enabled, false, "An empty or whitespace-only message disables Send despite a configured address");
    }
    function test_submission_keeps_text_on_failure_and_thanks_on_success_data() {
        return [
            {
                tag: "created",
                status: 201
            },
            {
                tag: "created-auto",
                status: 201
            },
            {
                tag: "limited",
                status: 429
            },
            {
                tag: "offline",
                status: 0
            }
        ];
    }
    function test_submission_keeps_text_on_failure_and_thanks_on_success(data) {
        const message = one(form, "feedback.text"), text = "Typed question with punctuation: why?\nA second line.";
        message.text = text;
        if (data.status === 201) {
            for (let index = 0; index < placeholders.length; ++index)
                fill(contacts()[index], remembered[index]);
            fill(subjectField(), "Subject before sending");
        }
        let completed = null, calls = 0;
        form.transport = function (url, body, done) {
            ++calls;
            completed = done;
        };
        const send = one(form, "feedback.send");
        press(send);
        compare(calls, 1, "One actual Send invokes only the injected transport");
        compare(send.enabled, false, "The form prevents duplicate Send while the injected request is pending");
        completed(data.status);
        const status = one(form, "feedback.status");
        verify(Ui.rendered(status) && status.text.trim().length > 0, "The form gives a visible outcome after the transport completes");
        if (data.status === 201) {
            compare(status.text, "Your message was sent. Thank you!", "An accepted submission replaces the form with the exact success confirmation");
            const inputs = Probe.objectsWithProperty(form, "objectName").filter(item => ["feedback.text", "feedback.subject", "feedback.kind"].includes(item.objectName) && Ui.rendered(item));
            compare(inputs.length, 0, "The confirmation replaces visible input fields instead of showing an empty form");
            const close = Probe.objectsWithProperty(form, "text").filter(item => item.text === "Close" && Ui.rendered(item) && typeof item.clicked === "function");
            compare(close.length, 1, "Success retains an immediate Close action");
            if (data.tag === "created-auto") {
                verify(form.visible, "The success confirmation is initially visible before its injected delay");
                // A timer arms on a frame and its exit transition needs later
                // frames; one large jump cannot observe that sequence.
                for (let elapsed = 0; elapsed < 1000; elapsed += 10)
                    OnboardingProbe.advanceClock(10);
                verify(form.visible, "The confirmation remains readable for at least one injected second");
                for (let elapsed = 1000; elapsed < 2500 && form.visible; elapsed += 10)
                    OnboardingProbe.advanceClock(10);
                compare(form.visible, false, "The confirmation closes automatically within the bounded 2.5-second injected delay");
            } else {
                press(close[0]);
                OnboardingProbe.advanceClock(300);
                compare(form.visible, false, "Close dismisses the confirmation immediately without waiting for its timer");
            }
            const link = Probe.objectsWithProperty(app, "text").find(item => item.text === "Help and feedback" && Ui.rendered(item) && typeof item.clicked === "function");
            verify(link !== undefined, "The accepted form can be reopened from Home");
            press(link);
            OnboardingProbe.advanceClock(1000);
            tryCompare(form, "opened", true, 2000, "A subsequent Home action opens a fresh feedback form");
            compare(one(form, "feedback.text").text, "", "Reopening after success starts with an empty message");
            compare(subjectField().text, "", "Reopening after success starts with an empty subject");
            const retained = contacts();
            for (let index = 0; index < retained.length; ++index)
                compare(retained[index].text, remembered[index], "Successful sends preserve the optional contact fields for the next message");
        } else {
            verify(form.visible, "A failed submission keeps the composed form open");
            compare(message.text, text, "Rate limits and transport failures preserve the exact typed multiline message");
            verify(data.status === 429 ? /too many|rate.limit/i.test(status.text) : /connect|network|offline/i.test(status.text), "A failure explains its specific rate-limit or connection reason");
            compare(send.enabled, true, "A failed request allows the retained message to be retried");
        }
    }
    function test_failed_submission_preserves_optional_contact_data() {
        return [
            {
                tag: "limited",
                status: 429
            },
            {
                tag: "offline",
                status: 0
            }
        ];
    }
    function test_failed_submission_preserves_optional_contact(data) {
        const fields = contacts();
        for (let n = 0; n < fields.length; ++n)
            fill(fields[n], remembered[n]);
        one(form, "feedback.text").text = "Please retain my optional reply details";
        fill(subjectField(), "Retain this subject too");
        form.transport = function (url, body, done) {
            done(data.status);
        };
        press(one(form, "feedback.send"));
        for (let n = 0; n < fields.length; ++n)
            compare(fields[n].text, remembered[n], "A rate limit or connection failure preserves every optional reply field");
        compare(subjectField().text, "Retain this subject too", "A failed request keeps the optional subject for retry");
    }
    // The Python witness adds one selected test function to a temporary copy and
    // launches two different host processes. These helpers never seed contact values.
    function writeContactSettings() {
        const fields = contacts();
        for (let n = 0; n < fields.length; ++n)
            fill(fields[n], remembered[n]);
        press(one(form, "feedback.cancel"));
        OnboardingProbe.advanceClock(1000);
        const stores = Probe.objectsWithProperty(Preferences, "location").concat(Probe.objectsWithProperty(app, "location"), Probe.objectsWithProperty(Preferences, "fileName"), Probe.objectsWithProperty(app, "fileName"));
        for (const store of stores) {
            if (typeof store.sync !== "function")
                continue;
            // Qt Settings buffers property changes on a wall-clock timer. Moving
            // its location flushes the current store synchronously, as destruction
            // does, without sleeping or synthesising any persisted key/value.
            if (typeof store.location !== "undefined")
                store.location = String(store.location) + ".closed";
            store.sync();
        }
        const file = settingLocation();
        const bytes = SettingsProof.text(file.folder, file.name);
        for (const value of remembered)
            verify(bytes.includes(value), "The real settings file persists each supplied contact value before restart");
        verify(SettingsProof.write(restartSnapshot, "preferences.ini", bytes), "The first app exports only its actual settings bytes to the restart fixture");
    }
    function readContactSettings() {
        const fields = contacts();
        for (let n = 0; n < fields.length; ++n)
            compare(fields[n].text, remembered[n], "A new application process restores each optional contact field from settings");
    }
}
