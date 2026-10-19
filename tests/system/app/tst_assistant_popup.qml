import QtQuick
import QtQuick.Window
import QtCore
import QtQuick.Controls
import QtTest
import edi.app
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EdiChartReference 1.0
import "../../unit/app/UiInteraction.js" as Ui

// Owner 99d50f71f supersedes the former second-dock and alternate-entry tests.
// Real Main/Session only. No provider, seeded message model or synthetic busy state.
TestCase {
    name: "AssistantPopup"
    when: windowShown
    FontMetrics { id: gui398FontMetrics }
    TextMetrics { id: gui470ActionInk }
    property var window
    property var popup
    property var assistant
    property var oldSide
    property var oldTheme
    property var oldToolTips
    Component {
        id: application
        Main {}
    }

    // Independent native window: ordinary focus/activation and input, never another Main/Session.
    Component {
        id: otherWindow479
        ApplicationWindow {
            width: 240
            height: 100
            visible: false
            title: "Acceptance unrelated window"
            Button {
                objectName: "input479.unrelated"
                anchors.centerIn: parent
                text: "Unrelated window input"
            }
        }
    }

    // Existing Probe.watch owns a QPointer and signal spies; retain only its
    // integer handle and a scalar identity captured while the QObject is alive.
    function lifetime313(object) {
        if (object === null) return null;
        const handle = Probe.watch(object);
        verify(handle >= 0 && Probe.watchedAlive(handle),
            "OBS313 SETUP: original QObject lifetime is captured while alive");
        return {handle: handle, identity: String(object)};
    }
    function alive313(receipt) {
        return receipt !== null && Probe.watchedAlive(receipt.handle);
    }
    function identity313(receipt) { return receipt === null ? "null" : receipt.identity; }
    function disconnect313(receipt, object, signal, callback) {
        // QObject destruction already disconnects its signals. Never access a
        // dead wrapper merely to ask whether its old signal property exists.
        if (alive313(receipt)) object[signal].disconnect(callback);
    }

    function item(name) {
        const found = findChild(window, name);
        verify(found !== null, "I16/popup: the actual application owns " + name);
        return found;
    }
    function rendered() {
        tryVerify(() => {
            if (Ui.moving(window.contentItem) || !window.contentArea) return false;
            const page = window.contentArea[AppState.Page.Project];
            const view = page ? page.SwipeView.view : null;
            const viewport = view ? view.contentItem : null;
            if (!viewport || !viewport.currentItem
                || viewport.currentIndex !== window.appBarCentralTabs.currentIndex) return false;
            // Qt Basic SwipeView uses ListView's strict preferred-highlight anchor.
            // Highlight auto-scroll can continue with Flickable.moving === false.
            // This observes actual selected-item placement, independent of Assistant geometry.
            const selected = viewport.currentItem.mapToItem(viewport, 0, 0);
            const position = view.orientation === Qt.Horizontal ? selected.x : selected.y;
            return Math.abs(position - viewport.preferredHighlightBegin) < 0.5;
        }, 2000, "I16/popup: actual navigation finishes before geometry observations");
        verify(waitForPolish(window, 2000), "I16/popup: queued layout settles before geometry observations");
        window.update();
        verify(waitForRendering(window.contentItem), "I16/popup: actual window renders after interaction");
    }
    function rect(control) {
        const point = control.mapToItem(window.contentItem, 0, 0);
        return [point.x, point.y, control.width, control.height];
    }
    function sameRect(actual, expected) {
        for (let i = 0; i < 4; ++i)
            verify(Math.abs(actual[i] - expected[i]) < 0.5, "I16/popup: actual sidebar/main rectangle stays aligned");
    }
    // Main's genuine appbar returns from current manual takeover before an
    // ordinary open/close action. Preference and physical visibility are distinct.
    function togglePolicy388(shown, takeover) {
        return {preference: takeover || !shown,
            action: takeover ? "return-to-chat" : (shown ? "ordinary-close" : "ordinary-open")};
    }
    function toggle() {
        const control = item("assistant.toggle");
        const original = {window: window, popup: popup, owner: Session.project,
            page: window.assistantWorkflowPage, assistant: assistant};
        const lives = [window, popup, control, original.owner, original.page, assistant].map(lifetime313);
        function current() {
            verify(lives.every(life => life === null || alive313(life)),
                "I16/popup: original appbar window/control/owner/page receivers remain alive");
            verify(window === original.window && popup === original.popup
                && Session.project === original.owner && window.assistantWorkflowPage === original.page
                && assistant === original.assistant && Session.assistant === original.assistant
                && findChild(window, "assistant.toggle") === control,
                "I16/popup: genuine action cannot retarget a replacement owner/window/page/control");
            verify(original.page !== null && window.visible && control.visible && control.enabled,
                "I16/popup: existing current workflow appbar button remains actionable");
            const center = control.mapToItem(window.contentItem, control.width / 2, control.height / 2);
            verify(Ui.exposed(control) && center.x >= 0 && center.y >= 0
                && center.x < window.contentItem.width && center.y < window.contentItem.height,
                "I16/popup: original actual-window appbar input point remains exposed");
        }
        current();
        let policy = togglePolicy388(Preferences.assistantShown, window.assistantManualTakeover);
        pointerObservation("before-toggle", control, policy.preference);
        const receipts = [];
        let truePresses = 0;
        let releases = 0;
        let clicks = 0;
        let canceledCount = 0;
        function receipt(name) {
            current();
            receipts.push(name);
            pointerObservation("button-" + name, control, policy.preference);
        }
        function pressedChanged() {
            current();
            if (control.pressed) ++truePresses;
            receipt("pressedChanged=" + control.pressed);
        }
        function released() {
            current();
            // Observe the real release, after genuine input filtering and before
            // the ensuing clicked action. Never infer takeover from popup output.
            compare(clicks, 0, "I16/popup: original release precedes its clicked receipt");
            policy = togglePolicy388(Preferences.assistantShown, window.assistantManualTakeover);
            ++releases;
            receipt("released-" + policy.action);
        }
        function clicked() { ++clicks; receipt("clicked"); }
        function canceled() { ++canceledCount; receipt("canceled"); }
        const connected = [];
        try {
            for (const pair of [["pressedChanged", pressedChanged], ["released", released],
                                ["clicked", clicked], ["canceled", canceled]]) {
                control[pair[0]].connect(pair[1]);
                connected.push(pair);
            }
            pointerObservation("before-pointer-move", control, policy.preference);
            mouseMove(control, control.width / 2, control.height / 2);
            current();
            policy = togglePolicy388(Preferences.assistantShown, window.assistantManualTakeover);
            pointerObservation("after-pointer-move", control, policy.preference);
            mouseClick(control);
        } finally {
            for (const pair of connected)
                disconnect313(lives[2], control, pair[0], pair[1]);
            console.log("APPBAR_CONTROL_RECEIPTS", JSON.stringify(receipts));
        }
        current();
        compare(truePresses, 1, "I16/popup: one genuine original button press is observed");
        compare(releases, 1, "I16/popup: one genuine original button release is observed");
        compare(clicks, 1, "I16/popup: one genuine original button clicked receipt is observed");
        compare(canceledCount, 0, "I16/popup: original appbar click is not a canceled input");
        compare(Preferences.assistantShown, policy.preference,
            "I16/popup: appbar follows original return-from-takeover or ordinary visibility policy");
        compare(window.assistantManualTakeover, false,
            "I16/popup: explicit original appbar return consumes only current takeover");
        pointerObservation("after-toggle", control, policy.preference);
        function requestedVisible() {
            current();
            compare(Preferences.assistantShown, policy.preference,
                "I16/popup: original request remains exact while its presentation settles");
            compare(window.assistantManualTakeover, false,
                "I16/popup: a newer takeover cannot silently satisfy old visibility cleanup");
            return policy.preference && !assistant.showingActions;
        }
        try {
            tryVerify(() => {
                const expected = requestedVisible();
                return popup.visible === expected;
            }, 2000,
                "I16/slide: actual opened/fully closed visibility follows current request and visible-action suppression");
        } finally {
            current();
            pointerObservation("after-toggle-wait", control, policy.preference);
        }
        if (requestedVisible())
            tryVerify(() => { current(); return popup.opened === true; }, 2000,
                "I16/slide: settled opening waits for actual enter completion");
        rendered();
        current();
        console.log("APPBAR_ACTION388", JSON.stringify({action: policy.action,
            preference: policy.preference, showingActions: assistant.showingActions,
            manualTakeover: window.assistantManualTakeover, visible: popup.visible,
            opened: popup.opened, window: identity313(lives[0]), popup: identity313(lives[1]),
            control: identity313(lives[2]), owner: identity313(lives[3]), page: identity313(lives[4])}));
        return policy.action;
    }
    function closeAssistant388() {
        // Explicit close intent is not a retry: one return-from-takeover action
        // lawfully opens chat; the following ordinary genuine action closes it.
        const owner = Session.project;
        const originalWindow = window;
        const originalPopup = popup;
        const originalPage = window.assistantWorkflowPage;
        const action = toggle();
        if (action === "return-to-chat") {
            verify(Session.project === owner && window === originalWindow && popup === originalPopup
                && window.assistantWorkflowPage === originalPage,
                "I16/popup: return-to-chat cannot authorize closing a replacement owner/page");
            compare(Preferences.assistantShown, true,
                "I16/popup: genuine return retains the current open preference before ordinary close");
            compare(window.assistantManualTakeover, false,
                "I16/popup: next genuine close is ordinary, never a second takeover return");
            compare(toggle(), "ordinary-close",
                "I16/popup: explicit close uses the following original ordinary appbar action");
        } else {
            compare(action, "ordinary-close",
                "I16/popup: a close caller requires an actual ordinary close action");
        }
        compare(Preferences.assistantShown, false, "I16/popup: explicit genuine close clears the requested visibility");
        compare(popup.visible, false, "I16/popup: explicit genuine close leaves actual popup fully closed");
    }
    function pointerObservation(stage, control, requested) {
        const center = control.mapToItem(window.contentItem, control.width / 2, control.height / 2);
        const path = [];
        let parent = window.contentItem;
        let point = center;
        for (let depth = 0; parent && depth < 32; ++depth) {
            const hit = parent.childAt(point.x, point.y);
            if (!hit) break;
            path.push({name: hit.objectName, type: String(hit), visible: hit.visible,
                enabled: hit.enabled, z: hit.z, geometry: rect(hit)});
            point = hit.mapFromItem(parent, point.x, point.y);
            parent = hit;
        }
        const popups = Probe.objectsWithProperty(window, "closePolicy");
        const visibleScopes = [];
        for(let i=0;i<popups.length;++i) {
            const candidate = popups[i];
            if(!candidate.visible)continue;
            visibleScopes.push({type: String(candidate), name: candidate.objectName,
                parent: candidate.parent ? candidate.parent.objectName : null,
                opened: candidate.opened, modal: candidate.modal, focus: candidate.focus,
                closePolicy: candidate.closePolicy,
                popupWidth: candidate.width, popupHeight: candidate.height,
                leftPadding: candidate.leftPadding, rightPadding: candidate.rightPadding,
                topPadding: candidate.topPadding, bottomPadding: candidate.bottomPadding,
                contentRect: candidate.contentItem ? rect(candidate.contentItem) : null,
                actualPopupItemRect: candidate.contentItem && candidate.contentItem.parent
                    ? rect(candidate.contentItem.parent) : null,
                actualPopupItemWidth: candidate.contentItem && candidate.contentItem.parent
                    ? candidate.contentItem.parent.width : null,
                actualPopupItemHeight: candidate.contentItem && candidate.contentItem.parent
                    ? candidate.contentItem.parent.height : null});
        }
        console.log("APPBAR_POINTER", stage, JSON.stringify({
            requested: requested, shown: Preferences.assistantShown, popupVisible: popup.visible,
            popupOpened: popup.opened, page: window.appBarCentralTabs.currentIndex,
            windowActive: window.active, windowVisible: window.visible,
            buttonVisible: control.visible, buttonEnabled: control.enabled,
            buttonFocus: control.activeFocus, buttonDown: control.down,
            buttonHovered: control.hovered, buttonRect: rect(control),
            clickPoint: [center.x, center.y], visualHitPath: path, visiblePopupScopes: visibleScopes
        }));
        // childAt reports the actual visual stacking path, not a claim about
        // event acceptance by a handler or passive decorative item.
    }
    function scopeObservation(stage) {
        const button = item("assistant.toggle");
        const parent = popup.parent;
        const host = window.activeAssistantHost;
        const focus = window.activeFocusItem;
        console.log("POPUP_SCOPE", stage, JSON.stringify({
            shown: Preferences.assistantShown,
            visible: popup.visible,
            opened: popup.opened,
            page: window.appBarCentralTabs.currentIndex,
            projectPresent: Session.project !== null,
            parentName: parent ? parent.objectName : null,
            parentVisible: parent ? parent.visible : null,
            parentEnabled: parent ? parent.enabled : null,
            parentRect: parent ? rect(parent) : null,
            hostName: host ? host.objectName : null,
            parentIsHost: parent === host,
            windowActive: window.active,
            focusName: focus ? focus.objectName : null,
            focusClass: focus ? String(focus) : null,
            buttonFocus: button.activeFocus,
            buttonDown: button.down,
            buttonEnabled: button.enabled,
            buttonVisible: button.visible
        }));
    }
    function capture(stem) {
        scopeObservation("capture-" + stem);
        // QtTest's actual framebuffer adapter supports the C++-created window root.
        // Item.grabToImage requires a QML engine on that root; this root has none.
        const image = grabImage(window.contentItem);
        verify(image.width > 0 && image.height > 0, "I16/popup: actual full-window framebuffer has nonempty dimensions");
        // The documented QtTest save method throws on failure; it returns no bool.
        image.save(stem + ".png");
        console.log("POPUP_CAPTURE", stem, image.width, image.height);
    }
    function eligibleProject() {
        if (Session.project === null)
            verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "I16/popup SETUP: real original project supplies an eligible workflow");
        const tab = item("appBar.tab.project");
        verify(tab.visible && tab.enabled, "I16/popup SETUP: genuine Project navigation is eligible");
        mouseClick(tab);
        tryCompare(window.appBarCentralTabs, "currentIndex", AppState.Page.Project, 2000, "I16/popup: real Project action activates the workflow");
        rendered();
    }
    function init() {
        eligibleProject();
        compare(Preferences.assistantShown, false, "I16/popup: each isolated row starts without an inherited open request");
        compare(popup.visible, false, "I16/popup: each isolated row starts with the actual popup closed");
    }
    function initTestCase() {
        oldSide = Preferences.sideBarSide;
        oldTheme = EaStyle.Colors.theme;
        oldToolTips = Preferences.toolTips;
        window = application.createObject(null);
        verify(window !== null, "I16/popup: production Main instantiates in the normal native runner");
        // QtTest keys use the active/focus window; pointer events use their item's window.
        // Establish original Main ONCE, before any account/work or later deliberate app switch.
        window.requestActivate();
        tryCompare(window, "active", true, 2000,
            "GUI497 SETUP: the separately created real Main is initially active for original native keyboard routing");
        rendered();
        popup = item("assistant.popup");
        assistant = Session.assistant;
        compare(popup.visible, false, "I16/popup: a fresh session starts with chat closed");
        compare(assistant.connected, false, "I12/popup: native availability does not imply provider connection");
    }
    function cleanup() {
        Preferences.dialogShown = false;
        // Home deliberately disables the opener but retains requested visibility.
        // Return through genuine workflow navigation before clearing that request.
        eligibleProject();
        if (popup && Preferences.assistantShown)
            closeAssistant388();
    }
    function cleanupTestCase() {
        eligibleProject();
        if (Preferences.assistantShown)
            closeAssistant388();
        Session.closeProject();
        Preferences.sideBarSide = oldSide;
        EaStyle.Colors.theme = oldTheme;
        Preferences.toolTips = oldToolTips;
        const originalMain490 = lifetime313(window);
        console.log("GUI490_MAIN_LIFETIME", JSON.stringify({phase: "before-original-destroy",
            identity: identity313(originalMain490), alive: alive313(originalMain490)}));
        window.destroy();
        try {
            tryVerify(() => !alive313(originalMain490), 2000,
                "GUI490: original Main QObject is actually deleted before the QML engine exits");
        } finally {
            console.log("GUI490_MAIN_LIFETIME", JSON.stringify({phase: "after-original-destroy-observation",
                identity: identity313(originalMain490), alive: alive313(originalMain490)}));
        }
    }
    function test_home_appbar_only_and_no_auto_dismiss() {
        const main = item("workflow.project.mainContent");
        const before = rect(main);
        const project = Session.project;
        const messages = assistant.messages;
        window.contentItem.forceActiveFocus();
        keyClick(Qt.Key_A, Qt.ControlModifier | Qt.ShiftModifier);
        compare(popup.visible, false, "I16/popup: retired global shortcut cannot open chat");
        const button = item("assistant.toggle");
        button.forceActiveFocus();
        keyClick(Qt.Key_Space);
        tryCompare(popup, "opened", true, 2000, "I16/popup: actual eligible appbar keyboard activation opens chat");
        compare(popup.modal, false, "I16/popup: sidebar popup does not block the whole window");
        compare(popup.dim, false, "I16/popup: sidebar popup does not dim scientific content");
        compare(popup.closePolicy, Popup.NoAutoClose, "I16/popup: outside and Escape are not dismissal routes");
        sameRect(rect(popup.contentItem), rect(item("workflow.project.sidebarHost")));
        sameRect(rect(main), before);
        keyClick(Qt.Key_Escape);
        compare(popup.visible, true, "I16/popup: Escape leaves eligible workflow chat open");
        const point = main.mapToItem(window.contentItem, main.width / 2, main.height / 2);
        mouseClick(window.contentItem, point.x, point.y);
        compare(popup.visible, true, "I16/popup: genuine outside click leaves eligible workflow chat open");
        gui392_signIn();
        const editor = item("assistant.composer");
        editor.insert(0, "Original Home-hidden draft");
        editor.select(2, 9);
        const draft = editor.text;
        const selection = [editor.selectionStart, editor.selectionEnd];
        verify(findChild(window, "assistant.close") === null, "I16/popup: no separate close control remains");
        Preferences.dialogShown = true;
        rendered();
        verify(findChild(window, "preferences.assistantShown") === null, "I16/popup: Preferences has no alternate chat opener");
        Preferences.dialogShown = false;
        mouseClick(item("appBar.tab.home"));
        tryCompare(window.appBarCentralTabs, "currentIndex", AppState.Page.Home, 2000, "HOME: actual appbar navigates to Home");
        tryCompare(popup, "visible", false, 2000, "HOME: Assistant fully slides out on Home");
        rendered();
        compare(button.enabled, false, "HOME: appbar Assistant is deliberately disabled on Home");
        compare(Preferences.assistantShown, true, "HOME: Home keeps the actual stored open request");
        verify(!editor.activeFocus, "HOME: hidden chat does not retain input focus");
        mouseClick(button);
        keyClick(Qt.Key_A, Qt.ControlModifier | Qt.ShiftModifier);
        compare(popup.visible, false, "HOME: disabled appbar/retired shortcut cannot reopen chat");
        compare(Session.project, project, "HOME: hiding chat does not replace the real project");
        compare(assistant.messages, messages, "HOME: hiding chat retains the actual conversation owner");
        eligibleProject();
        tryCompare(popup, "opened", true, 2000, "HOME: eligible return restores the stored request");
        compare(button.enabled, true, "HOME: eligible workflow restores the real appbar action");
        sameRect(rect(popup.contentItem), rect(item("workflow.project.sidebarHost")));
        sameRect(rect(main), before);
        compare(editor.text, draft, "HOME: unsent original survives hidden Home and return");
        compare(editor.selectionStart, selection[0], "HOME: original selection start survives");
        compare(editor.selectionEnd, selection[1], "HOME: original selection end survives");
        capture("assistant-popup-returned-from-home");
        closeAssistant388();
        editor.clear();
    }
    function focusWithinManual(manual) {
        for (let current = window.activeFocusItem; current; current = current.parent)
            if (current === manual) return true;
        return false;
    }
    function coveredManualInput(manual, target) {
        verify(target !== null && target.visible && typeof target.checked === "boolean" && !target.checked,
            "I16/popup SETUP: original covered target is a genuine unchecked visible manual tab");
        const point = target.mapToItem(window.contentItem, target.width / 2, target.height / 2);
        const connection = item("assistant.connection");
        if (connection.visible) {
            const accountRect = rect(connection);
            verify(!(point.x >= accountRect[0] && point.x <= accountRect[0] + accountRect[2]
                && point.y >= accountRect[1] && point.y <= accountRect[1] + accountRect[3]),
                "I12/popup SETUP: covered manual click never targets the genuine Sign in action");
        }
        mouseClick(window.contentItem, point.x, point.y);
        compare(target.checked, false, "I16/popup: covered real pointer input cannot change the manual tab");
        verify(!focusWithinManual(manual), "I16/popup: covered pointer cannot acquire manual focus");
        for (const backwards of [false, true]) {
            for (let step = 0; step < 32; ++step) {
                keyClick(Qt.Key_Tab, backwards ? Qt.ShiftModifier : Qt.NoModifier);
                verify(!focusWithinManual(manual), "I16/popup: actual Tab/Backtab traversal excludes covered manual input");
            }
        }
        compare(target.checked, false, "I16/popup: keyboard traversal never activates the covered manual tab");
    }
    function test_workflow_same_sidebar_and_live_state_data() {
        return [
            {
                tag: "left-light",
                side: "Left",
                dark: false
            },
            {
                tag: "right-dark",
                side: "Right",
                dark: true
            }
        ];
    }
    function test_workflow_same_sidebar_and_live_state(data) {
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "I4/popup: real Session opens existing independent project fixture");
        Preferences.sideBarSide = data.side;
        EaStyle.Colors.theme = data.dark ? EaStyle.Colors.DarkTheme : EaStyle.Colors.LightTheme;
        window.appBarCentralTabs.currentIndex = 1;
        rendered();
        const main = item("workflow.project.mainContent");
        const host = item("workflow.project.sidebarHost");
        const manual = item("workflow.project.manualSidebar");
        const before = rect(main);
        const sidebarBefore = rect(host);
        const project = Session.project;
        const tab = findChild(manual, "sideBar.tab.extras");
        verify(tab !== null, "I16/popup: tab belongs to the active real manual sidebar");
        verify(tab.enabled, "I16/popup: preserved manual tab is genuinely available");
        mouseClick(tab);
        const tabIndex = manual.currentIndex;
        compare(tab.checked, true, "I16/popup: manual tab state is established by real input");
        const coveredTab = findChild(manual, "sideBar.tab.basic");
        verify(coveredTab !== null && !coveredTab.checked, "I16/popup SETUP: actual opposite tab can expose click-through");
        const painted = {visible: manual.visible, opacity: manual.opacity};
        toggle();
        compare(popup.visible, true, "I16/popup: existing toolbar opens workflow overlay");
        compare(popup.assistant, assistant, "I16/popup: same real Session VM owns the single popup");
        sameRect(rect(popup.contentItem), sidebarBefore);
        sameRect(rect(main), before);
        compare(manual.visible, painted.visible, "I16/popup: covered manual stays painted rather than disappearing");
        compare(manual.opacity, painted.opacity, "I16/popup: covering never fades the ordinary manual colors");
        coveredManualInput(manual, coveredTab);
        compare(window.appBarCentralTabs.currentIndex, 1, "I16/popup: covered input never navigates the workflow");
        gui392_signIn();
        const composer = item("assistant.composer");
        composer.forceActiveFocus();
        composer.insert(0, "PbSO4 — unsent\ncell 5.43");
        composer.select(2, 8);
        const draft = composer.text;
        const start = composer.selectionStart;
        const end = composer.selectionEnd;
        const messages = assistant.messages;
        capture("assistant-popup-" + data.tag);
        closeAssistant388();
        compare(manual.visible, painted.visible, "I16/popup: original painted manual survives hiding");
        compare(manual.opacity, painted.opacity, "I16/popup: hiding preserves the ordinary manual opacity");
        compare(manual.currentIndex, tabIndex, "I16/popup: actual manual tab survives covering");
        mouseClick(coveredTab);
        tryCompare(coveredTab, "checked", true, 500, "I16/popup: the same real manual action works after full close");
        mouseClick(tab);
        tryCompare(tab, "checked", true, 500, "I16/popup: normal manual input restores its original selected tab");
        sameRect(rect(main), before);
        toggle();
        compare(item("assistant.popup"), popup, "I16/popup: hide/show retains the same popup instance");
        compare(item("assistant.composer"), composer, "I16/popup: hide/show retains the actual draft editor");
        compare(composer.text, draft, "I16/popup: unsent multiline Unicode draft survives");
        compare(composer.selectionStart, start, "I16/popup: draft selection start survives");
        compare(composer.selectionEnd, end, "I16/popup: draft selection end survives");
        compare(assistant.messages, messages, "I16/popup: hiding does not replace the conversation model");
        compare(Session.project, project, "I16/popup: toggling does not replace the open project");
        sameRect(rect(main), before);
        closeAssistant388();
        composer.clear();
    }
    function test_navigation_keeps_visible_popup_fixed_data() {
        return [{tag: "left", side: "Left"}, {tag: "right", side: "Right"}];
    }
    function test_navigation_keeps_visible_popup_fixed(data) {
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "NAV1 SETUP: original complete project enables genuine workflow navigation");
        Preferences.sideBarSide = data.side;
        const analysis = item("appBar.tab.analysis");
        verify(analysis.visible && analysis.enabled, "NAV1 SETUP: actual Analysis tab is available without forcing eligibility");
        mouseClick(analysis);
        tryCompare(window.appBarCentralTabs, "currentIndex", AppState.Page.Analysis, 2000, "NAV1: genuine appbar action reaches Analysis");
        rendered();
        const button = item("assistant.toggle");
        const closedIcon = button.fontIcon;
        toggle();
        gui392_signIn();
        verify(/manual|sidebar|controls/i.test(button.Accessible.name), "NAV1: shown-state appbar action truthfully names return to manual controls");
        verify(button.fontIcon !== closedIcon, "NAV1: shown-state real appbar icon distinguishes returning from opening Assistant");
        Preferences.toolTips = true;
        const tooltip = button.ToolTip.text;
        verify(/manual|sidebar|controls/i.test(tooltip), "NAV1: shown-state tooltip describes the actual sidebar-return action");
        const candidates = Probe.objectsWithProperty(button, "closePolicy");
        const ownedToolTips = [];
        for(let i=0;i<candidates.length;++i)
            if(candidates[i] instanceof EaElements.ToolTip)ownedToolTips.push(candidates[i]);
        compare(ownedToolTips.length, 1, "NAV1 SETUP: actual Ea ToolButton owns one painted custom tooltip");
        const toolTipPopup = ownedToolTips[0];
        function hoverObservation(stage) {
            const handlers = Probe.objectsWithProperty(button, "hovered");
            const realHandlers = [];
            for(let i=0;i<handlers.length;++i)
                if(String(handlers[i]).includes("HoverHandler"))realHandlers.push({
                    type: String(handlers[i]), hovered: handlers[i].hovered,
                    parent: handlers[i].parent ? String(handlers[i].parent) : null});
            console.info("NAV_HOVER", stage, JSON.stringify({
                hoverEnabled: button.hoverEnabled, hovered: button.hovered,
                showToolTips: EaGlobals.Vars.showToolTips, toolTipsPreference: Preferences.toolTips,
                buttonRect: rect(button), buttonVisible: button.visible, buttonEnabled: button.enabled,
                tooltipVisible: toolTipPopup.visible, tooltipOpened: toolTipPopup.opened,
                tooltipText: toolTipPopup.text,
                contentText: toolTipPopup.contentItem ? Ui.text(toolTipPopup.contentItem) : null,
                contentRendered: toolTipPopup.contentItem ? Ui.rendered(toolTipPopup.contentItem) : false,
                contentRect: toolTipPopup.contentItem ? rect(toolTipPopup.contentItem) : null,
                outerRect: toolTipPopup.contentItem && toolTipPopup.contentItem.parent
                    ? rect(toolTipPopup.contentItem.parent) : null,
                hoverHandlers: realHandlers}));
        }
        hoverObservation("before-away");
        mouseMove(window.contentItem, window.width / 2, window.height - 2);
        hoverObservation("after-away");
        mouseMove(button, button.width / 2, button.height / 2);
        hoverObservation("after-return");
        try {
            tryVerify(() => toolTipPopup.visible && toolTipPopup.contentItem !== null
                && Ui.rendered(toolTipPopup.contentItem) && Ui.text(toolTipPopup.contentItem).includes(tooltip),
                2000, "NAV1: actual hovered tooltip popup renders its action text, not merely attached metadata");
        } finally {
            hoverObservation("after-hover-wait");
        }
        const editor = item("assistant.composer");
        editor.insert(0, "Original navigation draft");
        editor.select(2, 9);
        const draft = editor.text;
        const selection = [editor.selectionStart, editor.selectionEnd];
        const project = Session.project;
        const messages = assistant.messages;
        const viewport = window.contentArea[AppState.Page.Project].SwipeView.view.contentItem;
        verify(viewport !== null && typeof viewport.contentX === "number", "NAV1 SETUP: actual outer workflow viewport exposes rendered navigation progress");
        for (const destination of [{name: "project", index: AppState.Page.Project}, {name: "analysis", index: AppState.Page.Analysis}]) {
            const before = rect(popup.contentItem);
            const firstX = viewport.contentX;
            const target = item("appBar.tab." + destination.name);
            verify(target.visible && target.enabled, "NAV1 SETUP: real destination appbar control remains eligible");
            mouseClick(target);
            const samples = [];
            for (let frame = 0; frame < 12; ++frame) {
                window.update();
                verify(waitForRendering(window.contentItem, 500), "NAV1: global geometry samples follow actual rendered frames");
                samples.push({x: viewport.contentX, moving: viewport.moving, rectangle: rect(popup.contentItem)});
            }
            tryCompare(window.appBarCentralTabs, "currentIndex", destination.index, 2000, "NAV1: real navigation reaches the requested destination");
            rendered();
            const lastX = viewport.contentX;
            const positions = [];
            for (const sample of samples)
                if (sample.x > Math.min(firstX, lastX) + 0.5 && sample.x < Math.max(firstX, lastX) - 0.5 && !positions.some(value => Math.abs(value - sample.x) < 0.5))
                    positions.push(sample.x);
            console.info("NAVIGATION_GEOMETRY", data.side, destination.name, JSON.stringify({before: before, firstX: firstX, lastX: lastX, samples: samples}));
            verify(positions.length >= 2, "NAV1 SETUP: genuine workflow animation visits distinct intermediate rendered positions, not immediate endpoints");
            for (const sample of samples)
                sameRect(sample.rectangle, before);
            sameRect(rect(popup.contentItem), before);
            sameRect(rect(popup.contentItem), rect(item("workflow." + destination.name + ".sidebarHost")));
            compare(Session.project, project, "NAV1: navigation preserves the real project owner");
            compare(assistant.messages, messages, "NAV1: navigation preserves the actual retained conversation model");
            compare(editor.text, draft, "NAV1: navigation preserves the actual unsent draft");
            compare(editor.selectionStart, selection[0], "NAV1: navigation preserves draft selection start");
            compare(editor.selectionEnd, selection[1], "NAV1: navigation preserves draft selection end");
        }
        button.forceActiveFocus();
        keyClick(Qt.Key_Space);
        tryCompare(popup, "visible", false, 2000, "NAV1: normal keyboard activation of the real return button reveals manual controls");
        rendered();
        verify(/assistant/i.test(button.Accessible.name), "NAV1: closed-state action truthfully offers Assistant again");
        editor.clear();
    }
    // POP1: actual traversal must escape Qt's Popup tab fence to the sole hide button.
    function test_keyboard_can_return_to_appbar_data() {
        return [
            {
                tag: "tab",
                backwards: false
            },
            {
                tag: "backtab",
                backwards: true
            }
        ];
    }
    function keyboardObservation(stage, button) {
        const focus = window.activeFocusItem;
        console.log("KEYBOARD_OBSERVATION", stage, JSON.stringify({
            windowActive: window.active,
            windowVisible: window.visible,
            popupVisible: popup.visible,
            shown: Preferences.assistantShown,
            focusName: focus ? focus.objectName : null,
            focusClass: focus ? String(focus) : null,
            buttonFocus: button.activeFocus,
            buttonVisible: button.visible,
            buttonEnabled: button.enabled,
            buttonDown: button.down
        }));
    }
    function test_keyboard_can_return_to_appbar(data) {
        if (popup.visible)
            closeAssistant388();
        const button = item("assistant.toggle");
        keyboardObservation("before-focus-" + data.tag, button);
        button.forceActiveFocus();
        keyboardObservation("after-focus-" + data.tag, button);
        keyClick(Qt.Key_Space);
        keyboardObservation("after-space-" + data.tag, button);
        tryCompare(popup, "visible", true, 500, "I16/POP1: real keyboard appbar activation opens chat");
        gui392_signIn();
        Ui.click(this, Probe, window, "assistant.composer");
        const composer = item("assistant.composer");
        tryVerify(() => composer.activeFocus, 500, "I16/POP1: traversal starts from the actual focused composer");
        const visited = [];
        // Finite fixture traversal bound, not a production resource or focus-policy limit.
        for (let i = 0; i < 32 && !button.activeFocus; ++i) {
            keyClick(Qt.Key_Tab, data.backwards ? Qt.ShiftModifier : Qt.NoModifier);
            const focus = window.activeFocusItem;
            if (focus && visited.indexOf(focus) < 0)
                visited.push(focus);
        }
        verify(visited.length > 0, "I16/POP1: real key events traverse actual focusable objects");
        verify(button.activeFocus, "I16/POP1: Tab and Backtab can reach the sole external appbar hide control");
        keyClick(Qt.Key_Space);
        tryCompare(popup, "visible", false, 500, "I16/POP1: keyboard activation hides through the same appbar button");
    }
    function test_focus_restore_uses_current_scope_data() {
        return [
            {
                tag: "page",
                replacement: false
            },
            {
                tag: "project-replacement",
                replacement: true
            }
        ];
    }
    function test_focus_restore_uses_current_scope(data) {
        if (popup.visible)
            closeAssistant388();
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "I16/POP2: real project establishes a live workflow scope");
        window.appBarCentralTabs.currentIndex = 1;
        rendered();
        const oldField = item("project.name");
        const oldFieldLife313 = lifetime313(oldField);
        mouseClick(oldField);
        verify(oldField.activeFocus, "I16/POP2: real manual field owns focus before pointer opening");
        toggle();
        verify(popup.visible, "I16/POP2: pointer opens the actual popup without changing widget focus policy");
        scopeObservation("scope-before-replacement-" + data.tag);
        if (data.replacement) {
            Session.closeProject();
            scopeObservation("scope-after-close");
            verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "I16/POP2: real replacement creates the next project scope");
            scopeObservation("scope-after-open");
        }
        const tab = item("appBar.tab.home");
        scopeObservation("scope-before-home-" + data.tag);
        mouseClick(tab);
        scopeObservation("scope-after-home-" + data.tag);
        tryCompare(window.appBarCentralTabs, "currentIndex", 0, 500, "I16/POP2: real outside navigation changes the current page while chat is open");
        tryCompare(popup, "visible", false, 2000, "I16/POP2: Home retires visible chat under the latest owner rule");
        compare(item("assistant.toggle").enabled, false, "I16/POP2: Home disables chat while preserving its request");
        compare(Preferences.assistantShown, true, "I16/POP2: Home preserves the intentional open request");
        tryVerify(() => {
            const current = window.activeFocusItem;
            return current !== null && Ui.rendered(current);
        }, 500, "I16/POP2: deferred close restores only a genuinely rendered current target");
        verify(!alive313(oldFieldLife313) || !oldField.activeFocus, "I16/POP2: retained or replaced offscreen field cannot receive restored focus");
        const current = window.activeFocusItem;
        keyClick(Qt.Key_Tab);
        verify(window.activeFocusItem !== oldField, "I16/POP2: following real keyboard traversal stays outside the retired field");
        verify(current !== null, "I16/POP2: close retains a usable visible keyboard target");
    }
    // Owner decision26630 removes Home chat coverage entirely: no Home strip
    // may cover a target. Old POP3 Home-under-popup geometry cases are superseded;
    // genuine workflow manual exclusion/current-scope focus cases remain above.
    function test_connection_header_reachable_by_real_keyboard_data() {
        return [
            {
                tag: "tab",
                backwards: false
            },
            {
                tag: "backtab",
                backwards: true
            }
        ];
    }
    function test_connection_header_reachable_by_real_keyboard(data) {
        eligibleProject();
        compare(assistant.connected, false, "I12/HDR1: this real native owner is genuinely disconnected, not a fabricated account state");
        toggle();
        const button = item("assistant.toggle");
        const editor = item("assistant.composer");
        verify(!Ui.rendered(editor), "GUI392/HDR1: signed-out composer is unavailable before genuine keyboard Sign in traversal");
        // Establish keyboard-only entry through the existing actual opener, without forceFocus.
        for (let step = 0; step < 32 && !button.activeFocus; ++step)
            keyClick(Qt.Key_Tab, Qt.ShiftModifier);
        verify(button.activeFocus, "I16/HDR1: genuine reverse traversal reaches the sole appbar control");
        keyClick(Qt.Key_Space);
        tryCompare(popup, "visible", false, 2000, "I16/HDR1: actual keyboard opener also closes the popup");
        keyClick(Qt.Key_Space);
        tryCompare(popup, "opened", true, 2000, "I16/HDR1: genuine appbar keyboard activation completes actual popup opening");
        const connection = item("assistant.connection");
        verify(connection.visible && connection.enabled, "I12/HDR1: actual Sign in is available to a disconnected user");
        const visited = [];
        for (let step = 0; step < 32 && !connection.activeFocus; ++step) {
            keyClick(Qt.Key_Tab, data.backwards ? Qt.ShiftModifier : Qt.NoModifier);
            const focus = window.activeFocusItem;
            if (focus && visited.indexOf(focus.objectName) < 0)
                visited.push(focus.objectName);
        }
        console.log("HEADER_KEYBOARD", data.tag, JSON.stringify(visited));
        verify(connection.activeFocus, "I12/I16/HDR1: normal forward and reverse keyboard routes reach the genuine Sign in action");
        compare(assistant.connected, false, "I12/HDR1: keyboard reachability does not fabricate authentication");
    }
    function test_project_close_during_actual_enter_preserves_requested_chat() {
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "I4/slide: actual project supplies the entering workflow owner");
        window.appBarCentralTabs.currentIndex = 1;
        rendered();
        mouseClick(item("assistant.toggle"));
        compare(Preferences.assistantShown, true, "I16/slide: real appbar establishes the open request before retirement");
        verify(popup.visible && !popup.opened, "I16/slide: retirement genuinely interrupts actual enter rather than a settled or hidden popup");
        scopeObservation("enter-before-project-close");
        Session.closeProject();
        mouseClick(item("appBar.tab.home"));
        rendered();
        scopeObservation("enter-after-project-close-render");
        compare(Preferences.assistantShown, true, "I16/slide: project retirement does not cancel the intentional open request");
        tryCompare(popup, "visible", false, 2000, "I16/slide: Home fully hides an interrupted entering chat");
        compare(item("assistant.toggle").enabled, false, "I16/slide: closed-project Home cannot reopen Assistant");
        compare(Session.project, null, "I4/slide: hiding chat never recreates the retired project");
        verify(!item("assistant.composer").activeFocus, "I16/slide: retired hidden scope cannot keep composer input focus");
        eligibleProject();
        tryCompare(popup, "opened", true, 2000, "I16/slide: ordinary eligible return restores requested chat after retirement");
        compare(popup.parent, item("workflow.project.sidebarHost"), "I16/slide: recovered chat uses the actual new current workflow host");
        sameRect(rect(popup.contentItem), rect(item("workflow.project.sidebarHost")));
    }
    function test_rapid_slide_keeps_actual_plot_and_input_scope() {
        if (popup.visible)
            closeAssistant388();
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "I16/slide: actual independent project anchors the live sidebar/plot");
        Preferences.sideBarSide = "Right";
        window.appBarCentralTabs.currentIndex = 1;
        rendered();
        toggle(); gui392_signIn(); closeAssistant388();
        const main = item("workflow.project.mainContent");
        const host = item("workflow.project.sidebarHost");
        const manual = item("workflow.project.manualSidebar");
        const plotBefore = rect(main);
        const hostBefore = rect(host);
        const projectBefore = Session.project;
        const cancelBefore = assistant.canCancel;
        const manualPaint = {visible: manual.visible, opacity: manual.opacity};
        const basicBefore = findChild(manual, "sideBar.tab.basic");
        verify(basicBefore !== null && typeof basicBefore.checked === "boolean", "I16/slide SETUP: real manual tab has checked state");
        const coveredTab = findChild(manual, basicBefore.checked ? "sideBar.tab.extras" : "sideBar.tab.basic");
        const button = item("assistant.toggle");
        // Raw appbar input deliberately does not wait for the new transition to finish.
        mouseClick(button);
        const editor = item("assistant.composer");
        const positions = [];
        let visibleExit = false;
        function sample() {
            window.update();
            verify(waitForRendering(window.contentItem, 500), "I16/slide: observations follow an actual rendered frame");
            sameRect(rect(main), plotBefore);
            sameRect(rect(host), hostBefore);
            if (popup.visible) {
                compare(manual.visible, manualPaint.visible, "I16/slide: entering/exiting preserves the painted manual subtree");
                compare(manual.opacity, manualPaint.opacity, "I16/slide: every observed transition frame preserves manual opacity");
                if (!Preferences.assistantShown)
                    visibleExit = true;
            }
            if (popup.visible && Ui.rendered(editor)) {
                const position = rect(editor);
                if (!positions.some(previous => Math.abs(previous[0] - position[0]) < 0.5 && Math.abs(previous[1] - position[1]) < 0.5)) {
                    positions.push(position);
                    if (positions.length <= 3)
                        capture("assistant-slide-frame-" + positions.length);
                }
            }
        }
        // Finite renderer samples are a fixture bound, not the producer's duration/transition state.
        for (let frame = 0; frame < 12; ++frame)
            sample();
        verify(positions.length >= 3, "I16/slide: actual rendered content visits distinct intermediate moving positions, not an instantaneous/fade-only toggle");
        tryCompare(popup, "opened", true, 2000, "I16/slide: after real moving frames, enter settles before covered input proof");
        coveredManualInput(manual, coveredTab);
        editor.insert(0, "Unsent slide — Å cell 5.43");
        editor.select(2, 9);
        const draft = editor.text;
        const selectedStart = editor.selectionStart;
        const selectedEnd = editor.selectionEnd;
        for (let action = 0; action < 3; ++action) {
            mouseClick(button);
            sample();
        }
        verify(visibleExit, "I16/slide: interrupted/reversed actions genuinely exercise a still-visible exit frame");
        tryCompare(popup, "visible", false, 2000, "I16/slide: final hide fully exits before manual controls become actionable");
        compare(manual.visible, manualPaint.visible, "I16/slide: fully exited popup retains the actual painted manual");
        compare(manual.opacity, manualPaint.opacity, "I16/slide: fully exited popup preserves manual opacity");
        sameRect(rect(main), plotBefore);
        sameRect(rect(host), hostBefore);
        compare(editor.text, draft, "I16/slide: reversing/hiding retains the actual unsent draft");
        compare(Session.project, projectBefore, "I16/slide: transitions never replace the real project");
        compare(assistant.canCancel, cancelBefore, "I16/slide: visibility alone does not alter the observed operation state");
        toggle();
        compare(editor.selectionStart, selectedStart, "I16/slide: interrupted show/hide restores actual selection start");
        compare(editor.selectionEnd, selectedEnd, "I16/slide: interrupted show/hide restores actual selection end");
        closeAssistant388();
        // Continue is intentionally hidden by the existing owner rule. Exercise a
        // genuine visible manual tab instead of requiring a retired action to appear.
        const basicTab = findChild(manual, "sideBar.tab.basic");
        verify(basicTab !== null && typeof basicTab.checked === "boolean", "I16/slide: actual Qt TabButton exposes the checked observer before choosing its opposite");
        const manualTab = findChild(manual, basicTab.checked ? "sideBar.tab.extras" : "sideBar.tab.basic");
        verify(manualTab !== null && typeof manualTab.checked === "boolean" && !manualTab.checked, "I16/slide: opposite real tab is initially unchecked before physical input");
        verify(manualTab !== null && manualTab.visible && manualTab.enabled, "I16/slide: genuine visible manual tab is restored after full exit");
        mouseClick(manualTab);
        tryCompare(manualTab, "checked", true, 500, "I16/slide: actual manual action works after exit without an invisible input blocker");
        editor.clear();
    }
    // Real retained transcript, no fixture row/model mutation or direct page handler call.
    function report187_state(stage) {
        console.log("REPORT187_STATE", stage, JSON.stringify({
            connected: assistant.connected, state: assistant.state, canCancel: assistant.canCancel,
            contextConsentRequired: assistant.contextConsentRequired, lastError: assistant.lastError,
            pendingQuestion: assistant.pendingQuestion, pendingPlan: assistant.pendingPlan,
            projectPresent: Session.project !== null,
            calculating: Session.project ? Session.project.calculating : null,
            models: assistant.models.count,
            focusedControl: window.activeFocusItem ? window.activeFocusItem.objectName : null,
            rows: Probe.rows(assistant.messages).map(row => ({id: row.id, kind: row.kind,
                status: row.status, text: row.text}))
        }));
    }
    function report187_ready(stage, approved) {
        try {
            tryVerify(() => assistant.connected && assistant.state === "idle" && !assistant.canCancel
                && (!approved || !assistant.contextConsentRequired), 2000,
                "REPORT171 SETUP: actual current thread is idle and disclosed before original Send");
        } finally { report187_state(stage); }
    }
    function test_report171_chat_anchor_uses_existing_current_report_page_data() {
        return [{tag: "current"}, {tag: "replacement"}, {tag: "missing"},
            {tag: "disabled"}, {tag: "protected-other"}];
    }
    function test_report171_chat_anchor_uses_existing_current_report_page(data) {
        const original = "[Open Report page](edi:report)\n\n[Unknown protected report](not-a-report:original)";
        toggle();
        // Ordinary public bootstrap uses the deliberate absolute owned peer;
        // it is not proof of physical Sign in delivery or provider entitlement.
        assistant.signIn();
        tryCompare(assistant, "connected", true, 2000, "REPORT171 SETUP: genuine managed account/catalog bootstrap");
        verify(assistant.models.count > 0, "REPORT171 SETUP: real catalog is admitted");
        report187_ready("before-approval-" + data.tag, false);
        if (assistant.contextConsentRequired) assistant.signIn();
        report187_ready("before-send-" + data.tag, true);
        verify(!assistant.contextConsentRequired, "REPORT171 SETUP: actual current disclosure is approved");
        const draft = "Original Main report navigation " + data.tag;
        const previousIds = new Set(Probe.rows(assistant.messages).map(row => row.id));
        assistant.send(draft);
        try {
        tryVerify(() => Probe.rows(assistant.messages).some(row => !previousIds.has(row.id) && row.kind === "assistant"
            && row.status === "completed" && row.text === original), 2000,
            "REPORT171 SETUP: genuine original completed transcript row exists before pointer input");
        } finally { report187_state("after-row-wait-" + data.tag); }
        const retained = Probe.rows(assistant.messages).find(row => !previousIds.has(row.id) && row.kind === "assistant"
            && row.status === "completed" && row.text === original);
        verify(retained.id.length > 0, "REPORT171: actual immutable source row has a real identity");
        compare(Probe.rows(assistant.messages).filter(row => !previousIds.has(row.id) && row.kind === "user" && row.text === draft).length,
            1, "REPORT171: ordinary original input is admitted once");
        if (data.tag === "replacement") {
            verify(Session.openProject(Probe.repoUrl("tests/fixtures/report_options/pairs")),
                "REPORT171 SETUP: genuine different current project replaces original row owner");
        } else if (data.tag === "missing") {
            Session.closeProject();
        } else if (data.tag === "disabled") {
            Session.project.removeStructure(0);
            compare(Session.project.structures.count, 0, "REPORT171 SETUP: actual model removal disables Report");
        }
        // Home hides Assistant by policy; use the real eligible workflow action,
        // never force a page/enable property to make the anchor reachable.
        function observeMissingOpener(stage) {
            if (data.tag !== "missing") return;
            try {
                const opener = findChild(window, "assistant.toggle");
                const projectTab = findChild(window, "appBar.tab.project");
                console.log("REPORT193_OPENER", stage, JSON.stringify({
                    page: window.appBarCentralTabs.currentIndex,
                    requested: Preferences.assistantShown, shown: popup.shown,
                    visible: popup.visible, opened: popup.opened,
                    showingActions: assistant.showingActions,
                    manualTakeover: window.assistantManualTakeover,
                    popupParent: popup.parent ? popup.parent.objectName : null,
                    projectPresent: Session.project !== null, hasProject: Session.hasProject,
                    projectPageEnabled: AppState.projectPageEnabled,
                    workflowPagePresent: window.assistantWorkflowPage != null,
                    activeHostPresent: window.activeAssistantHost != null,
                    activeHostName: window.activeAssistantHost ? window.activeAssistantHost.objectName : null,
                    projectTab: projectTab ? {visible: projectTab.visible, enabled: projectTab.enabled} : null,
                    toggle: opener ? {visible: opener.visible, enabled: opener.enabled} : null,
                    connected: assistant.connected, state: assistant.state,
                    canCancel: assistant.canCancel, sessionLastError: Session.lastError
                }));
            } catch (error) { console.log("REPORT193_OPENER_DIAGNOSTIC_ERROR", stage, String(error)); }
        }
        observeMissingOpener("before-original-project-click");
        try {
            mouseClick(item("appBar.tab.project"));
            tryCompare(window.appBarCentralTabs, "currentIndex", AppState.Page.Project, 2000,
                "REPORT171 SETUP: genuine Project action exposes the retained chat");
            rendered();
            tryCompare(popup, "opened", true, 2000, "REPORT171 SETUP: retained Assistant is actually visible");
        } finally { observeMissingOpener("after-original-opener-wait"); }
        const current = Session.project;
        const history = JSON.stringify(Probe.rows(assistant.messages));
        const parameters = current ? JSON.stringify(Probe.rows(current.parameters)) : "";
        const row = Ui.itemsWithProperty(Ui.windowRoot(window), "rowId").filter(item => item.rowId === retained.id && item.assistant === assistant
            && typeof item.resetDetails === "function" && typeof item.copyTechnicalPayload === "function"
            && item.kind === "assistant" && item.status === "completed");
        compare(row.length, 1, "REPORT171: real production delegate belongs to the retained row");
        const bodies = Ui.itemsWithProperty(row[0], "readOnly").filter(item => item.visible
            && typeof item.linkAt === "function" && item.readOnly);
        compare(bodies.length, 1, "REPORT171: actual rendered message owns its real selectable anchor");
        const body = bodies[0];
        const label = data.tag === "protected-other" ? "Unknown protected report" : "Open Report page";
        const href = data.tag === "protected-other" ? "not-a-report:original" : "edi:report";
        const plain = body.getText(0, body.length);
        const start = plain.indexOf(label);
        verify(start >= 0, "REPORT171: original visible link label survives actual Markdown rendering");
        const bounds = body.positionToRectangle(start + 2);
        const x = bounds.x + Math.max(1, bounds.width / 2);
        const y = bounds.y + bounds.height / 2;
        compare(body.linkAt(x, y), href, "REPORT171: physical point belongs to the exact original URI");
        mouseMove(window.contentItem, 1, window.height - 1);
        mouseMove(body, x, y);
        tryCompare(body, "hoveredLink", href, 2000, "REPORT171: actual pointer enters the rendered anchor");
        verify(Probe.objectsWithProperty(row[0], "cursorShape").some(handler => handler.cursorShape === Qt.PointingHandCursor),
            "REPORT171: live production anchor offers its actual pointing-hand cursor role");
        const pageBefore = window.appBarCentralTabs.currentIndex;
        mouseClick(body, x, y);
        if (data.tag === "missing" || data.tag === "disabled") {
            verify(!AppState.reportPageEnabled, "REPORT171 SETUP: normal project guard genuinely forbids Report");
            compare(window.appBarCentralTabs.currentIndex, pageBefore,
                "REPORT171: unavailable Report does not navigate a stale page");
            const dialog = findChild(window, "assistant.reportPageUnavailable");
            verify(dialog !== null, "REPORT171: actual unavailable dialog belongs to real Main");
            tryCompare(dialog, "opened", true, 2000, "REPORT171: unavailable navigation has a visible honest explanation");
            compare(dialog.title, "Report page unavailable", "REPORT171: report refusal is ordinary user-facing guidance");
            const close = dialog.standardButton(Dialog.Close);
            verify(close !== null && close.visible && close.enabled, "REPORT171: real refusal dialog can be acknowledged");
            mouseClick(close);
        } else if (data.tag === "protected-other") {
            compare(window.appBarCentralTabs.currentIndex, pageBefore,
                "REPORT171: only exact edi:report URI receives internal navigation authority");
            tryVerify(() => assistant.lastError.length > 0, 2000,
                "REPORT171: unchanged protected report guard refuses an untrusted unrelated scheme");
        } else {
            tryCompare(window.appBarCentralTabs, "currentIndex", AppState.Page.Report, 2000,
                "REPORT171: real anchor click reaches existing Main Report page");
            rendered();
            const preview = Ui.control(Probe, window, "report.preview");
            verify(preview !== null && Ui.rendered(preview), "REPORT171: existing live preview is actually exposed");
            compare(preview.report, current.report, "REPORT171: link means actual current report, including after replacement");
            tryCompare(current.report, "active", true, 2000, "REPORT171: existing Report model follows real selected page");
            verify(Ui.control(Probe, window, "group.reportExport") !== null,
                "REPORT171: existing export controls are reused rather than duplicated");
            verify(findChild(window, "assistant.reportPageUnavailable") === null
                || !findChild(window, "assistant.reportPageUnavailable").opened,
                "REPORT171: valid current navigation does not report unavailable");
        }
        compare(Session.project, current, "REPORT171: navigation alone never replaces project ownership");
        if (current) compare(JSON.stringify(Probe.rows(current.parameters)), parameters,
            "REPORT171: navigation cannot edit current native values/free/SU");
        compare(JSON.stringify(Probe.rows(assistant.messages)), history,
            "REPORT171: clicking a link preserves actual original conversation bytes/identities");
        verify(assistant.connected, "REPORT171: page navigation/refusal preserves genuine managed account");
        assistant.signOut();
        tryCompare(assistant, "connected", false, 2000, "REPORT171: owned fixture teardown actually settles");
    }

    // Genuine Main/default Session and ordinary native script. No fake account,
    // scientific model, busy state, pointer flag or worker is assigned here.
    function visible185_parameters(project) {
        return Probe.rows(project.parameters).map(row => row.parameter);
    }
    function visible185_parameter(project, label, name) {
        const found = visible185_parameters(project).filter(parameter =>
            parameter.rowLabel === label && parameter.name === name);
        compare(found.length, 1, "VA SETUP: independent original parameter metadata is unique");
        return found[0];
    }
    function visible185_inputs(project) {
        const experiment = project.currentExperiment;
        const observations = Probe.rows(experiment.pattern).map(row => [row.x, row.intensityMeas, row.intensityMeasSu]);
        verify(observations.length > 0 && observations.every(row => row.every(Number.isFinite) && row[2] > 0),
            "VA SETUP: genuine measured observations and positive supplied sigmas exist before preservation is asserted");
        return JSON.stringify({
            observations: observations,
            weight: experiment.datasetWeight,
            exclusions: Probe.rows(experiment.excludedRegions),
            links: Probe.rows(experiment.linkedStructures).map(row => [row.structureId, row.enabled])
        });
    }
    function visible185_values(project) {
        return JSON.stringify(visible185_parameters(project).map(parameter =>
            [parameter.path, parameter.value, parameter.free, parameter.hasUncertainty, parameter.uncertainty]));
    }
    function visible185_type(text) {
        keySequence(StandardKey.SelectAll);
        keyClick(Qt.Key_Backspace);
        for (const character of text)
            keyClick(character);
    }
    function visible185_page(name) {
        Ui.click(this, Probe, window, "appBar.tab." + name);
        rendered();
    }
    function visible185_field(parameter) {
        const fields = Ui.itemsWithProperty(Ui.page(window), "item").filter(candidate =>
            candidate.objectName.startsWith("parameters.value.")
            && candidate.item === parameter && candidate.visible && Ui.exposed(candidate));
        compare(fields.length, 1, "VA1 SETUP: genuine exposed visual Analysis cell belongs to exact ParameterItem");
        return fields[0];
    }
    function visible185_free(parameter) {
        const found = Ui.itemsWithProperty(Ui.page(window), "objectName").filter(candidate => {
            if (!candidate.objectName.startsWith("parameters.free.") || !Ui.exposed(candidate)) return false;
            for (let parent = candidate.parent; parent; parent = parent.parent)
                if (parent.parameter === parameter) return true;
            return false;
        });
        compare(found.length, 1, "VA1 SETUP: genuine exposed free checkbox belongs to exact visual row parameter");
        return found[0];
    }
    function visible185_outcome(callId, previousIds) {
        const rows = Probe.rows(assistant.messages).filter(value => !previousIds.has(value.id)
            && value.kind === "activity" && value.payload
            && value.payload.id === callId && value.payload.nativeOutcome);
        verify(rows.length <= 1, "VA: one new retained row owns the original current native call");
        return rows.length ? rows[0].payload.nativeOutcome : null;
    }
    function visible185_ready(stage) {
        try {
            tryVerify(() => assistant.connected && assistant.state === "idle" && !assistant.canCancel,
                2000, "VA SETUP: actual current managed context is idle before original admission");
        } finally { report187_state("visible-" + stage); }
    }
    function visible185_capture(stage) {
        // Optional actual frame receipt; no extra sleep/render wait or pixel oracle.
        try {
            const image = grabImage(window.contentItem);
            if (image.width > 0 && image.height > 0) {
                image.save("visible185-" + stage + ".png");
                console.log("VISIBLE185_FRAME", stage, image.width, image.height);
            }
        } catch (error) { console.log("VISIBLE185_FRAME_UNAVAILABLE", stage, String(error)); }
    }
    function visible237_observationMs(actions) {
        // Public de82 helper: move500/press100/relax-or-stage500; character100.
        // A complete parameter action has at most page/Main/reset/filter/target,
        // two select/delete pairs and literal path/value Unicode scalar spelling.
        // Keep the original10000 observation allowance and add the actual finite
        // serialized presentation workload; do not accelerate input or relax outcomes.
        return 10000 + actions.reduce((total, action) => total + 5 * (500 + 100 + 500)
            + 100 * (4 + [...action.path].length + [...action.text].length) + 2 * 500, 0);
    }
    function test_visible185_actual_native_manual_interaction_data() {
        return ["default-off", "analysis-value-free", "wavelength", "manual-override",
            "dirty-valid-value", "dirty-invalid-value", "dirty-valid-free", "dirty-invalid-free",
            "dirty-valid-fit", "dirty-invalid-fit", "real-fit", "fit-stop", "close-owner",
            "unsupported-values", "unsupported-free", "unsupported-relations", "normal-relations",
            "requested-cell-profile-flags"].map(tag => ({tag: tag}));
    }
    function test_visible185_actual_native_manual_interaction(data) {
        if (data.tag === "requested-cell-profile-flags") {
            // One independent CoSiO row in the original Main/native vehicle.
            const test609=this, fixture609="docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project";
            verify(Session.openProject(Probe.repoUrl(fixture609)),"FLAGS609 SETUP: genuine original orthorhombic CoSiO/d20 opens");
            const owner609=Session.project, life609=lifetime313(owner609);
            tryVerify(() => !owner609.calculating && Probe.computedCurrent(owner609.currentExperiment),10000);
            let all609=visible185_parameters(owner609);
            const cells609=["structure.cell.length_a","structure.cell.length_b","structure.cell.length_c","experiment.instrument.calib_twotheta_offset"];
            const profile609=["broad_gauss_u","broad_gauss_v","broad_gauss_w","broad_lorentz_y"].map(name => "experiment.peak."+name);
            const requested609=cells609.concat(profile609), peak609=profile609.concat(["experiment.peak.broad_lorentz_x"]);
            function member609(path) {const rows=all609.filter(p => p.path===path);compare(rows.length,1);return rows[0];}
            compare(cells609.slice(0,3).map(path => member609(path).value),[10.3,6.0,4.8],
                "FLAGS609 SETUP: independent original orthorhombic lengths, not cubic b/c followers");
            verify(requested609.every(path => member609(path).free && member609(path).fittable && member609(path).refinable),
                "FLAGS609 SETUP: genuine original requested members start free and independently editable");
            const original609=visible185_values(owner609), inputs609=visible185_inputs(owner609),
                declarations609=relation245_declarations(owner609), metadata609=import265_owner(owner609), originalUndo609=owner609.canUndo;
            toggle();gui392_signIn();visible185_ready("flags609-original");
            verify(!assistant.showActions && assistant.connected && !assistant.contextConsentRequired);
            const account609=assistant.connectionLabel,catalog609=JSON.stringify(Probe.rows(assistant.models));
            const prior609=new Set(Probe.rows(assistant.messages).map(row => row.id));
            assistant.send("Original normal setup fixes only the independently declared flag members");
            tryVerify(() => !assistant.canCancel && visible185_outcome("visible609-baseline",prior609)!==null,10000);
            compare(visible185_outcome("visible609-baseline",prior609).status,"edited");
            all609=visible185_parameters(owner609);
            const changed609=requested609.slice(1); // a is an explicit already-equal prefix; U really changes.
            verify(member609(cells609[0]).free && changed609.every(path => !member609(path).free),
                "FLAGS609 SETUP: original normal operation establishes actual changed b/c/zero/U/V/W/Y operands");
            const baseline609=visible185_values(owner609), baselineUndo609=owner609.canUndo;
            const before609=new Map(all609.map(p => [p.path,[p.value,p.free,p.hasUncertainty,p.uncertainty]]));
            const pins609=new Map(requested609.map(path => [path,{item:member609(path),life:lifetime313(member609(path))}]));
            Ui.click(test609,Probe,window,"assistant.showActions");verify(assistant.showActions);
            closeAssistant388();visible185_page("analysis");
            const slots609=[], watched609=new Set(), cues609=[], writes609=[], categories609=[];
            let point609=null, phase609="cells", keys609=0, toggles609=0, clicks609=0, resets609=0, fit609=0;
            function current609() {
                verify(alive313(life609) && Session.project===owner609,"FLAGS609: SAME live original owner");
                const actual=visible185_parameters(owner609);
                for(const [path,pin] of pins609)verify(alive313(pin.life) && actual.includes(pin.item) && pin.item.path===path,
                    "FLAGS609: exact live member identity survives the operation");
            }
            function bind609(object,signal,callback) {
                const life=lifetime313(object);object[signal].connect(callback);
                slots609.push({object:object,life:life,signal:signal,callback:callback});
            }
            function parameter609(control) {
                for(let p=control;p;p=p.parent)if(p.parameter && all609.includes(p.parameter))return p.parameter;
                return null;
            }
            function scan609() {
                current609();
                for(const control of Ui.itemsWithProperty(Ui.windowRoot(window),"objectName")) {
                    if(watched609.has(control))continue;
                    const name=control.objectName;
                    if(name==="parameters.category") {
                        watched609.add(control);bind609(control,"activated",index => {
                            if(assistant.showingActions)categories609.push(Ui.control(Probe,window,"parameters.list").sourceModel.categories[index]);
                        });
                    } else if(name==="parameters.resetFilters") {
                        watched609.add(control);bind609(control,"clicked",() => {if(assistant.showingActions)++resets609;});
                    } else if(name.startsWith("parameters.free.") || name==="parameters.freeHeader.free") {
                        watched609.add(control);
                        if(typeof control.clicked==="function")bind609(control,"clicked",() => {if(assistant.showingActions)++clicks609;});
                        if(typeof control.toggled==="function")bind609(control,"toggled",() => {if(assistant.showingActions)++toggles609;});
                    } else if(name.startsWith("parameters.value.") || name.startsWith("cell.") || name.startsWith("instrument.")) {
                        if(typeof control.textEdited==="function") {
                            watched609.add(control);bind609(control,"textEdited",() => {if(assistant.showingActions)++keys609;});
                        }
                    }
                }
            }
            function cue609() {
                scan609();verify(assistant.actionWindow===window && assistant.showingActions && point609!==null);
                verify(Ui.rendered(item("assistant.actionPointer")),"FLAGS609: genuine original visible pointer, not invented activity");
                const filter=Ui.control(Probe,window,"parameters.list").sourceModel;
                const controls=Ui.itemsWithProperty(Ui.windowRoot(window),"objectName").filter(c => c.objectName.startsWith("parameters.free.") && Ui.exposed(c));
                for(const control of controls) {
                    const box=rect(control);
                    if(point609.x<box[0] || point609.y<box[1] || point609.x>=box[0]+box[2] || point609.y>=box[1]+box[3])continue;
                    const parameter=parameter609(control);verify(parameter!==null && pins609.has(parameter.path));
                    verify(!parameter.free && parameter.fittable && parameter.refinable,
                        "FLAGS609: scientific cue targets a genuinely changed requested eligible member, not equal a");
                    compare(filter.nameFilter,"");compare(filter.variability,0);
                    verify(filter.shows(parameter));
                    if(parameter.category==="cell")compare(filter.categoryFilter,"","FLAGS609: cells use the original unfiltered scroll route");
                    if(phase609==="profile") {
                        verify(filter.categoryFilter.length>0 && categories609.includes(filter.categoryFilter),
                            "FLAGS609: profile route chooses an actual offered category");
                        const shown=[];for(let i=0;i<filter.rowCount();++i)shown.push(filter.parameterAt(i).path);
                        compare(JSON.stringify(shown.slice().sort()),JSON.stringify(peak609.slice().sort()),
                            "FLAGS609: CHANGED initially-shown U cannot retain a one-row name filter; complete five-profile category remains visible");
                    }
                    cues609.push({path:parameter.path,phase:phase609,category:filter.categoryFilter,rect:box,
                        identity:identity313(lifetime313(control))});
                }
            }
            function narrow609() {
                // Genuine user setup, not a requirement that the prior tool restore All.
                Ui.click(test609,Probe,window,"parameters.resetFilters");rendered();
                const filter=Ui.control(Probe,window,"parameters.list").sourceModel;
                compare(filter.categoryFilter,"");compare(filter.variability,0);compare(filter.nameFilter,"");
                const field=Ui.control(Probe,window,"parameters.nameFilter");verify(field!==null && Ui.exposed(field));
                Ui.click(test609,Probe,window,"parameters.nameFilter");visible185_type("broad_gauss_u");rendered();
                compare(filter.categoryFilter,"");compare(filter.variability,0);
                compare(filter.nameFilter,"broad_gauss_u");compare(filter.rowCount(),1);
                verify(filter.parameterAt(0)===member609(profile609[0]),"FLAGS611 SETUP: actual All/category+variability and real narrow name show exactly changed U before the original request");
            }
            for(const path of changed609) {
                const parameter=member609(path);bind609(parameter,"freeChanged",() => {
                    current609();if(!assistant.showingActions)return;
                    verify(parameter.free,"FLAGS609: exact requested final free=true is really applied");
                    compare(cues609.filter(c => c.path===path).length,1,
                        "FLAGS609: EACH actual scientific change follows exactly one exposed original row cue");
                    writes609.push(path);
                });
            }
            bind609(owner609.fit,"runningChanged",() => {if(owner609.fit.running)++fit609;});
            bind609(assistant,"actionPointerShown",scan609);
            bind609(assistant,"actionPointerMoved",point => {point609={x:point.x,y:point.y};scan609();});
            bind609(assistant,"actionPointerPressed",cue609);scan609();
            try {
                narrow609();
                const ids=new Set(Probe.rows(assistant.messages).map(row => row.id));
                assistant.send("Free the independently requested original a b c and zero, with a already equal");
                tryVerify(() => !assistant.canCancel && !assistant.showingActions && visible185_outcome("visible609-cells",ids)!==null,
                    visible237_observationMs(cells609.map(path => ({path:path,text:""}))),"FLAGS609: original requested cell array completes, no refused/partial success");
                const cells=visible185_outcome("visible609-cells",ids);
                verify(cells.status==="edited" && cells.complete===true && cells.atomic===false && cells.steps_completed===4,
                    "FLAGS609: all four original entries settle, including no-op a; zero partial/refusal allowance");
                verify(cells609.every(path => member609(path).free));
                phase609="profile";resets609=0;
                // Genuine user filter after the cell objective: U is NOW shown AND still changed.
                narrow609();verify(!member609(profile609[0]).free,"FLAGS609 SETUP: initially shown U is not a no-op escape");
                const profileIds=new Set(Probe.rows(assistant.messages).map(row => row.id));
                assistant.send("Free exactly U V W Y in the original peak profile, keeping X unchanged");
                tryVerify(() => !assistant.canCancel && !assistant.showingActions && visible185_outcome("visible609-after",profileIds)!==null,
                    visible237_observationMs(profile609.map(path => ({path:path,text:""}))),"FLAGS609: original profile request and following real native read settle");
                const profile=visible185_outcome("visible609-profile",profileIds);
                verify(profile!==null && profile.status==="edited" && profile.complete===true && profile.atomic===false && profile.steps_completed===4,
                    "FLAGS609: ALL U/V/W/Y complete; attempted first U/partial1 cannot pass");
                current609();compare(resets609<=1,true,"FLAGS609: suitable complete category is reused without a Reset per row");
                compare(JSON.stringify(writes609),JSON.stringify(changed609),"FLAGS609: exactly requested changes in request order, no repeated or missing b/c/V/Y");
                compare(cues609.length,changed609.length);compare([keys609,toggles609,clicks609,fit609],[0,0,0,0],
                    "FLAGS609: ordinary app mutation follows visual-only scientific cues, no keys/checkbox/menu dispatch or fitting");
                for(const parameter of all609) {
                    const old=before609.get(parameter.path);
                    compare(JSON.stringify([parameter.value,parameter.hasUncertainty,parameter.uncertainty]),JSON.stringify([old[0],old[2],old[3]]));
                    compare(parameter.free,requested609.includes(parameter.path)?true:old[1],"FLAGS609: X and ALL unrequested flags remain exact");
                }
                compare(visible185_inputs(owner609),inputs609);compare(relation245_declarations(owner609),declarations609);
                compare(import265_owner(owner609),metadata609);compare(assistant.connectionLabel,account609);
                compare(JSON.stringify(Probe.rows(assistant.models)),catalog609);verify(assistant.connected);
                console.log("FLAGS609_RESULT",JSON.stringify({cues:cues609,writes:writes609,keys:keys609,toggles:toggles609,
                    clicks:clicks609,resets:resets609,categories:categories609,values:JSON.parse(visible185_values(owner609)),
                    sameOwner:Session.project===owner609,cells:cells,profile:profile}));
                for(let i=changed609.length-1;i>=0;--i) {
                    verify(owner609.canUndo);Ui.click(test609,Probe,window,"appBar.button.undo");
                    compare(member609(changed609[i]).free,false,"FLAGS609: each genuine original ordinary Undo restores its own applied flag");
                }
                compare(visible185_values(owner609),baseline609,"FLAGS609: Undo restores exact normal-setup science and present SUs");
                compare(owner609.canUndo,baselineUndo609,"FLAGS609: no extra no-op/phantom assistant history");
                verify(owner609.canUndo);Ui.click(test609,Probe,window,"appBar.button.undo");
                compare(visible185_values(owner609),original609,"FLAGS609: NEXT ordinary Undo restores the genuine atomic normal setup, no hidden no-op history");
                compare(owner609.canUndo,originalUndo609);
            } finally {
                for(const slot of slots609)disconnect313(slot.life,slot.object,slot.signal,slot.callback);
            }
            return;
        }
        const fitCase = ["real-fit", "fit-stop"].includes(data.tag) || data.tag.endsWith("-fit");
        const fixture = fitCase ? "docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project"
            : "tests/fixtures/e04_t1/editable-project";
        verify(Session.openProject(Probe.repoUrl(fixture)), "VA SETUP: genuine independent complete project opens normally");
        const project = Session.project;
        const parameters = visible185_parameters(project);
        const cell = parameters.filter(parameter => parameter.category === "cell" && parameter.name === "length_a");
        compare(cell.length, 1, "VA SETUP: original independent cell scalar is unique");
        const la = fitCase ? cell[0] : visible185_parameter(project, "La", "adp_iso");
        const ba = fitCase ? null : visible185_parameter(project, "Ba", "adp_iso");
        if (fitCase) {
            for (const parameter of parameters) parameter.free = false;
            cell[0].free = true;
            project.currentExperiment.scale.free = true;
            project.analysis.maxIterations = 8; // Existing bounded real-fit prior art; no optimum oracle.
        } else {
            // The independent editable fixture deliberately supplies only La in a complete-replacement
            // custom table. Restore the public built-in-table mode before this nonfit setup calculates.
            const lengths = project.currentStructure.scatteringLengths;
            const originalLengths = Probe.rows(lengths);
            compare(originalLengths.length, 1, "VA SETUP: original fixture has its one declared custom neutron length");
            compare(originalLengths[0].typeSymbol, "La", "VA SETUP: original custom table is the literal fixture La entry");
            compare(originalLengths[0].lengthFm, 8.24, "VA SETUP: original custom length matches independent fixture bytes");
            for (let index = originalLengths.length - 1; index >= 0; --index) lengths.remove(index);
            compare(lengths.count, 0, "VA SETUP: public custom model is empty so the existing built-in table applies");
            compare(Probe.rows(lengths).length, 0, "VA SETUP: actual model readback confirms custom replacement was removed");
            la.free = false;
            ba.free = false;
        }
        try {
            tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment),
                10000, "VA SETUP: real original calculation and ordinary free-subset edits settle");
        } finally {
            try {
                const experiment = project ? project.currentExperiment : null;
                const pattern = experiment ? experiment.pattern : null;
                console.log("VISIBLE193_SETUP", data.tag, JSON.stringify({
                    currentOwner: Session.project === project, projectPresent: Session.hasProject,
                    calculating: project ? project.calculating : null,
                    computedCurrent: experiment ? Probe.computedCurrent(experiment) : null,
                    patternCalculationError: pattern ? pattern.calculationError : null,
                    patternStale: pattern ? pattern.stale : null,
                    patternCount: pattern ? pattern.count : null,
                    projectLastError: project ? project.lastError : null,
                    sessionLastError: Session.lastError,
                    sessionMessagesModel: "Session.loadWarnings",
                    sessionMessages: Probe.rows(Session.loadWarnings),
                    page: window.appBarCentralTabs.currentIndex
                }));
            } catch (error) { console.log("VISIBLE193_SETUP_DIAGNOSTIC_ERROR", String(error)); }
        }
        if (fitCase) verify(project.fit.available, "VA SETUP: actual installed native backend admits this real single fit");
        const inputs = visible185_inputs(project);
        const originalValues = visible185_values(project);
        const originalValue = la.value;
        const originalFlag = la.free;
        const wavelength = parameters.filter(parameter => parameter.name === "setup_wavelength");
        compare(wavelength.length, 1, "VA SETUP: genuine original wavelength scalar exists");
        const originalWavelength = wavelength[0].value;
        const declarationRows = [Probe.rows(project.analysis.aliases), Probe.rows(project.analysis.constraints)];
        const originalDeclarations = JSON.stringify(declarationRows);
        compare(typeof assistant.showActions, "boolean", "VA SETUP: real production mode property is available");
        compare(assistant.showActions, false, "VA: every actual new Session mode starts OFF, not fabricated enabled");
        toggle();
        assistant.signIn();
        visible185_ready("bootstrap");
        if (assistant.contextConsentRequired) assistant.signIn();
        visible185_ready("disclosed");
        verify(!assistant.contextConsentRequired, "VA SETUP: genuine current disclosed context is approved");
        const accountRows = Probe.rows(assistant.models).map(row => row.id);
        if (!["default-off", "normal-relations"].includes(data.tag)) {
            const checkbox = item("assistant.showActions");
            verify(checkbox.visible && checkbox.enabled, "VA SETUP: actual Show actions control is actionable");
            mouseClick(checkbox);
            compare(assistant.showActions, true, "VA: real checkbox enables the nonpersistent mode");
        }
        closeAssistant388(); // Actual original toggle exposes manual controls before setup input.
        visible185_page("analysis");
        if (!fitCase) {
            const filter = Ui.control(Probe, window, "parameters.nameFilter");
            verify(filter !== null && Ui.exposed(filter), "VA SETUP: actual Analysis filter is exposed");
            mouseClick(filter);
            visible185_type("adp_iso");
            rendered();
        }
        let field = fitCase ? null : visible185_field(la);
        let free = fitCase ? null : visible185_free(la);
        if (data.tag === "wavelength") {
            visible185_page("experiment");
            function wavelength243(stage) {
                try {
                    const candidates = Ui.itemsWithProperty(Ui.page(window), "objectName")
                        .filter(control => control.objectName === "instrument.setup_wavelength");
                    console.log("WAVELENGTH243_PREMISE", stage, JSON.stringify({
                        page: window.appBarCentralTabs.currentIndex, currentPage: String(Ui.page(window)),
                        expectedItem: String(wavelength[0]),
                        groups: Ui.itemsWithProperty(Ui.page(window), "objectName")
                            .filter(control => control.objectName === "group.instrument")
                            .map(group => ({identity: String(group), visible: group.visible,
                                enabled: group.enabled, collapsed: group.collapsed})),
                        candidates: candidates.map(control => {
                            const point = control.mapToItem(window.contentItem, 0, 0);
                            return {identity: String(control), item: String(control.item),
                                exactItem: control.item === wavelength[0], visible: control.visible,
                                enabled: control.enabled, inPane: Ui.inPane(control),
                                rect: [point.x, point.y, control.width, control.height],
                                clickPoint: Ui.clickPoint(control), exposed: Ui.exposed(control)};
                        }), sameOwner: Session.project === project, connected: assistant.connected,
                        lastError: assistant.lastError}));
                } catch (error) { console.log("WAVELENGTH243_PREMISE_ERROR", stage, String(error)); }
            }
            wavelength243("before-reveal");
            try {
                Ui.click(this, Probe, window, "sideBar.tab.basic");
                Ui.expandGroup(this, Probe, window, "group.instrument");
                field = Ui.control(Probe, window, "instrument.setup_wavelength");
                if (field !== null) {
                    Ui.scrollIntoView(field);
                    rendered();
                }
                verify(field !== null && field.item === wavelength[0] && Ui.exposed(field),
                    "VA SETUP: original supplied wavelength has its genuine current field");
            } finally { wavelength243("after-reveal-check"); }
            free = null;
        }
        const fitButton = fitCase ? Ui.control(Probe, window, "fitting.start") : null;
        if (fitCase) verify(fitButton !== null && Ui.exposed(fitButton), "VA FIT SETUP: genuine normal Start fitting button is exposed");
        let typed = 0, toggled = 0, activeStarts = 0, fitStarted = 0, finished = 0;
        let capturedTyping = false;
        let spellings = [], writes = [], fitClicks = 0;
        const editedParameter = data.tag === "wavelength" ? wavelength[0] : la;
        const pacedObservation = data.tag === "unsupported-relations"
            ? relation246_observationMs({aliases: [
                {id: "visible_original_la", path: la.path}, {id: "visible_original_ba", path: ba.path}],
                constraints: [{id: "visible_original_shared", expression: "visible_original_ba = visible_original_la", enabled: true}]})
            : assistant.showActions ? visible237_observationMs(
            data.tag === "analysis-value-free"
                ? [{path: la.path, text: "0.6"}, {path: la.path, text: ""}]
                : [{path: editedParameter.path, text: data.tag === "wavelength" ? "1.49" : "0.6"}]) : 10000;
        function valueReceipt() {
            if(assistant.showingActions && !fitCase)verify(scientificCues610.some(c=>c.kind==="value" && c.path===editedParameter.path),
                "VA610: actual ordinary value publication has a real prewrite target cue");
            writes.push(editedParameter.value);
        }
        function fitClickReceipt() { ++fitClicks; }
        function typedReceipt() {
            ++typed;
            spellings.push(field.text);
            if (data.tag === "analysis-value-free" && !capturedTyping) {
                capturedTyping = true;
                visible185_capture("typing");
            }
        }
        function freeReceipt() { ++toggled; }
        function activeReceipt() { if (assistant.showingActions) ++activeStarts; }
        function fitReceipt() { if (alive313(fitLife313) && fitOwner313.running) ++fitStarted; }
        function finishedReceipt() {
            ++finished;
            console.log("VISIBLE185_FINISHED", data.tag, JSON.stringify({finished: finished,
                actualOutcome: alive313(fitLife313) ? fitOwner313.outcome : null,
                running: alive313(fitLife313) ? fitOwner313.running : null,
                currentOwner: Session.project === project}));
        }
        const fieldLife313 = lifetime313(field), freeLife313 = lifetime313(free);
        const parameterLife313 = lifetime313(editedParameter), fitButtonLife313 = lifetime313(fitButton);
        const fitOwner313 = project.fit, fitLife313 = lifetime313(fitOwner313);
        if (field) field.textEdited.connect(typedReceipt);
        if (free) free.toggled.connect(freeReceipt);
        editedParameter.valueChanged.connect(valueReceipt);
        if (fitButton) fitButton.clicked.connect(fitClickReceipt);
        assistant.showingActionsChanged.connect(activeReceipt);
        project.fit.runningChanged.connect(fitReceipt);
        project.fit.finished.connect(finishedReceipt);
        let draftField = null, draft = "", draftFocus = null, draftSelection = null, draftPage = -1;
        const call = "visible185-action-" + data.tag;
        const requestPreviousIds = new Set(Probe.rows(assistant.messages).map(row => row.id));
        const scope481=data.tag==="manual-override" ? {
            controller:assistant,project:project,connection:assistant.connectionLabel,
            files:JSON.stringify(gui392_json(Probe.rows(assistant.selectedFiles)))} : null;
        const timelineEnabled = data.tag === "analysis-value-free";
        const timelinePriorIds = timelineEnabled ? new Set(Probe.rows(assistant.messages).map(row => row.id)) : null;
        let timelineCount = 0;
        const timelineLimit = 64; // Observer-only record budget; never a behavior assertion or runtime bound.
        function timelineControl(control) {
            if (!control) return null;
            try {
                const ancestry = [];
                let belongsToMain = control === window.contentItem;
                for (let parent = control.parent; parent; parent = parent.parent) {
                    if (parent === window.contentItem) belongsToMain = true;
                    ancestry.push({identity: String(parent), name: parent.objectName,
                        visible: parent.visible, enabled: parent.enabled, opacity: parent.opacity,
                        clip: parent.clip, rect: rect(parent)});
                }
                return {identity: String(control), name: control.objectName, belongsToMain: belongsToMain,
                    visible: control.visible, enabled: control.enabled, opacity: control.opacity,
                    activeFocus: control.activeFocus, clip: control.clip, rect: rect(control),
                    clickPoint: Ui.clickPoint(control), rendered: Ui.rendered(control),
                    text: typeof control.text === "string" ? control.text : null,
                    checked: typeof control.checked === "boolean" ? control.checked : null,
                    ancestry: ancestry};
            } catch (error) { return {observationError: String(error)}; }
        }
        function timeline(event, argument) {
            if (!timelineEnabled) return;
            const sequence = ++timelineCount;
            if (sequence > timelineLimit) return;
            try {
                const table = Ui.control(Probe, window, "parameters.list");
                const filter = table ? table.sourceModel : null;
                const rows = Probe.rows(assistant.messages).filter(row => !timelinePriorIds.has(row.id)
                    && row.payload && [call, "visible185-value-" + data.tag, "visible185-read-" + data.tag].includes(row.payload.id));
                console.log("VISIBLE199_TIMELINE", data.tag, JSON.stringify({
                    sequence: sequence, epochMs: Date.now(), event: event, argument: argument || null,
                    page: window.appBarCentralTabs.currentIndex, pageIdentity: String(Ui.page(window)),
                    windowIdentity: String(window), windowVisible: window.visible, windowActive: window.active,
                    actionWindow: String(assistant.actionWindow), actionWindowIsMain: assistant.actionWindow === window,
                    showingActions: assistant.showingActions, manualTakeover: window.assistantManualTakeover,
                    canCancel: assistant.canCancel, state: assistant.state, lastError: assistant.lastError,
                    requested: Preferences.assistantShown, shown: popup.shown, opened: popup.opened,
                    filter: filter ? {name: filter.nameFilter, category: filter.categoryFilter,
                        variability: filter.variability, targetRow: filter.rowOf(la), targetShown: filter.shows(la)} : null,
                    focus: timelineControl(window.activeFocusItem), field: timelineControl(field), free: timelineControl(free),
                    pointer: timelineControl(findChild(window, "assistant.actionPointer")),
                    target: {identity: String(la), path: la.path, value: la.value, free: la.free},
                    typed: typed, toggled: toggled, currentOwner: Session.project === project,
                    connected: assistant.connected, connectionLabel: assistant.connectionLabel,
                    models: Probe.rows(assistant.models).map(row => row.id), outcome: visible185_outcome(call, requestPreviousIds),
                    newNativeRows: rows.map(row => ({id: row.id, kind: row.kind, status: row.status,
                        payload: {id: row.payload.id, tool: row.payload.tool, namespace: row.payload.namespace,
                            arguments: row.payload.arguments, status: row.payload.status,
                            success: row.payload.success, error: row.payload.error,
                            nativeOutcome: row.payload.nativeOutcome}}))
                }));
            } catch (error) { console.log("VISIBLE199_TIMELINE_ERROR", sequence, event, String(error)); }
        }
        const scientificCues610=[],freeWrites610=[];
        let point610=null;
        function move610(point){point610={x:point.x,y:point.y};}
        function press610(){
            if(!assistant.showingActions || !point610)return;
            verify(Session.project===project && assistant.actionWindow===window && alive313(parameterLife313));
            const all=Ui.itemsWithProperty(Ui.windowRoot(window),"objectName");
            for(const receiver of all.filter(c => Ui.exposed(c))) {
                let kind=null;
                if(receiver.item===editedParameter && (receiver.objectName.startsWith("parameters.value.")
                    || receiver.objectName.startsWith("instrument.") || receiver.objectName.startsWith("cell.")))kind="value";
                if(receiver.objectName.startsWith("parameters.free."))
                    for(let parent=receiver;parent;parent=parent.parent)if(parent.parameter===editedParameter)kind="free";
                if(kind===null)continue;
                const box=rect(receiver);if(point610.x<box[0] || point610.y<box[1] || point610.x>=box[0]+box[2] || point610.y>=box[1]+box[3])continue;
                scientificCues610.push({kind:kind,path:editedParameter.path,before:kind==="value"?editedParameter.value:editedParameter.free,
                    receiver:receiver,life:lifetime313(receiver),rect:box});
            }
        }
        function freePublication610(){
            if(!assistant.showingActions || data.tag==="manual-override")return;
            verify(alive313(parameterLife313) && Session.project===project);
            compare(scientificCues610.filter(c=>c.kind==="free" && c.path===editedParameter.path).length,1,
                "VA610: actual ordinary flag publication follows ONE original exposed target cue");
            freeWrites610.push(editedParameter.free);
        }
        assistant.actionPointerMoved.connect(move610);assistant.actionPointerPressed.connect(press610);
        editedParameter.freeChanged.connect(freePublication610);
        const timelineSlots = timelineEnabled ? [
            [assistant.actionPointerShown, () => timeline("pointer-shown")],
            [assistant.actionPointerMoved, position => timeline("pointer-moved", {x: position.x, y: position.y})],
            [assistant.actionPointerPressed, () => timeline("pointer-pressed")],
            [assistant.actionPointerHidden, () => timeline("pointer-hidden")],
            [assistant.showingActionsChanged, () => timeline("showing-actions")],
            [assistant.actionManualTakeover, () => timeline("manual-takeover")],
            [window.activeFocusItemChanged, () => timeline("focus")],
            [window.appBarCentralTabs.currentIndexChanged, () => timeline("page")],
            [assistant.messages.rowsInserted, () => timeline("rows-inserted")],
            [assistant.messages.rowsRemoved, () => timeline("rows-removed")],
            [assistant.messages.dataChanged, () => timeline("rows-data")],
            [assistant.messages.modelReset, () => timeline("rows-reset")]
        ] : [];
        for (const slot of timelineSlots) slot[0].connect(slot[1]);
        timeline("armed-before-original-events");
        try {
            if (data.tag === "analysis-value-free") {
                verify(!Probe.objectsWithProperty(window, "item").includes(field),
                    "VA1 SETUP: actual value delegate is visual-only relative to QObject root traversal");
                verify(!Probe.objectsWithProperty(window, "checked").includes(free),
                    "VA1 SETUP: actual free delegate is visual-only relative to QObject root traversal");
            }
            if (data.tag.startsWith("dirty-")) {
                visible185_page("structure");
                Ui.click(this, Probe, window, "sideBar.tab.basic");
                Ui.expandGroup(this, Probe, window, "group.cell");
                draftField = Ui.control(Probe, window, "cell.length_a");
                if (draftField !== null) {
                    Ui.scrollIntoView(draftField);
                    rendered();
                }
                console.log("DRAFT253_PREMISE", data.tag, JSON.stringify({
                    page: window.appBarCentralTabs.currentIndex,
                    group: {identity: String(Ui.control(Probe, window, "group.cell")),
                        collapsed: Ui.control(Probe, window, "group.cell").collapsed},
                    basicChecked: Ui.control(Probe, window, "sideBar.tab.basic").checked,
                    field: draftField ? {identity: String(draftField), item: String(draftField.item),
                        exactItem: draftField.item === cell[0], visible: draftField.visible,
                        enabled: draftField.enabled, activeFocus: draftField.activeFocus,
                        readOnly: draftField.readOnly === undefined ? null : draftField.readOnly,
                        rect: rect(draftField),
                        clickPoint: Ui.clickPoint(draftField), exposed: Ui.exposed(draftField)} : null,
                    currentOwner: Session.project === project, connected: assistant.connected}));
                verify(draftField !== null && draftField.item === cell[0] && draftField.enabled && Ui.exposed(draftField),
                    "VA3 SETUP: genuine editable manual field is exposed before delegated work");
                Ui.click(this, Probe, window, draftField.objectName);
                draft = data.tag.startsWith("dirty-invalid") ? "invalid-partial" : String(cell[0].value + 0.02);
                visible185_type(draft);
                verify(draftField.activeFocus && draftField.text === draft,
                    "VA3 SETUP: original genuine keyboard draft is still active and uncommitted");
                compare(visible185_values(project), originalValues,
                    "VA3 SETUP: typing without Return has not committed a scientific change");
                draftFocus = window.activeFocusItem;
                draftSelection = [draftField.selectionStart, draftField.selectionEnd];
                draftPage = window.appBarCentralTabs.currentIndex;
            }
            if (["analysis-value-free", "wavelength", "manual-override", "close-owner", "real-fit", "fit-stop"].includes(data.tag)) {
                toggle();
                compare(Preferences.assistantShown, true, "VA SETUP: actual stored request covers manual controls before temporary action reveal");
            }
            visible185_ready("before-original-send");
            // Direct public Send is setup only: it intentionally does not blur a manual draft.
            assistant.send("Original delegated visible operation " + data.tag);
            if (data.tag === "analysis-value-free") {
                // SAME existing positive tool, genuinely before its original value input/commit.
                const activeCall479="visible185-value-"+data.tag;
                tryVerify(() => assistant.showingActions && assistant.canCancel && typed === 0 && la.value===originalValue
                    && Ui.rendered(item("assistant.actionPointer")),pacedObservation,
                    "INPUT479: actual original visible tool/pointer is active BEFORE unrelated native input");
                compare(visible185_outcome(activeCall479,requestPreviousIds),null,
                    "INPUT479: exact original tool is genuinely pending, not completed/setup-refused");
                verify(window.active,"INPUT479: SAME original Main genuinely owns activation before the switch");
                const ownerLife479=lifetime313(project), controllerLife479=lifetime313(assistant);
                const other479=createTemporaryObject(otherWindow479,null);
                verify(other479!==null,"INPUT479: independent ordinary Qt window is created without another Session");
                const otherLife479=lifetime313(other479), mainLife479=lifetime313(window);
                const button479=findChild(other479,"input479.unrelated"), buttonLife479=lifetime313(button479);
                verify(button479!==null,"INPUT479: unrelated native window owns its original actual Button");
                let deactivated479=0,reactivated479=0,pressed479=0,released479=0,clicked479=0,takeover479=0,pendingAtEdge482=false;
                function activation479(){
                    if(window.active)++reactivated479;
                    else {++deactivated479;pendingAtEdge482=assistant.showingActions && assistant.canCancel
                        && visible185_outcome(activeCall479,requestPreviousIds)===null;}
                }
                function press479(){++pressed479;}
                function release479(){++released479;}
                function click479(){++clicked479;}
                function manual479(){++takeover479;}
                window.activeChanged.connect(activation479);
                button479.pressed.connect(press479);button479.released.connect(release479);button479.clicked.connect(click479);
                assistant.actionManualTakeover.connect(manual479);
                try {
                    other479.show();other479.requestActivate();
                    tryVerify(() => other479.active && !window.active,2000,
                        "INPUT479: real OTHER Qt window activates and original Main genuinely deactivates");
                    verify(deactivated479>0 && pendingAtEdge482,
                        "INPUT482: original Main genuinely deactivates WHILE original tool is actually pending");
                    verify(button479.visible && button479.enabled && button479.width>0 && button479.height>0,
                        "INPUT479: actual unrelated native input target is actionable");
                    mouseMove(button479,button479.width/2,button479.height/2);
                    mouseClick(button479,button479.width/2,button479.height/2);
                    compare(pressed479,1,"INPUT479: unrelated window received ONE real native press");
                    compare(released479,1,"INPUT479: unrelated window received ONE real native release");
                    compare(clicked479,1,"INPUT479: unrelated window received ONE real native click");
                    verify(alive313(ownerLife479) && alive313(controllerLife479) && Session.project===project
                        && Session.assistant===assistant,"INPUT479: switching/input preserves original live owner and controller");
                    verify(other479.active && !window.active,
                        "INPUT479: original helper does not steal foreground activation from unrelated window input");
                    const progress482=visible185_outcome(activeCall479,requestPreviousIds);
                    if(progress482!==null)compare(progress482.status,"edited",
                        "INPUT482: genuine original progress may complete truthfully; unrelated input cannot cause refusal/interruption");
                    compare(takeover479,0,"INPUT479: unrelated window input is NOT a manual project takeover");
                    window.requestActivate();
                    tryVerify(() => window.active && !other479.active,2000,
                        "INPUT479: genuine activation returns to SAME original Main");
                    verify(reactivated479>0,"INPUT479: original Main emitted native reactivation");
                    const safe479=item("assistant.toggle"), point479=Ui.clickPoint(safe479);
                    verify(point479!==null && safe479.visible && safe479.enabled,
                        "INPUT479: original assistant appbar is a real safe pointer destination");
                    mouseMove(safe479,point479.x,point479.y);
                    compare(takeover479,0,"INPUT479: harmless assistant pointer motion is NOT conflicting scientific input");
                } finally {
                    console.log("INPUT479_NATIVE",JSON.stringify({call:activeCall479,
                        deactivated:deactivated479,pendingAtEdge:pendingAtEdge482,reactivated:reactivated479,pressed:pressed479,
                        released:released479,clicked:clicked479,manualTakeover:takeover479,
                        sameOwner:alive313(ownerLife479)&&Session.project===project,
                        sameController:alive313(controllerLife479)&&Session.assistant===assistant,
                        mainActive:alive313(mainLife479)?window.active:null,
                        otherActive:alive313(otherLife479)?other479.active:null,
                        showingActions:assistant.showingActions,canCancel:assistant.canCancel,
                        outcome:visible185_outcome(activeCall479,requestPreviousIds)}));
                    disconnect313(mainLife479,window,"activeChanged",activation479);
                    disconnect313(buttonLife479,button479,"pressed",press479);
                    disconnect313(buttonLife479,button479,"released",release479);
                    disconnect313(buttonLife479,button479,"clicked",click479);
                    disconnect313(controllerLife479,assistant,"actionManualTakeover",manual479);
                    if(alive313(otherLife479))other479.close();
                    if(alive313(mainLife479)&&!window.active)window.requestActivate();
                }
            }
            if (["manual-override", "close-owner"].includes(data.tag)) {
                tryVerify(() => assistant.showingActions && assistant.canCancel && la.value===originalValue
                    && scientificCues610.some(c=>c.kind==="value" && c.path===la.path && c.before===originalValue && alive313(c.life)),
                    pacedObservation, "VA610 SETUP: genuine original pending prewrite target cue precedes manual/owner intervention");
                const pointer = item("assistant.actionPointer");
                verify(Ui.rendered(pointer), "VA SETUP: actual accent pointer is rendered during real input");
                if (data.tag === "manual-override") {
                    // The actual current original La row is exposed by the confirmed cue; no full-path filter is assumed.
                    verify(la.refinable && la.fittable,
                        "VA2 SETUP: original same-row manual target is independently fittable, never a derived alias");
                    const manual = visible185_free(la);
                    const beforeFree = la.free;
                    const beforeManualUndo = project.canUndo;
                    const manualValues = JSON.parse(originalValues).map(row =>
                        row[0] === la.path ? [row[0], row[1], !beforeFree, row[3], row[4]] : row);
                    const filter = Ui.control(Probe, window, "parameters.list").sourceModel;
                    console.log("MANUAL253_PREMISE", JSON.stringify({target: la.path,
                        value: la.value, free: beforeFree, page: window.appBarCentralTabs.currentIndex,
                        filter: {name: filter.nameFilter, category: filter.categoryFilter,
                            variability: filter.variability, targetShown: filter.shows(la), targetRow: filter.rowOf(la),
                            otherShown: filter.shows(ba), otherRow: filter.rowOf(ba)},
                        rect: rect(manual), clickPoint: Ui.clickPoint(manual),
                        currentOwner: Session.project === project, connected: assistant.connected}));
                    let manualToggles = 0;
                    function manualReceipt() { ++manualToggles; }
                    manual.toggled.connect(manualReceipt);
                    try {
                        const point = Ui.clickPoint(manual);
                        verify(point !== null, "VA2 SETUP: original manual event has a genuine exposed target");
                        Ui.click(this, Probe, window, manual.objectName);
                        tryCompare(la, "free", !beforeFree, 2000,
                            "VA2: original user checkbox event reaches its original target while cancellation restores view");
                        compare(manualToggles, 1, "VA2: user input is delivered once, never retargeted or replayed");
                    } finally { manual.toggled.disconnect(manualReceipt); }
                    tryCompare(assistant, "showingActions", false, 10000,
                        "VA2: original visible input retires after real manual takeover");
                    compare(la.value, originalValue, "VA610: retired prewrite app action cannot write scientific state");
                    rendered();
                    compare(visible185_values(project), JSON.stringify(manualValues),
                        "VA2: only the genuine original manual free action changes state; no late numeric/other write");
                    compare(visible185_inputs(project), inputs,
                        "VA2: original manual receiver preserves every measured sigma/weight/mask/link");
                    compare(project.canUndo, beforeManualUndo,
                        "VA2: cancellation consumes no prior Undo and creates no phantom native step");
                    verify(Ui.rendered(manual), "VA2: manual controls stay exposed after genuine user takeover");
                    compare(Preferences.assistantShown, true, "VA2: takeover preserves the actual stored assistant request");
                    tryCompare(popup, "visible", false, 2000, "VA2: no sheet reopens between user press/release or subsequent input");
                } else {
                    Session.closeProject();
                    tryCompare(assistant, "showingActions", false, 10000,
                        "VA4: ordinary Session retirement cancels real presentation without stale owner continuation");
                    compare(Session.project, null, "VA4: late original input cannot resurrect the closed owner");
                }
            }
            if (data.tag === "fit-stop") {
                tryVerify(() => project.fit.running && assistant.showingActions, pacedObservation,
                    "VA FIT SETUP: actual worker is running before real Stop, never a fake pending interval");
                const stop = item("assistant.stopVisibleAction");
                verify(stop.visible && stop.enabled && Ui.exposed(stop), "VA FIT SETUP: real appbar Stop is available");
                mouseClick(stop);
            }
            if (data.tag === "manual-override") {
                compare(originalValue,0.5,"FRESH481 SETUP: original literal editable-project La ADP is 0.5 before any requested edit");
                tryVerify(() => visible185_outcome(call,requestPreviousIds)!==null
                    && visible185_outcome("visible481-fresh",requestPreviousIds)!==null
                    && assistant.canCancel && !assistant.showingActions,pacedObservation,
                    "FRESH481: old operation really settled and genuine fresh inspection completed in SAME active turn");
                const old481=JSON.stringify(gui392_json(visible185_outcome(call,requestPreviousIds)));
                verify(visible185_outcome(call,requestPreviousIds).status!=="edited",
                    "FRESH481: old pending write NEVER inherits renewed authority or claims success");
                const fresh481=gui392_json(visible185_outcome("visible481-fresh",requestPreviousIds));
                verify(Array.isArray(fresh481.parameters),"FRESH481: actual fresh inspect returns its public current parameter inventory");
                const manual481=fresh481.parameters.filter(row=>row.path===la.path);
                compare(manual481.length,1,"FRESH481: real fresh inspection resolves the exact original current La path once");
                compare(manual481[0].value,0.5,"FRESH481: old 0.6 write is absent from genuinely returned inspection");
                compare(manual481[0].free,true,"FRESH481: real fresh inspection observes independent genuinely committed manual free=true");
                const expectedManual481=JSON.parse(originalValues).map(row=>row[0]===la.path
                    ? [row[0],row[1],true,row[3],row[4]] : row);
                compare(visible185_values(project),JSON.stringify(expectedManual481),
                    "FRESH481: only actual original user toggle exists before the separate fresh action");
                compare(visible185_outcome("visible481-later",requestPreviousIds),null,
                    "FRESH481: later action has NOT been emitted/admitted before public barrier release");
                verify(Session.project===scope481.project && Session.assistant===scope481.controller && assistant.connected,
                    "FRESH481: inspection does NOT replace original project/controller/account connection");
                compare(assistant.connectionLabel,scope481.connection,"FRESH481: original connected account presentation is unchanged");
                compare(JSON.stringify(gui392_json(Probe.rows(assistant.selectedFiles))),scope481.files,
                    "FRESH481: inspection never reacquires or changes any original selected input scope");
                const bound481=Probe.readReferenceFile("original-client-lines.native-emitted.jsonl").trim().split("\n").map(line=>JSON.parse(line));
                compare(bound481.filter(row=>row.params.callId==="visible481-later").length,0,
                    "FRESH481: exact owned peer has NOT sent the later write before genuine Usage release");
                const manualUndo482=project.canUndo;
                const fields481=[], spellings481=[],freshCueStart610=scientificCues610.length;
                function scan481(){
                    const fields=Ui.itemsWithProperty(Ui.page(window),"item").filter(candidate=>
                        candidate.objectName.startsWith("parameters.value.") && candidate.item===la
                        && candidate.visible && Ui.exposed(candidate));
                    for(const receiver of fields)if(!fields481.some(entry=>entry.receiver===receiver)){
                        const life=lifetime313(receiver),slot=function(){
                            verify(alive313(life) && Session.project===project && Session.assistant===assistant
                                && receiver.item===la,"FRESH481: real later input receipt belongs to SAME live original owner/parameter");
                            spellings481.push(receiver.text);
                        };
                        receiver.textEdited.connect(slot);fields481.push({receiver:receiver,life:life,slot:slot});
                    }
                }
                assistant.actionPointerShown.connect(scan481);assistant.actionPointerMoved.connect(scan481);
                assistant.actionPointerPressed.connect(scan481);
                try {
                    scan481();
                    assistant.refreshUsage(); // SAME existing public successful-call barrier, no invented control.
                    tryVerify(() => visible185_outcome("visible481-later",requestPreviousIds)!==null
                        && !assistant.canCancel && !assistant.showingActions,pacedObservation,
                        "FRESH481: ONLY separate later action settles normally after fresh retained inspection");
                    compare(visible185_outcome("visible481-later",requestPreviousIds).status,"edited",
                        "FRESH481: later original action genuinely succeeds; setup/early refusal is not a positive");
                    compare(spellings481.length,0,"FRESH610: ordinary later action dispatches no scientific keys");
                    const freshCues610=scientificCues610.slice(freshCueStart610).filter(c=>c.kind==="value" && c.path===la.path && c.before===.5);
                    compare(freshCues610.length,1,"FRESH610: separate later .7 app edit has ONE genuine original prewrite cue");
                    compare(JSON.stringify(writes),JSON.stringify([0.7]),
                        "FRESH481: only NEW requested 0.7 writes science once; old 0.6 callback never gains fresh stamps");
                    compare(la.value,0.7,"FRESH481: separate new action commits exact independently requested value");
                    compare(la.free,true,"FRESH481: separate value action preserves genuine manual free flag");
                    compare(JSON.stringify(JSON.parse(visible185_values(project)).filter(row=>row[0]!==la.path)),
                        JSON.stringify(expectedManual481.filter(row=>row[0]!==la.path)),
                        "FRESH481: later action preserves EVERY unrelated value/free/SU and physical path");
                    compare(JSON.stringify(gui392_json(visible185_outcome(call,requestPreviousIds))),old481,
                        "FRESH481: old retired result remains exact after fresh inspection/new action, never blessed by replacement stamps");
                    Ui.click(this,Probe,window,"appBar.button.undo");
                    compare(visible185_values(project),JSON.stringify(expectedManual481),
                        "FRESH481: ONE ordinary Undo removes only genuinely new edit, retaining manual change");
                    compare(project.canUndo,manualUndo482,
                        "FRESH482: new action Undo restores original manual-only recorded-history availability, never consumes unrelated prior history");
                } finally {
                    assistant.actionPointerShown.disconnect(scan481);assistant.actionPointerMoved.disconnect(scan481);
                    assistant.actionPointerPressed.disconnect(scan481);
                    for(const entry of fields481)disconnect313(entry.life,entry.receiver,"textEdited",entry.slot);
                }
                console.log("FRESH481_NATIVE",JSON.stringify({oldCall:call,inspection:"visible481-fresh",later:"visible481-later",
                    freshValue:manual481[0].value,freshFree:manual481[0].free,
                    actualLaterSpellings:spellings481,sameOwner:Session.project===project,
                    sameController:Session.assistant===assistant,originalInputs:visible185_inputs(project)===inputs}));
            }
            if (data.tag !== "close-owner") {
                try {
                    tryVerify(() => visible185_outcome(call, requestPreviousIds) !== null && !assistant.canCancel && !assistant.showingActions,
                        pacedObservation, "VA: actual original native outcome settles after its own input/worker owner");
                } finally {
                    try {
                        function controlFact(control) {
                            if (!control) return null;
                            try {
                                const ancestors = [];
                                for (let parent = control.parent; parent; parent = parent.parent)
                                    ancestors.push({identity: String(parent), name: parent.objectName,
                                        visible: parent.visible, enabled: parent.enabled, clip: parent.clip, rect: rect(parent)});
                                return {identity: String(control), name: control.objectName,
                                    visible: control.visible, enabled: control.enabled,
                                    activeFocus: control.activeFocus, clip: control.clip, rect: rect(control),
                                    clickPoint: Ui.clickPoint(control), rendered: Ui.rendered(control),
                                    text: typeof control.text === "string" ? control.text : null,
                                    checked: typeof control.checked === "boolean" ? control.checked : null,
                                    targetItem: control.item === la, ancestors: ancestors};
                            } catch (error) { return {observationError: String(error)}; }
                        }
                        const page = Ui.page(window);
                        const table = Ui.control(Probe, window, "parameters.list");
                        const group = Ui.control(Probe, window, "group.parameters");
                        const filter = table ? table.sourceModel : null;
                        const outcome = visible185_outcome(call, requestPreviousIds);
                        const visual = Ui.itemsWithProperty(page, "item").filter(control => control.item === la);
                        const owned = Probe.objectsWithProperty(window, "item").filter(control => control.item === la);
                        const nativeRows = Probe.rows(assistant.messages).filter(row => !requestPreviousIds.has(row.id) && row.payload
                            && [call, "visible185-value-" + data.tag, "visible185-read-" + data.tag].includes(row.payload.id));
                        console.log("VISIBLE197_OUTCOME", data.tag, JSON.stringify({
                            outcome: outcome, outcomePresent: outcome !== null,
                            canCancel: assistant.canCancel, showingActions: assistant.showingActions,
                            state: assistant.state, lastError: assistant.lastError,
                            pageIndex: window.appBarCentralTabs.currentIndex, pageIdentity: String(page),
                            showActions: assistant.showActions, manualTakeover: window.assistantManualTakeover,
                            requested: Preferences.assistantShown, popupShown: popup.shown,
                            popupVisible: popup.visible, popupOpened: popup.opened,
                            focus: controlFact(window.activeFocusItem), field: controlFact(field), free: controlFact(free),
                            nameFilter: controlFact(Ui.control(Probe, window, "parameters.nameFilter")),
                            category: controlFact(Ui.control(Probe, window, "parameters.category")),
                            variability: controlFact(Ui.control(Probe, window, "parameters.variability")),
                            modelFilters: filter ? {name: filter.nameFilter, category: filter.categoryFilter,
                                variability: filter.variability, targetRow: filter.rowOf(la), targetShown: filter.shows(la)} : null,
                            selected: group ? {row: group.selectedRow,
                                path: group.selected ? group.selected.path : null, target: group.selected === la} : null,
                            visualMatches: visual.map(controlFact), ownedMatches: owned.map(controlFact),
                            target: {path: la.path, value: la.value, free: la.free},
                            typed: typed, toggled: toggled, spellings: spellings, writes: writes,
                            currentOwner: Session.project === project, projectPresent: Session.hasProject,
                            connected: assistant.connected, connectionLabel: assistant.connectionLabel,
                            models: Probe.rows(assistant.models).map(row => row.id),
                            nativeRows: nativeRows.map(row => ({id: row.id, status: row.status, text: row.text,
                                payload: {id: row.payload.id, type: row.payload.type, tool: row.payload.tool,
                                    namespace: row.payload.namespace, arguments: row.payload.arguments,
                                    status: row.payload.status, success: row.payload.success,
                                    error: row.payload.error, nativeOutcome: row.payload.nativeOutcome}}))
                        }));
                    } catch (error) { console.log("VISIBLE197_OUTCOME_DIAGNOSTIC_ERROR", data.tag, String(error)); }
                }
                const outcome = visible185_outcome(call, requestPreviousIds);
                if (data.tag.startsWith("dirty-")) {
                    verify(["refused", "unavailable"].includes(outcome.status) && typeof outcome.message === "string" && outcome.message.length > 0,
                        "VA3: original draft receives a truthful before-write refusal, never successful admission");
                    compare(visible185_values(project), originalValues, "VA3: refusal preserves every original value/free/SU");
                    compare(draftField.text, draft, "VA3: refusal preserves exact original uncommitted spelling");
                    compare(window.activeFocusItem, draftFocus, "VA3: preflight does not blur the original manual input");
                    compare(draftField.selectionStart, draftSelection[0], "VA3: original draft selection start survives");
                    compare(draftField.selectionEnd, draftSelection[1], "VA3: original draft selection end survives");
                    compare(window.appBarCentralTabs.currentIndex, draftPage, "VA3: refusal precedes navigation");
                    compare(fitStarted, 0, "VA3: a blocked draft never admits a hidden worker");
                } else if (data.tag.startsWith("unsupported-") && data.tag !== "unsupported-relations") {
                    verify(["refused", "unavailable"].includes(outcome.status) && typeof outcome.message === "string" && outcome.message.length > 0,
                        "VA: unsupported visible operations fail honestly before write without hidden fallback");
                    compare(visible185_values(project), originalValues, "VA: unsupported batch/relation cannot partly mutate the owner");
                    compare(JSON.stringify([Probe.rows(project.analysis.aliases), Probe.rows(project.analysis.constraints)]),
                        originalDeclarations, "VA: unsupported relation preserves every original declaration");
                    compare(typed + toggled, 0, "VA: refusal cannot be a decorative event sequence over a hidden write");
                } else if (["normal-relations", "unsupported-relations"].includes(data.tag)) {
                    compare(outcome.status, "edited", "REL SUPPORTED-STAGE: same original valid relation is confirmed by normal OFF or actual supported visible form");
                    verify(project.analysis.aliases.count === declarationRows[0].length + 2
                        && project.analysis.constraints.count === declarationRows[1].length + 1,
                        "VA SETUP CONTROL: genuine valid relation append proves unsupported-visible payload is not a malformed refusal");
                    if (data.tag === "normal-relations")
                        compare(activeStarts, 0, "VA: normal relation control does not invent visible activity");
                    else verify(activeStarts > 0, "REL SUPPORTED-STAGE: original visible relation actually uses the real helper/form");
                    Ui.click(this, Probe, window, "appBar.button.undo");
                    compare(JSON.stringify([Probe.rows(project.analysis.aliases), Probe.rows(project.analysis.constraints)]),
                        originalDeclarations, "VA: complete normal Undo restores original declarations");
                    compare(visible185_values(project), originalValues, "VA: complete relation Undo restores all original values/free/SU");
                } else if (fitCase) {
                    verify(fitStarted > 0 && finished === 1, "VA FIT: genuine worker admission and one actual completion precede result");
                    verify(!project.fit.running && project.fit.outcome.length > 0 && fitClicks > 0,
                        "VA FIT: actual Start click and normal final report publication precede original RPC settlement");
                    if (outcome.adopted) verify(project.fit.canUndo && Probe.rows(project.fit.results).length > 0,
                        "VA FIT: actual adopted report exposes ordinary result rows and normal Undo");
                    if (data.tag === "fit-stop") {
                        verify(["cancelled", "interrupted", "superseded"].includes(outcome.status),
                            "VA FIT: genuine Stop is a truthful partial/cancel outcome, not convergence");
                    } else {
                        verify(["done", "max_iterations", "no_step"].includes(outcome.status),
                            "VA FIT SETUP: actual supported backend finishes a real attempt, not unavailable/error substitute");
                        compare(typeof outcome.iterations, "number", "VA FIT: actual iteration count is reported");
                        verify(Number.isFinite(outcome.iterations) && outcome.iterations >= 0,
                            "VA FIT: actual iteration report is finite without an invented optimum");
                        if (outcome.reduced_chi_square !== undefined)
                            verify(Number.isFinite(outcome.reduced_chi_square) && outcome.reduced_chi_square >= 0,
                                "VA FIT: reported actual objective is finite, not an expected golden");
                    }
                } else if (data.tag !== "manual-override") {
                    compare(outcome.status, "edited", "VA: actual ordinary native edit is committed truthfully");
                    if (data.tag === "wavelength") {
                        compare(wavelength[0].value, 1.49, "VA: actual supplied wavelength is typed exactly, no guessed intermediate");
                        compare(typed,0,"VA610: ordinary wavelength setter dispatches no scientific keys");
                        compare(scientificCues610.filter(c=>c.kind==="value" && c.path===wavelength[0].path).length,1,
                            "VA610: actual wavelength change follows ONE original exposed control cue");
                        compare(JSON.stringify(writes), JSON.stringify([1.49]), "VA: incomplete numeric drafts never become scientific intermediate writes");
                    } else {
                        compare(la.value, 0.6, "VA1: genuine original Analysis parameter changes through actual input");
                        if (data.tag === "analysis-value-free") {
                            compare(la.free, true, "VA1: actual visual-only free checkbox changes its own ParameterItem");
                            compare([typed,toggled],[0,0],"VA610: ordinary parameter methods dispatch neither scientific keys nor checkbox toggles");
                            compare(scientificCues610.filter(c=>c.kind==="value" && c.path===la.path).length,1);
                            compare(JSON.stringify(writes),JSON.stringify([0.6]),"VA610: one actual literal value effect, not a decorative missing callback");
                            compare(JSON.stringify(freeWrites610),JSON.stringify([true]),"VA610: one actual literal free effect, not a decorative cue");
                        }
                    }
                    if (data.tag === "default-off") compare(activeStarts, 0, "VA: default OFF keeps normal native behavior without fake pointer activity");
                    else verify(activeStarts > 0, "VA: enabled supported operation has an actual presentation interval");
                    Ui.click(this, Probe, window, "appBar.button.undo");
                    if (data.tag === "analysis-value-free") {
                        compare(la.free, originalFlag, "VA: first normal Undo restores actual checkbox edit");
                        Ui.click(this, Probe, window, "appBar.button.undo");
                    }
                    if (data.tag === "wavelength") compare(wavelength[0].value, originalWavelength, "VA: normal Undo restores actual original wavelength");
                    else compare(la.value, originalValue, "VA: normal Undo restores actual original edited value");
                    compare(visible185_values(project), originalValues,
                        "VA: normal Undo restores every original parameter value/free/SU, including unrelated state");
                }
                if (!fitCase) compare(project.currentStructure.scatteringLengths.count, 0,
                    "VA: nonfit actions and normal Undo preserve the selected built-in-table mode");
                compare(visible185_inputs(project), inputs, "VA: actual input never changes measured observations/sigmas/exclusions/weights/links");
                compare(Session.project, project, "VA: final action/report belongs to the same actual native owner");
            }
            verify(assistant.connected, "VA: genuine account survives own native input, Stop or project retirement");
            compare(JSON.stringify(Probe.rows(assistant.models).map(row => row.id)), JSON.stringify(accountRows),
                "VA: genuine managed catalog remains without login repair");
            if (data.tag === "manual-override") {
                mouseClick(item("assistant.toggle"));
                tryCompare(popup, "opened", true, 2000, "VA2: only the next real opener restores assistant after takeover");
                compare(Preferences.assistantShown, true, "VA2: explicit opener does not corrupt stored request");
            }
            if (data.tag === "analysis-value-free") visible185_capture("restored");
            console.log("VISIBLE185_RESULT", data.tag, JSON.stringify({typed: typed, toggled: toggled,
                scientificCues610:scientificCues610.map(c=>({path:c.path,kind:c.kind,before:c.before,rect:c.rect})),freeWrites610:freeWrites610,
                activeStarts: activeStarts, fitStarted: fitStarted, finished: finished, fitClicks: fitClicks,
                currentOwner: Session.project === project, connected: assistant.connected}));
        } finally {
            assistant.actionPointerMoved.disconnect(move610);assistant.actionPointerPressed.disconnect(press610);
            disconnect313(parameterLife313,editedParameter,"freeChanged",freePublication610);
            disconnect313(fieldLife313, field, "textEdited", typedReceipt);
            disconnect313(freeLife313, free, "toggled", freeReceipt);
            disconnect313(parameterLife313, editedParameter, "valueChanged", valueReceipt);
            disconnect313(fitButtonLife313, fitButton, "clicked", fitClickReceipt);
            assistant.showingActionsChanged.disconnect(activeReceipt);
            if (alive313(fitLife313)) {
                fitOwner313.runningChanged.disconnect(fitReceipt);
                fitOwner313.finished.disconnect(finishedReceipt);
                if (Session.project === project && fitOwner313.running) fitOwner313.cancel();
            }
            if (assistant.canCancel) assistant.cancel();
            for (const slot of timelineSlots) slot[0].disconnect(slot[1]);
            if (timelineEnabled) console.log("VISIBLE199_TIMELINE_SUMMARY", JSON.stringify({
                observedSignalsAndSamples: timelineCount, emittedBudget: timelineLimit,
                omitted: Math.max(0, timelineCount - timelineLimit)}));
        }
    }

    // GUI-DRAFT1: actual common controls and normal native request; no guard-property oracle.
    function draft226_core(project) {
        return JSON.stringify({values: visible185_values(project),
            labels: Probe.rows(project.currentStructure.atomSites).map(row => row.label),
            background: Probe.rows(project.currentExperiment.background).map(row => [row.id, row.position]),
            maxIterations: project.analysis.maxIterations,
            tolerance: project.analysis.chiSquareTolerance,
            aliases: Probe.rows(project.analysis.aliases),
            constraints: Probe.rows(project.analysis.constraints)});
    }
    function test_draft226_common_editor_preserves_user_work_data() {
        return ["normal-text-id", "visible-text-id", "normal-integer", "visible-integer",
            "normal-number", "visible-number", "normal-partial", "visible-partial",
            "normal-formatted", "visible-formatted",
            "normal-text-formatted", "visible-text-formatted"].map(tag => ({tag: tag}));
    }
    function test_draft226_common_editor_preserves_user_work(data) {
        verify(Session.openProject(Probe.repoUrl("docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project")),
            "DRAFT1 SETUP: genuine original complete measured project opens normally");
        const project = Session.project;
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment),
            10000, "DRAFT1 SETUP: actual native calculation settles, never a fake current flag");
        const wavelength = visible185_parameters(project).filter(row => row.name === "setup_wavelength");
        compare(wavelength.length, 1, "DRAFT1 SETUP: actual native request has one original wavelength");
        const textFormatted = data.tag.endsWith("text-formatted");
        const cell = visible185_parameters(project).filter(row => row.category === "cell" && row.name === "length_a");
        compare(cell.length, 1, "DRAFT1 SETUP: independent original cell target is unique");
        const target = textFormatted ? cell[0] : wavelength[0];
        const originalValue = target.value;
        const requestedValue = textFormatted ? 10.4 : 1.49;
        verify(originalValue !== requestedValue, "DRAFT1 SETUP: positive control must cause a real edit");
        compare(assistant.showActions, false, "DRAFT1: fresh process has actual default-OFF mode");
        toggle();
        assistant.signIn();
        visible185_ready("draft226-bootstrap");
        if (assistant.contextConsentRequired) assistant.signIn();
        visible185_ready("draft226-current-context");
        verify(!assistant.contextConsentRequired, "DRAFT1 SETUP: actual disclosed current input is approved");
        if (data.tag.startsWith("visible-")) {
            const show = item("assistant.showActions");
            verify(show.visible && show.enabled, "DRAFT1 SETUP: actual mode checkbox receives pointer input");
            mouseClick(show);
            compare(assistant.showActions, true, "DRAFT1 SETUP: visible route is genuinely enabled");
        }
        closeAssistant388();
        const textCase = data.tag.endsWith("text-id");
        visible185_page(textCase ? "structure" : textFormatted ? "experiment" : "analysis");
        if (textCase) {
            Ui.click(this, Probe, window, "sideBar.tab.basic");
            Ui.expandGroup(this, Probe, window, "group.atom_site");
        }
        if (!textCase && !textFormatted) {
            Ui.click(this, Probe, window, "sideBar.tab.extras");
            rendered();
            const group = Ui.control(Probe, window, "group.minimizer");
            verify(group !== null, "DRAFT1 SETUP: real minimizer group exists in Analysis Extra");
            if (group.collapsed) Ui.click(this, Probe, window, "group.minimizer");
        }
        if (textFormatted) {
            const background = Ui.control(Probe, window, "group.background");
            verify(background !== null, "DRAFT1 SETUP: actual existing line-segment background is available");
            if (background.collapsed) Ui.click(this, Probe, window, "group.background");
        }
        const name = textCase ? "atomSite.label.0" : textFormatted ? "background.position.0"
            : data.tag.endsWith("integer")
            ? "minimizer.maxIterations" : "minimizer.chiSquareTolerance";
        const candidates = [...new Set(Ui.itemsWithProperty(Ui.page(window), "objectName"))]
            .filter(control => control.objectName === name && Ui.inPane(control)
                && typeof control.text === "string" && typeof control.cursorPosition === "number"
                && control.editingFinished !== undefined && control.textEdited !== undefined
                && control.committed !== undefined);
        compare(candidates.length, 1, "DRAFT1 SETUP: genuine visual common editor identity is unique");
        const field = candidates[0];
        function premise237(stage) {
            try {
                const origin = field.mapToItem(window.contentItem, 0, 0);
                const ancestry = [];
                for (let parent = field.parent; parent; parent = parent.parent) {
                    const point = parent.mapToItem(window.contentItem, 0, 0);
                    ancestry.push({identity: String(parent), name: parent.objectName,
                        visible: parent.visible, enabled: parent.enabled, clip: parent.clip,
                        rect: [point.x, point.y, parent.width, parent.height],
                        collapsed: parent.collapsed === undefined ? null : parent.collapsed});
                }
                console.log("DRAFT237_PREMISE", data.tag, stage, JSON.stringify({
                    identity: String(field), name: field.objectName, candidates: candidates.length,
                    visible: field.visible, enabled: field.enabled, readOnly: field.readOnly,
                    text: field.text, activeFocus: field.activeFocus, inPane: Ui.inPane(field),
                    focusIdentity: String(window.activeFocusItem), focusIsField: window.activeFocusItem === field,
                    rect: [origin.x, origin.y, field.width, field.height],
                    clickPoint: Ui.clickPoint(field), ancestry: ancestry,
                    page: window.appBarCentralTabs.currentIndex, currentPage: String(Ui.page(window)),
                    tabs: Ui.itemsWithProperty(Ui.page(window), "objectName")
                        .filter(control => control.objectName.startsWith("sideBar.tab."))
                        .map(control => ({name: control.objectName, checked: control.checked,
                            visible: control.visible, enabled: control.enabled})),
                    sameOwner: Session.project === project, connected: assistant.connected,
                    lastError: assistant.lastError}));
            } catch (error) { console.log("DRAFT237_PREMISE_ERROR", stage, String(error)); }
        }
        premise237("before-scroll");
        try {
            Ui.scrollIntoView(field);
            rendered();
            verify(field.visible && field.enabled && !field.readOnly && Ui.exposed(field),
                "DRAFT1 SETUP: actual common editor is actionable inside the real viewport");
        } finally { premise237("after-viewport-check"); }
        const cleanControl = data.tag.endsWith("formatted");
        if (cleanControl) {
            Ui.click(this, Probe, window, name);
            premise237("post-click-before-keys");
            verify(field.activeFocus && window.activeFocusItem === field,
                "DRAFT1 SETUP: real delayed click focuses the exact original common editor before keys");
            visible185_type("0.3333333333333333");
            keyClick(Qt.Key_Return);
            const actual = textFormatted ? Probe.rows(project.currentExperiment.background)[0].position
                : project.analysis.chiSquareTolerance;
            compare(actual, 1 / 3,
                "DRAFT1 SETUP: real typing/Return establishes the explicit full-precision control");
            Ui.click(this, Probe, window, name);
            premise237("post-click-before-keys");
            verify(field.activeFocus && window.activeFocusItem === field,
                "DRAFT1 SETUP: real delayed click focuses the exact original common editor before keys");
            verify(field.text !== String(actual),
                "DRAFT1 SETUP: unedited formatted spelling actually differs from the core number");
        } else {
            Ui.click(this, Probe, window, name);
            premise237("post-click-before-keys");
            verify(field.activeFocus && window.activeFocusItem === field,
                "DRAFT1 SETUP: real delayed click focuses the exact original common editor before keys");
            const originalText = field.text;
            const draft = textCase ? "original_manual_site" : data.tag.endsWith("integer")
                ? "19" : data.tag.endsWith("partial") ? "-" : "0.25";
            verify(draft !== originalText, "DRAFT1 SETUP: actual dirty spelling differs from displayed value");
            const beforeTyping = draft226_core(project);
            visible185_type(draft);
            compare(field.text, draft, "DRAFT1 SETUP: real key input reaches the common editor");
            compare(draft226_core(project), beforeTyping,
                "DRAFT1 SETUP: typed text/id/integer/number remains genuinely uncommitted");
        }
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment),
            10000, "DRAFT1 SETUP: any genuine manual control edit has a current real calculation");
        // Public connected-context approval is setup, never an account repair or focus setter.
        if (assistant.contextConsentRequired) assistant.signIn();
        visible185_ready("draft226-before-send");
        verify(!assistant.contextConsentRequired && field.activeFocus,
            "DRAFT1 SETUP: real current account/input and original editor focus coexist");
        const core = draft226_core(project);
        const inputs = visible185_inputs(project);
        const beforeText = field.text;
        const beforeFocus = window.activeFocusItem;
        const selection = [field.selectionStart, field.selectionEnd];
        const beforePage = window.appBarCentralTabs.currentIndex;
        const beforeTier = ["basic", "extras", "text", "settings"].map(tier => {
            const button = Ui.control(Probe, window, "sideBar.tab." + tier);
            return button ? button.checked : null;
        });
        const beforeUndo = item("appBar.button.undo").enabled;
        const models = JSON.stringify(Probe.rows(assistant.models));
        const history = Probe.rows(assistant.messages).map(row => JSON.stringify(row));
        const requestPreviousIds = new Set(Probe.rows(assistant.messages).map(row => row.id));
        let finished = 0, committed = 0, navigated = 0, tiersChanged = 0;
        function finishReceipt() { ++finished; }
        function commitReceipt() { ++committed; }
        function pageReceipt() { ++navigated; }
        function tierReceipt() { ++tiersChanged; }
        const tierButtons = ["basic", "extras", "text", "settings"].map(tier =>
            Ui.control(Probe, window, "sideBar.tab." + tier)).filter(button => button !== null);
        field.editingFinished.connect(finishReceipt);
        field.committed.connect(commitReceipt);
        window.appBarCentralTabs.currentIndexChanged.connect(pageReceipt);
        for (const button of tierButtons) button.checkedChanged.connect(tierReceipt);
        try {
            assistant.send("Change " + (textFormatted ? "cell a" : "wavelength") + " to "
                + requestedValue + " while preserving my unrelated manual editor, " + data.tag);
            tryVerify(() => visible185_outcome("draft226-action-" + data.tag, requestPreviousIds) !== null
                && !assistant.canCancel && !assistant.showingActions,
                cleanControl && assistant.showActions
                    ? visible237_observationMs([{path: target.path, text: String(requestedValue)}]) : 10000,
                "DRAFT1: genuine original native request publishes and settles its own outcome");
            const outcome = visible185_outcome("draft226-action-" + data.tag, requestPreviousIds);
            if (cleanControl) {
                compare(outcome.status, "edited", "DRAFT1: unedited formatted value never blocks valid navigation/work");
                compare(target.value, requestedValue, "DRAFT1: actual requested native edit lands");
                compare(committed, 0, "DRAFT1: navigation cannot commit an unedited formatted number");
                compare(textFormatted ? Probe.rows(project.currentExperiment.background)[0].position
                    : project.analysis.chiSquareTolerance, 1 / 3,
                    "DRAFT1: formatting never silently rounds or rewrites the unrelated core value");
                Ui.click(this, Probe, window, "appBar.button.undo");
                compare(target.value, originalValue,
                    "DRAFT1: one normal Undo restores the original actual request value");
                compare(draft226_core(project), core, "DRAFT1: one Undo restores every baseline field/declaration");
            } else {
                verify(["refused", "unavailable"].includes(outcome.status)
                    && typeof outcome.message === "string" && outcome.message.length > 0,
                    "DRAFT1: original dirty common editor causes an honest before-write refusal");
                compare(draft226_core(project), core, "DRAFT1: no unrelated draft or native edit reaches core");
                compare(item("appBar.button.undo").enabled, beforeUndo,
                    "DRAFT1: blocked work neither consumes nor creates the ordinary Undo record");
                compare(field.text, beforeText, "DRAFT1: exact original uncommitted spelling survives");
                compare(window.activeFocusItem, beforeFocus, "DRAFT1: original real input is never blurred");
                compare(field.selectionStart, selection[0], "DRAFT1: original selection start survives");
                compare(field.selectionEnd, selection[1], "DRAFT1: original selection end survives");
                compare(finished, 0, "DRAFT1: no editingFinished event escapes before refusal");
                compare(committed, 0, "DRAFT1: no commit escapes before refusal");
                compare(navigated, 0, "DRAFT1: no transient page navigation precedes refusal");
                compare(tiersChanged, 0, "DRAFT1: no transient Main/Extra change precedes refusal");
                compare(window.appBarCentralTabs.currentIndex, beforePage, "DRAFT1: original page remains current");
                compare(JSON.stringify(["basic", "extras", "text", "settings"].map(tier => {
                    const button = Ui.control(Probe, window, "sideBar.tab." + tier);
                    return button ? button.checked : null;
                })), JSON.stringify(beforeTier), "DRAFT1: actual Main/Extra choice is unchanged");
            }
            verify(assistant.connected, "DRAFT1: native refusal/work preserves genuine managed account");
            compare(JSON.stringify(Probe.rows(assistant.models)), models, "DRAFT1: genuine catalog remains unchanged");
            verify(history.every(row => Probe.rows(assistant.messages).some(value => JSON.stringify(value) === row)),
                "DRAFT1: original retained conversation is not discarded to protect a draft");
            compare(visible185_inputs(project), inputs, "DRAFT1: original measured data/sigmas/masks/weights/links survive");
            compare(Session.project, project, "DRAFT1: outcome remains owned by the actual original Session project");
        } finally {
            console.log("DRAFT226_STATE", data.tag, JSON.stringify({
                currentOwner: Session.project === project, connected: assistant.connected,
                text: field.text, activeFocus: field.activeFocus, page: window.appBarCentralTabs.currentIndex,
                finished: finished, committed: committed, navigated: navigated, tiersChanged: tiersChanged,
                beforeUndo: beforeUndo, afterUndo: item("appBar.button.undo").enabled,
                lastError: assistant.lastError, showingActions: assistant.showingActions,
                outcome: visible185_outcome("draft226-action-" + data.tag, requestPreviousIds)}));
            field.editingFinished.disconnect(finishReceipt);
            field.committed.disconnect(commitReceipt);
            window.appBarCentralTabs.currentIndexChanged.disconnect(pageReceipt);
            for (const button of tierButtons) button.checkedChanged.disconnect(tierReceipt);
        }
    }
    function exposure229_pick(combo, index) {
        verify(combo !== null && combo.enabled && Ui.exposed(combo),
            "EXPOSURE SETUP: actual filter control receives the original mouse event");
        mouseClick(combo);
        tryCompare(combo.popup, "opened", true, 2000,
            "EXPOSURE SETUP: genuine filter popup opens before keyboard selection");
        keyClick(Qt.Key_Home);
        for (let row = 0; row < index; ++row) keyClick(Qt.Key_Down);
        keyClick(Qt.Key_Return);
        tryCompare(combo, "currentIndex", index, 2000,
            "EXPOSURE SETUP: actual keyboard selection reaches the requested existing option");
    }
    function test_exposure229_existing_manual_controls_data() {
        return ["visible-extra", "visible-filtered", "visible-offscreen", "normal-page",
            "assistant-fit-modal", "manual-fit-modal"].map(tag => ({tag: tag}));
    }
    function test_exposure229_existing_manual_controls(data) {
        const fitCase = data.tag.endsWith("fit-modal");
        const manualFit = data.tag === "manual-fit-modal";
        const visible = data.tag.startsWith("visible-");
        const fixture = fitCase ? "docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project"
            : "tests/fixtures/e04_t1/editable-project";
        verify(Session.openProject(Probe.repoUrl(fixture)),
            "EXPOSURE SETUP: independent original complete measured project opens");
        const project = Session.project;
        const parameters = visible185_parameters(project);
        let target = null;
        if (fitCase) {
            const cells = parameters.filter(parameter => parameter.category === "cell" && parameter.name === "length_a");
            compare(cells.length, 1, "EXPOSURE FIT SETUP: original independent cell is unique");
            target = cells[0];
            for (const parameter of parameters) parameter.free = false;
            target.free = true;
            project.currentExperiment.scale.free = true;
            project.analysis.maxIterations = 8; // Existing original bounded real-fit setup, not an optimum oracle.
        } else {
            const lengths = project.currentStructure.scatteringLengths;
            const custom = Probe.rows(lengths);
            compare(custom.length, 1, "EXPOSURE SETUP: literal original custom table has its one entry");
            compare(custom[0].typeSymbol, "La", "EXPOSURE SETUP: original custom entry is the fixture La row");
            compare(custom[0].lengthFm, 8.24, "EXPOSURE SETUP: fixture bytes retain their declared neutron length");
            for (let index = custom.length - 1; index >= 0; --index) lengths.remove(index);
            compare(lengths.count, 0, "EXPOSURE SETUP: genuine public empty custom map restores built-in data");
            if (data.tag === "visible-offscreen") {
                const matches = parameters.filter(parameter => parameter.name === "march_r");
                compare(matches.length, 1, "EXPOSURE SETUP: original declared orientation scalar is unique");
                target = matches[0];
            } else target = visible185_parameter(project, "La", "adp_iso");
            target.free = false;
        }
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment),
            10000, "EXPOSURE SETUP: actual original calculation and ordinary subset setup settle");
        if (fitCase) verify(project.fit.available,
            "EXPOSURE FIT SETUP: genuine current installed backend must admit the real worker");
        const beforeValues = visible185_values(project);
        const beforeInputs = visible185_inputs(project);
        const beforeDeclarations = JSON.stringify([Probe.rows(project.analysis.aliases), Probe.rows(project.analysis.constraints)]);
        const beforeValue = target.value;
        const requested = data.tag === "visible-offscreen" ? 0.9 : 0.6;
        if (!fitCase) verify(beforeValue !== requested,
            "EXPOSURE SETUP: original user request changes the actual current scalar");
        compare(assistant.showActions, false, "EXPOSURE: fresh real process keeps default OFF");
        toggle();
        assistant.signIn();
        visible185_ready("exposure-bootstrap");
        if (assistant.contextConsentRequired) assistant.signIn();
        visible185_ready("exposure-disclosed");
        verify(!assistant.contextConsentRequired, "EXPOSURE SETUP: genuine current disclosed context is approved");
        const models = JSON.stringify(Probe.rows(assistant.models));
        if (visible) {
            const show = item("assistant.showActions");
            verify(show.visible && show.enabled, "EXPOSURE SETUP: real checkbox is actionable");
            mouseClick(show);
            compare(assistant.showActions, true, "EXPOSURE SETUP: genuine pointer enables visible mode");
        }
        closeAssistant388();
        visible185_page("analysis");
        Ui.click(this, Probe, window, "sideBar.tab.basic");
        const table = Ui.control(Probe, window, "parameters.list");
        const group = Ui.control(Probe, window, "group.parameters");
        verify(table !== null && group !== null && table.sourceModel !== null,
            "EXPOSURE SETUP: original current Analysis table/filter model exists");
        const filter = table.sourceModel;
        const actualNameFilter = Ui.control(Probe, window, "parameters.nameFilter");
        verify(actualNameFilter !== null, "EXPOSURE SETUP: actual current Analysis name input is retained");
        if (data.tag === "visible-filtered") {
            const cellCategory = filter.categories.indexOf("cell");
            verify(cellCategory > 0, "EXPOSURE SETUP: actual public category list has the independent cell category");
            exposure229_pick(Ui.control(Probe, window, "parameters.category"), cellCategory);
            exposure229_pick(Ui.control(Probe, window, "parameters.variability"), 1);
            const name = Ui.control(Probe, window, "parameters.nameFilter");
            verify(name !== null && Ui.exposed(name), "EXPOSURE SETUP: genuine name filter is exposed");
            mouseClick(name);
            visible185_type("length_a");
            compare(filter.nameFilter, "length_a", "EXPOSURE SETUP: actual typed name filter is active");
            compare(filter.categoryFilter, "cell", "EXPOSURE SETUP: real category menu changed the filter");
            compare(filter.variability, 1, "EXPOSURE SETUP: real free-only menu changed the filter");
            verify(!filter.shows(target), "EXPOSURE SETUP: original requested target is genuinely excluded");
        }
        if (data.tag === "visible-offscreen") {
            // Establish the original matching/all-rows viewport through genuine existing controls.
            exposure229_pick(Ui.control(Probe, window, "parameters.category"), 0);
            exposure229_pick(Ui.control(Probe, window, "parameters.variability"), 0);
            const name = Ui.control(Probe, window, "parameters.nameFilter");
            mouseClick(name);
            visible185_type("");
            mouseWheel(table, table.width / 2, table.height / 2, 0, 120 * parameters.length);
            rendered();
            compare(filter.nameFilter, "", "EXPOSURE SETUP: offscreen witness has no name exclusion");
            compare(filter.categoryFilter, "", "EXPOSURE SETUP: offscreen witness has no category exclusion");
            compare(filter.variability, 0, "EXPOSURE SETUP: offscreen witness has no free-only exclusion");
            verify(filter.shows(target), "EXPOSURE SETUP: target actually belongs to the current filtered set");
            const exposed = Ui.itemsWithProperty(Ui.page(window), "item").filter(control =>
                control.item === target && control.objectName.startsWith("parameters.value.") && Ui.exposed(control));
            compare(exposed.length, 0, "EXPOSURE SETUP: requested genuine row is initially outside the actual viewport");
        }
        if (data.tag === "visible-extra" || data.tag === "normal-page" || data.tag === "assistant-fit-modal") {
            Ui.click(this, Probe, window, "sideBar.tab.extras");
            verify(Ui.control(Probe, window, "sideBar.tab.extras").checked,
                "EXPOSURE SETUP: actual manual Extra tier is selected before original work");
        }
        if (data.tag === "normal-page" || data.tag === "assistant-fit-modal") visible185_page("structure");
        let typed = 0, toggled = 0, filterTyped = 0, started = 0, finished = 0, automatic = 0, active = 0;
        let filterSpellings = [];
        function filterReceipt() { ++filterTyped; filterSpellings.push(actualNameFilter.text); }
        let observedFields = [], observedFree = [];
        function typedReceipt() { ++typed; }
        function freeReceipt() { ++toggled; }
        function observeControls() {
            for (const field of Ui.itemsWithProperty(Ui.page(window), "item")) {
                if (field.item !== target || !field.objectName.startsWith("parameters.value.")
                    || !Ui.exposed(field) || observedFields.includes(field)) continue;
                field.textEdited.connect(typedReceipt);
                observedFields.push(field);
            }
            for (const control of Ui.itemsWithProperty(Ui.page(window), "objectName")) {
                if (!control.objectName.startsWith("parameters.free.") || !Ui.exposed(control)
                    || observedFree.includes(control)) continue;
                for (let parent = control.parent; parent; parent = parent.parent) {
                    if (parent.parameter !== target) continue;
                    control.toggled.connect(freeReceipt);
                    observedFree.push(control);
                    break;
                }
            }
        }
        function startReceipt() { if (project.fit.running) ++started; }
        function finishedReceipt() { ++finished; }
        function automaticReceipt() { ++automatic; }
        function activeReceipt() { if (assistant.showingActions) ++active; observeControls(); }
        const slots = [[assistant.actionPointerShown, observeControls], [assistant.actionPointerMoved, observeControls],
            [assistant.actionPointerPressed, observeControls], [window.activeFocusItemChanged, observeControls],
            [assistant.showingActionsChanged, activeReceipt], [project.fit.runningChanged, startReceipt],
            [project.fit.finished, finishedReceipt], [project.fit.automaticResultsRequested, automaticReceipt],
            [actualNameFilter.textEdited, filterReceipt]];
        for (const slot of slots) slot[0].connect(slot[1]);
        const previousIds = new Set(Probe.rows(assistant.messages).map(row => row.id));
        const history = Probe.rows(assistant.messages).map(row => JSON.stringify(row));
        const call = "exposure229-action-" + data.tag;
        // Passive receipts on the original actual buttons; never navigate or retarget input here.
        const navSlots240 = [];
        let navCount240 = 0;
        const expectedPage240 = Ui.page(window);
        const pageButton240 = Ui.control(Probe, window, "appBar.tab.analysis");
        const mainButtons240 = Ui.itemsWithProperty(expectedPage240, "objectName")
            .filter(control => control.objectName === "sideBar.tab.basic");
        function nav240(stage, source) {
            if (data.tag !== "visible-extra" || navCount240 >= 48) return;
            ++navCount240;
            try {
                function fact(control) {
                    if (!control) return null;
                    const point = control.mapToItem(window.contentItem, 0, 0);
                    return {identity: String(control), name: control.objectName,
                        visible: control.visible, enabled: control.enabled, activeFocus: control.activeFocus,
                        pressed: control.pressed, down: control.down, checked: control.checked,
                        rect: [point.x, point.y, control.width, control.height], clickPoint: Ui.clickPoint(control)};
                }
                console.log("EXPOSURE240_NAV", data.tag, JSON.stringify({sequence: navCount240,
                    stage: stage, source: source, epochMs: Date.now(),
                    page: window.appBarCentralTabs.currentIndex, currentPage: String(Ui.page(window)),
                    expectedPage: String(expectedPage240), pageIsExpected: Ui.page(window) === expectedPage240,
                    pageButton: fact(pageButton240), mainButtons: mainButtons240.map(fact),
                    currentSidebarTabs: Ui.itemsWithProperty(Ui.page(window), "objectName")
                        .filter(control => control.objectName.startsWith("sideBar.tab."))
                        .map(fact), showActions: assistant.showActions,
                    showingActions: assistant.showingActions, canCancel: assistant.canCancel,
                    sameOwner: Session.project === project, connected: assistant.connected,
                    lastError: assistant.lastError}));
            } catch (error) { console.log("EXPOSURE240_NAV_ERROR", stage, String(error)); }
        }
        if (data.tag === "visible-extra") {
            for (const button of [pageButton240, ...mainButtons240]) {
                if (!button) continue;
                for (const name of ["pressedChanged", "released", "clicked", "checkedChanged"]) {
                    const signal = button[name];
                    if (!signal || !signal.connect) continue;
                    const label = String(button) + ":" + name;
                    const callback = () => nav240(name, label);
                    signal.connect(callback);
                    navSlots240.push([signal, callback]);
                }
            }
        }
        const results = item("fit.results");
        const error = item("fit.error");
        verify(!results.visible && !error.visible, "EXPOSURE SETUP: original fit dialogs are initially closed");
        try {
            nav240("before-original-action", null);
            if (visible) toggle();
            observeControls();
            if (manualFit) {
                Ui.click(this, Probe, window, "fitting.start");
                tryVerify(() => finished === 1 && !project.fit.running, 10000,
                    "EXPOSURE FIT: original manual Start produces one actual Worker completion");
            } else {
                visible185_ready("exposure-before-send");
                assistant.send(fitCase
                    ? "Run the actual current fit and retain assistant results in the conversation, " + data.tag
                    : "Set " + (data.tag === "visible-offscreen" ? "orientation march_r" : "La isotropic ADP")
                        + " to " + requested + " and make that same parameter free; reveal its existing controls, " + data.tag);
                tryVerify(() => visible185_outcome(call, previousIds) !== null
                    && !assistant.canCancel && !assistant.showingActions,
                    visible && !fitCase ? visible237_observationMs([
                        {path: target.path, text: String(requested)}, {path: target.path, text: ""}]) : 10000,
                    "EXPOSURE: original current RPC and actual owner settle without a stale historical substitute");
                const outcome = visible185_outcome(call, previousIds);
                if (fitCase) verify(["done", "max_iterations", "no_step"].includes(outcome.status),
                    "EXPOSURE FIT: real native attempt finishes honestly, without invented optimum or unavailable substitute");
                else compare(outcome.status, "edited", "EXPOSURE: original native operation is genuinely applied and confirmed");
            }
            compare(window.appBarCentralTabs.currentIndex, 4,
                "EXPOSURE: original parameter/free/fit action follows the existing Analysis page");
            verify(Ui.control(Probe, window, "sideBar.tab.basic").checked,
                "EXPOSURE: the genuine requested current Analysis Main tier is selected");
            if (fitCase) {
                verify(started > 0 && finished === 1 && !project.fit.running,
                    "EXPOSURE FIT: actual worker start and final report precede presentation assertions");
                verify(Probe.rows(project.fit.results).length > 0,
                    "EXPOSURE FIT SETUP: actual supported final report has real ordinary result rows");
                if (manualFit) {
                    compare(automatic, 1, "EXPOSURE MODAL: genuine manual fitting retains one automatic result notification");
                    tryCompare(results, "opened", true, 2000,
                        "EXPOSURE MODAL: genuine manual result opens the existing actual dialog");
                    const ok = results.standardButton(Dialog.Ok);
                    verify(ok !== null && ok.visible && ok.enabled, "EXPOSURE MODAL: actual dialog acknowledgement exists");
                    mouseClick(ok);
                    tryCompare(results, "visible", false, 2000, "EXPOSURE MODAL: real acknowledgement closes the dialog");
                } else {
                    compare(automatic, 0, "EXPOSURE MODAL: assistant-owned fit does not emit a manual automatic popup request");
                    verify(!results.visible && !error.visible,
                        "EXPOSURE MODAL: actual assistant fit settles without either automatic result/error dialog");
                }
                if (project.fit.canUndo) {
                    Ui.click(this, Probe, window, "appBar.button.undo");
                    compare(visible185_values(project), beforeValues,
                        "EXPOSURE FIT: ordinary actual fit Undo restores the complete original subset/state");
                }
            } else {
                compare(target.value, requested, "EXPOSURE: original requested value reaches exact current ParameterItem");
                compare(target.free, true, "EXPOSURE: actual original free flag reaches the same current ParameterItem");
                if (visible) {
                    verify(active > 0 && typed > 0 && toggled === 1,
                        "EXPOSURE: genuine visible typing and one real checkbox toggle accompany the scientific edits");
                    const currentField = visible185_field(target);
                    const currentFree = visible185_free(target);
                    verify(currentField.item === target && Ui.exposed(currentFree),
                        "EXPOSURE: actual final visible controls bind the exact original requested owner");
                    compare(filter.nameFilter, target.path,
                        "EXPOSURE: the real name filter contains the exact original requested ParameterItem path");
                    compare(actualNameFilter.text, target.path,
                        "EXPOSURE: actual displayed filter and public model agree on that exact path");
                    verify(filterTyped > 0 && filterSpellings.includes(target.path),
                        "EXPOSURE: genuine original filter key input reaches the exact requested path");
                    compare(filter.categoryFilter, "", "EXPOSURE: genuine category filter is cleared to reveal requested row");
                    compare(filter.variability, 0, "EXPOSURE: genuine free-only filter is cleared to reveal requested row");
                } else compare(active, 0, "EXPOSURE: normal OFF page following does not manufacture pointer presentation");
                Ui.click(this, Probe, window, "appBar.button.undo");
                compare(target.free, false, "EXPOSURE: first real normal Undo restores the original free flag");
                Ui.click(this, Probe, window, "appBar.button.undo");
                compare(target.value, beforeValue, "EXPOSURE: second real normal Undo restores the requested value");
                compare(visible185_values(project), beforeValues,
                    "EXPOSURE: complete actual Undo preserves every unrelated value/free/SU");
            }
            compare(visible185_inputs(project), beforeInputs,
                "EXPOSURE: original observations/sigmas/masks/weights/links are unchanged");
            compare(JSON.stringify([Probe.rows(project.analysis.aliases), Probe.rows(project.analysis.constraints)]),
                beforeDeclarations, "EXPOSURE: original scientific declarations are preserved");
            verify(Session.project === project && assistant.connected,
                "EXPOSURE: genuine actual current owner and managed account survive");
            compare(JSON.stringify(Probe.rows(assistant.models)), models, "EXPOSURE: genuine catalog survives without login repair");
            verify(history.every(row => Probe.rows(assistant.messages).some(value => JSON.stringify(value) === row)),
                "EXPOSURE: original retained history is not discarded during navigation/work");
        } finally {
            nav240("after-original-action", null);
            for (const slot of navSlots240) {
                try { slot[0].disconnect(slot[1]); }
                catch (error) { console.log("EXPOSURE240_NAV_DISCONNECT", String(error)); }
            }
            console.log("EXPOSURE229_STATE", data.tag, JSON.stringify({
                currentOwner: Session.project === project, connected: assistant.connected,
                page: window.appBarCentralTabs.currentIndex, showingActions: assistant.showingActions,
                canCancel: assistant.canCancel, lastError: assistant.lastError,
                target: {path: target.path, value: target.value, free: target.free},
                typed: typed, toggled: toggled, filterTyped: filterTyped, filterSpellings: filterSpellings,
                active: active, started: started, finished: finished,
                automatic: automatic, resultsVisible: results.visible, errorVisible: error.visible,
                filter: {name: filter.nameFilter, category: filter.categoryFilter, variability: filter.variability},
                originalOutcome: manualFit ? null : visible185_outcome(call, previousIds)}));
            for (const slot of slots) slot[0].disconnect(slot[1]);
            for (const field of observedFields) if (field) field.textEdited.disconnect(typedReceipt);
            for (const control of observedFree) if (control) control.toggled.disconnect(freeReceipt);
        }
    }
    function slider231_curves(project) {
        const chart = ChartOracle.object(Ui.page(window), "chart");
        const rows = Probe.rows(project.currentExperiment.pattern);
        const byX = new Map(rows.map(row => [row.x, row]));
        const roles = {calc: "intensityCalc", bkg: "intensityBkg", resid: "residual"};
        const curves = {};
        for (const kind of ["calc", "bkg", "resid"]) {
            const points = ChartOracle.points(ChartOracle.object(chart, "chart.series." + kind));
            let finite = 0;
            for (const point of points) {
                if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) continue;
                const row = byX.get(point.x);
                if (!row || row[roles[kind]] !== point.y)
                    return {consistent: false, kind: kind, x: point.x, points: points.length};
                ++finite;
            }
            if (!finite) return {consistent: false, kind: kind, points: points.length};
            curves[kind] = points;
        }
        return {consistent: true, signature: JSON.stringify(curves),
            counts: Object.keys(curves).map(kind => curves[kind].length)};
    }
    function test_slider231_real_manual_publication_persists_data() {
        return ["native-platform", "clean-tab-focus", "full-precision", "dirty-valid", "dirty-invalid"].map(tag => ({tag: tag}));
    }
    function test_slider231_real_manual_publication_persists(data) {
        const fixture = "docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project";
        verify(Session.openProject(Probe.repoUrl(fixture)),
            "SLIDER SETUP: actual original complete measured project opens");
        const project = Session.project;
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment),
            10000, "SLIDER SETUP: actual original native calculation settles");
        compare(assistant.showActions, false, "SLIDER: genuine fresh process keeps assistant mode OFF");
        toggle();
        assistant.signIn();
        visible185_ready("slider-bootstrap");
        if (assistant.contextConsentRequired) assistant.signIn();
        visible185_ready("slider-disclosed");
        verify(!assistant.contextConsentRequired, "SLIDER SETUP: genuine current context is approved");
        closeAssistant388();
        visible185_page("analysis");
        Ui.click(this, Probe, window, "sideBar.tab.basic");
        const name = Ui.control(Probe, window, "parameters.nameFilter");
        verify(name !== null && Ui.exposed(name), "SLIDER SETUP: actual name filter is exposed");
        mouseClick(name);
        visible185_type("length_");
        rendered();
        const parameters = visible185_parameters(project);
        const matches = parameters.filter(parameter => parameter.category === "cell" && parameter.name === "length_a");
        const others = parameters.filter(parameter => parameter.category === "cell" && parameter.name === "length_b");
        compare(matches.length, 1, "SLIDER SETUP: original requested cell-a identity is unique");
        compare(others.length, 1, "SLIDER SETUP: a genuine different current row exists");
        const target = matches[0];
        const other = others[0];
        const originalValue = target.value;
        const group = Ui.control(Probe, window, "group.parameters");
        const field = visible185_field(target);
        const slider = Ui.control(Probe, window, "parameters.slider");
        verify(slider !== null && slider.enabled && Ui.exposed(slider),
            "SLIDER SETUP: original selected row has its actual exposed slider");
        const nativeFocusPolicy = slider.focusPolicy;
        // Pinned Qt6.11.2 QQuickSlider constructor: macOS TabFocus; other platforms StrongFocus.
        // Declare that public focus policy BEFORE input; never force the field after a slider event.
        if (data.tag !== "native-platform") slider.focusPolicy = Qt.TabFocus;
        const declaredFocusPolicy = slider.focusPolicy;
        if (data.tag !== "native-platform") compare(declaredFocusPolicy, Qt.TabFocus,
            "SLIDER SETUP: explicit pinned macOS focus contract is declared before genuine input");
        verify(field.enabled && !field.readOnly, "SLIDER SETUP: original current numeric cell is editable");
        const originalUndo = {project: project.canUndo, button: item("appBar.button.undo").enabled};
        let draftEdits = 0;
        function draftReceipt() { ++draftEdits; }
        field.textEdited.connect(draftReceipt);
        try {
            mouseClick(field);
            verify(field.activeFocus && group.selected === target,
                "SLIDER SETUP: original actual row selection has real editor focus");
            if (data.tag === "full-precision") {
                visible185_type("10.333333333333334");
                keyClick(Qt.Key_Return);
                compare(target.value, 10.333333333333334,
                    "SLIDER SETUP: real original user typing establishes its full-precision value");
                verify(Number(field.value) !== target.value,
                    "SLIDER SETUP: actual rounded display genuinely differs from full stored value");
            } else if (data.tag.startsWith("dirty-")) {
                const draft = data.tag === "dirty-valid" ? "10.32" : "not-a-number";
                const beforeTyping = visible185_values(project);
                visible185_type(draft);
                compare(field.text, draft, "SLIDER DRAFT: actual user spelling reaches the original field");
                compare(visible185_values(project), beforeTyping,
                    "SLIDER DRAFT: genuine typing is still uncommitted before original manual focus handoff");
                verify(draftEdits > 0, "SLIDER DRAFT: real textEdited distinguishes a user draft from formatting");
                verify(field.activeFocus && !slider.enabled,
                    "SLIDER DRAFT: actual pending same-parameter user draft disables the real slider without discarding text");
                compare(field.text, draft, "SLIDER DRAFT: displayed typed spelling remains owned until ordinary commit/refusal");
                keyClick(Qt.Key_Tab);
                tryCompare(slider, "enabled", true, 2000,
                    "SLIDER DRAFT: ordinary explicit focus handoff resolves the draft and restores the real control");
                if (data.tag === "dirty-valid") {
                    compare(target.value, 10.32,
                        "SLIDER DRAFT: ordinary genuine manual Tab commits a valid typed draft");
                    compare(field.refusal, "", "SLIDER DRAFT: valid actual input is not falsely refused");
                } else {
                    compare(target.value, originalValue,
                        "SLIDER DRAFT: invalid original user text never becomes a scientific value");
                    verify(typeof field.refusal === "string" && field.refusal.length > 0,
                        "SLIDER DRAFT: invalid input retains an actual honest refusal");
                }
            }
            tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment)
                && slider231_curves(project).consistent, 10000,
                "SLIDER SETUP: genuine committed input and actual plotted/model columns agree");
            rendered();
            mouseClick(field);
            verify(field.activeFocus && group.selected === target,
                "SLIDER SETUP: clean original full-value editor focus is genuine, never forced");
            compare(Number(field.text), target.value,
                "SLIDER SETUP: focused clean text is the authoritative full-precision current number");
            compare(project.canUndo, originalUndo.project,
                "SLIDER HISTORY: ordinary typed commit/refusal preserves the prior public Undo availability");
            compare(item("appBar.button.undo").enabled, originalUndo.button,
                "SLIDER HISTORY: ordinary typed input cannot manufacture a recorded Undo step");
            const beforeSliderValues = visible185_values(project);
            const beforeSlider = target.value;
            const beforeCurves = slider231_curves(project);
            const inputs = visible185_inputs(project);
            const models = JSON.stringify(Probe.rows(assistant.models));
            const history = JSON.stringify(Probe.rows(assistant.messages));
            const declarations = JSON.stringify([Probe.rows(project.analysis.aliases), Probe.rows(project.analysis.constraints)]);
            verify(slider.enabled && Ui.exposed(slider),
                "SLIDER SETUP: resolved clean focus keeps the actual slider enabled");
            compare(slider.value, beforeSlider, "SLIDER SETUP: real slider belongs to the original selected parameter");
            let moved = 0, edited = 0;
            let writes = [];
            function moveReceipt() { ++moved; }
            function textReceipt() { ++edited; }
            function valueReceipt() {
                writes.push(target.value);
            }
            slider.moved.connect(moveReceipt);
            field.textEdited.connect(textReceipt);
            target.valueChanged.connect(valueReceipt);
            try {
                const startX = slider.handle.x + slider.handle.width / 2;
                const endX = slider.leftPadding + slider.handle.width / 2
                    + 0.7 * (slider.availableWidth - slider.handle.width);
                verify(Math.abs(startX - endX) > 1,
                    "SLIDER SETUP: actual original handle and requested drag end are distinct screen points");
                mousePress(slider, startX, slider.height / 2);
                try {
                    if (data.tag !== "native-platform") verify(field.activeFocus,
                        "SLIDER FOCUS SETUP: declared TabFocus press genuinely retains original clean field focus");
                    mouseMove(slider, endX, slider.height / 2);
                    if (data.tag !== "native-platform") verify(field.activeFocus,
                        "SLIDER FOCUS SETUP: original clean editor remains focused during genuine slider publication");
                } finally {
                    mouseRelease(slider, endX, slider.height / 2);
                }
                const changed = target.value;
                verify(moved > 0 && writes.length > 0 && changed !== beforeSlider,
                    "SLIDER: genuine pointer slider input actually changes the selected scientific parameter");
                compare(changed, slider.value, "SLIDER: actual selected core value agrees with the real moved control");
                if (field.activeFocus) compare(Number(field.text), changed,
                    "SLIDER: focused clean numeric display immediately follows authoritative slider publication");
                else compare(field.text, field.value,
                    "SLIDER: actual native platform focus handoff keeps the normal current display binding");
                compare(edited, 0, "SLIDER: programmatic publication/formatting is not fabricated user text input");
                tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment)
                    && slider231_curves(project).consistent, 10000,
                    "SLIDER: actual current model columns and rendered calc/background/residual agree after input");
                const afterCurves = slider231_curves(project);
                verify(afterCurves.signature !== beforeCurves.signature,
                    "SLIDER: original cell change genuinely publishes a changed plotted calculation");
                const writesAfterDrag = writes.length;
                keyClick(Qt.Key_Tab);
                verify(!field.activeFocus, "SLIDER: actual Tab leaves the original numeric editor");
                compare(target.value, changed, "SLIDER: Tab cannot submit stale clean text over the changed core value");
                compare(field.text, field.value, "SLIDER: unfocused row uses its actual current formatted display");
                compare(writes.length, writesAfterDrag, "SLIDER: clean focus loss creates no second scientific edit");
                const otherField = visible185_field(other);
                verify(otherField.enabled && Ui.exposed(otherField),
                    "SLIDER SETUP: real different row is actionable before the original row switch");
                mouseClick(otherField);
                compare(group.selected, other, "SLIDER: actual pointer selects a genuinely different parameter row");
                compare(target.value, changed, "SLIDER: switching rows cannot restore the obsolete original value");
                compare(field.text, field.value, "SLIDER: old row still displays its authoritative current value");
                compare(writes.length, writesAfterDrag, "SLIDER: row switch does not invent an old-value write");
                tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment)
                    && slider231_curves(project).consistent, 10000,
                    "SLIDER: retained current plotted/model result survives actual Tab and row navigation");
                compare(slider231_curves(project).signature, afterCurves.signature,
                    "SLIDER: original changed chart persists instead of reverting after focus/selection changes");
                const expectedValues = JSON.parse(beforeSliderValues);
                const expectedTarget = expectedValues.find(row => row[0] === target.path);
                verify(expectedTarget !== undefined, "SLIDER SETUP: captured exact target belongs to the public prestate");
                expectedTarget[1] = changed;
                compare(visible185_values(project), JSON.stringify(expectedValues),
                    "SLIDER: only the actual selected scalar changes; unrelated values/free/SUs stay intact");
                compare(project.canUndo, originalUndo.project,
                    "SLIDER HISTORY: ordinary unrecorded slider input preserves prior public Undo availability");
                compare(item("appBar.button.undo").enabled, originalUndo.button,
                    "SLIDER HISTORY: actual pointer input/Tab/row switch creates no phantom recorded Undo step");
                compare(visible185_inputs(project), inputs,
                    "SLIDER: original observations/sigmas/masks/weights/links are preserved");
                compare(JSON.stringify([Probe.rows(project.analysis.aliases), Probe.rows(project.analysis.constraints)]),
                    declarations, "SLIDER: original scientific declarations are not changed by manual input");
                verify(Session.project === project && assistant.connected,
                    "SLIDER: original actual owner and genuine managed account survive all manual actions");
                compare(JSON.stringify(Probe.rows(assistant.models)), models, "SLIDER: genuine catalog is preserved");
                compare(JSON.stringify(Probe.rows(assistant.messages)), history,
                    "SLIDER: ordinary manual input does not rewrite retained conversation history");
            } finally {
                console.log("SLIDER231_STATE", data.tag, JSON.stringify({
                    currentOwner: Session.project === project, connected: assistant.connected,
                    nativeFocusPolicy: nativeFocusPolicy, declaredFocusPolicy: declaredFocusPolicy,
                    originalUndo: originalUndo, currentUndo: {project: project.canUndo, button: item("appBar.button.undo").enabled},
                    fieldText: field.text, fieldDisplay: field.value, fieldFocused: field.activeFocus,
                    selectedPath: group.selected ? group.selected.path : null, targetPath: target.path,
                    targetValue: target.value, beforeSlider: beforeSlider, sliderValue: slider.value,
                    moved: moved, writes: writes, userTextEditsDuringDrag: edited, draftTextEdits: draftEdits,
                    calculating: project.calculating, computedCurrent: Probe.computedCurrent(project.currentExperiment),
                    chart: slider231_curves(project).counts, lastError: project.lastError}));
                slider.moved.disconnect(moveReceipt);
                field.textEdited.disconnect(textReceipt);
                target.valueChanged.disconnect(valueReceipt);
            }
        } finally { field.textEdited.disconnect(draftReceipt); }
    }
    function test_sl1_233_focus_targeted_input_retires_original_work_data() {
        return ["helper-preedit", "helper-commit", "helper-key", "helper-query",
            "gap-preedit", "gap-commit", "gap-key", "gap-query"].map(tag => ({tag: tag}));
    }
    function test_sl1_233_focus_targeted_input_retires_original_work(data) {
        const gap = data.tag.startsWith("gap-");
        const query = data.tag.endsWith("query");
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")),
            "SL1 SETUP: original complete measured native project opens");
        const project = Session.project;
        const lengths = project.currentStructure.scatteringLengths;
        const custom = Probe.rows(lengths);
        compare(custom.length, 1, "SL1 SETUP: original fixture retains its literal custom table");
        compare(custom[0].typeSymbol, "La", "SL1 SETUP: original custom replacement is the La entry");
        compare(custom[0].lengthFm, 8.24, "SL1 SETUP: independent fixture literal is unchanged");
        for (let index = custom.length - 1; index >= 0; --index) lengths.remove(index);
        compare(lengths.count, 0, "SL1 SETUP: genuine public empty custom map selects full built-in data");
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment),
            10000, "SL1 SETUP: actual original native calculation settles");
        const target = visible185_parameter(project, "La", "adp_iso");
        const originalValue = target.value;
        verify(originalValue !== 0.6, "SL1 SETUP: delegated original value would cause a distinct real edit");
        const inputs = visible185_inputs(project);
        const values = visible185_values(project);
        const declarations = JSON.stringify([Probe.rows(project.analysis.aliases), Probe.rows(project.analysis.constraints)]);
        toggle();
        assistant.signIn();
        visible185_ready("sl1-bootstrap");
        if (assistant.contextConsentRequired) assistant.signIn();
        visible185_ready("sl1-disclosed");
        verify(!assistant.contextConsentRequired, "SL1 SETUP: genuine current disclosed context is approved");
        const show = item("assistant.showActions");
        verify(show.visible && show.enabled, "SL1 SETUP: actual Show actions checkbox receives input");
        mouseClick(show);
        compare(assistant.showActions, true, "SL1 SETUP: genuine visible mode is enabled");
        closeAssistant388();
        visible185_page("analysis");
        Ui.click(this, Probe, window, "sideBar.tab.basic");
        const name = Ui.control(Probe, window, "parameters.nameFilter");
        verify(name !== null && Ui.exposed(name), "SL1 SETUP: original manual name input is exposed");
        mouseClick(name);
        visible185_type("adp_iso");
        rendered();
        const field = visible185_field(target);
        mouseClick(field);
        verify(field.activeFocus && window.activeFocusItem === field,
            "SL1 SETUP: actual original Quick input has genuine current Main focus");
        const previousIds = new Set(Probe.rows(assistant.messages).map(row => row.id));
        const history = Probe.rows(assistant.messages).map(row => JSON.stringify(row));
        const models = JSON.stringify(Probe.rows(assistant.models));
        const call = "sl1-233-original-" + data.tag;
        const pointer = item("assistant.actionPointer");
        let takeovers = 0, userEdits = 0, preedits = 0, ownStarts = 0;
        function takeoverReceipt() { ++takeovers; }
        function editedReceipt() { ++userEdits; }
        function preeditReceipt() { ++preedits; }
        function pointerReceipt() { ++ownStarts; }
        assistant.actionManualTakeover.connect(takeoverReceipt);
        assistant.actionPointerShown.connect(pointerReceipt);
        field.textEdited.connect(editedReceipt);
        field.preeditTextChanged.connect(preeditReceipt);
        let receipt = null, retainedText = null, retainedPreedit = null;
        try {
            visible185_ready("sl1-before-send");
            assistant.send(gap ? "Inspect original current parameters, then wait for my next instruction"
                : "Change original La isotropic ADP to 0.6 through its actual manual controls");
            if (gap) {
                tryVerify(() => visible185_outcome(call, previousIds) !== null
                    && assistant.canCancel && !assistant.showingActions && ownStarts === 0
                    && pointer.opacity === 0, 10000,
                    "SL1 GAP SETUP: genuine original read reply is retained while the real request waits without helper pointer");
                compare(ownStarts, 0, "SL1 GAP SETUP: no helper ran during this actual read-only request interval");
            } else {
                tryVerify(() => assistant.canCancel && assistant.showingActions && field.activeFocus
                    && field.text !== field.editText && field.text !== field.value, visible237_observationMs([{path: target.path, text: "0.6"}]),
                    "SL1 HELPER SETUP: original actual paced partial input is active before the user event");
                verify(assistant.showingActions && ownStarts > 0 && pointer.opacity > 0 && Ui.rendered(pointer),
                    "SL1 HELPER SETUP: actual painted pointer/helper interval is genuinely reached");
            }
            verify(window.activeFocusItem === field && field.activeFocus,
                "SL1 SETUP: sender addresses original focused Quick item, not its window substitute");
            compare(target.value, originalValue, "SL1 SETUP: helper final Return has not written before intervention");
            const beforeText = field.text;
            const beforePreedit = field.preeditText;
            const beforeEdits = userEdits;
            const beforePreedits = preedits;
            const gapOutcome = gap ? JSON.stringify(visible185_outcome(call, previousIds)) : null;
            if (query) receipt = Probe.focusedInputMethodQuery233(window, field);
            else if (data.tag.endsWith("preedit")) receipt = Probe.focusedInputMethod233(window, field, "733", "");
            else if (data.tag.endsWith("commit")) receipt = Probe.focusedInputMethod233(window, field, "", "7");
            else receipt = Probe.focusedForwardedDigit233(window, field, "8");
            verify(receipt.delivered && receipt.targetAlive,
                "SL1 SETUP: actual bounded Qt event was delivered to original live focused input");
            if (query) {
                compare(takeovers, 0, "SL1 QUERY: nonediting query cannot become manual takeover");
                verify(assistant.canCancel, "SL1 QUERY: actual original request remains active after inert query");
                compare(field.text, beforeText, "SL1 QUERY: original text is untouched");
                compare(field.preeditText, beforePreedit, "SL1 QUERY: query neither starts nor clears composition");
                compare(target.value, originalValue, "SL1 QUERY: query cannot write a scientific value");
            } else {
                if (!gap) {
                    verify(takeovers > 0, "SL1 HELPER: original focused input invokes active-helper manual takeover");
                    verify(window.assistantManualTakeover,
                        "SL1 HELPER: actual Main retains manual controls for original user event");
                }
                if (data.tag.endsWith("preedit")) {
                    compare(field.preeditText, "733", "SL1: exact original composition reaches the actual field");
                    verify(preedits > beforePreedits, "SL1: original Qt preedit notification is genuinely new");
                } else verify(field.text.includes(data.tag.endsWith("commit") ? "7" : "8") && userEdits > beforeEdits,
                    "SL1: exact original commit/forwarded key reaches genuine user text signal");
                retainedText = field.text;
                retainedPreedit = field.preeditText;
            }
            const retirementDeadline480=Date.now()+10000; // Share original post-input retirement allowance across operation and explicit Stop.
            verify(assistant.canCancel,"ONLYSTOP480: actual ordinary/conflicting focused input leaves the original official turn ACTIVE");
            if (!gap && !query) {
                tryVerify(() => visible185_outcome(call,previousIds)!==null && !assistant.showingActions
                    && assistant.canCancel,Math.max(0,retirementDeadline480-Date.now()),
                    "ONLYSTOP480: conflicting input settles ONLY its original operation, never the held official turn");
                verify(visible185_outcome(call,previousIds).status!=="edited",
                    "ONLYSTOP480: superseded partial original operation cannot invent a completed scientific edit");
            }
            if (!query) {
                compare(field.text,retainedText,"SL1: before Stop no late helper cleanup overwrites genuine user draft");
                compare(field.preeditText,retainedPreedit,"SL1: before Stop original composition is retained exactly");
                verify(field.activeFocus && window.activeFocusItem===field,
                    "SL1: before Stop original real focused event target retains actual focus");
            }
            compare(visible185_values(project),values,
                "SL1: BEFORE real Stop, focused user input without Return makes NO scientific mutation");
            const fieldLife482=lifetime313(field),targetLife482=lifetime313(target);
            const draft482=field.text,preedit482=field.preeditText,undoBefore482=project.canUndo;
            const lo482=Math.min(field.selectionStart,field.selectionEnd),hi482=Math.max(field.selectionStart,field.selectionEnd);
            const committedIme482=draft482.slice(0,lo482)+preedit482+draft482.slice(hi482);
            let lostFocus482=0,terminals482=0,recordStop482=true;
            const stopWrites482=[];
            function focus482(){if(recordStop482 && !field.activeFocus)++lostFocus482;}
            function terminal482(){if(recordStop482)++terminals482;}
            function write482(){if(recordStop482){
                verify(alive313(fieldLife482) && alive313(targetLife482) && field.item===target,
                    "STOP482: actual terminal write observer retains original live field/parameter");
                stopWrites482.push({value:target.value,text:field.text});
            }}
            field.activeFocusChanged.connect(focus482);field.editingFinished.connect(terminal482);
            target.valueChanged.connect(write482);
            try {
            const beforeStop480=Probe.readReferenceFile("original-client-lines.jsonl").trim();
            verify(beforeStop480.length>0,"ONLYSTOP480: original owned peer trace exists BEFORE explicit Stop");
            const requests480=beforeStop480.split("\n").map(line=>JSON.parse(line));
            compare(requests480.filter(row=>row.method==="turn/interrupt").length,0,
                "ONLYSTOP480: genuine user input emitted ZERO whole-turn interrupts before Stop");
            // Original inert query can open chat without committing any draft; other rows retain manual focus.
            if (gap && query) toggle();
            const stopName480=gap && query ? "assistant.stop" : "assistant.stopVisibleAction";
            const stop480=item(stopName480), stopLife480=lifetime313(stop480);
            verify(stop480.visible && stop480.enabled && Ui.exposed(stop480),
                "ONLYSTOP480: existing sidebar/status AI Stop is a genuine exposed native action");
            let stopClicks480=0;
            function stopClicked480(){++stopClicks480;}
            stop480.clicked.connect(stopClicked480);
            try {
                const point480=Ui.clickPoint(stop480);
                verify(point480!==null,"ONLYSTOP480: exact original Stop has a real native input point");
                mouseClick(stop480,point480.x,point480.y);
                compare(stopClicks480,1,"ONLYSTOP480: ONE real native AI Stop click authorizes official interruption");
            } finally {disconnect313(stopLife480,stop480,"clicked",stopClicked480);}
            console.log("ONLYSTOP480_NATIVE",JSON.stringify({case:data.tag,stop:stopName480,
                clicks:stopClicks480,preStopInterrupts:0,preStopRequests:requests480.length,
                sameOwner:Session.project===project,controller:Session.assistant===assistant}));
            tryVerify(() => !assistant.canCancel && !assistant.showingActions,Math.max(0,retirementDeadline480-Date.now()),
                "ONLYSTOP480: original official turn retires AFTER actual explicit AI Stop");
            rendered();

            verify(alive313(fieldLife482) && alive313(targetLife482) && field.item===target && Session.project===project,
                "STOP482: ordinary native Stop transition retains original live editor/parameter owner");
            verify(stopWrites482.length<=1,"STOP482: one ordinary editor terminal cannot duplicate a scientific write");
            if(query)compare(stopWrites482.length,0,"STOP482: inert query plus Stop cannot commit an assistant partial draft");
            for(const write of stopWrites482){
                verify(!query && (lostFocus482>0 || terminals482>0),
                    "STOP482: post-Stop scientific write needs an ACTUAL ordinary editor focus/terminal event");
                verify(write.text===draft482 || (preedit482.length>0 && write.text===committedIme482),
                    "STOP482: only original genuine draft/IME selection replacement may be committed, never stale helper spelling");
                verify(/^[0-9]+(?:\.[0-9]*)?$/.test(write.text) && Number.isFinite(Number(write.text)),
                    "STOP482: actual terminal operand is the independently finite decimal user draft");
                compare(write.value,Number(write.text),"STOP482: ordinary manual terminal commits its exact original numeric operand");
            }
            if(query){
                compare(target.value,originalValue,"STOP482: query cannot authorize committing an assistant draft");
                verify(field.text===field.value || field.text===field.editText,
                    "STOP482: explicit Stop restores clean authoritative formatting for non-manual query case");
                compare(field.preeditText,beforePreedit,"STOP482: inert query and ordinary Stop do not create composition");
            }else if(lostFocus482===0 && terminals482===0){
                compare(field.text,draft482,"STOP482: no native terminal means no overwrite of original draft");
                compare(field.preeditText,preedit482,"STOP482: no native terminal means no loss of original composition");
            }else if(field.inputMethodComposing){
                compare(stopWrites482.length,0,"STOP482: still-composing native editor cannot commit science");
                compare(field.text,draft482,"STOP482: retained native composition preserves its original draft");
                compare(field.preeditText,preedit482,"STOP482: retained native composition preserves exact preedit");
            }else verify(field.text===field.value || field.text===field.editText,
                "STOP482: actual ordinary terminal refreshes the original editor's normal authoritative formatting");
            const otherValues482=JSON.parse(visible185_values(project)).filter(row=>row[0]!==target.path);
            compare(JSON.stringify(otherValues482),JSON.stringify(JSON.parse(values).filter(row=>row[0]!==target.path)),
                "STOP482: ordinary Stop blur cannot alter ANY unrelated scientific value/free/SU");
            compare(target.free,JSON.parse(values).filter(row=>row[0]===target.path)[0][2],
                "STOP482: ordinary numeric terminal cannot alter original free flag");
            recordStop482=false;
            compare(project.canUndo,undoBefore482,
                "STOP482: ordinary unrecorded manual terminal preserves original history; no phantom assistant step or unrelated Undo");
            if(stopWrites482.length)compare(target.value,stopWrites482[0].value,
                "STOP482: only actually observed original manual terminal value survives, no later stale assistant write");
            else compare(visible185_values(project),values,"STOP482: no terminal write preserves ALL original science exactly");
            if(!gap)verify(visible185_outcome(call,previousIds)!==null && visible185_outcome(call,previousIds).status!=="edited",
                "STOP482: old helper outcome stays non-edited despite ordinary user terminal effects");
            console.log("STOP482_TERMINAL",JSON.stringify({case:data.tag,lostFocus:lostFocus482,
                terminals:terminals482,writes:stopWrites482,draft:draft482,preedit:preedit482}));
            } finally {
                disconnect313(fieldLife482,field,"activeFocusChanged",focus482);
                disconnect313(fieldLife482,field,"editingFinished",terminal482);
                disconnect313(targetLife482,target,"valueChanged",write482);
            }
            if (gap) compare(JSON.stringify(visible185_outcome(call, previousIds)), gapOutcome,
                "SL1 GAP: already completed original read stays truthful through request retirement");

            compare(visible185_inputs(project), inputs, "SL1: original observations/sigmas/masks/weights/links survive");
            compare(JSON.stringify([Probe.rows(project.analysis.aliases), Probe.rows(project.analysis.constraints)]),
                declarations, "SL1: original scientific declarations remain intact");
            verify(Session.project === project && assistant.connected,
                "SL1: original current owner and genuine account survive input takeover/query");
            compare(JSON.stringify(Probe.rows(assistant.models)), models, "SL1: genuine catalog survives without login repair");
            verify(history.every(row => Probe.rows(assistant.messages).some(value => JSON.stringify(value) === row)),
                "SL1: retained conversation is not discarded during input retirement");
        } finally {
            console.log("SL1_233_STATE", data.tag, JSON.stringify({receipt: receipt,
                currentOwner: Session.project === project, connected: assistant.connected,
                focusIsOriginal: window.activeFocusItem === field, activeFocus: field.activeFocus,
                text: field.text, preedit: field.preeditText, value: target.value,
                canCancel: assistant.canCancel, showingActions: assistant.showingActions,
                takeovers: takeovers, userEdits: userEdits, preeditSignals: preedits, pointerStarts: ownStarts,
                pointerOpacity: pointer.opacity, pointerVisible: pointer.visible,
                pointerRendered: Ui.rendered(pointer), pointerSize: [pointer.width, pointer.height],
                lastError: assistant.lastError, originalOutcome: visible185_outcome(call, previousIds)}));
            assistant.actionManualTakeover.disconnect(takeoverReceipt);
            assistant.actionPointerShown.disconnect(pointerReceipt);
            field.textEdited.disconnect(editedReceipt);
            field.preeditTextChanged.disconnect(preeditReceipt);
            if (assistant.canCancel) assistant.cancel();
        }
    }
    // PRIVATE candidate. Public214 form contract and original affine145 invariants;
    // no production candidate body, calculated optimum or new test interface.
    function relation245_declarations(project) {
        return JSON.stringify([Probe.rows(project.analysis.aliases),
            Probe.rows(project.analysis.constraints)]);
    }
    function relation245_text(name, text) {
        const control = Ui.control(Probe, window, name);
        verify(control !== null, "REL SETUP: ordinary named form editor exists");
        Ui.scrollIntoView(control);
        rendered();
        Ui.click(this, Probe, window, name);
        compare(window.activeFocusItem, control, "REL: real click focuses the original form editor");
        visible185_type(text);
        compare(control.text, text, "REL: actual keys preserve exact original declaration spelling");
        return control;
    }
    function relation245_stage(project, aliases, constraints) {
        visible185_page("analysis");
        Ui.click(this, Probe, window, "sideBar.tab.extras");
        const science = visible185_values(project);
        const declarations = relation245_declarations(project);
        for (const [kind, rows] of [["aliases", aliases], ["constraints", constraints]]) {
            Ui.click(this, Probe, window, "relations.stage." + kind);
            for (const row of rows) {
                Ui.click(this, Probe, window, "relations.stage.add");
                relation245_text("relations.stage.id", row.id);
                relation245_text("relations.stage.definition", row.path === undefined ? row.expression : row.path);
                if (row.enabled !== undefined) {
                    const enabled = Ui.control(Probe, window, "relations.stage.enabled");
                    verify(enabled !== null && Ui.exposed(enabled), "REL: ordinary enabled checkbox is exposed");
                    if (enabled.checked !== row.enabled)
                        Ui.click(this, Probe, window, "relations.stage.enabled");
                    compare(enabled.checked, row.enabled, "REL: actual checkbox represents the requested declaration flag");
                }
                compare(visible185_values(project), science, "REL: staged typing/row/tab changes never publish science");
                compare(relation245_declarations(project), declarations,
                    "REL: stage remains presentation until one genuine Apply");
            }
        }
    }
    function test_relation245_actual_shared_manual_append_data() {
        return ["manual-shared", "manual-varied", "zero-new-aliases"].map(tag => ({tag: tag}));
    }
    function test_relation245_actual_shared_manual_append(data) {
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")),
            "REL SETUP: independent complete mixed-site fixture opens through real Session");
        const project = Session.project;
        const lengths = project.currentStructure.scatteringLengths;
        const originalLengths = Probe.rows(lengths);
        compare(originalLengths.length, 1, "REL SETUP: original fixture explicitly supplies one replacement-table entry");
        compare(originalLengths[0].typeSymbol, "La", "REL SETUP: literal source fixture declares La");
        compare(originalLengths[0].lengthFm, 8.24, "REL SETUP: original neutron length follows source bytes");
        lengths.remove(0);
        compare(lengths.count, 0, "REL SETUP: public empty custom map restores the ordinary complete built-in table");
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment),
            10000, "REL SETUP: real initial calculation settles before preservation snapshot");
        const la = visible185_parameter(project, "La", "adp_iso");
        const ba = visible185_parameter(project, "Ba", "adp_iso");
        const co = visible185_parameter(project, "Co", "adp_iso");
        // A non-identity equality: ordinary real typing changes Ba before the
        // relation; manual scalar preparation itself promises no recorded Undo.
        visible185_page("analysis");
        Ui.click(this, Probe, window, "parameters.nameFilter");
        visible185_type("adp_iso");
        rendered();
        const baField = visible185_field(ba);
        Ui.click(this, Probe, window, baField.objectName);
        visible185_type("0.8");
        keyClick(Qt.Key_Return);
        compare(ba.value, 0.8, "REL SETUP: actual ordinary input makes the shared-site equality nontrivial");
        compare(la.value, 0.5, "REL SETUP: literal original independent La value is unchanged by Ba preparation");
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment),
            10000, "REL SETUP: genuine manual preparation calculation settles before baseline");
        const inputs = visible185_inputs(project);
        const original = visible185_values(project);
        const initial = relation245_declarations(project);
        const aliases = [{id: "rel245_la", path: la.path}, {id: "rel245_ba", path: ba.path}];
        const shared = {id: "rel245_shared", expression: "rel245_ba = rel245_la", enabled: true};
        let addedAliases = aliases;
        let constraints = [shared];
        if (data.tag === "manual-varied") {
            addedAliases = aliases.concat([{id: "rel245_co", path: co.path}]);
            constraints = [shared, {id: "rel245_disabled", expression: "rel245_co = 0.8", enabled: false}];
        }
        toggle();
        assistant.signIn();
        visible185_ready("relation245-bootstrap");
        if (assistant.contextConsentRequired) assistant.signIn();
        visible185_ready("relation245-disclosed");
        const models = JSON.stringify(Probe.rows(assistant.models));
        closeAssistant388();
        if (data.tag === "zero-new-aliases") {
            // First real ordinary Apply establishes addresses. The second append
            // adds zero aliases and references those existing original IDs.
            relation245_stage(project, aliases, [{id: "rel245_prior", expression: "rel245_ba = rel245_la", enabled: false}]);
            Ui.click(this, Probe, window, "relations.stage.apply");
            compare(project.analysis.aliases.count, 2, "REL SETUP: actual prior ordinary aliases were published");
            addedAliases = [];
        }
        const beforeValues = visible185_values(project);
        const beforeDeclarations = relation245_declarations(project);
        const beforeAliases = Probe.rows(project.analysis.aliases);
        const beforeConstraints = Probe.rows(project.analysis.constraints);
        relation245_stage(project, addedAliases, constraints);
        Ui.click(this, Probe, window, "relations.stage.apply");
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment),
            10000, "REL: genuine shared editor publication/calculation completes before readback");
        const actualAliases = Probe.rows(project.analysis.aliases);
        const actualConstraints = Probe.rows(project.analysis.constraints);
        compare(actualAliases.length, beforeAliases.length + addedAliases.length,
            "REL: complete ordinary append preserves old aliases and adds exactly the requested count");
        for (const row of addedAliases)
            verify(actualAliases.some(value => value.id === row.id),
                "REL: every actual requested alias identity is published, not just an arbitrary count");
        compare(actualConstraints.length, beforeConstraints.length + constraints.length,
            "REL: complete ordinary append preserves old constraints and adds the entire batch");
        for (const row of beforeAliases)
            verify(actualAliases.some(value => JSON.stringify(value) === JSON.stringify(row)),
                "REL: prior alias declarations survive intact");
        for (const row of beforeConstraints.concat(constraints))
            verify(actualConstraints.some(value => value.id === row.id && value.expression === row.expression
                && value.enabled === row.enabled), "REL: exact enabled/disabled expression declarations survive Apply");
        compare(ba.value, la.value, "REL: independently requested equality applies to the mixed same-site ADPs");
        compare(co.value, 0.5, "REL: disabled unrelated Co declaration does not change its literal original fixture value");
        compare(visible185_inputs(project), inputs, "REL: complete measured data/sigma/weights/masks/links are preserved");
        Ui.click(this, Probe, window, "appBar.button.undo");
        compare(visible185_values(project), beforeValues, "REL: ONE real recorded Undo restores every value/free/SU");
        compare(relation245_declarations(project), beforeDeclarations,
            "REL: the same ONE Undo restores all prior declarations, never a partial batch");
        if (data.tag === "zero-new-aliases") {
            Ui.click(this, Probe, window, "appBar.button.undo");
            compare(relation245_declarations(project), initial, "REL: separate original Apply retains its own complete Undo");
        }
        compare(visible185_values(project), original, "REL: complete manual control leaves original independent parameter state");
        compare(Session.project, project, "REL: real Apply/Undo retains the actual current Session owner");
        compare(JSON.stringify(Probe.rows(assistant.models)), models, "REL: ordinary form never repairs/resets account catalog");
        verify(assistant.connected, "REL: actual managed account survives ordinary form Apply/Undo");
    }

    function relation246_parameters() {
        return {
            aliases: [{id: "rel246_la", path: "structure.atom_sites[La].adp_iso"},
                {id: "rel246_ba", path: "structure.atom_sites[Ba].adp_iso"}],
            constraints: [{id: "rel246_shared", expression: "rel246_ba = rel246_la", enabled: true}]
        };
    }
    function relation246_observationMs(args) {
        const texts = [];
        args.aliases.forEach(row => texts.push(row.id, row.path));
        args.constraints.forEach(row => texts.push(row.id, row.expression));
        // Original10000 observation plus public paced key100/move500/press100/
        // relax500 for actual tab/Add/two editors/optional flag per requested row.
        return 10000 + 1100 * (3 + 5 * (args.aliases.length + args.constraints.length))
            + 100 * texts.reduce((total, text) => total + [...text].length + 4, 0);
    }
    function relation246_shape(project) {
        return JSON.stringify(Probe.rows(project.currentStructure.atomSites).map(row =>
            [row.label, row.typeSymbol, row.wyckoffLetter, row.adpType, row.fractX.value,
                row.fractY.value, row.fractZ.value, row.occupancy.value]));
    }
    function test_relation246_original_rpc_full_gui_data() {
        return ["owner-fit", "varied-batch", "zero-new-aliases", "staged-draft",
            "stop", "manual-takeover", "resolved", "cleanup-successor"].map(tag => ({tag: tag}));
    }
    function test_relation246_original_rpc_full_gui(data) {
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")),
            "REL RPC SETUP: original independent complete mixed-site project opens normally");
        const project = Session.project;
        const lengths = project.currentStructure.scatteringLengths;
        const originalLengths = Probe.rows(lengths);
        compare(originalLengths.length, 1, "REL RPC SETUP: source fixture has its one declared custom entry");
        compare(originalLengths[0].typeSymbol, "La", "REL RPC SETUP: literal custom entry is La");
        compare(originalLengths[0].lengthFm, 8.24, "REL RPC SETUP: independent source neutron length remains exact");
        lengths.remove(0);
        compare(lengths.count, 0, "REL RPC SETUP: normal public built-in-table mode is restored");
        const la = visible185_parameter(project, "La", "adp_iso");
        const ba = visible185_parameter(project, "Ba", "adp_iso");
        const co = visible185_parameter(project, "Co", "adp_iso");
        if (data.tag === "owner-fit") {
            // Scientific fixture preparation through the existing public model,
            // explicitly NOT credited as input/visible free-helper delivery.
            for (const parameter of visible185_parameters(project)) parameter.free = false;
            project.analysis.maxIterations = 8; // Same bounded real FitJob prior art as VA185.
        }
        visible185_page("analysis");
        Ui.click(this, Probe, window, "parameters.nameFilter");
        visible185_type("adp_iso");
        rendered();
        for (const parameter of data.tag === "owner-fit" ? [la, ba] : [ba]) {
            const field = visible185_field(parameter);
            Ui.click(this, Probe, window, field.objectName);
            visible185_type(data.tag === "owner-fit" ? "0" : "0.8");
            keyClick(Qt.Key_Return);
            compare(parameter.value, data.tag === "owner-fit" ? 0 : 0.8,
                "REL RPC SETUP: ordinary actual input prepares the disclosed original mixed-site values");
        }
        if (data.tag === "owner-fit") {
            verify(!la.free && !ba.free, "REL OWNER SETUP: original zero ADPs are genuinely fixed before delegation");
            visible185_page("experiment");
            Ui.click(this, Probe, window, "sideBar.tab.basic");
            Ui.expandGroup(this, Probe, window, "group.instrument");
            Ui.click(this, Probe, window, "instrument.setup_wavelength");
            visible185_type("1.49");
            keyClick(Qt.Key_Return);
            const wavelength = visible185_parameters(project).filter(row => row.name === "setup_wavelength");
            compare(wavelength.length, 1, "REL OWNER SETUP: original physical wavelength is unique");
            compare(wavelength[0].value, 1.49, "REL OWNER: user's explicit wavelength is genuinely typed and committed");
        }
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment),
            10000, "REL RPC SETUP: actual original science settles before admission baseline");
        const args = relation246_parameters();
        if (data.tag === "varied-batch") {
            args.aliases.push({id: "rel246_co", path: co.path});
            args.constraints.push({id: "rel246_disabled", expression: "rel246_co = 0.8", enabled: false});
        }
        if (data.tag === "zero-new-aliases") {
            relation245_stage(project, args.aliases,
                [{id: "rel246_prior", expression: "rel246_ba = rel246_la", enabled: false}]);
            Ui.click(this, Probe, window, "relations.stage.apply");
            args.aliases = [];
        } else {
            // Preserve a genuine unrelated prior declaration across native append.
            relation245_stage(project, [{id: "rel246_prior_co", path: co.path}],
                [{id: "rel246_prior", expression: "rel246_prior_co = 0.5", enabled: false}]);
            Ui.click(this, Probe, window, "relations.stage.apply");
        }
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment),
            10000, "REL RPC SETUP: actual prior manual Apply is settled before native context disclosure");
        const values = visible185_values(project);
        const declarations = relation245_declarations(project);
        const inputs = visible185_inputs(project);
        console.log("RELATION246_INPUT", JSON.stringify({observations: JSON.parse(inputs).observations}));
        const structure = relation246_shape(project);
        const oldAliases = Probe.rows(project.analysis.aliases);
        const oldConstraints = Probe.rows(project.analysis.constraints);
        const beforeUndo = item("appBar.button.undo").enabled;
        toggle();
        assistant.signIn();
        visible185_ready("relation246-bootstrap");
        if (assistant.contextConsentRequired) assistant.signIn();
        visible185_ready("relation246-disclosed");
        compare(visible185_values(project), values, "REL RPC SETUP: genuine managed bootstrap cannot change science");
        const modeControl = item("assistant.showActions");
        verify(modeControl.enabled && modeControl.visible, "REL RPC SETUP: genuine mode checkbox is actionable");
        mouseClick(modeControl);
        verify(assistant.showActions, "REL RPC: original real Show actions checkbox enables the mode");
        closeAssistant388();
        visible185_page("analysis");
        Ui.click(this, Probe, window, "sideBar.tab.extras");
        const models = JSON.stringify(Probe.rows(assistant.models));
        const history = Probe.rows(assistant.messages).map(row => JSON.stringify(row));
        const previousIds = new Set(Probe.rows(assistant.messages).map(row => row.id));
        const call = "relation246-" + data.tag;
        let textEvents = 0, applies = 0, starts = 0, finished = 0, running = 0;
        let cleanupSends = 0, cleanupCallbackActive = false, requestPresentationStartedInside = false;
        const stage = Ui.control(Probe, window, "relations.stage");
        const editor = Ui.control(Probe, window, "relations.stage.id");
        const definition = Ui.control(Probe, window, "relations.stage.definition");
        const apply = Ui.control(Probe, window, "relations.stage.apply");
        verify(stage !== null && editor !== null && definition !== null && apply !== null,
            "REL RPC SETUP: existing current ordinary staged form owns its real controls");
        const editorLife313 = lifetime313(editor), definitionLife313 = lifetime313(definition);
        const applyLife313 = lifetime313(apply), stageLife313 = lifetime313(stage);
        const fitOwner313 = project.fit, fitLife313 = lifetime313(fitOwner313);
        function typed() { ++textEvents; }
        function applied() { ++applies; }
        function active() { if (assistant.showingActions) { ++starts; if (cleanupCallbackActive) requestPresentationStartedInside = true; } }
        function fitFinished() { ++finished; }
        function fitRunning() { if (alive313(fitLife313) && fitOwner313.running) ++running; }
        let cleanupArmed = false;
        function resetBoundary() {
            if (!cleanupArmed || cleanupSends || !alive313(stageLife313) || stage.aliasCount !== 0) return;
            ++cleanupSends;
            cleanupCallbackActive = true;
            try { assistant.send("Apply the genuinely new relation246 successor request now"); }
            finally { cleanupCallbackActive = false; }
        }
        editor.textEdited.connect(typed);
        definition.textEdited.connect(typed);
        apply.clicked.connect(applied);
        assistant.showingActionsChanged.connect(active);
        project.fit.finished.connect(fitFinished);
        project.fit.runningChanged.connect(fitRunning);
        stage.aliasCountChanged.connect(resetBoundary);
        let draft = null, originalStage = null;
        const pointer = item("assistant.actionPointer");
        let phase = "armed", lastAggregateConjuncts = "";
        function phase253(name) {
            phase = name;
            if (data.tag !== "owner-fit") return;
            try {
                const diagnostic = visible185_outcome("relation246-diagnostics", previousIds);
                console.log("RELATION253_PHASE", JSON.stringify({phase: phase, observedAtMs: Date.now(),
                    diagnosticsOutcomePresent: diagnostic !== null,
                    canCancel: assistant.canCancel, showingActions: assistant.showingActions,
                    currentOwner: Session.project === project, calculating: project.calculating,
                    computedCurrent: Probe.computedCurrent(project.currentExperiment),
                    fitRunning: project.fit.running, fitOutcome: project.fit.outcome,
                    fitStarts: running, fitFinished: finished, textEvents: textEvents, applies: applies,
                    originalOutcome: visible185_outcome(call, previousIds),
                    freeOutcome: visible185_outcome("relation246-free", previousIds),
                    fitOutcomeRecord: visible185_outcome("relation246-fit", previousIds),
                    diagnosticOutcome: diagnostic, connected: assistant.connected,
                    lastError: assistant.lastError}));
            } catch (error) { console.log("RELATION253_PHASE_ERROR", phase, String(error)); }
        }
        phase253("before-original-send");
        try {
            if (data.tag === "staged-draft") {
                relation245_stage(project, [{id: "manual246_co", path: co.path}],
                    [{id: "manual246_preserved", expression: "manual246_co = 0.8", enabled: false}]);
                draft = {id: editor.text, expression: definition.text, focus: window.activeFocusItem,
                    start: definition.selectionStart, end: definition.selectionEnd,
                    page: window.appBarCentralTabs.currentIndex, textEvents: textEvents, stage: stage.assistantStage};
            }
            assistant.send("Original complete relation request " + data.tag);
            if (data.tag === "owner-fit") {
                for (const editId of [call, "relation246-free"]) {
                    phase253("wait-edit-" + editId);
                    tryVerify(() => {
                        const edited = visible185_outcome(editId, previousIds);
                        return edited !== null && edited.status === "edited" && !project.calculating
                            && Probe.computedCurrent(project.currentExperiment) && Session.project === project;
                    }, relation246_observationMs(args),
                    "REL OWNER SETUP: exact original edit and real calculation settle before next original call");
                    verify(assistant.canCancel && assistant.showingActions,
                        "REL OWNER: per-tool settlement retains presentation across the genuine active objective");
                    console.log("RELATION246_SETTLED", JSON.stringify({callId: editId, observedAtMs: Date.now(),
                        canCancel: assistant.canCancel, showingActions: assistant.showingActions,
                        calculating: project.calculating, computedCurrent: Probe.computedCurrent(project.currentExperiment),
                        currentOwner: Session.project === project, value: la.value, free: la.free}));
                    phase253("settled-edit-" + editId);
                    assistant.refreshUsage(); // Actual public event, no new objective/steer or timer.
                }
            }
            if (["stop", "manual-takeover", "resolved", "cleanup-successor"].includes(data.tag)) {
                tryVerify(() => assistant.showingActions && assistant.canCancel && textEvents > 0
                    && editor.text.length > 0 && editor.text !== args.aliases[0].id,
                    relation246_observationMs(args), "REL INTERVAL SETUP: genuine partial original staging is reached before intervention");
                compare(visible185_values(project), values, "REL: partial original stage has not edited science");
                compare(relation245_declarations(project), declarations, "REL: no declaration is published before actual Apply");
                if (data.tag === "stop") {
                    const stop = item("assistant.stopVisibleAction");
                    verify(stop.enabled && Ui.exposed(stop), "REL STOP SETUP: actual original appbar Stop is exposed");
                    mouseClick(stop);
                }
                else if (data.tag === "manual-takeover") {
                    const target = Ui.control(Probe, window, "relations.stage.definition");
                    Ui.scrollIntoView(target);
                    rendered();
                    const point = Ui.clickPoint(target);
                    verify(point !== null, "REL TAKEOVER SETUP: original user's actual form input is exposed");
                    mouseClick(target, point.x, point.y);
                    verify(window.activeFocusItem === target, "REL: same surviving genuine manual receiver owns focus");
                    keyClick("x");
                    verify(target.text.includes("x"), "REL: original actual manual key survives helper retirement");
                    draft = {id: editor.text, expression: target.text};
                } else if (data.tag === "resolved") {
                    // Existing ordinary optional read causes the owned peer to emit
                    // real original serverRequest/resolved. It does not steer/change
                    // objective or synthesize any app/helper/model state.
                    originalStage = stage.assistantStage;
                    verify(originalStage !== undefined && originalStage !== null
                        && String(originalStage).length > 0 && pointer.opacity > 0,
                        "REL RESOLVED SETUP: actual original keyed stage and painted pointer are captured");
                    assistant.refreshUsage();
                } else {
                    cleanupArmed = true;
                    assistant.cancel();
                }
            }
            if (data.tag === "resolved") {
                tryVerify(() => stage.assistantStage !== originalStage && pointer.opacity === 0, 10000,
                    "REL RESOLVED: matching original stage retires and actual pointer paint ends");
                verify(assistant.canCancel && assistant.showingActions,
                    "REL RESOLVED: original held objective retains whole-request presentation after per-tool retirement");
                const stoppedEvents = textEvents;
                const stopped = [editor.text, definition.text];
                rendered();
                compare(textEvents, stoppedEvents, "REL RESOLVED: later rendering never continues original typing");
                compare(JSON.stringify([editor.text, definition.text]), JSON.stringify(stopped),
                    "REL RESOLVED: no late original staging cleanup rewrites current form");
                compare(applies, 0, "REL RESOLVED: original resolved RPC can never reach a late Apply");
                assistant.cancel(); // Explicit ordinary turn cleanup after stage-retirement facts.
                tryVerify(() => !assistant.canCancel && !assistant.showingActions, 10000,
                    "REL RESOLVED: whole presentation ends only after genuine explicit turn retirement");
            } else {
                const expected = data.tag === "cleanup-successor" ? "relation246-successor"
                    : data.tag === "owner-fit" ? "relation246-diagnostics" : call;
                phase253("aggregate-wait");
                tryVerify(() => {
                    const present = visible185_outcome(expected, previousIds) !== null;
                    const conjuncts = JSON.stringify([present, assistant.canCancel, assistant.showingActions]);
                    if (data.tag === "owner-fit" && conjuncts !== lastAggregateConjuncts) {
                        lastAggregateConjuncts = conjuncts;
                        phase253("aggregate-conjunct-change");
                    }
                    return present
                        && (data.tag === "cleanup-successor" || (!assistant.canCancel && !assistant.showingActions));
                },
                    relation246_observationMs(args) + (data.tag === "owner-fit" ? visible237_observationMs([
                        {path: la.path, text: ""}]) + 10000 : 0),
                    "REL RPC: real original operation and its publication settle with an actual retained outcome");
                phase253("aggregate-passed");
                const outcome = visible185_outcome(data.tag === "cleanup-successor" ? expected : call, previousIds);
                if (data.tag === "staged-draft") {
                    verify(["refused", "unavailable"].includes(outcome.status) && outcome.message.length > 0,
                        "REL DRAFT: existing original form draft causes honest before-write refusal");
                    compare(editor.text, draft.id, "REL DRAFT: exact original ID remains untouched");
                    compare(stage.assistantStage, draft.stage,
                        "REL DRAFT: native refusal never replaces the original manual form stage");
                    compare(applies, 0, "REL DRAFT: existing manual stage is never automatically applied");
                    compare(textEvents, draft.textEvents, "REL DRAFT: no helper typing touches the original manual form");
                    compare(definition.selectionStart, draft.start, "REL DRAFT: original selection start survives");
                    compare(definition.selectionEnd, draft.end, "REL DRAFT: original selection end survives");
                    compare(definition.text, draft.expression, "REL DRAFT: exact multiline original spelling survives");
                    compare(window.activeFocusItem, draft.focus, "REL DRAFT: no preflight blur commits the original stage");
                    compare(window.appBarCentralTabs.currentIndex, draft.page, "REL DRAFT: refusal precedes navigation");
                    compare(item("appBar.button.undo").enabled, beforeUndo, "REL DRAFT: original Undo history is neither consumed nor extended");
                } else if (["stop", "manual-takeover"].includes(data.tag)) {
                    verify(outcome.status !== "edited" && outcome.message.length > 0,
                        "REL CANCEL: truthful original cancellation never claims science was edited");
                    compare(applies, 0, "REL CANCEL: no late original Apply after Stop/manual takeover");
                    if (draft) {
                        rendered();
                        compare(editor.text, draft.id, "REL TAKEOVER: original handed-over staged ID survives late cleanup");
                        compare(definition.text, draft.expression, "REL TAKEOVER: exact original user's text remains");
                    }
                } else {
                    compare(outcome.status, "edited", "REL RPC: actual shared form/editor must confirm the complete native append");
                    if (data.tag === "cleanup-successor") {
                        compare(cleanupSends, 1, "REL REENTRY SETUP: one genuine old-stage reset signal admits the user's successor attempt");
                        verify(assistant.canCancel && assistant.showingActions,
                            "REL REENTRY: confirmed B operation retains whole presentation while its objective is held");
                        assistant.cancel();
                        tryVerify(() => !assistant.canCancel && !assistant.showingActions, 10000,
                            "REL REENTRY: actual explicit turn cleanup ends the held whole-request presentation");
                        // This flag observes only requestwide presentation, not an individual B start.
                        // Exact B-inside-A admission remains an explicitly unqualified interval.
                    }
                    const aliases = Probe.rows(project.analysis.aliases);
                    const constraints = Probe.rows(project.analysis.constraints);
                    compare(aliases.length, oldAliases.length + args.aliases.length,
                        "REL RPC: all requested aliases append once while prior declarations remain");
                    compare(constraints.length, oldConstraints.length + args.constraints.length,
                        "REL RPC: complete enabled/disabled constraint batch appends once");
                    for (const row of args.aliases)
                        verify(aliases.some(value => value.id === row.id && value.parameter
                            === "lbco.atom_site." + (row.path.includes("[La]") ? "La"
                                : row.path.includes("[Ba]") ? "Ba" : "Co") + ".adp_iso"),
                            "REL RPC: native paths resolve to the independently declared fixture atom/site parameter");
                    for (const row of oldAliases)
                        verify(aliases.some(value => JSON.stringify(value) === JSON.stringify(row)),
                            "REL RPC: prior original alias declarations survive intact");
                    for (const row of oldConstraints.concat(args.constraints))
                        verify(constraints.some(value => value.id === row.id && value.expression === row.expression
                            && value.enabled === row.enabled), "REL RPC: exact prior and new constraint declarations survive");
                    compare(ba.value, la.value, "REL RPC: actual mixed-site ADPs satisfy the independently requested equality");
                    compare(co.value, 0.5, "REL RPC: disabled or unrelated Co remains the independent fixture value");
                    if (data.tag === "owner-fit") {
                        const free = visible185_outcome("relation246-free", previousIds);
                        const fit = visible185_outcome("relation246-fit", previousIds);
                        const diagnostic = visible185_outcome("relation246-diagnostics", previousIds);
                        verify(free !== null && free.status === "edited" && la.free && !ba.free,
                            "REL OWNER: genuine native free checkbox owns only the independent member of the equality");
                        verify(running > 0 && finished === 1 && !project.fit.running && project.fit.outcome.length > 0,
                            "REL OWNER: actual native FitJob/report completion precedes scientific acceptance");
                        verify(fit !== null && ["done", "max_iterations", "no_step"].includes(fit.status),
                            "REL OWNER: real supported fit attempt is not an unavailable/error substitute or fictitious success");
                        verify(Number.isFinite(fit.iterations) && fit.iterations >= 0,
                            "REL OWNER: actual iteration report is finite without an optimum golden");
                        if (fit.reduced_chi_square !== undefined)
                            verify(Number.isFinite(fit.reduced_chi_square) && fit.reduced_chi_square >= 0,
                                "REL OWNER: genuine reported fit statistic is finite; improvement is not invented");
                        verify(diagnostic !== null && diagnostic.diagnostics !== null
                            && typeof diagnostic.diagnostics === "object",
                            "REL OWNER: original native diagnostics returns after the real fit publication");
                        phase253("post-fit-science");
                        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment),
                            10000, "REL OWNER: real post-fit calculated profile is current before observation");
                        const modeled = Probe.rows(project.currentExperiment.pattern);
                        compare(modeled.length, JSON.parse(inputs).observations.length,
                            "REL OWNER: actual fit keeps the complete measured grid");
                        verify(modeled.every(row => Number.isFinite(row.intensityCalc)),
                            "REL OWNER: actual native modeled intensity is finite at every original observation");
                        for (const parameter of visible185_parameters(project))
                            if (parameter.hasUncertainty)
                                verify(Number.isFinite(parameter.uncertainty) && parameter.uncertainty >= 0,
                                    "REL OWNER: actual reported scientific uncertainty is finite and nonnegative");
                        // Native fit may produce its own result Undo; ordinary appbar Undo
                        // restores its adopted values before the two original native edits.
                        if (fit.adopted) {
                            verify(project.fit.canUndo, "REL OWNER: adopted actual fit exposes its ordinary result Undo");
                            phase253("fit-undo");
                            Ui.click(this, Probe, window, "appBar.button.undo");
                        }
                        phase253("free-undo");
                        Ui.click(this, Probe, window, "appBar.button.undo");
                        compare(la.free, false, "REL OWNER: one native free Undo restores original fixed independent ADP");
                    }
                    phase253("relation-undo");
                    Ui.click(this, Probe, window, "appBar.button.undo");
                }
            }
            phase253("final-preservation");
            compare(visible185_values(project), values, "REL: complete Undo/refusal/retirement preserves all original values/free/SUs");
            compare(relation245_declarations(project), declarations, "REL: original full declarations survive exactly");
            compare(visible185_inputs(project), inputs, "REL: unchanged actual observations/sigmas/masks/weights/links survive");
            compare(relation246_shape(project), structure, "REL: original composition/site coordinates/Wyckoff geometry survive");
            verify(Session.project === project && assistant.connected, "REL: current owner and actual account remain genuine");
            compare(JSON.stringify(Probe.rows(assistant.models)), models, "REL: no account/catalog repair substitutes for completion");
            verify(history.every(row => Probe.rows(assistant.messages).some(value => JSON.stringify(value) === row)),
                "REL: retained original history survives native work and cancellation");
        } finally {
            phase253("finally-after-" + phase);
            console.log("RELATION246_STATE", data.tag, JSON.stringify({showingActions: assistant.showingActions,
                canCancel: assistant.canCancel, textEvents: textEvents, applies: applies, starts: starts,
                fitStarts: running, fitFinished: finished, currentOwner: Session.project === project,
                connected: assistant.connected, lastError: assistant.lastError,
                stagedId: alive313(editorLife313) ? editor.text : null,
                stagedDefinition: alive313(definitionLife313) ? definition.text : null,
                stageAlive: alive313(stageLife313), editorAlive: alive313(editorLife313),
                definitionAlive: alive313(definitionLife313), cleanupSends: cleanupSends,
                requestPresentationStartedInside: requestPresentationStartedInside,
                originalStage: originalStage === null ? null : String(originalStage),
                currentStage: alive313(stageLife313) ? String(stage.assistantStage) : null, pointerOpacity: pointer.opacity, outcome: visible185_outcome(call, previousIds)}));
            disconnect313(editorLife313, editor, "textEdited", typed);
            disconnect313(definitionLife313, definition, "textEdited", typed);
            disconnect313(applyLife313, apply, "clicked", applied);
            assistant.showingActionsChanged.disconnect(active);
            disconnect313(fitLife313, fitOwner313, "finished", fitFinished);
            disconnect313(fitLife313, fitOwner313, "runningChanged", fitRunning);
            disconnect313(stageLife313, stage, "aliasCountChanged", resetBoundary);
            if (assistant.canCancel) assistant.cancel();
        }
    }


    // Public226/231 actual import form; no producer-private counter or expected fit output.
    function import265_recipe() {
        return {project_name: "Original measured PbSO4", description: "Original typed independent import",
            experiment_name: "d1a", sample_form: "powder", beam_mode: "constant wavelength",
            radiation_probe: "neutron", scattering_type: "bragg", peak_profile: "cwl-tch-pseudo-voigt",
            wavelength: 1.909, zero_offset: -0.001, phase_scale: 1,
            background: [{position: 10, intensity: 200}, {position: 155.85, intensity: 200}],
            exclusions: [{first: 10, second: 11}, {first: 155, second: 155.85}],
            initial_parameters: [{path: "experiment.peak.broad_gauss_u", value: 0.1},
                {path: "experiment.peak.broad_gauss_v", value: 0},
                {path: "experiment.peak.broad_gauss_w", value: 0.1},
                {path: "experiment.peak.broad_lorentz_x", value: 0},
                {path: "experiment.peak.broad_lorentz_y", value: 0.1}]};
    }
    function import265_observationMs(recipe) {
        // Existing public237 pacing model: move500/press100/relax500, scalar100.
        // Count this complete original recipe's actual form fields/rows, never a producer counter.
        let texts = [recipe.project_name, recipe.experiment_name, recipe.description,
            String(recipe.wavelength), String(recipe.zero_offset), String(recipe.phase_scale)];
        recipe.background.forEach(row => texts.push(String(row.position), String(row.intensity)));
        recipe.exclusions.forEach(row => texts.push(String(row.first), String(row.second)));
        recipe.initial_parameters.forEach(row => texts.push(row.path, String(row.value)));
        const rows = recipe.background.length + recipe.exclusions.length + recipe.initial_parameters.length;
        const clicks = 3 + 1 + 3 + 3 + texts.length + rows + 1;
        const scalarKeys = texts.reduce((count, text) => count + [...text].length + 2, 0);
        const comboKeys = (2 + 1) + (2 + 1) + (2 + 5); // two sources, six public profiles maximum.
        return 10000 + clicks * (500 + 100 + 500) + 100 * (scalarKeys + comboKeys);
    }
    function import265_control(name) {
        const found = Ui.itemsWithProperty(Ui.windowRoot(window), "objectName")
            .filter(control => control.objectName === name && control.visible);
        compare(found.length, 1, "IMPORT265 SETUP: one real visible import control owns " + name);
        Ui.scrollIntoView(found[0]);
        verify(Ui.exposed(found[0]) && found[0].enabled,
            "IMPORT265 SETUP: the genuine import input is exposed and enabled: " + name);
        return found[0];
    }
    function import265_click(name) {
        const control = import265_control(name);
        let delay = 0;
        for (let parent = control.parent; parent; parent = parent.parent)
            if (typeof parent.pressDelay === "number") delay = Math.max(delay, parent.pressDelay + 1);
        const point = Ui.clickPoint(control);
        mouseClick(control, point.x, point.y, Qt.LeftButton, Qt.NoModifier, delay);
        window.update();
        verify(waitForRendering(window.contentItem), "IMPORT265: actual form input has a real rendered receipt");
        return control;
    }
    function import265_text(name, text) {
        const control = import265_click(name);
        tryVerify(() => control.activeFocus || (window.activeFocusItem &&
            Probe.objectsWithProperty(control, "activeFocus").includes(window.activeFocusItem)),
            2000, "IMPORT265 SETUP: real pointer focuses the actual form editor before typing");
        visible185_type(String(text));
        compare(control.text, String(text), "IMPORT265: actual form retains exact original typed text");
    }
    // Passive276: bounded public control/focus receipts; no Keys handler or event acceptance changes.
    function import276_identity(object) {
        if (!object) return null;
        const properties = ["objectName", "visible", "enabled", "opacity", "clip", "x", "y",
            "width", "height", "focus", "activeFocus", "visualFocus", "currentIndex",
            "highlightedIndex", "currentText", "displayText", "textRole", "valueRole",
            "count", "down", "pressed", "editable", "opened", "modal"];
        const result = {identity: String(object).slice(0, 200)};
        properties.forEach(property => {
            try {
                const value = object[property];
                if (["string", "number", "boolean"].includes(typeof value))
                    result[property] = typeof value === "string" ? value.slice(0, 200) : value;
            } catch (error) { result[property] = "<unreadable>"; }
        });
        try {
            const point = object.mapToItem(window.contentItem, 0, 0);
            result.scene = {x: point.x, y: point.y};
        } catch (error) { result.scene = null; }
        return result;
    }
    function import276_ancestors(object) {
        const result = [];
        for (let current = object, count = 0; current && count < 12; current = current.parent, ++count)
            result.push(import276_identity(current));
        return result;
    }
    function import276_comboReceipt(stage, control, name, label, matches, detail) {
        try {
            const choices = [];
            for (let i = 0; i < Math.min(control.count, 8); ++i)
                choices.push({index: i, text: String(control.textAt(i)).slice(0, 200)});
            const actualPopup = control.popup;
            const content = actualPopup ? actualPopup.contentItem : null;
            console.log("IMPORT276_COMBO", JSON.stringify({stage: stage, name: name,
                requestedLabel: label, matchingIndices: matches, detail: detail || null,
                page: window.appBarCentralTabs.currentIndex, pageItem: import276_identity(Ui.page(window)),
                control: import276_identity(control), controlAncestors: import276_ancestors(control),
                model: String(control.model).slice(0, 200), choices: choices, choicesTruncated: control.count > 8,
                popup: import276_identity(actualPopup), popupParent: actualPopup ? import276_identity(actualPopup.parent) : null,
                popupContent: import276_identity(content), popupCurrentItem: content ? import276_identity(content.currentItem) : null,
                focusItem: import276_identity(window.activeFocusItem),
                focusAncestors: import276_ancestors(window.activeFocusItem), window: String(window).slice(0, 200)}));
        } catch (error) { console.log("IMPORT276_DIAGNOSTIC_ERROR", stage, String(error).slice(0, 240)); }
    }
    function import265_combo(name, label) {
        const control = import265_control(name);
        const matches = [];
        for (let i = 0; i < control.count; ++i) if (control.textAt(i) === label) matches.push(i);
        compare(matches.length, 1, "IMPORT265 SETUP: exact displayed original choice is uniquely offered");
        const observations = [];
        let signalCount = 0;
        function observe(object, signalName) {
            if (!object || !object[signalName] || !object[signalName].connect) return;
            const receive = function(value) {
                if (signalCount++ < 48)
                    import276_comboReceipt("signal:" + signalName, control, name, label, matches,
                        {value: typeof value === "number" || typeof value === "boolean" ? value : null});
            };
            object[signalName].connect(receive);
            observations.push({signal: object[signalName], receive: receive});
        }
        try {
            ["activated", "highlighted", "currentIndexChanged", "highlightedIndexChanged", "activeFocusChanged"]
                .forEach(signal => observe(control, signal));
            ["opened", "closed", "visibleChanged"].forEach(signal => observe(control.popup, signal));
            observe(window, "activeFocusItemChanged");
            import276_comboReceipt("before-click", control, name, label, matches);
            import265_click(name);
            import276_comboReceipt("after-click/before-Home", control, name, label, matches);
            keyClick(Qt.Key_Home);
            import276_comboReceipt("after-Home", control, name, label, matches);
            for (let i = 0; i < matches[0]; ++i) {
                import276_comboReceipt("before-Down", control, name, label, matches, {ordinal: i});
                keyClick(Qt.Key_Down);
                import276_comboReceipt("after-Down", control, name, label, matches, {ordinal: i});
            }
            import276_comboReceipt("before-Return", control, name, label, matches);
            keyClick(Qt.Key_Return);
            import276_comboReceipt("after-Return", control, name, label, matches);
            compare(control.currentIndex, matches[0], "IMPORT265: real ComboBox keyboard selects original choice");
            compare(control.currentText, label, "IMPORT265: actual displayed source/profile matches original choice");
            // Existing2000ms form-focus setup bound; wait on the real popup, not elapsed animation time.
            tryVerify(() => !control.popup.visible && !control.popup.opened, 2000,
                "IMPORT278 SETUP: original selected ComboBox popup is closed before the next physical input");
            import276_comboReceipt("after-popup-closed", control, name, label, matches);
        } finally {
            import276_comboReceipt("finally", control, name, label, matches, {observedSignals: signalCount});
            observations.forEach(observation => observation.signal.disconnect(observation.receive));
        }
    }
    function import265_owner(project) {
        return project ? JSON.stringify({name: project.name, title: project.title,
            description: project.description, authors: project.authors, path: project.path,
            suRule: project.suRule, embedLibraries: project.report.embedLibraries}) : null;
    }
    function import265_science(project) {
        compare(project.structures.count, 1, "IMPORT265: actual import creates one original phase");
        compare(project.experiments.count, 1, "IMPORT265: actual import creates one measured experiment");
        compare(project.currentStructure.spaceGroup.nameHM, "P n m a", "IMPORT265: original CIF symmetry is retained");
        compare(project.currentExperiment.name, "d1a", "IMPORT267: explicit original experiment name is retained");
        compare(project.currentExperiment.sampleFormToken, "powder", "IMPORT267: actual imported model has original powder type");
        compare(project.currentExperiment.beamModeToken, "constant wavelength", "IMPORT267: actual imported model has original CW geometry");
        compare(project.currentExperiment.radiationProbeToken, "neutron", "IMPORT267: actual imported model has original neutron probe");
        compare(project.currentExperiment.scatteringTypeToken, "bragg", "IMPORT267: actual imported model has original Bragg scattering");
        compare(project.currentExperiment.peakType, "cwl-tch-pseudo-voigt", "IMPORT267: actual selected canonical peak profile survives");
        compare(project.fit.running, false, "IMPORT267: creation alone never claims or launches refinement");
        compare(JSON.stringify(Probe.rows(project.currentExperiment.background).map(row => [row.position, row.intensity.value])),
            JSON.stringify([[10, 200], [155.85, 200]]), "IMPORT267: every original supplied background point survives");
        for (const pair of [["length_a", 8.48], ["length_b", 5.398], ["length_c", 6.958]]) {
            const parameters = visible185_parameters(project).filter(parameter => parameter.name === pair[0]);
            compare(parameters.length, 1, "IMPORT267 SETUP: original cell scalar is unique");
            compare(parameters[0].value, pair[1], "IMPORT267: bare original cell value survives import");
            compare(parameters[0].free, false, "IMPORT267: original fixed cell does not become free");
            compare(parameters[0].uncertainty, 0, "IMPORT267: public cell uncertainty view retains numeric zero");
        }
        const siteRows = Probe.rows(project.currentStructure.atomSites);
        const sites = siteRows.map(row => [row.label, row.typeSymbol])
            .sort((a, b) => a[0].localeCompare(b[0]));
        compare(JSON.stringify(sites), JSON.stringify([["O1", "O"], ["O2", "O"], ["O3", "O"], ["Pb", "Pb"], ["S", "S"]]),
            "IMPORT265: every original independent site/species is retained");
        const positions = {Pb: [0.1882, 0.25, 0.167], S: [0.063, 0.25, 0.686],
            O1: [-0.095, 0.25, 0.6], O2: [0.181, 0.25, 0.543], O3: [0.085, 0.026, 0.806]};
        for (const label of Object.keys(positions)) {
            const matchingSites = siteRows.filter(site => site.label === label);
            compare(matchingSites.length, 1, "IMPORT281: each original physical site has one public owning-model row");
            const site = matchingSites[0];
            for (let index = 0; index < 3; ++index)
                compare(site[["fractX", "fractY", "fractZ"][index]].value,
                    positions[label][index], "IMPORT265: original fractional coordinates retain literal source values");
            compare(site.occupancy.value, 1,
                "IMPORT265: original occupancies are unchanged");
            compare(site.adpIso.value, 0.01,
                "IMPORT265: original isotropic ADP retains source Uiso convention/value");
            compare(site.adpType, "Uiso", "IMPORT281: every original site retains the literal CIF displacement convention");
        }
        // Original CIF block data_pbso4-phase; public nonempty datablock keys retain that spelling.
        compare(project.currentStructure.name, "pbso4-phase", "IMPORT281: sole phase retains its original canonical datablock key");
        compare(JSON.stringify(Probe.rows(project.currentExperiment.linkedStructures)
            .map(row => [row.structureId, row.enabled])), JSON.stringify([["pbso4-phase", true]]),
            "IMPORT281: the sole original canonical phase is actually linked and enabled");
        const wavelengths = visible185_parameters(project).filter(parameter => parameter.name === "setup_wavelength");
        compare(wavelengths.length, 1, "IMPORT265 SETUP: original wavelength parameter is unique");
        compare(wavelengths[0].value, 1.909, "IMPORT265: explicit supplied original wavelength is retained");
        const offsets = visible185_parameters(project).filter(parameter => parameter.name === "calib_twotheta_offset");
        compare(offsets.length, 1, "IMPORT267 SETUP: public two-theta offset scalar is unique");
        compare(offsets[0].value, -0.001, "IMPORT267: original explicit zero offset survives typed form input");
        compare(project.currentExperiment.scale.value, 1, "IMPORT267: original explicit single-phase scale survives");
        for (const requested of import265_recipe().initial_parameters) {
            const name = requested.path.split(".").slice(-1)[0];
            const parameters = visible185_parameters(project).filter(parameter => parameter.name === name);
            compare(parameters.length, 1, "IMPORT267 SETUP: original requested physical parameter is unique");
            compare(parameters[0].value, requested.value, "IMPORT267: every explicit initial physical value survives real form reconstruction");
        }
        compare(JSON.stringify(Probe.rows(project.currentExperiment.excludedRegions).map(row => [row.start, row.end])),
            JSON.stringify([[10, 11], [155, 155.85]]), "IMPORT267: original explicit exclusion intervals survive");
        console.log("IMPORT265_INPUT", visible185_inputs(project));
    }
    function test_import265_actual_manual_and_visible_creation_data() {
        return ["manual-no-owner", "manual-saved-empty", "visible-no-owner", "visible-saved-empty",
            "visible-stop", "visible-manual-input", "visible-close", "visible-new-owner",
            "visible-source-refusal-close"].map(tag => ({tag: tag}));
    }
    function test_import265_actual_manual_and_visible_creation(data) {
        const manual = ["manual-no-owner", "manual-saved-empty"].includes(data.tag);
        const same = data.tag.endsWith("saved-empty");
        const cancelled = !manual && !["visible-no-owner", "visible-saved-empty"].includes(data.tag);
        const recipe = import265_recipe();
        Session.closeProject();
        compare(Session.project, null, "IMPORT265 SETUP: genuine normal Session closes the initial fixture");
        if (same) {
            const url = String(Probe.scratchProjectUrl());
            verify(url.startsWith("file:///"), "IMPORT265 SETUP: actual scratch project URL is local");
            const directory = decodeURIComponent(url.slice(7));
            verify(Session.createProject("Original saved empty owner", "Original preserved description", directory,
                "iucr_99", "Original preserved title", "Original preserved author", true),
                "IMPORT265 SETUP: actual Session normally saves the real named empty owner");
        }
        const original = Session.project;
        const originalLife313 = lifetime313(original);
        let replacementLife313 = null, fieldLife313 = null, applyLife313 = null;
        const metadata = import265_owner(original);
        const originalUndo = original ? original.canUndo : null;
        const originalSavedText = original ? Probe.readFile(original.path + "/project.edi") : null;
        const token = assistant.beginFileSelection();
        verify(token.length > 0 && assistant.addSelectedFiles(token, [
            Probe.repoUrl("tests/fixtures/assistant/reference/PbSO4-Wyckoff.cif"),
            Probe.repoUrl("/tmp/relay-e11-t5-tests/seq85-private/inputs/observed.xye")]),
            "IMPORT265 SETUP: genuine existing chooser admission owns both original immutable sources");
        tryCompare(assistant.selectedFiles, "count", 2, 2000, "IMPORT265 SETUP: source rows finish admission");
        const selected = Probe.rows(assistant.selectedFiles);
        if (Session.project === null) {
            visible185_page("home");
            compare(window.appBarCentralTabs.currentIndex, AppState.Page.Home,
                "IMPORT270 SETUP: genuine Home page is selected before exposed Start");
            Ui.click(this, Probe, window, "home.start");
            compare(window.appBarCentralTabs.currentIndex, AppState.Page.Project,
                "IMPORT270 SETUP: actual Home Start selects the normal Project workflow");
        } else visible185_page("project");
        rendered();
        const cif = selected.filter(row => row.name === "PbSO4-Wyckoff.cif");
        const measurement = selected.filter(row => row.name === "observed.xye");
        compare(cif.length, 1, "IMPORT265 SETUP: actual original CIF ID is unique");
        compare(measurement.length, 1, "IMPORT265 SETUP: actual original measurement ID is unique");
        verify(cif[0].id !== measurement[0].id, "IMPORT265 SETUP: actual source IDs are distinct");
        let ownStarts = 0, edits = 0, applyClicks = 0, field = null, form = null, retained = null, applyTarget = null;
        function pointerReceipt() { ++ownStarts; }
        function editReceipt() { ++edits; }
        function applyReceipt() { ++applyClicks; }
        assistant.actionPointerShown.connect(pointerReceipt);
        let previous = new Set(), models = null, accountWasConnected = false, replacement = null;
        const callId = "import265-create-" + data.tag;
        try {
            if (manual) {
                compare(assistant.connected, false, "IMPORT265: ordinary import works offline without provider setup");
                Ui.click(this, Probe, window, "sideBar.tab.basic");
                Ui.click(this, Probe, window, "project.importNativeCwl");
                form = item("nativeImport.dialog");
                tryCompare(form, "opened", true, 2000, "IMPORT265: actual ordinary Import button opens its form");
                compare(assistant.nativeImport.state, "draft", "IMPORT265: manual form owns an actual fresh draft");
                compare(import265_control("nativeImport.cif").currentIndex, -1,
                    "IMPORT267 SETUP: fresh source choices contain no invented default selection");
                compare(import265_control("nativeImport.measurement").currentIndex, -1,
                    "IMPORT267 SETUP: measurement starts genuinely unselected");
                for (const name of ["projectName", "experimentName", "description"])
                    compare(import265_control("nativeImport." + name).text, "",
                        "IMPORT267 SETUP: original manual text fields begin empty");
                import265_combo("nativeImport.cif", "PbSO4-Wyckoff.cif");
                import265_combo("nativeImport.measurement", "observed.xye");
                compare(assistant.selectedFiles.text(import265_control("nativeImport.cif").currentIndex, "id"), cif[0].id,
                    "IMPORT265: actual source row index grants its original CIF ID, not currentValue");
                compare(assistant.selectedFiles.text(import265_control("nativeImport.measurement").currentIndex, "id"), measurement[0].id,
                    "IMPORT265: actual measurement row index grants its original source ID");
                import265_text("nativeImport.projectName", recipe.project_name);
                import265_text("nativeImport.experimentName", recipe.experiment_name);
                import265_text("nativeImport.description", recipe.description);
                import265_click("nativeImport.tab.instrument");
                import265_combo("nativeImport.profile", recipe.peak_profile);
                import265_text("nativeImport.wavelength", recipe.wavelength);
                import265_text("nativeImport.zero", recipe.zero_offset);
                import265_text("nativeImport.scale", recipe.phase_scale);
                for (const section of ["background", "exclusions", "parameters"]) {
                    import265_click("nativeImport.tab." + section);
                    const rows = section === "background" ? recipe.background : section === "exclusions"
                        ? recipe.exclusions : recipe.initial_parameters;
                    for (const row of rows) {
                        import265_click("nativeImport.row.add");
                        import265_text("nativeImport.row.first", section === "background" ? row.position
                            : section === "exclusions" ? row.first : row.path);
                        import265_text("nativeImport.row.second", section === "background" ? row.intensity
                            : section === "exclusions" ? row.second : row.value);
                    }
                }
                applyTarget = import265_control("nativeImport.apply");
                applyLife313 = lifetime313(applyTarget); applyTarget.clicked.connect(applyReceipt);
                import265_click("nativeImport.apply");
                compare(applyClicks, 1, "IMPORT265: ordinary real Apply is clicked exactly once");
                tryVerify(() => assistant.nativeImport.state === "created", 10000,
                    "IMPORT265: ordinary real Worker completes genuine adoption before success is observed");
                verify(assistant.nativeImport.outcome && assistant.nativeImport.outcome.adopted === true
                    && (same ? assistant.nativeImport.outcome.presentation_complete
                        : assistant.nativeImport.presentation_complete) === true,
                    "IMPORT267: ordinary success requires complete actual adoption, not partial committed presentation");
            } else {
                toggle(); assistant.signIn(); visible185_ready("import265-bootstrap");
                if (assistant.contextConsentRequired) assistant.signIn();
                visible185_ready("import265-disclosed");
                verify(!assistant.contextConsentRequired, "IMPORT265 SETUP: original exact disclosed context is approved");
                const show = item("assistant.showActions");
                verify(show.visible && show.enabled, "IMPORT265 SETUP: actual Show actions checkbox is available");
                mouseClick(show); compare(assistant.showActions, true, "IMPORT265: actual mode checkbox enables visible creation");
                accountWasConnected = assistant.connected; models = JSON.stringify(Probe.rows(assistant.models));
                previous = new Set(Probe.rows(assistant.messages).map(row => row.id));
                assistant.send("Import the actual selected PbSO4 CIF and measured XYE with the original explicit recipe");
                tryVerify(() => {
                        form = findChild(window, "nativeImport.dialog");
                        if (!form || !form.opened) return false;
                        const fields = Ui.itemsWithProperty(form.contentItem, "objectName")
                            .filter(control => control.objectName === "nativeImport.projectName");
                        field = fields.length === 1 ? fields[0] : null;
                        return assistant.showingActions && ownStarts > 0 && field && field.activeFocus
                            && field.text.length > 0 && field.text !== recipe.project_name;
                }, import265_observationMs(recipe), "IMPORT265 SETUP: actual original paced form text is partially typed before intervention");
                compare(Session.project, original, "IMPORT265 SETUP: real form staging has made no scientific owner commit");
                const applyCandidates = Ui.itemsWithProperty(form.contentItem, "objectName")
                    .filter(control => control.objectName === "nativeImport.apply");
                compare(applyCandidates.length, 1, "IMPORT267 SETUP: one real actual form Apply owns the native stage");
                applyTarget = applyCandidates[0];
                applyLife313 = lifetime313(applyTarget); applyTarget.clicked.connect(applyReceipt);
                if (cancelled) {
                    if (data.tag === "visible-stop") {
                        const stop = item("assistant.stopVisibleAction");
                        verify(stop.visible && stop.enabled && Ui.exposed(stop), "IMPORT265 SETUP: real Stop is exposed");
                        let stopped = 0;
                        function stopReceipt() { ++stopped; }
                        stop.clicked.connect(stopReceipt);
                        try {
                            mouseClick(stop);
                            compare(stopped, 1, "IMPORT267 SETUP: original genuine Stop click reaches its actual receiver");
                        } finally { stop.clicked.disconnect(stopReceipt); }
                    } else if (data.tag === "visible-manual-input") {
                        fieldLife313 = lifetime313(field); field.textEdited.connect(editReceipt);
                        keyClick(Qt.Key_Z);
                        compare(edits, 1, "IMPORT265: original genuine user key reaches its actual focused form receiver once");
                        verify(field.text.includes("z") || field.text.includes("Z"), "IMPORT265: the original user's key text is retained");
                        retained = field.text;
                    } else if (data.tag === "visible-close") {
                        // Actual Qt close/hide lifecycle, no invented inherited Escape policy.
                        let hides = 0;
                        function hideReceipt() { ++hides; }
                        form.aboutToHide.connect(hideReceipt);
                        try {
                            form.close();
                            tryCompare(form, "opened", false, 2000, "IMPORT267: actual original Qt form closes");
                            compare(hides, 1, "IMPORT267: the genuine original form hide boundary is reached once");
                        } finally { form.aboutToHide.disconnect(hideReceipt); }
                    } else if (data.tag === "visible-source-refusal-close") {
                        verify(!assistant.removeSelectedFile(cif[0].id),
                            "IMPORT270: active original staging honestly refuses a busy source removal");
                        compare(JSON.stringify(Probe.rows(assistant.selectedFiles)), JSON.stringify(selected),
                            "IMPORT270: refused active removal preserves every original source grant");
                        compare(Session.project, original,
                            "IMPORT270: refused source maintenance cannot change the original owner");
                        compare(applyClicks, 0,
                            "IMPORT270: active source refusal precedes any scientific Apply");
                        form.close();
                        tryCompare(form, "opened", false, 2000,
                            "IMPORT270: actual supported Qt form close then cancels the original stage");
                    } else {
                        Session.closeProject();
                        verify(Session.createProject("Original replacement owner", "Original replacement metadata"),
                            "IMPORT265: genuine Session action installs the independent replacement owner");
                        replacement = Session.project;
                        replacementLife313 = lifetime313(replacement);
                    }
                    tryVerify(() => !assistant.canCancel && !assistant.showingActions
                        && (data.tag === "visible-new-owner"
                            || visible185_outcome(callId, previous) !== null), 10000,
                        "IMPORT265: original staged request actually retires after real user/owner/source action");
                    rendered();
                    if (retained !== null) compare(field.text, retained, "IMPORT265: no later stage cleanup overwrites original manual text");
                    compare(Session.project, replacement || original, "IMPORT265: retired original staging cannot install a late owner");
                    if (original) compare(import265_owner(original), metadata, "IMPORT265: cancelled stage preserves original metadata/settings/path");
                    const outcome = visible185_outcome(callId, previous);
                    verify((data.tag === "visible-new-owner" && outcome === null)
                        || (outcome !== null && !outcome.adopted
                            && !["completed", "created"].includes(outcome.status)),
                        "IMPORT265: retired before-Apply work cannot claim real scientific adoption");
                    compare(applyClicks, 0, "IMPORT267: real staged retirement precedes any Apply click");
                    verify(assistant.connected && JSON.stringify(Probe.rows(assistant.models)) === models,
                        "IMPORT267: real staging retirement preserves the original genuine account/catalog");
                    if (data.tag === "visible-new-owner") {
                        compare(Probe.rows(assistant.selectedFiles).length, 0,
                            "IMPORT270: genuine replacement owner has fresh scope without old source grants");
                        compare(replacement.structures.count, 0,
                            "IMPORT270: cancelled original cannot populate the new empty owner's structures");
                        compare(replacement.experiments.count, 0,
                            "IMPORT270: cancelled original cannot populate the new empty owner's experiments");
                    } else compare(JSON.stringify(Probe.rows(assistant.selectedFiles)), JSON.stringify(selected),
                        "IMPORT267: same-owner retirement actions preserve original source grants");
                    return;
                }
                tryVerify(() => {
                    const outcome = visible185_outcome(callId, previous);
                    return outcome !== null && outcome.adopted === true && outcome.presentation_complete === true
                        && outcome.status === (same ? "completed" : "created")
                        && !assistant.canCancel && !assistant.showingActions;
                }, import265_observationMs(recipe), "IMPORT265: original once-only native result confirms real visible adoption and complete presentation");
                compare(applyClicks, 1, "IMPORT267: visible helper clicks the same actual Apply exactly once");
                verify(ownStarts > 0, "IMPORT267: supported visible import has an actual pointer presentation");
                form = item("nativeImport.dialog");
            }
            if (form.opened) {
                form.close();
                tryCompare(form, "opened", false, 2000, "IMPORT267: actual postcommit form hides before ordinary Undo");
            }
            const project = Session.project;
            verify(project !== null, "IMPORT265: successful real import supplies an actual project");
            if (original) {
                compare(project, original, "IMPORT265: saved scientifically empty PVM owner is populated in place");
                compare(import265_owner(project), metadata, "IMPORT265: original user metadata/settings/saved path survive recipe defaults");
                verify(project.modified, "IMPORT265: same-owner scientific completion is modified, never silently saved");
            } else {
                compare(project.name, recipe.project_name, "IMPORT265: no-owner adoption uses the original supplied name");
                compare(project.description, recipe.description, "IMPORT265: no-owner adoption retains exact original description");
                compare(project.path, "", "IMPORT265: creation alone never invents a saved destination");
            }
            tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment), 10000,
                "IMPORT265: the actual same native calculation finishes and is genuinely current");
            import265_science(project);
            compare(JSON.stringify(Probe.rows(assistant.selectedFiles)), JSON.stringify(selected),
                "IMPORT267: genuine selected IDs/source grants survive actual creation");
            if (original) compare(Probe.readFile(original.path + "/project.edi"), originalSavedText,
                "IMPORT267: model completion does not silently overwrite the independent saved empty source");
            if (original) {
                verify(project.canUndo, "IMPORT265: actual same-owner completion owns one recorded science Undo");
                Ui.click(this, Probe, window, "appBar.button.undo");
                tryVerify(() => project.structures.count === 0 && project.experiments.count === 0 && !project.calculating,
                    10000, "IMPORT265: one real appbar Undo restores original empty science");
                compare(Session.project, original, "IMPORT265: one Undo retains original owner");
                compare(import265_owner(original), metadata, "IMPORT265: complete Undo retains original metadata/settings/path");
                compare(original.canUndo, originalUndo, "IMPORT265: one Undo restores original recorded-history availability");
                compare(Probe.readFile(original.path + "/project.edi"), originalSavedText,
                    "IMPORT267: genuine model Undo never rewrites the original saved empty file");
            }
            if (manual) compare(assistant.connected, false, "IMPORT265: manual form success never silently signs in");
            else verify(accountWasConnected && assistant.connected && JSON.stringify(Probe.rows(assistant.models)) === models,
                "IMPORT265: original managed account/catalog survive actual visible import and Undo");
        } finally {
            console.log("IMPORT265_STATE", data.tag, JSON.stringify({currentOwner: String(Session.project),
                originalOwner: identity313(originalLife313), replacementOwner: identity313(replacementLife313),
                connected: assistant.connected, canCancel: assistant.canCancel, showingActions: assistant.showingActions,
                nativeImport: assistant.nativeImport, pointerStarts: ownStarts, userEdits: edits,
                applyClicks: applyClicks, originalOutcome: visible185_outcome(callId, previous)}));
            disconnect313(fieldLife313, field, "textEdited", editReceipt);
            disconnect313(applyLife313, applyTarget, "clicked", applyReceipt);
            assistant.actionPointerShown.disconnect(pointerReceipt);
            if (assistant.canCancel) assistant.cancel();
        }
    }

    // BG285 public-stage tests: actual Main/default Session, real Qt input and
    // original native envelopes. Numeric expectations are declared fixture inputs.
    function background285_rows(project) {
        return Probe.rows(project.currentExperiment.background).map(row => ({
            id: row.id, position: row.position, intensity: row.intensity.value,
            free: row.intensity.free, hasUncertainty: row.intensity.hasUncertainty,
            uncertainty: row.intensity.uncertainty, uid: row.intensity.uid,
            minimum: row.intensity.minimum, maximum: row.intensity.maximum,
            name: row.intensity.name, units: row.intensity.displayUnits
        }));
    }
    function background285_unrelated(project) {
        return JSON.stringify(visible185_parameters(project).filter(p => !p.path.includes(".background["))
            .map(p => [p.path, p.value, p.free, p.hasUncertainty, p.uncertainty]));
    }
    // Observe the selected public sidebar pane and its original source-bound form.
    // Basic/Extra retain separate component trees; a page-wide name is not ownership.
    function background294_under(control, owner) {
        for (let current = control; current; current = current.parent)
            if (current === owner) return true;
        return false;
    }
    function background294_fact(control) {
        if (!control) return null;
        try {
            const ancestors = [];
            for (let parent = control.parent; parent && ancestors.length < 14; parent = parent.parent)
                ancestors.push({identity: String(parent), name: parent.objectName,
                    visible: parent.visible, enabled: parent.enabled, clip: parent.clip,
                    shownTier: parent.shownTier === undefined ? null : parent.shownTier,
                    categoryId: parent.categoryId === undefined ? null : parent.categoryId,
                    currentIndex: parent.currentIndex === undefined ? null : parent.currentIndex,
                    currentItem: parent.currentItem === undefined ? null : String(parent.currentItem),
                    interactive: parent.interactive === undefined ? null : parent.interactive,
                    hasItemAt: typeof parent.itemAt === "function"});
            return {identity: String(control), name: control.objectName,
                visible: control.visible, enabled: control.enabled, opacity: control.opacity,
                geometry: rect(control), inPane: Ui.inPane(control), exposed: Ui.exposed(control),
                activeFocus: control.activeFocus,
                readOnly: control.readOnly === undefined ? null : control.readOnly,
                text: typeof control.text === "string" ? control.text.slice(0, 80) : null,
                hasTextEdited: typeof control.textEdited === "function",
                hasClicked: typeof control.clicked === "function",
                currentIndex: control.currentIndex === undefined ? null : control.currentIndex,
                currentItem: control.currentItem === undefined ? null : String(control.currentItem),
                interactive: control.interactive === undefined ? null : control.interactive,
                hasItemAt: typeof control.itemAt === "function",
                sourceModel: control.sourceModel === undefined ? null : String(control.sourceModel),
                ancestors: ancestors};
        } catch (error) { return {observationError: String(error)}; }
    }
    function background313_lives(scope) {
        const alive = {};
        for (const key of Object.keys(scope.lifetimes)) alive[key] = alive313(scope.lifetimes[key]);
        return alive;
    }
    function background313_candidates(scope, controls) {
        scope.ownershipCandidates = controls;
        scope.ownershipCandidateLives = controls.map(lifetime313);
        scope.ownershipCandidateFacts = controls.map(background294_fact);
    }
    function background294_observe(stage, scope) {
        try {
            const slot = Ui.page(window);
            const page = window.assistantWorkflowPage;
            const originalViewAlive = scope && alive313(scope.lifetimes.view);
            const names = ["background.stage", "background.stage.id", "background.stage.apply"];
            const candidates = Ui.itemsWithProperty(slot, "objectName")
                .filter(control => names.includes(control.objectName));
            console.log("BACKGROUND294_CANDIDATES", stage, JSON.stringify({
                page: String(slot), pageIndex: window.appBarCentralTabs.currentIndex,
                selectedSlotItem: slot && slot.item !== undefined ? String(slot.item) : null,
                workflowPage: String(page), pageCurrent: page ? page.current : null,
                pageName: page ? page.pageName : null,
                pageProject: page ? String(page.project) : null,
                pageHasExperiment: page ? page.experiment !== undefined : false,
                pageExperiment: page && page.experiment !== undefined ? String(page.experiment) : null,
                currentOwner: String(Session.project), expectedOwner: scope ? identity313(scope.lifetimes.project) : null,
                originalSlot: scope ? identity313(scope.lifetimes.slot) : null,
                originalPage: scope ? identity313(scope.lifetimes.page) : null,
                originalExperiment: scope ? identity313(scope.lifetimes.experiment) : null,
                sidebar: scope ? identity313(scope.lifetimes.sidebar) : null,
                view: scope ? identity313(scope.lifetimes.view) : null,
                viewIndex: originalViewAlive ? scope.view.currentIndex : null,
                selectedPane: originalViewAlive ? String(scope.view.currentItem) : null,
                originalPane: scope ? identity313(scope.lifetimes.pane) : null,
                selectedPaneContent: originalViewAlive && scope.view.currentItem
                    ? String(scope.view.currentItem.item) : null,
                originalPaneContent: scope ? identity313(scope.lifetimes.content) : null,
                originalForm: scope ? identity313(scope.lifetimes.form) : null,
                focused: String(window.activeFocusItem), candidateCount: candidates.length,
                candidates: candidates.slice(0, 12).map(background294_fact),
                originalLifetimesAlive: scope ? background313_lives(scope) : {},
                ownershipCandidates: scope && scope.ownershipCandidateFacts
                    ? scope.ownershipCandidateFacts.slice(0, 8) : [],
                ownershipCandidateAlive: scope && scope.ownershipCandidateLives
                    ? scope.ownershipCandidateLives.slice(0, 8).map(alive313) : [],
                ownershipCandidateCount: scope && scope.ownershipCandidates ? scope.ownershipCandidates.length : 0}));
        } catch (error) { console.log("BACKGROUND294_OBSERVATION_ERROR", stage, String(error)); }
    }
    function background294_scope(project, stage) {
        // Ui.page is the contentArea Loader. Main's public alias is its loaded
        // WorkflowPage; only that declared owner has current/project/experiment.
        const scope = {project: project, experiment: project.currentExperiment,
            slot: Ui.page(window), page: window.assistantWorkflowPage,
            sidebar: null, view: null, pane: null, content: null, form: null};
        scope.lifetimes = {};
        for (const key of ["project", "experiment", "slot", "page", "sidebar", "view", "pane", "content", "group", "form", "source"])
            scope.lifetimes[key] = lifetime313(scope[key] === undefined ? null : scope[key]);
        background294_observe(stage + "-before-ownership", scope);
        const page = scope.page;
        verify(Session.project === project && scope.slot !== null && page !== null
            && window.appBarCentralTabs.currentIndex === AppState.Page.Experiment
            && scope.slot === window.contentArea[AppState.Page.Experiment]
            && scope.slot.item === page && window.assistantWorkflowPage === page
            && page.current && page.project === project
            && scope.experiment !== null && page.experiment === scope.experiment
            && project.currentExperiment === scope.experiment,
            "BG294 SETUP: operative current Experiment page belongs to the exact original project/experiment");
        const sidebars = Ui.itemsWithProperty(page, "objectName").filter(control =>
            control.objectName === "workflow.experiment.manualSidebar");
        background313_candidates(scope, sidebars);
        background294_observe(stage + "-sidebar-candidates", scope);
        compare(sidebars.length, 1, "BG294 SETUP: current Experiment page owns exactly one ordinary sidebar");
        scope.sidebar = sidebars[0];
        scope.lifetimes.sidebar = lifetime313(scope.sidebar);
        // Public EA SideBar: its direct-child SwipeView owns retained Loader items;
        // TabBar's internal view is not a direct child with this Container contract.
        const views = Ui.itemsWithProperty(scope.sidebar, "interactive").filter(control =>
            control.parent === scope.sidebar && typeof control.itemAt === "function"
            && control.currentIndex !== undefined && control.currentItem !== undefined);
        background313_candidates(scope, views);
        background294_observe(stage + "-view-candidates", scope);
        compare(views.length, 1, "BG294 SETUP: actual ordinary sidebar owns one direct selected-pane view");
        scope.view = views[0];
        scope.lifetimes.view = lifetime313(scope.view);
        scope.pane = scope.view.currentItem;
        scope.lifetimes.pane = lifetime313(scope.pane);
        const basic = Ui.itemsWithProperty(scope.sidebar, "objectName").filter(control =>
            control.objectName === "sideBar.tab.basic" && typeof control.checked === "boolean");
        background294_observe(stage + "-selected-pane", scope);
        compare(basic.length, 1, "BG294 SETUP: exact sidebar has one genuine Main tab control");
        verify(basic[0].checked && scope.view.currentIndex === 0 && scope.pane !== null
            && scope.pane === scope.view.itemAt(0)
            && scope.pane.item !== undefined && scope.pane.item !== null,
            "BG294 SETUP: original real Main click selects the actual Basic Loader, not retained Extras content");
        // WorkflowPage declares Basic/Extras as Loader items of the sidebar view.
        // Category properties belong to their loaded content, never the Loader.
        scope.content = scope.pane.item;
        scope.lifetimes.content = lifetime313(scope.content);
        const groups = Ui.itemsWithProperty(scope.content, "categoryId").filter(control =>
            control.objectName === "group.background" && control.categoryId === "background"
            && control.shownTier === "Basic");
        background313_candidates(scope, groups);
        background294_observe(stage + "-category-candidates", scope);
        compare(groups.length, 1, "BG294 SETUP: actual current Basic pane owns exactly one Background category");
        scope.group = groups[0];
        scope.lifetimes.group = lifetime313(scope.group);
        const forms = Ui.itemsWithProperty(scope.group, "objectName").filter(control =>
            control.objectName === "background.stage"
            && control.sourceModel === scope.experiment.background);
        background313_candidates(scope, forms);
        background294_observe(stage + "-form-candidates", scope);
        compare(forms.length, 1, "BG294 SETUP: original category owns exactly one stage for the original background model");
        scope.form = forms[0];
        scope.lifetimes.form = lifetime313(scope.form);
        scope.source = scope.experiment.background;
        scope.lifetimes.source = lifetime313(scope.source);
        background294_observe(stage + "-owned-form", scope);
        return scope;
    }
    function background294_control(scope, name, stage) {
        background294_observe(stage + "-before-control", scope);
        verify(Object.keys(scope.lifetimes).every(key => alive313(scope.lifetimes[key])),
            "BG313 SETUP: all original scoped QObject receivers remain alive before property access");
        verify(Session.project === scope.project && Ui.page(window) === scope.slot
            && scope.slot === window.contentArea[AppState.Page.Experiment]
            && window.appBarCentralTabs.currentIndex === AppState.Page.Experiment
            && scope.slot.item === scope.page && window.assistantWorkflowPage === scope.page
            && scope.page.current && scope.page.project === scope.project
            && scope.page.experiment === scope.experiment
            && scope.project.currentExperiment === scope.experiment
            && scope.view.currentItem === scope.pane && scope.view.currentIndex === 0
            && scope.pane === scope.view.itemAt(0) && scope.pane.item === scope.content
            && background294_under(scope.group, scope.content)
            && background294_under(scope.form, scope.group)
            && scope.form.sourceModel === scope.source
            && scope.experiment.background === scope.source,
            "BG294 SETUP: exact original current form/pane/source ownership remains valid before accessing its receiver");
        const found = Ui.itemsWithProperty(scope.form, "objectName")
            .filter(control => control.objectName === name);
        background313_candidates(scope, found);
        background294_observe(stage + "-receiver-candidates", scope);
        compare(found.length, 1, "BG294 SETUP: exactly one original named receiver belongs to the operative source-bound form: " + name);
        return found[0];
    }
    function background294_expose(scope, name) {
        const control = background294_control(scope, name, "expose-" + name);
        // Existing genuine viewport reveal, followed by original Ui input. No
        // visibility/focus/model write, alternate click executor or hidden opener.
        Ui.scrollIntoView(control); rendered();
        background294_observe("exposed-" + name, scope);
        verify(Ui.control(Probe, window, name) === control && control.enabled && Ui.exposed(control),
            "BG294 SETUP: existing physical input lookup resolves the exact exposed original form receiver: " + name);
        return control;
    }
    function background294_text(scope, name, text) {
        const original = background294_expose(scope, name);
        verify(typeof original.textEdited === "function" && original.readOnly === false,
            "BG294 SETUP: original scoped editor is the actual editable TextField signal receiver");
        compare(relation245_text(name, text), original,
            "BG294: unchanged real input helper types into the exact original scoped editor");
    }
    function background285_operation(operation, scope) {
        const combo = background294_control(scope, "background.stage.operation", "operation");
        verify(combo !== null, "BG SETUP: actual ordinary operation ComboBox exists");
        Ui.scrollIntoView(combo); rendered();
        verify(Ui.control(Probe, window, "background.stage.operation") === combo,
            "BG294 SETUP: actual operation input resolves the original form ComboBox");
        Ui.click(this, Probe, window, "background.stage.operation");
        keyClick(Qt.Key_Home);
        const index = ["add", "update", "remove"].indexOf(operation);
        verify(index >= 0, "BG SETUP: operation belongs to the public ordered three-value selector");
        for (let i = 0; i < index; ++i) keyClick(Qt.Key_Down);
        keyClick(Qt.Key_Return);
        tryCompare(combo, "currentValue", operation, 2000,
            "BG: real keys select the exact original requested operation");
        tryVerify(() => !combo.popup.visible && !combo.popup.opened, 2000,
            "BG SETUP: original operation popup actually closes before next real input");
    }
    function background285_stage(operation, id, position, intensity, free, scope) {
        visible185_page("experiment");
        Ui.click(this, Probe, window, "sideBar.tab.basic");
        Ui.expandGroup(this, Probe, window, "group.background");
        if (Ui.control(Probe, window, "background.stage.id") === null) {
            Ui.click(this, Probe, window, "background.append");
            tryVerify(() => Ui.control(Probe, window, "background.stage.id") !== null, 2000,
                "BG SETUP: genuine ordinary Add point opens the original staged form before input");
        }
        background285_operation(operation, scope);
        background294_text(scope, "background.stage.id", id);
        if (operation !== "remove") {
            background294_text(scope, "background.stage.position", String(position));
            background294_text(scope, "background.stage.intensity", String(intensity));
            const flag = background294_control(scope, "background.stage.free", "free");
            verify(flag !== null, "BG SETUP: genuine staged free checkbox exists");
            Ui.scrollIntoView(flag); rendered();
            verify(Ui.control(Probe, window, "background.stage.free") === flag,
                "BG294 SETUP: actual free input resolves the original form checkbox");
            if (flag.checked !== free) Ui.click(this, Probe, window, "background.stage.free");
            compare(flag.checked, free, "BG: actual ordinary free control stores only requested draft flag");
        }
    }
    function background285_observationMs(operation, id, position, intensity) {
        // Same public input pacing as prior relation/import actors: movement500,
        // press100, relaxation500, key100. Eight possible real stage actions plus
        // three declared text entries, SelectAll/Backspace/Return (4 extra keys).
        const texts = operation === "remove" ? [id] : [id, String(position), String(intensity)];
        return 10000 + 1100 * 8 + 100 * texts.reduce((n, text) => n + [...text].length + 4, 0);
    }
    function test_background285_real_stage_and_original_rpc_data() {
        return ["manual-add", "manual-update", "manual-remove", "visible-add-cw",
            "visible-update-tof", "visible-remove", "stop", "manual-takeover",
            "preexisting-draft", "new-owner"].map(tag => ({tag: tag}));
    }
    function test_background285_real_stage_and_original_rpc(data) {
        verify(Session.openProject(Probe.referenceUrl("Original declared background input")),
            "BG SETUP: independently generated original scientific source opens through real Session");
        const project = Session.project;
        const projectLife313 = lifetime313(project);
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment), 10000,
            "BG SETUP: original actual calculation is current before staging/input baselines");
        const manual = ["manual-add", "manual-update", "manual-remove"].includes(data.tag);
        const operation = data.tag === "manual-remove" || data.tag === "visible-remove" ? "remove"
            : data.tag === "manual-update" || data.tag === "visible-update-tof" ? "update" : "add";
        const id = operation === "add" ? "native-bg-original" : "p1";
        const position = data.tag === "visible-update-tof" ? 4200 : operation === "update" ? 21.5 : 32.5;
        const intensity = 19.75;
        const original = background285_rows(project);
        compare(original.length, 3, "BG SETUP: independent fixture carries all three declared anchors");
        const inputs = visible185_inputs(project);
        const unrelated = background285_unrelated(project);
        const declarations = relation245_declarations(project);
        const shape = relation246_shape(project);
        const previousUndo = item("appBar.button.undo").enabled;
        const previousIds = new Set(Probe.rows(assistant.messages).map(row => row.id));
        const oldHistory = Probe.rows(assistant.messages).map(row => JSON.stringify(row));
        let models = null;
        if (!manual) {
            toggle(); assistant.signIn(); visible185_ready("background285-bootstrap");
            if (assistant.contextConsentRequired) assistant.signIn();
            visible185_ready("background285-current-context");
            verify(!assistant.contextConsentRequired, "BG SETUP: actual current original scope is disclosed once");
            compare(assistant.showActions, false, "BG: fresh actual Session begins in default normal mode");
            const show = item("assistant.showActions");
            verify(show.enabled && show.visible, "BG SETUP: genuine mode checkbox is actionable");
            mouseClick(show); compare(assistant.showActions, true, "BG: real checkbox enables visible route");
            models = JSON.stringify(Probe.rows(assistant.models));
            closeAssistant388();
        }
        visible185_page("experiment");
        Ui.click(this, Probe, window, "sideBar.tab.basic");
        Ui.expandGroup(this, Probe, window, "group.background");
        if (manual || data.tag === "preexisting-draft") {
            Ui.click(this, Probe, window, "background.append");
            tryVerify(() => Ui.control(Probe, window, "background.stage.id") !== null, 2000,
                "BG SETUP: original ordinary Add action exposes the real form before controls/input");
        }
        // Passive original handles belong to the actual current pane/category/form,
        // including a still-hidden native stage. Exposure follows its genuine opener.
        const scope = background294_scope(project, data.tag);
        const idField = background294_control(scope, "background.stage.id", "original-id");
        const apply = background294_control(scope, "background.stage.apply", "original-apply");
        verify(typeof idField.textEdited === "function" && idField.readOnly === false
            && typeof apply.clicked === "function",
            "BG294 SETUP: unique original ID/Apply are the real editable/clickable signal receivers");
        let edits = 0, applies = 0, starts = 0, takeovers = 0;
        function edited() { ++edits; }
        function applied() { ++applies; }
        function pointerStarted() { ++starts; }
        function tookOver() { ++takeovers; }
        idField.textEdited.connect(edited); apply.clicked.connect(applied);
        assistant.actionPointerShown.connect(pointerStarted);
        assistant.actionManualTakeover.connect(tookOver);
        const idLife313 = lifetime313(idField), applyLife313 = lifetime313(apply);
        let replacementLife313 = null;
        let manualText = null, replacement = null, draft = null;
        const call = "background285-" + data.tag;
        try {
            if (manual || data.tag === "preexisting-draft") {
                background285_stage(operation, id, position, intensity, true, scope);
                compare(JSON.stringify(background285_rows(project)), JSON.stringify(original),
                    "BG: real staged typing/free selection and ordinary focus changes never mutate before Apply");
                if (data.tag === "preexisting-draft") {
                    draft = {id: idField.text, focus: window.activeFocusItem,
                        start: window.activeFocusItem.selectionStart, end: window.activeFocusItem.selectionEnd};
                }
            }
            if (manual) {
                compare(background294_expose(scope, "background.stage.apply"), apply,
                    "BG294 SETUP: actual ordinary Apply belongs to the same original retained form");
                Ui.click(this, Probe, window, "background.stage.apply");
            }
            else {
                assistant.send("Perform the original defined background operation " + data.tag);
                if (data.tag !== "preexisting-draft") {
                    tryVerify(() => Ui.control(Probe, window, "background.stage.id") === idField
                        && Ui.control(Probe, window, "background.stage.apply") === apply,
                        background285_observationMs(operation, id, position, intensity),
                        "BG SETUP: original native helper actually opens its genuine form before input/exposure assertions");
                }
            }
            if (["stop", "manual-takeover", "new-owner"].includes(data.tag)) {
                tryVerify(() => assistant.showingActions && assistant.canCancel && starts > 0
                    && edits > 0 && idField.text.length > 0 && idField.text !== id,
                    background285_observationMs(operation, id, position, intensity),
                    "BG INTERVAL SETUP: actual original partial staged text and real painted-helper route are reached");
                verify(item("assistant.actionPointer").opacity > 0,
                    "BG INTERVAL SETUP: current helper actually paints its original pointer");
                compare(JSON.stringify(background285_rows(project)), JSON.stringify(original),
                    "BG: partial native form has zero scientific effect before original Apply");
                if (data.tag === "stop") {
                    const stop = item("assistant.stopVisibleAction");
                    verify(stop.enabled && Ui.exposed(stop), "BG SETUP: genuine original Stop is exposed");
                    mouseClick(stop);
                } else if (data.tag === "manual-takeover") {
                    compare(background294_expose(scope, "background.stage.id"), idField,
                        "BG294 SETUP: original manual takeover targets the same actually exposed current-form editor");
                    Ui.click(this, Probe, window, "background.stage.id");
                    compare(window.activeFocusItem, idField, "BG: original actual manual receiver gains focus normally");
                    keyClick("x");
                    verify(idField.text.includes("x"), "BG: original genuine manual key survives native retirement");
                    manualText = idField.text;
                } else {
                    Session.closeProject();
                    verify(Session.createProject("BG-new-owner", "Original real replacement"),
                        "BG SETUP: actual Session creates a distinct genuinely empty replacement owner");
                    replacement = Session.project;
                    replacementLife313 = lifetime313(replacement);
                    verify(replacement !== project, "BG: original A cannot acquire the new B owner");
                }
            }
            const retired = ["stop", "manual-takeover", "new-owner", "preexisting-draft"].includes(data.tag);
            if (!manual) {
                tryVerify(() => !assistant.canCancel && !assistant.showingActions
                    && (data.tag === "new-owner" || visible185_outcome(call, previousIds) !== null),
                    background285_observationMs(operation, id, position, intensity),
                    "BG: same-owner original retained outcome and real terminal presentation settle within the existing bound");
                const outcome = visible185_outcome(call, previousIds);
                if (data.tag === "new-owner") {
                    if (outcome !== null) verify(!["edited", "applied_unconfirmed"].includes(outcome.status),
                        "BG: any surviving old-A row cannot claim an edit of the new owner");
                    compare(Session.project, replacement, "BG: later original cleanup cannot replace B");
                    compare(replacement.structures.count, 0, "BG: stale A never injects old science into new empty owner");
                    compare(replacement.experiments.count, 0, "BG: old staged Apply cannot create a bank in B");
                    compare(applies, 0, "BG: retired original A never clicks a late Apply");
                    return;
                }
                verify(outcome !== null, "BG: same-owner original native outcome is actually retained");
                if (retired) {
                    verify(!["edited", "applied_unconfirmed"].includes(outcome.status),
                        "BG: pre-Apply draft/Stop/manual retirement honestly refuses without scientific success");
                    compare(applies, 0, "BG: genuine retirement/draft refusal cannot click original Apply later");
                    if (draft !== null) {
                        compare(idField.text, draft.id, "BG: preexisting genuine draft text remains intact");
                        compare(window.activeFocusItem, draft.focus, "BG: refusal never blurs/commits existing draft");
                        compare(draft.focus.selectionStart, draft.start, "BG: original draft selection start survives");
                        compare(draft.focus.selectionEnd, draft.end, "BG: original draft selection end survives");
                    }
                    if (manualText !== null) {
                        verify(takeovers > 0, "BG: actual manual event is recognized in the reached helper interval");
                        compare(idField.text, manualText, "BG: no late helper typing overwrites original manual text");
                    }
                } else {
                    compare(outcome.status, "edited", "BG: actual visible edit is confirmed, never normalized from uncertainty");
                    compare(applies, 1, "BG: the genuine native prearm reaches exactly one ordinary Apply click");
                    verify(starts > 0 && edits > 0, "BG: real pointer and typed controls perform native work");
                }
            }
            if (!retired) {
                tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment), 10000,
                    "BG: real post-edit calculation becomes current before scientific readback");
                const rows = background285_rows(project);
                let expected = original.map(row => Object.assign({}, row));
                if (operation === "remove") expected = expected.filter(row => row.id !== id);
                else if (operation === "add") expected.push({id: id, position: position, intensity: intensity, free: true});
                else expected = expected.map(row => row.id === id ? Object.assign({}, row,
                    {position: position, intensity: intensity, free: true}) : row);
                compare(JSON.stringify(rows.map(row => [row.id, row.position, row.intensity, row.free])),
                    JSON.stringify(expected.map(row => [row.id, row.position, row.intensity, row.free])),
                    "BG: actual ordinary/visible Apply publishes the complete exact requested arrangement");
                Ui.click(this, Probe, window, "appBar.button.undo");
                compare(JSON.stringify(background285_rows(project)), JSON.stringify(original),
                    "BG: ONE actual appbar Undo restores all original ordered keys/values/SU/free/spec metadata");
            } else compare(JSON.stringify(background285_rows(project)), JSON.stringify(original),
                "BG: refusal/retirement preserves every original background parameter");
            compare(item("appBar.button.undo").enabled, previousUndo,
                "BG: one Apply/Undo or refusal preserves actual prior Undo availability");
            compare(background285_unrelated(project), unrelated, "BG: all unrelated scientific parameters/SUs/free flags survive");
            compare(visible185_inputs(project), inputs, "BG: every actual observation/sigma/mask/phase/weight is unchanged");
            compare(relation245_declarations(project), declarations, "BG: all preexisting relation declarations survive");
            compare(relation246_shape(project), shape, "BG: complete original composition/fractional coordinates survive");
            compare(Session.project, project, "BG: ordinary/visible transaction retains exact original owner");
            if (!manual) {
                verify(assistant.connected, "BG: genuine managed account survives scientific work and Undo");
                compare(JSON.stringify(Probe.rows(assistant.models)), models, "BG: real catalog never repaired by signing in again");
                verify(oldHistory.every(row => Probe.rows(assistant.messages).some(value => JSON.stringify(value) === row)),
                    "BG: original history remains intact through shared editor execution");
            }
        } finally {
            background294_observe("finally-" + data.tag, scope);
            console.log("BACKGROUND285_STATE", data.tag, JSON.stringify({currentOwner: String(Session.project),
                originalOwner: identity313(projectLife313), replacementOwner: identity313(replacementLife313), connected: assistant.connected,
                canCancel: assistant.canCancel, showingActions: assistant.showingActions, edits: edits,
                applies: applies, starts: starts, takeovers: takeovers,
                originalOutcome: visible185_outcome(call, previousIds)}));
            disconnect313(idLife313, idField, "textEdited", edited);
            disconnect313(applyLife313, apply, "clicked", applied);
            assistant.actionPointerShown.disconnect(pointerStarted);
            assistant.actionManualTakeover.disconnect(tookOver);
            if (assistant.canCancel) assistant.cancel();
        }
    }
    function ux289_descendantText(root) {
        return Ui.itemsWithProperty(root, "text").filter(value => value.visible)
            .map(value => String(value.text));
    }
    function test_ux289_original_ack_consumes_only_submitted_presentation_data() {
        return [{tag: "unchanged-draft"}, {tag: "new-identical-draft"}, {tag: "active-ime"},
            {tag: "server-refusal"}, {tag: "new-file-sent-revoke"}];
    }
    function test_ux289_original_ack_consumes_only_submitted_presentation(data) {
        const project = Session.project;
        const source = "tests/fixtures/assistant/reference/PbSO4-Wyckoff.cif";
        const beforeBytes = Probe.readFile(source);
        const intent = assistant.beginFileSelection();
        verify(intent.length > 0 && assistant.addSelectedFiles(intent, [Probe.repoUrl(source)]),
            "UX289 SETUP: genuine selected-file intent admits unchanged committed source bytes");
        tryCompare(assistant.selectedFiles, "count", 1, 2000,
            "UX289 SETUP: real selected model publishes the original file");
        function canonicalSelected() {
            return JSON.stringify(Probe.rows(assistant.selectedFiles).map(row => ({id: row.id,
                name: row.name, bytes: row.bytes, textReadable: row.textReadable, format: row.format})));
        }
        const selected = canonicalSelected();
        compare(Probe.rows(assistant.selectedFiles)[0].pending, true,
            "UX289: newly admitted original selected file is pending before any completed input");
        const selectedId = assistant.selectedFiles.text(0, "id");
        verify(selectedId.length > 0, "UX289 SETUP: original selected identity is app-issued");
        toggle();
        assistant.signIn();
        report187_ready("ux289-bootstrap", false);
        if (assistant.contextConsentRequired) assistant.signIn();
        report187_ready("ux289-disclosed", true);
        const account = JSON.stringify(Probe.rows(assistant.models));
        const editor = item("assistant.composer");
        const composer = Probe.objectsWithProperty(window, "textRevision").filter(object =>
            object.firstFocusItem === editor);
        compare(composer.length, 1, "UX289 SETUP: exact original editor has one owning composer revision");
        const text = "Original sent source " + data.tag;
        Ui.click(this, Probe, window, editor.objectName);
        visible185_type(text);
        const beforeRefusal = JSON.stringify(Probe.rows(assistant.messages));
        compare(assistant.submitDraft("   "), "", "UX289: actual empty-input admission returns no original row authority");
        compare(editor.text, text, "UX289: real pre-admission refusal preserves the original editor spelling");
        compare(JSON.stringify(Probe.rows(assistant.messages)), beforeRefusal,
            "UX289: refused admission cannot fabricate a successfully submitted user row");
        compare(Probe.rows(assistant.selectedFiles)[0].pending, true,
            "UX289: refused admission cannot consume a pending selected-file presentation");
        const submittedRevision = composer[0].textRevision;
        const previous = new Set(Probe.rows(assistant.messages).map(row => row.id));
        Ui.click(this, Probe, window, "assistant.send");
        let original = null;
        tryVerify(() => {
            const matches = Probe.rows(assistant.messages).filter(row => !previous.has(row.id)
                && row.kind === "user" && row.text === text);
            if (matches.length !== 1 || matches[0].status !== "pending") return false;
            original = matches[0]; return true;
        }, 2000, "UX289 SETUP: actual once-only original admitted row is pending before wire ACK");
        compare(editor.text, text, "UX289: pre-ACK row publication must preserve the submitted editor spelling");
        compare(canonicalSelected(), selected,
            "UX289: pending presentation cannot revoke original selected identities or authority");
        const popupContent = popup.contentItem;
        verify(popupContent !== null, "UX345 SETUP: original popup has its actual visual content root");
        const originalPreAckChipCandidates345 = Ui.itemsWithProperty(popupContent, "objectName").filter(value =>
            value.objectName === "assistant.file." + selectedId);
        console.info("UX345_DRAFT_CHIP", JSON.stringify({selectedId: selectedId,
            popup: String(popup), content: String(popupContent), candidateCount: originalPreAckChipCandidates345.length,
            candidates: originalPreAckChipCandidates345.slice(0, 4).map(value => ({identity: String(value),
                name: value.objectName, visible: value.visible, rendered: Ui.rendered(value),
                exposed: Ui.exposed(value), width: value.width, height: value.height}))}));
        compare(originalPreAckChipCandidates345.length, 1, "UX345: exactly one draft chip owns the original selected source ID");
        const draftChip = originalPreAckChipCandidates345[0];
        let inComposer = false, inPopup = false, inWindow = false;
        for (let parent = draftChip; parent; parent = parent.parent) {
            inComposer = inComposer || parent === composer[0];
            inPopup = inPopup || parent === popupContent;
            inWindow = inWindow || parent === Ui.windowRoot(window);
        }
        console.info("UX345_DRAFT_ANCESTRY", JSON.stringify({selectedId: selectedId,
            inComposer: inComposer, inPopup: inPopup, inWindow: inWindow}));
        verify(inComposer && inPopup && inWindow,
            "UX345: original draft chip belongs to the original composer, popup content and window");
        compare(Ui.control(Probe, window, draftChip.objectName), draftChip,
            "UX345: original draft chip satisfies the existing current-popup and physical-window exposure contract");
        verify(draftChip.visible && Ui.rendered(draftChip) && Ui.exposed(draftChip),
            "UX289: original pre-ACK draft chip is genuinely rendered inside the visible viewport");
        const filenames = Ui.itemsWithProperty(draftChip, "text").filter(value =>
            value.visible && Ui.rendered(value) && Ui.exposed(value)
                && String(value.text).indexOf("PbSO4-Wyckoff.cif") >= 0);
        console.info("UX345_DRAFT_TEXT", JSON.stringify({selectedId: selectedId,
            inComposer: inComposer, inPopup: inPopup, inWindow: inWindow,
            visibleFilenameCount: filenames.length,
            labels: filenames.slice(0, 4).map(value => ({identity: String(value), text: String(value.text),
                visible: value.visible, rendered: Ui.rendered(value), exposed: Ui.exposed(value)}))}));
        compare(filenames.length, 1, "UX289: pending original attachment stays visibly presented before its ACK");
        if (data.tag === "new-identical-draft") {
            Ui.click(this, Probe, window, editor.objectName);
            visible185_type("New original draft");
            visible185_type(text);
            verify(composer[0].textRevision > submittedRevision,
                "UX289 SETUP: real keyboard edits created a newer revision with identical text");
        }
        if (data.tag === "active-ime") {
            Ui.click(this, Probe, window, editor.objectName);
            const input = Probe.focusedInputMethod233(window, window.activeFocusItem, "原稿", "");
            verify(input.delivered && input.accepted && input.preeditAfter === "原稿",
                "UX289 SETUP: actual focused composer receives genuine uncommitted InputMethod preedit");
            compare(editor.text, text, "UX289 SETUP: genuine preedit precedes committed-text revision");
        }
        const revisionBeforeAck = composer[0].textRevision;
        // Existing public optional read releases the exact real received input in the
        // owned peer. It grants no turn/native authority and mutates no UI/model state.
        assistant.refreshUsage();
        if (data.tag === "server-refusal") {
            tryVerify(() => Probe.rows(assistant.messages).some(row => row.id === original.id
                && row.kind === "user" && row.text === text && row.status !== "pending" && row.status !== "completed")
                && !assistant.canCancel && assistant.connected, 10000,
                "UX295: real original server refusal settles without completed input acknowledgement");
            compare(editor.text, text, "UX295: refused original RPC retains exact submitted editor text");
            compare(composer[0].textRevision, revisionBeforeAck,
                "UX295: refusal does not replace or consume the original editor revision");
            compare(Probe.rows(assistant.selectedFiles)[0].pending, true,
                "UX295: refused original input cannot consume pending selected presentation");
            compare(canonicalSelected(), selected, "UX295: refusal preserves original selected IDs and descriptors");
            const refused = Probe.rows(assistant.messages).filter(row => row.id === original.id);
            compare(refused.length, 1, "UX295: failed original row identity remains unique");
            verify(!refused.some(row => row.status === "completed"),
                "UX295: refusal cannot fabricate durable original completed acknowledgement");
            verify(findChild(window, "assistant.sentFile." + selectedId) === null,
                "UX295: failed original row cannot fabricate a sent-file snapshot chip");
            compare(Probe.readFile(source), beforeBytes, "UX295: refusal leaves original scientific file untouched");
            compare(Session.project, project, "UX295: refusal preserves original displayed project owner");
            compare(JSON.stringify(Probe.rows(assistant.models)), account,
                "UX295: input refusal does not revoke genuine managed account/catalog");
            visible185_capture("ux295-original-refusal");
            return;
        }
        tryVerify(() => Probe.rows(assistant.messages).some(row => row.id === original.id
            && row.kind === "user" && row.text === text && row.status === "completed")
            && !assistant.canCancel && assistant.connected, 10000,
            "UX289: original exact row receives a real ACK and original native turn completes");
        compare(editor.text, ["new-identical-draft", "active-ime"].includes(data.tag) ? text : "",
            "UX289: original ACK consumes only its original editor revision, preserving newer identical draft");
        if (data.tag === "new-identical-draft") compare(composer[0].textRevision, revisionBeforeAck,
            "UX289: old ACK must not edit the newer editor revision");
        if (data.tag === "active-ime") {
            compare(editor.preeditText, "原稿", "UX289: original ACK cannot clear an active original composition");
            verify(window.activeFocusItem === editor || focusWithinManual(editor),
                "UX289: ACK cannot steal the actual composition target");
        }
        const completed = Probe.rows(assistant.messages).filter(row => row.id === original.id);
        compare(completed.length, 1, "UX289: exact original completed user identity remains unique");
        compare(completed[0].payload.type, "ediInput", "UX289: completed input uses the declared bounded descriptor payload");
        const expectedDescriptors = JSON.parse(selected);
        compare(completed[0].payload.files.length, expectedDescriptors.length,
            "UX289: actual submitted descriptor cardinality matches the original selected snapshot");
        for (let index = 0; index < expectedDescriptors.length; ++index)
            for (const key of ["id", "name", "bytes", "textReadable", "format"])
                compare(completed[0].payload.files[index][key], expectedDescriptors[index][key],
                    "UX289: every bounded descriptor field retains the exact original selected snapshot");
        compare(Probe.rows(assistant.selectedFiles)[0].pending, false,
            "UX289: only acknowledged selected identity changes its pending presentation role");
        const rows = Ui.itemsWithProperty(window.contentItem, "rowId").filter(row => row.rowId === original.id && row.assistant === assistant
            && typeof row.resetDetails === "function" && typeof row.copyTechnicalPayload === "function");
        compare(rows.length, 1, "UX289: exactly one actual original user bubble owns the sent attachment presentation");
        const sent = findChild(rows[0], "assistant.sentFile." + selectedId);
        verify(sent !== null && sent.visible, "UX289: exact acknowledged user bubble owns the actual original sent-chip ID");
        if (data.tag === "unchanged-draft") {
            const sentLife592 = lifetime313(sent), flow592 = sent.parent;
            verify(flow592 !== null && Number.isFinite(flow592.width) && flow592.width > 0,
                "SENT592 SETUP: original live sent snapshot has a positive actual available-width owner");
            const flowLife592 = lifetime313(flow592), available592 = flow592.width, width592 = sent.width;
            verify(Number.isFinite(width592) && width592 >= 0 && width592 <= available592,
                "SENT592 SETUP: original real sent delegate respects its available width");
            failOnWarning(/Cannot read property ['"]width['"] of null|Binding loop detected/);
            try {
                sent.parent = null; // Real QQuickItem visual detach, not a replacement or synthetic VM row.
                rendered();
                verify(alive313(sentLife592) && sent.parent === null && alive313(flowLife592),
                    "SENT592: actual original delegate detaches while QObject and its width owner stay alive");
                verify(Number.isFinite(sent.width) && sent.width >= 0 && sent.width <= available592,
                    "SENT592: detaching preserves finite bounded available-width behavior without null-parent errors");
                compare(sent.width, width592, "SENT592: an unchanged width owner keeps the SAME actual sent width");
            } finally {
                if (alive313(sentLife592) && alive313(flowLife592)) sent.parent = flow592;
            }
            rendered();
            compare(sent.parent, flow592, "SENT592: original native sent delegate returns to its same actual Flow");
            compare(sent.width, width592, "SENT592: restoring the same visual owner preserves width");
        }
        verify(ux289_descendantText(rows[0]).some(value => value.indexOf("PbSO4-Wyckoff.cif") >= 0),
            "UX289: actual acknowledged user bubble displays the original sent filename");
        const draftChips = findChild(window, "assistant.file." + selectedId);
        verify(draftChips === null || !draftChips.visible,
            "UX289: consumed sent chip is absent from unsent presentation after ACK");
        compare(canonicalSelected(), selected,
            "UX289: presentation consumption preserves canonical file IDs, descriptors and native usability");
        compare(Probe.readFile(source), beforeBytes, "UX289: original scientific input bytes remain untouched");
        compare(Session.project, project, "UX289: sent presentation does not replace the project owner");
        compare(JSON.stringify(Probe.rows(assistant.models)), account,
            "UX289: exact original managed account and model catalog remain admitted");
        compare(Probe.rows(assistant.messages).filter(row => !previous.has(row.id)
            && row.kind === "user" && row.text === text).length, 1,
            "UX289: original Send has one retained identity, never a second synthetic user input");
        if (data.tag === "new-file-sent-revoke") {
            const extraSource = "tests/fixtures/assistant/reference/inst_d1a.prm";
            const extraBytes = Probe.readFile(extraSource);
            const extraIntent = assistant.beginFileSelection();
            verify(extraIntent.length > 0 && assistant.addSelectedFiles(extraIntent, [Probe.repoUrl(extraSource)]),
                "UX295: later genuine picker admission adds an independent original source ID");
            tryCompare(assistant.selectedFiles, "count", 2, 2000,
                "UX295: both canonical selected sources remain independently represented");
            const later = Probe.rows(assistant.selectedFiles).filter(row => row.id !== selectedId);
            compare(later.length, 1, "UX295: exactly one newly selected identity differs from old ACK snapshot");
            compare(later[0].pending, true, "UX295: earlier completed input cannot consume later selected source");
            compare(Probe.rows(assistant.selectedFiles).filter(row => row.id === selectedId)[0].pending, false,
                "UX295: acknowledged original identity remains consumed independently of later file");
            const retained = Probe.rows(assistant.messages).filter(row => row.id === original.id);
            compare(JSON.stringify(retained[0].payload), JSON.stringify(completed[0].payload),
                "UX295: later selection cannot rewrite historical acknowledged descriptor payload");
            const authority471 = canonicalSelected();
            const snapshotRows471 = Ui.itemsWithProperty(popup.contentItem,"rowId").filter(row => row.rowId === original.id && row.assistant === assistant
            && typeof row.resetDetails === "function" && typeof row.copyTechnicalPayload === "function");
            compare(snapshotRows471.length,1,"UX471: original historical row is re-resolved after actual later-file layout publication");
            gui471_sentSnapshot(snapshotRows471[0], selectedId);
            compare(canonicalSelected(), authority471,
                "UX471: sent snapshot inspection preserves every original and later selected descriptor");
            const pending = ux356_chip(popup.contentItem, later[0], false);
            verify(pending.remove.enabled, "UX471: genuine later PENDING chip retains its original remove action");
            mouseClick(pending.remove, Ui.clickPoint(pending.remove).x, Ui.clickPoint(pending.remove).y);
            tryCompare(assistant.selectedFiles, "count", 1, 2000,
                "UX471: real pending removal revokes only the later pending source authority");
            const remaining = Probe.rows(assistant.selectedFiles);
            compare(remaining[0].id, selectedId, "UX471: pending removal preserves original acknowledged authority");
            compare(remaining[0].pending, false, "UX471: historical ACK never reverts original consumed presentation");
            const historical = Probe.rows(assistant.messages).filter(row => row.id === original.id);
            compare(historical.length, 1, "UX471: pending removal retains exact original user history identity");
            compare(JSON.stringify(historical[0].payload), JSON.stringify(completed[0].payload),
                "UX471: pending removal cannot erase historical sent descriptor snapshot");
            verify(findChild(window, "assistant.sentFile." + selectedId) !== null,
                "UX471: independently retained current authority remains represented as historical sent input");
            compare(Probe.readFile(extraSource), extraBytes, "UX471: later source bytes remain immutable after pending removal");
            compare(Probe.readFile(source), beforeBytes, "UX471: pending removal never deletes original source bytes");
            compare(Session.project, project, "UX471: snapshot and pending removal preserve scientific owner");
            compare(JSON.stringify(Probe.rows(assistant.models)), account,
                "UX471: snapshot and pending removal preserve original genuine account and model catalog");
        }
        visible185_capture("ux289-" + data.tag);
    }


    // Owner471: sent attachments are historical presentation, never revoke controls.
    function gui472_actionCapable(object) {
        if (typeof object.readOnly === "boolean" && !object.readOnly
            && typeof object.text === "string") return true; // Editable native input is not a historical snapshot.
        const signal = typeof object.clicked === "function" || typeof object.pressed === "function"
            || typeof object.tapped === "function" || typeof object.doubleTapped === "function";
        if (!signal) return false;
        // AbstractButton remains keyboard-capable even with no accepted pointer buttons.
        if (typeof object.checkable === "boolean" || typeof object.tapped === "function"
            || typeof object.doubleTapped === "function") return true;
        const mouseArea = typeof object.acceptedButtons === "number" && typeof object.containsMouse === "boolean"
            && typeof object.mouseX === "number" && typeof object.mouseY === "number"
            && typeof object.pressAndHold === "function";
        if (mouseArea && object.acceptedButtons === Qt.NoButton && object.activeFocusOnTab !== true) return false;
        return true; // Unknown action carrier cannot become a passive-decoration exemption.
    }
    function gui471_sentSnapshot(root, id) {
        const chips = Ui.itemsWithProperty(root, "objectName").filter(object => object.objectName === "assistant.sentFile."+id);
        compare(chips.length, 1, "GUI471: SAME original user row owns ONE immutable sent snapshot");
        const chip = chips[0], life = lifetime313(chip), owner = Session.project;
        const controls = Probe.objectsWithProperty(chip,"enabled").filter(gui472_actionCapable);
        compare(controls.length,0,"GUI471: sent snapshot has NO interactive descendants, including hidden revoke controls");
        verify(!gui472_actionCapable(chip),"GUI472: sent snapshot itself has no input-capable native action");
        verify(alive313(life) && Session.project === owner,"GUI471: snapshot inspection retains exact live owner/receiver");
    }
    function gui471_flow(working) {
        const list = item("assistant.messages"), editor = item("assistant.composer");
        compare(list.model,assistant.messages,"GUI471: original conversation retains actual canonical message model");
        verify(list.footerItem !== null && gui393_under(working,list.footerItem),
            "GUI471: real Working belongs INSIDE original scrollable conversation footer");
        const composers = Ui.itemsWithProperty(popup.contentItem,"captureConsentDraft").filter(control =>
            control.assistant === assistant && gui393_under(editor,control));
        compare(composers.length,1,"GUI472: original editor belongs to ONE actual current AssistantComposer");
        const composer = composers[0];
        verify(!gui393_under(working,composer),"GUI472: real Working never occupies actual input/composer subtree");
        for (const name of ["assistant.plan.approve","assistant.question.answer"]) {
            const controls = Ui.itemsWithProperty(popup.contentItem,"objectName").filter(object => object.objectName === name);
            compare(controls.length,1,"GUI471: original pending-decision control remains unique even while hidden: "+name);
            verify(gui393_under(controls[0],list.footerItem),
                "GUI471: SAME original pending decision belongs to conversation flow, not reserved composer region");
        }
        // Owner477: a REAL current Edi error is a chronological chat item, not a footer/fixed strip.
        // Healthy activity must not require a fake inactive notice instance.
        if (assistant.lastError.length > 0) {
            const error477=assistant.lastError;
            const notices=Ui.itemsWithProperty(popup.contentItem,"objectName").filter(object =>
                object.objectName === "assistant.currentNotice" && object.visible);
            compare(notices.length,1,"GUI477: actual active Edi error owns exactly ONE visible current notice");
            const notice=notices[0];
            verify(list.contentItem !== null && gui393_under(notice,list.contentItem)
                && !gui393_under(notice,list.footerItem) && !gui393_under(notice,composer),
                "GUI477: actual Edi notice belongs to scrolling CHAT CONTENT, never footer/input/fixed overlay");
            Ui.scrollIntoView(notice);rendered();
            verify(Ui.rendered(notice) && Ui.text(notice).includes(error477),
                "GUI480: actual exposed scrolling notice preserves its complete truthful current error without a redundant visible heading");
            const accessible482=Ui.itemsWithProperty(notice,"readOnly").filter(receiver=>receiver.readOnly
                && receiver.visible && Ui.rendered(receiver) && receiver.text===error477
                && receiver.Accessible.role===Accessible.StaticText
                && receiver.Accessible.name==="Edi notice: "+error477);
            compare(accessible482.length,1,"GUI482: SAME unique notice owns ONE actual exposed accessible error text receiver");
            compare(accessible482[0].textFormat,TextEdit.PlainText,"GUI482: complete current Edi error remains literal native text");
            verify(accessible482[0].selectByMouse,"GUI482: actual Edi notice text remains natively selectable");
            compare(assistant.lastError,error477,"GUI477: observing original notice never clears or bypasses the error/fence");
        }
        const trials = Ui.itemsWithProperty(popup.contentItem,"text").filter(object =>
            object.assistant === assistant && object.text === "Refinement trial running · "+assistant.activeJobId);
        compare(trials.length,1,"GUI471: original Trial presentation remains uniquely owned even while inactive");
        verify(gui393_under(trials[0],list.footerItem),"GUI471: original Trial is in conversation flow");
        return list;
    }
    function gui471_activity(previous, callId) {
        const records = Probe.rows(assistant.messages).filter(row => !previous.has(row.id)
            && row.kind === "activity" && row.payload && row.payload.id === callId && row.payload.nativeOutcome);
        compare(records.length,1,"GUI471: actual successful original native call owns ONE canonical activity record");
        const canonical = records[0], payload = JSON.stringify(gui392_json(canonical.payload),null,2);
        compare(canonical.status,"completed","GUI471: actual successful inspect has truthful completed presentation");
        const list = item("assistant.messages"), index = Probe.rows(assistant.messages).findIndex(row => row.id === canonical.id);
        verify(index >= 0,"GUI471: canonical original activity has actual native ListView model index");
        list.positionViewAtIndex(index,ListView.Contain);rendered();
        const rows = Ui.itemsWithProperty(popup.contentItem,"rowId").filter(row => row.rowId === canonical.id && row.assistant === assistant
            && typeof row.resetDetails === "function" && typeof row.copyTechnicalPayload === "function");
        compare(rows.length,1,"GUI471: actual rendered original activity delegate is unique");
        const row = rows[0], life = lifetime313(row), owner = Session.project;
        compare(row.assistant,assistant,"GUI471: activity retains original controller");
        const toggles = Ui.itemsWithProperty(row,"objectName").filter(object =>
            object.objectName === "assistant.activity.toggle" || object.objectName === "assistant.command.toggle");
        compare(toggles.length,1,"GUI471: original activity has ONE main native disclosure");
        const toggle = toggles[0], copies = Ui.itemsWithProperty(row,"objectName").filter(object => object.objectName === "assistant.activity.copyTechnical");
        compare(copies.length,1,"GUI471: original activity has ONE canonical full-payload copy action");
        const copy = copies[0];
        Ui.scrollIntoView(toggle); rendered(); ux356_fullyExposed(toggle);
        const restPoint472 = Ui.clickPoint(toggle);
        verify(restPoint472 !== null,"GUI472: SAME original disclosure has real native header-hover destination outside copy");
        mouseMove(toggle,restPoint472.x,restPoint472.y);rendered();ux356_fullyExposed(copy);
        compare(toggle.checked,false,"GUI471: original activity starts folded");
        const tr = rect(toggle), cr = rect(copy);
        verify(cr[0] >= tr[0] && Math.abs(cr[1]+cr[3]/2-tr[1]-tr[3]/2) <= 0.5,
            "GUI471: full-payload Copy is on SAME activity HEADER before opening details");
        const glyphs = gui392_labels(toggle).filter(label => label.font.family === EaStyle.Fonts.iconsFamily);
        // Existing successful native-inspect outcome and original native icon vocabulary.
        compare(glyphs.length,2,"GUI471: main header has ONLY status/type icons, no extra disclosure arrow");
        const statuses = glyphs.filter(label => label.text === FitOutcomes.icon("success"));
        const categories = glyphs.filter(label => label.text === "info-circle" || label.text === "cog");
        compare(statuses.length,1,"GUI471: original successful activity exposes ONE truthful native status icon");
        compare(categories.length,1,"GUI471: original native activity exposes ONE type icon");
        verify(rect(statuses[0])[0]+statuses[0].width <= rect(categories[0])[0]+0.5,
            "GUI471: truthful STATUS icon precedes activity TYPE icon");
        const copyGlyphs = gui392_labels(copy.contentItem).filter(label =>
            label.font.family === EaStyle.Fonts.iconsFamily && label.text === "copy");
        compare(copyGlyphs.length,1,"GUI472: original copy content owns ONE actual painted native copy glyph");
        const copyGlyph = copyGlyphs[0], copyGlyphLife = lifetime313(copyGlyph);
        verify(gui393_under(copyGlyph,copy.contentItem),"GUI472: palette observation belongs to SAME actual native copy content");
        verify(!copy.hovered && !copy.down && !copy.pressed,
            "GUI472: real pointer relocation observes Copy at REST without forced interaction state");
        tryVerify(() => Qt.colorEqual(copyGlyph.color, EaStyle.Colors.themeForegroundMinor),2000,
            "GUI472: actual painted resting copy glyph uses original independent native MINOR palette");
        compare(String(copyGlyph.color),String(categories[0].color),
            "GUI472: painted resting Copy matches actual original muted type/gear icon");
        verify(alive313(copyGlyphLife),"GUI472: actual painted copy receiver remains alive at native input boundary");
        let clicks471 = 0;
        const copied471 = function(){++clicks471;};
        const copyLife471 = lifetime313(copy);
        try {
            copy.clicked.connect(copied471);
            status410Clipboard.text="";gui392_button(copy,popup);status410Clipboard.paste();
            compare(clicks471,1,"GUI471: SAME native header copy receiver receives exactly ONE original click");
        } finally { disconnect313(copyLife471,copy,"clicked",copied471); }
        compare(status410Clipboard.text,payload,"GUI471: genuine header Copy publishes ENTIRE original canonical payload exactly");
        gui392_button(toggle,popup);
        compare(toggle.checked,true,"GUI471: ONE native main disclosure opens original details directly");
        const nested = Ui.itemsWithProperty(row,"text").filter(control => typeof control.clicked === "function"
            && ["Technical details","Hide technical details"].includes(control.text));
        compare(nested.length,0,"GUI471: activity has NO secondary Technical details action, visible or hidden");
        const viewports = Ui.itemsWithProperty(row,"objectName").filter(object =>
            object.objectName === "assistant.activity.details" || object.objectName === "assistant.command.details");
        compare(viewports.length,1,"GUI471: direct unfold owns ONE public unified activity viewport");
        verify(viewports[0].visible,"GUI471: main disclosure directly shows unified details");
        const body = Ui.itemsWithProperty(viewports[0],"readOnly").filter(field => field.readOnly && field.text === payload);
        compare(body.length,1,"GUI471: direct unfold exposes ONE complete selectable canonical payload");
        ux356_fullyExposed(viewports[0]);
        Ui.scrollIntoView(body[0]);rendered();
        verify(body[0].visible && Ui.exposed(body[0]) && body[0].selectByMouse,
            "GUI471: complete original read-only text is selectable through its actual scrollable viewport");
        const boxes = Ui.itemsWithProperty(row,"radius").filter(box => box.visible && box.radius > 0
            && String(box.color) === String(EaStyle.Colors.contentBackground)
            && gui393_under(body[0],box));
        compare(boxes.length,1,"GUI471: entire unfolded payload belongs to ONE rounded native user-message surface");
        verify(Math.abs(boxes[0].width-row.width) <= AppSizes.unit+0.5,
            "GUI471: unfolded surface uses full available original sidebar row width");
        Ui.scrollIntoView(toggle);rendered();gui392_button(toggle,popup);
        compare(toggle.checked,false,"GUI471: SAME main disclosure closes original details without a second toggle");
        verify(alive313(life) && Session.project === owner && row.rowId === canonical.id,
            "GUI471: native disclosure/copy retain SAME original row, owner and identity");
        compare(JSON.stringify(gui392_json(row.payload)),JSON.stringify(gui392_json(canonical.payload)),
            "GUI471: header copy/disclosure cannot mutate canonical retained native result");
    }
    function gui471_workingFrame(control, variant, name) {
        verify(assistant.state === "agent_active" && assistant.canCancel,
            "GUI471 SETUP: presentation selection is allowed ONLY during independently reached real native activity");
        verify(control.working && control.visible && Ui.exposed(control),
            "GUI471: actual current shared Working receiver is visible and physically exposed");
        control.variant = variant; // Explicitly authorized PRESENTATION choice, never VM state/busy.
        rendered();
        compare(control.variant,variant,"GUI471: snapshot uses the declared original presentation variant");
        compare(control.text,"AI working...","GUI471: real busy uses original truthful native working text");
        const logos = Ui.itemsWithProperty(control,"source").filter(image =>
            image.sourceSize !== undefined && typeof image.fillMode === "number"
            && /Assistant(?:Working|Spinner)\.svg$/.test(String(image.source)));
        compare(logos.length,1,"GUI472: SAME shared native Working owns ONE original logo destination");
        const logo = logos[0], rotating = logo.parent, slot = rotating ? rotating.parent : null;
        verify(slot !== null && slot.parent === control && gui393_under(logo,slot),
            "GUI472: original fixed shared icon slot is physically owned by SAME Working control");
        verify(slot.width > 0 && slot.height > 0 && Math.abs(slot.width-slot.height) <= 0.5
            && Math.abs(logo.width-slot.width) <= 0.5 && Math.abs(logo.height-slot.height) <= 0.5
            && Math.abs(rotating.width-slot.width) <= 0.5 && Math.abs(rotating.height-slot.height) <= 0.5,
            "GUI472: actual fixed slot and original native logo destination have SAME positive square extent");
        const slotRect = slot.mapToItem(control,0,0,slot.width,slot.height);
        const slotBounds = [slotRect.x,slotRect.y,slotRect.width,slotRect.height];
        const robots = gui392_labels(control).filter(label => label.font.family === EaStyle.Fonts.iconsFamily && label.text === "robot");
        if (variant === 2) {
            compare(robots.length,1,"GUI471: actual robot frame has ONE visible original native glyph");
            gui470ActionInk.font=robots[0].font;gui470ActionInk.text="robot";
            const ink=gui470ActionInk.tightBoundingRect;
            const mapped=robots[0].mapToItem(control,ink.x,robots[0].baselineOffset+ink.y,ink.width,ink.height);
            verify(gui393_under(robots[0],rotating),"GUI472: actual robot and native logo share SAME rotating receiver and original fixed slot");
            verify(gui470_contains(slotBounds,[mapped.x,mapped.y,mapped.width,mapped.height]),
                "GUI472: ACTUAL rotated robot ink fits exact native shared icon SLOT, never text-gap/padded band");
            const textInk = control.mapToItem(window.contentItem,control.leftPadding,control.baselineOffset,0,0);
            gui470ActionInk.font=control.font;gui470ActionInk.text="H";
            const metrics=gui470ActionInk.tightBoundingRect;
            const actual=robots[0].mapToItem(window.contentItem,ink.x,robots[0].baselineOffset+ink.y,ink.width,ink.height);
            verify(Math.abs(actual.y+actual.height/2-(textInk.y+metrics.y+metrics.height/2)) <= 1,
                "GUI472: actual native robot ink center aligns with original app CAPITAL-H optical ink at actual Label baseline");
        }
        visible185_capture(name);
        console.info("GUI471_WORKING",JSON.stringify({name:name,variant:variant,state:assistant.state,
            canCancel:assistant.canCancel,receiver:String(control),owner:String(Session.project),bounds:rect(control),slot:slotBounds,logo:String(logo)}));
    }
    function test_ux289_hidden_activity_uses_real_original_request() {
        const project = Session.project;
        const values = visible185_values(project);
        toggle();
        gui392_signIn();
        report187_ready("ux289-working-bootstrap", false);
        const account = JSON.stringify(Probe.rows(assistant.models));
        const previous = new Set(Probe.rows(assistant.messages).map(row => row.id));
        Ui.click(this, Probe, window, "assistant.composer");
        visible185_type("Original two-tool activity retained across public observation");
        const needsApproval471 = assistant.contextConsentRequired;
        Ui.click(this, Probe, window, "assistant.send");
        if (needsApproval471) {
            const dialog = ux356_dialog();
            tryCompare(dialog,"opened",true,2000,"GUI471: original Send opens SAME owned consent dialog before ONE approval");
            gui470_standardAction(dialog.standardButton(Dialog.Ok),dialog,"approve-context");
        }
        tryVerify(() => visible185_outcome("ux289-working-first", previous) !== null
            && assistant.state === "agent_active" && assistant.canCancel, 10000,
            "UX289 SETUP: real first original native read completed while original objective is still active");
        const panelWorking = item("assistant.working"), status = item("statusBar.assistant.working");
        const theme471 = EaStyle.Colors.theme, panelVariant471 = panelWorking.variant, statusVariant471 = status.variant;
        try {
            EaStyle.Colors.theme = 0; // Finite owner-requested LIGHT render, restore below.
            const list471 = gui471_flow(panelWorking);
            Ui.scrollIntoView(panelWorking);rendered();
            gui471_workingFrame(panelWorking,2,"ux471-panel-robot-light");
            gui471_workingFrame(panelWorking,1,"ux471-panel-logo-light");
            gui471_activity(previous,"ux289-working-first");
            closeAssistant388(); // Genuine explicit user hide must retain precedence after terminal.
            tryCompare(status,"visible",true,2000,
                "UX289: hidden chat displays shared Working during real request gap, not synthetic busy");
            compare(panelWorking.visible,false,"UX289: covered panel and hidden-chat status do not duplicate painted activity");
            verify(Ui.exposed(status) && status.width>0 && status.height>0,
                "UX289: actual hidden-chat activity owns nonzero unobscured status geometry");
            gui471_workingFrame(status,2,"ux471-status-robot-light");
            gui471_workingFrame(status,1,"ux471-status-logo-light");
        } finally {
            panelWorking.variant=panelVariant471;status.variant=statusVariant471;EaStyle.Colors.theme=theme471;
        }
        assistant.refreshUsage();
        tryVerify(() => visible185_outcome("ux289-working-second", previous) !== null
            && Probe.rows(assistant.messages).some(row => !previous.has(row.id)
                && row.kind === "assistant" && row.status === "completed")
            && assistant.state === "idle" && !assistant.canCancel, 10000,
            "UX289: both original native replies and actual retained assistant completion settle before activity ends");
        tryCompare(status, "visible", false, 2000, "UX289: whole original completion retires genuine Working once");
        compare(Preferences.assistantShown, false, "UX289: explicit later hide survives original objective completion");
        compare(popup.visible, false, "UX289: terminal cannot reopen over the user's later explicit hide");
        compare(Session.project, project, "UX289: activity presentation keeps original project ownership");
        compare(visible185_values(project), values, "UX289: two read-only native tools preserve all actual scientific scalars/free/SU");
        compare(JSON.stringify(Probe.rows(assistant.models)), account,
            "UX289: activity presentation preserves genuine managed account/model admission");
    }
    function test_ux289_folder_caption_preserves_actual_grant() {
        const project = Session.project;
        const directory = Probe.scratchProjectUrl();
        const path = ApplicationInfo.localPath(directory);
        verify(path.length > 0, "UX289 SETUP: actual owned scratch directory has a physical filesystem path");
        toggle();
        assistant.signIn();
        report187_ready("ux289-folder-bootstrap", false);
        if (assistant.contextConsentRequired) assistant.signIn();
        report187_ready("ux289-folder-disclosed", true);
        const history = JSON.stringify(Probe.rows(assistant.messages));
        const account = JSON.stringify(Probe.rows(assistant.models));
        const intent = assistant.beginWorkingFolderSelection();
        verify(intent.length > 0 && assistant.completeWorkingFolderSelection(intent, directory),
            "UX289 SETUP: original real picker intent consumes its actual local directory callback");
        compare(assistant.workingFolder, path, "UX289: caption never replaces actual selected physical folder authority");
        const caption = item("assistant.workingFolder.caption");
        const show = item("assistant.showActions");
        const basename = path.replace(/\\/g, "/").split("/").filter(part => part.length).slice(-1)[0];
        compare(caption.text, basename, "UX289: actual compact caption spells the independent real folder basename");
        compare(caption.elide, Text.ElideMiddle, "UX289: long actual folder text uses middle elision");
        compare(caption.ToolTip.text, path, "UX289: full original physical scope remains available in tooltip");
        compare(caption.Accessible.name, path, "UX289: actual full original scope remains accessible");
        verify(Ui.exposed(caption) && Ui.exposed(show), "UX289: compact scope and mode control are actually exposed");
        const cr = rect(caption), sr = rect(show);
        verify(Math.abs((cr[1] + cr[3] / 2) - (sr[1] + sr[3] / 2)) <= Math.max(cr[3], sr[3]) / 2
            && cr[0] >= sr[0] + sr[2], "UX289: scope occupies the same row to the right without covering Show actions");
        const oldWidth = window.width;
        try {
            window.width = Math.max(window.minimumWidth, 800);
            rendered();
            verify(Ui.exposed(caption) && Ui.exposed(show),
                "UX289: actual narrow viewport preserves usable caption and mode-control hit areas");
            verify(rect(caption)[0] + caption.width <= window.contentItem.width,
                "UX289: actual scope caption cannot expand outside the narrow application viewport");
            compare(assistant.workingFolder, path, "UX289: layout changes cannot create or replace a grant");
            visible185_capture("ux289-folder-narrow");
        } finally { window.width = oldWidth; }
        verify(!assistant.completeWorkingFolderSelection(intent, directory),
            "UX289: consumed picker callback cannot acquire a second authority from caption presentation");
        Ui.click(this, Probe, window, "assistant.temporaryWorkingFolder");
        tryCompare(assistant, "workingFolder", "", 2000,
            "UX289: genuine existing temporary action restores actual app-owned temporary scope");
        compare(caption.text, "Temporary workspace", "UX289: temporary mode has an honest compact caption");
        compare(Session.project, project, "UX289: scope presentation and ordinary picker/temp controls preserve project owner");
        compare(JSON.stringify(Probe.rows(assistant.messages)), history, "UX289: scope presentation retains actual original history");
        compare(JSON.stringify(Probe.rows(assistant.models)), account, "UX289: picker/temp presentation retains original managed account");
    }

    function test_ux300_real_selection_notification_keeps_original_authority_data() {
        return ["add-refused-input", "remove-refused-input", "add-new-owner", "remove-new-owner",
            "add-nested-add", "remove-nested-add"]
            .map(tag => ({tag: tag}));
    }
    function test_ux300_real_selection_notification_keeps_original_authority(data) {
        const original = Session.project;
        const originalLifetime = lifetime313(original);
        const originalIdentity = identity313(originalLifetime);
        const selectedModel = assistant.selectedFiles;
        const selectedLifetime = lifetime313(selectedModel);
        verify(original !== null && !assistant.connected && !assistant.canCancel,
            "UX300 SETUP: actual ordinary project and signed-out idle selection are genuine");
        const source = "tests/fixtures/assistant/reference/PbSO4-Wyckoff.cif";
        const bytes = Probe.readFile(source);
        const beforeInputs = visible185_inputs(original);
        const beforeShape = relation246_shape(original);
        const beforeRelations = relation245_declarations(original);
        const beforeUndo = item("appBar.button.undo").enabled;
        compare(assistant.selectedFiles.count, 0, "UX300 SETUP: real fresh selected authority starts empty");
        const removal = data.tag.startsWith("remove-");
        const nested = data.tag.endsWith("nested-add");
        const laterSource = "tests/fixtures/assistant/reference/inst_d1a.prm";
        const laterBytes = nested ? Probe.readFile(laterSource) : null;
        let laterReference = null;
        if (nested) {
            // This separate ordinary admission establishes only the public format
            // label; basename/ASCII-byte count/readability come from the fixture.
            const referenceIntent = assistant.beginFileSelection();
            verify(referenceIntent.length > 0 && assistant.addSelectedFiles(referenceIntent,
                [Probe.repoUrl(laterSource)]), "UX334 SETUP: real independent ordinary later-file admission succeeds before callback setup");
            tryCompare(assistant.selectedFiles, "count", 1, 2000,
                "UX334 SETUP: independent ordinary admission settles before its descriptor reference");
            const referenceRows = Probe.rows(assistant.selectedFiles);
            compare(referenceRows.length, 1, "UX334 SETUP: ordinary reference has exactly the one independently supplied fixture");
            const referenceRow = referenceRows[0];
            verify(typeof referenceRow.id === "string" && referenceRow.id.length > 0,
                "UX334 SETUP: independent ordinary admission has an actual opaque app ID");
            compare(referenceRow.name, "inst_d1a.prm", "UX334: expected basename comes from the committed fixture path");
            compare(referenceRow.bytes, laterBytes.length,
                "UX334: committed ASCII fixture length independently specifies its exact UTF8 byte count");
            compare(referenceRow.textReadable, true, "UX334: actual complete ASCII fixture is independently readable UTF8 without NUL");
            compare(referenceRow.pending, true, "UX334: genuinely new ordinary source is unacknowledged");
            verify(typeof referenceRow.format === "string", "UX334 SETUP: ordinary reference supplies the unspecified public format label");
            laterReference = {name: "inst_d1a.prm", bytes: laterBytes.length,
                textReadable: true, format: referenceRow.format, pending: true};
            console.log("UX334_ORDINARY_REFERENCE", JSON.stringify({fixture: laterSource,
                descriptor: laterReference, referenceID: referenceRow.id}));
            verify(assistant.removeSelectedFile(referenceRow.id),
                "UX334 SETUP: genuine reference cleanup removes only its ordinary source authority");
            tryCompare(assistant.selectedFiles, "count", 0, 2000,
                "UX334 SETUP: ordinary reference is removed before original outer admission/removal");
        }
        let originalId = null;
        if (removal) {
            const initial = assistant.beginFileSelection();
            verify(initial.length > 0 && assistant.addSelectedFiles(initial, [Probe.repoUrl(source)]),
                "UX300 SETUP: normal public picker first admits the real removable source");
            compare(assistant.selectedFiles.count, 1, "UX300 SETUP: original source exists before removal observer");
            originalId = assistant.selectedFiles.text(0, "id");
        }
        let armed = true, outerReturned = false, observations = [], replacement = null;
        function notified() {
            if (!armed || assistant.selectedFiles.count !== (removal ? 0 : 1)) return;
            armed = false;
            const record = {beforeOuterReturn: !outerReturned, count: assistant.selectedFiles.count, enteringOwner: String(Session.project),
                enteringConnected: assistant.connected, enteringFiles: Probe.rows(assistant.selectedFiles)};
            observations.push(record);
            if (data.tag.endsWith("refused-input")) {
                record.refusedRow = assistant.submitDraft("   ");
                record.returningOwner = String(Session.project);
            } else if (data.tag.endsWith("nested-add")) {
                const nestedIntent = assistant.beginFileSelection();
                record.nestedIntent = nestedIntent;
                record.nestedAccepted = nestedIntent.length > 0 && assistant.addSelectedFiles(nestedIntent,
                    [Probe.repoUrl("tests/fixtures/assistant/reference/inst_d1a.prm")]);
                record.nestedRows = Probe.rows(assistant.selectedFiles);
            } else {
                Session.closeProject();
                record.created = Session.createProject("UX300 replacement", "Real owner from selected model notification");
                replacement = Session.project;
                record.returningOwner = String(replacement);
            }
            record.callbackActionReturned = true;
        }
        selectedModel.countChanged.connect(notified);
        let accepted;
        try {
            if (removal) accepted = assistant.removeSelectedFile(originalId);
            else {
                const intent = assistant.beginFileSelection();
                verify(intent.length > 0, "UX300 SETUP: genuine original file-selection intent is issued before admission");
                accepted = assistant.addSelectedFiles(intent, [Probe.repoUrl(source)]);
            }
            outerReturned = true;
            compare(observations.length, 1,
                "UX300 SETUP: exact genuine selected-model notification reached the original synchronous owner action");
            verify(observations[0].beforeOuterReturn && observations[0].callbackActionReturned,
                "UX332 SETUP: real model signal and original public action both return synchronously inside original Add/Remove");
            compare(observations[0].enteringOwner, originalIdentity,
                "UX300: notification belongs to the original actual displayed project");
            compare(observations[0].enteringConnected, false,
                "UX300: ordinary file authority never requires a fabricated authenticated provider");
            verify(accepted, "UX300: already admitted original selection/removal remains a truthful admitted fact");
            if (data.tag.endsWith("refused-input")) {
                compare(observations[0].refusedRow, "", "UX300: actual nested whitespace input is refused without a user authority");
                compare(Session.project, original, "UX300: same-owner refusal cannot strand original ordinary selection continuation");
                compare(assistant.selectedFiles.count, removal ? 0 : 1,
                    "UX300: actual offline Add/Remove publishes its complete requested canonical selection");
                if (!removal) {
                    const rows = Probe.rows(assistant.selectedFiles);
                    verify(rows[0].id.length > 0 && rows[0].name === "PbSO4-Wyckoff.cif" && rows[0].pending === true,
                        "UX300: ordinary original source has real canonical identity/name and remains unacknowledged");
                }
                compare(visible185_inputs(original), beforeInputs, "UX300: reentrant refusal leaves every original measured input unchanged");
                compare(relation246_shape(original), beforeShape, "UX300: ordinary admission leaves original structure/composition unchanged");
                compare(relation245_declarations(original), beforeRelations, "UX300: selection/refusal cannot rewrite scientific relations");
                compare(item("appBar.button.undo").enabled, beforeUndo, "UX300: selection/refusal adds no scientific Undo record");
            } else if (data.tag.endsWith("nested-add")) {
                verify(observations[0].nestedIntent.length > 0 && observations[0].nestedAccepted,
                    "UX303 SETUP: real same-owner model notification admits a distinct nested source through its genuine picker");
                compare(Session.project, original, "UX303: nested same-owner source publication preserves scientific owner");
                const expectedSurvivors = observations[0].enteringFiles;
                compare(expectedSurvivors.length, removal ? 0 : 1,
                    "UX334 SETUP: exact pre-nested projection identifies every original surviving source");
                const originalIDs = expectedSurvivors.map(row => row.id);
                compare(new Set(originalIDs).size, expectedSurvivors.length,
                    "UX334 SETUP: original pre-nested surviving IDs are unique before nested publication");
                if (!removal) verify(expectedSurvivors[0].id.length > 0
                    && expectedSurvivors[0].name === "PbSO4-Wyckoff.cif"
                    && expectedSurvivors[0].pending === true,
                    "UX334 SETUP: original surviving selection has its real pre-nested ID and remains unacknowledged");
                let rows = [], later = [];
                tryVerify(() => {
                    rows = Probe.rows(assistant.selectedFiles);
                    later = rows.filter(row => row.name === laterReference.name);
                    if (rows.length !== expectedSurvivors.length + 1 || later.length !== 1)
                        return false;
                    const row = later[0];
                    if (typeof row.id !== "string" || row.id.length === 0
                        || originalIDs.includes(row.id) || (removal && row.id === originalId))
                        return false;
                    for (const key of ["name", "bytes", "textReadable", "format", "pending"])
                        if (row[key] !== laterReference[key]) return false;
                    const survivors = rows.filter(value => value.id !== row.id);
                    return JSON.stringify(survivors) === JSON.stringify(expectedSurvivors)
                        && new Set(rows.map(value => value.id)).size === rows.length
                        && (!removal || !rows.some(value => value.id === originalId));
                }, 2000, "UX334: outer-return settlement preserves exact original descriptors/IDs and independently admitted later-file facts");
                compare(rows.length, removal ? 1 : 2,
                    "UX303: old publisher continuation cannot erase or resurrect canonical nested selected rows");
                compare(later.length, 1, "UX303: exact independently selected later source remains unique after old cleanup");
                verify(typeof later[0].id === "string" && later[0].id.length > 0
                    && later[0].pending === true && !originalIDs.includes(later[0].id),
                    "UX334: genuine nested source has a unique nonempty opaque ID distinct from every surviving original authority");
                for (const key of ["name", "bytes", "textReadable", "format", "pending"])
                    compare(later[0][key], laterReference[key],
                        "UX334: final later-file descriptor equals independent fixture/ordinary-reference facts");
                compare(JSON.stringify(rows.filter(row => row.id !== later[0].id)),
                    JSON.stringify(expectedSurvivors),
                    "UX334: final surviving original descriptors and IDs equal the pre-nested snapshot exactly");
                if (removal) verify(!rows.some(row => row.id === originalId),
                    "UX303: admitted original removal is never undone by nested source publication");
                compare(Probe.readFile(laterSource), laterBytes,
                    "UX334: ordinary reference and nested admission never rewrite the independent later-file bytes");
                compare(visible185_inputs(original), beforeInputs, "UX303: nested file publication leaves all original observations unchanged");
                compare(relation246_shape(original), beforeShape, "UX303: nested file publication leaves original composition unchanged");
                compare(relation245_declarations(original), beforeRelations, "UX303: nested file publication leaves all scientific relations unchanged");
                compare(item("appBar.button.undo").enabled, beforeUndo, "UX303: nested selection creates no scientific Undo step");
            } else {
                verify(observations[0].created && replacement !== null
                    && String(replacement) !== originalIdentity,
                    "UX300 SETUP: actual public callback really created a distinct replacement owner");
                compare(Session.project, replacement, "UX300: original selection continuation cannot recapture or replace B");
                compare(assistant.selectedFiles.count, 0, "UX300: A selection cannot publish old input authority into replacement B");
                compare(replacement.structures.count, 0, "UX300: old selection never creates stale structure in genuine empty B");
                compare(replacement.experiments.count, 0, "UX300: old selection never creates stale dataset in genuine empty B");
                compare(replacement.canUndo, false, "UX300: selection from A cannot create a hidden edit record in B");
            }
            compare(Probe.readFile(source), bytes, "UX300: actual model notification/reentry never rewrites original scientific file");
            compare(assistant.connected, false, "UX300: offline selection remains genuinely signed out");
            verify(!assistant.canCancel && !assistant.showingActions,
                "UX300: source selection/refused input cannot fabricate active work or visible execution");
            compare(Probe.rows(assistant.messages).filter(row => row.kind === "user").length, 0,
                "UX300: rejected nested draft and selection never fabricate a successfully admitted user request");
        } finally {
            disconnect313(selectedLifetime, selectedModel, "countChanged", notified);
            console.log("UX300_SELECTION", data.tag, JSON.stringify({observations: observations,
                accepted: accepted, originalOwner: originalIdentity, originalAlive: alive313(originalLifetime), currentOwner: String(Session.project),
                selected: Probe.rows(assistant.selectedFiles), connected: assistant.connected,
                canCancel: assistant.canCancel, showingActions: assistant.showingActions}));
        }
    }
    function test_ux300_real_signout_retires_despite_same_owner_notification_data() {
        return [{tag: "refused-input"}, {tag: "picker"}];
    }
    function test_ux300_real_signout_retires_despite_same_owner_notification(data) {
        const project = Session.project;
        const projectLifetime = lifetime313(project);
        const projectIdentity = identity313(projectLifetime);
        const assistantLifetime = lifetime313(assistant);
        const inputs = visible185_inputs(project), shape = relation246_shape(project);
        const relations = relation245_declarations(project);
        const undo = item("appBar.button.undo").enabled;
        const source = "tests/fixtures/assistant/reference/PbSO4-Wyckoff.cif";
        const sourceBytes = Probe.readFile(source), selectedIntent = assistant.beginFileSelection();
        verify(selectedIntent.length > 0 && assistant.addSelectedFiles(selectedIntent, [Probe.repoUrl(source)]),
            "UX303 SETUP: original source is genuinely admitted before account retirement");
        const originalSelected = JSON.stringify(Probe.rows(assistant.selectedFiles));
        toggle(); assistant.signIn(); report187_ready("ux300-signout-bootstrap", false);
        if (assistant.contextConsentRequired) assistant.signIn();
        report187_ready("ux300-signout-disclosed", true);
        verify(assistant.connected && !assistant.canCancel, "UX300 SETUP: real owned authenticated process is idle before logout");
        let armed = true, callerReturned = false, observations = [];
        function retired() {
            if (!armed) return;
            armed = false;
            const record = {beforeCallerReturn: !callerReturned, owner: String(Session.project), connectedAtEntry: assistant.connected,
                rowCount: assistant.messages.count};
            observations.push(record);
            if (data.tag === "refused-input") record.row = assistant.submitDraft("   ");
            else record.picker = assistant.beginFileSelection();
            record.ownerAfter = String(Session.project);
            record.callbackActionReturned = true;
        }
        assistant.conversationRetired.connect(retired);
        try {
            assistant.signOut();
            callerReturned = true;
            tryVerify(() => !assistant.connected && !assistant.canCancel && assistant.models.count === 0, 10000,
                "UX300: genuine explicit sign-out completes original account retirement despite same-owner nested presentation action");
            compare(observations.length, 1, "UX300 SETUP: real conversation retirement delivered original callback before caller completed");
            verify(observations[0].beforeCallerReturn && observations[0].callbackActionReturned,
                "UX332 SETUP: original public retirement signal really encloses the nested action before signOut returns");
            compare(observations[0].owner, projectIdentity, "UX300: logout notification belongs to original unchanged scientific owner");
            compare(observations[0].ownerAfter, projectIdentity, "UX300: nested refused input/picker cannot replace scientific owner");
            if (data.tag === "refused-input") compare(observations[0].row, "",
                "UX300: actual logout-interval empty input is refused without durable ACK");
            else {
                verify(typeof observations[0].picker === "string", "UX300: nested ordinary picker call returns its actual public intent result");
                if (observations[0].picker.length) assistant.cancelFileSelection(observations[0].picker);
            }
            compare(Session.project, project, "UX300: original logout leaves displayed project owner intact");
            compare(visible185_inputs(project), inputs, "UX300: genuine account retirement preserves all original measured inputs");
            compare(relation246_shape(project), shape, "UX300: logout/reentrant presentation preserves original structure/composition");
            compare(relation245_declarations(project), relations, "UX300: logout/reentrant presentation preserves scientific relations");
            compare(item("appBar.button.undo").enabled, undo, "UX300: logout/refusal creates no scientific Undo step");
            verify(!assistant.showingActions, "UX303: original logout cannot fabricate visible active work");
            compare(JSON.stringify(Probe.rows(assistant.selectedFiles)), originalSelected,
                "UX303: genuine account retirement preserves actual earlier admitted immutable file authority");
            compare(Probe.readFile(source), sourceBytes, "UX303: logout notification never rewrites admitted original source bytes");
            compare(Probe.rows(assistant.messages).filter(row => row.kind === "user").length, 0,
                "UX300: same-owner rejected input cannot survive as fabricated completed logout-interval Send");
        } finally {
            disconnect313(assistantLifetime, assistant, "conversationRetired", retired);
            console.log("UX300_SIGNOUT", data.tag, JSON.stringify({observations: observations,
                currentOwner: String(Session.project), connected: assistant.connected, state: assistant.state,
                canCancel: assistant.canCancel, showingActions: assistant.showingActions,
                modelCount: assistant.models.count, lastError: assistant.lastError}));
        }
    }

    function save349_science(project) {
        return JSON.stringify({values: JSON.parse(visible185_values(project)),
            inputs: JSON.parse(visible185_inputs(project)),
            declarations: JSON.parse(relation245_declarations(project)),
            sites: Probe.rows(project.currentStructure.atomSites).map(row => [row.label, row.typeSymbol,
                row.adpType, row.fractX.value, row.fractY.value, row.fractZ.value, row.occupancy.value]),
            results: Probe.rows(project.fit.results), outcome: project.fit.outcome,
            iterations: project.fit.iterations, goodnessOfFit: project.fit.goodnessOfFit});
    }
    function save380_preAdmissionRefusal(callId, previousIds, expectedArguments) {
        const rows = Probe.rows(assistant.messages).filter(row => !previousIds.has(row.id)
            && row.kind === "activity" && row.payload && row.payload.id === callId);
        verify(rows.length <= 1, "SAVE380: only one new original activity owns the exact refused call");
        if (!rows.length) return null;
        const row = rows[0], payload = row.payload;
        verify(typeof row.id === "string" && row.id.length > 0,
            "SAVE380: original refused activity has a genuine nonempty public identity");
        compare(payload.type, "dynamicToolCall", "SAVE380: original result is a real dynamic tool activity");
        compare(payload.tool, "save_project", "SAVE380: exact original Save tool owns the refusal");
        compare(payload.namespace, null, "SAVE380: original Save namespace is unchanged");
        verify(payload.arguments && typeof payload.arguments === "object",
            "SAVE380: original full Save arguments remain available");
        compare(Object.keys(payload.arguments).sort(), Object.keys(expectedArguments).sort(),
            "SAVE380: refused original arguments have exactly the independently requested fields");
        for (const key of Object.keys(expectedArguments))
            compare(payload.arguments[key], expectedArguments[key],
                "SAVE380: each refused original argument equals the independent requested operand");
        if (row.status !== "failed") return null;
        compare(payload.status, "failed", "SAVE380: original generic activity truthfully records failure");
        compare(payload.success, false, "SAVE380: original pre-admission result cannot claim success");
        verify(!Object.prototype.hasOwnProperty.call(payload, "nativeOutcome"),
            "SAVE380: pre-admission refusal does not fabricate an admitted native record");
        // Existing retained-public-JSON convention: QVariantList proxies are
        // JSON arrays without necessarily being native JavaScript Array objects.
        const contentItems384 = JSON.parse(JSON.stringify(payload.contentItems));
        verify(Array.isArray(contentItems384) && contentItems384.length === 1,
            "SAVE380: original refusal retains exactly one typed result item");
        const content = contentItems384[0];
        compare(content.type, "inputText", "SAVE380: original refused result uses the public text item type");
        verify(typeof content.text === "string", "SAVE380: original typed refusal contains actual JSON text");
        const result = JSON.parse(content.text);
        compare(Object.keys(result).sort(), ["message", "status"],
            "SAVE380: original validation refusal has the exact public result fields");
        compare(result.status, "refused", "SAVE380: no-grant Save explicitly refuses before admission");
        verify(typeof result.message === "string"
            && result.message.endsWith("[save_project:WORKING_OWNER/VALIDATION]"),
            "SAVE380: deliberate absent authority refuses at the exact expected validation phase");
        return {activityId: row.id, result: result};
    }
    function test_save349_visible_real_save_and_retirement_data() {
        return ["fresh", "current", "no-grant", "collision", "stop", "close-owner", "current-ten-refit"].map(tag => ({tag: tag}));
    }
    function test_save349_visible_real_save_and_retirement(data) {
        const leaf = "Original μ 🧪 saved project";
        verify(Session.openProject(Probe.referenceUrl("input")),
            "SAVE349 SETUP: actual independently owned complete native input opens");
        let project = Session.project;
        const parameters = visible185_parameters(project);
        const cell = parameters.filter(parameter => parameter.category === "cell" && parameter.name === "length_a");
        compare(cell.length, 1, "SAVE349 SETUP: independent original fit cell is unique");
        // Existing VA185 lawful fit-subset setup, never credited as visible editing/Save delivery.
        if (data.tag !== "current") {
            for (const parameter of parameters) parameter.free = false;
            cell[0].free = true;
            project.currentExperiment.scale.free = true;
        } else verify(parameters.filter(parameter => parameter.free).length > 2,
            "SAVE592 SETUP: original authentic CoSiO/d20 free flags retain a genuinely fuller fit than the two-parameter control");
        project.analysis.maxIterations = 8;
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment), 10000,
            "SAVE349 SETUP: actual complete native science is current before real fitting");
        const beforeFit = visible185_values(project), originalInputs = visible185_inputs(project);
        visible185_page("analysis");
        Ui.click(this, Probe, window, "sideBar.tab.basic");
        let fitStarts = 0, fitFinishes = 0;
        const fit = project.fit, fitLife = lifetime313(fit);
        function started() { if (alive313(fitLife) && fit.running) ++fitStarts; }
        function finished() { ++fitFinishes; }
        fit.runningChanged.connect(started);
        fit.finished.connect(finished);
        try {
            Ui.click(this, Probe, window, "fitting.start");
            tryVerify(() => fitFinishes === 1 && !fit.running && !project.calculating
                && Probe.computedCurrent(project.currentExperiment), 10000,
                "SAVE349 SETUP: genuine ordinary FitJob finishes and publishes actual current science");
            compare(fitStarts, 1, "SAVE349 SETUP: the real manual Fit button starts exactly one worker");
            verify(["success", "maxIterations"].includes(fit.outcome),
                "SAVE349 SETUP: actual fitted outcome is successful or bounded max-iterations, never stopped/failed");
            verify(visible185_values(project) !== beforeFit && Probe.rows(fit.results).length > 0,
                "SAVE349 SETUP: moving real fitted result, never no-step/cached/fabricated success");
            verify(visible185_parameters(project).some(parameter => parameter.free && parameter.hasUncertainty && parameter.uncertainty > 0),
                "SAVE349 SETUP: genuine fitted uncertainties exercise ordinary writer rounding");
            compare(visible185_inputs(project), originalInputs,
                "SAVE349: actual fit retains every measured coordinate/intensity/sigma/weight/exclusion/phase link");
        } finally {
            disconnect313(fitLife, fit, "runningChanged", started);
            disconnect313(fitLife, fit, "finished", finished);
        }
        // Ordinary public writer/readback is the independent pre-existing SU-rounding control.
        // Neither call is credited as delegated visible Save.
        verify(Session.saveAs(Probe.referenceUrl("ordinary")), "SAVE349 SETUP: ordinary fitted writer establishes reference tree");
        verify(Session.saveAs(Probe.referenceUrl("current")), "SAVE349 SETUP: separate genuinely owned current directory exists");
        verify(Session.openProject(Probe.referenceUrl("current")), "SAVE349 SETUP: normal reader establishes rounded current model");
        project = Session.project;
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment), 10000,
            "SAVE349 SETUP: ordinary real readback is current before Save admission");
        if (data.tag === "current-ten-refit") { save359_current_ten_refit(project); return; }
        const science = save349_science(project), owner = lifetime313(project);
        const correlations592 = data.tag === "current" ? JSON.stringify({available: project.correlations.available,
            labels: Array.from(project.correlations.labels), values: Array.from(project.correlations.values)}) : null;
        if (data.tag === "current") {
            verify(project.correlations.available > 2,
                "SAVE592 SETUP: genuine fitted/rounded current owner retains a higher-dimensional actual correlation shape");
            console.log("SAVE592_SHAPE", JSON.stringify({parameters: visible185_parameters(project).length,
                free: visible185_parameters(project).filter(parameter => parameter.free).length,
                correlationAvailable: project.correlations.available,
                shown: project.correlations.labels.length, values: project.correlations.values.length}));
        }
        const currentPath = project.path;
        const saveDirectoryLife603 = data.tag === "current" ? lifetime313(Session) : null;
        let saveDirectoryCount603 = 0, saveDirectoryPath603 = null;
        function currentDirectoryUsed603(path) {
            ++saveDirectoryCount603;
            if (saveDirectoryCount603 === 1) saveDirectoryPath603 = String(path);
        }
        const sourceDocuments = ["project.edi", "structures/cosio.edi", "experiments/d20.edi", "analysis/analysis.edi"];
        const currentBytes = sourceDocuments.map(name => Probe.readReferenceFile("current/" + name));
        visible185_page("project");
        Ui.click(this, Probe, window, "mainArea.project.tab.description");
        if (data.tag === "current") {
            Ui.click(this, Probe, window, "project.title");
            visible185_type("Original manual current Save control");
            keyClick(Qt.Key_Return);
            verify(project.modified && !Session.needsSaveAs,
                "SAVE592 CONTROL: real title edit dirties the SAME owned current project before ordinary toolbar Save");
            const manualSave592 = Ui.control(Probe, window, "appBar.button.save");
            verify(manualSave592 !== null && manualSave592.enabled && Ui.exposed(manualSave592),
                "SAVE592 CONTROL: genuine ordinary current toolbar Save is exposed and enabled");
            const manualLife592 = lifetime313(manualSave592);
            let manualClicks592 = 0;
            function manualSaved592() { ++manualClicks592; }
            manualSave592.clicked.connect(manualSaved592);
            const manualUndo592 = item("appBar.button.undo").enabled;
            let manualDirectoryConnected603 = false;
            try {
                Session.projectDirectoryUsed.connect(currentDirectoryUsed603); manualDirectoryConnected603 = true;
                Ui.click(this, Probe, window, "appBar.button.save");
                compare(manualClicks592, 1, "SAVE592 CONTROL: exactly ONE genuine manual toolbar Save click");
                compare(saveDirectoryCount603, 1,
                    "SAVE603 CONTROL: manual Save has exactly one actual ordinary Session completion");
                compare(saveDirectoryPath603, currentPath,
                    "SAVE603 CONTROL: actual ordinary manual completion names the SAME owned directory");
                tryCompare(project, "modified", false, 2000,
                    "SAVE592 CONTROL: ordinary Save actually persists the current dirty project");
                compare(Session.project, project, "SAVE592 CONTROL: manual writer preserves exact owner");
                compare(project.path, currentPath, "SAVE592 CONTROL: manual current Save never changes the owned directory");
                verify(!Session.needsSaveAs, "SAVE592 CONTROL: manual current Save needs no chooser");
                compare(save349_science(project), science, "SAVE592 CONTROL: manual Save preserves every rounded scientific fact");
                compare(item("appBar.button.undo").enabled, manualUndo592,
                    "SAVE592 CONTROL: ordinary Save neither consumes nor invents history");
            } finally {
                if (manualDirectoryConnected603)
                    disconnect313(saveDirectoryLife603, Session, "projectDirectoryUsed", currentDirectoryUsed603);
                disconnect313(manualLife592, manualSave592, "clicked", manualSaved592);
            }
        }
        Ui.click(this, Probe, window, "project.title");
        visible185_type("Original visible Save " + data.tag);
        keyClick(Qt.Key_Return);
        compare(project.title, "Original visible Save " + data.tag, "SAVE349 SETUP: genuine user title edit makes current model dirty");
        verify(project.modified && !Session.needsSaveAs,
            "SAVE349 SETUP: ordinary current Save is eligible for the real fitted owned project");
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment), 10000,
            "SAVE349 SETUP: genuine title commit is settled before native Save admission");
        compare(save349_science(project), science, "SAVE349 SETUP: title edit changes no fitted scientific fact");
        const metadata = JSON.parse(import265_owner(project));
        delete metadata.path;
        const undoBefore = item("appBar.button.undo").enabled;
        toggle();
        assistant.signIn();
        visible185_ready("save349-bootstrap");
        if (assistant.contextConsentRequired) assistant.signIn();
        visible185_ready("save349-disclosed");
        if (!["no-grant", "current"].includes(data.tag)) {
            const intent = assistant.beginWorkingFolderSelection();
            verify(intent.length > 0 && assistant.completeWorkingFolderSelection(intent, Probe.referenceUrl("selected")),
                "SAVE349 SETUP: real original picker intent grants exactly the owned parent");
            compare(assistant.workingFolder, ApplicationInfo.localPath(Probe.referenceUrl("selected")),
                "SAVE349 SETUP: native grant is the independently selected physical parent");
            if (assistant.contextConsentRequired) assistant.signIn();
            visible185_ready("save349-folder-disclosed");
        } else if (data.tag === "current") {
            compare(Session.project, project,
                "SAVE599 SETUP: actual current owner survives account/context admission without a folder-grant API");
            compare(project.path, currentPath,
                "SAVE599 SETUP: current Save authority remains the SAME independently owned physical directory");
            verify(!Session.needsSaveAs,
                "SAVE599 SETUP: actual owned-current Save needs no fresh-parent selection or grant");
        } else compare(assistant.workingFolder, "", "SAVE349 SETUP: current/no-grant cases have no unrelated fresh-parent grant");
        const show = item("assistant.showActions");
        verify(show.enabled && show.visible, "SAVE349 SETUP: actual Show actions control is actionable");
        if (data.tag === "current") compare(assistant.showActions, false,
            "SAVE592 SETUP: owner-equivalent ordinary current Save uses actual Show actions OFF");
        else {
            mouseClick(show);
            verify(assistant.showActions, "SAVE349 SETUP: real checkbox admits visible mode");
        }
        const account = JSON.stringify(Probe.rows(assistant.models));
        const beforeIds = new Set(Probe.rows(assistant.messages).map(row => row.id));
        const save = Ui.control(Probe, window, "appBar.button.save");
        verify(save !== null && save.enabled && Ui.exposed(save), "SAVE349 SETUP: genuine ordinary Save button is physically enabled");
        let saveClicks = 0, finalClicks = 0, typed = 0, finalName = null;
        let editor = null, finalSave = null, editorLife = null, finalLife = null;
        let originalDialog = null, dialogLife = null, originalFooter = null, openedEvents = 0;
        const saveLife370 = lifetime313(save);
        const connected370 = {save: false, text: false, press: false, click: false, opened: false, directory603: false};
        function savedClicked() { ++saveClicks; }
        function finalPressed() {
            verify(alive313(dialogLife) && alive313(editorLife) && alive313(finalLife),
                "SAVE352: original dialog/editor/footer receiver remain alive at real final press");
            if (!finalSave.pressed) return; // pressedChanged also notifies release; only the true edge is precommit.
            verify(originalDialog.opened && originalDialog.visible && finalSave.enabled
                && Ui.rendered(finalSave) && Ui.exposed(finalSave),
                "SAVE352: genuine final Save is physically exposed in its actual opened original form");
            let parent = finalSave;
            while (parent && parent !== originalFooter) parent = parent.parent;
            compare(parent, originalFooter, "SAVE352: pressed Save belongs to the exact original Dialog.footer");
            let windowParent = finalSave;
            while (windowParent && windowParent !== Ui.windowRoot(window)) windowParent = windowParent.parent;
            compare(windowParent, Ui.windowRoot(window), "SAVE352: final receiver belongs to the original physical window");
            const point = Ui.clickPoint(finalSave);
            verify(point !== null, "SAVE352: actual footer button has an unclipped click point");
            const position = finalSave.mapToItem(window.contentItem, point.x, point.y);
            verify(position.x >= 0 && position.y >= 0 && position.x < window.contentItem.width
                && position.y < window.contentItem.height, "SAVE352: original final press lies inside the actual window");
            finalName = editor.text;
        }
        function openedChanged() {
            if (alive313(dialogLife) && originalDialog.opened) ++openedEvents;
        }
        function finalClicked() { ++finalClicks; }
        function textEdited() { ++typed; }
        const call = "save349-" + data.tag;
        const observation = visible237_observationMs([{path: "", text: leaf}]);
        try {
            if (data.tag === "current") {
                saveDirectoryCount603 = 0; saveDirectoryPath603 = null;
                Session.projectDirectoryUsed.connect(currentDirectoryUsed603); connected370.directory603 = true;
            }
            save.clicked.connect(savedClicked); connected370.save = true;
            if (["fresh", "collision", "stop", "close-owner", "current"].includes(data.tag)) {
                // Passive original receiver binding, including collision. A closed
                // form need not be rendered/exposed and no open interval is forced.
                const forms = Probe.objectsWithProperty(window, "opened").filter(object =>
                    object.objectName === "assistant.resultSaveAs");
                compare(forms.length, 1, "SAVE352 SETUP: exact original window owns one Save dialog receiver");
                originalDialog = forms[0]; dialogLife = lifetime313(originalDialog);
                const content = originalDialog.contentItem;
                originalFooter = originalDialog.footer;
                verify(content !== null && originalFooter !== null,
                    "SAVE352 SETUP: original dialog has its distinct content and footer owners");
                const names = Ui.itemsWithProperty(content, "objectName").filter(object =>
                    object.objectName === "assistant.resultFolderName");
                const buttons = Ui.itemsWithProperty(originalFooter, "objectName").filter(object =>
                    object.objectName === "assistant.resultFolderSave");
                compare(names.length, 1, "SAVE352 SETUP: exact content owns one original name editor");
                compare(buttons.length, 1, "SAVE352 SETUP: exact footer owns one original final Save receiver");
                editor = names[0]; finalSave = buttons[0];
                editorLife = lifetime313(editor); finalLife = lifetime313(finalSave);
                verify(typeof finalSave.pressed === "boolean" && typeof finalSave.pressedChanged === "function",
                    "SAVE370 SETUP: actual original Qt Button exposes pressed STATE and its pressedChanged SIGNAL");
                editor.textEdited.connect(textEdited); connected370.text = true;
                finalSave.pressedChanged.connect(finalPressed); connected370.press = true;
                finalSave.clicked.connect(finalClicked); connected370.click = true;
                originalDialog.openedChanged.connect(openedChanged); connected370.opened = true;
                console.log("SAVE352_ORIGINAL_RECEIVERS", JSON.stringify({case: data.tag,
                    dialog: identity313(dialogLife), editor: identity313(editorLife),
                    finalSave: identity313(finalLife), originallyOpened: originalDialog.opened}));
            }
            assistant.send("Save this actual fitted displayed project using original visible Save " + data.tag);
            if (!["current", "no-grant", "collision"].includes(data.tag)) {
                tryVerify(() => {
                    if (!alive313(dialogLife) || !alive313(editorLife) || !alive313(finalLife)
                        || !originalDialog.opened || !originalDialog.visible) return false;
                    const forms = Probe.objectsWithProperty(window, "opened").filter(object =>
                        object.objectName === "assistant.resultSaveAs");
                    compare(forms.length, 1, "SAVE352: no second dialog can replace the original Save receiver");
                    compare(forms[0], originalDialog, "SAVE352: actual opened form is the bound original dialog");
                    let ancestor = editor;
                    while (ancestor && ancestor !== Ui.windowRoot(window)) ancestor = ancestor.parent;
                    if (ancestor !== Ui.windowRoot(window)) return false;
                    return saveClicks === 1 && assistant.showingActions && assistant.canCancel
                        && editor.visible && Ui.rendered(editor) && Ui.exposed(editor)
                        && typed > 0 && editor.text.length > 0 && editor.text !== leaf;
                }, observation, "SAVE349 INTERVAL: real Save opens its unique form and genuine partial original name typing is reached");
                console.log("SAVE349_PARTIAL", JSON.stringify({case: data.tag, saveClicks: saveClicks,
                    typed: typed, text: editor.text, finalClicks: finalClicks, currentOwner: Session.project === project}));
                const pending575=originalDialog.intent;
                verify(typeof pending575==="string" && pending575.length>0
                    && originalDialog.presentedIntent===pending575 && Session.saveAsCurrent(pending575),
                    "HUMAN575 MAIN: reached original fresh Save form owns the SAME current real Session SaveAs intent");
                verify(Session.assistantSaveReady && Session.assistantSaveAs && Session.project===project
                    && assistant.connected && JSON.stringify(Probe.rows(assistant.models))===account,
                    "HUMAN575 MAIN: actual pending fresh Save retains real owner/account authority before original completion or Stop");
                console.log("HUMAN575_MAIN_PENDING",JSON.stringify({originalIntent:true,ownerCurrent:true,
                    connected:assistant.connected,canCancel:assistant.canCancel,dialogAlive:alive313(dialogLife),
                    editorAlive:alive313(editorLife),finalClicks:finalClicks}));
                if (data.tag === "stop") {
                    const stop = item("assistant.stopVisibleAction");
                    verify(stop.enabled && Ui.exposed(stop), "SAVE349 STOP: genuine original Stop is exposed in reached interval");
                    mouseClick(stop);
                } else if (data.tag === "close-owner") Session.closeProject();
            }
            const refused = ["no-grant", "collision", "stop", "close-owner"].includes(data.tag);
            const expectedArguments380 = {purpose: "Save original fitted displayed project through actual visible controls",
                destination: "fresh", name: leaf};
            let preAdmission380 = null;
            tryVerify(() => !assistant.canCancel && !assistant.showingActions
                && (data.tag === "close-owner" ? Session.project === null : data.tag === "no-grant"
                    ? (preAdmission380 = save380_preAdmissionRefusal(call, beforeIds, expectedArguments380)) !== null
                    : visible185_outcome(call, beforeIds) !== null),
                observation, "SAVE349: original whole request settles without a fabricated native receipt");
            const originalRefusal380 = data.tag === "no-grant"
                ? save380_preAdmissionRefusal(call, beforeIds, expectedArguments380) : null;
            if (data.tag === "no-grant") verify(originalRefusal380 !== null,
                "SAVE380: settled no-grant requires its original typed refusal, never an admitted fallback");
            if (originalRefusal380 !== null) compare(originalRefusal380.activityId, preAdmission380.activityId,
                "SAVE380: the same original refused public activity survives whole-turn settlement");
            const outcome = originalRefusal380 !== null ? originalRefusal380.result : visible185_outcome(call, beforeIds);
            if (!refused) verify(alive313(owner) && Session.project === project,
                "SAVE352: successful Save keeps the exact original live displayed owner before any inspection");
            console.log("SAVE349_TERMINAL", JSON.stringify({case: data.tag, outcome: outcome,
                saveClicks: saveClicks, finalClicks: finalClicks, typed: typed,
                originalReceiversBound: dialogLife !== null, openedEvents: openedEvents,
                originalDialogAlive: alive313(dialogLife),
                currentPath: Session.project ? Session.project.path : null,
                modified: Session.project ? Session.project.modified : null,
                connected: assistant.connected, originalOwnerAlive: alive313(owner)}));
            if (refused) {
                if (data.tag !== "close-owner") verify(outcome !== null && outcome.status !== "succeeded" && outcome.committed !== true,
                    "SAVE349: precommit refusal/cancel truthfully denies disk commit");
                if (data.tag !== "collision") compare(finalClicks, 0,
                    "SAVE349: missing authority/retired original helper cannot click final Save later");
                if (data.tag === "no-grant") compare(saveClicks, 0,
                    "SAVE352: absent parent authority refuses before ordinary Save action");
                // Collision is always a negative no-write result, with factual
                // bound control receipts; no earlier/later discovery point is invented.
                for (let index = 0; index < sourceDocuments.length; ++index)
                    compare(Probe.readReferenceFile("current/" + sourceDocuments[index]), currentBytes[index],
                        "SAVE349: refusal/retirement preserves existing native document bytes");
                if (data.tag !== "close-owner") {
                    compare(Session.project, project, "SAVE349: refused Save retains original displayed owner");
                    compare(save349_science(project), science, "SAVE349: refused Save retains complete fitted science");
                    compare(project.path, currentPath, "SAVE349: refused Save cannot change owned path");
                    verify(project.modified, "SAVE349: refused Save cannot falsely clear actual dirty state");
                }
            } else {
                verify(outcome !== null && outcome.status === "succeeded" && outcome.committed === true
                    && outcome.reopened === (data.tag === "fresh") && outcome.active === true
                    && typeof outcome.presentation_complete === "boolean"
                    && (data.tag !== "fresh" || outcome.presentation_complete === true),
                    "SAVE603: actual commit/current owner and truthful presentation flag; current ordinary Save never invents a reopen");
                compare(saveClicks, data.tag === "current" ? 0 : 1,
                    "SAVE592: one native OFF Save or one real visible toolbar Save owns the original RPC, never both");
                if (data.tag === "current") {
                    compare(saveDirectoryCount603, 1,
                        "SAVE603: one assistant request has exactly one actual ordinary Session completion");
                    compare(saveDirectoryPath603, currentPath,
                        "SAVE603: assistant ordinary completion names the SAME independently owned directory");
                    compare(openedEvents, 0, "SAVE592: owned omitted-destination Save never opens a chooser");
                    verify(alive313(dialogLife) && !originalDialog.opened,
                        "SAVE592: the SAME actual closed Save form remains unopened");
                    compare(JSON.stringify({available: project.correlations.available,
                        labels: Array.from(project.correlations.labels), values: Array.from(project.correlations.values)}), correlations592,
                        "SAVE592: ordinary current Save retains complete current rounded correlation presentation/shape");
                }
                compare(finalClicks, data.tag === "current" ? 0 : 1,
                    "SAVE349: fresh confirms once through real final Save; current has no invented name form");
                if (data.tag === "fresh") {
                    verify(typed > 0, "SAVE349: literal fresh Unicode/spaces name was genuinely typed");
                    compare(finalName, leaf, "SAVE349: real final Save receives the exact spaces/BMP/non-BMP spelling");
                }
                verify(alive313(owner) && Session.project === project && !project.modified, "SAVE349: actual displayed saved owner is unmodified");
                compare(project.path, data.tag === "current" ? currentPath
                    : ApplicationInfo.localPath(Probe.referenceUrl("selected/" + leaf)), "SAVE349: active directory is exactly the authorized destination");
                compare(outcome.destination, project.path, "SAVE349: original outcome tells the exact active saved path");
                tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment), 10000,
                    "SAVE349: actual saved/reopened scientific model is current");
                compare(save349_science(project), science, "SAVE349: actual visible Save preserves rounded fitted science and declarations");
                const afterMetadata = JSON.parse(import265_owner(project)); delete afterMetadata.path;
                compare(JSON.stringify(afterMetadata), JSON.stringify(metadata), "SAVE349: every displayed metadata/settings fact survives actual save/reopen");
                verify(!Session.needsSaveAs, "SAVE349: real adopted saved directory no longer needs Save As");
                if (data.tag === "fresh") {
                    for (let index = 0; index < sourceDocuments.length; ++index)
                        compare(Probe.readReferenceFile("current/" + sourceDocuments[index]), currentBytes[index],
                            "SAVE349: fresh-child Save cannot also overwrite the previously owned current native input");
                }
            }
            if (data.tag !== "close-owner") compare(item("appBar.button.undo").enabled, undoBefore,
                "SAVE349: Save/refusal does not manufacture or consume an ordinary Undo step");
            verify(assistant.connected, "SAVE349: save/cancel/retirement preserves genuine managed account");
            compare(JSON.stringify(Probe.rows(assistant.models)), account, "SAVE349: original account/model catalog is unchanged");
        } finally {
            if (connected370.directory603)
                disconnect313(saveDirectoryLife603, Session, "projectDirectoryUsed", currentDirectoryUsed603);
            if (connected370.save) disconnect313(saveLife370, save, "clicked", savedClicked);
            if (connected370.opened) disconnect313(dialogLife, originalDialog, "openedChanged", openedChanged);
            if (connected370.text) disconnect313(editorLife, editor, "textEdited", textEdited);
            if (connected370.press) disconnect313(finalLife, finalSave, "pressedChanged", finalPressed);
            if (connected370.click) disconnect313(finalLife, finalSave, "clicked", finalClicked);
        }
    }
    function ux358_acknowledgedPresentation(composer, files) {
        const selected = Probe.rows(assistant.selectedFiles);
        compare(JSON.stringify(selected.map(file => ({id: file.id, name: file.name, bytes: file.bytes,
            textReadable: file.textReadable, format: file.format}))), JSON.stringify(files),
            "UX358: completed original ACK preserves exact canonical source descriptors and order");
        for (const file of files) {
            const matches = selected.filter(row => row.id === file.id);
            compare(matches.length, 1, "UX358: each acknowledged original source retains one exact canonical authority row");
            compare(matches[0].pending, false,
                "UX358: matching completed ACK consumes this original source's pending presentation role");
            const chips = Ui.itemsWithProperty(composer, "objectName").filter(control =>
                control.objectName === "assistant.file." + file.id);
            verify(chips.length <= 1 && chips.every(chip => !chip.visible),
                "UX358: each acknowledged original chip is absent or hidden in its exact original composer subtree");
        }
    }
    function ux356_fullyExposed(control) {
        verify(control !== null && control.visible && control.width > 0 && control.height > 0,
            "UX356: original visible control has real positive layout geometry");
        let inWindow = false;
        for (let parent = control.parent; parent; parent = parent.parent) {
            inWindow = inWindow || parent === Ui.windowRoot(window);
            if (parent.clip) {
                const bounds = control.mapToItem(parent, 0, 0, control.width, control.height);
                verify(bounds.x >= -0.5 && bounds.y >= -0.5
                    && bounds.x + bounds.width <= parent.width + 0.5
                    && bounds.y + bounds.height <= parent.height + 0.5,
                    "UX356: complete original primary text/control is inside every actual clipping viewport");
            }
        }
        verify(inWindow && Ui.rendered(control) && Ui.exposed(control),
            "UX356: original control belongs to the genuine visible Main window");
        const bounds = control.mapToItem(window.contentItem, 0, 0, control.width, control.height);
        verify(bounds.x >= -0.5 && bounds.y >= -0.5
            && bounds.x + bounds.width <= window.contentItem.width + 0.5
            && bounds.y + bounds.height <= window.contentItem.height + 0.5,
            "UX356: original primary control/text fits the unchanged normal window viewport");
    }
    function ux356_dialog() {
        const candidates = Probe.objectsWithProperty(window, "disclosedContext").filter(object =>
            object.assistant === assistant);
        compare(candidates.length, 1, "UX356: one exact original assistant owns the existing disclosure/sign-in dialog");
        return candidates[0];
    }
    function ux356_dialogControl(dialog, name) {
        const found = Ui.itemsWithProperty(dialog.contentItem, "objectName").filter(control =>
            control.objectName === name);
        compare(found.length, 1, "UX356: exact original dialog owns one " + name);
        return found[0];
    }
    function ux356_compactDialog(dialog) {
        verify(dialog.opened && dialog.visible, "UX356: actual original consent/sign-in dialog is open");
        const details = ux356_dialogControl(dialog, "assistant.contextDetailsToggle");
        const preview = ux356_dialogControl(dialog, "assistant.contextPreview");
        compare(details.checked, false, "UX356: exact technical payload is collapsed in the primary flow");
        verify(!preview.visible, "UX356: exact technical JSON is not primary dialog prose");
        const primary = Ui.itemsWithProperty(dialog.contentItem, "text").filter(control =>
            control.visible && typeof control.text === "string" && control.text.length > 0);
        verify(primary.length > 0, "UX356: compact primary flow still presents actual human-readable scope/account information");
        for (const control of primary) ux356_fullyExposed(control);
        verify(/ChatGPT|OpenAI/.test(dialog.title) || primary.some(control => /ChatGPT|OpenAI/.test(control.text)),
            "UX356: compact primary presentation still identifies the real provider/account route");
        const ok = dialog.standardButton(Dialog.Ok), cancel = dialog.standardButton(Dialog.Cancel);
        verify(ok !== null && cancel !== null && ok.enabled && cancel.enabled,
            "UX356: original standard consent/sign-in actions remain genuinely available");
        ux356_fullyExposed(ok); ux356_fullyExposed(cancel); ux356_fullyExposed(details);
        const actual = assistant.contextPreview;
        compare(JSON.stringify(dialog.disclosedContext), JSON.stringify(JSON.parse(actual)),
            "UX356: collapsed primary dialog still owns the exact actual current disclosure");
        mouseClick(details, Ui.clickPoint(details).x, Ui.clickPoint(details).y);
        tryCompare(details, "checked", true, 2000, "UX356: real detail control opens exact payload on demand");
        verify(preview.visible && preview.readOnly, "UX356: actual original technical payload is accessible as read-only text");
        compare(preview.text, actual, "UX356: on-demand technical text is byte-exact actual outgoing context, not a summary/golden");
        // Expanded details may legitimately scroll. Close through the same live
        // original control before measuring/using the compact primary actions.
        Ui.scrollIntoView(details); rendered();
        verify(details.enabled && Ui.exposed(details), "UX356: original expanded-details control remains physically reachable");
        mouseClick(details, Ui.clickPoint(details).x, Ui.clickPoint(details).y);
        tryCompare(details, "checked", false, 2000, "UX356: genuine detail close restores compact primary flow");
        rendered(); ux356_fullyExposed(ok); ux356_fullyExposed(cancel);
    }
    function ux356_chip(root, file, sent) {
        const name = (sent ? "assistant.sentFile." : "assistant.file.") + file.id;
        const chips = Ui.itemsWithProperty(root, "objectName").filter(control => control.objectName === name);
        compare(chips.length, 1, "UX356: exact original composer/user row owns one canonical attachment chip");
        const chip = chips[0];
        Ui.scrollIntoView(chip); rendered(); ux356_fullyExposed(chip);
        const labels = Ui.itemsWithProperty(chip, "text").filter(control => control.visible
            && typeof control.text === "string" && control.text.includes(file.name));
        compare(labels.length, 1, "UX356: original chip has one actual complete filename/size label");
        const label = labels[0];
        ux356_fullyExposed(label);
        verify(label.truncated === false && label.contentHeight <= label.height + 0.5,
            "UX356: short message cannot collapse ordinary filename/size to ellipses or vertically crop it");
        verify(/[0-9]/.test(label.text) && /bytes|[KMGT]i?B|[kmgt]B/.test(label.text),
            "UX356: readable ordinary filename retains its actual size presentation");
        verify(label.Accessible.name.includes(file.name) && label.Accessible.name.includes(String(file.bytes)),
            "UX356: accessibility retains the complete original filename and exact admitted byte count");
        const buttons = Ui.itemsWithProperty(chip, "enabled").filter(control =>
            gui472_actionCapable(control) && control.Accessible.name.includes(file.name));
        if (sent) {
            gui471_sentSnapshot(root, file.id);
            compare(buttons.length, 0, "UX471: historical snapshot has NO named remove action");
            return {chip: chip};
        }
        compare(buttons.length, 1, "UX356: original PENDING chip owns one actual named remove action");
        ux356_fullyExposed(buttons[0]);
        return {chip: chip, remove: buttons[0]};
    }
    function test_ux356_real_send_compact_scope_and_short_files_data() {
        return ["send-click", "send-keyboard", "cancel-new-draft"].map(tag => ({tag: tag}));
    }
    function test_ux356_real_send_compact_scope_and_short_files(data) {
        verify(Session.openProject(Probe.referenceUrl("project")),
            "UX356 SETUP: lawful owned default-table scientific input opens through real Session");
        const project = Session.project, owner = lifetime313(project);
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment), 10000,
            "UX356 SETUP: original real scientific calculation is actually current");
        const science = save349_science(project), undo = project.canUndo;
        const metadata = import265_owner(project), modified = project.modified;
        compare(Probe.rows(assistant.messages).length, 0,
            "UX356 SETUP: actual unique Qt test-mode storage starts without unrelated prior user history");
        toggle();
        Ui.click(this, Probe, window, "assistant.connection");
        const dialog = ux356_dialog(), dialogLife = lifetime313(dialog);
        tryCompare(dialog, "opened", true, 2000, "UX356: genuine connection control opens original sign-in dialog");
        ux356_compactDialog(dialog);
        const signIn = dialog.standardButton(Dialog.Ok);
        mouseClick(signIn, Ui.clickPoint(signIn).x, Ui.clickPoint(signIn).y);
        report187_ready("ux356-real-signin", false);
        verify(!dialog.visible, "UX356: original sign-in acceptance closes its actual modal before composer input");
        const account = JSON.stringify(Probe.rows(assistant.models));
        const token = assistant.beginFileSelection();
        verify(token.length > 0 && assistant.addSelectedFiles(token, [
            Probe.referenceUrl("files/Original structure.cif"), Probe.referenceUrl("files/Original measured neutron profile.xye")]),
            "UX356 SETUP: existing genuine selection door admits the actual independently owned source bytes");
        tryCompare(assistant.selectedFiles, "count", 2, 2000,
            "UX356 SETUP: both exact real canonical source IDs are present before Send");
        const admitted = Probe.rows(assistant.selectedFiles);
        const files = admitted.map(file => ({id: file.id, name: file.name,
            bytes: file.bytes, textReadable: file.textReadable, format: file.format}));
        compare(new Set(files.map(file => file.id)).size, 2, "UX356 SETUP: source IDs are app-issued, nonempty and distinct");
        verify(admitted.every(file => file.id.length > 0 && file.pending === true),
            "UX356 SETUP: actual newly admitted sources await original Send acknowledgement");
        verify(assistant.contextConsentRequired, "UX356 SETUP: genuine changed selected-input scope requires fresh approval");
        const initialHistory = JSON.stringify(Probe.rows(assistant.messages));
        const editor = item("assistant.composer");
        const composers = Probe.objectsWithProperty(window, "textRevision").filter(object => object.firstFocusItem === editor);
        compare(composers.length, 1, "UX356: exact original editor has one genuine draft-revision owner");
        const composer = composers[0];
        for (const file of files) ux356_chip(composer, file, false);
        verify(!Ui.itemsWithProperty(popup.contentItem, "text").some(control => control.visible
            && control.text === "Inspect outgoing project context"),
            "UX356: required approval is reached from actual Send, without the retired separate context link");
        let opens = 0;
        function opened() { if (alive313(dialogLife) && dialog.opened) ++opens; }
        dialog.openedChanged.connect(opened);
        try {
            Ui.click(this, Probe, window, editor.objectName); visible185_type("continue");
            const originalText = editor.text, originalRevision = composer.textRevision;
            const selectedBefore = JSON.stringify(Probe.rows(assistant.selectedFiles));
            if (data.tag === "send-keyboard") {
                compare(window.activeFocusItem, editor, "UX356: real Return Send targets the actual focused original composer");
                keyClick(Qt.Key_Return);
            } else Ui.click(this, Probe, window, "assistant.send");
            tryCompare(dialog, "opened", true, 2000, "UX356: actual click/Return Send directly opens required original disclosure");
            compare(JSON.stringify(Probe.rows(assistant.messages)), initialHistory,
                "UX356: requesting approval cannot fabricate an admitted or acknowledged original user row");
            compare(editor.text, originalText, "UX356: before approval original typed text remains exact");
            compare(JSON.stringify(Probe.rows(assistant.selectedFiles)), selectedBefore,
                "UX356: before approval all exact pending source identities/descriptors remain unchanged");
            ux356_compactDialog(dialog);
            if (data.tag === "cancel-new-draft") {
                const cancel = dialog.standardButton(Dialog.Cancel);
                mouseClick(cancel, Ui.clickPoint(cancel).x, Ui.clickPoint(cancel).y);
                tryCompare(dialog, "visible", false, 2000, "UX356: genuine Cancel closes original disclosure without admission");
                compare(editor.text, originalText, "UX356: actual Cancel preserves original draft spelling");
                compare(JSON.stringify(Probe.rows(assistant.selectedFiles)), selectedBefore,
                    "UX356: actual Cancel preserves all original pending source authority/presentation");
                compare(JSON.stringify(Probe.rows(assistant.messages)), initialHistory,
                    "UX356: canceled approval has no admitted/completed input or transcript side effect");
                Ui.click(this, Probe, window, editor.objectName); visible185_type("A genuinely newer draft"); visible185_type("continue");
                verify(composer.textRevision > originalRevision,
                    "UX356: real keyboard edits create a distinct newer revision with identical final text");
                Ui.click(this, Probe, window, "assistant.send");
                tryCompare(dialog, "opened", true, 2000, "UX356: only new actual Send can reopen a canceled request");
            }
            const approvedRevision = composer.textRevision;
            const expectedOpens = data.tag === "cancel-new-draft" ? 2 : 1;
            compare(opens, expectedOpens, "UX356: original approval dialog opens once per genuine requested approval");
            const oldIds = new Set(Probe.rows(assistant.messages).map(row => row.id));
            const ok = dialog.standardButton(Dialog.Ok);
            ux356_fullyExposed(ok); mouseClick(ok, Ui.clickPoint(ok).x, Ui.clickPoint(ok).y);
            let original = null;
            tryVerify(() => {
                const rows = Probe.rows(assistant.messages).filter(row => !oldIds.has(row.id)
                    && row.kind === "user" && row.text === "continue");
                if (rows.length !== 1 || rows[0].status !== "pending") return false;
                original = rows[0]; return true;
            }, 2000, "UX356: actual matching approval auto-resumes exactly one original pending input before held ACK");
            const submissions358 = [{text: "continue", id: original.id, files: files}];
            compare(editor.text, "continue", "UX356: approval/admission is not an acknowledgement that consumes editor text");
            compare(composer.textRevision, approvedRevision, "UX356: queued original approval cannot rewrite original admitted draft revision");
            compare(JSON.stringify(Probe.rows(assistant.selectedFiles)), selectedBefore,
                "UX356: unacknowledged original cannot consume pending selected presentation");
            assistant.refreshUsage();
            tryVerify(() => !assistant.canCancel && assistant.connected && Probe.rows(assistant.messages).some(row =>
                row.id === original.id && row.kind === "user" && row.status === "completed")
                && Probe.rows(assistant.messages).some(row => !oldIds.has(row.id)
                    && row.kind === "assistant" && row.status === "completed"), 10000,
                "UX356: actual original ACK AND original assistant publication settle before history baseline");
            ux358_acknowledgedPresentation(composer, files);
            compare(editor.text, "", "UX356: only completed matching ACK consumes original editor revision");
            const originalRows = Probe.rows(assistant.messages).filter(row => row.id === original.id);
            compare(originalRows.length, 1, "UX356: matching approval/ACK never duplicates original row ID");
            compare(JSON.stringify(originalRows[0].payload.files.map(file => ({id: file.id, name: file.name,
                bytes: file.bytes, textReadable: file.textReadable, format: file.format}))), JSON.stringify(files),
                "UX356: original completed user snapshot retains every exact submitted source descriptor");
            const userRows = Ui.itemsWithProperty(popup.contentItem, "rowId").filter(row => row.rowId === original.id && row.assistant === assistant
            && typeof row.resetDetails === "function" && typeof row.copyTechnicalPayload === "function");
            compare(userRows.length, 1, "UX356: exact original user row owns short-message sent chip presentation");
            for (const file of files) ux356_chip(userRows[0], file, true);
            verify(!assistant.contextConsentRequired, "UX356: completed approved current scope does not request repeat consent");
            const retained = Probe.rows(assistant.messages).map(row => JSON.stringify(row));
            const followIds = new Set(Probe.rows(assistant.messages).map(row => row.id));
            const followFiles358 = Probe.rows(assistant.selectedFiles).map(file => ({id: file.id, name: file.name,
                bytes: file.bytes, textReadable: file.textReadable, format: file.format}));
            Ui.click(this, Probe, window, editor.objectName); visible185_type("continue again");
            Ui.click(this, Probe, window, "assistant.send");
            tryVerify(() => Probe.rows(assistant.messages).some(row => !followIds.has(row.id)
                && row.kind === "user" && row.text === "continue again" && row.status === "pending"), 2000,
                "UX356: already-approved unchanged scope sends directly without another modal");
            const followRows358 = Probe.rows(assistant.messages).filter(row => !followIds.has(row.id)
                && row.kind === "user" && row.text === "continue again" && row.status === "pending");
            compare(followRows358.length, 1, "UX358: second held original input has one actual pending public user identity");
            submissions358.push({text: "continue again", id: followRows358[0].id, files: followFiles358});
            compare(opens, expectedOpens, "UX356: unchanged approved scope never repeats the disclosure");
            verify(!dialog.visible, "UX356: ordinary approved Send does not reopen approval UI");
            assistant.refreshUsage();
            tryVerify(() => !assistant.canCancel && Probe.rows(assistant.messages).some(row => !followIds.has(row.id)
                && row.kind === "user" && row.text === "continue again" && row.status === "completed")
                && Probe.rows(assistant.messages).some(row => !followIds.has(row.id)
                    && row.kind === "assistant" && row.status === "completed"), 10000,
                "UX356: second original ACK and response settle before removal/readback");
            ux358_acknowledgedPresentation(composer, followFiles358);
            const completedFollow358 = Probe.rows(assistant.messages).filter(row => row.id === followRows358[0].id);
            compare(completedFollow358.length, 1, "UX358: second matching ACK retains exactly its original public row identity");
            compare(completedFollow358[0].status, "completed", "UX358: second original receipt is its actual completed ACK row");
            compare(JSON.stringify(completedFollow358[0].payload.files.map(file => ({id: file.id, name: file.name,
                bytes: file.bytes, textReadable: file.textReadable, format: file.format}))), JSON.stringify(followFiles358),
                "UX358: second acknowledged user snapshot retains every exact corresponding submitted source descriptor");
            verify(retained.every(row => Probe.rows(assistant.messages).some(actual => JSON.stringify(actual) === row)),
                "UX356: ordinary repeated work retains every completed original message unchanged");
            const retainedRows = Ui.itemsWithProperty(popup.contentItem, "rowId").filter(row => row.rowId === original.id && row.assistant === assistant
            && typeof row.resetDetails === "function" && typeof row.copyTechnicalPayload === "function");
            compare(retainedRows.length, 1, "UX356: original ID is re-resolved after later delegate/layout publication");
            ux356_chip(retainedRows[0], files[0], true);
            ux356_chip(retainedRows[0], files[1], true);
            compare(JSON.stringify(Probe.rows(assistant.selectedFiles).map(file => ({id:file.id,name:file.name,bytes:file.bytes,textReadable:file.textReadable,format:file.format}))), JSON.stringify(files),
                "UX471: noninteractive sent history preserves BOTH exact original canonical file authorities");
            const preserved = Probe.rows(assistant.messages).filter(row => row.id === original.id);
            compare(preserved.length, 1, "UX471: inspecting sent history preserves sole original historical row");
            compare(JSON.stringify(preserved[0].payload.files.map(file => ({id:file.id,name:file.name,
                bytes:file.bytes,textReadable:file.textReadable,format:file.format}))), JSON.stringify(files),
                "UX471: sent history retains all five original immutable descriptor fields");
            const context = JSON.parse(assistant.contextPreview);
            compare(JSON.stringify(context.selected_files.files.map(file => file.id)), JSON.stringify(files.map(file => file.id)),
                "UX471: history presentation neither grants nor silently revokes current selected read authority");
            Ui.click(this, Probe, window, "assistant.clear");
            tryCompare(assistant.selectedFiles, "count", 0, 2000,
                "UX471: genuine Clear retires ALL original selected read authorities");
            tryCompare(assistant.messages, "count", 0, 2000,
                "UX471: genuine Clear removes old sent snapshots and original conversation together");
            compare(JSON.stringify(JSON.parse(assistant.contextPreview).selected_files.files), "[]",
                "UX471: current outgoing disclosure has NO historical read authority after actual Clear");
            verify(alive313(owner) && Session.project === project,
                "UX356: compact consent/attachment presentation preserves exact original scientific owner");
            compare(save349_science(project), science, "UX356: input/consent/chip changes preserve all original science/data/SU/relations/metadata");
            compare(import265_owner(project), metadata, "UX356: original owner metadata/path/settings remain exact");
            compare(project.modified, modified, "UX356: conversation/file presentation does not dirty the scientific project");
            verify(!project.calculating && Probe.computedCurrent(project.currentExperiment),
                "UX356: unchanged actual science remains current without a forced stamp or extra observation window");
            compare(project.canUndo, undo, "UX356: presentation and permission changes invent no scientific Undo step");
            compare(JSON.stringify(Probe.rows(assistant.models)), account,
                "UX356: genuine managed account/catalog remains exact through original admission and removal");
            console.info("UX356_IDS", JSON.stringify({case: data.tag, first: original.id,
                files: files, cleared: files.map(file => file.id), dialogOpens: opens,
                submissions: submissions358}));
            visible185_capture("ux356-" + data.tag);
        } finally { disconnect313(dialogLife, dialog, "openedChanged", opened); }
    }
    // The seven-case family's additional row enters only after the original
    // four-point fit and ordinary writer/readback establish the saved directory.
    function save359_current_ten_refit(project) {
        const owner = lifetime313(project), path = project.path;
        const inputs = visible185_inputs(project), shape = relation246_shape(project);
        const declarations = relation245_declarations(project);
        const beforeRows = Probe.rows(project.currentExperiment.background);
        compare(JSON.stringify(beforeRows.map(row => [row.id, row.position, row.intensity.value])),
            JSON.stringify([["1", 8, 0], ["6", 15, 0], ["10", 70, 0], ["14", 150, 0]]),
            "SAVE359 SETUP: real saved current owner begins with FOUR independently declared original anchors");
        verify(!project.modified && !Session.needsSaveAs,
            "SAVE359 SETUP: the four-anchor current folder is genuinely owned and clean before editing");
        compare(path, ApplicationInfo.localPath(Probe.referenceUrl("current")),
            "SAVE359 SETUP: original current path is the established four-anchor directory");
        const names = ["project.edi", "structures/cosio.edi", "experiments/d20.edi", "analysis/analysis.edi"];
        const diskBefore = names.map(name => Probe.readReferenceFile("current/" + name));
        const background = project.currentExperiment.background;
        const update = background.changeDefined("update", "1", 8, 5.5, false);
        verify(update.applied === true && update.published === true,
            "SAVE359 SETUP: lawful original ordinary background update actually applies/publishes");
        const added = [["save359_9", 9, 10], ["save359_12", 12, 12.5], ["save359_25", 25, 15],
            ["save359_50", 50, 17.5], ["save359_90", 90, 20], ["save359_130", 130, 22.5]];
        for (const entry of added) {
            const outcome = background.changeDefined("add", entry[0], entry[1], entry[2], false);
            verify(outcome.applied === true && outcome.published === true,
                "SAVE359 SETUP: each lawful ordinary Add really applies/publishes one independent anchor");
            verify(alive313(owner) && Session.project === project && project.path === path && project.modified,
                "SAVE359: background edits retain original current owner/path and genuinely dirty its saved state");
        }
        for (const row of Probe.rows(background)) {
            verify(row.intensity.refinable && row.intensity.fittable,
                "SAVE362B SETUP: every one of the ten genuine background intensities is actually eligible for fitting");
            row.intensity.free = true; // Existing ordinary ParameterItem free entrance; never a fabricated fit/currentness stamp.
            compare(row.intensity.free, true, "SAVE362B SETUP: all TEN actual background intensities are free before refit");
        }
        const expected = [["1", 8, 5.5, true], ["6", 15, 0, true], ["10", 70, 0, true], ["14", 150, 0, true]]
            .concat(added.map(entry => [entry[0], entry[1], entry[2], true]));
        function anchors() {
            return Probe.rows(background).map(row => [row.id, row.position, row.intensity.value, row.intensity.free]);
        }
        function assertTenMembership() {
            const actual = anchors();
            compare(actual.length, 10, "SAVE359: all TEN actual original and newly admitted background rows remain present");
            for (const row of expected) {
                const found = actual.filter(value => value[0] === row[0]);
                compare(found.length, 1, "SAVE359: every independently declared background ID remains unique");
                compare(JSON.stringify([found[0][0], found[0][1], found[0][3]]), JSON.stringify([row[0], row[1], true]),
                    "SAVE362B: all ten independent anchor identities/positions and FREE flags survive real refit/Save");
            }
        }
        function assertTenStarts() {
            assertTenMembership();
            for (const row of expected) compare(JSON.stringify(anchors().filter(value => value[0] === row[0])[0]), JSON.stringify(row),
                "SAVE362B SETUP: exact independent starting intensity operands are required BEFORE actual fitting only");
        }
        function roundedBackground() {
            return JSON.stringify(background285_rows(project).map(row => {
                const su = project.suText(row.intensity, row.uncertainty);
                return [row.id, row.position, row.free, row.hasUncertainty, row.uid,
                    row.minimum, row.maximum, row.name, row.units, su.value, su.su, su.bracket];
            }));
        }
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment), 10000,
            "SAVE359 SETUP: actual ten-anchor edit calculation settles before genuine refit");
        assertTenStarts();
        const beforeFit = visible185_values(project);
        const fit = project.fit, fitLife = lifetime313(fit);
        let starts = 0, finishes = 0;
        function started() { if (alive313(fitLife) && fit.running) ++starts; }
        function finished() { ++finishes; }
        fit.runningChanged.connect(started); fit.finished.connect(finished);
        try {
            visible185_page("analysis"); Ui.click(this, Probe, window, "sideBar.tab.basic");
            Ui.click(this, Probe, window, "fitting.start");
            tryVerify(() => finishes === 1 && !fit.running && !project.calculating
                && Probe.computedCurrent(project.currentExperiment), 10000,
                "SAVE359 SETUP: real ordinary second FitJob finishes/publishes current ten-anchor science");
            compare(starts, 1, "SAVE359: actual ten-anchor refit starts precisely one real worker");
            verify(["success", "maxIterations"].includes(fit.outcome) && fit.iterations > 0
                && Probe.rows(fit.results).length > 0 && visible185_values(project) !== beforeFit,
                "SAVE359: refit actually moves parameters with real successful/bounded iterative results");
            verify(visible185_parameters(project).some(parameter => parameter.free
                && parameter.hasUncertainty && parameter.uncertainty > 0),
                "SAVE359: actual positive fitted SUs exercise ordinary writer rounding");
        } finally {
            disconnect313(fitLife, fit, "runningChanged", started);
            disconnect313(fitLife, fit, "finished", finished);
        }
        assertTenMembership();
        const postFitBackground = background285_rows(project);
        verify(postFitBackground.length === 10 && postFitBackground.every(row => row.free
            && row.hasUncertainty && Number.isFinite(row.intensity) && Number.isFinite(row.uncertainty) && row.uncertainty > 0),
            "SAVE362B SETUP: genuine refit publishes positive fitted SUs for ALL TEN actual free background intensities");
        verify(postFitBackground.some(row => row.intensity !== expected.filter(value => value[0] === row.id)[0][2]),
            "SAVE362B SETUP: actual background fitting moves at least one declared start, never a fixed/cached substitute");
        const encodedBackground = roundedBackground();
        compare(visible185_inputs(project), inputs, "SAVE359: background/refit preserves every original measured triple, mask, weight and phase link");
        compare(relation246_shape(project), shape, "SAVE359: background/refit preserves actual original sites/composition/coordinates/occupancies");
        compare(relation245_declarations(project), declarations, "SAVE359: actual original enabled/disabled equations and aliases survive refit");
        visible185_page("project"); Ui.click(this, Probe, window, "mainArea.project.tab.description");
        Ui.click(this, Probe, window, "project.title"); visible185_type("Original visible Save current-ten-refit");
        keyClick(Qt.Key_Return);
        compare(project.title, "Original visible Save current-ten-refit",
            "SAVE359: actual original user title is committed before ordinary writer reference and Save");
        for (let index = 0; index < names.length; ++index)
            compare(Probe.readReferenceFile("current/" + names[index]), diskBefore[index],
                "SAVE359: ten-anchor edits/refit have NOT been secretly saved before delegated current Save");
        // Existing public BlockText is the ordinary writer's lazy Text-tab
        // output. Reading it creates no destination or replacement owner.
        const blocks = {"project.edi": project.metadataText, "structures/cosio.edi": project.currentStructure.text,
            "experiments/d20.edi": project.currentExperiment.text, "analysis/analysis.edi": project.analysis.text};
        const documents = {};
        for (const name of names) {
            documents[name] = blocks[name].text;
            verify(blocks[name].error === "" && documents[name].length > 0,
                "SAVE359: each actual pre-Save ordinary writer document is nonempty and has no writer refusal");
        }
        const completeText = project.projectText.text;
        verify(project.projectText.error === "" && completeText.length > 0,
            "SAVE359: complete original public Project Text is a healthy ordinary-writer document-closure witness");
        function roundedValues() {
            return JSON.stringify(visible185_parameters(project).map(parameter => {
                const su = project.suText(parameter.value, parameter.uncertainty);
                // Compare encoded ordinary SU spelling here, not an unsupported
                // raw null-versus-fixed-zero storage promise. The independent
                // real loader compares every persisted value/free/SU below.
                return [parameter.path, parameter.free,
                    su.value.length > 0 ? [su.value, su.su, su.bracket] : [parameter.value, su.su, su.bracket]];
            }));
        }
        const values = roundedValues(), metadata = import265_owner(project);
        const result = {outcome: fit.outcome, iterations: fit.iterations};
        const undo = item("appBar.button.undo").enabled;
        console.info("SAVE359_ORDINARY", JSON.stringify({documents: documents, completeText: completeText,
            currentPath: path, four: 4, initialTen: expected, ten: anchors(), postFitBackground: postFitBackground,
            encodedBackground: encodedBackground, dirty: project.modified, refitStarts: starts,
            fittedOutcome: fit.outcome, fittedIterations: fit.iterations}));
        verify(alive313(owner) && Session.project === project && project.path === path && project.modified,
            "SAVE359: public ordinary Text reference leaves original ten-anchor fitted owner/path DIRTY before Save");
        toggle(); assistant.signIn(); visible185_ready("save359-bootstrap");
        if (assistant.contextConsentRequired) assistant.signIn();
        visible185_ready("save359-disclosed");
        compare(Session.project, project,
            "SAVE604 SETUP: ordinary current refit Save retains the actual original Session owner");
        compare(project.path, path,
            "SAVE604 SETUP: ordinary refit Save retains the SAME independently owned current directory");
        verify(!Session.needsSaveAs,
            "SAVE604 SETUP: actual owned-current refit Save needs no fresh-parent selection or grant");
        const show = item("assistant.showActions");
        verify(show.enabled && show.visible && !assistant.showActions,
            "SAVE359 SETUP: original actionable mode checkbox begins in normal mode");
        mouseClick(show); verify(assistant.showActions, "SAVE359: real checkbox selects actual visible Save controls");
        const account = JSON.stringify(Probe.rows(assistant.models));
        const before = new Set(Probe.rows(assistant.messages).map(row => row.id));
        const save = Ui.control(Probe, window, "appBar.button.save"), saveLife = lifetime313(save);
        verify(save.enabled && Ui.exposed(save), "SAVE359: original ordinary current Save button is physically actionable");
        let clicks = 0;
        function clicked() { ++clicks; }
        save.clicked.connect(clicked);
        try {
            assistant.send("Save this actual fitted displayed project using original visible Save current-ten-refit");
            tryVerify(() => !assistant.canCancel && !assistant.showingActions
                && visible185_outcome("save349-current-ten-refit", before) !== null,
                visible237_observationMs([{path: "", text: "Original μ 🧪 saved project"}]),
                "SAVE359: exact original current Save request actually returns/settles within the existing bound");
            const outcome = visible185_outcome("save349-current-ten-refit", before);
            console.log("SAVE349_TERMINAL", JSON.stringify({case: "current-ten-refit", outcome: outcome,
                currentPath: Session.project ? Session.project.path : null}));
            verify(outcome.status === "succeeded" && outcome.committed === true && outcome.reopened === false
                && outcome.active === true && typeof outcome.presentation_complete === "boolean",
                "SAVE604: ordinary current refit Save commits/is active with truthful presentation and no invented reopen");
            compare(clicks, 0, "SAVE604: visible current Save uses only the original cue, never a dispatched button click");
            verify(alive313(owner) && Session.project === project && project.path === path && !project.modified,
                "SAVE359: same live original displayed owner/path is saved/unmodified without a fresh directory");
            verify(alive313(fitLife), "SAVE359: original public real-fit receiver remains alive before outcome readback");
            compare(outcome.destination, path, "SAVE359: exact original current directory is the truthful actual destination");
            tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment), 10000,
                "SAVE359: original active ten-anchor owner is actually current after saved readback publication");
            assertTenMembership();
            compare(roundedBackground(), encodedBackground,
                "SAVE362B: ALL genuine post-fit background values/free/positive-SU/spec metadata follow ordinary writer rounding after active Save");
            compare(roundedValues(), values, "SAVE359: all active parameter values/free/SUs follow the ORIGINAL ordinary writer rounding rule");
            compare(visible185_inputs(project), inputs, "SAVE359: current Save retains ALL original observations/sigmas/masks/weights/links");
            compare(relation246_shape(project), shape, "SAVE359: current Save retains actual original physical sites/composition");
            compare(relation245_declarations(project), declarations, "SAVE359: current Save retains exact original scientific declarations");
            compare(import265_owner(project), metadata, "SAVE359: actual current Save retains every original metadata/path/settings fact");
            compare(fit.outcome, result.outcome, "SAVE359: original real refit outcome remains factual after Save");
            compare(fit.iterations, result.iterations, "SAVE359: original actual refit iterations survive Save");
            compare(item("appBar.button.undo").enabled, undo, "SAVE359: current Save invents/consumes no original Undo availability");
            verify(!Session.needsSaveAs && assistant.connected, "SAVE359: genuine current Save retains account and current-directory ownership");
            compare(JSON.stringify(Probe.rows(assistant.models)), account, "SAVE359: original managed account/model catalog stays exact");
        } finally { disconnect313(saveLife, save, "clicked", clicked); }
    }
    // GUI392: owner/public331 interfaces; source-authored, not a runtime result.
    function gui392_json(value) { return JSON.parse(JSON.stringify(value)); }
    function gui392_labels(root) {
        return Ui.itemsWithProperty(root, "text").filter(control => control.visible
            && typeof control.text === "string" && typeof control.textFormat === "number");
    }
    function gui392_dialog(name) {
        const original = {assistant: Session.assistant, project: Session.project, popup: popup};
        verify(original.assistant === assistant && popup.assistant === assistant,
            "GUI398: original Main Popup and Session retain SAME controller before genuine dialog readiness");
        const dialogs = Probe.objectsWithProperty(window, "opened").filter(object => object.objectName === name);
        compare(dialogs.length, 1, "GUI398: SAME original Main window owns ONE exact named dialog, including its enter interval: " + name);
        const dialog = dialogs[0], life = lifetime313(dialog), popupLife = lifetime313(popup);
        tryVerify(() => alive313(life) && alive313(popupLife)
            && Session.assistant === original.assistant && Session.project === original.project
            && popup === original.popup && popup.assistant === original.assistant
            && dialog.visible && dialog.opened, 2000,
            "GUI398: original unique receiver genuinely completes native enter before opened/exposure assertions: " + name);
        const current = Probe.objectsWithProperty(window, "opened").filter(object => object.objectName === name);
        compare(current.length, 1, "GUI398: settled original dialog remains unique, no replacement/hidden duplicate blessing");
        compare(current[0], dialog, "GUI398: readiness belongs to SAME captured original dialog");
        gui398_nativeDialog(dialog);
        return dialog;
    }
    function gui563_pickerExposed(control, panel, host) {
        verify(control !== null && host !== null && host.visible && host.contentItem !== null
            && panel.contentItem.Window.window === host && control.Window.window === host
            && control.visible && control.width > 0 && control.height > 0,
            "PICKER563: original picker control has positive geometry in its exact current content-host Window");
        let inHost = false;
        for (let parent = control.parent; parent; parent = parent.parent) {
            inHost = inHost || parent === Ui.windowRoot(host);
            if (parent.clip) {
                const bounds = control.mapToItem(parent, 0, 0, control.width, control.height);
                verify(bounds.x >= -0.5 && bounds.y >= -0.5
                    && bounds.x + bounds.width <= parent.width + 0.5
                    && bounds.y + bounds.height <= parent.height + 0.5,
                    "PICKER563: complete original control fits every actual picker clipping viewport");
            }
        }
        verify(inHost && Ui.rendered(control) && Ui.exposed(control),
            "PICKER563: original receiver belongs to its genuine visible picker window");
        const bounds = control.mapToItem(host.contentItem, 0, 0, control.width, control.height);
        verify(bounds.x >= -0.5 && bounds.y >= -0.5
            && bounds.x + bounds.width <= host.contentItem.width + 0.5
            && bounds.y + bounds.height <= host.contentItem.height + 0.5,
            "PICKER563: complete original control fits the unchanged actual picker window viewport");
    }
    function gui392_button(button, dialog, retainReceipt407, pickerHost563) {
        verify(button !== null && button.enabled, "GUI392: original standard action is enabled");
        if (pickerHost563) gui563_pickerExposed(button, dialog, pickerHost563);
        else ux356_fullyExposed(button);
        const point = Ui.clickPoint(button);
        const receipt407 = gui407_nativeReceipt(button, dialog, point);
        let returned407 = false;
        try {
            receipt407.sample("before-original-mouse",false);
            verify(receipt407.current(), "GUI407: original native receiver/dialog/window/controller/owner are current before SAME mouse action");
            mouseClick(button, point.x, point.y);
            rendered();
            receipt407.sample("original-helper-return",false);
            verify(receipt407.current(), "GUI407: original surviving native receiver/dialog/window/controller/owner cannot be replaced at helper return");
            returned407 = true;
            if (retainReceipt407) return receipt407;
        } finally {
            if (!retainReceipt407 || !returned407) {
                const evidence407 = receipt407.finish(returned407 ? "standard-return" : "standard-failure");
                if (returned407) verify(evidence407, "GUI407: successful original native action requires complete passive input/frame receipt");
            }
        }
    }
    // GUI470: ordinary standard action geometry and ORIGINAL native signal receipt.
    function gui470_contains(outer, inner) {
        return outer.length === 4 && inner.length === 4
            && outer.concat(inner).every(value => typeof value === "number" && Number.isFinite(value))
            && outer[2] > 0 && outer[3] > 0 && inner[2] > 0 && inner[3] > 0
            && inner[0] >= outer[0] - 0.5 && inner[1] >= outer[1] - 0.5
            && inner[0] + inner[2] <= outer[0] + outer[2] + 0.5
            && inner[1] + inner[3] <= outer[1] + outer[3] + 0.5;
    }
    function gui470_standardAction(button, dialog, role) {
        verify(role === "sign-in" || role === "approve-context",
            "GUI472 SETUP: independent original semantic role is sign-in or current-context approval");
        const labels472 = {"sign-in":"Sign in with ChatGPT","approve-context":"Approve context"};
        const expectedText = labels472[role]; // Independent unchanged PUBLIC original full labels, never button.text as golden.
        const original = {owner:Session.project,controller:Session.assistant,window:window,button:button,dialog:dialog};
        const objects = [original.owner,original.controller,original.window,button,dialog];
        const lives = objects.map(lifetime313);
        function current() {
            return lives.every(alive313) && Session.project === original.owner
                && Session.assistant === original.controller && window === original.window
                && original.button === button && original.dialog === dialog;
        }
        verify(current() && dialog.visible && dialog.opened && button !== null && button.enabled,
            "GUI470: original settled action/dialog/window/controller/project are live before native input");
        compare(dialog.standardButton(Dialog.Ok), button,
            "GUI470: action is exact original native standard Ok receiver, not a substitute input");
        compare(button.text, expectedText, "GUI470: actual native action displays complete independent literal label");
        compare(assistant.connected, role === "approve-context",
            "GUI470: Sign in starts disconnected, Approve starts genuinely connected");
        const connectedBefore = assistant.connected, footer = dialog.footer;
        verify(footer !== null && footer.contentItem !== null && gui393_under(button, footer.contentItem),
            "GUI470: SAME original standard receiver really belongs to original footer's native content row");
        const row = footer.contentItem;
        function scene(item) {
            const r = item.mapToItem(window.contentItem, 0, 0, item.width, item.height);
            return [r.x,r.y,r.width,r.height];
        }
        const mappedDialog = dialog.parent.mapToItem(window.contentItem,dialog.x,dialog.y,dialog.width,dialog.height);
        const popupBounds = [mappedDialog.x,mappedDialog.y,mappedDialog.width,mappedDialog.height];
        const footerBounds = scene(footer), rowBounds = scene(row), buttonBounds = scene(button);
        // Observe at the SAME original opened/click interval. No extra polish,
        // scroll, delay, changed point, forced geometry or label assignment.
        verify(gui470_contains(popupBounds,footerBounds) && gui470_contains(footerBounds,rowBounds),
            "GUI470: actual original footer and native row are contained by their own modal surface");
        for (const bounds of [popupBounds,footerBounds,rowBounds]) verify(gui470_contains(bounds,buttonBounds),
            "GUI470: full actual Sign in/Approve hit rectangle stays INSIDE original popup/footer/row");
        const labels = gui392_labels(button).filter(label => label.text === expectedText
            && button.contentItem !== null && gui393_under(label,button.contentItem));
        compare(labels.length,1,"GUI470: original standard action owns ONE actual painted complete native label");
        const label = labels[0];
        verify(label.lineCount === 1 && !label.truncated && label.contentWidth > 0,
            "GUI470: full actual standard action label is one untruncated native text line");
        ux356_fullyExposed(button);ux356_fullyExposed(label);
        gui470ActionInk.font = label.font;gui470ActionInk.text = expectedText;
        const metrics = gui470ActionInk.tightBoundingRect;
        const available = label.width - label.leftPadding - label.rightPadding;
        verify(Number.isFinite(available) && available >= gui470ActionInk.advanceWidth - 0.5,
            "GUI470: actual native text slot fits full independently measured original action label");
        let origin = label.leftPadding;
        if (label.horizontalAlignment === Text.AlignHCenter) origin += (available-gui470ActionInk.advanceWidth)/2;
        else if (label.horizontalAlignment === Text.AlignRight) origin += available-gui470ActionInk.advanceWidth;
        else compare(label.horizontalAlignment,Text.AlignLeft,
            "GUI470: original literal single-line label has a supported native horizontal alignment");
        const ink = label.mapToItem(window.contentItem,origin+metrics.x,label.baselineOffset+metrics.y,metrics.width,metrics.height);
        const inkBounds = [ink.x,ink.y,ink.width,ink.height];
        // Original strict geometry is unchanged. Record its actual operands BEFORE a possible failure.
        console.log("GUI499_ACTION_INK_BEFORE", JSON.stringify({role:role,
            receiver:identity313(lives[3]), dialog:identity313(lives[4]),
            owner:identity313(lives[0]), controller:identity313(lives[1]),
            label:String(label), labelBounds:scene(label), baseline:label.baselineOffset,
            padding:[label.leftPadding,label.topPadding,label.rightPadding,label.bottomPadding],
            content:[label.contentWidth,label.contentHeight], labelAdvance:[label.advance.width,label.advance.height],
            horizontalAlignment:label.horizontalAlignment, verticalAlignment:label.verticalAlignment,
            font:{family:label.font.family,pixelSize:label.font.pixelSize,pointSize:label.font.pointSize,
                bold:label.font.bold,italic:label.font.italic,hinting:label.font.hintingPreference},
            labelRenderType:label.renderType, metricsRenderType:gui470ActionInk.renderType,
            advanceWidth:gui470ActionInk.advanceWidth, tightBounds:[metrics.x,metrics.y,metrics.width,metrics.height],
            actualInk:inkBounds, containers:[buttonBounds,rowBounds,footerBounds,popupBounds].map((bounds,index) => ({
                kind:["button","row","footer","popup"][index],bounds:bounds,fits:gui470_contains(bounds,inkBounds)}))}));
        for (const bounds of [buttonBounds,rowBounds,footerBounds,popupBounds]) verify(gui470_contains(bounds,inkBounds),
            "GUI470: independently measured actual font ink fits original action/row/footer/popup");
        const point = Ui.clickPoint(button);
        verify(point !== null,"GUI470: SAME original standard action supplies its unchanged native click point");
        const scenePoint = button.mapToItem(window.contentItem,point.x,point.y);
        verify([scenePoint.x,scenePoint.y].every(Number.isFinite) && [buttonBounds,rowBounds,footerBounds,popupBounds].every(bounds =>
            scenePoint.x >= bounds[0] && scenePoint.x < bounds[0]+bounds[2]
            && scenePoint.y >= bounds[1] && scenePoint.y < bounds[1]+bounds[3]),
            "GUI470: unchanged original center/clip click point is inside SAME original modal/native action");
        const events = [], bindings = [];
        function record(kind) {
            verify(current(),"GUI470: real standard-button signal retains exact original live receiver/window/owner");
            events.push({kind:kind,pressed:button.pressed});
        }
        const pressed = function(){record("pressedChanged");};
        const released = function(){record("released");};
        const clicked = function(){record("clicked");};
        const canceled = function(){record("canceled");};
        try {
            for (const pair of [["pressedChanged",pressed],["released",released],["clicked",clicked],["canceled",canceled]]) {
                button[pair[0]].connect(pair[1]);bindings.push(pair);
            }
            gui392_button(button,dialog); // Original helper performs its ONE unchanged native mouse action.
            verify(current(),"GUI470: original physical receiver and owner survive the native signal tail");
            const presses = events.filter(event => event.kind === "pressedChanged" && event.pressed);
            compare(presses.length,1,"GUI470: exactly ONE actual true pressed edge reached original standard button");
            compare(events.filter(event => event.kind === "released").length,1,
                "GUI470: exactly ONE actual native released signal reached original standard button");
            compare(events.filter(event => event.kind === "clicked").length,1,
                "GUI470: exactly ONE actual native clicked signal, not a popup-dismissal substitute");
            compare(events.filter(event => event.kind === "canceled").length,0,
                "GUI470: outside-modal or canceled pointer delivery cannot qualify as original action");
            verify(events.findIndex(event => event.kind === "pressedChanged" && event.pressed)
                < events.findIndex(event => event.kind === "released")
                && events.findIndex(event => event.kind === "released") < events.findIndex(event => event.kind === "clicked"),
                "GUI470: original true press then release precede exact native click");
            console.log("GUI470_STANDARD_ACTION",JSON.stringify({role:role,text:expectedText,connectedBefore:connectedBefore,
                button:identity313(lives[3]),dialog:identity313(lives[4]),owner:identity313(lives[0]),controller:identity313(lives[1]),
                popup:popupBounds,footer:footerBounds,row:rowBounds,buttonBounds:buttonBounds,ink:inkBounds,
                scenePoint:[scenePoint.x,scenePoint.y],events:events}));
        } finally {
            for (const pair of bindings) disconnect313(lives[3],button,pair[0],pair[1]);
        }
    }
    function gui392_signIn(showDetails476) {
        if (assistant.connected) return;
        Ui.click(this, Probe, window, "assistant.connection");
        const dialog = ux356_dialog();
        tryCompare(dialog, "opened", true, 2000, "GUI392: actual header Sign in opens original provider dialog");
        if (showDetails476 === true) gui398_details(dialog); // Existing original exact-preview observer, SAME disconnected offer.
        gui470_standardAction(dialog.standardButton(Dialog.Ok), dialog, "sign-in");
        report187_ready("gui392-genuine-header-signin", false);
        tryCompare(dialog, "visible", false, 2000, "GUI398: original ready sign-in dialog genuinely finishes native exit before reuse");
    }
    function gui392_science() {
        const project = Session.project;
        return {owner: project, life: lifetime313(project), metadata: import265_owner(project),
            values: visible185_values(project), inputs: visible185_inputs(project),
            relations: relation245_declarations(project), undo: project.canUndo, modified: project.modified};
    }
    function gui392_unchanged(before) {
        verify(alive313(before.life) && Session.project === before.owner,
            "GUI392: GUI/configuration does not replace or retire the original scientific owner");
        compare(import265_owner(before.owner), before.metadata, "GUI392: original metadata/path/settings stay exact");
        compare(visible185_values(before.owner), before.values, "GUI392: every physical value/free/SU stays exact");
        compare(visible185_inputs(before.owner), before.inputs, "GUI392: whole measured triples/weights/exclusions/links stay exact");
        compare(relation245_declarations(before.owner), before.relations, "GUI392: aliases/constraints stay exact");
        compare(before.owner.canUndo, before.undo, "GUI392: GUI/source configuration creates no scientific Undo");
        compare(before.owner.modified, before.modified, "GUI392: GUI/source configuration creates no scientific dirty state");
    }
    function gui392_setup() {
        verify(Session.openProject(Probe.referenceUrl("project")), "GUI392 SETUP: owned lawful default-table fixture opens normally");
        tryVerify(() => !Session.project.calculating && Probe.computedCurrent(Session.project.currentExperiment), 10000,
            "GUI392 SETUP: original lawful scientific calculation is actually current before GUI preservation baseline");
        toggle();
        return gui392_science();
    }
    function test_gui392_signed_out_native_empty_and_real_account() {
        const before = gui392_setup();
        compare(assistant.connected, false, "GUI392: owned actor begins genuinely signed out");
        const empty = gui392_labels(popup.contentItem).filter(label => label.text === "Sign in to use the assistant");
        compare(empty.length, 1, "GUI392: exactly one native signed-out empty-state label is painted");
        ux356_fullyExposed(empty[0]);
        const emptyOwner = empty[0].parent;
        const region = empty[0].mapToItem(emptyOwner, 0, 0, empty[0].width, empty[0].height);
        verify(emptyOwner.height >= popup.contentItem.height / 2
            && Math.abs(region.y + region.height / 2 - emptyOwner.height / 2) < 0.5,
            "GUI392: native empty state is vertically centered in its actual sidebar body, not a second sign-in toolbar");
        compare(empty[0].font.family, EaStyle.Fonts.secondFontFamily,
            "GUI395: original native EmptyStateLabel uses independent second font family");
        compare(empty[0].font.pixelSize, EaStyle.Sizes.fontPixelSize * 3,
            "GUI395: original native EmptyStateLabel uses three existing font units");
        compare(empty[0].font.weight, Font.ExtraLight,
            "GUI395: original native EmptyStateLabel uses independent extra-light weight");
        compare(empty[0].enabled, false, "GUI395: native empty-state text is semantically disabled");
        tryVerify(() => Qt.colorEqual(empty[0].color, EaStyle.Colors.themeForegroundDisabled), 2000,
            "GUI395: original native disabled Label resolves disabled theme foreground");
        compare(empty[0].horizontalAlignment, Text.AlignHCenter, "GUI395: native empty-state text is horizontally centered");
        compare(empty[0].wrapMode, Text.WordWrap, "GUI395: native empty-state retains original word wrapping");
        const links = Ui.itemsWithProperty(popup.contentItem, "clicked").filter(control =>
            control.visible && control.enabled && control.text === "Sign in");
        compare(links.length, 1, "GUI392: ONLY one actual header Sign in action, no centered duplicate");
        compare(links[0].objectName, "assistant.connection", "GUI392: sole Sign in is original connection entrance");
        for (const name of ["assistant.composer", "assistant.files.add", "assistant.send", "assistant.clear", "assistant.usage", "assistant.showActions", "assistant.modelEffort"]) {
            const controls = Ui.itemsWithProperty(popup.contentItem, "objectName").filter(control => control.objectName === name);
            verify(controls.every(control => !Ui.rendered(control)), "GUI392: signed-out ordinary action is physically unavailable: " + name);
        }
        verify(!Ui.itemsWithProperty(popup.contentItem, "objectName").some(control => control.objectName === "assistant.workflow"),
            "GUI392: retired per-skill chat browser is absent");
        capture("gui392-signed-out-native-empty");
        gui395_dividers("signed-out");
        gui395_signInHover(links[0]);
        console.log("GUI395_SIGNIN_BEFORE");
        Ui.click(this, Probe, window, "assistant.connection");
        const signIn = ux356_dialog();
        tryCompare(signIn, "opened", true, 2000, "GUI392: genuine Sign in reaches original dialog");
        console.log("GUI395_SIGNIN_OPEN");
        gui398_details(signIn);
        compare(Session.project, before.owner, "GUI395: genuine Sign in click preserves SAME original scientific owner");
        gui392_button(signIn.standardButton(Dialog.Cancel), signIn);
        tryCompare(signIn, "visible", false, 2000, "GUI395: ordinary Cancel actually closes ORIGINAL sign-in dialog");
        compare(assistant.connected, false, "GUI392: real authentication Cancel does not create account authority");
        gui392_unchanged(before);
        gui392_signIn();
        verify(item("assistant.composer").visible && item("assistant.composer").enabled,
            "GUI392: real authenticated readiness reveals usable original composer");
        compare(gui392_labels(popup.contentItem).filter(label => label.text === "Sign in to use the assistant").length, 0,
            "GUI392: ready state hides signed-out presentation");
        gui395_dividers("authenticated");
        const avatar = item("assistant.connection"), usage = item("assistant.usage"), clear = item("assistant.clear");
        for (const control of [clear, usage, avatar]) ux356_fullyExposed(control);
        verify(rect(clear)[0] < rect(usage)[0] && rect(usage)[0] < rect(avatar)[0],
            "GUI392: real header order is Clear, actual remaining percentage, avatar at far right");
        compare(avatar.text, "O", "GUI392: actual Original@example.invalid email yields its email initial, not invented name");
        verify(clear.fontIcon === "eraser" && /clear/i.test(clear.Accessible.name),
            "GUI392: actual Clear has icon and accessible action name");
        gui398_header(avatar);
        const consent = assistant.contextConsentRequired, selected = JSON.stringify(Probe.rows(assistant.selectedFiles));
        Ui.click(this, Probe, window, "assistant.connection");
        const account = gui392_dialog("assistant.accountDialog");
        const accountText = gui392_labels(account.contentItem).map(label => label.text).join("\n");
        verify(accountText.includes("Original@example.invalid") && accountText.includes("Plus"),
            "GUI392: Account shows exact actual owned email and supported plan");
        verify(!Probe.objectsWithProperty(window, "opened").some(object => object.objectName === "assistant.usageDialog" && object.visible),
            "GUI392: Account is distinct from Usage");
        gui398_account(account);
        ux356_fullyExposed(account.contentItem); ux356_fullyExposed(account.footer);
        capture("gui392-ready-account");
        gui392_button(account.standardButton(Dialog.Close), account);
        tryCompare(account, "visible", false, 2000, "GUI399: SAME original Account exit settles before actual later reopen");
        compare(assistant.contextConsentRequired, consent, "GUI392: avatar never approves outgoing project scope");
        compare(JSON.stringify(Probe.rows(assistant.selectedFiles)), selected, "GUI392: avatar never grants selected files");
        Ui.click(this, Probe, window, "assistant.connection");
        compare(gui392_dialog("assistant.accountDialog"), account, "GUI399: genuine later avatar opening settles SAME original Account before Sign out input");
        import265_click("assistant.signOut");
        tryCompare(assistant, "connected", false, 2000, "GUI392: real Account sign out retires actual account");
        tryCompare(account, "visible", false, 2000, "GUI392: actual sign out closes original account popup");
        verify(!Ui.rendered(item("assistant.composer")), "GUI392: signed-out composer becomes physically unavailable again");
        gui392_unchanged(before);
    }
    function gui392_usageLabel(expected) {
        const control = item("assistant.usage");
        const labels = gui392_labels(control).filter(label => label.text === expected);
        compare(labels.length, 1, "GUI392: one actual painted usage value equals independent supplied allowance: " + expected);
        compare(labels[0].font.pixelSize, EaStyle.Sizes.fontPixelSize, "GUI392: usage uses normal native font size");
        ux356_fullyExposed(labels[0]);
        return labels[0];
    }
    function gui392_usageData() { return gui392_json(assistant.usage); }
    function test_gui392_usage_actual_windows_data() {
        return [
            {tag: "remaining25", remaining: 25, headerUsed: 75, used: [75, 32], color: "normal"},
            {tag: "remaining24", remaining: 24, headerUsed: 76, used: [76, 32], color: "amber"},
            {tag: "remaining5", remaining: 5, headerUsed: 95, used: [95, 32], color: "amber"},
            {tag: "remaining4", remaining: 4, headerUsed: 96, used: [96, 32], color: "red"},
            {tag: "remaining100", remaining: 100, headerUsed: 0, used: [null, 0], color: "normal"},
            {tag: "over100", remaining: 0, headerUsed: 137, used: [137, 32], color: "red"},
            {tag: "unknown", remaining: null, headerUsed: null, used: [null, null], color: "normal"},
            {tag: "stale", remaining: 17, headerUsed: 83, used: [17, 83], color: "amber"},
            {tag: "zero-missing-recovered", remaining: 100, headerUsed: 0, used: [null, 0], color: "normal"}
        ];
    }
    function gui392_closeUsage(dialog) {
        gui392_button(dialog.standardButton(Dialog.Close), dialog);
        tryCompare(dialog, "visible", false, 2000, "GUI392: original Usage dialog actually closes before next open refresh");
    }
    function test_gui392_usage_actual_windows(data) {
        const before = gui392_setup(); gui392_signIn();
        tryVerify(() => !!gui392_usageData().observedAt, 2000, "GUI392: first genuine account usage reply is actually observed");
        mouseMove(window.contentItem, 0, 0); rendered();
        const label = gui392_usageLabel(data.headerUsed === null ? "–" : data.headerUsed + "% used");
        tryVerify(() => Qt.colorEqual(label.color, data.color === "red" ? EaStyle.Colors.red : data.color === "amber" ? EaStyle.Colors.orange : EaStyle.Colors.themeForeground), 2000,
            "GUI398: actual USED header preserves strict remaining thresholds below25 orange/below5 red, not their equality");
        if (data.headerUsed !== null) verify(/used/i.test(item("assistant.usage").ToolTip.text)
            && /used/i.test(item("assistant.usage").Accessible.name),
            "GUI398: actual header tooltip/accessibility consistently disclose USED rather than remaining");
        gui398_noBlueOutline(item("assistant.usage"));
        if (data.tag === "zero-missing-recovered") {
            capture("gui392-usage-actual-zero");
            Ui.click(this, Probe, window, "assistant.usage");
            let dialog = gui392_dialog("assistant.usageDialog");
            tryVerify(() => !gui392_usageData().available && !gui392_usageData().stale
                && gui392_usageData().buckets.length === 0, 2000,
                "GUI392: real dialog-open optional read observes actual empty provider windows, not zero");
            gui392_usageLabel("–"); gui398_usageRows(dialog, [null, null], false);
            capture("gui392-usage-missing"); gui392_closeUsage(dialog);
            Ui.click(this, Probe, window, "assistant.usage"); dialog = gui392_dialog("assistant.usageDialog");
            tryVerify(() => gui392_usageData().available && !gui392_usageData().stale, 2000,
                "GUI392: actual third optional reply recovers genuine zero usage");
            gui392_usageLabel("0% used"); gui398_usageRows(dialog, [null, 0], false);
            capture("gui392-usage-recovered-zero"); gui392_closeUsage(dialog);
        } else {
            const observedBefore = gui392_usageData().observedAt;
            Ui.click(this, Probe, window, "assistant.usage");
            const dialog = gui392_dialog("assistant.usageDialog");
            if (data.tag === "stale") tryVerify(() => gui392_usageData().stale === true, 2000,
                "GUI392: genuine optional read failure marks retained current-account observation stale");
            else tryVerify(() => gui392_usageData().available === (data.remaining !== null)
                && gui392_usageData().observedAt !== observedBefore, 2000,
                "GUI392: real dialog read retains exact known versus unknown provider semantics");
            if (data.tag === "stale") {
                gui392_usageLabel(data.headerUsed + "% used");
                verify(gui392_usageData().stale === true, "GUI404: hiding unsolicited stale copy cannot falsify actual internal freshness");
            }
            gui398_usageRows(dialog, data.used, data.tag === "stale");
            ux356_fullyExposed(dialog.contentItem); ux356_fullyExposed(dialog.footer);
            capture("gui392-usage-" + data.tag); gui392_closeUsage(dialog);
        }
        console.log("GUI392_USAGE", JSON.stringify({tag: data.tag, usage: gui392_usageData()}));
        gui392_unchanged(before);
    }
    function gui392_preferences() {
        Ui.click(this, Probe, window, "appBar.button.preferences");
        const preferences = gui392_dialog("preferences");
        const dialog = preferences, life = lifetime313(dialog), original = Session.project;
        import265_click("preferences.tab.aiAssistance");
        tryVerify(() => {
            if (!alive313(life) || Session.project !== original || !dialog.opened) return false;
            const tables = Ui.itemsWithProperty(dialog.contentItem, "objectName").filter(control =>
                control.objectName === "preferences.ai.sources" && control.sourceModel === assistant.skillSources);
            if (tables.length !== 1 || !Ui.rendered(tables[0]) || !Ui.exposed(tables[0])) return false;
            const r = tables[0].mapToItem(dialog.contentItem,0,0,tables[0].width,tables[0].height);
            return r.x >= -0.5 && r.y >= -0.5 && r.x+r.width <= dialog.contentItem.width+0.5
                && r.y+r.height <= dialog.contentItem.height+0.5;
        }, 2000, "PREFS417: same original native tab/table settles inside actual dialog viewport before strict row input");
        verify(import265_control("preferences.ai.sources").visible,
            "GUI392: genuine Preferences tab exposes original source DataTable");
        return preferences;
    }
    function gui392_sources() { return gui392_json(Probe.rows(assistant.skillSources)); }
    function gui392_sourceControl(name) {
        const preferences = gui392_dialog("preferences");
        const tables = Ui.itemsWithProperty(preferences.contentItem, "objectName").filter(control =>
            control.objectName === "preferences.ai.sources" && Ui.rendered(control));
        compare(tables.length, 1, "GUI392: one current Preferences source table owns row controls");
        compare(tables[0].sourceModel, assistant.skillSources, "GUI392: actual table is bound to original VM source model");
        const controls = Ui.itemsWithProperty(tables[0], "objectName").filter(control =>
            control.objectName === name && Ui.rendered(control));
        compare(controls.length, 1, "GUI392: exact current model/table owns unique opaque-ID row control: " + name);
        ux356_fullyExposed(controls[0]);
        return controls[0];
    }

    function gui392_folder(relative, cancel) {
        const before = gui392_sources();
        import265_click("preferences.ai.sources.add");
        const selectors = Probe.objectsWithProperty(window, "visible").filter(object =>
            object.objectName === "preferences.ai.sources.folder" && object.visible);
        compare(selectors.length, 1, "GUI392: actual Add opens original single named FolderDialog");
        const selector = selectors[0], selectorLife = lifetime313(selector);
        const panels = Probe.visibleDialogs(window).filter(panel => panel.objectName !== "preferences"
            && typeof panel.standardButton === "function" && panel.standardButton(Dialog.Open) !== null);
        compare(panels.length, 1, "GUI392: same genuine FolderDialog owns exactly one current standard Open panel");
        const panel = panels[0], panelLife = lifetime313(panel);
        const host = panel.contentItem.Window.window;
        verify(host !== null && panel.header !== null, "PICKER563: SAME original panel exposes its actual content Window and header");
        const hostLife = lifetime313(host), header = panel.header, headerLife = lifetime313(header);
        const breadcrumbs = Ui.itemsWithProperty(header, "textField").filter(control => control.dialog === panel && control.textField !== null);
        compare(breadcrumbs.length, 1, "PICKER563: original header owns exactly one breadcrumb for SAME panel");
        const breadcrumb = breadcrumbs[0], breadcrumbLife = lifetime313(breadcrumb);
        const originalField = breadcrumb.textField, fieldLife = lifetime313(originalField);
        tryVerify(() => alive313(selectorLife) && alive313(panelLife) && alive313(hostLife)
            && alive313(headerLife) && alive313(breadcrumbLife) && alive313(fieldLife)
            && selector.visible && panel.opened && host.visible && host.active
            && panel.contentItem.Window.window === host && header.Window.window === host
            && breadcrumb.dialog === panel && breadcrumb.textField === originalField,
            2000, "PICKER563: exact original picker is opened in its active content-host Window before native shortcut/action");
        let accepted = 0, rejected = 0;
        function onAccepted() { ++accepted; }
        function onRejected() { ++rejected; }
        selector.accepted.connect(onAccepted); selector.rejected.connect(onRejected);
        try {
            if (cancel) gui392_button(panel.standardButton(Dialog.Cancel), panel, false, host);
            else {
                keyClick(Qt.Key_L, Qt.ControlModifier);
                const field = alive313(hostLife) ? host.activeFocusItem : null;
                const sameHeader = field !== null && alive313(headerLife) && gui393_under(field, header);
                console.log("PICKER563_RECEIVER", JSON.stringify({sameMainWindow:host === window,
                    selectorAlive:alive313(selectorLife), panelAlive:alive313(panelLife), hostAlive:alive313(hostLife),
                    headerAlive:alive313(headerLife), breadcrumbAlive:alive313(breadcrumbLife), fieldAlive:alive313(fieldLife),
                    hostActive:alive313(hostLife) ? host.active : null, panelOpened:alive313(panelLife) ? panel.opened : null,
                    focusedPresent:field !== null, focusedIsOriginalBreadcrumb:field === originalField,
                    focusedInOriginalHeader:sameHeader, activeFocus:field !== null ? field.activeFocus : null,
                    rendered:field !== null ? Ui.rendered(field) : null, exposed:field !== null ? Ui.exposed(field) : null}));
                verify(alive313(selectorLife) && alive313(panelLife) && alive313(hostLife)
                    && field !== null && field === originalField && alive313(fieldLife)
                    && field.activeFocus && Ui.rendered(field) && Ui.exposed(field),
                    "GUI392: genuine Ctrl+L focuses original exposed native folder breadcrumb");
                verify(sameHeader && alive313(panelLife) && alive313(headerLife) && alive313(breadcrumbLife)
                    && breadcrumb.dialog === panel && breadcrumb.textField === field,
                    "GUI392: exact focused breadcrumb belongs to SAME original folder panel header");
                gui563_pickerExposed(field, panel, host);
                const path = String(Probe.referenceUrl(relative)).replace(/^file:\/\//, "");
                visible185_type(decodeURIComponent(path));
                compare(field.text, decodeURIComponent(path), "GUI392: actual focused folder spelling equals independently owned full path");
                keyClick(Qt.Key_Return);
                verify(alive313(panelLife) && panel.visible && alive313(selectorLife),
                    "GUI392: directory navigation retains same live original chooser before actual Open");
                gui392_button(panel.standardButton(Dialog.Open), panel, false, host);
            }
            tryVerify(() => !selector.visible, 2000, "GUI392: actual original chooser closes from genuine Cancel/Open");
            compare(accepted, cancel ? 0 : 1, "GUI392: exact original selector has one expected acceptance, never synthesized");
            compare(rejected, cancel ? 1 : 0, "GUI392: exact original selector has one expected rejection");
        } finally {
            disconnect313(selectorLife, selector, "accepted", onAccepted);
            disconnect313(selectorLife, selector, "rejected", onRejected);
        }
        if (cancel) compare(JSON.stringify(gui392_sources()), JSON.stringify(before),
            "GUI392: actual folder Cancel changes no source descriptor/configuration");
    }
    function test_gui392_preferences_real_sources() {
        const before = gui392_setup(), preferences = gui392_preferences();
        const original = gui392_sources();
        compare(original.length, 1, "GUI392 SETUP: isolated original source configuration has only builtin");
        compare(original[0].id, "builtin", "GUI392: builtin has public fixed identity");
        verify(original[0].builtin && original[0].enabled, "GUI392: builtin is initially enabled");
        const label = gui392_sourceControl("preferences.ai.source.label.builtin");
        compare(label.text, "EasyDiffraction", "GUI392: builtin label exposes ONLY product name, never repository path");
        const remove = gui392_sourceControl("preferences.ai.source.remove.builtin");
        verify(!remove.enabled && remove.ToolTip.text === "The built-in source cannot be removed",
            "GUI392: original builtin delete is physically unavailable with truthful tooltip");
        const toggle = gui392_sourceControl("preferences.ai.source.enabled.builtin");
        verify(toggle.Accessible.checkable && toggle.Accessible.checked
            && toggle.Accessible.name === "Disable this skill source", "GUI392: builtin uses actual accessible table toggle policy");
        import265_click(toggle.objectName);
        compare(gui392_sources()[0].enabled, false, "GUI392: genuine builtin toggle disables actual source");
        compare(gui392_json(JSON.parse(assistant.contextPreview).skills).length, 0,
            "GUI392: all-disabled configuration honestly discloses no skills");
        gui392_folder("skills/collection", true);
        gui392_folder("skills/collection", false);
        let rows = gui392_sources();
        compare(rows.length, 2, "GUI392: one real folder selection admits exactly one collection source");
        const locals = rows.filter(row => !row.builtin);
        compare(locals.length, 1, "GUI392: collection is one actual source row, not guessed per-package rows");
        const local = locals[0];
        verify(typeof local.id === "string" && local.id.length > 0 && local.id !== "builtin" && local.enabled,
            "GUI392: local identity is genuine nonempty opaque app-issued source ID");
        const path = decodeURIComponent(String(Probe.referenceUrl("skills/collection")).replace(/^file:\/\//, ""));
        compare(local.path, path, "GUI392: local model path is exact genuinely selected owned collection");
        const localLabel = gui392_sourceControl("preferences.ai.source.label." + local.id);
        compare(localLabel.text, path, "GUI392: local row labels actual path rather than invented name");
        compare(localLabel.ToolTip.text, path, "GUI392: complete local path remains accessible in tooltip");
        const disclosed = JSON.parse(assistant.contextPreview);
        const serialized = JSON.stringify(disclosed.skills);
        verify(serialized.includes("GUI392 independent alpha guidance") && serialized.includes("GUI392 independent beta guidance"),
            "GUI392: enabled collection contributes BOTH independently authored complete guidance packages");
        capture("gui392-preferences-local-source");
        import265_click("preferences.ai.source.enabled." + local.id);
        compare(gui392_sources().filter(row => row.id === local.id)[0].enabled, false,
            "GUI392: original opaque-ID table toggle actually disables local source");
        compare(JSON.parse(assistant.contextPreview).skills.length, 0,
            "GUI392: disabled local plus disabled builtin contribute no instructions");
        import265_click("preferences.ai.source.enabled." + local.id);
        compare(gui392_sources().filter(row => row.id === local.id)[0].id, local.id,
            "GUI392: toggling retains exact opaque source identity");
        gui392_button(preferences.standardButton(Dialog.Ok), preferences);
        gui393_sourceApproval();
        const account = JSON.stringify(Probe.rows(assistant.models));
        if (assistant.contextConsentRequired) assistant.signIn();
        report187_ready("gui392-local-source-disclosed", true);
        Ui.click(this, Probe, window, "assistant.showActions");
        const eye = item("assistant.showActions");
        verify(eye.checked && eye.Accessible.checkable && eye.Accessible.checked
            && eye.Accessible.name === "Show actions" && eye.ToolTip.text === "Show actions" && eye.fontIcon === "eye",
            "GUI392: original eye action is genuinely checkable/named and presentation only");
        mouseMove(window.contentItem, 0, 0); rendered();
        const icons = gui392_labels(eye);
        tryVerify(() => icons.some(label => Qt.colorEqual(label.color, EaStyle.Colors.themeAccent)), 2000,
            "GUI392: checked original eye has an actual painted accent state");
        Ui.click(this, Probe, window, "assistant.composer"); visible185_type("GUI392 original held source request");
        Ui.click(this, Probe, window, "assistant.send");
        tryVerify(() => assistant.canCancel, 2000, "GUI392: original actual transport input is genuinely pending before busy checks");
        verify(!eye.enabled, "GUI392: original Show actions eye is disabled during real original work");
        const preferencesBusy = gui392_preferences();
        for (const id of ["builtin", local.id]) for (const action of ["enabled", "remove"]) {
            const button = gui392_sourceControl("preferences.ai.source." + action + "." + id);
            verify(!button.enabled, "GUI392: genuine active work disables original source row actions");
        }
        verify(!item("preferences.ai.sources.add").enabled, "GUI392: genuine active work disables source Add");
        gui392_button(preferencesBusy.standardButton(Dialog.Ok), preferencesBusy);
        assistant.refreshUsage(); // Existing original optional-read barrier releases exact received input.
        tryVerify(() => !assistant.canCancel && Probe.rows(assistant.messages).some(row => row.kind === "assistant"
            && row.status === "completed" && row.text === "Original fileauth reply 1"), 2000,
            "GUI392: original held input settles with exact real peer reply, not idle alone");
        const selected = JSON.stringify(Probe.rows(assistant.selectedFiles));
        const usage = JSON.stringify(gui392_usageData());
        Ui.click(this, Probe, window, "assistant.clear");
        tryCompare(assistant.messages, "count", 0, 2000, "GUI392: actual eraser Clear removes original conversation");
        verify(assistant.connected, "GUI392: Clear retains connected account");
        compare(JSON.stringify(Probe.rows(assistant.models)), account, "GUI392: Clear retains original model catalog");
        compare(JSON.stringify(Probe.rows(assistant.selectedFiles)), selected, "GUI392: Clear retains original selected-source authority semantics");
        compare(JSON.stringify(gui392_usageData()), usage, "GUI392: Clear retains current account-owned allowance");
        const preferencesAgain = gui392_preferences();
        import265_click("preferences.ai.source.remove." + local.id);
        compare(gui392_sources().length, 1, "GUI392: genuine local Remove leaves only protected builtin");
        compare(gui392_sources()[0].id, "builtin", "GUI392: removing local cannot remove builtin");
        verify(!JSON.stringify(JSON.parse(assistant.contextPreview).skills).includes("GUI392 independent"),
            "GUI392: removed local source contributes no next disclosed instructions");
        import265_click("preferences.ai.source.enabled.builtin");
        gui392_button(preferencesAgain.standardButton(Dialog.Ok), preferencesAgain);
        console.log("GUI392_SOURCE", JSON.stringify({id: local.id, path: local.path, selected: gui392_json(Probe.rows(assistant.selectedFiles))}));
        gui392_unchanged(before);
    }
    function test_gui392_source_refusals_data() {
        return ["missing-skill", "malformed", "duplicate-names", "linked-skill", "duplicate-source"].map(tag => ({tag: tag}));
    }
    function test_gui392_source_refusals(data) {
        const before = gui392_setup(), preferences = gui392_preferences();
        if (["duplicate-source", "duplicate-names"].includes(data.tag)) {
            const initialCount = gui392_sources().length;
            gui392_folder("skills/collection", false);
            compare(gui392_sources().length, initialCount + 1,
                "GUI393: original duplicate refusal starts from genuinely admitted healthy name-matched collection");
            compare(assistant.skillSourceError, "", "GUI393: healthy duplicate-control collection has no masked source error");
        }
        const original = JSON.stringify(gui392_sources());
        gui392_folder(data.tag === "duplicate-source" ? "skills/collection" : "skills/" + data.tag, false);
        compare(JSON.stringify(gui392_sources()), original,
            "GUI392: actual invalid/missing/duplicate/link source selection refuses before any configuration write");
        verify(typeof assistant.skillSourceError === "string" && assistant.skillSourceError.length > 0,
            "GUI392: exact actual source refusal reports explicit original error");
        gui392_button(preferences.standardButton(Dialog.Ok), preferences);
        gui392_unchanged(before);
    }
    // GUI393: additive PUBLIC333-v3, never a private producer implementation oracle.
    function gui393_under(control, root) {
        for (let parent = control; parent; parent = parent.parent) if (parent === root) return true;
        return false;
    }
    function gui393_control(choice, name) {
        const matches = Ui.itemsWithProperty(choice.contentItem, "objectName").filter(control =>
            control.objectName === name && Ui.rendered(control));
        compare(matches.length, 1, "GUI393: exact original chooser owns one current radio/row/label: " + name);
        ux356_fullyExposed(matches[0]);
        return matches[0];
    }
    function gui393_effortName(token) {
        return token === "" ? "assistant.choice.effort.default" : "assistant.choice.effort.value." + token;
    }
    function gui393_layout(choice, expectedEfforts) {
        const models = gui392_json(Probe.rows(assistant.models));
        compare(JSON.stringify(models.map(row => [row.id, row.displayName, row.available])), JSON.stringify([
            ["gpt-6.1-sol", "Original primary model", true],
            ["gpt-6-luna", "Original unavailable model", false],
            ["gpt-6-sol", "Original alternate model", true]
        ]), "GUI393: actual model rows equal complete independent provider catalogue in source order");
        const modelTable = gui393_control(choice, "assistant.choice.models");
        const effortTable = gui393_control(choice, "assistant.choice.efforts");
        compare(modelTable.sourceModel, assistant.models, "GUI393: original model table uses actual VM rows");
        verify(rect(modelTable)[0] + rect(modelTable)[2] <= rect(effortTable)[0] + 0.5
            && Math.abs(rect(modelTable)[1] - rect(effortTable)[1]) < 0.5,
            "GUI398: full natural model and effort tables are SIDE BY SIDE on the same native dialog row");
        const modelRadios = models.map(row => gui393_control(choice, "assistant.choice.model." + row.id));
        const effortRadios = expectedEfforts.map(token => gui393_control(choice, gui393_effortName(token)));
        const all = Ui.itemsWithProperty(choice.contentItem, "objectName");
        compare(all.filter(control => /^assistant\.choice\.model\.[^.]+/.test(control.objectName)
            && control.objectName !== "assistant.choice.models" && typeof control.checked === "boolean").length,
            modelRadios.length, "GUI393: model table offers no extra invented radio choice");
        compare(all.filter(control => /^assistant\.choice\.effort\./.test(control.objectName)
            && typeof control.checked === "boolean").length, effortRadios.length,
            "GUI393: effort table offers ONLY original default plus actual dependent choices");
        compare(modelRadios.filter(control => control.checked).length, 1,
            "GUI393: models are genuine single selection");
        compare(effortRadios.filter(control => control.checked).length, 1,
            "GUI393: efforts are genuine single selection");
        const radioRects = [], labelRects = [];
        for (let index = 0; index < models.length; ++index) {
            const row = models[index], radio = modelRadios[index];
            compare(radio.checked, row.id === assistant.selectedModel, "GUI393: checked model is exact actual selected ID");
            compare(radio.enabled, row.available, "GUI394: both healthy model controls and disabled middle match independent offered availability");
            const label = gui393_control(choice, "assistant.choice.model.label." + row.id);
            compare(label.text, row.displayName, "GUI393: model label is exact independent provider text");
            const originalRow = gui393_control(choice, "assistant.choice.model.row." + row.id);
            verify(gui393_under(originalRow, modelTable) && gui393_under(radio, originalRow) && gui393_under(label, originalRow),
                "GUI393: SAME original model row/table owns its exact radio and label controls");
            verify(!label.truncated && label.contentWidth <= label.width + 0.5,
                "GUI398: normal viewport shows full natural offered label without elision/scroll substitute");
            const rr = rect(radio), lr = rect(label), tableX = rect(modelTable)[0];
            radioRects.push([rr[0] - tableX, rr[2]]); labelRects.push([lr[0] - tableX, lr[2]]);
        }
        const labels = {"": "Auto", "medium": "Medium", "high": "High"};
        for (let index = 0; index < expectedEfforts.length; ++index) {
            const token = expectedEfforts[index], radio = effortRadios[index];
            compare(radio.checked, token === assistant.selectedEffort, "GUI393: checked effort is exact actual token");
            const label = gui393_control(choice, gui393_effortName(token) + ".label");
            compare(label.text, labels[token], "GUI393: default and known effort labels use independent original meanings");
            const originalRow = gui393_control(choice, gui393_effortName(token) + ".row");
            verify(gui393_under(originalRow, effortTable) && gui393_under(radio, originalRow) && gui393_under(label, originalRow),
                "GUI393: SAME original dependent effort row/table owns its exact radio and label");
            verify(!label.truncated && label.contentWidth <= label.width + 0.5,
                "GUI398: normal viewport shows full natural offered label without elision/scroll substitute");
            const rr = rect(radio), lr = rect(label), tableX = rect(effortTable)[0];
            radioRects.push([rr[0] - tableX, rr[2]]); labelRects.push([lr[0] - tableX, lr[2]]);
        }
        for (const bounds of radioRects) verify(Math.abs(bounds[0] - radioRects[0][0]) < 0.5
            && Math.abs(bounds[1] - radioRects[0][1]) < 0.5,
            "GUI393: actual radio column offsets/widths align relative to BOTH side-by-side tables");
        for (const bounds of labelRects) verify(Math.abs(bounds[0] - labelRects[0][0]) < 0.5
            && Math.abs(bounds[1] - labelRects[0][1]) < 0.5,
            "GUI393: actual label column offsets/widths align relative to BOTH side-by-side tables");
        gui399_tableExtent(choice, modelTable, models.map(row => gui393_control(choice, "assistant.choice.model.row." + row.id)));
        gui399_tableExtent(choice, effortTable, expectedEfforts.map(token => gui393_control(choice, gui393_effortName(token) + ".row")));
        gui400_chooserSpacing(choice, [modelTable, effortTable]);
        ux356_fullyExposed(choice.contentItem);
        return {models: models, modelRadios: modelRadios, effortRadios: effortRadios,
            modelTable: modelTable, effortTable: effortTable};
    }
    function gui393_open() {
        const pill = item("assistant.modelEffort");
        verify(pill.enabled, "GUI393: original combined pill is available only at genuine ready state");
        Ui.click(this, Probe, window, "assistant.modelEffort");
        const choice = gui392_dialog("assistant.modelEffort.popup");
        const actual = gui393_control(choice, "assistant.choice.model." + assistant.selectedModel);
        compare(window.activeFocusItem, actual, "GUI393: actual popup opening focuses selected available model radio");
        verify(!Probe.objectsWithProperty(window, "objectName").some(control =>
            ["assistant.model", "assistant.effort"].includes(control.objectName)),
            "GUI393: superseded combo controls are absent, including hidden compatibility controls");
        return choice;
    }
    function gui393_pill(modelName, effortLabel) {
        const pill = item("assistant.modelEffort");
        const labels = gui392_labels(pill);
        const model = labels.filter(label => label.text === modelName);
        const effort = labels.filter(label => label.text === effortLabel);
        compare(model.length, 1, "GUI393: one painted pill model label shows actual chosen model");
        compare(effort.length, 1, "GUI393: one painted pill effort label shows actual chosen effort");
        verify(pill.enabled && effort[0].enabled, "GUI393: muted effort remains semantically enabled");
        verify(pill.Accessible.name.includes(modelName) && pill.Accessible.name.includes(effortLabel)
            && pill.ToolTip.text.includes(modelName) && pill.ToolTip.text.includes(effortLabel),
            "GUI393: accessible name and tooltip disclose BOTH exact selected values");
        const background = pill.background;
        verify(background && background.visible && background.color.a > 0,
            "GUI393: real pill has painted light rounded background");
        verify(background.radius >= Math.min(background.width, background.height) / 2 - 0.5,
            "GUI393: original combined control is a rounded pill");
        function contrast(label) {
            const alpha = label.color.a * label.opacity;
            return Math.pow((label.color.r - background.color.r) * alpha, 2)
                + Math.pow((label.color.g - background.color.g) * alpha, 2)
                + Math.pow((label.color.b - background.color.b) * alpha, 2);
        }
        if (pill.hovered || pill.down || pill.visualFocus) {
            tryVerify(() => [model[0], effort[0]].every(label => Qt.colorEqual(label.color, EaStyle.Colors.themeAccent)), 2000,
                "GUI494: actual active pill model AND effort use owner-requested native accent ink");
        } else {
            tryVerify(() => contrast(effort[0]) < contrast(model[0]), 2000,
                "GUI393: resting effort ink is less pronounced against SAME persistent neutral background than model ink");
        }
        gui398FontMetrics.font = model[0].font;
        const modelBounds = rect(model[0]), effortBounds = rect(effort[0]);
        verify(Math.abs(effortBounds[0] - modelBounds[0] - modelBounds[2]
            - gui398FontMetrics.advanceWidth(" ")) < 0.5,
            "GUI398: actual model and muted effort have exactly ONE natural text-space, not widened layout gap");
        gui398_noBlueOutline(pill);
        return pill;
    }
    function gui393_roundFooter() {
        const send = item("assistant.send"), editor = item("assistant.composer");
        const revisions = Probe.objectsWithProperty(window, "textRevision").filter(object => object.firstFocusItem === editor);
        const testWindow = this.Window.window, focus = window.activeFocusItem;
        console.log("GUI497_SEND_BEFORE", JSON.stringify({
            send: String(send), sendEnabled: send.enabled, sendVisible: send.visible,
            background: String(send.background), backgroundAlpha: send.background ? send.background.color.a : null,
            controller: String(assistant), sameController: Session.assistant === assistant,
            state: assistant.state, connected: assistant.connected, canCancel: assistant.canCancel,
            editor: String(editor), editorLength: editor.text.length, revisionOwners: revisions.length,
            revision: revisions.length === 1 ? revisions[0].textRevision : null,
            composing: editor.inputMethodComposing, editorFocus: editor.focus, editorActiveFocus: editor.activeFocus,
            editorEnabled: editor.enabled, editorVisible: editor.visible,
            main: String(window), mainActive: window.active, mainVisible: window.visible,
            editorWindow: String(editor.Window.window), editorInMain: editor.Window.window === window,
            testWindow: String(testWindow), testWindowActive: testWindow ? testWindow.active : null,
            mainFocus: String(focus), mainFocusName: focus ? String(focus.objectName).slice(0, 80) : "",
            focusIsEditor: focus === editor,
            testFocus: testWindow ? String(testWindow.activeFocusItem) : "null"}));
        verify(send.enabled, "GUI497: independent real typed draft enables original Send");
        verify(send.visible, "GUI497: original Send is visible at the same pre-input interval");
        verify(send.background.color.a > 0, "GUI497: original Send retains its actually painted strong background");
        for (const name of ["assistant.files.add", "assistant.showActions",
                            "assistant.previousUserMessage", "assistant.nextUserMessage"]) {
            const control = item(name), background = control.background;
            ux356_fullyExposed(control);
            verify(background && background.visible && background.color.a > 0
                && Math.abs(background.width - background.height) < 0.5
                && background.radius >= background.height / 2 - 0.5,
                "GUI393: actual original footer action has circular painted background: " + name);
            gui398_noBlueOutline(control);
            const point = Ui.clickPoint(control);
            mouseMove(control, point.x, point.y); rendered();
            gui398_noBlueOutline(control);
            mouseMove(window.contentItem, 0, 0); rendered();
            gui398_noBlueOutline(control);
            tryVerify(() => !Qt.colorEqual(background.color, send.background.color), 2000,
                "GUI494: persistent neutral footer treatment remains distinct from stronger original Send fill: " + name);
        }
            const previous = rect(item("assistant.previousUserMessage")), next = rect(item("assistant.nextUserMessage")), submit = rect(send);
        const firstGap = next[0] - previous[0] - previous[2], secondGap = submit[0] - next[0] - next[2];
        verify(firstGap >= 0 && Math.abs(firstGap - secondGap) < 0.5,
            "GUI398: actual Previous/Next/Send horizontal gaps are equal in SAME original footer");
        gui398_noBlueOutline(send);
    }
    function gui393_sourceApproval() {
        Ui.click(this, Probe, window, "assistant.connection");
        const dialog = ux356_dialog();
        tryCompare(dialog, "opened", true, 2000, "GUI393: source approval witness belongs to actual original sign-in dialog");
        const original = gui392_json(dialog.disclosedContext);
        compare(JSON.stringify(original), JSON.stringify(JSON.parse(assistant.contextPreview)),
            "GUI393: actual original displayed disclosure equals exact current context before approval");
        verify(Array.isArray(original.skills) && original.skills.length === 2
            && original.skills.every(row => typeof row.id === "string" && row.id.length > 0 && row.id.length <= 1024
                && typeof row.sha256 === "string" && /^[0-9a-f]{64}$/.test(row.sha256)
                && typeof row.content === "string" && row.content.length <= 4096),
            "GUI393: original approval receipt contains only two bounded actual independent fixture guidance entries");
        console.log("GUI393_APPROVED_SOURCE", JSON.stringify({skills: original.skills.map(row =>
            ({id: row.id, sha256: row.sha256, content: row.content}))}));
        gui392_button(dialog.standardButton(Dialog.Ok), dialog);
        report187_ready("gui393-original-approved-source", false);
    }
    function test_gui393_original_combined_chooser_data() {
        return ["pointer", "space", "return", "enter", "retirement"].map(tag => ({tag: tag}));
    }
    function test_gui393_original_combined_chooser(data) {
        const before = gui392_setup(); gui392_signIn();
        compare(assistant.selectedModel, "gpt-6.1-sol", "GUI393 SETUP: independently declared provider-default original model is selected");
        compare(assistant.selectedEffort, "", "GUI393 SETUP: original empty token means provider Auto");
        compare(JSON.stringify(gui392_json(assistant.availableEfforts)), JSON.stringify(["medium", "high"]),
            "GUI393 SETUP: actual initial efforts equal independent original catalogue");
        const modelCatalog = JSON.stringify(gui392_json(Probe.rows(assistant.models)));
        const selected = JSON.stringify(gui392_json(Probe.rows(assistant.selectedFiles)));
        const pill = gui393_pill("Original primary model", "Auto"), pillLife = lifetime313(pill);
        let choice = gui393_open();
        gui393_layout(choice, ["", "medium", "high"]);
        capture("gui393-original-two-table-choice-" + data.tag);
        if (data.tag === "retirement") {
            const originalChoice = lifetime313(choice);
            assistant.signOut(); // Genuine existing public account retirement, no fabricated state/signal.
            tryVerify(() => !assistant.connected && (!alive313(originalChoice) || !choice.visible), 2000,
                "GUI393: actual account retirement closes exact old chooser before any replacement authority");
            verify(!Ui.rendered(pill) || !pill.enabled, "GUI393: old pill cannot authorize signed-out model changes");
            gui392_unchanged(before);
            return;
        }
        if (["space", "return", "enter"].includes(data.tag)) {
            keyClick(Qt.Key_Escape);
            tryCompare(choice, "visible", false, 2000, "GUI393: real Escape closes original chooser");
            compare(window.activeFocusItem, pill, "GUI393: actual Escape returns focus to SAME enabled original pill");
            const opening = choice, openingLife = lifetime313(choice), openingOwner = Session.project;
            let openings = 0;
            function opened394() {
                verify(alive313(openingLife) && Session.project === openingOwner && Session.assistant === assistant,
                    "GUI394: opening receipt belongs to same original receiver/owner after actual key");
                if (opening.opened) ++openings;
            }
            opening.openedChanged.connect(opened394);
            try {
                gui398_noBlueOutline(pill);
                keyClick(data.tag === "space" ? Qt.Key_Space : data.tag === "enter" ? Qt.Key_Enter : Qt.Key_Return);
                choice = gui392_dialog("assistant.modelEffort.popup");
                compare(choice, opening, "GUI394: genuine key opens SAME original popup, no replacement blessing");
                compare(openings, 1, "GUI394: ONE actual Space/Return/Enter press-release opens original popup exactly once");
            } finally { disconnect313(openingLife, opening, "openedChanged", opened394); }
            let layout = gui393_layout(choice, ["", "medium", "high"]);
            if (data.tag === "space") {
                gui394_sameCurrent(choice, layout.modelRadios[0], "space", false);
                // Original bounded real keyboard traversal; no forceFocus or state setter.
                const autoRadio = gui393_control(choice, gui393_effortName(""));
                for (let step = 0; step < 32 && !autoRadio.activeFocus; ++step) keyClick(Qt.Key_Tab);
                compare(window.activeFocusItem, autoRadio, "GUI394: genuine traversal reaches actual current Auto radio");
                gui394_sameCurrent(choice, autoRadio, "space", true);
                choice = gui393_open(); layout = gui393_layout(choice, ["", "medium", "high"]);
            }
            const radios = [layout.modelRadios[0], layout.modelRadios[2]].concat(layout.effortRadios);
            compare(window.activeFocusItem, radios[0], "GUI393: genuine Space/Return opening focuses original selected model");
            for (let index = 1; index < radios.length; ++index) {
                keyClick(Qt.Key_Tab);
                compare(window.activeFocusItem, radios[index], "GUI393: genuine Tab traverses models then efforts without stale combo neighbor");
            }
            if (data.tag === "space") {
                for (let index = radios.length - 2; index >= 0; --index) {
                    keyClick(Qt.Key_Tab, Qt.ShiftModifier);
                    compare(window.activeFocusItem, radios[index],
                        "GUI394: genuine Backtab also skips unavailable middle and preserves enabled-table order");
                }
                for (let index = 1; index < radios.length; ++index) {
                    keyClick(Qt.Key_Tab);
                    compare(window.activeFocusItem, radios[index], "GUI394: same original forward traversal remains usable after Backtab");
                }
            }
            keyClick(Qt.Key_Space);
            tryCompare(assistant, "selectedEffort", "high", 2000, "GUI393: actual final focused High radio changes original effort");
            tryCompare(choice, "visible", false, 2000, "GUI393: actual effort selection closes chooser");
            compare(window.activeFocusItem, pill, "GUI393: actual effort choice returns focus to SAME pill");
            gui393_pill("Original primary model", "High");
        } else {
            let currentLayout = gui393_layout(choice, ["", "medium", "high"]);
            gui394_unavailable(choice, currentLayout.modelRadios[1], gui393_control(choice, "assistant.choice.model.label.gpt-6-luna"));
            gui394_sameCurrent(choice, currentLayout.modelRadios[0], "mouse", false);
            gui393_layout(choice, ["", "medium", "high"]);
            gui394_sameCurrent(choice, gui393_control(choice, gui393_effortName("")), "mouse", true);
            choice = gui393_open();
            const high = gui393_control(choice, gui393_effortName("high"));
            compare(import265_click(high.objectName), high, "GUI393: genuine original high-radio click reaches exact live control");
            tryCompare(assistant, "selectedEffort", "high", 2000, "GUI393: genuine original High selection is non-noop");
            tryCompare(choice, "visible", false, 2000, "GUI393: selected High closes actual chooser");
            choice = gui393_open();
            const beta = gui393_control(choice, "assistant.choice.model.label.gpt-6-sol");
            compare(import265_click(beta.objectName), beta, "GUI393: original model LABEL is a genuine activation entrance");
            tryCompare(assistant, "selectedModel", "gpt-6-sol", 2000, "GUI393: real model label changes selected model without an index guess");
            verify(choice.visible && choice.opened, "GUI393: model choice keeps SAME popup open for dependent effort choice");
            compare(assistant.selectedEffort, "", "GUI393: unsupported old High falls back to original provider-default token");
            compare(JSON.stringify(gui392_json(assistant.availableEfforts)), JSON.stringify(["medium"]),
                "GUI393: model choice replaces dependent options with actual sole supported effort");
            const dependent = gui393_layout(choice, ["", "medium"]);
            verify(gui393_under(window.activeFocusItem, dependent.effortTable),
                "GUI393: model selection genuinely moves focus into original effort table");
            const medium = gui393_control(choice, gui393_effortName("medium") + ".label");
            compare(import265_click(medium.objectName), medium, "GUI393: actual effort LABEL also selects through genuine pointer input");
            tryCompare(assistant, "selectedEffort", "medium", 2000, "GUI393: exact original Medium is selected");
            tryCompare(choice, "visible", false, 2000, "GUI393: genuine effort label closes original popup");
            compare(window.activeFocusItem, pill, "GUI393: label activation restores SAME actual pill focus");
            gui393_pill("Original alternate model", "Medium");
            if (assistant.contextConsentRequired) assistant.signIn();
            report187_ready("gui393-current-choice-disclosed", true);
            Ui.click(this, Probe, window, "assistant.composer"); visible185_type("GUI393 actual chosen model request");
            gui393_roundFooter();
            Ui.click(this, Probe, window, "assistant.send");
            tryVerify(() => assistant.canCancel, 2000, "GUI393: actual original user request is genuinely held before busy check");
            verify(alive313(pillLife) && !pill.enabled && !choice.visible,
                "GUI393: original live busy state disables pill and retains no active chooser");
            const stop = item("assistant.stop"), eye = item("assistant.showActions");
            tryVerify(() => stop.visible && stop.enabled && stop.background.color.a > 0
                && !Qt.colorEqual(stop.background.color, eye.background.color), 2000,
                "GUI393: original busy Stop retains stronger treatment than light footer actions");
            assistant.refreshUsage(); // Same original received-input release door as GUI392.
            tryVerify(() => !assistant.canCancel && Probe.rows(assistant.messages).some(row => row.kind === "assistant"
                && row.status === "completed" && row.text === "Original offline reply"), 2000,
                "GUI393: original selected-model request really completes before re-enabling choices");
            gui398_noBlueOutline(pill);
            verify(pill.enabled, "GUI393: genuine completed original work re-enables original combined chooser");
            compare(assistant.selectedModel, "gpt-6-sol", "GUI393: actual request retains independently chosen model");
            compare(assistant.selectedEffort, "medium", "GUI393: actual request retains independently chosen effort");
        }
        compare(JSON.stringify(gui392_json(Probe.rows(assistant.models))), modelCatalog,
            "GUI393: ordinary choices preserve actual original catalogue/account");
        compare(JSON.stringify(gui392_json(Probe.rows(assistant.selectedFiles))), selected,
            "GUI393: model/effort presentation grants no selected file authority");
        gui392_unchanged(before);
        console.log("GUI393_CHOICE", JSON.stringify({tag: data.tag, model: assistant.selectedModel, effort: assistant.selectedEffort}));
    }
    function test_gui393_first_delivery_eye_clear() {
        const before = gui392_setup(); gui392_signIn(true);
        compare(assistant.contextApprovalBlocked, false,
            "CONSENT464 SETUP: original healthy native controller has no retained outcome fence");
        const account = JSON.stringify(gui392_json(Probe.rows(assistant.models)));
        const token = assistant.beginFileSelection();
        verify(token.length > 0 && assistant.addSelectedFiles(token,
            [Probe.referenceUrl("project/structures/lbco.edi")]),
            "GUI393 SETUP: one independently owned original source is genuinely admitted before Clear");
        tryCompare(assistant.selectedFiles, "count", 1, 2000,
            "GUI393 SETUP: actual canonical source grant exists, not an empty Clear assertion");
        const originalFile = gui392_json(Probe.rows(assistant.selectedFiles))[0];
        const canonicalFile405 = {id:originalFile.id, name:originalFile.name, bytes:originalFile.bytes,
            textReadable:originalFile.textReadable, format:originalFile.format};
        verify(originalFile.id.length > 0 && originalFile.pending,
            "GUI393 SETUP: real canonical pending ID is app issued");
        verify(assistant.connected && assistant.contextConsentRequired,
            "GUI404 SETUP: changed attachment scope REALLY requires approval, never preapproved via signIn");
        report187_ready("gui404-attachment-needs-approval", false);
        const eye = item("assistant.showActions");
        compare(eye.checked, false, "GUI393 SETUP: original isolated presentation starts with actions off");
        Ui.click(this, Probe, window, "assistant.showActions");
        console.log("GUI486_EYE_SNAPSHOT", JSON.stringify({
            receiver: String(eye), controller: String(assistant), project: String(before.owner),
            sameController: Session.assistant === assistant, sameProject: Session.project === before.owner,
            originalOwnerAlive: alive313(before.life), controllerShowActions: assistant.showActions,
            window: String(window), receiverWindow: String(eye.Window.window), sameWindow: eye.Window.window === window,
            windowActive: window.active, windowVisible: window.visible,
            receiverVisible: eye.visible, receiverEnabled: eye.enabled, receiverRect: rect(eye),
            fields: [["checked", eye.checked], ["Accessible.checkable", eye.Accessible.checkable],
                ["Accessible.checked", eye.Accessible.checked], ["Accessible.name", eye.Accessible.name],
                ["ToolTip.text", eye.ToolTip.text], ["fontIcon", eye.fontIcon]].map(pair => ({
                    property: pair[0], type: typeof pair[1], value: typeof pair[1] === "undefined" ? null : pair[1]}))
        }));
        capture("gui486-original-eye-before-assertions");
        verify(eye.checked, "GUI486: original clicked eye is checked");
        verify(eye.Accessible.checkable, "GUI486: original eye accessibility remains checkable");
        verify(eye.Accessible.checked, "GUI486: original eye accessibility reports checked");
        verify(eye.Accessible.name === "Show actions", "GUI486: original eye accessible name is exact");
        verify(eye.ToolTip.text === "Show actions", "GUI486: original eye tooltip is exact");
        verify(eye.fontIcon === "eye", "GUI486: original eye glyph is exact");
        mouseMove(window.contentItem, 0, 0); rendered();
        tryVerify(() => gui392_labels(eye).some(label => Qt.colorEqual(label.color, EaStyle.Colors.themeAccent)), 2000,
            "GUI393: original checked eye actually paints accent ink");
        gui398_noBlueOutline(eye);
        const editor = item("assistant.composer"), send = item("assistant.send");
        const composers = Probe.objectsWithProperty(window, "textRevision").filter(object => object.firstFocusItem === editor);
        compare(composers.length, 1, "GUI404: exact original native editor has ONE actual revision owner");
        const composer = composers[0], dialog = ux356_dialog(), dialogLife = lifetime313(dialog), sendLife = lifetime313(send);
        const selectedBefore = JSON.stringify(gui392_json(Probe.rows(assistant.selectedFiles)));
        const historyBefore = JSON.stringify(gui392_json(Probe.rows(assistant.messages)));
        const oldIds = new Set(Probe.rows(assistant.messages).map(row => row.id));
        const originalText = "GUI393 first delivery original Clear request";
        let sendClicks = 0, opens = 0, cancelClicks = 0, approvalClicks = 0;
        let cancel = null, approve = null, cancelLife = null, approveLife = null;
        function current() { verify(alive313(before.life) && Session.project === before.owner && Session.assistant === assistant,
            "GUI404: original native input/approval retains SAME live project/controller"); }
        function submitted() { current(); ++sendClicks; }
        function opened() { current(); verify(alive313(dialogLife), "GUI404: original dialog alive at actual opened signal"); if (dialog.opened) ++opens; }
        function canceled() { current(); ++cancelClicks; }
        function approved() { current(); ++approvalClicks; }
        send.clicked.connect(submitted); dialog.openedChanged.connect(opened);
        try {
            Ui.click(this, Probe, window, editor.objectName); visible185_type(originalText);
            const canceledRevision = composer.textRevision;
            gui393_roundFooter();
            Ui.click(this, Probe, window, "assistant.send");
            tryCompare(dialog, "opened", true, 2000, "GUI404: actual Send directly opens original required consent");
            gui398_nativeDialog(dialog);
            gui398_details(dialog); // Once in original first connected approval offer, before its genuine Cancel.
            compare(JSON.stringify(dialog.disclosedContext), JSON.stringify(JSON.parse(assistant.contextPreview)),
                "GUI404: actual consent discloses the SAME complete original current scope");
            compare(JSON.stringify(gui392_json(Probe.rows(assistant.messages))), historyBefore,
                "GUI404: requesting approval cannot admit an input before actual approval");
            cancel = dialog.standardButton(Dialog.Cancel); cancelLife = lifetime313(cancel); cancel.clicked.connect(canceled);
            gui392_button(cancel, dialog);
            tryCompare(dialog, "visible", false, 2000, "GUI404: real original Cancel settles its native exit");
            compare(editor.text, originalText, "GUI404: Cancel retains exact original draft");
            compare(composer.textRevision, canceledRevision, "GUI404: Cancel is not draft editing or ACK");
            compare(JSON.stringify(gui392_json(Probe.rows(assistant.selectedFiles))), selectedBefore,
                "GUI404: Cancel retains every original canonical/pending descriptor");
            compare(JSON.stringify(gui392_json(Probe.rows(assistant.messages))), historyBefore,
                "GUI404: Cancel admits NOTHING and cannot fabricate user history");
            verify(!assistant.canCancel && assistant.contextConsentRequired, "GUI404: original canceled scope remains unadmitted");
            Ui.click(this, Probe, window, editor.objectName);
            visible185_type("A genuinely newer original draft"); visible185_type(originalText);
            const admittedRevision = composer.textRevision;
            verify(admittedRevision > canceledRevision, "GUI404: genuine newer-identical keyboard draft has a DISTINCT revision");
            Ui.click(this, Probe, window, "assistant.send");
            tryCompare(dialog, "opened", true, 2000, "GUI404: only the new actual Send opens the new pending approval interval");
            gui398_nativeDialog(dialog);
            approve = dialog.standardButton(Dialog.Ok); approveLife = lifetime313(approve); approve.clicked.connect(approved);
            compare(editor.text, originalText, "GUI404: exact current objective still exists at original approval");
            compare(JSON.stringify(gui392_json(Probe.rows(assistant.selectedFiles))), selectedBefore,
                "GUI404: exact current attachments remain original at approval");
            capture("gui404-send-required-approval");
            gui470_standardAction(approve, dialog, "approve-context");
            // No Send after this original approval. A second-Send requirement MUST fail here.
            tryVerify(() => assistant.canCancel && Probe.rows(assistant.messages).filter(row => !oldIds.has(row.id)
                && row.kind === "user" && row.text === originalText && row.status === "pending").length === 1, 2000,
                "GUI404: matching real approval AUTOMATICALLY admits exactly original pending input before held ACK");
            compare(editor.text, originalText, "GUI404: admission is not an ACK consuming the editor");
            compare(composer.textRevision, admittedRevision, "GUI404: original admitted draft revision remains exact before ACK");
            compare(JSON.stringify(gui392_json(Probe.rows(assistant.selectedFiles))), selectedBefore,
                "GUI404: preACK authority and pending presentation remain exact");
            compare(sendClicks, 2, "GUI404: canceled attempt then new Send ONLY; NO postapproval Send workaround");
            compare(cancelClicks, 1, "GUI404: original native Cancel clicked once");
            compare(approvalClicks, 1, "GUI404: original native approval clicked ONCE");
            compare(opens, 2, "GUI404: exact original dialog opened only for the two real Send attempts");
            verify(!eye.enabled && !item("assistant.modelEffort").enabled,
                "GUI393: real original work disables presentation and choice changes");
            const pending = Probe.rows(assistant.messages).filter(row => row.kind === "user" && row.text === originalText);
            compare(pending.length, 1, "GUI393: held input has one actual original user row");
            verify(pending[0].id.length > 0 && pending[0].status === "pending", "GUI393: original actual user ID still pending before ACK");
            const originalUserId = pending[0].id;
            const markdown = Probe.readReferenceFile("gui404-table.md");
            assistant.refreshUsage();
            tryVerify(() => !assistant.canCancel && Probe.rows(assistant.messages).some(row => row.id === originalUserId
                && row.kind === "user" && row.status === "completed") && Probe.rows(assistant.messages).some(row => !oldIds.has(row.id)
                    && row.kind === "assistant" && row.status === "completed" && row.text === markdown), 2000,
                "GUI393: actual original user ACK AND original literal completed reply settle before Clear baseline");
            ux358_acknowledgedPresentation(composer, [canonicalFile405]);
            compare(editor.text, "", "GUI404: only actual matching ACK consumes SAME original draft");
            const selected = gui392_json(Probe.rows(assistant.selectedFiles));
            compare(selected.length, 1, "GUI393: ACK retains actual canonical source authority before Clear");
            compare(selected[0].id, originalFile.id, "GUI393: actual original ACK preserves exact source ID");
            compare(selected[0].pending, false, "GUI393: actual matching ACK consumes pending source presentation");
            // GUI475: native leaf-hover and plain-text Copy on the SAME actual acknowledged user row.
            {
                const list475 = item("assistant.messages");
                const record475 = Probe.rows(assistant.messages).filter(row => row.id === originalUserId);
                compare(record475.length,1,"GUI475: actual matching ACK retains ONE original user identity");
                compare(record475[0].text,originalText,"GUI475: immutable expected copy text is original independently typed literal");
                compare(record475[0].status,"completed","GUI475: sent-copy witness begins only AFTER actual original ACK");
                const canonical475 = JSON.stringify(gui392_json(record475[0]));
                const index475 = Probe.rows(assistant.messages).findIndex(row => row.id === originalUserId);
                list475.positionViewAtIndex(index475,ListView.Contain);rendered();
                const rows475 = Ui.itemsWithProperty(popup.contentItem,"rowId").filter(row => row.rowId === originalUserId && row.assistant === assistant
            && typeof row.resetDetails === "function" && typeof row.copyTechnicalPayload === "function");
                compare(rows475.length,1,"GUI475: actual rendered user-row receiver is unique after native positioning");
                const row475=rows475[0], owner475=Session.project, controller475=Session.assistant;
                const rowLife475=lifetime313(row475);
                const bodies475=Ui.itemsWithProperty(row475,"readOnly").filter(field => field.readOnly
                    && field.selectByMouse && field.text === originalText && typeof field.positionToRectangle === "function");
                compare(bodies475.length,1,"GUI475: original exact user text has ONE real selectable native TextEdit");
                const body475=bodies475[0], copies475=Probe.objectsWithProperty(row475,"objectName")
                    .filter(control => control.objectName === "assistant.user.copyText");
                compare(copies475.length,1,"GUI475: SAME original sent row owns ONE public native Copy target");
                const copy475=copies475[0], copyLife475=lifetime313(copy475), bodyLife475=lifetime313(body475);
                const bubbles475=Ui.itemsWithProperty(row475,"radius").filter(box => box.visible && box.radius>0
                    && String(box.color) === String(EaStyle.Colors.contentBackground));
                compare(bubbles475.length,1,"GUI475: actual user text has ONE original rounded native bubble surface");
                const bubble475=bubbles475[0];
                ux356_fullyExposed(body475);ux356_fullyExposed(bubble475);
                verify(copy475.width>0 && copy475.height>0 && !copy475.activeFocus,
                    "GUI475: original completed row reserves a real copy extent without fabricated keyboard focus");
                const geometry475=[rect(row475),rect(body475),rect(bubble475),rect(copy475)];
                const rb475=geometry475[2], rc475=geometry475[3];
                verify(rc475[0]>rb475[0]+rb475[2],"GUI475: native Copy is OUTSIDE user bubble with a positive actual gap");
                function current475() {
                    verify(alive313(rowLife475) && alive313(copyLife475) && alive313(bodyLife475)
                        && Session.project===owner475 && Session.assistant===controller475
                        && row475.rowId===originalUserId && row475.assistant===controller475,
                        "GUI475: actual native hover/copy retains original living row/controller/project");
                    [row475,body475,bubble475,copy475].forEach((object,index)=>sameRect(rect(object),geometry475[index]));
                    compare(JSON.stringify(gui392_json(Probe.rows(assistant.messages).find(row=>row.id===originalUserId))),canonical475,
                        "GUI475: pointer and clipboard actions preserve whole immutable original acknowledged row");
                }
                const outside475=Ui.clickPoint(editor);
                verify(outside475!==null,"GUI475: original composer supplies genuine outside-bubble pointer destination");
                const outsideScene475=editor.mapToItem(window.contentItem,outside475.x,outside475.y);
                verify(outsideScene475.y>rb475[1]+rb475[3] || outsideScene475.y<rb475[1]
                    || outsideScene475.x<rb475[0] || outsideScene475.x>rc475[0]+rc475[2],
                    "GUI475: idle pointer really leaves original bubble AND copy rail");
                mouseMove(editor,outside475.x,outside475.y);rendered();current475();
                verify(!copy475.visible || copy475.opacity===0,"GUI475: original user Copy is hidden at genuine pointer-idle outside state");
                // Existing native TextEdit layout identifies first visible character, not bubble padding.
                const cursor475=body475.positionToRectangle(0), next475=body475.positionToRectangle(1);
                verify(cursor475.height>0 && next475.x>cursor475.x && Math.abs(cursor475.y-next475.y)<0.5,
                    "GUI475: original literal starts in one actual laid-out native text line with positive character advance");
                const inkPoint475={x:(cursor475.x+next475.x)/2,y:cursor475.y+cursor475.height/2};
                verify(inkPoint475.x>=0 && inkPoint475.x<body475.width && inkPoint475.y>=0 && inkPoint475.y<body475.height,
                    "GUI475: native hover targets first-character TextEdit descendant region, NEVER blank bubble padding");
                mouseMove(body475,inkPoint475.x,inkPoint475.y);rendered();current475();
                verify(copy475.visible && copy475.opacity===1,"GUI475: real TEXTEDIT LEAF hover reveals SAME reserved user Copy");
                const gapScene475={x:(rb475[0]+rb475[2]+rc475[0])/2,y:rc475[1]+rc475[3]/2};
                verify(gapScene475.x>rb475[0]+rb475[2] && gapScene475.x<rc475[0],
                    "GUI475: native route crosses the ACTUAL blank gap between original bubble and Copy");
                const gap475=window.contentItem.mapToItem(row475,gapScene475.x,gapScene475.y);
                verify(gap475.x>=0 && gap475.x<row475.width && gap475.y>=0 && gap475.y<row475.height,
                    "GUI475: original copy-gap pointer stays in SAME bounded sent-user row");
                mouseMove(row475,gap475.x,gap475.y);rendered();current475();
                verify(copy475.visible && copy475.opacity===1,"GUI475: genuine gap traversal retains SAME revealed Copy target without geometry jump");
                const point475=Ui.clickPoint(copy475);
                verify(point475!==null,"GUI475: actual revealed Copy owns a genuine unclipped native target");
                mouseMove(copy475,point475.x,point475.y);rendered();current475();
                verify(copy475.visible && copy475.opacity===1,"GUI475: original real copy-target descendant hover retains reveal");
                let clicks475=0;
                const clicked475=function(){current475();++clicks475;};
                try {
                    copy475.clicked.connect(clicked475);
                    status410Clipboard.text="";
                    gui392_button(copy475,popup);status410Clipboard.paste();
                    compare(clicks475,1,"GUI475: ONE original native user Copy clicked receipt, never synthetic/repeated input");
                    compare(status410Clipboard.text,originalText,"GUI475: actual clipboard is EXACT original plain user text, not metadata/JSON/files");
                    current475();
                    console.info("GUI475_USER_COPY",JSON.stringify({row:originalUserId,text:originalText,clicks:clicks475,
                        geometry:geometry475,inkPoint:[inkPoint475.x,inkPoint475.y],gap:[gap475.x,gap475.y],
                        owner:String(owner475),receiver:String(copy475)}));
                } finally {disconnect313(copyLife475,copy475,"clicked",clicked475);}
            }
            gui404_table(oldIds, markdown);
            console.log("GUI404_APPROVAL", JSON.stringify({user: originalUserId, text: originalText,
                files: selected.map(file => ({id:file.id,name:file.name,bytes:file.bytes,textReadable:file.textReadable,format:file.format})),
                canceledRevision:canceledRevision, admittedRevision:admittedRevision, sendClicks:sendClicks,
                cancelClicks:cancelClicks, approvalClicks:approvalClicks, opens:opens}));
            const usage = JSON.stringify(gui392_usageData());
            console.log("GUI393_CLEAR_IDS", JSON.stringify({user: originalUserId, file: originalFile.id}));
            Ui.click(this, Probe, window, "assistant.clear");
            tryCompare(assistant.messages, "count", 0, 2000, "GUI393: actual eraser Clear removes original conversation");
            compare(assistant.selectedFiles.count, 0, "GUI393: original Clear retires actual selected-file grants");
            tryCompare(assistant, "canCancel", false, 2000,
                "CLEAR513: original Clear fresh-thread setup settles before unchanged account and consent observations");
            const clearConnected509=assistant.connected;
            const clearCanCancel509=clearConnected509 ? assistant.canCancel : null;
            const clearConsent509=clearConnected509 && !clearCanCancel509 ? assistant.contextConsentRequired : null;
            console.log("GUI509_CLEAR_OPERANDS",JSON.stringify({connected:clearConnected509,
                canCancel:clearCanCancel509,contextConsentRequired:clearConsent509}));
            verify(clearConnected509 && !clearCanCancel509 && !clearConsent509,
                "GUI393: original Clear preserves genuine account and unchanged remaining-scope consent");
            compare(JSON.stringify(gui392_json(Probe.rows(assistant.models))), account,
                "GUI393: actual Clear preserves original model catalogue");
            compare(JSON.stringify(gui392_usageData()), usage, "GUI393: actual Clear preserves account-owned usage");
            gui392_unchanged(before);
            compare(assistant.contextApprovalBlocked, false,
                "CONSENT464: genuine Clear returns healthy original approval state without forging retention");
            const newToken = assistant.beginFileSelection();
            verify(newToken.length > 0 && assistant.addSelectedFiles(newToken,
                [Probe.referenceUrl("project/structures/lbco.edi")]),
                "CONSENT464 SETUP: after Clear a genuine NEW selection admits the current attachment");
            tryCompare(assistant.selectedFiles, "count", 1, 2000,
                "CONSENT464 SETUP: actual reselected source exists before new Send");
            const newRows = gui392_json(Probe.rows(assistant.selectedFiles));
            const newCanonical = newRows.map(file => ({id:file.id,name:file.name,bytes:file.bytes,
                textReadable:file.textReadable,format:file.format}));
            verify(newRows[0].id.length > 0 && newRows[0].pending && assistant.contextConsentRequired,
                "CONSENT464 SETUP: changed current scope really needs approval after genuine Clear");
            const newText = "GUI464 original draft after genuine Clear";
            Ui.click(this, Probe, window, editor.objectName); visible185_type(newText);
            const newRevision = composer.textRevision;
            Ui.click(this, Probe, window, "assistant.send");
            tryCompare(dialog, "opened", true, 2000,
                "CONSENT464: ONE post-Clear Send opens SAME original consent dialog");
            gui398_nativeDialog(dialog);
            compare(JSON.stringify(dialog.disclosedContext), JSON.stringify(JSON.parse(assistant.contextPreview)),
                "CONSENT464: actual original opening discloses exact current post-Clear context");
            const newApprove = dialog.standardButton(Dialog.Ok), newApproveLife = lifetime313(newApprove);
            let newApprovalClicks = 0;
            function newlyApproved() { current(); ++newApprovalClicks; }
            newApprove.clicked.connect(newlyApproved);
            try {
                gui470_standardAction(newApprove, dialog, "approve-context");
                // Exactly one Approve; NO Send after the real approval.
                tryVerify(() => assistant.canCancel && Probe.rows(assistant.messages).filter(row =>
                    row.kind === "user" && row.text === newText && row.status === "pending").length === 1, 2000,
                    "CONSENT464: ONE genuine post-Clear approval automatically admits exact pending draft once");
                current();
                compare(editor.text, newText, "CONSENT464: held original ACK has not consumed the new draft");
                compare(composer.textRevision, newRevision, "CONSENT464: exact new draft revision survives admission");
                compare(JSON.stringify(gui392_json(Probe.rows(assistant.selectedFiles))), JSON.stringify(newRows),
                    "CONSENT464: exact current attachment authority/pending state survive before ACK");
                compare(sendClicks, 3, "CONSENT464: exactly ONE additional Send, no postapproval workaround");
                compare(newApprovalClicks, 1, "CONSENT464: exactly ONE original new native approval");
                compare(opens, 3, "CONSENT464: exactly ONE additional original opening");
                const newUser = Probe.rows(assistant.messages).filter(row => row.kind === "user" && row.text === newText);
                compare(newUser.length, 1, "CONSENT464: new objective has exactly one actual original user row");
                verify(newUser[0].id.length > 0 && newUser[0].id !== originalUserId,
                    "CONSENT464: Clear/new input has actual fresh user identity, never resurrected old row");
                assistant.refreshUsage();
                tryVerify(() => !assistant.canCancel && Probe.rows(assistant.messages).some(row =>
                    row.id === newUser[0].id && row.kind === "user" && row.status === "completed")
                    && Probe.rows(assistant.messages).some(row => row.kind === "assistant"
                        && row.status === "completed" && row.text === markdown), 2000,
                    "CONSENT464: original matching new ACK and completed reply settle without another Send");
                ux358_acknowledgedPresentation(composer, newCanonical);
                compare(editor.text, "", "CONSENT464: only the matching new ACK consumes exact post-Clear draft");
                console.log("GUI464_ONCE", JSON.stringify({user:newUser[0].id,text:newText,files:newCanonical,
                    revision:newRevision,sendClicks:sendClicks,approvalClicks:newApprovalClicks,opens:opens}));
            } finally { disconnect313(newApproveLife, newApprove, "clicked", newlyApproved); }
            gui392_unchanged(before);
            capture("gui393-first-delivery-eye-clear");
        } finally {
            disconnect313(sendLife, send, "clicked", submitted);
            disconnect313(dialogLife, dialog, "openedChanged", opened);
            if (cancel !== null) disconnect313(cancelLife, cancel, "clicked", canceled);
            if (approve !== null) disconnect313(approveLife, approve, "clicked", approved);
        }
    }
    function gui394_sameCurrent(choice, radio, mode, effort) {
        const original = {assistant: assistant, project: Session.project, choice: choice,
            model: assistant.selectedModel, effort: assistant.selectedEffort};
        const lives = [assistant, original.project, choice, radio].map(lifetime313);
        verify(radio.enabled && radio.checked && gui393_under(radio, choice.contentItem),
            "GUI394 SETUP: original independently selected current radio is exposed, checked and enabled");
        let presses = 0, releases = 0, falseChecks = 0, hides = 0;
        const hideChecks = [], connected = [];
        function current() {
            verify(lives.every(alive313) && assistant === original.assistant && Session.assistant === original.assistant
                && Session.project === original.project && choice === original.choice,
                "GUI394: genuine original native-radio signal retains exact live owner/control/popup");
        }
        function pressed() { current(); if (radio.pressed) ++presses; }
        function released() { current(); ++releases; }
        function checked() { current(); if (!radio.checked) ++falseChecks; }
        function hiding() {
            current(); ++hides;
            hideChecks.push({checked: radio.checked, model: assistant.selectedModel, effort: assistant.selectedEffort});
        }
        try {
            for (const pair of [[radio, "pressedChanged", pressed], [radio, "released", released],
                                [radio, "checkedChanged", checked], [choice, "aboutToHide", hiding]]) {
                pair[0][pair[1]].connect(pair[2]); connected.push(pair);
            }
            if (mode === "mouse") compare(import265_click(radio.objectName), radio,
                "GUI394: same-current native mouse action uses exact original physical radio");
            else {
                compare(window.activeFocusItem, radio, "GUI394: genuine same-current Space targets original focused radio");
                keyClick(Qt.Key_Space);
            }
            compare(presses, 1, "GUI394: one real true press, not a synthetic clicked signal");
            compare(releases, 1, "GUI394: one real original release completes native signal tail");
            compare(falseChecks, 0, "GUI394: current radio NEVER falsely clears during same-value native mouse/Space tail");
            compare(assistant.selectedModel, original.model, "GUI394: same-current activation preserves exact selected model");
            compare(assistant.selectedEffort, original.effort, "GUI394: same-current activation preserves exact selected effort");
            if (effort) {
                tryCompare(choice, "visible", false, 2000, "GUI394: same-current effort still performs original genuine popup close");
                compare(hides, 1, "GUI394: exact original effort activation has one real pre-hide delivery witness");
                compare(JSON.stringify(hideChecks), JSON.stringify([{checked: true, model: original.model, effort: original.effort}]),
                    "GUI394: mandatory live ORIGINAL pre-hide checked/selection receipt precedes any close/recreation repair");
            } else {
                compare(hides, 0, "GUI394: same-current model retains original open chooser");
                verify(alive313(lives[3]) && radio.checked && choice.opened,
                    "GUI394: actual current model remains checked in SAME original open table after native tail");
            }
        } finally {
            for (const pair of connected)
                disconnect313(pair[0] === choice ? lives[2] : lives[3], pair[0], pair[1], pair[2]);
        }
    }
    function gui394_unavailable(choice, radio, label) {
        verify(!radio.enabled && !radio.checked && Ui.rendered(radio) && Ui.exposed(radio),
            "GUI394 SETUP: independently offered MIDDLE model is genuinely visible, disabled and unselected");
        const model = assistant.selectedModel, effort = assistant.selectedEffort, error = assistant.lastError;
        const life = lifetime313(radio);
        let clicks = 0;
        function clicked() { ++clicks; }
        radio.clicked.connect(clicked);
        try {
            for (const target of [radio, label]) {
                verify(gui393_under(target, choice.contentItem) && Ui.rendered(target) && Ui.exposed(target),
                    "GUI394: actual unavailable radio AND label are observable original input targets");
                const point = Ui.clickPoint(target);
                mouseClick(target, point.x, point.y); rendered();
                compare(clicks, 0, "GUI394: actual disabled middle radio/label refuse genuine pointer activation");
                compare(assistant.selectedModel, model, "GUI394: disabled offered model cannot change backend selection");
                compare(assistant.selectedEffort, effort, "GUI394: refused disabled-model activation retains exact current effort");
                compare(assistant.lastError, error, "GUI394: disabled UI input does not dispatch a setter failure or alter real account error");
            }
            verify(choice.opened && alive313(life) && !radio.checked,
                "GUI394: refusal preserves same current popup and unavailable radio state");
        } finally { disconnect313(life, radio, "clicked", clicked); }
    }
    // GUI395: original native Button/EmptyState and divider contracts, not producer339 output.
    function gui395_signInHover(connection) {
        verify(connection.enabled && Ui.rendered(connection) && Ui.exposed(connection),
            "GUI395: SAME original signed-out header Sign in is physically actionable");
        const labels = gui392_labels(connection).filter(label => label.text === "Sign in");
        compare(labels.length, 1, "GUI395: original Sign in owns one actual painted text label");
        mouseMove(window.contentItem, 0, 0); rendered();
        tryVerify(() => Qt.colorEqual(labels[0].color, EaStyle.Colors.themeForeground), 2000,
            "GUI395: original native unhovered enabled button uses ordinary foreground");
        const point = Ui.clickPoint(connection);
        mouseMove(connection, point.x, point.y); rendered();
        tryVerify(() => Qt.colorEqual(labels[0].color, EaStyle.Colors.themeForegroundHovered), 2000,
            "GUI395: genuine mouse hover paints original native hovered foreground, not a hardcoded label color");
        gui398_noBlueOutline(connection);
        capture("gui395-real-sign-in-hover");
        mouseMove(window.contentItem, 0, 0); rendered();
        tryVerify(() => Qt.colorEqual(labels[0].color, EaStyle.Colors.themeForeground), 2000,
            "GUI395: genuine pointer leave restores native foreground");
    }
    function gui395_divider(stage) {
        verify(popup.opened && popup.visible, "GUI395: divider observation uses actual open sidebar");
        const host = item("workflow.project.sidebarHost");
        sameRect(rect(popup.contentItem), rect(host));
        const width = EaStyle.Sizes.borderThickness;
        const expectedX = Preferences.sideBarOnLeft ? popup.contentItem.width - width : 0;
        const candidates = Ui.itemsWithProperty(popup.contentItem, "color").filter(control => {
            if (!control.visible || String(control.color).toLowerCase() !== String(EaStyle.Colors.appBorder).toLowerCase()
                || Math.abs(control.width - width) >= 0.5
                || Math.abs(control.height - popup.contentItem.height) >= 0.5) return false;
            const point = control.mapToItem(popup.contentItem, 0, 0);
            return Math.abs(point.x - expectedX) < 0.5 && Math.abs(point.y) < 0.5;
        });
        compare(candidates.length, 1, "GUI395: exact current assistant owns one full-height native divider at main/sidebar boundary");
        const line = candidates[0];
        ux356_fullyExposed(line);
        const bounds = rect(line), image = grabImage(window.contentItem);
        verify(image.width > 0 && image.height > 0, "GUI395: passive actual window framebuffer exists");
        const scaleX = image.width / window.contentItem.width, scaleY = image.height / window.contentItem.height;
        for (const fraction of [0.25, 0.5, 0.75]) {
            const x = Math.floor((bounds[0] + bounds[2] / 2) * scaleX);
            const y = Math.floor((bounds[1] + bounds[3] * fraction) * scaleY);
            verify(x >= 0 && x < image.width && y >= 0 && y < image.height,
                "GUI395: original boundary sample belongs to SAME actual window frame");
            compare(String(image.pixel(x, y)).toLowerCase(), String(EaStyle.Colors.appBorder).toLowerCase(),
                "GUI395: actual native divider is PAINTED over signed-out/auth content at " + stage + ", not merely declared behind it");
        }
    }
    function gui395_dividers(stage) {
        const originalSide = Preferences.sideBarSide;
        try {
            for (const side of ["Left", "Right"]) {
                // Same existing public Preference layout fixture as original popup tests.
                Preferences.sideBarSide = side; rendered();
                gui395_divider(stage + "-" + side);
                capture("gui395-divider-" + stage + "-" + side);
            }
        } finally { Preferences.sideBarSide = originalSide; }
        rendered();
    }
    // GUI398: independent original native AppDialog and owner display contract.
    function gui398_nativeDialog(dialog) {
        verify(dialog.visible && dialog.opened && dialog.contentItem !== null && dialog.parent !== null,
            "GUI398: original settled native dialog has real parent/content before geometry");
        verify(gui393_under(dialog.parent, Ui.windowRoot(window)),
            "GUI398: original native dialog parent belongs to SAME actual Main window");
        compare(dialog.parent.width, window.contentItem.width, "GUI398: native modal surface spans actual app width");
        compare(dialog.parent.height, window.contentItem.height, "GUI398: native modal surface spans actual app height");
        compare(dialog.x, Math.round((dialog.parent.width - dialog.width) / 2),
            "GUI398: original AppDialog is centered on whole pixels in app, not anchored to composer pill");
        compare(dialog.y, Math.round((dialog.parent.height - dialog.height) / 2),
            "GUI398: original AppDialog is vertically centered on whole pixels");
        compare(dialog.leftPadding, EaStyle.Sizes.fontPixelSize * 2, "GUI398: native dialog retains original horizontal margin");
        compare(dialog.rightPadding, EaStyle.Sizes.fontPixelSize * 2, "GUI398: native dialog retains symmetric original margin");
        compare(dialog.topPadding, EaStyle.Sizes.fontPixelSize, "GUI398: native dialog retains original top margin");
        compare(dialog.bottomPadding, EaStyle.Sizes.fontPixelSize, "GUI398: native dialog retains original bottom margin");
        tryVerify(() => Qt.colorEqual(dialog.background.color, EaStyle.Colors.dialogBackground), 2000, "GUI398: standard native dialog background is reused");
        compare(dialog.font.pixelSize, EaStyle.Sizes.fontPixelSize, "GUI398: native dialog uses original standard font size");
        ux356_fullyExposed(dialog.contentItem);
    }
    function gui398_owned(root, name, exposed) {
        const matches = Ui.itemsWithProperty(root.contentItem, "objectName").filter(control => control.objectName === name);
        compare(matches.length, 1, "GUI398: SAME original dialog uniquely owns actual presentation control: " + name);
        verify(gui393_under(matches[0], root.contentItem), "GUI398: named native control belongs to original content subtree");
        if (exposed) ux356_fullyExposed(matches[0]);
        return matches[0];
    }
    function gui398_noBlueOutline(control) {
        const background = control.background;
        verify(typeof background !== "undefined", "GUI398: actual original native button exposes its public background property");
        // A genuinely absent background cannot paint an outline; shape assertions
        // for pill/avatar/footer remain independently mandatory at their callers.
        const outlines = background === null ? [] : Ui.itemsWithProperty(background, "border");
        for (const item of outlines) {
            // Bounded native identity/presentation facts BEFORE the original strict comparison.
            // Rectangle's default width getter alone is not evidence of a painted valid pen.
            console.log("GUI494_BORDER_RECEIVER", JSON.stringify({control: control.objectName,
                receiver: String(item).slice(0, 200), receiverName: String(item.objectName).slice(0, 80),
                parent: String(item.parent).slice(0, 200), parentName: item.parent ? String(item.parent.objectName).slice(0, 80) : "",
                sameBackground: item === background, visible: item.visible, enabled: item.enabled,
                geometry: [item.x, item.y, item.width, item.height], width: item.border.width,
                color: String(item.border.color), alpha: item.border.color.a}));
            if (["assistant.modelEffort", "assistant.files.add", "assistant.showActions",
                 "assistant.previousUserMessage", "assistant.nextUserMessage", "assistant.send", "assistant.stop",
                 "assistant.clear", "assistant.usage", "assistant.connection"].includes(control.objectName)) {
                compare(item.border.width, 0, "GUI494: original custom composer/header surface explicitly has zero border in actual normal/hover/focus/checked state");
                continue;
            }
            const color = String(item.border.color).toLowerCase();
            verify(item.border.width === 0 || item.border.color.a === 0
                || ![EaStyle.Colors.themeAccent, EaStyle.Colors.themeAccentMinor, EaStyle.Colors.blue,
                     EaStyle.Colors.themeForegroundHovered].some(value => String(value).toLowerCase() === color),
                "GUI398: actual assistant button background has NO blue outline, including genuine focus/checked state");
        }
    }
    function gui398_header(avatar) {
        const clear = item("assistant.clear"), plus = item("assistant.files.add"), eye = item("assistant.showActions");
        gui399_avatar(avatar);
        const glyphs = [clear, plus, eye].map(control => {
            const labels = gui392_labels(control).filter(label => label.text === control.fontIcon
                && label.font.family === EaStyle.Fonts.iconsFamily);
            compare(labels.length, 1, "GUI398: original actual native icon glyph is uniquely observable");
            ux356_fullyExposed(labels[0]); return labels[0];
        });
        compare(glyphs[0].font.pixelSize, glyphs[1].font.pixelSize,
            "GUI398: eraser glyph has same small native size as original composer Plus, not an enlarged header icon");
        compare(glyphs[0].font.pixelSize, glyphs[2].font.pixelSize,
            "GUI398: eraser glyph also matches original eye, preserving actual action hitboxes");
        const usage = item("assistant.usage"), pill = item("assistant.modelEffort");
        const headerRects = [clear, usage, avatar].map(control => rect(control));
        const footerGap = rect(eye)[0] - rect(plus)[0] - rect(plus)[2];
        verify(footerGap >= 0 && Math.abs(headerRects[1][0] - headerRects[0][0] - headerRects[0][2] - footerGap) < 0.5
            && Math.abs(headerRects[2][0] - headerRects[1][0] - headerRects[1][2] - footerGap) < 0.5,
            "GUI494: actual rounded header action gaps match original composer Plus/Eye spacing");
        compare(usage.leftPadding, pill.leftPadding, "GUI494: original Usage left padding matches accepted model pill");
        compare(usage.rightPadding, pill.rightPadding, "GUI494: original Usage right padding matches accepted model pill");
        for (const control of [avatar, clear, usage]) gui398_noBlueOutline(control);
        const titles = gui392_labels(popup.contentItem).filter(label => label.text === "Assistant");
        compare(titles.length, 1, "GUI398: actual sidebar has ONE native Assistant header title");
        const bounds = rect(titles[0]), side = rect(popup.contentItem), image = grabImage(window.contentItem);
        const x = side[0] + (Preferences.sideBarOnLeft ? side[2] - 3 : 3), y = bounds[1] + bounds[3] / 2;
        compare(String(image.pixel(Math.floor(x * image.width / window.contentItem.width),
            Math.floor(y * image.height / window.contentItem.height))).toLowerCase(), String(EaStyle.Colors.contentBackground).toLowerCase(),
            "GUI398: actual Assistant titlebar paint matches FIRST native Main/Extra contentBackground, not body/divider redesign");
    }
    function gui398_account(account) {
        const labels = gui392_labels(account.contentItem);
        const email = labels.filter(label => label.text === "Original@example.invalid");
        const plan = labels.filter(label => label.text === "Plus");
        compare(email.length, 1, "GUI398: native Account shows exact actual supplied email once");
        compare(plan.length, 1, "GUI398: actual supported plan is title-cased Plus once");
        verify(!labels.some(label => label.text === "Original"),
            "GUI398: absent provider full-name metadata is NOT fabricated from email local part");
        const ordinary = labels.filter(label => label.font.family !== EaStyle.Fonts.iconsFamily && label.text.trim().length > 0);
        verify(ordinary.every(label => ["Original@example.invalid", "Plus", "Sign out"].includes(label.text)),
            "GUI398: original nameless provider record gains no invented personal name or account prose");
        function contrast(label) {
            let alpha = label.color.a;
            for (let object = label; object && object !== account.contentItem; object = object.parent) alpha *= object.opacity;
            const background = account.background.color;
            return alpha * alpha * (Math.pow(label.color.r - background.r, 2)
                + Math.pow(label.color.g - background.g, 2) + Math.pow(label.color.b - background.b, 2));
        }
        verify(contrast(plan[0]) < contrast(email[0]),
            "GUI398: title-case plan has genuinely muted painted ink against SAME native dialog, not disabled semantic authority");
        ux356_fullyExposed(email[0]); ux356_fullyExposed(plan[0]);
        const signOut = gui398_owned(account, "assistant.signOut", true);
        const emailRect = rect(email[0]), planRect = rect(plan[0]), signOutRect = rect(signOut);
        const tight = planRect[1] - emailRect[1] - emailRect[3];
        verify(tight >= -0.5 && tight <= EaStyle.Sizes.fontPixelSize / 2,
            "GUI398: original email/plan are tightly stacked using normal native spacing");
        verify(signOutRect[1] - planRect[1] - planRect[3] > tight + 0.5,
            "GUI398: native Sign out has genuinely larger gap below compact identity/plan");
            const icon = gui392_labels(signOut).filter(label => label.text === "sign-out-alt"
            && label.font.family === EaStyle.Fonts.iconsFamily);
        const text = labels.filter(label => label.text === "Sign out");
        compare(icon.length, 1, "GUI399: original Sign out owns ONE native icon glyph");
        compare(text.length, 1, "GUI399: original Account owns ONE Sign out text");
        verify(gui393_under(icon[0], signOut.contentItem) && gui393_under(text[0], signOut.contentItem),
            "GUI400: exact original native Button content owns its literal child icon and Sign out label, no ToolButton-only property");
        ux356_fullyExposed(icon[0]); ux356_fullyExposed(text[0]);
        const ir = rect(icon[0]), tr = rect(text[0]);
        verify(Math.abs(ir[1] + ir[3] / 2 - tr[1] - tr[3] / 2) < 0.5,
            "GUI399: actual native Sign out glyph and text share their vertical content center");
        verify(Math.abs(ir[0] - emailRect[0]) < 0.5 && Math.abs(ir[0] - planRect[0]) < 0.5
            && tr[0] >= ir[0] + ir[2],
            "GUI399: native Sign out content starts at SAME original email/plan left edge with text after icon");
    }
    function gui398_relativeReset(control, timestamp) {
        const match = /^Resets in\s+(?:(\d+)d\s*)?(?:(\d+)h\s*)?(?:(\d+)\s+min\s*)?$/i.exec(control.text);
        verify(match !== null && match.slice(1).some(value => value !== undefined),
            "GUI399: reset uses compact days/hours and readable separated minute unit, e.g. 12 min");
        const represented = Number(match[1] || 0) * 86400 + Number(match[2] || 0) * 3600 + Number(match[3] || 0) * 60;
        const precision = match[3] !== undefined ? 60 : match[2] !== undefined ? 3600 : 86400;
        verify(Math.abs((timestamp - Date.now() / 1000) - represented) <= precision + 2,
            "GUI398: relative reset is independently bonded to literal actual provider timestamp at its shown precision");
    }
    function gui398_usageRows(dialog, expectedUsed, stale) {
        const ids = ["session", "weekly"], titles = ["Session limit", "Weekly"];
        const supplied = JSON.parse(Probe.readReferenceFile("usage399-resets.json"));
        verify(supplied !== null && typeof supplied === "object" && !Array.isArray(supplied)
            && Object.keys(supplied).sort().join(",") === "session,weekly"
            && ids.every(id => Number.isInteger(supplied[id]) && supplied[id] > 0),
            "GUI399 SETUP: independent original provider reset operands exist before Main, not derived from observed Usage");
        const rows = [], all = Ui.itemsWithProperty(dialog.contentItem, "objectName");
        for (let index = 0; index < ids.length; ++index) {
            const stem = "assistant.usage." + ids[index];
            if (expectedUsed[index] === null) {
                verify(!all.some(control => (control.objectName === stem || control.objectName.indexOf(stem + ".") === 0)
                    && Ui.rendered(control)),
                    "GUI399: genuinely missing allowance paints NO semantic row/percentage/track/reset, never fake zero or per-row Unavailable");
                verify(!gui392_labels(dialog.contentItem).some(label => label.text === titles[index] && Ui.rendered(label)),
                    "GUI399: missing Session/Weekly has no visible title even if passive native objects remain");
                continue;
            }
            const row = gui398_owned(dialog, stem, true), percent = gui398_owned(dialog, stem + ".percent", true);
            const track = gui398_owned(dialog, stem + ".bar", true), fill = gui398_owned(dialog, stem + ".fill", false);
            const reset = gui398_owned(dialog, stem + ".reset", true);
            for (const control of [percent, track, fill, reset]) verify(gui393_under(control, row),
                "GUI398: exact original semantic allowance row owns its own percentage/bar/reset, never a different window");
            const labels = gui392_labels(row).filter(label => label.text === titles[index]);
            compare(labels.length, 1, "GUI398: exactly one independent duration-based Session/Weekly title, not primary/secondary guess");
            const title = rect(labels[0]), value = rect(percent);
            verify(title[0] < value[0] && Math.abs(title[1] + title[3] / 2 - value[1] - value[3] / 2) < 0.5,
                "GUI398: native allowance title left and USED percentage right share same actual baseline");
            compare(percent.text, expectedUsed[index] + "% used", "GUI398: exact independently supplied USED percentage remains truthful, including over100");
            gui399_track(dialog, track, fill, expectedUsed[index]);
            const remaining = 100 - expectedUsed[index];
            tryVerify(() => Qt.colorEqual(fill.color, remaining < 5 ? EaStyle.Colors.red : remaining < 25 ? EaStyle.Colors.orange : EaStyle.Colors.themeAccent), 2000,
                "GUI398: actual used fill is normal accent/orange below25remaining/red below5remaining");
            gui398_relativeReset(reset, supplied[ids[index]]);
            if (supplied[ids[index]] - Date.now() / 1000 < 13 * 60)
                verify(/\d+ min\b/.test(reset.text), "GUI399: real near-minute provider reset visibly separates number and min");
            rows.push(row);
        }
        if (rows.length === 2) verify(rect(rows[0])[1] < rect(rows[1])[1],
            "GUI398: actual Session and Weekly are separate ordered native rows");
        compare(all.filter(control => /^assistant\.usage\.[^.]+$/.test(control.objectName) && Ui.rendered(control)).length,
            expectedUsed.filter(value => value !== null).length,
            "GUI399: exactly the known semantic rows are visible; missing rows are omitted, not placeholders");
        const visibleLabels = gui392_labels(dialog.contentItem).filter(label => Ui.rendered(label) && label.text.trim().length > 0);
        const unavailable = visibleLabels.filter(label => /unavailable/i.test(label.text));
        compare(unavailable.length, rows.length === 0 ? 1 : 0,
            "GUI399: neither known means ONE compact honest unavailable message; partial known has no missing-row clutter");
        const text = visibleLabels.map(label => label.text).join("\n");
        verify(!/Read at|different allowance|context|credit|balance|primary|secondary|Original owned limit|12\.50|\b300\b|\b10080\b|\d{4}-\d{2}-\d{2}/i.test(text),
            "GUI398: default Usage has no Read-at/context/credits/raw-duration/ISO/bucket clutter");
        if (stale) verify(/last known/i.test(text), "GUI398: genuine failed refresh explicitly marks retained observation Last known");
    }
    function gui398_details(dialog) {
        gui398_nativeDialog(dialog);
        const original = {owner: Session.project, assistant: Session.assistant, raw: assistant.contextPreview};
        const human = gui398_owned(dialog, "assistant.contextDetailsToggle", true);
        const technical = gui398_owned(dialog, "assistant.contextTechnicalToggle", false);
        const preview = gui398_owned(dialog, "assistant.contextPreview", false);
        verify(human.checkable && technical.checkable && human.enabled,
            "GUI398: original disclosure links are genuine native checkable controls");
        compare(human.checked, false, "GUI398: actual human Details starts collapsed");
        compare(technical.checked, false, "GUI398: raw technical data independently starts collapsed");
        verify(technical.visible === false && preview.visible === false
            && !Ui.rendered(technical) && !Ui.rendered(preview),
            "GUI398: default short Sign in reveals neither technical toggle nor raw payload");
        function link(button, text) {
            compare(button.text, text, "GUI398: actual original native link shows exact current Show/Hide action");
            const labels = gui392_labels(button).filter(label => label.text === text);
            compare(labels.length, 1, "GUI398: original enabled Details link has ONE actually painted label");
            tryVerify(() => Qt.colorEqual(labels[0].color, EaStyle.Colors.themeAccent), 2000, "GUI398: original enabled Details link paints native blue text");
        }
        // Pin only original actual receivers/viewports, never their current geometry.
        const originalViewports = [];
        for (let parent = preview.parent; parent && parent !== dialog.contentItem; parent = parent.parent)
            if (parent.clip) originalViewports.push(parent);
        verify(originalViewports.length > 0, "GUI438 SETUP: original raw presentation has an actual owning clipped viewport");
        const originalLives = [dialog, human, technical, preview].concat(originalViewports).map(lifetime313);
        function current() {
            verify(originalLives.every(alive313), "GUI438: original disclosure receivers and viewports remain alive after layout/render");
            verify(Session.project === original.owner && Session.assistant === original.assistant
                && dialog.assistant === original.assistant && dialog.visible && dialog.opened,
                "GUI438: observation retains exact original open dialog, project and controller");
            compare(gui398_owned(dialog, "assistant.contextDetailsToggle", false), human,
                "GUI438: SAME original human control survives layout/render");
            compare(gui398_owned(dialog, "assistant.contextTechnicalToggle", false), technical,
                "GUI438: SAME original technical control survives layout/render");
            compare(gui398_owned(dialog, "assistant.contextPreview", false), preview,
                "GUI438: SAME original raw preview survives layout/render");
            const viewports = [];
            for (let parent = preview.parent; parent && parent !== dialog.contentItem; parent = parent.parent)
                if (parent.clip) viewports.push(parent);
            compare(viewports.length, originalViewports.length, "GUI438: original owning viewport chain remains complete");
            verify(viewports.every((viewport, index) => viewport === originalViewports[index]),
                "GUI438: preview is not replaced or reparented to another clipped viewport");
        }
        let lastReceipt407 = null, completed407 = false;
        function input(button, beforeNativeInput) {
            Ui.scrollIntoView(button); rendered(); current();
            if (beforeNativeInput !== undefined) beforeNativeInput();
            if (lastReceipt407 !== null) {
                const previous407 = lastReceipt407; lastReceipt407 = null;
                verify(previous407.finish("details-before-next-input"), "GUI407: previous original disclosure interval retains complete passive evidence");
            }
            current();
            lastReceipt407 = gui392_button(button, dialog, true);
            current();
            verify(Session.project === original.owner && Session.assistant === original.assistant
                && dialog.assistant === original.assistant,
                "GUI398: genuine disclosure toggle preserves SAME original owner/controller/dialog");
            compare(assistant.contextPreview, original.raw, "GUI398: presentation toggles do not alter original exact outgoing payload");
        }
        function observePreview() {
            Ui.scrollIntoView(preview); rendered(); current();
            verify(Ui.rendered(preview) && preview.readOnly && preview.selectByMouse,
                "GUI398: actually exposed original raw payload is read-only/selectable, not substituted summary");
            compare(preview.text, original.raw, "GUI398: independently observed disclosed text is byte-exact original current payload");
            compare(JSON.stringify(dialog.disclosedContext), JSON.stringify(JSON.parse(original.raw)),
                "GUI398: original dialog owns exact same structured disclosure while technical text is visible");
        }
        try {
            current();
            link(human, "Show details"); input(human);
            tryCompare(human, "checked", true, 2000, "GUI398: genuine original Show details exposes human-readable Details");
            link(human, "Hide details");
            input(technical, function () {
                ux356_fullyExposed(technical); link(technical, "Show technical data");
                compare(technical.checked, false, "GUI398: opening human Details NEVER automatically expands raw technical data");
                verify(preview.visible === false && !Ui.rendered(preview), "GUI398: raw payload stays hidden inside initially opened human Details");
                capture("gui398-signin-human-details");
            });
            tryCompare(technical, "checked", true, 2000, "GUI398: genuine Show technical data exposes original exact payload");
            link(technical, "Hide technical data");
            observePreview();
            input(technical);
            tryCompare(technical, "checked", false, 2000, "GUI398: genuine Hide technical data hides original raw presentation");
            link(technical, "Show technical data"); verify(preview.visible === false && !Ui.rendered(preview), "GUI398: raw field really hides after its own toggle");
            input(technical);
            tryCompare(technical, "checked", true, 2000, "GUI398: original technical interval reopens before human-collapse reset witness");
            observePreview();
            input(human);
            tryCompare(human, "checked", false, 2000, "GUI398: genuine Hide details collapses human presentation");
            compare(technical.checked, false, "GUI398: collapsing human Details retires original expanded technical state");
            verify(technical.visible === false && preview.visible === false
            && !Ui.rendered(technical) && !Ui.rendered(preview), "GUI398: collapsed human Details exposes no raw content");
            input(human);
            tryCompare(human, "checked", true, 2000, "GUI398: genuine later Show details restores human view only");
            compare(technical.checked, false, "GUI398: later human open cannot resurrect old technical expansion");
            link(technical, "Show technical data"); verify(preview.visible === false && !Ui.rendered(preview), "GUI398: later human Details again keeps technical payload collapsed");
            input(human);
            tryCompare(human, "checked", false, 2000, "GUI398: original compact Sign in is restored before genuine Cancel");
            link(human, "Show details");
            compare(technical.checked, false, "GUI438: final compact state keeps original technical expansion retired");
            verify(technical.visible === false && preview.visible === false
                && !Ui.rendered(technical) && !Ui.rendered(preview),
                "GUI438: final compact Sign in semantically hides original raw controls independent of viewport position");
            ux356_fullyExposed(dialog.standardButton(Dialog.Cancel));
            completed407 = true;
        } finally {
            if (lastReceipt407 !== null) {
                const evidence407 = lastReceipt407.finish(completed407 ? "details-return" : "details-failure");
                if (completed407) verify(evidence407, "GUI407: original successful disclosure sequence retains mandatory input/final framebuffer evidence");
            }
        }
    }
    // GUI399: owner geometry measured from original public native items, not source348 output.
    function gui399_track(dialog, track, fill, used) {
        verify(track.width > 0 && track.height > 0 && track.radius >= track.height / 2 - 0.5
            && track.border.width > 0 && track.border.color.a > 0,
            "GUI399: actual full rounded track has a permanent visible native outline");
        tryVerify(() => Qt.colorEqual(track.border.color, EaStyle.Colors.appBorder), 2000,
            "GUI400: Usage outline uses FIRST native application/control appBorder in current palette, never bright muted-text ink");
        function distance(a, b) { return Math.pow(a.r - b.r, 2) + Math.pow(a.g - b.g, 2) + Math.pow(a.b - b.b, 2); }
        verify(distance(track.border.color, dialog.background.color) > 0,
            "GUI399: full track outline has actual contrast against same original popup");
        const inset = track.border.width, origin = fill.mapToItem(track, 0, 0);
        const innerWidth = track.width - 2 * inset, innerHeight = track.height - 2 * inset;
        verify(innerWidth > 0 && innerHeight > 0 && origin.x >= inset - 0.5 && origin.y >= inset - 0.5
            && origin.x + fill.width <= track.width - inset + 0.5
            && origin.y + fill.height <= track.height - inset + 0.5,
            "GUI399: actual fill is contained INSIDE all sides of rounded track border, no edge overdraw");
        verify(Math.abs(fill.width / innerWidth - Math.min(100, Math.max(0, used)) / 100) < 0.000001,
            "GUI399: actual inset fill uses truthful independently supplied USED fraction; clamp paint only");
        compare(fill.height, innerHeight, "GUI399: actual fill occupies inner track height, preserving full border");
        verify(fill.radius >= fill.height / 2 - 0.5, "GUI398: allowance fill is genuinely rounded");
    }
    function gui399_avatar(avatar) {
        const original = {owner: Session.project, assistant: Session.assistant, theme: EaStyle.Colors.theme};
        const life = lifetime313(avatar), target = rect(avatar);
        compare(target[2], rect(item("assistant.files.add"))[2],
            "GUI494: connected avatar footprint matches accepted original composer action extent");
        compare(target[3], EaStyle.Sizes.toolButtonHeight, "GUI399: original connected avatar click HEIGHT is unchanged native toolButtonHeight");
        function distance(a, b) { return Math.pow(a.r - b.r, 2) + Math.pow(a.g - b.g, 2) + Math.pow(a.b - b.b, 2); }
        function observe() {
            verify(alive313(life) && Session.project === original.owner && Session.assistant === original.assistant,
                "GUI399: genuine palette/pointer observations retain SAME live original avatar owner");
            sameRect(rect(avatar), target); ux356_fullyExposed(avatar);
            const circles = Ui.itemsWithProperty(avatar.background, "radius").filter(control => control.visible
                && control.color !== undefined && control.color.a > 0 && control.width > 0 && control.height > 0
                && Math.abs(control.width - control.height) < 0.5 && control.radius >= control.height / 2 - 0.5);
            compare(circles.length, 1, "GUI399: original native avatar owns ONE actual painted circle, not a duplicate overlay");
            const circle = circles[0], origin = circle.mapToItem(avatar, 0, 0);
            verify(circle.width <= avatar.width && circle.height < avatar.height
                && Math.abs(origin.x + circle.width / 2 - avatar.width / 2) < 0.5
                && Math.abs(origin.y + circle.height / 2 - avatar.height / 2) < 0.5,
                "GUI494: accepted small visual circle is centered and contained in original header target");
            compare(circle.border.width, 0, "GUI494: connected avatar is borderless, including real hover and both palettes");
            const fill = circle.color;
            tryVerify(() => Qt.colorEqual(circle.color, EaStyle.Colors.isDarkPalette ? "white" : "black"), 2000,
                "GUI494: actual avatar retains strong enabled-Send-like contrasting native fill");
            const labels = gui392_labels(avatar).filter(label => label.text === avatar.text && gui393_under(label, avatar.contentItem));
            compare(labels.length, 1, "GUI494: SAME actual avatar owns its unique painted initial label");
            tryVerify(() => Qt.colorEqual(labels[0].color,
                avatar.hovered || avatar.down || avatar.visualFocus ? EaStyle.Colors.themeAccent
                    : EaStyle.Colors.isDarkPalette ? "black" : "white"), 2000,
                "GUI494: actual avatar initial retains native contrasting resting ink and real active accent");
            verify(distance(fill, EaStyle.Colors.contentBackground) * fill.a * fill.a > 0,
                "GUI400: actual avatar fill separately contrasts native header in both palettes/real hover, without cross-distance ordering");
        }
        try {
            for (const theme of [EaStyle.Colors.LightTheme, EaStyle.Colors.DarkTheme]) {
                EaStyle.Colors.theme = theme;
                mouseMove(window.contentItem, 0, 0); rendered(); observe();
                const point = Ui.clickPoint(avatar);
                mouseMove(avatar, point.x, point.y); rendered(); observe();
                mouseMove(window.contentItem, 0, 0); rendered(); observe();
            }
        } finally {
            EaStyle.Colors.theme = original.theme;
            mouseMove(window.contentItem, 0, 0); rendered();
        }
    }
    function gui399_tableExtent(choice, table, rows) {
        verify(rows.length > 0 && table.count === rows.length,
            "GUI399: actual native table exposes ALL independently offered rows, not a fitted subset");
        const border = EaStyle.Sizes.borderThickness, viewport = rect(table), content = rect(choice.contentItem);
        ux356_fullyExposed(table);
        verify(viewport[0] >= content[0] - 0.5 && viewport[0] + viewport[2] <= content[0] + content[2] + 0.5,
            "GUI399: full native table including RIGHT border is within original dialog content");
        const naturalHeight = table.tableRowHeight * rows.length + (table.headerItem ? table.headerItem.height : 0);
        verify(table.height >= naturalHeight - 0.5,
            "GUI399: normal roomy original Main shows full natural ALL-row table height, not clipped final row");
        const borders = Ui.itemsWithProperty(table, "border").filter(control => control.visible && control.border.width > 0
            && control.border.color.a > 0 && Math.abs(rect(control)[0] - viewport[0]) < 0.5
            && Math.abs(rect(control)[1] - viewport[1]) < 0.5 && Math.abs(control.width - table.width) < 0.5
            && Math.abs(control.height - table.height) < 0.5);
        compare(borders.length, 1, "GUI399: original native full table border exists once, not cropped/right-edge omitted");
        const nativeBorder = borders[0], nativeBounds = rect(nativeBorder);
        const innerTop = nativeBounds[1] + nativeBorder.border.width;
        const innerBottom = nativeBounds[1] + nativeBounds[3] - nativeBorder.border.width;
        for (const row of rows) {
            ux356_fullyExposed(row);
            const bounds = rect(row);
            verify(bounds[1] >= innerTop - 0.5 && bounds[1] + bounds[3] <= innerBottom + 0.5,
                "GUI400: EVERY actual row including first/last ends inside real inner vertical native border, never under its z4 paint");
            verify(bounds[0] >= viewport[0] - 0.5 && bounds[0] + bounds[2] <= viewport[0] + viewport[2] + 0.5
                && bounds[1] >= viewport[1] - 0.5 && bounds[1] + bounds[3] <= viewport[1] + viewport[3] + 0.5,
                "GUI399: EACH offered row, including last, lies within same native table viewport");
        }

    }
    // GUI400: original native padding balance, measured in original actual dialog coordinates.
    function gui400_chooserSpacing(choice, tables) {
        const origin = choice.parent.mapToItem(window.contentItem, choice.x, choice.y);
        const popupBounds = [origin.x, origin.y, choice.width, choice.height];
        const contentBounds = rect(choice.contentItem);
        const bounds = tables.map(rect);
        const left = Math.min.apply(null, bounds.map(value => value[0]));
        const right = Math.max.apply(null, bounds.map(value => value[0] + value[2]));
        const bottom = Math.max.apply(null, bounds.map(value => value[1] + value[3]));
        const leftGap = left - popupBounds[0], rightGap = popupBounds[0] + popupBounds[2] - right;
        const bottomGap = popupBounds[1] + popupBounds[3] - bottom;
        verify(Math.abs(leftGap - choice.leftPadding) < 0.5
            && Math.abs(rightGap - choice.rightPadding) < 0.5,
            "GUI400: full natural chooser tables retain ONLY balanced original native side padding, no unused right scrollbar gutter");
        verify(Math.abs(contentBounds[0] + contentBounds[2] - right) < 0.5,
            "GUI400: actual normal-room rightmost table reaches original content right edge; no invisible scrollbar reserve");
        verify(bottomGap >= choice.bottomPadding - 0.5 && bottomGap >= Math.min(leftGap, rightGap) - 0.5,
            "GUI400: bottom has native breathing room balanced against real side margins, not cramped against table border");
    }
    // GUI404: existing Report171 native TextEdit observation, independent literal table.
    function gui404_table(oldIds, markdown) {
        const owner = Session.project, controller = Session.assistant, theme = EaStyle.Colors.theme;
        const ownerLife = lifetime313(owner);
        const rows = Probe.rows(assistant.messages).filter(row => !oldIds.has(row.id)
            && row.kind === "assistant" && row.status === "completed" && row.text === markdown);
        compare(rows.length, 1, "GUI404: exactly ONE genuinely completed original literal table response");
        const rowId = rows[0].id;
        // Existing bounded polish/render phase precedes ANY native delegate/body lookup.
        rendered();
        verify(alive313(ownerLife) && Session.project === owner && Session.assistant === controller,
            "GUI405: original completed-row owner/controller is STILL live/current after original bounded layout/render");
        compare(Probe.rows(assistant.messages).filter(row => row.id === rowId && row.kind === "assistant"
            && row.status === "completed" && row.text === markdown).length, 1,
            "GUI405: SAME exact original completed row survives genuine layout before unique native lookup");
        const delegates = Ui.itemsWithProperty(Ui.windowRoot(window), "rowId").filter(object => object.rowId === rowId && object.assistant === assistant
            && typeof object.resetDetails === "function" && typeof object.copyTechnicalPayload === "function"
            && object.kind === "assistant" && object.status === "completed");
        compare(delegates.length, 1, "GUI404: exact original response has ONE current native message delegate");
        const bodies = Ui.itemsWithProperty(delegates[0], "readOnly").filter(object => object.visible
            && typeof object.linkAt === "function" && object.readOnly);
        compare(bodies.length, 1, "GUI404: original real delegate owns ONE actual native selectable TextEdit");
        const body = bodies[0], bodyLife = lifetime313(body);
        const labels = ["Alpha", "Bravo", "Charlie", "Delta"], values = ["111", "222", "333", "444"];
        try {
            for (const palette of [EaStyle.Colors.LightTheme, EaStyle.Colors.DarkTheme]) {
                EaStyle.Colors.theme = palette; rendered();
                verify(alive313(ownerLife) && alive313(bodyLife) && Session.project === owner
                    && Session.assistant === controller, "GUI404: SAME live original response/owner survives native palette observation");
                ux356_fullyExposed(body);
                verify(body.readOnly && body.selectByMouse, "GUI404: actual table body remains passive/read-only and genuinely selectable");
                const plain = body.getText(0, body.length);
                const prefix = "Original fileauth reply 1";
                verify(plain.includes(prefix) && plain.includes("Item") && plain.includes("Value"),
                    "GUI404: actual semantic copy retains independent original prose and BOTH literal column headers");
                let prior = plain.indexOf(prefix);
                function operand(text) {
                    compare(plain.split(text).length - 1, 1, "GUI404: independently declared cell appears exactly ONCE in native semantic text: " + text);
                    const index = plain.indexOf(text);
                    verify(index > prior, "GUI404: actual native copy retains literal original cell order: " + text); prior = index;
                    const first = body.positionToRectangle(index), last = body.positionToRectangle(index + text.length);
                    verify(Math.abs(first.y - last.y) < 0.5 && first.height > 0,
                        "GUI404: independent short cell really occupies ONE native text line: " + text);
                    return {x:first.x, y:first.y, height:first.height, end:last.x};
                }
                const left = [], right = [];
                for (let index = 0; index < labels.length; ++index) { left.push(operand(labels[index])); right.push(operand(values[index])); }
                const headLeft = body.positionToRectangle(plain.indexOf("Item")), headRight = body.positionToRectangle(plain.indexOf("Value"));
                verify(left.every(cell => Math.abs(cell.x - headLeft.x) < 0.5)
                    && right.every(cell => Math.abs(cell.x - headRight.x) < 0.5),
                    "GUI404: BOTH native headers and all ordinary values are actually LEFT aligned to their respective columns");
                for (let index = 0; index < left.length; ++index) verify(Math.abs(left[index].y - right[index].y) < 0.5
                    && Math.abs(left[index].height - right[index].height) < 0.5,
                    "GUI404: same ordinary row contains both single-line cells on one actual text baseline band");
                const image = grabImage(window.contentItem), sx = image.width / window.contentItem.width, sy = image.height / window.contentItem.height;
                verify(sx > 0 && sy > 0, "GUI404: original native framebuffer exists with actual measured pixel scales");
                const origin = body.mapToItem(window.contentItem, 0, 0);
                function pixel(x,y) { return String(image.pixel(Math.floor((origin.x+x)*sx),Math.floor((origin.y+y)*sy))).toLowerCase(); }
                const x = (Math.max.apply(null,left.map(cell => cell.end)) + Math.min.apply(null,right.map(cell => cell.x))) / 2;
                verify(x > Math.max.apply(null,left.map(cell => cell.end)) && x < Math.min.apply(null,right.map(cell => cell.x)),
                    "GUI404: actual inter-column blank sampling lane contains NO original glyphs");
                const prefixRect = body.positionToRectangle(plain.indexOf(prefix));
                const prefixEnd = body.positionToRectangle(plain.indexOf(prefix) + prefix.length);
                verify(body.width > prefixEnd.x, "GUI404 SETUP: genuine original prose has actual blank native message background to its RIGHT");
                const base = pixel((prefixEnd.x+body.width)/2, prefixRect.y + prefixRect.height / 2), shade = String(EaStyle.Colors.contentBackground).toLowerCase();
                verify(base !== shade, "GUI404 SETUP: native unshaded message surface and original public table-shade token are independently distinguishable");
                const bands = left.map((cell,index) => {
                    const center = Math.floor((origin.y+cell.y+cell.height/2)*sy), column = Math.floor((origin.x+x)*sx);
                    const color = String(image.pixel(column,center)).toLowerCase();
                    let top = center, bottom = center;
                    while (top > 0 && String(image.pixel(column,top-1)).toLowerCase() === color) --top;
                    while (bottom+1 < image.height && String(image.pixel(column,bottom+1)).toLowerCase() === color) ++bottom;
                    const textTop = (origin.y+cell.y)*sy, textBottom = (origin.y+cell.y+cell.height)*sy;
                    return {index:index,color:color,top:top,bottom:bottom,height:bottom-top+1,
                        above:textTop-top,below:bottom+1-textBottom,textTop:textTop,textBottom:textBottom};
                });
                console.log("GUI404_TABLE", JSON.stringify({row:rowId,theme:palette,plain:plain,left:left,right:right,base:base,shade:shade,bands:bands,scale:[sx,sy]}));
                // Interior neighbors independently delimit BOTH a shaded and an unshaded row.
                // Header/table outer margins need not paint a distinct color: never invent those boundaries.
                const interior = bands.slice(1,3);
                verify(interior.every(band => band.top > 0 && band.bottom+1 < image.height && band.above > 0 && band.below > 0),
                    "GUI404: BOTH shaded/unshaded interior rows have observed finite boundaries and positive breathing room, never inferred outer edges");
                verify(bands[0].color !== bands[1].color && bands[0].color === bands[2].color && bands[1].color === bands[3].color
                    && bands.every(band => band.color === base || band.color === shade),
                    "GUI404: actual alternating shaded/unshaded ordinary rows use exact native public shade and independent message background");
                for (const band of interior) verify(Math.abs(band.height-interior[0].height) <= 2
                    && Math.abs(band.above-interior[0].above) <= 2 && Math.abs(band.below-interior[0].below) <= 2,
                    "GUI404: equal native single-line rows have equal height AND top/bottom padding within two quantized framebuffer edges");
                for (let index=0;index+1<bands.length;++index) {
                    const middle = ((origin.y+left[index].y+left[index].height/2)+(origin.y+left[index+1].y+left[index+1].height/2))*sy/2;
                    verify(Math.abs(bands[index].bottom+1-middle) <= 2 && Math.abs(bands[index+1].top-middle) <= 2,
                        "GUI404: original shade stops at its OWN row boundary between independent actual text bands, no oversized neighbor paint");
                }
                const centers = left.map(cell => cell.y+cell.height/2);
                verify(Math.abs((centers[1]-centers[0])-(centers[2]-centers[1])) <= 2/sy
                    && Math.abs((centers[2]-centers[1])-(centers[3]-centers[2])) <= 2/sy,
                    "GUI404: ALL FOUR equal single-line data rows retain uniform independent native text-band spacing");
                const from = Math.ceil((origin.x+headLeft.x)*sx), to = Math.floor((origin.x+Math.max.apply(null,right.map(cell => cell.end)))*sx);
                for (const band of interior) {
                    const blankTop = Math.floor(band.textTop)-1, blankBottom = Math.ceil(band.textBottom);
                    verify(blankTop >= band.top && blankBottom <= band.bottom,
                        "GUI404: BOTH actual interior rows provide at least ONE whole framebuffer pixel of genuinely blank upper/lower padding");
                    for (const y of [blankTop,blankBottom]) for (let column=from;column<=to;++column) compare(String(image.pixel(column,y)).toLowerCase(),band.color,
                        "GUI404: actual blank row padding shades full own row across BOTH columns with NO vertical separators or split-cell gaps");
                }
                image.save("gui404-native-table-"+palette+".png");
                capture("gui404-native-table-window-"+palette);
            }
        } finally { EaStyle.Colors.theme = theme; rendered(); }
    }
    // GUI407: passive original native input receipts; childAt is VISUAL, never event acceptance.
    function gui407_nativeReceipt(button, dialog, point) {
        const original = {button:button, dialog:dialog, window:window, owner:Session.project, controller:Session.assistant};
        const objects = [button, dialog, original.window, original.owner, original.controller];
        const lives = objects.map(lifetime313), identities = lives.map(identity313);
        const events = [], connected = [], errors = [];
        let finished = false;
        function current() {
            return lives.every(life => life === null || alive313(life)) && window === original.window
                && Session.project === original.owner && Session.assistant === original.controller
                && (gui393_under(button, dialog.contentItem) || gui393_under(button, dialog.footer));
        }
        function sample(stage, frame) {
            // No test assertion is caught here: only diagnostic reads/save. An original
            // failed predicate stays first; missing diagnostics can never bless a PASS.
            try {
                const alive = lives.map(life => life === null || alive313(life));
                const receipt = {stage:stage, sequence:events.length, at:Date.now(), originalIdentities:identities,
                    alive:alive, sameWindow:window === original.window, sameOwner:Session.project === original.owner,
                    sameController:Session.assistant === original.controller, localPoint:[point.x,point.y]};
                if (alive[0] && alive[1] && alive[2]) {
                    const scene = button.mapToItem(original.window.contentItem,point.x,point.y);
                    const root = Ui.windowRoot(original.window), rootPoint = button.mapToItem(root,point.x,point.y);
                    receipt.scenePoint=[scene.x,scene.y]; receipt.rootPoint=[rootPoint.x,rootPoint.y];
                    receipt.button={name:button.objectName, pressed:button.pressed, down:button.down, checked:button.checked,
                        checkable:button.checkable, hovered:button.hovered, activeFocus:button.activeFocus,
                        visible:button.visible, enabled:button.enabled, width:button.width, height:button.height};
                    receipt.dialog={visible:dialog.visible, opened:dialog.opened, x:dialog.x, y:dialog.y,
                        width:dialog.width, height:dialog.height, modal:dialog.modal, focus:dialog.focus,
                        contentWidth:dialog.contentWidth,contentHeight:dialog.contentHeight};
                    receipt.currentOriginal=current();
                    receipt.window={visible:original.window.visible, active:original.window.active,
                        width:original.window.width,height:original.window.height,
                        focus:original.window.activeFocusItem ? String(original.window.activeFocusItem) : null};
                    const ancestors=[];
                    for(let parent=button;parent;parent=parent.parent) {
                        const mapped=button.mapToItem(parent,0,0,button.width,button.height);
                        const record={name:parent.objectName,type:String(parent),visible:parent.visible,enabled:parent.enabled,
                            clip:parent.clip,z:parent.z,opacity:parent.opacity,width:parent.width,height:parent.height,
                            receiverRect:[mapped.x,mapped.y,mapped.width,mapped.height]};
                        for(const name of ["pressDelay","contentX","contentY","contentWidth","contentHeight","originX","originY","moving","dragging","flicking","interactive"])
                            record[name]=(typeof parent[name] === "number" || typeof parent[name] === "boolean") ? parent[name] : null;
                        ancestors.push(record);
                    }
                    receipt.ancestors=ancestors;
                    const visual=[];let parent=root,position=rootPoint;
                    for(let depth=0;parent && depth<32;++depth) {
                        const hit=parent.childAt(position.x,position.y);if(!hit)break;
                        const mapped=hit.mapToItem(original.window.contentItem,0,0);
                        visual.push({name:hit.objectName,type:String(hit),visible:hit.visible,enabled:hit.enabled,z:hit.z,
                            geometry:[mapped.x,mapped.y,hit.width,hit.height]});
                        position=hit.mapFromItem(parent,position.x,position.y);parent=hit;
                    }
                    receipt.visualHitPath=visual;receipt.visualPathIsNotNativeReceipt=true;
                }
                events.push({stage:stage,sequence:receipt.sequence,at:receipt.at,alive:alive,
                    sameWindow:receipt.sameWindow,sameOwner:receipt.sameOwner,sameController:receipt.sameController,
                    pressed:receipt.button ? receipt.button.pressed : null,
                    checked:receipt.button ? receipt.button.checked : null,opened:receipt.dialog ? receipt.dialog.opened : null});
                console.log("GUI407_NATIVE_INPUT",JSON.stringify(receipt));
                if(frame) {
                    if(!alive[2] || window !== original.window)throw Error("original window unavailable for failure-time framebuffer");
                    const image=grabImage(original.window.contentItem);
                    if(image.width<=0 || image.height<=0)throw Error("original framebuffer empty");
                    const stem="gui407-original-input-"+lives[0].handle+"-"+stage;
                    image.save(stem+".png");console.log("GUI407_INPUT_FRAME",JSON.stringify({stem:stem,width:image.width,height:image.height,originalIdentities:identities}));
                }
            } catch(error) { errors.push(String(error));console.log("GUI407_DIAGNOSTIC_ERROR",JSON.stringify({stage:stage,originalIdentities:identities,error:String(error)})); }
        }
        function pressedChanged(){sample("native-pressedChanged",false);}
        function released(){sample("native-released",false);}
        function clicked(){sample("native-clicked",false);}
        function canceled(){sample("native-canceled",false);}
        function checkedChanged(){sample("native-checkedChanged",false);}
        function openedChanged(){sample("dialog-openedChanged",false);}
        function closed(){sample("dialog-closed",false);}
        function disconnect() {
            for(const pair of connected) {
                try { disconnect313(pair.life,pair.object,pair.signal,pair.callback); }
                catch(error){errors.push(String(error));console.log("GUI407_DISCONNECT_ERROR",String(error),identities);}
            }
        }
        try {
            // pressed/opened are public BOOL properties in QML; their Changed signals
            // give actual state edges, never the inaccessible same-name signal/property.
            for(const pair of [[button,lives[0],"pressedChanged",pressedChanged],[button,lives[0],"released",released],
                [button,lives[0],"clicked",clicked],[button,lives[0],"canceled",canceled],
                [button,lives[0],"checkedChanged",checkedChanged],[dialog,lives[1],"openedChanged",openedChanged],
                [dialog,lives[1],"closed",closed]]) {
                pair[0][pair[2]].connect(pair[3]);connected.push({object:pair[0],life:pair[1],signal:pair[2],callback:pair[3]});
            }
        } catch(error){sample("partial-hookup-failure",false);disconnect();throw error;}
        return {sample:sample, current:current, finish:function(stage){
            if(finished)throw Error("original native receipt finished twice");finished=true;
            try {sample(stage,true);}finally{disconnect();}
            const stillCurrent=current();
            console.log("GUI407_INPUT_SUMMARY",JSON.stringify({originalIdentities:identities,events:events,diagnosticErrors:errors,currentOriginal:stillCurrent}));
            return errors.length===0 && stillCurrent;
        }};
    }
    TextEdit { id: status410Clipboard; visible: false }
    function test_status410_original_opener_currentness_data() {
        return [{tag:"new-owner"},{tag:"same-object-reopen"},{tag:"unchanged"}];
    }
    function test_status410_original_opener_currentness(data) {
        const aUrl=Probe.referenceUrl("status410/A"), bUrl=Probe.referenceUrl("status410/B");
        const savedUrl=Probe.referenceUrl("status410/reopened");
        const aPath=ApplicationInfo.localPath(aUrl), bPath=ApplicationInfo.localPath(bUrl), savedPath=ApplicationInfo.localPath(savedUrl);
        verify(Session.openProject(aUrl),"STATUS410 SETUP: independent saved owner opens through original Session");
        const actions=Probe.objectsWithProperty(window,"objectName").filter(x=>x.objectName==="statusBar.project");
        const dialogs=Probe.objectsWithProperty(window,"objectName").filter(x=>x.objectName==="statusBar.project.folder");
        compare(actions.length,1,"STATUS410: actual native status action is unique in original window");
        compare(dialogs.length,1,"STATUS410: original standard dialog exists uniquely even when hidden");
        const action=actions[0], dialog=dialogs[0], dialogLife=lifetime313(dialog), windowLife=lifetime313(window);
        function own(name) {
            const controls=[dialog.contentItem,dialog.footer].filter(x=>x!==null).flatMap(root=>
                Ui.itemsWithProperty(root,"objectName").filter(x=>x.objectName===name));
            compare(controls.length,1,"STATUS410: exact original native content/footer owns one "+name);return controls[0];
        }
        const path=own("statusBar.project.path"), copy=own("statusBar.project.copy"), open=own("statusBar.project.open");
        const pathLife=lifetime313(path);
        function clickStatus() {
            verify(alive313(dialogLife) && alive313(windowLife),"STATUS410: same physical native opener receivers remain alive");
            ux356_fullyExposed(action);const point=Ui.clickPoint(action);mouseClick(action,point.x,point.y);rendered();
        }
        function closeStatus() {
            const close=dialog.standardButton(Dialog.Ok);
            verify(close!==null && close.enabled,"STATUS413: actual original native Ok dismiss control remains available");gui392_button(close,dialog);
        }
        // Learn actual public/metaobject notifications through a genuine unchanged
        // positive. No implementation property name is an acceptance requirement.
        clickStatus();tryVerify(()=>dialog.opened && dialog.visible,2000,"STATUS410: original unchanged native positive genuinely settles");
        compare(path.text,aPath,"STATUS410: independent saved A path is exposed in real positive");
        verify(path.readOnly && path.selectByMouse && copy.enabled && open.enabled,
            "STATUS410: unchanged native positive preserves selectable path and Copy/Open usability");
        const notifyNames=Object.keys(Probe.events(dialogLife.handle)).filter(signal=> {
            if(!signal.endsWith("Changed") || typeof dialog[signal]!=="function")return false;
            const property=signal.substring(0,signal.length-7);
            return dialog[property]===Session.project || dialog[property]===aPath;
        });
        verify(notifyNames.length<=32,"STATUS410 SETUP: finite actual owned presentation notify inventory");
        closeStatus();
        verify(Session.openProject(aUrl),"STATUS410 SETUP: genuine fresh logical A starts the reentry opener");
        const ownerA=Session.project, lifeA=lifetime313(ownerA);
        tryVerify(()=>!ownerA.calculating && Probe.computedCurrent(ownerA.currentExperiment),10000,
            "STATUS410 SETUP: original scientific owner is current before status input");
        const scienceA=save349_science(ownerA), inputsA=visible185_inputs(ownerA);
        let calls=0, returned=false, expectedOwner=ownerA, expectedPath=aPath, expectedLife=lifeA, reentered=false, triggering=null;
        const bindings=[];let originalFailed413=false;
        function notification(signal,receiver,property) {
            if(calls)return;
            verify(alive313(dialogLife) && alive313(pathLife) && alive313(windowLife),
                "STATUS410: actual original notify arrives on same surviving native presentation");
            // A notify must carry this opener's literal owner/path, not arbitrary geometry.
            if(receiver[property]!==ownerA && receiver[property]!==aPath)return;
            ++calls;triggering={signal:signal,receiver:receiver===dialog?"original-dialog":"original-public-path"};
            compare(Session.project,ownerA,"STATUS410: first owned presentation notification belongs to independent A");
            if(data.tag==="new-owner") {
                verify(Session.openProject(bUrl),"STATUS410: genuine synchronous Session replaces A with independent B");
                expectedOwner=Session.project;expectedLife=lifetime313(expectedOwner);expectedPath=bPath;
                verify(expectedOwner!==ownerA,"STATUS410: B is a distinct real owner, not a renamed A");
                dialog.openCurrent();reentered=true;
            } else if(data.tag==="same-object-reopen") {
                verify(Session.saveAs(savedUrl),"STATUS410: real ordinary writer changes SAME owner's current saved path");
                compare(Session.project,ownerA,"STATUS410: real Save As retains original owner identity");
                compare(ownerA.path,savedPath,"STATUS410: literal independently requested new directory is current");
                expectedPath=savedPath;dialog.openCurrent();reentered=true;
            }
            returned=true;
        }
        function bind(receiver,life,signal,property) {
            const callback=function(){notification(signal,receiver,property);};receiver[signal].connect(callback);
            bindings.push({receiver:receiver,life:life,signal:signal,callback:callback});
        }
        try {
            for(const signal of notifyNames)bind(dialog,dialogLife,signal,signal.substring(0,signal.length-7));
            verify(typeof path.textChanged==="function","STATUS410 SETUP: actual public path has its real Qt text notification");
            bind(path,pathLife,"textChanged","text");
            clickStatus();
            compare(calls,1,"STATUS410 SETUP: one actual owned presentation notify reaches synchronous callback");
            verify(returned && (data.tag==="unchanged" || reentered),"STATUS410: actual nested native owner/path/opener action returned inside original notify");
            verify(alive313(dialogLife) && alive313(windowLife) && alive313(expectedLife),"STATUS410: newest owner and original native dialog/window survive");
            compare(Session.project,expectedOwner,"STATUS410: old opener cannot restore A over newest actual owner");
            compare(expectedOwner.path,expectedPath,"STATUS410: newest saved path remains the literal independent destination");
            tryVerify(()=>dialog.opened && dialog.visible,2000,"STATUS410: genuinely newest native dialog settles under original bound");
            compare(dialog.title,"Project folder","STATUS410: original standard native title remains");
            compare(path.text,expectedPath,"STATUS410: old opener cannot overwrite B/same-owner-new-path presentation");
            verify(copy.enabled && open.enabled,"STATUS410: old opener cannot disable newest saved owner's Copy/Open");
            ux356_fullyExposed(path);ux356_fullyExposed(copy);ux356_fullyExposed(open);
            gui392_button(copy,dialog);status410Clipboard.text="";status410Clipboard.paste();
            compare(status410Clipboard.text,expectedPath,"STATUS410: actual native Copy publishes precisely newest independent path");
            if(data.tag!=="new-owner") {
                compare(save349_science(ownerA),scienceA,"STATUS410: status/reopen/ordinary Save As preserves native science");
                compare(visible185_inputs(ownerA),inputsA,"STATUS410: status reentry preserves original measurements/sigma/weight/phase links");
            }
            console.log("STATUS410_RECEIPT",JSON.stringify({tag:data.tag,calls:calls,returned:returned,reentered:reentered,
                triggering:triggering,learnedNotifyNames:notifyNames,newOwner:identity313(expectedLife),newPath:expectedPath,
                copyEnabled:copy.enabled,openEnabled:open.enabled}));
        } catch(error413) {
            originalFailed413=true;throw error413;
        } finally {
            let cleanupFailed413=false,cleanupFailure413;
            for(const pair of bindings) {
                try {disconnect313(pair.life,pair.receiver,pair.signal,pair.callback);}
                catch(error413) {if(!cleanupFailed413)cleanupFailure413=error413;cleanupFailed413=true;console.log("STATUS413_CLEANUP",String(error413));}
            }
            try {if(alive313(dialogLife) && dialog.visible)closeStatus();}
            catch(error413) {if(!cleanupFailed413)cleanupFailure413=error413;cleanupFailed413=true;console.log("STATUS413_CLEANUP",String(error413));}
            if(cleanupFailed413 && !originalFailed413)throw cleanupFailure413;
        }
    }
    // PREFS417: public intended360 plus original native Preferences/settings prior art.
    function prefs417_rows() {
        const rows = gui392_sources();
        verify(rows.length >= 1 && rows[0].id === "builtin" && rows[0].builtin,
            "PREFS417: fixed protected builtin is actual first public row");
        verify(new Set(rows.map(row => row.id)).size === rows.length && rows.every(row =>
            typeof row.id === "string" && row.id.length > 0 && typeof row.label === "string"
            && typeof row.path === "string" && typeof row.enabled === "boolean"
            && typeof row.builtin === "boolean" && typeof row.status === "string"),
            "PREFS417: all actual source roles have declared types and distinct opaque IDs");
        return rows;
    }
    // Public-v3 configured declarations are identities/digests, not duplicate bodies.
    function prefs421_declarations(context) {
        verify(context && Array.isArray(context.skills), "PREFS421: actual configured disclosure has a typed inventory");
        const rows = context.skills.map(row => {
            verify(row !== null && typeof row === "object" && !Array.isArray(row)
                && typeof row.id === "string" && row.id.length > 0
                && typeof row.sha256 === "string" && /^[0-9a-f]{64}$/.test(row.sha256),
                "PREFS421: every declaration has mandatory nonempty actual identity and lowercase SHA256");
            return {id:row.id,sha256:row.sha256};
        });
        compare(new Set(rows.map(row => row.id)).size, rows.length,
            "PREFS421: actual configured instruction identities are unique, never optional/missing or duplicated");
        return rows;
    }
    function prefs417_expected(skills, variant) {
        const fixture = JSON.parse(Probe.readReferenceFile("prefs417.json"));
        const expected = variant === "empty" ? [] : [fixture.alphaASha256, fixture.betaSha256];
        compare(JSON.stringify(skills.map(row => row.sha256).sort()), JSON.stringify(expected.slice().sort()),
            "PREFS421: exact declaration digests equal independently hashed literal captured files, without builtin/default fallback");
        compare(new Set(skills.map(row => row.id)).size, skills.length,
            "PREFS421: exact digests cannot conceal duplicated actual captured instruction identities");
    }
    function prefs417_preferences() { return gui392_preferences(); }
    function prefs417_closePreferences(dialog) { gui392_button(dialog.standardButton(Dialog.Ok), dialog); }
    function prefs417_configure(local, observeToggle553) {
        const preferences = prefs417_preferences();
        const rows = prefs417_rows();
        compare(rows.length, 1, "PREFS417 SETUP: fresh owned settings start with only builtin");
        verify(rows[0].enabled, "PREFS417 SETUP: missing preference explicitly defaults builtin enabled");
        const remove = gui392_sourceControl("preferences.ai.source.remove.builtin");
        verify(!remove.enabled, "PREFS417: protected builtin has no usable Remove action");
        compare(gui392_sourceControl("preferences.ai.source.label.builtin").text, "EasyDiffraction",
            "PREFS417: builtin presentation is product label without internal repo path");
        let install553 = null, sample553 = null, finish553 = null;
        if (observeToggle553) {
            const buttons553 = Ui.itemsWithProperty(preferences.contentItem, "objectName").filter(control =>
                control.objectName === "preferences.ai.source.enabled.builtin" && control.visible);
            compare(buttons553.length, 1, "PREFS553: observe ONE original builtin receiver");
            const button553 = buttons553[0], controller553 = assistant, owner553 = Session.project;
            let row553 = button553.parent;
            while (row553 && typeof row553.sourceId !== "string") row553 = row553.parent;
            verify(row553 !== null && row553.sourceId === "builtin", "PREFS553: original receiver has its actual builtin row");
            const objects553 = [button553, row553, preferences, controller553, owner553, window];
            const lives553 = objects553.map(lifetime313), identities553 = lives553.map(identity313);
            const point553 = Ui.clickPoint(button553);
            verify(point553 !== null, "PREFS553: original clipped input point exists before observation");
            const receipt553 = gui407_nativeReceipt(button553, preferences, point553);
            const bindings553 = [], counts553 = {pressed:0, pressedChanged:0, released:0, clicked:0, canceled:0, checkedChanged:0, skillSourcesChanged:0}, samples553 = {}, errors553 = {};
            let sequence553 = 0;
            function current553() {
                return lives553.every(life => life === null || alive313(life)) && receipt553.current()
                    && row553.sourceId === "builtin" && row553.original === controller553;
            }
            sample553 = function(stage) {
                const current = current553();
                const facts = {sequence: sequence553++, currentOriginal: current,
                    alive: lives553.map(life => life === null || alive313(life))};
                try { if (current) {
                    const gesture = button553.gesture;
                    facts.pressed = button553.pressed; facts.checked = button553.checked;
                    facts.enabled = button553.enabled; facts.rowEnabled = row553.model.enabled;
                    facts.presentation = row553.presentation; facts.canCancel = controller553.canCancel;
                    const sourceError = controller553.skillSourceError;
                    facts.sourceErrorPresent = typeof sourceError === "string" && sourceError.length > 0;
                    facts.gesturePresent = gesture !== null;
                    facts.gestureOwnerCurrent = gesture !== null && gesture.owner === controller553;
                    facts.gestureIdCurrent = gesture !== null && gesture.id === row553.sourceId;
                    facts.gesturePresentationCurrent = gesture !== null && gesture.presentation === row553.presentation;
                    facts.gestureDesiredEnabled = gesture !== null ? gesture.enabled : null;
                    facts.gestureRevisionPresent = gesture !== null && typeof gesture.revision === "string" && gesture.revision.length > 0;
                } else errors553.originalRetiredOrReplaced = true;
                } catch (error) { errors553.snapshot = true; facts.captureFailed = true; }
                counts553[stage] = (counts553[stage] || 0) + 1;
                if (!samples553[stage]) samples553[stage] = {first: facts};
                samples553[stage].last = facts;
                if (stage === "pressedChanged" && facts.pressed === true) counts553.pressed = (counts553.pressed || 0) + 1;
            };
            install553 = function() {
                for (const signal of ["pressedChanged", "released", "clicked", "canceled", "checkedChanged"]) {
                    const callback = function() { sample553(signal); };
                    button553[signal].connect(callback);
                    bindings553.push({object:button553, life:lives553[0], signal:signal, callback:callback});
                }
                const callback = function() { sample553("skillSourcesChanged"); };
                controller553.skillSourcesChanged.connect(callback);
                bindings553.push({object:controller553, life:lives553[3], signal:"skillSourcesChanged", callback:callback});
                receipt553.sample("prefs553-before-original-click", false);
                verify(current553(), "PREFS553: original observed receiver remains current before SAME native click");
            };
            finish553 = function() {
                let receiptOK = false;
                try { receiptOK = receipt553.finish("prefs553-after-original-click-and-assertion"); }
                catch (error) { errors553.receiptFinish = true; }
                for (const pair of bindings553) {
                    try { disconnect313(pair.life, pair.object, pair.signal, pair.callback); }
                    catch (error) { errors553.disconnect = true; }
                }
                try { console.log("PREFS553_TOGGLE", JSON.stringify({originalIdentities:identities553,
                    counts:counts553, samples:samples553, errors:errors553, receiptOK:receiptOK,
                    compositeRevisionGetterNotRead:true, setterEntryOrReturnNotObserved:true})); }
                catch (error) { errors553.output = true; }
                try { return receiptOK && Object.keys(errors553).length === 0 && current553(); }
                catch (error) { return false; }
            };
        }
        let originalPassed553 = false;
        try {
            if (install553) { install553(); sample553("before-original-click"); }
            import265_click("preferences.ai.source.enabled.builtin");
            if (sample553) sample553("original-helper-return");
            compare(prefs417_rows()[0].enabled, false, "PREFS417: original native toggle really disables builtin");
            originalPassed553 = true;
        } finally {
            if (finish553) {
                const observed553 = finish553();
                if (originalPassed553) verify(observed553, "PREFS553: successful original click retains complete passive original-receiver evidence");
            }
        }
        const localUrl = Probe.referenceUrl("skills/collection");
        if (local) gui392_folder("skills/collection", false);
        const current = prefs417_rows();
        compare(current.length, local ? 2 : 1, "PREFS417: genuine Add admits exactly one source row");
        const added = local ? current.filter(row => !row.builtin) : [];
        if (local) {
            compare(added.length, 1, "PREFS417: actual new local row is unique");
            verify(added[0].id !== "builtin" && added[0].enabled, "PREFS417: enabled local uses app-issued opaque ID");
            compare(added[0].path, SettingsProof.localPath(localUrl), "PREFS417: actual path bonds genuine selected own folder");
        }
        prefs417_closePreferences(preferences);
        return added.length ? added[0].id : null;
    }
    function test_prefs417_sources_data() {
        return ["lifecycle", "malformed", "retirement", "local", "all-off", "stage-changed"].map(tag => ({tag: tag}));
    }
    function test_prefs417_sources(data) {
        const before = gui392_setup();
        const settings = EaGlobals.Vars.settingsFile;
        verify(SettingsProof.temporary(settings), "PREFS417 SETUP: actual settings store is owned fresh test storage");
        const fixture = JSON.parse(Probe.readReferenceFile("prefs417.json"));
        if (data.tag === "stage-changed") prefs419_storage();
        if (data.tag === "malformed") {
            const originalFacts = SettingsProof.settingFacts(settings, "Assistant", "skillSources");
            compare(originalFacts.type, "invalid", "PREFS417 SETUP: no preexisting source key is overwritten");
            try {
                SettingsProof.seed(settings, "Assistant", "skillSources", "{PREFS417 malformed original value");
                assistant.refreshSkillSources();
                verify(typeof assistant.skillSourceError === "string" && assistant.skillSourceError.length > 0,
                    "PREFS417: malformed/wrong-typed persisted sources report actionable assistant invalidity");
                const invalidRows = gui392_json(Probe.rows(assistant.skillSources));
                verify(invalidRows.every(row => row.enabled === false),
                    "PREFS417: explicit assistant-invalid source state has no implicitly enabled builtin fallback");
                gui392_unchanged(before);
                const code = 'import QtQuick; import edi.app; QtObject { property bool opened: false; '
                    + 'property bool projectPresent: Session.project !== null; property string sourceError: Session.assistant.skillSourceError; '
                    + 'Component.onCompleted: opened = Session.openProject(' + JSON.stringify(String(Probe.referenceUrl("project"))) + ') }';
                const restarted = SettingsProof.restart(code);
                verify(!("error" in restarted) && restarted.opened === true && restarted.projectPresent === true,
                    "PREFS417: fresh actual Session construction and ordinary project Open remain usable under malformed assistant settings");
                verify(typeof restarted.sourceError === "string" && restarted.sourceError.length > 0,
                    "PREFS417: fresh Session keeps actual assistant invalid rather than swallowing the bad preference");
                console.log("PREFS417_MALFORMED", JSON.stringify({restarted: restarted, mainOwner: identity313(before.life)}));
            } finally {
                SettingsProof.erase(settings, "Assistant", "skillSources");
                assistant.refreshSkillSources();
            }
            compare(assistant.skillSourceError, "", "PREFS417: explicit owned correction restores source usability");
            gui392_unchanged(before);
            return;
        }
        if (data.tag === "retirement") {
            const originalAssistant = assistant, originalLife = lifetime313(originalAssistant);
            const a = originalAssistant.beginSkillSourceSelection();
            verify(a.length > 0, "PREFS417: actual API token A exists before genuine owner replacement");
            verify(Session.openProject(Probe.referenceUrl("project")), "PREFS417: actual ordinary Open replaces original project owner");
            verify(Session.project !== before.owner, "PREFS417: token test reaches a genuinely different owner");
            const current = Session.assistant, currentLife = lifetime313(current);
            const b = current.beginSkillSourceSelection();
            verify(b.length > 0 && b !== a, "PREFS417: new owner obtains a distinct actual token B");
            const baseline = JSON.stringify(gui392_json(Probe.rows(current.skillSources)));
            if (alive313(originalLife)) {
                compare(originalAssistant.addSkillSource(a, Probe.referenceUrl("skills/collection")), false,
                    "PREFS417: exact retired token A cannot complete against replacement owner");
                originalAssistant.cancelSkillSourceSelection(a);
            }
            verify(alive313(currentLife) && Session.assistant === current,
                "PREFS417: old completion/cancel cannot replace new original receiver");
            compare(JSON.stringify(gui392_json(Probe.rows(current.skillSources))), baseline,
                "PREFS417: stale completion changes no configuration row");
            verify(current.addSkillSource(b, Probe.referenceUrl("skills/collection")),
                "PREFS417: unchanged actual B token remains usable after old-A cancellation");
            compare(gui392_json(Probe.rows(current.skillSources)).length, JSON.parse(baseline).length + 1,
                "PREFS417: positive B admits exactly one real local row");
            let reentries = 0, newOwner = null;
            function replaced417() {
                if (reentries) return;
                ++reentries;
                verify(Session.openProject(Probe.referenceUrl("project")), "PREFS417: actual source publication callback performs ordinary replacement");
                newOwner = Session.project;
            }
            current.skillSourcesChanged.connect(replaced417);
            try { current.setSkillSourceEnabled("builtin", false); }
            finally { disconnect313(currentLife, current, "skillSourcesChanged", replaced417); }
            compare(reentries, 1, "PREFS417: real source notification delivered synchronous replacement callback once");
            verify(newOwner !== null && Session.project === newOwner,
                "PREFS417: retiring caller cannot replace or retire genuine B after callback return");
            const replacement = gui392_json(Probe.rows(Session.assistant.skillSources));
            compare(replacement.filter(row => row.id === "builtin")[0].enabled, false,
                "PREFS417: factual committed config survives, without stale caller reverting builtin into B");
            compare(visible185_values(newOwner), before.values, "PREFS417: replacement keeps exact independent loaded scientific values/free/SUs");
            compare(visible185_inputs(newOwner), before.inputs, "PREFS417: replacement keeps all original measured triples/weights/exclusions/links");
            compare(relation245_declarations(newOwner), before.relations, "PREFS417: source callback cannot alter declarations");
            compare(import265_owner(newOwner), before.metadata, "PREFS417: same-file replacement preserves original metadata/settings/path");
            compare(newOwner.canUndo, before.undo, "PREFS417: source publication cannot manufacture scientific Undo");
            compare(newOwner.modified, before.modified, "PREFS417: configuration callback creates no scientific dirty state");
            verify(!newOwner.fit.running, "PREFS417: source configuration never starts a scientific fit");
            console.log("PREFS417_RETIREMENT", JSON.stringify({a: a, b: b, reentries: reentries, rows: replacement}));
            return;
        }
        const local = prefs417_configure(data.tag !== "all-off", data.tag === "lifecycle");
        if (data.tag === "lifecycle") {
            const preferences = prefs417_preferences();
            const initial = JSON.stringify(prefs417_rows());
            const revision = assistant.skillSourceRevision;
            verify(typeof revision === "string" && revision.length > 0, "PREFS417: actual configuration revision is a nonempty opaque identity");
            assistant.refreshSkillSources();
            compare(assistant.skillSourceRevision, revision, "PREFS417: unchanged reload does not retire the actual configuration revision");
            compare(JSON.stringify(prefs417_rows()), initial, "PREFS417: unchanged ordinary reload preserves all exact row identities/configuration");
            gui392_folder("skills/collection", true);
            compare(JSON.stringify(prefs417_rows()), initial, "PREFS417: actual FolderDialog Cancel preserves exact rows");
            const original = prefs421_declarations(JSON.parse(assistant.contextPreview)); prefs417_expected(original, "local");
            verify(SettingsProof.write(Probe.referenceUrl("skills/collection"), "gui392-alpha/SKILL.md", fixture.alphaB),
                "PREFS417: own source changes to independently declared lawful B");
            const changed = prefs421_declarations(JSON.parse(assistant.contextPreview));
            compare(JSON.stringify(changed.map(row => row.sha256).sort()), JSON.stringify([fixture.alphaBSha256,fixture.betaSha256].sort()),
                "PREFS421: actual public declaration observes independently hashed captured B, not cached A");
            verify(SettingsProof.write(Probe.referenceUrl("skills/collection"), "gui392-alpha/SKILL.md", fixture.alphaA),
                "PREFS417: own source is genuinely restored to original A");
            const restored = prefs421_declarations(JSON.parse(assistant.contextPreview)); prefs417_expected(restored, "local");
            const staleRevision = assistant.skillSourceRevision;
            import265_click("preferences.ai.source.enabled." + local);
            import265_click("preferences.ai.source.enabled." + local);
            const sameAgain = JSON.stringify(prefs417_rows());
            verify(assistant.skillSourceRevision !== staleRevision,
                "PREFS417: actual config A→B→A creates a new composite operation identity");
            compare(assistant.removeSkillSource(local, staleRevision), false,
                "PREFS417: exact stale pre-transition row revision cannot authorize current Remove");
            compare(JSON.stringify(prefs417_rows()), sameAgain,
                "PREFS417: refused stale row operation preserves every current descriptor");
            import265_click("preferences.ai.source.enabled." + local);
            compare(prefs421_declarations(JSON.parse(assistant.contextPreview)).length, 0,
                "PREFS417: disabling actual local plus builtin produces zero instructions");
            const disabled = gui392_sourceControl("preferences.ai.source.enabled." + local);
            verify(disabled.Accessible.checkable && !disabled.Accessible.checked
                && disabled.Accessible.name === "Enable this skill source", "PREFS417: native accessibility reflects actual disabled state");
            const persisted = SettingsProof.settingFacts(settings, "Assistant", "skillSources");
            verify(persisted.type !== "invalid", "PREFS417: native source action persists in actual original app store");
            assistant.refreshSkillSources();
            compare(prefs417_rows().filter(row => row.id === local)[0].enabled, false,
                "PREFS417: disabled state persists through explicit ordinary reload");
            import265_click("preferences.ai.source.remove." + local);
            compare(prefs417_rows().length, 1, "PREFS417: genuine Remove leaves only protected builtin");
            prefs417_closePreferences(preferences);
            console.log("PREFS417_LIFECYCLE", JSON.stringify({original: original, changed: changed, restored: restored, rows: prefs417_rows()}));
            gui392_unchanged(before); return;
        }
        // Existing actual signed-out header, no connected-email approval workaround.
        Ui.click(this, Probe, window, "assistant.connection");
        const dialog = ux356_dialog(); tryCompare(dialog, "opened", true, 2000,
            "PREFS417: original native sign-in/disclosure receiver is genuinely open");
        const approved = prefs421_declarations(gui392_json(dialog.disclosedContext));
        prefs417_expected(approved, data.tag === "all-off" ? "empty" : "local");
        console.log("PREFS417_APPROVED", JSON.stringify({tag:data.tag,skills:approved}));
        gui392_button(dialog.standardButton(Dialog.Ok), dialog);
        report187_ready("prefs417-current-sources", false);
        tryCompare(dialog, "visible", false, 2000, "PREFS417: actual original approval completes native exit");
        const approvedRevision = assistant.skillSourceRevision;
        const consentBefore = assistant.contextConsentRequired;
        assistant.refreshSkillSources();
        compare(assistant.skillSourceRevision, approvedRevision,
            "PREFS417: unchanged source reload preserves exact approved configuration identity");
        compare(assistant.contextConsentRequired, consentBefore,
            "PREFS417: unchanged reload does not invent a new consent requirement");
        if (data.tag === "stage-changed") {
            compare(assistant.lastError, "", "PREFS417 SETUP: actual original backend is healthy before stage attack");
            verify(assistant.connected && !assistant.contextConsentRequired,
                "PREFS417 SETUP: genuine original account and A approval are ready before attack");
            verify(SettingsProof.write(Probe.referenceUrl(""), "prefs417-arm", "PREFS417 original stage interval"),
                "PREFS417: arm only owned provider fixture after actual ready/approval, not during bootstrap");
            assistant.refreshUsage(); // Genuine existing optional-read transport entrance.
            tryVerify(() => Probe.readReferenceFile("prefs417-mutated").length > 0, 2000,
                "PREFS417: actual provider channel reached recorded A→B stage change before SAME original Send");
        }
        Ui.click(this, Probe, window, "assistant.composer"); visible185_type("PREFS417 exact current source request");
        Ui.click(this, Probe, window, "assistant.send");
        if (data.tag === "stage-changed") {
            tryVerify(() => !assistant.canCancel && !assistant.showingActions && assistant.lastError.length > 0, 2000,
                "PREFS417: SAME original real Send refuses changed staged instructions before inference");
            console.log("PREFS417_STAGE_REFUSAL", JSON.stringify({error:assistant.lastError,owner:identity313(before.life)}));
            gui392_unchanged(before); return;
        }
        tryVerify(() => assistant.canCancel, 2000, "PREFS417: original current request really reaches held transport");
        const busy = JSON.stringify(prefs417_rows());
        compare(assistant.setSkillSourceEnabled("builtin", true), false,
            "PREFS417: actual active work cannot mutate source configuration");
        compare(JSON.stringify(prefs417_rows()), busy, "PREFS417: refused busy config leaves every row/ID exact");
        assistant.refreshUsage();
        tryVerify(() => !assistant.canCancel && Probe.rows(assistant.messages).some(row => row.kind === "assistant"
            && row.status === "completed" && row.text === "Original offline reply"), 2000,
            "PREFS417: exact real acknowledged original reply completes once before preservation");
        console.log("PREFS417_SENT", JSON.stringify({tag:data.tag,approved:approved,skills:prefs421_declarations(JSON.parse(assistant.contextPreview))}));
        gui392_unchanged(before);
    }
    // PREFS419: actual original public publications, same-stack observations (no timer repair).
    function prefs419_storage() {
        const receipt = {application: Qt.application.name, organization: Qt.application.organization,
            app_local_data: SettingsProof.localPath(StandardPaths.writableLocation(StandardPaths.AppLocalDataLocation))};
        verify(/^acceptance-[0-9a-f]{64}$/.test(receipt.application)
            && receipt.organization === "EdiIndependentAcceptance" && receipt.app_local_data.length > 0,
            "PREFS419 SETUP: public Qt storage query belongs exact original isolated test application");
        verify(SettingsProof.write(Probe.referenceUrl(""), "prefs419-storage.json", JSON.stringify(receipt)),
            "PREFS419 SETUP: only own reference receipt conveys actual application-local storage to owned peer");
        console.log("PREFS419_STORAGE", JSON.stringify(receipt));
    }
    // Qt6.11 automatically bridges QByteArray to ArrayBuffer and QString to string.
    // Preserve the original native values for seed; only the observation gets projected.
    function prefs421_opaque(value) {
        if (typeof value === "string") {
            verify(value.length > 0, "PREFS421 SETUP: actual native QString setting is nonempty");
            return {carrier:"string",value:value};
        }
        verify(value instanceof ArrayBuffer && value.byteLength > 0,
            "PREFS421 SETUP: actual opaque byte setting is a nonempty native ArrayBuffer, not enumerable JSON or a length-shaped object");
        const view = new Uint8Array(value), bytes = [];
        for (let i=0;i<view.length;++i) bytes.push(view[i]);
        return {carrier:"ArrayBuffer",bytes:bytes};
    }
    function prefs419_configs(local, settings) {
        verify(assistant.setSkillSourceEnabled(local, false),
            "PREFS419 SETUP: ordinary source operation constructs valid independent all-off configuration B");
        compare(prefs417_rows().filter(row => row.id === local)[0].enabled, false,
            "PREFS419 SETUP: actual B meaning is observed from public row, not decoded settings schema");
        const b = SettingsProof.value(settings, "Assistant", "skillSources");
        const bProjection = prefs421_opaque(b);
        verify(assistant.setSkillSourceEnabled(local, true),
            "PREFS419 SETUP: ordinary source operation restores valid independent local configuration A");
        const a = SettingsProof.value(settings, "Assistant", "skillSources");
        compare(prefs417_rows().filter(row => row.id === local)[0].enabled, true,
            "PREFS421 SETUP: actual A meaning is independently observed after the real native operation");
        const aProjection = prefs421_opaque(a);
        compare(aProjection.carrier, bProjection.carrier,
            "PREFS421 SETUP: ordinary writer retains the same actual native carrier for both lawful settings");
        compare(JSON.stringify(prefs421_opaque(b)), JSON.stringify(bProjection),
            "PREFS421 SETUP: original opaque B bytes remain intact across ordinary A restoration");
        verify(JSON.stringify(aProjection) !== JSON.stringify(bProjection),
            "PREFS421 SETUP: actual native writer produced distinct contents-preserving opaque lawful A/B values");
        return {a:a,b:b};
    }
    function prefs419_state(receiver) {
        return {state:receiver.state,error:receiver.lastError,connected:receiver.connected,
            account:gui392_json(receiver.account),skills:gui392_json(Probe.rows(receiver.skills)),
            selectedSkill:receiver.selectedSkill,pendingPlan:gui392_json(receiver.pendingPlan),pendingQuestion:gui392_json(receiver.pendingQuestion),model:receiver.selectedModel,effort:receiver.selectedEffort,
            messages:gui392_json(Probe.rows(receiver.messages)),files:gui392_json(Probe.rows(receiver.selectedFiles)),
            canCancel:receiver.canCancel,showingActions:receiver.showingActions};
    }
    function test_prefs419_sources_data() {
        return ["publication", "send-retirement"].map(tag => ({tag:tag}));
    }
    function test_prefs419_sources(data) {
        const before = gui392_setup(), settings = EaGlobals.Vars.settingsFile;
        verify(SettingsProof.temporary(settings), "PREFS419 SETUP: only actual fresh owned settings store is changed");
        const local = prefs417_configure(true), stored = prefs419_configs(local, settings);
        const original = assistant, originalLife = lifetime313(original), originalOwner = before.owner;
        const oldIdentity = identity313(originalLife);
        if (data.tag === "publication") {
            compare(original.connected, false, "PREFS419 SETUP: helper-owned account retirement is reached from genuinely signed-out original owner");
            const account = JSON.stringify(gui392_json(original.account));
            Ui.click(this, Probe, window, "assistant.connection");
            const dialog = ux356_dialog(), dialogLife = lifetime313(dialog);
            tryCompare(dialog, "opened", true, 2000, "PREFS419 SETUP: original live consent offer exists before source change");
            verify(dialog.assistant === original, "PREFS419 SETUP: original consent property bindings belong exact original receiver");
            prefs417_expected(prefs421_declarations(gui392_json(dialog.disclosedContext)), "local");
            const events = [], returns = []; let phase = "", inspecting = false;
            function published419() {
                if (!phase || inspecting) return;
                verify(alive313(originalLife) && Session.assistant === original && Session.project === originalOwner,
                    "PREFS419: actual context notifier is delivered on original receiver/owner, never replacement authority");
                inspecting = true;
                try {
                    let raw = null, parseError = null;
                    try { raw = original.contextPreview; JSON.parse(raw); }
                    catch (error) { parseError = String(error); }
                    events.push({phase:phase,raw:raw,parseError:parseError,
                        consent:original.contextConsentRequired,sourceError:original.skillSourceError,
                        account:gui392_json(original.account),owner:identity313(before.life)});
                } finally { inspecting = false; }
            }
            function returned419(label, empty, invalid) {
                // FIRST observation at outer API return; no rendering/poll/queued timer between mutation and proof.
                verify(events.some(event => event.phase === label),
                    "PREFS419: actual contextPreviewChanged publication occurs synchronously before " + label + " returns");
                verify(alive313(originalLife) && alive313(before.life) && Session.assistant === original
                    && Session.project === originalOwner && alive313(dialogLife) && dialog.assistant === original,
                    "PREFS419: reload/config publication retains exact live original property owners");
                const bound = gui392_json(dialog.disclosedContext);
                const declarations = prefs421_declarations({skills:gui392_json(dialog.skills)});
                prefs417_expected(declarations, empty ? "empty" : "local");
                verify(original.contextConsentRequired === true,
                    "PREFS419: changed/invalid signed-out source projection remains unapproved before any timer repair");
                verify(invalid ? original.skillSourceError.length > 0 : original.skillSourceError === "",
                    "PREFS419: invalid source error versus healthy correction is a mandatory actual public fact");
                if (invalid) verify(gui392_json(Probe.rows(original.skillSources)).every(row => row.enabled === false),
                    "PREFS419: invalid reload cannot fall back to enabled builtin/source rows");
                compare(JSON.stringify(gui392_json(original.account)), account,
                    "PREFS419: helper-owned signed-out transition does not become a different account identity");
                returns.push({phase:label,context:bound,declarations:declarations,consent:original.contextConsentRequired,
                    sourceError:original.skillSourceError,account:gui392_json(original.account)});
            }
            original.contextPreviewChanged.connect(published419);
            try {
                phase = "native-off";
                verify(original.setSkillSourceEnabled(local, false), "PREFS419: real explicit configuration commit reaches helper-owned transition");
                returned419(phase,true,false);
                phase = "native-on";
                verify(original.setSkillSourceEnabled(local, true), "PREFS419: unchanged owner may lawfully restore local instructions");
                returned419(phase,false,false);
                phase = "reload-off";
                SettingsProof.seed(settings,"Assistant","skillSources",stored.b);
                original.refreshSkillSources();
                returned419(phase,true,false);
                phase = "invalid";
                SettingsProof.seed(settings,"Assistant","skillSources","{PREFS419 invalid external configuration");
                original.refreshSkillSources();
                returned419(phase,true,true);
                phase = "correction";
                SettingsProof.seed(settings,"Assistant","skillSources",stored.a);
                original.refreshSkillSources();
                returned419(phase,false,false);
                phase = "";
                const revision = original.skillSourceRevision, context = JSON.stringify(gui392_json(dialog.disclosedContext));
                original.refreshSkillSources();
                compare(original.skillSourceRevision, revision, "PREFS419: unchanged good reload remains same actual configuration revision");
                compare(JSON.stringify(gui392_json(dialog.disclosedContext)), context,
                    "PREFS419: unchanged good reload preserves original current bound disclosure");
                console.log("PREFS419_RESULT",JSON.stringify({tag:data.tag,baselineAccount:JSON.parse(account),events:events,returns:returns,owner:identity313(before.life)}));
            } finally {
                disconnect313(originalLife,original,"contextPreviewChanged",published419);
                SettingsProof.seed(settings,"Assistant","skillSources",stored.a);
                if (alive313(originalLife) && Session.project === originalOwner) original.refreshSkillSources();
            }
            if (alive313(dialogLife) && dialog.opened) gui392_button(dialog.standardButton(Dialog.Cancel),dialog);
            gui392_unchanged(before); return;
        }
        // Real original public Send entrance. The source reload must occur INSIDE this call.
        gui392_signIn();
        verify(original.connected && !original.contextConsentRequired && !original.canCancel,
            "PREFS419 SETUP: actual healthy original A account/approval is ready, not a disconnected refusal");
        Ui.click(this,Probe,window,"assistant.composer");
        visible185_type("PREFS419 original source-dependent request");
        const field = Ui.find(window,"assistant.composer"), fieldLife = lifetime313(field);
        compare(field.text,"PREFS419 original source-dependent request", "PREFS419 SETUP: original real editor owns literal request before callback");
        let inside = false, replacements = 0, callbackCount = 0, bOwner = null, bReceiver = null,
            bLife = null, bOwnerLife = null, bState = null, bDraft = null, returned = null;
        function replace419() {
            ++callbackCount;
            if (replacements) return;
            verify(inside, "PREFS419: actual original source notification reaches synchronous public submitDraft interval");
            ++replacements;
            verify(Session.openProject(Probe.referenceUrl("project")), "PREFS419: genuine ordinary owner replacement occurs in original Send callback");
            bOwner = Session.project; bReceiver = Session.assistant;
            bLife = lifetime313(bReceiver); bOwnerLife = lifetime313(bOwner);
            verify(bOwner !== originalOwner, "PREFS419: callback genuinely creates B, never reuses A owner proof");
            bState = prefs419_state(bReceiver);
            verify(alive313(fieldLife), "PREFS419: actual original composer receiver survives for B draft observation");
            bDraft = field.text;
        }
        original.skillSourcesChanged.connect(replace419);
        try {
            // Opaque valid B was produced by a genuine ordinary source action; schema is never guessed.
            SettingsProof.seed(settings,"Assistant","skillSources",stored.b);
            inside = true;
            try { returned = original.submitDraft("PREFS419 original source-dependent request"); }
            finally { inside = false; }
        } finally { disconnect313(originalLife,original,"skillSourcesChanged",replace419); }
        compare(replacements,1, "PREFS419: actual original public Send reaches one genuine replacement callback, not early-refusal pass");
        compare(returned,"", "PREFS419: retired original public Send cannot return any admitted user-row authority");
        verify(alive313(bLife) && alive313(bOwnerLife) && Session.assistant === bReceiver && Session.project === bOwner,
            "PREFS419: outer original Send cannot retire/replace callback-created B");
        compare(JSON.stringify(prefs419_state(bReceiver)),JSON.stringify(bState),
            "PREFS419: no stale Send refusal/state/account/catalogue/model/message/file/action write reaches B after callback return");
        verify(alive313(fieldLife), "PREFS419: original editor remains live before exact B draft preservation observation");
        compare(field.text,bDraft,"PREFS419: old Send cannot clear or commit callback-created B current draft");
        compare(visible185_values(bOwner),before.values,"PREFS419: exact independent same-file physical values/free/PRESENT SUs survive callback");
        compare(visible185_inputs(bOwner),before.inputs,"PREFS419: every original measured triple/weight/exclusion/phase link survives callback");
        compare(relation245_declarations(bOwner),before.relations,"PREFS419: no old Send changes scientific aliases/constraints");
        compare(import265_owner(bOwner),before.metadata,"PREFS419: same-file B preserves original source/path/settings/metadata");
        compare(bOwner.canUndo,before.undo,"PREFS419: source callback creates no scientific Undo");
        compare(bOwner.modified,before.modified,"PREFS419: source callback creates no scientific dirty state");
        verify(!bOwner.fit.running,"PREFS419: source-dependent Send cannot start a scientific fit");
        console.log("PREFS419_RESULT",JSON.stringify({tag:data.tag,callbacks:callbackCount,replacements:replacements,
            originalReceiver:oldIdentity,originalOwner:identity313(before.life),newOwner:identity313(bOwnerLife),returned:returned,before:bState,after:prefs419_state(bReceiver),draft:bDraft}));
    }
    // PUBLIC381/381v2: original scalar widgets, current physical items, one RPC.
    function array450_physical(project) {
        const all = Probe.objectsWithProperty(project, "refinable").filter(parameter =>
            typeof parameter.path === "string" && typeof parameter.value === "number"
            && typeof parameter.fittable === "boolean");
        verify(all.length > 3 && new Set(all.map(parameter => parameter.path)).size === all.length,
            "ARRAY450 SETUP: actual physical ParameterItems, not only the refinable Analysis projection, are unique");
        return all;
    }
    function array450_values(parameters) {
        return JSON.stringify(parameters.map(parameter => [parameter.path, parameter.value, parameter.free,
            parameter.hasUncertainty, parameter.uncertainty]).sort((a,b) => a[0].localeCompare(b[0])));
    }
    function array450_parameter(parameters, path) {
        const found = parameters.filter(parameter => parameter.path === path);
        compare(found.length, 1, "ARRAY450: independent literal native path resolves one current physical object");
        return found[0];
    }
    function array450_activity(callId, previousIds) {
        const found = Probe.rows(assistant.messages).filter(row => !previousIds.has(row.id)
            && row.kind === "activity" && row.payload && row.payload.id === callId);
        verify(found.length <= 1, "ARRAY450: one genuine new activity belongs to the exact original call");
        if (!found.length || !["completed", "failed"].includes(found[0].status)) return null;
        verify(typeof found[0].id === "string" && found[0].id.length > 0,
            "ARRAY450: settled activity has an actual public identity");
        return found[0];
    }
    function test_array450_ordered_original_controls_data() {
        return ["normal-values", "singleton", "values", "free", "all-noop-values", "all-noop-free",
            "mixed-values", "invalid-last", "manual-draft", "stop", "takeover"].map(tag => ({tag:tag}));
    }
    function test_array450_ordered_original_controls(data) {
        const specification = JSON.parse(Probe.readReferenceFile("array450.json"));
        compare(specification.case, data.tag, "ARRAY450 SETUP: exact independent request/configuration pair is predeclared");
        verify(Session.openProject(Probe.referenceUrl("project")), "ARRAY450 SETUP: owned lawful original project opens normally");
        const project = Session.project, ownerLife = lifetime313(project);
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment), 10000,
            "ARRAY450 SETUP: real default-table calculation is current before history setup");
        let parameters = array450_physical(project);
        let la = array450_parameter(parameters,"structure.atom_sites[La].adp_iso");
        let ba = array450_parameter(parameters,"structure.atom_sites[Ba].adp_iso");
        let co = array450_parameter(parameters,"structure.atom_sites[Co].adp_iso");
        let wavelength = array450_parameter(parameters,"experiment.instrument.setup_wavelength");
        let cell = array450_parameter(parameters,"structure.cell.length_a");
        compare([la.value,ba.value,co.value,wavelength.value,cell.value],[0.5,0.5,0.5,1.494,3.88],
            "ARRAY450 SETUP: independently committed literal physical operands are present");
        compare([la.free,ba.free,co.free],[true,true,true], "ARRAY450 SETUP: original present-zero-SU ADP flags start free");
        const initialValues = array450_values(parameters), inputs = visible185_inputs(project);
        const declarations = relation245_declarations(project), shape = relation246_shape(project);
        toggle(); gui392_signIn();
        verify(!assistant.contextConsentRequired && assistant.connected, "ARRAY450 SETUP: actual managed current disclosure is admitted");
        compare(assistant.showActions,false,"ARRAY450 SETUP: independent prior edit uses genuine default normal mode");
        const account = assistant.connectionLabel, catalog = JSON.stringify(Probe.rows(assistant.models));
        // A separate real normal native edit establishes a recorded sentinel.
        // It is setup, never credited as visible array input or scientific proof.
        const sentinelIds = new Set(Probe.rows(assistant.messages).map(row => row.id));
        assistant.send("Original450 establish the independent prior Undo sentinel");
        tryVerify(() => array450_activity("array450-sentinel",sentinelIds) !== null && !assistant.canCancel,10000,
            "ARRAY450 SETUP: genuine prior native RPC completes before the array is admitted");
        compare(array450_parameter(array450_physical(project),"experiment.instrument.setup_wavelength").value,1.495,
            "ARRAY450 SETUP: real ordinary native sentinel actually changed the CURRENT logical wavelength");
        verify(project.canUndo,"ARRAY450 SETUP: prior genuine edit owns actual recorded Undo");
        tryVerify(() => alive313(ownerLife) && Session.project === project && !project.calculating && Probe.computedCurrent(project.currentExperiment),10000,
            "ARRAY450 SETUP: actual prior science settles, no fabricated currentness");
        // The prior ordinary edit/calculation may refresh wrapper children.
        // Main-call identities are captured only now, from actual current objects.
        parameters=array450_physical(project);
        la=array450_parameter(parameters,"structure.atom_sites[La].adp_iso");
        ba=array450_parameter(parameters,"structure.atom_sites[Ba].adp_iso");
        co=array450_parameter(parameters,"structure.atom_sites[Co].adp_iso");
        wavelength=array450_parameter(parameters,"experiment.instrument.setup_wavelength");
        cell=array450_parameter(parameters,"structure.cell.length_a");
        const before = array450_values(parameters);
        const originals = new Map(parameters.map(parameter => [parameter.path,
            {value:parameter.value,free:parameter.free,hasUncertainty:parameter.hasUncertainty,uncertainty:parameter.uncertainty}]));
        const call = specification.calls[1], entries = call.arguments.values || call.arguments.flags;
        const requestedPaths=new Set(entries.map(entry => entry.path));
        const tracked=parameters.filter(parameter => requestedPaths.has(parameter.path));
        const lives=tracked.map(parameter => lifetime313(parameter));
        const originalPhysicalPaths=JSON.stringify(parameters.map(parameter => parameter.path).sort());
        if (data.tag !== "normal-values") {
            Ui.click(this,Probe,window,"assistant.showActions");
            verify(assistant.showActions,"ARRAY450: genuine original mode checkbox enables visible controls");
        }
        closeAssistant388();
        let draftField = null, draftLife = null, draftFocus = null, draftSelection = null;
        if (data.tag === "manual-draft") {
            visible185_page("structure"); Ui.click(this,Probe,window,"sideBar.tab.basic");
            Ui.expandGroup(this,Probe,window,"group.cell");
            draftField = Ui.control(Probe,window,"cell.length_a");
            verify(draftField !== null && draftField.item === cell && Ui.exposed(draftField),
                "ARRAY450 SETUP: original owned manual cell field is actually exposed");
            draftLife=lifetime313(draftField);Ui.click(this,Probe,window,draftField.objectName);
            visible185_type("3.901");
            compare(draftField.text,"3.901","ARRAY450 SETUP: genuine new numeric draft remains uncommitted");
            compare(draftField.assistantManualDraft,true,"ARRAY450 SETUP: original public field reports genuinely UNFINISHED user input");
            compare(array450_values(parameters),before,"ARRAY450 SETUP: typing has not changed science");
            draftFocus=window.activeFocusItem;draftSelection=[draftField.selectionStart,draftField.selectionEnd];
        }
        const slots=[], input=[], writes=[], navigation=[], dispatched610=[];
        const controls=new Set();let starts=0,fitStarts=0;
        function current() {
            verify(alive313(ownerLife) && Session.project === project && lives.every(alive313),
                "ARRAY450: every action/observation still belongs to the original live owner/items");
            const now=array450_physical(project);
            verify(JSON.stringify(now.map(parameter => parameter.path).sort()) === originalPhysicalPaths
                && tracked.every(parameter => now.includes(parameter)),
                "ARRAY450: the original requested physical members cannot be replaced behind a logical path/index");
        }
        function bind(object,signal,callback) {
            const life=lifetime313(object);object[signal].connect(callback);slots.push({object:object,life:life,signal:signal,callback:callback});
        }
        function controlParameter(control) {
            if (typeof control.item !== "undefined" && parameters.includes(control.item)) return control.item;
            if (!control.objectName.startsWith("parameters.free.")) return null;
            for (let parent=control.parent;parent;parent=parent.parent)
                if (parameters.includes(parent.parameter)) return parent.parameter;
            return null;
        }
        function scan() {
            current();
            const candidates=Ui.itemsWithProperty(Ui.windowRoot(window),"objectName");
            for (const control of candidates) {
                if (controls.has(control)) continue;
                const name=control.objectName;
                const parameter=controlParameter(control);
                const value=parameter !== null && (name.startsWith("parameters.value.") || name.startsWith("instrument.") || name.startsWith("cell."));
                const free=parameter !== null && name.startsWith("parameters.free.");
                const filter=name === "parameters.nameFilter";
                const reset=name === "parameters.resetFilters";
                if (!value && !free && !filter && !reset) continue;
                controls.add(control);
                const life=lifetime313(control), identity=identity313(life);
                function received(kind) {
                    current();verify(alive313(life) && controlParameter(control) === parameter,
                        "ARRAY450: original input cannot move to a reused delegate/index/new parameter");
                    verify(control.visible && control.enabled && Ui.exposed(control),
                        "ARRAY450: receipt is from a genuinely exposed native control, not a hidden batch fallback");
                    const receipt={kind:kind,path:parameter ? parameter.path : null,name:name,identity:identity,
                        rect:rect(control),point:Ui.clickPoint(control),text:value || filter ? control.text : null,
                        checked:free ? control.checked : null};
                    if (filter || reset) navigation.push(receipt);else dispatched610.push(receipt);
                }
                if (reset) bind(control,"clicked",() => received("reset"));
                else if (free) bind(control,"toggled",() => received("free"));
                else bind(control,"textEdited",() => received(value ? "value" : "filter"));
            }
        }
        function stopObservers() {
            while (slots.length) {
                const slot=slots.pop();disconnect313(slot.life,slot.object,slot.signal,slot.callback);
            }
        }
        for (const parameter of [la,ba,co,wavelength,cell]) {
            const parameterLife=lifetime313(parameter);
            bind(parameter,"valueChanged",() => {current();verify(alive313(parameterLife),"ARRAY450: original value receipt is still live before dereference");writes.push({path:parameter.path,field:"value",value:parameter.value});});
            bind(parameter,"freeChanged",() => {current();verify(alive313(parameterLife),"ARRAY450: original flag receipt is still live before dereference");writes.push({path:parameter.path,field:"free",value:parameter.free});});
        }
        for (const name of ["appBar.tab.structure","appBar.tab.experiment","appBar.tab.analysis"]) {
            const control=item(name);bind(control,"clicked",() => {current();navigation.push({kind:"page-click",name:name});});
        }
        bind(window.appBarCentralTabs,"currentIndexChanged",() => {navigation.push({kind:"page-change",page:window.appBarCentralTabs.currentIndex});scan();});
        let point610=null;
        function move610(point){point610={x:point.x,y:point.y};scan();}
        function pressed610(){
            scan();if(!assistant.showingActions || !point610)return;
            verify(assistant.actionWindow===window);
            for(const control of Ui.itemsWithProperty(Ui.windowRoot(window),"objectName")) {
                const parameter=controlParameter(control);if(parameter===null || !Ui.exposed(control))continue;
                const name=control.objectName;
                const kind=name.startsWith("parameters.free.")?"free":
                    name.startsWith("parameters.value.") || name.startsWith("instrument.") || name.startsWith("cell.")?"value":null;
                if(kind===null)continue;
                const box=rect(control);if(point610.x<box[0] || point610.y<box[1] || point610.x>=box[0]+box[2] || point610.y>=box[1]+box[3])continue;
                const entry=entries.filter(e=>e.path===parameter.path);compare(entry.length,1);
                const desired=kind==="free"?entry[0].free:entry[0].value;
                verify(typeof desired!=="undefined" && (kind==="free"?parameter.free:parameter.value)!==desired,
                    "ARRAY610: actual scientific cue is a changed member of THIS original request, never a settled no-op");
                input.push({kind:kind,path:parameter.path,name:name,identity:identity313(lifetime313(control)),
                    rect:box,point:point610,before:kind==="free"?parameter.free:parameter.value});
            }
        }
        bind(assistant,"actionPointerShown",scan);bind(assistant,"actionPointerMoved",move610);bind(assistant,"actionPointerPressed",pressed610);
        bind(assistant,"showingActionsChanged",() => {if(assistant.showingActions)++starts;});
        bind(project.fit,"runningChanged",() => {if(project.fit.running)++fitStarts;});
        scan();
        const previous=new Set(Probe.rows(assistant.messages).map(row => row.id));
        const beforePage=window.appBarCentralTabs.currentIndex;
        const requestedPreference=Preferences.assistantShown;
        const budget=visible237_observationMs(entries.map(entry => ({path:entry.path,
            text:Object.prototype.hasOwnProperty.call(entry,"value") ? String(entry.value) : ""})));
        let manualToggles=0, stopped=false;
        try {
            // Existing direct Send entrance intentionally preserves an active manual draft.
            assistant.send("Original ordered visible array " + data.tag);
            if (["stop","takeover"].includes(data.tag)) {
                let second=null;
                tryVerify(() => {
                    const found=Ui.itemsWithProperty(Ui.page(window),"item").filter(control => control.item === ba
                        && control.objectName.startsWith("parameters.value.") && Ui.exposed(control));
                    second=found.length === 1 ? found[0] : null;
                    return assistant.showingActions && la.value === 0.6 && second !== null
                        && ba.value===0.5 && input.some(row => row.path === ba.path && row.kind === "value" && row.before===0.5);
                },budget,"ARRAY610 SETUP: first edit is applied and exact second original prewrite cue is pending before intervention");
                compare([ba.value,co.value],[0.5,0.5],"ARRAY450 SETUP: later native scientific writes have NOT occurred");
                if (data.tag === "stop") {
                    const stop=item("assistant.stopVisibleAction");
                    verify(stop.visible && stop.enabled && Ui.exposed(stop),"ARRAY450: original appbar Stop is genuinely actionable");
                    mouseClick(stop);stopped=true;
                } else {
                    const manual=visible185_free(ba),life=lifetime313(manual);
                    function toggled(){++manualToggles;}
                    manual.toggled.connect(toggled);
                    try {Ui.click(this,Probe,window,manual.objectName);}
                    finally {disconnect313(life,manual,"toggled",toggled);}
                    compare(manualToggles,1,"ARRAY450: exactly one genuine user checkbox toggle causes takeover");
                    compare(ba.free,false,"ARRAY450: the original manual receiver actually changes its own flag");
                }
            }
            tryVerify(() => array450_activity(call.call_id,previous) !== null && !assistant.canCancel && !assistant.showingActions,
                budget,"ARRAY450: exact original call/whole turn settles after real input, without retry or missing receipt");
            current();scan();
            const row=array450_activity(call.call_id,previous);
            compare(row.payload.tool,call.tool,"ARRAY450: retained result belongs to original tool");
            const initialRefusal=["invalid-last","manual-draft"].includes(data.tag);
            if (!initialRefusal) verify(typeof row.payload.nativeOutcome === "object" && row.payload.nativeOutcome !== null,
                "ARRAY450: genuine supported result is admitted native work, never setup refusal as positive");
            compare(fitStarts,0,"ARRAY450: parameter/free arrays never invent a fit worker");
            compare(visible185_inputs(project),inputs,"ARRAY450: all measured coordinates/intensities/SUs/weights/exclusions/links remain exact");
            compare(relation245_declarations(project),declarations,"ARRAY450: aliases/constraints remain exact");
            compare(relation246_shape(project),shape,"ARRAY450: physical sites/composition/fractional operands remain exact");
            compare(assistant.connectionLabel,account,"ARRAY450: original managed account remains unchanged");
            compare(JSON.stringify(Probe.rows(assistant.models)),catalog,"ARRAY450: catalog is not replaced to repair native work");
            verify(assistant.connected,"ARRAY450: actual managed transport remains healthy after the original call");
            const finalInput=input.slice(),finalWrites=writes.slice(),finalNavigation=navigation.slice();
            compare(dispatched610.filter(r=>r.kind==="value").length,0,"ARRAY610: delegated scalar mutation dispatches no scientific keys");
            compare(dispatched610.filter(r=>r.kind==="free").length,manualToggles,"ARRAY610: only genuine test-user takeover can dispatch a checkbox toggle");
            stopObservers();
            const noOp=data.tag.startsWith("all-noop-");
            const changed=data.tag === "normal-values" || data.tag === "values" ? [la,wavelength,cell]
                : data.tag === "free" ? [la,co] : data.tag === "mixed-values" ? [ba]
                : ["singleton","stop","takeover"].includes(data.tag) ? [la] : [];
            if (initialRefusal || noOp) {
                compare(array450_values(array450_physical(project)),before,"ARRAY450: initial refusal/all-noop preserves every actual physical value/free/SU");
                compare(finalInput.length,0,"ARRAY450: refusal/noop happens before ANY scientific key/toggle input");
                compare(finalWrites.length,0,"ARRAY450: refusal/noop creates no native scientific write");
                compare(finalNavigation.length,0,"ARRAY450: refusal/noop precedes navigation/filter input");
                compare(window.appBarCentralTabs.currentIndex,beforePage,"ARRAY450: actual original page is unchanged");
            } else {
                for (const parameter of changed) {
                    const entry=entries.find(value => value.path === parameter.path);
                    if (call.tool === "set_free") compare(parameter.free,entry.free,"ARRAY450: literal requested flag is actually adopted");
                    else compare(parameter.value,entry.value,"ARRAY450: literal requested physical value is actually adopted");
                    const field=call.tool === "set_free" ? "free" : "value";
                    compare(JSON.stringify(finalWrites.filter(receipt => receipt.path === parameter.path && receipt.field === field).map(receipt => receipt.value)),
                        JSON.stringify([entry[field]]),"ARRAY450: one actual changed member publishes one literal scientific edit, never intermediate numeric drafts");
                    if (data.tag !== "normal-values") compare(finalInput.filter(receipt => receipt.path === parameter.path
                        && receipt.kind === (call.tool === "set_free" ? "free" : "value") && receipt.before!==entry[field]).length,1,
                        "ARRAY610: every changed entry has ONE exposed prewrite native target cue AND its exact actual app-method effect");
                }
                if (data.tag !== "normal-values") verify(starts > 0,"ARRAY450: changed visible array genuinely entered original helper presentation");
                else compare([starts,finalInput.length,finalNavigation.length],[0,0,0],
                    "ARRAY450: unchanged normal mode remains truly programmatic/atomic without decorative widget input");
                const noopPaths=entries.filter(entry => {
                    const old=originals.get(entry.path);
                    return old && (call.tool === "set_free" ? old.free === entry.free : old.value === entry.value);
                }).map(entry => entry.path);
                verify(finalInput.every(receipt => !noopPaths.includes(receipt.path)) && finalWrites.every(receipt => !noopPaths.includes(receipt.path)),
                    "ARRAY450: confirmed noop entries create neither original native input nor a scientific write");
                const allowed=new Set(changed.map(parameter => parameter.path));
                if (allowed.has(cell.path)) for(const suffix of ["b","c"]) {
                    const follower=array450_parameter(parameters,"structure.cell.length_"+suffix);
                    compare(follower.value,cell.value,"ARRAY450: original cubic cell equality remains scientifically valid");allowed.add(follower.path);
                }
                if(data.tag === "takeover")allowed.add(ba.path);
                for(const parameter of array450_physical(project))if(!allowed.has(parameter.path)) {
                    const original=originals.get(parameter.path);
                    compare(JSON.stringify([parameter.value,parameter.free,parameter.hasUncertainty,parameter.uncertainty]),
                        JSON.stringify([original.value,original.free,original.hasUncertainty,original.uncertainty]),
                        "ARRAY450: every unrelated physical value/free/PRESENT-SU remains exact");
                }
                if(data.tag === "mixed-values")verify(finalInput.every(receipt => receipt.path === ba.path),
                    "ARRAY450: settled noop entries never borrow input/Undo from the one actual changed member");
                if(["stop","takeover"].includes(data.tag)) {
                    compare([ba.value,co.value],[0.5,0.5],"ARRAY450: retiring original input cannot write B or continue to C");
                    compare(Preferences.assistantShown,requestedPreference,"ARRAY450: Stop/takeover preserves the stored sidebar request");
                    if(data.tag === "stop")verify(stopped,"ARRAY450: incomplete prefix is caused by actual original Stop");
                }
            }
            if(draftField !== null) {
                verify(alive313(draftLife),"ARRAY450: original manual draft field survives before inspection");
                compare(draftField.text,"3.901","ARRAY450: refused request preserves exact newer manual spelling");
                compare(draftField.assistantManualDraft,true,"ARRAY450: refused native request cannot finish/authorize the user's original draft");
                compare(window.activeFocusItem,draftFocus,"ARRAY450: admission never blurs original manual draft");
                compare([draftField.selectionStart,draftField.selectionEnd],draftSelection,"ARRAY450: original manual selection survives");
            }
            const changedPaths=changed.map(parameter => parameter.path);
            const finalValues=array450_values(array450_physical(project));
            const users=Probe.rows(assistant.messages).filter(value => value.kind === "user").map(value => ({id:value.id,text:value.text,status:value.status}));
            console.log("ARRAY450_RESULT",JSON.stringify({case:data.tag,input:finalInput,writes:finalWrites,navigation:finalNavigation,dispatched610:dispatched610,
                starts:starts,fitStarts:fitStarts,values:JSON.parse(finalValues),users:users,
                calculationAtPublication:project.calculating,nativeOutcome:row.payload.nativeOutcome || null,
                sameOwner:Session.project === project,manualToggles:manualToggles}));
            if(data.tag === "takeover") {
                verify(window.assistantManualTakeover,"ARRAY450: original native manual-input policy actually retains control for the user");
                return; // User-toggle history shape is not promised; do not invent a manual Undo.
            }
            if(draftField !== null) {
                keyClick(Qt.Key_Escape);
                compare(cell.value,3.88,"ARRAY450: genuine Escape cancels only uncommitted manual draft");
                compare(draftField.assistantManualDraft,false,"ARRAY450: original cancellation is FINISHED before the NEXT ordinary Undo input");
            }
            const undoCount=data.tag === "normal-values" ? 1 : changed.length;
            for(let index=0;index<undoCount;++index) {
                Ui.click(this,Probe,window,"appBar.button.undo");
                tryVerify(() => alive313(ownerLife) && Session.project === project && !project.calculating && Probe.computedCurrent(project.currentExperiment),10000,
                    "ARRAY450: each genuine ordinary Undo settles its actual native calculation");
                if(data.tag !== "normal-values") {
                    const path=changedPaths[changedPaths.length-1-index];
                    const restored=array450_parameter(array450_physical(project),path),original=originals.get(path);
                    compare(JSON.stringify([restored.value,restored.free,restored.hasUncertainty,restored.uncertainty]),
                        JSON.stringify([original.value,original.free,original.hasUncertainty,original.uncertainty]),
                        "ARRAY450: ordinary Undo restores exactly the most recent changed scalar, never a noop");
                }
            }
            compare(array450_values(array450_physical(project)),before,"ARRAY450: normal single Undo or per-control visible Undo restores ALL original physical operands");
            Ui.click(this,Probe,window,"appBar.button.undo");
            tryVerify(() => alive313(ownerLife) && Session.project === project && !project.calculating && Probe.computedCurrent(project.currentExperiment),10000,
                "ARRAY450: NEXT prior sentinel Undo genuinely settles");
            compare(array450_values(array450_physical(project)),initialValues,"ARRAY450: NEXT real Undo removes prior wavelength sentinel, proving no phantom noop/refusal history");
            compare(visible185_inputs(project),inputs,"ARRAY450: ordinary Undo preserves every supplied measured triple/SU");
            compare(relation245_declarations(project),declarations,"ARRAY450: Undo preserves original declarations");
        } finally {
            stopObservers();
            if(assistant.canCancel)assistant.cancel();
        }
    }
    // PUBLIC original category/model ownership, no recursive QObject discovery as membership proof.
    function array451_member(model,path) {
        const found=Probe.rows(model).filter(row => row.parameter && row.parameter.path === path);
        compare(found.length,1,"ARRAY451: exact CURRENT original model role owns one independent literal path");
        return found[0];
    }
    function array451_science(project) {
        const values=Probe.rows(project.parameters).map(row => [row.parameter.path,row.parameter.value,row.parameter.free,
            row.parameter.hasUncertainty,row.parameter.uncertainty]);
        verify(new Set(values.map(row => row[0])).size === values.length,"ARRAY451: original live parameter model paths are unique");
        return {values:values,inputs:visible185_inputs(project),relations:relation245_declarations(project),
            shape:relation246_shape(project),metadata:import265_owner(project),undo:project.canUndo,modified:project.modified};
    }
    function array451_activity(receiver,id,previous) {
        const found=Probe.rows(receiver.messages).filter(row => !previous.has(row.id) && row.kind === "activity"
            && row.payload && row.payload.id === id && ["completed","failed"].includes(row.status));
        verify(found.length <= 1,"ARRAY451: at most one completed original call row, no duplicate publication");
        return found.length ? found[0] : null;
    }
    function test_array451_original_member_data() {
        return ["hidden-change","hidden-noop","removed-noop","applied-replacement"].map(tag => ({tag:tag}));
    }
    function test_array451_original_member(data) {
        const spec=JSON.parse(Probe.readReferenceFile("array451.json"));
        compare(spec.case,data.tag,"ARRAY451 SETUP: original literal fixture and request inventory match");
        verify(Session.openProject(Probe.referenceUrl("project")),"ARRAY451 SETUP: normal public project reader admits owned lawful fixture");
        const project=Session.project,ownerLife=lifetime313(project),original=Session.assistant,receiverLife=lifetime313(original);
        tryVerify(() => !project.calculating && Probe.computedCurrent(project.currentExperiment),10000,
            "ARRAY451 SETUP: actual independent fixture calculation is Current before request admission");
        const initial=array451_science(project), la=array451_member(project.parameters,"structure.atom_sites[La].adp_iso").parameter;
        compare(la.value,0.5,"ARRAY451 SETUP: literal original La displacement value is independent of native response");
        const laPath=la.path,laLife=lifetime313(la),model=project.parameters,modelLife=lifetime313(model);
        toggle();gui392_signIn();
        verify(original.connected && !original.contextConsentRequired && !original.canCancel,
            "ARRAY451 SETUP: actual current account/disclosure and normal tool route are healthy, not setup-refusal positives");
        compare(original.showActions,false,"ARRAY451 SETUP: same lawful positive begins in ORIGINAL normal atomic mode");
        const account=original.connectionLabel,catalog=JSON.stringify(Probe.rows(original.models));
        const slots=[],events=[],navigation=[],writes=[];const controls=new Set();let fitStarts=0;
        function bind(object,signal,callback){const life=lifetime313(object);object[signal].connect(callback);slots.push({object:object,signal:signal,callback:callback,life:life});}
        function stop(){while(slots.length){const slot=slots.pop();disconnect313(slot.life,slot.object,slot.signal,slot.callback);}}
        function current(){verify(alive313(ownerLife) && Session.project === project && alive313(receiverLife) && Session.assistant === original,
            "ARRAY451: original scientific/request owner remains live before owned effects");}
        function scan(){
            current();
            for(const control of Ui.itemsWithProperty(Ui.windowRoot(window),"objectName")){
                if(controls.has(control))continue;
                const name=control.objectName;
                const parameter=typeof control.item !== "undefined" ? control.item : null;
                const numeric=parameter !== null && (name.startsWith("parameters.value.") || name.startsWith("instrument.") || name.startsWith("cell."));
                const isFree=name.startsWith("parameters.free.");
                const filter=name === "parameters.nameFilter",reset=name === "parameters.resetFilters";
                if(!numeric && !isFree && !filter && !reset)continue;
                controls.add(control);const life=lifetime313(control);
                function received(kind){
                    current();verify(alive313(life),"ARRAY451: receipt owns an original surviving receiver");
                    verify(control.visible && control.enabled && Ui.exposed(control),"ARRAY451: scientific input is genuinely exposed, not a hidden native shortcut");
                    const receipt={kind:kind,name:name,path:parameter ? parameter.path : null,identity:identity313(life),rect:rect(control),
                        point:Ui.clickPoint(control),text:numeric || filter ? control.text : null};
                    if(filter || reset)navigation.push(receipt);else events.push(receipt);
                }
                bind(control,reset ? "clicked" : isFree ? "toggled" : "textEdited",() => received(reset ? "reset" : isFree ? "free" : "text"));
            }
        }
        function watchScience(){for(const row of Probe.rows(project.parameters)){
            const parameter=row.parameter,life=lifetime313(parameter),path=parameter.path;
            bind(parameter,"valueChanged",() => {verify(alive313(life),"ARRAY451: original physical write receipt is live");writes.push({path:path,value:parameter.value});});
        }}
        function send(index){
            current();const call=spec.calls[index],before=new Set(Probe.rows(original.messages).map(row => row.id));
            original.send("Original451 "+index);
            tryVerify(() => array451_activity(original,call.call_id,before) !== null && !original.canCancel && !original.showingActions,
                10000,"ARRAY451: exact original native RPC settles once, no missing/early-refusal positive");
            return array451_activity(original,call.call_id,before);
        }
        function settled(){tryVerify(() => alive313(ownerLife) && Session.project === project && !project.calculating
            && Probe.computedCurrent(project.currentExperiment),10000,"ARRAY451: genuine native calculation/ordinary Undo actually settles");}
        function undo(){Ui.click(this,Probe,window,"appBar.button.undo");settled();}
        try {
            if(data.tag === "applied-replacement") {
                // This is the original public ParameterItem notification of an ACTUAL native write.
                // No signal is invoked by the test; Session.openProject is the genuine public replacement.
                Ui.click(this,Probe,window,"assistant.showActions");verify(original.showActions,"ARRAY451: genuine public mode checkbox enables visible arrays");
                closeAssistant388();watchScience();scan();
                bind(original,"actionPointerShown",scan);bind(original,"actionPointerMoved",scan);bind(original,"actionPointerPressed",scan);
                const applied=[];let replacements=0,bOwner=null,bReceiver=null,bLife=null,bReceiverLife=null,bBaseline=null,atApply=null,oldUser=null;
                function replaced(){
                    current();verify(alive313(laLife),"ARRAY451: actual applied receipt belongs to the original current La object");
                    if(la.value !== 0.6)return;
                    compare(replacements,0,"ARRAY451: one actual original scalar write creates exactly one owner replacement");
                    verify(array451_member(model,la.path).parameter === la,"ARRAY451: application is observed on an actual original live model member");
                    verify(events.some(row => row.path === la.path && row.kind === "text" && Number(row.text) === 0.6),
                        "ARRAY451: original native typing reached literal final operand BEFORE science publication");
                    const users=Probe.rows(original.messages).filter(row => row.kind === "user" && row.text === "Original451 0");
                    compare(users.length,1,"ARRAY451: original applied call belongs to one actually admitted user row");
                    verify(typeof users[0].id === "string" && users[0].id.length > 0 && users[0].status === "completed",
                        "ARRAY451: original user has a genuine completed matching ACK before actual native application");
                    oldUser={id:users[0].id,text:users[0].text,status:users[0].status};
                    applied.push(la.value);atApply=array451_science(project);++replacements;
                    stop(); // retire only TEST observers before real Session closing notifications; never dereference A after replacement.
                    verify(Session.openProject(Probe.referenceUrl("replacement")),"ARRAY451: actual synchronous original value notification opens independent B normally");
                    bOwner=Session.project;bReceiver=Session.assistant;bLife=lifetime313(bOwner);bReceiverLife=lifetime313(bReceiver);
                    verify(bOwner !== project,"ARRAY451: original publication truly replaces A, never reuses A identity as B");
                    bBaseline={science:array451_science(bOwner),state:prefs419_state(bReceiver)};
                }
                bind(la,"valueChanged",replaced);
                original.send("Original451 0");
                tryVerify(() => replacements === 1 && bOwner !== null && alive313(bLife) && alive313(bReceiverLife)
                    && Session.project === bOwner && Session.assistant === bReceiver && !bReceiver.canCancel && !bReceiver.showingActions,
                    visible237_observationMs([{path:laPath,text:"0.6"}]),"ARRAY451: known applied first input reaches synchronous replacement and old work retires naturally");
                compare(applied,[0.6],"ARRAY451: applied receipt is a real scientific fact, never inferred from prepared text");
                compare(atApply.values.find(row => row[0] === "structure.atom_sites[La].adp_iso")[1],0.6,"ARRAY451: original A actually owns changed physical science at replacement");
                compare(atApply.values.find(row => row[0] === "structure.atom_sites[Ba].adp_iso")[1],0.5,"ARRAY451: next requested A member never applied before replacement");
                for(const row of atApply.values)if(row[0] !== laPath)
                    compare(JSON.stringify(row),JSON.stringify(initial.values.find(value => value[0] === row[0])),
                        "ARRAY451: every unrelated A physical value/free/PRESENT-SU is unchanged at the actual write boundary");
                compare(atApply.inputs,initial.inputs,"ARRAY451: actual A input triples/weights/exclusions/links are untouched before replacement");
                compare(atApply.relations,initial.relations,"ARRAY451: actual A aliases/constraints remain unchanged before replacement");
                // atApply retains public dirty/Undo observations, not proof of later presentation:
                // this original valueChanged interval precedes normal flag publication and destroys A.
                // Live-owner rows still require real ordinary Undo; post-destruction A Undo is unobserved.
                compare(array451_member(bOwner.parameters,"structure.atom_sites[La].adp_iso").parameter.value,0.5,"ARRAY451: B remains independent literal input, no old A application leaks");
                compare(array451_member(bOwner.parameters,"structure.atom_sites[Ba].adp_iso").parameter.value,0.5,"ARRAY451: old continuation cannot apply next A operand to B");
                // Initial async calculation may publish B's computed pattern; compare science/metadata, not its pending flag.
                stop();
                tryVerify(() => alive313(bLife) && Session.project === bOwner && !bOwner.calculating && Probe.computedCurrent(bOwner.currentExperiment),10000,
                    "ARRAY451: genuine B initial calculation finishes without old-A authority");
                compare(JSON.stringify(array451_science(bOwner)),JSON.stringify(bBaseline.science),"ARRAY451: B physical/free/SU/input/declaration/path/metadata/Undo/dirty facts stay untouched");
                const state=prefs419_state(bReceiver);
                for(const key of ["account","skills","selectedSkill","model","effort","files"])
                    compare(JSON.stringify(state[key]),JSON.stringify(bBaseline.state[key]),"ARRAY451: old A cannot mutate B account/configuration/draft authority: "+key);
                verify(!Probe.rows(bReceiver.messages).some(row => row.payload && row.payload.id === spec.calls[0].call_id),
                    "ARRAY451: retired A result cannot be published in replacement conversation B");
                console.log("ARRAY451_RESULT",JSON.stringify({case:data.tag,applied:applied,replacements:replacements,bUntouched:true,
                    originalOwner:identity313(ownerLife),newOwner:identity313(bLife),oldUser:oldUser,atApply:atApply,bScience:array451_science(bOwner),input:events,writes:writes}));
                return;
            }
            send(0);settled();const afterSentinel=array451_science(project);
            compare(array451_member(project.parameters,"experiment.instrument.setup_wavelength").parameter.value,1.495,
                "ARRAY451: prior genuine normal tool created its literal recorded Undo sentinel");
            let target=null,targetLife=null,hiddenRow=null;
            if(data.tag.startsWith("hidden-")){
                compare(project.currentExperiment.beamModeToken,"constant wavelength","ARRAY451: free TOF scalar is unused in the real original CW profile, no forced exposure");
                hiddenRow=array451_member(project.currentExperiment.instrument,"experiment.instrument.calib_d_to_tof_linear");target=hiddenRow.parameter;
                compare([hiddenRow.name,hiddenRow.usedByProfile,target.value,target.free],["calib_d_to_tof_linear",false,123,true],
                    "ARRAY451: original ParameterListModel owns independent declared free-but-unused member");
                verify(array451_member(project.parameters,target.path).parameter === target,"ARRAY451: Analysis and Instrument are bound to SAME actual current ParameterItem");
            }else target=array451_member(project.parameters,"structure.atom_sites[La].adp_iso").parameter;
            targetLife=lifetime313(target);const path=target.path,oldValue=target.value;
            const normal=send(1);settled();
            verify(normal.payload.nativeOutcome !== null && typeof normal.payload.nativeOutcome === "object",
                "ARRAY451: SAME exact lawful normal array is genuine admitted native work, never setup/refusal");
            const entries=spec.calls[1].arguments.values;
            for(const entry of entries)compare(array451_member(project.parameters,entry.path).parameter.value,entry.value,
                "ARRAY451: SAME normal operands actually change or retain their independent literal physical member");
            verify(project.canUndo,"ARRAY451: normal atomic positive has a real ordinary Undo");
            undo();compare(JSON.stringify(array451_science(project).values),JSON.stringify(afterSentinel.values),
                "ARRAY451: ONE ordinary Undo restores whole positive array; native noops add no extra history");
            let removedReceipt=null;
            if(data.tag === "removed-noop"){
                const liveTarget=array451_member(project.parameters,path).parameter,removedLife=lifetime313(liveTarget);
                const sites=project.currentStructure.atomSites,siteLife=lifetime313(sites),rows=Probe.rows(sites);
                const index=rows.findIndex(row => row.label === "La");
                verify(index >= 0 && rows[index].adpIso === liveTarget,"ARRAY451 SETUP: exact original La site/ADP live role selected BEFORE ordinary removal");
                function removed(){
                    if(Probe.rows(model).some(row => row.parameter === liveTarget))return;
                    if(removedReceipt !== null)return;
                    verify(alive313(removedLife),"ARRAY451: genuine original rowsRemoved notification reaches still-live deleteLater child interval");
                    removedReceipt={alive:true,identity:identity313(removedLife),path:path,oldValue:liveTarget.value,
                        currentPaths:Probe.rows(model).map(row => row.parameter.path)};
                    verify(!removedReceipt.currentPaths.includes(path),"ARRAY451: removed cached path is NOT current model membership even while old QObject lives");
                }
                bind(model,"rowsRemoved",removed);
                sites.remove(index);
                verify(removedReceipt !== null && removedReceipt.alive,"ARRAY451: actual model removal reached owned deferred-child observation, not optional missing seam");
                verify(alive313(siteLife),"ARRAY451: original owning site model survives its actual public removal");
                verify(!Probe.rows(project.parameters).some(row => row.parameter.path === path),"ARRAY451: no-op operand's old physical object is truly retired from CURRENT model");
            }else{
                visible185_page("experiment");Ui.click(this,Probe,window,"sideBar.tab.basic");Ui.expandGroup(this,Probe,window,"group.instrument");rendered();
                const rows=Probe.rows(project.currentExperiment.instrument),entry=rows.filter(row => row.name === "calib_d_to_tof_linear");
                compare(entry.length,1,"ARRAY451: currently selected original Instrument still owns exactly one declared unused field");
                verify(entry[0].usedByProfile === false && entry[0].parameter === array451_member(project.parameters,path).parameter,
                    "ARRAY451: live original role, not block name or recursive QObject, establishes hidden target identity");
                const fields=Ui.itemsWithProperty(Ui.windowRoot(window),"objectName").filter(control => control.objectName === "instrument.calib_d_to_tof_linear");
                compare(fields.length,1,"ARRAY451: original ParameterGrid creates one exact hidden delegate");
                verify(fields[0].item === entry[0].parameter && !fields[0].visible && !Ui.exposed(fields[0]),
                    "ARRAY451: original usedByProfile semantics genuinely hide control without changing UI properties/profile");
            }
            Ui.click(this,Probe,window,"assistant.showActions");verify(original.showActions,"ARRAY451: genuine eye toggles only visible mode AFTER normal positive/Undo");
            closeAssistant388();
            const before=array451_science(project),beforePage=window.appBarCentralTabs.currentIndex;
            watchScience();scan();
            bind(original,"actionPointerShown",scan);bind(original,"actionPointerMoved",scan);bind(original,"actionPointerPressed",scan);
            bind(window.appBarCentralTabs,"currentIndexChanged",() => {navigation.push({kind:"page"});scan();});
            bind(project.fit,"runningChanged",() => {if(project.fit.running)++fitStarts;});
            const refused=send(2);current();stop();
            compare(JSON.stringify(spec.calls[1].arguments),JSON.stringify(spec.calls[2].arguments),"ARRAY451: visible negative uses EXACT SAME independent whole operands as healthy normal positive");
            compare(JSON.stringify(array451_science(project)),JSON.stringify(before),"ARRAY451: known-unmapped/removed later member refuses BEFORE earlier edit/dirty/Undo/science");
            compare([events.length,writes.length,navigation.length,fitStarts],[0,0,0,0],"ARRAY451: initial whole refusal reaches ZERO scientific/control/navigation/Fit effects");
            compare(window.appBarCentralTabs.currentIndex,beforePage,"ARRAY451: known unsupported original route cannot navigate as a partial attempt");
            compare(original.connectionLabel,account,"ARRAY451: refusal never repairs original account");
            compare(JSON.stringify(Probe.rows(original.models)),catalog,"ARRAY451: exact catalogue stays healthy/unchanged");
            if(data.tag === "removed-noop"){
                undo();
                compare(JSON.stringify(array451_science(project).values),JSON.stringify(afterSentinel.values),"ARRAY451: NEXT ordinary Undo restores genuine removed member; refusal/noop created no phantom history");
                const restored=array451_member(project.parameters,path).parameter;
                compare(restored.value,oldValue,"ARRAY451: actual current restored member retains independent old no-op operand");
            }
            undo();compare(JSON.stringify(array451_science(project).values),JSON.stringify(initial.values),
                "ARRAY451: NEXT prior sentinel Undo reaches original physical state, no hidden refusal/noop edit");
            compare(visible185_inputs(project),initial.inputs,"ARRAY451: original measured triples/SUs/weights/links/exclusions survive actual native/Undo steps");
            compare(relation245_declarations(project),initial.relations,"ARRAY451: original relations survive native refusal and real Undo");
            const users=Probe.rows(original.messages).filter(row => row.kind === "user").map(row => ({id:row.id,text:row.text,status:row.status}));
            console.log("ARRAY451_RESULT",JSON.stringify({case:data.tag,normalSucceeded:true,zeroVisibleInput:true,users:users,
                removed:removedReceipt,hidden: data.tag.startsWith("hidden-") ? {path:path,usedByProfile:false} : null}));
        } finally {stop();if(alive313(receiverLife) && original.canCancel)original.cancel();}
    }
    function test_main504_lbco_show_actions_owner_outcome() {
        const test = this;
        const plan = JSON.parse(Probe.readReferenceFile("main504-plan.json"));
        const triples = JSON.parse(Probe.readReferenceFile("triples.json"));
        const sourceBytes = ["lbco.cif", "hrpt.xye"].map(name => Probe.readReferenceFile(name));
        Session.closeProject();
        const path = ApplicationInfo.localPath(Probe.referenceUrl("current"));
        // CREATE574: genuine user Create precedes every assistant/account action.
        visible185_page("home");
        Ui.click(test,Probe,window,"home.start");
        compare(window.appBarCentralTabs.currentIndex,AppState.Page.Project,
            "CREATE574: ordinary Home Start exposes the original Project workflow");
        Ui.click(test,Probe,window,"sideBar.tab.basic");
        Ui.click(test,Probe,window,"project.create");
        const createDialogs574=Probe.visibleDialogs(window).filter(dialog => dialog.objectName==="createProject.dialog");
        compare(createDialogs574.length,1,"CREATE574: ONE actual Main-owned production Create dialog opens");
        const createDialog574=createDialogs574[0], createLife574=lifetime313(createDialog574);
        tryCompare(createDialog574,"opened",true,2000,"CREATE574: original Create dialog opens before native input");
        for(const [name,value] of [["name","Original Main LBCO owner"],["title","Original Main title"],
            ["authors","Original Main author"],["description","Original Main description"],["location",path]]) {
            const field=findChild(createDialog574,"createProject."+name);
            verify(field!==null && field.enabled && field.visible,
                "CREATE574: exact original named input belongs to the current production Create dialog");
            Ui.scrollIntoView(field);rendered();ux356_fullyExposed(field);
            const point=Ui.clickPoint(field);
            mouseClick(field,point.x,point.y);
            verify(field.activeFocus,"CREATE574: native pointer focuses the actual original Create field");
            visible185_type(value);
            compare(field.text,value,"CREATE574: original native keys retain the complete independent user operand");
        }
        const createButton574=createDialog574.standardButton(Dialog.Ok), createButtonLife574=lifetime313(createButton574);
        verify(createButton574!==null && createButton574.enabled && createButton574.objectName==="createProject.accept",
            "CREATE574: original enabled standard Create action owns the actual final native input");
        Ui.scrollIntoView(createButton574);rendered();ux356_fullyExposed(createButton574);
        const createReceipt574={pressed:0,released:0,clicked:0,canceled:0,accepted:0};
        const pressed574=function(){if(createButton574.pressed)++createReceipt574.pressed;};
        const released574=function(){++createReceipt574.released;};
        const clicked574=function(){++createReceipt574.clicked;};
        const canceled574=function(){++createReceipt574.canceled;};
        const accepted574=function(){++createReceipt574.accepted;};
        createButton574.pressedChanged.connect(pressed574);createButton574.released.connect(released574);
        createButton574.clicked.connect(clicked574);createButton574.canceled.connect(canceled574);
        createDialog574.accepted.connect(accepted574);
        try {
            const point=Ui.clickPoint(createButton574);
            mouseClick(createButton574,point.x,point.y);
            tryVerify(() => Session.project!==null,2000,"CREATE574: ONE genuine Create click adopts the saved empty owner");
            compare(JSON.stringify(createReceipt574),JSON.stringify({pressed:1,released:1,clicked:1,canceled:0,accepted:1}),
                "CREATE574: exactly ONE native press/release/click/accept creates the original owner");
        } finally {
            disconnect313(createButtonLife574,createButton574,"pressedChanged",pressed574);
            disconnect313(createButtonLife574,createButton574,"released",released574);
            disconnect313(createButtonLife574,createButton574,"clicked",clicked574);
            disconnect313(createButtonLife574,createButton574,"canceled",canceled574);
            disconnect313(createLife574,createDialog574,"accepted",accepted574);
        }
        compare(Session.project.name,"Original Main LBCO owner","CREATE574: real Create retains the independent user name");
        compare(Session.project.title,"Original Main title","CREATE574: real Create retains the independent user title");
        compare(Session.project.description,"Original Main description");compare(Session.project.authors,"Original Main author");
        compare(Session.project.path,path,"CREATE574: actual chosen location becomes the original saved owner path");
        verify(!Session.project.modified && !Session.needsSaveAs && Session.projectDirectoryExists(path),
            "CREATE574: user Create already saved its directory before assistant population or Save");
        const emptyDisk574=Probe.readReferenceFile("current/project.edi");
        verify(emptyDisk574.length>0 && emptyDisk574.includes("Original Main LBCO owner")
            && emptyDisk574.includes("Original Main title"),
            "CREATE574: actual initial project document contains the independent user-created metadata on disk");
        const original = Session.project, ownerLife = lifetime313(original), metadata = import265_owner(original);
        compare(original.structures.count, 0); compare(original.experiments.count, 0);
        const token = assistant.beginFileSelection();
        verify(token.length > 0 && assistant.addSelectedFiles(token,
            [Probe.referenceUrl("lbco.cif"), Probe.referenceUrl("hrpt.xye")]), "MAIN504: original intake admits immutable authentic sources");
        tryCompare(assistant.selectedFiles, "count", 2, 2000);
        const selectedRows507 = gui392_json(Probe.rows(assistant.selectedFiles));
        const selected = JSON.stringify(selectedRows507.map(row =>
            ({id:row.id,name:row.name,bytes:row.bytes,textReadable:row.textReadable,format:row.format})));
        compare(selectedRows507.length,2);
        compare(new Set(selectedRows507.map(row => row.id)).size,2,"MAIN507: actual original selected membership has two distinct opaque IDs");
        for(const [index,name,bytes] of [[0,"lbco.cif",487],[1,"hrpt.xye",83671]]) {
            const row=selectedRows507[index];
            verify(typeof row.id==="string" && row.id.length>0 && row.name===name && row.bytes===bytes
                && row.textReadable===true && typeof row.format==="string" && row.format.length>0,
                "MAIN507: genuine original intake binds known file order/type/bytes to each opaque selected identity");
        }
        visible185_page("project"); toggle(); gui392_signIn(false);
        Ui.click(test, Probe, window, "assistant.showActions");
        verify(assistant.showActions && item("assistant.showActions").checked, "MAIN504: genuine native eye enables ON mode");
        const account = JSON.stringify(Probe.rows(assistant.models)), previous = new Set(Probe.rows(assistant.messages).map(row => row.id));
        const bindings = [], watched = new Set(), cues = {"structures.load":0,"experiments.loadData.0":0};
        let filePresses = 0, fileReleases = 0, fileClicks = 0, dialogsOpened = 0, typed = 0, freeClicks = 0, fitStarts = 0, fitFinishes = 0;
        let delegatedTyped612=0; const creationInputs612=[];
        // NATURAL578: actual native receipts; strategy inference/default-three is not simulated here.
        const watched578=new Set(), natural578={namesPressed:0,namesClicked:0,headerPressed:0,headerChosen:0,
            menuAdmitted:0,categoryKeys:[],adpValues:new Set(),adpFree:new Set(),cellFree:0,aliasesReady:false,constraintUsed:false,freeCues:[],valueCues:[]};
        const watched610=new Set(),groupCues610=[],ordinaryFreeWrites610=[],ordinaryValueWrites610=[];
        let headerOpening610=null,scientificHeaderEvents610=0;
        let objective578=3, requested578={}, background578=[], cell578="", aliases578={};
        let menuReceiver583=null, menuIdentity583=null;
        function nativeFilter578(parameter) {
            verify(alive313(ownerLife) && Session.project===original
                && visible185_parameters(original).includes(parameter),"NATURAL578: native input retains SAME current owner and member");
            const table=Ui.control(Probe,window,"parameters.list");
            verify(table!==null && table.sourceModel!==null,"NATURAL578: actual Analysis table owns the native action");
            const filter=table.sourceModel;
            compare(filter.nameFilter,"","NATURAL578: native parameter action never uses a full-path/name filter per row");
            verify(filter.shows(parameter),"NATURAL578: SAME actual requested member belongs to the offered native rows");
            if(parameter.category==="cell") {
                compare(filter.categoryFilter,"");compare(filter.variability,0);
            } else {
                verify(filter.categoryFilter.length>0 && natural578.categoryKeys.includes(filter.categoryFilter),
                    "NATURAL578: non-cell input follows an actual offered native category activation");
                if(parameter.name==="adp_iso") {
                    const offered=filter.categoryGroups.filter(group => group.key==="@displacement");
                    compare(offered.length,1);compare(filter.categoryFilter,offered[0].key);
                }
            }
            verify(!(natural578.aliasesReady && !natural578.constraintUsed),
                "NATURAL578: related aliases are followed by their constraint use before another scientific input");
            return filter;
        }
        function freeCue610(control) {
            let row=control;
            while(row && !(row.parameter && visible185_parameters(original).includes(row.parameter)))row=row.parent;
            verify(row!==null,"NATURAL610: actual cue owns its original live ParameterItem row");
            const parameter=row.parameter;nativeFilter578(parameter);
            verify(Object.prototype.hasOwnProperty.call(requested578,parameter.path)
                && parameter.fittable && parameter.refinable && parameter.free!==requested578[parameter.path],
                "NATURAL610: cue targets exactly a changed requested eligible flag, never a no-op");
            verify(!background578.includes(parameter.path),"NATURAL610: exact complete background request must use its actual header/menu route");
            natural578.freeCues.push({path:parameter.path,objective:objective578,from:parameter.free,to:requested578[parameter.path]});
        }
        function eligible610() {
            verify(alive313(ownerLife) && Session.project===original);
            const table=Ui.control(Probe,window,"parameters.list");verify(table!==null);
            const filter=table.sourceModel,eligible=[];
            compare(filter.nameFilter,"");compare(filter.variability,0);
            verify(filter.categoryFilter.length>0 && natural578.categoryKeys.includes(filter.categoryFilter));
            for(let index=0;index<filter.rowCount();++index) {
                const p=filter.parameterAt(index);if(p.fittable && p.refinable)eligible.push(p);
            }
            verify(eligible.length>0 && eligible.every(p => Object.prototype.hasOwnProperty.call(requested578,p.path)));
            const requested=Object.keys(requested578).filter(path => {
                const rows=visible185_parameters(original).filter(p => p.path===path);compare(rows.length,1);
                return rows[0].fittable && rows[0].refinable && filter.shows(rows[0]);
            });
            compare(JSON.stringify(eligible.map(p => p.path).sort()),JSON.stringify(requested.sort()),
                "NATURAL610: header owns the EXACT complete displayed eligible requested set, including equal prefixes");
            const free=requested578[eligible[0].path];verify(eligible.every(p => requested578[p.path]===free));
            return {parameters:eligible,paths:eligible.map(p => p.path).sort(),free:free};
        }
        function scanNatural578() {
            const objects=Probe.objectsWithProperty(window,"objectName");
            for(const control of objects.filter(object => object.objectName==="background.namePoints"
                || object.objectName==="parameters.category" || ["parameters.freeHeader.free","parameters.freeHeader.fixed"].includes(object.objectName))) {
                if(watched578.has(control))continue;watched578.add(control);
                if(control.objectName==="background.namePoints") {
                    bind(control,"pressedChanged",() => {if(!assistant.showingActions || !control.pressed)return;
                        compare(objective578,3);verify(control.enabled && Ui.exposed(control));
                        compare(JSON.stringify(Probe.rows(original.currentExperiment.background).map(row => [row.position,row.intensity.value])),
                            JSON.stringify(plan.recipe.background.map(row => [row.position,row.intensity])),
                            "NATURAL578: all explicit requested values precede the ONE real original naming action");
                        ++natural578.namesPressed;});
                    bind(control,"clicked",() => {if(assistant.showingActions){++natural578.namesClicked;
                        compare(JSON.stringify(Probe.rows(original.currentExperiment.background).map(row => row.id)),JSON.stringify(["10","165"]));
                        compare(JSON.stringify(Probe.rows(original.currentExperiment.background).map(row => [row.position,row.intensity.value])),
                            JSON.stringify(plan.recipe.background.map(row => [row.position,row.intensity])));
                    }});
                } else if(control.objectName==="parameters.category") {
                    bind(control,"activated",index => {if(assistant.showingActions){
                        const table=Ui.control(Probe,window,"parameters.list");verify(table!==null);
                        natural578.categoryKeys.push(table.sourceModel.categories[index]);}});
                } else {
                    bind(control,"pressedChanged",() => {if(assistant.showingActions && control.pressed)++scientificHeaderEvents610;});
                    bind(control,"clicked",() => {if(assistant.showingActions)++scientificHeaderEvents610;});
                }
            }
            const header=Ui.control(Probe,window,"parameters.freeHeader");
            if(header && header.parent && header.parent.parent) {
                for(const area of Probe.objectsWithProperty(header.parent.parent,"mouseX").filter(area =>
                    area.parent===header.parent.parent && typeof area.pressed==="boolean" && typeof area.pressedChanged==="function" && typeof area.clicked==="function")) {
                    if(watched578.has(area))continue;watched578.add(area);
                    bind(area,"pressedChanged",() => {if(!assistant.showingActions || !area.pressed)return;
                        const point=area.mapToItem(header,area.mouseX,area.mouseY);
                        if(point.x>=0 && point.y>=0 && point.x<header.width && point.y<header.height) {
                            verify(header.visible && Ui.exposed(header));const group=eligible610();
                            const menus=Probe.objectsWithProperty(window,"objectName").filter(o=>o.objectName==="parameters.freeHeader.menu");
                            compare(menus.length,1,"NATURAL610: ONE original public header menu belongs to this real opening");
                            const headerLife=lifetime313(header),menuLife=lifetime313(menus[0]);
                            headerOpening610={objective:objective578,paths:group.paths,free:group.free,header:identity313(headerLife),
                                headerLife:headerLife,menu:menus[0],menuLife:menuLife,menuIdentity:identity313(menuLife)};
                            if(objective578===10 && JSON.stringify(group.paths)===JSON.stringify(background578.slice().sort()))++natural578.headerPressed;
                        }});
                }
            }
            for(const parameter of visible185_parameters(original)) {
                if(watched610.has(parameter))continue;watched610.add(parameter);
                const life=lifetime313(parameter);let previousFree=parameter.free;
                bind(parameter,"freeChanged",() => {
                    verify(alive313(life) && alive313(ownerLife) && Session.project===original
                        && visible185_parameters(original).includes(parameter),"NATURAL610: actual flag publication retains its prepared current owner/member");
                    const before=previousFree;previousFree=parameter.free;
                    if(!assistant.showingActions || before===parameter.free || !Object.prototype.hasOwnProperty.call(requested578,parameter.path))return;
                    compare(parameter.free,requested578[parameter.path]);
                    const row=natural578.freeCues.filter(c => c.objective===objective578 && c.path===parameter.path);
                    const groups=groupCues610.filter(c => c.objective===objective578 && c.paths.includes(parameter.path));
                    compare(row.length+groups.length,1,"NATURAL610: every real flag mutation has ONE exact row or complete-group admission");
                    for(const group of groups)verify(alive313(group.menuLife) && identity313(group.menuLife)===group.menuIdentity,
                        "NATURAL610: actual group effects retain the SAME admitted original menu receiver");
                    ordinaryFreeWrites610.push({path:parameter.path,value:parameter.free,objective:objective578});
                    ++observations518.inputReceipt["parameter-free"];
                    if(parameter.path===cell578)++natural578.cellFree;
                    if(parameter.name==="adp_iso")natural578.adpFree.add(parameter.path);
                    for(const group of groups)if(!group.completed && group.parameters.every(p => p.free===group.free)) {
                        group.completed=true;
                        if(group.objective===10 && JSON.stringify(group.paths)===JSON.stringify(background578.slice().sort()))++natural578.headerChosen;
                    }
                });
                if(parameter.name==="adp_iso")bind(parameter,"valueChanged",() => {
                    if(!assistant.showingActions || objective578!==10 || parameter.value!==.5)return;
                    verify(alive313(life) && visible185_parameters(original).includes(parameter));
                    compare(natural578.valueCues.filter(c => c.path===parameter.path && c.objective===objective578).length,1,
                        "NATURAL610: actual requested ADP .5 publication follows ONE exposed native value cue");
                    natural578.adpValues.add(parameter.path);ordinaryValueWrites610.push(parameter.path);
                    ++observations518.inputReceipt["parameter-text"];
                });
            }
        }
        function scientificCue610() {
            if(lastPoint===null)return;
            for(const control of Ui.itemsWithProperty(Ui.windowRoot(window),"objectName").filter(c => Ui.exposed(c))) {
                const box=rect(control);
                if(lastPoint.x<box[0] || lastPoint.y<box[1] || lastPoint.x>=box[0]+box[2] || lastPoint.y>=box[1]+box[3])continue;
                if(control.objectName.startsWith("parameters.free."))freeCue610(control);
                else if(control.objectName.startsWith("parameters.value.") && control.item && plan.adps.includes(control.item.path) && objective578===10) {
                    nativeFilter578(control.item);verify(control.item.value!==.5);
                    natural578.valueCues.push({path:control.item.path,objective:objective578});
                } else if(["parameters.freeHeader.free","parameters.freeHeader.fixed"].includes(control.objectName)) {
                    const life=lifetime313(control),group=eligible610();
                    compare(control.objectName,group.free?"parameters.freeHeader.free":"parameters.freeHeader.fixed");
                    verify(headerOpening610!==null && headerOpening610.objective===objective578
                        && JSON.stringify(headerOpening610.paths)===JSON.stringify(group.paths) && headerOpening610.free===group.free,
                        "NATURAL610: SAME successful original header opening precedes exact scientific-choice cue");
                    verify(alive313(life) && control.enabled && alive313(headerOpening610.headerLife)
                        && alive313(headerOpening610.menuLife) && headerOpening610.menu.visible);
                    let sameMenu=false;for(let parent=control;parent;parent=parent.parent)
                        if(parent===headerOpening610.menu.contentItem)sameMenu=true;
                    verify(sameMenu,"NATURAL610: visual scientific choice belongs to the SAME actually opened original menu");
                    menuReceiver583=control;menuIdentity583=identity313(life);
                    groupCues610.push({objective:objective578,paths:group.paths,parameters:group.parameters,free:group.free,
                        menuLife:life,menuIdentity:identity313(life),completed:false});
                    if(objective578===10 && JSON.stringify(group.paths)===JSON.stringify(background578.slice().sort()))++natural578.menuAdmitted;
                }
            }
        }
        let lastPoint = null;
        let elapsedPhase511="setup";
        const observations518={frames:{setup:0,active:0,settled_idle:0,manual:0},
            inputIssue:{composer:0,send:0,"approve-context":0,"manual-value":0,undo:0,report:0},
            inputReceipt:{"parameter-free":0,"parameter-text":0},monotonicClockAvailable:false};
        const frame511=function(){ ++observations518.frames[elapsedPhase511]; };
        function bind(object, signal, callback) {
            const life = lifetime313(object); object[signal].connect(callback);
            bindings.push({object:object,signal:signal,callback:callback,life:life});
        }
        function scan() {
            if(assistant.canCancel && elapsedPhase511!=="active") {
                elapsedPhase511="active";console.info("GUI511_PHASE","active",JSON.stringify(observations518));
            }
            for (const name of Object.keys(cues)) {
                const controls = Ui.itemsWithProperty(Ui.windowRoot(window), "objectName").filter(c => c.objectName === name && c.visible && Ui.rendered(c));
                compare(controls.length <= 1, true, "MAIN504: original Load receiver is unique");
                for (const control of controls) {
                    if (watched.has(control)) continue; watched.add(control);
                    let nativeReceivers=0;
                    if (typeof control.clicked === "function") { bind(control, "clicked", () => { ++fileClicks; }); ++nativeReceivers; }
                    if (typeof control.released === "function") bind(control,"released",() => { ++fileReleases; });
                    if (typeof control.pressed === "boolean") bind(control, "pressedChanged", () => { if (control.pressed) ++filePresses; });
                    for (const handler of Probe.objectsWithProperty(control, "pressed").filter(h => h.parent === control && typeof h.tapped === "function")) {
                        bind(handler,"pressedChanged",() => { if(handler.pressed) ++filePresses; });
                        bind(handler,"tapped",() => { ++fileClicks; }); ++nativeReceivers;
                    }
                    verify(nativeReceivers>0,"MAIN504: actual rendered original Load owns a real button/TapHandler receipt, never absent witness");
                }
            }
            const chooserDialogs574=[...Probe.objectsWithProperty(window,"fileMode"),
                ...Probe.objectsWithProperty(window,"selectedFolder"),
                ...Probe.objectsWithProperty(window,"objectName").filter(dialog => dialog.objectName==="assistant.resultSaveAs")];
            verify(chooserDialogs574.some(dialog => typeof dialog.selectedFolder!=="undefined")
                && chooserDialogs574.some(dialog => dialog.objectName==="assistant.resultSaveAs"),
                "CREATE574: actual original folder picker and fresh Save As form are present as no-chooser witnesses");
            for (const dialog of chooserDialogs574) {
                if (watched.has(dialog)) continue; watched.add(dialog);
                verify(!dialog.visible, "MAIN504: no existing file dialog is already open");
                bind(dialog,"visibleChanged",() => { if(dialog.visible) ++dialogsOpened; });
            }
            for (const control of Ui.itemsWithProperty(Ui.windowRoot(window),"objectName").filter(c =>
                c.objectName.startsWith("parameters.free.") && typeof c.clicked === "function")) {
                if (watched.has(control)) continue; watched.add(control);
                bind(control,"clicked",() => {if(assistant.showingActions)++freeClicks;});
            }
            const field = window.activeFocusItem;
            if (field && !watched.has(field) && typeof field.textEdited === "function") {
                let parent = field;
                while(parent && !(parent.item && Session.project && visible185_parameters(Session.project).includes(parent.item))) parent=parent.parent;
                if(parent) { watched.add(field); const receiver578=parent;
                    bind(field,"textEdited",() => { ++observations518.inputReceipt["parameter-text"];
                        if(assistant.showingActions) {++typed;
                            const parameter=receiver578.item;
                            const creationInstrument612=objective578===3 && alive313(ownerLife) && Session.project===original
                                && visible185_parameters(original).includes(parameter)
                                && ["setup_wavelength","calib_twotheta_offset"].includes(parameter.name)
                                && receiver578.objectName==="instrument."+parameter.name;
                            if(creationInstrument612) {
                                creationInputs612.push({path:parameter.path,name:parameter.name,text:field.text});
                            } else {
                                ++delegatedTyped612;
                                verify(false,"NATURAL610: changed ordinary-setter paths must not dispatch scientific textEdited");
                            }
                        }}); }
            }
            scanNatural578();
        }
        function cue() {
            scan(); verify(assistant.actionWindow === window && assistant.showingActions, "MAIN504: cue belongs to actual current Main action");
            const pointer = item("assistant.actionPointer"); verify(Ui.rendered(pointer), "MAIN504: cue is actually rendered");
            for(const name of Object.keys(cues)) {
                const targets=Ui.itemsWithProperty(Ui.windowRoot(window),"objectName").filter(c => c.objectName===name && Ui.exposed(c));
                if(targets.length===1 && lastPoint) {
                    const box=rect(targets[0]);
                    if(lastPoint.x>=box[0] && lastPoint.y>=box[1] && lastPoint.x<box[0]+box[2] && lastPoint.y<box[1]+box[3]) ++cues[name];
                }
            }
            compare(filePresses,0,"MAIN504: visual file-load cue never dispatches a real press");
            compare(fileClicks,0,"MAIN504: visual file-load cue never dispatches a real Load click/tap");
            compare(fileReleases,0,"MAIN504: visual file-load cue never dispatches a real Load release");
            compare(dialogsOpened,0,"MAIN504: attached-file cue never opens an ordinary file dialog");
            scientificCue610();
        }
        function outcome(index) {
            const rows=Probe.rows(assistant.messages).filter(row => !previous.has(row.id) && row.kind==="activity"
                && row.payload && row.payload.id==="main504-"+index);
            compare(rows.length<=1,true,"MAIN504: each exact native call has one original row");
            if(!rows.length || rows[0].status!=="completed") return null;
            verify(rows[0].payload.success===true && rows[0].payload.nativeOutcome,
                "MAIN504: completed original call has factual successful native outcome, never partial/refused substitute");
            const items=JSON.parse(JSON.stringify(rows[0].payload.contentItems));
            verify(Array.isArray(items) && items.length===1 && items[0].type==="inputText" && typeof items[0].text==="string",
                "MAIN504: SAME completed admitted row owns exactly one original typed native response");
            return JSON.parse(items[0].text);
        }
        function objective(text, last) {
            objective578=last;
            if(last!==3) {
                const declared=outcome(2).parameters;
                const identity=path => {const rows=declared.filter(row => row.path===path);compare(rows.length,1);return rows[0].path;};
                const scale=declared.filter(row => row.path.endsWith(".scale"));compare(scale.length,1);
                requested578={};background578=plan.nuisance.slice(1).map(identity);cell578=identity(plan.nuisance[0]);
                for(const path of [plan.zero,...plan.nuisance])requested578[identity(path)]=true;
                for(const path of plan.profiles)requested578[identity(path)]=last===16;
                if(last===10)requested578[scale[0].path]=true;
                else for(const index of [0,2,3])requested578[identity(plan.adps[index])]=true;
            }
            if(window.assistantManualTakeover || !popup.shown) toggle();
            const requiresApproval=assistant.contextConsentRequired;
            ++observations518.inputIssue["composer"];
            Ui.click(test,Probe,window,"assistant.composer"); visible185_type(text);
            compare(item("assistant.composer").text,text); verify(item("assistant.send").enabled);
            ++observations518.inputIssue["send"];
            Ui.click(test,Probe,window,"assistant.send");
            if(requiresApproval) {
                const dialog=ux356_dialog(); tryCompare(dialog,"opened",true,2000);
                ++observations518.inputIssue["approve-context"];
                gui470_standardAction(dialog.standardButton(Dialog.Ok),dialog,"approve-context");
            }
            tryVerify(() => !assistant.canCancel && !assistant.showingActions && outcome(last)!==null
                && Session.project!==null && !Session.project.calculating && Probe.computedCurrent(Session.project.currentExperiment),
                270000,"MAIN504: original objective completes all calls and actual current calculation within existing bounds");
            verify(!assistant.lastError,"MAIN504: no retained/context/worker error can substitute for completion");
            elapsedPhase511="settled_idle";console.info("GUI511_PHASE","settled_idle",JSON.stringify(observations518));
        }
        try {
            bind(window,"frameSwapped",frame511);
            console.info("GUI511_PHASE","setup",JSON.stringify(observations518));
            scan(); bind(assistant,"actionPointerShown",scan);
            bind(assistant,"actionPointerMoved",point => { lastPoint={x:point.x,y:point.y}; scan(); });
            bind(assistant,"actionPointerPressed",cue); bind(window,"activeFocusItemChanged",scan);
            objective("Import these original LBCO and HRPT attachments using the explicit original recipe",3);
            verify(alive313(ownerLife) && Session.project===original,"MAIN504: import populates SAME original saved owner");
            compare(import265_owner(original),metadata); compare(original.structures.count,1); compare(original.experiments.count,1);
            compare(natural578.namesPressed,1);compare(natural578.namesClicked,1,
                "NATURAL578: compound visible recipe actually uses ONE native IDs-from-values action after its supplied values");
            compare(original.currentExperiment.name,"NPD","MAIN528: successful native Text completion retains the independently supplied experiment name in the actual stored model");
            const closed507=outcome(0).selected_files.files;
            verify(Array.isArray(closed507) && closed507.length===2,"MAIN507: genuine successful inspection exposes both closed opaque File operands");
            compare(new Set(closed507.map(row => row.id)).size,2);
            for(let index=0;index<2;++index) {
                const wire=closed507[index], selectedRow=selectedRows507[index];
                compare(wire.id,selectedRow.id,"MAIN507: exact actual selected ID survives closed wire projection in known intake order");
                compare(wire.bytes,selectedRow.bytes); compare(wire.format,selectedRow.format);
                if(Object.prototype.hasOwnProperty.call(wire,"textReadable"))
                    compare(wire.textReadable,true,"MAIN507: optional PUBLIC readable role, when present, remains strictly typed true");
            }
            const aliasesExpected={};
            for(const [id,path] of [["original_la_biso",plan.adps[0]],["original_ba_biso",plan.adps[1]]]) {
                const matches=outcome(2).parameters.filter(row => row.path===path);
                compare(matches.length,1); verify(typeof matches[0].unique_name==="string" && matches[0].unique_name.length>0);
                aliasesExpected[id]=matches[0].unique_name;
            }
            verify(aliasesExpected.original_la_biso!==aliasesExpected.original_ba_biso);
            aliases578=aliasesExpected;
            const relation578=function(){
                if(!alive313(ownerLife) || Session.project!==original)return;
                const rows=Probe.rows(original.analysis.aliases),mapping={};for(const row of rows)mapping[row.id]=row.parameter;
                const complete=rows.length===2 && Object.keys(aliases578).every(id => mapping[id]===aliases578[id]);
                if(complete)natural578.aliasesReady=true;
                const uses=Probe.rows(original.analysis.constraints).filter(row => row.id==="original_chosen_shared_biso" && row.expression==="original_ba_biso = original_la_biso" && row.enabled);
                if(uses.length && !natural578.constraintUsed) {
                    verify(complete && natural578.aliasesReady && objective578===10,
                        "NATURAL578: all related actual aliases exist together BEFORE their constraint becomes enabled");
                    natural578.constraintUsed=true;
                }
            };
            compare(original.analysis.aliases.count,0);compare(original.analysis.constraints.count,0);
            for(const model of [original.analysis.aliases,original.analysis.constraints])
                for(const signal of ["rowsInserted","dataChanged","modelReset"])bind(model,signal,relation578);
            function aliasesCurrent(project) {
                const rows=Probe.rows(project.analysis.aliases); compare(rows.length,2);
                const mapping={}; for(const row of rows) mapping[row.id]=row.parameter;
                compare(JSON.stringify(Object.keys(mapping).sort()),JSON.stringify(Object.keys(aliasesExpected).sort()));
                for(const id of Object.keys(aliasesExpected)) compare(mapping[id],aliasesExpected[id]);
                compare(JSON.stringify(Probe.rows(project.analysis.constraints).map(row => [row.id,row.expression,row.enabled])),
                    JSON.stringify([["original_chosen_shared_biso","original_ba_biso = original_la_biso",true]]));
            }
            const physicalSites=Probe.rows(original.currentStructure.atomSites);
            compare(physicalSites.length,4); compare(original.currentStructure.spaceGroup.nameHM,"P m -3 m");
            for(const [label,xyz,occupancy] of [["La",[0,0,0],.5],["Ba",[0,0,0],.5],["Co",[.5,.5,.5],1],["O",[0,.5,.5],1]]) {
                const matches=physicalSites.filter(row => row.label===label); compare(matches.length,1);
                const site=matches[0]; compare(site.typeSymbol,label); compare(site.adpType,"Biso");
                compare(JSON.stringify([site.fractX.value,site.fractY.value,site.fractZ.value]),JSON.stringify(xyz));
                compare(site.occupancy.value,occupancy); compare(visible185_parameter(original,label,"adp_iso").value,0);
            }
            const wavelengths=visible185_parameters(original).filter(parameter => parameter.name==="setup_wavelength");
            compare(wavelengths.length,1); compare(wavelengths[0].value,1.49);
            compare(typed,creationInputs612.length);
            verify(creationInputs612.some(receipt => receipt.path===wavelengths[0].path
                && receipt.name==="setup_wavelength" && receipt.text==="1.49"),
                "MAIN612: unchanged real creation instrument input actually types the supplied 1.49, independently read back above");
            compare(delegatedTyped612,0,"MAIN612: compound parameter-child setters dispatch no scientific keys");
            const inputs=JSON.parse(visible185_inputs(original));
            compare(JSON.stringify(inputs.observations),JSON.stringify(triples)); compare(inputs.weight,1);
            compare(inputs.exclusions.length,0); compare(JSON.stringify(inputs.links),JSON.stringify([["lbco",true]]));
            compare(cues["structures.load"],1,"MAIN504: exact original Structure Load receives one genuine visual cue");
            compare(cues["experiments.loadData.0"],1,"MAIN504: exact original Data Load receives one genuine visual cue");
            compare(filePresses,0); compare(fileReleases,0); compare(fileClicks,0); compare(dialogsOpened,0);
            const nuisanceIds510={};
            for(const path of plan.nuisance) {
                const matches=outcome(2).parameters.filter(row => row.path===path);
                compare(matches.length,1);
                verify(matches[0].dependence==="independent" && matches[0].free===false
                    && typeof matches[0].unique_name==="string" && matches[0].unique_name.length>0,
                    "MAIN510: each literal nuisance path identifies one genuine original independent fixed cell/background member");
                nuisanceIds510[path]=matches[0].unique_name;
            }
            compare(new Set(Object.values(nuisanceIds510)).size,3,"MAIN510: literal cell/background targets retain distinct original identities");
            const profileIds514={};
            for(const path of plan.profiles) {
                const matches=outcome(2).parameters.filter(row => row.path===path);
                compare(matches.length,1,"MAIN514: original profile path identifies exactly one initial member");
                verify(matches[0].dependence==="independent" && matches[0].free===false
                    && typeof matches[0].unique_name==="string" && matches[0].unique_name.length>0,
                    "MAIN514: original profile member is genuinely independent and held before warm-up");
                profileIds514[path]=matches[0].unique_name;
            }
            compare(new Set(Object.values(profileIds514)).size,plan.profiles.length,"MAIN514: original profile identities remain distinct");
            const fit=original.fit, fitLife=lifetime313(fit);
            bind(fit,"runningChanged",() => { if(alive313(fitLife) && fit.running) ++fitStarts; });
            bind(fit,"finished",() => { ++fitFinishes; });
            const profileBaselines507={};
            const profileInitial580=plan.recipe.initial_parameters.filter(setting => plan.profiles.includes(setting.path));
            compare(profileInitial580.length,plan.profiles.length,"MAIN580: complete independently declared profile baseline excludes the separate initial background no-op");
            for(const setting of profileInitial580) {
                verify(!Object.prototype.hasOwnProperty.call(profileBaselines507,setting.path));
                profileBaselines507[setting.path]=setting.value;
            }
            profileBaselines507[plan.zero]=plan.recipe.zero_offset;
            const originalScales507=outcome(2).parameters.filter(row => row.path.endsWith(".scale"));
            compare(originalScales507.length,1,"MAIN507: original successful pre-fit list identifies ONE physical phase-scale path");
            compare(originalScales507[0].value,plan.recipe.phase_scale,"MAIN507: independent literal recipe establishes the preceding scale baseline");
            profileBaselines507[originalScales507[0].path]=plan.recipe.phase_scale;
            for(const path of Object.keys(profileBaselines507)) {
                const matches=outcome(2).parameters.filter(row => row.path===path);
                compare(matches.length,1,"MAIN507: each intended profile/zero/scale path is unique in the genuine preceding native list");
                compare(matches[0].value,profileBaselines507[path],"MAIN507: literal recipe baseline really precedes optimization");
            }
            objective("Set positive ADP starts, share La and Ba, then warm up scale cell background and zero while holding profile and ADPs",10);
            compare(Session.project,original); compare(import265_owner(original),metadata); aliasesCurrent(original);
            verify(natural578.aliasesReady && natural578.constraintUsed,"NATURAL578: same original relation request reaches actual alias-before-use boundary");
            compare(natural578.headerPressed,1,"NATURAL583: ONE real outer-header press is mandatory, never conditional on an optional menu callback");
            compare(natural578.menuAdmitted,1,"NATURAL610: ONE successful same-receiver menu cue executes every strict admission check");
            compare(natural578.headerChosen,1,"NATURAL610: exact full background group actually applies once after its real menu-opening and visual choice");
            verify(natural578.cellFree>0,"NATURAL578: requested cell freedom reaches an unfiltered actual row");
            for(const path of plan.adps){const row=outcome(2).parameters.filter(row => row.path===path);compare(row.length,1);
                verify(natural578.adpValues.has(row[0].path),"NATURAL578: each requested ADP value reaches actual category-selected native row input");}
            for(const path of plan.nuisance) {
                const matches=outcome(8).parameters.filter(row => row.path===path);
                compare(matches.length,1);
                verify(matches[0].unique_name===nuisanceIds510[path] && matches[0].dependence==="independent" && matches[0].free===true,
                    "MAIN510: first genuine post-fit read proves SAME actual independent cell/background roles free");
            }
            for(const path of plan.profiles) {
                const matches=outcome(8).parameters.filter(row => row.path===path);
                compare(matches.length,1,"MAIN514: first post-fit read retains one original profile member");
                verify(matches[0].unique_name===profileIds514[path] && matches[0].dependence==="independent"
                    && matches[0].free===false && matches[0].value===profileBaselines507[path],
                    "MAIN514: first actual warm-up holds SAME original profile member at literal start");
            }
            const profileAdps=["La","Ba","Co","O"].map(label => visible185_parameter(original,label,"adp_iso"));
            verify(profileAdps.every(parameter => parameter.value===.5 && !parameter.free),"MAIN504: actual first-stage ADPs remain the four fixed positive starts");
            compare([delegatedTyped612,freeClicks,scientificHeaderEvents610],[0,0,0],"NATURAL610: no scientific keys/toggle/menu-choice input is dispatched");
            compare(ordinaryValueWrites610.length,plan.adps.length,"NATURAL610: actual ADP app-method effects, not missing text callbacks, prove completion");
            verify(ordinaryFreeWrites610.length>0 && groupCues610.every(group => group.completed),"NATURAL610: each admitted group has real complete scientific effects");
            const profileResults507=outcome(8).parameters;
            let profileMoved507=false;
            for(const path of [plan.zero,originalScales507[0].path]) {
                const matches=profileResults507.filter(row => row.path===path);
                compare(matches.length,1,"MAIN507: first post-fit native list uniquely returns each intended optimization path");
                verify(typeof matches[0].value==="number" && Number.isFinite(matches[0].value));
                if(matches[0].value!==profileBaselines507[path]) profileMoved507=true;
            }
            verify(profileMoved507,"MAIN514: first warm-up moves actual zero or scale, never held profile/ADP setup or SU");
            const baseline=profileAdps.map(parameter => parameter.value);
            objective("Release profile and independent La Co O ADPs jointly, carry warm cell background zero and scale, then Save current",16);
            console.info("GUI511_IDLE_BEGIN","settled_idle");
            wait(5000); // Exactly one authorized event-processing idle observation; original outer90s unchanged.
            console.info("GUI511_IDLE_END","settled_idle");
            const current=Session.project, saved=outcome(16), fitted=outcome(13).parameters;
            const independentAdps578=[0,2,3].map(index => outcome(2).parameters.find(row => row.path===plan.adps[index]).path);
            compare(JSON.stringify(Array.from(natural578.adpFree).sort()),JSON.stringify(independentAdps578.sort()),
                "NATURAL610: actual cue-backed ordinary ADP effects reach EXACT requested independent members, never dependent Ba");
            compare([delegatedTyped612,freeClicks,scientificHeaderEvents610],[0,0,0]);
            verify(groupCues610.every(group => group.completed),"NATURAL610: no cue-only incomplete group can pass");
            for(const path of plan.nuisance) {
                const matches=fitted.filter(row => row.path===path);
                compare(matches.length,1);
                verify(matches[0].unique_name===nuisanceIds510[path] && matches[0].dependence==="independent" && matches[0].free===true,
                    "MAIN510: ADP stage carries original cell/background freedom through actual pre-Save post-fit read");
            }
            for(const path of [plan.zero,...plan.profiles]) {
                const matches=fitted.filter(row => row.path===path);
                compare(matches.length,1); verify(matches[0].dependence==="independent" && matches[0].free===true
                    && (path===plan.zero || matches[0].unique_name===profileIds514[path]),
                    "MAIN514: actual final read retains reference full-free SAME original profile and zero roles");
            }
            verify(saved.status==="succeeded" && saved.committed===true && saved.reopened===false
                && saved.active===true && typeof saved.presentation_complete==="boolean",
                "MAIN604: ordinary current Save commits/is active with truthful presentation and no invented reopen");
            compare(current.path,path); verify(!current.modified && !Session.needsSaveAs);
            compare(current.name,"Original Main LBCO owner");compare(current.title,"Original Main title");
            compare(dialogsOpened,0,"CREATE574: filling and current Save never opens a file/folder/fresh Save As chooser");
            compare(import265_owner(current),metadata); compare(visible185_inputs(current),JSON.stringify(inputs));
            compare(fitStarts,2); compare(fitFinishes,2);
            for(const index of [7,12]) { const result=outcome(index);
                verify(["done","max_iterations"].includes(result.status) && result.adopted===true && result.iterations>0,"MAIN504: both actual native fit stages run/adopt, never no-step"); }
            verify([0,2,3].some(i => fitted.filter(row => row.path===plan.adps[i]).length===1
                && fitted.filter(row => row.path===plan.adps[i])[0].value!==baseline[i]),"MAIN504: ADPs genuinely move before Save");
            for(const label of ["La","Co","O"]) { const parameter=visible185_parameter(current,label,"adp_iso");
                verify(parameter.free && parameter.hasUncertainty && Number.isFinite(parameter.uncertainty) && parameter.uncertainty>0 && parameter.value>=0,"MAIN504: real fitted ADPs retain positive finite native SUs"); }
            compare(visible185_parameter(current,"La","adp_iso").value,visible185_parameter(current,"Ba","adp_iso").value);
            aliasesCurrent(current);
            const rounded=save349_science(current); verify(Session.openProject(Probe.referenceUrl("current")),"MAIN504: original Session reader genuinely reopens committed current output");
            tryVerify(() => !Session.project.calculating && Probe.computedCurrent(Session.project.currentExperiment),10000);
            compare(save349_science(Session.project),rounded,"MAIN504: ordinary readback preserves current saved scientific result");
            compare(Session.project.path,path,"CREATE574: ordinary reopen retains the exact user-created saved path");
            compare(import265_owner(Session.project),metadata,
                "CREATE574: normal Save/reopen retains full original user-created name/title/owner metadata");
            aliasesCurrent(Session.project);
            // One ordinary existing manual edit/Undo after readback; never an invented atomic visible-import Undo.
            elapsedPhase511="manual";console.info("GUI511_PHASE","manual",JSON.stringify(observations518));
            visible185_page("analysis"); Ui.click(test,Probe,window,"sideBar.tab.basic");
            Ui.click(test,Probe,window,"parameters.nameFilter"); visible185_type("adp_iso"); rendered();
            const undoOwner=Session.project, undoBefore=undoOwner.canUndo, valuesBefore=visible185_values(undoOwner);
            const inputsBefore=visible185_inputs(undoOwner), declarationsBefore=relation245_declarations(undoOwner);
            const manual=visible185_parameter(undoOwner,"La","adp_iso"), oldValue=manual.value, requested=oldValue+.125;
            const field=visible185_field(manual); Ui.scrollIntoView(field); rendered();
            ++observations518.inputIssue["manual-value"];
            mouseClick(field); visible185_type(String(requested)); keyClick(Qt.Key_Return);
            tryCompare(manual,"value",requested,2000); verify(undoOwner.canUndo,"MAIN504: actual original manual value commit owns ordinary Undo");
            ++observations518.inputIssue["undo"];
            Ui.click(test,Probe,window,"appBar.button.undo");
            tryVerify(() => !Session.project.calculating && Probe.computedCurrent(Session.project.currentExperiment),10000);
            compare(Session.project,undoOwner); compare(visible185_values(Session.project),valuesBefore);
            compare(visible185_inputs(Session.project),inputsBefore); compare(relation245_declarations(Session.project),declarationsBefore);
            compare(Session.project.canUndo,undoBefore,"MAIN504: exactly one actual ordinary Undo restores pre-edit history availability");
            if(window.assistantManualTakeover || !popup.shown) toggle(); rendered();
            const messages=Probe.rows(assistant.messages).filter(row => row.kind==="assistant" && row.status==="completed" && row.text.includes("[Open Report page](edi:report)"));
            compare(messages.length,3,"MAIN504: original completed peer turns retain their truthful explicit Report links");
            const delegates=Ui.itemsWithProperty(Ui.windowRoot(window),"rowId").filter(control => control.rowId===messages[2].id
                && control.assistant===assistant && typeof control.resetDetails==="function" && typeof control.copyTechnicalPayload==="function");
            compare(delegates.length,1);
            const bodies=Ui.itemsWithProperty(delegates[0],"readOnly").filter(control => control.readOnly && control.visible && typeof control.linkAt==="function");
            compare(bodies.length,1); Ui.scrollIntoView(bodies[0]); rendered();
            const body=bodies[0], start=body.getText(0,body.length).indexOf("Open Report page"); verify(start>=0);
            const point=body.positionToRectangle(start+2), x=point.x+Math.max(1,point.width/2), y=point.y+point.height/2;
            ++observations518.inputIssue["report"];
            compare(body.linkAt(x,y),"edi:report"); mouseMove(body,x,y); mouseClick(body,x,y);
            tryCompare(window.appBarCentralTabs,"currentIndex",AppState.Page.Report,2000); rendered();
            const preview=Ui.control(Probe,window,"report.preview"); verify(preview!==null && Ui.rendered(preview));
            compare(preview.report,Session.project.report); tryCompare(Session.project.report,"active",true,2000);
            compare(filePresses,0); compare(fileReleases,0); compare(fileClicks,0); compare(dialogsOpened,0);
            compare(JSON.stringify(Probe.rows(assistant.models)),account);
            compare(JSON.stringify(gui392_json(Probe.rows(assistant.selectedFiles)).map(row =>
                ({id:row.id,name:row.name,bytes:row.bytes,textReadable:row.textReadable,format:row.format}))),selected);
            compare(Probe.readReferenceFile("lbco.cif"),sourceBytes[0]); compare(Probe.readReferenceFile("hrpt.xye"),sourceBytes[1]);
            capture("main504-original-current-report");
        } finally {
            console.log("MAIN504_NATIVE_FACTS",JSON.stringify({observations518:observations518,filePresses:filePresses,fileReleases:fileReleases,fileClicks:fileClicks,dialogsOpened:dialogsOpened,
                createReceipt574:createReceipt574,initialEmptyDocumentCharacters574:emptyDisk574.length,
                natural578:{namesPressed:natural578.namesPressed,namesClicked:natural578.namesClicked,headerPressed:natural578.headerPressed,
                    headerChosen:natural578.headerChosen,menuAdmitted:natural578.menuAdmitted,menuIdentity:menuIdentity583,
                    categoryKeys:natural578.categoryKeys,adpValueCount:natural578.adpValues.size,
                    adpFreeCount:natural578.adpFree.size,cellFree:natural578.cellFree,aliasesReady:natural578.aliasesReady,constraintUsed:natural578.constraintUsed},
                cues:cues,typed:typed,creationInputs612:creationInputs612,delegatedTyped612:delegatedTyped612,freeClicks:freeClicks,scientificHeaderEvents610:scientificHeaderEvents610,
                ordinaryValueWrites610:ordinaryValueWrites610,ordinaryFreeWrites610:ordinaryFreeWrites610,
                groupCues610:groupCues610.map(group => ({objective:group.objective,paths:group.paths,free:group.free,completed:group.completed})),
                fitStarts:fitStarts,fitFinishes:fitFinishes,
                currentOwner:String(Session.project),canCancel:assistant.canCancel,lastError:assistant.lastError}));
            for(const row of bindings) disconnect313(row.life,row.object,row.signal,row.callback);
        }
    }
    //519: same real Main and readonly native caller, both modes; genuine selection/no Project.
    function test_read625_selected_text_is_same_read_in_both_modes() {
        Session.closeProject(); compare(Session.project,null);
        visible185_page("home"); Ui.click(this,Probe,window,"home.start");rendered();
        compare(window.appBarCentralTabs.currentIndex,AppState.Page.Project);
        toggle();
        const token=assistant.beginFileSelection();
        verify(token.length>0 && assistant.addSelectedFiles(token,[Probe.repoUrl("tests/fixtures/assistant/read625/literal.txt")]));
        tryCompare(assistant.selectedFiles,"count",1,2000);
        const selected=Probe.rows(assistant.selectedFiles);compare(selected.length,1);
        assistant.signIn();visible185_ready("read625-bootstrap");
        if(assistant.contextConsentRequired)assistant.signIn();visible185_ready("read625-disclosed");
        verify(assistant.connected && !assistant.contextConsentRequired);
        const originalAssistant=assistant,life=lifetime313(assistant);
        const modes=Probe.rows(assistant.models).map(row=>row.id);
        let cues=0;const onCue=()=>{++cues;};assistant.actionPointerPressed.connect(onCue);
        function result625(identifier,ids) {
            const rows=Probe.rows(assistant.messages).filter(row=>!ids.has(row.id) && row.kind==="activity"
                && row.payload && row.payload.id===identifier);
            compare(rows.length<=1,true);if(!rows.length || rows[0].status!=="completed")return null;
            verify(rows[0].payload.success===true && rows[0].payload.nativeOutcome);
            const content=JSON.parse(JSON.stringify(rows[0].payload.contentItems));
            verify(content.length===1 && content[0].type==="inputText");return JSON.parse(content[0].text);
        }
        const results=[];
        try {
            compare(assistant.showActions,false);
            for(let mode=0;mode<2;++mode) {
                if(mode===1) {
                    const checkbox=item("assistant.showActions");verify(checkbox.visible && checkbox.enabled);
                    mouseClick(checkbox);compare(assistant.showActions,true);
                }
                const ids=new Set(Probe.rows(assistant.messages).map(row=>row.id));
                const page=window.appBarCentralTabs.currentIndex;
                assistant.send("Read the original selected text exactly, without creating a project");
                const call="read625-main-"+mode;
                tryVerify(()=>!assistant.canCancel && result625(call,ids)!==null,2000);
                const value=result625(call,ids);compare(value.status,"completed");
                compare(value.selected_text.file_id,selected[0].id);
                compare(value.selected_text.text,"A\r\n\t\"\\\u0001λ🙂e\u0301\r\n");
                compare(value.selected_text.total_bytes,18);compare(value.selected_text.start,0);
                compare(value.selected_text.end,18);compare(value.selected_text.next_offset,18);
                compare(value.selected_text.eof,true);compare(value.selected_text.complete,true);
                compare(Session.project,null);compare(assistant,originalAssistant);verify(alive313(life));
                compare(window.appBarCentralTabs.currentIndex,page);compare(cues,0);
                compare(JSON.stringify(Probe.rows(assistant.models).map(row=>row.id)),JSON.stringify(modes));
                compare(Probe.rows(assistant.selectedFiles)[0].id,selected[0].id);
                verify(assistant.connected && !assistant.lastError);results.push(value.selected_text);
            }
            compare(JSON.stringify(results[0]),JSON.stringify(results[1]));
        } finally {disconnect313(life,originalAssistant,"actionPointerPressed",onCue);}
        assistant.signOut();tryCompare(assistant,"connected",false,2000);
    }

}
