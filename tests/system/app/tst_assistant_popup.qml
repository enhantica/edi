import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EdiAcceptance 1.0
import EdiChartReference 1.0
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
            if (["manual-override", "close-owner"].includes(data.tag)) {
                tryVerify(() => assistant.showingActions && field.activeFocus && field.text !== field.editText,
                    pacedObservation, "VA2/VA4 SETUP: genuine paced original draft is active before intervention");
                const pointer = item("assistant.actionPointer");
                verify(Ui.rendered(pointer), "VA SETUP: actual accent pointer is rendered during real input");
                if (data.tag === "manual-override") {
                    // The exact original La path is now the genuine displayed filter.
                    // Ba exposure under that filter remains explicitly unqualified.
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
                    compare(la.value, originalValue, "VA2: cancelled uncommitted agent draft cannot write scientific state");
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
        toggle();
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
        toggle();
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
        toggle();
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
                assistant.cancel(); // Explicit ordinary cleanup AFTER the inertness assertions.
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
            tryVerify(() => !assistant.canCancel && !assistant.showingActions, 10000,
                "SL1: actual original request/helper retires before final observation");
            rendered();
            if (!query) {
                compare(field.text, retainedText, "SL1: no later helper cleanup/typing overwrites genuine user text");
                compare(field.preeditText, retainedPreedit, "SL1: original composition survives retirement/rendering");
                verify(field.activeFocus && window.activeFocusItem === field,
                    "SL1: original event keeps its original focused target after cancellation/restore");
                if (!gap) {
                    const outcome = visible185_outcome(call, previousIds);
                    verify(outcome !== null && outcome.status !== "edited",
                        "SL1: cancelled helper never claims its scientific edit completed");
                }
            }
            if (gap) compare(JSON.stringify(visible185_outcome(call, previousIds)), gapOutcome,
                "SL1 GAP: already completed original read stays truthful through request retirement");
            compare(visible185_values(project), values,
                "SL1: focused user input without Return and cancelled original work make no scientific mutation");
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
        toggle();
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
        toggle();
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
        function typed() { ++textEvents; }
        function applied() { ++applies; }
        function active() { if (assistant.showingActions) { ++starts; if (cleanupCallbackActive) requestPresentationStartedInside = true; } }
        function fitFinished() { ++finished; }
        function fitRunning() { if (project.fit.running) ++running; }
        let cleanupArmed = false;
        function resetBoundary() {
            if (!cleanupArmed || cleanupSends || stage.aliasCount !== 0) return;
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
                stagedId: editor.text, stagedDefinition: definition.text, cleanupSends: cleanupSends,
                requestPresentationStartedInside: requestPresentationStartedInside,
                originalStage: originalStage === null ? null : String(originalStage),
                currentStage: String(stage.assistantStage), pointerOpacity: pointer.opacity, outcome: visible185_outcome(call, previousIds)}));
            editor.textEdited.disconnect(typed);
            definition.textEdited.disconnect(typed);
            apply.clicked.disconnect(applied);
            assistant.showingActionsChanged.disconnect(active);
            project.fit.finished.disconnect(fitFinished);
            project.fit.runningChanged.disconnect(fitRunning);
            stage.aliasCountChanged.disconnect(resetBoundary);
            if (assistant.canCancel) assistant.cancel();
        }
    }

}
