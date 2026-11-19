// SPDX-License-Identifier: BSD-3-Clause
// Pinned gui-components copy; the project's location joins its folder and name with one separator, and the
// location the dialog shows is the one Create project saves into (the owner, 2026-10-08). It also asks for the title
// and the authors, in the Project page's order (the owner, 2026-10-13). Each field says what it is for (the owner,
// 2026-11-19): Short name · Folder names the project folder; Title, Authors and Description are shown in the report
// (the CIF export does not read them); Location is the folder in which the project folder is created. "Folder", never
// "Directory".
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtCore

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app
import EasyApplication.Gui.Logic as EaLogic

EaElements.Dialog {
    id: dialog

    property alias projectName: projectNameField.text
    property alias projectTitle: projectTitleField.text
    property alias projectAuthors: projectAuthorsField.text
    property alias projectDescription: projectDescriptionField.text

    function acceptsProjectName(value) {
        return ApplicationInfo.projectDescriptionAdmitted(value, false);
    }
    function acceptsProjectTitle(value) {
        return ApplicationInfo.projectDescriptionAdmitted(value, true);
    }
    readonly property int projectTitleMaximumLength: projectTitleField.maximumLength

    property string projectLocation: ""
    property string projectParentDirectory: ""
    property string defaultProjectParentDirectory: projectLocation

    // A folder and a name joined by one separator, whatever separators the folder ends with (a folder chosen in
    // the dialog arrives as a URL that may end in one).
    function joinedPath(folder, name) {
        return ApplicationInfo.projectJoinedPath(folder, name);
    }

    property int inputFieldWidth: EaStyle.Sizes.fontPixelSize * 35
    // False for a project that is not saved when it is made (a tutorial's): no location to show.
    property bool showsLocation: true

    title: qsTr("Create project")

    // Whether the user chose Replace for a project already at the location (replaceAsked); reset at every opening.
    property bool replaceExisting: false
    signal replaceAsked(string name, string folder)
    // OK: a location already taken asks first, "Replace it?", and the form stays as typed until the answer (the
    // owner, 2026-11-04); Replace comes back through accept() with replaceExisting set.
    function tryAccept() {
        const location = projectLocationField.text;
        if (showsLocation && !replaceExisting && location !== "" && Session.locationExists(location)) {
            replaceAsked(projectName, Session.existingParentFolder(location));
            return;
        }
        accept();
    }

    // The dialog's own OK button, as every dialog has it (tutorials, the assistant and tests find it there), checks the
    // location first: it acts as an action button that calls tryAccept, never accepting by itself.
    standardButtons: Dialog.Ok
    Component.onCompleted: {
        const ok = dialog.standardButton(Dialog.Ok);
        ok.objectName = "createProject.accept";
        ok.DialogButtonBox.buttonRole = DialogButtonBox.ActionRole;
        ok.clicked.connect(dialog.tryAccept);
    }

    onAccepted: projectLocation = projectLocationField.text
    // OK is named as the dialog starts to show, and the name field takes the keyboard as it opens: what the user
    // types goes into the name at once.
    onAboutToShow: {
        replaceExisting = false;
        ApplicationInfo.projectDescriptionOpened(false);
    }
    onOpened: ApplicationInfo.projectDescriptionOpened(true)

    // Main layout

    Column {
        spacing: EaStyle.Sizes.fontPixelSize

        // Project name field

        Column {
            EaElements.Label {
                enabled: false
                text: qsTr("Short name · Folder")
            }

            EaElements.TextField {
                id: projectNameField

                objectName: "createProject.name"

                implicitWidth: dialog.inputFieldWidth
                horizontalAlignment: TextInput.AlignLeft
                validator: RegularExpressionValidator {
                    regularExpression: /^[a-zA-Z][a-zA-Z0-9_\-\.]{1,30}$/
                }
                placeholderText: qsTr("e.g. lbco-hrpt: becomes the project folder name; letters, digits, - and _")

                Keys.onReturnPressed: dialog.tryAccept()
                Keys.onEnterPressed: dialog.tryAccept()
            }
        }

        // Project title field

        Column {
            EaElements.Label {
                enabled: false
                text: qsTr("Title")
            }

            EaElements.TextField {
                id: projectTitleField

                objectName: "createProject.title"

                implicitWidth: dialog.inputFieldWidth
                horizontalAlignment: TextInput.AlignLeft
                placeholderText: qsTr("Optional: the title shown at the top of the report")

                Keys.onReturnPressed: dialog.tryAccept()
                Keys.onEnterPressed: dialog.tryAccept()
            }
        }

        // Project authors field

        Column {
            EaElements.Label {
                enabled: false
                text: qsTr("Authors")
            }

            EaElements.TextField {
                id: projectAuthorsField

                objectName: "createProject.authors"

                implicitWidth: dialog.inputFieldWidth
                horizontalAlignment: TextInput.AlignLeft
                placeholderText: qsTr("Optional, separated by ;  shown under the title in the report")

                Keys.onReturnPressed: dialog.tryAccept()
                Keys.onEnterPressed: dialog.tryAccept()
            }
        }

        // Project description field

        Column {
            EaElements.Label {
                enabled: false
                text: qsTr("Description")
            }

            // Several lines, as long a description as the project needs (the owner, 2026-10-27).
            MultiLineField {
                id: projectDescriptionField

                editorObjectName: "createProject.description"
                implicitWidth: dialog.inputFieldWidth
                placeholderText: qsTr("Optional: a few lines shown in the report under the authors")
            }
        }

        // Project location field

        Column {
            visible: dialog.showsLocation
            EaElements.Label {
                enabled: false
                text: qsTr("Location")
            }

            EaElements.TextField {
                id: projectLocationField
                objectName: "createProject.location"

                implicitWidth: dialog.inputFieldWidth
                rightPadding: chooseParentDirectoryButton.width
                horizontalAlignment: TextInput.AlignLeft

                placeholderText: qsTr("The folder in which the project folder is created")
                text: dialog.joinedPath(dialog.projectParentDirectory ? EaLogic.Utils.urlToLocalFile(dialog.projectParentDirectory) : dialog.defaultProjectParentDirectory, dialog.projectName)

                Keys.onReturnPressed: dialog.tryAccept()
                Keys.onEnterPressed: dialog.tryAccept()

                EaElements.ToolButton {
                    id: chooseParentDirectoryButton

                    anchors.right: parent.right

                    fontIcon: "folder-open"
                    ToolTip.text: qsTr("Choose the folder in which the project folder is created")

                    showBackground: false

                    onClicked: projectParentDirDialog.open()
                }
            }
        }
    }

    // The folder in which the project folder is created

    FolderDialog {
        id: projectParentDirDialog

        title: qsTr("Choose the folder for the project")
        selectedFolder: dialog.projectParentDirectory
        onAccepted: dialog.projectParentDirectory = selectedFolder
    }

    // Persistent settings

    Settings {
        location: EaGlobals.Vars.settingsFile // Gives WASM error on run
        category: 'Project.Location'
        property alias projectParentDirectory: dialog.projectParentDirectory
    }
}
