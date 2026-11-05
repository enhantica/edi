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

    // Same Create API/preferences as the ordinary current-window form. Native
    // callers pass an original Session-bound intent, never another app/window.
    property var assistantCreateGuard: null
    function prepareNativeProjectCreate(intent) {
        return ApplicationInfo.prepareProjectCreation(intent);
    }
    function nativeProjectCreateSaveCurrent(intent, control) {
        return ApplicationInfo.projectCreationSaveCurrent(intent, control);
    }
    function chooseNativeProjectCreateSave(intent, control) {
        return ApplicationInfo.chooseProjectCreationSave(intent, control);
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
    readonly property int pagesWanted: ApplicationInfo.workflowPagesCount(false)
    readonly property int pagesBuilt: ApplicationInfo.workflowPagesCount(true)
    function pageTurn(loader) {
        return ApplicationInfo.workflowPageTurn(loader);
    }
    Connections {
        target: Session
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
        assistantChatShown: window.assistantPanelVisible && window.assistantPanelShown
        assistantManualTakeover: window.assistantManualTakeover
        objectName: "statusBar"
        pagesBuilt: window.pagesBuilt
        pagesWanted: window.pagesWanted
        tutorial: tutorialPanel
        onUpdateRequested: updateAvailableNotice.open()
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
    onClosing: close => ApplicationInfo.projectWindowClosing(close)
    Connections {
        target: AppState
        function onChangesQuestion(action, abandoned) {
            ApplicationInfo.projectChangesQuestion(action, abandoned);
        }
        // The same question about the user's own project while a tutorial holds it aside (edi ADR-0064).
        function onSetAsideChangesQuestion(action) {
            ApplicationInfo.projectChangesQuestion(action, null, true);
        }
    }
    AppDialog {
        id: unsavedChanges
        objectName: "unsavedChanges"
        property var action: null
        property var abandoned: null
        property var nativeCreation: null
        onOpened: ApplicationInfo.unsavedProjectOpened()
        function abandonAction() {
            ApplicationInfo.abandonUnsavedProjectAction();
        }
        onRejected: abandonAction()
        title: qsTr("Save the changes?")
        standardButtons: Dialog.Save | Dialog.Discard | Dialog.Cancel
        // Name the existing visible controls, as Save as names its real native OK button.
        Binding {
            target: unsavedChanges.opened ? unsavedChanges.header : null
            when: target !== null
            property: "objectName"
            value: "unsavedChanges.title"
        }
        Binding {
            target: unsavedChanges.opened ? unsavedChanges.standardButton(Dialog.Discard) : null
            when: target !== null
            property: "objectName"
            value: "unsavedChanges.discard"
        }
        Binding {
            target: unsavedChanges.opened ? unsavedChanges.standardButton(Dialog.Save) : null
            when: target !== null
            property: "objectName"
            value: "unsavedChanges.save"
        }
        Binding {
            target: unsavedChanges.opened ? unsavedChanges.standardButton(Dialog.Cancel) : null
            when: target !== null
            property: "objectName"
            value: "unsavedChanges.cancel"
        }
        // As wide as its line (owner, 2026-10-25).
        contentWidth: unsavedRow.implicitWidth
        contentHeight: unsavedRow.implicitHeight
        // Save writes in place; a project with nowhere to write yet opens Save as, and the action waits for the user to
        // ask again. In the web app the place is written after Save returns: the action waits until it is, and is
        // dropped if it is not (the window says why).
        property var afterSave: null
        // The question is about the user's own project, which a tutorial holds aside: Save and Discard first bring it
        // back and end the tutorial, on the next turn; Cancel leaves the tutorial running.
        property bool setAside: false
        property var afterSaveAbandoned: null
        onAccepted: ApplicationInfo.acceptUnsavedProject()

        Connections {
            target: Session
            function onWebSaveFinished(saved) {
                ApplicationInfo.projectWebSaveFinished(saved);
            }
        }
        onDiscarded: ApplicationInfo.discardUnsavedProject()

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
                text: ApplicationInfo.windowUnsavedText()
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
        readonly property Item nativeAcceptButton: opened ? standardButton(Dialog.Ok) : null
        onOpened: ApplicationInfo.windowSaveChoiceOpened()
        // A browser without the File System Access API writes no folder and moves no project onto the disk: a copy
        // as a .zip download is all it offers.
        readonly property bool diskWritable: !WebFiles.available || WebStorage.diskAccess
        title: qsTr("Save project as")
        standardButtons: Dialog.Ok | Dialog.Cancel
        // About half the usual dialog width, never narrower than its content (owner, 2026-10-25).
        contentWidth: Math.max(saveAsChoiceColumn.implicitWidth, Math.round(AppSizes.messagesDialogContentWidth / 2))
        contentHeight: saveAsChoiceColumn.implicitHeight
        onAboutToShow: ApplicationInfo.prepareProjectSaveChoice()
        onAccepted: ApplicationInfo.acceptProjectSaveChoice()

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
            ApplicationInfo.openProjectSavePicker(target);
        }
        title: saveAsChoice.copy ? qsTr("Save a copy of the project as a folder") : qsTr("Save the project as a folder")
        fileMode: FileDialog.SaveFile
        acceptLabel: qsTr("Save")
        onAccepted: ApplicationInfo.acceptProjectSavePicker(false)
    }

    FileDialog {
        id: saveZip
        onRejected: window.cancelAssistantSaveAs()
        function openAt(target) {
            ApplicationInfo.openProjectSavePicker(target);
        }
        title: saveAsChoice.copy ? qsTr("Save a copy of the project as a .zip") : qsTr("Save the project as a .zip")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "zip"
        nameFilters: [qsTr("Zip archives (*.zip)")]
        acceptLabel: qsTr("Save")
        onAccepted: ApplicationInfo.acceptProjectSavePicker(true)
    }

    // A folder, a project.edi or a .zip dropped on the window opens it (edi ADR-0052).
    DropArea {
        anchors.fill: parent
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
        Component.onCompleted: ApplicationInfo.windowBrowserWarningReady()
        onApplied: ApplicationInfo.windowBrowserWarningApplied()

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
        function onProjectChanged() {
            window.assistantEmptyManualTakeover = false;
        }
        function onLoadFailed(message) {
            ApplicationInfo.windowFailure(1, message);
        }
    }
    Connections {
        target: Session.project
        function onRefused(message) {
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
    Component.onCompleted: ApplicationInfo.windowCompleted()
}
