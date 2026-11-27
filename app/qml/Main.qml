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
    appBar.objectName: "appBar"
    appBarCentralTabs.objectName: "appBar.workflow"

    // The app bar is drawn under the system title bar on macOS and Windows (Qt 6.9 expanded client
    // area). The system window buttons stay; the app bar's own buttons move clear of them by the safe-area margins.
    readonly property bool mergedTitleBar: ApplicationInfo.mergedTitleBar
    // The same flags main.cpp sets, here too so the window has them from creation, before its kept position is
    // restored (on Windows the merged strip changes what Qt counts as frame).
    readonly property int mergedFlags: Qt.Window | Qt.ExpandedClientAreaHint | Qt.NoTitleBarBackgroundHint
    // Windows: no title hint, so Qt draws no icon or title in the strip, only the three buttons.
    readonly property int windowsMergedFlags: mergedFlags | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint
    flags: !mergedTitleBar ? Qt.Window : Qt.platform.os === "windows" ? windowsMergedFlags : mergedFlags
    // Let the app bar reach the top edge (Qt keeps the content inside the safe area by default); the system
    // buttons then sit in a strip at the top of the app bar, and every group of the app bar moves down below it.
    topPadding: mergedTitleBar ? 0 : undefined
    // macOS: the red traffic light's left edge, set from C++ (mac_titlebar.mm); the first app bar button lines up
    // with it. The bar keeps its height.
    property real trafficLightsLeft: -1
    function setUpMergedTitleBar() {
        if (!mergedTitleBar)
            return;
        // Our left and right buttons sit 4 px lower, clear of the system buttons; the page tabs stay.
        appBar.children[0].anchors.verticalCenterOffset = 4;
        appBar.children[2].anchors.verticalCenterOffset = 4;
        if (Qt.platform.os !== "osx")
            return;
        const left = appBar.children[0];
        const base = left.anchors.leftMargin;
        left.anchors.leftMargin = Qt.binding(() => trafficLightsLeft >= 0 ? trafficLightsLeft : base);
    }
    // Dragging the empty app bar moves the window, and a double click maximizes or restores it, as a title bar does.
    // Starts on press, before any button or tab can take the press, so a drag works anywhere on the empty bar.
    PointHandler {
        parent: window.appBar
        enabled: window.mergedTitleBar
        acceptedButtons: Qt.LeftButton
        grabPermissions: PointerHandler.TakeOverForbidden
        onActiveChanged: if (active && !window.appBarControlAt(point.position))
            window.startSystemMove()
    }
    function appBarControlAt(position) {
        for (const row of appBar.children) {
            const local = appBar.mapToItem(row, position.x, position.y);
            if (row.visible && row.contains(local) && row.childAt(local.x, local.y))
                return true;
        }
        return false;
    }
    TapHandler {
        parent: window.appBar
        enabled: window.mergedTitleBar
        acceptedButtons: Qt.LeftButton
        onDoubleTapped: window.visibility === Window.Maximized ? window.showNormal() : window.showMaximized()
    }

    // Same Create API/preferences as the ordinary current-window form. Native
    // callers pass an original Session-bound intent, never another app/window.
    property var assistantCreateGuard: null
    // The assistant creates no project while a tutorial runs.
    readonly property bool tutorialRunning: AppState.tutorialRunning || Session.hasProjectSetAside
    function prepareNativeProjectCreate(intent) {
        return ApplicationInfo.prepareProjectCreation(intent);
    }
    function finishNativeProjectCreateGuard(intent) {
        ApplicationInfo.finishProjectCreationGuard(intent);
    }

    function createNativeProject(values, intent) {
        return ApplicationInfo.createProjectFromIntent(values, intent);
    }
    function showNativeReport(project) {
        return ApplicationInfo.showProjectReport(project);
    }

    readonly property WorkflowPage assistantWorkflowPage: ApplicationInfo.assistantBuilt ? ApplicationInfo.assistantWorkflowPage() : null
    readonly property Item activeAssistantHost: assistantWorkflowPage ? assistantWorkflowPage.assistantOverlayHost : assistantFallbackHost
    readonly property Item assistantCurrentPage: assistantWorkflowPage || homePage
    property Item assistantPreviousFocus: null
    property Item assistantPreviousPage: null
    property Item assistantPreviousHost: null
    property var assistantPreviousProject: null
    property int assistantFocusEpoch: 0
    property var assistantManualTakeoverProject: null
    property bool assistantEmptyManualTakeover: false
    property bool assistantManualPane: false
    readonly property bool assistantManualTakeover: assistantEmptyManualTakeover && Session.project === null || assistantManualTakeoverProject !== null && assistantManualTakeoverProject === Session.project

    // The web build carries no assistant (ADR-0023 §6): its procedures are not there to call.
    function containsAssistantItem(ancestor, item) {
        return ApplicationInfo.assistantBuilt ? ApplicationInfo.assistantContainsItem(ancestor, item) : false;
    }
    function rehostAssistant() {
        if (ApplicationInfo.assistantBuilt)
            ApplicationInfo.rehostAssistant();
    }
    function focusAssistantOpener() {
        if (ApplicationInfo.assistantBuilt)
            ApplicationInfo.focusAssistantOpener();
    }
    function retireAssistantFocus() {
        if (ApplicationInfo.assistantBuilt)
            ApplicationInfo.retireAssistantFocus();
    }
    function restoreAssistantFocus() {
        if (ApplicationInfo.assistantBuilt)
            ApplicationInfo.restoreAssistantFocus();
    }
    // This binding observes the complete target/ancestor and strip geometry, including movement
    // without a focus change. A partly exposed control remains usable in its uncovered portion.
    readonly property bool assistantHomeFocusCovered: ApplicationInfo.assistantBuilt ? ApplicationInfo.assistantHomeFocusCovered() : false
    function enforceAssistantHomeFocus() {
        if (!ApplicationInfo.assistantBuilt)
            return;
        ApplicationInfo.enforceAssistantHomeFocus();
    }
    onAssistantHomeFocusCoveredChanged: Qt.callLater(enforceAssistantHomeFocus)
    onActiveAssistantHostChanged: rehostAssistant()
    onActiveFocusItemChanged: Qt.callLater(enforceAssistantHomeFocus)

    // The supported minimum (AppSizes): the window cannot be made smaller than every page is made for.
    minimumWidth: AppSizes.minimumAppWidth
    // The headless platforms warn on every later size-hint change and nobody drags their window, so they keep one value.
    minimumHeight: Qt.platform.pluginName === "offscreen" || Qt.platform.pluginName === "minimal" ? AppSizes.minimumAppHeight(AppSizes.sideBarBelowWidth) : AppSizes.minimumAppHeight(width)
    // Below 600 px the app bar keeps Save, Undo, the pages as icons, the assistant and Preferences (ADR-0103 decision 2).
    readonly property bool compactAppBar: AppSizes.compact

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
            // Not while a save is running: the project takes no change until it is done (edi ADR-0069).
            enabled: Session.project !== null && Session.project.modified && !Session.project.saving
            highlighted: true
            fontIcon: "save"
            // A disabled control's tooltip says why and how to enable it (the owner, 2026-11-02).
            ToolTip.text: enabled ? qsTr("Save the project") : Session.project === null ? qsTr("No project to save: open or create one first") : Session.project.saving ? qsTr("Saving the project: Save is available again when it finishes") : qsTr("Nothing to save: the project has no unsaved changes")
            Accessible.name: qsTr("Save the project")
            onClicked: window.saveProject()
        },
        // Undo: the newest recorded change, an edit of the aliases or constraints or a fit, in the order they
        // were made (edi ADR-0024); a fit restores its pre-fit state (edi undo_fit, one level).
        EaElements.ToolButton {
            objectName: "appBar.button.undo"
            enabled: Session.project !== null && Session.project.canUndo
            fontIcon: "undo"
            ToolTip.text: enabled ? qsTr("Undo the last change") : qsTr("Nothing to undo: edit the project, its aliases or constraints, or run a fit first")
            Accessible.name: qsTr("Undo the last change")
            onClicked: Session.project.undo()
        },
        EaElements.ToolButton {
            objectName: "appBar.button.redo"
            visible: !window.compactAppBar
            enabled: false
            fontIcon: "redo"
            ToolTip.text: qsTr("Redo is not available yet")
            Accessible.name: qsTr("Redo the last undone change")
        },
        EaElements.ToolButton {
            objectName: "appBar.button.reset"
            visible: !window.compactAppBar
            fontIcon: "backspace"
            ToolTip.text: qsTr("Clear: close the project and start again")
            Accessible.name: ToolTip.text
            onClicked: ApplicationInfo.resetProjectAfterChanges()
        }
    ]

    function updateApplication() {
        window.launchMaintenance(false);
    }

    function launchMaintenance(openMaintenanceTool: bool) {
        AppState.afterChanges(() => {
            if (openMaintenanceTool ? DesktopUpdates.startMaintenance() : DesktopUpdates.startUpdate()) {
                window.quitting = true;
                window.close();
            } else {
                updateLaunchFailed.maintenance = openMaintenanceTool;
                updateLaunchFailed.open();
            }
        });
    }
    AppDialog {
        id: updateLaunchFailed
        objectName: "update.launchFailed"
        property bool maintenance: false
        title: maintenance ? qsTr("The Maintenance Tool did not open") : qsTr("The updater did not open")
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: updateFailureText.implicitHeight
        standardButtons: Dialog.Ok
        EaElements.Label {
            id: updateFailureText
            text: DesktopUpdates.status
            wrapMode: Text.Wrap
            width: AppSizes.messagesDialogContentWidth
        }
    }

    // Qt draws some things itself, such as the Windows title bar's buttons: its colour scheme follows edi's Theme.
    Connections {
        target: EaStyle.Colors
        function onThemeChanged() {
            ApplicationInfo.applyColorScheme(EaStyle.Colors.theme);
        }
    }

    // In the browser, System follows the page's prefers-color-scheme, which can change while the app runs.
    Timer {
        interval: 1000
        repeat: true
        running: Qt.platform.os === "wasm" && EaStyle.Colors.theme === 2
        onTriggered: ApplicationInfo.applyColorScheme(EaStyle.Colors.theme)
    }

    property string updateNotifiedVersion: ""
    Connections {
        target: DesktopUpdates
        function onCheckFinished(manual) {
            if (DesktopUpdates.available && (manual || Preferences.updateNotifications && window.updateNotifiedVersion !== DesktopUpdates.availableVersion)) {
                window.updateNotifiedVersion = DesktopUpdates.availableVersion;
                updateAvailableNotice.open();
            }
        }
    }
    WhatsNewDialog {
        id: updateAvailableNotice
        objectName: "update.availableNotice"
        updateMode: true
        onUpdateRequested: window.updateApplication()
    }

    appBarRightButtons: [
        EaElements.ToolButton {
            id: assistantToggle
            KeyNavigation.tab: window.assistantPanelVisible && window.assistantPanelShown ? window.assistantPanel.firstFocusItem : null
            objectName: "assistant.toggle"
            readonly property bool assistantSelected: ApplicationInfo.assistantAvailable && window.assistantPanelShown
            fontIcon: assistantSelected ? "columns" : "robot"
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
            // Without the assistant built in (the web, ADR-0023 §6) the button stays, and opens the note instead.
            enabled: !ApplicationInfo.assistantBuilt || !ApplicationInfo.assistantAvailable || window.assistantWorkflowPage !== null
            ToolTip.text: !ApplicationInfo.assistantBuilt ? qsTr("AI assistant: available in the desktop app") : !ApplicationInfo.assistantAvailable ? ApplicationInfo.assistantUnavailableReason : window.assistantWorkflowPage === null ? qsTr("Assistant is available on project workflow pages") : assistantToggle.assistantSelected ? qsTr("Show project sidebar") : qsTr("Open assistant")
            Accessible.name: !ApplicationInfo.assistantAvailable ? qsTr("AI assistant unavailable") : assistantToggle.assistantSelected ? qsTr("Show project sidebar") : qsTr("Open assistant")
            Accessible.description: ApplicationInfo.assistantBuilt ? ApplicationInfo.assistantUnavailableReason : qsTr("The AI assistant is available in the desktop app")
            onClicked: ApplicationInfo.assistantBuilt ? ApplicationInfo.assistantToolbarActivated(window, assistantToggle, window.assistantPanel, Session, Preferences, assistantDesktopOnlyDialog) : assistantDesktopOnlyDialog.open()
        },
        // The tooltip switch (the owner, 2026-11-01): a click turns tooltips off, or back on at the last level used; a right
        // click opens Preferences, where the level and the delay are.
        EaElements.ToolButton {
            id: toolTipsButton

            readonly property bool on: Preferences.toolTipLevel !== "Off"

            objectName: "appBar.button.toolTips"
            visible: !window.compactAppBar
            fontIcon: on ? "comment" : "comment-slash"
            ToolTip.text: on ? qsTr("Turn tooltips off; right-click for their level and delay") : qsTr("Turn tooltips on; right-click for their level and delay")
            Accessible.name: on ? qsTr("Turn tooltips off") : qsTr("Turn tooltips on")
            onClicked: Preferences.toolTipLevel = on ? "Off" : Preferences.toolTipLastLevel

            TapHandler {
                acceptedButtons: Qt.RightButton
                onTapped: Preferences.dialogShown = true
            }
        },
        EaElements.ToolButton {
            objectName: "appBar.button.preferences"
            fontIcon: "cog"
            ToolTip.text: qsTr("Application preferences")
            Accessible.name: ToolTip.text
            // edi's own preferences dialog (AppPreferencesDialog; edi ADR-0017 §12), not the base's.
            onClicked: Preferences.dialogShown = true
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
    readonly property int pagesWanted: ApplicationInfo.workflowPagesCount(false)
    readonly property int pagesBuilt: ApplicationInfo.workflowPagesCount(true)
    function pageTurn(loader) {
        return ApplicationInfo.workflowPageTurn(loader);
    }
    Connections {
        target: Session
        // The window's questions and Save As about the replaced project end before anything of the next one shows.
        function onProjectReplacing() {
            ApplicationInfo.retireProjectAsks();
        }
        function onProjectAboutToChange() {
            ApplicationInfo.workflowProjectChanging();
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

        // Only while a tab is preparing: the handler takes the hover from the tabs under it, which then lose their
        // hover colours.
        HoverHandler {
            id: tabBarHover

            enabled: [projectTab, structureTab, experimentTab, analysisTab, reportTab].some(tab => tab.preparing)
        }
        readonly property WorkflowTabButton preparingTab: ApplicationInfo.workflowPreparingTab()

        // The app's own tooltip, as every other one (owner, 2026-10-25).
        EaElements.ToolTip {
            objectName: "appBar.preparingToolTip"
            parent: tabBarOverlay.preparingTab !== null ? tabBarOverlay.preparingTab : tabBarOverlay
            requested: tabBarOverlay.preparingTab !== null
            text: qsTr("Preparing this page…")
        }
    }

    // The Home page's intro at start, over the whole window (HomeIntro).
    HomeIntro {
        id: homeIntro
        parent: Overlay.overlay
        anchors.fill: parent
        wordmark: homePage.wordmark
        Component.onCompleted: if (Preferences.introAnimationOn)
            Qt.callLater(homeIntro.start)
    }

    contentArea: [
        HomePage {
            id: homePage
            objectName: "workflow.home.mainContent"
            introRunning: homeIntro.running
        },
        Loader {
            id: projectLoader

            readonly property bool wanted: AppState.projectPageEnabled
            // Once made, the page stays while another project replaces the open one (edi ADR-0052): a press on it, or its
            // open Load menu, would go with a page let go.
            property bool made: false
            active: wanted && !window.quitting && (made || window.pageTurn(projectLoader))
            onLoaded: made = true
            onActiveChanged: {
                if (!active)
                    made = false;
            }
            // In the browser built at once: a click on the page was lost while it was being built in the background.
            asynchronous: Qt.platform.os !== "wasm"
            sourceComponent: Component {
                ProjectPage {
                    current: projectLoader.SwipeView.isCurrentItem
                    assistantCovered: window.assistantPanelVisible
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
                    assistantCovered: window.assistantPanelVisible
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
                    assistantCovered: window.assistantPanelVisible
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
                    assistantCovered: window.assistantPanelVisible
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
        id: appStatusBar

        assistantChatShown: window.assistantPanelVisible && window.assistantPanelShown
        assistantManualTakeover: window.assistantManualTakeover
        objectName: "statusBar"
        pagesBuilt: window.pagesBuilt
        pagesWanted: window.pagesWanted
        tutorial: tutorialPanel
        onUpdateRequested: updateAvailableNotice.open()
    }

    // The rare "Enjoying EasyDiffraction?" bar, just above the status bar (edi ADR-0063).
    LikesBar {
        id: likesBar

        // At the window's bottom edge: standing on the status bar while it shows (its strip is the window's bottom
        // statusBarHeight), at the very bottom while it is hidden (Home with no project), never over it.
        parent: window.contentItem
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: appStatusBar.visible ? EaStyle.Sizes.statusBarHeight : 0
        z: 50  // above the window's overlay hosts (the sidebar host is 20)
        fit: Session.project ? Session.project.fit : null
        tutorialRunning: AppState.tutorialRunning
        survey: surveyBar
    }
    // The survey invitation, in the same place; never in the same session as the likes bar.
    SurveyBar {
        id: surveyBar

        parent: window.contentItem
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: appStatusBar.visible ? EaStyle.Sizes.statusBarHeight : 0
        z: 50
        likes: likesBar
        fit: Session.project ? Session.project.fit : null
        tutorialRunning: AppState.tutorialRunning
    }

    AppPreferencesDialog {
        onMaintenanceRequested: window.launchMaintenance(true)
    }

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
        target: ApplicationInfo.assistantBuilt ? Session.assistant : null
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
        color: EaStyle.Colors.themeForegroundHighlight
        Accessible.ignored: true
    }
    Connections {
        target: ApplicationInfo.assistantBuilt ? Session.assistant : null
        function onActionPageRequested(page, extra) {
            ApplicationInfo.windowAssistantAction(0, page, extra);
        }
        function onActionControlsRequested() {
            window.assistantManualPane = false;
        }
        function onShowingActionsChanged() {
            ApplicationInfo.windowAssistantAction(1, undefined, undefined);
        }
        function onActionPointerShown() {
            assistantPointer.show();
        }
        function onActionPointerMoved(position) {
            const local = assistantPointer.parent.mapFromItem(null, position.x, position.y);
            assistantPointer.move(local.x, local.y);
        }
        function onActionPointerPressed() {
            assistantPointer.click();
        }
        function onActionPointerHidden() {
            ApplicationInfo.windowAssistantAction(2, undefined, undefined);
        }
        function onStateChanged() {
            ApplicationInfo.windowAssistantAction(2, undefined, undefined);
        }
        function onActionManualTakeover() {
            ApplicationInfo.windowAssistantAction(3, undefined, undefined);
        }
    }
    AppDialog {
        id: assistantDesktopOnlyDialog
        objectName: "assistant.desktopOnly"
        parent: Overlay.overlay
        title: qsTr("AI assistant")
        standardButtons: ApplicationInfo.assistantBuilt ? Dialog.Ok : Dialog.Close
        enterAccepts: true
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: assistantDesktopOnlyColumn.implicitHeight

        Column {
            id: assistantDesktopOnlyColumn
            width: assistantDesktopOnlyDialog.contentWidth
            spacing: AppSizes.unit
            EaElements.Label {
                id: assistantDesktopOnlyText
                objectName: "assistant.desktopOnly.message"
                width: parent.width
                wrapMode: Text.Wrap
                // The web build's note (the owner, 2026-11-04): what the desktop app offers and how it signs in.
                text: ApplicationInfo.assistantBuilt ? ApplicationInfo.assistantUnavailableReason : qsTr("The AI assistant is available in the desktop app with your ChatGPT account. It signs in through OpenAI's official app server; your plan's usage limits apply.")
            }
            IconLink {
                objectName: "assistant.desktopOnly.updates"
                visible: ApplicationInfo.assistantBuilt && DesktopUpdates.managed
                fontIcon: "cog"
                text: qsTr("Open Updates in Preferences to add the AI assistant")
                onClicked: {
                    assistantDesktopOnlyDialog.close();
                    Preferences.dialogTab = "updates";
                    Preferences.dialogShown = true;
                }
            }
            AssistantDownloadLink {
                visible: !ApplicationInfo.assistantBuilt
            }
        }
    }

    // The assistant's panel, only in a build that carries the assistant (ADR-0023 §6): loaded by file name with its
    // required properties, so a build without the component still loads this window. `assistantPanel` keeps the name
    // the procedures resolve, as a var: null without the assistant.
    readonly property var assistantPanel: assistantPanelLoader.item
    readonly property bool assistantPanelVisible: assistantPanel ? assistantPanel.visible : false
    readonly property bool assistantPanelShown: assistantPanel ? assistantPanel.shown : false
    Loader {
        id: assistantPanelLoader
        Component.onCompleted: {
            if (ApplicationInfo.assistantBuilt)
                setSource("Components/AssistantPanel.qml", {
                    assistant: Session.assistant,
                    toggleControl: assistantToggle
                });
        }
        onLoaded: {
            const panel = window.assistantPanel;
            panel.parent = assistantFallbackHost;
            panel.shown = Qt.binding(() => (Session.assistant.chatRevealRequested || Preferences.assistantShown && (!Session.assistant.showingActions || window.assistantManualPane) && !window.assistantManualTakeover) && window.assistantWorkflowPage !== null);
            // Under the window's questions the user answers while the assistant works (Close project, Save as): they are
            // centred over the sidebar, where the panel lies, and a panel raised after them covered their buttons.
            panel.z = Qt.binding(() => unsavedChanges.visible || saveAsChoice.visible ? -1 : 0);
            panel.aboutToHide.connect(window.retireAssistantFocus);
            // `opened` is the popup's state as well as its signal: watch the state.
            panel.openedChanged.connect(() => {
                if (panel.opened)
                    panel.focusComposer();
            });
            panel.closed.connect(window.restoreAssistantFocus);
        }
    }

    Repeater {
        model: [false, true]
        delegate: Rectangle {
            required property bool modelData
            parent: window.contentItem
            visible: window.assistantPanelVisible && window.assistantWorkflowPage !== null
            x: Preferences.sideBarOnLeft ? 0 : window.contentItem.width - width
            y: modelData ? window.contentItem.height - EaStyle.Sizes.statusBarHeight : EaStyle.Sizes.appBarHeight - height
            width: window.activeAssistantHost ? window.activeAssistantHost.width : 0
            height: EaStyle.Sizes.borderThickness
            z: 100
            color: EaStyle.Colors.appBorder
        }
    }
    // Help and feedback, opened from anywhere through AppState (edi ADR-0063), and the popup offering a crashed run's log
    // to it (edi ADR-0062).
    FeedbackDialog {
        id: feedbackDialog

        roomWidth: window.width
    }
    // The run log's line for each page opened (edi ADR-0062).
    Connections {
        target: EaGlobals.Vars
        function onAppBarCurrentIndexChanged() {
            RunLog.note(`page: ${["home", "project", "structure", "experiment", "analysis", "report"][EaGlobals.Vars.appBarCurrentIndex] ?? EaGlobals.Vars.appBarCurrentIndex}`);
        }
    }
    Connections {
        target: AppState
        function onFeedbackRequested(kind, log) {
            feedbackDialog.openAs(kind, log);
        }
        function onUpdateDialogRequested() {
            updateAvailableNotice.open();
        }
        function onCrashReported(log, text) {
            feedbackDialog.openAs("problem", log, text, []);
        }
        function onProblemReported(message, file) {
            feedbackDialog.openAs("problem", "", message, file === "" ? [] : [ApplicationInfo.fileAttachment(file, true)]);
        }
        function onTutorialRequested(tutorial) {
            tutorialPanel.start(tutorial);
        }
        function onWhatsNewRequested() {
            whatsNewDialog.open();
        }
    }
    // What's new (edi ADR-0067), also opened once by itself at the first start after an update.
    WhatsNewDialog {
        id: whatsNewDialog
    }
    CrashDialog {}
    // A running tutorial's steps (edi ADR-0064).
    TutorialPanel {
        id: tutorialPanel
        objectName: "tutorialPanel"
    }

    // Below the supported minimum, which only the browser's page can reach (the owner, 2026-10-25): the empty view's
    // background and a request for more room, over everything, dialogs included. Nothing beneath is torn down, so
    // growing the page back shows the same page, tab, selection and scroll position.
    Rectangle {
        objectName: "app.tooSmall"
        parent: Overlay.overlay
        anchors.fill: parent
        z: 1000000
        visible: window.width < AppSizes.minimumAppWidth || window.height < AppSizes.minimumAppHeight(window.width)
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
        ApplicationInfo.saveCurrentProject();
    }
    // Save project as asks first, on every surface (edi ADR-0052 §6, §9). A browser that cannot write the disk offers
    // only a copy as a .zip download (owner, 2026-10-25).
    property string assistantSaveIntent: ""
    function saveProjectAs(intent = "") {
        ApplicationInfo.saveCurrentProjectAs(intent);
    }
    function finishAssistantSaveAs(target, zip, copy) {
        return ApplicationInfo.finishProjectSaveAs(target, zip, copy);
    }
    function cancelAssistantSaveAs() {
        ApplicationInfo.cancelProjectSaveAs();
    }
    Connections {
        target: Session
        function onAssistantSaveAsRequested(intent) {
            window.saveProjectAs(intent);
        }
    }

    // The sidebar's width follows the window smoothly (AppSizes.sideBarWidthFor; ADR-0103 decision 3); below
    // AppSizes.sideBarBelowWidth it sits under the main view at the window's full width (WorkflowPage).
    Binding {
        target: AppSizes
        property: "appWidth"
        value: window.width
    }
    Binding {
        target: EaStyle.Sizes
        property: "sideBarBelow"
        value: AppSizes.appWidth < AppSizes.sideBarBelowWidth
    }
    // The width steps as last measured, so a chosen width mode holds before any project's table is laid out, and kept
    // whenever a table notes them again (the owner, 2026-11-22).
    function restoreSideBarSteps(): void {
        if (Preferences.sideBarStepBounds > 0 && AppSizes.sideBarSteps.bounds === undefined)
            AppSizes.sideBarSteps = {
                "bounds": Preferences.sideBarStepBounds,
                "values": Preferences.sideBarStepValues,
                "compact": Preferences.sideBarStepCompact
            };
    }
    Connections {
        target: AppSizes
        function onSideBarStepsChanged() {
            const steps = AppSizes.sideBarSteps;
            if (steps.bounds === undefined)
                return;
            Preferences.sideBarStepBounds = steps.bounds;
            Preferences.sideBarStepValues = steps.values;
            Preferences.sideBarStepCompact = steps.compact;
        }
    }
    // Full's fixed width, edi main's rule: from the window's edge to the Experiment button's centre in the top bar.
    Binding {
        target: AppSizes
        property: "sideBarMainWidth"
        value: Math.round(window.width - (window.appBarCentralTabs.x + window.appBarCentralTabs.leftPadding + experimentTab.x + experimentTab.width / 2))
    }
    Binding {
        target: EaStyle.Sizes
        property: "sideBarWidth"
        value: EaStyle.Sizes.sideBarBelow ? Math.round(AppSizes.appWidth) : AppSizes.sideBarWidthChosen(AppSizes.appWidth, Preferences.sideBarWidthMode, Preferences.sideBarManualWidth)
    }

    Shortcut {
        sequences: [StandardKey.Save]
        onActivated: window.saveProject()
    }
    Shortcut {
        sequences: ["Ctrl+Shift+S"]
        // As the Save menu's EasyDiffraction folder entry, or a .zip copy where the browser writes no folder.
        onActivated: saveAsChoice.saveWith(false, false)
    }
    Connections {
        target: AppState
        function onSaveAsRequested() {
            saveAsChoice.saveWith(false, false);
        }
        function onSaveAsFormatRequested(zip, copy) {
            saveAsChoice.saveWith(zip, copy);
        }
        // Once unsaved changes are dealt with (saved, discarded or none), the chooser: here, since a discard closes the
        // project and the page that asked is rebuilt. In the browser, its own chooser.
        function onOpenProjectRequested(zip) {
            AppState.afterChanges(() => {
                if (WebFiles.available)
                    Session.openWebProject(zip ? "file" : "folder");
                else
                    window.openChooser(zip ? openZipChooser : openFolderChooser, {});
            });
        }
        function onImportProjectRequested(importer) {
            AppState.afterChanges(() => window.openChooser(importChooser, {
                    importer: importer
                }));
        }
    }
    // A Load chooser opens on the next turn for the project whose changes were just dealt with, and what it chooses
    // opens only while that project is still open: another one published meanwhile was never asked about. The
    // browser's chooser carries its request the same way (Session.openWebProject).
    function openChooser(chooser, properties) {
        const owner = Session.projectGeneration();
        Qt.callLater(() => {
            if (Session.projectGeneration() !== owner)
                return;
            const ask = window.showNativeAsk(chooser, properties);
            ask.ownerGeneration = owner;
            ask.open();
        });
    }
    // A native picker is made for each showing and goes with it. A platform may deliver a dialog's answer after its
    // close(); that late answer then reaches only the retired showing's own object, never the next showing's.
    property var nativeAsk: null
    // The last showing a handoff or a newer ask ended, kept until it is deleted: a test can still deliver its old
    // answer there and see that it changes nothing.
    property var retiredAsk: null
    function showNativeAsk(component, properties) {
        window.endNativeAsk(window.nativeAsk);
        window.nativeAsk = component.createObject(window, properties);
        return window.nativeAsk;
    }
    // Ends a showing on every path, in this order: no longer the current one and its answer void, then closed (its
    // close() answers Rejected at once, which now finds nothing), then deleted.
    function endNativeAsk(ask) {
        if (!ask || ask.ended)
            return;
        ask.ended = true;
        ask.ownerGeneration = -2;
        if (window.nativeAsk === ask)
            window.nativeAsk = null;
        if (ask.visible) {
            window.retiredAsk = ask;
            ask.close();
        }
        ask.destroy();
    }
    function openChosen(location) {
        const owner = Session.projectGeneration();
        Qt.callLater(() => {
            if (Session.projectGeneration() === owner)
                Session.openProject(location);
        });
    }

    // Unsaved changes are saved or discarded before the project is replaced, closed or the app quits (edi ADR-0052): a
    // project's temporary folder goes with it.
    property bool quitting: false
    onClosing: close => ApplicationInfo.projectWindowClosing(close)
    Connections {
        target: AppState
        function onChangesQuestion(action, abandoned) {
            ApplicationInfo.projectChangesQuestion(action, abandoned);
        }
        function onCloseQuestion(action, abandoned, closing) {
            ApplicationInfo.projectChangesQuestion(action, abandoned, false, closing);
        }
        // The same question about the user's own project while a tutorial holds it aside (edi ADR-0064).
        function onSetAsideChangesQuestion(action) {
            ApplicationInfo.projectChangesQuestion(action, null, true);
        }
    }
    // The question's state, which outlives each showing: what waits on the answer, a browser Save's action and an
    // untitled guard Save's (ApplicationInfo). Each showing is its own dialog, made when it asks and gone with it, and
    // each answer names its showing: an answer from a showing that ended (a handoff, or a newer question) does
    // nothing, and every showing takes one answer only.
    // Each showing is placed as the declared dialogs were: on the window's overlay, the base Dialog's parent, centred by
    // AppDialog.
    QtObject {
        id: unsavedChanges
        property var action: null
        property var abandoned: null
        property var nativeCreation: null
        // The assistant closes a saved project: nothing to save, only Close project or Cancel.
        property bool saved: false
        property string closing: ""
        // The project the answer was given about: a browser Save's waiting action runs only while it is open.
        property real ownerGeneration: -1
        // The tutorial is bringing its own project back to answer this question (ApplicationInfo.retireProjectAsks).
        property bool restoring: false
        // Save writes in place; a project with nowhere to write yet opens Save as, and the action waits for the user to
        // ask again. In the web app the place is written after Save returns: the action waits until it is, and is
        // dropped if it is not (the window says why).
        property var afterSave: null
        // The question is about the user's own project, which a tutorial holds aside: Save and Discard first bring it
        // back and end the tutorial, on the next turn; Cancel leaves the tutorial running.
        property bool setAside: false
        property var afterSaveAbandoned: null
        // A guard Save on untitled work (ADR-0100): the waiting action runs only when that operation is saved.
        property var untitledId: 0
        property var untitledAction: null
        property var untitledAbandoned: null
        // The project the guard asked about: the action runs only while it is still the open one.
        property var untitledProject: null
        // The showing on screen, `{dialog, ownerGeneration, answered, gone}`, or null; kept until its exit has ended.
        property var ask: null
        readonly property var dialog: ask !== null ? ask.dialog : null
        readonly property bool visible: ask !== null && ask.dialog.visible

        function abandonAction() {
            ApplicationInfo.abandonUnsavedProjectAction();
        }
        // An open question that has not been answered takes the new action as it is; otherwise a new showing asks.
        function open() {
            if (unsavedChanges.ask !== null && !unsavedChanges.ask.answered)
                return;
            unsavedChanges.retire();
            const showing = {
                dialog: unsavedQuestion.createObject(window.contentItem, {
                    parent: window.Overlay.overlay
                }),
                ownerGeneration: Session.projectGeneration(),
                answered: false,
                gone: false
            };
            showing.dialog.opened.connect(() => unsavedChanges.shown(showing));
            showing.dialog.accepted.connect(() => unsavedChanges.answer(showing, "save"));
            showing.dialog.discarded.connect(() => unsavedChanges.answer(showing, "discard"));
            showing.dialog.rejected.connect(() => unsavedChanges.answer(showing, "cancel"));
            showing.dialog.closed.connect(() => unsavedChanges.forget(showing));
            unsavedChanges.ask = showing;
            showing.dialog.open();
        }
        function close() {
            if (unsavedChanges.ask !== null)
                unsavedChanges.ask.dialog.close();
        }
        function shown(showing) {
            if (showing === unsavedChanges.ask && !showing.answered)
                ApplicationInfo.unsavedProjectOpened();
        }
        function answer(showing, kind) {
            // Discard leaves a dialog open by itself.
            if (kind === "discard")
                showing.dialog.close();
            if (showing !== unsavedChanges.ask || showing.answered)
                return;
            showing.answered = true;
            if (showing.ownerGeneration !== Session.projectGeneration())
                return;
            unsavedChanges.ownerGeneration = showing.ownerGeneration;
            if (kind === "save")
                ApplicationInfo.acceptUnsavedProject();
            else if (kind === "discard")
                ApplicationInfo.discardUnsavedProject();
            else
                unsavedChanges.abandonAction();
        }
        function forget(showing) {
            if (unsavedChanges.ask === showing)
                unsavedChanges.ask = null;
            if (!showing.gone) {
                showing.gone = true;
                showing.dialog.destroy();
            }
        }
        // Ends the showing at once, an answered one still closing included: true when nobody had answered it.
        function retire(): bool {
            const showing = unsavedChanges.ask;
            if (showing === null)
                return false;
            unsavedChanges.ask = null;
            const pending = !showing.answered;
            showing.answered = true;
            window.retiredAsk = showing.dialog;
            AppState.retirePopup(showing.dialog);
            unsavedChanges.forget(showing);
            return pending;
        }
    }
    Connections {
        target: Session
        function onWebSaveFinished(saved) {
            ApplicationInfo.projectWebSaveFinished(saved);
        }
        function onUntitledSettled(id, state) {
            ApplicationInfo.projectUntitledSettled(id, state);
        }
    }
    Component {
        id: unsavedQuestion
        AppDialog {
            id: question
            objectName: "unsavedChanges"
            title: unsavedChanges.saved ? qsTr("Close the project?") : qsTr("Save the changes?")
            standardButtons: unsavedChanges.saved ? Dialog.Yes | Dialog.Cancel : Dialog.Save | Dialog.Discard | Dialog.Cancel
            onAboutToShow: {
                const yes = question.standardButton(Dialog.Yes);
                if (yes !== null) {
                    yes.text = qsTr("Close project");
                    yes.objectName = "unsavedChanges.close";
                }
            }
            // Name the existing visible controls, as Save as names its real native OK button.
            Binding {
                target: question.opened ? question.header : null
                when: target !== null
                property: "objectName"
                value: "unsavedChanges.title"
            }
            Binding {
                target: question.opened ? question.standardButton(Dialog.Discard) : null
                when: target !== null
                property: "objectName"
                value: "unsavedChanges.discard"
            }
            Binding {
                target: question.opened ? question.standardButton(Dialog.Save) : null
                when: target !== null
                property: "objectName"
                value: "unsavedChanges.save"
            }
            Binding {
                target: question.opened ? question.standardButton(Dialog.Cancel) : null
                when: target !== null
                property: "objectName"
                value: "unsavedChanges.cancel"
            }
            // As wide as its line (owner, 2026-10-25).
            contentWidth: unsavedRow.implicitWidth
            contentHeight: unsavedRow.implicitHeight

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
                    anchors.verticalCenter: parent.verticalCenter
                    textFormat: Text.StyledText
                    text: ApplicationInfo.windowUnsavedText()
                }
            }
        }
    }

    // Save as (edi ADR-0052): the format and whether to keep working where the project is (a copy) come from Get
    // started's Save menu (saveWith), then the system's dialog for the folder or the .zip. The dialog itself opens only
    // for the assistant's delegated save, which presses its OK.
    QtObject {
        id: saveAsChoice
        property bool zip: false
        property bool copy: false
        // Measured data (edi ADR-0088 point 5): for a project that reads data from outside its folder, copied into the
        // project or kept linked, preset from Data on save.
        property bool linkedData: false
        property string dataChoice: "copy"
        // A browser without the File System Access API writes no folder and moves no project onto the disk: a copy
        // as a .zip download is all it offers.
        readonly property bool diskWritable: !WebFiles.available || WebStorage.diskAccess
        // The showing on screen, `{dialog, ownerGeneration, answered, gone}`, or null: each showing is its own dialog,
        // and an answer acts only from the current one, once, for the project it asked about.
        property var ask: null
        readonly property bool visible: ask !== null && ask.dialog.visible

        function open() {
            saveAsChoice.retire();
            saveAsChoice.linkedData = Session.project !== null && Session.project.hasLinkedData();
            saveAsChoice.dataChoice = Session.project !== null ? Session.project.presetSaveData() : "copy";
            ApplicationInfo.prepareProjectSaveChoice();
            const showing = {
                dialog: saveAsQuestion.createObject(window.contentItem, {
                    parent: window.Overlay.overlay
                }),
                ownerGeneration: Session.projectGeneration(),
                answered: false,
                gone: false
            };
            showing.dialog.accepted.connect(() => saveAsChoice.answer(showing, true));
            showing.dialog.rejected.connect(() => saveAsChoice.answer(showing, false));
            showing.dialog.closed.connect(() => saveAsChoice.forget(showing));
            saveAsChoice.ask = showing;
            showing.dialog.open();
        }
        function answer(showing, accepted) {
            if (showing !== saveAsChoice.ask || showing.answered)
                return;
            showing.answered = true;
            if (showing.ownerGeneration !== Session.projectGeneration())
                return;
            if (!accepted) {
                Session.setNextSaveData("");
                window.cancelAssistantSaveAs();
                return;
            }
            Session.setNextSaveData(saveAsChoice.linkedData ? saveAsChoice.dataChoice : "");
            ApplicationInfo.acceptProjectSaveChoice();
        }
        // The format and copy chosen from Get started's Save menu: the same save as the dialog's OK, without asking
        // again. Linked measured data follows Data on save's preset.
        function saveWith(asZip, asCopy) {
            if (Session.project === null)
                return;
            saveAsChoice.retire();
            window.assistantSaveIntent = "";
            saveAsChoice.linkedData = Session.project.hasLinkedData();
            saveAsChoice.dataChoice = Session.project.presetSaveData();
            saveAsChoice.zip = asZip || !saveAsChoice.diskWritable;
            saveAsChoice.copy = asCopy || !saveAsChoice.diskWritable;
            Session.setNextSaveData(saveAsChoice.linkedData ? saveAsChoice.dataChoice : "");
            ApplicationInfo.acceptProjectSaveChoice();
        }
        function forget(showing) {
            if (saveAsChoice.ask === showing)
                saveAsChoice.ask = null;
            if (!showing.gone) {
                showing.gone = true;
                showing.dialog.destroy();
            }
        }
        // Ends the showing at once: true when nobody had answered it.
        function retire(): bool {
            const showing = saveAsChoice.ask;
            if (showing === null)
                return false;
            saveAsChoice.ask = null;
            const pending = !showing.answered;
            showing.answered = true;
            window.retiredAsk = showing.dialog;
            AppState.retirePopup(showing.dialog);
            saveAsChoice.forget(showing);
            return pending;
        }
    }
    Component {
        id: saveAsQuestion
        AppDialog {
            id: saveAsDialog
            objectName: "saveAs.choice"
            enterAccepts: true
            readonly property Item nativeAcceptButton: opened ? standardButton(Dialog.Ok) : null
            onOpened: ApplicationInfo.windowSaveChoiceOpened()
            title: qsTr("Save project as")
            standardButtons: Dialog.Ok | Dialog.Cancel
            // About half the usual dialog width, never narrower than its content (owner, 2026-10-25).
            contentWidth: Math.max(saveAsChoiceColumn.implicitWidth, Math.round(AppSizes.messagesDialogContentWidth / 2))
            contentHeight: saveAsChoiceColumn.implicitHeight

            Column {
                id: saveAsChoiceColumn
                objectName: "project.saveChoice"

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
                        requested: saveAsFolderHover.hovered
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
                Item {
                    width: 1
                    height: EaStyle.Sizes.fontPixelSize
                    visible: saveAsChoice.linkedData
                }
                EaElements.Label {
                    visible: saveAsChoice.linkedData
                    text: Session.categoryTitle("data")
                }
                ChoiceRadioButton {
                    objectName: "saveAs.dataCopy"
                    visible: saveAsChoice.linkedData
                    text: qsTr("Copy into the project")
                    checked: saveAsChoice.dataChoice === "copy"
                    onClicked: saveAsChoice.dataChoice = "copy"
                }
                ChoiceRadioButton {
                    objectName: "saveAs.dataLinked"
                    visible: saveAsChoice.linkedData
                    text: qsTr("Keep linked")
                    checked: saveAsChoice.dataChoice === "linked"
                    onClicked: saveAsChoice.dataChoice = "linked"
                }
            }
        }
    }

    // Open project's and Import's choosers (Get started's Load menu), both opening where one was last chosen, one
    // object per showing (showNativeAsk). The project read replaces the current one on the next turn.
    Component {
        id: openFolderChooser
        FolderDialog {
            id: chooser
            objectName: "load.folderChooser"
            // The project it was opened over (window.openChooser); -2 once answered or retired.
            property real ownerGeneration: -1
            property bool ended: false
            title: qsTr("Open an edi project folder")
            acceptLabel: qsTr("Open")
            currentFolder: DialogFolders.folder("openProject", "")
            onAccepted: {
                if (window.nativeAsk === chooser && ApplicationInfo.takeOwnedAnswer()) {
                    DialogFolders.remember("openProject", selectedFolder);
                    window.openChosen(selectedFolder);
                }
                window.endNativeAsk(chooser);
            }
            onRejected: {
                window.endNativeAsk(chooser);
            }
        }
    }
    Component {
        id: openZipChooser
        FileDialog {
            id: chooser
            objectName: "load.zipChooser"
            property real ownerGeneration: -1
            property bool ended: false
            title: qsTr("Open an edi project archive")
            nameFilters: [qsTr("edi project archives (*.zip)")]
            currentFolder: DialogFolders.folder("openProject", "")
            onAccepted: {
                if (window.nativeAsk === chooser && ApplicationInfo.takeOwnedAnswer()) {
                    DialogFolders.remember("openProject", selectedFile);
                    window.openChosen(selectedFile);
                }
                window.endNativeAsk(chooser);
            }
            onRejected: {
                window.endNativeAsk(chooser);
            }
        }
    }
    // An import opens as a new, unsaved project, as Open does.
    Component {
        id: importChooser
        FileDialog {
            id: chooser
            objectName: "load.importChooser"
            property var importer: null
            property real ownerGeneration: -1
            property bool ended: false
            title: importer !== null ? qsTr("Import a %1 project").arg(importer.program) : ""
            nameFilters: importer !== null ? [importer.nameFilter] : []
            currentFolder: DialogFolders.folder("importProject", "")
            onAccepted: {
                if (window.nativeAsk === chooser && ApplicationInfo.takeOwnedAnswer()) {
                    DialogFolders.remember("importProject", selectedFile);
                    window.openChosen(selectedFile);
                }
                window.endNativeAsk(chooser);
            }
            onRejected: {
                window.endNativeAsk(chooser);
            }
        }
    }

    // The project's folder by its name, as a file is named: the dialog is filled with the project's own name, in the
    // folder it is in (owner, 2026-10-25); the folder is made if it is new. One object per showing, as Load's.
    Component {
        id: saveFolderPicker
        FileDialog {
            id: picker
            objectName: "saveAs.folderPicker"
            // The project it was opened over (ApplicationInfo.openProjectSavePicker); -2 once answered or retired, a
            // retirement having ended its Save As already.
            property real ownerGeneration: -1
            property bool ended: false
            readonly property bool saving: true
            onRejected: {
                if (window.nativeAsk === picker && ApplicationInfo.takeOwnedAnswer()) {
                    Session.setNextSaveData("");
                    window.cancelAssistantSaveAs();
                }
                window.endNativeAsk(picker);
            }
            // In the folder a project was last saved to, unless the assistant chose the place (the owner, 2026-11-17).
            function openAt(target) {
                ApplicationInfo.openProjectSavePicker(window.assistantSaveIntent === "" ? DialogFolders.retarget("saveProject", target) : target);
            }
            title: saveAsChoice.copy ? qsTr("Save a copy of the project as a folder") : qsTr("Save the project as a folder")
            fileMode: FileDialog.SaveFile
            acceptLabel: qsTr("Save")
            onAccepted: {
                if (window.nativeAsk === picker && ApplicationInfo.takeOwnedAnswer()) {
                    DialogFolders.remember("saveProject", selectedFile);
                    ApplicationInfo.acceptProjectSavePicker(false);
                }
                window.endNativeAsk(picker);
            }
        }
    }
    Component {
        id: saveZipPicker
        FileDialog {
            id: picker
            objectName: "saveAs.zipPicker"
            property real ownerGeneration: -1
            property bool ended: false
            readonly property bool saving: true
            onRejected: {
                if (window.nativeAsk === picker && ApplicationInfo.takeOwnedAnswer()) {
                    Session.setNextSaveData("");
                    window.cancelAssistantSaveAs();
                }
                window.endNativeAsk(picker);
            }
            function openAt(target) {
                ApplicationInfo.openProjectSavePicker(window.assistantSaveIntent === "" ? DialogFolders.retarget("saveProject", target) : target);
            }
            title: saveAsChoice.copy ? qsTr("Save a copy of the project as a .zip") : qsTr("Save the project as a .zip")
            fileMode: FileDialog.SaveFile
            defaultSuffix: "zip"
            nameFilters: [qsTr("Zip archives (*.zip)")]
            acceptLabel: qsTr("Save")
            onAccepted: {
                if (window.nativeAsk === picker && ApplicationInfo.takeOwnedAnswer()) {
                    DialogFolders.remember("saveProject", selectedFile);
                    ApplicationInfo.acceptProjectSavePicker(true);
                }
                window.endNativeAsk(picker);
            }
        }
    }

    // A folder, a project.edi or a .zip dropped on the window opens it (edi ADR-0052); a CIF or magnetic CIF is loaded
    // as a structure into the open project.
    // Not while Help and feedback is open: a file dropped there is an attachment (FeedbackDialog.qml).
    DropArea {
        objectName: "window.projectDrop"
        anchors.fill: parent
        enabled: !feedbackDialog.visible
        onDropped: drop => ApplicationInfo.dropProject(drop)
    }

    // The browser's file access: an archive that could not be opened or a project not packed.
    Connections {
        target: WebFiles
        function onFailed(request, message) {
            ApplicationInfo.windowFailure(0, message);
        }
    }
    // The web app's saves (edi ADR-0052 §9): where the project went, and what a failed write says.
    Connections {
        target: Session
        // The first save of a project into the browser's storage warns in a dialog, later ones in the short notice
        // (owner, 2026-10-25).
        function onWebSaved(kind) {
            ApplicationInfo.windowWebSaved(kind);
        }
        function onWebStorageUnavailable() {
            ApplicationInfo.windowStorageUnavailable();
        }
        // Handed to the browser, which may still ask whether to allow it: never "downloaded". Replacing the original
        // is said only for a project opened from a file (owner, 2026-10-25).
        function onWebDownloaded(name, fromFile) {
            ApplicationInfo.windowWebDownloaded(name, fromFile);
        }
        function onWebSaveFailed(message) {
            ApplicationInfo.windowFailure(0, message);
        }
    }
    // Where a save into the browser's storage leaves the project: kept there, which the browser may clear, or, where it
    // keeps nothing, only in this tab. Save project as… is the way onto the disk.
    QtObject {
        id: browserSaved
        property var warnedFor: null
        property bool kept: true
        // The showing on screen, `{dialog, ownerGeneration, answered, gone}`, or null: its Save project as… acts only
        // from the current showing, once, for the project the warning is about.
        property var ask: null
        readonly property bool visible: ask !== null && ask.dialog.visible

        function open() {
            browserSaved.retire();
            const showing = {
                dialog: browserSavedQuestion.createObject(window.Overlay.overlay, {
                    parent: window.Overlay.overlay
                }),
                ownerGeneration: Session.projectGeneration(),
                answered: false,
                gone: false
            };
            showing.dialog.applied.connect(() => browserSaved.apply(showing));
            showing.dialog.closed.connect(() => browserSaved.forget(showing));
            browserSaved.ask = showing;
            showing.dialog.open();
        }
        function apply(showing) {
            if (showing !== browserSaved.ask || showing.answered)
                return;
            showing.answered = true;
            showing.dialog.close();
            if (showing.ownerGeneration === Session.projectGeneration())
                ApplicationInfo.windowBrowserWarningApplied();
        }
        function forget(showing) {
            if (browserSaved.ask === showing)
                browserSaved.ask = null;
            if (!showing.gone) {
                showing.gone = true;
                showing.dialog.destroy();
            }
        }
        function retire() {
            const showing = browserSaved.ask;
            if (showing === null)
                return;
            browserSaved.ask = null;
            showing.answered = true;
            window.retiredAsk = showing.dialog;
            AppState.retirePopup(showing.dialog);
            browserSaved.forget(showing);
        }
    }
    Component {
        id: browserSavedQuestion
        AppDialog {
            id: browserSavedDialog
            objectName: "webStorageWarning"
            enterAccepts: true
            title: browserSaved.kept ? qsTr("Saved in this browser only") : qsTr("Not saved")
            standardButtons: Dialog.Apply | Dialog.Ok
            contentWidth: AppSizes.messagesDialogContentWidth
            contentHeight: browserSavedRow.implicitHeight
            Component.onCompleted: ApplicationInfo.windowBrowserWarningReady()

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
                    width: browserSavedDialog.contentWidth - x
                    wrapMode: Text.Wrap
                    // The way out in bold (owner, 2026-10-25).
                    textFormat: Text.StyledText
                    text: browserSaved.kept ? qsTr("Saved in this browser only. The browser may clear what it keeps; use <b>Save project as…</b> to keep a copy on your disk.") : qsTr("This browser keeps nothing for the app here (a private window, for example), so the project is only in this tab. Use <b>Save project as…</b> to keep it on your disk.")
                }
            }
        }
    }

    // A saved report says so in the short notice below, with the files and their folder (the owner, 2026-11-10).
    Connections {
        target: Session.project ? Session.project.report : null
        function onSaved(location) {
            const files = location.split(", ");
            const names = files.map(file => file.substring(file.lastIndexOf("/") + 1)).join(", ");
            const folder = files[0].substring(0, files[0].lastIndexOf("/"));
            webNotice.show(WebFiles.available ? qsTr("Report saved: %1, handed to the browser to download.").arg(names) : qsTr("Report saved: %1, in %2").arg(names).arg(ApplicationInfo.shownLocalPath(folder)));
        }
    }
    // A short notice at the foot of the window, gone after a few seconds or on a click.
    Popup {
        id: webNotice
        objectName: "webNotice"
        property string text
        function show(message) {
            ApplicationInfo.windowNotice(message);
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
    ErrorDialog {
        id: webFilesError
        objectName: "webFiles.error"
        title: qsTr("The browser could not use the file")
    }

    // A created project that could not be saved at its location stays open, unsaved; this says why. Here, not on the
    // Project page, which the new project replaces.
    Connections {
        target: AppState
        function onCreateFailed() {
            createError.open();
        }
    }
    ErrorDialog {
        id: createError
        objectName: "create.error"
        title: qsTr("The project was not saved")
        message: Session.lastError
    }

    // A change a page could not make, in plain words; the Messages center keeps it too (the owner, 2026-11-19).
    Connections {
        target: Session
        function onRefused(message) {
            refusalError.message = message;
            refusalError.open();
        }
    }
    ErrorDialog {
        id: refusalError
        objectName: "change.error"
        title: qsTr("The change was not made")
    }

    ErrorDialog {
        id: saveError
        objectName: "save.error"
        title: qsTr("The project was not saved")
        message: Session.lastError
    }

    // A save asks first (edi ADR-0069): above 100 MB, or with the project set to ask, the user chooses whether a scan's
    // linked files go with it (the owner, 2026-11-04). The answer names the question it answers.
    // The save's question about its data. Each showing is its own dialog and answers the session's question it was
    // made for, once: a showing a handoff ended answers nothing, and the session drops a replaced project's question.
    QtObject {
        id: saveData
        // The showing on screen, `{dialog, request, answered, gone}`, or null.
        property var ask: null
        readonly property bool visible: ask !== null && ask.dialog.visible

        function open(request, bytes, files, large, linked) {
            saveData.retire();
            const showing = {
                dialog: saveDataQuestion.createObject(window.contentItem, {
                    parent: window.Overlay.overlay,
                    bytes: bytes,
                    files: files,
                    large: large,
                    linked: linked
                }),
                request: request,
                answered: false,
                gone: false
            };
            showing.dialog.showing = showing;
            showing.dialog.rejected.connect(() => saveData.answer(showing, "cancel"));
            showing.dialog.closed.connect(() => saveData.forget(showing));
            saveData.ask = showing;
            showing.dialog.open();
        }
        function answer(showing, choice) {
            if (showing !== saveData.ask || showing.answered)
                return;
            showing.answered = true;
            showing.dialog.close();
            Session.answerSaveData(showing.request, choice);
        }
        function forget(showing) {
            if (saveData.ask === showing)
                saveData.ask = null;
            if (!showing.gone) {
                showing.gone = true;
                showing.dialog.destroy();
            }
        }
        function retire() {
            const showing = saveData.ask;
            if (showing === null)
                return;
            saveData.ask = null;
            showing.answered = true;
            window.retiredAsk = showing.dialog;
            AppState.retirePopup(showing.dialog);
            saveData.forget(showing);
        }
    }
    Component {
        id: saveDataQuestion
        AppDialog {
            id: saveDataDialog
            objectName: "save.dataChoice"
            property var showing: null
            property real bytes: 0
            property int files: 0
            property bool large: false
            property bool linked: false
            title: saveDataDialog.linked ? qsTr("Linked data") : qsTr("Large save")
            contentWidth: AppSizes.messagesDialogContentWidth
            contentHeight: saveDataText.implicitHeight

            EaElements.Label {
                id: saveDataText
                width: saveDataDialog.contentWidth
                wrapMode: Text.Wrap
                text: !saveDataDialog.linked ? qsTr("This save writes %1 (%2 files).").arg(Qt.locale().formattedDataSize(saveDataDialog.bytes)).arg(saveDataDialog.files) : saveDataDialog.large ? qsTr("This save writes %1 (%2 files). Keep the data linked instead?").arg(Qt.locale().formattedDataSize(saveDataDialog.bytes)).arg(saveDataDialog.files) : qsTr("This save writes %1 (%2 files) with the linked data. Copy the data into the project?").arg(Qt.locale().formattedDataSize(saveDataDialog.bytes)).arg(saveDataDialog.files)
            }
            footer: EaElements.DialogButtonBox {
                EaElements.Button {
                    objectName: "save.dataChoice.linked"
                    visible: saveDataDialog.linked
                    text: qsTr("Keep linked")
                    DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
                    onClicked: saveData.answer(saveDataDialog.showing, "linked")
                }
                EaElements.Button {
                    objectName: "save.dataChoice.copy"
                    text: !saveDataDialog.linked ? qsTr("Save") : saveDataDialog.large ? qsTr("Copy anyway") : qsTr("Copy")
                    DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
                    onClicked: saveData.answer(saveDataDialog.showing, "copy")
                }
                EaElements.Button {
                    objectName: "save.dataChoice.cancel"
                    text: qsTr("Cancel")
                    DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                }
            }
        }
    }
    Connections {
        target: Session
        function onSaveDataChoiceNeeded(request, bytes, files, large, linked) {
            saveData.open(request, bytes, files, large, linked);
        }
    }

    // A fit's end: its results in diffraction-lib's table, or why it was refused.
    FitResultsDialog {
        id: fitResults
    }
    ErrorDialog {
        id: fitError
        objectName: "fit.error"
        title: qsTr("The fit did not run")
    }
    // A refused open (a project, an example) or a refused change of the project (a load of experiments, a structure
    // or data, …) always says why: never a silent no-op (the owner, 2026-10-11).
    ErrorDialog {
        id: refusal
        objectName: "refusal.dialog"
    }
    // An error nothing else caught, from the application's event loop: said, never a silent close.
    Connections {
        target: RunLog
        function onErrorCaught(message) {
            refusal.show(qsTr("Something went wrong"), message, "");
        }
    }
    Connections {
        target: Session
        function onProjectChanged() {
            window.assistantEmptyManualTakeover = false;
        }
        function onLoadFailed(message, file) {
            // The project member edi could not read goes with the problem when the user sends it.
            refusal.file = file || "";
            ApplicationInfo.windowFailure(1, message);
        }
    }
    Connections {
        target: Session.project
        function onRefused(message) {
            // A file edi could not read goes with the problem when the user sends it.
            refusal.file = Session.project.takeRefusedFile(message);
            ApplicationInfo.windowFailure(2, message);
        }
    }
    // The fit owner requests automatic presentation only for ordinary manual fits/scans.
    // Native assistant fits retain their result; the status bar can still open it explicitly.
    Connections {
        target: Session.project ? Session.project.fit : null
        function onAutomaticResultsRequested() {
            ApplicationInfo.windowAutomaticResults();
        }
        function onRefused(message) {
            ApplicationInfo.windowFailure(3, message);
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
        ApplicationInfo.storeWindowGeometry(window, windowSettings);
    }
    function restoreGeometry() {
        ApplicationInfo.restoreWindowGeometry(window, windowSettings);
    }
    onXChanged: storeGeometry()
    onYChanged: storeGeometry()
    onWidthChanged: storeGeometry()
    onHeightChanged: storeGeometry()

    // The window takes its kept geometry as it is created, after the base's own settings have loaded; edi's
    // preferences go to the base once everything, the base's hidden dialog and its settings included, is complete
    // (Preferences.apply).
    Component.onCompleted: {
        restoreSideBarSteps();
        setUpMergedTitleBar();
        ApplicationInfo.applyColorScheme(EaStyle.Colors.theme);
        ApplicationInfo.windowCompleted();
    }
}
