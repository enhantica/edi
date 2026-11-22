// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// The likes bar shows inside the whole window whether or not the status bar does: on Home with no project (the status
// bar hidden) from Home's link, and after a successful fit with the status bar shown, standing on it, never over it.
TestCase {
    name: "MainLikesBar"
    when: windowShown

    property var window: null

    QtObject {
        id: fakeFit

        signal finished
        property bool running: false
        property string outcome: "success"
    }

    function visit(item, name) {
        if (!item)
            return null;
        if (item.objectName === name)
            return item;
        for (const child of item.children) {
            const found = visit(child, name);
            if (found)
                return found;
        }
        return null;
    }
    function insideWindow(item) {
        const at = item.mapToItem(window.contentItem, 0, 0);
        return item.visible && item.height > 0 && at.y >= 0 && at.y + item.height <= window.contentItem.height + 0.5;
    }

    function initTestCase() {
        failOnWarning(/qml|QML|\.js:/);
        const component = Qt.createComponent("qrc:/qt/qml/edi/app/qml/Main.qml");
        verify(component.status === Component.Ready, component.errorString());
        window = component.createObject(null);
        verify(window);
        window.visible = true;
        tryVerify(() => findChild(window, "likes.bar") !== null, 10000);
    }
    function cleanupTestCase() {
        window.destroy();
    }

    function test_a_home_link_shows_the_bar_with_the_status_bar_hidden() {
        const status = findChild(window, "statusBar");
        verify(!status.visible, "Home with no project hides the status bar");
        const link = visit(window.contentItem, "home.likes");
        verify(link, "Home's Enjoying link");
        mouseClick(link);
        const bar = findChild(window, "likes.bar");
        tryVerify(() => bar.visible);
        verify(insideWindow(bar), "inside the window");
        const at = bar.mapToItem(window.contentItem, 0, 0);
        compare(Math.round(at.y + bar.height), Math.round(window.contentItem.height), "at the bottom edge");
        mouseClick(visit(bar, "likes.close"));
        tryVerify(() => !bar.visible);
    }
    function test_b_a_successful_fit_shows_it_standing_on_the_status_bar() {
        const bar = findChild(window, "likes.bar");
        const status = findChild(window, "statusBar");
        AppState.open(AppState.Page.Project);
        tryVerify(() => status.visible, 5000, "another page shows the status bar");
        bar.store.sessions = 5;
        bar.store.firstSession = Date.now() - 30 * 24 * 3600 * 1000;
        bar.store.lastPrompt = 0;
        bar.store.disabled = false;
        bar.shownThisSession = false;  // Home's link showed it in this session already (test_a)
        bar.fit = fakeFit;
        fakeFit.finished();
        tryVerify(() => bar.visible, 3000);
        verify(insideWindow(bar));
        const barBottom = bar.mapToItem(window.contentItem, 0, bar.height).y;
        const statusTop = status.mapToItem(window.contentItem, 0, 0).y;
        verify(barBottom <= statusTop + 0.5, `the bar (bottom ${barBottom}) stands on the status bar (top ${statusTop})`);
    }

    function test_c_no_status_bar_on_home_in_any_case() {
        AppState.open(AppState.Page.Home);
        const status = findChild(window, "statusBar");
        AppState.tutorialRunning = true;
        wait(50);
        verify(!status.visible, "not even while a tutorial runs");
        AppState.tutorialRunning = false;
        const update = visit(window.contentItem, "home.update");
        verify(update, "Home has the Update available link");
        compare(update.visible, DesktopUpdates.available);
    }
    // The x edges of what a bar item shows: a button's content, a field's box, a label's text.
    function edges(bar, item) {
        if (item.contentItem && item.objectName !== "likes.text")
            return [item.contentItem.mapToItem(bar, 0, 0).x, item.contentItem.mapToItem(bar, item.contentItem.width, 0).x];
        if (item.contentWidth !== undefined && item.objectName !== "likes.text")
            return [item.mapToItem(bar, item.leftPadding, 0).x, item.mapToItem(bar, item.leftPadding + item.contentWidth, 0).x];
        return [item.mapToItem(bar, 0, 0).x, item.mapToItem(bar, item.width, 0).x];
    }
    function gapsOf(bar, names) {
        const shown = names.map(name => visit(bar, name));
        const gaps = [];
        for (let i = 1; i < shown.length; ++i)
            gaps.push(edges(bar, shown[i])[0] - edges(bar, shown[i - 1])[1]);
        return gaps;
    }
    function test_d_no_leading_icon_and_one_gap() {
        const bar = findChild(window, "likes.bar");
        bar.stage = "ask";
        tryVerify(() => bar.visible);
        const question = visit(bar, "likes.question");
        const shown = Array.from(question.parent.children).filter(item => item.visible && item.width > 0);
        compare(shown[0], question, "the question comes first, with no icon before it");
        compare(shown.length, 4, "the question and its three answers only");
        const gaps = gapsOf(bar, ["likes.question", "likes.yes", "likes.no", "likes.unsure"]);
        verify(Math.max(...gaps) - Math.min(...gaps) <= 1, `one gap: ${gaps}`);
        bar.close();
    }
    // Every answer is sent at once, then opens Help and feedback: Yes as Share feedback.
    function test_f_each_answer_is_sent_and_opens_the_form() {
        const bar = findChild(window, "likes.bar");
        const dialog = findChild(window, "feedback.form");
        const sent = [];
        bar.endpoint = "https://feedback.invalid/feedback";
        bar.transport = (url, payload, completed) => {
            sent.push(payload);
            Qt.callLater(() => completed(201, ""));
        };
        const expected = {
            "yes": "feedback",
            "no": "problem",
            "unsure": "question"
        };
        for (const answer of ["yes", "no", "unsure"]) {
            bar.stage = "ask";
            tryVerify(() => bar.visible);
            wait(Qt.styleHints.mouseDoubleClickInterval + 50);
            mouseClick(visit(bar, "likes." + answer));
            tryVerify(() => !bar.visible);
            compare(sent[sent.length - 1].answer, answer);
            if (dialog) {
                tryVerify(() => dialog.opened || dialog.visible, 3000, "the form opens");
                compare(dialog.kind, expected[answer]);
                dialog.close();
                tryVerify(() => !dialog.visible);
            }
        }
        const last = sent[sent.length - 1];
        compare(last.kind, "likes");
        verify(last.app && last.app.version !== undefined && last.app.os !== undefined, "the app lines go with the answer");
        verify(last.log === undefined && last.contact === undefined, "never the log or contact details");
    }
    function test_e_dont_ask_again_is_a_preference() {
        const bar = findChild(window, "likes.bar");
        Preferences.askLikes = true;
        bar.stage = "ask";
        tryVerify(() => bar.visible);
        mouseClick(visit(bar, "likes.never"));
        tryVerify(() => !bar.visible);
        verify(!Preferences.askLikes, "Don't ask again turns the setting off");
        bar.store.lastPrompt = 0;
        bar.shownThisSession = false;
        fakeFit.finished();
        wait(200);
        verify(!bar.visible, "off: a successful fit does not ask");
        Preferences.askLikes = true;
        bar.shownThisSession = false;
        fakeFit.finished();
        tryVerify(() => bar.visible, 3000, "on again in Preferences: it asks");
        bar.stage = "";
    }
    // The two bars together (owner, 2026-11-17): a loaded project with no successful fit still gets the survey
    // invitation once the likes bar's thresholds are met, and Home's likes action replaces a showing invitation.
    function test_g_survey_after_a_load_and_home_replaces_it() {
        const likes = findChild(window, "likes.bar");
        const survey = findChild(window, "survey.bar");
        verify(survey);
        likes.close();
        likes.shownThisSession = false;
        likes.fit = fakeFit;
        fakeFit.running = false;
        likes.store.sessions = 9;
        likes.store.firstSession = Date.now() - 60 * 24 * 3600 * 1000;
        likes.store.lastPrompt = 0;
        Preferences.askLikes = true;
        Preferences.surveyInvitation = true;
        survey.store.stopped = false;
        survey.store.lastShown = 0;
        survey.shownThisSession = false;
        survey.usefulWork = true;  // a project was loaded; no fit has run
        survey.lastInput = Date.now() - 61 * 1000;
        survey.offer();
        verify(survey.visible, "no successful fit is pending, so the invitation is not held back");
        verify(!likes.visible);
        AppState.likesRequested();
        tryVerify(() => likes.visible);
        verify(!survey.visible, "the likes bar never sits over the invitation");
        survey.lastInput = Date.now() - 61 * 1000;
        survey.offer();
        verify(!survey.visible, "not both in one session");
        likes.close();
    }
}
