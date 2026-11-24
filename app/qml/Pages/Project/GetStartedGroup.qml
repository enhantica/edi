// SPDX-License-Identifier: BSD-3-Clause
import QtQml
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtCore

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents
import EasyApplication.Gui.Logic as EaLogic

import edi.app

// Get started (easydiffractionbeta Pages/Project/SideBarBasic/GetStarted.qml): create a new project, open one from its
// project.edi or a .zip or import one from another program, or save the open one as a folder or a .zip, or a copy of
// it (edi ADR-0017 §13, ADR-0052).
SideBarGroup {
    id: group
    // The tab's last shown group draws no bottom border (edi ADR-0017 section 3).
    last: SideBarGroups.isLast(group)
    objectName: "group.getStarted"
    title: qsTr("Get started")
    icon: "rocket"
    // The one group that starts open: the first thing a new user needs (the owner, 2026-09-29; edi ADR-0017 §3).
    collapsed: false

    // Create, Load ▾ and Save as side by side at equal widths, as on the Structure and Experiment pages (the owner,
    // 2026-11-21). The Load menu opens an EasyDiffraction project or imports one from another program; an import
    // becomes a new, unsaved project.
    Row {
        id: buttons

        readonly property real buttonWidth: (EaStyle.Sizes.sideBarContentWidth - 2 * spacing) / 3

        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            objectName: "project.create"
            width: buttons.buttonWidth
            fontIcon: "plus-circle"
            text: qsTr("Create a new project")
            ToolTip.text: qsTr("Start a new, empty project")
            onClicked: ApplicationInfo.createProjectClicked()
        }

        EaElements.SideBarButton {
            id: loadButton
            objectName: "project.load"
            width: buttons.buttonWidth
            fontIcon: "upload"
            text: qsTr("Load project")

            // The menu's caret, from the icon font: the text fonts have no such character.
            EaElements.Label {
                anchors.right: parent.right
                anchors.rightMargin: EaStyle.Sizes.fontPixelSize * 0.75
                anchors.verticalCenter: parent.verticalCenter
                font.family: EaStyle.Fonts.iconsFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.9
                color: loadButton.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundDisabled
                text: "caret-down"
            }
            ToolTip.text: qsTr("Open an EasyDiffraction project or import one from another program")
            onClicked: loadMenu.open()

            EaElements.Menu {
                id: loadMenu
                objectName: "project.load.menu"
                y: loadButton.height
                // Clear of the window's edges when the window is too narrow for it beside its button.
                margins: EaStyle.Sizes.fontPixelSize * 0.5
                // Nothing below the last item (the owner, 2026-11-04).
                bottomPadding: 0
                // As wide as its widest entry, never narrower than its button.
                contentWidth: Math.max(loadButton.width - leftPadding - rightPadding, loadProjectHeader.implicitWidth, importHeader.implicitWidth, loadFolderItem.implicitWidth, loadZipItem.implicitWidth, loadUrlItem.implicitWidth, importItemsWidth)

                // The entry keyboard navigation has reached, as a list's current item.
                readonly property Item currentItem: currentIndex >= 0 ? itemAt(currentIndex) : null
                readonly property real labelWidth: Math.max(loadFolderItem.labelImplicitWidth, loadZipItem.labelImplicitWidth, loadUrlItem.labelImplicitWidth, importLabelsWidth)
                // The widest import entry and label: the entries come from the importer list below.
                property real importItemsWidth: 0
                property real importLabelsWidth: 0

                LoadMenuHeader {
                    id: loadProjectHeader
                    first: true
                    text: qsTr("EasyDiffraction project")
                }
                // The browser's own chooser copies a folder into its storage; Chrome and Edge open it on the disk.
                LoadMenuItem {
                    id: loadFolderItem
                    objectName: "project.load.folder"
                    labelWidth: loadMenu.labelWidth
                    hintRight: true
                    rightPadding: leftPadding
                    fontIcon: "folder-open"
                    text: qsTr("Open project folder…")
                    hint: qsTr("with project.edi")
                    toolTip: qsTr("Open an EasyDiffraction project from its folder")
                    onTriggered: group.openProject(false)
                }
                LoadMenuItem {
                    id: loadZipItem
                    objectName: "project.load.zip"
                    labelWidth: loadMenu.labelWidth
                    hintRight: true
                    rightPadding: leftPadding
                    fontIcon: "archive"
                    text: qsTr("Open project zip…")
                    hint: ".zip"
                    toolTip: qsTr("Open an EasyDiffraction project from a .zip of its folder")
                    onTriggered: group.openProject(true)
                }
                // Not implemented yet: shown, disabled (edi ADR-0017 §4).
                LoadMenuItem {
                    id: loadUrlItem
                    objectName: "project.load.url"
                    labelWidth: loadMenu.labelWidth
                    hintRight: true
                    rightPadding: leftPadding
                    enabled: false
                    fontIcon: "link"
                    text: qsTr("Open project from URL…")
                    toolTip: qsTr("Open an EasyDiffraction project from a web address")
                }
                LoadMenuHeader {
                    id: importHeader
                    text: qsTr("Import from another program")
                }
                // One entry per importer the core knows (edi ADR-0098), in its order: a program added there appears
                // here with no change to this page.
                Component {
                    id: importItem
                    LoadMenuItem {
                        property var importer: null
                        objectName: importer !== null ? "project.import." + importer.key : ""
                        hintRight: true
                        rightPadding: leftPadding
                        // The importers read files from the disk; the browser has none to give them yet.
                        enabled: !WebFiles.available
                        fontIcon: "file-import"
                        text: importer !== null ? qsTr("Import %1…").arg(importer.program) : ""
                        hint: importer !== null ? importer.hint : ""
                    }
                }
                // Created once the menu holds its own entries, in the list's order, right after the import header.
                Component.onCompleted: {
                    const importers = Session.projectImporters();
                    const at = group.menuIndexAfter(loadMenu, importHeader);
                    for (let i = 0; i < importers.length; ++i) {
                        const importer = importers[i];
                        const item = importItem.createObject(loadMenu.contentItem, {
                            importer: importer
                        }) as LoadMenuItem;
                        item.labelWidth = Qt.binding(() => loadMenu.labelWidth);
                        item.toolTip = group.importToolTip(importer);
                        item.triggered.connect(() => group.importProject(importer));
                        loadMenu.insertItem(at + i, item);
                        loadMenu.importItemsWidth = Math.max(loadMenu.importItemsWidth, item.implicitWidth);
                        loadMenu.importLabelsWidth = Math.max(loadMenu.importLabelsWidth, item.labelImplicitWidth);
                    }
                }
                onCurrentIndexChanged: group.skipHeader(loadMenu)
            }
        }

        EaElements.SideBarButton {
            id: saveButton
            objectName: "project.saveAs"
            width: buttons.buttonWidth
            enabled: Session.project !== null
            fontIcon: "file-export"
            text: qsTr("Save project as")

            EaElements.Label {
                anchors.right: parent.right
                anchors.rightMargin: EaStyle.Sizes.fontPixelSize * 0.75
                anchors.verticalCenter: parent.verticalCenter
                font.family: EaStyle.Fonts.iconsFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.9
                color: saveButton.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundDisabled
                text: "caret-down"
            }
            ToolTip.text: qsTr("Save the project as an EasyDiffraction folder or .zip, or export a copy for another program")
            onClicked: saveMenu.open()

            EaElements.Menu {
                id: saveMenu
                objectName: "project.saveAs.menu"
                y: saveButton.height
                margins: EaStyle.Sizes.fontPixelSize * 0.5
                bottomPadding: 0
                // As wide as its widest entry, never narrower than its button.
                contentWidth: Math.max(saveButton.width - leftPadding - rightPadding, saveProjectHeader.implicitWidth, exportHeader.implicitWidth, saveasFolderItem.implicitWidth, saveasZipItem.implicitWidth, exportCryspyItem.implicitWidth, exportFullprofItem.implicitWidth, exportGsasItem.implicitWidth, saveCopyBox.implicitWidth)

                readonly property Item currentItem: currentIndex >= 0 ? itemAt(currentIndex) : null
                readonly property real labelWidth: Math.max(saveasFolderItem.labelImplicitWidth, saveasZipItem.labelImplicitWidth, exportCryspyItem.labelImplicitWidth, exportFullprofItem.labelImplicitWidth, exportGsasItem.labelImplicitWidth)
                // A browser without the File System Access API writes no folder on the disk: a .zip copy only.
                readonly property bool diskWritable: !WebFiles.available || WebStorage.diskAccess
                property bool copy: false
                onAboutToShow: copy = !diskWritable
                onCurrentIndexChanged: group.skipHeader(saveMenu)

                LoadMenuHeader {
                    id: saveProjectHeader
                    first: true
                    text: qsTr("EasyDiffraction project")
                }
                LoadMenuItem {
                    id: saveasFolderItem
                    objectName: "project.saveAs.folder"
                    labelWidth: saveMenu.labelWidth
                    hintRight: true
                    rightPadding: leftPadding
                    enabled: saveMenu.diskWritable
                    fontIcon: "folder-open"
                    text: qsTr("As project folder…")
                    hint: qsTr("with project.edi")
                    toolTip: saveMenu.diskWritable ? qsTr("Save the project as a folder holding project.edi") : qsTr("This browser cannot write a folder on your disk; Chrome and Edge can")
                    onTriggered: AppState.saveAsFormatRequested(false, saveMenu.copy)
                }
                LoadMenuItem {
                    id: saveasZipItem
                    objectName: "project.saveAs.zip"
                    labelWidth: saveMenu.labelWidth
                    hintRight: true
                    rightPadding: leftPadding
                    fontIcon: "archive"
                    text: qsTr("As project zip…")
                    hint: ".zip"
                    toolTip: qsTr("Save the project as a .zip of its folder")
                    onTriggered: AppState.saveAsFormatRequested(true, saveMenu.copy)
                }
                // Applies to the two EasyDiffraction choices above; the exports below always write a copy.
                EaElements.CheckBox {
                    id: saveCopyBox
                    objectName: "project.saveAs.copy"
                    // The box in the entries' icon column, and the entries' own row spacing above and below it.
                    leftPadding: saveasZipItem.leftPadding + (EaStyle.Sizes.fontPixelSize * 1.25 - indicator.width) / 2
                    topPadding: saveasZipItem.topPadding
                    bottomPadding: saveasZipItem.bottomPadding
                    enabled: saveMenu.diskWritable
                    text: qsTr("Save a copy")
                    checked: saveMenu.copy
                    onToggled: saveMenu.copy = checked
                    ToolTip.text: qsTr("Write the project there and keep working where it is")
                }
                LoadMenuHeader {
                    id: exportHeader
                    text: qsTr("Export to another program (always a copy)")
                }
                LoadMenuItem {
                    id: exportCryspyItem
                    objectName: "project.export.cryspy"
                    labelWidth: saveMenu.labelWidth
                    hintRight: true
                    rightPadding: leftPadding
                    enabled: !WebFiles.available
                    fontIcon: "file-export"
                    text: qsTr("As cryspy…")
                    hint: ".rcif"
                    toolTip: qsTr("Export a copy of the project as a cryspy .rcif file; the app keeps working on this project")
                    onTriggered: group.exportCopy("cryspy")
                }
                LoadMenuItem {
                    id: exportFullprofItem
                    objectName: "project.export.fullProf"
                    labelWidth: saveMenu.labelWidth
                    hintRight: true
                    rightPadding: leftPadding
                    enabled: !WebFiles.available
                    fontIcon: "file-export"
                    text: qsTr("As FullProf…")
                    hint: ".pcr"
                    toolTip: qsTr("Export a copy of the project as a FullProf .pcr with its data files; the app keeps working on this project")
                    onTriggered: group.exportCopy("FullProf")
                }
                LoadMenuItem {
                    id: exportGsasItem
                    objectName: "project.export.gsas"
                    labelWidth: saveMenu.labelWidth
                    hintRight: true
                    rightPadding: leftPadding
                    enabled: false
                    fontIcon: "file-export"
                    text: qsTr("As GSAS-II…")
                    hint: ".gpx"
                    toolTip: qsTr("Export a copy of the project for GSAS-II")
                }
            }
        }
    }

    property var createLife: ({
            alive: true
        })
    property var createIntent: null
    property var createOperation: null
    property var assistantCreate: null
    Component.onDestruction: createLife.alive = false
    function prepareAssistantCreate(id) {
        return ApplicationInfo.assistantBuilt ? ApplicationInfo.prepareAssistantCreate(id) : null;
    }
    function assistantCreateDialog(id) {
        return ApplicationInfo.assistantBuilt ? ApplicationInfo.assistantCreateDialog(id) : null;
    }
    function retireAssistantCreate(id, manual) {
        if (ApplicationInfo.assistantBuilt)
            ApplicationInfo.retireAssistantCreate(id, manual);
    }
    // Native Create reuses this actual form's remembered parent/defaults. It does
    // not accept a dialog or synthesize a chooser selection.
    function nativeProjectNameError(name) {
        return ApplicationInfo.createProjectNameError(name);
    }
    function nativeCreateDefaults(name, description, title) {
        return ApplicationInfo.createProjectDefaults(name, description, title);
    }
    function chooseCreate() {
        ApplicationInfo.chooseCreateProject();
    }

    // Open project (edi ADR-0052 §3, §9) and Import (edi ADR-0098): the window deals with unsaved changes, then shows
    // the chooser (Main.qml).
    function openProject(zip) {
        AppState.openProjectRequested(zip);
    }
    function importProject(importer) {
        AppState.importProjectRequested(importer);
    }

    function importToolTip(importer) {
        switch (importer.key) {
        case "fullProf":
            return qsTr("Import a FullProf project from its .pcr file and the data files beside it");
        case "gsas":
            return qsTr("Import a GSAS-II project from its .gpx file or a GSAS-II text bundle");
        default:
            return qsTr("Import a %1 project").arg(importer.program);
        }
    }
    // A group title is never a choice: when keyboard navigation (or a menu opened from the keyboard) lands on one, the
    // next enabled entry in the same direction is chosen instead.
    property int lastMenuIndex: -1
    function skipHeader(menu) {
        const index = menu.currentIndex;
        const item = index >= 0 ? menu.itemAt(index) : null;
        if (item === null || item.activeFocusOnTab) {
            group.lastMenuIndex = index;
            return;
        }
        const step = index < group.lastMenuIndex ? -1 : 1;
        for (let i = index + step; i >= 0 && i < menu.count; i += step) {
            const next = menu.itemAt(i);
            if (next !== null && next.activeFocusOnTab && next.enabled) {
                menu.currentIndex = i;
                return;
            }
        }
        menu.currentIndex = group.lastMenuIndex;
    }
    // The menu position just after `header`, where the entries generated for it go.
    function menuIndexAfter(menu, header) {
        for (let i = 0; i < menu.count; ++i) {
            if (menu.itemAt(i) === header)
                return i + 1;
        }
        return menu.count;
    }
    // An export writes a new folder beside the chosen one's other projects and leaves this project open.
    function exportCopy(program) {
        exportFolder.program = program;
        exportFolder.sourceProject = Session.project;
        exportFolder.open();
    }

    // Save on the untitled project opens Create project here: it names the project and saves it, its work kept.
    // What opens the Create dialog on untitled work: the Project page's Create, or a Save (ADR-0100).
    property string untitledOrigin: "manual-create"
    // The untitled operation the next opening answers (a guard Save's), 0 for one of its own.
    property real untitledRequest: 0
    Connections {
        target: AppState
        function onUntitledSaveRequested(id) {
            group.untitledOrigin = "save";
            group.untitledRequest = id > 0 ? id : 0;
            group.chooseCreate();
        }
    }

    EaComponents.ProjectDescriptionDialog {
        id: createDialog
        objectName: "createProject.dialog"
        // During a tutorial a press outside, such as the status bar's Next, keeps the dialog open: the next step is its
        // OK. Escape still closes it.
        closePolicy: AppState.tutorialRunning ? Popup.CloseOnEscape : Popup.CloseOnEscape | Popup.CloseOnPressOutside
        readonly property string assistantIntentId: group.createIntent !== null && group.createIntent.assistant !== null ? group.createIntent.assistant.id : ""
        // The base's dialog (edi's copy joins the location cleanly), placed on whole pixels as AppDialog is.
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        visible: EaGlobals.Vars.showProjectDescriptionDialog
        // A tutorial's project, made by the user in a tutorial that set theirs aside, is not saved until they keep
        // it (edi ADR-0064).
        showsLocation: !AppState.tutorialRunning || !Session.hasProjectSetAside || Session.project !== null
        // The untitled operation this dialog answers (ADR-0100): the request that opened it, while that one still
        // asks (a guard Save's), else a new one for what opened the dialog. Never another request's, and only an
        // answer for this id counts.
        property var untitledId: 0
        property bool untitledAccepted: false
        // On an untitled project the form starts from what the Project page already holds for it.
        onAboutToShow: {
            untitledAccepted = false;
            untitledId = 0;
            const request = group.untitledRequest;
            group.untitledRequest = 0;
            if (Session.untitled && Session.project !== null && assistantIntentId === "")
                untitledId = request > 0 && Session.askingUntitledId() === request ? request : Session.beginUntitled(group.untitledOrigin);
            group.untitledOrigin = "manual-create";
            if (Session.untitled && Session.project !== null) {
                projectTitle = Session.project.title;
                projectAuthors = Session.project.authors;
                projectDescription = Session.project.description;
            }
        }
        onOpened: ApplicationInfo.createProjectDialogEvent(0)
        onRejected: ApplicationInfo.createProjectDialogEvent(1)
        onClosed: {
            // Closed without its OK (Cancel, Escape or a press outside): its own request is rejected.
            if (untitledId > 0 && !untitledAccepted)
                Session.rejectUntitled(untitledId);
            ApplicationInfo.createProjectDialogEvent(2);
        }
        // A new project's folder is beside the last project opened, else under the user's documents, unless one was
        // chosen before; it is saved there at once (the owner, 2026-10-08 and 2026-11-02). The browser has no folder to
        // save into: Save As downloads it.
        readonly property string lastOpenFolder: Session.existingParentFolder(RecentProjects.last)
        defaultProjectParentDirectory: lastOpenFolder !== "" ? lastOpenFolder : EaLogic.Utils.urlToLocalFile(String(StandardPaths.writableLocation(StandardPaths.DocumentsLocation)))
        // On the next turn: the new project replaces this page, dialog and all (AppState.afterChanges). The flag is
        // reset here, not only when the dialog has closed: this page goes before its closing ends, and the new page's
        // dialog would open again on a flag still set.
        onAccepted: {
            untitledAccepted = true;
            ApplicationInfo.createProjectDialogEvent(3);
        }
        onReplaceAsked: (name, folder) => {
            replaceProject.projectName = name;
            replaceProject.folder = folder;
            // What it asks about: this location, for this dialog's request.
            replaceProject.location = chosenLocation();
            replaceProject.untitledId = untitledId;
            replaceProject.open();
        }
    }

    // A project already at the chosen location (the owner, 2026-11-04): Replace writes the new one over it through
    // the ordinary save, so a refused write leaves the old project; Cancel returns to the form as typed.
    AppDialog {
        id: replaceProject
        objectName: "createProject.replace"
        property string projectName: ""
        property string folder: ""
        property string location: ""
        property var untitledId: 0
        parent: Overlay.overlay
        title: qsTr("Replace project?")
        standardButtons: Dialog.Yes | Dialog.Cancel
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: replaceText.implicitHeight
        onAboutToShow: {
            const yes = standardButton(Dialog.Yes);
            yes.text = qsTr("Replace");
            yes.objectName = "createProject.replace.accept";
        }
        onAccepted: {
            // Replace confirms the folder it showed, for the request it asked for: once the form names another
            // location or answers another request, the form stays open as it is.
            if (createDialog.chosenLocation() !== location || createDialog.untitledId !== untitledId)
                return;
            // Untitled work replaces only the folder that is there now, as its operation records it (ADR-0100).
            if (untitledId > 0)
                Session.approveUntitledReplace(untitledId, location);
            createDialog.replaceExisting = true;
            createDialog.accept();
        }

        EaElements.Label {
            id: replaceText
            width: replaceProject.contentWidth
            wrapMode: Text.Wrap
            text: qsTr("A project named %1 already exists in %2. Replace it?").arg(replaceProject.projectName).arg(replaceProject.folder)
        }
    }

    FolderDialog {
        id: exportFolder
        property string program: ""
        property var sourceProject
        title: qsTr("Choose where to create the %1 project folder").arg(program)
        currentFolder: DialogFolders.folder("exportProject", "")
        onAccepted: {
            if (sourceProject === Session.project) {
                DialogFolders.remember("exportProject", selectedFolder);
                Session.exportProjectCopy(program, selectedFolder);
            }
        }
    }
}
