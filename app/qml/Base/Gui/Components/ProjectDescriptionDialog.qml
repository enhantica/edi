// SPDX-License-Identifier: BSD-3-Clause
// Pinned gui-components copy; the project's location joins its folder and name with one separator, and the
// location the dialog shows is the one Create project saves into (the owner, 2026-10-08). It also asks for the title
// and the authors, in the Project page's order (the owner, 2026-10-13).
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtCore

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Logic as EaLogic

EaElements.Dialog {
    id: dialog

    property alias projectName: projectNameField.text
    property alias projectTitle: projectTitleField.text
    property alias projectAuthors: projectAuthorsField.text
    property alias projectDescription: projectDescriptionField.text

    property string projectLocation: ""
    property string projectParentDirectory: ""
    property string defaultProjectParentDirectory: projectLocation

    // A folder and a name joined by one separator, whatever separators the folder ends with (a folder chosen in
    // the dialog arrives as a URL that may end in one).
    function joinedPath(folder, name) {
        let path = folder;
        while (path.length > 1 && (path.endsWith("/") || path.endsWith("\\")))
            path = path.slice(0, -1);
        if (path === "")
            return name;
        return path.endsWith("/") || path.endsWith("\\") ? path + name : path + EaLogic.Utils.osPathSep() + name;
    }

    property int inputFieldWidth: EaStyle.Sizes.fontPixelSize * 35

    objectName: "createProject.dialog"
    title: qsTr("Create project")
    onOpened: {
        const button = standardButton(Dialog.Ok);
        if (button) button.objectName = "createProject.accept";
    }

    standardButtons: Dialog.Ok

    onAccepted: projectLocation = projectLocationField.text

    // Main layout

    Column {
        spacing: EaStyle.Sizes.fontPixelSize

        // Project name field

        Column {
            EaElements.Label {
                enabled: false
                text: qsTr("Name")
            }

            EaElements.TextField {
                id: projectNameField

                objectName: "createProject.name"

                implicitWidth: dialog.inputFieldWidth
                horizontalAlignment: TextInput.AlignLeft
                validator: RegularExpressionValidator {
                    regularExpression: /^[^/\\\u0000]+$/
                }
                placeholderText: qsTr("Enter project name here")

                Keys.onReturnPressed: dialog.accept()
                Keys.onEnterPressed: dialog.accept()
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
                placeholderText: qsTr("Enter project title here")

                Keys.onReturnPressed: dialog.accept()
                Keys.onEnterPressed: dialog.accept()
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
                placeholderText: qsTr("Enter authors here, separated by ;")

                Keys.onReturnPressed: dialog.accept()
                Keys.onEnterPressed: dialog.accept()
            }
        }

        // Project description field

        Column {
            EaElements.Label {
                enabled: false
                text: qsTr("Description")
            }

            EaElements.TextArea {
                id: projectDescriptionField
                objectName: "createProject.description"

                implicitWidth: dialog.inputFieldWidth
                horizontalAlignment: TextInput.AlignLeft
                placeholderText: qsTr("Enter project description here")

                wrapMode: TextEdit.Wrap
                implicitHeight: Math.max(contentHeight + topPadding + bottomPadding, font.pixelSize * 3)
            }
        }

        // Project location field

        Column {
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

                placeholderText: qsTr("Enter project location here")
                text: dialog.joinedPath(dialog.projectParentDirectory ? EaLogic.Utils.urlToLocalFile(dialog.projectParentDirectory) : dialog.defaultProjectParentDirectory, dialog.projectName)

                Keys.onReturnPressed: dialog.accept()
                Keys.onEnterPressed: dialog.accept()

                EaElements.ToolButton {
                    id: chooseParentDirectoryButton

                    anchors.right: parent.right

                    fontIcon: "folder-open"
                    ToolTip.text: qsTr("Choose project parent directory")

                    showBackground: false

                    onClicked: projectParentDirDialog.open()
                }
            }
        }
    }

    // Choose project parent directory dialog

    FolderDialog {
        id: projectParentDirDialog

        title: qsTr("Choose project parent directory")
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
