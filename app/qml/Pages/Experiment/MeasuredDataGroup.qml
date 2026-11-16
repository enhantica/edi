// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Measured data: what the selected experiment measures, and Load ▾ to bring it in or replace it, from a file, a folder
// of datasets or the web (the owner, 2026-11-04, 2026-11-14). A new experiment always starts from Create in the
// Experiments group; measured data then goes into the selected one. Data the project cannot find, or a collection's
// data not downloaded yet, is shown here with its fix. The file choosers stay the Experiments group's (`experiments`),
// which owns the loading dialogs.
SideBarGroup {
    id: group

    property ProjectViewModel project: null
    // The Experiments group: its functions open the data choosers in its own context.
    property var experiments: null
    readonly property ExperimentViewModel selected: project ? project.currentExperiment : null
    readonly property bool dataIntoSelected: selected !== null && selected.canLoadData
    readonly property bool replacing: selected !== null && !selected.calculationOnly

    objectName: "group.measuredData"
    title: qsTr("Measured data")
    icon: "chart-area"
    last: SideBarGroups.isLast(group)
    collapsed: false

    Column {
        spacing: AppSizes.groupContentSpacing

        // What Load does now: into the selected experiment, replacing what it holds, or nothing until one exists.
        EaElements.Label {
            objectName: "measuredData.target"
            width: EaStyle.Sizes.sideBarContentWidth
            wrapMode: Text.Wrap
            color: group.selected === null ? EaStyle.Colors.red : EaStyle.Colors.themeForeground
            text: group.selected === null ? qsTr("Create an experiment first to load data into it") : group.replacing ? qsTr("Replace measured data of %1").arg(group.selected.name) : qsTr("Load measured data into %1").arg(group.selected.name)
        }

        EaElements.SideBarButton {
            id: loadButton
            objectName: "experiments.load.data"
            width: EaStyle.Sizes.sideBarContentWidth
            enabled: group.dataIntoSelected
            fontIcon: "upload"
            text: group.project && group.project.listingDatasetFolder ? qsTr("Listing datasets…") : qsTr("Load measured data")

            EaElements.Label {
                anchors.right: parent.right
                anchors.rightMargin: EaStyle.Sizes.fontPixelSize * 0.75
                anchors.verticalCenter: parent.verticalCenter
                font.family: EaStyle.Fonts.iconsFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.9
                color: loadButton.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundDisabled
                text: "caret-down"
            }
            ToolTip.text: group.selected === null ? qsTr("Create an experiment first to load data into it") : qsTr("Load measured data into the selected experiment from a file, a folder or the web")
            onClicked: dataMenu.open()

            EaElements.Menu {
                id: dataMenu
                objectName: "experiments.load.dataMenu"
                y: loadButton.height
                bottomPadding: 0
                width: Math.max(loadButton.width, EaStyle.Sizes.fontPixelSize * 24)

                LoadMenuItem {
                    objectName: "experiments.load.dataFile"
                    enabled: group.dataIntoSelected
                    fontIcon: "file"
                    text: qsTr("From file…")
                    hint: ".xye .xy .dat .txt .csv · .int .hkl"
                    toolTip: group.selected === null ? "" : group.replacing ? qsTr("Replace the measured data of %1 with a file's; its type and parameters stay, Undo brings the data back").arg(group.selected.name) : qsTr("Load a measured pattern or reflection list into %1").arg(group.selected.name)
                    onTriggered: group.experiments.confirmScanReplacement(() => group.experiments.chooseDataForSelected())
                }
                LoadMenuItem {
                    objectName: "experiments.load.dataFolder"
                    enabled: group.dataIntoSelected && group.project !== null && !group.project.listingDatasetFolder
                    fontIcon: "folder-open"
                    text: qsTr("From folder…")
                    hint: Session.optionLabel("fitting_mode.type", "sequential")
                    toolTip: qsTr("Load all datasets in a folder; fit the template first, then choose Sequential in Analysis")
                    onTriggered: group.experiments.confirmScanReplacement(() => group.experiments.chooseFolderForSelected())
                }
                LoadMenuItem {
                    objectName: "experiments.load.dataWeb"
                    enabled: group.dataIntoSelected
                    fontIcon: "globe"
                    text: qsTr("From web…")
                    hint: "EasyDiffraction"
                    toolTip: group.selected === null ? "" : qsTr("Search EasyDiffraction's collection for measured data for %1").arg(group.selected.name)
                    onTriggered: group.experiments.chooseWebDataForSelected()
                }
            }
        }

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
}
