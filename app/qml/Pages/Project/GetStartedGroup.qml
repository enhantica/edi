// SPDX-License-Identifier: BSD-3-Clause
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
                // Nothing below the last item (the owner, 2026-11-04).
                bottomPadding: 0
                width: Math.max(loadButton.width, EaStyle.Sizes.fontPixelSize * 26)

                readonly property real labelWidth: EaStyle.Sizes.fontPixelSize * 13

                LoadMenuHeader {
                    first: true
                    text: qsTr("Project")
                }
                // The browser's own chooser copies a folder into its storage; Chrome and Edge open it on the disk.
                LoadMenuItem {
                    objectName: "project.load.folder"
                    labelWidth: loadMenu.labelWidth
                    fontIcon: "folder-open"
                    text: qsTr("Open EasyDiffraction folder…")
                    hint: "project.edi"
                    toolTip: qsTr("Open an EasyDiffraction project from its folder")
                    onTriggered: group.openProject(false)
                }
                LoadMenuItem {
                    objectName: "project.load.zip"
                    labelWidth: loadMenu.labelWidth
                    fontIcon: "archive"
                    text: qsTr("Open EasyDiffraction zip…")
                    hint: ".zip"
                    toolTip: qsTr("Open an EasyDiffraction project from a .zip of its folder")
                    onTriggered: group.openProject(true)
                }
                // Not implemented yet: shown, disabled (edi ADR-0017 §4).
                LoadMenuItem {
                    objectName: "project.load.url"
                    labelWidth: loadMenu.labelWidth
                    enabled: false
                    fontIcon: "link"
                    text: qsTr("Open from URL…")
                    toolTip: qsTr("Open an EasyDiffraction project from a web address")
                }
                LoadMenuHeader {
                    text: qsTr("Import from another program")
                }
                // Not implemented yet: shown, disabled (edi ADR-0017 §4).
                LoadMenuItem {
                    objectName: "project.import.cryspy"
                    labelWidth: loadMenu.labelWidth
                    enabled: false
                    fontIcon: "file-import"
                    text: qsTr("Import cryspy…")
                    hint: ".rcif"
                    toolTip: qsTr("Import a cryspy project")
                }
                LoadMenuItem {
                    objectName: "project.import.fullProf"
                    labelWidth: loadMenu.labelWidth
                    // The importers read files from the disk; the browser has none to give them yet.
                    enabled: !WebFiles.available
                    fontIcon: "file-import"
                    text: qsTr("Import FullProf…")
                    hint: ".pcr"
                    toolTip: qsTr("Import a FullProf project from its .pcr file and the data files beside it")
                    onTriggered: importFullProfDialog.open()
                }
                LoadMenuItem {
                    objectName: "project.import.gsas"
                    labelWidth: loadMenu.labelWidth
                    enabled: !WebFiles.available
                    fontIcon: "file-import"
                    text: qsTr("Import GSAS-II…")
                    hint: ".gpx"
                    toolTip: qsTr("Import a GSAS-II project from its .gpx file or a GSAS-II text bundle")
                    onTriggered: importGsasDialog.open()
                }
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
                bottomPadding: 0
                width: Math.max(saveButton.width, EaStyle.Sizes.fontPixelSize * 26)

                readonly property real labelWidth: EaStyle.Sizes.fontPixelSize * 13
                // A browser without the File System Access API writes no folder on the disk: a .zip copy only.
                readonly property bool diskWritable: !WebFiles.available || WebStorage.diskAccess
                property bool copy: false
                onAboutToShow: copy = !diskWritable

                LoadMenuHeader {
                    first: true
                    text: qsTr("Project")
                }
                LoadMenuItem {
                    objectName: "project.saveAs.folder"
                    labelWidth: saveMenu.labelWidth
                    enabled: saveMenu.diskWritable
                    fontIcon: "folder-open"
                    text: qsTr("As EasyDiffraction folder…")
                    hint: "project.edi"
                    toolTip: saveMenu.diskWritable ? qsTr("Save the project as a folder holding project.edi") : qsTr("This browser cannot write a folder on your disk; Chrome and Edge can")
                    onTriggered: AppState.saveAsFormatRequested(false, saveMenu.copy)
                }
                LoadMenuItem {
                    objectName: "project.saveAs.zip"
                    labelWidth: saveMenu.labelWidth
                    fontIcon: "archive"
                    text: qsTr("As Zip…")
                    hint: ".zip"
                    toolTip: qsTr("Save the project as a .zip of its folder")
                    onTriggered: AppState.saveAsFormatRequested(true, saveMenu.copy)
                }
                // Applies to the two EasyDiffraction choices above; the exports below always write a copy.
                EaElements.CheckBox {
                    objectName: "project.saveAs.copy"
                    leftPadding: EaStyle.Sizes.fontPixelSize * 0.5
                    enabled: saveMenu.diskWritable
                    text: qsTr("Save a copy")
                    checked: saveMenu.copy
                    onToggled: saveMenu.copy = checked
                    ToolTip.text: qsTr("Write the project there and keep working where it is")
                }
                LoadMenuHeader {
                    text: qsTr("Export to another program (always a copy)")
                }
                // Not implemented yet: shown, disabled (edi ADR-0017 §4).
                LoadMenuItem {
                    objectName: "project.export.cryspy"
                    labelWidth: saveMenu.labelWidth
                    enabled: false
                    fontIcon: "file-export"
                    text: qsTr("As cryspy…")
                    hint: ".rcif"
                    toolTip: qsTr("Export a copy of the project for cryspy")
                }
                LoadMenuItem {
                    objectName: "project.export.fullProf"
                    labelWidth: saveMenu.labelWidth
                    enabled: !WebFiles.available
                    fontIcon: "file-export"
                    text: qsTr("As FullProf…")
                    hint: ".pcr"
                    toolTip: qsTr("Export a copy of the project as a FullProf .pcr with its data files; the app keeps working on this project")
                    onTriggered: {
                        exportFullProfFolder.sourceProject = Session.project;
                        exportFullProfFolder.open();
                    }
                }
                LoadMenuItem {
                    objectName: "project.export.gsas"
                    labelWidth: saveMenu.labelWidth
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

    // Open project (edi ADR-0052 §3, §9): once unsaved changes are dealt with, the system's folder chooser for the
    // project folder holding project.edi, or its file chooser for a .zip; in the browser the browser's own chooser.
    function openProject(zip) {
        const life = group.createLife;
        AppState.afterChanges(() => {
            if (!life.alive)
                return;
            if (WebFiles.available)
                Session.openWebProject(zip ? "file" : "folder");
            else
                Qt.callLater(() => (zip ? openZipDialog : openFolderDialog).open());
        });
    }

    // Save on the untitled project opens Create project here: it names the project and saves it, its work kept.
    Connections {
        target: AppState
        function onUntitledSaveRequested() {
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
        // On an untitled project the form starts from what the Project page already holds for it.
        onAboutToShow: {
            if (Session.untitled && Session.project !== null) {
                projectTitle = Session.project.title;
                projectAuthors = Session.project.authors;
                projectDescription = Session.project.description;
            }
        }
        onOpened: ApplicationInfo.createProjectDialogEvent(0)
        onRejected: ApplicationInfo.createProjectDialogEvent(1)
        onClosed: ApplicationInfo.createProjectDialogEvent(2)
        // A new project's folder is beside the last project opened, else under the user's documents, unless one was
        // chosen before; it is saved there at once (the owner, 2026-10-08 and 2026-11-02). The browser has no folder to
        // save into: Save As downloads it.
        readonly property string lastOpenFolder: Session.existingParentFolder(RecentProjects.last)
        defaultProjectParentDirectory: lastOpenFolder !== "" ? lastOpenFolder : EaLogic.Utils.urlToLocalFile(String(StandardPaths.writableLocation(StandardPaths.DocumentsLocation)))
        // On the next turn: the new project replaces this page, dialog and all (AppState.afterChanges). The flag is
        // reset here, not only when the dialog has closed: this page goes before its closing ends, and the new page's
        // dialog would open again on a flag still set.
        onAccepted: ApplicationInfo.createProjectDialogEvent(3)
        onReplaceAsked: (name, folder) => {
            replaceProject.projectName = name;
            replaceProject.folder = folder;
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

    // The system's choosers. On the next turn the opened project replaces this page, dialogs and all
    // (AppState.afterChanges).
    // Both open where a project was last chosen.
    FolderDialog {
        id: openFolderDialog
        title: qsTr("Open an edi project folder")
        acceptLabel: qsTr("Open")
        currentFolder: DialogFolders.folder("openProject", "")
        onAccepted: {
            DialogFolders.remember("openProject", selectedFolder);
            Qt.callLater(Session.openProject, selectedFolder);
        }
    }
    FileDialog {
        id: openZipDialog
        title: qsTr("Open an edi project archive")
        nameFilters: [qsTr("edi project archives (*.zip)")]
        currentFolder: DialogFolders.folder("openProject", "")
        onAccepted: {
            DialogFolders.remember("openProject", selectedFile);
            Qt.callLater(Session.openProject, selectedFile);
        }
    }
    // Imports open as a new, unsaved project, as Open does: on the next turn it replaces this page.
    FileDialog {
        id: importFullProfDialog
        title: qsTr("Import a FullProf project")
        nameFilters: [qsTr("FullProf control files (*.pcr *.PCR)")]
        currentFolder: DialogFolders.folder("importProject", "")
        onAccepted: {
            DialogFolders.remember("importProject", selectedFile);
            Qt.callLater(Session.openProject, selectedFile);
        }
    }
    FileDialog {
        id: importGsasDialog
        title: qsTr("Import a GSAS-II project")
        nameFilters: [qsTr("GSAS-II projects (*.gpx *.gsas.json)")]
        currentFolder: DialogFolders.folder("importProject", "")
        onAccepted: {
            DialogFolders.remember("importProject", selectedFile);
            Qt.callLater(Session.openProject, selectedFile);
        }
    }
    // A FullProf export writes a new folder beside the chosen one's other projects and leaves this project open.
    FolderDialog {
        id: exportFullProfFolder
        property var sourceProject
        title: qsTr("Choose where to create the FullProf project folder")
        currentFolder: DialogFolders.folder("exportProject", "")
        onAccepted: {
            if (sourceProject === Session.project) {
                DialogFolders.remember("exportProject", selectedFolder);
                Session.exportFullProf(selectedFolder, false);
            }
        }
    }
}
