// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0
import "NativeTurn.js" as Turn
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "LikesFeedback"
    when: windowShown
    property var app
    property var bar
    property var history
    property var fitWitness
    property var sent
    property string previousEndpoint
    property var previousContact
    property bool previousAskLikes
    property var previousSurveyPreference
    property bool previousTutorial
    property real clockNow
    property string gateTurnSelector: ""
    Component {
        id: application
        Main {}
    }
    Component {
        id: fitSource
        QtObject {
            property bool running: false
            property string outcome: "success"
            signal finished
        }
    }
    function find(root, name) {
        const items = Probe.objectsWithProperty(root, "objectName").filter(item => item.objectName === name);
        compare(items.length, 1, "ADR-0063: the real feedback UI exposes its control " + name);
        return items[0];
    }
    function action(label) {
        const items = Probe.objectsWithProperty(bar, "text").filter(item => item.text === label && Ui.rendered(item) && typeof item.clicked === "function");
        compare(items.length, 1, "ADR-0063: the real likes bar offers one visible action " + label);
        return items[0];
    }
    function press(item) {
        verify(item.enabled && waitForPolish(item), "ADR-0063: the likes action is enabled and laid out");
        verify(waitForRendering(item), "ADR-0063: a changed likes stage is rendered before pointer input");
        const point = Ui.clickPoint(item);
        verify(point !== null, "ADR-0063: the likes action is exposed for pointer input");
        mouseClick(item, point.x, point.y);
    }
    function locateHistory(owner) {
        const stores = Probe.objectsWithProperty(owner, "category").filter(item => item.category === "Likes");
        compare(stores.length, 1, "ADR-0063: prompt timing uses the actual persisted Likes settings");
        return stores[0];
    }
    function seed(changes) {
        const state = Object.assign({
            sessions: 3,
            firstSession: clockNow - 8 * 86400000,
            lastPrompt: 0
        }, changes || {});
        for (const key of Object.keys(state))
            history[key] = state[key];
        Preferences.askLikes = true;
        if ("shownThisSession" in bar)
            bar.shownThisSession = false;
        const survey = Probe.objectsWithProperty(app, "objectName").find(item => item.objectName === "survey.bar");
        if (survey) {
            survey.shownThisSession = false;
            survey.store.lastShown = 0;
            survey.store.stopped = false;
            survey.usefulWork = false;
            survey.visible = false;
        }
        fitWitness.running = false;
        fitWitness.outcome = "success";
        AppState.tutorialRunning = false;
        bar.stage = "";
    }
    function initTestCase() {
        verify(OnboardingProbe.startHostLog().length > 0, "ADR-0063: anonymous answers use a real run header before preferences load");
        previousContact = [Preferences.feedbackName, Preferences.feedbackEmail, Preferences.feedbackAffiliation];
        Preferences.feedbackName = "Ada Example";
        Preferences.feedbackEmail = "ada@example.invalid";
        Preferences.feedbackAffiliation = "Example Institute";
        previousAskLikes = Preferences.askLikes;
        previousSurveyPreference = Preferences.surveyInvitation;
        if (previousSurveyPreference !== undefined)
            Preferences.surveyInvitation = false;
        previousEndpoint = Preferences.feedbackEndpoint;
        previousTutorial = AppState.tutorialRunning;
        Preferences.feedbackEndpoint = "offline-feedback://fixture";
    }
    function cleanupTestCase() {
        Preferences.feedbackEndpoint = previousEndpoint;
        AppState.tutorialRunning = previousTutorial;
        Preferences.askLikes = previousAskLikes;
        Preferences.feedbackName = previousContact[0];
        Preferences.feedbackEmail = previousContact[1];
        Preferences.feedbackAffiliation = previousContact[2];
        if (previousSurveyPreference !== undefined)
            Preferences.surveyInvitation = previousSurveyPreference;
        OnboardingProbe.finishHostLog();
    }
    function init() {
        gateTurnSelector = Turn.begin(test, Probe, message => test.warn(message));
        sent = [];
        OnboardingProbe.interceptUrls();
        app = application.createObject(null);
        verify(app !== null && waitForRendering(app.contentItem), "ADR-0063: likes acceptance uses the rendered production window");
        const form = find(app, "feedback.form");
        form.endpoint = "offline-feedback://fixture";
        form.transport = function () {
            fail("ADR-0063: routing to feedback must not submit a problem report automatically");
        };
        bar = find(app, "likes.bar");
        bar.transport = function (url, payload, done) {
            sent.push(payload);
            done(201);
        };
        history = locateHistory(bar);
        fitWitness = fitSource.createObject(test);
        bar.fit = fitWitness;
        clockNow = Date.now();
        seed();
        fitWitness.finished();
        tryCompare(bar, "visible", true, 1000, "ADR-0063: a successful fit signal shows the eligible production likes bar");
    }
    function cleanup() {
        OnboardingProbe.releaseUrls();
        AppState.tutorialRunning = false;
        Preferences.dialogShown = false;
        if (app)
            app.destroy();
        if (fitWitness)
            fitWitness.destroy();
        app = null;
        bar = null;
        history = null;
        fitWitness = null;
        Turn.end(gateTurnSelector, message => test.warn(message));
    }
    function test_a_bar_uses_the_approved_controls() {
        const title = Probe.objectsWithProperty(bar, "text").filter(item => item.text === "Enjoying EasyDiffraction?" && Ui.rendered(item));
        compare(title.length, 1, "ADR-0063: the likes bar asks the approved question");
        compare(title[0].font.pixelSize, 14, "ADR-0063: the question shares the approved 14 pixel text size");
        verify(history.lastPrompt >= clockNow && history.lastPrompt <= Date.now(), "ADR-0063: the cooldown starts when the question is shown, before any answer");
        const status = find(app, "statusBar");
        verify(!status.visible, "ADR-0063: Home never shows the status bar");
        const root = Ui.windowRoot(app);
        verify(waitForPolish(bar), "ADR-0063: the Home likes bar finishes layout");
        verify(Math.abs(bar.mapToItem(root, 0, bar.height).y - root.height) <= 1, "ADR-0063: Home's likes bar sits at the window bottom");
        compare(Probe.objectsWithProperty(bar, "cursorPosition").filter(item => Ui.rendered(item)).length, 0, "ADR-0063: the question bar has no inline text editor");
        for (const obsolete of ["Send", "Send again", "Tell us more in the 10–15 min survey"])
            compare(Probe.objectsWithProperty(bar, "text").filter(item => item.text === obsolete && Ui.rendered(item) && typeof item.clicked === "function").length, 0, "ADR-0063: the question bar has no second-stage send or survey action");
        for (const label of ["Yes", "Not really", "Not sure"]) {
            const button = action(label);
            compare(Math.round(button.height), 32, "ADR-0063: likes choices use 32 pixel controls");
            compare(button.font.pixelSize, 14, "ADR-0063: likes choices use one 14 pixel text size");
        }
        action("Don't ask again");
    }
    function test_b_activity_blocks_an_offer_data() {
        return [
            {
                tag: "fitting"
            },
            {
                tag: "tutorial"
            },
            {
                tag: "disabled"
            },
            {
                tag: "young"
            },
            {
                tag: "few-sessions"
            },
            {
                tag: "recent"
            }
        ];
    }
    function test_b_activity_blocks_an_offer(data) {
        seed();
        if (data.tag === "fitting")
            fitWitness.running = true;
        if (data.tag === "tutorial")
            AppState.tutorialRunning = true;
        if (data.tag === "disabled")
            Preferences.askLikes = false;
        if (data.tag === "young")
            history.firstSession = clockNow - 86400000;
        if (data.tag === "few-sessions")
            history.sessions = 2;
        if (data.tag === "recent")
            history.lastPrompt = clockNow - 86400000;
        fitWitness.finished();
        tryCompare(bar, "visible", false, 1000, "ADR-0063: activity, opt-out and stored timing limits prevent an offer");
        compare(sent.length, 0, "ADR-0063: suppressing a prompt never sends feedback");
    }
    function test_b_live_activity_hides_the_bar_data() {
        return [
            {
                tag: "fitting"
            },
            {
                tag: "tutorial"
            }
        ];
    }
    function test_b_live_activity_hides_the_bar(data) {
        if (data.tag === "fitting")
            fitWitness.running = true;
        else
            AppState.tutorialRunning = true;
        tryCompare(bar, "visible", false, 1000, "ADR-0063: a shown prompt never remains visible during a fit or tutorial");
        compare(sent.length, 0, "ADR-0063: hiding a prompt for activity never submits an answer");
    }
    function test_c_negative_answers_open_the_existing_form_data() {
        return [
            {
                tag: "problem",
                label: "Not really",
                answer: "no"
            },
            {
                tag: "question",
                label: "Not sure",
                answer: "unsure"
            }
        ];
    }
    function test_c_negative_answers_open_the_existing_form(data) {
        press(action(data.label));
        const form = find(app, "feedback.form");
        tryCompare(form, "opened", true, 1000, "ADR-0063: a negative or uncertain answer opens the existing feedback form");
        verify(find(form, "feedback.text").enabled, "A negative or uncertain answer opens the shared message editor");
        compare(sent.length, 1, "ADR-0063: the chosen like answer is submitted once while the follow-up message awaits composition");
        compare(sent[0].kind, "likes", "ADR-0063: the answer is identified for the likes submission route");
        compare(sent[0].answer, data.answer, "ADR-0063: the answer matches the actual clicked choice");
        checkAnonymousAnswer(sent[0]);
        press(find(form, "feedback.cancel"));
        tryCompare(form, "visible", false, 1000, "ADR-0063: the routed form can be cancelled");
        compare(sent.length, 1, "ADR-0063: Cancel never retracts or repeats the already submitted answer");
    }
    function checkAnonymousAnswer(answer) {
        verify(answer.app && answer.app.version !== "" && answer.app.os !== "", "ADR-0063: an answer carries the real app version and system lines");
        verify(!("contact" in answer) && !("log" in answer), "ADR-0063: a likes answer is anonymous and contains neither contact nor log");
        const wire = JSON.stringify(answer);
        for (const contact of ["Ada Example", "ada@example.invalid", "Example Institute"])
            verify(!wire.includes(contact), "ADR-0063: saved contact values are absent from every answer field");
    }
    function test_d_yes_sends_then_opens_feedback() {
        let finish;
        bar.transport = function (url, payload, done) {
            sent.push(payload);
            finish = done;
        };
        press(action("Yes"));
        const form = find(app, "feedback.form");
        tryCompare(form, "opened", true, 1000, "ADR-0063: Yes immediately opens the existing Share feedback form");
        compare(sent.length, 1, "ADR-0063: Yes sends its answer once before the user composes feedback");
        compare(sent[0].kind, "likes", "ADR-0063: the answer carries the likes submission route");
        compare(sent[0].answer, "yes", "ADR-0063: the submitted answer retains the clicked Yes choice");
        checkAnonymousAnswer(sent[0]);
        verify(find(form, "feedback.text").enabled, "Yes leaves the shared message editor usable");
        tryCompare(bar, "visible", false, 1000, "ADR-0063: answering closes the question bar without a Yes stage");
        press(find(form, "feedback.cancel"));
        tryCompare(form, "visible", false, 1000, "ADR-0063: the optional follow-up can be cancelled");
        compare(sent.length, 1, "ADR-0063: cancelling the follow-up keeps the already sent Yes answer");
        verify(typeof finish === "function", "ADR-0063: the follow-up opened while the answer's transport was pending");
        finish(201, "");
        verify(!form.visible, "ADR-0063: a late answer completion never reopens the cancelled follow-up");
    }
    function test_e_opt_out_and_close_are_dismissible_data() {
        return [
            {
                tag: "opt-out",
                object: "",
                text: "Don't ask again"
            },
            {
                tag: "close",
                object: "likes.close",
                text: ""
            }
        ];
    }
    function test_e_opt_out_and_close_are_dismissible(data) {
        press(data.object === "" ? action(data.text) : find(bar, data.object));
        tryCompare(bar, "visible", false, 1000, "ADR-0063: opt-out and close dismiss the production bar");
        compare(sent.length, 0, "ADR-0063: dismissing the initial question never sends feedback");
        if (data.tag === "opt-out")
            verify(!Preferences.askLikes, "ADR-0063: Don't ask again turns off the persisted preference");
    }
    function test_f_another_fit_does_not_repeat_a_recent_prompt() {
        press(find(bar, "likes.close"));
        const sessions = history.sessions;
        fitWitness.finished();
        compare(history.sessions, sessions, "ADR-0063: further fits in the same window never count as new sessions");
        tryCompare(bar, "visible", false, 1000, "ADR-0063: another fit respects the persisted three-month cooldown");
    }
    function test_g_unsuccessful_fits_do_not_prompt_data() {
        return [
            {
                tag: "stopped"
            },
            {
                tag: "maxIterations"
            }
        ];
    }
    function test_g_unsuccessful_fits_do_not_prompt(data) {
        seed();
        fitWitness.outcome = data.tag;
        fitWitness.finished();
        tryCompare(bar, "visible", false, 1000, "ADR-0063: a stopped or unconverged fit is not a successful fit for prompting");
    }
    function test_h_opt_out_survives_a_new_bar_instance() {
        press(action("Don't ask again"));
        const sessions = history.sessions;
        const firstSession = history.firstSession;
        const lastPrompt = history.lastPrompt;
        const previous = app;
        app = null;
        bar = null;
        history = null;
        previous.destroy();
        tryVerify(() => !Qt.isQtObject(previous), 2000, "ADR-0063: the original bar and its settings are destroyed before re-creation");
        app = application.createObject(null);
        verify(app !== null && waitForRendering(app.contentItem), "ADR-0063: another real window loads the stored opt-out");
        bar = find(app, "likes.bar");
        history = locateHistory(bar);
        verify(!Preferences.askLikes, "ADR-0063: Don't ask again survives destruction and re-creation of the bar");
        Preferences.feedbackSettings.sync();
        compare(String(Preferences.feedbackSettings.value("askLikes", true)), "false", "ADR-0063: the opt-out is written to the real Feedback settings group");
        compare(history.sessions, sessions + 1, "ADR-0063: the next application window counts exactly one persisted new session");
        compare(history.firstSession, firstSession, "ADR-0063: subsequent sessions retain the original first-session date");
        compare(history.lastPrompt, lastPrompt, "ADR-0063: another application window retains the persisted last-prompt time");
    }
    function test_i_preferences_offer_both_feedback_switches_data() {
        return [
            {
                tag: "likes",
                name: "preferences.askLikes",
                property: "askLikes",
                label: "Enjoying EasyDiffraction? prompt"
            },
            {
                tag: "survey",
                name: "preferences.surveyInvitation",
                property: "surveyInvitation",
                label: "Survey invitation"
            }
        ];
    }
    function test_i_preferences_offer_both_feedback_switches(row) {
        Preferences[row.property] = true;
        tryVerify(() => String(Preferences.feedbackSettings.value(row.property)) === "true", 1500, "ADR-0063: each preference starts persisted On so Off must perform a real change");
        press(find(app, "appBar.button.preferences"));
        const dialog = find(app, "preferences");
        tryCompare(dialog, "opened", true, 1000, "ADR-0063: the actual Preferences dialog opens");
        press(find(dialog, "preferences.tab.interface"));
        const combo = find(dialog, row.name);
        Ui.scrollIntoView(combo);
        verify(waitForPolish(combo) && waitForRendering(combo), "ADR-0063: the Feedback preference row is rendered before inspection");
        verify(Probe.objectsWithProperty(dialog, "text").some(item => item.text === row.label && Ui.rendered(item)), "ADR-0063: Interface Feedback names each prompt setting");
        compare([combo.textAt(0), combo.textAt(1)], ["On", "Off"], "ADR-0063: each Feedback setting is an On/Off choice");
        for (const option of ["Off", "On"]) {
            press(combo);
            tryCompare(combo.popup, "opened", true, 1000, "ADR-0063: the setting opens its actual choice popup");
            const choices = () => Render.descendants(combo.popup.contentItem).filter(item => item.text === option && typeof item.clicked === "function" && Ui.rendered(item));
            tryVerify(() => choices().length === 1, 1000, "ADR-0063: the requested On/Off choice is rendered and selectable");
            press(choices()[0]);
            tryCompare(combo.popup, "visible", false, 1000, "ADR-0063: the selected settings popup closes before the next input");
            compare(Preferences[row.property], option === "On", "ADR-0063: the chosen prompt setting reaches persisted Preferences");
            tryVerify(() => String(Preferences.feedbackSettings.value(row.property)) === String(option === "On"), 1500, "ADR-0063: each On/Off choice is stored in the real Feedback settings group");
        }
    }
}
