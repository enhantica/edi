import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EasyApplication.Gui.Style as EaStyle
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
        tryVerify(() => !Ui.moving(window.contentItem), 2000, "I16/popup: actual navigation finishes before geometry observations");
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
        mouseMove(button, button.width / 2, button.height / 2);
        const candidates = Probe.objectsWithProperty(button, "closePolicy");
        const ownedToolTips = [];
        for(let i=0;i<candidates.length;++i)
            if(candidates[i] instanceof EaElements.ToolTip)ownedToolTips.push(candidates[i]);
        compare(ownedToolTips.length, 1, "NAV1 SETUP: actual Ea ToolButton owns one painted custom tooltip");
        const toolTipPopup = ownedToolTips[0];
        tryVerify(() => toolTipPopup.visible && toolTipPopup.contentItem !== null
            && Ui.rendered(toolTipPopup.contentItem) && Ui.text(toolTipPopup.contentItem).includes(tooltip),
            2000, "NAV1: actual hovered tooltip popup renders its action text, not merely attached metadata");
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
}
