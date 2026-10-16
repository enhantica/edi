import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EdiAcceptance 1.0
import "../../unit/app/UiInteraction.js" as Ui

// Owner 99d50f71f supersedes the former second-dock and alternate-entry tests.
// Real Main/Session only. No provider, seeded message model or synthetic busy state.
TestCase {
    name: "AssistantPopup"
    when: windowShown
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
    function toggle() {
        const control = item("assistant.toggle");
        verify(control.visible && control.enabled, "I16/popup: existing appbar button remains actionable");
        const requested = !Preferences.assistantShown;
        pointerObservation("before-toggle", control, requested);
        const receipts = [];
        function receipt(name) {
            receipts.push(name);
            pointerObservation("button-" + name, control, requested);
        }
        function pressedChanged() { receipt("pressedChanged=" + control.pressed); }
        function released() { receipt("released"); }
        function clicked() { receipt("clicked"); }
        function canceled() { receipt("canceled"); }
        control.pressedChanged.connect(pressedChanged);
        control.released.connect(released);
        control.clicked.connect(clicked);
        control.canceled.connect(canceled);
        try {
            pointerObservation("before-pointer-move", control, requested);
            mouseMove(control, control.width / 2, control.height / 2);
            pointerObservation("after-pointer-move", control, requested);
            mouseClick(control);
        } finally {
            control.pressedChanged.disconnect(pressedChanged);
            control.released.disconnect(released);
            control.clicked.disconnect(clicked);
            control.canceled.disconnect(canceled);
            console.log("APPBAR_CONTROL_RECEIPTS", JSON.stringify(receipts));
        }
        pointerObservation("after-toggle", control, requested);
        try {
            tryCompare(popup, "visible", requested, 2000, "I16/slide: appbar request reaches actual opened/fully closed visibility");
        } finally {
            pointerObservation("after-toggle-wait", control, requested);
        }
        if (requested)
            tryCompare(popup, "opened", true, 2000, "I16/slide: settled opening waits for actual enter completion");
        rendered();
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
            toggle();
    }
    function cleanupTestCase() {
        eligibleProject();
        if (Preferences.assistantShown)
            toggle();
        Session.closeProject();
        Preferences.sideBarSide = oldSide;
        EaStyle.Colors.theme = oldTheme;
        Preferences.toolTips = oldToolTips;
        window.destroy();
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
        toggle();
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
        const composer = item("assistant.composer");
        composer.forceActiveFocus();
        composer.insert(0, "PbSO4 — unsent\ncell 5.43");
        composer.select(2, 8);
        const draft = composer.text;
        const start = composer.selectionStart;
        const end = composer.selectionEnd;
        const messages = assistant.messages;
        capture("assistant-popup-" + data.tag);
        toggle();
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
        toggle();
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
            toggle();
        const button = item("assistant.toggle");
        keyboardObservation("before-focus-" + data.tag, button);
        button.forceActiveFocus();
        keyboardObservation("after-focus-" + data.tag, button);
        keyClick(Qt.Key_Space);
        keyboardObservation("after-space-" + data.tag, button);
        tryCompare(popup, "visible", true, 500, "I16/POP1: real keyboard appbar activation opens chat");
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
            toggle();
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "I16/POP2: real project establishes a live workflow scope");
        window.appBarCentralTabs.currentIndex = 1;
        rendered();
        const oldField = item("project.name");
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
        verify(!oldField.activeFocus, "I16/POP2: retained or replaced offscreen field cannot receive restored focus");
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
        tryVerify(() => editor.activeFocus, 500, "I16/HDR1: normal opening places real input focus in the actual composer");
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
            toggle();
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "I16/slide: actual independent project anchors the live sidebar/plot");
        Preferences.sideBarSide = "Right";
        window.appBarCentralTabs.currentIndex = 1;
        rendered();
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
        toggle();
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
        const row = Ui.itemsWithProperty(Ui.windowRoot(window), "rowId").filter(item => item.rowId === retained.id
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
    function test_visible185_actual_native_manual_interaction_data() {
        return ["default-off", "analysis-value-free", "wavelength", "manual-override",
            "dirty-valid-value", "dirty-invalid-value", "dirty-valid-free", "dirty-invalid-free",
            "dirty-valid-fit", "dirty-invalid-fit", "real-fit", "fit-stop", "close-owner",
            "unsupported-values", "unsupported-free", "unsupported-relations", "normal-relations"].map(tag => ({tag: tag}));
    }
    function test_visible185_actual_native_manual_interaction(data) {
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
        toggle(); // Actual original toggle exposes manual controls before setup input.
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
            field = Ui.control(Probe, window, "instrument.setup_wavelength");
            verify(field !== null && field.item === wavelength[0] && Ui.exposed(field),
                "VA SETUP: original supplied wavelength has its genuine current field");
            free = null;
        }
        const fitButton = fitCase ? Ui.control(Probe, window, "fitting.start") : null;
        if (fitCase) verify(fitButton !== null && Ui.exposed(fitButton), "VA FIT SETUP: genuine normal Start fitting button is exposed");
        let typed = 0, toggled = 0, activeStarts = 0, fitStarted = 0, finished = 0;
        let capturedTyping = false;
        let spellings = [], writes = [], fitClicks = 0;
        const editedParameter = data.tag === "wavelength" ? wavelength[0] : la;
        function valueReceipt() { writes.push(editedParameter.value); }
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
        function fitReceipt() { if (project.fit.running) ++fitStarted; }
        function finishedReceipt() {
            ++finished;
            console.log("VISIBLE185_FINISHED", data.tag, JSON.stringify({finished: finished,
                actualOutcome: project.fit.outcome, running: project.fit.running,
                currentOwner: Session.project === project}));
        }
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
                draftField = Ui.control(Probe, window, "cell.length_a");
                verify(draftField !== null && draftField.enabled && Ui.exposed(draftField),
                    "VA3 SETUP: genuine editable manual field is exposed before delegated work");
                mouseClick(draftField);
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
            if (["manual-override", "close-owner"].includes(data.tag)) {
                tryVerify(() => assistant.showingActions && field.activeFocus && field.text !== field.editText,
                    10000, "VA2/VA4 SETUP: genuine paced original draft is active before intervention");
                const pointer = item("assistant.actionPointer");
                verify(Ui.rendered(pointer), "VA SETUP: actual accent pointer is rendered during real input");
                if (data.tag === "manual-override") {
                    const manual = visible185_free(ba);
                    const beforeFree = ba.free;
                    let manualToggles = 0;
                    function manualReceipt() { ++manualToggles; }
                    manual.toggled.connect(manualReceipt);
                    try {
                        const point = Ui.clickPoint(manual);
                        verify(point !== null, "VA2 SETUP: original manual event has a genuine exposed target");
                        mouseClick(manual, point.x, point.y);
                        tryCompare(ba, "free", !beforeFree, 2000,
                            "VA2: original user checkbox event reaches its original target while cancellation restores view");
                        compare(manualToggles, 1, "VA2: user input is delivered once, never retargeted or replayed");
                    } finally { manual.toggled.disconnect(manualReceipt); }
                    tryCompare(assistant, "showingActions", false, 10000,
                        "VA2: original visible input retires after real manual takeover");
                    compare(la.value, originalValue, "VA2: cancelled uncommitted agent draft cannot write scientific state");
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
                tryVerify(() => project.fit.running && assistant.showingActions, 10000,
                    "VA FIT SETUP: actual worker is running before real Stop, never a fake pending interval");
                const stop = item("assistant.stopVisibleAction");
                verify(stop.visible && stop.enabled && Ui.exposed(stop), "VA FIT SETUP: real appbar Stop is available");
                mouseClick(stop);
            }
            if (data.tag !== "close-owner") {
                try {
                    tryVerify(() => visible185_outcome(call, requestPreviousIds) !== null && !assistant.canCancel && !assistant.showingActions,
                        10000, "VA: actual original native outcome settles after its own input/worker owner");
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
                } else if (data.tag.startsWith("unsupported-")) {
                    verify(["refused", "unavailable"].includes(outcome.status) && typeof outcome.message === "string" && outcome.message.length > 0,
                        "VA: unsupported visible operations fail honestly before write without hidden fallback");
                    compare(visible185_values(project), originalValues, "VA: unsupported batch/relation cannot partly mutate the owner");
                    compare(JSON.stringify([Probe.rows(project.analysis.aliases), Probe.rows(project.analysis.constraints)]),
                        originalDeclarations, "VA: unsupported relation preserves every original declaration");
                    compare(typed + toggled, 0, "VA: refusal cannot be a decorative event sequence over a hidden write");
                } else if (data.tag === "normal-relations") {
                    compare(outcome.status, "edited", "VA SETUP CONTROL: identical valid relation payload is admitted in normal OFF mode");
                    verify(project.analysis.aliases.count === declarationRows[0].length + 2
                        && project.analysis.constraints.count === declarationRows[1].length + 1,
                        "VA SETUP CONTROL: genuine valid relation append proves unsupported-visible payload is not a malformed refusal");
                    compare(activeStarts, 0, "VA: normal relation control does not invent visible activity");
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
                        verify(typed > 0 && spellings.includes("1.49"), "VA: real field receives original numeric spelling through actual key events");
                        compare(JSON.stringify(writes), JSON.stringify([1.49]), "VA: incomplete numeric drafts never become scientific intermediate writes");
                    } else {
                        compare(la.value, 0.6, "VA1: genuine original Analysis parameter changes through actual input");
                        if (data.tag === "analysis-value-free") {
                            compare(la.free, true, "VA1: actual visual-only free checkbox changes its own ParameterItem");
                            verify(typed > 0 && toggled === 1, "VA1: actual typing and one real checkbox toggle accompany scientific edits");
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
                activeStarts: activeStarts, fitStarted: fitStarted, finished: finished, fitClicks: fitClicks,
                currentOwner: Session.project === project, connected: assistant.connected}));
        } finally {
            if (field && field.textEdited) field.textEdited.disconnect(typedReceipt);
            if (free && free.toggled) free.toggled.disconnect(freeReceipt);
            if (editedParameter && editedParameter.valueChanged) editedParameter.valueChanged.disconnect(valueReceipt);
            if (fitButton && fitButton.clicked) fitButton.clicked.disconnect(fitClickReceipt);
            assistant.showingActionsChanged.disconnect(activeReceipt);
            if (project && project.fit) {
                project.fit.runningChanged.disconnect(fitReceipt);
                project.fit.finished.disconnect(finishedReceipt);
                if (Session.project === project && project.fit.running) project.fit.cancel();
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
        toggle();
        const textCase = data.tag.endsWith("text-id");
        visible185_page(textCase ? "structure" : textFormatted ? "experiment" : "analysis");
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
        Ui.scrollIntoView(field);
        rendered();
        verify(field.visible && field.enabled && !field.readOnly && Ui.exposed(field),
            "DRAFT1 SETUP: actual common editor is actionable inside the real viewport");
        const cleanControl = data.tag.endsWith("formatted");
        if (cleanControl) {
            mouseClick(field);
            visible185_type("0.3333333333333333");
            keyClick(Qt.Key_Return);
            const actual = textFormatted ? Probe.rows(project.currentExperiment.background)[0].position
                : project.analysis.chiSquareTolerance;
            compare(actual, 1 / 3,
                "DRAFT1 SETUP: real typing/Return establishes the explicit full-precision control");
            mouseClick(field);
            verify(field.text !== String(actual),
                "DRAFT1 SETUP: unedited formatted spelling actually differs from the core number");
        } else {
            mouseClick(field);
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
                && !assistant.canCancel && !assistant.showingActions, 10000,
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
}
