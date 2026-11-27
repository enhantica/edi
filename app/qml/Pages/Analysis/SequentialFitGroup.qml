// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `sequential_fit`: the scan's declaration. The data directory has a row of its own, typed or chosen with the button
// inside it, as Create project's Location; the file pattern and the order are shown below it.
Column {
    id: group

    property ProjectViewModel project: null
    property AnalysisViewModel analysis: null
    readonly property SequentialFitViewModel fit: analysis ? analysis.sequentialFit : null
    // A browser gives the app no folder to name.
    property bool folderEditable: !WebFiles.available

    spacing: AppSizes.groupContentSpacing

    ValueField {
        id: folderField

        objectName: "sequentialFit.dataDir"
        width: EaStyle.Sizes.sideBarContentWidth
        rightPadding: browseButton.visible ? browseButton.width : padding
        horizontalAlignment: TextInput.AlignLeft
        editable: group.folderEditable
        uid: "sequential_fit.data_dir"
        fieldValue: group.fit ? group.fit.dataDir : ""
        shortened: contentWidth > width - leftPadding - rightPadding
        onCommitted: text => group.project.setDataFolder(text)

        EaElements.ToolButton {
            id: browseButton

            objectName: "sequentialFit.dataDir.browse"
            visible: group.folderEditable
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: height
            height: folderField.height - folderField.topInset
            fontIcon: "folder-open"
            ToolTip.text: qsTr("Choose the folder of the scan's data files")
            showBackground: false
            onClicked: {
                // The chooser belongs to the project it was opened for: an answer after a change does nothing.
                folderDialog.project = group.project;
                folderDialog.open();
            }
        }
    }
    EaElements.GroupRow {
        spacing: AppSizes.inputSpacing

        ValueField {
            objectName: "sequentialFit.filePattern"
            editable: false
            uid: "sequential_fit.file_pattern"
            fieldValue: group.fit ? group.fit.filePattern : ""
        }
        FlagField {
            objectName: "sequentialFit.reverse"
            editable: false
            uid: "sequential_fit.reverse"
            disabledReason: qsTr("Part of the scan declaration, which this group shows but does not edit: change it in the Analysis Text tab")
            checked: group.fit ? group.fit.reverse : false
        }
    }
    FolderDialog {
        id: folderDialog

        property ProjectViewModel project: null

        title: qsTr("Choose the folder of the scan's data files")
        currentFolder: DialogFolders.folder("loadData", "")
        onAccepted: {
            DialogFolders.remember("loadData", selectedFolder);
            if (project !== null && project === group.project)
                project.locateDataFolder(selectedFolder);
        }
    }
}
