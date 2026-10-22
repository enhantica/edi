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
            onClicked: AppState.reset()
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
            id: experimentTab
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
        HomePage {},
        Loader {
            id: projectLoader

            active: AppState.projectPageEnabled
            sourceComponent: Component {
                ProjectPage {
                    current: projectLoader.SwipeView.isCurrentItem
                }
            }
        },
        Loader {
            id: structureLoader

            active: AppState.structurePageEnabled
            sourceComponent: Component {
                StructurePage {
                    current: structureLoader.SwipeView.isCurrentItem
                }
            }
        },
        Loader {
            id: experimentLoader

            active: AppState.experimentPageReached
            sourceComponent: Component {
                ExperimentPage {
                    current: experimentLoader.SwipeView.isCurrentItem
                }
            }
        },
        Loader {
            id: analysisLoader

            active: AppState.analysisPageReached
            sourceComponent: Component {
                AnalysisPage {
                    current: analysisLoader.SwipeView.isCurrentItem
                }
            }
        },
        Loader {
            id: reportLoader

            active: AppState.reportPageReached
            sourceComponent: Component {
                ReportPage {
                    current: reportLoader.SwipeView.isCurrentItem
                }
            }
        }
    ]

    statusBar: StatusBar {}

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
        else if (WebFiles.available)
            WebFiles.downloadProject(Session.project.path);
    }
    // In the browser (edi ADR-0023) a project saves into the page's memory under its name and goes to the
    // user as a .zip download: no folder on the user's disk is reachable from the page.
    function saveProjectAs() {
        if (Session.project === null)
            return;
        if (!WebFiles.available) {
            saveFolder.open();
            return;
        }
        if (Session.saveAs(WebFiles.saveLocation(Session.project.name)))
            WebFiles.downloadProject(Session.project.path);
        else
            saveError.open();
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

    FolderDialog {
        id: saveFolder
        title: qsTr("Save the project into a directory")
        onAccepted: {
            if (!Session.saveAs(selectedFolder))
                saveError.open();
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
        restoreGeometry();
        Qt.callLater(() => {
            Preferences.apply();
            RecentProjects.refresh();
        });
    }
}
