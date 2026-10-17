// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtCore

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The application window (easydiffractionbeta Components/ApplicationWindow.qml, ported): the app bar
// with its tool buttons and the six workflow tabs, the pages, and the status bar. Pages load when
// their tab is enabled, as in the original; a loaded page stays in the window's page view while another
// is shown, so each is told whether it is the shown one (WorkflowPage.current).
EaComponents.ApplicationWindow {
    id: window

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
            enabled: Session.project !== null && (Session.project.modified || Session.assistantSaveReady)
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
            onClicked: AppState.reset()
        }
    ]

    appBarRightButtons: [
        EaElements.ToolButton {
            id: assistantToggle
            KeyNavigation.tab: assistantPanel.visible && assistantPanel.shown ? assistantPanel.firstFocusItem : null
            objectName: "assistant.toggle"
            readonly property bool assistantSelected: assistantPanel.shown || (Session.assistant.showingActions && Preferences.assistantShown)
            fontIcon: assistantSelected ? "columns" : "robot"
            readonly property bool rotateRobot: visible && enabled && !assistantSelected
                && Session.assistant.state === "agent_active"
                && Object.keys(Session.assistant.pendingQuestion).length === 0
                && Object.keys(Session.assistant.pendingPlan).length === 0
                && EaStyle.Times.translationChange > 0
            onRotateRobotChanged: if (!rotateRobot && contentItem) contentItem.rotation = 0
            RotationAnimation {
                target: assistantToggle.contentItem
                property: "rotation"
                running: assistantToggle.rotateRobot
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
        EaElements.AppBarTabButton {
            objectName: "appBar.tab.home"
            fontIcon: "home"
            text: qsTr("Home")
            ToolTip.text: qsTr("Home page")
        },
        EaElements.AppBarTabButton {
            objectName: "appBar.tab.project"
            enabled: AppState.projectPageEnabled
            fontIcon: "archive"
            text: qsTr("Project")
            ToolTip.text: qsTr("Project description page")
        },
        EaElements.AppBarTabButton {
            objectName: "appBar.tab.structure"
            enabled: AppState.structurePageEnabled
            fontIcon: "layer-group"
            text: qsTr("Structure")
            ToolTip.text: qsTr("Crystal structure page")
        },
        EaElements.AppBarTabButton {
            objectName: "appBar.tab.experiment"
            enabled: AppState.experimentPageEnabled
            fontIcon: "microscope"
            text: qsTr("Experiment")
            ToolTip.text: qsTr("Experimental settings and measured data page")
        },
        EaElements.AppBarTabButton {
            objectName: "appBar.tab.analysis"
            enabled: AppState.analysisPageEnabled
            fontIcon: "calculator"
            text: qsTr("Analysis")
            ToolTip.text: qsTr("Simulation and fitting page")
        },
        EaElements.AppBarTabButton {
            objectName: "appBar.tab.report"
            enabled: AppState.reportPageEnabled
            fontIcon: "clipboard-list"
            text: qsTr("Report")
            ToolTip.text: qsTr("Report of the work done")
        }
    ]

    contentArea: [
        HomePage {
            id: homePage
            objectName: "workflow.home.mainContent"
        },
        Loader {
            id: projectLoader

            active: AppState.projectPageEnabled
            sourceComponent: Component {
                ProjectPage {
                    current: projectLoader.SwipeView.isCurrentItem
                    assistantCovered: assistantPanel.visible
                }
            }
        },
        Loader {
            id: structureLoader

            active: AppState.structurePageEnabled
            sourceComponent: Component {
                StructurePage {
                    current: structureLoader.SwipeView.isCurrentItem
                    assistantCovered: assistantPanel.visible
                }
            }
        },
        Loader {
            id: experimentLoader

            active: AppState.experimentPageReached
            sourceComponent: Component {
                ExperimentPage {
                    current: experimentLoader.SwipeView.isCurrentItem
                    assistantCovered: assistantPanel.visible
                }
            }
        },
        Loader {
            id: analysisLoader

            active: AppState.analysisPageReached
            sourceComponent: Component {
                AnalysisPage {
                    current: analysisLoader.SwipeView.isCurrentItem
                    assistantCovered: assistantPanel.visible
                }
            }
        },
        Loader {
            id: reportLoader

            active: AppState.reportPageReached
            sourceComponent: Component {
                ReportPage {
                    current: reportLoader.SwipeView.isCurrentItem
                    assistantCovered: assistantPanel.visible
                }
            }
        }
    ]

    statusBar: StatusBar {
        assistantChatShown: assistantPanel.shown
        assistantManualTakeover: window.assistantManualTakeover
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
        onChooseWorkingFolderRequested: {
            if (assistantWorkingFolder.visible) return;
            const token = Session.assistant.beginWorkingFolderSelection();
            if (!token.length) return;
            assistantWorkingFolder.intent = token;
            assistantWorkingFolder.open();
        }
    }
    Connections {
        target: Session.assistant
        function onWorkingFolderSelectionRetired(token) {
            if (assistantWorkingFolder.intent !== token) return;
            assistantWorkingFolder.intent = "";
            assistantWorkingFolder.reject();
        }
    }
    FolderDialog {
        id: assistantWorkingFolder
        property string intent: ""
        title: qsTr("Choose the assistant working folder")
        onRejected: { Session.assistant.cancelWorkingFolderSelection(intent); intent = ""; }
        onAccepted: {
            const token = intent; intent = "";
            Session.assistant.completeWorkingFolderSelection(token, selectedFolder);
        }
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

    // Saving (edi ADR-0017 §13): the core writes (Session.save / saveAs -> edi::save_project_as); a refusal
    // shows the core's message.
    function saveProject() {
        if (Session.project === null)
            return;
        if (Session.assistantSaveAs || Session.needsSaveAs) {
            window.saveProjectAs();
            return;
        }
        const originalOwner = Session.project;
        const nativeIntent = Session.assistantSaveReady;
        const accepted = Session.save();
        if (!Qt.isQtObject(window) || Session.project !== originalOwner) return;
        // The original native RPC owns asynchronous Save results; no generic modal can overwrite its refusal.
        if (!accepted && !nativeIntent) saveError.open();
        else if (accepted && WebFiles.available) WebFiles.downloadProject(originalOwner.path);
    }
    // In the browser (edi ADR-0023) a project saves into the page's memory under its name and goes to the
    // user as a .zip download: no folder on the user's disk is reachable from the page.
    function saveProjectAs() {
        const originalWindow = window;
        const originalOwner = Session.project;
        const picker = saveFolder;
        const form = freshProjectFolder;
        const sameOwner = function() {
            return Qt.isQtObject(originalWindow) && Qt.isQtObject(originalOwner) && Qt.isQtObject(picker) &&
                Qt.isQtObject(form) && Session.project === originalOwner;
        };
        const originalIntent = function(token) {
            if (!sameOwner() || picker.intent !== token) return false;
            const admitted = Session.saveAsCurrent(token);
            return sameOwner() && picker.intent === token && admitted;
        };
        if (!sameOwner()) return;
        if (!WebFiles.available) {
            if (saveFolder.visible || freshProjectFolder.visible) return;
            const intent = Session.beginSaveAs();
            if (!sameOwner()) return;
            if (!intent.length) { saveError.open(); return; }
            const admittedParent = Session.saveAsParent(intent);
            const valid = Session.saveAsCurrent(intent);
            if (!sameOwner() || !valid || saveFolder.intent.length || freshProjectFolder.intent.length) {
                Session.cancelSaveAs(intent);
                return;
            }
            if (admittedParent.toString().length) {
                if (!freshProjectFolder.openOriginalSave(intent, admittedParent)) Session.cancelSaveAs(intent);
                return;
            }
            saveFolder.intent = intent;
            if (!originalIntent(intent)) { Session.cancelSaveAs(intent); return; }
            saveFolder.fresh = Session.needsFreshSaveAs;
            if (!originalIntent(intent)) { Session.cancelSaveAs(intent); return; }
            saveFolder.open();
            return;
        }
        const saved = Session.saveAs(WebFiles.saveLocation(originalOwner.name));
        if (!sameOwner()) return;
        if (saved) WebFiles.downloadProject(originalOwner.path);
        else saveError.open();
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

    FolderDialog {
        id: saveFolder
        property string intent: ""
        property bool fresh: false
        title: fresh ? qsTr("Choose a parent directory for a new project folder") : qsTr("Save the project into a directory")
        onRejected: { const token = intent; intent = ""; Session.cancelSaveAs(token); }
        Component.onDestruction: { const token = intent; intent = ""; Session.cancelSaveAs(token); }
        onAccepted: {
            const picker = saveFolder;
            const originalOwner = Session.project;
            const token = intent;
            const parent = selectedFolder;
            const needsFresh = fresh;
            const nativeIntent = Session.assistantSaveReady;
            intent = "";
            if (!Qt.isQtObject(picker) || !Qt.isQtObject(originalOwner) || Session.project !== originalOwner || picker.intent.length) {
                Session.cancelSaveAs(token); return;
            }
            const valid = Session.saveAsCurrent(token);
            if (!Qt.isQtObject(picker) || !Qt.isQtObject(originalOwner) || Session.project !== originalOwner ||
                picker.intent.length || !valid) { Session.cancelSaveAs(token); return; }
            if (needsFresh) {
                if (!freshProjectFolder.openOriginalSave(token, parent)) Session.cancelSaveAs(token);
            } else {
                const saved = Session.completeSaveAs(token, parent, "");
                if (!Qt.isQtObject(picker) || !Qt.isQtObject(originalOwner) || Session.project !== originalOwner || picker.intent.length) return;
                if (!saved && !nativeIntent) saveError.open();
            }
        }
    }

    AppDialog {
        id: freshProjectFolder
        objectName: "assistant.resultSaveAs"
        parent: Overlay.overlay
        property string intent: ""
        property string presentedIntent: ""
        function openOriginalSave(token, parentFolder) {
            const form = freshProjectFolder;
            const originalOwner = Session.project;
            const current = function() {
                if (!Qt.isQtObject(form) || !Qt.isQtObject(originalOwner) || Session.project !== originalOwner ||
                    form.presentedIntent !== token || form.intent !== token) return false;
                const valid = Session.saveAsCurrent(token);
                return Qt.isQtObject(form) && Qt.isQtObject(originalOwner) && valid && Session.project === originalOwner &&
                    form.presentedIntent === token && form.intent === token;
            };
            const admitted = Session.saveAsCurrent(token);
            if (!Qt.isQtObject(form) || !Qt.isQtObject(originalOwner) || !admitted ||
                Session.project !== originalOwner || form.visible || (form.intent.length && form.intent !== token)) return false;
            presentedIntent = token;
            if (!Qt.isQtObject(form) || !Qt.isQtObject(originalOwner) || form.presentedIntent !== token ||
                Session.project !== originalOwner || (form.intent.length && form.intent !== token)) return false;
            const stillAdmitted = Session.saveAsCurrent(token);
            if (!Qt.isQtObject(form) || !stillAdmitted || form.presentedIntent !== token || Session.project !== originalOwner) return false;
            intent = token;
            if (!current()) { if (Qt.isQtObject(form)) form.retireAssistantSave(token, false); return false; }
            destinationParent = parentFolder;
            if (!current()) { if (Qt.isQtObject(form)) form.retireAssistantSave(token, false); return false; }
            const suggestion = originalOwner.name;
            if (!current()) { if (Qt.isQtObject(form)) form.retireAssistantSave(token, false); return false; }
            freshFolderName.assistantEditing = false;
            if (!current()) { if (Qt.isQtObject(form)) form.retireAssistantSave(token, false); return false; }
            freshFolderName.assistantStage = "";
            if (!current()) { if (Qt.isQtObject(form)) form.retireAssistantSave(token, false); return false; }
            freshFolderName.initialText = suggestion;
            if (!current()) { if (Qt.isQtObject(form)) form.retireAssistantSave(token, false); return false; }
            freshFolderName.text = suggestion;
            if (!current()) { if (Qt.isQtObject(form)) form.retireAssistantSave(token, false); return false; }
            open();
            return current();
        }
        property url destinationParent
        function retireAssistantSave(token, preserveDraft) {
            if (intent !== token) return;
            const form = freshProjectFolder;
            const originalPresentation = presentedIntent;
            intent = "";
            if (!Qt.isQtObject(form) || form.presentedIntent !== originalPresentation || form.intent.length) return;
            // Manual takeover keeps the same visible target and text until its original event returns.
            if (preserveDraft) {
                freshFolderName.assistantEditing = false;
                if (!Qt.isQtObject(form) || form.presentedIntent !== originalPresentation || form.intent.length) return;
                freshFolderName.assistantStage = "";
            } else form.close();
        }
        title: qsTr("Save in a fresh project folder")
        standardButtons: Dialog.NoButton
        function completeOriginalSave() {
            const form = freshProjectFolder;
            const originalOwner = Session.project;
            const presentation = presentedIntent;
            const token = intent;
            const parent = destinationParent;
            const leaf = freshFolderName.text;
            const nativeIntent = Session.assistantSaveReady;
            if (!token.length) return;
            const samePresentation = function() {
                return Qt.isQtObject(form) && Qt.isQtObject(originalOwner) && Session.project === originalOwner &&
                    form.presentedIntent === presentation && !form.intent.length;
            };
            intent = "";
            if (!samePresentation()) { Session.cancelSaveAs(token); return; }
            const valid = Session.saveAsCurrent(token);
            if (!samePresentation() || !valid) { Session.cancelSaveAs(token); return; }
            const saved = Session.completeSaveAs(token, parent, leaf);
            if (!samePresentation()) return;
            form.close();
            if (!samePresentation()) return;
            // The original assistant RPC owns its asynchronous result and refusal.
            if (!saved && !nativeIntent) saveError.open();
        }
        footer: DialogButtonBox {
            EaElements.Button {
                objectName: "assistant.resultFolderSave"
                text: qsTr("Save")
                enabled: freshProjectFolder.intent.length > 0
                DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
                onClicked: freshProjectFolder.completeOriginalSave()
            }
            EaElements.Button {
                text: qsTr("Cancel")
                DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
                onClicked: freshProjectFolder.reject()
            }
        }
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: freshFolderContent.implicitHeight
        onOpened: {
            const token = intent;
            const form = freshProjectFolder;
            if (!Qt.isQtObject(form) || !form.visible || !token.length || form.presentedIntent !== token) return;
            const valid = Session.saveAsCurrent(token);
            if (Qt.isQtObject(form) && form.visible && form.intent === token && form.presentedIntent === token && valid)
                freshFolderName.forceActiveFocus();
        }
        onAboutToHide: {
            const token = intent;
            intent = "";
            Session.cancelSaveAs(token);
        }
        onRejected: { const token = intent; intent = ""; Session.cancelSaveAs(token); }
        Component.onDestruction: { const token = intent; intent = ""; Session.cancelSaveAs(token); }
        // Only the explicit Save control consumes the one-shot intent; any other close revokes it.
        Column {
            id: freshFolderContent
            width: freshProjectFolder.contentWidth
            spacing: AppSizes.unit
            EaElements.Label {
                width: parent.width
                wrapMode: Text.Wrap
                textFormat: Text.PlainText
                text: freshProjectFolder.intent.length
                    ? qsTr("Existing folders are preserved. Choose a new project folder name.")
                    : qsTr("This Save As request stopped. Your draft is retained; close and reopen Save As before saving.")
            }
            EaElements.TextField {
                id: freshFolderName
                objectName: "assistant.resultFolderName"
                width: parent.width
                placeholderText: qsTr("New project folder")
                selectByMouse: true
                property bool assistantEditing: false
                property string assistantOriginalText: ""
                property string assistantStage: ""
                property string initialText: ""
                readonly property string editText: text
                readonly property bool assistantManualDraft: inputMethodComposing ||
                    (!assistantEditing && assistantStage !== freshProjectFolder.intent && text !== initialText) ||
                    (!assistantEditing && !assistantStage.length && text !== initialText)
                function beginAssistantEdit() {
                    const field = freshFolderName;
                    const form = freshProjectFolder;
                    const token = form.intent;
                    if (assistantEditing || assistantManualDraft || !token.length || !Session.assistantSaveReady) return false;
                    const current = function() { return Qt.isQtObject(field) && Qt.isQtObject(form) && form.intent === token; };
                    assistantOriginalText = text;
                    if (!current()) return false;
                    assistantStage = token;
                    if (!current()) return false;
                    assistantEditing = true;
                    return current() && field.assistantStage === token;
                }
                function allowAssistantCommit() {
                    const field = freshFolderName;
                    const form = freshProjectFolder;
                    const token = assistantStage;
                    if (!token.length || token !== form.intent) return false;
                    assistantEditing = false;
                    return Qt.isQtObject(field) && Qt.isQtObject(form) && field.assistantStage === token && form.intent === token;
                }
                function cancelAssistantEdit() {
                    if (!assistantEditing) return;
                    const field = freshFolderName;
                    const form = freshProjectFolder;
                    const token = assistantStage;
                    const original = assistantOriginalText;
                    assistantEditing = false;
                    if (!Qt.isQtObject(field) || !Qt.isQtObject(form) || form.intent !== token || field.assistantStage !== token) return;
                    assistantStage = "";
                    if (!Qt.isQtObject(field) || !Qt.isQtObject(form) || form.intent !== token || field.assistantStage.length) return;
                    text = original;
                }
                Accessible.name: qsTr("New project folder name")
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
            width: webFilesError.contentWidth
            wrapMode: Text.Wrap
            text: webFilesError.message
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
    Connections {
        target: Session.project ? Session.project.fit : null
        function onAutomaticResultsRequested() {
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
        window.rehostAssistant();
        restoreGeometry();
        Qt.callLater(() => {
            Preferences.apply();
            RecentProjects.refresh();
        });
    }
}
