// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// What the Experiments group says under its table about data it cannot use yet (ADR-0069): a scan folder or a data
// file that is not where the project says, with Locate…, and a collection's data not downloaded yet.
Column {
    id: group

    property ProjectViewModel project: null

    spacing: AppSizes.groupContentSpacing
    visible: project !== null && (project.missingDataFolder !== "" || project.missingDataFile !== "" || project.pendingCollectionData !== "")

    // A scan whose data folder cannot be found (ADR-0069): the project still opens; this line says which folder
    // and Locate folder… points the scan at its new place.
    Row {
        objectName: "experiments.dataNotFound"
        visible: group.project !== null && group.project.missingDataFolder !== ""
        spacing: EaStyle.Sizes.fontPixelSize
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            width: EaStyle.Sizes.sideBarContentWidth - locateButton.width - parent.spacing
            wrapMode: Text.Wrap
            color: EaStyle.Colors.red
            text: group.project !== null ? qsTr("Data not found: %1").arg(group.project.missingDataFolder) : ""
        }
        EaElements.Button {
            id: locateButton
            objectName: "experiments.locateFolder"
            text: qsTr("Locate folder…")
            onClicked: {
                // The chooser belongs to the project it was opened for: an answer after a change does nothing.
                locateDialog.project = group.project;
                locateDialog.missing = group.project.missingDataFolder;
                locateDialog.open();
            }
        }
    }
    // A linked experiment whose data file cannot be found: the same line for the selected
    // experiment, and Locate file… reads it from where it is now.
    Row {
        objectName: "experiments.dataFileNotFound"
        visible: group.project !== null && group.project.missingDataFile !== ""
        spacing: EaStyle.Sizes.fontPixelSize
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            width: EaStyle.Sizes.sideBarContentWidth - locateFileButton.width - parent.spacing
            wrapMode: Text.Wrap
            color: EaStyle.Colors.red
            text: group.project !== null ? qsTr("Data not found: %1").arg(group.project.missingDataFile) : ""
        }
        EaElements.Button {
            id: locateFileButton
            objectName: "experiments.locateFile"
            text: qsTr("Locate file…")
            onClicked: {
                locateFileDialog.project = group.project;
                locateFileDialog.experiment = group.project.currentExperiment;
                locateFileDialog.open();
            }
        }
    }
    // Data from a collection that is not here yet (edi ADR-0069): it is downloaded when a fit starts, or now.
    Row {
        objectName: "experiments.collectionDataPending"
        visible: group.project !== null && group.project.pendingCollectionData !== ""
        spacing: EaStyle.Sizes.fontPixelSize
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            width: EaStyle.Sizes.sideBarContentWidth - downloadButton.width - parent.spacing
            wrapMode: Text.Wrap
            text: group.project !== null ? qsTr("Not downloaded yet: %1. It is downloaded when a fit starts.").arg(group.project.pendingCollectionData) : ""
        }
        EaElements.Button {
            id: downloadButton
            objectName: "experiments.downloadData"
            text: qsTr("Download")
            onClicked: group.project.downloadCollectionData()
        }
    }
    FileDialog {
        id: locateFileDialog
        property ProjectViewModel project: null
        property ExperimentViewModel experiment: null
        title: qsTr("Locate the experiment's data file")
        fileMode: FileDialog.OpenFile
        onAccepted: {
            if (project !== null && project === group.project)
                project.locateDataFile(experiment, selectedFile);
        }
    }
    FolderDialog {
        id: locateDialog
        property ProjectViewModel project: null
        property string missing: ""
        title: qsTr("Locate the scan's data folder")
        onAccepted: {
            if (project !== null && project === group.project)
                project.locateDataFolder(selectedFolder, missing);
        }
    }
}
