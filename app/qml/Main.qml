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

    // A workflow tab as wide when it is the current page's as when it is not: the base sets the current tab's name in
    // bold, so the tab bar changed width with every page switch, which moved the Experiment button the sidebar is
    // measured from, resized every page's main area and drew each shown chart a second time.
    component WorkflowTab: EaElements.AppBarTabButton {
        id: tab

        // The tab's page: while it is being built in the background the tab stays disabled and says so (edi ADR-0052).
        property Loader page: null
        property bool pageWanted: false
        readonly property bool preparing: page !== null && pageWanted && Session.hasProject && page.status !== Loader.Ready

        // The base binds the width to the name's width in its current weight; this is the wider of the two.
        width: implicitWidth
        implicitWidth: Math.ceil(Math.max(plainName.advanceWidth, boldName.advanceWidth) + font.pixelSize * 1.5)

        TextMetrics {
            id: plainName

            font.family: tab.font.family
            font.pixelSize: tab.font.pixelSize * 0.95
            text: tab.text
        }
        TextMetrics {
            id: boldName

            font.family: tab.font.family
            font.pixelSize: tab.font.pixelSize * 0.95
            font.bold: true
            text: tab.text
        }
    }

    appBarCentralTabs.contentData: [
        WorkflowTab {
            objectName: "appBar.tab.home"
            fontIcon: "home"
            text: qsTr("Home")
            ToolTip.text: qsTr("Home page")
        },
        WorkflowTab {
            id: projectTab
            objectName: "appBar.tab.project"
            page: projectLoader
            pageWanted: AppState.projectPageEnabled
            enabled: AppState.projectPageEnabled && !preparing
            fontIcon: "archive"
            text: qsTr("Project")
            ToolTip.text: qsTr("Project description page")
        },
        WorkflowTab {
            id: structureTab
            objectName: "appBar.tab.structure"
            page: structureLoader
            pageWanted: AppState.structurePageEnabled
            enabled: AppState.structurePageEnabled && !preparing
            fontIcon: "layer-group"
            text: qsTr("Structure")
            ToolTip.text: qsTr("Crystal structure page")
        },
        WorkflowTab {
            id: experimentTab
            objectName: "appBar.tab.experiment"
            page: experimentLoader
            pageWanted: AppState.experimentPageReached
            enabled: AppState.experimentPageEnabled && !preparing
            fontIcon: "microscope"
            text: qsTr("Experiment")
            ToolTip.text: qsTr("Experimental settings and measured data page")
        },
        WorkflowTab {
            id: analysisTab
            objectName: "appBar.tab.analysis"
            page: analysisLoader
            pageWanted: AppState.analysisPageReached
            enabled: AppState.analysisPageEnabled && !preparing
            fontIcon: "calculator"
            text: qsTr("Analysis")
            ToolTip.text: qsTr("Simulation and fitting page")
        },
        WorkflowTab {
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
        readonly property WorkflowTab preparingTab: {
            if (!tabBarHover.hovered)
                return null;
            for (const tab of [projectTab, structureTab, experimentTab, analysisTab, reportTab]) {
                const point = tab.mapFromItem(tabBarOverlay, tabBarHover.point.position.x, tabBarHover.point.position.y);
                if (tab.preparing && tab.contains(point))
                    return tab;
            }
            return null;
        }

        ToolTip {
            objectName: "appBar.preparingToolTip"
            parent: tabBarOverlay.preparingTab !== null ? tabBarOverlay.preparingTab : tabBarOverlay
            visible: tabBarOverlay.preparingTab !== null
            text: qsTr("Preparing this page…")
        }
    }

    contentArea: [
        HomePage {},
        Loader {
            id: projectLoader

            readonly property bool wanted: AppState.projectPageEnabled
            active: wanted && window.pageTurn(projectLoader)
            asynchronous: true
            sourceComponent: Component {
                ProjectPage {
                    current: projectLoader.SwipeView.isCurrentItem
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

    // Saving (edi ADR-0017 §13): the core writes (Session.save / saveAs -> edi::save_project_as); a refusal
    // shows the core's message.
    function saveProject() {
        if (Session.project === null)
            return;
        if (Session.needsSaveAs) {
            window.saveProjectAs();
            return;
        }
        if (!Session.save())
            saveError.open();
    }
    // In the browser (edi ADR-0052 §9) Save as writes onto the disk: where the browser can write it, into a folder or
    // a .zip the user picks, as on the desktop; elsewhere as a .zip download.
    function saveProjectAs() {
        if (Session.project === null)
            return;
        if (WebFiles.available && !WebStorage.diskAccess)
            Session.downloadWebProject();
        else
            saveAsChoice.open();
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
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: unsavedText.implicitHeight
        // Save writes in place; a project with nowhere to write yet opens Save as, and the action waits for the user to
        // ask again.
        onAccepted: {
            if (Session.needsSaveAs) {
                window.saveProjectAs();
            } else if (Session.save()) {
                action();
            } else {
                saveError.open();
            }
        }
        onDiscarded: {
            close();
            Session.discardKeptChanges();
            action();
        }

        EaElements.Label {
            id: unsavedText
            width: unsavedChanges.contentWidth
            wrapMode: Text.Wrap
            text: qsTr("%1 has changes that are not saved.").arg(Session.project !== null ? Session.project.name : "")
        }
    }

    // Save as (edi ADR-0052): first the format and whether to keep working where the project is (a copy), then the
    // system's dialog for the folder or the .zip.
    AppDialog {
        id: saveAsChoice
        objectName: "saveAs.choice"
        property bool zip: false
        property bool copy: false
        title: qsTr("Save project as")
        standardButtons: Dialog.Ok | Dialog.Cancel
        // As wide as its content (the owner, 2026-10-25).
        contentWidth: saveAsChoiceColumn.implicitWidth
        contentHeight: saveAsChoiceColumn.implicitHeight
        onAboutToShow: {
            zip = false;
            copy = false;
        }
        onAccepted: {
            if (WebFiles.available)
                Session.saveWebProjectAs(zip ? "zip" : "folder", copy);
            else if (zip)
                saveZip.open();
            else
                saveFolder.open();
        }

        Column {
            id: saveAsChoiceColumn

            EaElements.Label {
                text: qsTr("Format")
                bottomPadding: EaStyle.Sizes.fontPixelSize * 0.25
            }
            // Folder and Zip archive: one group, rows at the usual spacing.
            EaElements.RadioButton {
                objectName: "saveAs.folder"
                verticalPadding: 0
                text: qsTr("Folder")
                checked: !saveAsChoice.zip
                onClicked: saveAsChoice.zip = false
            }
            EaElements.RadioButton {
                objectName: "saveAs.zip"
                verticalPadding: 0
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
                text: qsTr("Save a copy")
                checked: saveAsChoice.copy
                onToggled: saveAsChoice.copy = checked
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Write the project there and keep working where it is")
            }
        }
    }

    FolderDialog {
        id: saveFolder
        title: saveAsChoice.copy ? qsTr("Save a copy of the project into a folder") : qsTr("Save the project into a folder")
        acceptLabel: qsTr("Choose")
        onAccepted: {
            if (!Session.saveProjectAs(selectedFolder, false, saveAsChoice.copy))
                saveError.open();
        }
    }

    FileDialog {
        id: saveZip
        title: saveAsChoice.copy ? qsTr("Save a copy of the project as a .zip") : qsTr("Save the project as a .zip")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "zip"
        nameFilters: [qsTr("Zip archives (*.zip)")]
        acceptLabel: qsTr("Save")
        onAccepted: {
            if (!Session.saveProjectAs(selectedFile, true, saveAsChoice.copy))
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
        function onWebSaved(kind) {
            if (kind === "browser")
                webNotice.show(qsTr("Saved in this browser only. Use Save project as… to keep a copy on your disk: the browser may clear what it keeps."));
        }
        function onWebDownloaded(name) {
            webNotice.show(qsTr("Downloaded %1 to the browser's downloads folder. To replace the original file, have the browser ask where to save downloads and choose that file.").arg(name));
        }
        function onWebSaveFailed(message) {
            webFilesError.message = message;
            webFilesError.open();
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
        function onFinished() {
            fitResults.open();
        }
        function onScanFinished() {
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
        GraphicsInfo.observe(window);
        restoreGeometry();
        Qt.callLater(() => {
            Preferences.apply();
            RecentProjects.refresh();
        });
    }
}
