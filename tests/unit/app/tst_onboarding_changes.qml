// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0
import EasyApplication.Gui.Globals as EaGlobals
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "OnboardingChanges"
    when: windowShown
    property var app
    property var reference
    Component {
        id: application
        Main {}
    }
    function init() {
        reference = JSON.parse(OnboardingProbe.sourceText("tests/fixtures/onboarding/changelog.json"));
        OnboardingProbe.injectChangelog(JSON.stringify(reference.entries.map(entry => ({
                    date: entry.date,
                    text: entry.changes.map(change => "- " + change).join("\n")
                }))));
        OnboardingProbe.interceptUrls();
        verify(typeof Preferences.whatsNewSeen === "string", "What's new has an injectable stored last-seen date");
    }
    function cleanup() {
        OnboardingProbe.stopClock();
        const urls = OnboardingProbe.urls();
        OnboardingProbe.releaseUrls();
        if (app)
            app.destroy();
        app = null;
        OnboardingProbe.injectChangelog("");
        verify(urls.every(url => /^https?:\/\/[^/]+/.test(url)), "What's new dispatches only absolute HTTP(S) documentation URLs");
    }
    function openApp(lastSeen) {
        Preferences.whatsNewSeen = lastSeen;
        app = application.createObject(null);
        verify(app !== null, "The injected changes are exercised in the actual application window");
        verify(waitForRendering(app.contentItem), "Startup changes use the rendered production window");
    }
    function popup() {
        const found = Probe.objectsWithProperty(app, "objectName").filter(item => item.objectName === "whatsNew");
        compare(found.length, 1, "The actual app owns one What's new popup");
        return found[0];
    }
    function press(item) {
        verify(item !== undefined && item !== null, "A changes action exists before input");
        tryVerify(() => item.visible && item.enabled && Ui.exposed(item), 2000, "The changes action is visibly available before input");
        verify(waitForPolish(item), "The changes action finishes layout before input");
        const point = Ui.clickPoint(item);
        verify(point !== null, "Changes navigation clicks inside the real action");
        mouseClick(item, point.x, point.y);
    }
    function manual(small = false) {
        openApp(reference.newest);
        if (small) {
            app.width = app.minimumWidth;
            app.height = app.minimumHeight;
        }
        Preferences.whatsNewSeen = reference.lastSeen;
        const link = Probe.objectsWithProperty(app, "text").find(item => item.visible && item.text === "What's new" && typeof item.clicked === "function");
        press(link);
        tryCompare(popup(), "opened", true, 2000, "The Home What's new action opens its in-app popup");
        compare(OnboardingProbe.urls().length, 0, "Opening What's new does not open a browser");
    }
    function shown(expected) {
        const rows = Render.descendants(popup().contentItem).filter(item => item.objectName.startsWith("whatsNew.day.") && Ui.rendered(item));
        rows.sort((a, b) => a.mapToItem(app.contentItem, 0, 0).y - b.mapToItem(app.contentItem, 0, 0).y);
        compare(rows.map(item => item.objectName.slice("whatsNew.day.".length)).join("|"), expected.join("|"), "What's new paints precisely the requested entries in newest-first scene order");
        for (const row of rows) {
            const date = row.objectName.slice("whatsNew.day.".length);
            const entry = reference.entries.find(item => item.date === date);
            for (const change of entry.changes)
                verify(Ui.text(row).includes(change), "The injected change text is actually rendered for " + date);
        }
    }
    function test_manual_popup_filters_since_seen_and_sorts_newest_first() {
        manual();
        shown(["2031-02-28", "2031-02-16"]);
    }
    function test_show_all_changes_lists_every_entry() {
        manual();
        const action = Probe.objectsWithProperty(popup(), "text").find(item => item.visible && item.text === "Show all changes" && typeof item.clicked === "function");
        press(action);
        shown(["2031-02-28", "2031-02-16", "2031-02-05", "2030-12-31"]);
    }
    function test_show_all_changes_stays_in_footer_data() {
        return [
            {
                tag: "default",
                small: false
            },
            {
                tag: "small",
                small: true
            }
        ];
    }
    function fullyVisible(item) {
        if (!Ui.rendered(item))
            return false;
        const bounds = item.mapToItem(app.contentItem, 0, 0, item.width, item.height);
        if (bounds.x < 0 || bounds.y < 0 || bounds.x + bounds.width > app.contentItem.width || bounds.y + bounds.height > app.contentItem.height)
            return false;
        for (let parent = item.parent; parent; parent = parent.parent) {
            if (!parent.clip)
                continue;
            const r = item.mapToItem(parent, 0, 0, item.width, item.height);
            if (r.x < -1 || r.y < -1 || r.x + r.width > parent.width + 1 || r.y + r.height > parent.height + 1)
                return false;
        }
        return true;
    }
    function test_show_all_changes_stays_in_footer(data) {
        OnboardingProbe.injectChangelog(JSON.stringify(reference.entries.map(entry => ({
                    date: entry.date,
                    text: Array.from({
                        length: 30
                    }, (_, index) => "- **Feature " + index + "**: a change with enough detail to exercise the scrolling list.").join("\n")
                }))));
        manual(data.small);
        const dialog = popup();
        const action = Probe.objectsWithProperty(dialog, "objectName").find(item => item.objectName === "whatsNew.showAll");
        verify(action !== undefined, "The changes popup exposes its show-all control before any list scrolling");
        const footerItems = Render.descendants(dialog.footer);
        verify(footerItems.includes(action), "Show all changes belongs to the fixed footer, not the scrolling list");
        compare(action.text, "Show all changes", "The footer uses the agreed Show all changes label");
        const closes = footerItems.filter(item => item.text === "Close" && typeof item.clicked === "function" && item.visible);
        compare(closes.length, 1, "Show all changes and the actual Close action share the fixed footer");
        const close = closes[0];
        const body = Render.descendants(dialog.contentItem).find(item => typeof item.contentY === "number" && item.contentHeight > item.height + 1);
        verify(body !== undefined, "The long injected changes actually overflow the list at each window size");
        compare(body.contentY, body.originY, "The popup opens at the top without scrolling to reveal its footer");
        for (const item of [action, close])
            verify(fullyVisible(item), "Show all changes and Close are fully visible without scrolling at " + data.tag + " window size");
        const a = action.mapToItem(app.contentItem, 0, action.height / 2);
        const c = close.mapToItem(app.contentItem, 0, close.height / 2);
        verify(Math.abs(a.y - c.y) <= 1, "Show all changes sits beside Close on the same footer row");
        const original = [action, close].map(item => item.mapToItem(app.contentItem, 0, 0));
        body.contentY = body.originY + body.contentHeight - body.height;
        app.update();
        verify(waitForRendering(app.contentItem), "The overflowing changes list renders its scrolled position");
        for (const item of [action, close])
            verify(fullyVisible(item), "Only the list scrolls; both footer actions stay visible");
        [action, close].forEach((item, index) => {
            const after = item.mapToItem(app.contentItem, 0, 0);
            verify(Math.abs(after.x - original[index].x) <= 1 && Math.abs(after.y - original[index].y) <= 1, "Scrolling changes cannot move either fixed footer action");
        });
        body.contentY = body.originY;
        press(action);
        verify(waitForPolish(dialog.contentItem), "All changes finish layout after the real footer click");
        app.update();
        verify(waitForRendering(app.contentItem), "All changes render after the real footer click");
        const rows = Render.descendants(dialog.contentItem).filter(item => item.objectName.startsWith("whatsNew.day."));
        compare(rows.length, reference.entries.length, "The visible footer action really switches to every injected entry");
    }
    function test_documentation_link_opens_the_full_changes_page() {
        manual();
        const action = Probe.objectsWithProperty(popup(), "objectName").find(item => item.objectName === "whatsNew.page");
        press(action);
        const urls = OnboardingProbe.urls();
        compare(urls.length, 1, "The changes documentation link dispatches one URL through the injected handler");
        verify(/^https:\/\/enhantica\.github\.io\/edi\//.test(urls[0]) && /changelog|changes|whats-new/.test(urls[0]), "The full changes link uses the public documentation changes page");
    }
    function test_update_opens_once_then_restart_remembers_seen_date() {
        openApp(reference.lastSeen);
        tryCompare(popup(), "opened", true, 2000, "An update automatically opens What's new on its first start");
        shown(["2031-02-28", "2031-02-16"]);
        press(popup().standardButton(Dialog.Close));
        tryCompare(popup(), "visible", false, 2000, "The user dismisses the automatic changes popup");
        compare(Preferences.whatsNewSeen, reference.newest, "Seeing the update stores its newest date");
        verify(OnboardingProbe.settingsContain(String(EaGlobals.Vars.settingsFile), reference.newest), "The last-seen date is written to the real settings file before an immediate restart");
        app.destroy();
        app = null;
        app = application.createObject(null);
        verify(app !== null && waitForRendering(app.contentItem), "A second app start retains the real last-seen preference");
        OnboardingProbe.startClock();
        OnboardingProbe.advanceClock(10000);
        OnboardingProbe.stopClock();
        verify(!popup().visible, "The same update never automatically opens a second time");
    }
    function test_current_and_future_seen_dates_do_not_auto_open_data() {
        return [
            {
                tag: "current",
                date: "2031-02-28"
            },
            {
                tag: "future",
                date: "2031-03-01"
            }
        ];
    }
    function test_current_and_future_seen_dates_do_not_auto_open(data) {
        openApp(data.date);
        OnboardingProbe.startClock();
        OnboardingProbe.advanceClock(10000);
        OnboardingProbe.stopClock();
        verify(!popup().visible, "A current or newer stored date has no unseen update to open");
    }
}
