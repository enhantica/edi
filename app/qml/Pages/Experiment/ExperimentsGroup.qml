// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// Experiments (N) (easydiffractionbeta Pages/Experiment/SideBarBasic/Experiments.qml): the project's
// experiments, one current, each with how the last fit ended on it (Fit) and the file its data is in; under
// the table the selected experiment's type (ExperimentTypeGroup), then Load experiment (`.edi` block files,
// several at once, each with its type, data and parameters) and Create experiment (a new experiment without
// data, a simulation). A row without data has a Load data… button in its File cell, disabled until plain data
// files load. Create and Load are each one undoable step.
EaElements.GroupBox {
    id: group

    property ProjectViewModel project: null

    objectName: "group.experiments"
    title: qsTr("Experiments (%1)").arg(project ? project.experiments.count : 0)
    icon: "microscope"
    last: SideBarGroups.isLast(group)

    Column {
        spacing: AppSizes.groupContentSpacing

        EaComponents.TableView {
            id: table
            objectName: "experiments.list"
            defaultInfoText: qsTr("No experiments defined")
            model: group.project ? group.project.experiments : null

            header: EaComponents.TableViewHeader {
                EaComponents.TableViewLabel {
                    width: AppSizes.indexColumnWidth
                    text: qsTr("No.")
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.tableRowHeight
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.tableRowHeight
                    text: qsTr("Fit")
                }
                EaComponents.TableViewLabel {
                    flexibleWidth: true
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Datablock")
                }
                EaComponents.TableViewLabel {
                    width: AppSizes.fileColumnWidth
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("File")
                }
                EaComponents.TableViewLabel {
                    width: AppSizes.iconColumnWidth
                }
            }

            delegate: EaComponents.TableViewDelegate {
                id: row

                required property int index
                required property string name
                required property ExperimentViewModel experiment
                required property string fitOutcome

                objectName: `experiments.row.${index}`
                color: group.project && group.project.currentExperimentIndex === index ? EaStyle.Colors.tableHighlight : (index % 2 ? EaStyle.Colors.themeBackgroundHovered2 : EaStyle.Colors.themeBackgroundHovered1)
                mouseArea.onPressed: group.project.currentExperimentIndex = row.index

                EaComponents.TableViewLabel {
                    width: AppSizes.indexColumnWidth
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                // The block's icon in its colour (easydiffractionbeta's colour column; ADR-0017 §8).
                IconCell {
                    objectName: `experiments.color.${row.index}`
                    icon: "microscope"
                    iconColor: AppColors.experiment(row.index)
                    toolTip: qsTr("Measured pattern color")
                }
                // How the project's last fit ended on this experiment; empty when it has no result.
                IconCell {
                    objectName: `experiments.fit.${row.index}`
                    icon: FitOutcomes.icon(row.fitOutcome)
                    iconColor: String(FitOutcomes.color(row.fitOutcome))
                    toolTip: FitOutcomes.word(row.fitOutcome)
                }
                // The datablock name, editable: a refused rename returns the cell to the stored name and shows why.
                // Editing a name also makes its row current, as a click on the row does.
                TextCell {
                    objectName: `experiments.name.${row.index}`
                    width: table.headerLabelItems.length > 3 ? table.headerLabelItems[3].width : 0
                    value: row.name
                    onActiveFocusChanged: if (activeFocus)
                        group.project.currentExperimentIndex = row.index
                    onCommitted: text => row.experiment.name = text
                }
                // The data's file: the experiment's own `.edi`, which holds its data; Load data… without data.
                Item {
                    width: AppSizes.fileColumnWidth
                    height: parent ? parent.height : 0

                    EaComponents.TableViewLabel {
                        visible: row.experiment !== null && !row.experiment.calculationOnly
                        width: parent.width
                        horizontalAlignment: Text.AlignLeft
                        elide: Text.ElideMiddle
                        text: `${row.name}.edi`
                    }
                    EaElements.Button {
                        objectName: `experiments.loadData.${row.index}`
                        visible: row.experiment !== null && row.experiment.calculationOnly
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width
                        enabled: false
                        text: qsTr("Load data…")
                    }
                }
                EaComponents.TableViewButton {
                    objectName: `experiments.remove.${row.index}`
                    fontIcon: "minus-circle"
                    ToolTip.text: qsTr("Remove this experiment")
                    onClicked: group.project.removeExperiment(row.index)
                }
            }
        }

        ExperimentTypeGroup {
            visible: group.project !== null && group.project.currentExperiment !== null
            project: group.project
            experiment: group.project ? group.project.currentExperiment : null
            experimentIndex: group.project ? group.project.currentExperimentIndex : -1
        }

        Row {
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.SideBarButton {
                objectName: "experiments.load"
                enabled: group.project !== null
                fontIcon: "upload"
                text: qsTr("Load experiment")
                ToolTip.text: qsTr("Load experiments from .edi files, each with its type, data and parameters")
                // In the browser the files come through the page (edi ADR-0023).
                onClicked: {
                    if (WebFiles.available) {
                        group.webRequestProject = group.project;
                        group.webRequest = WebFiles.openFiles(".edi", true);
                    } else {
                        loadDialog.open();
                    }
                }
            }
            EaElements.SideBarButton {
                objectName: "experiments.create"
                enabled: group.project !== null && group.project.canCreateExperiment
                fontIcon: "plus-circle"
                text: qsTr("Create experiment")
                ToolTip.text: enabled ? qsTr("Add an experiment without data, to calculate its pattern") : qsTr("The project's experiments carry measured data; an experiment without data cannot join them")
                onClicked: group.project.createExperiment()
            }
        }
    }

    // This page's browser file request and the project it was made for: only its own answer is used, and only
    // while that project is still open.
    property int webRequest: 0
    property var webRequestProject: null
    Connections {
        target: WebFiles
        function onFilesOpened(request, files) {
            if (request !== group.webRequest)
                return;
            group.webRequest = 0;
            if (group.project !== null && group.project === group.webRequestProject)
                group.project.loadExperiments(files);
        }
        function onFailed(request) {
            if (request === group.webRequest)
                group.webRequest = 0;
        }
        function onCancelled(request) {
            if (request === group.webRequest)
                group.webRequest = 0;
        }
    }

    FileDialog {
        id: loadDialog
        title: qsTr("Load experiments from .edi block files")
        fileMode: FileDialog.OpenFiles
        nameFilters: [qsTr("edi block files (*.edi)")]
        onAccepted: group.project.loadExperiments(selectedFiles)
    }
}
