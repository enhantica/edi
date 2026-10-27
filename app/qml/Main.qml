// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtCore

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The application window (easydiffractionbeta Components/ApplicationWindow.qml, ported): the app bar
// with its tool buttons and the six workflow tabs, the pages, and the status bar. Pages load when
// their tab is enabled, as in the original; a loaded page stays in the window's page view while another
// is shown, so each is told whether it is the shown one (WorkflowPage.current).
EaComponents.ApplicationWindow {
    id: window

    // Same Create API/preferences as the ordinary current-window form. Native
    // callers pass an original Session-bound intent, never another app/window.
    function prepareNativeProjectCreate() {
        if (Session.project !== null) return false;
        AppState.open(AppState.Page.Project);
        return Session.project === null;
    }

    readonly property Item assistantWorkflowPage: {
        const loaders = [projectLoader, structureLoader, experimentLoader, analysisLoader, reportLoader];
        const index = appBarCentralTabs.currentIndex - 1;
        return index >= 0 && index < loaders.length ? loaders[index].item : null;
    }
    readonly property Item activeAssistantHost: assistantWorkflowPage ? assistantWorkflowPage.assistantOverlayHost : assistantFallbackHost
    readonly property Item assistantCurrentPage: assistantWorkflowPage || homePage
    property Item assistantPreviousFocus: null
    property Item assistantPreviousPage: null
    property Item assistantPreviousHost: null
    property var assistantPreviousProject: null
    property int assistantFocusEpoch: 0
    property var assistantManualTakeoverProject: null
    property bool assistantEmptyManualTakeover: false
    readonly property bool assistantManualTakeover: assistantEmptyManualTakeover && Session.project === null
        || assistantManualTakeoverProject !== null && assistantManualTakeoverProject === Session.project

    function containsAssistantItem(ancestor, item) {
        for (let current = item; current; current = current.parent)
            if (current === ancestor)
                return true;
        return false;
    }
    function rehostAssistant() {
        ++assistantFocusEpoch;
        if (!activeAssistantHost || !assistantPanel)
            return;
        const previous = activeFocusItem;
        const restoreChatFocus = containsAssistantItem(assistantPanel.contentItem, previous);
        // The active page identifies focus/currentness; its SwipeView transform
        // must not move the independent fixed sidebar sheet during navigation.
        assistantPanel.parent = assistantFallbackHost;
        const epoch = assistantFocusEpoch;
        const host = activeAssistantHost;
        const project = Session.project;
        if (restoreChatFocus) {
            Qt.callLater(() => {
                if (epoch === assistantFocusEpoch && host === activeAssistantHost && project === Session.project && assistantPanel.visible && assistantPanel.shown && previous && previous.visible && previous.enabled && containsAssistantItem(assistantPanel.contentItem, previous))
                    previous.forceActiveFocus();
            });
        }
    }
    function focusAssistantOpener() {
        if (assistantToggle.enabled) assistantToggle.forceActiveFocus();
        else if (appBarCentralTabs.currentItem) appBarCentralTabs.currentItem.forceActiveFocus();
    }
    function retireAssistantFocus() {
        ++assistantFocusEpoch;
        // Establish a safe current window focus before Qt's Popup exit restoration.
        focusAssistantOpener();
    }
    function restoreAssistantFocus() {
        const previous = assistantPreviousFocus;
        const page = assistantPreviousPage;
        const host = assistantPreviousHost;
        const project = assistantPreviousProject;
        const epoch = assistantFocusEpoch;
        assistantPreviousFocus = null;
        assistantPreviousPage = null;
        assistantPreviousHost = null;
        assistantPreviousProject = null;
        if (assistantManualTakeover) return; // Never redirect a genuine manual event/focus.
        Qt.callLater(() => {
            if (epoch !== assistantFocusEpoch || assistantPanel.shown || assistantPanel.visible)
                return;
            if (page === assistantCurrentPage && host === activeAssistantHost && project === Session.project && previous && previous.visible && previous.enabled && (containsAssistantItem(page, previous) || previous === assistantToggle))
                previous.forceActiveFocus();
            else
                focusAssistantOpener();
        });
    }
    // This binding observes the complete target/ancestor and strip geometry, including movement
    // without a focus change. A partly exposed control remains usable in its uncovered portion.
    readonly property bool assistantHomeFocusCovered: {
        const item = activeFocusItem;
        if (!assistantPanel || !assistantPanel.visible || !item || !containsAssistantItem(assistantCurrentPage, item))
            return false;
        for (let current = item; current; current = current.parent) {
            const geometry = [current.x, current.y, current.width, current.height, current.scale, current.rotation];
            if (!geometry.every(Number.isFinite))
                return false;
        }
        const stripGeometry = [assistantPanel.x, assistantPanel.y, activeAssistantHost.x, activeAssistantHost.y, activeAssistantHost.width, activeAssistantHost.height, window.width, window.height];
        if (!stripGeometry.every(Number.isFinite))
            return false;
        const rectangle = item.mapToItem(assistantPanel.contentItem, 0, 0, item.width, item.height);
        return rectangle.width > 0 && rectangle.height > 0 && rectangle.x >= 0 && rectangle.y >= 0 && rectangle.x + rectangle.width <= assistantPanel.contentItem.width && rectangle.y + rectangle.height <= assistantPanel.contentItem.height;
    }
    function enforceAssistantHomeFocus() {
        if (assistantManualTakeover) return;
        if (assistantHomeFocusCovered) {
            if (assistantPanel.shown)
                assistantPanel.focusComposer();
            else
                focusAssistantOpener();
        }
    }
    onAssistantHomeFocusCoveredChanged: Qt.callLater(enforceAssistantHomeFocus)
    onActiveAssistantHostChanged: rehostAssistant()
    onActiveFocusItemChanged: Qt.callLater(enforceAssistantHomeFocus)


    // The supported minimum (AppSizes): the window cannot be made smaller than every page is made for.
    minimumWidth: AppSizes.minimumAppWidth
    minimumHeight: AppSizes.minimumAppHeight

    // A leading "•" while the open project has unsaved changes (edi ADR-0017 §13).
    title: (Session.project && Session.project.modified ? "• " : "") + ApplicationInfo.name
    appName: ApplicationInfo.name
    appVersion: ApplicationInfo.version
    appDate: ApplicationInfo.releaseDate

    // The icon-only buttons name themselves by their tool tip, for screen readers and the browser checks.
    appBarLeftButtons: [
        // Save (edi ADR-0017 §13): enabled while the project has unsaved changes; a project with no directory
        // of its own (a bundled example's working copy) is saved as. Save as has no app-bar button (the owner,
        // 2026-09-29): Ctrl/Cmd+Shift+S, and Get started's "Save project as…".
        EaElements.ToolButton {
            objectName: "appBar.button.save"
            enabled: Session.project !== null && Session.project.modified
            highlighted: true
            fontIcon: "save"
            ToolTip.text: qsTr("Save current state of the project")
            Accessible.name: ToolTip.text
            onClicked: window.saveProject()
        },
        // Undo: the newest recorded change, an edit of the aliases or constraints or a fit, in the order they
        // were made (edi ADR-0024); a fit restores its pre-fit state (edi undo_fit, one level).
        EaElements.ToolButton {
            objectName: "appBar.button.undo"
            enabled: Session.project !== null && Session.project.canUndo
            fontIcon: "undo"
            ToolTip.text: qsTr("Undo the last change")
            Accessible.name: ToolTip.text
            onClicked: Session.project.undo()
        },
        EaElements.ToolButton {
            objectName: "appBar.button.redo"
            enabled: false
            fontIcon: "redo"
            ToolTip.text: qsTr("Redo the last undone change")
            Accessible.name: ToolTip.text
        },
        EaElements.ToolButton {
            objectName: "appBar.button.reset"
            fontIcon: "backspace"
            ToolTip.text: qsTr("Reset to initial state without project, model and data")
            Accessible.name: ToolTip.text
            onClicked: AppState.afterChanges(() => AppState.reset())
        }
    ]

    appBarRightButtons: [
        EaElements.ToolButton {
            id: assistantToggle
            KeyNavigation.tab: assistantPanel.visible && assistantPanel.shown ? assistantPanel.firstFocusItem : null
            objectName: "assistant.toggle"
            readonly property bool assistantSelected: assistantPanel.shown || (Session.assistant.showingActions && Preferences.assistantShown)
            fontIcon: assistantSelected ? "columns" : "robot"
            readonly property bool rotateRobot: Session.assistant.state === "agent_active"
                && EaStyle.Times.translationChange > 0
            contentItem: Item {
                implicitWidth: Math.max(assistantRobot.implicitWidth, assistantColumns.implicitWidth)
                implicitHeight: Math.max(assistantRobot.implicitHeight, assistantColumns.implicitHeight)
                EaElements.Label {
                    id: assistantRobot
                    anchors.centerIn: parent
                    visible: !assistantToggle.assistantSelected
                    text: "robot"
                    font.family: EaStyle.Fonts.iconsFamily
                    font.pixelSize: assistantToggle.font.pixelSize * 1.25
                    color: assistantToggle.foregroundColor()
                    Accessible.ignored: true
                }
                EaElements.Label {
                    id: assistantColumns
                    anchors.centerIn: parent
                    visible: assistantToggle.assistantSelected
                    text: "columns"
                    font.family: EaStyle.Fonts.iconsFamily
                    font.pixelSize: assistantToggle.font.pixelSize * 1.25
                    color: assistantToggle.foregroundColor()
                    Accessible.ignored: true
                }
            }
            RotationAnimator {
                target: assistantRobot
                running: assistantToggle.rotateRobot
                onStopped: if (!assistantToggle.rotateRobot) assistantRobot.rotation = 0
                loops: Animation.Infinite
                from: 0
                to: 360 * 6
                duration: 2000
                easing.type: Easing.OutInElastic
                easing.amplitude: 1
                easing.period: 0.3
            }
            enabled: ApplicationInfo.assistantAvailable && window.assistantWorkflowPage !== null
            ToolTip.text: !ApplicationInfo.assistantAvailable ? ApplicationInfo.assistantUnavailableReason
                : window.assistantWorkflowPage === null ? qsTr("Assistant is available on project workflow pages")
                : assistantToggle.assistantSelected ? qsTr("Show project sidebar") : qsTr("Open assistant")
            Accessible.name: assistantToggle.assistantSelected ? qsTr("Show project sidebar") : qsTr("Open assistant")
            Accessible.description: ApplicationInfo.assistantUnavailableReason
            onClicked: {
                if (!assistantToggle.enabled)
                    return;
                if (window.assistantManualTakeover) {
                    window.assistantManualTakeoverProject = null;
                    window.assistantEmptyManualTakeover = false;
                    Preferences.assistantShown = true;
                    return;
                }
                if (!Preferences.assistantShown) {
                    ++window.assistantFocusEpoch;
                    window.assistantPreviousFocus = window.activeFocusItem;
                    window.assistantPreviousPage = window.assistantCurrentPage;
                    window.assistantPreviousHost = window.activeAssistantHost;
                    window.assistantPreviousProject = Session.project;
                }
                Preferences.assistantShown = !Preferences.assistantShown;
            }
        },
        EaElements.ToolButton {
            objectName: "appBar.button.preferences"
            fontIcon: "cog"
            ToolTip.text: qsTr("Application preferences")
            Accessible.name: ToolTip.text
            // edi's own preferences dialog (AppPreferencesDialog; edi ADR-0017 §12), not the base's.
            onClicked: Preferences.dialogShown = true
        },
        EaElements.ToolButton {
            objectName: "appBar.button.help"
            fontIcon: "question-circle"
            ToolTip.text: qsTr("Get online help")
            Accessible.name: ToolTip.text
            onClicked: Qt.openUrlExternally(ApplicationInfo.docsUrl)
        },
        EaElements.ToolButton {
            objectName: "appBar.button.bug"
            fontIcon: "bug"
            ToolTip.text: qsTr("Report a bug or issue")
            Accessible.name: ToolTip.text
            onClicked: Qt.openUrlExternally(ApplicationInfo.issuesUrl)
        }
    ]

    appBarCentralTabs.contentData: [
        WorkflowTabButton {
            objectName: "appBar.tab.home"
            fontIcon: "home"
            text: qsTr("Home")
            ToolTip.text: qsTr("Home page")
        },
        WorkflowTabButton {
            id: projectTab
            objectName: "appBar.tab.project"
            page: projectLoader
            pageWanted: AppState.projectPageEnabled
            enabled: AppState.projectPageEnabled && !preparing
            fontIcon: "archive"
            text: qsTr("Project")
            ToolTip.text: qsTr("Project description page")
        },
        WorkflowTabButton {
            id: structureTab
            objectName: "appBar.tab.structure"
            page: structureLoader
            pageWanted: AppState.structurePageEnabled
            enabled: AppState.structurePageEnabled && !preparing
            fontIcon: "layer-group"
            text: qsTr("Structure")
            ToolTip.text: qsTr("Crystal structure page")
        },
        WorkflowTabButton {
            id: experimentTab
            objectName: "appBar.tab.experiment"
            page: experimentLoader
            pageWanted: AppState.experimentPageReached
            enabled: AppState.experimentPageEnabled && !preparing
            fontIcon: "microscope"
            text: qsTr("Experiment")
            ToolTip.text: qsTr("Experimental settings and measured data page")
        },
        WorkflowTabButton {
            id: analysisTab
            objectName: "appBar.tab.analysis"
            page: analysisLoader
            pageWanted: AppState.analysisPageReached
            enabled: AppState.analysisPageEnabled && !preparing
            fontIcon: "calculator"
            text: qsTr("Analysis")
            ToolTip.text: qsTr("Simulation and fitting page")
        },
        WorkflowTabButton {
            id: reportTab
            objectName: "appBar.tab.report"
            page: reportLoader
            pageWanted: AppState.reportPageReached
            enabled: AppState.reportPageEnabled && !preparing
            fontIcon: "clipboard-list"
            text: qsTr("Report")
            ToolTip.text: qsTr("Report of the work done")
        }
    ]

    // edi ADR-0052: an opened project shows at once and its pages follow. Each page is built afresh for each project, in
    // the background (asynchronous loaders, in time slices between frames), one after another in the order Project,
    // Structure, Experiment, Analysis, Report; each tab is enabled once its page is ready. The pages let go of a project
    // before it is replaced, so opening another one meanwhile drops what was being built for the first.
    property bool pagesStarted: true
    readonly property var pageLoaders: [projectLoader, structureLoader, experimentLoader, analysisLoader, reportLoader]
    // The opening's progress, which the status bar shows until every page is built.
    readonly property int pagesWanted: Session.hasProject ? pageLoaders.filter(loader => loader.wanted).length : 0
    readonly property int pagesBuilt: Session.hasProject ? pageLoaders.filter(loader => loader.wanted && loader.status === Loader.Ready).length : 0
    function pageTurn(loader) {
        return pagesStarted && pageLoaders.slice(0, pageLoaders.indexOf(loader)).every(earlier => !earlier.wanted || earlier.status === Loader.Ready);
    }
    Connections {
        target: Session
        function onProjectAboutToChange() {
            window.pagesStarted = false;
            // A page past Project is rebuilt later; its tab is disabled meanwhile, so the window shows Project.
            if (window.appBarCentralTabs.currentIndex > 1)
                window.appBarCentralTabs.setCurrentIndex(1);
        }
        function onProjectChanged() {
            pagesStart.restart();
        }
    }
    Timer {
        id: pagesStart
        interval: 0
        onTriggered: window.pagesStarted = true
    }

    // A disabled tab takes no hover, so the preparing tabs' tooltip comes from here, over the whole tab bar.
    Item {
        id: tabBarOverlay

        parent: window.appBarCentralTabs
        anchors.fill: parent
        z: 10

        HoverHandler {
            id: tabBarHover
        }
        readonly property WorkflowTabButton preparingTab: {
            if (!tabBarHover.hovered)
                return null;
            for (const tab of [projectTab, structureTab, experimentTab, analysisTab, reportTab]) {
                const point = tab.mapFromItem(tabBarOverlay, tabBarHover.point.position.x, tabBarHover.point.position.y);
                if (tab.preparing && tab.contains(point))
                    return tab;
            }
            return null;
        }

        // The app's own tooltip, as every other one (owner, 2026-10-25).
        EaElements.ToolTip {
            objectName: "appBar.preparingToolTip"
            parent: tabBarOverlay.preparingTab !== null ? tabBarOverlay.preparingTab : tabBarOverlay
            visible: tabBarOverlay.preparingTab !== null && EaGlobals.Vars.showToolTips
            text: qsTr("Preparing this page…")
        }
    }

    contentArea: [
        HomePage {
            id: homePage
            objectName: "workflow.home.mainContent"
        },
        Loader {
            id: projectLoader

            readonly property bool wanted: AppState.projectPageEnabled
            active: wanted && window.pageTurn(projectLoader)
            asynchronous: true
            sourceComponent: Component {
                ProjectPage {
                    current: projectLoader.SwipeView.isCurrentItem
                    assistantCovered: assistantPanel.visible
                }
            }
        },
        Loader {
            id: structureLoader

            readonly property bool wanted: AppState.structurePageEnabled
            active: wanted && window.pageTurn(structureLoader)
            asynchronous: true
            sourceComponent: Component {
                StructurePage {
                    current: structureLoader.SwipeView.isCurrentItem
                    assistantCovered: assistantPanel.visible
                }
            }
        },
        Loader {
            id: experimentLoader

            readonly property bool wanted: AppState.experimentPageReached
            active: wanted && window.pageTurn(experimentLoader)
            asynchronous: true
            sourceComponent: Component {
                ExperimentPage {
                    current: experimentLoader.SwipeView.isCurrentItem
                    assistantCovered: assistantPanel.visible
                }
            }
        },
        Loader {
            id: analysisLoader

            readonly property bool wanted: AppState.analysisPageReached
            active: wanted && window.pageTurn(analysisLoader)
            asynchronous: true
            sourceComponent: Component {
                AnalysisPage {
                    current: analysisLoader.SwipeView.isCurrentItem
                    assistantCovered: assistantPanel.visible
                }
            }
        },
        Loader {
            id: reportLoader

            readonly property bool wanted: AppState.reportPageReached
            active: wanted && window.pageTurn(reportLoader)
            asynchronous: true
            sourceComponent: Component {
                ReportPage {
                    current: reportLoader.SwipeView.isCurrentItem
                }
            }
        }
    ]

    statusBar: StatusBar {
        pagesBuilt: window.pagesBuilt
        pagesWanted: window.pagesWanted
    }

    AppPreferencesDialog {}

    Item {
        id: assistantFallbackHost
        objectName: "workflow.home.sidebarHost"
        parent: window.contentItem
        anchors.top: parent.top
        anchors.topMargin: EaStyle.Sizes.appBarHeight
        anchors.bottom: parent.bottom
        anchors.bottomMargin: EaStyle.Sizes.statusBarHeight
        width: EaStyle.Sizes.sideBarWidth
        x: Preferences.sideBarOnLeft ? 0 : parent.width - width
        clip: true
        z: 20
    }
    Binding {
        target: Session.assistant
        property: "actionWindow"
        value: window
    }
    EaElements.RemotePointer {
        id: assistantPointer
        objectName: "assistant.actionPointer"
        moveDuration: 500
        pressDuration: 100
        clickRelaxation: 500
        showHideDuration: 500
        parent: Overlay.overlay.parent
        z: Overlay.overlay.z + 1
        enabled: false
        color: EaStyle.Colors.themeAccent
        Accessible.ignored: true
    }
    Connections {
        target: Session.assistant
        function onActionPageRequested(page, extra) {
            const project = Session.project;
            if (!project) return;
            let target = null;
            let destination = -1;
            if (page === "analysis" && AppState.analysisPageEnabled) {
                target = analysisLoader.item; destination = AppState.Page.Analysis;
            } else if (page === "experiment" && AppState.experimentPageEnabled) {
                target = experimentLoader.item; destination = AppState.Page.Experiment;
            } else if (page === "structure" && AppState.structurePageEnabled) {
                target = structureLoader.item; destination = AppState.Page.Structure;
            }
            if (!target || destination < 0) return;
            AppState.open(destination);
            if (Session.project === project && target === window.assistantWorkflowPage)
                target.showSidebarTab(extra);
        }
        function onActionPointerShown() { assistantPointer.show(); }
        function onActionPointerMoved(position) { const local = assistantPointer.parent.mapFromItem(null, position.x, position.y); assistantPointer.move(local.x, local.y); }
        function onActionPointerPressed() { assistantPointer.click(); }
        function onActionPointerHidden() { assistantPointer.hide(); }
        function onActionManualTakeover() {
            // Synchronous marker only: the sidebar is already exposed. Keep it
            // so until the user explicitly chooses to reopen the assistant.
            window.assistantManualTakeoverProject = Session.project;
            window.assistantEmptyManualTakeover = Session.project === null;
        }
    }
    AssistantPanel {
        id: assistantPanel
        parent: assistantFallbackHost
        assistant: Session.assistant
        shown: Preferences.assistantShown && !Session.assistant.showingActions && !window.assistantManualTakeover && window.assistantWorkflowPage !== null
        toggleControl: assistantToggle
        onAboutToHide: window.retireAssistantFocus()
        onOpened: focusComposer()
        onClosed: window.restoreAssistantFocus()
    }

    Repeater {
        model: [false, true]
        delegate: Rectangle {
            required property bool modelData
            parent: window.contentItem
            visible: assistantPanel.visible && window.assistantWorkflowPage !== null
            x: Preferences.sideBarOnLeft ? 0 : window.contentItem.width - width
            y: modelData ? window.contentItem.height - EaStyle.Sizes.statusBarHeight
                         : EaStyle.Sizes.appBarHeight - height
            width: activeAssistantHost ? activeAssistantHost.width : 0
            height: EaStyle.Sizes.borderThickness
            z: 100
            color: EaStyle.Colors.appBorder
        }
    }


    // Below the supported minimum, which only the browser's page can reach (the owner, 2026-10-25): the empty view's
    // background and a request for more room, over everything, dialogs included. Nothing beneath is torn down, so
    // growing the page back shows the same page, tab, selection and scroll position.
    Rectangle {
        objectName: "app.tooSmall"
        parent: Overlay.overlay
        anchors.fill: parent
        z: 1000000
        visible: window.width < AppSizes.minimumAppWidth || window.height < AppSizes.minimumAppHeight
        color: EaStyle.Colors.contentBackground

        // The content beneath takes no pointer input while it is hidden.
        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.AllButtons
            onWheel: wheel => wheel.accepted = true
        }
        EmptyStateLabel {
            objectName: "app.tooSmall.text"
            anchors.centerIn: parent
            width: parent.width - 2 * EaStyle.Sizes.fontPixelSize
            text: qsTr("Increase the window size")
        }
    }

    // Saving (edi ADR-0017 §13): the core writes (Session.save / saveAs -> edi::save_project_as); a refusal
    // shows the core's message.
    function saveProject() {
        if (Session.project === null)
            return;
        if (Session.needsSaveAs) {
            window.saveProjectAs();
            return;
        }
        // Where the browser keeps nothing, Save says so itself (webStorageUnavailable) with no error of its own.
        if (!Session.save() && Session.lastError !== "")
            saveError.open();
    }
    // Save project as asks first, on every surface (edi ADR-0052 §6, §9). A browser that cannot write the disk offers
    // only a copy as a .zip download (owner, 2026-10-25).
    property string assistantSaveIntent: ""
    function saveProjectAs(intent = "") {
        if (Session.project === null) return;
        if (assistantSaveIntent !== "" && assistantSaveIntent !== intent)
            Session.cancelAssistantSaveAs(assistantSaveIntent);
        assistantSaveIntent = intent;
        saveAsChoice.open();
    }
    function finishAssistantSaveAs(target, zip, copy) {
        const intent = assistantSaveIntent;
        assistantSaveIntent = "";
        return intent === "" ? Session.saveProjectAs(target, zip, copy)
            : Session.completeAssistantSaveAs(intent, target, zip, copy);
    }
    function cancelAssistantSaveAs() {
        const intent = assistantSaveIntent;
        assistantSaveIntent = "";
        if (intent !== "") Session.cancelAssistantSaveAs(intent);
    }
    Connections {
        target: Session
        function onAssistantSaveAsRequested(intent) { window.saveProjectAs(intent); }
    }


    // The sidebar reaches from the window's edge to the Experiment button's centre in the top bar (the owner,
    // 2026-10-22), read from where the centred tabs are, so it follows the window and any change to the buttons.
    Binding {
        target: EaStyle.Sizes
        property: "sideBarWidth"
        value: Math.round(window.width - (window.appBarCentralTabs.x + window.appBarCentralTabs.leftPadding + experimentTab.x + experimentTab.width / 2))
    }

    Shortcut {
        sequences: [StandardKey.Save]
        onActivated: window.saveProject()
    }
    Shortcut {
        sequences: ["Ctrl+Shift+S"]
        onActivated: window.saveProjectAs()
    }
    Connections {
        target: AppState
        function onSaveAsRequested() {
            window.saveProjectAs();
        }
    }

    // Unsaved changes are saved or discarded before the project is replaced, closed or the app quits (edi ADR-0052): a
    // project's temporary folder goes with it.
    property bool quitting: false
    onClosing: close => {
        if (!quitting && Session.project !== null && Session.project.modified) {
            close.accepted = false;
            AppState.afterChanges(() => {
                window.quitting = true;
                window.close();
            });
        }
    }
    Connections {
        target: AppState
        function onChangesQuestion(action) {
            unsavedChanges.action = action;
            unsavedChanges.open();
        }
    }
    AppDialog {
        id: unsavedChanges
        objectName: "unsavedChanges"
        property var action: null
        title: qsTr("Save the changes?")
        standardButtons: Dialog.Save | Dialog.Discard | Dialog.Cancel
        // As wide as its line (owner, 2026-10-25).
        contentWidth: unsavedRow.implicitWidth
        contentHeight: unsavedRow.implicitHeight
        // Save writes in place; a project with nowhere to write yet opens Save as, and the action waits for the user to
        // ask again. In the web app the place is written after Save returns: the action waits until it is, and is
        // dropped if it is not (the window says why).
        property var afterSave: null
        onAccepted: {
            if (Session.needsSaveAs) {
                window.saveProjectAs();
            } else if (Session.save()) {
                if (WebFiles.available)
                    afterSave = action;
                else
                    Qt.callLater(action);
            } else if (Session.lastError !== "") {
                saveError.open();
            }
        }
        Connections {
            target: Session
            function onWebSaveFinished(saved) {
                const waiting = unsavedChanges.afterSave;
                unsavedChanges.afterSave = null;
                // An edit made while the place was written is asked about again.
                if (saved && waiting !== null)
                    AppState.afterChanges(waiting);
            }
        }
        onDiscarded: {
            close();
            Session.discardKeptChanges();
            Qt.callLater(action);
        }

        // The app's warning icon, then the project's name in bold (owner, 2026-10-25).
        Row {
            id: unsavedRow
            spacing: EaStyle.Sizes.fontPixelSize * 0.5

            EaElements.Label {
                anchors.verticalCenter: parent.verticalCenter
                font.family: EaStyle.Fonts.iconsFamily
                color: EaStyle.Colors.orange
                text: "exclamation-triangle"
            }
            EaElements.Label {
                id: unsavedText
                anchors.verticalCenter: parent.verticalCenter
                textFormat: Text.StyledText
                text: qsTr("The current project <b>%1</b> has unsaved changes.").arg(Session.project !== null ? Session.project.name.replace(/&/g, "&amp;").replace(/</g, "&lt;") : "")
            }
        }
    }

    // Save as (edi ADR-0052): first the format and whether to keep working where the project is (a copy), then the
    // system's dialog for the folder or the .zip.
    AppDialog {
        id: saveAsChoice
        objectName: "saveAs.choice"
        onRejected: window.cancelAssistantSaveAs()
        enterAccepts: true
        property bool zip: false
        property bool copy: false
        // A browser without the File System Access API writes no folder and moves no project onto the disk: a copy
        // as a .zip download is all it offers.
        readonly property bool diskWritable: !WebFiles.available || WebStorage.diskAccess
        title: qsTr("Save project as")
        standardButtons: Dialog.Ok | Dialog.Cancel
        // About half the usual dialog width, never narrower than its content (owner, 2026-10-25).
        contentWidth: Math.max(saveAsChoiceColumn.implicitWidth, Math.round(AppSizes.messagesDialogContentWidth / 2))
        contentHeight: saveAsChoiceColumn.implicitHeight
        onAboutToShow: {
            zip = !diskWritable;
            copy = !diskWritable;
        }
        onAccepted: {
            if (!diskWritable)
                Session.downloadWebProject();
            else if (WebFiles.available)
                Session.saveWebProjectAs(zip ? "zip" : "folder", copy);
            else if (zip)
                saveZip.openAt(window.assistantSaveIntent === "" ? Session.suggestedSaveTarget(true) : Session.assistantSaveAsTarget(window.assistantSaveIntent, true));
            else
                saveFolder.openAt(window.assistantSaveIntent === "" ? Session.suggestedSaveTarget(false) : Session.assistantSaveAsTarget(window.assistantSaveIntent, false));
        }

        Column {
            id: saveAsChoiceColumn

            // Folder and Zip archive: one group, rows closer than the usual spacing, no heading (owner, 2026-10-25).
            // A disabled button takes no hover, so its tooltip comes from the item around it.
            Item {
                implicitWidth: saveAsFolder.implicitWidth
                implicitHeight: saveAsFolder.implicitHeight

                ChoiceRadioButton {
                    id: saveAsFolder
                    objectName: "saveAs.folder"
                    enabled: saveAsChoice.diskWritable
                    text: qsTr("Folder")
                    checked: !saveAsChoice.zip
                    onClicked: saveAsChoice.zip = false
                }
                HoverHandler {
                    id: saveAsFolderHover
                }
                EaElements.ToolTip {
                    Component.onCompleted: contentItem.objectName = "saveAs.folderTooltip"
                    text: saveAsChoice.diskWritable ? "" : qsTr("This browser cannot write a folder on your disk; Chrome and Edge can")
                    visible: text !== "" && saveAsFolderHover.hovered && EaGlobals.Vars.showToolTips
                }
            }
            ChoiceRadioButton {
                objectName: "saveAs.zip"
                text: qsTr("Zip archive")
                checked: saveAsChoice.zip
                onClicked: saveAsChoice.zip = true
            }
            // Set apart from the format.
            Item {
                width: 1
                height: EaStyle.Sizes.fontPixelSize
            }
            EaElements.CheckBox {
                objectName: "saveAs.copy"
                enabled: saveAsChoice.diskWritable
                text: qsTr("Save a copy")
                checked: saveAsChoice.copy
                onToggled: saveAsChoice.copy = checked
                // The check box draws the app's tooltip from this text itself.
                ToolTip.text: qsTr("Write the project there and keep working where it is")
            }
        }
    }

    // The project's folder by its name, as a file is named: the dialog is filled with the project's own name, in the
    // folder it is in (owner, 2026-10-25); the folder is made if it is new.
    FileDialog {
        id: saveFolder
        onRejected: window.cancelAssistantSaveAs()
        function openAt(target) {
            currentFolder = target.toString().substring(0, target.toString().lastIndexOf("/"));
            selectedFile = target;
            open();
        }
        title: saveAsChoice.copy ? qsTr("Save a copy of the project as a folder") : qsTr("Save the project as a folder")
        fileMode: FileDialog.SaveFile
        acceptLabel: qsTr("Save")
        onAccepted: {
            if (!window.finishAssistantSaveAs(selectedFile, false, saveAsChoice.copy))
                saveError.open();
        }
    }

    FileDialog {
        id: saveZip
        onRejected: window.cancelAssistantSaveAs()
        function openAt(target) {
            currentFolder = target.toString().substring(0, target.toString().lastIndexOf("/"));
            selectedFile = target;
            open();
        }
        title: saveAsChoice.copy ? qsTr("Save a copy of the project as a .zip") : qsTr("Save the project as a .zip")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "zip"
        nameFilters: [qsTr("Zip archives (*.zip)")]
        acceptLabel: qsTr("Save")
        onAccepted: {
            if (!window.finishAssistantSaveAs(selectedFile, true, saveAsChoice.copy))
                saveError.open();
        }
    }

    // A folder, a project.edi or a .zip dropped on the window opens it (edi ADR-0052).
    DropArea {
        anchors.fill: parent
        onDropped: drop => {
            if (drop.hasUrls && drop.urls.length > 0) {
                drop.accept();
                const url = drop.urls[0];
                AppState.afterChanges(() => Session.openProject(url));
            }
        }
    }

    // The browser's file access: an archive that could not be opened or a project not packed.
    Connections {
        target: WebFiles
        function onFailed(request, message) {
            webFilesError.message = message;
            webFilesError.open();
        }
    }
    // The web app's saves (edi ADR-0052 §9): where the project went, and what a failed write says.
    Connections {
        target: Session
        // The first save of a project into the browser's storage warns in a dialog, later ones in the short notice
        // (owner, 2026-10-25).
        function onWebSaved(kind) {
            if (kind !== "browser")
                return;
            if (browserSaved.warnedFor !== Session.project) {
                browserSaved.warnedFor = Session.project;
                browserSaved.kept = true;
                browserSaved.open();
            } else {
                webNotice.show(qsTr("Saved in this browser only."));
            }
        }
        function onWebStorageUnavailable() {
            browserSaved.kept = false;
            browserSaved.open();
        }
        // Handed to the browser, which may still ask whether to allow it: never "downloaded". Replacing the original
        // is said only for a project opened from a file (owner, 2026-10-25).
        function onWebDownloaded(name, fromFile) {
            let text = qsTr("%1 was handed to the browser to download.").arg(name);
            if (fromFile)
                text += " " + qsTr("To replace the original file, have the browser ask where to save downloads and choose that file.");
            webNotice.show(text);
        }
        function onWebSaveFailed(message) {
            webFilesError.message = message;
            webFilesError.open();
        }
    }
    // Where a save into the browser's storage leaves the project: kept there, which the browser may clear, or, where it
    // keeps nothing, only in this tab. Save project as… is the way onto the disk.
    AppDialog {
        id: browserSaved
        objectName: "webStorageWarning"
        enterAccepts: true
        property var warnedFor: null
        property bool kept: true
        parent: Overlay.overlay
        title: kept ? qsTr("Saved in this browser only") : qsTr("Not saved")
        standardButtons: Dialog.Apply | Dialog.Ok
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: browserSavedRow.implicitHeight
        Component.onCompleted: {
            standardButton(Dialog.Apply).text = qsTr("Save project as…");
            standardButton(Dialog.Apply).objectName = "webStorageWarning.saveAs";
            standardButton(Dialog.Ok).objectName = "webStorageWarning.ok";
        }
        onApplied: {
            close();
            window.saveProjectAs();
        }

        Row {
            id: browserSavedRow
            spacing: EaStyle.Sizes.fontPixelSize * 0.5

            // Centred on the text, however many lines it wraps to (owner, 2026-10-25).
            EaElements.Label {
                objectName: "webStorageWarning.icon"
                anchors.verticalCenter: parent.verticalCenter
                font.family: EaStyle.Fonts.iconsFamily
                color: EaStyle.Colors.orange
                text: "exclamation-triangle"
            }
            EaElements.Label {
                objectName: "webStorageWarning.text"
                width: browserSaved.contentWidth - x
                wrapMode: Text.Wrap
                // The way out in bold (owner, 2026-10-25).
                textFormat: Text.StyledText
                text: browserSaved.kept ? qsTr("Saved in this browser only. The browser may clear what it keeps; use <b>Save project as…</b> to keep a copy on your disk.") : qsTr("This browser keeps nothing for the app here (a private window, for example), so the project is only in this tab. Use <b>Save project as…</b> to keep it on your disk.")
            }
        }
    }

    // A short notice at the foot of the window, gone after a few seconds or on a click.
    Popup {
        id: webNotice
        objectName: "webNotice"
        property string text
        function show(message) {
            text = message;
            open();
            webNoticeTimer.restart();
        }
        parent: Overlay.overlay
        x: Math.round((parent.width - width) / 2)
        y: parent.height - height - EaStyle.Sizes.fontPixelSize * 3
        width: Math.min(parent.width - EaStyle.Sizes.fontPixelSize * 4, EaStyle.Sizes.fontPixelSize * 40)
        padding: EaStyle.Sizes.fontPixelSize
        closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape
        background: Rectangle {
            color: EaStyle.Colors.dialogBackground
            border.color: EaStyle.Colors.appBarBorder
            radius: 2
        }
        contentItem: EaElements.Label {
            objectName: "webNotice.text"
            wrapMode: Text.Wrap
            text: webNotice.text
        }
        Timer {
            id: webNoticeTimer
            interval: 8000
            onTriggered: webNotice.close()
        }
    }
    AppDialog {
        id: webFilesError
        objectName: "webFiles.error"
        property string message
        title: qsTr("The browser could not use the file")
        standardButtons: Dialog.Ok
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: webFilesErrorText.implicitHeight

        EaElements.Label {
            id: webFilesErrorText
            objectName: "webFiles.error.message"
            width: webFilesError.contentWidth
            wrapMode: Text.Wrap
            text: webFilesError.message
        }
    }

    // A created project that could not be saved at its location stays open, unsaved; this says why. Here, not on the
    // Project page, which the new project replaces.
    Connections {
        target: AppState
        function onCreateFailed() {
            createError.open();
        }
    }
    AppDialog {
        id: createError
        objectName: "create.error"
        title: qsTr("The project was not saved")
        standardButtons: Dialog.Ok
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: createErrorText.implicitHeight

        EaElements.Label {
            id: createErrorText
            width: createError.contentWidth
            wrapMode: Text.Wrap
            text: Session.lastError
        }
    }

    AppDialog {
        id: saveError
        objectName: "save.error"
        title: qsTr("The project was not saved")
        standardButtons: Dialog.Ok
        // Sized explicitly, as the Messages dialog and with its width (edi ADR-0017 §13), the message wrapped
        // inside it: a dialog sized by its wrapping label, or narrower than its own button row, is a binding
        // loop on its implicit width.
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: saveErrorText.implicitHeight

        EaElements.Label {
            id: saveErrorText
            width: saveError.contentWidth
            wrapMode: Text.Wrap
            text: Session.lastError
        }
    }

    // A fit's end: its results in diffraction-lib's table, or why it was refused.
    FitResultsDialog {
        id: fitResults
    }
    AppDialog {
        id: fitError
        objectName: "fit.error"
        property string message: ""
        title: qsTr("The fit did not run")
        standardButtons: Dialog.Ok
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: fitErrorText.implicitHeight

        EaElements.Label {
            id: fitErrorText
            width: fitError.contentWidth
            wrapMode: Text.Wrap
            text: fitError.message
        }
    }
    // A refused open (a project, an example) or a refused change of the project (a load of experiments, a structure
    // or data, …) always says why: never a silent no-op (the owner, 2026-10-11).
    AppDialog {
        id: refusal
        objectName: "refusal.dialog"
        property string message: ""
        parent: Overlay.overlay
        standardButtons: Dialog.Ok
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: refusalText.implicitHeight

        EaElements.Label {
            id: refusalText
            width: refusal.contentWidth
            wrapMode: Text.Wrap
            text: refusal.message
        }
    }
    Connections {
        target: Session
        function onProjectChanged() { window.assistantEmptyManualTakeover = false; }
        function onLoadFailed(message) {
            refusal.title = qsTr("The project was not opened");
            refusal.message = message;
            refusal.open();
        }
    }
    Connections {
        target: Session.project
        function onRefused(message) {
            refusal.title = qsTr("The change was not made");
            refusal.message = message;
            refusal.open();
        }
    }
    // A finished fit opens its results unless the preferences say not to; the status bar's fit status opens them then.
    Connections {
        target: Session.project ? Session.project.fit : null
        function onFinished() {
            if (Preferences.showFitResults)
                fitResults.open();
        }
        function onScanFinished() {
            if (Preferences.showFitResults)
                fitResults.open();
        }
        function onRefused(message) {
            fitError.message = message;
            fitError.open();
        }
    }

    // ADR-0031: the window's size and position, in logical pixels, in the store's Window group. Restored at start, after
    // the base's own; a position on no screen now comes back onto the primary screen's available area. The browser's
    // page fills its window and keeps none.
    Settings {
        id: windowSettings
        location: EaGlobals.Vars.settingsFile
        category: "Window"
        property int x: 0
        property int y: 0
        property int width: 0
        property int height: 0
    }
    // Stored only once restored, so the window's first size at start never replaces the kept one.
    property bool geometryRestored: false
    function storeGeometry() {
        if (!window.geometryRestored || WebFiles.available || window.visibility === Window.Maximized || window.visibility === Window.FullScreen)
            return;
        windowSettings.x = window.x;
        windowSettings.y = window.y;
        windowSettings.width = window.width;
        windowSettings.height = window.height;
    }
    function restoreGeometry() {
        if (WebFiles.available || windowSettings.width <= 0 || windowSettings.height <= 0) {
            window.geometryRestored = true;
            window.storeGeometry();
            return;
        }
        window.width = windowSettings.width;
        window.height = windowSettings.height;
        const position = ApplicationInfo.onScreenPosition(windowSettings.x, windowSettings.y, window.width, window.height);
        window.x = position.x;
        window.y = position.y;
        window.geometryRestored = true;
        window.storeGeometry();
    }
    onXChanged: storeGeometry()
    onYChanged: storeGeometry()
    onWidthChanged: storeGeometry()
    onHeightChanged: storeGeometry()

    // The window takes its kept geometry as it is created, after the base's own settings have loaded; edi's
    // preferences go to the base once everything, the base's hidden dialog and its settings included, is complete
    // (Preferences.apply).
    Component.onCompleted: {
        // What Qt draws with, read in the first frame: reported at startup, shown in Develop, and it chooses how the
        // Stacked view draws (edi ADR-0041).
        RenderingInfo.observe(window);
        restoreGeometry();
        Qt.callLater(() => {
            Preferences.apply();
            RecentProjects.refresh();
        });
    }
}
