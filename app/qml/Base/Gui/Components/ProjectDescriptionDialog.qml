// SPDX-License-Identifier: BSD-3-Clause
// Pinned gui-components copy; the project's location joins its folder and name with one separator (the owner,
// 2026-10-08): the Location field holds the folder and Create saves into its short-name folder. It also asks for
// the title and the authors, in the Project page's order (the owner, 2026-10-13). Each field says what it is for (the owner,
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
    // Where Create saves: the short-name folder inside the Location field's folder, joined once; none without a folder.
    function chosenLocation() {
        const folder = projectLocationField.text.trim();
        return folder === "" ? "" : joinedPath(folder, projectName);
    }
    // An empty form for another project; the folder chosen for new projects is remembered.
    function startOver() {
        for (const field of [projectNameField, projectTitleField, projectAuthorsField, projectDescriptionField])
            field.text = "";
        projectLocationField.text = Qt.binding(projectLocationField.parentFolder);
        projectLocation = "";
    }
    function tryAccept() {
        const location = chosenLocation();
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

    onAccepted: projectLocation = chosenLocation()
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
                    regularExpression: /^[a-zA-Z][a-zA-Z0-9_\-]{1,30}$/
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
                function parentFolder() {
                    return dialog.projectParentDirectory ? EaLogic.Utils.urlToLocalFile(dialog.projectParentDirectory) : dialog.defaultProjectParentDirectory;
                }
                text: parentFolder()

                Keys.onReturnPressed: dialog.tryAccept()
                Keys.onEnterPressed: dialog.tryAccept()

                EaElements.ToolButton {
                    id: chooseParentDirectoryButton

                    anchors.right: parent.right

                    fontIcon: "folder-open"
                    ToolTip.text: qsTr("Choose the folder in which the project folder is created")

                    showBackground: false

                    objectName: "createProject.chooseLocation"
                    onClicked: dialog.openLocationPicker()
                }
            }
        }
    }

    // The folder in which the project folder is created. A picker is made for each showing and goes with it, and only
    // the showing still current, for the project it was opened on, may set the folder: a platform can deliver an
    // answer after close(), and a replaced project's answer would otherwise become the next project's location and
    // the saved preference. Each showing answers once, so a late Accepted after its Rejected changes nothing.
    // `locationPicker`: the current showing, `{picker, generation}`, or null.
    property var locationPicker: null
    function openLocationPicker() {
        retirePickers();
        const picker = locationPickerComponent.createObject(dialog.contentItem, {
            selectedFolder: projectParentDirectory
        }) as FolderDialog;
        const showing = {
            picker: picker,
            generation: Session.projectGeneration()
        };
        // Each handler names its own showing.
        picker.accepted.connect(() => dialog.answerLocationPicker(showing, true));
        picker.rejected.connect(() => dialog.answerLocationPicker(showing, false));
        locationPicker = showing;
        picker.open();
    }
    function answerLocationPicker(showing, accepted) {
        if (showing !== locationPicker)
            return;
        locationPicker = null;
        const folder = showing.picker.selectedFolder;
        showing.picker.destroy();
        if (accepted && showing.generation === Session.projectGeneration())
            projectParentDirectory = folder;
    }
    // When the project is replaced. The picker stops being current before close(), which emits its answer at once.
    function retirePickers() {
        const showing = locationPicker;
        if (showing === null)
            return;
        locationPicker = null;
        showing.picker.close();
        showing.picker.destroy();
    }

    Component {
        id: locationPickerComponent

        FolderDialog {
            objectName: "createProject.locationPicker"
            title: qsTr("Choose the folder for the project")
        }
    }

    // Persistent settings

    Settings {
        location: EaGlobals.Vars.settingsFile // Gives WASM error on run
        category: 'Project.Location'
        property alias projectParentDirectory: dialog.projectParentDirectory
    }
}
